# Dashboard Redesign — Phase 2: KPI Cards — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the four-KPI strip on the Übersicht (currently rendered via `render_evidence_strip`) with proper card components that show *label · big number with `tabular-nums` · semantic delta with comparison context · 56 px sparkline*. Add a reusable `kpi_card()` primitive that becomes the only way KPIs are rendered going forward.

**Architecture:** A new module `src/ui/cards.py` exposes `kpi_card(...)` plus small pure helpers (formatting, delta text/color, sparkline figure). A CSS-injection helper lives on `src/ui/theme.py` and is called once at the top of `app.py`. The 4 overview KPIs are computed inline in `app.py` for now (Phase 3 will move data computation out of `app.py` when pages are split). Comparison method for Phase 2 is **last 12 months vs. previous 12 months** — a stable proxy until the global date-range arrives in Phase 3.

**Tech Stack:** Streamlit ≥ 1.50 (Phase 1 dependency), Plotly ≥ 5.20, pandas. No new component libraries.

**Reference:** [`docs/superpowers/specs/2026-05-17-dashboard-redesign-design.md`](../specs/2026-05-17-dashboard-redesign-design.md) §4 (KPI cards), §2.2 (typography rules incl. `tabular-nums`), §2.3 (card spacing).

**Depends on:** Phase 1 (theme.py tokens, polish() chart layer) is merged.

**Out of scope:** st.metric calls on the Critic / Agent-Verlauf pages — those get their own treatment in later phases. The "vs. Vormonat" copy on the forecast card is rendered as text; an interactive comparison-window switcher (e.g. "vs. Vorjahr") is a Phase 4 polish.

---

## File Plan

**Create:**
- `src/ui/cards.py` — `kpi_card()` + helpers
- `tests/test_ui_cards.py` — unit tests for helpers
- `tests/test_ui_cards_render.py` — Streamlit-AppTest smoke test for `kpi_card()`

**Modify:**
- `src/ui/theme.py` — add `inject_global_css()` helper
- `tests/test_ui_theme.py` — add tests for the CSS helper
- `app.py` — wire `inject_global_css()`, compute KPI data, replace `render_evidence_strip(...)` on the overview, remove old `[data-testid="stMetric"]` CSS block

**Do not touch:**
- `src/ui/viz_theme.py` (stable from Phase 1)
- `render_decision_panel`, `render_evidence_strip` definitions themselves — `render_evidence_strip` stays available for the Forecast tab which still calls it (line 555). We're only swapping the *overview call site*.

---

## Task 1: `inject_global_css()` in `theme.py`

Centralised CSS injection. Loads Inter + JetBrains Mono from Google Fonts and applies the four global rules the spec requires: `tabular-nums` everywhere numbers live, card-padding override, hide the "Made with Streamlit" footer, and the KPI-card class set.

**Files:**
- Modify: `src/ui/theme.py`
- Modify: `tests/test_ui_theme.py`

- [ ] **Step 1: Append failing tests to `tests/test_ui_theme.py`**

```python
def test_inject_global_css_returns_a_style_block():
    css = theme.global_css()
    assert "<style>" in css and "</style>" in css


def test_global_css_imports_inter_font():
    css = theme.global_css()
    assert "Inter" in css
    assert "fonts.googleapis.com" in css


def test_global_css_enables_tabular_nums_on_kpi_class():
    css = theme.global_css()
    assert ".kpi-number" in css
    assert "tabular-nums" in css


def test_global_css_defines_kpi_label_delta_classes():
    css = theme.global_css()
    for cls in (".kpi-label", ".kpi-number", ".kpi-delta", ".kpi-card"):
        assert cls in css, f"missing rule for {cls}"


def test_global_css_uses_token_values():
    css = theme.global_css()
    # representative spot-checks — if these miss, tokens are not flowing in
    assert theme.MUTED in css        # used for label color
    assert theme.HEADING in css      # used for value color
    assert theme.BORDER in css       # used for card border
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_ui_theme.py -v`
Expected: 5 new tests FAIL (AttributeError: module 'src.ui.theme' has no attribute 'global_css').

