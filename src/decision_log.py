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
    paths = sorted(log_dir.glob("*.json"), reverse=True)
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
