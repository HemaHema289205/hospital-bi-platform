"""
Step 1 : Data Cleaning + Feature Engineering   (Pandas / NumPy)

Reads the raw Synthea-style CSVs from data/raw/ and produces clean,
analysis-ready tables in data/processed/.

Output (data/processed/):
    dim_patients.csv        one row per patient  (+ age, age_band)
    fact_encounters.csv     one row per visit    (+ length_of_stay, is_admission, ...)
    fact_conditions.csv     cleaned condition records
    fact_procedures.csv     cleaned procedure records
    agg_daily_flow.csv      per-day visits / admissions / discharges   <- ML input
    agg_department.csv      per-department summary

Usage:
    python scripts/01_clean_transform.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

ADMISSION_CLASSES = {"inpatient", "emergency", "urgentcare"}


def log(msg: str) -> None:
    print(f"  {msg}")


# --------------------------------------------------------------- patients
def build_patients() -> pd.DataFrame:
    print("\n[1/6] Cleaning patients ...")
    df = pd.read_csv(RAW / "patients.csv")

    # --- cleaning -------------------------------------------------------
    df = df.drop_duplicates(subset="Id")
    # Drop identifiers we never analyse (privacy + they are noise)
    df = df.drop(columns=[c for c in ("SSN", "DRIVERS", "PASSPORT", "MAIDEN") if c in df.columns])

    df["BIRTHDATE"] = pd.to_datetime(df["BIRTHDATE"], errors="coerce")
    df["DEATHDATE"] = pd.to_datetime(df["DEATHDATE"], errors="coerce")
    df = df.dropna(subset=["BIRTHDATE"])

    # --- feature engineering -------------------------------------------
    today = pd.Timestamp("today").normalize()
    end = df["DEATHDATE"].fillna(today)
    df["AGE"] = ((end - df["BIRTHDATE"]).dt.days / 365.25).round().astype(int).clip(0, 110)

    df["AGE_BAND"] = pd.cut(
        df["AGE"],
        bins=[-1, 17, 34, 49, 64, 200],
        labels=["0-17", "18-34", "35-49", "50-64", "65+"],
    ).astype(str)

    df["GENDER"] = df["GENDER"].fillna("U").str.upper().str[0]
    df["GENDER_LABEL"] = df["GENDER"].map({"M": "Male", "F": "Female"}).fillna("Other")
    df["IS_DECEASED"] = df["DEATHDATE"].notna().astype(int)
    df["FULL_NAME"] = df["LAST"].astype(str).str.strip() + ", " + df["FIRST"].astype(str).str.strip()

    keep = [
        "Id", "FULL_NAME", "FIRST", "LAST", "BIRTHDATE", "DEATHDATE", "AGE", "AGE_BAND",
        "GENDER", "GENDER_LABEL", "MARITAL", "RACE", "ETHNICITY", "CITY", "STATE", "ZIP",
        "HEALTHCARE_EXPENSES", "HEALTHCARE_COVERAGE", "IS_DECEASED",
    ]
    df = df[[c for c in keep if c in df.columns]].rename(columns={"Id": "PATIENT_ID"})

    log(f"patients        : {len(df):>6,} rows, mean age {df['AGE'].mean():.1f}")
    df.to_csv(OUT / "dim_patients.csv", index=False)
    return df


# ------------------------------------------------------------- encounters
def build_encounters(patients: pd.DataFrame) -> pd.DataFrame:
    print("\n[2/6] Cleaning encounters + engineering features ...")
    df = pd.read_csv(RAW / "encounters.csv")
    df = df.drop_duplicates(subset="Id")

    df["START"] = pd.to_datetime(df["START"], errors="coerce", utc=True).dt.tz_localize(None)
    df["STOP"] = pd.to_datetime(df["STOP"], errors="coerce", utc=True).dt.tz_localize(None)
    df = df.dropna(subset=["START"])

    # A stop time before the start time is dirty data -> treat as unknown
    bad = df["STOP"].notna() & (df["STOP"] < df["START"])
    df.loc[bad, "STOP"] = pd.NaT
    log(f"fixed {int(bad.sum()):,} rows where STOP was before START")

    df["ENCOUNTERCLASS"] = df["ENCOUNTERCLASS"].fillna("outpatient").str.lower().str.strip()

    # "Data as of" = the last day a patient walked in. A patient admitted two
    # days before that, who is booked to leave next week, is STILL IN HOSPITAL
    # today - their discharge has not happened yet, so we blank it out.
    as_of = df["START"].max().normalize() + pd.Timedelta(days=1)
    still_inside = df["STOP"].notna() & (df["STOP"] >= as_of)
    df.loc[still_inside, "STOP"] = pd.NaT
    log(f"{int(still_inside.sum()):,} patients are still admitted as of {as_of.date()}")

    # ---- derived flags --------------------------------------------------
    df["IS_ADMISSION"] = df["ENCOUNTERCLASS"].isin(ADMISSION_CLASSES).astype(int)
    df["IS_EMERGENCY"] = (df["ENCOUNTERCLASS"] == "emergency").astype(int)

    # ---- length of stay (days) -----------------------------------------
    hours = (df["STOP"] - df["START"]).dt.total_seconds() / 3600.0
    df["STAY_HOURS"] = hours.round(2)
    los = hours / 24.0
    # LOS only makes sense for admissions; outpatient visits are same-day
    df["LENGTH_OF_STAY"] = np.where(df["IS_ADMISSION"] == 1, los.round(2), 0.0)
    df["LENGTH_OF_STAY"] = df["LENGTH_OF_STAY"].clip(lower=0, upper=60)
    # Patients who have not been discharged yet have no final stay length.
    # Leaving them in would drag every average down, so they become NaN and
    # the ML model simply never sees them.
    df.loc[df["STOP"].isna() & (df["IS_ADMISSION"] == 1), "LENGTH_OF_STAY"] = np.nan

    # ---- waiting time proxy (minutes before treatment starts) ----------
    rng = np.random.default_rng(42)
    base = np.where(df["IS_EMERGENCY"] == 1, 18, np.where(df["IS_ADMISSION"] == 1, 32, 26))
    df["WAIT_MINUTES"] = (base + rng.gamma(2.0, 6.0, len(df))).round().astype(int)

    # ---- calendar features (used by the ML model) ----------------------
    df["VISIT_DATE"] = df["START"].dt.date
    df["DISCHARGE_DATE"] = df["STOP"].dt.date
    df["YEAR"] = df["START"].dt.year
    df["MONTH"] = df["START"].dt.month
    df["DAY_OF_WEEK"] = df["START"].dt.dayofweek          # 0 = Monday
    df["DAY_NAME"] = df["START"].dt.day_name()
    df["HOUR"] = df["START"].dt.hour
    df["IS_WEEKEND"] = (df["DAY_OF_WEEK"] >= 5).astype(int)

    # ---- status for the dashboard table --------------------------------
    df["STATUS"] = np.select(
        [df["IS_ADMISSION"].eq(1) & df["STOP"].isna(),
         df["IS_ADMISSION"].eq(1) & df["STOP"].notna()],
        ["Admitted", "Discharged"],
        default="Completed",
    )

    # ---- money ----------------------------------------------------------
    for col in ("BASE_ENCOUNTER_COST", "TOTAL_CLAIM_COST", "PAYER_COVERAGE"):
        df[col] = pd.to_numeric(df.get(col), errors="coerce").fillna(0.0)
    df["OUT_OF_POCKET"] = (df["TOTAL_CLAIM_COST"] - df["PAYER_COVERAGE"]).clip(lower=0).round(2)

    if "DEPARTMENT" not in df.columns:
        df["DEPARTMENT"] = "General Medicine"
    df["DEPARTMENT"] = df["DEPARTMENT"].fillna("General Medicine")

    # ---- join a few patient attributes (star-schema style) --------------
    pcols = patients[["PATIENT_ID", "FULL_NAME", "AGE", "AGE_BAND", "GENDER_LABEL"]]
    df = df.merge(pcols, left_on="PATIENT", right_on="PATIENT_ID", how="left")
    df["AGE"] = df["AGE"].fillna(df["AGE"].median()).astype(int)
    df["GENDER_LABEL"] = df["GENDER_LABEL"].fillna("Other")
    df["AGE_BAND"] = df["AGE_BAND"].fillna("35-49")
    df["FULL_NAME"] = df["FULL_NAME"].fillna("Unknown")

    keep = [
        "Id", "PATIENT", "FULL_NAME", "AGE", "AGE_BAND", "GENDER_LABEL",
        "ORGANIZATION", "DEPARTMENT", "ENCOUNTERCLASS", "DESCRIPTION",
        "REASONDESCRIPTION", "PAYER_NAME",
        "START", "STOP", "VISIT_DATE", "DISCHARGE_DATE",
        "YEAR", "MONTH", "DAY_OF_WEEK", "DAY_NAME", "HOUR", "IS_WEEKEND",
        "IS_ADMISSION", "IS_EMERGENCY", "LENGTH_OF_STAY", "STAY_HOURS",
        "WAIT_MINUTES", "STATUS",
        "BASE_ENCOUNTER_COST", "TOTAL_CLAIM_COST", "PAYER_COVERAGE", "OUT_OF_POCKET",
    ]
    df = df[[c for c in keep if c in df.columns]].rename(
        columns={"Id": "ENCOUNTER_ID", "PATIENT": "PATIENT_ID"}
    )

    log(f"encounters      : {len(df):>6,} rows  ({int(df['IS_ADMISSION'].sum()):,} admissions)")
    log(f"date range      : {df['START'].min().date()}  ->  {df['START'].max().date()}")
    df.to_csv(OUT / "fact_encounters.csv", index=False)
    return df


# ------------------------------------------------------------- conditions
def build_conditions() -> pd.DataFrame:
    print("\n[3/6] Cleaning conditions ...")
    df = pd.read_csv(RAW / "conditions.csv")
    df["START"] = pd.to_datetime(df["START"], errors="coerce")
    df["STOP"] = pd.to_datetime(df["STOP"], errors="coerce")
    df = df.dropna(subset=["START", "PATIENT"])
    df["DESCRIPTION"] = df["DESCRIPTION"].fillna("Unspecified").str.strip()
    df["IS_ACTIVE"] = df["STOP"].isna().astype(int)
    df = df.rename(columns={"PATIENT": "PATIENT_ID", "ENCOUNTER": "ENCOUNTER_ID"})
    df = df[["START", "STOP", "PATIENT_ID", "ENCOUNTER_ID", "CODE", "DESCRIPTION", "IS_ACTIVE"]]
    log(f"conditions      : {len(df):>6,} rows, {df['DESCRIPTION'].nunique()} distinct")
    df.to_csv(OUT / "fact_conditions.csv", index=False)
    return df


# ------------------------------------------------------------- procedures
def build_procedures() -> pd.DataFrame:
    print("\n[4/6] Cleaning procedures ...")
    df = pd.read_csv(RAW / "procedures.csv")
    df["START"] = pd.to_datetime(df["START"], errors="coerce", utc=True).dt.tz_localize(None)
    df = df.dropna(subset=["START", "PATIENT"])
    df["BASE_COST"] = pd.to_numeric(df["BASE_COST"], errors="coerce").fillna(0.0)
    df["DESCRIPTION"] = df["DESCRIPTION"].fillna("Unspecified").str.strip()
    df = df.rename(columns={"PATIENT": "PATIENT_ID", "ENCOUNTER": "ENCOUNTER_ID"})
    df = df[["START", "PATIENT_ID", "ENCOUNTER_ID", "CODE", "DESCRIPTION", "BASE_COST"]]
    log(f"procedures      : {len(df):>6,} rows")
    df.to_csv(OUT / "fact_procedures.csv", index=False)
    return df


# --------------------------------------------------------- daily aggregate
def build_daily_flow(enc: pd.DataFrame) -> pd.DataFrame:
    """One row per calendar day. This table is what the ML model learns from."""
    print("\n[5/6] Building daily patient-flow aggregate (ML training table) ...")

    visits = enc.groupby("VISIT_DATE").size().rename("VISITS")
    adm = enc[enc["IS_ADMISSION"] == 1].groupby("VISIT_DATE").size().rename("ADMISSIONS")
    emg = enc[enc["IS_EMERGENCY"] == 1].groupby("VISIT_DATE").size().rename("EMERGENCY_CASES")
    dis = (
        enc[enc["DISCHARGE_DATE"].notna() & (enc["IS_ADMISSION"] == 1)]
        .groupby("DISCHARGE_DATE").size().rename("DISCHARGES")
    )
    rev = enc.groupby("VISIT_DATE")["TOTAL_CLAIM_COST"].sum().round(2).rename("REVENUE")
    wait = enc.groupby("VISIT_DATE")["WAIT_MINUTES"].mean().round(1).rename("AVG_WAIT_MINUTES")
    los = (
        enc[enc["IS_ADMISSION"] == 1]
        .groupby("VISIT_DATE")["LENGTH_OF_STAY"].mean().round(2).rename("AVG_LENGTH_OF_STAY")
    )

    daily = pd.concat([visits, adm, dis, emg, rev, wait, los], axis=1)

    # The calendar runs from the first visit to the LAST VISIT. Discharge
    # dates can fall after that (a patient admitted on the last day leaves
    # later) - those trailing days have zero visits and would pollute the
    # time series, so they are cut off here.
    first_visit, last_visit = enc["VISIT_DATE"].min(), enc["VISIT_DATE"].max()
    idx = pd.date_range(first_visit, last_visit, freq="D").date
    daily = daily.reindex(idx).fillna(0)
    daily.index.name = "FLOW_DATE"
    daily = daily.reset_index()

    # The first days are a "warm-up": nobody was admitted before the window
    # opened, so bed occupancy starts near zero and climbs. Those days are
    # not representative of the hospital, so drop them.
    WARMUP_DAYS = 21
    daily = daily.iloc[WARMUP_DAYS:].reset_index(drop=True)

    daily["FLOW_DATE"] = pd.to_datetime(daily["FLOW_DATE"])
    daily["DAY_OF_WEEK"] = daily["FLOW_DATE"].dt.dayofweek
    daily["DAY_NAME"] = daily["FLOW_DATE"].dt.day_name()
    daily["MONTH"] = daily["FLOW_DATE"].dt.month
    daily["WEEK_OF_YEAR"] = daily["FLOW_DATE"].dt.isocalendar().week.astype(int)
    daily["IS_WEEKEND"] = (daily["DAY_OF_WEEK"] >= 5).astype(int)

    # occupancy proxy: how many admitted patients are still inside that day
    beds_total = 220
    occupied = []
    adm_s = enc[enc["IS_ADMISSION"] == 1][["VISIT_DATE", "DISCHARGE_DATE"]].copy()
    adm_s["VISIT_DATE"] = pd.to_datetime(adm_s["VISIT_DATE"])
    adm_s["DISCHARGE_DATE"] = pd.to_datetime(adm_s["DISCHARGE_DATE"])
    for d in daily["FLOW_DATE"]:
        inside = ((adm_s["VISIT_DATE"] <= d) &
                  (adm_s["DISCHARGE_DATE"].isna() | (adm_s["DISCHARGE_DATE"] >= d)))
        occupied.append(int(inside.sum()))
    daily["BEDS_OCCUPIED"] = occupied
    daily["BED_OCCUPANCY_PCT"] = (daily["BEDS_OCCUPIED"] / beds_total * 100).round(1).clip(upper=100)

    for c in ("VISITS", "ADMISSIONS", "DISCHARGES", "EMERGENCY_CASES"):
        daily[c] = daily[c].astype(int)

    log(f"daily flow      : {len(daily):>6,} days, avg {daily['ADMISSIONS'].mean():.1f} admissions/day")
    daily.to_csv(OUT / "agg_daily_flow.csv", index=False)
    return daily


# ---------------------------------------------------- department aggregate
def build_department(enc: pd.DataFrame) -> pd.DataFrame:
    print("\n[6/6] Building department aggregate ...")
    g = enc.groupby("DEPARTMENT").agg(
        TOTAL_VISITS=("ENCOUNTER_ID", "count"),
        ADMISSIONS=("IS_ADMISSION", "sum"),
        EMERGENCY_CASES=("IS_EMERGENCY", "sum"),
        AVG_LENGTH_OF_STAY=("LENGTH_OF_STAY", "mean"),
        AVG_WAIT_MINUTES=("WAIT_MINUTES", "mean"),
        REVENUE=("TOTAL_CLAIM_COST", "sum"),
    ).reset_index()
    g["AVG_LENGTH_OF_STAY"] = g["AVG_LENGTH_OF_STAY"].round(2)
    g["AVG_WAIT_MINUTES"] = g["AVG_WAIT_MINUTES"].round(1)
    g["REVENUE"] = g["REVENUE"].round(2)
    total = g["TOTAL_VISITS"].sum()
    g["SHARE_PCT"] = (g["TOTAL_VISITS"] / total * 100).round(1)
    g = g.sort_values("TOTAL_VISITS", ascending=False).reset_index(drop=True)
    log(f"departments     : {len(g):>6,} rows")
    g.to_csv(OUT / "agg_department.csv", index=False)
    return g


def main() -> None:
    print("=" * 66)
    print("  STEP 1 : DATA CLEANING + FEATURE ENGINEERING")
    print("=" * 66)

    missing = [f for f in ("patients.csv", "encounters.csv", "conditions.csv", "procedures.csv")
               if not (RAW / f).exists()]
    if missing:
        raise SystemExit(
            f"\nERROR: missing raw files {missing} in {RAW}\n"
            "Run first:  python scripts/00_generate_sample_data.py\n"
        )

    patients = build_patients()
    enc = build_encounters(patients)
    build_conditions()
    build_procedures()
    build_daily_flow(enc)
    build_department(enc)

    print("\n" + "=" * 66)
    print(f"  DONE. Clean tables written to  {OUT}")
    print("  Next:  python scripts/02_load_to_db.py")
    print("=" * 66)


if __name__ == "__main__":
    main()
