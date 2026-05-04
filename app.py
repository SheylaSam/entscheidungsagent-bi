import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import date
from src.data_processing import build_database, get_connection, DB_PATH
from src.rfm_analysis import load_rfm
from src.forecasting import load_forecast, run_backtest
from src.product_analysis import load_product_analysis
from src.customer_analysis import load_primary_customer_country, summarize_segments_by_country
from src.decision_agent import generate_recommendations

st.set_page_config(page_title="RetailBI — Entscheidungsagent", layout="wide")

if not DB_PATH.exists():
    with st.spinner("Datenbankimport läuft — das dauert beim ersten Start ca. 30–90 Sekunden..."):
        build_database()
else:
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
    format="DD/MM/YYYY",
)

if len(date_range) != 2:
    st.stop()

start_date, end_date = date_range

if (end_date - start_date).days < 62:
    st.warning("Bitte mindestens 2 Monate auswählen, damit der Forecast berechnet werden kann.")
    st.stop()
st.sidebar.caption(
    f"{start_date.strftime('%d.%m.%Y')} – {end_date.strftime('%d.%m.%Y')}"
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

st.sidebar.header("Länder")
selected_countries = st.sidebar.multiselect(
    "Länder (leer = alle)",
    options=all_countries,
    default=[],
    placeholder="Alle Länder…",
)
countries_tuple = tuple(all_countries) if not selected_countries else tuple(selected_countries)
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
def load_all(start_date: str, end_date: str, countries: tuple, declining_months: int = 3):
    conn = get_connection()
    try:
        rfm = load_rfm(conn, start_date, end_date, countries)
        actuals, forecast = load_forecast(conn, start_date, end_date, countries)
        top_products, declining = load_product_analysis(conn, start_date, end_date, countries, declining_months)
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
    start_date.isoformat(), end_date.isoformat(), countries_tuple, 3
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
recs = generate_recommendations(forecast, rfm, declining, actuals_df=actuals)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Übersicht", "📈 Forecast", "👥 Kunden RFM", "📦 Produkte", "🤖 KI-Entscheid"
])

