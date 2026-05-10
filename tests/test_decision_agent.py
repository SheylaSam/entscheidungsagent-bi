import pandas as pd
from src.decision_agent import AgentThresholds, generate_agent_run, generate_recommendations

def make_forecast_decline():
    return pd.DataFrame({'ds': pd.date_range('2010-01-01', periods=6, freq='MS'), 'yhat': [1000, 1000, 1000, 850, 900, 950]})

def make_forecast_stable():
    return pd.DataFrame({'ds': pd.date_range('2010-01-01', periods=6, freq='MS'), 'yhat': [1000, 1000, 1000, 1050, 1000, 850]})

def make_forecast_negative():
    return pd.DataFrame({'ds': pd.date_range('2010-01-01', periods=6, freq='MS'), 'yhat': [1000, 1000, 1000, -100, 1000, 1000]})

def make_actuals():
    return pd.DataFrame({'ds': pd.date_range('2010-01-01', periods=3, freq='MS'), 'y': [1000, 1000, 1000]})

def make_rfm_high_at_risk():
    return pd.DataFrame({'segment': ['At Risk'] * 25 + ['Champions'] * 75, 'monetary': [1000.0] * 100})

def make_rfm_low_at_risk():
    return pd.DataFrame({'segment': ['At Risk'] * 5 + ['Champions'] * 95, 'monetary': [1000.0] * 100})

def make_rfm_low_champions():
    # 5% champions → rule 3 fires; even monetary → rule 5 doesn't fire
    return pd.DataFrame({'segment': ['Champions'] * 5 + ['Others'] * 95, 'monetary': [1000.0] * 100})

def make_rfm_high_champions():
    # 20% champions, 10% new → neither rule 3 nor 4 fires; even monetary → rule 5 doesn't fire
    return pd.DataFrame({'segment': ['Champions'] * 20 + ['New'] * 10 + ['Others'] * 70, 'monetary': [1000.0] * 100})

def make_rfm_concentrated():
    # top 20 of 100 hold ~96% of revenue → rule 5 fires
    return pd.DataFrame({'segment': ['Others'] * 100, 'monetary': [1000.0] * 20 + [10.0] * 80})

def make_declining_products():
    return pd.DataFrame({
        'stock_code': ['X'],
        'description': ['Bad Product'],
        'revenue_last_month': [10.0],
        'revenue_avg': [100.0],
    })

def make_declining_above_threshold():
    # revenue_last_month >= 50% of avg → rule 2 should NOT fire
    return pd.DataFrame({
        'stock_code': ['Y'],
        'description': ['Okay Product'],
        'revenue_last_month': [60.0],
        'revenue_avg': [100.0],
    })

def make_no_declining():
    return pd.DataFrame(columns=['stock_code', 'description', 'revenue_last_month', 'revenue_avg'])

# ── Rule 1 ────────────────────────────────────────────────────────────────────

def test_rule1_triggers_on_decline_with_at_risk():
    recs = generate_recommendations(make_forecast_decline(), make_rfm_high_at_risk(), make_no_declining(), actuals_df=make_actuals())
    assert 'HOCH' in [r['priority'] for r in recs]

def test_rule1_does_not_trigger_on_stable_forecast():
    recs = generate_recommendations(make_forecast_stable(), make_rfm_low_at_risk(), make_no_declining(), actuals_df=make_actuals())
    assert 'HOCH' not in [r['priority'] for r in recs]

def test_rule1_uses_first_future_month_not_last_future_month():
    recs = generate_recommendations(make_forecast_stable(), make_rfm_high_at_risk(), make_no_declining(), actuals_df=make_actuals())
    assert 'HOCH' not in [r['priority'] for r in recs]

def test_rule1_can_use_custom_comparison_value():
    recs = generate_recommendations(
        make_forecast_stable(),
        make_rfm_high_at_risk(),
        make_no_declining(),
        actuals_df=make_actuals(),
        comparison_value=1200,
    )
    assert 'HOCH' in [r['priority'] for r in recs]

# ── Rule 2 ────────────────────────────────────────────────────────────────────

def test_rule2_triggers_on_declining_products_below_threshold():
    recs = generate_recommendations(make_forecast_stable(), make_rfm_low_at_risk(), make_declining_products())
    assert any('Sortiment' in r['decision'] for r in recs)

def test_rule2_does_not_trigger_when_revenue_above_50pct_avg():
    recs = generate_recommendations(make_forecast_stable(), make_rfm_low_at_risk(), make_declining_above_threshold())
    assert not any('Sortiment' in r['decision'] for r in recs)

# ── Rule 3 ────────────────────────────────────────────────────────────────────

