"""
LLM Layer - the "Queries Chatbot" on the dashboard.

Three providers, chosen with LLM_PROVIDER in .env:

  builtin (default) : offline engine. Understands the question with keyword
                      rules, runs the matching SQL, answers in plain English.
                      Needs no internet, no API key, no GPU - it always works.
  ollama            : local Ollama (ollama run llama3). The hospital numbers
                      are fetched first and passed to the model as context.
  openai            : OpenAI API, same context-passing idea.

Even in ollama/openai mode the numbers always come from the database, never
from the model's imagination.
"""
from __future__ import annotations

import re
from datetime import datetime

from backend import config, queries
from backend import ml_service

# -------------------------------------------------------------- helpers
def _fmt_int(n) -> str:
    return f"{int(round(float(n or 0))):,}"


def _fmt_money(n) -> str:
    return f"${float(n or 0):,.0f}"


def _card(kpi: dict, key: str) -> dict:
    for c in kpi["cards"]:
        if c["key"] == key:
            return c
    return {"value": 0, "change_pct": 0}


def _arrow(pct: float) -> str:
    if pct > 0:
        return f"up {abs(pct)}%"
    if pct < 0:
        return f"down {abs(pct)}%"
    return "flat"


# ----------------------------------------------------- intent handlers
def _h_admissions(start, end, _):
    k = queries.kpis(start, end)
    c = _card(k, "admissions")
    flow = queries.patient_flow(start, end)
    last = flow[-1] if flow else {}
    return (
        f"There were **{_fmt_int(c['value'])} admissions** between {start} and {end} "
        f"({_arrow(c['change_pct'])} vs the previous period). "
        f"On the most recent day ({last.get('date', 'n/a')}) the hospital admitted "
        f"{_fmt_int(last.get('admissions', 0))} patients."
    ), {"chart": "flow", "data": flow}


def _h_visits(start, end, _):
    k = queries.kpis(start, end)
    c = _card(k, "total_visits")
    extra = k["extra"]
    return (
        f"**{_fmt_int(c['value'])} patient visits** were recorded between {start} and {end} "
        f"({_arrow(c['change_pct'])} vs the previous period), from "
        f"{_fmt_int(extra['unique_patients'])} unique patients."
    ), {"chart": "flow", "data": queries.patient_flow(start, end)}


def _h_discharges(start, end, _):
    k = queries.kpis(start, end)
    c = _card(k, "discharges")
    return (
        f"**{_fmt_int(c['value'])} patients were discharged** between {start} and {end} "
        f"({_arrow(c['change_pct'])} vs the previous period)."
    ), {"chart": "flow", "data": queries.patient_flow(start, end)}


def _h_los(start, end, _):
    k = queries.kpis(start, end)
    c = _card(k, "avg_length_of_stay")
    depts = queries.departments(start, end)
    longest = max((d for d in depts if d["avg_los"] > 0), key=lambda d: d["avg_los"], default=None)
    msg = (f"The **average length of stay is {c['value']} days** "
           f"({_arrow(c['change_pct'])} vs the previous period).")
    if longest:
        msg += f" The longest stays are in **{longest['name']}** at {longest['avg_los']} days."
    return msg, {"chart": "departments", "data": depts}


def _h_revenue(start, end, _):
    k = queries.kpis(start, end)
    c = _card(k, "total_revenue")
    depts = sorted(queries.departments(start, end), key=lambda d: -d["revenue"])[:5]
    top = depts[0] if depts else None
    msg = (f"Total billed revenue for {start} to {end} is **{_fmt_money(c['value'])}** "
           f"({_arrow(c['change_pct'])} vs the previous period).")
    if top:
        msg += f" The biggest contributor is **{top['name']}** at {_fmt_money(top['revenue'])}."
    return msg, {"chart": "departments", "data": depts}


def _h_wait(start, end, _):
    rows = queries.wait_times(start, end)
    k = queries.kpis(start, end)
    worst = max(rows, key=lambda r: r["avg_wait"], default=None)
    msg = f"The average waiting time is **{k['extra']['avg_wait_minutes']} minutes**."
    if worst:
        msg += f" The longest waits are for **{worst['label']}** visits at {worst['avg_wait']} minutes."
    return msg, {"chart": "wait", "data": rows}


def _h_departments(start, end, _):
    rows = queries.departments(start, end)
    top = rows[:3]
    listed = ", ".join(f"**{r['name']}** ({_fmt_int(r['visits'])} visits, {r['pct']}%)" for r in top)
    return f"Busiest departments between {start} and {end}: {listed}.", {"chart": "departments", "data": rows}


def _h_conditions(start, end, _):
    rows = queries.top_conditions(start, end, 5)
    real = [r for r in rows if r["name"] != "Other"]
    listed = ", ".join(f"**{r['name']}** ({r['pct']}%)" for r in real[:5])
    return f"The most frequently recorded conditions are: {listed}.", {"chart": "conditions", "data": rows}


