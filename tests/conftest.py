import pytest

from src.common import connect


@pytest.fixture
def con():
    connection = connect()
    yield connection
    connection.close()


@pytest.fixture
def events(con):
    # Session 1 has a cutoff tie; session 2 has no positive target.
    rows = [
        (1,10,1000,0,0),(1,11,2000,0,1),(1,10,3000,1,2),
        (1,12,4000,0,3),(1,13,5000,0,4),(1,14,5000,0,5),
        (1,99,6000,1,6),(1,98,6000,2,7),(1,97,90000000,2,8),
        (2,20,1000,0,0),(2,21,2000,0,1),(2,22,3000,0,2),
        (2,23,4000,0,3),(2,24,5000,0,4),
    ]
    con.execute("CREATE OR REPLACE TABLE raw_events(session BIGINT, aid INTEGER, ts BIGINT, action TINYINT, event_index SMALLINT)")
    con.executemany("INSERT INTO raw_events VALUES (?,?,?,?,?)", rows)
    return rows
