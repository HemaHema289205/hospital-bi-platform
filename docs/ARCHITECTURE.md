# Architecture — HospitalFlow AI

This document explains what each layer does, why it exists, and which file
implements it. It is written so it can be lifted almost directly into a project
report.

---

## 1. Data Source Layer

**Dataset:** Synthea-style synthetic healthcare records.

Synthea is an open-source synthetic patient generator used widely in healthcare
research. Real patient data cannot be used in a student project for privacy
reasons, and the real Synthea generator needs Java plus a multi-gigabyte download,
so `scripts/00_generate_sample_data.py` produces CSV files with **the same column
names and structure that Synthea exports**. Everything downstream therefore works
unchanged if real Synthea CSVs are dropped into `data/raw/` instead.

| File | Rows (default) | Key columns |
|---|---|---|
| `patients.csv` | 12,000 | Id, BIRTHDATE, GENDER, CITY, ... |
| `encounters.csv` | ~84,000 | Id, START, STOP, PATIENT, ENCOUNTERCLASS, DEPARTMENT, costs |
| `conditions.csv` | ~55,000 | START, STOP, PATIENT, ENCOUNTER, DESCRIPTION |
| `procedures.csv` | ~94,000 | START, PATIENT, ENCOUNTER, DESCRIPTION, BASE_COST |
| `organizations.csv` | 8 | Id, NAME, CITY, REVENUE |

The generator models realistic behaviour: weekday peaks, a winter respiratory
season, age-dependent length of stay, and costs that vary with condition severity.

---

## 2. Data Engineering Layer

**Implemented in:** `scripts/01_clean_transform.py` (Pandas + NumPy)

### Cleaning
- duplicate patient and encounter IDs removed
- identifier columns (SSN, licence, passport) dropped — never used for analysis
- dates parsed, timezone stripped, invalid rows removed
- rows where the discharge time was before the admission time are repaired
- missing department / encounter class filled with sensible defaults

### A deliberate modelling decision
The last day in the dataset is treated as "today". A patient admitted shortly
before that, whose discharge date falls after it, **has not actually been
discharged yet** — their `STOP` is blanked and their status becomes `Admitted`.
Their length of stay is left as null so that it never drags the averages down and
is never shown to the ML model as a completed stay. This is why the dashboard
shows fewer discharges than admissions, exactly as a real hospital would.

### Feature engineering
| Feature | How it is derived | Why |
|---|---|---|
| `AGE`, `AGE_BAND` | birth date vs. date of death or today | demographics, ML input |
| `IS_ADMISSION`, `IS_EMERGENCY` | from `ENCOUNTERCLASS` | separates inpatient flow from OPD |
| `LENGTH_OF_STAY` | discharge − admission, in days | ML target |
| `WAIT_MINUTES` | modelled per visit type | waiting-time analysis |
| `DAY_OF_WEEK`, `MONTH`, `HOUR`, `IS_WEEKEND` | calendar features from `START` | seasonality for forecasting |
| `STATUS` | Admitted / Discharged / Completed | dashboard table |
| `OUT_OF_POCKET` | claim cost − payer coverage | revenue analysis |

### Aggregate tables
- **`agg_daily_flow`** — one row per calendar day: visits, admissions, discharges,
  emergency cases, revenue, average wait, average LOS, beds occupied and occupancy
  percentage. This is the table the forecasting model learns from.
  Trailing days that contain only discharges are cut off, and the first 21 days
  are dropped as a warm-up period (bed occupancy starts at zero and climbs,
  which is an artefact of where the window opens, not a real hospital pattern).
- **`agg_department`** — one row per department with visits, admissions, average
  LOS, average wait, revenue and share of total visits.

---

## 3. Database Layer

**Implemented in:** `scripts/02_load_to_db.py`, `sql/schema.sql`, `backend/database.py`

A star-schema-style design:

```
            dim_patients
                 ^
                 | PATIENT_ID
                 |
fact_conditions  |  fact_procedures
        \        |        /
         \       |       /
          fact_encounters          <- the central fact table
                 |
     agg_daily_flow, agg_department   <- pre-computed aggregates
```

**Portability.** SQLAlchemy is used as the engine layer and all date columns are
stored as plain `YYYY-MM-DD` text, so **the identical SQL runs on both SQLite and
MySQL**. SQLite is the default because it needs no server — the database is a
single file at `data/hospital.db`. Setting `DB_TYPE=mysql` in `.env` switches to
MySQL without changing a line of query code.