def _h_demographics(start, end, _):
    d = queries.demographics(start, end)
    g = ", ".join(f"{x['name']} {x['pct']}%" for x in d["gender"])
    biggest = max(d["age_bands"], key=lambda a: a["value"], default=None)
    msg = f"Across {_fmt_int(d['total'])} visits the gender split is {g}."
    if biggest:
        msg += f" The largest age group is **{biggest['name']}** with {biggest['pct']}% of visits."
    return msg, {"chart": "demographics", "data": d}


def _h_occupancy(start, end, _):
    rows = queries.bed_occupancy(start, end)
    flow = queries.patient_flow(start, end)
    latest = flow[-1]["occupancy"] if flow else 0
    worst = max(rows, key=lambda r: r["occupancy_pct"], default=None)
    msg = f"Hospital-wide bed occupancy is currently **{latest}%**."
    if worst:
        msg += f" The tightest ward is **{worst['ward']}** at {worst['occupancy_pct']}% ({worst['available']} beds free)."
    return msg, {"chart": "occupancy", "data": rows}


def _h_emergency(start, end, _):
    k = queries.kpis(start, end)
    n = k["extra"]["emergency_cases"]
    flow = queries.patient_flow(start, end)
    return (f"**{_fmt_int(n)} emergency cases** were handled between {start} and {end} - "
            f"about {round(n / max(len(flow), 1), 1)} per day."), {"chart": "flow", "data": flow}


def _h_forecast(start, end, msg):
    if not ml_service.models_ready():
        return ("The prediction models have not been trained yet. "
                "Run `python scripts/03_train_models.py` first."), None
    n = 7
    m = re.search(r"(\d+)\s*day", msg)
    if m:
        n = max(1, min(30, int(m.group(1))))
    f = ml_service.forecast_admissions(n)
    h = f["headline"]
    first = f["forecast"][0]
    return (
        f"The **{f['model']}** model predicts **{h['next_day']} admissions** for "
        f"{first['label']} ({h['confidence']}), which is {_arrow(h['vs_recent_avg_pct'])} "
        f"compared with the 30-day average of {h['recent_avg']}. "
        f"Model accuracy on unseen days: MAE {f['metrics']['mae']}, R2 {f['metrics']['r2']}."
    ), {"chart": "forecast", "data": f}


def _h_predict_los(start, end, msg):
    if not ml_service.models_ready():
        return ("The prediction models have not been trained yet. "
                "Run `python scripts/03_train_models.py` first."), None
    age_m = re.search(r"(\d{1,3})\s*(?:year|yr|y/o|years old|age)", msg)
    age = int(age_m.group(1)) if age_m else 55
    dept = "General Medicine"
    for d in ml_service.los_options()["DEPARTMENT"]:
        if d.lower() in msg:
            dept = d
            break
    cls = "emergency" if "emergency" in msg else "inpatient"
    r = ml_service.predict_los(age=age, department=dept, encounter_class=cls)
    return (
        f"For a {age}-year-old {cls} patient in **{dept}**, the model predicts a stay of "
        f"**{r['predicted_days']} days** (likely {r['range_low']}-{r['range_high']} days). "
        f"Risk level: {r['risk_level']}. {r['recommendation']}"
    ), {"chart": "los", "data": r}


def _h_summary(start, end, _):
    k = queries.kpis(start, end)
    v, a, d = _card(k, "total_visits"), _card(k, "admissions"), _card(k, "discharges")
    los, rev = _card(k, "avg_length_of_stay"), _card(k, "total_revenue")
    return (
        f"Summary for {start} to {end}:\n"
        f"- Visits: **{_fmt_int(v['value'])}** ({_arrow(v['change_pct'])})\n"
        f"- Admissions: **{_fmt_int(a['value'])}** ({_arrow(a['change_pct'])})\n"
        f"- Discharges: **{_fmt_int(d['value'])}** ({_arrow(d['change_pct'])})\n"
        f"- Avg length of stay: **{los['value']} days**\n"
        f"- Revenue: **{_fmt_money(rev['value'])}**\n"
        f"- Emergency cases: **{_fmt_int(k['extra']['emergency_cases'])}**, "
        f"avg wait {k['extra']['avg_wait_minutes']} min"
    ), {"chart": "flow", "data": queries.patient_flow(start, end)}


def _h_help(start, end, _):
    return (
        "I can answer questions about the hospital data. Try:\n"
        "- How many patients were admitted?\n"
        "- What is the average length of stay?\n"
        "- Show me the busiest departments\n"
        "- What is the bed occupancy?\n"
        "- Predict admissions for the next 7 days\n"
        "- Predict length of stay for a 70 year old emergency patient\n"
        "- Give me a summary"
    ), None