- [ ] **Step 3: Append the helper to `src/ui/theme.py`**

Append to the end of `src/ui/theme.py`:

```python
# ── Global CSS injection ────────────────────────────────────────────────────
def global_css() -> str:
    """Return the complete <style> block to inject once per page.

    Sources two Google Fonts (Inter, JetBrains Mono), forces tabular
    figures wherever numbers appear, sets card padding/border tokens,
    hides the default Streamlit chrome (footer/main-menu), and defines
    the .kpi-* class hierarchy used by src/ui/cards.py.
    """
    return f"""
<style>
@import url("{INTER_URL}");
@import url("{JETBRAINS_MONO_URL}");

/* ── Page chrome ──────────────────────────────────────────────── */
.block-container {{
    padding-top: 2rem;
    padding-bottom: 4rem;
    max-width: {PAGE_MAX_WIDTH_PX}px;
}}
#MainMenu, footer {{ visibility: hidden; }}

/* ── Tabular figures everywhere numbers live ──────────────────── */
.kpi-number, .stDataFrame td, [data-testid="stMetricValue"] {{
    font-variant-numeric: tabular-nums;
    font-feature-settings: "tnum" 1, "cv11" 1;
}}

/* ── KPI card layout (used by src/ui/cards.kpi_card) ──────────── */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.kpi-card) {{
    border: 1px solid {BORDER};
    border-radius: {CARD_RADIUS_REM};
    padding: {CARD_PADDING_PX}px;
    background: {BG_PAGE};
}}
.kpi-card {{
    display: flex;
    flex-direction: column;
    gap: 6px;
}}
.kpi-label {{
    display: flex;
    align-items: center;
    gap: 6px;
    color: {MUTED};
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZES_PX["KPI_LABEL"]}px;
    font-weight: 500;
    letter-spacing: 0.02em;
    text-transform: uppercase;
}}
.kpi-tooltip {{
    color: {FAINT};
    cursor: help;
    font-size: {FONT_SIZES_PX["KPI_LABEL"]}px;
}}
.kpi-number {{
    color: {HEADING};
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZES_PX["KPI_NUMBER"]}px;
    font-weight: 600;
    line-height: 1.1;
    margin-top: 2px;
}}
.kpi-delta {{
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZES_PX["KPI_DELTA"]}px;
    font-weight: 500;
    margin-bottom: 4px;
}}
.kpi-delta.is-muted {{ color: {MUTED}; }}
.kpi-delta-period {{ color: {MUTED}; margin-left: 6px; font-weight: 400; }}
</style>
""".strip()


def inject_global_css() -> None:
    """Call once near the top of the Streamlit script."""
    import streamlit as st  # imported lazily so tests can import this module
    st.markdown(global_css(), unsafe_allow_html=True)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_ui_theme.py -v`
Expected: all tests PASS (including the 5 new ones).

- [ ] **Step 5: Commit**

```bash
git add src/ui/theme.py tests/test_ui_theme.py
git commit -m "feat(ui): add inject_global_css() with KPI-card class set"
```

---

## Task 2: Cards module — pure formatting helpers

Three pure functions that turn raw values into display strings + semantic colors. All unit-testable without Streamlit.

**Files:**
- Create: `src/ui/cards.py`
- Create: `tests/test_ui_cards.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_ui_cards.py`:

