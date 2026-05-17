"""Decision Log — persists agent runs as JSON for auditability.

The Week-11 lecture's Decision Layer slide names "Entscheidungslog mit
Nachvollziehbarkeit" as a core capability. Every agent run is written to
logs/agent_runs/<run_id>.json, so the recommendation, evidence, trace and
guardrails can be reviewed after the fact — without re-running the agent.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np


DEFAULT_LOG_DIR = Path("logs/agent_runs")


class _RunEncoder(json.JSONEncoder):
    """Convert numpy / pandas / datetime values to JSON-native types."""

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (datetime,)):
            return obj.isoformat()
        return super().default(obj)


def log_agent_run(run: dict, log_dir: str | Path = DEFAULT_LOG_DIR) -> Path:
    """Persist an agent run to disk and return the file path."""
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"{run['run_id']}.json"
    with path.open('w', encoding='utf-8') as f:
        json.dump(run, f, cls=_RunEncoder, indent=2, ensure_ascii=False)
    return path


def list_agent_runs(log_dir: str | Path = DEFAULT_LOG_DIR, limit: int | None = None) -> list[dict]:
    """Return a summary of persisted runs, newest first."""
    log_dir = Path(log_dir)
    if not log_dir.exists():
        return []
    paths = sorted(
        (p for p in log_dir.glob("*.json") if not p.name.endswith('.outcome.json')),
        reverse=True,
    )
    if limit is not None:
        paths = paths[:limit]
    summaries: list[dict] = []
    for path in paths:
        try:
            with path.open('r', encoding='utf-8') as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        recs = data.get('recommendations') or []
        top = recs[0] if recs else {}
        summaries.append({
            'run_id': data.get('run_id'),
            'agent_type': data.get('agent_type'),
            'top_priority': top.get('priority'),
            'top_decision': top.get('decision'),
            'recommendation_count': len(recs),
            'approval_required': data.get('approval_required'),
            'path': path,
        })
    return summaries


def load_agent_run(run_id: str, log_dir: str | Path = DEFAULT_LOG_DIR) -> dict:
    """Load a single persisted run by run_id."""
    path = Path(log_dir) / f"{run_id}.json"
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


# ── Decision outcomes ────────────────────────────────────────────────────────
# A separate companion file <run_id>.outcome.json captures the human approval
# step (Freigegeben/Zurückgestellt/Abgelehnt + note). Splitting it from the run
# file means the original agent output stays immutable while still being
# joinable for the Critic / learning loop.

def log_decision_outcome(
    run_id: str,
    status: str,
    note: str = '',
    log_dir: str | Path = DEFAULT_LOG_DIR,
) -> Path:
    """Persist the human-in-the-loop decision for a given run."""
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"{run_id}.outcome.json"
    payload = {
        'run_id': run_id,
        'status': status,
        'note': note,
        'logged_at': datetime.now().isoformat(),
    }
    with path.open('w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return path


def load_outcomes(log_dir: str | Path = DEFAULT_LOG_DIR) -> dict[str, dict]:
    """Return {run_id: outcome_dict} for every persisted decision outcome."""
    log_dir = Path(log_dir)
    if not log_dir.exists():
        return {}
    outcomes: dict[str, dict] = {}
    for path in log_dir.glob("*.outcome.json"):
        try:
            with path.open('r', encoding='utf-8') as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if data.get('run_id'):
            outcomes[data['run_id']] = data
    return outcomes


def log_feedback(
    rec_id: str,
    vote: str,
    *,
    log_path: Path | None = None,
) -> None:
    """Append one feedback event (👍 / 👎) to the feedback JSONL log.

    Parameters
    ----------
    rec_id:
        Stable recommendation identifier (matches the UI trace-ID).
    vote:
        Either ``"up"`` or ``"down"``.
    log_path:
        Override the default path (used by tests).  Default writes to
        ``<DEFAULT_LOG_DIR>/feedback.jsonl`` alongside the existing
        decision-outcomes log.
    """
    if vote not in {"up", "down"}:
        raise ValueError(f"vote must be 'up' or 'down', got {vote!r}")

    if log_path is None:
        log_path = DEFAULT_LOG_DIR / "feedback.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "rec_id": rec_id,
        "vote": vote,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    with log_path.open("a") as f:
        f.write(json.dumps(record) + "\n")
