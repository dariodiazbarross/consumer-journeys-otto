"""Consolidate full-data quality, journey, sample-flow and resource evidence."""
import json

from src.common import ROOT, connect, parquet_view, save_json


def query_dicts(relation) -> list[dict]:
    columns = [item[0] for item in relation.description]
    return [dict(zip(columns, row)) for row in relation.fetchall()]


def audit() -> None:
    if not (ROOT / "reports/ingestion.json").exists():
        raise RuntimeError("Run acquisition and ingestion first")
    ingestion = json.loads((ROOT / "reports/ingestion.json").read_text())
    con = connect()
    session_path = (ROOT / "data/interim/sessions/*/*.parquet").as_posix()
    transition_path = (ROOT / "data/interim/action_transitions/*/*.parquet").as_posix()
    con.execute(f"""CREATE VIEW all_sessions AS
        SELECT * EXCLUDE(filename), CASE WHEN filename LIKE '%/train/%' THEN 'train' ELSE 'test' END AS source
        FROM read_parquet('{session_path}', filename=true)""")
    con.execute(f"""CREATE VIEW transitions AS
        SELECT * EXCLUDE(filename), CASE WHEN filename LIKE '%/train/%' THEN 'train' ELSE 'test' END AS source
        FROM read_parquet('{transition_path}', filename=true)""")
    session_summary = query_dicts(con.sql("""
        SELECT source,
               count(*) sessions, sum(n_events) events, sum(clicks) clicks, sum(carts) carts, sum(orders) orders,
               min(n_events) minimum_events, max(n_events) maximum_events,
               median(n_events) median_events, avg(n_events) mean_events,
               median(duration_hours) median_duration_hours, avg(duration_hours) mean_duration_hours,
               avg(repeat_share) mean_repeat_share,
               count(*) FILTER (WHERE n_events>=5) sessions_at_least_five
        FROM all_sessions GROUP BY source ORDER BY source
    """))
    duplicate_sessions = con.sql("SELECT count(*)-count(DISTINCT (source,session)) FROM all_sessions").fetchone()[0]
    action_transitions = query_dicts(con.sql("""
        SELECT source, source_action, destination_action, sum(transitions) transitions
        FROM transitions GROUP BY source, source_action, destination_action
        ORDER BY source, source_action, destination_action
    """))
    flow = {}
    for split in ("validation", "test"):
        parquet_view(con, f"{split}_prefixes", ROOT / f"data/processed/{split}/prefixes/*.parquet")
        source = "train" if split == "validation" else "test"
        source_sessions = next(x["sessions"] for x in session_summary if x["source"] == source)
        at_least_five = next(x["sessions_at_least_five"] for x in session_summary if x["source"] == source)
        row = con.sql(f"""
            SELECT count(*) eligible, count(*) FILTER (WHERE target_count>0) target_positive,
                   avg(target_count) FILTER (WHERE target_count>0) mean_target_set_size,
                   count(*) FILTER (WHERE prefix_length>5) cutoff_tie_extended,
                   count(*) FILTER (WHERE prefix_carts+prefix_orders=0) click_only,
                   avg(repeat_share) mean_prefix_repeat_share
            FROM {split}_prefixes
        """).fetchone()
        flow[split] = {"source_sessions": source_sessions, "sessions_at_least_five": at_least_five,
                       "excluded_too_short": source_sessions-at_least_five,
                       "eligible_after_time_and_horizon": row[0],
                       "excluded_time_or_horizon_among_long_enough": at_least_five-row[0],
                       "target_positive": row[1], "target_negative": row[0]-row[1],
                       "mean_positive_target_set_size": row[2], "cutoff_tie_extended": row[3],
                       "click_only_prefixes": row[4], "mean_prefix_repeat_share": row[5]}
    resources = []
    for path in (ROOT / "data/interim/completed").glob("*.json"):
        resources.append(json.loads(path.read_text()))
    report = {
        "source_ingestion": ingestion, "session_summary": session_summary,
        "duplicate_session_keys": duplicate_sessions, "action_block_transitions": action_transitions,
        "sample_flow": flow,
        "resource_profile": {
            "partitions": len(resources), "sql_elapsed_seconds": sum(x["seconds"] for x in resources),
            "maximum_worker_rss_bytes": max(x["rss_bytes"] for x in resources),
            "parquet_event_bytes": sum(p.stat().st_size for p in (ROOT / "data/interim/events").glob("*/*.parquet")),
            "sampling": "None; every source session and event was processed."
        }
    }
    save_json(ROOT / "reports/data_audit.json", report)
    con.close()
    print(json.dumps(report["sample_flow"], indent=2))


if __name__ == "__main__":
    audit()
