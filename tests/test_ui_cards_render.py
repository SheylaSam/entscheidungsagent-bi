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
        higher_is_better=False,
        sparkline=None,
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
