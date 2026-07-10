from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "zenodo_3d_garments_sewing_patterns"
ARCHIVES = RAW / "archives"
EXP = ROOT / "experiments" / "exp01_zenodo_full_pattern_audit"
RECORD_URL = "https://zenodo.org/api/records/5267549"
SHARED_CANDIDATES: list[Path] = []


def log(message: str) -> None:
    print(time.strftime("[%Y-%m-%d %H:%M:%S]"), message, flush=True)


def md5(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_manifest() -> list[dict]:
    with urllib.request.urlopen(RECORD_URL, timeout=120) as response:
        data = json.load(response)
    rows = []
    for item in data["files"]:
        checksum = item.get("checksum", "")
        rows.append(
            {
                "key": item["key"],
                "size": int(item["size"]),
                "md5": checksum.split(":", 1)[1] if checksum.startswith("md5:") else checksum,
                "url": item["links"]["self"],
            }
        )
    rows.sort(key=lambda row: (row["size"], row["key"]))
    EXP.mkdir(parents=True, exist_ok=True)
    (EXP / "zenodo_record_manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    with (EXP / "zenodo_file_manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["key", "size", "md5", "url"])
        writer.writeheader()
        writer.writerows(rows)
    return rows


def try_link_existing(key: str, expected_md5: str, out_path: Path) -> bool:
    if out_path.exists():
        return False
    for directory in SHARED_CANDIDATES:
        candidate = directory / key
        if not candidate.exists():
            continue
        log(f"Found existing candidate for {key}: {candidate}")
        if md5(candidate) != expected_md5:
            log(f"Existing candidate md5 mismatch, ignoring: {candidate}")
            continue
        try:
            os.link(candidate, out_path)
            log(f"Hardlinked verified existing archive: {out_path}")
        except OSError:
            shutil.copy2(candidate, out_path)
            log(f"Copied verified existing archive: {out_path}")
        return True
    return False


def curl_download(url: str, out_path: Path) -> None:
    cmd = [
        "curl.exe",
        "-L",
        "-C",
        "-",
        "--retry",
        "30",
        "--retry-delay",
        "20",
        "--retry-all-errors",
        "--connect-timeout",
        "60",
        "--output",
        str(out_path),
        url,
    ]
    subprocess.run(cmd, check=True)


def write_status(rows: list[dict]) -> None:
    with (EXP / "download_status.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["key", "size", "md5", "url", "path", "status", "actual_md5"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only-manifest", action="store_true")
    parser.add_argument("--max-files", type=int, default=0, help="Debug limit. 0 means all files.")
    args = parser.parse_args()

    ARCHIVES.mkdir(parents=True, exist_ok=True)
    rows = fetch_manifest()
    if args.max_files:
        rows = rows[: args.max_files]
    log(f"Zenodo files in manifest: {len(rows)}")
    log(f"Total compressed bytes: {sum(row['size'] for row in rows):,}")
    if args.only_manifest:
        return 0

    status_rows = []
    for index, row in enumerate(rows, start=1):
        key = row["key"]
        out_path = ARCHIVES / key
        expected_md5 = row["md5"]
        log(f"[{index}/{len(rows)}] {key}")
        try_link_existing(key, expected_md5, out_path)
        if out_path.exists() and out_path.stat().st_size == row["size"]:
            actual = md5(out_path)
            if actual == expected_md5:
                log(f"Verified existing archive: {key}")
                status_rows.append({**row, "path": str(out_path), "status": "verified"})
                write_status(status_rows)
                continue
            log(f"Existing archive md5 mismatch, redownloading: {key}")
        curl_download(row["url"], out_path)
        actual = md5(out_path)
        if actual != expected_md5:
            status_rows.append({**row, "path": str(out_path), "status": "md5_failed", "actual_md5": actual})
            write_status(status_rows)
            raise RuntimeError(f"MD5 mismatch for {key}: expected {expected_md5}, got {actual}")
        status_rows.append({**row, "path": str(out_path), "status": "verified"})
        write_status(status_rows)
        log(f"Verified downloaded archive: {key}")

    log("All requested Zenodo archives verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
