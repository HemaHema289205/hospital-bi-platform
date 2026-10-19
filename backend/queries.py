"""
Analytics layer: every SQL query the dashboard needs.

All date columns are stored as 'YYYY-MM-DD' text, so the same SQL runs
unchanged on SQLite and MySQL.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from backend.database import query_df, query_one, query_rows


# ------------------------------------------------------------- helpers
def date_bounds() -> dict:
    """Earliest and latest day present in the data."""
    row = query_one(
        "SELECT MIN(VISIT_DATE) AS min_date, MAX(VISIT_DATE) AS max_date FROM fact_encounters"
    ) or {}
    return {"min_date": row.get("min_date"), "max_date": row.get("max_date")}


def default_range(days: int = 30) -> tuple[str, str]:
    """The last `days` days of data (not the last `days` days of real life)."""
    b = date_bounds()
    end = datetime.strptime(b["max_date"], "%Y-%m-%d").date()
    start = end - timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


def _previous_window(start: str, end: str) -> tuple[str, str]:
    s = datetime.strptime(start, "%Y-%m-%d").date()
    e = datetime.strptime(end, "%Y-%m-%d").date()
    span = (e - s).days + 1
    return (s - timedelta(days=span)).isoformat(), (s - timedelta(days=1)).isoformat()


def _pct_change(now: float, before: float) -> float:
    if not before:
        return 0.0
    return round((now - before) / before * 100, 1)


# ----------------------------------------------------------------- KPIs
_KPI_SQL = """
SELECT
    COUNT(*)                                        AS total_visits,
    SUM(IS_ADMISSION)                               AS admissions,
    SUM(CASE WHEN IS_ADMISSION = 1 AND DISCHARGE_DATE IS NOT NULL
             THEN 1 ELSE 0 END)                     AS discharges,
    SUM(IS_EMERGENCY)                               AS emergency_cases,
    AVG(CASE WHEN IS_ADMISSION = 1 AND LENGTH_OF_STAY > 0
             THEN LENGTH_OF_STAY END)               AS avg_length_of_stay,
    AVG(WAIT_MINUTES)                               AS avg_wait_minutes,
    SUM(TOTAL_CLAIM_COST)                           AS total_revenue,
    COUNT(DISTINCT PATIENT_ID)                      AS unique_patients
