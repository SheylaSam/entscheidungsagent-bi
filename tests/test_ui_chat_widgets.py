"""Tests for src/ui/chat_widgets.py."""
from src.ui import chat_widgets


def test_default_suggestion_chips_exists():
    chips = chat_widgets.SUGGESTION_CHIPS
    assert isinstance(chips, tuple)
    assert len(chips) >= 3
    assert all(isinstance(c, str) and len(c) > 0 for c in chips)


def test_chips_are_unique():
    assert len(set(chat_widgets.SUGGESTION_CHIPS)) == len(chat_widgets.SUGGESTION_CHIPS)


def test_render_suggestion_chips_is_callable():
    assert callable(chat_widgets.render_suggestion_chips)


def test_pop_pending_prompt_is_callable():
    assert callable(chat_widgets.pop_pending_prompt)
