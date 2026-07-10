from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments" / "exp01_zenodo_full_pattern_audit"
ARCHIVES = ROOT / "raw" / "zenodo_3d_garments_sewing_patterns" / "archives"


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def process_alive(pid: str) -> bool:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", f"Get-Process -Id {pid} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == pid


def main() -> int:
    pid_path = EXP / "full_experiment.pid"
    pid = pid_path.read_text(encoding="utf-8").strip() if pid_path.exists() else ""
    print(f"PID: {pid or 'not started'}")
    if pid:
        print(f"Process alive: {process_alive(pid)}")

    manifest = read_csv(EXP / "zenodo_file_manifest.csv")
    status = read_csv(EXP / "download_status.csv")
    verified = {row["key"] for row in status if row.get("status") == "verified"}
    total_bytes = sum(int(row["size"]) for row in manifest if row.get("size"))
    verified_bytes = sum(int(row["size"]) for row in manifest if row["key"] in verified)
    print(f"Verified files: {len(verified)}/{len(manifest)}")
    print(f"Verified bytes: {verified_bytes:,}/{total_bytes:,}")

    for row in manifest:
        path = ARCHIVES / row["key"]
        if row["key"] in verified:
            continue
        if path.exists():
            size = path.stat().st_size
            target = int(row["size"])
            percent = 100 * size / target if target else 0
            print(f"Current/partial: {row['key']} {size:,}/{target:,} ({percent:.2f}%)")
            break

    summary_path = EXP / "summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        print(f"Audited samples in latest summary: {summary.get('total_samples')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
