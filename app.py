from datetime import date

import streamlit as st

from src.data_processing import build_database, DB_PATH
from src.customer_analysis import summarize_segments_by_country
from src.decision_agent import generate_recommendations
from src.ui import theme as ui_theme
from src.ui.legacy_renderers import inject_legacy_css
from src.ui.page_loader import (
    get_countries, load_all,
    load_customer_country, load_monthly_product, load_revenue_by_country,
)
from src.pages import (
    overview,
    forecast as forecast_page,
    customers,
    products,
    agent_recommendations,
    agent_history,
    chat,
    data_source,
    settings,
)
from src.ui.navigation import sidebar_nav

st.set_page_config(page_title="RetailBI — Entscheidungsagent", layout="wide")

ui_theme.inject_global_css()
inject_legacy_css()

if not DB_PATH.exists():
    with st.spinner("Datenbankimport läuft — das dauert beim ersten Start ca. 30–90 Sekunden..."):
        build_database()
else:
    build_database()

# ── Sidebar: Navigation ───────────────────────────────────────────────────────
active_page = sidebar_nav()
st.sidebar.divider()

# ── Sidebar: Zeitraum-Filter ──────────────────────────────────────────────────
_MIN_DATE = date(2009, 12, 1)
_MAX_DATE = date(2011, 12, 9)
_DEFAULT_START = date(2011, 6, 1)

date_range = st.sidebar.slider(
    "Zeitraum",
    min_value=_MIN_DATE,
    max_value=_MAX_DATE,
    value=(_DEFAULT_START, _MAX_DATE),
    format="DD/MM/YYYY",
)

start_date, end_date = date_range

if (end_date - start_date).days < 180:
    st.warning("Bitte mindestens 6 Monate auswählen, damit der Forecast aussagekräftig berechnet werden kann.")
    st.stop()
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
st.sidebar.caption(
    "Filtert Kleinst-Positionen (unter dem Wert) aus *Top Produkte* und *Rückläufige Produkte* aus."
)
st.sidebar.divider()


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

country_seg = summarize_segments_by_country(rfm, customer_country_df)

# ── Dispatch ──────────────────────────────────────────────────────────────────
filters = {
    "actuals":               actuals,
    "forecast":              forecast,
    "rfm":                   rfm,
    "declining":             declining,
    "top_products":          top_products,
    "country_seg":           country_seg,
    "recs":                  recs,
    "forecast_baseline_mode": forecast_baseline_mode,
    "start_date":            start_date,
    "end_date":              end_date,
    "countries":             countries_tuple,
    "agent_forecast_base":   agent_forecast_base,
    # products page extras
    "top_n_products":        top_n_products,
    "min_product_revenue":   min_product_revenue,
    "monthly_product_df":    monthly_product_df,
    "revenue_by_country_df": revenue_by_country_df,
}

PAGES = {
    "overview":      overview.render,
    "forecast":      forecast_page.render,
    "customers":     customers.render,
    "products":      products.render,
    "agent_recs":    agent_recommendations.render,
    "agent_history": agent_history.render,
    "chat":          chat.render,
    "data_source":   data_source.render,
    "settings":      settings.render,
}

PAGES[active_page](filters)
