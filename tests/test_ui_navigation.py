"""Minimal unit tests for the navigation module.

The actual `sac.menu` render is covered by manual smoke after Task 11;
here we just verify the public surface exists and that PAGE_KEYS / labels
stay in sync.
"""
from src.ui import navigation


def test_page_keys_match_labels():
    assert set(navigation.PAGE_KEYS) == set(navigation.PAGE_LABELS.keys())


def test_default_active_page_is_overview():
    assert navigation.DEFAULT_PAGE == "overview"


def test_page_keys_exact_order():
    """Order in PAGE_KEYS drives sidebar item order — pin it."""
    assert navigation.PAGE_KEYS == (
        "overview", "forecast", "customers", "products",
        "agent_recs", "chat",
    )


def test_sidebar_nav_is_callable():
    """sidebar_nav must be importable and callable.

    We don't invoke it here because that requires a Streamlit runtime;
    a deeper smoke happens via `streamlit run app.py` after Task 11.
    """
    assert callable(navigation.sidebar_nav)