# ── Tab 1 ────────────────────────────────────────────────────────────────────
with tab1:
    st.title("Online Retail — Business Intelligence Dashboard")
    st.caption("Datenquelle: Online Retail II (UCI ML Repository, 2009–2011)")

    with st.expander("ℹ️ Wie funktioniert dieses Dashboard?", expanded=False):
        st.markdown("""
**Willkommen beim RetailBI Entscheidungsagenten.** Dieses Dashboard analysiert Umsatz, Kunden und Produkte eines britischen Online-Shops (2009–2011) und leitet daraus automatisch Handlungsempfehlungen ab.

---

**Sidebar — Filter**
| Filter | Funktion |
|---|---|
| **Datumsbereich** | Alle Tabs zeigen nur Daten im gewählten Zeitraum |
| **Land** | Filtert auf ein einzelnes Land oder alle Länder |

> Tipp: Mindestens 6 Monate und "Alle Länder" wählen für aussagekräftige Ergebnisse.

---

**Die 5 Tabs**

| Tab | Inhalt |
|---|---|
| 📊 **Übersicht** | KPI-Kennzahlen, Umsatztrend, Kundensegmente, Top-Empfehlung |
| 📈 **Forecast** | Prophet-Prognose für die nächsten 3 Monate mit Konfidenzintervall |
| 👥 **Kunden RFM** | Kundensegmentierung nach Recency, Frequency, Monetary |
| 📦 **Produkte** | Top-Produkte + rückläufige Produkte — Klick auf Balken zeigt Monatsverlauf |
| 🤖 **KI-Entscheid** | Empfehlungen des Agenten — Schwellwerte per Slider anpassbar |

---

**KI-Entscheidungslogik**

Der Agent kombiniert Forecast, RFM und Produktanalyse und prüft sechs Regeln:
1. **HOCH** — Forecast fällt stark UND viele At-Risk-Kunden → Reaktivierungskampagne
2. **MITTEL** — Produkte mit anhaltend sinkendem Umsatz → Sortiment bereinigen
3. **MITTEL** — Champion-Anteil < 10% → Kundenbindungsprogramm aufbauen
4. **MITTEL** — Neukunden-Anteil < 5% → Neukundenakquisition ausbauen
5. **MITTEL** — Top-20%-Kunden >80% des Umsatzes → Klumpenrisiko reduzieren
6. **TIEF** — Keine Auffälligkeiten → kein Handlungsbedarf

Im Tab 🤖 KI-Entscheid können die Schwellwerte für Regel 1 per Slider angepasst werden.
        """)

    st.divider()

    total_revenue = actuals['y'].sum()
    total_customers = rfm['customer_id'].nunique()
    at_risk_count = (rfm['segment'] == 'At Risk').sum()
    last_actual = actuals['y'].iloc[-1]
    future_rows = forecast[forecast['ds'] > actuals['ds'].max()]
    if future_rows.empty:
        st.warning("Forecast enthält keine zukünftigen Datenpunkte. Bitte einen längeren Zeitraum wählen.")
        st.stop()
    next_forecast = future_rows['yhat'].iloc[0]
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

    # ── Backtest / Modellgüte ────────────────────────────────────────────────
    st.divider()
    st.subheader("Modellgüte — Backtest (letzte 3 Monate)")
    st.caption("Das Modell wurde auf allen Daten ausser den letzten 3 Monaten trainiert. Die Prognose für diese 3 Monate wird mit den tatsächlichen Werten verglichen.")

    if backtest is None:
        st.info("Zu wenig Daten für einen Backtest (mindestens 6 Monate benötigt).")
    else:
        bc1, bc2, bc3 = st.columns(3)
        bc1.metric("MAPE", f"{backtest['mape']:.1%}",
                   help="Mean Absolute Percentage Error — mittlerer prozentualer Fehler")
        bc2.metric("MAE", f"£{backtest['mae']:,.0f}",
                   help="Mean Absolute Error — mittlerer absoluter Fehler in Pfund")
        accuracy = max(0, 1 - backtest['mape'])
        bc3.metric("Treffergenauigkeit", f"{accuracy:.0%}",
                   help="1 − MAPE als einfache Näherung der Modellgenauigkeit")

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
        st.caption("Prophet zerlegt den Forecast in einen Langzeit-Trend und saisonale Muster pro Monat.")

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

        st.subheader("At-Risk Kunden")
        at_risk = rfm[rfm['segment'] == 'At Risk'][['customer_id', 'recency', 'frequency', 'monetary']].head(10).copy()
        at_risk['monetary'] = at_risk['monetary'].map('£{:,.0f}'.format)
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
    st.caption("Top-Produkte nach Umsatz · Rückläufige Produkte (≥3 Monate)")

    col_top, col_decline = st.columns(2)

    with col_top:
        st.subheader("Top 10 Produkte")
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
        points = selection["selection"]["points"]
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
    st.caption("Regelbasierter Agent — kombiniert Forecast, RFM und Produktanalyse")

    # ── Sliders ──────────────────────────────────────────────────────────────
    st.subheader("Schwellwerte anpassen")
    st.caption("Passe die Grenzwerte für Regel 1 an — die Regelstatus-Anzeige und Empfehlungen aktualisieren sich sofort.")
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
    with st.expander("Kontext: Wie wurden die Standardwerte gewählt?"):
        hist_changes = actuals['y'].pct_change().dropna()
        if len(hist_changes) > 0:
            hc1, hc2, hc3, hc4 = st.columns(4)
            hc1.metric("Ø monatliche Änderung", f"{hist_changes.mean():+.1%}")
            hc2.metric("Schlechtester Monat", f"{hist_changes.min():+.1%}")
            hc3.metric("Bester Monat", f"{hist_changes.max():+.1%}")
            hc4.metric("Aktueller At-Risk-Anteil", f"{(rfm['segment']=='At Risk').sum()/len(rfm):.1%}")
            st.caption(
                f"Der Schwellwert **{forecast_threshold:.0%}** liegt {'über' if abs(forecast_threshold) < abs(hist_changes.mean()) else 'unter'} "
                f"dem historischen Durchschnitt ({hist_changes.mean():+.1%}). "
                f"Ein Rückgang unter {forecast_threshold:.0%} ist also ein **{'normales' if abs(forecast_threshold) < abs(hist_changes.std()) else 'aussergewöhnliches'}** Warnsignal im Kontext dieser Daten."
            )

    # ── Live-Werte berechnen ──────────────────────────────────────────────────
    _future = forecast[forecast['ds'] > actuals['ds'].max()]
    _last = actuals['y'].iloc[-1]
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

    def _badge(ok: bool, true_label: str, false_label: str) -> str:
        if ok:
            return f'<span style="color:#4ade80;font-weight:700">{true_label}</span>'
        return f'<span style="color:#ef4444;font-weight:700">{false_label}</span>'

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
        icon = '✅' if met else '❌'
        return f'<div style="margin-bottom:6px;font-size:13px;color:#e2e8f0">{icon} {label}: <strong>{actual}</strong> <span style="color:#64748b">(Schwelle: {threshold})</span></div>'

    st.divider()
    st.subheader("Regelstatus — live")

    col_r1, col_r2, col_r3 = st.columns(3)

    with col_r1:
        if not _data_ok:
            conds = _cond_row("Datenbasis", f"{len(rfm)} Kunden / Forecast {'negativ' if _next < 0 else 'ok'}", "≥10 Kunden, Forecast ≥0", False)
        else:
            conds = (
                _cond_row("Forecast nächster Monat", f"{_pct:+.1%}", f"< {forecast_threshold:.0%}", _c1a) +
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

    # ── Empfehlungskarten ─────────────────────────────────────────────────────
    st.divider()
    st.subheader("Empfehlung des Agenten")

    live_recs = generate_recommendations(
        forecast,
        rfm,
        declining,
        forecast_threshold,
        at_risk_threshold,
        actuals_df=actuals,
    )

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