```python
"""Tests for the pure helper functions in src/ui/cards.py."""
import pandas as pd

from src.ui import cards, theme


# ── _format_value ───────────────────────────────────────────────────────────
def test_format_value_with_format_string():
    assert cards._format_value(17_743_429, "£{:,.0f}") == "£17,743,429"


def test_format_value_with_percent_format():
    assert cards._format_value(0.084, "{:.1%}") == "8.4%"


def test_format_value_with_none_returns_em_dash():
    assert cards._format_value(None, "£{:,.0f}") == "—"


# ── _delta_text ─────────────────────────────────────────────────────────────
def test_delta_text_positive():
    assert cards._delta_text(8.1, "vs. Vormonat") == "↑ +8.1%"


def test_delta_text_negative():
    assert cards._delta_text(-3.2, "vs. Vormonat") == "↓ -3.2%"


def test_delta_text_zero_uses_horizontal_arrow():
    assert cards._delta_text(0.0, "vs. Vormonat") == "→ 0.0%"


def test_delta_text_none_returns_empty():
    assert cards._delta_text(None, "vs. Vormonat") == ""


# ── _delta_color ────────────────────────────────────────────────────────────
def test_delta_color_positive_higher_is_better():
    assert cards._delta_color(8.1, higher_is_better=True) == theme.POSITIVE


def test_delta_color_positive_lower_is_better():
    """At-risk customers UP is BAD → red on positive delta."""
    assert cards._delta_color(8.1, higher_is_better=False) == theme.NEGATIVE


def test_delta_color_negative_higher_is_better():
    assert cards._delta_color(-3.2, higher_is_better=True) == theme.NEGATIVE


def test_delta_color_negative_lower_is_better():
    """At-risk customers DOWN is GOOD → green on negative delta."""
    assert cards._delta_color(-3.2, higher_is_better=False) == theme.POSITIVE


def test_delta_color_zero_is_muted():
    assert cards._delta_color(0.0, higher_is_better=True) == theme.MUTED
    assert cards._delta_color(0.0, higher_is_better=False) == theme.MUTED


def test_delta_color_none_is_muted():
    assert cards._delta_color(None, higher_is_better=True) == theme.MUTED
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_ui_cards.py -v`
Expected: all tests FAIL with `ModuleNotFoundError: No module named 'src.ui.cards'`.

- [ ] **Step 3: Create `src/ui/cards.py` with the helpers**

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_ui_cards.py -v`
Expected: all 13 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ui/cards.py tests/test_ui_cards.py
git commit -m "feat(ui): cards.py format/delta helpers"
```

---

## Task 3: Sparkline figure helper

Render a 56 px tall, axis-free Plotly mini-chart from a time series, with an optional dashed-tail split (used by the forecast card) and a colored last-point dot reflecting trend direction.

**Files:**
- Modify: `src/ui/cards.py`
- Modify: `tests/test_ui_cards.py`

- [ ] **Step 1: Append failing tests to `tests/test_ui_cards.py`**

```python
# ── _sparkline_figure ───────────────────────────────────────────────────────
def test_sparkline_figure_with_simple_series():
    s = pd.Series([1, 2, 3, 4, 5])
    fig = cards._sparkline_figure(s, trend_positive=True)
    # one solid line + one last-point dot trace
    assert len(fig.data) == 2
    assert fig.layout.height == 56
    assert fig.layout.xaxis.visible is False
    assert fig.layout.yaxis.visible is False


def test_sparkline_figure_split_renders_three_traces():
    """split_at=4 → solid up to index 4, dashed from index 4, last-point dot."""
    s = pd.Series([1, 2, 3, 4, 5, 6])
    fig = cards._sparkline_figure(s, trend_positive=True, split_at=4)
    assert len(fig.data) == 3
    # Find the dashed trace by line.dash
    dashed = [t for t in fig.data if getattr(t.line, "dash", None) == "dash"]
    assert len(dashed) == 1


def test_sparkline_figure_last_dot_uses_positive_color():
    fig = cards._sparkline_figure(pd.Series([1, 2, 3]), trend_positive=True)
    dot_trace = fig.data[-1]
    assert dot_trace.mode == "markers"
    assert dot_trace.marker.color == theme.POSITIVE


def test_sparkline_figure_last_dot_uses_negative_color_when_trend_down():
    fig = cards._sparkline_figure(pd.Series([3, 2, 1]), trend_positive=False)
    dot_trace = fig.data[-1]
    assert dot_trace.marker.color == theme.NEGATIVE


def test_sparkline_figure_with_none_returns_none():
    """No data → no figure. kpi_card() will leave the slot empty."""
    assert cards._sparkline_figure(None, trend_positive=True) is None


def test_sparkline_figure_empty_series_returns_none():
    assert cards._sparkline_figure(pd.Series([], dtype=float),
                                   trend_positive=True) is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_ui_cards.py -v`
