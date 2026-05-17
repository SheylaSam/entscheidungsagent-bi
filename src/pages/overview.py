"""Page: Übersicht (Overview).

Lifted from Tab 1 of app.py during Phase 3.  No logic changes.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_processing import get_connection
from src.ui import theme
from src.ui.cards import kpi_card, prev_period_delta
from src.ui.agent_panel import agent_recommendation_card
from src.ui.page_loader import forecast_baseline, short_baseline_label
from src.ui.viz_theme import polish, PLOTLY_CONFIG


def render(filters: dict) -> None:
    """Render the Übersicht page.

    Expects in ``filters``:
        actuals, forecast, rfm, recs, forecast_baseline_mode
    """
    actuals                 = filters["actuals"]
    forecast                = filters["forecast"]
    rfm                     = filters["rfm"]
    recs                    = filters["recs"]
    forecast_baseline_mode  = filters["forecast_baseline_mode"]

    # ── lifted body ──────────────────────────────────────────────────────
    st.title("RetailBI Entscheidungsagent")
    st.caption("Online Retail II · Management View · 2009–2011")

    total_revenue = actuals['y'].sum()
    total_customers = rfm['customer_id'].nunique()
    at_risk_count = (rfm['segment'] == 'At Risk').sum()
    at_risk_share = at_risk_count / total_customers if total_customers > 0 else 0
    forecast_base_value, forecast_base_label = forecast_baseline(actuals, forecast_baseline_mode)
    forecast_base_short = short_baseline_label(forecast_base_label)
    future_rows = forecast[forecast['ds'] > actuals['ds'].max()]
    if future_rows.empty:
        st.warning("Forecast enthält keine zukünftigen Datenpunkte. Bitte einen längeren Zeitraum wählen.")
        st.stop()
    next_forecast = future_rows['yhat'].iloc[0]
    forecast_delta = (next_forecast - forecast_base_value) / forecast_base_value
    top_rec = recs[0]

    # ── Monthly time series for the KPI sparklines ──────────────────────────
    monthly_revenue = (
        actuals.set_index('ds')['y']
        if 'ds' in actuals.columns else actuals
    )

    conn = get_connection()
    monthly_customers = pd.read_sql(
        """
        SELECT strftime('%Y-%m-01', invoice_date) AS month,
               COUNT(DISTINCT customer_id) AS active
          FROM transactions
         WHERE customer_id IS NOT NULL
         GROUP BY 1
         ORDER BY 1
        """,
        conn,
        parse_dates=['month'],
    ).set_index('month')['active']

    rev_current, rev_delta, rev_spark = prev_period_delta(monthly_revenue, window=12)
    cust_current, cust_delta, cust_spark = prev_period_delta(monthly_customers, window=12)

    forecast_history = monthly_revenue.tail(12)
    forecast_series = pd.concat([
        forecast_history,
        pd.Series([next_forecast],
                  index=pd.DatetimeIndex([future_rows['ds'].iloc[0]])),
    ])

    agent_recommendation_card(top_rec)
    if len(recs) > 1:
        st.markdown('<div class="section-kicker">Weitere Massnahmen</div>', unsafe_allow_html=True)
        for rec in recs[1:4]:
            agent_recommendation_card(rec, variant='compact')
    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        kpi_card(
            label="Gesamtumsatz",
            value=rev_current,
            value_format="£{:,.0f}",
            delta_pct=rev_delta,
            delta_period="vs. vorherige 12 Monate",
            higher_is_better=True,
            sparkline=rev_spark,
            tooltip="Summe aller Bestellungen in den letzten 12 Monaten.",
        )
    with c2:
        kpi_card(
            label="Aktive Kunden",
            value=cust_current if cust_delta is None else cust_spark.iloc[-1],
            value_format="{:,.0f}",
            delta_pct=cust_delta,
            delta_period="vs. vorherige 12 Monate",
            higher_is_better=True,
            sparkline=cust_spark,
            tooltip="Distinct Customer-IDs mit mindestens einer Bestellung im Monat.",
        )
    with c3:
        kpi_card(
            label="At-Risk Kunden",
            value=at_risk_count,
            value_format="{:,.0f}",
            delta_pct=None,
            delta_period="",
            higher_is_better=False,
            sparkline=None,
            tooltip="Kunden im RFM-Segment 'At Risk' (Stand: heute).",
        )
    with c4:
        kpi_card(
            label="Forecast nächster Monat",
            value=next_forecast,
            value_format="£{:,.0f}",
            delta_pct=forecast_delta * 100,
            delta_period=f"vs. {forecast_base_short}",
            higher_is_better=True,
            sparkline=forecast_series,
            sparkline_split_at=len(forecast_history) - 1,
            tooltip="Prognose des Monatsumsatzes mit Prophet, Vergleich gegen Ist-Basis.",
        )

    st.markdown('<div class="section-kicker">Belege</div>', unsafe_allow_html=True)
    col_left, col_mid = st.columns([1.35, 1])

    with col_left:
        st.subheader("Umsatztrend", anchor=False)
        fig = px.bar(actuals.tail(12), x='ds', y='y', labels={'ds': '', 'y': ''})
        fig.update_layout(height=300)
        fig = polish(fig, y_format=',.0f', hide_legend=True)
        st.plotly_chart(fig, use_container_width=True,
                        theme=None, config=PLOTLY_CONFIG)

    with col_mid:
        st.subheader("Kundensegmente", anchor=False)
        seg_counts = rfm['segment'].value_counts().reset_index()
        # Older pandas calls the count column 'segment' (the column name);
        # newer pandas calls it 'count'. Normalize.
        if 'count' in seg_counts.columns:
            seg_counts = seg_counts.rename(columns={'count': 'Anzahl', 'segment': 'Segment'})
        else:
            seg_counts.columns = ['Segment', 'Anzahl']
        seg_counts = seg_counts.sort_values('Anzahl', ascending=True)
        # Each row carries its semantic color directly.
        seg_counts['_color'] = seg_counts['Segment'].map(
            theme.SEGMENT_SEMANTICS
        ).fillna(theme.MUTED)

        fig2 = px.bar(
            seg_counts, x='Anzahl', y='Segment', orientation='h',
            color='_color', color_discrete_map='identity',
        )
        fig2.update_layout(height=300, yaxis_title='')
        fig2 = polish(fig2, hide_legend=True)
        fig2.update_layout(margin=dict(l=90))
        st.plotly_chart(fig2, use_container_width=True,
                        theme=None, config=PLOTLY_CONFIG)
