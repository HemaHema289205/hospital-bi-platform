# HospitalFlow AI
### AI-Enabled Hospital Operational and Patient-Flow BI Platform

A complete, end-to-end Business Intelligence platform for a hospital: it takes raw
healthcare records, cleans them, stores them in a database, trains machine-learning
models on them, serves everything through a REST API, and presents it in an
interactive React dashboard with a built-in AI chatbot.

**Author:** Gudimetla Hema Kota Nagu · Roll No. 23ME1A5421
APP: https://hospital-bi-platform.vercel.app
---

## What it does

| Capability | Where you see it |
|---|---|
| Sign-in with demo hospital accounts | Login screen |
| Real-time hospital overview (visits, admissions, discharges, LOS, revenue) | Dashboard |
| Patient flow trend, demographics, top conditions, recent encounters | Dashboard |
| Department-wise performance, bed occupancy, waiting times, peak hours | Patient Flow Analytics |
| Admission forecasting + length-of-stay prediction (scikit-learn) | ML Predictions |
| Write your own SQL and export the result as CSV | Reports & Queries |
| Ask questions in plain English, answered from the database | AI Chatbot |

---

## Technology stack

| Layer | Technology |
|---|---|
| Dataset | Synthea-style synthetic healthcare CSVs |
| Data processing | Python, Pandas, NumPy |
| Database | SQLite (default, zero setup) or MySQL |
| Machine Learning | scikit-learn (Gradient Boosting, Random Forest, Ridge) |
| Backend | FastAPI + Uvicorn |
| Frontend | React 18, Vite, TypeScript |
| UI styling | Tailwind CSS |
| Charts | Recharts |
| Chatbot | Built-in rule + SQL engine (optionally Ollama or OpenAI) |
| Version control | Git, GitHub |

> **Note on Power BI.** The original proposal used Power BI for the visualisation
> layer. This build replaces it with a custom **React + Recharts** dashboard, so
> the whole BI layer lives in the same web application as the API and the chatbot,
> works on any machine without a Power BI licence, and can be hosted anywhere.

---

## Architecture

```
  Synthea-style CSVs            data/raw/*.csv
          |
          v
  Data Engineering Layer        scripts/01_clean_transform.py
  Pandas + NumPy                cleaning -> feature engineering
          |
          v
  Database Layer                SQLite / MySQL
  star-ish schema               dim_patients, fact_encounters,
                                fact_conditions, fact_procedures,
                                agg_daily_flow, agg_department
          |
          +--------------------------+
          |                          |
          v                          v
  ML Layer                     Analytics Layer
  scripts/03_train_models.py   backend/queries.py
  admission forecasting        KPIs, trends, departments,
  length-of-stay prediction    occupancy, waiting times
          |                          |
          +------------+-------------+
                       |
                       v
              Backend API (FastAPI)        backend/main.py
              REST + /docs                 + chatbot (LLM layer)
                       |
                       v
              Frontend (React + Vite + TypeScript + Tailwind)
              Dashboard | Analytics | Predictions | Reports | Chatbot
```

---

## Quick start

```bash
# macOS / Linux
bash setup.sh      # install everything + build database + train models
bash start.sh      # run the backend and the frontend
```

```bat
REM Windows
setup.bat
start.bat
```

Then open **http://127.0.0.1:5173** and sign in:

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | Hospital Administrator |
| `doctor` | `doctor123` | Doctor |
| `staff` | `staff123` | Operations Staff |

The login screen lists these and fills the form for you on a click. Passwords
are set in `.env`.

Step-by-step instructions (including what to do when something goes wrong) are in
**[RUN_GUIDE.md](RUN_GUIDE.md)**.

---

## Project layout