Expected: the 6 new tests FAIL with `AttributeError: module ... has no attribute '_sparkline_figure'`.

- [ ] **Step 3: Append the helper to `src/ui/cards.py`**

Append the following to `src/ui/cards.py` (after the imports, before `_format_value` — keep all helpers grouped; or simply at end of file is fine):

```python
import plotly.graph_objects as go


def _sparkline_figure(
    series: pd.Series | None,
    *,
    trend_positive: bool,
    split_at: int | None = None,
) -> go.Figure | None:
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_ui_cards.py -v`
Expected: all 19 tests PASS (13 + 6).

- [ ] **Step 5: Commit**

```bash
git add src/ui/cards.py tests/test_ui_cards.py
git commit -m "feat(ui): cards.py sparkline helper with optional dashed tail"
```

---

## Task 4: `kpi_card()` composition

The public function — wires the helpers into a Streamlit `st.container(border=True)` with markdown for label/value/delta and an `st.plotly_chart` for the sparkline.

**Files:**
- Modify: `src/ui/cards.py`
- Create: `tests/test_ui_cards_render.py`

- [ ] **Step 1: Write the smoke test**

Create `tests/test_ui_cards_render.py`:

```python
"""Smoke tests for kpi_card() via Streamlit's AppTest.

These don't assert visual properties — they just guarantee the function
runs end-to-end across the relevant value/delta/sparkline permutations
without raising.
"""
import pandas as pd
from streamlit.testing.v1 import AppTest


_SMOKE_SCRIPT = """
import pandas as pd
import streamlit as st
from src.ui import theme
from src.ui.cards import kpi_card

theme.inject_global_css()

c1, c2, c3, c4 = st.columns(4)
with c1:
    kpi_card(
        label="Gesamtumsatz",
        value=17_743_429,
        value_format="£{:,.0f}",
        delta_pct=8.1,
        delta_period="vs. letzte 12 Monate",
        higher_is_better=True,
        sparkline=pd.Series([1, 2, 1.5, 3, 4]),
    )
with c2:
    kpi_card(
        label="At-Risk Kunden",
        value=825,
        value_format="{:,.0f}",
        delta_pct=12.4,
        delta_period="vs. letzte 12 Monate",
        higher_is_better=False,           # up is bad → red
        sparkline=None,                    # no series available
    )
with c3:
    kpi_card(
        label="Forecast",
        value=659_963,
        value_format="£{:,.0f}",
        delta_pct=27.4,
        delta_period="vs. letzter Ist-Monat",
        higher_is_better=True,
        sparkline=pd.Series([1, 2, 3, 4, 5, 6]),
        sparkline_split_at=4,
    )
with c4:
    kpi_card(
        label="Ohne Delta",
        value=None,
        value_format="{:,.0f}",
        delta_pct=None,
        delta_period="",
        higher_is_better=True,
        sparkline=None,
    )
"""


def test_kpi_card_renders_all_variants_without_exception(tmp_path):
    script = tmp_path / "smoke.py"
    script.write_text(_SMOKE_SCRIPT)
    at = AppTest.from_file(str(script))
    at.run(timeout=20)
    assert not at.exception, [e.message for e in at.exception]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_ui_cards_render.py -v`
Expected: FAIL with `ImportError: cannot import name 'kpi_card' from 'src.ui.cards'`.

- [ ] **Step 3: Append `kpi_card()` to `src/ui/cards.py`**

Append:

