# BI Entscheidungsagent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an interactive Streamlit BI dashboard with a rule-based KI decision agent on top of the Online Retail II dataset (1M+ transactions), persisted in SQLite.

**Architecture:** Excel data is imported once into a SQLite database (`retail.db`). Python modules query SQLite via pandas, run RFM segmentation, Prophet forecasting, and product performance analysis. A rule-based decision agent combines all three outputs into prioritised management recommendations. Streamlit renders everything in a 5-tab dashboard.

**Tech Stack:** Python 3.10+, pandas, SQLite (stdlib), Streamlit, Plotly, Prophet, openpyxl, pytest

---

## File Map

| File | Responsibility |
|---|---|
| `src/data_processing.py` | Load Excel → clean → write SQLite `transactions` table |
| `src/rfm_analysis.py` | Query SQLite, compute R/F/M scores, return segmented DataFrame |
| `src/forecasting.py` | Query monthly revenue, fit Prophet, return forecast DataFrame |
| `src/product_analysis.py` | Query SQLite, return top/bottom/declining products |
| `src/decision_agent.py` | Combine RFM + forecast + product results, emit recommendations |
| `app.py` | Streamlit app — 5 tabs, calls all src modules |
| `tests/test_data_processing.py` | Unit tests for cleaning logic |
| `tests/test_rfm_analysis.py` | Unit tests for RFM scoring |
| `tests/test_product_analysis.py` | Unit tests for declining-product detection |
| `tests/test_decision_agent.py` | Unit tests for all three decision rules |
| `requirements.txt` | Pinned dependencies |
| `.gitignore` | Exclude data files and generated artefacts |
| `README.md` | Setup, run instructions, dataset download link |

---

## Task 1: Project Skeleton

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create `requirements.txt`**

```
streamlit==1.33.0
pandas==2.2.2
plotly==5.21.0
prophet==1.1.5
openpyxl==3.1.2
pytest==8.2.0
```

- [ ] **Step 2: Create `.gitignore`**

```
data/online_retail_II.xlsx
data/retail.db
__pycache__/
.pytest_cache/
*.pyc
.DS_Store
.superpowers/
```

- [ ] **Step 3: Create empty `src/__init__.py` and `tests/__init__.py`**

Both files are empty — they just mark the directories as Python packages.

- [ ] **Step 4: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages install without error. Prophet may take 1-2 minutes.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .gitignore src/__init__.py tests/__init__.py
git commit -m "feat: project skeleton with dependencies"
```

---

## Task 2: Data Processing — Excel → SQLite

**Files:**
- Create: `src/data_processing.py`
- Create: `tests/test_data_processing.py`

The Excel file has two sheets (`Year 2009-2010`, `Year 2010-2011`). We combine them, drop invalid rows, add a `revenue` column, and write to SQLite.

**Cleaning rules:**
- Drop rows where `Quantity <= 0` (returns/adjustments)
- Drop rows where `Price <= 0`
- Drop rows where `Customer ID` is null
- Add column: `revenue = Quantity * Price`
- Rename columns to snake_case: `invoice`, `stock_code`, `description`, `quantity`, `invoice_date`, `price`, `customer_id`, `country`, `revenue`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_data_processing.py -v
```

Expected: `ModuleNotFoundError` or `ImportError` — functions don't exist yet.

- [ ] **Step 3: Implement `src/data_processing.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_data_processing.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/data_processing.py tests/test_data_processing.py
git commit -m "feat: data processing — Excel cleaning and SQLite import"
```

---

## Task 3: RFM Analysis

**Files:**
- Create: `src/rfm_analysis.py`
- Create: `tests/test_rfm_analysis.py`

RFM segments customers by Recency (days since last purchase), Frequency (unique invoices), and Monetary (total revenue). Each dimension is scored 1–5 by quintile. Segments are assigned by score combinations.

**Segment rules:**

| Segment | Condition |
|---|---|
| Champions | r_score=5 AND f_score>=4 |
| Loyal | f_score>=3 AND r_score>=3 |
| At Risk | r_score<=2 AND f_score>=3 |
| Lost | r_score=1 AND f_score<=2 |
| New | r_score>=4 AND f_score=1 |
| Others | everything else |

- [ ] **Step 1: Write failing tests**

