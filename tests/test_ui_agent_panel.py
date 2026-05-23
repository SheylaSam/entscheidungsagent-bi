"""Tests for src/ui/agent_panel.py — pure helpers + AppTest smoke."""
from streamlit.testing.v1 import AppTest

from src.ui import agent_panel, theme


# ── _priority_badge ──────────────────────────────────────────────────────────
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


# ── _rec_id ──────────────────────────────────────────────────────────────────
def test_rec_id_uses_existing_id_if_present():
    rec = {"rec_id": "abc-123", "decision": "x"}
    assert agent_panel._rec_id(rec) == "abc-123"


def test_rec_id_falls_back_to_hash_of_decision_and_finding():
    rec = {"decision": "Sortiment bereinigen", "finding": "298 Produkte"}
    rid1 = agent_panel._rec_id(rec)
    rid2 = agent_panel._rec_id(rec)
    assert rid1 == rid2
    assert len(rid1) >= 6


def test_rec_id_differs_for_different_recs():
    a = {"decision": "X", "finding": "1"}
    b = {"decision": "X", "finding": "2"}
    assert agent_panel._rec_id(a) != agent_panel._rec_id(b)


# ── _freshness_line ──────────────────────────────────────────────────────────
def test_freshness_line_with_timestamp():
    line = agent_panel._freshness_line({"timestamp": "2026-05-17T12:00:00Z"})
    assert "2026-05-17" in line or "vor" in line or "gerade" in line


def test_freshness_line_without_timestamp_returns_dash():
    assert agent_panel._freshness_line({}) == "–"


# ── Smoke: full card renders ─────────────────────────────────────────────────
_SMOKE_FULL = """
import streamlit as st
from src.ui import theme
from src.ui.agent_panel import agent_recommendation_card

theme.inject_global_css()

rec = {
    "priority": "HOCH",
    "decision": "Sortiment bereinigen",
    "finding": "298 Produkte zeigen >=3 Monate rueckl. Umsatz.",
    "reasoning": "Ein Drittel des aktiven Sortiments laeuft auf eine Auslistung zu.",
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


# ── Smoke: compact card renders ──────────────────────────────────────────────
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
