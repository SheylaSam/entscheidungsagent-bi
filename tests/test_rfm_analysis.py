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

def test_assign_segment_loyal():
    row = pd.Series({'r_score': 3, 'f_score': 4, 'm_score': 3})
    assert assign_segment(row) == 'Loyal'

def test_assign_segment_others():
    # r=3, f=2 — doesn't match Champions, Loyal, At Risk, Lost, or New
    row = pd.Series({'r_score': 3, 'f_score': 2, 'm_score': 2})
    assert assign_segment(row) == 'Others'

def test_qscore_fewer_than_5_customers():
    from src.rfm_analysis import _qscore
    series = pd.Series([100, 200, 300])
    scores = _qscore(series, ascending=True)
    assert len(scores) == 3
    assert scores.min() >= 1
    assert scores.max() <= 3
