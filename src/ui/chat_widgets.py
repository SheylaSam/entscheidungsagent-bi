"""Reusable widgets for the Chat-Agent page.

Currently exposes the default suggestion-chip set and helpers that
emit chips above the chat input and pick up the resulting pending
prompt from session state.
"""
from __future__ import annotations

from typing import Iterable


SUGGESTION_CHIPS: tuple[str, ...] = (
    "Was sollten wir diesen Monat tun?",
    "Welche Produkte zeigen Rückgang?",
    "Wie sehen die At-Risk-Kunden aus?",
    "Wie zuverlässig ist der Forecast?",
)


_PENDING_KEY = "chat_pending_prompt"


def render_suggestion_chips(
    chips: Iterable[str] | None = None,
    *,
    key_prefix: str = "chip",
) -> None:
    """Render a row of clickable suggestion chips above the chat input.

    Each chip is wrapped in a ``<div class="chat-suggestion-chip">`` so
    the global CSS can re-style it as a pill.  Clicking writes the chip
    text into ``st.session_state[_PENDING_KEY]`` and reruns; the chat
    page reads it via :func:`pop_pending_prompt` and submits it as if
    the user had typed it.
    """
    import streamlit as st

    chip_list = list(chips) if chips is not None else list(SUGGESTION_CHIPS)
    if not chip_list:
        return

    cols = st.columns(len(chip_list))
    for i, (col, chip) in enumerate(zip(cols, chip_list)):
        with col:
            st.markdown('<div class="chat-suggestion-chip">',
                        unsafe_allow_html=True)
            if st.button(chip, key=f"{key_prefix}_{i}",
                         use_container_width=True):
                st.session_state[_PENDING_KEY] = chip
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


def pop_pending_prompt() -> str | None:
    """Return and clear any pending prompt set by chip click."""
    import streamlit as st
    return st.session_state.pop(_PENDING_KEY, None)