```python
def kpi_card(
    *,
    label: str,
    value: float | int | None,
    value_format: str = "{:,.0f}",
    delta_pct: float | None = None,
    delta_period: str = "",
    higher_is_better: bool = True,
    sparkline: pd.Series | None = None,
    sparkline_split_at: int | None = None,
    tooltip: str | None = None,
) -> None:
    """Render one KPI card.

    Call inside an ``st.columns(...)`` cell or any other container.
    The function emits a bordered ``st.container`` containing a
    label row, the big number, a delta+period line, and (optionally)
    a sparkline.

    Parameters
    ----------
    label:
        Short uppercase metric name (e.g. "Gesamtumsatz").
    value:
        The metric's current value, or ``None`` to render an em-dash.
    value_format:
        Python format-spec string, applied via ``.format(value)``.
    delta_pct:
        Percentage delta vs. the comparison window (8.1 means +8.1 %).
        Pass ``None`` to omit the delta line entirely.
    delta_period:
        Comparison phrase ("vs. letzte 12 Monate"), rendered to the
        right of the percentage.
    higher_is_better:
        Inverts color semantics when False (used for at-risk
        customers, churn, costs).
    sparkline:
        Numeric pandas Series for the embedded sparkline. ``None`` →
        no sparkline rendered (slot stays empty so layout doesn't
        shift).
    sparkline_split_at:
        Index where the sparkline switches from solid to dashed (used
        by the forecast card to mark the actual→forecast boundary).
    tooltip:
        Optional native browser-tooltip text on the ⓘ icon next to
        the label.
    """
    import streamlit as st  # lazy: keep cards.py importable without ST

    value_str = _format_value(value, value_format)
    delta_str = _delta_text(delta_pct, delta_period)
    delta_color = _delta_color(delta_pct, higher_is_better=higher_is_better)
    trend_positive = (delta_pct is not None and delta_pct >= 0) == higher_is_better

    tooltip_span = (
        f'<span class="kpi-tooltip" title="{tooltip}">&#9432;</span>'
        if tooltip else ""
    )
    delta_html = (
        f'<div class="kpi-delta" style="color:{delta_color}">'
        f'{delta_str}<span class="kpi-delta-period">{delta_period}</span>'
        f'</div>'
    ) if delta_str else '<div class="kpi-delta">&nbsp;</div>'

    body = (
        f'<div class="kpi-card">'
        f'  <div class="kpi-label">'
        f'    <span class="kpi-label-text">{label}</span>{tooltip_span}'
        f'  </div>'
        f'  <div class="kpi-number">{value_str}</div>'
        f'  {delta_html}'
        f'</div>'
    )

    with st.container(border=True):
        st.markdown(body, unsafe_allow_html=True)
        fig = _sparkline_figure(
            sparkline,
            trend_positive=trend_positive,
            split_at=sparkline_split_at,
        )
        if fig is not None:
            from src.ui.viz_theme import PLOTLY_CONFIG  # avoid top-level cycle
            st.plotly_chart(
                fig,
                use_container_width=True,
                theme=None,
                config={**PLOTLY_CONFIG, "staticPlot": True},
            )
```

- [ ] **Step 4: Run the smoke test to verify it passes**