def test_rule3_triggers_on_low_champion_share():
    recs = generate_recommendations(make_forecast_stable(), make_rfm_low_champions(), make_no_declining())
    assert any('Kundenbindung' in r['decision'] or 'Champions' in r['finding'] for r in recs)

def test_rule3_does_not_trigger_on_sufficient_champion_share():
    recs = generate_recommendations(make_forecast_stable(), make_rfm_high_champions(), make_no_declining())
    assert not any('Kundenbindungsprogramm' in r['decision'] for r in recs)

# ── Rule 4 ────────────────────────────────────────────────────────────────────

def test_rule4_triggers_on_low_new_share():
    # make_rfm_low_champions has 0 New customers → new_share = 0% < 5%
    recs = generate_recommendations(make_forecast_stable(), make_rfm_low_champions(), make_no_declining())
    assert any('Neukundenakquisition' in r['decision'] for r in recs)

def test_rule4_does_not_trigger_on_sufficient_new_share():
    # make_rfm_high_champions has 10% New → new_share = 10% > 5%
    recs = generate_recommendations(make_forecast_stable(), make_rfm_high_champions(), make_no_declining())
    assert not any('Neukundenakquisition' in r['decision'] for r in recs)

# ── Rule 5 ────────────────────────────────────────────────────────────────────

def test_rule5_triggers_on_concentration_risk():
    recs = generate_recommendations(make_forecast_stable(), make_rfm_concentrated(), make_no_declining())
    assert any('diversifizieren' in r['decision'] for r in recs)

def test_rule5_does_not_trigger_on_distributed_revenue():
    recs = generate_recommendations(make_forecast_stable(), make_rfm_high_champions(), make_no_declining())
    assert not any('diversifizieren' in r['decision'] for r in recs)

# ── Rule 6 (TIEF) ─────────────────────────────────────────────────────────────

def test_rule6_tief_when_all_conditions_green():
    recs = generate_recommendations(make_forecast_stable(), make_rfm_high_champions(), make_no_declining())
    assert any(r['priority'] == 'TIEF' for r in recs)
    assert 'HOCH' not in [r['priority'] for r in recs]

# ── Edge cases ────────────────────────────────────────────────────────────────

def test_thin_data_returns_early_with_mittel():
    tiny_rfm = pd.DataFrame({'segment': ['Champions'] * 5, 'monetary': [1000.0] * 5})
    recs = generate_recommendations(make_forecast_stable(), tiny_rfm, make_no_declining())
    assert len(recs) == 1
    assert recs[0]['priority'] == 'MITTEL'
    assert 'dünn' in recs[0]['finding']

def test_negative_forecast_returns_mittel():
    recs = generate_recommendations(make_forecast_negative(), make_rfm_low_at_risk(), make_no_declining())
    assert len(recs) == 1
    assert recs[0]['priority'] == 'MITTEL'
    assert 'negativ' in recs[0]['finding'].lower()

def test_recommendation_has_required_keys():
    recs = generate_recommendations(make_forecast_decline(), make_rfm_high_at_risk(), make_declining_products())
    for r in recs:
        assert {'priority', 'finding', 'decision', 'reasoning'}.issubset(r.keys())


def test_agent_thresholds_document_rule_defaults():
    thresholds = AgentThresholds()
    assert thresholds.forecast_decline == -0.05
    assert thresholds.at_risk_share == 0.20
    assert thresholds.declining_product_share == 0.50
    assert thresholds.top_customer_revenue_share == 0.80


def test_generate_agent_run_contains_trace_evidence_and_guardrails():
    run = generate_agent_run(
        make_forecast_decline(),
        make_rfm_high_at_risk(),
        make_declining_products(),
        actuals_df=make_actuals(),
    )
    assert run['agent_type'] == 'Regelbasierter BI-Agent mit Human-in-the-Loop'
    assert len(run['recommendations']) >= 1
    assert len(run['trace']) >= 6
    assert {'baseline_revenue', 'next_forecast', 'at_risk_share'}.issubset(run['evidence'])
    assert any(g['name'] == 'Human-in-the-Loop' for g in run['guardrails'])


def test_generate_agent_run_requires_approval_for_medium_or_high_recommendation():
    run = generate_agent_run(
        make_forecast_stable(),
        make_rfm_low_at_risk(),
        make_declining_products(),
        actuals_df=make_actuals(),
    )
    assert run['approval_required'] is True


def test_generate_agent_run_marks_human_approval_optional_for_low_priority():
    run = generate_agent_run(
        make_forecast_stable(),
        make_rfm_high_champions(),
        make_no_declining(),
        actuals_df=make_actuals(),
    )
    assert run['recommendations'][0]['priority'] == 'TIEF'
    assert run['approval_required'] is False
