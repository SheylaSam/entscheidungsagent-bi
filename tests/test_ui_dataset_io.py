"""Tests for dataset upload helpers."""
import pandas as pd
import pytest

from src.ui import dataset_io


_RAW_COLS = ('Invoice', 'StockCode', 'Description', 'Quantity',
             'InvoiceDate', 'Price', 'Customer ID', 'Country')


def _sample_raw_df() -> pd.DataFrame:
    return pd.DataFrame({
        'Invoice':     ['001'],
        'StockCode':   ['ABC'],
        'Description': ['Widget'],
        'Quantity':    [2],
        'InvoiceDate': ['2010-01-01 12:00:00'],
        'Price':       [9.99],
        'Customer ID': [12345],
        'Country':     ['United Kingdom'],
    })


def test_expected_columns_constant():
    assert isinstance(dataset_io.EXPECTED_RAW_COLUMNS, tuple)
    assert set(dataset_io.EXPECTED_RAW_COLUMNS) == set(_RAW_COLS)


def test_validate_uploaded_dataframe_happy_path():
    ok, errors = dataset_io.validate_uploaded_dataframe(_sample_raw_df())
    assert ok is True
    assert errors == []


def test_validate_uploaded_dataframe_missing_columns():
    df = _sample_raw_df().drop(columns=['Customer ID', 'Country'])
    ok, errors = dataset_io.validate_uploaded_dataframe(df)
    assert ok is False
    assert any("Customer ID" in e for e in errors)
    assert any("Country" in e for e in errors)


def test_validate_uploaded_dataframe_empty():
    ok, errors = dataset_io.validate_uploaded_dataframe(pd.DataFrame())
    assert ok is False
    assert any("leer" in e.lower() or "empty" in e.lower() for e in errors)


def test_replace_database_from_dataframe(tmp_path):
    """End-to-end: a sample raw frame turns into a populated SQLite DB."""
    db_path = tmp_path / "out.db"
    df = _sample_raw_df()
    df['Quantity'] = [3]
    df['Price'] = [10.0]
    dataset_io.replace_database_from_dataframe(df, db_path=db_path)

    import sqlite3
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT customer_id, revenue FROM transactions").fetchall()
    finally:
        conn.close()
    assert rows == [("12345", 30.0)]
