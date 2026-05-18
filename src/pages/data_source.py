"""Page: Datenquelle.

Read-only overview of the SQLite database that backs the dashboard
plus a rebuild button.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data_processing import DB_PATH, build_database, get_connection
from src.ui.cards import kpi_card


def render(filters: dict) -> None:
    st.title("Datenquelle")
    st.caption(
        "Online Retail II (UCI ML Repository) · 2009–2011 · "
        "SQLite-Snapshot lokal, kein Live-Feed."
    )

    db_exists = DB_PATH.exists()
    db_size_mb: float | None = None
    n_rows = 0
    n_customers = 0
    min_date = max_date = None

    if db_exists:
        db_size_mb = DB_PATH.stat().st_size / (1024 * 1024)
        conn = get_connection()
        n_rows = pd.read_sql("SELECT COUNT(*) AS n FROM transactions", conn)["n"].iloc[0]
        n_customers = pd.read_sql(
            "SELECT COUNT(DISTINCT customer_id) AS n FROM transactions "
            "WHERE customer_id IS NOT NULL",
            conn,
        )["n"].iloc[0]
        bounds = pd.read_sql(
            "SELECT MIN(invoice_date) AS mn, MAX(invoice_date) AS mx FROM transactions",
            conn,
        )
        min_date = bounds["mn"].iloc[0]
        max_date = bounds["mx"].iloc[0]

    # ── Status row ────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        kpi_card(
            label="Status",
            value=("OK" if db_exists else "FEHLT"),
            value_format="{}",
            delta_pct=None, delta_period="", higher_is_better=True,
            sparkline=None,
            tooltip=f"SQLite-Datei: {DB_PATH}",
        )
    with c2:
        kpi_card(
            label="Transaktionen",
            value=int(n_rows) if db_exists else None,
            value_format="{:,.0f}",
            delta_pct=None, delta_period="", higher_is_better=True,
            sparkline=None,
        )
    with c3:
        kpi_card(
            label="Distinct Kunden",
            value=int(n_customers) if db_exists else None,
            value_format="{:,.0f}",
            delta_pct=None, delta_period="", higher_is_better=True,
            sparkline=None,
        )
    with c4:
        kpi_card(
            label="Dateigrösse",
            value=db_size_mb if db_size_mb is not None else None,
            value_format="{:.1f} MB",
            delta_pct=None, delta_period="", higher_is_better=True,
            sparkline=None,
        )

    # ── Date range + path ─────────────────────────────────────────────────
    st.subheader("Zeitraum", anchor=False)
    if db_exists and min_date and max_date:
        st.markdown(
            f"**Erste Transaktion:** {min_date}  \n"
            f"**Letzte Transaktion:** {max_date}"
        )
    else:
        st.warning("Datenbank fehlt — bitte unten neu aufbauen.")

    st.subheader("Speicherort", anchor=False)
    st.code(str(DB_PATH.resolve()))

    # ── Rebuild action ────────────────────────────────────────────────────
    st.subheader("Aktionen", anchor=False)
    if st.button("Datenbank neu aufbauen",
                 help="Liest die Excel-Quelle erneut und schreibt SQLite "
                      "neu (~30–90 Sekunden beim ersten Mal)."):
        with st.spinner("Importiere Daten…"):
            build_database()
        st.success("Datenbank wurde neu aufgebaut.")
        st.rerun()
