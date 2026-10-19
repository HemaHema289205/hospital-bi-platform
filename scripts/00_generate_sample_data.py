"""
Step 0 : Generate Synthea-style synthetic hospital data.

Why this exists
---------------
The project uses the Synthea synthetic healthcare dataset. Running the real
Synthea generator needs Java + a few GB download. This script produces CSV
files with the SAME column names and structure that Synthea exports, so the
whole pipeline works offline. If you later download real Synthea CSVs, just
drop them into data/raw/ and skip this step - nothing else changes.

Output (data/raw/):
    patients.csv, encounters.csv, conditions.csv,
    organizations.csv, procedures.csv

Usage:
    python scripts/00_generate_sample_data.py
    python scripts/00_generate_sample_data.py --patients 3000 --years 3
"""
from __future__ import annotations

import argparse
import csv
import math
import random
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

# ---------------------------------------------------------------- reference data
FIRST_NAMES = [
    "Aarav", "Diya", "Rohan", "Ananya", "Vikram", "Meera", "Arjun", "Kavya",
    "Nikhil", "Sneha", "Rahul", "Pooja", "Karthik", "Lakshmi", "Suresh",
    "Priya", "Manoj", "Divya", "Ravi", "Anjali", "James", "Mary", "Robert",
    "Linda", "Michael", "Patricia", "David", "Jennifer", "William", "Susan",
]
LAST_NAMES = [
    "Reddy", "Sharma", "Patel", "Nair", "Rao", "Gupta", "Iyer", "Kumar",
    "Chowdary", "Verma", "Smith", "Johnson", "Williams", "Brown", "Jones",
    "Garcia", "Miller", "Davis", "Wilson", "Anderson",
]
CITIES = [
    ("Visakhapatnam", "AP", "530001"), ("Vijayawada", "AP", "520001"),
    ("Hyderabad", "TG", "500001"), ("Chennai", "TN", "600001"),
    ("Bengaluru", "KA", "560001"), ("Kakinada", "AP", "533001"),
    ("Rajahmundry", "AP", "533101"), ("Guntur", "AP", "522001"),
]
RACES = ["white", "black", "asian", "native", "other"]
ETHNICITIES = ["hispanic", "nonhispanic"]

# Synthea encounter classes. Weight them so "ambulatory" dominates, like real data.
ENCOUNTER_CLASSES = [
    ("ambulatory", 0.42), ("outpatient", 0.18), ("wellness", 0.12),
    ("emergency", 0.14), ("inpatient", 0.09), ("urgentcare", 0.05),
]

# (SNOMED-ish code, description) pairs per encounter class
ENCOUNTER_TYPES = {
    "ambulatory":  [("185349003", "Encounter for check up"),
                    ("162673000", "General examination of patient")],
    "outpatient":  [("183452005", "Outpatient follow-up visit"),
                    ("308335008", "Patient encounter procedure")],
    "wellness":    [("410620009", "Well child visit"),
                    ("162673000", "General examination of patient")],
    "emergency":   [("50849002", "Emergency room admission"),
                    ("183478001", "Emergency hospital admission for trauma")],
    "inpatient":   [("32485007", "Hospital admission"),
                    ("305351004", "Admission to intensive care unit"),
                    ("183495009", "Non-urgent hospital admission")],
    "urgentcare":  [("702927004", "Urgent care clinic visit")],
}

