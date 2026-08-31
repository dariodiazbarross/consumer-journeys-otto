from src.common import run_sql


def test_prefix_join_keys_are_unique(con, events):
    run_sql(con, "01_events.sql")
    run_sql(con, "02_sessions.sql")
    con.execute("SET VARIABLE period_start=0")
    con.execute("SET VARIABLE period_end=200000000")
    run_sql(con, "04_prefixes.sql")
    assert con.sql("SELECT count(*)=count(DISTINCT session) FROM prefixes").fetchone()[0]
    assert con.sql("SELECT count(*)=count(DISTINCT (session,aid)) FROM prefix_items").fetchone()[0]
    assert con.sql("SELECT count(*) FROM prefix_events WHERE ts>cutoff").fetchone()[0] == 0


def test_split_boundary_is_half_open(con):
    con.execute("CREATE TABLE raw_events AS SELECT 1 AS session, 1 AS aid, 1000 AS ts, 0::TINYINT AS action, 0::SMALLINT AS event_index")
    run_sql(con, "01_events.sql")
    con.execute("SET VARIABLE history_end=1000")
    run_sql(con, "03_item_history.sql")
    assert con.sql("SELECT count(*) FROM item_counts").fetchone()[0] == 0
