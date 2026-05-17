"""KPI cards — the canonical way to render a single key metric.

Public API: ``kpi_card(...)``. Everything prefixed ``_`` is a pure helper
exposed only for testing.

See: docs/superpowers/specs/2026-05-17-dashboard-redesign-design.md §4
"""
from __future__ import annotations

from typing import Iterable

import pandas as pd
import plotly.graph_objects as go

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


def _sparkline_figure(
    series: "pd.Series | None",
    *,
    trend_positive: bool,
    split_at: "int | None" = None,
) -> "go.Figure | None":
    """Build a 56 px-tall sparkline figure from ``series``.

    Parameters
    ----------
    series:
        Numeric, indexed by anything plottable on a categorical x axis
        (datetimes work, ints work).  Returns ``None`` if the series is
        empty or ``None`` — caller leaves the slot empty.
    trend_positive:
        Used to color the last-point dot.  Caller decides based on the
        delta direction and ``higher_is_better`` (so the dot is green on
        good outcomes, red on bad ones — same semantic as the delta
        text).
    split_at:
        Integer index.  When given, the series is split into a solid
        line for ``series[:split_at + 1]`` and a dashed line for
        ``series[split_at:]``.  Used by the forecast card to mark the
        actual→forecast boundary.
    """
    if series is None or len(series) == 0:
        return None

    x = list(series.index)
    y = series.tolist()
    last_color = theme.POSITIVE if trend_positive else theme.NEGATIVE

    fig = go.Figure()

    if split_at is not None and 0 <= split_at < len(series) - 1:
        # Solid head; dashed tail.  Overlap one point so the line is
        # visually continuous.
        fig.add_trace(go.Scatter(
            x=x[: split_at + 1], y=y[: split_at + 1],
            mode="lines",
            line=dict(color=theme.MUTED, width=2),
            hoverinfo="skip", showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=x[split_at:], y=y[split_at:],
            mode="lines",
            line=dict(color=theme.MUTED, width=2, dash="dash"),
            hoverinfo="skip", showlegend=False,
        ))
    else:
        fig.add_trace(go.Scatter(
            x=x, y=y,
            mode="lines",
            line=dict(color=theme.MUTED, width=2),
            hoverinfo="skip", showlegend=False,
        ))

    # Last-point dot
    fig.add_trace(go.Scatter(
        x=[x[-1]], y=[y[-1]],
        mode="markers",
        marker=dict(color=last_color, size=6),
        hoverinfo="skip", showlegend=False,
    ))

    fig.update_layout(
        height=56,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(visible=False, fixedrange=True)
    fig.update_yaxes(visible=False, fixedrange=True)
    return fig