Indexes are created on `VISIT_DATE`, `DEPARTMENT`, `ENCOUNTERCLASS`,
`IS_ADMISSION` and condition descriptions, which are the columns the dashboard
filters and groups by.

---

## 4. ML Layer

**Implemented in:** `scripts/03_train_models.py` (training), `backend/ml_service.py` (serving)

### A. Admission forecasting

**Problem:** how many patients will be admitted on a future day?

**Features (11):** day of week, month, is-weekend, week of year, admissions 1 / 2 /
7 / 14 days ago, and 7 / 14 / 30-day rolling means.

**Validation:** the last 20% of days form the test set. The data is **never
shuffled** — shuffling a time series leaks future information into training and
produces a meaningless score.

**Model selection:** three algorithms are trained and compared, and the best R² wins:

| Candidate | Why it is included |
|---|---|
| Ridge Regression | linear baseline; captures the weekly pattern cleanly |
| Gradient Boosting | captures non-linear interactions between calendar and lag features |
| Random Forest | robust ensemble, less prone to overfitting noise |

A naive baseline ("tomorrow equals the long-run average") is also measured, and
the report prints how much the chosen model beats it by. The winner is then
retrained on the full dataset and saved to `models/admission_forecast.pkl`
together with the history it needs to build lag features for future dates.

**Serving:** `forecast_admissions(days)` predicts recursively — day 1 from real
history, then that prediction is appended and day 2 is predicted from it, and
so on. A confidence band of ± RMSE is returned with each point.

### B. Length-of-stay prediction

**Problem:** how many days will a newly admitted patient stay?

**Features:** age, waiting time, day of week, month, hour, is-weekend,
is-emergency (numeric, standard-scaled) plus gender, department, encounter class
and age band (categorical, one-hot encoded).

**Model:** `Pipeline(ColumnTransformer(StandardScaler + OneHotEncoder) → RandomForestRegressor)`.
Wrapping the preprocessing inside the pipeline means the saved `.pkl` can accept
raw values straight from the web form — no manual encoding at prediction time,
and no risk of train/serve skew.

**Output:** predicted days, a likely range of ± MAE, a risk level (Low / Medium /
High) and a resource-planning recommendation.

All scores are written to `models/metrics.json` and displayed on the ML
Predictions page, so the dashboard always reports the model's real accuracy rather
than a hard-coded number.

---

## 5. Analytics Layer

**Implemented in:** `backend/queries.py`

Every number on the dashboard comes from a SQL query in this one file — there are
no computed figures hidden in the frontend. Highlights:

- **KPIs** are computed for the selected window *and* for the window immediately
  before it, which is what produces the "↑ 8.5% vs previous period" comparisons.
- **Bed occupancy** is point-in-time: a bed counts as occupied if the patient was
  admitted on or before the end date and has no discharge date yet. Bed capacity
  is shared across departments in proportion to their admission volume.
- **Report queries** are guarded: only statements starting with `SELECT` or `WITH`
  are accepted, a keyword blacklist blocks `INSERT`/`UPDATE`/`DELETE`/`DROP`/
  `ATTACH`/`PRAGMA`, the query is wrapped in a subquery with a hard `LIMIT`, and
  parameters are always bound rather than string-formatted.

---

## 6. Backend API Layer

**Implemented in:** `backend/main.py` (FastAPI)

REST endpoints grouped into `meta`, `dashboard`, `patient-flow`, `ml`, `reports`
and `chatbot`. Pydantic models validate every request body (age is bounded 0–110,
chat messages to 500 characters), and CORS is enabled so the React dev server on
port 5173 can call the API on port 8000. FastAPI generates interactive
documentation automatically at `/docs`.

A `/api/health` endpoint reports whether the database is loaded and the models are
trained, and every data endpoint returns a clear 503 with the exact command to run
if the pipeline has not been executed yet.

---

## 7. LLM Layer — the AI chatbot

**Implemented in:** `backend/chatbot.py`

Three interchangeable providers, selected by `LLM_PROVIDER` in `.env`:

