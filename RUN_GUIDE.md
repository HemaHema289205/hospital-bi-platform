# RUN GUIDE — HospitalFlow AI
### Hema ki step-by-step guide (simple ga)

Ee file lo project ni **run cheyyadam ela** ani step by step undi.
Code ni nuvvu edit cheyyanakkarledu — just commands run cheste chalu.

---

## 0. Mundu em kavali (one time only)

Ee rendu ni ne computer lo install cheyyali:

| Em kavali | Ekkada download | Check command |
|---|---|---|
| **Python 3.10+** | https://www.python.org/downloads/ | `python --version` |
| **Node.js 18+** | https://nodejs.org/ | `node --version` |

> Windows lo Python install chesetappudu **"Add Python to PATH"** checkbox ni
> tappakunda tick cheyyi. Lekapote `python` command panicheyydu.

---

## 1. Setup — oka sari matrame cheyyali

Project folder ni open chesi, terminal (Windows lo Command Prompt) lo:

**Windows:**
```
setup.bat
```

**Mac / Linux:**
```
bash setup.sh
```

Idi em chestundi ante:

1. Python packages install chestundi (pandas, scikit-learn, FastAPI...)
2. `.env` file create chestundi (settings file)
3. **Data pipeline** run chestundi — hospital data generate chesi, clean chesi,
   database lo pettu, ML models train chestundi
4. Frontend packages install chestundi (React, Recharts...)

**Time:** modati sari 3-5 nimishalu padutundi. Internet kavali (packages download ki).

Chivarlo ila vastundi ante setup success:
```
==============================================
  Setup complete.
  Now run:  start.bat
==============================================
```

---

## 2. Project ni run cheyyadam

**Windows:**
```
start.bat
```

**Mac / Linux:**
```
bash start.sh
```

Idi rendu servers start chestundi:

| Server | Address | Enduku |
|---|---|---|
| Backend (FastAPI) | http://127.0.0.1:8000 | Data + ML + chatbot |
| Frontend (React) | http://127.0.0.1:5173 | **Dashboard — idi browser lo open avutundi** |

Browser automatic ga open avvakapote, manual ga **http://127.0.0.1:5173** type cheyyi.

**Aapali ante:** terminal lo `Ctrl + C` press cheyyi.

---

## 2a. Login

Modati ga **login page** vastundi. Ee 3 accounts unnayi:

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | Hospital Administrator |
| `doctor` | `doctor123` | Doctor |
| `staff` | `staff123` | Operations Staff |

Login page lo kinda **"Demo accounts"** box untundi — dani meeda click cheste
username/password automatic ga fill avutayi. Taruvata **Sign in** kottu.

- Oka sari login ayyaka, browser refresh chesina malli adagadu (12 hours varaku)
- Logout kavali ante top-right lo **arrow icon** click cheyyi
- Password marchali ante `.env` file lo `ADMIN_PASSWORD=...` marchi, backend restart cheyyi

> Idi **demo login** — passwords `.env` lo unnayi, database lo users table ledu.
> Viva lo adigithe ila cheppu: *"demo authentication with signed, expiring session
> tokens — production lo users table + bcrypt hashing vaadali."*

---

## 3. Dashboard lo em untayi

| Page | Em chuputundi |
|---|---|
| **Dashboard** | 5 KPI cards, patient flow trend, demographics donut, top conditions, predictions, recent patients, AI assistant |
| **Patient Flow Analytics** | Bed occupancy, department-wise flow, waiting times, weekday & hourly peaks, department table |
| **ML Predictions** | Admission forecast graph + Length of Stay predictor (nuvve values petti predict cheyyochu) + model scores |
| **Reports & Queries** | Ne sontha SQL rasi run cheyyochu, result ni CSV ga download cheyyochu |
| **AI Chatbot** | English lo question adagochu — answer database nunchi vastundi |

Py top-right lo **moon icon** untundi — adi dark mode toggle.

---

## 4. Demo / Viva lo em chupinchali

Ee order lo chupiste project flow clear ga ardham avutundi:

1. **Login** — demo account tho sign in cheyyi (admin / admin123)
2. **Dashboard** — "idi hospital overview, real data nunchi vachina numbers"
3. **Date range** ni "Last 7 days" ki marchu — anni charts automatic ga update avutayi
4. **Patient Flow Analytics** — "ikkada bed occupancy, waiting time analysis"
5. **ML Predictions** —
   - Admission forecast graph chupinchu (solid line = actual, dashed = prediction)
   - LOS predictor lo age 75, department Emergency petti **Predict stay** kottu
   - "Model Performance" card lo 3 algorithms compare chesina table undi — adi chupinchu
