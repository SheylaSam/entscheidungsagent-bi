import pandas as pd
import sqlite3

from src.semantic import NON_PRODUCT_STOCK_CODES  # re-exported for backward compatibility

__all__ = [
    'NON_PRODUCT_STOCK_CODES',
    'filter_product_rows',
    'get_top_products',
    'get_declining_products',
    'load_product_analysis',
]


def filter_product_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Keep rows that represent sellable products, excluding fees and adjustments."""
    result = df.copy()
    result['stock_code'] = result['stock_code'].astype(str).str.strip()
    result['description'] = result['description'].fillna('').astype(str).str.strip()
    mask = (
        result['description'].ne('')
        & ~result['stock_code'].str.upper().isin(NON_PRODUCT_STOCK_CODES)
        & ~result['description'].str.upper().isin(NON_PRODUCT_STOCK_CODES)
    )
    return result[mask].reset_index(drop=True)


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
                'revenue_avg': group['revenue'].mean(),
            })
    return pd.DataFrame(declining)


def load_product_analysis(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
    countries: tuple = (),
    declining_months: int = 3,
    top_n: int = 10,
    min_revenue: float = 0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (top_products_df, declining_products_df)."""
    placeholders = ','.join(['?' for _ in countries])
    sql = f"""
        SELECT stock_code, description,
               strftime('%Y-%m', invoice_date) AS month,
               SUM(revenue) AS revenue
        FROM transactions
        WHERE invoice_date >= ? AND invoice_date <= ?
        AND country IN ({placeholders})
        GROUP BY stock_code, description, month
        """
    params = (start_date, end_date + ' 23:59:59') + countries
    df = pd.read_sql(sql, conn, params=params)
    df = filter_product_rows(df)

    total = (
        df.groupby(['stock_code', 'description'])['revenue']
        .sum()
        .reset_index()
        .sort_values('revenue', ascending=False)
    )
    if min_revenue > 0:
        total = total[total['revenue'] >= min_revenue]
        eligible_codes = set(total['stock_code'])
        df = df[df['stock_code'].isin(eligible_codes)]

    top = get_top_products(total, n=top_n)
    declining = get_declining_products(df, months=declining_months)
    return top, declining
