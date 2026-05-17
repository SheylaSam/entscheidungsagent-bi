import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
from datetime import date
from src.data_processing import build_database, get_connection, DB_PATH
from src.rfm_analysis import load_rfm
from src.forecasting import load_forecast, run_backtest
from src.product_analysis import load_product_analysis
from src.customer_analysis import load_primary_customer_country, summarize_segments_by_country
from src.decision_agent import generate_recommendations, generate_agent_run
from src.decision_log import list_agent_runs, log_agent_run, log_decision_outcome
from src.critic import analyze_decision_history
from src.agent_chat import AAIAgent, AgentContext, OllamaNotAvailable
from src.ui.viz_theme import polish, PLOTLY_CONFIG

st.set_page_config(page_title="RetailBI — Entscheidungsagent", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    [data-testid="stMetric"] {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 14px 16px;
    }
    [data-testid="stMetricLabel"] { color: #94a3b8; }
    .decision-panel {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-left: 5px solid var(--accent);
        border-radius: 8px;
        padding: 20px 22px;
        margin: 8px 0 18px;
    }
    .decision-kicker {
        color: #94a3b8;
        font-size: 13px;
        font-weight: 700;
        letter-spacing: .04em;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .decision-title {
        color: #f8fafc;
        font-size: 24px;
        font-weight: 750;
        line-height: 1.25;
        margin-bottom: 10px;
    }
    .decision-body {
        color: #cbd5e1;
        font-size: 15px;
        line-height: 1.5;
        margin-bottom: 6px;
    }
    .evidence-strip {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 12px;
        margin: 10px 0 20px;
    }
    .evidence-item {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 12px 14px;
    }
    .evidence-label {
        color: #94a3b8;
        font-size: 12px;
        font-weight: 650;
        margin-bottom: 4px;
    }
    .evidence-value {
        color: #f8fafc;
        font-size: 18px;
        font-weight: 750;
    }
    .section-kicker {
        color: #64748b;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: .05em;
        text-transform: uppercase;
        margin-top: 18px;
    }
    .action-list {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        gap: 10px;
        margin: 0 0 20px;
    }
    .action-item {
        background: #111827;
        border: 1px solid #1f2937;
        border-left: 4px solid var(--accent);
        border-radius: 8px;
        padding: 12px 14px;
        color: #e5e7eb;
        font-size: 14px;
        line-height: 1.35;
    }
    .action-priority {
        color: #94a3b8;
        font-size: 11px;
        font-weight: 750;
        letter-spacing: .04em;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    @media (max-width: 900px) {
        .evidence-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 520px) {
        .evidence-strip { grid-template-columns: 1fr; }
        .decision-title { font-size: 20px; }
    }
</style>
""", unsafe_allow_html=True)

if not DB_PATH.exists():
    with st.spinner("Datenbankimport läuft — das dauert beim ersten Start ca. 30–90 Sekunden..."):
        build_database()
else:
    build_database()

# ── Sidebar: Zeitraum-Filter ──────────────────────────────────────────────────
_MIN_DATE = date(2009, 12, 1)
_MAX_DATE = date(2011, 12, 9)
_DEFAULT_START = date(2011, 6, 1)

st.sidebar.header("Zeitraum")
date_range = st.sidebar.slider(
    "Datumsbereich",
    min_value=_MIN_DATE,
    max_value=_MAX_DATE,
    value=(_DEFAULT_START, _MAX_DATE),
    format="DD/MM/YYYY",
)

start_date, end_date = date_range

if (end_date - start_date).days < 180:
    st.warning("Bitte mindestens 6 Monate auswählen, damit der Forecast aussagekräftig berechnet werden kann.")
    st.stop()
st.sidebar.caption(
    f"{start_date.strftime('%d.%m.%Y')} – {end_date.strftime('%d.%m.%Y')}"
)
st.sidebar.divider()

st.sidebar.header("Forecast")
forecast_baseline_mode = st.sidebar.radio(
    "Vergleichsbasis",
    options=[
        "Letzter vollständiger Monat",
        "Durchschnitt letzte 3 Monate",
    ],
    index=1,
    help="Bestimmt, worauf sich die Forecast-Prozentänderung bezieht.",
)
st.sidebar.divider()


@st.cache_data
def get_countries() -> list[str]:
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT DISTINCT country FROM transactions ORDER BY country", conn)
    finally:
        conn.close()
    return df['country'].tolist()


all_countries = get_countries()

st.sidebar.header("Markt")
market_focus = st.sidebar.radio(
    "Markt-Fokus",
    options=["Alle", "Nur UK", "Ohne UK", "Manuell"],
    index=0,
    help="UK dominiert den Datensatz stark. Der Fokus hilft, internationale Muster sichtbar zu machen.",
)

if market_focus == "Nur UK":
    countries_tuple = ("United Kingdom",)
elif market_focus == "Ohne UK":
    countries_tuple = tuple(country for country in all_countries if country != "United Kingdom")
elif market_focus == "Manuell":
    selected_countries = st.sidebar.multiselect(
        "Länder",
        options=all_countries,
        default=[],
        placeholder="Länder auswählen…",
    )
    if not selected_countries:
        st.sidebar.warning("Bitte mindestens ein Land auswählen.")
        st.stop()
    countries_tuple = tuple(selected_countries)
else:
    countries_tuple = tuple(all_countries)
st.sidebar.divider()

st.sidebar.header("Produkte")
top_n_products = st.sidebar.select_slider(
    "Top-N Produkte",
    options=[5, 10, 15, 20],
    value=10,
)
min_product_revenue = st.sidebar.number_input(
    "Mindestumsatz Produkt (£)",
    min_value=0,
    value=100,
    step=100,
    help="Blendet kleine Produktpositionen aus Top-Produkten und Rückgangsliste aus.",
)
st.sidebar.divider()


@st.cache_data
def load_backtest(start_date: str, end_date: str, countries: tuple) -> dict | None:
    conn = get_connection()
    try:
        from src.forecasting import prepare_monthly_series
        series = prepare_monthly_series(conn, start_date, end_date, countries)
    finally:
        conn.close()
    return run_backtest(series, holdout_months=3)


@st.cache_data
def load_all(
    start_date: str,
    end_date: str,
    countries: tuple,
    declining_months: int = 3,
    top_n: int = 10,
    min_product_revenue: float = 0,
):
    conn = get_connection()
    try:
        rfm = load_rfm(conn, start_date, end_date, countries)
        actuals, forecast = load_forecast(conn, start_date, end_date, countries)
        top_products, declining = load_product_analysis(
            conn,
            start_date,
            end_date,
            countries,
            declining_months,
            top_n,
            min_product_revenue,
        )
    finally:
        conn.close()
    return rfm, actuals, forecast, top_products, declining


@st.cache_data
def load_customer_country(start_date: str, end_date: str, countries: tuple) -> pd.DataFrame:
    conn = get_connection()
    try:
        df = load_primary_customer_country(conn, start_date, end_date, countries)
    finally:
        conn.close()
    return df


@st.cache_data
def load_monthly_product(start_date: str, end_date: str, countries: tuple):
    conn = get_connection()
    try:
        df = pd.read_sql(
            f"""SELECT description, strftime('%Y-%m-01', invoice_date) as month,
                       SUM(revenue) as revenue
                FROM transactions
                WHERE invoice_date >= ? AND invoice_date <= ?
                AND country IN ({','.join(['?']*len(countries))})
                GROUP BY description, month
                ORDER BY month""",
            conn,
            params=(start_date, end_date + ' 23:59:59') + countries,
        )
    finally:
        conn.close()
    df['month'] = pd.to_datetime(df['month'])
    return df


@st.cache_data
def load_revenue_by_country(start_date: str, end_date: str, countries: tuple) -> pd.DataFrame:
    conn = get_connection()
    try:
        df = pd.read_sql(
            f"""SELECT country, SUM(revenue) as revenue, COUNT(DISTINCT customer_id) as customers
                FROM transactions
                WHERE invoice_date >= ? AND invoice_date <= ?
                AND country IN ({','.join(['?']*len(countries))})
                AND customer_id IS NOT NULL
                GROUP BY country
                ORDER BY revenue DESC""",
            conn,
            params=(start_date, end_date + ' 23:59:59') + countries,
        )
    finally:
        conn.close()
    return df


rfm, actuals, forecast, top_products, declining = load_all(
    start_date.isoformat(),
    end_date.isoformat(),
    countries_tuple,
    3,
    top_n_products,
    min_product_revenue,
)
monthly_product_df = load_monthly_product(
    start_date.isoformat(), end_date.isoformat(), countries_tuple
)
customer_country_df = load_customer_country(
    start_date.isoformat(), end_date.isoformat(), countries_tuple
)
revenue_by_country_df = load_revenue_by_country(
    start_date.isoformat(), end_date.isoformat(), countries_tuple
)
backtest = load_backtest(start_date.isoformat(), end_date.isoformat(), countries_tuple)
if len(actuals) < 6:
    st.warning("Der gewählte Zeitraum enthält weniger als 6 vollständige Umsatzmonate. Bitte Zeitraum erweitern.")
    st.stop()
agent_forecast_base = (
    actuals.tail(3)['y'].mean()
    if forecast_baseline_mode == "Durchschnitt letzte 3 Monate" and len(actuals) >= 3
    else actuals['y'].iloc[-1]
)
recs = generate_recommendations(
    forecast,
    rfm,
    declining,
    actuals_df=actuals,
    comparison_value=agent_forecast_base,
)


def priority_meta(priority: str) -> dict:
    return {
        'HOCH': {'accent': '#ef4444', 'label': 'Hohe Priorität'},
        'MITTEL': {'accent': '#f59e0b', 'label': 'Mittlere Priorität'},
        'TIEF': {'accent': '#22c55e', 'label': 'Tiefe Priorität'},
    }.get(priority, {'accent': '#94a3b8', 'label': priority})


def format_utility(rec: dict) -> str:
    utility = rec.get('utility', 0.0)
    if utility <= 0:
        return ""
    comps = rec.get('utility_components', {})
    return (
        f"Utility ≈ £{utility:,.0f} "
        f"(Impact £{comps.get('expected_impact_gbp', 0):,.0f} × "
        f"Dringlichkeit {comps.get('urgency', 0):.1f} × "
        f"Konfidenz {comps.get('confidence', 0):.1f})"
    )


def render_decision_panel(rec: dict, eyebrow: str = "Management-Entscheid") -> None:
    meta = priority_meta(rec['priority'])
    utility_line = format_utility(rec)
    utility_html = (
        f'<div class="decision-body"><strong>Nutzen:</strong> {utility_line}</div>'
        if utility_line else ''
    )
    st.markdown(f"""
    <div class="decision-panel" style="--accent:{meta['accent']}">
        <div class="decision-kicker">{eyebrow} · {meta['label']}</div>
        <div class="decision-title">{rec['decision']}</div>
        <div class="decision-body"><strong>Befund:</strong> {rec['finding']}</div>
        <div class="decision-body"><strong>Begründung:</strong> {rec['reasoning']}</div>
        {utility_html}
    </div>
    """, unsafe_allow_html=True)


def render_evidence_strip(items: list[tuple[str, str]]) -> None:
    cells = ''.join(
        f'<div class="evidence-item"><div class="evidence-label">{label}</div>'
        f'<div class="evidence-value">{value}</div></div>'
        for label, value in items
    )
    st.markdown(f'<div class="evidence-strip">{cells}</div>', unsafe_allow_html=True)


def render_action_list(recommendations: list[dict]) -> None:
    if not recommendations:
        return
    cards = ''
    for rec in recommendations:
        meta = priority_meta(rec['priority'])
        utility = rec.get('utility', 0.0)
        utility_badge = (
            f'<div style="color:#94a3b8;font-size:11px;margin-top:6px;">'
            f'Utility ≈ £{utility:,.0f}</div>'
        ) if utility > 0 else ''
        cards += (
            f'<div class="action-item" style="--accent:{meta["accent"]}">'
            f'<div class="action-priority">{meta["label"]}</div>'
            f'<div>{rec["decision"]}</div>'
            f'{utility_badge}'
            '</div>'
        )
    st.markdown(f'<div class="action-list">{cards}</div>', unsafe_allow_html=True)


def render_agent_trace(trace: list[dict]) -> None:
    rows = pd.DataFrame(trace)
    rows = rows.rename(columns={
        'step': 'Schritt',
        'name': 'Agentenaktion',
        'tool': 'Tool / Layer',
        'output': 'Output',
    })
    st.dataframe(rows[['Schritt', 'Agentenaktion', 'Tool / Layer', 'Output']],
                 use_container_width=True, hide_index=True)


def render_guardrails(guardrails: list[dict]) -> None:
    display = pd.DataFrame(guardrails).copy()
    display['status'] = display['status'].map({
        'pass': 'OK',
        'warn': 'Warnung',
        'fail': 'Fehler',
        'required': 'Freigabe nötig',
        'optional': 'Optional',
    }).fillna(display['status'])
    display = display.rename(columns={'name': 'Guardrail', 'status': 'Status', 'detail': 'Detail'})
    st.dataframe(display[['Guardrail', 'Status', 'Detail']], use_container_width=True, hide_index=True)


def _json_default(value):
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    if hasattr(value, 'item'):
        return value.item()
    return str(value)


def forecast_baseline(actuals_df: pd.DataFrame, mode: str) -> tuple[float, str]:
    if mode == "Durchschnitt letzte 3 Monate" and len(actuals_df) >= 3:
        return actuals_df.tail(3)['y'].mean(), "Ø der letzten 3 vollständigen Ist-Monate"
    return actuals_df['y'].iloc[-1], "letzter vollständiger Ist-Monat"


def short_baseline_label(label: str) -> str:
    if label.startswith("Ø"):
        return "Ø letzte 3 Monate"
    return "Letzter Ist-Monat"

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Übersicht", "Forecast", "Kunden RFM", "Produkte", "KI-Entscheid", "Chat-Agent"
])

# ── Tab 1 ────────────────────────────────────────────────────────────────────
with tab1:
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

    render_decision_panel(top_rec)
    if len(recs) > 1:
        st.markdown('<div class="section-kicker">Weitere Massnahmen</div>', unsafe_allow_html=True)
        render_action_list(recs[1:4])
    render_evidence_strip([
        ("Umsatz im Zeitraum", f"£{total_revenue:,.0f}"),
        ("Aktive Kunden", f"{total_customers:,}"),
        ("At-Risk Anteil", f"{at_risk_share:.1%}"),
        ("Vergleichsumsatz", f"£{forecast_base_value:,.0f}"),
        ("Prognose nächster Monat", f"£{next_forecast:,.0f}"),
        ("Abweichung zur Vergleichsbasis", f"{forecast_delta:+.1%}"),
    ])

    st.markdown('<div class="section-kicker">Belege</div>', unsafe_allow_html=True)
    col_left, col_mid = st.columns([1.35, 1])

    with col_left:
        st.subheader("Umsatztrend")
        fig = px.bar(actuals.tail(12), x='ds', y='y', labels={'ds': '', 'y': ''})
        fig.update_layout(height=300)
        fig = polish(fig, y_format=',.0f', hide_legend=True)
        st.plotly_chart(fig, use_container_width=True,
                        theme=None, config=PLOTLY_CONFIG)

    with col_mid:
        st.subheader("Kundensegmente")
        seg_counts = rfm['segment'].value_counts().reset_index()
        seg_counts.columns = ['Segment', 'Anzahl']
        color_map = {'Champions': '#4ade80', 'Loyal': '#60a5fa', 'At Risk': '#f59e0b',
                     'Lost': '#ef4444', 'New': '#a78bfa', 'Others': '#94a3b8'}
        fig2 = px.bar(seg_counts, x='Anzahl', y='Segment', orientation='h',
                      color='Segment', color_discrete_map=color_map)
        fig2.update_layout(height=300)
        fig2 = polish(fig2, hide_legend=True)
        st.plotly_chart(fig2, use_container_width=True,
                        theme=None, config=PLOTLY_CONFIG)

# ── Tab 2 ────────────────────────────────────────────────────────────────────
with tab2:
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
    fig.add_hline(y=forecast_base_value, line_dash='dot', line_color='#94a3b8',
                  annotation_text='Vergleichsbasis', annotation_position='top left')
    fig.update_layout(
        height=430,
        barmode='group',
        xaxis_title='',
        yaxis_title='Umsatz (£)',
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        margin=dict(t=20, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

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
    st.subheader("Kann man dem Forecast trauen?")

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
        fig_bt.update_layout(height=280, xaxis_title='Monat', yaxis_title='Umsatz (£)',
                             legend=dict(orientation='h', yanchor='bottom', y=1.02),
                             margin=dict(t=10))
        st.plotly_chart(fig_bt, use_container_width=True)

    # ── Saisonalitäts-Decomposition ──────────────────────────────────────────
    if 'trend' in forecast.columns:
        st.divider()
        st.subheader("Saisonalitäts-Decomposition")
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
                xaxis_title='Monat', yaxis_title='Umsatz (£)',
                margin=dict(t=40, b=10),
            )
            st.plotly_chart(fig_trend, use_container_width=True)

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
                    xaxis_title='Monat', yaxis_title='Saisonaler Beitrag (£)',
                    margin=dict(t=40, b=10), showlegend=False,
                )
                st.plotly_chart(fig_yearly, use_container_width=True)

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

        st.subheader("Top At-Risk Kunden")
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
    st.subheader("Kundensegmente nach Land")

    country_seg = summarize_segments_by_country(rfm, customer_country_df)

    col_map, col_ctable = st.columns([2, 1])

    with col_map:
        top_n = (country_seg[country_seg['At_Risk'] > 0]
                 .sort_values('At_Risk_%', ascending=False)
                 .head(15))
        fig_c = px.bar(
            top_n, x='At_Risk_%', y='country', orientation='h',
            color='At_Risk_%',
            color_continuous_scale='Reds',
            labels={'At_Risk_%': 'At-Risk Anteil', 'country': ''},
            title='At-Risk Anteil pro Land (Top 15, nach % sortiert)',
        )
        fig_c.update_layout(height=420, coloraxis_showscale=False,
                            yaxis={'categoryorder': 'total ascending'},
                            xaxis_tickformat='.0%')
        st.plotly_chart(fig_c, use_container_width=True)

    with col_ctable:
        display = (country_seg[['country', 'Kunden', 'At_Risk', 'At_Risk_%', 'Umsatz']]
                   .sort_values('At_Risk_%', ascending=False)
                   .copy())
        display['At_Risk_%'] = display['At_Risk_%'].map('{:.0%}'.format)
        display['Umsatz'] = display['Umsatz'].map('£{:,.0f}'.format)
        display.columns = ['Land', 'Kunden', 'At-Risk', 'At-Risk %', 'Umsatz']
        st.dataframe(display, use_container_width=True, hide_index=True, height=420)

# ── Tab 4 ────────────────────────────────────────────────────────────────────
with tab4:
    st.title("Produkt-Performance")
    st.caption(f"Top-Produkte nach Umsatz · Rückläufige Produkte · Mindestumsatz £{min_product_revenue:,.0f}")

    col_top, col_decline = st.columns(2)

    with col_top:
        st.subheader(f"Top {top_n_products} Produkte")
        if top_products.empty:
            st.info("Keine Produkte erfüllen den gewählten Mindestumsatz.")
            selection = None
        else:
            fig = px.bar(top_products, x='revenue', y='description', orientation='h',
                labels={'revenue': 'Umsatz (£)', 'description': ''},
                color='revenue', color_continuous_scale='Blues')
            fig.update_layout(height=380, coloraxis_showscale=False, yaxis={'categoryorder': 'total ascending'})
            selection = st.plotly_chart(fig, use_container_width=True,
                                        on_select="rerun", key="top_products_chart")

    with col_decline:
        st.subheader(f"Rückläufige Produkte ({len(declining)})")
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
        st.subheader(f"Monatlicher Umsatz: {selected_product}")
        product_monthly = monthly_product_df[monthly_product_df['description'] == selected_product]
        if not product_monthly.empty:
            fig_trend = px.line(
                product_monthly, x='month', y='revenue',
                labels={'month': 'Monat', 'revenue': 'Umsatz (£)'},
                markers=True,
            )
            fig_trend.update_traces(line_color='#60a5fa', marker_color='#3b82f6')
            fig_trend.update_layout(height=300)
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("Keine Monatsdaten für dieses Produkt.")
    else:
        st.caption("Klicke auf ein Produkt im Balkendiagramm, um den monatlichen Umsatzverlauf zu sehen.")

    # ── Umsatz nach Land ──────────────────────────────────────────────────────
    st.divider()
    st.subheader("Umsatz nach Land")
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
        )
        st.plotly_chart(fig_country, use_container_width=True)

    with col_country_table:
        display_countries = top_countries.copy()
        display_countries['revenue'] = display_countries['revenue'].map('£{:,.0f}'.format)
        display_countries.columns = ['Land', 'Umsatz', 'Kunden']
        st.dataframe(display_countries, use_container_width=True, hide_index=True, height=420)

# ── Tab 5 ────────────────────────────────────────────────────────────────────
with tab5:
    st.title("KI-Entscheidungsagent")
    st.caption("Priorisierte Managemententscheidung mit nachvollziehbarer Regelbasis")

    # ── Sliders ──────────────────────────────────────────────────────────────
    with st.expander("Regelparameter", expanded=False):
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            _ft_pct = st.slider(
                "Forecast-Rückgang (Regel 1)",
                min_value=-30, max_value=-1, value=-5, step=1,
                format="%d%%",
                help="Wie stark muss der Forecast fallen, damit Regel 1 anschlägt?",
            )
            forecast_threshold = _ft_pct / 100
        with col_s2:
            _ar_pct = st.slider(
                "At-Risk-Anteil (Regel 1)",
                min_value=5, max_value=50, value=20, step=1,
                format="%d%%",
                help="Wie hoch muss der At-Risk-Anteil sein, damit Regel 1 anschlägt?",
            )
            at_risk_threshold = _ar_pct / 100

    # ── Schwellwert-Kontext ───────────────────────────────────────────────────
        hist_changes = actuals['y'].pct_change().dropna()
        if len(hist_changes) > 0:
            hc1, hc2, hc3, hc4 = st.columns(4)
            hc1.metric("Ø monatliche Änderung", f"{hist_changes.mean():+.1%}")
            hc2.metric("Schlechtester Monat", f"{hist_changes.min():+.1%}")
            hc3.metric("Bester Monat", f"{hist_changes.max():+.1%}")
            hc4.metric("Aktueller At-Risk-Anteil", f"{(rfm['segment']=='At Risk').sum()/len(rfm):.1%}")

    # ── Live-Werte berechnen ──────────────────────────────────────────────────
    _future = forecast[forecast['ds'] > actuals['ds'].max()]
    _last, _last_label = forecast_baseline(actuals, forecast_baseline_mode)
    _last_short = short_baseline_label(_last_label)
    _next = _future['yhat'].iloc[0] if not _future.empty else 0
    _pct  = (_next - _last) / _last if _last > 0 else 0
    _ar_share = (rfm['segment'] == 'At Risk').sum() / len(rfm) if len(rfm) > 0 else 0
    _ar_count = (rfm['segment'] == 'At Risk').sum()
    _data_ok  = len(rfm) >= 10 and _next >= 0

    _c1a = _data_ok and _pct < forecast_threshold
    _c1b = _data_ok and _ar_share > at_risk_threshold
    _r1  = _c1a and _c1b
    if 'revenue_avg' in declining.columns and len(declining) > 0:
        _significant_declining = declining[
            declining['revenue_last_month'] < declining['revenue_avg'] * 0.5
        ]
    else:
        _significant_declining = declining
    _r2  = _data_ok and len(_significant_declining) > 0

    _champion_share = (rfm['segment'] == 'Champions').sum() / len(rfm) if len(rfm) > 0 else 0
    _new_share      = (rfm['segment'] == 'New').sum() / len(rfm) if len(rfm) > 0 else 0
    _top_n          = max(1, int(len(rfm) * 0.2))
    _top20_share    = (rfm['monetary'].sort_values(ascending=False).head(_top_n).sum()
                       / rfm['monetary'].sum()) if len(rfm) >= 5 else 0
    _r4 = _data_ok and _champion_share < 0.10
    _r5 = _data_ok and _new_share < 0.05
    _r6 = _data_ok and _top20_share > 0.80

    live_recs = generate_recommendations(
        forecast,
        rfm,
        declining,
        forecast_threshold,
        at_risk_threshold,
        actuals_df=actuals,
        comparison_value=_last,
    )
    agent_run = generate_agent_run(
        forecast,
        rfm,
        declining,
        forecast_threshold,
        at_risk_threshold,
        actuals_df=actuals,
        comparison_value=_last,
    )
    try:
        log_agent_run(agent_run)
    except OSError:
        pass

    render_decision_panel(live_recs[0], "Agenten-Empfehlung")
    render_evidence_strip([
        ("Vergleichsumsatz", f"£{_last:,.0f}"),
        ("Prognose nächster Monat", f"£{_next:,.0f}"),
        ("Abweichung zur Vergleichsbasis", f"{_pct:+.1%}"),
        ("At-Risk Kunden", f"{_ar_count:,} · {_ar_share:.1%}"),
        ("Rückläufige Produkte", f"{len(_significant_declining):,}"),
        ("Top-20 Umsatzanteil", f"{_top20_share:.0%}"),
    ])

    def _rule_box(title, priority_label, priority_color, conditions_html, fired: bool) -> str:
        border = priority_color if fired else '#334155'
        status_color = priority_color if fired else '#64748b'
        status_text = '● Ausgelöst' if fired else '○ Nicht ausgelöst'
        return f"""
        <div style="background:#1e293b;border:2px solid {border};padding:18px;border-radius:10px;height:100%;">
            <div style="font-size:13px;color:#94a3b8;margin-bottom:2px;">Priorität bei Auslösung</div>
            <div style="font-size:17px;font-weight:700;color:{priority_color};margin-bottom:12px;">{priority_label}</div>
            <div style="font-size:14px;color:#cbd5e1;margin-bottom:4px;font-weight:600">{title}</div>
            <hr style="border-color:#334155;margin:10px 0">
            {conditions_html}
            <hr style="border-color:#334155;margin:10px 0">
            <div style="font-size:13px;color:{status_color};font-weight:700">{status_text}</div>
        </div>"""

    def _cond_row(label: str, actual: str, threshold: str, met: bool) -> str:
        icon = '✓' if met else '×'
        return f'<div style="margin-bottom:6px;font-size:13px;color:#e2e8f0">{icon} {label}: <strong>{actual}</strong> <span style="color:#64748b">(Schwelle: {threshold})</span></div>'

    st.markdown('<div class="section-kicker">Regelbelege</div>', unsafe_allow_html=True)
    st.subheader("Regelstatus")

    col_r1, col_r2, col_r3 = st.columns(3)

    with col_r1:
        if not _data_ok:
            conds = _cond_row("Datenbasis", f"{len(rfm)} Kunden / Forecast {'negativ' if _next < 0 else 'ok'}", "≥10 Kunden, Forecast ≥0", False)
        else:
            conds = (
                _cond_row("Prognose nächster Monat", f"{_pct:+.1%}", f"< {forecast_threshold:.0%}", _c1a) +
                _cond_row("At-Risk-Anteil", f"{_ar_share:.1%} ({_ar_count} Kunden)", f"> {at_risk_threshold:.0%}", _c1b) +
                '<div style="font-size:12px;color:#64748b;margin-top:8px">Beide Bedingungen müssen erfüllt sein.</div>'
            )
        st.markdown(_rule_box("Reaktivierungskampagne", "HOCH", "#ef4444", conds, _r1), unsafe_allow_html=True)

    with col_r2:
        conds2 = _cond_row(
            "Signifikant rückläufige Produkte",
            str(len(_significant_declining)),
            "≥1",
            _r2,
        )
        if _r2:
            names = ', '.join(_significant_declining['description'].head(3).tolist())
            conds2 += f'<div style="font-size:12px;color:#94a3b8;margin-top:6px">{names}{"…" if len(_significant_declining) > 3 else ""}</div>'
        st.markdown(_rule_box("Sortiment bereinigen", "MITTEL", "#f59e0b", conds2, _r2), unsafe_allow_html=True)

    with col_r3:
        conds4 = _cond_row("Champion-Anteil", f"{_champion_share:.1%}", "≥ 10%", not _r4)
        st.markdown(_rule_box("Kundenbindung stärken", "MITTEL", "#f59e0b", conds4, _r4), unsafe_allow_html=True)

    col_r4, col_r5, col_r6 = st.columns(3)

    with col_r4:
        conds5 = _cond_row("Neukunden-Anteil", f"{_new_share:.1%}", "≥ 5%", not _r5)
        st.markdown(_rule_box("Neukundenakquisition prüfen", "MITTEL", "#f59e0b", conds5, _r5), unsafe_allow_html=True)

    with col_r5:
        conds6 = _cond_row("Top 20% Kunden, Umsatzanteil", f"{_top20_share:.0%}", "≤ 80%", not _r6)
        st.markdown(_rule_box("Klumpenrisiko", "MITTEL", "#f59e0b", conds6, _r6), unsafe_allow_html=True)

    with col_r6:
        _r3 = not any([_r1, _r2, _r4, _r5, _r6])
        _mittel_fired = [r for r in [_r2, _r4, _r5, _r6] if r]
        conds3 = (
            _cond_row("Keine HOCH-Regel ausgelöst", "ausgelöst" if _r1 else "—", "nicht ausgelöst", not _r1) +
            _cond_row("Keine MITTEL-Regel ausgelöst", f"{len(_mittel_fired)} ausgelöst" if _mittel_fired else "—", "nicht ausgelöst", not any(_mittel_fired)) +
            f'<div style="font-size:12px;color:#64748b;margin-top:8px">Champion-Anteil: {_champion_share:.1%}</div>'
        )
        st.markdown(_rule_box("Kein Handlungsbedarf", "TIEF", "#4ade80", conds3, _r3), unsafe_allow_html=True)

    if len(live_recs) > 1:
        with st.expander("Weitere Empfehlungen", expanded=False):
            for rec in live_recs[1:]:
                render_decision_panel(rec, "Weitere Empfehlung")

    st.divider()
    st.subheader("Agentic Trace")
    st.caption("Planung, Tool-Nutzung und Synthese der aktuellen Empfehlung.")
    render_agent_trace(agent_run['trace'])

    col_guard, col_approval = st.columns([1.2, 1])
    with col_guard:
        st.subheader("Guardrails")
        render_guardrails(agent_run['guardrails'])

    with col_approval:
        st.subheader("Human-in-the-Loop")
        if agent_run['approval_required']:
            st.warning("Operative Umsetzung benötigt Management-Freigabe.")
        else:
            st.success("Keine zwingende Freigabe nötig.")

        log_key = "decision_agent_log"
        if log_key not in st.session_state:
            st.session_state[log_key] = []

        selected_status = st.radio(
            "Entscheidungsstatus",
            ["Offen", "Freigegeben", "Zurückgestellt", "Abgelehnt"],
            horizontal=True,
            key="approval_status",
        )
        note = st.text_area(
            "Management-Notiz",
            placeholder="Kurz begründen, warum die Empfehlung freigegeben, zurückgestellt oder abgelehnt wird.",
            key="approval_note",
        )
        if st.button("Entscheidung protokollieren", type="primary"):
            entry = {
                'run_id': agent_run['run_id'],
                'status': selected_status,
                'note': note,
                'decision': live_recs[0]['decision'],
                'priority': live_recs[0]['priority'],
                'evidence': agent_run['evidence'],
            }
            st.session_state[log_key].insert(0, entry)
            log_decision_outcome(agent_run['run_id'], selected_status, note)
            st.success("Entscheidung wurde im Session-Memory protokolliert und für den Lern-Loop gespeichert.")

        st.download_button(
            "Agent Run als JSON exportieren",
            data=json.dumps(agent_run, ensure_ascii=False, indent=2, default=_json_default),
            file_name=f"decision-agent-run-{agent_run['run_id']}.json",
            mime="application/json",
        )

    if st.session_state.get("decision_agent_log"):
        st.subheader("Entscheidungslog / Memory")
        log_df = pd.DataFrame(st.session_state["decision_agent_log"])
        st.dataframe(
            log_df[['run_id', 'status', 'priority', 'decision', 'note']],
            use_container_width=True,
            hide_index=True,
        )

    persisted_runs = list_agent_runs(limit=10)
    if persisted_runs:
        with st.expander(f"Persistierte Agent-Runs ({len(persisted_runs)})", expanded=False):
            st.caption(
                "Jeder Agent-Lauf wird unter `logs/agent_runs/<run_id>.json` archiviert — "
                "Empfehlung, Evidence, Trace und Guardrails bleiben so nachvollziehbar."
            )
            st.dataframe(
                pd.DataFrame([
                    {
                        'run_id': r['run_id'],
                        'priorität': r['top_priority'],
                        'empfehlungen': r['recommendation_count'],
                        'freigabe nötig': r['approval_required'],
                    }
                    for r in persisted_runs
                ]),
                use_container_width=True,
                hide_index=True,
            )

    # ── Lern-Loop / Kritik-Komponente (Russell & Norvig Fig. 2.15, Folie 18) ──
    st.divider()
    st.subheader("Lern-Loop · Kritik-Komponente")
    st.caption(
        "Liest persistierte Agent-Runs und Entscheidungs-Outcomes und schlägt "
        "Schwellwert-Anpassungen vor. Read-only — Übernahme bleibt manuell."
    )
    critique = analyze_decision_history()
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        st.metric("Agent-Läufe gesamt", critique['run_count'])
    with col_c2:
        st.metric("Mit Outcome", critique['outcome_count'])
    with col_c3:
        approval_rate = critique['approval_rate']
        st.metric(
            "Freigabe-Quote",
            f"{approval_rate:.0%}" if approval_rate is not None else "n/a",
        )

    if critique['priority_distribution']:
        st.write("**Verteilung der Top-Prioritäten:**")
        st.dataframe(
            pd.DataFrame(
                [{'Priorität': k, 'Anzahl': v} for k, v in critique['priority_distribution'].items()]
            ),
            use_container_width=True,
            hide_index=True,
        )

    if critique['suggestions']:
        st.write("**Vorschläge des Kritik-Agents:**")
        for s in critique['suggestions']:
            if s['threshold']:
                st.warning(
                    f"**{s['threshold']}**: aktuell `{s['current_default']}`, "
                    f"vorgeschlagen `{s['suggested']}`.  \n{s['reasoning']}"
                )
            else:
                st.info(s['reasoning'])
    elif critique['run_count'] >= 3:
        st.success("Keine Anpassungen nötig — Schwellwerte produzieren akzeptierte Empfehlungen.")
    else:
        st.info(
            f"Noch zu wenig Datenbasis für Vorschläge "
            f"(mindestens 3 Läufe + Outcomes nötig, aktuell {critique['run_count']} Läufe / "
            f"{critique['outcome_count']} Outcomes)."
        )


# ── Tab 6: Chat-Agent ────────────────────────────────────────────────────────
with tab6:
    st.title("Chat-Agent")
    st.caption(
        "Natürlichsprachlicher Layer mit Tool-Calling (Ollama lokal). "
        "Der LLM wählt ein Tool, ruft die deterministische BI-Logik auf und antwortet auf Deutsch."
    )

    with st.expander("Setup-Hinweis", expanded=False):
        st.markdown(
            "1. Ollama installieren: <https://ollama.com>\n"
            "2. Modell laden: `ollama pull llama3.2`\n"
            "3. Python-Paket: `pip install ollama`\n"
            "4. Ollama läuft als Hintergrunddienst — keine API-Keys nötig."
        )

    model_name = st.text_input("Ollama-Modell", value="llama3.2")
    user_question = st.text_area(
        "Frage an den Agent",
        placeholder="z.B. Was sollten wir diesen Monat tun? — Welche Produkte gehen zurück? — Wie ist der Forecast?",
        key="chat_question",
    )

    if st.button("Frage absenden", type="primary"):
        if not user_question.strip():
            st.warning("Bitte eine Frage eingeben.")
        else:
            agent_ctx = AgentContext(
                forecast_df=forecast,
                rfm_df=rfm,
                declining_df=declining,
                actuals_df=actuals,
                comparison_value=agent_forecast_base,
            )
            agent = AAIAgent(agent_ctx, model=model_name)
            try:
                with st.spinner("Agent denkt nach…"):
                    result = agent.chat(user_question)
            except OllamaNotAvailable as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Ollama-Fehler: {exc}")
            else:
                st.markdown("### Antwort")
                st.write(result.answer)
                with st.expander("Agent-Trace (Think → Act → Observe → Answer)", expanded=False):
                    for step in result.trace:
                        st.markdown(f"**{step['step'].upper()}**")
                        st.json({k: v for k, v in step.items() if k != 'step'})
