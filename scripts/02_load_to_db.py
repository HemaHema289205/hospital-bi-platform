"""
Step 2 : Load the clean tables into the database  (Database Layer)

Reads data/processed/*.csv and writes them into SQLite (default) or MySQL,
depending on DB_TYPE in your .env file.

Usage:
    python scripts/02_load_to_db.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend import config                      # noqa: E402
from backend.database import get_engine          # noqa: E402

PROC = ROOT / "data" / "processed"

# (table, csv file, date-only columns, full-timestamp columns)
# Dates are stored as plain "YYYY-MM-DD" / "YYYY-MM-DD HH:MM:SS" strings so
# that the exact same SQL runs unchanged on both SQLite and MySQL.
TABLES = [
    ("dim_patients",    "dim_patients.csv",    ["BIRTHDATE", "DEATHDATE"],              []),
    ("fact_encounters", "fact_encounters.csv", ["VISIT_DATE", "DISCHARGE_DATE"],        ["START", "STOP"]),
    ("fact_conditions", "fact_conditions.csv", ["START", "STOP"],                       []),
    ("fact_procedures", "fact_procedures.csv", [],                                      ["START"]),
    ("agg_daily_flow",  "agg_daily_flow.csv",  ["FLOW_DATE"],                           []),
    ("agg_department",  "agg_department.csv",  [],                                      []),
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_enc_date  ON fact_encounters (VISIT_DATE)",
    "CREATE INDEX IF NOT EXISTS idx_enc_dept  ON fact_encounters (DEPARTMENT)",
    "CREATE INDEX IF NOT EXISTS idx_enc_class ON fact_encounters (ENCOUNTERCLASS)",
    "CREATE INDEX IF NOT EXISTS idx_enc_adm   ON fact_encounters (IS_ADMISSION)",
    "CREATE INDEX IF NOT EXISTS idx_cond_desc ON fact_conditions (DESCRIPTION)",
]


def main() -> None:
    print("=" * 66)
    print("  STEP 2 : LOAD INTO DATABASE")
    print("=" * 66)

    if not PROC.exists() or not any(PROC.glob("*.csv")):
        raise SystemExit(
            "\nERROR: no processed files found.\n"
            "Run first:  python scripts/01_clean_transform.py\n"
        )

    engine = get_engine()
    target = (f"MySQL  {config.MYSQL_USER}@{config.MYSQL_HOST}:{config.MYSQL_PORT}/{config.MYSQL_DB}"
              if config.DB_TYPE == "mysql" else f"SQLite  {config.SQLITE_PATH}")
    print(f"\n  Target : {target}\n")

    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
    except Exception as exc:                       # noqa: BLE001
        raise SystemExit(
            f"\nERROR: could not connect to the database.\n  {exc}\n\n"
            "Tip: keep DB_TYPE=sqlite in .env - it needs no server at all.\n"
        )

    from backend.database import table_exists

    for table, filename, date_cols, ts_cols in TABLES:
        path = PROC / filename
        if not path.exists():
            print(f"  ! skipping {table} ({filename} not found)")
            continue

        df = pd.read_csv(path)
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
        for col in ts_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
        df = df.where(pd.notna(df), None)

        # If the table already exists (because you ran sql/schema.sql on
        # MySQL) keep that schema and just refill it. Otherwise create it.
        if table_exists(table):
            with engine.begin() as conn:
                conn.execute(text(f"DELETE FROM {table}"))
            mode = "append"
        else:
            mode = "replace"

        df.to_sql(table, engine, if_exists=mode, index=False, chunksize=1000)
        print(f"  {table:<18} {len(df):>7,} rows loaded  ({mode})")

    if config.DB_TYPE != "mysql":
        with engine.begin() as conn:
            for stmt in INDEXES:
                conn.execute(text(stmt))
        print("\n  indexes created")

    print("\n" + "=" * 66)
    print("  DONE. Database is ready.")
    print("  Next:  python scripts/03_train_models.py")
    print("=" * 66)


if __name__ == "__main__":
    main()
