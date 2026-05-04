import pandas as pd

from src.customer_analysis import get_primary_customer_country, summarize_segments_by_country


def test_primary_customer_country_uses_highest_revenue_country():
    transactions = pd.DataFrame({
        'customer_id': ['A', 'A', 'A', 'B'],
        'country': ['France', 'Germany', 'Germany', 'Spain'],
        'revenue': [100.0, 80.0, 70.0, 50.0],
    })
    result = get_primary_customer_country(transactions)
    countries = dict(zip(result['customer_id'], result['country']))
    assert countries['A'] == 'Germany'
    assert countries['B'] == 'Spain'


def test_segment_summary_does_not_duplicate_multi_country_customers():
    rfm = pd.DataFrame({
        'customer_id': ['A', 'B'],
        'segment': ['At Risk', 'Champions'],
        'monetary': [100.0, 50.0],
    })
    customer_country = pd.DataFrame({
        'customer_id': ['A', 'B'],
        'country': ['Germany', 'Spain'],
    })
    result = summarize_segments_by_country(rfm, customer_country)
    assert result['Kunden'].sum() == 2
    assert result['Umsatz'].sum() == 150.0