FROM fact_encounters
WHERE VISIT_DATE BETWEEN :start AND :end
"""


def kpis(start: str, end: str) -> dict:
    cur = query_one(_KPI_SQL, {"start": start, "end": end}) or {}
    p_start, p_end = _previous_window(start, end)
    prev = query_one(_KPI_SQL, {"start": p_start, "end": p_end}) or {}

    def num(d: dict, k: str) -> float:
        return float(d.get(k) or 0)

    cards = [
        {"key": "total_visits",       "label": "Total Patient Visits", "format": "number"},
        {"key": "admissions",         "label": "Admissions",           "format": "number"},
        {"key": "discharges",         "label": "Discharges",           "format": "number"},
        {"key": "avg_length_of_stay", "label": "Avg. Length of Stay",  "format": "days"},
        {"key": "total_revenue",      "label": "Total Revenue",        "format": "currency"},
    ]
    out = []
    for c in cards:
        now, before = num(cur, c["key"]), num(prev, c["key"])
        out.append({
            **c,
            "value": round(now, 2) if c["format"] in ("days",) else round(now),
            "change_pct": _pct_change(now, before),
            "previous": round(before, 2),
        })

    return {
        "range": {"start": start, "end": end},
        "previous_range": {"start": p_start, "end": p_end},
        "cards": out,
        "extra": {
            "emergency_cases": int(num(cur, "emergency_cases")),
            "avg_wait_minutes": round(num(cur, "avg_wait_minutes"), 1),
            "unique_patients": int(num(cur, "unique_patients")),
        },
    }


# ------------------------------------------------------- patient flow
def patient_flow(start: str, end: str) -> list[dict]:
    rows = query_rows(
        """
        SELECT FLOW_DATE AS date, VISITS AS visits, ADMISSIONS AS admissions,
               DISCHARGES AS discharges, EMERGENCY_CASES AS emergency,
               BED_OCCUPANCY_PCT AS occupancy, AVG_WAIT_MINUTES AS wait_minutes
        FROM agg_daily_flow
        WHERE FLOW_DATE BETWEEN :start AND :end
        ORDER BY FLOW_DATE
        """,
        {"start": start, "end": end},
    )
    for r in rows:
        r["label"] = datetime.strptime(r["date"], "%Y-%m-%d").strftime("%b %d")
    return rows


def hourly_flow(start: str, end: str) -> list[dict]:
    return query_rows(
        """
        SELECT HOUR AS hour, COUNT(*) AS visits, SUM(IS_EMERGENCY) AS emergency
        FROM fact_encounters
        WHERE VISIT_DATE BETWEEN :start AND :end
        GROUP BY HOUR ORDER BY HOUR
        """,
        {"start": start, "end": end},
    )


def weekday_flow(start: str, end: str) -> list[dict]:
    rows = query_rows(
        """
        SELECT DAY_OF_WEEK AS dow, DAY_NAME AS day,
               COUNT(*) AS visits, SUM(IS_ADMISSION) AS admissions,
               AVG(WAIT_MINUTES) AS wait_minutes
        FROM fact_encounters
        WHERE VISIT_DATE BETWEEN :start AND :end
        GROUP BY DAY_OF_WEEK, DAY_NAME ORDER BY DAY_OF_WEEK
        """,
        {"start": start, "end": end},
    )
    for r in rows:
        r["wait_minutes"] = round(float(r["wait_minutes"] or 0), 1)
        r["day_short"] = str(r["day"])[:3]
    return rows


# ------------------------------------------------------- demographics
def demographics(start: str, end: str) -> dict:
    gender = query_rows(
        """
        SELECT GENDER_LABEL AS name, COUNT(*) AS value
        FROM fact_encounters
        WHERE VISIT_DATE BETWEEN :start AND :end
        GROUP BY GENDER_LABEL ORDER BY value DESC
        """,
        {"start": start, "end": end},
    )
    total = sum(g["value"] for g in gender) or 1
    for g in gender:
        g["pct"] = round(g["value"] / total * 100, 1)

    age = query_rows(
        """
        SELECT AGE_BAND AS name, COUNT(*) AS value, SUM(IS_ADMISSION) AS admissions
        FROM fact_encounters
        WHERE VISIT_DATE BETWEEN :start AND :end
        GROUP BY AGE_BAND ORDER BY AGE_BAND
        """,
        {"start": start, "end": end},
    )
    for a in age:
        a["pct"] = round(a["value"] / total * 100, 1)

    return {"total": total, "gender": gender, "age_bands": age}


# ---------------------------------------------------------- conditions
def top_conditions(start: str, end: str, limit: int = 5) -> list[dict]:
    rows = query_rows(
        """
        SELECT c.DESCRIPTION AS name, COUNT(*) AS value
        FROM fact_conditions c
        WHERE c.START BETWEEN :start AND :end
        GROUP BY c.DESCRIPTION ORDER BY value DESC
        LIMIT :limit
        """,
        {"start": start, "end": end, "limit": limit},
    )
    grand = query_one(
        "SELECT COUNT(*) AS n FROM fact_conditions WHERE START BETWEEN :start AND :end",
        {"start": start, "end": end},
    ) or {"n": 0}
    total = float(grand["n"] or 1)
    listed = 0
    for r in rows:
        r["pct"] = round(r["value"] / total * 100, 1)
        listed += r["value"]
    other = total - listed
    if other > 0:
        rows.append({"name": "Other", "value": int(other), "pct": round(other / total * 100, 1)})
    return rows


# --------------------------------------------------------- departments
def departments(start: str, end: str) -> list[dict]:
    rows = query_rows(
        """
        SELECT DEPARTMENT AS name,
               COUNT(*)            AS visits,
               SUM(IS_ADMISSION)   AS admissions,
               SUM(IS_EMERGENCY)   AS emergency,
               AVG(CASE WHEN IS_ADMISSION = 1 AND LENGTH_OF_STAY > 0
                        THEN LENGTH_OF_STAY END) AS avg_los,
               AVG(WAIT_MINUTES)   AS avg_wait,
               SUM(TOTAL_CLAIM_COST) AS revenue
        FROM fact_encounters
        WHERE VISIT_DATE BETWEEN :start AND :end
        GROUP BY DEPARTMENT ORDER BY visits DESC
        """,
        {"start": start, "end": end},
    )
    total = sum(r["visits"] for r in rows) or 1
    for r in rows:
        r["avg_los"] = round(float(r["avg_los"] or 0), 2)
        r["avg_wait"] = round(float(r["avg_wait"] or 0), 1)
        r["revenue"] = round(float(r["revenue"] or 0), 2)
        r["pct"] = round(r["visits"] / total * 100, 1)
    return rows


# ----------------------------------------------------- bed occupancy
def bed_occupancy(start: str, end: str) -> list[dict]:
    """
    Beds in use per department, AS OF the last day of the selected range.

    A bed is occupied if a patient was admitted on or before that day and
    has not been discharged yet. Bed capacity (TOTAL_BEDS in
    backend/config.py) is shared out across departments in proportion to
    how many admissions each one handles.
    """
    from backend import config

    capacity = query_rows(
        """
        SELECT DEPARTMENT AS ward, SUM(IS_ADMISSION) AS admissions
        FROM fact_encounters
        WHERE VISIT_DATE BETWEEN :start AND :end
        GROUP BY DEPARTMENT
        HAVING SUM(IS_ADMISSION) > 0
        """,
        {"start": start, "end": end},
    )
    if not capacity:
        return []

    occupied_rows = query_rows(
        """
        SELECT DEPARTMENT AS ward, COUNT(*) AS occupied
        FROM fact_encounters
        WHERE IS_ADMISSION = 1
          AND VISIT_DATE <= :end
          AND (DISCHARGE_DATE IS NULL OR DISCHARGE_DATE >= :end)
        GROUP BY DEPARTMENT
        """,
        {"end": end},
    )
    occupied = {r["ward"]: int(r["occupied"] or 0) for r in occupied_rows}

    total_adm = sum(float(r["admissions"] or 0) for r in capacity) or 1
    out = []
    for r in capacity:
        share = float(r["admissions"] or 0) / total_adm
        beds = max(8, round(config.TOTAL_BEDS * share))
        used = min(beds, occupied.get(r["ward"], 0))
        out.append({
            "ward": r["ward"],
            "beds": int(beds),
            "occupied": int(used),
            "available": int(beds - used),
            "occupancy_pct": round(used / beds * 100, 1),
        })
    return sorted(out, key=lambda x: -x["beds"])


# ------------------------------------------------------ recent visits
def recent_encounters(limit: int = 10) -> list[dict]:
    return query_rows(
        """
        SELECT ENCOUNTER_ID, PATIENT_ID, FULL_NAME, AGE, GENDER_LABEL,
               DEPARTMENT, ENCOUNTERCLASS, VISIT_DATE, STATUS,
               LENGTH_OF_STAY, WAIT_MINUTES
        FROM fact_encounters
        ORDER BY START DESC
        LIMIT :limit
        """,
        {"limit": limit},
    )


def search(term: str, limit: int = 15) -> list[dict]:
    like = f"%{term}%"
    return query_rows(
        """
        SELECT ENCOUNTER_ID, PATIENT_ID, FULL_NAME, AGE, GENDER_LABEL,
               DEPARTMENT, ENCOUNTERCLASS, VISIT_DATE, STATUS, LENGTH_OF_STAY
        FROM fact_encounters
        WHERE FULL_NAME LIKE :like OR DEPARTMENT LIKE :like
           OR DESCRIPTION LIKE :like OR REASONDESCRIPTION LIKE :like
        ORDER BY START DESC LIMIT :limit
        """,
        {"like": like, "limit": limit},
    )


# -------------------------------------------------- wait-time analysis
def wait_times(start: str, end: str) -> list[dict]:
    rows = query_rows(
        """
        SELECT ENCOUNTERCLASS AS name, AVG(WAIT_MINUTES) AS avg_wait,
               MAX(WAIT_MINUTES) AS max_wait, COUNT(*) AS visits
        FROM fact_encounters
        WHERE VISIT_DATE BETWEEN :start AND :end
        GROUP BY ENCOUNTERCLASS ORDER BY visits DESC
        """,
        {"start": start, "end": end},
    )
    pretty = {"outpatient": "OPD", "emergency": "Emergency", "inpatient": "Inpatient",
              "ambulatory": "Ambulatory", "wellness": "Wellness", "urgentcare": "Urgent Care"}
    for r in rows:
        r["avg_wait"] = round(float(r["avg_wait"] or 0), 1)
        r["label"] = pretty.get(r["name"], str(r["name"]).title())
    return rows


# ------------------------------------------------- generic SQL (reports)
SAFE_PREFIX = ("select", "with")


def run_report_sql(sql: str, limit: int = 200):
    """Read-only SQL runner used by the Reports & Queries page."""
    cleaned = sql.strip().rstrip(";")
    if not cleaned.lower().startswith(SAFE_PREFIX):
        raise ValueError("Only SELECT queries are allowed.")
    banned = (" insert ", " update ", " delete ", " drop ", " alter ", " create ",
              " attach ", " pragma ", " truncate ")
    padded = f" {cleaned.lower()} ".replace("\n", " ")
    for word in banned:
        if word in padded:
            raise ValueError(f"'{word.strip()}' is not allowed in a report query.")
    df = query_df(f"SELECT * FROM ({cleaned}) AS report_sub LIMIT {int(limit)}")
    return {"columns": list(df.columns), "rows": df.to_dict(orient="records"),
            "row_count": len(df)}
