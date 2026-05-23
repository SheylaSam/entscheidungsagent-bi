"""Page: Kunden (RFM).

Lifted from Tab 3 of app.py during Phase 3.  No logic changes.
"""
from __future__ import annotations

import plotly.express as px
import streamlit as st

from src.customer_analysis import summarize_segments_by_country
from src.ui import theme
from src.ui.page_loader import load_all, load_customer_country
from src.ui.viz_theme import polish, PLOTLY_CONFIG


def render(filters: dict) -> None:
    """Render the Kunden page.

    Expects in ``filters``: start_date, end_date, countries.
    RFM is always computed on the full dataset history (date filter bypassed).
    """
    countries  = filters["countries"]
    # The At-Risk-by-Country chart legitimately uses the user range
    # (shows the at-risk share within the period of interest), so we
    # still need start_date / end_date:
    start_date = filters["start_date"]
    end_date   = filters["end_date"]

    # RFM is conventionally computed on the full history (recency =
    # days since last order, relative to the most recent date in the
    # dataset).  Bypass the global date filter for the rfm dataframe.
    _FULL_START = "2009-12-01"
    _FULL_END   = "2011-12-09"
    rfm, *_ = load_all(_FULL_START, _FULL_END, countries)

    # ── lifted body ──────────────────────────────────────────────────────
    st.title("Kundensegmentierung — RFM-Analyse")
    st.caption("Recency · Frequency · Monetary | Segmente basierend auf Quintil-Scores")
    st.caption(
        "RFM nutzt die volle Datenhistorie. Recency = Tage seit letzter "
        "Bestellung, bezogen auf den jüngsten Datenpunkt 2011-12-09."
    )

    col_scatter, col_table = st.columns([2, 1])

    with col_scatter:
        st.subheader("RFM Scatter — Recency vs. Frequency", anchor=False)
        st.caption("Blasengrösse = Monetary")
        # RFM scatter is one of the few places categorical color is the point —
        # use the Okabe-Ito palette so all six segments get a distinct,
        # colorblind-safe color (and we stop carrying ad-hoc hex codes).
        fig = px.scatter(rfm, x='recency', y='frequency', size='monetary',
            color='segment',
            color_discrete_sequence=list(theme.CHART_CATEGORICAL),
            hover_data=['customer_id', 'monetary'],
            labels={'recency': 'Recency (Tage)', 'frequency': 'Frequency (Bestellungen)'})
        fig.update_layout(height=400)
        fig = polish(fig)
        fig.update_layout(margin=dict(t=72))  # extra room above for the legend
        st.plotly_chart(fig, use_container_width=True,
                        theme=None, config=PLOTLY_CONFIG)

    with col_table:
        st.subheader("Segmente Übersicht", anchor=False)
        summary = (rfm.groupby('segment')
            .agg(Kunden=('customer_id', 'count'), Umsatz=('monetary', 'sum'))
            .reset_index().sort_values('Umsatz', ascending=False))
        summary['Umsatz'] = summary['Umsatz'].map('£{:,.0f}'.format)
        st.dataframe(summary, use_container_width=True, hide_index=True)

        st.subheader("Top At-Risk Kunden", anchor=False)
        at_risk = (
            rfm[rfm['segment'] == 'At Risk']
            [['customer_id', 'recency', 'frequency', 'monetary']]
            .sort_values('monetary', ascending=False)
            .head(10)
            .copy()
        )
        at_risk['monetary'] = at_risk['monetary'].map('£{:,.0f}'.format)
        at_risk.columns = ['Kunde', 'Recency (Tage)', 'Bestellungen', 'Umsatz']
        st.dataframe(at_risk, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Kundensegmente nach Land", anchor=False)

    customer_country_df = load_customer_country(start_date, end_date, countries)
    country_seg = summarize_segments_by_country(rfm, customer_country_df)

    col_map, col_ctable = st.columns([2, 1])

    with col_map:
        top_n = (country_seg[country_seg['At_Risk'] > 0]
                 .sort_values('At_Risk_%', ascending=False)
                 .head(15))
        fig_c = px.bar(
            top_n,
            x='At_Risk_%', y='country', orientation='h',
            labels={'At_Risk_%': 'At-Risk Anteil', 'country': ''},
            title='At-Risk Anteil pro Land (Top 15, nach % sortiert)',
        )
        fig_c.update_traces(marker_color=theme.CHART_HERO)
        fig_c.update_layout(
            height=400,
            xaxis_title='', yaxis_title='',
            yaxis={'categoryorder': 'total ascending'},
        )
        fig_c = polish(fig_c, hide_legend=True)
        fig_c.update_xaxes(tickformat='.0%')
        fig_c.update_layout(margin=dict(l=160))
        st.plotly_chart(fig_c, use_container_width=True,
                        theme=None, config=PLOTLY_CONFIG)

    with col_ctable:
        display = (country_seg[['country', 'Kunden', 'At_Risk', 'At_Risk_%', 'Umsatz']]
                   .sort_values('At_Risk_%', ascending=False)
                   .copy())
        display['At_Risk_%'] = display['At_Risk_%'].map('{:.0%}'.format)
        display['Umsatz'] = display['Umsatz'].map('£{:,.0f}'.format)
        display.columns = ['Land', 'Kunden', 'At-Risk', 'At-Risk %', 'Umsatz']
        st.dataframe(display, use_container_width=True, hide_index=True, height=420)