```python
# tests/test_rfm_analysis.py
import pandas as pd
import numpy as np
from src.rfm_analysis import compute_rfm, assign_segment

def make_rfm_df():
    return pd.DataFrame({
        'customer_id': ['1', '2', '3', '4', '5'],
        'recency':     [5,   90,  200, 365, 10],
        'frequency':   [20,  10,  8,   1,   1],
        'monetary':    [5000, 2000, 1500, 100, 50],
    })

def test_compute_rfm_returns_required_columns():
    # Build a minimal in-memory transactions DataFrame
    dates = pd.date_range('2010-01-01', periods=12, freq='ME')
    rows = []
    for i, d in enumerate(dates):
        rows.append({'customer_id': 'A', 'invoice': f'INV{i}', 'invoice_date': d, 'revenue': 100.0})
        rows.append({'customer_id': 'B', 'invoice': f'INV{i+100}', 'invoice_date': d, 'revenue': 50.0})
    df = pd.DataFrame(rows)
    rfm = compute_rfm(df)
    assert set(['customer_id', 'recency', 'frequency', 'monetary', 'r_score', 'f_score', 'm_score', 'segment']).issubset(rfm.columns)

def test_assign_segment_champions():
    row = pd.Series({'r_score': 5, 'f_score': 5, 'm_score': 5})
    assert assign_segment(row) == 'Champions'

def test_assign_segment_at_risk():
    row = pd.Series({'r_score': 2, 'f_score': 4, 'm_score': 3})
    assert assign_segment(row) == 'At Risk'

def test_assign_segment_lost():
    row = pd.Series({'r_score': 1, 'f_score': 1, 'm_score': 1})
    assert assign_segment(row) == 'Lost'

def test_assign_segment_new():
    row = pd.Series({'r_score': 5, 'f_score': 1, 'm_score': 2})
    assert assign_segment(row) == 'New'
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_rfm_analysis.py -v
```

Expected: `ImportError` — module doesn't exist.

- [ ] **Step 3: Implement `src/rfm_analysis.py`**

```python
import pandas as pd
import sqlite3
from src.data_processing import get_connection


def assign_segment(row: pd.Series) -> str:
    r, f = row['r_score'], row['f_score']
    if r == 5 and f >= 4:
        return 'Champions'
    if f >= 3 and r >= 3:
        return 'Loyal'
    if r <= 2 and f >= 3:
        return 'At Risk'
    if r == 1 and f <= 2:
        return 'Lost'
    if r >= 4 and f == 1:
        return 'New'
    return 'Others'


def compute_rfm(df: pd.DataFrame) -> pd.DataFrame:
    reference_date = df['invoice_date'].max() + pd.Timedelta(days=1)

    rfm = df.groupby('customer_id').agg(
        recency=('invoice_date', lambda x: (reference_date - x.max()).days),
        frequency=('invoice', 'nunique'),
        monetary=('revenue', 'sum'),
    ).reset_index()

    rfm['r_score'] = pd.qcut(rfm['recency'], q=5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm['f_score'] = pd.qcut(rfm['frequency'].rank(method='first'), q=5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm['m_score'] = pd.qcut(rfm['monetary'].rank(method='first'), q=5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm['segment'] = rfm.apply(assign_segment, axis=1)
    return rfm


def load_rfm(conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql(
        "SELECT customer_id, invoice, invoice_date, revenue FROM transactions",
        conn,
        parse_dates=['invoice_date'],
    )
    return compute_rfm(df)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_rfm_analysis.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/rfm_analysis.py tests/test_rfm_analysis.py
git commit -m "feat: RFM customer segmentation (Champions/Loyal/At Risk/Lost/New)"
```

---

## Task 4: Prophet Forecasting

**Files:**
- Create: `src/forecasting.py`

No unit tests for Prophet model accuracy — integration tests are enough here. We test that the output shape and columns are correct.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_forecasting.py
import pandas as pd
from src.forecasting import prepare_monthly_series, forecast_revenue

def make_monthly_series():
    dates = pd.date_range('2010-01-01', periods=24, freq='MS')
    return pd.DataFrame({'ds': dates, 'y': range(24)})

def test_forecast_returns_future_rows():
    series = make_monthly_series()
    result = forecast_revenue(series, periods=3)
    assert len(result) == 24 + 3

def test_forecast_has_required_columns():
    series = make_monthly_series()
    result = forecast_revenue(series, periods=3)
    assert {'ds', 'yhat', 'yhat_lower', 'yhat_upper'}.issubset(result.columns)

