"""Shallow smoke tests for each page module."""
import importlib
import pytest


PAGE_MODULES = [
    "src.pages.overview",
    "src.pages.forecast",
    "src.pages.customers",
    "src.pages.products",
    "src.pages.agent_recommendations",
    "src.pages.chat",
]


@pytest.mark.parametrize("module_name", PAGE_MODULES)
def test_page_module_imports_and_exposes_render(module_name):
    mod = importlib.import_module(module_name)
    assert hasattr(mod, "render"), f"{module_name} missing render()"
    assert callable(mod.render), f"{module_name}.render is not callable"
