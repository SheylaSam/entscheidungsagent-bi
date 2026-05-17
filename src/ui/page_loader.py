"""Cached data loaders + small per-page helpers.

Pages call into these instead of duplicating SQL. Caching keys are
keyed by the function args so distinct date-range/country selections
each get their own cache entry.

Moved here from app.py during Phase 3.  No behavior change.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.customer_analysis import (
    load_primary_customer_country, summarize_segments_by_country,
)
from src.data_processing import get_connection
from src.forecasting import load_forecast, run_backtest
from src.product_analysis import load_product_analysis
from src.rfm_analysis import load_rfm


# ── then the 9 functions, copied verbatim from app.py ──────────────────────

@st.cache_data
def get_countries() -> list[str]:
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT DISTINCT country FROM transactions ORDER BY country", conn)
    finally:
        conn.close()
    return df['country'].tolist()


@st.cache_data
def load_backtest(start_date: str, end_date: str, countries: tuple) -> dict | None:
    conn = get_connection()
    try:
        from src.forecasting import prepare_monthly_series
        series = prepare_monthly_series(conn, start_date, end_date, countries)
    finally:
        conn.close()
    return run_backtest(series, holdout_months=3)


@st.cache_data
def load_all(
    start_date: str,
    end_date: str,
    countries: tuple,
    declining_months: int = 3,
    top_n: int = 10,
    min_product_revenue: float = 0,
):
    conn = get_connection()
    try:
        rfm = load_rfm(conn, start_date, end_date, countries)
        actuals, forecast = load_forecast(conn, start_date, end_date, countries)
        top_products, declining = load_product_analysis(
            conn,
            start_date,
            end_date,
            countries,
            declining_months,
            top_n,
            min_product_revenue,
        )
    finally:
        conn.close()
    return rfm, actuals, forecast, top_products, declining


@st.cache_data
def load_customer_country(start_date: str, end_date: str, countries: tuple) -> pd.DataFrame:
    conn = get_connection()
    try:
        df = load_primary_customer_country(conn, start_date, end_date, countries)
    finally:
        conn.close()
    return df


@st.cache_data
def load_monthly_product(start_date: str, end_date: str, countries: tuple):
    conn = get_connection()
    try:
        df = pd.read_sql(
            f"""SELECT description, strftime('%Y-%m-01', invoice_date) as month,
                       SUM(revenue) as revenue
                FROM transactions
                WHERE invoice_date >= ? AND invoice_date <= ?
                AND country IN ({','.join(['?']*len(countries))})
                GROUP BY description, month
                ORDER BY month""",
            conn,
            params=(start_date, end_date + ' 23:59:59') + countries,
        )
    finally:
        conn.close()
    df['month'] = pd.to_datetime(df['month'])
    return df


@st.cache_data
def load_revenue_by_country(start_date: str, end_date: str, countries: tuple) -> pd.DataFrame:
    conn = get_connection()
    try:
        df = pd.read_sql(
            f"""SELECT country, SUM(revenue) as revenue, COUNT(DISTINCT customer_id) as customers
                FROM transactions
                WHERE invoice_date >= ? AND invoice_date <= ?
                AND country IN ({','.join(['?']*len(countries))})
                AND customer_id IS NOT NULL
                GROUP BY country
                ORDER BY revenue DESC""",
            conn,
            params=(start_date, end_date + ' 23:59:59') + countries,
        )
    finally:
        conn.close()
    return df


def _json_default(value):
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    if hasattr(value, 'item'):
        return value.item()
    return str(value)


def forecast_baseline(actuals_df: pd.DataFrame, mode: str) -> tuple[float, str]:
    if mode == "Durchschnitt letzte 3 Monate" and len(actuals_df) >= 3:
        return actuals_df.tail(3)['y'].mean(), "Ø der letzten 3 vollständigen Ist-Monate"
    return actuals_df['y'].iloc[-1], "letzter vollständiger Ist-Monat"


def short_baseline_label(label: str) -> str:
    if label.startswith("Ø"):
        return "Ø letzte 3 Monate"
    return "Letzter Ist-Monat"