def test_forecast_future_dates_are_after_training():
    series = make_monthly_series()
    result = forecast_revenue(series, periods=3)
    last_train = series['ds'].max()
    future = result[result['ds'] > last_train]
    assert len(future) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_forecasting.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `src/forecasting.py`**

```python
import pandas as pd
import sqlite3
from prophet import Prophet


def prepare_monthly_series(conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql(
        "SELECT invoice_date, revenue FROM transactions",
        conn,
        parse_dates=['invoice_date'],
    )
    monthly = (
        df.set_index('invoice_date')
        .resample('MS')['revenue']
        .sum()
        .reset_index()
        .rename(columns={'invoice_date': 'ds', 'revenue': 'y'})
    )
    return monthly


def forecast_revenue(series: pd.DataFrame, periods: int = 3) -> pd.DataFrame:
    model = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
    model.fit(series)
    future = model.make_future_dataframe(periods=periods, freq='MS')
    forecast = model.predict(future)
    return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]


def load_forecast(conn: sqlite3.Connection, periods: int = 3) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (monthly_actuals, forecast_df)."""
    series = prepare_monthly_series(conn)
    forecast = forecast_revenue(series, periods=periods)
    return series, forecast
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_forecasting.py -v
```

Expected: all 3 tests PASS. Prophet fit may take 10–20 seconds.

- [ ] **Step 5: Commit**

```bash
git add src/forecasting.py tests/test_forecasting.py
git commit -m "feat: Prophet revenue forecasting with 3-month horizon"
```

---

## Task 5: Product Analysis

**Files:**
- Create: `src/product_analysis.py`
- Create: `tests/test_product_analysis.py`

Returns top 10 products by revenue, and products that have been declining for 3+ consecutive months.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_product_analysis.py
import pandas as pd
from src.product_analysis import get_top_products, get_declining_products

def make_monthly_product_df():
    # Product A: growing, Product B: declining 3 months, Product C: declining only 2 months
    rows = []
    for month in range(6):
        rows.append({'stock_code': 'A', 'description': 'Widget A', 'month': month, 'revenue': 100 + month * 10})
        rows.append({'stock_code': 'B', 'description': 'Widget B', 'month': month, 'revenue': 500 - month * 50})
        rows.append({'stock_code': 'C', 'description': 'Widget C', 'month': month, 'revenue': 200 if month < 4 else 150})
    return pd.DataFrame(rows)

def make_total_revenue_df():
    return pd.DataFrame({
        'stock_code': ['A', 'B', 'C', 'D'],
        'description': ['Widget A', 'Widget B', 'Widget C', 'Widget D'],
        'revenue': [5000, 3000, 2000, 1000],
    })

def test_top_products_returns_n_rows():
    df = make_total_revenue_df()
    result = get_top_products(df, n=3)
    assert len(result) == 3

def test_top_products_sorted_descending():
    df = make_total_revenue_df()
    result = get_top_products(df, n=4)
    assert result['revenue'].is_monotonic_decreasing

def test_declining_products_detects_3_month_decline():
    df = make_monthly_product_df()
    result = get_declining_products(df, months=3)
    assert 'B' in result['stock_code'].values

def test_declining_products_ignores_2_month_decline():
    df = make_monthly_product_df()
    result = get_declining_products(df, months=3)
    assert 'C' not in result['stock_code'].values
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_product_analysis.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `src/product_analysis.py`**

```python
import pandas as pd
import sqlite3


def get_top_products(total_df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    return total_df.nlargest(n, 'revenue').reset_index(drop=True)


def get_declining_products(monthly_df: pd.DataFrame, months: int = 3) -> pd.DataFrame:
    """Returns products where revenue declined in each of the last `months` months."""
    declining = []
    for code, group in monthly_df.groupby('stock_code'):
        recent = group.sort_values('month').tail(months + 1)
        revenues = recent['revenue'].tolist()
        if len(revenues) >= months + 1 and all(
            revenues[i] > revenues[i + 1] for i in range(len(revenues) - 1)
        ):
            declining.append({
                'stock_code': code,
                'description': group['description'].iloc[0],
                'revenue_last_month': revenues[-1],
            })
    return pd.DataFrame(declining)


def load_product_analysis(conn: sqlite3.Connection) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (top_products_df, declining_products_df)."""
    df = pd.read_sql(
        """
        SELECT stock_code, description,
               strftime('%Y-%m', invoice_date) AS month,
               SUM(revenue) AS revenue
        FROM transactions
        GROUP BY stock_code, description, month
        """,
        conn,
    )

    total = (
        df.groupby(['stock_code', 'description'])['revenue']
        .sum()
        .reset_index()
        .sort_values('revenue', ascending=False)
    )

    df['month_num'] = pd.to_datetime(df['month']).dt.to_period('M').apply(lambda x: x.ordinal)
    top = get_top_products(total)
    declining = get_declining_products(df)
    return top, declining
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_product_analysis.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/product_analysis.py tests/test_product_analysis.py
git commit -m "feat: product analysis — top 10 and declining products"
```