**`builtin` (default).** A keyword-to-intent router maps the question to one of
fifteen intents (admissions, discharges, length of stay, revenue, departments,
conditions, demographics, occupancy, waiting times, emergency, forecast,
LOS prediction, summary, help). The matching handler runs the relevant SQL or ML
call and writes the answer in plain English. It needs no internet, no API key and
no GPU, so it always works during a demo.

**`ollama` / `openai`.** The real numbers are fetched from the database *first*
and passed to the language model as context, with a system prompt that forbids
inventing figures. If the model is unreachable the request falls back silently to
the built-in engine, so the dashboard never shows an error.

The key design point: **the language model phrases the answer, the database
provides the facts.** That is what keeps the chatbot trustworthy.

---

## 7a. Authentication

**Implemented in:** `backend/auth.py`, `frontend/src/lib/auth.tsx`, `frontend/src/pages/Login.tsx`

A demo sign-in sits in front of the dashboard. Three accounts (Hospital
Administrator, Doctor, Operations Staff) are defined in `backend/auth.py`, with
their passwords read from `.env`.

**How a session works**

1. `POST /api/auth/login` checks the credentials and returns a token.
2. The token is `base64(payload).HMAC-SHA256(payload, secret)`, where the payload
   holds the username and an expiry timestamp. It is signed, so it cannot be
   forged by hand, and it expires after `TOKEN_HOURS` (12 by default).
3. The React app stores the token in `localStorage` and sends it as an
   `Authorization: Bearer` header on every request.
4. On page load the app calls `GET /api/auth/me`; if the token is still valid the
   session is revived, otherwise the login screen appears.
5. If any request comes back `401`, an interceptor clears the session and returns
   the user to the login screen, rather than showing an error on every card.

Two small security details worth pointing out in a viva: `hmac.compare_digest` is
used instead of `==` so the comparison cannot be timed, and a wrong username and
a wrong password return the *same* message, so the form never reveals which
accounts exist.

**What it is not.** There is no user table and passwords are not hashed — this is
a demo login for a project, not production authentication. The production version
would be a `users` table with `bcrypt` hashes and standard JWTs.

---

## 8. Frontend Layer

**Implemented in:** `frontend/` — React 18 + Vite + TypeScript + Tailwind CSS + Recharts

| Page | File | Contents |
|---|---|---|
| Dashboard | `src/pages/Dashboard.tsx` | KPI cards, flow trend, demographics donut, top conditions, prediction tiles, recent encounters, chat rail |
| Patient Flow Analytics | `src/pages/PatientFlow.tsx` | occupancy over time, department donut, ward utilisation, waiting times, weekday and hourly peaks, department table |
| ML Predictions | `src/pages/Predictions.tsx` | forecast chart with confidence band, LOS predictor form, model scorecards |
| Reports & Queries | `src/pages/Reports.tsx` | SQL editor, saved reports, result grid, CSV export |
| AI Chatbot | `src/pages/Chatbot.tsx` | full-height chat with example questions |
| Login | `src/pages/Login.tsx` | split-screen sign-in with demo account shortcuts |

**Design system.** Every colour is a CSS custom property defined in
`src/index.css` with real hex values, written out explicitly for **both light and
dark themes**, and mapped into Tailwind in `tailwind.config.js`. Buttons, inputs,
selects, textareas and scrollbars are all styled explicitly, and the font stack is
a web-safe system stack, so the application renders correctly with no external
stylesheet, no web font and no dependency on any host page's CSS.

**Data flow.** `src/api.ts` is the single place that talks to the backend;
`src/lib/useFetch.ts` is a small hook that reloads when the date range changes and
discards responses that were superseded while in flight. Vite proxies `/api` to
`http://127.0.0.1:8000` in development, so the browser never encounters a CORS
problem.

---

## 9. Why React instead of Power BI

The original proposal named Power BI as the visualisation layer. This build uses a
custom React dashboard instead:

| | Power BI | React + Recharts |
|---|---|---|
| Licence | Pro licence needed to share | none |
| Runs on | Windows desktop / Power BI service | any browser |
| Integration | separate tool, separate refresh | same app as the API and chatbot |
| ML predictions | awkward to embed | native — a chart and a form |
| Chatbot | not possible inline | built into the layout |
| Portfolio value | a `.pbix` file | source code you wrote |

The analytical content is identical — KPIs, trends, drill-down by department,
filters and export — but it all lives in one deployable web application.
