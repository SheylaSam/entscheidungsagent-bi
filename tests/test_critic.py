import json

from src.critic import analyze_decision_history
from src.decision_log import log_agent_run, log_decision_outcome


def _make_run(run_id: str, priority: str, top_utility: float = 5000.0) -> dict:
    return {
        'run_id': run_id,
        'agent_type': 'Utility-basierter BI-Agent mit Human-in-the-Loop',
        'recommendations': [
            {
                'priority': priority,
                'decision': f'Decision {run_id}',
                'finding': '',
                'reasoning': '',
                'utility': top_utility,
                'utility_components': {
                    'expected_impact_gbp': top_utility,
                    'urgency': 1.0,
                    'confidence': 1.0,
                },
            }
        ],
        'evidence': {'top_utility_gbp': top_utility},
        'trace': [],
        'guardrails': [],
        'approval_required': priority in {'HOCH', 'MITTEL'},
    }


def test_critic_reports_zero_state_when_no_runs(tmp_path):
    summary = analyze_decision_history(log_dir=tmp_path)
    assert summary['run_count'] == 0
    assert summary['outcome_count'] == 0
    assert summary['suggestions'] == []
    assert summary['approval_rate'] is None


def test_critic_suggests_tighter_forecast_threshold_when_high_priority_keeps_being_rejected(tmp_path):
    for i in range(4):
        run = _make_run(f"hoch_{i}", 'HOCH')
        log_agent_run(run, log_dir=tmp_path)
        log_decision_outcome(run['run_id'], 'Abgelehnt', note='Zu sensibel', log_dir=tmp_path)

    summary = analyze_decision_history(log_dir=tmp_path)
    assert summary['run_count'] == 4
    assert any(s['threshold'] == 'forecast_decline' for s in summary['suggestions'])


def test_critic_does_not_suggest_when_high_priority_is_being_approved(tmp_path):
    for i in range(4):
        run = _make_run(f"hoch_{i}", 'HOCH')
        log_agent_run(run, log_dir=tmp_path)
        log_decision_outcome(run['run_id'], 'Freigegeben', log_dir=tmp_path)

    summary = analyze_decision_history(log_dir=tmp_path)
    assert not any(s['threshold'] == 'forecast_decline' for s in summary['suggestions'])
    assert summary['approval_rate'] == 1.0


def test_critic_flags_dominant_no_action(tmp_path):
    for i in range(5):
        run = _make_run(f"tief_{i}", 'TIEF', top_utility=0.0)
        log_agent_run(run, log_dir=tmp_path)
    summary = analyze_decision_history(log_dir=tmp_path)
    assert any(s['threshold'] == 'at_risk_share' for s in summary['suggestions'])


def test_log_decision_outcome_round_trip(tmp_path):
    log_decision_outcome('abc123', 'Freigegeben', note='gut', log_dir=tmp_path)
    summary = analyze_decision_history(log_dir=tmp_path)
    assert summary['outcome_count'] == 1
    path = tmp_path / 'abc123.outcome.json'
    assert path.exists()
    with path.open() as f:
        payload = json.load(f)
    assert payload['status'] == 'Freigegeben'
    assert payload['note'] == 'gut'