6. **Reports & Queries** — "Visits per department" saved report run chesi chupinchu
7. **AI Chatbot** — *"Predict admissions for the next 7 days"* ani adugu

---

## 5. Em thappu ayina — fix ela

### `python` is not recognized (Windows)
Python PATH lo ledu. Python ni malli install chesi **"Add Python to PATH"**
tick cheyyi. Leda `python` badulu `py` try cheyyi.

### `npm` is not recognized
Node.js install cheyyaledu. https://nodejs.org/ nunchi install chesi,
terminal ni **close chesi malli open** cheyyi.

### Dashboard lo "Could not load this data" ani vastundi
Backend run avvatledu. Inko terminal open chesi:
```
python -m uvicorn backend.main:app --reload
```

### "Database is empty" ani vastundi
Pipeline run avvaledu:
```
python scripts/run_pipeline.py
```

### "Run: python scripts/03_train_models.py" ani prediction page lo vastundi
Models train avvaledu:
```
python scripts/03_train_models.py
```

### Login lo "Wrong username or password" ani vastundi
Username/password correct ga type cheyyi (`admin` / `admin123`), leda login page lo
**Demo accounts** box lo click cheyyi — automatic ga fill avutundi.

### Login ayyaka malli login page ki vellipotundi
Session expire ayindi (12 hours taruvata), leda backend restart ayindi.
Malli login cheyyi.

### Port 8000 / 5173 already in use
Aa port lo inko program nadustundi. Aa terminal ni close chesi malli try cheyyi.

### Anni malli modati nunchi cheyyali ante
```
python scripts/run_pipeline.py --regenerate
```
Idi kotha data generate chesi, anni steps malli chestundi.

---

## 6. Data ni marchali ante

Ekkuva/takkuva patients tho data kavali ante:

```
python scripts/00_generate_sample_data.py --patients 20000 --years 3
python scripts/01_clean_transform.py
python scripts/02_load_to_db.py
python scripts/03_train_models.py
```

Nijamaina Synthea data vaadali ante — Synthea CSV files ni `data/raw/` lo pettu
(same file names tho), appudu step 00 skip chesi step 01 nunchi start cheyyi.

---

## 7. MySQL vaadali ante (optional)

Default ga **SQLite** vaadutundi — idi oka file matrame, server avasaram ledu,
andhuke setup easy. Report lo MySQL raasavu kabatti MySQL kuda support chestundi:

1. MySQL install chesi:
   ```
   mysql -u root -p < sql/schema.sql
   ```
2. `.env` file lo marchu:
   ```
   DB_TYPE=mysql
   MYSQL_PASSWORD=ne_password
   ```
3. Malli load cheyyi:
   ```
   python scripts/02_load_to_db.py
   ```

Migatha anni same — SQL code okkate rendu databases meeda pani chestundi.

---

## 8. Each file enduku undi (report rayadaniki)

| File / Folder | Enduku |
|---|---|
| `scripts/00_generate_sample_data.py` | Synthea style hospital data generate chestundi |
| `scripts/01_clean_transform.py` | **Data cleaning + feature engineering** (LOS, waiting time, age band, daily aggregates) |
| `scripts/02_load_to_db.py` | Clean data ni database lo load chestundi |
| `scripts/03_train_models.py` | **ML models** train chestundi + 3 algorithms compare chestundi |
| `backend/queries.py` | Anni **SQL analytics queries** ikkada unnayi |
| `backend/ml_service.py` | Trained models ni load chesi predictions ichestundi |
| `backend/chatbot.py` | **AI chatbot** logic — question ni ardham chesukoni SQL run chestundi |
| `backend/auth.py` | **Login** — accounts, password check, signed session tokens |
| `backend/main.py` | **REST API** — anni endpoints |
| `frontend/src/pages/` | Login + 5 dashboard pages |
| `frontend/src/lib/auth.tsx` | Login state, token storage, session expire ayite auto logout |
| `frontend/src/components/` | Reusable UI parts (sidebar, KPI card, chat panel...) |
| `sql/schema.sql` | Database schema (MySQL DDL) — report lo pettukovachu |
| `docs/ARCHITECTURE.md` | Prathi layer ela pani chestundo detail ga — report ki direct ga use cheyyochu |

---

## Okka line lo

```
setup.bat  (oka sari)  ->  start.bat  (prathi sari)  ->  http://127.0.0.1:5173
                                                      ->  admin / admin123
```
