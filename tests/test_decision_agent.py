import pandas as pd
from src.decision_agent import generate_recommendations

def make_forecast_decline():
    return pd.DataFrame({'ds': pd.date_range('2010-01-01', periods=5, freq='MS'), 'yhat': [1000, 1000, 1000, 1000, 850]})

def make_forecast_stable():
    return pd.DataFrame({'ds': pd.date_range('2010-01-01', periods=5, freq='MS'), 'yhat': [1000, 1000, 1000, 1000, 1050]})

def make_rfm_high_at_risk():
    return pd.DataFrame({'segment': ['At Risk'] * 25 + ['Champions'] * 75})

def make_rfm_low_at_risk():
    return pd.DataFrame({'segment': ['At Risk'] * 5 + ['Champions'] * 95})

def make_declining_products():
    return pd.DataFrame({'stock_code': ['X'], 'description': ['Bad Product'], 'revenue_last_month': [10.0]})

def make_no_declining():
    return pd.DataFrame(columns=['stock_code', 'description', 'revenue_last_month'])

def test_rule1_triggers_on_decline_with_at_risk():
    recs = generate_recommendations(make_forecast_decline(), make_rfm_high_at_risk(), make_no_declining())
    assert 'HOCH' in [r['priority'] for r in recs]

def test_rule1_does_not_trigger_on_stable_forecast():
    recs = generate_recommendations(make_forecast_stable(), make_rfm_low_at_risk(), make_no_declining())
    assert 'HOCH' not in [r['priority'] for r in recs]

def test_rule2_triggers_on_declining_products():
    recs = generate_recommendations(make_forecast_stable(), make_rfm_low_at_risk(), make_declining_products())
    assert any('Sortiment' in r['decision'] for r in recs)

def test_recommendation_has_required_keys():
    recs = generate_recommendations(make_forecast_decline(), make_rfm_high_at_risk(), make_declining_products())
    for r in recs:
        assert {'priority', 'finding', 'decision', 'reasoning'}.issubset(r.keys())
