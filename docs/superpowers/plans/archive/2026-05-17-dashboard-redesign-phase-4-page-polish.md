# Dashboard Redesign — Phase 4: Per-Page Polish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply per-page color discipline (one "hero" accent per page, everything else grayscale-with-semantic-color-only-where-it-encodes-meaning), bypass the global date filter on the two pages where it actively hurts (Forecast, Kunden), and add a short explanatory caption on the Saisonalitäts-Decomposition that prevents the "is it really that linear?" confusion.

**Architecture:** No new modules. Pure edits to the 4 analytics pages (`overview.py`, `forecast.py`, `customers.py`, `products.py`). Each page picks one chart as the "hero" (carries `theme.CHART_HERO` blue); the rest go gray with optional semantic accents (positive/negative for the few cases where direction is meaningful, e.g. RFM "Champions" green vs "At Risk" red).

**Tech Stack:** Phase 1–3 stack. No new dependencies.

**Reference:** [`docs/superpowers/specs/2026-05-17-dashboard-redesign-design.md`](../specs/2026-05-17-dashboard-redesign-design.md) §5.3 (color discipline per chart type).

**Depends on:** Phases 1–3 merged, including the visual fixes in commit `72d7bbb`.

**Out of scope:**
- `streamlit-shadcn-ui` date-range picker — the existing native slider works; swap is optional, defer until proven necessary
- Top-bar component — sidebar filter layout stays
- Agent panel redesign (Phase 5)
- New pages (Datenquelle, Settings — Phase 7)
- Dark mode (later)

---

## Color Budget (the decisions)

