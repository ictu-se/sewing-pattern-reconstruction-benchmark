from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments" / "exp01_zenodo_full_pattern_audit"


def log(message: str) -> None:
    print(time.strftime("[%Y-%m-%d %H:%M:%S]"), message, flush=True)


def run(args: list[str]) -> None:
    log("RUN " + " ".join(args))
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> int:
    EXP.mkdir(parents=True, exist_ok=True)
    log("Starting full Zenodo pattern reconstruction experiment")
    run([sys.executable, "scripts/download_zenodo_full.py"])
    run([sys.executable, "scripts/audit_zenodo_full_patterns.py"])
    log("Full experiment finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