# (code, description, typical_los_days, seasonal_peak_month, severity 1-5)
CONDITIONS = [
    ("195967001", "Asthma",                       3.0, 7,  2),
    ("44054006",  "Diabetes",                     4.5, 0,  3),
    ("38341003",  "Hypertension",                 3.5, 0,  3),
    ("233604007", "Pneumonia",                    6.0, 1,  4),
    ("40055000",  "Chronic sinusitis",            1.5, 11, 1),
    ("22298006",  "Myocardial infarction",        8.5, 1,  5),
    ("230690007", "Stroke",                       9.5, 1,  5),
    ("73430006",  "Sleep apnea",                  2.0, 0,  2),
    ("162864005", "Body mass index 30+ obesity",  2.5, 0,  2),
    ("431855005", "Chronic kidney disease",        7.0, 0,  4),
    ("840539006", "COVID-19",                     5.5, 12, 4),
    ("65363002",  "Otitis media",                 1.5, 8,  1),
    ("284551006", "Laceration of foot",           1.0, 5,  1),
    ("125605004", "Fracture of bone",             4.0, 6,  3),
    ("271737000", "Anemia",                       3.0, 0,  2),
]

PROCEDURES = [
    ("430193006", "Medication reconciliation", 120.0),
    ("710824005", "Assessment of health and social care needs", 180.0),
    ("117015009", "Throat culture", 95.0),
    ("399208008", "Plain chest X-ray", 450.0),
    ("433112001", "Transthoracic echocardiography", 1200.0),
    ("18286008",  "Catheter ablation of tissue of heart", 8500.0),
    ("65200003",  "Insertion of intrauterine device", 650.0),
    ("287664005", "Electrocardiographic procedure", 300.0),
    ("73761001",  "Colonoscopy", 2200.0),
    ("76601001",  "Intramuscular injection", 75.0),
]

DEPARTMENTS = [
    "Emergency", "General Medicine", "Cardiology", "Orthopaedics",
    "Pulmonology", "Nephrology", "Paediatrics", "ICU",
]

PAYERS = [
    ("7caa7254-5050-3b5e-9eae-bd5ea30e809c", "Medicare"),
    ("4d71f845-a6a9-3c39-b2b6-5d2b9d1b0f8c", "Private Insurance"),
    ("b1c428d6-4f94-31b1-aebe-d3c2e9e96b7f", "Self Pay"),
    ("d47b3510-2895-3b70-9897-342d681c769d", "Government Scheme"),
]


