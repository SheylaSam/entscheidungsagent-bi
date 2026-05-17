"""KPI cards — the canonical way to render a single key metric.

Public API: ``kpi_card(...)``. Everything prefixed ``_`` is a pure helper
exposed only for testing.

See: docs/superpowers/specs/2026-05-17-dashboard-redesign-design.md §4
"""
from __future__ import annotations

from typing import Iterable

import pandas as pd

from src.ui import theme


def _format_value(value: float | int | None, fmt: str) -> str:
    """Format a numeric value using a Python format spec string.

    Returns an em-dash when ``value`` is None — keeps card layout from
    shifting when data is missing.
    """
    if value is None:
        return "—"
    return fmt.format(value)


def _delta_text(delta_pct: float | None, period: str) -> str:
    """Render the delta-percentage string with directional arrow.

    The caller is responsible for passing a percentage value (8.1 means
    +8.1 %, not 0.081). Returns the empty string when ``delta_pct`` is
    None so layout collapses gracefully.
    """
    if delta_pct is None:
        return ""
    if delta_pct > 0:
        return f"↑ +{delta_pct:.1f}%"
    if delta_pct < 0:
        return f"↓ {delta_pct:.1f}%"
    return "→ 0.0%"


def _delta_color(delta_pct: float | None, *, higher_is_better: bool) -> str:
    """Pick the semantic color for the delta line.

    When ``higher_is_better`` is False (at-risk customers, churn, costs)
    the colour mapping inverts: an increase is bad (red), a decrease is
    good (green).
    """
    if delta_pct is None or delta_pct == 0:
        return theme.MUTED
    going_up = delta_pct > 0
    is_good = going_up if higher_is_better else not going_up
    return theme.POSITIVE if is_good else theme.NEGATIVE