---

## Task 6: Decision Agent

**Files:**
- Create: `src/decision_agent.py`
- Create: `tests/test_decision_agent.py`

The agent applies three rules and returns a list of recommendation dicts, each with `priority`, `finding`, `decision`, and `reasoning`.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_decision_agent.py
import pandas as pd
from src.decision_agent import generate_recommendations

def make_forecast_decline():
    return pd.DataFrame({
        'ds': pd.date_range('2010-01-01', periods=5, freq='MS'),
        'yhat': [1000, 1000, 1000, 1000, 850],  # last value = forecast, -15%
    })

def make_forecast_stable():
    return pd.DataFrame({
        'ds': pd.date_range('2010-01-01', periods=5, freq='MS'),
        'yhat': [1000, 1000, 1000, 1000, 1050],  # +5%
    })

def make_rfm_high_at_risk():
    segments = ['At Risk'] * 25 + ['Champions'] * 75
    return pd.DataFrame({'segment': segments})

def make_rfm_low_at_risk():
    segments = ['At Risk'] * 5 + ['Champions'] * 95
    return pd.DataFrame({'segment': segments})

def make_declining_products():
    return pd.DataFrame({'stock_code': ['X'], 'description': ['Bad Product'], 'revenue_last_month': [10.0]})

def make_no_declining():
    return pd.DataFrame(columns=['stock_code', 'description', 'revenue_last_month'])

def test_rule1_triggers_on_decline_with_at_risk():
    recs = generate_recommendations(make_forecast_decline(), make_rfm_high_at_risk(), make_no_declining())
    priorities = [r['priority'] for r in recs]
    assert 'HOCH' in priorities

def test_rule1_does_not_trigger_on_stable_forecast():
    recs = generate_recommendations(make_forecast_stable(), make_rfm_low_at_risk(), make_no_declining())
    priorities = [r['priority'] for r in recs]
    assert 'HOCH' not in priorities

def test_rule2_triggers_on_declining_products():
    recs = generate_recommendations(make_forecast_stable(), make_rfm_low_at_risk(), make_declining_products())
    decisions = [r['decision'] for r in recs]
    assert any('Sortiment' in d for d in decisions)

def test_recommendation_has_required_keys():
    recs = generate_recommendations(make_forecast_decline(), make_rfm_high_at_risk(), make_declining_products())
    for r in recs:
        assert {'priority', 'finding', 'decision', 'reasoning'}.issubset(r.keys())
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_decision_agent.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `src/decision_agent.py`**

