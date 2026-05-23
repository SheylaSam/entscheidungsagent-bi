"""Helpers for uploading and replacing the active dataset.

The dashboard expects the Online-Retail-II raw schema:
``Invoice, StockCode, Description, Quantity, InvoiceDate, Price,
Customer ID, Country``.  An uploaded dataframe must match that schema
before it's accepted — the cleaning + RFM + forecast logic downstream
assumes those columns.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data_processing import (
    DB_PATH,
    clean_dataframe,
    load_to_sqlite,
)


EXPECTED_RAW_COLUMNS: tuple[str, ...] = (
    "Invoice", "StockCode", "Description", "Quantity",
    "InvoiceDate", "Price", "Customer ID", "Country",
)


def validate_uploaded_dataframe(
    df: pd.DataFrame,
) -> tuple[bool, list[str]]:
    """Check that ``df`` has the Online-Retail-II raw schema.

    Returns ``(ok, errors)``.  ``errors`` is a list of human-readable
    German strings (the upload UI surfaces them as ``st.error`` rows).
    """
    errors: list[str] = []
    if df is None or len(df) == 0:
        errors.append("Datei ist leer.")
        return False, errors

    missing = [c for c in EXPECTED_RAW_COLUMNS if c not in df.columns]
    if missing:
        errors.append(
            "Fehlende Spalten: " + ", ".join(missing) +
            ". Erwartet werden die Original-Spalten des "
            "Online-Retail-II-Datensatzes."
        )
    return (not errors), errors


def replace_database_from_dataframe(
    df: pd.DataFrame,
    *,
    db_path: str | Path = DB_PATH,
) -> None:
    """Clean ``df`` and write it as the new SQLite database.

    Removes ``db_path`` if it exists, then re-creates it.  Caller is
    responsible for invalidating Streamlit's data cache afterwards
    (``st.cache_data.clear()``).
    """
    cleaned = clean_dataframe(df)
    target = Path(db_path)
    if target.exists():
        target.unlink()
    load_to_sqlite(cleaned, target)
