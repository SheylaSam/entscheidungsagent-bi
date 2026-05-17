"""Sidebar navigation built with streamlit-antd-components.

Public API:
    PAGE_KEYS     -- canonical ordered tuple of page keys
    PAGE_LABELS   -- key -> display label
    DEFAULT_PAGE  -- the key shown on first visit
    sidebar_nav() -> str   -- renders the menu, returns the active key
"""
from __future__ import annotations

import streamlit as st
import streamlit_antd_components as sac


PAGE_KEYS: tuple[str, ...] = (
    "overview", "forecast", "customers", "products",
    "agent_recs", "chat",
)

PAGE_LABELS: dict[str, str] = {
    "overview":   "Übersicht",
    "forecast":   "Forecast",
    "customers":  "Kunden",
    "products":   "Produkte",
    "agent_recs": "Empfehlungen",
    "chat":       "Chat-Agent",
}

# Bootstrap-icon names (used by streamlit-antd-components by default).
_PAGE_ICONS: dict[str, str] = {
    "overview":   "bar-chart",
    "forecast":   "graph-up",
    "customers":  "people",
    "products":   "box",
    "agent_recs": "stars",
    "chat":       "chat-dots",
}

DEFAULT_PAGE: str = "overview"


def _menu_items() -> list:
    return [
        sac.MenuItem(label="ANALYTICS", type="group", children=[
            sac.MenuItem(PAGE_LABELS["overview"],   icon=_PAGE_ICONS["overview"]),
            sac.MenuItem(PAGE_LABELS["forecast"],   icon=_PAGE_ICONS["forecast"]),
            sac.MenuItem(PAGE_LABELS["customers"],  icon=_PAGE_ICONS["customers"]),
            sac.MenuItem(PAGE_LABELS["products"],   icon=_PAGE_ICONS["products"]),
        ]),
        sac.MenuItem(label="AGENT", type="group", children=[
            sac.MenuItem(PAGE_LABELS["agent_recs"], icon=_PAGE_ICONS["agent_recs"]),
            sac.MenuItem(PAGE_LABELS["chat"],       icon=_PAGE_ICONS["chat"]),
        ]),
    ]


def sidebar_nav() -> str:
    """Render the sidebar menu; return the active page key.

    The label-to-key mapping is internal so renaming a label later
    doesn't break the dispatch table.
    """
    with st.sidebar:
        selected_label = sac.menu(
            items=_menu_items(),
            open_all=True,
            indent=18,
            size="md",
            key="sidebar_nav_menu",
        )

    label_to_key = {v: k for k, v in PAGE_LABELS.items()}
    active_key = label_to_key.get(selected_label, DEFAULT_PAGE)
    st.session_state["active_page"] = active_key
    return active_key
