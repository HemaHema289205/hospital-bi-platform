"""
ML Layer service: loads the trained .pkl models and answers prediction
requests coming from the API.
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd

# scikit-learn is imported eagerly on purpose. Importing it lazily inside a
# request handler meant two concurrent requests could start importing the same
# sub-module from different threads, which Python rejects with an import
# DeadlockError. Importing here happens once, on a single thread, at startup.
import sklearn.ensemble          # noqa: F401
import sklearn.linear_model      # noqa: F401
import sklearn.pipeline          # noqa: F401
import sklearn.preprocessing     # noqa: F401

from backend import config
from backend.database import query_one

ADM_PATH = config.MODELS_DIR / "admission_forecast.pkl"
LOS_PATH = config.MODELS_DIR / "los_model.pkl"


class ModelNotTrained(RuntimeError):
    pass


# Uvicorn serves requests from a thread pool, so two requests can ask for a
# model at the same moment. The lock makes sure a model is unpickled once.
_load_lock = threading.Lock()


@lru_cache(maxsize=1)
def _load_admission():
    if not ADM_PATH.exists():
        raise ModelNotTrained("Run:  python scripts/03_train_models.py")
    with _load_lock:
        return joblib.load(ADM_PATH)


@lru_cache(maxsize=1)
def _load_los():
    if not LOS_PATH.exists():
        raise ModelNotTrained("Run:  python scripts/03_train_models.py")
    with _load_lock:
        return joblib.load(LOS_PATH)


def models_ready() -> bool:
    return ADM_PATH.exists() and LOS_PATH.exists()


# ------------------------------------------------- admission forecasting
def forecast_admissions(days: int = 7) -> dict:
    """
    Predict admissions for the next `days` days.

    It is a recursive forecast: day 1 is predicted from real history, then
    that prediction is appended to the history and day 2 is predicted from
    it, and so on.
    """
    bundle = _load_admission()
    model, features = bundle["model"], bundle["features"]

    hist = pd.DataFrame(bundle["history"])
    hist["FLOW_DATE"] = pd.to_datetime(hist["FLOW_DATE"])
    hist = hist.sort_values("FLOW_DATE").reset_index(drop=True)

    series = hist["ADMISSIONS"].astype(float).tolist()
    last_day = hist["FLOW_DATE"].iloc[-1]

    out = []
    for step in range(1, days + 1):
        d = last_day + timedelta(days=step)
        row = {
            "DAY_OF_WEEK": d.dayofweek,
            "MONTH": d.month,
            "IS_WEEKEND": int(d.dayofweek >= 5),
            "WEEK_OF_YEAR": int(d.isocalendar().week),
            "LAG_1": series[-1],
            "LAG_2": series[-2],
            "LAG_7": series[-7],
            "LAG_14": series[-14],
            "ROLL_7": float(np.mean(series[-7:])),
            "ROLL_14": float(np.mean(series[-14:])),
            "ROLL_30": float(np.mean(series[-30:])),
        }
        pred = float(model.predict(pd.DataFrame([row])[features])[0])
        pred = max(0.0, pred)
        series.append(pred)

        ci = bundle["metrics"].get("rmse", 0) * 1.0
        out.append({
            "date": d.strftime("%Y-%m-%d"),
            "label": d.strftime("%b %d"),
            "day": d.strftime("%a"),
            "predicted": round(pred),
            "lower": max(0, round(pred - ci)),
            "upper": round(pred + ci),
        })

    recent = hist.tail(21)
    history = [
        {"date": r.FLOW_DATE.strftime("%Y-%m-%d"),
         "label": r.FLOW_DATE.strftime("%b %d"),
         "actual": int(r.ADMISSIONS)}
        for r in recent.itertuples()
    ]

    tomorrow = out[0]
    avg_recent = float(hist["ADMISSIONS"].tail(30).mean())
    return {
        "model": bundle["metrics"].get("model", "model"),
        "metrics": bundle["metrics"],
        "history": history,
        "forecast": out,
        "headline": {
            "next_day": tomorrow["predicted"],
            "confidence": f"+/- {round(bundle['metrics'].get('rmse', 0))}",
            "vs_recent_avg_pct": round((tomorrow["predicted"] - avg_recent) / max(avg_recent, 1) * 100, 1),
            "recent_avg": round(avg_recent, 1),
        },
    }


# ----------------------------------------------------- length of stay
def los_options() -> dict:
    return _load_los()["options"]


@lru_cache(maxsize=16)
def _op_consult_minutes(department: str) -> dict:
    """Average / shortest / longest outpatient consultation, in minutes."""
    row = query_one(
        """
        SELECT AVG(STAY_HOURS) * 60 AS avg, MIN(STAY_HOURS) * 60 AS min,
               MAX(STAY_HOURS) * 60 AS max
        FROM fact_encounters
        WHERE ENCOUNTERCLASS = 'outpatient' AND DEPARTMENT = :dept
        """,
        {"dept": department},
    ) or {}
    if not row.get("avg"):
        return {"avg": 34.0, "min": 15.0, "max": 60.0}
    return {k: float(row[k]) for k in ("avg", "min", "max")}


def predict_los(
    age: int,
    gender: str = "Male",
    department: str = "General Medicine",
    encounter_class: str = "inpatient",
    wait_minutes: int = 30,
    is_emergency: int | None = None,
    when: str | None = None,
) -> dict:
    bundle = _load_los()
    model = bundle["model"]

    # An outpatient (OP) visit never takes a bed, so there is no stay in days
    # to predict. Instead we estimate the hours spent in hospital: the waiting
    # time entered plus the average consultation time for that department.
    if encounter_class == "outpatient":
        consult = _op_consult_minutes(department)
        hours = (wait_minutes + consult["avg"]) / 60
        return {
            "predicted_days": 0.0,
            "predicted_hours": round(hours, 1),
            "range_low": 0.0,
            "range_high": 0.0,
            "hours_low": round((wait_minutes + consult["min"]) / 60, 1),
            "hours_high": round((wait_minutes + consult["max"]) / 60, 1),
            "risk_level": "Low",
            "recommendation": (
                f"Outpatient (OP) visit - about {wait_minutes} min waiting + "
                f"{consult['avg']:.0f} min with the doctor. The patient goes home "
                "the same day and no bed is needed."
            ),
            "model": "Rule: outpatients are not admitted",
            "model_mae": 0.0,
            "input": {"AGE": age, "GENDER_LABEL": gender, "DEPARTMENT": department,
                      "ENCOUNTERCLASS": encounter_class, "WAIT_MINUTES": wait_minutes},
        }

    dt = datetime.strptime(when, "%Y-%m-%d") if when else datetime.now()
    if is_emergency is None:
        is_emergency = int(encounter_class == "emergency")

    band = ("0-17" if age <= 17 else "18-34" if age <= 34
            else "35-49" if age <= 49 else "50-64" if age <= 64 else "65+")

    row = pd.DataFrame([{
        "AGE": age,
        "WAIT_MINUTES": wait_minutes,
        "DAY_OF_WEEK": dt.weekday(),
        "MONTH": dt.month,
        "HOUR": dt.hour,
        "IS_WEEKEND": int(dt.weekday() >= 5),
        "IS_EMERGENCY": int(is_emergency),
        "GENDER_LABEL": gender,
        "DEPARTMENT": department,
        "ENCOUNTERCLASS": encounter_class,
        "AGE_BAND": band,
    }])

    pred = float(model.predict(row)[0])
    mae = float(bundle["metrics"].get("mae", 1.0))

    if pred < 1:
        risk, note = "Low", "Same-day visit - the patient is expected to go home today."
    elif pred < 2:
        risk, note = "Low", "Short stay expected - plan a same-week discharge."
    elif pred < 5:
        risk, note = "Medium", "Average stay - standard bed allocation is fine."
    else:
        risk, note = "High", "Long stay likely - reserve the bed and plan resources."

    return {
        "predicted_days": round(pred, 2),
        "range_low": round(max(0.0, pred - mae), 2),
        "range_high": round(pred + mae, 2),
        "risk_level": risk,
        "recommendation": note,
        "model": bundle["metrics"].get("model"),
        "model_mae": round(mae, 2),
        "input": row.to_dict(orient="records")[0],
    }


def all_metrics() -> dict:
    import json
    path = config.MODELS_DIR / "metrics.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}