# -------------------------------------------------------------- routing
# order matters: the first matching rule wins
INTENTS: list[tuple[str, list[str], object]] = [
    ("forecast",     ["forecast", "predict admission", "next day", "next week",
                      "future admission", "how many will", "tomorrow"], _h_forecast),
    ("predict_los",  ["predict length", "predict stay", "los prediction",
                      "how long will", "expected stay"],                _h_predict_los),
    ("summary",      ["summary", "overview", "report", "how are we doing",
                      "overall"],                                       _h_summary),
    ("occupancy",    ["occupancy", "bed", "ward", "capacity", "icu"],   _h_occupancy),
    ("wait",         ["wait", "waiting", "queue", "delay"],             _h_wait),
    ("emergency",    ["emergency case", "emergencies", "casualty", "er "], _h_emergency),
    ("los",          ["length of stay", "los", "how long do patients",
                      "stay duration", "average stay"],                 _h_los),
    ("revenue",      ["revenue", "income", "money", "billing", "cost",
                      "earning"],                                       _h_revenue),
    ("departments",  ["department", "busiest", "ward wise", "unit",
                      "speciality", "specialty"],                       _h_departments),
    ("conditions",   ["condition", "diagnosis", "disease", "illness",
                      "top medical"],                                   _h_conditions),
    ("demographics", ["demographic", "gender", "male", "female", "age"], _h_demographics),
    ("discharges",   ["discharge"],                                     _h_discharges),
    ("admissions",   ["admission", "admitted", "admit"],                _h_admissions),
    ("visits",       ["visit", "patient count", "how many patients",
                      "footfall", "total patient"],                     _h_visits),
    ("help",         ["help", "what can you", "hello", "hi ", "hey"],   _h_help),
]


def detect_intent(message: str) -> tuple[str, object]:
    msg = f" {message.lower().strip()} "
    for name, keywords, handler in INTENTS:
        if any(k in msg for k in keywords):
            return name, handler
    return "summary", _h_summary


SUGGESTIONS = [
    "Show patient flow trends",
    "What is the average length of stay?",
    "Predict admissions for the next 7 days",
    "Which department is busiest?",
]


# ------------------------------------------------------------ providers
def _builtin(message: str, start: str, end: str) -> dict:
    intent, handler = detect_intent(message)
    reply, payload = handler(start, end, message.lower())
    return {
        "reply": reply,
        "intent": intent,
        "provider": "builtin",
        "context": payload,
        "suggestions": SUGGESTIONS,
    }


def _context_block(start: str, end: str) -> str:
    """Real numbers handed to an LLM so it cannot invent any."""
    k = queries.kpis(start, end)
    depts = queries.departments(start, end)[:5]
    conds = queries.top_conditions(start, end, 5)
    lines = [f"Reporting period: {start} to {end}", "KPIs:"]
    lines += [f"  - {c['label']}: {c['value']} ({c['change_pct']}% vs previous period)"
              for c in k["cards"]]
    lines.append(f"  - Emergency cases: {k['extra']['emergency_cases']}")
    lines.append(f"  - Average wait: {k['extra']['avg_wait_minutes']} minutes")
    lines.append("Departments (visits, avg LOS days):")
    lines += [f"  - {d['name']}: {d['visits']} visits, LOS {d['avg_los']}" for d in depts]
    lines.append("Top conditions:")
    lines += [f"  - {c['name']}: {c['pct']}%" for c in conds]
    if ml_service.models_ready():
        f = ml_service.forecast_admissions(3)
        lines.append("ML forecast (next days admissions): " +
                     ", ".join(f"{x['label']}={x['predicted']}" for x in f["forecast"]))
    return "\n".join(lines)


SYSTEM_PROMPT = (
    "You are the assistant inside a hospital Business Intelligence dashboard. "
    "Answer only from the HOSPITAL DATA given to you. Never invent a number. "
    "If the data does not contain the answer, say so. Keep answers under 90 words."
)


def _ollama(message: str, start: str, end: str) -> dict:
    import requests
    payload = {
        "model": config.OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"HOSPITAL DATA\n{_context_block(start, end)}\n\nQUESTION: {message}"},
        ],
    }
    r = requests.post(f"{config.OLLAMA_URL}/api/chat", json=payload, timeout=90)
    r.raise_for_status()
    reply = r.json()["message"]["content"].strip()
    intent, _ = detect_intent(message)
    return {"reply": reply, "intent": intent, "provider": "ollama",
            "context": None, "suggestions": SUGGESTIONS}


def _openai(message: str, start: str, end: str) -> dict:
    import requests
    if not config.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is empty in .env")
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
        json={
            "model": config.OPENAI_MODEL,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"HOSPITAL DATA\n{_context_block(start, end)}\n\nQUESTION: {message}"},
            ],
        },
        timeout=90,
    )
    r.raise_for_status()
    reply = r.json()["choices"][0]["message"]["content"].strip()
    intent, _ = detect_intent(message)
    return {"reply": reply, "intent": intent, "provider": "openai",
            "context": None, "suggestions": SUGGESTIONS}


def ask(message: str, start: str | None = None, end: str | None = None) -> dict:
    if not start or not end:
        start, end = queries.default_range(30)

    provider = config.LLM_PROVIDER
    try:
        if provider == "ollama":
            return _ollama(message, start, end)
        if provider == "openai":
            return _openai(message, start, end)
    except Exception as exc:                            # noqa: BLE001
        # Any LLM problem (server off, no key, no internet) falls back to the
        # offline engine so the dashboard never shows an error.
        out = _builtin(message, start, end)
        out["provider"] = f"builtin (fallback, {provider} failed: {type(exc).__name__})"
        return out

    return _builtin(message, start, end)
