# tests/test_data_processing.py
import pandas as pd
import sqlite3
import tempfile
import os
from src.data_processing import clean_dataframe, load_to_sqlite, get_connection

def make_raw_df():
    return pd.DataFrame({
        'Invoice': ['536365', '536366', 'C536367', '536368', '536369'],
        'StockCode': ['85123A', '85123B', '85123C', '85123D', '85123E'],
        'Description': ['A', 'B', 'C', 'D', 'E'],
        'Quantity': [6, -1, 3, 0, 2],
        'InvoiceDate': pd.to_datetime(['2009-12-01'] * 5),
        'Price': [2.55, 3.39, 2.75, 0.0, 4.20],
        'Customer ID': [17850.0, 17850.0, None, 13047.0, 13047.0],
        'Country': ['United Kingdom'] * 5
    })

def test_clean_removes_negative_quantity():
    df = clean_dataframe(make_raw_df())
    assert all(df['quantity'] > 0)

def test_clean_removes_null_customer():
    df = clean_dataframe(make_raw_df())
    assert df['customer_id'].notna().all()

def test_clean_removes_zero_price():
    df = clean_dataframe(make_raw_df())
    assert all(df['price'] > 0)

def test_clean_adds_revenue_column():
    df = clean_dataframe(make_raw_df())
    assert 'revenue' in df.columns
    assert (df['revenue'] == df['quantity'] * df['price']).all()

def test_clean_renames_columns():
    df = clean_dataframe(make_raw_df())
    assert 'customer_id' in df.columns
    assert 'stock_code' in df.columns

def test_load_to_sqlite_creates_table():
    df = clean_dataframe(make_raw_df())
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    try:
        load_to_sqlite(df, db_path)
        conn = sqlite3.connect(db_path)
        result = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        conn.close()
        assert result == len(df)
    finally:
        os.unlink(db_path)
