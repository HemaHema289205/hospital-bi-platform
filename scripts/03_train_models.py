"""
Step 3 : Train the Machine Learning models   (ML Layer, scikit-learn)

Two models are trained:

  A) ADMISSION FORECASTING  - how many patients will be admitted on a
     future day. Time-series regression using lag + calendar features.

  B) LENGTH-OF-STAY (LOS) PREDICTION - how many days a newly admitted
     patient is likely to stay. Tabular regression on patient + visit
     attributes.

Both are saved to models/ as .pkl and their scores to models/metrics.json.

Usage:
    python scripts/03_train_models.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PROC = ROOT / "data" / "processed"
MODELS = ROOT / "models"
MODELS.mkdir(parents=True, exist_ok=True)

# feature names the forecast model expects, in this exact order
ADM_FEATURES = [
    "DAY_OF_WEEK", "MONTH", "IS_WEEKEND", "WEEK_OF_YEAR",
    "LAG_1", "LAG_2", "LAG_7", "LAG_14",
    "ROLL_7", "ROLL_14", "ROLL_30",
]


def rmse(y_true, y_pred) -> float:
    return float(np.sqrt(np.mean((np.asarray(y_true) - np.asarray(y_pred)) ** 2)))


# ====================================================================
#  A)  ADMISSION FORECASTING
# ====================================================================
def make_lag_features(daily: pd.DataFrame, col: str = "ADMISSIONS") -> pd.DataFrame:
    df = daily.copy().sort_values("FLOW_DATE").reset_index(drop=True)
    for lag in (1, 2, 7, 14):
        df[f"LAG_{lag}"] = df[col].shift(lag)
    for win in (7, 14, 30):
        df[f"ROLL_{win}"] = df[col].shift(1).rolling(win).mean()
    return df


def candidate_models() -> dict:
    """Three different algorithms. The best one on the test window wins."""
    onehot = ColumnTransformer(
        [("oh", OneHotEncoder(handle_unknown="ignore"), ["DAY_OF_WEEK", "MONTH"])],
        remainder="passthrough",
    )
    return {
        "Ridge Regression": Pipeline([("pre", onehot), ("reg", Ridge(alpha=1.0))]),
        "Gradient Boosting": GradientBoostingRegressor(
            n_estimators=150, learning_rate=0.03, max_depth=2,
            subsample=0.8, random_state=42),
        "Random Forest": RandomForestRegressor(
            n_estimators=300, max_depth=6, min_samples_leaf=10,
            n_jobs=-1, random_state=42),
    }


def train_admissions() -> dict:
    print("\n" + "-" * 66)
    print("  A) ADMISSION FORECASTING MODEL")
    print("-" * 66)

    daily = pd.read_csv(PROC / "agg_daily_flow.csv", parse_dates=["FLOW_DATE"])
    df = make_lag_features(daily).dropna(subset=ADM_FEATURES).reset_index(drop=True)

    X = df[ADM_FEATURES]
    y = df["ADMISSIONS"]

    # Time-series split: the LAST 20% of days is the test set.
    # Never shuffle a time series - that would leak the future into training.
    cut = int(len(df) * 0.8)
    X_tr, X_te = X.iloc[:cut], X.iloc[cut:]
    y_tr, y_te = y.iloc[:cut], y.iloc[cut:]

    # naive baseline to beat: "tomorrow = long-run average"
    base_pred = np.full(len(y_te), y_tr.mean())
    base_mae = float(mean_absolute_error(y_te, base_pred))
    print(f"  baseline (predict the average)   MAE {base_mae:.2f}")
    print()

    results, fitted = [], {}
    for name, model in candidate_models().items():
        model.fit(X_tr, y_tr)
        pred = model.predict(X_te)
        r = {
            "name": name,
            "mae": round(float(mean_absolute_error(y_te, pred)), 3),
            "rmse": round(rmse(y_te, pred), 3),
            "r2": round(float(r2_score(y_te, pred)), 3),
        }
        results.append(r)
        fitted[name] = model
        print(f"  {name:<20}  MAE {r['mae']:>6}   RMSE {r['rmse']:>6}   R2 {r['r2']:>6}")

    best = max(results, key=lambda r: r["r2"])
    print(f"\n  --> best model: {best['name']}")
    print(f"      {(1 - best['mae'] / base_mae) * 100:.1f}% lower error than the baseline")

    metrics = {
        "model": best["name"],
        "target": "daily admissions",
        "train_days": int(len(X_tr)),
        "test_days": int(len(X_te)),
        "mae": best["mae"],
        "rmse": best["rmse"],
        "r2": best["r2"],
        "baseline_mae": round(base_mae, 3),
        "mean_actual": round(float(y_te.mean()), 2),
        "all_models": results,
    }

    # retrain the winner on ALL the data - that is the model we ship
    final = candidate_models()[best["name"]].fit(X, y)

    joblib.dump(
        {
            "model": final,
            "features": ADM_FEATURES,
            # history is needed to rebuild lag features for future dates
            "history": daily[["FLOW_DATE", "ADMISSIONS"]].to_dict(orient="records"),
            "metrics": metrics,
        },
        MODELS / "admission_forecast.pkl",
    )
    print("  saved -> models/admission_forecast.pkl")
    return metrics


# ====================================================================
#  B)  LENGTH OF STAY
# ====================================================================
LOS_NUM = ["AGE", "WAIT_MINUTES", "DAY_OF_WEEK", "MONTH", "HOUR", "IS_WEEKEND", "IS_EMERGENCY"]
LOS_CAT = ["GENDER_LABEL", "DEPARTMENT", "ENCOUNTERCLASS", "AGE_BAND"]


def train_los() -> dict:
    print("\n" + "-" * 66)
    print("  B) LENGTH-OF-STAY PREDICTION MODEL")
    print("-" * 66)

    enc = pd.read_csv(PROC / "fact_encounters.csv")
    df = enc[(enc["IS_ADMISSION"] == 1) & enc["LENGTH_OF_STAY"].notna()].copy()
    df = df[df["LENGTH_OF_STAY"] > 0]

    X = df[LOS_NUM + LOS_CAT]
    y = df["LENGTH_OF_STAY"]

    # random split is fine here (each row is an independent patient visit)
    rng = np.random.default_rng(42)
    mask = rng.random(len(df)) < 0.8
    X_tr, X_te, y_tr, y_te = X[mask], X[~mask], y[mask], y[~mask]

    pre = ColumnTransformer([
        ("num", StandardScaler(), LOS_NUM),
        ("cat", OneHotEncoder(handle_unknown="ignore"), LOS_CAT),
    ])
    pipe = Pipeline([
        ("pre", pre),
        ("rf", RandomForestRegressor(
            n_estimators=200, max_depth=14, min_samples_leaf=5,
            n_jobs=-1, random_state=42)),
    ])
    pipe.fit(X_tr, y_tr)

    pred = pipe.predict(X_te)
    metrics = {
        "model": "RandomForestRegressor + OneHotEncoder pipeline",
        "target": "length of stay (days)",
        "train_rows": int(len(X_tr)),
        "test_rows": int(len(X_te)),
        "mae": round(float(mean_absolute_error(y_te, pred)), 3),
        "rmse": round(rmse(y_te, pred), 3),
        "r2": round(float(r2_score(y_te, pred)), 3),
        "mean_actual": round(float(y_te.mean()), 2),
    }
    print(f"  trained on {metrics['train_rows']:,} visits, tested on {metrics['test_rows']:,}")
    print(f"  MAE  {metrics['mae']} days   RMSE {metrics['rmse']}   R2 {metrics['r2']}")

    final = Pipeline([
        ("pre", ColumnTransformer([
            ("num", StandardScaler(), LOS_NUM),
            ("cat", OneHotEncoder(handle_unknown="ignore"), LOS_CAT),
        ])),
        ("rf", RandomForestRegressor(
            n_estimators=200, max_depth=14, min_samples_leaf=5,
            n_jobs=-1, random_state=42)),
    ]).fit(X, y)

    joblib.dump(
        {
            "model": final,
            "numeric_features": LOS_NUM,
            "categorical_features": LOS_CAT,
            "options": {
                "DEPARTMENT": sorted(df["DEPARTMENT"].dropna().unique().tolist()),
                "ENCOUNTERCLASS": sorted(df["ENCOUNTERCLASS"].dropna().unique().tolist()),
                "GENDER_LABEL": sorted(df["GENDER_LABEL"].dropna().unique().tolist()),
                "AGE_BAND": sorted(df["AGE_BAND"].dropna().unique().tolist()),
            },
            "metrics": metrics,
        },
        MODELS / "los_model.pkl",
    )
    print(f"  saved -> models/los_model.pkl")
    return metrics


def main() -> None:
    print("=" * 66)
    print("  STEP 3 : MACHINE LEARNING  (scikit-learn)")
    print("=" * 66)

    if not (PROC / "agg_daily_flow.csv").exists():
        raise SystemExit(
            "\nERROR: processed data missing.\n"
            "Run first:  python scripts/01_clean_transform.py\n"
        )

    adm = train_admissions()
    los = train_los()

    (MODELS / "metrics.json").write_text(
        json.dumps({"admission_forecast": adm, "length_of_stay": los}, indent=2),
        encoding="utf-8",
    )

    print("\n" + "=" * 66)
    print("  DONE. Models saved in models/")
    print("  Next:  python -m uvicorn backend.main:app --reload")
    print("=" * 66)


if __name__ == "__main__":
    main()
