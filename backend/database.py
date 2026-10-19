"""Database engine + a tiny helper that returns query results as dicts."""
from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from backend import config

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(
            config.database_url(),
            pool_pre_ping=True,
            future=True,
        )
    return _engine


def query_df(sql: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    """Run a SELECT and get a DataFrame back."""
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


def query_rows(sql: str, params: dict[str, Any] | None = None) -> list[dict]:
    """
    Run a SELECT and get a list of dicts, ready to be turned into JSON.

    NaN is not valid JSON, and NaN turns up legitimately (a patient who has
    not been discharged has no length of stay yet), so every NaN becomes
    null here instead of blowing up the API response.
    """
    df = query_df(sql, params)
    if df.empty:
        return []
    return df.astype(object).where(pd.notna(df), None).to_dict(orient="records")


def query_one(sql: str, params: dict[str, Any] | None = None) -> dict | None:
    rows = query_rows(sql, params)
    return rows[0] if rows else None


def table_exists(name: str) -> bool:
    from sqlalchemy import inspect
    return name in inspect(get_engine()).get_table_names()
