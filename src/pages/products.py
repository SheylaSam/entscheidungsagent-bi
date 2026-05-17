"""Page: Produkte.

Lifted from Tab 4 of app.py during Phase 3.  No logic changes.
"""
from __future__ import annotations

import plotly.express as px
import streamlit as st

from src.ui.legacy_renderers import render_decision_panel, render_evidence_strip
from src.ui.page_loader import load_monthly_product, load_revenue_by_country
from src.ui.viz_theme import polish, PLOTLY_CONFIG


def render(filters: dict) -> None:
    """Render the Produkte page.

    Expects in ``filters``:
        declining, top_products, country_seg, start_date, end_date, countries,
        top_n_products, min_product_revenue, monthly_product_df, revenue_by_country_df
    """
    declining            = filters["declining"]
    top_products         = filters["top_products"]
    country_seg          = filters["country_seg"]
    start_date           = filters["start_date"]
    end_date             = filters["end_date"]
    countries            = filters["countries"]
    top_n_products       = filters["top_n_products"]
    min_product_revenue  = filters["min_product_revenue"]
    monthly_product_df   = filters["monthly_product_df"]
    revenue_by_country_df = filters["revenue_by_country_df"]

    # ── lifted body ──────────────────────────────────────────────────────
    st.title("Produkt-Performance")
    st.caption(f"Top-Produkte nach Umsatz · Rückläufige Produkte · Mindestumsatz £{min_product_revenue:,.0f}")

    col_top, col_decline = st.columns(2)

    with col_top:
        st.subheader(f"Top {top_n_products} Produkte", anchor=False)
        if top_products.empty:
            st.info("Keine Produkte erfüllen den gewählten Mindestumsatz.")
            selection = None
        else:
            fig = px.bar(top_products, x='revenue', y='description', orientation='h',
                labels={'revenue': '', 'description': ''},
                color='revenue', color_continuous_scale='Blues')
            fig.update_layout(height=380, coloraxis_showscale=False, yaxis={'categoryorder': 'total ascending'})
            fig = polish(fig, hide_legend=True)
            fig.update_xaxes(tickformat=',.0f')
            fig.update_layout(margin=dict(l=220))  # wide left margin for product names
            selection = st.plotly_chart(fig, use_container_width=True,
                                        theme=None, config=PLOTLY_CONFIG,
                                        on_select="rerun", key="top_products_chart")

    with col_decline:
        st.subheader(f"Rückläufige Produkte ({len(declining)})", anchor=False)
        if len(declining) == 0:
            st.success("Keine Produkte mit ≥3 Monaten rückläufigem Umsatz.")
        else:
            st.warning(f"{len(declining)} Produkte zeigen anhaltenden Umsatzrückgang.")
            d = declining[['stock_code', 'description', 'revenue_last_month']].copy()
            d['revenue_last_month'] = d['revenue_last_month'].map('£{:,.0f}'.format)
            d.columns = ['Stock Code', 'Bezeichnung', 'Umsatz (letzter Monat)']
            st.dataframe(d, use_container_width=True, hide_index=True)

    # Drill-down: show monthly trend for selected product
    selected_product = None
    try:
        points = selection["selection"]["points"] if selection is not None else []
        if points:
            selected_product = points[0]["y"]
    except (KeyError, TypeError, IndexError):
        pass

    if selected_product:
        st.divider()
        st.subheader(f"Monatlicher Umsatz: {selected_product}", anchor=False)
        product_monthly = monthly_product_df[monthly_product_df['description'] == selected_product]
        if not product_monthly.empty:
            fig_trend = px.line(
                product_monthly, x='month', y='revenue',
                labels={'month': 'Monat', 'revenue': 'Umsatz (£)'},
                markers=True,
            )
            fig_trend.update_traces(line_color='#60a5fa', marker_color='#3b82f6')
            fig_trend.update_layout(height=300, xaxis_title='', yaxis_title='')
            fig_trend = polish(fig_trend, y_format=',.0f')
            st.plotly_chart(fig_trend, use_container_width=True,
                            theme=None, config=PLOTLY_CONFIG)
        else:
            st.info("Keine Monatsdaten für dieses Produkt.")
    else:
        st.caption("Klicke auf ein Produkt im Balkendiagramm, um den monatlichen Umsatzverlauf zu sehen.")

    # ── Umsatz nach Land ──────────────────────────────────────────────────────
    st.divider()
    st.subheader("Umsatz nach Land", anchor=False)
    st.caption("Top 15 Länder nach Gesamtumsatz im gewählten Zeitraum.")

    top_countries = revenue_by_country_df.head(15).copy()
    col_country_chart, col_country_table = st.columns([2, 1])

    with col_country_chart:
        fig_country = px.bar(
            top_countries, x='revenue', y='country', orientation='h',
            labels={'revenue': 'Umsatz (£)', 'country': ''},
            color='revenue', color_continuous_scale='Blues',
        )
        fig_country.update_layout(
            height=420, coloraxis_showscale=False,
            yaxis={'categoryorder': 'total ascending'},
            xaxis_title='', yaxis_title='',
        )
        fig_country = polish(fig_country, hide_legend=True)
        fig_country.update_xaxes(tickformat=',.0f')
        fig_country.update_layout(margin=dict(l=140))  # wide left margin for country names
        st.plotly_chart(fig_country, use_container_width=True,
                        theme=None, config=PLOTLY_CONFIG)

    with col_country_table:
        display_countries = top_countries.copy()
        display_countries['revenue'] = display_countries['revenue'].map('£{:,.0f}'.format)
        display_countries.columns = ['Land', 'Umsatz', 'Kunden']
        st.dataframe(display_countries, use_container_width=True, hide_index=True, height=420)
