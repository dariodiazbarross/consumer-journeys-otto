"""Batched, leakage-safe candidate ranking and paired session evaluation."""
import time

import numpy as np
import pandas as pd

from src.common import CONFIG, ROOT, connect, export, parquet_view, run_sql, save_json

METHODS = ("global", "recent", "repeat", "r", "ra", "c")


def rank_split(split: str) -> None:
    destination = ROOT / f"data/processed/{split}/evaluation"
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "_COMPLETE").exists():
        return
    con = connect()
    parquet_view(con, "popularity", ROOT / f"data/processed/{split}/popularity.parquet")
    parquet_view(con, "neighbors", ROOT / f"data/processed/{split}/neighbors.parquet")
    prefix_files = sorted((ROOT / f"data/processed/{split}/prefixes").glob("*.parquet"))
    item_root = ROOT / f"data/processed/{split}/prefix_items"
    result_part = 0
    started = time.perf_counter()
    for file_number, prefix_path in enumerate(prefix_files):
        parquet_view(con, "all_prefixes", prefix_path)
        parquet_view(con, "all_prefix_items", item_root / prefix_path.name)
        sessions = [r[0] for r in con.sql(
            "SELECT session FROM all_prefixes WHERE target_count>0 ORDER BY session").fetchall()]
        for begin in range(0, len(sessions), CONFIG["evaluation_batch_sessions"]):
            current = sessions[begin: begin+CONFIG["evaluation_batch_sessions"]]
            con.execute("CREATE OR REPLACE TEMP TABLE batch_ids(session BIGINT)")
            con.executemany("INSERT INTO batch_ids VALUES (?)", [(s,) for s in current])
            con.execute("CREATE OR REPLACE TEMP TABLE batch_prefixes AS SELECT p.* FROM all_prefixes p JOIN batch_ids USING(session)")
            con.execute("CREATE OR REPLACE TEMP TABLE batch_items AS SELECT p.* FROM all_prefix_items p JOIN batch_ids USING(session)")
            assert con.sql("SELECT count(*) FROM batch_ids").fetchone()[0] == con.sql("SELECT count(*) FROM batch_prefixes").fetchone()[0]
            run_sql(con, "06_candidates.sql")
            assert con.sql("SELECT count(*) FROM candidates").fetchone()[0] == con.sql("SELECT count(DISTINCT (session,aid)) FROM candidates").fetchone()[0]
            run_sql(con, "07_evaluation.sql")
            query = """
                SELECT e.*, p.prefix_length, p.distinct_items, p.repeat_share,
                       p.prefix_carts, p.prefix_orders,
                       CASE WHEN p.prefix_carts+p.prefix_orders=0 THEN 'click_only' ELSE 'prior_action' END AS prior_action_group,
                       CASE WHEN p.prefix_length=5 THEN 'five_events' ELSE 'cutoff_tie_extended' END AS length_group,
                       CASE WHEN p.repeat_share>=0.4 THEN 'repeat_heavy' ELSE 'broad_exploration' END AS exploration_group,
                       CASE
                         WHEN bool_and(coalesce(h.support,0)<5) THEN 'rare'
                         WHEN bool_and(h.global_rank <= (SELECT ceil(count(*)*.01) FROM popularity)) THEN 'head'
                         WHEN bool_or(coalesce(h.support,0)<5) OR bool_or(h.global_rank <= (SELECT ceil(count(*)*.01) FROM popularity)) THEN 'mixed'
                         ELSE 'tail' END AS target_popularity_group
                FROM evaluated e JOIN batch_prefixes p USING(session), unnest(p.targets) t(aid)
                LEFT JOIN popularity h ON t.aid=h.aid
                GROUP BY ALL
            """
            export(con, query, destination / f"part-{result_part:05d}.parquet")
            # Top-20 recommendations are retained locally only for coverage diagnostics.
            export(con, """
                SELECT session, aid, method, rank FROM ranks
                UNPIVOT (rank FOR method IN (global_rank,recent_rank,repeat_rank,r_rank,ra_rank,c_rank))
                WHERE rank<=20
            """, ROOT / f"data/processed/{split}/recommendations/part-{result_part:05d}.parquet")
            result_part += 1
            print(f"rank {split}: {file_number+1}/{len(prefix_files)}, {begin+len(current)}/{len(sessions)} "
                  f"({time.perf_counter()-started:.0f}s)", flush=True)
    (destination / "_COMPLETE").write_text(str(result_part), encoding="ascii")
    con.close()