```
hospital-bi-platform/
├── data/
│   ├── raw/                 Synthea-style source CSVs
│   ├── processed/           cleaned, feature-engineered tables  (generated)
│   └── hospital.db          SQLite database                     (generated)
├── scripts/
│   ├── 00_generate_sample_data.py    create the synthetic dataset
│   ├── 01_clean_transform.py         cleaning + feature engineering
│   ├── 02_load_to_db.py              load into SQLite / MySQL
│   ├── 03_train_models.py            train + compare the ML models
│   └── run_pipeline.py               run steps 00-03 in one command
├── backend/
│   ├── main.py              FastAPI app (all REST endpoints)
│   ├── auth.py              demo sign-in + signed session tokens
│   ├── queries.py           every analytics SQL query
│   ├── ml_service.py        loads the models and makes predictions
│   ├── chatbot.py           the AI assistant (builtin / Ollama / OpenAI)
│   ├── database.py          database engine + helpers
│   └── config.py            settings, read from .env
├── models/                  trained .pkl files + metrics.json   (generated)
├── sql/schema.sql           reference DDL (needed only for MySQL)
├── frontend/                React + Vite + TypeScript + Tailwind app
├── docs/ARCHITECTURE.md     how every layer works, for the report
├── requirements.txt
├── setup.sh / setup.bat     one-time setup
└── start.sh / start.bat     run both servers
```

---

## Machine learning

**1. Admission forecasting** — predicts how many patients will be admitted on a
future day. Three algorithms (Ridge Regression, Gradient Boosting, Random Forest)
are trained on lag and calendar features and compared on a time-ordered test
split; the best one is kept. Current scores are written to `models/metrics.json`
and shown on the ML Predictions page.

**2. Length-of-stay prediction** — predicts how many days a newly admitted patient
will stay, from age, gender, department, admission type, waiting time and calendar
features, using a Random Forest inside a scikit-learn pipeline with one-hot
encoding.

Both models are retrained on the full dataset after evaluation and saved to
`models/`. Re-run `python scripts/03_train_models.py` any time to retrain.

---

## API

With the backend running, the full interactive API documentation is at
**http://127.0.0.1:8000/docs**.

| Endpoint | Purpose |
|---|---|
| `POST /api/auth/login` | sign in, returns a session token |
| `GET /api/auth/me` | who is signed in (used to revive a saved session) |
| `GET /api/health` | is the database loaded, are the models trained |
| `GET /api/kpis` | the five headline numbers + period-on-period change |
| `GET /api/patient-flow` | daily visits / admissions / discharges / occupancy |
| `GET /api/demographics` | gender and age-band split |
| `GET /api/conditions` | top medical conditions |
| `GET /api/departments` | department-wise performance |
| `GET /api/bed-occupancy` | beds in use per department |
| `GET /api/wait-times` | average waiting time per visit type |
| `GET /api/predictions/admissions?days=7` | admission forecast |
| `POST /api/predictions/length-of-stay` | length-of-stay prediction |
| `POST /api/reports/query` | run a read-only SELECT |
| `POST /api/chat` | ask the AI assistant a question |

---

## A note on the login

The sign-in is a **demo** login: three accounts are defined in `backend/auth.py`
with passwords read from `.env`, and the session token is a signed, expiring
HMAC string stored in the browser. That is enough to put a realistic login in
front of the dashboard, and the frontend drops back to the login screen by
itself when a session expires.

It is deliberately not a production auth system — there is no user table and
passwords are not hashed. Upgrading it would mean a `users` table, `bcrypt`
password hashing and proper JWTs.

---

## Switching to MySQL

SQLite is the default and needs no server. To use MySQL instead:

```bash
mysql -u root -p < sql/schema.sql       # creates the hospital_bi database
```

Then set in `.env`:

```
DB_TYPE=mysql
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DB=hospital_bi
```

and re-run `python scripts/02_load_to_db.py`. Nothing else changes — the same SQL
runs on both databases.

---

## Using a real LLM for the chatbot

The chatbot works offline out of the box. To have a language model phrase the
answers instead (the numbers still always come from the database):

```
LLM_PROVIDER=ollama        # after: ollama run llama3
# or
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

If the model is unreachable, the chatbot silently falls back to the offline engine.
