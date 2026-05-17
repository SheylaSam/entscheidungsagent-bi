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
