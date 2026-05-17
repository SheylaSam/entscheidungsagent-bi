import json

import numpy as np
import pandas as pd
import pytest

from src.decision_agent import generate_agent_run
from src.decision_log import list_agent_runs, load_agent_run, log_agent_run


def _sample_run():
    return generate_agent_run(
        pd.DataFrame({'ds': pd.date_range('2010-01-01', periods=6, freq='MS'),
                      'yhat': [1000, 1000, 1000, 850, 900, 950]}),
        pd.DataFrame({'segment': ['At Risk'] * 25 + ['Champions'] * 75,
                      'monetary': [1000.0] * 100}),
        pd.DataFrame({
            'stock_code': ['X'],
            'description': ['Bad Product'],
            'revenue_last_month': [10.0],
            'revenue_avg': [100.0],
        }),
        actuals_df=pd.DataFrame({'ds': pd.date_range('2010-01-01', periods=3, freq='MS'),
                                 'y': [1000, 1000, 1000]}),
    )


def test_log_agent_run_persists_run_as_json(tmp_path):
    run = _sample_run()
    path = log_agent_run(run, log_dir=tmp_path)
    assert path.exists()
    with path.open() as f:
        data = json.load(f)
    assert data['run_id'] == run['run_id']
    assert data['agent_type'] == 'Utility-basierter BI-Agent mit Human-in-the-Loop'
    assert len(data['recommendations']) == len(run['recommendations'])


def test_log_agent_run_handles_numpy_scalars(tmp_path):
    run = {
        'run_id': '20260510120000000000',
        'goal': 'test',
        'agent_type': 'test',
        'recommendations': [],
        'evidence': {
            'baseline_revenue': np.float64(1234.5),
            'customer_count': np.int64(42),
        },
        'trace': [],
        'guardrails': [],
        'approval_required': np.bool_(True),
    }
    path = log_agent_run(run, log_dir=tmp_path)
    with path.open() as f:
        data = json.load(f)
    assert data['evidence']['baseline_revenue'] == 1234.5
    assert data['evidence']['customer_count'] == 42
    assert data['approval_required'] is True


def test_list_agent_runs_returns_newest_first(tmp_path):
    run_a = _sample_run()
    run_a['run_id'] = '20260510120000000000'
    run_b = _sample_run()
    run_b['run_id'] = '20260510130000000000'
    log_agent_run(run_a, log_dir=tmp_path)
    log_agent_run(run_b, log_dir=tmp_path)
    runs = list_agent_runs(log_dir=tmp_path)
    assert [r['run_id'] for r in runs] == [run_b['run_id'], run_a['run_id']]
    assert runs[0]['recommendation_count'] >= 1


def test_list_agent_runs_returns_empty_when_log_dir_missing(tmp_path):
    assert list_agent_runs(log_dir=tmp_path / 'does_not_exist') == []


def test_load_agent_run_round_trips_a_persisted_run(tmp_path):
    run = _sample_run()
    log_agent_run(run, log_dir=tmp_path)
    loaded = load_agent_run(run['run_id'], log_dir=tmp_path)
    assert loaded['recommendations'] == run['recommendations']
    assert loaded['guardrails'] == run['guardrails']


def test_log_feedback_writes_jsonl(tmp_path):
    from src.decision_log import log_feedback
    log_file = tmp_path / "feedback.jsonl"
    log_feedback("rec-abc", "up", log_path=log_file)
    log_feedback("rec-abc", "down", log_path=log_file)
    lines = log_file.read_text().strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["rec_id"] == "rec-abc"
    assert first["vote"] == "up"
    assert "timestamp" in first


def test_log_feedback_rejects_unknown_vote(tmp_path):
    from src.decision_log import log_feedback
    with pytest.raises(ValueError):
        log_feedback("rec-1", "maybe", log_path=tmp_path / "feedback.jsonl")
