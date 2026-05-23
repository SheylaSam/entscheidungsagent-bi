"""Critic — the Learning-Agent's feedback loop (Russell & Norvig, Fig. 2.15).

The Critic reads past agent runs and human decision outcomes from the decision
log, evaluates whether the rule thresholds produced useful recommendations, and
suggests threshold adjustments. Suggestions are read-only — the user decides
whether to adopt them via the dashboard sliders. This keeps reproducibility
intact while still closing the lecture's "Lernelement → Kritik → Leistungselement"
loop conceptually (Folie 18).
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from src.decision_log import DEFAULT_LOG_DIR, list_agent_runs, load_agent_run, load_outcomes
from src.semantic import AgentThresholds


REJECTED_STATUSES = {'Zurückgestellt', 'Abgelehnt'}
APPROVED_STATUSES = {'Freigegeben'}
MIN_SAMPLES_FOR_SUGGESTION = 3


def _high_rejection_suggestion(runs: list[dict], outcomes: dict[str, dict]) -> dict | None:
    high_runs = [r for r in runs if r['top_priority'] == 'HOCH']
    if len(high_runs) < MIN_SAMPLES_FOR_SUGGESTION:
        return None
    rejected = sum(1 for r in high_runs if outcomes.get(r['run_id'], {}).get('status') in REJECTED_STATUSES)
    rate = rejected / len(high_runs)
    if rate <= 0.5:
        return None
    return {
        'threshold': 'forecast_decline',
        'current_default': AgentThresholds().forecast_decline,
        'suggested': -0.08,
        'reasoning': (
            f'{rejected} von {len(high_runs)} HOCH-Empfehlungen wurden zurückgestellt oder abgelehnt '
            f'({rate:.0%}). Schwellwert für Forecast-Rückgang evtl. zu sensibel — strengere Auslösung '
            'reduziert False-Positives.'
        ),
    }


def _no_action_dominant_suggestion(runs: list[dict]) -> dict | None:
    if len(runs) < MIN_SAMPLES_FOR_SUGGESTION:
        return None
    tief_count = sum(1 for r in runs if r['top_priority'] == 'TIEF')
    rate = tief_count / len(runs)
    if rate <= 0.7:
        return None
    return {
        'threshold': 'at_risk_share',
        'current_default': AgentThresholds().at_risk_share,
        'suggested': 0.15,
        'reasoning': (
            f'{tief_count} von {len(runs)} Läufen ({rate:.0%}) endeten ohne Handlungsbedarf. '
            'Schwellwerte evtl. zu locker — sensiblere Auslösung könnte mehr relevante Signale erfassen.'
        ),
    }


def _approval_rate(runs: list[dict], outcomes: dict[str, dict]) -> float | None:
    decided = [
        r for r in runs
        if outcomes.get(r['run_id'], {}).get('status') in APPROVED_STATUSES | REJECTED_STATUSES
    ]
    if not decided:
        return None
    approved = sum(1 for r in decided if outcomes.get(r['run_id'], {}).get('status') in APPROVED_STATUSES)
    return approved / len(decided)


def _utility_drift(runs: list[dict], log_dir: Path) -> dict | None:
    """If average top utility has drifted strongly down, surface it."""
    if len(runs) < 6:
        return None
    utilities: list[float] = []
    for r in runs:
        try:
            full = load_agent_run(r['run_id'], log_dir=log_dir)
        except (OSError, FileNotFoundError):
            continue
        top_utility = full.get('evidence', {}).get('top_utility_gbp')
        if top_utility is not None:
            utilities.append(float(top_utility))
    if len(utilities) < 6:
        return None
    recent = utilities[: len(utilities) // 2]
    older = utilities[len(utilities) // 2 :]
    if not recent or not older:
        return None
    recent_avg = sum(recent) / len(recent)
    older_avg = sum(older) / len(older)
    if older_avg == 0 or abs(recent_avg - older_avg) / max(older_avg, 1) < 0.30:
        return None
    direction = 'gestiegen' if recent_avg > older_avg else 'gesunken'
    return {
        'threshold': None,
        'current_default': None,
        'suggested': None,
        'reasoning': (
            f'Durchschnittliche Top-Utility ist von £{older_avg:,.0f} auf £{recent_avg:,.0f} {direction} '
            f'({(recent_avg - older_avg) / max(older_avg, 1):+.0%}). '
            'Trend prüfen: Verändert sich das Risikoprofil oder driften die Daten?'
        ),
    }


def analyze_decision_history(log_dir: str | Path = DEFAULT_LOG_DIR) -> dict:
    """Read decision log + outcomes, produce learning-loop diagnostics."""
    log_dir = Path(log_dir)
    runs = list_agent_runs(log_dir=log_dir, limit=None)
    outcomes = load_outcomes(log_dir=log_dir)

    priority_dist = Counter(r['top_priority'] for r in runs if r['top_priority'])
    status_dist = Counter(
        outcomes.get(r['run_id'], {}).get('status', 'Offen') for r in runs
    )

    suggestions: list[dict] = []
    for finder in (
        lambda: _high_rejection_suggestion(runs, outcomes),
        lambda: _no_action_dominant_suggestion(runs),
        lambda: _utility_drift(runs, log_dir),
    ):
        suggestion = finder()
        if suggestion is not None:
            suggestions.append(suggestion)

    return {
        'run_count': len(runs),
        'outcome_count': len(outcomes),
        'priority_distribution': dict(priority_dist),
        'status_distribution': dict(status_dist),
        'approval_rate': _approval_rate(runs, outcomes),
        'suggestions': suggestions,
    }
