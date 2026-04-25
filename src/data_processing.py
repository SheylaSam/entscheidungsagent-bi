import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path("data/retail.db")
EXCEL_PATH = Path("data/online_retail_II.xlsx")

COLUMN_MAP = {
    'Invoice': 'invoice',
    'StockCode': 'stock_code',
    'Description': 'description',
    'Quantity': 'quantity',
    'InvoiceDate': 'invoice_date',
    'Price': 'price',
    'Customer ID': 'customer_id',
    'Country': 'country',
}


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=COLUMN_MAP)
    df = df[df['quantity'] > 0]
    df = df[df['price'] > 0]
    df = df[df['customer_id'].notna()]
    df['customer_id'] = df['customer_id'].astype(str).str.split('.').str[0]
    df['revenue'] = df['quantity'] * df['price']
    df['invoice_date'] = pd.to_datetime(df['invoice_date'])
    return df.reset_index(drop=True)


def load_to_sqlite(df: pd.DataFrame, db_path: str | Path = DB_PATH) -> None:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    df.to_sql('transactions', conn, if_exists='replace', index=False)
    conn.close()


def get_connection(db_path: str | Path = DB_PATH) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


def build_database(excel_path: str | Path = EXCEL_PATH, db_path: str | Path = DB_PATH) -> None:
    """Import Excel → SQLite. Skips if DB already exists."""
    if Path(db_path).exists():
        return
    sheets = pd.read_excel(excel_path, sheet_name=None)
    combined = pd.concat(sheets.values(), ignore_index=True)
    clean = clean_dataframe(combined)
    load_to_sqlite(clean, db_path)