```python
import pandas as pd


def generate_recommendations(
    forecast_df: pd.DataFrame,
    rfm_df: pd.DataFrame,
    declining_df: pd.DataFrame,
) -> list[dict]:
    recommendations = []

    # Rule 1: Forecast decline + elevated At-Risk share
    actuals = forecast_df.iloc[:-3] if len(forecast_df) > 3 else forecast_df
    last_actual = actuals['yhat'].iloc[-1]
    next_forecast = forecast_df['yhat'].iloc[-3]
    pct_change = (next_forecast - last_actual) / last_actual if last_actual > 0 else 0

    at_risk_share = (rfm_df['segment'] == 'At Risk').sum() / len(rfm_df) if len(rfm_df) > 0 else 0

    if pct_change < -0.05 and at_risk_share > 0.20:
        at_risk_count = (rfm_df['segment'] == 'At Risk').sum()
        recommendations.append({
            'priority': 'HOCH',
            'finding': f'Umsatz-Forecast zeigt {pct_change:.1%} Rückgang nächsten Monat.',
            'decision': 'Reaktivierungskampagne für At-Risk-Kunden starten.',
            'reasoning': (
                f'{at_risk_count} Kunden ({at_risk_share:.1%} des Kundenstamms) '
                f'im Segment "At Risk" — kombiniert mit sinkendem Forecast erhöht sich Abwanderungsrisiko.'
            ),
        })

    # Rule 2: Declining products
    if len(declining_df) > 0:
        product_list = ', '.join(declining_df['description'].head(5).tolist())
        recommendations.append({
            'priority': 'MITTEL',
            'finding': f'{len(declining_df)} Produkte zeigen ≥3 Monate rückläufigen Umsatz.',
            'decision': 'Sortiment bereinigen: betroffene Produkte prüfen und ggf. absetzen.',
            'reasoning': f'Betroffene Produkte: {product_list}.',
        })

    # Rule 3: No action needed
    if not recommendations:
        champion_share = (rfm_df['segment'] == 'Champions').sum() / len(rfm_df) if len(rfm_df) > 0 else 0
        recommendations.append({
            'priority': 'TIEF',
            'finding': f'Forecast stabil ({pct_change:+.1%}). Champion-Anteil: {champion_share:.1%}.',
            'decision': 'Kein unmittelbarer Handlungsbedarf.',
            'reasoning': 'Alle KPIs im grünen Bereich. Reguläre Erfolgskontrolle genügt.',
        })

    return recommendations
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_decision_agent.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/decision_agent.py tests/test_decision_agent.py
git commit -m "feat: rule-based KI decision agent (3 rules, prioritised recommendations)"
```

---

## Task 7: Streamlit App — Skeleton + Tab 1 (Übersicht)

**Files:**
- Create: `app.py`

All data is loaded once at startup via `@st.cache_data` to avoid recomputation on every interaction.

- [ ] **Step 1: Create `app.py` skeleton with data loading and Tab 1**

```python
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from src.data_processing import build_database, get_connection
from src.rfm_analysis import load_rfm
from src.forecasting import load_forecast
from src.product_analysis import load_product_analysis
from src.decision_agent import generate_recommendations

st.set_page_config(page_title="RetailBI — Entscheidungsagent", layout="wide")

build_database()  # no-op if DB already exists

@st.cache_data
def load_all():
    conn = get_connection()
    rfm = load_rfm(conn)
    actuals, forecast = load_forecast(conn)
    top_products, declining = load_product_analysis(conn)
    conn.close()
    recs = generate_recommendations(forecast, rfm, declining)
    return rfm, actuals, forecast, top_products, declining, recs

rfm, actuals, forecast, top_products, declining, recs = load_all()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Übersicht", "📈 Forecast", "👥 Kunden RFM", "📦 Produkte", "🤖 KI-Entscheid"
])

# ── Tab 1: Executive Overview ────────────────────────────────────────────────
with tab1:
    st.title("Online Retail — Business Intelligence Dashboard")
    st.caption("Datenquelle: Online Retail II (UCI ML Repository, 2009–2011)")

    # KPI row
    total_revenue = actuals['y'].sum()
    total_customers = rfm['customer_id'].nunique()
    at_risk_count = (rfm['segment'] == 'At Risk').sum()

    last_actual = actuals['y'].iloc[-1]
    next_forecast = forecast[forecast['ds'] > actuals['ds'].max()]['yhat'].iloc[0]
    forecast_delta = (next_forecast - last_actual) / last_actual

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Gesamtumsatz", f"£{total_revenue:,.0f}")
    col2.metric("Aktive Kunden", f"{total_customers:,}")
    col3.metric("At-Risk Kunden", f"{at_risk_count:,}")
    col4.metric("Forecast nächster Monat", f"£{next_forecast:,.0f}", f"{forecast_delta:+.1%}")

    st.divider()
    col_left, col_mid, col_right = st.columns(3)

    with col_left:
        st.subheader("Umsatz Trend")
        fig = px.bar(actuals.tail(12), x='ds', y='y', labels={'ds': '', 'y': 'Umsatz (£)'})
        fig.update_layout(height=220, margin=dict(t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with col_mid:
        st.subheader("Kundensegmente")
        seg_counts = rfm['segment'].value_counts().reset_index()
        seg_counts.columns = ['Segment', 'Anzahl']
        color_map = {'Champions': '#4ade80', 'Loyal': '#60a5fa', 'At Risk': '#f59e0b',
                     'Lost': '#ef4444', 'New': '#a78bfa', 'Others': '#94a3b8'}
        fig2 = px.bar(seg_counts, x='Anzahl', y='Segment', orientation='h',
                      color='Segment', color_discrete_map=color_map)
        fig2.update_layout(height=220, margin=dict(t=0, b=0), showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    with col_right:
        st.subheader("KI-Empfehlung")
        top_rec = recs[0]
        priority_color = {'HOCH': '🔴', 'MITTEL': '🟡', 'TIEF': '🟢'}
        icon = priority_color.get(top_rec['priority'], '⚪')
        st.markdown(f"**{icon} Priorität: {top_rec['priority']}**")
        st.markdown(f"_{top_rec['finding']}_")
        st.markdown(f"**→ {top_rec['decision']}**")
        st.caption("Details auf Tab 🤖 KI-Entscheid")
```

