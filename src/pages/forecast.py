"""Page: Forecast & Umsatzrisiko.

Lifted from Tab 2 of app.py during Phase 3.  No logic changes.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.ui.legacy_renderers import render_decision_panel, render_evidence_strip
from src.ui.page_loader import (
    forecast_baseline, short_baseline_label, load_backtest,
)
from src.ui.viz_theme import polish, PLOTLY_CONFIG


def render(filters: dict) -> None:
    """Render the Forecast page.

    Expects in ``filters``:
        actuals, forecast, forecast_baseline_mode, start_date, end_date, countries
    """
    actuals                 = filters["actuals"]
    forecast                = filters["forecast"]
    forecast_baseline_mode  = filters["forecast_baseline_mode"]
    start_date              = filters["start_date"]
    end_date                = filters["end_date"]
    countries               = filters["countries"]

    # ── lifted body ──────────────────────────────────────────────────────
    future_forecast = forecast[forecast['ds'] > actuals['ds'].max()]
    last_actual = actuals['y'].iloc[-1]
    forecast_base_value, forecast_base_label = forecast_baseline(actuals, forecast_baseline_mode)
    forecast_base_short = short_baseline_label(forecast_base_label)
    next_row = future_forecast.iloc[0]
    next_delta = (next_row['yhat'] - forecast_base_value) / forecast_base_value if forecast_base_value > 0 else 0
    recent_avg = actuals.tail(3)['y'].mean()
    forecast_avg = future_forecast['yhat'].mean()
    avg_delta = (forecast_avg - recent_avg) / recent_avg if recent_avg > 0 else 0
    uncertainty = (
        (future_forecast['yhat_upper'] - future_forecast['yhat_lower']) / future_forecast['yhat'].clip(lower=1)
    ).mean()

    if next_delta <= -0.05:
        forecast_rec = {
            'priority': 'HOCH',
            'decision': 'Umsatzrückgang im nächsten Monat aktiv beobachten.',
            'finding': f'Prognose £{next_row["yhat"]:,.0f} liegt {next_delta:+.1%} unter dem Vergleichsumsatz (£{forecast_base_value:,.0f}; {forecast_base_label}).',
            'reasoning': 'Der Agent sollte diesen Forecast zusammen mit Kunden- und Produktindikatoren interpretieren, nicht isoliert.',
        }
    elif next_delta >= 0.05:
        forecast_rec = {
            'priority': 'TIEF',
            'decision': 'Kurzfristig positiver Umsatztrend erwartet.',
            'finding': f'Prognose £{next_row["yhat"]:,.0f} liegt {next_delta:+.1%} über dem Vergleichsumsatz (£{forecast_base_value:,.0f}; {forecast_base_label}).',
            'reasoning': 'Der Ausblick ist positiv, sollte aber wegen Saisonalität und Unsicherheitsband weiter überwacht werden.',
        }
    else:
        forecast_rec = {
            'priority': 'MITTEL',
            'decision': 'Umsatzentwicklung bleibt kurzfristig stabil.',
            'finding': f'Prognose £{next_row["yhat"]:,.0f} liegt {next_delta:+.1%} nahe am Vergleichsumsatz (£{forecast_base_value:,.0f}; {forecast_base_label}).',
            'reasoning': 'Bei stabilem Forecast sind Kundensegmente und rückläufige Produkte die wichtigeren Entscheidungstreiber.',
        }

    st.title("Forecast & Umsatzrisiko")
    st.caption("3-Monats-Ausblick mit Unsicherheit und Modellgüte")
    render_decision_panel(forecast_rec, "Forecast-Interpretation")
    render_evidence_strip([
        ("Vergleichsumsatz", f"£{forecast_base_value:,.0f}"),
        ("Prognose nächster Monat", f"£{next_row['yhat']:,.0f}"),
        ("Abweichung zur Vergleichsbasis", f"{next_delta:+.1%}"),
        ("Ø Prognose vs. letzte 3 Monate", f"{avg_delta:+.1%}"),
        ("Ø Unsicherheitsband", f"{uncertainty:.0%}"),
    ])

    chart_history = actuals.tail(12).copy()
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=chart_history['ds'], y=chart_history['y'],
        name='Ist-Umsatz', marker_color='#60a5fa',
        hovertemplate='%{x|%b %Y}<br>Ist: £%{y:,.0f}<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        x=future_forecast['ds'], y=future_forecast['yhat'],
        name='Forecast', marker_color='#f59e0b',
        error_y=dict(
            type='data',
            array=(future_forecast['yhat_upper'] - future_forecast['yhat']).clip(lower=0),
            arrayminus=(future_forecast['yhat'] - future_forecast['yhat_lower']).clip(lower=0),
            color='#fbbf24',
            thickness=1.5,
            width=4,
        ),
        hovertemplate='%{x|%b %Y}<br>Forecast: £%{y:,.0f}<extra></extra>',
    ))
    fig.update_layout(
        height=430,
        barmode='group',
        xaxis_title='',
        yaxis_title='',
    )
    fig = polish(fig, y_format=',.0f', reference=forecast_base_value,
                 reference_label='Vergleichsbasis')
    st.plotly_chart(fig, use_container_width=True,
                    theme=None, config=PLOTLY_CONFIG)

    forecast_display = future_forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
    forecast_display['Delta zur Vergleichsbasis'] = (
        (forecast_display['yhat'] - forecast_base_value) / forecast_base_value
    )
    forecast_display['Monat'] = forecast_display['ds'].dt.strftime('%b %Y')
    forecast_display['Forecast'] = forecast_display['yhat'].map('£{:,.0f}'.format)
    forecast_display['Unsicherheitsband'] = (
        forecast_display['yhat_lower'].map('£{:,.0f}'.format)
        + ' – '
        + forecast_display['yhat_upper'].map('£{:,.0f}'.format)
    )
    forecast_display['Delta'] = forecast_display['Delta zur Vergleichsbasis'].map('{:+.1%}'.format)
    st.dataframe(
        forecast_display[['Monat', 'Forecast', 'Delta', 'Unsicherheitsband']],
        use_container_width=True,
        hide_index=True,
    )

    # ── Backtest / Modellgüte ────────────────────────────────────────────────
    st.divider()
    st.subheader("Kann man dem Forecast trauen?", anchor=False)

    countries_tuple = tuple(countries) if not isinstance(countries, tuple) else countries
    backtest = load_backtest(start_date, end_date, countries_tuple)

    if backtest is None:
        st.info("Zu wenig vollständige Monatsdaten für einen belastbaren Backtest (mindestens 9 Monate benötigt: 6 Training + 3 Test).")
    else:
        mape = backtest['mape']
        accuracy = max(0, 1 - backtest['mape'])
        quality = "hoch" if mape < 0.15 else "mittel" if mape < 0.30 else "niedrig"
        q_priority = "TIEF" if quality == "hoch" else "MITTEL" if quality == "mittel" else "HOCH"
        render_decision_panel({
            'priority': q_priority,
            'decision': f'Modellgüte: {quality}.',
            'finding': f'Der Backtest-Fehler liegt bei {mape:.1%} MAPE und £{backtest["mae"]:,.0f} MAE.',
            'reasoning': 'Das Modell wurde auf den letzten drei historischen Monaten geprüft. Je tiefer der Fehler, desto belastbarer die Prognose.',
        }, "Backtest")
        render_evidence_strip([
            ("MAPE", f"{mape:.1%}"),
            ("MAE", f"£{backtest['mae']:,.0f}"),
            ("Näherungsgenauigkeit", f"{accuracy:.0%}"),
            ("Holdout", "3 Monate"),
        ])

        fig_bt = go.Figure()
        fig_bt.add_trace(go.Scatter(
            x=backtest['actuals']['ds'], y=backtest['actuals']['y'],
            mode='lines+markers', name='Tatsächlich',
            line=dict(color='#60a5fa', width=2)))
        fig_bt.add_trace(go.Scatter(
            x=backtest['forecast']['ds'], y=backtest['forecast']['yhat'],
            mode='lines+markers', name='Forecast (Backtest)',
            line=dict(color='#f59e0b', width=2, dash='dash')))
        fig_bt.add_trace(go.Scatter(
            x=pd.concat([backtest['forecast']['ds'], backtest['forecast']['ds'].iloc[::-1]]),
            y=pd.concat([backtest['forecast']['yhat_upper'], backtest['forecast']['yhat_lower'].iloc[::-1]]),
            fill='toself', fillcolor='rgba(245,158,11,0.15)',
            line=dict(color='rgba(255,255,255,0)'), name='Konfidenzintervall'))
        fig_bt.update_layout(height=380, xaxis_title='', yaxis_title='')
        fig_bt = polish(fig_bt, y_format=',.0f')
        st.plotly_chart(fig_bt, use_container_width=True,
                        theme=None, config=PLOTLY_CONFIG)

    # ── Saisonalitäts-Decomposition ──────────────────────────────────────────
    if 'trend' in forecast.columns:
        st.divider()
        st.subheader("Saisonalitäts-Decomposition", anchor=False)
        st.caption("Prophet zerlegt den Forecast in einen Langzeit-Trend. Jahres-Saisonalität wird erst ab 12 vollständigen Monaten modelliert.")

        col_trend, col_yearly = st.columns(2)

        with col_trend:
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=forecast['ds'], y=forecast['trend'],
                mode='lines', name='Trend',
                line=dict(color='#60a5fa', width=2),
            ))
            fig_trend.update_layout(
                title='Langzeit-Trend', height=300,
                xaxis_title='', yaxis_title='',
            )
            fig_trend = polish(fig_trend, y_format=',.0f')
            st.plotly_chart(fig_trend, use_container_width=True,
                            theme=None, config=PLOTLY_CONFIG)

        with col_yearly:
            if 'yearly' in forecast.columns:
                seasonal = forecast[['ds', 'yearly']].copy()
                seasonal['month'] = seasonal['ds'].dt.month
                monthly_avg = seasonal.groupby('month')['yearly'].mean().reset_index()
                month_names = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun',
                               'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']
                monthly_avg['month_name'] = monthly_avg['month'].apply(lambda m: month_names[m - 1])
                fig_yearly = go.Figure()
                fig_yearly.add_trace(go.Bar(
                    x=monthly_avg['month_name'],
                    y=monthly_avg['yearly'],
                    marker_color=['#ef4444' if v < 0 else '#4ade80' for v in monthly_avg['yearly']],
                ))
                fig_yearly.update_layout(
                    title='Jahreszeitlicher Effekt (Ø pro Monat)', height=300,
                    xaxis_title='', yaxis_title='',
                    showlegend=False,
                )
                fig_yearly = polish(fig_yearly, y_format=',.0f')
                st.plotly_chart(fig_yearly, use_container_width=True,
                                theme=None, config=PLOTLY_CONFIG)
