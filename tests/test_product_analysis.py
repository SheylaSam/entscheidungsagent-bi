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