- [ ] **Step 2: Run the app to verify Tab 1 works**

```bash
streamlit run app.py
```

Open `http://localhost:8501`. Verify: 4 KPI tiles, trend bar chart, segment bar chart, KI-alert box all appear. No errors in terminal.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: Streamlit app skeleton + Tab 1 executive overview"
```

---

## Task 8: Tab 2 — Umsatz-Forecast

**Files:**
- Modify: `app.py` (Tab 2 section)

- [ ] **Step 1: Add Tab 2 content to `app.py`**

Find the line `# ── Tab 1` and add after the Tab 1 block:

```python
# ── Tab 2: Forecast ──────────────────────────────────────────────────────────
with tab2:
    st.title("Umsatz-Forecast")
    st.caption("Historischer Monatsumsatz + Prophet-Prognose (3 Monate)")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=actuals['ds'], y=actuals['y'],
        mode='lines+markers', name='Tatsächlicher Umsatz',
        line=dict(color='#60a5fa', width=2)
    ))
    future_forecast = forecast[forecast['ds'] > actuals['ds'].max()]
    fig.add_trace(go.Scatter(
        x=future_forecast['ds'], y=future_forecast['yhat'],
        mode='lines+markers', name='Forecast',
        line=dict(color='#a78bfa', width=2, dash='dash')
    ))
    fig.add_trace(go.Scatter(
        x=pd.concat([future_forecast['ds'], future_forecast['ds'].iloc[::-1]]),
        y=pd.concat([future_forecast['yhat_upper'], future_forecast['yhat_lower'].iloc[::-1]]),
        fill='toself', fillcolor='rgba(167,139,250,0.15)',
        line=dict(color='rgba(255,255,255,0)'),
        name='Konfidenzintervall'
    ))
    fig.update_layout(height=400, xaxis_title='Monat', yaxis_title='Umsatz (£)',
                      legend=dict(orientation='h', yanchor='bottom', y=1.02))
    st.plotly_chart(fig, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    for i, row in enumerate(future_forecast.itertuples()):
        [col1, col2, col3][i].metric(
            row.ds.strftime('%b %Y'),
            f"£{row.yhat:,.0f}",
            f"£{row.yhat_lower:,.0f} – £{row.yhat_upper:,.0f}"
        )
```

- [ ] **Step 2: Verify in browser**

```bash
streamlit run app.py
```

Click Tab 2. Verify: historical line + forecast dash line + confidence band + 3 future metric tiles.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: Tab 2 — Prophet forecast chart with confidence interval"
```

---

## Task 9: Tab 3 — Kunden RFM

**Files:**
- Modify: `app.py` (Tab 3 section)

- [ ] **Step 1: Add Tab 3 content to `app.py`**

```python
# ── Tab 3: Kunden RFM ────────────────────────────────────────────────────────
with tab3:
    st.title("Kundensegmentierung — RFM-Analyse")
    st.caption("Recency · Frequency · Monetary | Segmente basierend auf Quintil-Scores")

    color_map = {'Champions': '#4ade80', 'Loyal': '#60a5fa', 'At Risk': '#f59e0b',
                 'Lost': '#ef4444', 'New': '#a78bfa', 'Others': '#94a3b8'}

    col_scatter, col_table = st.columns([2, 1])

    with col_scatter:
        fig = px.scatter(
            rfm, x='recency', y='frequency', size='monetary',
            color='segment', color_discrete_map=color_map,
            hover_data=['customer_id', 'monetary'],
            labels={'recency': 'Recency (Tage)', 'frequency': 'Frequency (Bestellungen)'},
            title='RFM Scatter — Recency vs. Frequency (Grösse = Monetary)'
        )
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)

    with col_table:
        st.subheader("Segmente Übersicht")
        summary = (
            rfm.groupby('segment')
            .agg(Kunden=('customer_id', 'count'), Umsatz=('monetary', 'sum'))
            .reset_index()
            .sort_values('Umsatz', ascending=False)
        )
        summary['Umsatz'] = summary['Umsatz'].map('£{:,.0f}'.format)
        st.dataframe(summary, use_container_width=True, hide_index=True)

        st.subheader("At-Risk Kunden")
        at_risk = rfm[rfm['segment'] == 'At Risk'][['customer_id', 'recency', 'frequency', 'monetary']].head(10)
        at_risk['monetary'] = at_risk['monetary'].map('£{:,.0f}'.format)
        st.dataframe(at_risk, use_container_width=True, hide_index=True)