**Per-page hero rule:** exactly one chart per page uses `theme.CHART_HERO` (#0072B2 blue). Everything else uses `theme.MUTED` gray with optional semantic green/red where direction matters.

| Page | Hero chart | Secondary charts |
|---|---|---|
| Übersicht | Umsatztrend (blue bars) | Kundensegmente → gray sorted + semantic (Champions/Loyal green, At-Risk/Lost red, Others/New muted) |
| Forecast | Main forecast chart (blue bars for actuals, muted-gray dashed for forecast) | Backtest, Trend, Yearly → single muted gray series |
| Kunden | RFM Scatter (Okabe-Ito palette — *one of two pages where categorical color is the point*) | At-Risk-by-Country → gray bars with chart-1 highlight on top |
| Produkte | Top Products (gray sorted + chart-1 highlight on selected/top-1) | Trend, Country → single chart-1 line/bar, no palette |

Key principle: when a chart has only ONE series, color is wasted ink. Use gray. When color carries meaning (status/segment), use the smallest distinct palette possible.

---

## File Plan

**Modify:**
- `src/pages/overview.py` — Kundensegmente color overhaul
- `src/pages/forecast.py` — filter bypass + chart-color cleanup + trend caption
- `src/pages/customers.py` — filter bypass + country chart color
- `src/pages/products.py` — top-products + trend + country color
- `src/ui/theme.py` — add a small `SEGMENT_SEMANTICS` dict mapping RFM segment names to one of {positive, negative, muted} for consistent use across overview + customers

**Tests:**
- `tests/test_ui_theme.py` — assert `SEGMENT_SEMANTICS` exists and maps correctly
- `tests/test_pages_smoke.py` already covers each page imports + has `render` (added Phase 3)

---

## Task 1: RFM segment semantics in `theme.py`

A small dict shared between Overview's Kundensegmente bar and Customers' RFM scatter. Single source of truth for "Champions are good, At Risk is bad".

**Files:**
- Modify: `src/ui/theme.py`
- Modify: `tests/test_ui_theme.py`

- [ ] **Step 1: Append failing tests**

Append to `tests/test_ui_theme.py`:

```python
def test_segment_semantics_has_known_segments():
    expected_segments = {"Champions", "Loyal", "At Risk", "Lost", "New", "Others"}
    assert set(theme.SEGMENT_SEMANTICS.keys()) >= expected_segments


def test_segment_semantics_maps_to_token_colors():
    valid = {theme.POSITIVE, theme.NEGATIVE, theme.MUTED, theme.FAINT}
    for seg, color in theme.SEGMENT_SEMANTICS.items():
        assert color in valid, f"{seg!r} → {color!r} not in {valid}"


def test_champions_and_loyal_are_positive():
    assert theme.SEGMENT_SEMANTICS["Champions"] == theme.POSITIVE
    assert theme.SEGMENT_SEMANTICS["Loyal"] == theme.POSITIVE


def test_at_risk_and_lost_are_negative():
    assert theme.SEGMENT_SEMANTICS["At Risk"] == theme.NEGATIVE
    assert theme.SEGMENT_SEMANTICS["Lost"] == theme.NEGATIVE
```

- [ ] **Step 2: Run, verify they fail**

```bash
pytest tests/test_ui_theme.py -v
```

- [ ] **Step 3: Append to `src/ui/theme.py`** (near the other color tokens)

```python
# ── RFM segment semantics ───────────────────────────────────────────────────
# Maps each RFM segment to a semantic color used by Overview's
# Kundensegmente chart and the Kunden page.  Charts get gray bars with
# colored accents on Champions/Loyal (positive) and At Risk/Lost
# (negative); Others/New are neutral.
SEGMENT_SEMANTICS: dict[str, str] = {
    "Champions": POSITIVE,
    "Loyal":     POSITIVE,
    "At Risk":   NEGATIVE,
    "Lost":      NEGATIVE,
    "Others":    MUTED,
    "New":       MUTED,
}
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
pytest tests/test_ui_theme.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/ui/theme.py tests/test_ui_theme.py
git commit -m "feat(ui): SEGMENT_SEMANTICS — single source for RFM segment colors"
```

---

## Task 2: Forecast page — bypass date filter

Forecast must train on the full historical window, not a user-selected slice. The page now reloads its own forecast & actuals using the full data range and adds a small caption explaining the override.

**Files:**
- Modify: `src/pages/forecast.py`

- [ ] **Step 1: Locate the current forecast loading**

Look at the top of `forecast.py`'s `render(filters)`. Currently it pulls `actuals` and `forecast` from `filters` — those were sliced by `start_date`/`end_date` in `app.py`. We override here.

- [ ] **Step 2: Reload with full history**

Add an import:

```python
from src.ui.page_loader import load_all
```

At the top of `render(filters)`, replace the `actuals = filters["actuals"]; forecast = filters["forecast"]` unpacking with a fresh load using the full data range. Use the project's known data bounds (`2009-12-01` to `2011-12-09`):

```python
def render(filters: dict) -> None:
    forecast_baseline_mode  = filters["forecast_baseline_mode"]
    # countries filter still applies — user can scope forecast to a market
    countries               = filters["countries"]

    # Forecast page intentionally bypasses the global date filter.
    # Prophet needs the full historical window for a usable model;
    # restricting it to 6 months collapses the trend component.
    _FULL_START = "2009-12-01"
    _FULL_END   = "2011-12-09"
    _, actuals, forecast, *_ = load_all(_FULL_START, _FULL_END, countries, forecast_horizon=3)

    st.caption(
        "Forecast nutzt die volle Datenhistorie 2009–2011 — der globale "
        "Zeitraum-Slider wirkt hier nicht. Prophet braucht mehr als ein "
        "halbes Jahr Trainingsdaten, sonst kollabiert die Trend-Komponente."
    )
```

The exact `load_all` return signature: `(rfm, actuals, forecast, top_products, declining)` — verify by reading `src/ui/page_loader.py`. The `*_` pattern unpacks and discards the unused returns. Adjust the unpacking order if the signature differs.

The `start_date` and `end_date` from `filters` are NO LONGER used in this page (Backtest still uses the user range — keep that, it's intentional: "did Prophet do well in the user's range?"). Remove the `start_date = filters["start_date"]` and `end_date = filters["end_date"]` lines if they're no longer referenced — but keep them if Backtest uses them.

- [ ] **Step 3: Smoke**

```bash
python -c "from src.pages import forecast" 2>&1 | head -5
python -c "import app" 2>&1 | head -5
```

- [ ] **Step 4: Commit**

```bash
git add src/pages/forecast.py
git commit -m "fix(forecast): always use full historical window for Prophet training"
```

---

## Task 3: Kunden page — bypass date filter for RFM

RFM is by convention computed on the full history (recency is defined relative to *today*, not relative to "the start of your selected window"). Force a full-history load.

**Files:**
- Modify: `src/pages/customers.py`

- [ ] **Step 1: Override `rfm` at the top of `render()`**

Add an import:

```python
from src.ui.page_loader import load_all
```

At the top of `render(filters)`:

```python
def render(filters: dict) -> None:
    countries = filters["countries"]

    # RFM is conventionally computed on the full history (recency =
    # days since last order, relative to the most recent date in the
    # dataset).  The global date slider is bypassed here.
    _FULL_START = "2009-12-01"
    _FULL_END   = "2011-12-09"
    rfm, *_ = load_all(_FULL_START, _FULL_END, countries, forecast_horizon=3)
    # ... rest of the page ...
```

Add a `st.caption(...)` near the top of the page:

```python
st.caption(
    "RFM nutzt die volle Datenhistorie. Recency = Tage seit letzter "
    "Bestellung, bezogen auf den jüngsten Datenpunkt 2011-12-09."
)
```

Keep `start_date`/`end_date`/`countries` from filters if the At-Risk-by-Country chart still uses them (it does — that chart shows the at-risk *share* per country, which is meaningful per selected period). If unused, drop them.

- [ ] **Step 2: Smoke + commit**

```bash
python -c "from src.pages import customers" 2>&1 | head -5
git add src/pages/customers.py
git commit -m "fix(customers): always use full history for RFM computation"
```

---

## Task 4: Overview — Kundensegmente single-color + semantic accents

Replace the rainbow `color_discrete_map` with a sorted single-color bar where each segment's color encodes its meaning (positive/negative/muted), pulled from `theme.SEGMENT_SEMANTICS`.

**Files:**
- Modify: `src/pages/overview.py`

- [ ] **Step 1: Edit the Kundensegmente block**

Find the existing chart (around line 142) and replace with:

```python
    with col_mid:
        st.subheader("Kundensegmente", anchor=False)
        seg_counts = (
            rfm['segment'].value_counts()
            .reset_index()
            .rename(columns={'segment': 'Segment', 'count': 'Anzahl', 'index': 'Segment'})
        )
        # Ensure column names are exact (older pandas may emit 'index')
        if 'count' in seg_counts.columns:
            seg_counts = seg_counts.rename(columns={'count': 'Anzahl'})
        # Sort ascending so the longest bar is on top in a horizontal bar
        seg_counts = seg_counts.sort_values('Anzahl', ascending=True)
        # Map each segment to its semantic color (gray for neutrals)
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
```

Why `color='_color', color_discrete_map='identity'`: this is Plotly's idiom for "the color column already contains hex codes, use them verbatim". No second mapping layer.

Add the import at the top of the file if not already present:

```python
from src.ui import theme
```

- [ ] **Step 2: Smoke + commit**

```bash
python -c "from src.pages import overview" 2>&1 | head -5
git add src/pages/overview.py
git commit -m "polish(overview): Kundensegmente → semantic single-color, sorted"
```

---

## Task 5: Forecast page — chart color cleanup

The main forecast bar chart currently uses `marker_color='#60a5fa'` for actuals and `marker_color='#f59e0b'` for forecast (left over from the original UI). Replace with `theme.CHART_HERO` for actuals and `theme.MUTED` (with dashed pattern via `marker_pattern`) for the forecast portion. The Saisonalitäts-Decomposition charts get a clarifying caption.

**Files:**
- Modify: `src/pages/forecast.py`

- [ ] **Step 1: Update the main forecast chart**

Find the `go.Figure()` construction in `forecast.py` (the one with `name='Ist-Umsatz'` and `name='Forecast'`). Replace the inline hex codes:

```python
# Actuals trace
fig.add_trace(go.Bar(
    x=chart_history['ds'], y=chart_history['y'],
    name='Ist-Umsatz',
    marker_color=theme.CHART_HERO,
    hovertemplate='%{x|%b %Y}<br>Ist: £%{y:,.0f}<extra></extra>',
))

# Forecast trace
fig.add_trace(go.Bar(
    x=future_forecast['ds'], y=future_forecast['yhat'],
    name='Forecast',
    marker_color=theme.MUTED,
    marker_pattern_shape='/',          # diagonal stripes = "not real yet"
    error_y=dict(
        type='data',
        array=(future_forecast['yhat_upper'] - future_forecast['yhat']).clip(lower=0),
        arrayminus=(future_forecast['yhat'] - future_forecast['yhat_lower']).clip(lower=0),
        color=theme.FAINT,
        thickness=1.5, width=4,
    ),
    hovertemplate='%{x|%b %Y}<br>Forecast: £%{y:,.0f}<extra></extra>',
))
```

Make sure `from src.ui import theme` is imported (or `from src.ui.theme import CHART_HERO, MUTED, FAINT`).

- [ ] **Step 2: Update other forecast-tab charts**

For the **Backtest** chart (`fig_bt`): make it single-color (chart_hero for the prediction, muted for actual). Find the `go.Scatter`/`go.Bar` traces and change their `marker_color` / `line=dict(color=...)` to `theme.CHART_HERO` / `theme.MUTED`.

For the **Trend** chart (`fig_trend`): single chart_hero line.

For the **Yearly** chart (`fig_yearly`): single chart_hero line/bar.

(If any of these uses `px.line` or `px.bar` without color overrides, the polish template's colorway will pick the right color from CHART_CATEGORICAL — but the FIRST color in that palette IS `CHART_HERO`, so single-series charts get hero-color for free. The cleanup here is for charts that have hardcoded marker_color/line color values.)

- [ ] **Step 3: Add caption to Saisonalitäts-Decomposition**

Before the trend chart, add:

```python
st.caption(
    "Prophet zerlegt den Forecast in Trend + Saisonalität. Der "
    "Langzeit-Trend ist nach Modell-Design stückweise linear "
    "(Changepoints) — die saisonale Variation siehst du im Hauptchart."
)
```

- [ ] **Step 4: Smoke + commit**

```bash
python -c "from src.pages import forecast" 2>&1 | head -5
git add src/pages/forecast.py
git commit -m "polish(forecast): use theme tokens for chart colors + trend caption"
```

---

## Task 6: Customers — country bar color

The "At-Risk Anteil pro Land" bar currently has its color encoded by the at-risk percentage (via `color='At_Risk_%'` and a `color_continuous_scale='Reds'`). Replace with single gray bars; the *length* already encodes the value, color is redundant.

**Files:**
- Modify: `src/pages/customers.py`

- [ ] **Step 1: Edit the country chart construction**

Find the `px.bar` for `fig_c`. Strip the `color=...` and `color_continuous_scale=...` kwargs. The new construction:

```python
fig_c = px.bar(
    country_summary,
    x='At_Risk_%', y='country', orientation='h',
    labels={'At_Risk_%': '', 'country': ''},
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
```

(Remove the previous `coloraxis_showscale=False` — it's only relevant when a coloraxis exists, which it now doesn't.)

Import: ensure `from src.ui import theme` is in the imports.

- [ ] **Step 2: Smoke + commit**

```bash
python -c "from src.pages import customers" 2>&1 | head -5
git add src/pages/customers.py
git commit -m "polish(customers): country chart → single chart-hero color"
```

---

## Task 7: Produkte — top-products + country color cleanup

Top-products: gray-by-default, accent in `chart_hero` on the selected bar (or top-1 if nothing selected). Country bar: same single-color treatment as customers.

**Files:**
- Modify: `src/pages/products.py`

- [ ] **Step 1: Top-products chart with conditional accent**

In `products.py`, find the top-products `px.bar` construction. Replace the `color='revenue', color_continuous_scale='Blues'` pattern with a manual color list:

```python
# Build a per-bar color list: chart-hero for the selected product,
# muted for everything else. Selection state lives in the previous
# chart event response.
selected_product = None
if "top_products_chart" in st.session_state:
    sel = st.session_state["top_products_chart"]
    if sel and sel.get("selection", {}).get("points"):
        selected_product = sel["selection"]["points"][0].get("y")

bar_colors = [
    theme.CHART_HERO if name == selected_product else theme.MUTED
    for name in top_products['description']
]
# If nothing is selected, highlight the top-1 (highest revenue) instead.
if selected_product is None and len(top_products) > 0:
    top_idx = top_products['revenue'].idxmax()
    top_name = top_products.loc[top_idx, 'description']
    bar_colors = [
        theme.CHART_HERO if name == top_name else theme.MUTED
        for name in top_products['description']
    ]

fig = px.bar(
    top_products, x='revenue', y='description', orientation='h',
    labels={'revenue': '', 'description': ''},
)
fig.update_traces(marker_color=bar_colors)
fig.update_layout(
    height=380,
    yaxis={'categoryorder': 'total ascending'},
)
fig = polish(fig, hide_legend=True)
fig.update_xaxes(tickformat=',.0f')
fig.update_layout(margin=dict(l=220))
selection = st.plotly_chart(
    fig, use_container_width=True,
    theme=None, config=PLOTLY_CONFIG,
    on_select="rerun", key="top_products_chart",
)
```

The `coloraxis_showscale=False` becomes unnecessary (no continuous colorbar exists anymore).

Import: ensure `from src.ui import theme` is present.

- [ ] **Step 2: Country chart — same treatment**

Find `fig_country` (the "Umsatz nach Land" bar). Replace its `color=...` kwarg with a flat `marker_color`:

```python
fig_country = px.bar(
    country_revenue,
    x='revenue', y='country', orientation='h',
    labels={'revenue': '', 'country': ''},
)
fig_country.update_traces(marker_color=theme.CHART_HERO)
fig_country.update_layout(
    height=420,
    yaxis={'categoryorder': 'total ascending'},
    xaxis_title='', yaxis_title='',
)
fig_country = polish(fig_country, hide_legend=True)
fig_country.update_xaxes(tickformat=',.0f')
fig_country.update_layout(margin=dict(l=140))
```

- [ ] **Step 3: Monthly trend chart**

If `fig_trend` (the monthly trend for a selected product) has any hardcoded color, replace with `theme.CHART_HERO`. If it uses `polish()`'s default colorway, no change needed.

- [ ] **Step 4: Smoke + commit**

```bash
python -c "from src.pages import products" 2>&1 | head -5
git add src/pages/products.py
git commit -m "polish(products): single-color charts with chart-hero accent on selection"
```

---

## Task 8: Final smoke + full test sweep

- [ ] **Step 1: Run tests**

```bash
pytest tests/ -q 2>&1 | tail -5
```
Expected: all green (existing ~156 + the new theme tests from Task 1).

- [ ] **Step 2: Import smoke**

```bash
python -c "import app" 2>&1 | grep -v -i "MemoryCache\|ScriptRunContext\|streamlit run\|view your Streamlit\|missing ScriptRunContext\|can be ignored" | head
```
Expected: no tracebacks.

- [ ] **Step 3: Headless dev-server**

```bash
streamlit run app.py --server.headless true --server.port 8590 > /tmp/p4smoke.log 2>&1 &
PID=$!
sleep 4
curl -s -o /dev/null -w "HTTP %{http_code}\n" "http://localhost:8590"
curl -s "http://localhost:8590/_stcore/health"
kill $PID 2>/dev/null
wait $PID 2>/dev/null
```
Expected: HTTP 200 and `ok`.

- [ ] **Step 4: Visual checkpoint**

Hand off to the user with the same checklist as Phase 3: walk each page, check
- Übersicht — Kundensegmente colors are now green/red/muted, not rainbow
- Forecast — caption explains the trend; charts blue+muted, not blue+orange
- Kunden — country bars all blue; caption explains RFM uses full history
- Produkte — top-products gray with one blue accent; country bars blue

---

## Definition of Done — Phase 4

- [ ] `pytest tests/` green
- [ ] `streamlit run app.py` runs every page; no tracebacks
- [ ] No `color_continuous_scale=` or `color_discrete_map=` calls remain in `src/pages/` except where they map to `theme.SEGMENT_SEMANTICS`
- [ ] Forecast + Kunden pages each have a visible caption noting the full-history override
- [ ] `theme.SEGMENT_SEMANTICS` exists and is referenced by both `overview.py` and (where useful) `customers.py`
- [ ] Forecast trend chart has a caption explaining the piecewise-linear behavior

## What's Next (Phase 5 preview)

Phase 5 rebuilds the AI / Decision-Agent panel: replaces `render_decision_panel` and `render_action_list` with `agent_recommendation_card`, adds the violet 4-px left border + sparkle icon, mandatory inline Evidence drilldown, Akzeptieren/Verwerfen + 👍/👎 buttons, freshness stamp, trace-ID. The Critic-Metriken `st.metric` block (currently default Streamlit look) gets the same KPI-card treatment.
