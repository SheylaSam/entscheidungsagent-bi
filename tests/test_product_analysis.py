import sqlite3
import pandas as pd
from src.product_analysis import get_top_products, get_declining_products, filter_product_rows, load_product_analysis


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


def test_filter_product_rows_removes_non_product_entries():
    df = pd.DataFrame({
        'stock_code': ['85123A', 'POST', 'BANK CHARGES', 'M', 'DOT'],
        'description': ['Widget', 'POSTAGE', 'Bank Charges', 'Manual', 'Dotcom postage'],
        'revenue': [100.0, 20.0, 10.0, 5.0, 3.0],
    })
    result = filter_product_rows(df)
    assert result['stock_code'].tolist() == ['85123A']


def test_load_product_analysis_respects_top_n_and_min_revenue():
    conn = sqlite3.connect(':memory:')
    df = pd.DataFrame({
        'stock_code': ['A', 'B', 'C'],
        'description': ['Widget A', 'Widget B', 'Widget C'],
        'invoice_date': ['2011-01-15', '2011-01-15', '2011-01-15'],
        'revenue': [500.0, 300.0, 50.0],
        'country': ['United Kingdom', 'United Kingdom', 'United Kingdom'],
    })
    df.to_sql('transactions', conn, index=False)
    try:
        top, declining = load_product_analysis(
            conn,
            '2011-01-01',
            '2011-01-31',
            ('United Kingdom',),
            top_n=1,
            min_revenue=100,
        )
    finally:
        conn.close()
    assert top['stock_code'].tolist() == ['A']
    assert 'C' not in top['stock_code'].values