```

- [ ] **Step 2: Verify in browser**

```bash
streamlit run app.py
```

Click Tab 3. Verify: scatter plot with coloured segments, summary table, At-Risk customer list.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: Tab 3 — RFM scatter plot and segment summary"
```

---

## Task 10: Tab 4 — Produkt-Performance

**Files:**
- Modify: `app.py` (Tab 4 section)

- [ ] **Step 1: Add Tab 4 content to `app.py`**

```python
# ── Tab 4: Produkt-Performance ───────────────────────────────────────────────
with tab4:
    st.title("Produkt-Performance")
    st.caption("Top-Produkte nach Umsatz · Rückläufige Produkte (≥3 Monate)")

    col_top, col_decline = st.columns(2)

    with col_top:
        st.subheader("Top 10 Produkte")
        fig = px.bar(
            top_products, x='revenue', y='description',
            orientation='h',
            labels={'revenue': 'Umsatz (£)', 'description': ''},
            color='revenue', color_continuous_scale='Blues'
        )
        fig.update_layout(height=380, coloraxis_showscale=False, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

    with col_decline:
        st.subheader(f"Rückläufige Produkte ({len(declining)})")
        if len(declining) == 0:
            st.success("Keine Produkte mit ≥3 Monaten rückläufigem Umsatz.")
        else:
            st.warning(f"{len(declining)} Produkte zeigen anhaltenden Umsatzrückgang.")
            declining_display = declining.copy()
            declining_display['revenue_last_month'] = declining_display['revenue_last_month'].map('£{:,.0f}'.format)
            declining_display.columns = ['Stock Code', 'Bezeichnung', 'Umsatz (letzter Monat)']
            st.dataframe(declining_display, use_container_width=True, hide_index=True)
```

- [ ] **Step 2: Verify in browser**

```bash
streamlit run app.py
```

