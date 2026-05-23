import io
import sqlite3
import zipfile
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

DB_PATH = Path("data/retail.db")
EXCEL_PATH = Path("data/online_retail_II.xlsx")

UCI_URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"


def fetch_uci_dataset(
    excel_path: str | Path = EXCEL_PATH,
    *,
    url: str = UCI_URL,
) -> None:
    """Download the Online Retail II dataset from UCI if not present.

    No-op when ``excel_path`` already exists.  Otherwise downloads the
    canonical zip, extracts the first ``.xlsx`` entry, and writes it to
    ``excel_path``.  Network errors propagate so callers can surface a
    clear "no internet?" message.
    """
    target = Path(excel_path)
    if target.exists():
        return

    target.parent.mkdir(parents=True, exist_ok=True)

    with urlopen(url, timeout=60) as response:  # noqa: S310
        data = response.read()

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        xlsx_names = [n for n in zf.namelist() if n.lower().endswith(".xlsx")]
        if not xlsx_names:
            raise RuntimeError(
                f"UCI zip at {url} did not contain an .xlsx file "
                f"(got {zf.namelist()!r})"
            )
        with zf.open(xlsx_names[0]) as src, target.open("wb") as dst:
            dst.write(src.read())

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
    try:
        df.to_sql('transactions', conn, if_exists='replace', index=False)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON transactions(invoice_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_country ON transactions(country)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_date_country ON transactions(invoice_date, country)")
        conn.commit()
    finally:
        conn.close()


def get_connection(db_path: str | Path = DB_PATH) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


def country_filter_clause(countries: tuple) -> tuple[str, tuple]:
    """Return (sql_fragment, params) for filtering transactions by country.

    Empty tuple → empty fragment, so callers can safely default to "no country
    filter" without producing the invalid SQL ``country IN ()``.
    """
    if not countries:
        return "", ()
    placeholders = ",".join("?" for _ in countries)
    return f" AND country IN ({placeholders})", countries


def date_range_params(start_date: str, end_date: str) -> tuple[str, str]:
    """Return (start, exclusive_end) for ``invoice_date >= ? AND invoice_date < ?``.

    Replaces the string concat ``end_date + ' 23:59:59'`` with a proper
    next-day upper bound, which also keeps the full end_date inclusive.
    """
    end_exclusive = (pd.Timestamp(end_date) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    return start_date, end_exclusive


def build_database(excel_path: str | Path = EXCEL_PATH, db_path: str | Path = DB_PATH) -> None:
    """Import Excel → SQLite. Skips if DB already exists.

    Auto-downloads the Excel from the UCI ML Repository when missing.
    """
    if Path(db_path).exists():
        return
    fetch_uci_dataset(excel_path=excel_path)
    sheets = pd.read_excel(excel_path, sheet_name=None)
    combined = pd.concat(sheets.values(), ignore_index=True)
    clean = clean_dataframe(combined)
    load_to_sqlite(clean, db_path)
