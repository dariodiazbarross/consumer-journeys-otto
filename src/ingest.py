"""Stream the original ZIP into bounded, whole-session Parquet partitions."""
import hashlib
import json
import time
import zipfile
from array import array
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import orjson
import psutil
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
TYPES = {"clicks": 0, "carts": 1, "orders": 2}
SCHEMA = pa.schema([
    ("session", pa.int64()), ("aid", pa.int32()), ("ts", pa.int64()),
    ("action", pa.int8()), ("event_index", pa.int16()),
])


def parse_record(line: bytes) -> tuple[int, list[dict]]:
    """Reject invalid records; retain duplicates and timestamp ties for audit."""
    record = orjson.loads(line)
    sid, events = record["session"], record["events"]
    if not isinstance(sid, int) or sid < 0 or not events or len(events) > 32767:
        raise ValueError("Invalid session or length")
    for e in events:
        if (e["type"] not in TYPES or not isinstance(e["aid"], int)
                or e["aid"] < 0 or e["aid"] >= 2**31
                or not isinstance(e["ts"], int) or not 10**12 <= e["ts"] < 10**13):
            raise ValueError("Invalid event schema or millisecond timestamp")
    return sid, events


def ingest() -> None:
    manifest_path = ROOT / "reports/ingestion.json"
    if manifest_path.exists():
        print("Ingestion already complete; use recorded partitions.", flush=True)
        return
    started = time.perf_counter()
    audit = {"sources": {}, "partition_event_target": 1_000_000,
             "sampling": "None: all source sessions", "python": "3.13"}
    process = psutil.Process()
    with zipfile.ZipFile(ROOT / "data/raw/otto-recsys-v1.zip") as archive:
        for source in ("test", "train"):
            output = ROOT / "data/interim/events" / source
            output.mkdir(parents=True, exist_ok=True)
            if list(output.glob("*.parquet")):
                raise RuntimeError(f"Incomplete ingestion exists in {output}; inspect before rerun")
            counts = Counter()
            lengths = Counter()
            minimum, maximum = 10**15, 0
            digest = hashlib.sha256()
            buffers = [array(t) for t in ("q", "i", "q", "b", "h")]
            part = 0
            peak_rss = 0

            def flush() -> None:
                nonlocal buffers, part, peak_rss
                table = pa.Table.from_arrays(
                    [pa.array(b, type=f.type) for b, f in zip(buffers, SCHEMA)], schema=SCHEMA
                )
                pq.write_table(table, output / f"part-{part:04d}.parquet", compression="zstd")
                part += 1
                peak_rss = max(peak_rss, process.memory_info().rss)
                buffers = [array(t) for t in ("q", "i", "q", "b", "h")]
                print(f"{source}: {counts['sessions']:,} sessions; {counts['events']:,} events; "
                      f"RSS {peak_rss / 2**20:.0f} MiB; {time.perf_counter()-started:.0f}s", flush=True)

            with archive.open(f"otto-recsys-{source}.jsonl") as stream:
                for line in stream:
                    digest.update(line)
                    sid, events = parse_record(line)
                    counts["sessions"] += 1
                    counts["events"] += len(events)
                    lengths[len(events)] += 1
                    counts["starts_nonclick"] += events[0]["type"] != "clicks"
                    previous = -1
                    seen = set()
                    for index, event in enumerate(events):
                        aid, ts, kind = event["aid"], event["ts"], event["type"]
                        counts[kind] += 1
                        counts["out_of_order_events"] += ts < previous
                        counts["same_timestamp_adjacent"] += ts == previous
                        key = (aid, ts, kind)
                        counts["duplicate_event_tuples"] += key in seen
                        seen.add(key)
                        previous = ts
                        minimum, maximum = min(minimum, ts), max(maximum, ts)
                        for buffer, value in zip(buffers, (sid, aid, ts, TYPES[kind], index)):
                            buffer.append(value)
                    if len(buffers[0]) >= 1_000_000:
                        flush()
            if buffers[0]:
                flush()
            audit["sources"][source] = dict(counts) | {
                "minimum_ts": minimum, "maximum_ts": maximum,
                "minimum_utc": datetime.fromtimestamp(minimum/1000, timezone.utc).isoformat(),
                "maximum_utc": datetime.fromtimestamp(maximum/1000, timezone.utc).isoformat(),
                "length_histogram": dict(sorted(lengths.items())),
                "uncompressed_sha256": digest.hexdigest(), "partitions": part,
                "parquet_bytes": sum(p.stat().st_size for p in output.glob("*.parquet")),
                "peak_rss_bytes": peak_rss,
            }
            (ROOT / f"reports/ingestion_{source}.json").write_text(
                json.dumps(audit["sources"][source], indent=2), encoding="utf-8")
    audit["elapsed_seconds"] = time.perf_counter()-started
    manifest_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")


if __name__ == "__main__":
    ingest()
