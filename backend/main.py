"""
HospitalFlow AI  -  Backend API  (FastAPI)

Start it with:
    python -m uvicorn backend.main:app --reload
Then open:
    http://127.0.0.1:8000/docs      <- interactive API documentation
"""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend import auth, config, chatbot, ml_service, queries
from backend.database import table_exists

# Everything else under /api needs a signed-in user.
PUBLIC_PATHS = {
    "/",
    "/api/health",
    "/api/auth/login",
    "/api/auth/me",
    "/api/auth/demo-accounts",
}


def _user_from_header(authorization: Optional[str]) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not signed in")
    try:
        return auth.read_token(authorization.split(" ", 1)[1])
    except auth.AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


def require_user(request: Request) -> None:
    """Applied to every route; lets the public ones through."""
    if request.url.path in PUBLIC_PATHS:
        return
    _user_from_header(request.headers.get("authorization"))


app = FastAPI(
    title="HospitalFlow AI API",
    description="AI-Enabled Hospital Operations and Patient-Flow BI Platform",
    version="1.0.0",
    dependencies=[Depends(require_user)],
)

# The React dev server runs on a different port, so the browser needs this.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def warm_up() -> None:
    """
    Load the models once, at startup, on a single thread.

    Without this the very first page load fires several prediction requests at
    the same time and they all race to unpickle the same file.
    """
    if ml_service.models_ready():
        try:
            ml_service.forecast_admissions(1)
            ml_service.los_options()
            print("  models loaded and ready")
        except Exception as exc:                        # noqa: BLE001
            print(f"  could not preload models: {exc}")


# --------------------------------------------------------------- models
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=100)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    start: Optional[str] = None
    end: Optional[str] = None


class LOSRequest(BaseModel):
    age: int = Field(50, ge=0, le=110)
    gender: str = "Male"
    department: str = "General Medicine"
    encounter_class: str = "inpatient"
    wait_minutes: int = Field(30, ge=0, le=600)


class ReportRequest(BaseModel):
    sql: str
    limit: int = Field(200, ge=1, le=2000)


# -------------------------------------------------------------- helpers
def _resolve(start: Optional[str], end: Optional[str], days: int = 30) -> tuple[str, str]:
    if start and end:
        return start, end
    return queries.default_range(days)


def _require_db() -> None:
    if not table_exists("fact_encounters"):
        raise HTTPException(
            status_code=503,
            detail="Database is empty. Run: python scripts/run_pipeline.py",
        )


# ------------------------------------------------------------- auth
@app.post("/api/auth/login", tags=["auth"])
def auth_login(req: LoginRequest):
    try:
        return auth.login(req.username, req.password)
    except auth.AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


@app.get("/api/auth/me", tags=["auth"])
def auth_me(authorization: Optional[str] = Header(default=None)):
    """Used by the frontend on page load to check a saved session."""
    return _user_from_header(authorization)


@app.get("/api/auth/demo-accounts", tags=["auth"])
def auth_demo_accounts():
    """The demo credentials, listed on the sign-in screen."""
    return {"items": auth.demo_accounts()}


# ------------------------------------------------------------ meta
@app.get("/api/health", tags=["meta"])
def health():
    db_ok = table_exists("fact_encounters")
    return {
        "status": "ok" if db_ok else "database not loaded",
        "database": config.DB_TYPE,
        "database_loaded": db_ok,
        "models_trained": ml_service.models_ready(),
        "llm_provider": config.LLM_PROVIDER,
    }


@app.get("/api/meta", tags=["meta"])
def meta():
    _require_db()
    bounds = queries.date_bounds()
    start, end = queries.default_range(30)
    depts = [d["name"] for d in queries.departments(bounds["min_date"], bounds["max_date"])]
    return {
        "data_range": bounds,
        "default_range": {"start": start, "end": end},
        "departments": depts,
        "total_beds": config.TOTAL_BEDS,
        "models_trained": ml_service.models_ready(),
    }


# ------------------------------------------------------------ dashboard
@app.get("/api/kpis", tags=["dashboard"])
def get_kpis(start: Optional[str] = None, end: Optional[str] = None):
    _require_db()
    return queries.kpis(*_resolve(start, end))


@app.get("/api/patient-flow", tags=["dashboard"])
def get_patient_flow(start: Optional[str] = None, end: Optional[str] = None):
    _require_db()
    s, e = _resolve(start, end)
    return {"range": {"start": s, "end": e}, "series": queries.patient_flow(s, e)}


@app.get("/api/demographics", tags=["dashboard"])
def get_demographics(start: Optional[str] = None, end: Optional[str] = None):
    _require_db()
    return queries.demographics(*_resolve(start, end))


@app.get("/api/conditions", tags=["dashboard"])
def get_conditions(start: Optional[str] = None, end: Optional[str] = None,
                   limit: int = Query(5, ge=1, le=20)):
    _require_db()
    s, e = _resolve(start, end)
    return {"items": queries.top_conditions(s, e, limit)}


@app.get("/api/encounters/recent", tags=["dashboard"])
def get_recent(limit: int = Query(10, ge=1, le=100)):
    _require_db()
    return {"items": queries.recent_encounters(limit)}


