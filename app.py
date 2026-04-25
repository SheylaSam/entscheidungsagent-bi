import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import date
from src.data_processing import build_database, get_connection
from src.rfm_analysis import load_rfm
from src.forecasting import load_forecast
from src.product_analysis import load_product_analysis
from src.decision_agent import generate_recommendations

st.set_page_config(page_title="RetailBI — Entscheidungsagent", layout="wide")

build_database()

# ── Sidebar: Zeitraum-Filter ──────────────────────────────────────────────────
_MIN_DATE = date(2009, 12, 1)
_MAX_DATE = date(2011, 12, 9)

st.sidebar.header("Zeitraum")
date_range = st.sidebar.date_input(
    "Datumsbereich",
    value=(_MIN_DATE, _MAX_DATE),
    min_value=_MIN_DATE,
    max_value=_MAX_DATE,
)

if len(date_range) != 2:
    st.stop()

start_date, end_date = date_range
st.sidebar.caption(
    f"{start_date.strftime('%d.%m.%Y')} – {end_date.strftime('%d.%m.%Y')}"
)
st.sidebar.divider()


@st.cache_data
def get_countries() -> list[str]:
    conn = get_connection()
    df = pd.read_sql("SELECT DISTINCT country FROM transactions ORDER BY country", conn)
    conn.close()
    return df['country'].tolist()


all_countries = get_countries()

st.sidebar.header("Land")
selected_countries = st.sidebar.multiselect(
    "Länder", options=all_countries, default=all_countries
)

if not selected_countries:
    st.sidebar.warning("Mindestens 1 Land auswählen.")
    st.stop()

countries_tuple = tuple(selected_countries)
st.sidebar.divider()


@st.cache_data
def load_all(start_date: str, end_date: str, countries: tuple, declining_months: int = 3):
    conn = get_connection()
    rfm = load_rfm(conn, start_date, end_date, countries)
    actuals, forecast = load_forecast(conn, start_date, end_date, countries)
    top_products, declining = load_product_analysis(conn, start_date, end_date, countries, declining_months)
    conn.close()
    return rfm, actuals, forecast, top_products, declining


rfm, actuals, forecast, top_products, declining = load_all(
    start_date.isoformat(), end_date.isoformat(), countries_tuple, 3
)
recs = generate_recommendations(forecast, rfm, declining)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Übersicht", "📈 Forecast", "👥 Kunden RFM", "📦 Produkte", "🤖 KI-Entscheid"
])

