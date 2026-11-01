"""
API tests.

Run from the project root (needs data/hospital.db and models/):
    python -m pytest
"""
import pytest
from fastapi.testclient import TestClient

from backend import auth
from backend.main import app

client = TestClient(app)


@pytest.fixture(scope="module")
def headers():
    password = auth.USERS["admin"]["password"]
    res = client.post("/api/auth/login", json={"username": "admin", "password": password})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['token']}"}


# ---------------------------------------------------------------- auth
def test_health_is_public():
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["database_loaded"] is True
    assert body["models_trained"] is True


def test_wrong_password_is_rejected():
    res = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert res.status_code == 401


@pytest.mark.parametrize("path", ["/api/kpis", "/api/meta", "/api/departments",
                                  "/api/predictions/admissions", "/api/auth/me"])
def test_data_needs_login(path):
    assert client.get(path).status_code == 401


def test_bad_token_is_rejected():
    res = client.get("/api/kpis", headers={"Authorization": "Bearer not.valid"})
    assert res.status_code == 401


def test_me_returns_user(headers):
    res = client.get("/api/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["username"] == "admin"
    assert "password" not in res.json()


def test_changed_password_is_not_listed(monkeypatch):
    monkeypatch.setitem(auth.USERS["admin"], "password", "a-real-secret")
    names = [a["username"] for a in client.get("/api/auth/demo-accounts").json()["items"]]
    assert "admin" not in names


# ----------------------------------------------------------- dashboard
@pytest.mark.parametrize("path", [
    "/api/meta", "/api/kpis", "/api/patient-flow", "/api/demographics",
    "/api/conditions", "/api/encounters/recent", "/api/departments",
    "/api/bed-occupancy", "/api/wait-times", "/api/hourly-flow",
    "/api/weekday-flow", "/api/model-metrics", "/api/reports/samples",
    "/api/chat/suggestions",
])
def test_endpoints_respond(path, headers):
    assert client.get(path, headers=headers).status_code == 200


def test_kpis_have_cards(headers):
    cards = client.get("/api/kpis", headers=headers).json()["cards"]
    assert any(c["key"] == "total_visits" and c["value"] > 0 for c in cards)


# ------------------------------------------------------------------ ML
def test_admission_forecast(headers):
    res = client.get("/api/predictions/admissions?days=7", headers=headers)
    assert res.status_code == 200


def test_length_of_stay_prediction(headers):
    res = client.post("/api/predictions/length-of-stay", headers=headers, json={
        "age": 65, "gender": "Female", "department": "Cardiology",
        "encounter_class": "inpatient", "wait_minutes": 40,
    })
    assert res.status_code == 200
    body = res.json()
    assert body["predicted_days"] > 0
    assert body["range_low"] <= body["predicted_days"] <= body["range_high"]


def test_outpatient_has_no_stay(headers):
    res = client.post("/api/predictions/length-of-stay", headers=headers, json={
        "age": 40, "gender": "Male", "department": "Cardiology",
        "encounter_class": "outpatient", "wait_minutes": 20,
    })
    assert res.status_code == 200
    body = res.json()
    assert body["predicted_days"] == 0
    # 20 min wait + a 15-60 min consultation
    assert 0.5 <= body["predicted_hours"] <= 1.5


# ------------------------------------------------------------- reports
def test_select_query_runs(headers):
    res = client.post("/api/reports/query", headers=headers,
                      json={"sql": "SELECT COUNT(*) AS n FROM fact_encounters"})
    assert res.status_code == 200
    assert res.json()["rows"][0]["n"] > 0


@pytest.mark.parametrize("sql", [
    "DROP TABLE dim_patients",
    "DELETE FROM fact_encounters",
    "SELECT * FROM fact_encounters WHERE 1=1; DROP TABLE dim_patients",
])
def test_write_queries_are_blocked(sql, headers):
    assert client.post("/api/reports/query", headers=headers,
                       json={"sql": sql}).status_code == 400


# ---------------------------------------------------------------- chat
@pytest.mark.parametrize("question", [
    "How many patients?", "What is the average length of stay?",
    "Which department has the longest wait?",
])
def test_chatbot_answers(question, headers):
    res = client.post("/api/chat", headers=headers, json={"message": question})
    assert res.status_code == 200
    assert res.json()["reply"]