Run: `pytest tests/test_ui_cards_render.py -v`
Expected: PASS. (May take ~10 seconds — Streamlit's AppTest spins up the runtime.)

- [ ] **Step 5: Run the full UI-test suite**

Run: `pytest tests/test_ui_*.py -v`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add src/ui/cards.py tests/test_ui_cards_render.py
git commit -m "feat(ui): kpi_card() — bordered card with sparkline"
```

---

## Task 5: Previous-period delta data helper

A tiny pure function that, given a monthly time series, returns `(current_window_value, delta_pct, monthly_sparkline_series)` for the "last 12 vs previous 12" comparison. Used by `app.py` when computing the overview KPIs.

**Files:**
- Modify: `src/ui/cards.py`
- Modify: `tests/test_ui_cards.py`

- [ ] **Step 1: Append failing tests to `tests/test_ui_cards.py`**

```python
# ── prev_period_delta ───────────────────────────────────────────────────────
def test_prev_period_delta_simple_doubling():
    """Previous 12 sum to 100, current 12 sum to 200 → +100.0 %."""
    idx = pd.date_range("2020-01-01", periods=24, freq="MS")
    values = [100/12] * 12 + [200/12] * 12
    series = pd.Series(values, index=idx)
    current, delta_pct, sparkline = cards.prev_period_delta(series, window=12)
    assert round(current, 2) == 200.0
    assert round(delta_pct, 1) == 100.0
    assert len(sparkline) == 12


def test_prev_period_delta_returns_none_when_too_few_points():
    idx = pd.date_range("2020-01-01", periods=10, freq="MS")
    series = pd.Series(range(10), index=idx)
    current, delta_pct, sparkline = cards.prev_period_delta(series, window=12)
    assert current == series.sum()
    assert delta_pct is None
    assert sparkline.equals(series)


def test_prev_period_delta_window_4():
    idx = pd.date_range("2020-01-01", periods=8, freq="MS")
    series = pd.Series([1, 1, 1, 1, 2, 2, 2, 2], index=idx)
    current, delta_pct, sparkline = cards.prev_period_delta(series, window=4)
    assert current == 8
    assert delta_pct == 100.0
    assert len(sparkline) == 4
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_ui_cards.py -v`
Expected: 3 new tests FAIL.

- [ ] **Step 3: Append `prev_period_delta` to `src/ui/cards.py`**

```python
def prev_period_delta(
    monthly_series: pd.Series,
    *,
    window: int = 12,
) -> tuple[float, float | None, pd.Series]:
    """Sum the last ``window`` months and compare to the previous block.

    Returns ``(current_sum, delta_pct, sparkline_series)``.  When fewer
    than ``2 * window`` data points are available, ``delta_pct`` is
    ``None`` and the sparkline falls back to whatever data exists.
    """
    total_points = len(monthly_series)
    if total_points < 2 * window:
        return float(monthly_series.sum()), None, monthly_series

    current = monthly_series.iloc[-window:]
    previous = monthly_series.iloc[-2 * window : -window]
    current_sum = float(current.sum())
    previous_sum = float(previous.sum())
    if previous_sum == 0:
        return current_sum, None, current

    delta_pct = (current_sum - previous_sum) / previous_sum * 100.0
    return current_sum, delta_pct, current
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_ui_cards.py -v`
Expected: all 22 tests PASS (13 + 6 + 3).

- [ ] **Step 5: Commit**

```bash
git add src/ui/cards.py tests/test_ui_cards.py
git commit -m "feat(ui): cards.prev_period_delta() — last N vs previous N"
```

---

## Task 6: Migrate the Übersicht KPIs in `app.py`

Replace the `render_evidence_strip(...)` call on the Übersicht (lines ~485–492) with a 4-column grid of `kpi_card()`s. Compute the 4 KPI data sets above the render call. **Do not touch** the Forecast tab's later `render_evidence_strip` call (line 555) — that strip is multi-row context, not the headline KPIs.

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Add imports**

Near the top of `app.py` (alongside the Phase 1 polish import), add:

```python
from src.ui.cards import kpi_card, prev_period_delta
from src.ui import theme as ui_theme
```

- [ ] **Step 2: Add a small helper for the active-customers monthly series**

`actuals` is a monthly revenue series. We also need a monthly count of distinct customers. The orders DataFrame lives behind `get_connection()`. Add the following helper at the top of the `with tab1:` block (right after `at_risk_count = ...` and `forecast_base_value = ...` already exist):

In `app.py`, after line 472 (`forecast_base_short = short_baseline_label(...)`), insert:

```python
    # ── Monthly time series for the KPI sparklines ──────────────────────────
    monthly_revenue = (
        actuals.set_index('ds')['y']
        if 'ds' in actuals.columns else actuals
    )

    conn = get_connection()
    monthly_customers = pd.read_sql(
        """
        SELECT strftime('%Y-%m-01', invoice_date) AS month,
               COUNT(DISTINCT customer_id) AS active
          FROM transactions
         WHERE customer_id IS NOT NULL
         GROUP BY 1
         ORDER BY 1
        """,
        conn,
        parse_dates=['month'],
    ).set_index('month')['active']

    rev_current, rev_delta, rev_spark = prev_period_delta(monthly_revenue, window=12)
    cust_current, cust_delta, cust_spark = prev_period_delta(monthly_customers, window=12)

    forecast_history = monthly_revenue.tail(12)
    forecast_series = pd.concat([
        forecast_history,
        pd.Series([next_forecast],
                  index=pd.DatetimeIndex([future_rows['ds'].iloc[0]])),
    ])
```

If the actual column name for the orders table is not `transactions` or for `invoice_date` differs, adjust the SQL — check `src/data_processing.py` for the schema. (The agent's existing KPI helpers may already expose this — search for `compute_agent_kpis` in `src/decision_agent.py`; if a function there already returns monthly active customers, prefer using it over a fresh SQL query.)

- [ ] **Step 3: Replace `render_evidence_strip(...)` with the four cards**

Locate the existing block at lines ~485–492:

```python
    render_evidence_strip([
        ("Umsatz im Zeitraum", f"£{total_revenue:,.0f}"),
        ("Aktive Kunden", f"{total_customers:,}"),
        ("At-Risk Anteil", f"{at_risk_share:.1%}"),
        ("Vergleichsumsatz", f"£{forecast_base_value:,.0f}"),
        ("Prognose nächster Monat", f"£{next_forecast:,.0f}"),
        ("Abweichung zur Vergleichsbasis", f"{forecast_delta:+.1%}"),
    ])
```

Replace with:

```python
    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        kpi_card(
            label="Gesamtumsatz",
            value=rev_current,
            value_format="£{:,.0f}",
            delta_pct=rev_delta,
            delta_period="vs. vorherige 12 Monate",
            higher_is_better=True,
            sparkline=rev_spark,
            tooltip="Summe aller Bestellungen in den letzten 12 Monaten.",
        )
    with c2:
        kpi_card(
            label="Aktive Kunden",
            value=cust_current if cust_delta is None else cust_spark.iloc[-1],
            value_format="{:,.0f}",
            delta_pct=cust_delta,
            delta_period="vs. vorherige 12 Monate",
            higher_is_better=True,
            sparkline=cust_spark,
            tooltip="Distinct Customer-IDs mit mindestens einer Bestellung im Monat.",
        )
    with c3:
        kpi_card(
            label="At-Risk Kunden",
            value=at_risk_count,
            value_format="{:,.0f}",
            delta_pct=None,        # historic at-risk requires per-month RFM; out of scope here
            delta_period="",
            higher_is_better=False,
            sparkline=None,
            tooltip="Kunden im RFM-Segment 'At Risk' (Stand: heute).",
        )
    with c4:
        kpi_card(
            label="Forecast nächster Monat",
            value=next_forecast,
            value_format="£{:,.0f}",
            delta_pct=forecast_delta * 100,         # forecast_delta is a fraction
            delta_period=f"vs. {forecast_base_short}",
            higher_is_better=True,
            sparkline=forecast_series,
            sparkline_split_at=len(forecast_history) - 1,
            tooltip="Prognose des Monatsumsatzes mit Prophet, Vergleich gegen Ist-Basis.",
        )
```

The "Aktive Kunden" value uses the latest month's distinct-customer count when there are enough datapoints (because summing distinct counts over 12 months doesn't make sense). The cleaner semantic — "active customers in the last month" — is what we'd want even after Phase 3 lands.

- [ ] **Step 4: Run the app and verify**

Run: `streamlit run app.py`
Open the Übersicht. Verify:
- 4 cards across the top, equal width
- Each shows label (uppercase), big number, delta line (3 of 4), sparkline (3 of 4)
- At-Risk shows red color cue (would be red if it had a delta — placeholder OK)
- Forecast sparkline has a visible dashed tail (the final segment)
- Numbers align vertically (`tabular-nums` working)
- No traceback in the terminal

If the SQL query in Step 2 errors (table/column name mismatch), open `src/data_processing.py`, find the actual schema, and adjust. Common alternatives: table may be `orders`, date column may be `InvoiceDate` (PascalCase from the UCI dataset).

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "feat(app): replace overview evidence strip with kpi_card grid"
```

---

## Task 7: Clean up legacy CSS + wire `inject_global_css`

Remove the metric-card CSS hack now that `kpi_card` owns its styling, and wire the global CSS injection at the top of `app.py`.

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Call `inject_global_css()` at the top**

Right after `st.set_page_config(...)` (around line 17), insert:

```python
ui_theme.inject_global_css()
```

- [ ] **Step 2: Delete the legacy metric-card CSS block**

In the existing `st.markdown("""<style>...""")` call (starting at line 19), delete these specific lines (~22–28):

```css
    [data-testid="stMetric"] {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 14px 16px;
    }
    [data-testid="stMetricLabel"] { color: #94a3b8; }
```

Also remove the now-redundant `.block-container { padding-top: 2rem; }` (~line 21) — `inject_global_css()` sets this with the spec's correct values.

**Keep** the `.decision-panel`, `.evidence-strip`, `.evidence-item`, `.section-kicker`, `.action-list`, and `.action-item` rules — they're still used by `render_decision_panel`, `render_evidence_strip` (which is still called from the Forecast tab), and `render_action_list`. Those get replaced in Phase 5, not now.

- [ ] **Step 3: Re-run the app and verify**

Run: `streamlit run app.py`
Open the Übersicht and the other tabs. Verify:
- KPI cards still render correctly (same as Task 6)
- The dark "decision panel" at the top of the Übersicht still looks unchanged (it uses `.decision-panel` rules which we kept)
- `st.metric` calls on the Critic page still render — they'll now be the default Streamlit look (no dark background) because we removed that hack. **That is intentional** — Phase 5 will replace them.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "chore(app): wire global css; drop legacy stMetric overrides"
```

---

## Task 8: Full test sweep + final smoke

- [ ] **Step 1: Run all tests**

Run: `pytest tests/ -v`
Expected: every test passes — both Phase 1 tests and Phase 2 tests, plus the unchanged pre-existing tests for `decision_agent`, `decision_log`, `agent_chat`, `critic`.

- [ ] **Step 2: Drift check (left over from Phase 1's Task 12)**

Run: `pytest tests/test_render_streamlit_config.py::test_committed_config_matches_current_theme -v`
Expected: PASS (we didn't touch tokens in Phase 2, so config.toml is still in sync).

- [ ] **Step 3: Manual visual smoke**

Run: `streamlit run app.py`
For the Übersicht specifically, verify against the spec §4 picture:

```
┌──────────────────────────────┐
│ GESAMTUMSATZ          ⓘ      │
│ £…                            │
│ ↑ +x.x%  vs. vorherige 12…    │
│ ▁▂▃▅▆▇█▇▆▅▃▂▁                 │
└──────────────────────────────┘
```

Check:
- All four cards are equal width
- Border + radius look right (1 px, ~12 px corners)
- Numbers render in `tabular-nums` — digits align column-wise across cards if you mentally stack them
- Hover the ⓘ icon → browser shows a native tooltip
- Sparklines are 56 px tall, no axes, no modebar, last-point dot in semantic color
- Forecast card's sparkline visibly transitions to dashed for the last segment
- At-Risk card has no sparkline and no delta line — but the card height matches the others (layout doesn't shift)

If any of these are off, fix in `src/ui/cards.py` or the relevant CSS in `theme.global_css()` rather than per-call workarounds.

- [ ] **Step 4: Final cleanup commit (only if needed)**

```bash
# only if you made tweaks during the smoke test
git status
git add <files>
git commit -m "chore(ui): kpi-card smoke cleanup"
```

---

## Definition of Done — Phase 2

- [ ] `pytest tests/` is green
- [ ] `streamlit run app.py` loads the Übersicht without exception; 4 KPI cards render
- [ ] The four overview KPIs are emitted via `kpi_card(...)`, not `render_evidence_strip`
- [ ] `[data-testid="stMetric"]` CSS rules no longer exist in `app.py`
- [ ] `inject_global_css()` is called once near the top of `app.py`
- [ ] At-Risk card uses `higher_is_better=False` (color semantic inverted) — wired even though no delta is computed in this phase
- [ ] Forecast card's sparkline shows the dashed tail at the actual→forecast boundary

## What's Next (Phase 3 preview)

Phase 3 is the highest-risk phase: it restructures `app.py` into a sidebar-based page-dispatch architecture. We introduce `streamlit-antd-components` for the sidebar menu, `streamlit-shadcn-ui` for the top-bar date-range picker, and split every current tab into its own `src/pages/*.py` file. The KPI cards we just built will keep working unchanged — they're the first thing this architecture is supposed to host without modification.
