"""Public, streamed download of the official OTTO dataset version 1."""
import argparse
import hashlib
import json
import time
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "https://www.kaggle.com/api/v1/datasets/download/otto/recsys-dataset?datasetVersionNumber=1"


def digest(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def acquire():
    raw = ROOT / "data" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    archive = raw / "otto-recsys-v1.zip"
    if not archive.exists():
        partial = archive.with_suffix(".zip.part")
        started, total, next_report = time.perf_counter(), 0, 128*1024**2
        with urllib.request.urlopen(URL, timeout=120) as response, partial.open("wb") as output:
            while chunk := response.read(8*1024**2):
                output.write(chunk)
                total += len(chunk)
                if total >= next_report:
                    print(f"Downloaded {total/1024**3:.2f} GiB in {time.perf_counter()-started:.0f}s", flush=True)
                    next_report += 128*1024**2
        partial.replace(archive)
    with zipfile.ZipFile(archive) as zf:
        members = [{"file": info.filename, "uncompressed_bytes": info.file_size,
                    "compressed_bytes": info.compress_size, "zip_crc32": info.CRC}
                   for info in zf.infolist()]
    record = {
        "dataset": "OTTO Recommender Systems Dataset", "version": 1,
        "dataset_id": 2895394, "dataset_version_id": 4991874,
        "doi": "10.34740/KAGGLE/DSV/4991874", "download_url": URL,
        "accessed_utc": datetime.now(timezone.utc).isoformat(),
        "bytes": archive.stat().st_size, "sha256": digest(archive),
        "source_repo_commit": "f404284240ac654d0b924b2fabec0aea7b23f168",
        "members": members,
    }
    manifest = ROOT / "reports" / "source_manifest.json"
    if manifest.exists():
        frozen = json.loads(manifest.read_text(encoding="utf-8"))
        if record["sha256"] != frozen["sha256"]:
            raise ValueError("Raw archive hash changed. Review provenance before continuing.")
    else:
        manifest.write_text(json.dumps(record, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(record, indent=2), flush=True)


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    acquire()

