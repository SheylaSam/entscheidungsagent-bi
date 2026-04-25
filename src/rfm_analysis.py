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


def _qscore(series: pd.Series, ascending: bool = True, q: int = 5) -> pd.Series:
    """Assign quintile scores 1–q robustly, handling small or duplicate-heavy datasets."""
    ranked = series.rank(method='first', ascending=ascending)
    n = len(ranked)
    effective_q = min(q, n)
    labels = list(range(1, effective_q + 1))
    result = pd.qcut(ranked, q=effective_q, labels=labels, duplicates='drop')
    # qcut with duplicates='drop' may yield fewer categories than labels;
    # re-derive labels from actual categories to avoid mismatch.
    actual_cats = result.cat.categories
    actual_labels = list(range(1, len(actual_cats) + 1))
    result = pd.qcut(ranked, q=effective_q, labels=actual_labels, duplicates='drop')
    return result.astype(int)


def compute_rfm(df: pd.DataFrame) -> pd.DataFrame:
    reference_date = df['invoice_date'].max() + pd.Timedelta(days=1)

    rfm = df.groupby('customer_id').agg(
        recency=('invoice_date', lambda x: (reference_date - x.max()).days),
        frequency=('invoice', 'nunique'),
        monetary=('revenue', 'sum'),
    ).reset_index()

    # Recency: lower recency = better = higher score (ascending=False for rank so rank 1 = smallest recency)
    rfm['r_score'] = _qscore(rfm['recency'], ascending=False)
    rfm['f_score'] = _qscore(rfm['frequency'], ascending=True)
    rfm['m_score'] = _qscore(rfm['monetary'], ascending=True)
    rfm['segment'] = rfm.apply(assign_segment, axis=1)
    return rfm


def load_rfm(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
    countries: tuple = (),
) -> pd.DataFrame:
    placeholders = ','.join(['?' for _ in countries])
    sql = (
        "SELECT customer_id, invoice, invoice_date, revenue FROM transactions"
        f" WHERE invoice_date >= ? AND invoice_date <= ?"
        f" AND country IN ({placeholders})"
    )
    params = (start_date, end_date + ' 23:59:59') + countries
    df = pd.read_sql(sql, conn, params=params, parse_dates=['invoice_date'])
    return compute_rfm(df)
