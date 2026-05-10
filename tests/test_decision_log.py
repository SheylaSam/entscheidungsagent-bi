import json

import numpy as np
import pandas as pd

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
    assert data['agent_type'] == 'Regelbasierter BI-Agent mit Human-in-the-Loop'
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