Click Tab 4. Verify: horizontal bar chart with top 10, declining products table or success message.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: Tab 4 — product performance with top 10 and declining products"
```

---

## Task 11: Tab 5 — KI-Entscheid

**Files:**
- Modify: `app.py` (Tab 5 section)

- [ ] **Step 1: Add Tab 5 content to `app.py`**

```python
# ── Tab 5: KI-Entscheid ──────────────────────────────────────────────────────
with tab5:
    st.title("KI-Entscheidungsagent")
    st.caption("Regelbasierter Agent — kombiniert Forecast, RFM und Produktanalyse")

    priority_config = {
        'HOCH':   {'icon': '🔴', 'color': '#ef4444', 'bg': '#2d1515'},
        'MITTEL': {'icon': '🟡', 'color': '#f59e0b', 'bg': '#2d2410'},
        'TIEF':   {'icon': '🟢', 'color': '#4ade80', 'bg': '#152d1d'},
    }

    for rec in recs:
        cfg = priority_config.get(rec['priority'], {'icon': '⚪', 'color': '#94a3b8', 'bg': '#1e293b'})
        st.markdown(
            f"""
            <div style="background:{cfg['bg']};border-left:4px solid {cfg['color']};
                        padding:16px 20px;border-radius:8px;margin-bottom:16px;">
                <div style="font-size:18px;font-weight:700;color:{cfg['color']};margin-bottom:8px;">
                    {cfg['icon']} Priorität: {rec['priority']}
                </div>
                <div style="font-size:15px;color:#e2e8f0;margin-bottom:8px;">
                    <strong>Befund:</strong> {rec['finding']}
                </div>
                <div style="font-size:15px;color:#e2e8f0;margin-bottom:8px;">
                    <strong>Entscheid:</strong> {rec['decision']}
                </div>
                <div style="font-size:13px;color:#94a3b8;">
                    <strong>Begründung:</strong> {rec['reasoning']}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.divider()
    st.subheader("Entscheidungslogik")
    st.markdown("""
    | Regel | Bedingung | Entscheid | Priorität |
    |---|---|---|---|
    | 1 | Forecast < –5% UND At-Risk > 20% | Reaktivierungskampagne | HOCH |
    | 2 | ≥1 Produkt mit 3+ Monaten Rückgang | Sortiment bereinigen | MITTEL |
    | 3 | Keine der obigen Regeln | Kein Handlungsbedarf | TIEF |
    """)
```

- [ ] **Step 2: Verify in browser**

```bash
streamlit run app.py
```

Click Tab 5. Verify: coloured recommendation cards with Befund/Entscheid/Begründung, decision logic table below.

- [ ] **Step 3: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: Tab 5 — KI decision agent recommendations display"
```

---

## Task 12: README + GitHub Push

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create `README.md`**

```markdown
# BI Entscheidungsagent — Online Retail II

Interaktives Business-Intelligence-Dashboard mit regelbasiertem KI-Entscheidungsagenten.
Gebaut im Rahmen des Kurses Business Intelligence (Sheyla Sampietro, 2026).

## Live Demo

`streamlit run app.py` → öffne http://localhost:8501

## Dataset

Lade `online_retail_II.xlsx` von https://archive.ics.uci.edu/dataset/502/online+retail+ii
und lege die Datei in den Ordner `data/`.

## Setup

```bash
pip install -r requirements.txt
# Excel in data/ ablegen, dann:
streamlit run app.py
# Die SQLite-Datenbank (data/retail.db) wird automatisch beim ersten Start erstellt.
```

## Tests

```bash
pytest tests/ -v
```

## Technologie-Entscheide

### Python + Streamlit statt R + Shiny
Obwohl der Kurs R/Shiny eingeführt hat, wurde Python + Streamlit gewählt, weil:
- Die KI-Bibliotheken (Prophet, scikit-learn) Python-nativ sind
- Die gesamte Pipeline einheitlich in einer Sprache läuft
- Streamlit eine flachere Lernkurve als Shiny hat
- Week 08 des Kurses Python bereits verwendete (Prophet-Guide, SimpleAutoencoder.py)

### SQLite statt MySQL
Der Kurs verwendete MySQL. Für dieses Projekt wurde SQLite gewählt, weil:
- Kein Datenbankserver nötig — funktioniert sofort nach `git clone`
- Die `.db`-Datei wird automatisch beim ersten Start erzeugt
- Für ein Read-only BI-Dashboard ist SQLite vollständig ausreichend

## Architektur

```
Excel → SQLite (retail.db) → Pandas → Prophet / RFM / Produktanalyse → KI-Agent → Streamlit
```

## Dashboard-Struktur

| Tab | Inhalt |
|---|---|
| 📊 Übersicht | KPIs, Trendchart, Segmente, KI-Alert |
| 📈 Forecast | Prophet-Zeitreihe + 3-Monats-Prognose |
| 👥 Kunden RFM | Segmentierung, Scatter Plot, At-Risk-Liste |
| 📦 Produkte | Top 10, rückläufige Produkte |
| 🤖 KI-Entscheid | Strukturierte Empfehlungen mit Priorität |
```

- [ ] **Step 2: Create GitHub repository and push**

```bash
git add README.md
git commit -m "docs: README with setup, tech decisions, architecture"

# On GitHub: create new repo "entscheidungsagent-bi" (public), then:
git remote add origin https://github.com/<your-username>/entscheidungsagent-bi.git
git push -u origin main
```

- [ ] **Step 3: Verify on GitHub**

Open the GitHub repo URL. Verify: README renders correctly, all source files are visible, `data/` folder is empty (gitignored), commit history is clean.

---

## Final Verification

- [ ] Run all tests: `pytest tests/ -v` → all PASS
- [ ] Run the app: `streamlit run app.py` → all 5 tabs load without errors
- [ ] Check Tab 1: 4 KPI tiles, 2 mini-charts, KI-alert visible
- [ ] Check Tab 2: forecast line + confidence band + 3 future metric tiles
- [ ] Check Tab 3: RFM scatter plot coloured by segment, summary table
- [ ] Check Tab 4: top 10 bar chart, declining products table
- [ ] Check Tab 5: recommendation cards with priority colours, logic table
- [ ] GitHub: repo public, README renders, no Excel/DB files committed