def _bootstrap(frame: pd.DataFrame, columns: list[str]) -> dict:
    values = frame[columns].to_numpy(float)
    n = len(values)
    rng = np.random.default_rng(CONFIG["seed"])
    samples = np.empty((CONFIG["bootstrap_replicates"], len(columns)))
    # Mean frequency weights avoid allocating a 100M-element index matrix.
    for i in range(len(samples)):
        weight = rng.multinomial(n, np.full(n, 1/n))
        samples[i] = weight @ values / n
    return {column: {"estimate": float(values[:, j].mean()),
                     "ci95": [float(x) for x in np.quantile(samples[:, j], [.025, .975])]}
            for j, column in enumerate(columns)} | {"_draws": samples}


def summarize_split(split: str) -> dict:
    files = str(ROOT / f"data/processed/{split}/evaluation/*.parquet").replace("\\", "/")
    frame = pd.read_parquet(files)
    columns = [f"{m}_{metric}" for metric in ("recall", "mrr") for m in METHODS]
    base = _bootstrap(frame, columns)
    draws = base.pop("_draws")
    result = {"split": split, "target_positive_prefixes": len(frame), "metrics": base, "differences": {}}
    for metric in ("recall", "mrr"):
        for left, right in (("r","recent"),("ra","r"),("c","ra"),("c","repeat"),("c","recent"),("c","global")):
            name = f"{left}_minus_{right}_{metric}"
            diff = frame[f"{left}_{metric}"]-frame[f"{right}_{metric}"]
            j1, j0 = columns.index(f"{left}_{metric}"), columns.index(f"{right}_{metric}")
            result["differences"][name] = {"estimate": float(diff.mean()),
                "ci95": [float(x) for x in np.quantile(draws[:,j1]-draws[:,j0],[.025,.975])]}
    result["failure_decomposition"] = {
        "candidate_recall": float(frame.candidate_recall.mean()),
        "retrieval_lost_target_mass": float(1-frame.candidate_recall.mean()),
        "ranking_lost_target_mass_c": float((frame.candidate_recall-frame.c_recall).mean()),
        "all_targets_missed_by_candidates": float((frame.candidate_recall==0).mean()),
        "all_targets_missed_by_c_top20": float((frame.c_recall==0).mean()),
    }
    result["subgroups"] = {}
    for group in ("target_popularity_group","length_group","exploration_group","prior_action_group"):
        result["subgroups"][group] = []
        for value, sub in frame.groupby(group, observed=True):
            record = {"group": str(value), "n": len(sub), "candidate_recall": float(sub.candidate_recall.mean()),
                      "c_recall": float(sub.c_recall.mean()), "c_mrr": float(sub.c_mrr.mean()),
                      "repeat_recall": float(sub.repeat_recall.mean()),
                      "delta_c_repeat_recall": float((sub.c_recall-sub.repeat_recall).mean())}
            if len(sub)>=100:
                subboot = _bootstrap(sub, ["c_recall","repeat_recall"])
                d = subboot.pop("_draws")
                record["delta_ci95"] = [float(x) for x in np.quantile(d[:,0]-d[:,1],[.025,.975])]
            result["subgroups"][group].append(record)
    con = connect()
    recs = ROOT / f"data/processed/{split}/recommendations/*.parquet"
    parquet_view(con, "recommendations", recs)
    coverage = con.sql("SELECT method, count(DISTINCT aid) n_items FROM recommendations GROUP BY method ORDER BY method").df()
    result["unique_recommended_items"] = dict(zip(coverage.method, coverage.n_items.astype(int)))
    con.close()
    save_json(ROOT / f"reports/results_{split}.json", result)
    return result


def main() -> None:
    for split in ("validation", "test"):
        rank_split(split)
        summarize_split(split)


if __name__ == "__main__":
    main()
