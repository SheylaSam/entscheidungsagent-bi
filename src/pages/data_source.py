"""Page: Datenquelle.

Read-only overview of the SQLite database that backs the dashboard
plus a rebuild button.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data_processing import DB_PATH, build_database, get_connection
from src.ui.cards import kpi_card
from src.ui.dataset_io import validate_uploaded_dataframe, replace_database_from_dataframe


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

    # ── Standard-Datensatz ───────────────────────────────────────────────
    st.subheader("Standard-Datensatz", anchor=False)
    st.markdown(
        "Online Retail II vom UCI ML Repository (~45 MB). "
        "Wird beim ersten App-Start automatisch heruntergeladen."
    )
    col_a, col_b = st.columns([1, 3])
    with col_a:
        if st.button("Neu laden",
                     help="Löscht die lokale DB und lädt das Original "
                          "neu von der UCI-Quelle."):
            from src.data_processing import EXCEL_PATH
            DB_PATH.unlink(missing_ok=True)
            EXCEL_PATH.unlink(missing_ok=True)
            with st.spinner("Lade Datensatz von UCI…"):
                try:
                    build_database()
                except Exception as exc:                       # noqa: BLE001
                    st.error(f"Download fehlgeschlagen: {exc}")
                else:
                    st.cache_data.clear()
                    st.success("Standard-Datensatz neu geladen.")
                    st.rerun()
    with col_b:
        st.caption("Setzt die aktive Datenbank auf den Stand 2009–2011 zurück.")

    # ── Eigener Datensatz ────────────────────────────────────────────────
    st.subheader("Eigener Datensatz", anchor=False)
    st.markdown(
        "Lade eine Excel-Datei (`.xlsx`) im Online-Retail-II-Schema hoch. "
        "Erwartete Spalten: `Invoice, StockCode, Description, Quantity, "
        "InvoiceDate, Price, Customer ID, Country` — auf einem oder "
        "mehreren Tabellenblättern."
    )
    uploaded = st.file_uploader(
        "Datei wählen",
        type=["xlsx"],
        accept_multiple_files=False,
        key="data_source_upload",
    )
    if uploaded is not None:
        try:
            sheets = pd.read_excel(uploaded, sheet_name=None)
            combined = pd.concat(sheets.values(), ignore_index=True)
        except Exception as exc:                              # noqa: BLE001
            st.error(f"Konnte Datei nicht lesen: {exc}")
            return

        ok, errors = validate_uploaded_dataframe(combined)
        if not ok:
            for err in errors:
                st.error(err)
            return

        st.success(
            f"Schema OK — {len(combined):,} Zeilen, "
            f"{combined['Country'].nunique()} Länder."
        )
        st.markdown("**Vorschau (erste 5 Zeilen):**")
        st.dataframe(combined.head(), use_container_width=True, hide_index=True)

        if st.button("Datenbank ersetzen",
                     type="primary",
                     help="Achtung: ersetzt die aktive Datenbank. "
                          "Du kannst jederzeit zurück zum Standard wechseln."):
            with st.spinner("Schreibe neue Datenbank…"):
                replace_database_from_dataframe(combined)
            st.cache_data.clear()
            st.success("Eigener Datensatz aktiv. Lade die anderen Seiten neu.")
            st.rerun()
