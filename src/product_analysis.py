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


def load_product_analysis(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
    countries: tuple = (),
    declining_months: int = 3,
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

    total = (
        df.groupby(['stock_code', 'description'])['revenue']
        .sum()
        .reset_index()
        .sort_values('revenue', ascending=False)
    )

    df['month_num'] = pd.to_datetime(df['month']).dt.to_period('M').apply(lambda x: x.ordinal)
    top = get_top_products(total)
    declining = get_declining_products(df, months=declining_months)
    return top, declining
