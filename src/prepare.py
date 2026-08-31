"""Run substantial SQL transformations on bounded, whole-session partitions."""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil

from src.common import DAY, ROOT, connect, export, parquet_view, run_sql, save_json


def boundaries() -> dict:
    path = ROOT / "reports/boundaries.json"
    if path.exists():
        return json.loads(path.read_text())
    audit = json.loads((ROOT / "reports/ingestion_test.json").read_text())
    hour = 3_600_000
    start = audit["minimum_ts"] // hour * hour
    end = (audit["maximum_ts"] // hour + 1) * hour
    assert end-start == 7*DAY
    result = {"validation_start": start-7*DAY, "validation_end": start,
              "test_start": start, "test_end": end}
    result["utc"] = {k: datetime.fromtimestamp(v/1000, timezone.utc).isoformat()
                     for k, v in result.items()}
    save_json(path, result)
    return result


def process_part(path: Path, source: str, bounds: dict) -> None:
    started = time.perf_counter()
    tag = f"{source}-{path.stem}"
    marker = ROOT / "data/interim/completed" / f"{tag}.json"
    if marker.exists():
        return
    con = connect()
    parquet_view(con, "raw_events", path)
    run_sql(con, "01_events.sql")
    run_sql(con, "02_sessions.sql")
    n_events = con.sql("SELECT count(*) FROM events").fetchone()[0]
    n_sessions = con.sql("SELECT count(*) FROM sessions").fetchone()[0]
    assert con.sql("SELECT sum(n_events) FROM sessions").fetchone()[0] == n_events
    assert con.sql("SELECT count(*) FROM events WHERE action NOT IN (0,1,2) OR aid<0").fetchone()[0] == 0
    export(con, "SELECT * FROM sessions", ROOT / f"data/interim/sessions/{source}/{path.name}")
    export(con, "SELECT * FROM action_transitions", ROOT / f"data/interim/action_transitions/{source}/{path.name}")
    split = "validation" if source == "train" else "test"
    con.execute("SET VARIABLE period_start = ?", [bounds[f"{split}_start"]])
    con.execute("SET VARIABLE period_end = ?", [bounds[f"{split}_end"]])
    run_sql(con, "04_prefixes.sql")
    assert con.sql("SELECT count(*) FROM eligible").fetchone()[0] == con.sql("SELECT count(*) FROM prefixes").fetchone()[0]
    assert con.sql("SELECT count(*) FROM prefix_events WHERE ts>cutoff").fetchone()[0] == 0
    assert con.sql("SELECT count(*) FROM prefix_items").fetchone()[0] == con.sql("SELECT count(DISTINCT (session,aid)) FROM prefix_items").fetchone()[0]
    export(con, "SELECT * FROM prefixes", ROOT / f"data/processed/{split}/prefixes/{path.name}")
    export(con, "SELECT * FROM prefix_items", ROOT / f"data/processed/{split}/prefix_items/{path.name}")
    resource = {"source": source, "partition": path.name, "events": n_events, "sessions": n_sessions,
                "prefixes": con.sql("SELECT count(*) FROM prefixes").fetchone()[0], "associations": {}}
    if source == "train":
        assert con.sql("SELECT max(ts) FROM events").fetchone()[0] < bounds["test_start"]
        for split in ("validation", "test"):
            con.execute("SET VARIABLE history_end = ?", [bounds[f"{split}_start"]])
            run_sql(con, "03_item_history.sql")
            export(con, "SELECT * FROM item_counts", ROOT / f"data/interim/history/{split}/items/{path.name}")
            run_sql(con, "05_transitions.sql")
            export(con, "SELECT * FROM pair_counts", ROOT / f"data/interim/history/{split}/pairs/{path.name}")
            row = con.sql("SELECT count(*), count(*) FILTER (WHERE n_items>10 OR next_n_items>10) FROM block_pairs").fetchone()
            resource["associations"][split] = {"relevant_block_pairs": row[0], "omitted_large_blocks": row[1]}
    resource["seconds"] = time.perf_counter()-started
    resource["rss_bytes"] = psutil.Process().memory_info().rss
    save_json(marker, resource)
    con.close()
    print(f"SQL {tag}: {n_events:,} events in {resource['seconds']:.1f}s; "
          f"RSS {resource['rss_bytes']/2**20:.0f} MiB", flush=True)


def finalize_history(split: str) -> None:
    output = ROOT / f"data/processed/{split}/popularity.parquet"
    if output.exists():
        return
    con = connect()
    parquet_view(con, "partial_items", ROOT / f"data/interim/history/{split}/items/*.parquet")
    con.execute("""
        CREATE TABLE item_totals AS SELECT aid, sum(support) AS support,
            sum(recent_support) AS recent_support, sum(cart_order_events) AS cart_order_events
        FROM partial_items GROUP BY aid;
        CREATE TABLE popularity AS
        WITH recent AS (
            SELECT aid, row_number() OVER (ORDER BY recent_support DESC, aid) AS recent_rank
            FROM item_totals WHERE recent_support>0
        )
        SELECT i.*, row_number() OVER (ORDER BY support DESC, i.aid) AS global_rank, r.recent_rank
        FROM item_totals i LEFT JOIN recent r ON i.aid=r.aid;
    """)
    export(con, "SELECT * FROM popularity", output)
    parquet_view(con, "partial_pairs", ROOT / f"data/interim/history/{split}/pairs/*.parquet")
    con.execute("""
        CREATE TABLE neighbors AS
        WITH combined AS (
            SELECT source_aid, aid, sum(support) AS support
            FROM partial_pairs GROUP BY source_aid, aid HAVING sum(support)>=2
        ), top_neighbors AS (
            SELECT *, row_number() OVER (PARTITION BY source_aid ORDER BY support DESC, aid) AS rank
            FROM combined QUALIFY rank<=30
        )
        SELECT *, support::DOUBLE / sum(support) OVER (PARTITION BY source_aid) AS strength
        FROM top_neighbors;
    """)
    export(con, "SELECT * FROM neighbors", ROOT / f"data/processed/{split}/neighbors.parquet")
    save_json(ROOT / f"reports/history_{split}.json", {
        "items": con.sql("SELECT count(*) FROM popularity").fetchone()[0],
        "neighbors": con.sql("SELECT count(*) FROM neighbors").fetchone()[0],
        "source_items_with_neighbors": con.sql("SELECT count(DISTINCT source_aid) FROM neighbors").fetchone()[0],
        "head_support_share": con.sql("SELECT sum(support) FILTER (WHERE global_rank <= (SELECT ceil(count(*)*.01) FROM popularity))/sum(support) FROM popularity").fetchone()[0],
    })
    con.close()


def prepare(watch: bool = False, limit: int | None = None) -> None:
    bounds = boundaries()
    processed = 0
    while True:
        changed = False
        for source in ("train", "test"):
            files = sorted((ROOT / f"data/interim/events/{source}").glob("*.parquet"))
            # Do not read a partition still being written by the ingestion process.
            source_finished = (ROOT / f"reports/ingestion_{source}.json").exists()
            available = files if source_finished else files[:-1]
            for path in available:
                if (ROOT / f"data/interim/completed/{source}-{path.stem}.json").exists():
                    continue
                process_part(path, source, bounds)
                changed = True
                processed += 1
                if limit and processed >= limit:
                    return
        complete = (ROOT / "reports/ingestion.json").exists()
        pending = any(
            not (ROOT / f"data/interim/completed/{source}-{path.stem}.json").exists()
            for source in ("train", "test")
            for path in (ROOT / f"data/interim/events/{source}").glob("*.parquet")
        )
        if complete and not pending:
            for split in ("validation", "test"):
                finalize_history(split)
            return
        if not watch:
            return
        if not changed:
            time.sleep(2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    prepare(args.watch, args.limit)
