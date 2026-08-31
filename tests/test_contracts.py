import json

import numpy as np
import pytest

from src.acquire import URL
from src.common import ROOT, run_sql
from src.ingest import parse_record


def test_event_parsing_and_action_contract():
    session, events = parse_record(b'{"session":7,"events":[{"aid":4,"ts":1661724000000,"type":"carts"}]}')
    assert session == 7 and events[0]["type"] == "carts"
    with pytest.raises(ValueError):
        parse_record(b'{"session":7,"events":[{"aid":4,"ts":42,"type":"buy"}]}')
    assert "datasetVersionNumber=1" in URL


def _build_prefix(con, events):
    run_sql(con, "01_events.sql")
    run_sql(con, "02_sessions.sql")
    con.execute("SET VARIABLE period_start=0")
    con.execute("SET VARIABLE period_end=200000000")
    run_sql(con, "04_prefixes.sql")
    return con.sql("SELECT * FROM prefixes ORDER BY session").df(), con.sql("SELECT * FROM prefix_items ORDER BY session,aid").df()


def test_cutoff_ties_target_set_and_horizon(con, events):
    prefixes, items = _build_prefix(con, events)
    first = prefixes.iloc[0]
    assert first.cutoff == 5000 and first.prefix_length == 6
    assert list(first.targets) == [98,99] and first.target_count == 2
    assert 97 not in first.targets
    assert set(items.query("session==1").aid) == {10,11,12,13,14}


def test_future_mutation_cannot_change_prefix_features(con, events):
    before, items_before = _build_prefix(con, events)
    con.execute("UPDATE raw_events SET aid=123456 WHERE session=1 AND ts=6000")
    after, items_after = _build_prefix(con, events)
    assert before.loc[0,"targets"].tolist() != after.loc[0,"targets"].tolist()
    assert items_before.equals(items_after)


def test_temporal_history_filter(con, events):
    run_sql(con, "01_events.sql")
    con.execute("SET VARIABLE history_end=5000")
    run_sql(con, "03_item_history.sql")
    assert 13 not in set(con.sql("SELECT aid FROM item_counts").fetchnumpy()["aid"])


def test_target_never_enters_candidates(con):
    candidate_sql = "\n".join(
        line for line in (ROOT / "sql/06_candidates.sql").read_text().lower().splitlines()
        if not line.strip().startswith("--")
    )
    assert "target" not in candidate_sql
    assert "batch_prefixes" not in candidate_sql


def test_metric_math_and_deterministic_ties(con):
    con.execute("CREATE TABLE batch_prefixes AS SELECT 1 AS session, [4,5] AS targets, 2 AS target_count")
    con.execute("CREATE TABLE ranks AS SELECT * FROM (VALUES (1,4,3,3,3,3,3,3),(1,5,30,30,30,30,30,30)) t(session,aid,global_rank,recent_rank,repeat_rank,r_rank,ra_rank,c_rank)")
    run_sql(con, "07_evaluation.sql")
    row = con.sql("SELECT global_recall,global_mrr FROM evaluated").fetchone()
    assert row == (0.5, pytest.approx(1/3))
    # Item ID is explicitly the final tie break in every ranking rule.
    sql = (ROOT / "sql/06_candidates.sql").read_text()
    assert sql.count("aid) AS") >= 6


def test_config_and_seed_are_frozen():
    config = json.loads((ROOT / "config/protocol.json").read_text())
    assert config["seed"] == 20260831 and config["recommendation_count"] == 20
    a = np.random.default_rng(config["seed"]).integers(100, size=5)
    b = np.random.default_rng(config["seed"]).integers(100, size=5)
    assert np.array_equal(a,b)
