"""Small shared helpers; all paths resolve inside this repository."""
import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config/protocol.json").read_text())
DAY = 86_400_000


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(f"SET memory_limit='{CONFIG['duckdb_memory_limit']}'")
    con.execute(f"SET threads={CONFIG['duckdb_threads']}")
    con.execute("SET preserve_insertion_order=false")
    temp = ROOT / "data/interim/duckdb_temp"
    temp.mkdir(parents=True, exist_ok=True)
    con.execute(f"SET temp_directory='{temp.as_posix()}'")
    return con


def run_sql(con: duckdb.DuckDBPyConnection, name: str) -> None:
    con.execute((ROOT / "sql" / name).read_text(encoding="utf-8"))


def save_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False), encoding="utf-8")


def export(con: duckdb.DuckDBPyConnection, query: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"COPY ({query}) TO '{path.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)")


def parquet_view(con: duckdb.DuckDBPyConnection, name: str, path: Path) -> None:
    con.execute(f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_parquet('{path.as_posix()}')")