# ------------------------------------------------------- patient flow
@app.get("/api/departments", tags=["patient-flow"])
def get_departments(start: Optional[str] = None, end: Optional[str] = None):
    _require_db()
    s, e = _resolve(start, end)
    return {"items": queries.departments(s, e)}


@app.get("/api/bed-occupancy", tags=["patient-flow"])
def get_bed_occupancy(start: Optional[str] = None, end: Optional[str] = None):
    _require_db()
    s, e = _resolve(start, end)
    return {"items": queries.bed_occupancy(s, e)}


@app.get("/api/wait-times", tags=["patient-flow"])
def get_wait_times(start: Optional[str] = None, end: Optional[str] = None):
    _require_db()
    s, e = _resolve(start, end)
    return {"items": queries.wait_times(s, e)}


@app.get("/api/hourly-flow", tags=["patient-flow"])
def get_hourly(start: Optional[str] = None, end: Optional[str] = None):
    _require_db()
    s, e = _resolve(start, end)
    return {"items": queries.hourly_flow(s, e)}


@app.get("/api/weekday-flow", tags=["patient-flow"])
def get_weekday(start: Optional[str] = None, end: Optional[str] = None):
    _require_db()
    s, e = _resolve(start, end)
    return {"items": queries.weekday_flow(s, e)}


# --------------------------------------------------------- predictions
@app.get("/api/predictions/admissions", tags=["ml"])
def predict_admissions(days: int = Query(7, ge=1, le=30)):
    try:
        return ml_service.forecast_admissions(days)
    except ml_service.ModelNotTrained as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/api/predictions/length-of-stay", tags=["ml"])
def predict_los(req: LOSRequest):
    try:
        return ml_service.predict_los(
            age=req.age, gender=req.gender, department=req.department,
            encounter_class=req.encounter_class, wait_minutes=req.wait_minutes,
        )
    except ml_service.ModelNotTrained as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/api/predictions/options", tags=["ml"])
def prediction_options():
    try:
        return ml_service.los_options()
    except ml_service.ModelNotTrained as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/api/model-metrics", tags=["ml"])
def model_metrics():
    return ml_service.all_metrics()


# ------------------------------------------------------------- reports
@app.get("/api/search", tags=["reports"])
def search(q: str = Query(..., min_length=1), limit: int = Query(15, ge=1, le=100)):
    _require_db()
    return {"items": queries.search(q, limit)}


@app.post("/api/reports/query", tags=["reports"])
def run_query(req: ReportRequest):
    _require_db()
    try:
        return queries.run_report_sql(req.sql, req.limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:                                # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"SQL error: {exc}")


@app.get("/api/reports/samples", tags=["reports"])
def sample_queries():
    return {"items": [
        {"title": "Visits per department",
         "sql": "SELECT DEPARTMENT, COUNT(*) AS visits, SUM(IS_ADMISSION) AS admissions\nFROM fact_encounters\nGROUP BY DEPARTMENT\nORDER BY visits DESC"},
        {"title": "Busiest 10 days",
         "sql": "SELECT FLOW_DATE, VISITS, ADMISSIONS, BED_OCCUPANCY_PCT\nFROM agg_daily_flow\nORDER BY VISITS DESC\nLIMIT 10"},
        {"title": "Average stay by age band",
         "sql": "SELECT AGE_BAND, COUNT(*) AS admissions, ROUND(AVG(LENGTH_OF_STAY),2) AS avg_los\nFROM fact_encounters\nWHERE IS_ADMISSION = 1 AND LENGTH_OF_STAY IS NOT NULL\nGROUP BY AGE_BAND\nORDER BY AGE_BAND"},
        {"title": "Top 10 conditions",
         "sql": "SELECT DESCRIPTION, COUNT(*) AS cases\nFROM fact_conditions\nGROUP BY DESCRIPTION\nORDER BY cases DESC\nLIMIT 10"},
        {"title": "Monthly revenue trend",
         "sql": "SELECT YEAR, MONTH, COUNT(*) AS visits, ROUND(SUM(TOTAL_CLAIM_COST),2) AS revenue\nFROM fact_encounters\nGROUP BY YEAR, MONTH\nORDER BY YEAR, MONTH"},
        {"title": "Patients still admitted",
         "sql": "SELECT FULL_NAME, AGE, DEPARTMENT, VISIT_DATE\nFROM fact_encounters\nWHERE IS_ADMISSION = 1 AND DISCHARGE_DATE IS NULL\nORDER BY VISIT_DATE DESC\nLIMIT 25"},
    ]}


# ---------------------------------------------------------------- chat
@app.post("/api/chat", tags=["chatbot"])
def chat(req: ChatRequest):
    _require_db()
    return chatbot.ask(req.message, req.start, req.end)


@app.get("/api/chat/suggestions", tags=["chatbot"])
def chat_suggestions():
    return {"items": chatbot.SUGGESTIONS}


@app.get("/", include_in_schema=False)
def root():
    return {
        "name": "HospitalFlow AI API",
        "docs": "/docs",
        "health": "/api/health",
    }
