"""
Runs the whole data pipeline in one go:

    00  generate Synthea-style sample data   (skipped if data/raw already has files)
    01  clean + feature engineering
    02  load into the database
    03  train the ML models

Usage:
    python scripts/run_pipeline.py
    python scripts/run_pipeline.py --regenerate     # rebuild the raw CSVs too
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

STEPS = [
    ("00_generate_sample_data.py", "Generate sample hospital data"),
    ("01_clean_transform.py", "Clean data + engineer features"),
    ("02_load_to_db.py", "Load into the database"),
    ("03_train_models.py", "Train the ML models"),
]


def run(script: str) -> None:
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / script)], cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(f"\n>>> {script} failed. Fix the error above and run again.\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--regenerate", action="store_true",
                    help="rebuild data/raw/*.csv even if they already exist")
    args = ap.parse_args()

    have_raw = RAW.exists() and any(RAW.glob("*.csv"))

    print("\n" + "#" * 66)
    print("#  HospitalFlow AI  -  full data pipeline")
    print("#" * 66)

    t0 = time.time()
    for script, title in STEPS:
        if script.startswith("00") and have_raw and not args.regenerate:
            print(f"\n>>> SKIP  {title} (data/raw already has CSV files)")
            print("    use --regenerate to rebuild them")
            continue
        print(f"\n>>> {title}")
        run(script)

    print("\n" + "#" * 66)
    print(f"#  PIPELINE COMPLETE in {time.time() - t0:.1f}s")
    print("#")
    print("#  Next, start the two servers in two separate terminals:")
    print("#    1)  python -m uvicorn backend.main:app --reload")
    print("#    2)  cd frontend  &&  npm run dev")
    print("#" * 66 + "\n")


if __name__ == "__main__":
    main()