# ── Tab 1 ────────────────────────────────────────────────────────────────────
with tab1:
    st.title("Online Retail — Business Intelligence Dashboard")
    st.caption("Datenquelle: Online Retail II (UCI ML Repository, 2009–2011)")

    total_revenue = actuals['y'].sum()
    total_customers = rfm['customer_id'].nunique()
    at_risk_count = (rfm['segment'] == 'At Risk').sum()
    last_actual = actuals['y'].iloc[-1]
    next_forecast = forecast[forecast['ds'] > actuals['ds'].max()]['yhat'].iloc[0]
    forecast_delta = (next_forecast - last_actual) / last_actual

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Gesamtumsatz", f"£{total_revenue:,.0f}")
    col2.metric("Aktive Kunden", f"{total_customers:,}")
    col3.metric("At-Risk Kunden", f"{at_risk_count:,}")
    col4.metric("Forecast nächster Monat", f"£{next_forecast:,.0f}", f"{forecast_delta:+.1%}")

    st.divider()
    col_left, col_mid, col_right = st.columns(3)

    with col_left:
        st.subheader("Umsatz Trend")
        fig = px.bar(actuals.tail(12), x='ds', y='y', labels={'ds': '', 'y': 'Umsatz (£)'})
        fig.update_layout(height=220, margin=dict(t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with col_mid:
        st.subheader("Kundensegmente")
        seg_counts = rfm['segment'].value_counts().reset_index()
        seg_counts.columns = ['Segment', 'Anzahl']
        color_map = {'Champions': '#4ade80', 'Loyal': '#60a5fa', 'At Risk': '#f59e0b',
                     'Lost': '#ef4444', 'New': '#a78bfa', 'Others': '#94a3b8'}
        fig2 = px.bar(seg_counts, x='Anzahl', y='Segment', orientation='h',
                      color='Segment', color_discrete_map=color_map)
        fig2.update_layout(height=220, margin=dict(t=0, b=0), showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    with col_right:
        st.subheader("KI-Empfehlung")
        top_rec = recs[0]
        icon = {'HOCH': '🔴', 'MITTEL': '🟡', 'TIEF': '🟢'}.get(top_rec['priority'], '⚪')
        st.markdown(f"**{icon} Priorität: {top_rec['priority']}**")
        st.markdown(f"_{top_rec['finding']}_")
        st.markdown(f"**→ {top_rec['decision']}**")
        st.caption("Details auf Tab 🤖 KI-Entscheid")

# ── Tab 2 ────────────────────────────────────────────────────────────────────
with tab2:
    st.title("Umsatz-Forecast")
    st.caption("Historischer Monatsumsatz + Prophet-Prognose (3 Monate)")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=actuals['ds'], y=actuals['y'],
        mode='lines+markers', name='Tatsächlicher Umsatz', line=dict(color='#60a5fa', width=2)))
    future_forecast = forecast[forecast['ds'] > actuals['ds'].max()]
    fig.add_trace(go.Scatter(x=future_forecast['ds'], y=future_forecast['yhat'],
        mode='lines+markers', name='Forecast', line=dict(color='#a78bfa', width=2, dash='dash')))
    fig.add_trace(go.Scatter(
        x=pd.concat([future_forecast['ds'], future_forecast['ds'].iloc[::-1]]),
        y=pd.concat([future_forecast['yhat_upper'], future_forecast['yhat_lower'].iloc[::-1]]),
        fill='toself', fillcolor='rgba(167,139,250,0.15)',
        line=dict(color='rgba(255,255,255,0)'), name='Konfidenzintervall'))
    fig.update_layout(height=400, xaxis_title='Monat', yaxis_title='Umsatz (£)',
                      legend=dict(orientation='h', yanchor='bottom', y=1.02))
    st.plotly_chart(fig, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    for i, row in enumerate(future_forecast.itertuples()):
        [col1, col2, col3][i].metric(row.ds.strftime('%b %Y'), f"£{row.yhat:,.0f}",
            f"£{row.yhat_lower:,.0f} – £{row.yhat_upper:,.0f}")

# ── Tab 3 ────────────────────────────────────────────────────────────────────
with tab3:
    st.title("Kundensegmentierung — RFM-Analyse")
    st.caption("Recency · Frequency · Monetary | Segmente basierend auf Quintil-Scores")

    color_map = {'Champions': '#4ade80', 'Loyal': '#60a5fa', 'At Risk': '#f59e0b',
                 'Lost': '#ef4444', 'New': '#a78bfa', 'Others': '#94a3b8'}
    col_scatter, col_table = st.columns([2, 1])

    with col_scatter:
        fig = px.scatter(rfm, x='recency', y='frequency', size='monetary',
            color='segment', color_discrete_map=color_map,
            hover_data=['customer_id', 'monetary'],
            labels={'recency': 'Recency (Tage)', 'frequency': 'Frequency (Bestellungen)'},
            title='RFM Scatter — Recency vs. Frequency (Grösse = Monetary)')
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)

    with col_table:
        st.subheader("Segmente Übersicht")
        summary = (rfm.groupby('segment')
            .agg(Kunden=('customer_id', 'count'), Umsatz=('monetary', 'sum'))
            .reset_index().sort_values('Umsatz', ascending=False))
        summary['Umsatz'] = summary['Umsatz'].map('£{:,.0f}'.format)
        st.dataframe(summary, use_container_width=True, hide_index=True)

        st.subheader("At-Risk Kunden")
        at_risk = rfm[rfm['segment'] == 'At Risk'][['customer_id', 'recency', 'frequency', 'monetary']].head(10).copy()
        at_risk['monetary'] = at_risk['monetary'].map('£{:,.0f}'.format)
        st.dataframe(at_risk, use_container_width=True, hide_index=True)

# ── Tab 4 ────────────────────────────────────────────────────────────────────
with tab4:
    st.title("Produkt-Performance")
    st.caption("Top-Produkte nach Umsatz · Rückläufige Produkte (≥3 Monate)")

    col_top, col_decline = st.columns(2)

    with col_top:
        st.subheader("Top 10 Produkte")
        fig = px.bar(top_products, x='revenue', y='description', orientation='h',
            labels={'revenue': 'Umsatz (£)', 'description': ''},
            color='revenue', color_continuous_scale='Blues')
        fig.update_layout(height=380, coloraxis_showscale=False, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

    with col_decline:
        st.subheader(f"Rückläufige Produkte ({len(declining)})")
        if len(declining) == 0:
            st.success("Keine Produkte mit ≥3 Monaten rückläufigem Umsatz.")
        else:
            st.warning(f"{len(declining)} Produkte zeigen anhaltenden Umsatzrückgang.")
            d = declining.copy()
            d['revenue_last_month'] = d['revenue_last_month'].map('£{:,.0f}'.format)
            d.columns = ['Stock Code', 'Bezeichnung', 'Umsatz (letzter Monat)']
            st.dataframe(d, use_container_width=True, hide_index=True)

# ── Tab 5 ────────────────────────────────────────────────────────────────────
with tab5:
    st.title("KI-Entscheidungsagent")
    st.caption("Regelbasierter Agent — kombiniert Forecast, RFM und Produktanalyse")

    st.subheader("Schwellwerte anpassen")
    col_s1, col_s2 = st.columns(2)

    with col_s1:
        forecast_threshold = st.slider(
            "Regel 1: Forecast-Rückgang (Schwellwert)",
            min_value=-0.30, max_value=-0.01, value=-0.05, step=0.01,
            format="%.2f",
            help="Regel 1 wird ausgelöst wenn Forecast diesen Wert unterschreitet",
        )
        st.caption(f"Aktuell: Forecast < {forecast_threshold:.0%}")

    with col_s2:
        at_risk_threshold = st.slider(
            "Regel 1: At-Risk-Anteil (Schwellwert)",
            min_value=0.05, max_value=0.50, value=0.20, step=0.01,
            format="%.2f",
            help="Regel 1 wird ausgelöst wenn At-Risk-Anteil diesen Wert überschreitet",
        )
        st.caption(f"Aktuell: At-Risk > {at_risk_threshold:.0%}")

    live_recs = generate_recommendations(forecast, rfm, declining, forecast_threshold, at_risk_threshold)

    st.divider()

    priority_config = {
        'HOCH':   {'icon': '🔴', 'color': '#ef4444', 'bg': '#2d1515'},
        'MITTEL': {'icon': '🟡', 'color': '#f59e0b', 'bg': '#2d2410'},
        'TIEF':   {'icon': '🟢', 'color': '#4ade80', 'bg': '#152d1d'},
    }

    for rec in live_recs:
        cfg = priority_config.get(rec['priority'], {'icon': '⚪', 'color': '#94a3b8', 'bg': '#1e293b'})
        st.markdown(f"""
        <div style="background:{cfg['bg']};border-left:4px solid {cfg['color']};padding:16px 20px;border-radius:8px;margin-bottom:16px;">
            <div style="font-size:18px;font-weight:700;color:{cfg['color']};margin-bottom:8px;">{cfg['icon']} Priorität: {rec['priority']}</div>
            <div style="font-size:15px;color:#e2e8f0;margin-bottom:8px;"><strong>Befund:</strong> {rec['finding']}</div>
            <div style="font-size:15px;color:#e2e8f0;margin-bottom:8px;"><strong>Entscheid:</strong> {rec['decision']}</div>
            <div style="font-size:13px;color:#94a3b8;"><strong>Begründung:</strong> {rec['reasoning']}</div>
        </div>""", unsafe_allow_html=True)

    st.divider()
    st.subheader("Entscheidungslogik")
    st.markdown(f"""
| Regel | Bedingung | Entscheid | Priorität |
|---|---|---|---|
| 1 | Forecast < {forecast_threshold:.0%} UND At-Risk > {at_risk_threshold:.0%} | Reaktivierungskampagne | HOCH |
| 2 | ≥1 Produkt mit 3+ Monaten Rückgang | Sortiment bereinigen | MITTEL |
| 3 | Keine der obigen Regeln | Kein Handlungsbedarf | TIEF |
""")