def _iso(dt: datetime) -> str:
    """Synthea timestamp format."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _seasonal_multiplier(d: date, peak_month: int) -> float:
    """Smooth yearly cycle. peak_month == 0 means no seasonality."""
    if peak_month == 0:
        return 1.0
    month = ((peak_month - 1) % 12) + 1
    phase = (d.month - month) / 12.0 * 2 * math.pi
    return 1.0 + 0.45 * math.cos(phase)


def _weekday_multiplier(d: date) -> float:
    """Hospitals are busier on weekdays; Mondays worst."""
    return [1.25, 1.10, 1.05, 1.02, 1.08, 0.72, 0.62][d.weekday()]


def generate(n_patients: int, years: int, seed: int) -> None:
    random.seed(seed)
    RAW.mkdir(parents=True, exist_ok=True)

    end_date = date.today()
    start_date = end_date - timedelta(days=365 * years)
    total_days = (end_date - start_date).days

    # ------------------------------------------------------------ organizations
    orgs = []
    for i, (city, state, zipc) in enumerate(CITIES):
        orgs.append({
            "Id": str(uuid.uuid4()),
            "NAME": f"{city} {'General Hospital' if i % 2 == 0 else 'Medical Centre'}",
            "ADDRESS": f"{random.randint(1, 400)} Hospital Road",
            "CITY": city, "STATE": state, "ZIP": zipc,
            "LAT": round(random.uniform(12.0, 19.0), 6),
            "LON": round(random.uniform(77.0, 84.0), 6),
            "PHONE": f"5{random.randint(10, 99)}-555-{random.randint(1000, 9999)}",
            "REVENUE": 0.0,
            "UTILIZATION": 0,
        })

    with (RAW / "organizations.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(orgs[0].keys()))
        w.writeheader()
        w.writerows(orgs)

    # ----------------------------------------------------------------- patients
    patients = []
    for _ in range(n_patients):
        city, state, zipc = random.choice(CITIES)
        # Age distribution skewed towards adults, with a paediatric tail.
        age = int(min(95, max(0, random.gauss(45, 22))))
        birth = end_date - timedelta(days=age * 365 + random.randint(0, 364))
        # ~3% mortality in the window
        death = ""
        if random.random() < 0.03 and age > 60:
            death = str(end_date - timedelta(days=random.randint(0, total_days)))
        patients.append({
            "Id": str(uuid.uuid4()),
            "BIRTHDATE": str(birth),
            "DEATHDATE": death,
            "SSN": f"999-{random.randint(10,99)}-{random.randint(1000,9999)}",
            "DRIVERS": "", "PASSPORT": "", "PREFIX": "",
            "FIRST": random.choice(FIRST_NAMES),
            "LAST": random.choice(LAST_NAMES),
            "SUFFIX": "", "MAIDEN": "",
            "MARITAL": random.choice(["M", "S", ""]),
            "RACE": random.choice(RACES),
            "ETHNICITY": random.choice(ETHNICITIES),
            "GENDER": random.choice(["M", "F"]),
            "BIRTHPLACE": city,
            "ADDRESS": f"{random.randint(1, 999)} {random.choice(LAST_NAMES)} Street",
            "CITY": city, "STATE": state, "COUNTY": f"{city} District",
            "ZIP": zipc,
            "LAT": round(random.uniform(12.0, 19.0), 6),
            "LON": round(random.uniform(77.0, 84.0), 6),
            "HEALTHCARE_EXPENSES": 0.0,
            "HEALTHCARE_COVERAGE": 0.0,
        })

    # -------------------------------------------- encounters / conditions / procs
    encounters, conditions, procedures = [], [], []
    class_names = [c for c, _ in ENCOUNTER_CLASSES]
    class_weights = [w for _, w in ENCOUNTER_CLASSES]

    # Base visits per day grows slightly year over year (capacity trend).
    base_per_day = max(4.0, n_patients / 120.0)

    for day_offset in range(total_days):
        d = start_date + timedelta(days=day_offset)
        growth = 1.0 + 0.12 * (day_offset / max(1, total_days))
        flu_season = _seasonal_multiplier(d, 1)          # winter respiratory peak
        expected = base_per_day * growth * _weekday_multiplier(d) * (0.85 + 0.3 * flu_season)
        n_today = max(0, int(random.gauss(expected, expected * 0.22)))

        for _ in range(n_today):
            patient = random.choice(patients)
            # Skip encounters after death / before birth
            if patient["DEATHDATE"] and str(d) > patient["DEATHDATE"]:
                continue
            if str(d) < patient["BIRTHDATE"]:
                continue

            enc_class = random.choices(class_names, weights=class_weights, k=1)[0]
            code, desc = random.choice(ENCOUNTER_TYPES[enc_class])
            org = random.choice(orgs)
            payer_id, payer_name = random.choice(PAYERS)

            start_hour = random.choices(
                range(24),
                weights=[1, 1, 1, 1, 1, 2, 4, 6, 9, 11, 11, 10,
                         9, 9, 9, 8, 7, 6, 5, 4, 3, 2, 2, 1],
                k=1,
            )[0]
            start_dt = datetime(d.year, d.month, d.day, start_hour,
                                random.choice([0, 15, 30, 45]))

            # Pick a condition; weight seasonal ones in their peak month.
            cond_pool = []
            for c in CONDITIONS:
                weight = _seasonal_multiplier(d, c[3])
                cond_pool.append(weight if enc_class in ("inpatient", "emergency") else 1.0)
            cond = random.choices(CONDITIONS, weights=cond_pool, k=1)[0]
            cond_code, cond_desc, typ_los, _peak, severity = cond

            # Length of stay only meaningful for inpatient/emergency admissions.
            patient_age = (d - date.fromisoformat(patient["BIRTHDATE"])).days / 365.25
            if enc_class in ("inpatient", "emergency"):
                age_factor = 1.0 + max(0.0, (patient_age - 50) / 100.0)
                los_days = max(0.5, random.gauss(typ_los * age_factor, typ_los * 0.3))
                stop_dt = start_dt + timedelta(days=los_days)
            else:
                stop_dt = start_dt + timedelta(minutes=random.choice([15, 20, 30, 45, 60]))

            base_cost = {
                "ambulatory": 125.0, "outpatient": 150.0, "wellness": 110.0,
                "emergency": 1400.0, "inpatient": 2800.0, "urgentcare": 300.0,
            }[enc_class]
            base_cost *= 1.0 + 0.15 * severity
            enc_id = str(uuid.uuid4())

            # Procedures attached to this encounter
            total_claim = base_cost
            for _ in range(random.randint(0, 3 if enc_class in ("inpatient", "emergency") else 2)):
                p_code, p_desc, p_cost = random.choice(PROCEDURES)
                p_cost = round(p_cost * random.uniform(0.85, 1.2), 2)
                total_claim += p_cost
                procedures.append({
                    "START": _iso(start_dt + timedelta(hours=random.randint(0, 6))),
                    "STOP": _iso(stop_dt),
                    "PATIENT": patient["Id"], "ENCOUNTER": enc_id,
                    "CODE": p_code, "DESCRIPTION": p_desc,
                    "BASE_COST": p_cost,
                    "REASONCODE": cond_code, "REASONDESCRIPTION": cond_desc,
                })

            encounters.append({
                "Id": enc_id,
                "START": _iso(start_dt), "STOP": _iso(stop_dt),
                "PATIENT": patient["Id"],
                "ORGANIZATION": org["Id"],
                "PROVIDER": str(uuid.uuid4()),
                "PAYER": payer_id,
                "ENCOUNTERCLASS": enc_class,
                "CODE": code, "DESCRIPTION": desc,
                "BASE_ENCOUNTER_COST": round(base_cost, 2),
                "TOTAL_CLAIM_COST": round(total_claim, 2),
                "PAYER_COVERAGE": round(total_claim * random.uniform(0.0, 0.85), 2),
                "REASONCODE": cond_code,
                "REASONDESCRIPTION": cond_desc,
                # Extra columns (not in Synthea) that make the BI layer richer.
                "DEPARTMENT": random.choice(DEPARTMENTS) if enc_class != "emergency" else "Emergency",
                "PAYER_NAME": payer_name,
            })

            if random.random() < 0.65:
                conditions.append({
                    "START": str(d),
                    "STOP": str(stop_dt.date()) if random.random() < 0.4 else "",
                    "PATIENT": patient["Id"], "ENCOUNTER": enc_id,
                    "CODE": cond_code, "DESCRIPTION": cond_desc,
                })

            org["REVENUE"] = round(org["REVENUE"] + total_claim, 2)
            org["UTILIZATION"] += 1
            patient["HEALTHCARE_EXPENSES"] = round(
                patient["HEALTHCARE_EXPENSES"] + total_claim, 2)

    # --------------------------------------------------------------- write files
    def dump(name: str, rows: list[dict]) -> None:
        if not rows:
            return
        with (RAW / name).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"  {name:<20} {len(rows):>8,} rows")

    print(f"Writing Synthea-style CSVs to {RAW}")
    dump("patients.csv", patients)
    dump("encounters.csv", encounters)
    dump("conditions.csv", conditions)
    dump("procedures.csv", procedures)
    dump("organizations.csv", orgs)          # rewrite with revenue filled in
    print(f"\nDone. Date range: {start_date} -> {end_date}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate Synthea-style hospital data")
    ap.add_argument("--patients", type=int, default=12000)
    ap.add_argument("--years", type=int, default=2)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    generate(a.patients, a.years, a.seed)
