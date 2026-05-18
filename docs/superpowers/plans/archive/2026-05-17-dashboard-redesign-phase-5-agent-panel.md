# Dashboard Redesign — Phase 5: Agent Panel Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the dark-block `render_decision_panel` / `render_action_list` / `render_evidence_strip` calls on every page with a single new `agent_recommendation_card()` primitive that has the spec's full feature set (violet 4px left border, sparkle icon, semantic priority badge, evidence drilldown, accept/reject + 👍/👎 buttons, trace-ID, freshness stamp). Also migrate the Critic-Metrik block on the Empfehlungen page from default `st.metric` to `kpi_card()` so it matches Phase 2.

**Architecture:** A new module `src/ui/agent_panel.py` exposes one public function with two variants — `agent_recommendation_card(rec, *, variant='full')` (variant='full' or 'compact'). The existing dark-block legacy renderers stay alive in `src/ui/legacy_renderers.py` for now (they're still used by `render_evidence_strip` on the Forecast tab); only `render_decision_panel` + `render_action_list` get retired from the page call sites. The card's CSS lives in `theme.global_css()` so it's available everywhere `inject_global_css()` has been called (i.e. globally). A small `log_feedback(rec_id, vote)` extends `src/decision_log.py` so 👍/👎 events get persisted in the same JSONL format as outcomes.

**Tech Stack:** Phases 1–4 stack. No new dependencies.

**Reference:** [`docs/superpowers/specs/2026-05-17-dashboard-redesign-design.md`](../specs/2026-05-17-dashboard-redesign-design.md) §6 (the full Agent panel spec).

**Depends on:** Phases 1–4 merged.

**Out of scope:**
- Splitting agent_recommendations.py into separate `agent_history.py` (Phase 7)
- Re-styling `render_evidence_strip` on the Forecast page (still used there; Phase 4 already partially polished those callsites)
- AgGrid table for the Verlauf (Phase 7)
- Suggestion-chips on the chat page (Phase 6)
- Dynamic "history of similar recommendations" link in the card — surface only the count; the dedicated history page comes Phase 7

---

## Recommendation Data Contract

The card expects each `rec` dict to have:

| Key | Type | Purpose | Fallback if missing |
|---|---|---|---|
| `priority` | `'HOCH' \| 'MITTEL' \| 'TIEF' \| 'KRITISCH'` | Drives badge color | `"MITTEL"` |
| `decision` | str | Title (imperative sentence) | `"(unbenannte Empfehlung)"` |
| `finding` | str | One-sentence reason | empty |
| `reasoning` | str | Additional context | empty |
| `utility` | float | Score in £ | not shown |
| `utility_components` | dict | breakdown for evidence | not shown |
| `rule` | str | The fired rule's name (if rule-based) | `"–"` |
| `rec_id` | str | Stable ID for log writes; used as Streamlit `key` | hash of `decision` + `finding` |
| `timestamp` | ISO datetime or str | Freshness display | `"–"` |
| `source_version` | str | e.g. `"rules v0.4"` | omitted |

The current `recs` produced by `src/decision_agent.generate_recommendations` already supplies `priority`, `decision`, `finding`, `reasoning`, `utility`, `utility_components`. The card uses what's there and degrades gracefully.

---

## File Plan

**Create:**
- `src/ui/agent_panel.py` — `agent_recommendation_card`, `_priority_badge`, `_evidence_block`, `_decision_buttons`, `_feedback_buttons`, `_freshness_line`, `_rec_id`
- `tests/test_ui_agent_panel.py` — unit tests for the pure helpers + an AppTest smoke for the card

**Modify:**
- `src/ui/theme.py` — extend `global_css()` with the agent-card class set (`.agent-card`, `.agent-marker`, `.agent-title`, `.agent-priority-badge`, `.agent-meta`)
- `src/decision_log.py` — add `log_feedback(rec_id, vote)` (vote = `'up' | 'down'`) writing to a `feedback.jsonl` next to the existing decision log
- `tests/test_decision_log.py` — add a single test for `log_feedback`
- `src/pages/overview.py` — replace `render_decision_panel(top_rec)` + `render_action_list(recs[1:4])` with `agent_recommendation_card(top_rec)` + a list of compact cards
- `src/pages/forecast.py` — replace `render_decision_panel(forecast_rec, "Forecast-Interpretation")` with the new card
- `src/pages/agent_recommendations.py` — replace every `render_decision_panel` / `render_action_list` call site with the new card; replace the Critic `st.metric` block with `kpi_card` calls

---

## Task 1: Agent-panel CSS in `theme.global_css()`

The card's styling lives in the same `<style>` block that already drives `.kpi-*` classes (Phase 2). Adding it here means every page that called `inject_global_css()` (i.e. all of them, via `app.py`) automatically gets these styles too.

**Files:**
- Modify: `src/ui/theme.py`
- Modify: `tests/test_ui_theme.py`

- [ ] **Step 1: Append failing tests**

Append to `tests/test_ui_theme.py`:

```python
def test_global_css_defines_agent_card_classes():
    css = theme.global_css()
    for cls in (".agent-card", ".agent-marker", ".agent-title",
                ".agent-priority-badge", ".agent-meta", ".agent-finding"):
        assert cls in css, f"missing rule for {cls}"


def test_global_css_agent_marker_uses_ai_accent():
    css = theme.global_css()
    # The 4px left border is the central visual marker for "from the agent"
    assert theme.AI_ACCENT in css
    assert "4px" in css  # border-left width
```

- [ ] **Step 2: Run, verify fail**

`pytest tests/test_ui_theme.py -v` → 2 new tests FAIL.

- [ ] **Step 3: Extend `global_css()` in `src/ui/theme.py`**

Find the closing `</style>` line inside the f-string returned by `global_css()`. **Just before** that closing tag, insert these rules:

```css
/* ── Agent recommendation card (src/ui/agent_panel.py) ───────── */
.agent-card {{
    border: 1px solid {BORDER};
    border-left: 4px solid {AI_ACCENT};
    border-radius: {CARD_RADIUS_REM};
    background: {AI_BG_TINT};
    padding: {CARD_PADDING_PX}px;
    margin: 8px 0 16px;
}}
.agent-card.compact {{ padding: 16px 20px; margin: 6px 0 10px; }}
.agent-marker {{
    display: flex; align-items: center; gap: 10px;
    color: {AI_ACCENT};
    font-family: {FONT_FAMILY};
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-bottom: 8px;
}}
.agent-sparkle {{ font-size: 16px; line-height: 1; }}
.agent-title {{
    color: {HEADING};
    font-family: {FONT_FAMILY};
    font-size: 22px;
    font-weight: 600;
    line-height: 1.25;
    margin: 4px 0 8px;
}}
.agent-card.compact .agent-title {{ font-size: 16px; margin-bottom: 4px; }}
.agent-finding {{
    color: {BODY};
    font-family: {FONT_FAMILY};
    font-size: 14px;
    line-height: 1.5;
    margin-bottom: 10px;
}}
.agent-priority-badge {{
    display: inline-flex; align-items: center; gap: 6px;
    margin-left: auto;
    padding: 3px 10px;
    border-radius: 999px;
    font-family: {FONT_FAMILY};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}}
.agent-priority-badge .dot {{
    width: 8px; height: 8px; border-radius: 999px;
}}
.agent-meta {{
    color: {MUTED};
    font-family: {MONO_FAMILY};
    font-size: 11px;
    margin-top: 10px;
}}
```

- [ ] **Step 4: Run, verify pass**

`pytest tests/test_ui_theme.py -v` → all green.

- [ ] **Step 5: Commit**

```bash
git add src/ui/theme.py tests/test_ui_theme.py
git commit -m "feat(ui): agent-card CSS in global_css() — violet border, sparkle, badge"
```

---

## Task 2: `log_feedback()` in `src/decision_log.py`

A small JSONL writer that 👍/👎 buttons call. Reuses the same file conventions as `log_decision_outcome` (which already exists).

**Files:**
- Modify: `src/decision_log.py`
- Modify: `tests/test_decision_log.py`

- [ ] **Step 1: Append a failing test**

Append to `tests/test_decision_log.py`:

```python
import json


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
    import pytest
    with pytest.raises(ValueError):
        log_feedback("rec-1", "maybe", log_path=tmp_path / "feedback.jsonl")
```

- [ ] **Step 2: Run, verify fail**

`pytest tests/test_decision_log.py::test_log_feedback_writes_jsonl tests/test_decision_log.py::test_log_feedback_rejects_unknown_vote -v` → fail with ImportError.

- [ ] **Step 3: Add `log_feedback` to `src/decision_log.py`**

Append (at the end of the file, after the existing `log_decision_outcome` definition):

```python
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
        Stable recommendation identifier (matches the one the UI shows
        as the trace-ID).
    vote:
        Either ``"up"`` or ``"down"``.
    log_path:
        Override the default path (used by tests).  Default writes to
        ``data/feedback.jsonl`` alongside the existing decision log.
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
```

You'll need `from datetime import datetime` and `import json` at the top if they're not already imported. `DEFAULT_LOG_DIR` is the existing constant in the file (re-use it; don't redefine).

- [ ] **Step 4: Run, verify pass**

`pytest tests/test_decision_log.py -v` → all green (existing + 2 new).

- [ ] **Step 5: Commit**

```bash
git add src/decision_log.py tests/test_decision_log.py
git commit -m "feat(decision-log): log_feedback() for 👍/👎 votes"
```

---

## Task 3: `src/ui/agent_panel.py` — build the card

This is the meatiest task. The card is composed of pure helpers (testable) + a Streamlit-side render function (smoke-testable).

**Files:**
- Create: `src/ui/agent_panel.py`
- Create: `tests/test_ui_agent_panel.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_ui_agent_panel.py`:

```python
"""Unit tests for src/ui/agent_panel.py pure helpers + a smoke test
for agent_recommendation_card() via Streamlit AppTest."""
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.ui import agent_panel, theme


# ── _priority_badge (HTML string) ───────────────────────────────────────────
def test_priority_badge_high_is_negative():
    html = agent_panel._priority_badge("HOCH")
    assert "HOCH" in html
    assert theme.NEGATIVE in html


def test_priority_badge_medium_is_warning():
    html = agent_panel._priority_badge("MITTEL")
    assert "MITTEL" in html
    assert theme.WARNING in html


def test_priority_badge_low_is_positive():
    html = agent_panel._priority_badge("TIEF")
    assert "TIEF" in html
    assert theme.POSITIVE in html


def test_priority_badge_critical_is_negative():
    html = agent_panel._priority_badge("KRITISCH")
    assert theme.NEGATIVE in html


def test_priority_badge_unknown_is_muted():
    html = agent_panel._priority_badge("WHATEVER")
    assert theme.MUTED in html


# ── _rec_id ─────────────────────────────────────────────────────────────────
def test_rec_id_uses_existing_id_if_present():
    rec = {"rec_id": "abc-123", "decision": "x"}
    assert agent_panel._rec_id(rec) == "abc-123"


def test_rec_id_falls_back_to_hash_of_decision_and_finding():
    rec = {"decision": "Sortiment bereinigen", "finding": "298 Produkte"}
    rid1 = agent_panel._rec_id(rec)
    rid2 = agent_panel._rec_id(rec)
    assert rid1 == rid2  # stable
    assert len(rid1) >= 6  # short fingerprint


def test_rec_id_differs_for_different_recs():
    a = {"decision": "X", "finding": "1"}
    b = {"decision": "X", "finding": "2"}
    assert agent_panel._rec_id(a) != agent_panel._rec_id(b)


# ── _freshness_line ─────────────────────────────────────────────────────────
def test_freshness_line_with_timestamp():
    line = agent_panel._freshness_line({"timestamp": "2026-05-17T12:00:00Z"})
    assert "2026-05-17" in line or "vor" in line


def test_freshness_line_without_timestamp_returns_dash():
    assert agent_panel._freshness_line({}) == "–"


# ── Smoke: full card renders ────────────────────────────────────────────────
_SMOKE_FULL = """
import streamlit as st
from src.ui import theme
from src.ui.agent_panel import agent_recommendation_card

theme.inject_global_css()

rec = {
    "priority": "HOCH",
    "decision": "Sortiment bereinigen",
    "finding": "298 Produkte zeigen ≥3 Monate rückläufigen Umsatz.",
    "reasoning": "Ein Drittel des aktiven Sortiments läuft auf eine Auslistung zu.",
    "utility": 12_400.0,
    "utility_components": {"expected_impact_gbp": 12400, "urgency": 0.8, "confidence": 0.6},
    "rule": "revenue_decline",
    "timestamp": "2026-05-17T12:00:00Z",
    "source_version": "rules v0.4",
}
agent_recommendation_card(rec)
"""


def test_full_card_renders_without_exception(tmp_path):
    script = tmp_path / "smoke.py"
    script.write_text(_SMOKE_FULL)
    at = AppTest.from_file(str(script))
    at.run(timeout=20)
    assert not at.exception, [e.message for e in at.exception]


# ── Smoke: compact card renders ─────────────────────────────────────────────
_SMOKE_COMPACT = """
import streamlit as st
from src.ui import theme
from src.ui.agent_panel import agent_recommendation_card

theme.inject_global_css()

rec = {"priority": "MITTEL", "decision": "Folge-Aktion X", "finding": "kurz"}
agent_recommendation_card(rec, variant='compact')
"""


def test_compact_card_renders_without_exception(tmp_path):
    script = tmp_path / "smoke.py"
    script.write_text(_SMOKE_COMPACT)
    at = AppTest.from_file(str(script))
    at.run(timeout=20)
    assert not at.exception, [e.message for e in at.exception]
```

- [ ] **Step 2: Run, verify they fail**

`pytest tests/test_ui_agent_panel.py -v` → ModuleNotFoundError.

- [ ] **Step 3: Create `src/ui/agent_panel.py`**

```python
"""Agent recommendation card — the canonical AI-surface primitive.

Used everywhere the dashboard shows a generated recommendation
(Übersicht top card, Empfehlungen list, Forecast interpretation, etc.).

See: docs/superpowers/specs/2026-05-17-dashboard-redesign-design.md §6
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Literal

from src.ui import theme

Variant = Literal["full", "compact"]


# ── Priority → semantic color ──────────────────────────────────────────────
_PRIORITY_COLORS: dict[str, str] = {
    "KRITISCH": theme.NEGATIVE,
    "HOCH":     theme.NEGATIVE,
    "MITTEL":   theme.WARNING,
    "TIEF":     theme.POSITIVE,
}


def _priority_badge(priority: str) -> str:
    """Return the HTML for a single priority badge (uppercase pill)."""
    color = _PRIORITY_COLORS.get(priority.upper() if priority else "", theme.MUTED)
    return (
        f'<span class="agent-priority-badge" '
        f'style="background:{color}1A; color:{color};">'
        f'<span class="dot" style="background:{color}"></span>'
        f'PRIORITÄT {priority}'
        f'</span>'
    )


# ── Stable recommendation ID for streamlit widget keys & log writes ────────
def _rec_id(rec: dict) -> str:
    """Return an existing rec_id or derive a short fingerprint."""
    if rec.get("rec_id"):
        return str(rec["rec_id"])
    raw = f"{rec.get('decision', '')}|{rec.get('finding', '')}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]


# ── Freshness display ──────────────────────────────────────────────────────
def _freshness_line(rec: dict) -> str:
    """Return a short freshness label, e.g. "vor 12 Min" or "–"."""
    ts = rec.get("timestamp")
    if not ts:
        return "–"
    try:
        # Accept Z suffix as UTC
        if isinstance(ts, str) and ts.endswith("Z"):
            ts_dt = datetime.fromisoformat(ts[:-1]).replace(tzinfo=timezone.utc)
        elif isinstance(ts, str):
            ts_dt = datetime.fromisoformat(ts)
        else:
            ts_dt = ts
    except ValueError:
        return str(ts)

    now = datetime.now(timezone.utc) if ts_dt.tzinfo else datetime.utcnow()
    delta = now - ts_dt
    seconds = delta.total_seconds()
    if seconds < 60:
        return "gerade eben"
    if seconds < 3600:
        return f"vor {int(seconds / 60)} Min"
    if seconds < 86400:
        return f"vor {int(seconds / 3600)} Std"
    days = int(seconds / 86400)
    if days < 30:
        return f"vor {days} Tag" + ("" if days == 1 else "en")
    return ts_dt.strftime("%Y-%m-%d")


# ── Card sections ──────────────────────────────────────────────────────────
def _marker_row_html(priority: str) -> str:
    badge = _priority_badge(priority)
    return (
        '<div class="agent-marker" style="display:flex;align-items:center;width:100%;">'
        '  <span class="agent-sparkle">✦</span>'
        '  <span>AGENT-EMPFEHLUNG</span>'
        f'  {badge}'
        '</div>'
    )


def _title_html(rec: dict) -> str:
    title = rec.get("decision") or "(unbenannte Empfehlung)"
    return f'<div class="agent-title">{title}</div>'


def _finding_html(rec: dict) -> str:
    finding = rec.get("finding", "")
    reasoning = rec.get("reasoning", "")
    parts = []
    if finding:
        parts.append(finding)
    if reasoning:
        parts.append(reasoning)
    text = " ".join(parts) if parts else ""
    if not text:
        return ""
    return f'<div class="agent-finding">{text}</div>'


def _meta_html(rec: dict) -> str:
    rid = _rec_id(rec)
    freshness = _freshness_line(rec)
    source = rec.get("source_version", "rules v0.4")
    return (
        '<div class="agent-meta">'
        f'aktualisiert: {freshness} · Quelle: {source} · Trace #{rid}'
        '</div>'
    )


# ── Public surface ─────────────────────────────────────────────────────────
def agent_recommendation_card(
    rec: dict,
    *,
    variant: Variant = "full",
) -> None:
    """Render one recommendation card.

    Parameters
    ----------
    rec:
        Recommendation dict.  See the spec/plan for expected keys; the
        card degrades gracefully when keys are missing.
    variant:
        ``"full"`` (default) renders the complete card with evidence
        drilldown and action buttons. ``"compact"`` renders a slim
        variant for stacked follow-up lists (no evidence drilldown,
        no buttons — just marker + title + finding).
    """
    import streamlit as st

    rid = _rec_id(rec)
    css_class = "agent-card" + (" compact" if variant == "compact" else "")

    header_html = (
        f'<div class="{css_class}">'
        f'{_marker_row_html(rec.get("priority", "MITTEL"))}'
        f'{_title_html(rec)}'
        f'{_finding_html(rec)}'
        '</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)

    if variant == "compact":
        return

    # ── Evidence drilldown ────────────────────────────────────────────────
    with st.expander("Evidenz ansehen", expanded=False):
        rule = rec.get("rule", "–")
        st.markdown(f"**Regel:** `{rule}`")
        utility = rec.get("utility")
        if utility:
            comps = rec.get("utility_components", {})
            st.markdown(
                f"**Nutzen-Score:** £{utility:,.0f}  "
                f"_(Impact £{comps.get('expected_impact_gbp', 0):,.0f} · "
                f"Dringlichkeit {comps.get('urgency', 0):.2f} · "
                f"Konfidenz {comps.get('confidence', 0):.2f})_"
            )
        evidence_rows = rec.get("evidence_rows")
        if evidence_rows is not None and len(evidence_rows) > 0:
            st.dataframe(
                evidence_rows.head(10) if hasattr(evidence_rows, "head")
                else evidence_rows[:10],
                use_container_width=True, hide_index=True,
            )

    # ── Decision + feedback buttons ───────────────────────────────────────
    col_accept, col_reject, col_thumbs_up, col_thumbs_down, col_spacer = (
        st.columns([1.2, 1.2, 0.4, 0.4, 4])
    )
    with col_accept:
        if st.button("Akzeptieren", key=f"accept_{rid}", type="primary"):
            from src.decision_log import log_decision_outcome
            try:
                log_decision_outcome(rid, "accepted")
                st.toast("Empfehlung akzeptiert.")
            except Exception as e:                            # noqa: BLE001
                st.warning(f"Konnte Outcome nicht loggen: {e}")
    with col_reject:
        if st.button("Verwerfen", key=f"reject_{rid}"):
            from src.decision_log import log_decision_outcome
            try:
                log_decision_outcome(rid, "rejected")
                st.toast("Empfehlung verworfen.")
            except Exception as e:                            # noqa: BLE001
                st.warning(f"Konnte Outcome nicht loggen: {e}")
    with col_thumbs_up:
        if st.button("👍", key=f"fb_up_{rid}", help="Empfehlung war hilfreich"):
            from src.decision_log import log_feedback
            log_feedback(rid, "up")
            st.toast("Feedback gespeichert.")
    with col_thumbs_down:
        if st.button("👎", key=f"fb_down_{rid}", help="Empfehlung war nicht hilfreich"):
            from src.decision_log import log_feedback
            log_feedback(rid, "down")
            st.toast("Feedback gespeichert.")

    # ── Freshness / source meta ──────────────────────────────────────────
    st.markdown(_meta_html(rec), unsafe_allow_html=True)
```

The `log_decision_outcome` signature is whatever's already in `src/decision_log.py` — check it. If the existing signature takes `(rec_id, status)`, the calls above are correct. If it takes different args, adapt them.

- [ ] **Step 4: Run tests, verify they pass**

`pytest tests/test_ui_agent_panel.py -v` → all green (12 unit + 2 smoke).

`pytest tests/ -q` → full suite green.

- [ ] **Step 5: Commit**

```bash
git add src/ui/agent_panel.py tests/test_ui_agent_panel.py
git commit -m "feat(ui): agent_recommendation_card with violet accent + actions"
```

---

## Task 4: Critic metrics → kpi_card on Empfehlungen page

The Critic section currently uses default `st.metric` widgets (which lost their dark styling in Phase 2). Replace with the styled `kpi_card` so they match Phase 2 visual language.

**Files:**
- Modify: `src/pages/agent_recommendations.py`

- [ ] **Step 1: Locate the Critic metric block**

```bash
grep -n "analyze_decision_history\|st.metric" src/pages/agent_recommendations.py
```

Expect to see ~3 `st.metric(...)` calls in the Critic section (around the "Lern-Loop · Kritik-Komponente" subheader).

- [ ] **Step 2: Replace each `st.metric(...)` with `kpi_card(...)`**

Add the import at the top of `src/pages/agent_recommendations.py`:

```python
from src.ui.cards import kpi_card
```

Replace each `st.metric(label, value)` call with the matching `kpi_card(label=..., value=..., value_format=..., delta_pct=None, delta_period="", higher_is_better=True, sparkline=None, ...)`. For "Agent-Läufe gesamt" / "Mit Outcome" use `value_format="{:,.0f}"`; for accept-rate style metrics that are percentages, use `value_format="{:.1%}"`.

Wrap them in `st.columns(3)` (or however many there are) so they sit in a row, similar to the Übersicht overview KPIs.

Example:

```python
critique = analyze_decision_history()
c1, c2, c3 = st.columns(3)
with c1:
    kpi_card(
        label="Agent-Läufe gesamt",
        value=critique['run_count'],
        value_format="{:,.0f}",
        delta_pct=None, delta_period="",
        higher_is_better=True,
        sparkline=None,
    )
with c2:
    kpi_card(
        label="Mit Outcome",
        value=critique['outcome_count'],
        value_format="{:,.0f}",
        delta_pct=None, delta_period="",
        higher_is_better=True,
        sparkline=None,
    )
with c3:
    # If critique exposes an accept-rate or similar percentage:
    kpi_card(
        label="Akzeptanzrate",
        value=critique.get('accept_rate', 0.0),
        value_format="{:.1%}",
        delta_pct=None, delta_period="",
        higher_is_better=True,
        sparkline=None,
    )
```

**Verify the actual `critique` dict structure first** — read the relevant `analyze_decision_history` function in `src/critic.py`. The keys above are illustrative; transcribe what's actually there.

- [ ] **Step 3: Smoke + commit**

```bash
python -c "from src.pages import agent_recommendations" 2>&1 | head -5
pytest tests/ -q 2>&1 | tail -3
git add src/pages/agent_recommendations.py
git commit -m "polish(agent): Critic-Metriken auf kpi_card umgestellt"
```

---

## Task 5: Migrate Übersicht page

Replace `render_decision_panel(top_rec)` and `render_action_list(recs[1:4])` with the new agent cards.

**Files:**
- Modify: `src/pages/overview.py`

- [ ] **Step 1: Replace the two calls**

Locate this block in `overview.py`:

```python
    render_decision_panel(top_rec)
    if len(recs) > 1:
        st.markdown('<div class="section-kicker">Weitere Massnahmen</div>',
                    unsafe_allow_html=True)
        render_action_list(recs[1:4])
```

Replace with:

```python
    agent_recommendation_card(top_rec)
    if len(recs) > 1:
        st.markdown('<div class="section-kicker">Weitere Massnahmen</div>',
                    unsafe_allow_html=True)
        for rec in recs[1:4]:
            agent_recommendation_card(rec, variant='compact')
```

Update imports at the top of the file: remove the legacy imports if they're now unused:

```python
# old:
from src.ui.legacy_renderers import render_decision_panel, render_action_list
# new:
from src.ui.agent_panel import agent_recommendation_card
```

Be careful: `render_decision_panel` and `render_action_list` may also be referenced elsewhere on the same page — grep before removing the imports. If they're unused after this swap, remove the import lines; if still used, leave the imports and just add the new one.

- [ ] **Step 2: Smoke + commit**

```bash
python -c "from src.pages import overview" 2>&1 | head -5
git add src/pages/overview.py
git commit -m "feat(overview): use agent_recommendation_card for top + follow-up recs"
```

---

## Task 6: Migrate Forecast page

The Forecast page has one `render_decision_panel(forecast_rec, "Forecast-Interpretation")` call. The `forecast_rec` dict is constructed inline from the forecast results (priority, decision, finding, reasoning). It maps directly onto the agent card.

**Files:**
- Modify: `src/pages/forecast.py`

- [ ] **Step 1: Replace the call**

Locate the line:

```python
    render_decision_panel(forecast_rec, "Forecast-Interpretation")
```

Replace with:

```python
    agent_recommendation_card(forecast_rec)
```

The "Forecast-Interpretation" eyebrow is dropped — the agent-card's "AGENT-EMPFEHLUNG" marker is the new universal eyebrow.

Update imports: remove `render_decision_panel` from the `legacy_renderers` import line (keep `render_evidence_strip` if it's still used elsewhere on the page — grep to confirm). Add:

```python
from src.ui.agent_panel import agent_recommendation_card
```

- [ ] **Step 2: Smoke + commit**

```bash
python -c "from src.pages import forecast" 2>&1 | head -5
git add src/pages/forecast.py
git commit -m "feat(forecast): use agent_recommendation_card for forecast interpretation"
```

---

## Task 7: Migrate agent_recommendations page

This page has multiple `render_decision_panel` / `render_action_list` calls. Replace each.

**Files:**
- Modify: `src/pages/agent_recommendations.py`

- [ ] **Step 1: Audit the call sites**

```bash
grep -n "render_decision_panel\|render_action_list" src/pages/agent_recommendations.py
```

You'll see multiple sites. For each:
- `render_decision_panel(rec, eyebrow)` → `agent_recommendation_card(rec)` (eyebrow is implicit)
- `render_action_list(recs)` → loop with `agent_recommendation_card(rec, variant='compact')`

- [ ] **Step 2: Replace systematically**

Walk through each call site. Update the imports at the top of the file:

```python
from src.ui.agent_panel import agent_recommendation_card
# remove if no longer needed: render_decision_panel, render_action_list
# keep if still used: render_evidence_strip, render_agent_trace, render_guardrails
```

Keep `render_evidence_strip`, `render_agent_trace`, `render_guardrails` — those are still useful on this page and aren't part of Phase 5's scope.

- [ ] **Step 3: Smoke + commit**

```bash
python -c "from src.pages import agent_recommendations" 2>&1 | head -5
pytest tests/ -q 2>&1 | tail -3
git add src/pages/agent_recommendations.py
git commit -m "feat(agent): replace decision panels with agent_recommendation_card"
```

---

## Task 8: Final smoke + handoff

- [ ] **Step 1: Full test sweep**

```bash
pytest tests/ -q 2>&1 | tail -5
```
Expected: 156 + ~12 new from agent_panel ≈ 168 passing.

- [ ] **Step 2: Static asserts**

```bash
grep -rn "render_decision_panel\|render_action_list" src/pages/
```
Expected: NO matches in `src/pages/` (all migrated). The function definitions in `src/ui/legacy_renderers.py` can stay — they're harmless dead code now and Phase 7 can prune them.

```bash
grep -rn "agent_recommendation_card" src/pages/ | wc -l
```
Expected: ≥ 4 references (overview top + at least one compact in overview loop, forecast, agent_recommendations).

```bash
grep -c "st.metric" src/pages/agent_recommendations.py
```
Expected: 0 (all moved to kpi_card).

- [ ] **Step 3: Headless smoke**

```bash
streamlit run app.py --server.headless true --server.port 8592 > /tmp/p5smoke.log 2>&1 &
PID=$!
sleep 4
curl -s -o /dev/null -w "HTTP %{http_code}\n" "http://localhost:8592"
curl -s "http://localhost:8592/_stcore/health"
kill $PID 2>/dev/null
wait $PID 2>/dev/null
```
Expected: HTTP 200 + `ok`.

- [ ] **Step 4: User visual handoff**

Walk through:
- **Übersicht** → Top recommendation now has violet left border + ✦ + priority badge + Akzept/Verwerf + 👍/👎. Follow-up recommendations below "Weitere Massnahmen" are compact cards (same violet styling, smaller padding, no buttons).
- **Forecast** → Forecast interpretation panel uses the new card.
- **Empfehlungen** → Every recommendation block on this page uses the new card. Critic-Metriken are now KPI cards matching the Übersicht.
- **Other pages** → Unchanged.

Clicking Akzept/Verwerf writes to the decision log (`data/logs/decisions/` or wherever `DEFAULT_LOG_DIR` points). Clicking 👍/👎 writes to `feedback.jsonl` in the same directory.

---

## Definition of Done — Phase 5

- [ ] `pytest tests/` is green
- [ ] `streamlit run app.py` runs without exceptions
- [ ] `src/pages/` contains zero calls to `render_decision_panel` / `render_action_list`
- [ ] `src/ui/agent_panel.py` is the only module that renders the violet recommendation card
- [ ] `src/ui/theme.global_css()` includes the agent-card class rules
- [ ] `src/decision_log.py` exports `log_feedback`
- [ ] Critic page section uses `kpi_card` (no `st.metric` left on that page)

## What's Next (Phase 6 preview)

Phase 6 polishes the Chat-Agent page: dynamic suggestion-chips above the input row, message-bubble styling that matches the agent-card violet for AI responses and neutral for user prompts, inline pill rendering when AI cites KPIs or row counts, sparkle icon on the AI side. Plus the small `streamlit-shadcn-ui` swap for the date-range picker if we still think it's worth the iframe overhead.
