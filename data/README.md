# Local data contract

Large and event-level artifacts are deliberately ignored by Git.

| Path | Contents | Published? |
|---|---|---:|
| `raw/otto-recsys-v1.zip` | Authoritative versioned ZIP | No |
| `interim/events/` | Whole-session Parquet event partitions | No |
| `interim/sessions/`, `history/` | SQL intermediate aggregates | No |
| `processed/{validation,test}/` | Prefixes, candidates and evaluation rows | No |

From the repository root on Python 3.13:

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
python -m src.acquire
python -m src.ingest
python -m src.prepare --watch
python -m src.audit
python -m src.evaluate
python -m src.visualize
python -m src.reporting
python -m src.notebooks
pytest -q
```

`src.acquire` refuses to replace a recorded raw revision silently. `src.ingest`
streams the compressed JSONL without extracting 12 GB to disk, keeps sessions whole
at Parquet boundaries, and records member hashes. The SQL worker uses a 512 MB DuckDB
limit and one thread by default. The measured end-to-end resource profile is published
in `reports/data_audit.json`; compact aggregate reports, figures and executed notebooks
are versioned, but event-level derivatives are not.

Deletion of ignored data does not alter published evidence. To reproduce from scratch,
delete the ignored `data/raw`, `data/interim` and `data/processed` contents deliberately,
then run the commands in order. Do not mix source revisions.
