# Dashboard Redesign — Design Spec

**Date:** 2026-05-17
**Project:** Entscheidungsagent-BI — Retail BI / Decision-Agent Dashboard
**Scope:** End-to-end visual & structural redesign of the Streamlit dashboard, from default "tutorial-grade" look to SaaS-grade BI surface modeled on Linear / Stripe / Vercel / Tremor patterns.
**Path chosen:** B — Theme + Components + New Layout (Streamlit + Custom Components, ~3–5 days)

---

## 1. Motivation & Guiding Principles

The current dashboard reads as "Webdesign 101": default Plotly defaults, harsh white-body / dark-metric-card contrast, emoji-prefixed tabs, three incompatible chart palettes per page, large empty space below content, and an AI recommendation rendered as plain text with no evidence. Research across Linear, Stripe, Vercel, PostHog, Tremor, and shadcn/ui shows a strong consensus on what a modern BI dashboard looks like in 2026; the redesign applies that consensus.

Five non-negotiable principles drive every decision:

1. **Neutrals first, one accent.** ~90 % of pixel ink is grayscale. Color encodes meaning (status, primary series), not brand. The brand accent (violet `#6C5CE7`) appears only in active navigation and AI surfaces.
2. **One typeface, `tabular-nums` everywhere.** Inter + JetBrains Mono. Numbers always render with tabular figures so columns of digits align across cards and re-renders.
3. **Subtract chart ink.** No vertical gridlines, no axis spines, no tick marks, no modebar. Faint horizontal gridlines only. Direct labels replace legends where there are ≤ 4 series.
4. **AI surfaces are visually distinct.** Violet 4 px left border, sparkle icon, `ai-bg-tint` background, mandatory inline evidence drilldown, mandatory feedback affordance. No AI output ever appears without trace-ID and freshness stamp.
5. **Sidebar over tabs** once there are > 4 destinations. Tabs only for switching views of the same content within a page.

## 2. Design Tokens

Single source of truth lives in `src/ui/theme.py` (Python constants). A small build script renders `.streamlit/config.toml` from the same constants so native Streamlit theming and custom-component styling never diverge.

### 2.1 Colors (Light Mode)

```
# Surfaces (≈90 % of pixels)
bg-page          #FFFFFF
bg-card          #F8FAFC        Tailwind slate-50
bg-sidebar       #0F1020        dark contrast block
border           #E2E8F0        card borders, dividers
gridline         #F1F5F9        ultra-faint y-gridlines

# Text
heading          #0F172A
body             #334155
muted            #64748B        axis labels, captions
faint            #94A3B8        footnotes

# Brand accent — active nav, primary CTA only
primary          #6C5CE7        violet

# Semantic (status only — never used as chart categorical)
positive         #16A34A
negative         #DC2626
warning          #D97706
info             #2563EB

# AI accent (recommendation panels & chat)
ai-accent        #7C3AED
ai-bg-tint       #F5F3FF

# Chart categorical palette (Okabe–Ito, colorblind-safe, max 6)
chart-1          #0072B2        blue       (default "hero" series)
chart-2          #E69F00        orange
chart-3          #009E73        green
chart-4          #CC79A7        purple
chart-5          #56B4E9        sky
chart-6          #6B7280        gray
```

Dark mode is **out of scope for this redesign** — token slots are reserved (`bg-page-dark`, etc.) but the implementation ships light-only. A `polish_dark` Plotly template is built so dark mode can be added incrementally without re-architecting.

The brand accent (`primary`) and the chart "hero" color are **deliberately different**: violet is reserved for navigation and AI; blue is the default chart hero. This preserves AI as a recognizable surface and gives charts a more conventional BI feel.

### 2.2 Typography

- **Inter** (Google Fonts), weights 400 / 500 / 600
- **JetBrains Mono** for IDs, timestamps, trace-IDs

| Role | Size / line-height | Weight | Color |
|---|---|---|---|
| Page H1 | 24 / 32 | 600 | `heading` |
| Card H2 / chart title | 15 / 20 | 600 | `heading` |
| **KPI number** | **32 / 36** | **600 + tabular-nums** | `heading` |
| KPI delta (+8.1 %) | 13 / 16 | 500 | semantic |
| KPI label | 12 / 16 | 500, UPPERCASE, ls 0.02em | `muted` |
| Body | 14 / 20 | 400 | `body` |
| Chart axis tick | 12 / 16 | 400 | `muted` |
| Table cell | 13 / 20 | 400 + tabular-nums | `body` |
| Footnote | 11 / 16 | 400 | `faint` |

CSS rule applied globally: `font-variant-numeric: tabular-nums; font-feature-settings: "tnum" 1, "cv11" 1;` on `.kpi-number`, `.chart text`, and all table cells.

### 2.3 Spacing & Radius

- Card padding: 24 px
- Gap between cards: 16 px (tight — avoids "floating tiles")
- Card radius: 12 px (`baseRadius = "0.75rem"`)
- Button radius: 8 px
- Card edge: 1 px border (no shadow)
- Page max-width: 1280 px

## 3. Information Architecture

The five emoji-prefixed tabs are replaced by a left sidebar with two grouped destinations. The Agent area is split into three sub-pages because Recommendations, History, and Chat are independent surfaces.

```
┌──────────────────┬─────────────────────────────────────────────┐
│  RetailBI        │  Breadcrumb · Date-Range · Refresh · User   │  ← Top-Bar (48px)
│  ────────        ├─────────────────────────────────────────────┤
│  ANALYTICS       │                                             │
│  ▸ Übersicht     │                                             │
│    Forecast      │                Page Content                 │
│    Kunden        │                                             │
│    Produkte      │             (max-width 1280px)              │
│                  │                                             │
│  AGENT           │                                             │
│    Empfehlungen  │                                             │
│    Verlauf       │                                             │
│    Chat          │                                             │
│  ────────        │                                             │
│  Datenquelle     │                                             │
│  Einstellungen   │                                             │
└──────────────────┴─────────────────────────────────────────────┘
   220px wide
```

- **Sidebar** (220 px, `bg-sidebar`): rendered with `streamlit-antd-components.menu`. Lucide icons (16 px, stroke 1.5). Two groups (Analytics, Agent) separated by whitespace, no dividers. Two unattached items below (Datenquelle, Einstellungen). Active item: violet-tinted background block (`primary` at 10 % alpha), full opacity text. Inactive: 70 % opacity.
- **Top-Bar** (48 px, light): breadcrumb left, global date-range picker + refresh + avatar right.
- **Within-page tabs** (when needed for view-switching) use `streamlit-shadcn-ui.tabs` with an underline-active style — never used for primary navigation.

### 3.1 Page → Code mapping

| Sidebar entry | Page file | Notes |
|---|---|---|
| Übersicht | `src/pages/overview.py` | Landing page |
| Forecast | `src/pages/forecast.py` | |
| Kunden | `src/pages/customers.py` | Was "Kunden RFM"; RFM is implementation detail, not user language |
| Produkte | `src/pages/products.py` | |
| Agent → Empfehlungen | `src/pages/agent_recommendations.py` | All open + historical recs, filterable by status/priority |
| Agent → Verlauf | `src/pages/agent_history.py` | AgGrid table of all runs |
| Agent → Chat | `src/pages/agent_chat.py` | Existing chat re-wrapped |
| Datenquelle | `src/pages/data_source.py` | NEW. DB connection, data freshness, refresh button |
| Einstellungen | `src/pages/settings.py` | NEW. Language, AI model, future: dark-mode toggle |

### 3.2 Global date-range with local override

- A single date-range picker in the top-bar drives a value held in `st.session_state["global_date_range"]`.
- All pages consume it by default via `filters.with_global_range(df)`.
- Pages that need a different range (notably `customers.py` for RFM, which is computed on the full dataset) call `filters.with_local_override(...)` which renders an inline override UI on that page only and stores its value in a page-scoped session_state key.

## 4. KPI Cards

A single helper `kpi_card(...)` in `src/ui/cards.py` is the only way KPIs render anywhere in the dashboard. Four-part layout, fixed order; missing parts leave the slot empty without shifting the layout.

```
┌──────────────────────────────┐
│ LABEL                  ⓘ     │   12px UPPERCASE muted + optional tooltip
│                              │
│ £17,743,429                  │   32px tabular-nums heading-color
│ ↑ +8.1%  vs. Vormonat        │   13px semantic green/red + comparison
│                              │
│ ▁▂▃▅▆▇█▇▆▅▃▂▁                │   56px sparkline, axes off, last point dot
└──────────────────────────────┘
   1px border #E2E8F0, radius 12px, padding 24px
```

### 4.1 Sparkline rules

- 56 px tall, full card width, transparent background
- No axes, no gridlines, no tooltips, no modebar
- Line in `muted` (`#94A3B8`); last point as a 4 px dot in semantic color (green if trend ↑, red if ↓)
- All sparklines in a row use the **same y-domain scaling rule** (each card is scaled to its own range — but every card in a row covers the same time period)

### 4.2 Delta semantics

- Format: `↑ +8.1 % vs. Vormonat` — always arrow + percentage + explicit comparison phrase. Never bare "+8.1 %".
- Comparison method: **previous range of equal length** (if user has selected 90 days, comparison is the 90 days before that). Same rule on every page.
- `higher_is_better` parameter inverts color semantics: At-Risk customers, churn, costs → ↑ is red, ↓ is green.

### 4.3 Overview page KPIs

| # | Label | Value | Comparison | Sparkline | `higher_is_better` |
|---|---|---|---|---|---|
| 1 | GESAMTUMSATZ | Sum in range | prev range, same length | monthly revenue in range | True |
| 2 | AKTIVE KUNDEN | Distinct customer-IDs | prev range | active customers per month | True |
| 3 | AT-RISK KUNDEN | RFM At-Risk + Lost | prev range | at-risk per month | **False** |
| 4 | FORECAST NÄCHSTER MONAT | Forecast value | vs. last actual month | 12 actuals + 1 forecast; forecast portion rendered **dashed** to mark the actual→forecast boundary | True |

### 4.4 Signature

```python
kpi_card(
    label="Gesamtumsatz",
    value=17_743_429,
    value_format="£{:,.0f}",
    delta_pct=8.1,
    delta_period="vs. Vormonat",
    higher_is_better=True,
    sparkline=monthly_revenue_series,
    sparkline_split_at=None,        # index where sparkline switches to dashed (forecast)
    tooltip="Summe aller Bestellungen im gewählten Zeitraum",
)
```

## 5. Charts & Plotly Template

A single template module (`src/ui/viz_theme.py`) registers two Plotly templates (`polish_light`, `polish_dark`) and exports `polish(fig, ...)` which is the final transformation before `st.plotly_chart`. No chart in the codebase sets colors, fonts, margins, or hover styles directly.

### 5.1 Template behavior (fixed)

- Transparent paper + plot background — chart shows the card surface through it
- Font: Inter 13 px, axis labels in `muted`
- Y-gridlines only, `#F1F5F9`, 1 px. No vertical gridlines, no zero-line, no axis spines.
- No tick marks; axis labels float at plot edge
- Margins: `l=48, r=16, t=40, b=40`
- Hover: `hovermode="x unified"`, dark tooltip on `heading`, trace-name suffix removed via `<extra></extra>`
- Modebar: hidden by default
- Colorway: `[#0072B2, #E69F00, #009E73, #CC79A7, #56B4E9, #6B7280]`
- Legend: horizontal, top-left, no border, no background — or hidden in favor of direct labels

### 5.2 `polish()` signature

```python
polish(
    fig,
    y_format=",.0f",         # ",.0f" count, "£,.0f" money, ".1%" ratio
    reference=None,           # value of dotted reference line (target, prior)
    reference_label="Ziel",
    dark=False,
    hide_legend=False,
)
```

Render call:

```python
st.plotly_chart(fig, config=PLOTLY_CONFIG, use_container_width=True, theme=None)
```

`theme=None` is mandatory — without it Streamlit overrides the template.

### 5.3 Color discipline per chart type

| Chart type | Rule |
|---|---|
| Single-series line/bar (e.g. revenue trend) | One color: `chart-1` blue. No palette. |
| Sorted horizontal bar (e.g. top products) | All bars gray (`muted`); top-1 or selected bar in `chart-1`. Length encodes value — color is redundant. |
| Categorical segments (e.g. RFM Loyal/Champions/At-Risk/Lost) | Okabe–Ito in fixed order, **same segment name → same color everywhere**. |
| Forecast w/ uncertainty | `chart-1` line + transparent `chart-1` ribbon (alpha 0.15) for CI band. |
| Status / delta | Semantic colors only. |
| Heatmap (cohort) | Sequential blue scale `#EFF6FF → #1E3A8A`. |

### 5.4 Concrete redesign of overview charts

| Chart | Today | After |
|---|---|---|
| Umsatz-Trend (bars) | Default Plotly blue, visible axes, "Umsatz (£)" y-title | Single-color `chart-1` bars, `£.0M` y-format, no y-title (card title suffices), reference line for mean |
| Kundensegmente (horizontal bars, rainbow) | 5 colors | Sorted by count, all bars `muted`; Champions+Loyal in `positive`, At-Risk+Lost in `negative`, Others/New in `muted`. Values labeled at bar end. No legend. |
| (KI-Empfehlung area) | Plain text | Becomes the agent panel — see §6 |

### 5.5 Other pages

- **Forecast page**: line + ribbon CI, dashed transition at actual→forecast boundary, annotation for last actual value
- **Customers page**: RFM heatmap in sequential blue
- **Products page**: sorted horizontal bar of top products, gray with `chart-1` highlight for selection

## 6. Decision-Agent / AI Panel

The agent is the project's USP and gets its own visual language. PostHog / Linear / Notion all converge on the same idiom: violet accent, sparkle icon, mandatory inline evidence, mandatory feedback. We adopt it.

### 6.1 Recommendation card

```
┌──────────────────────────────────────────────────────────────┐
│ ╎  ✦ AGENT-EMPFEHLUNG          PRIORITÄT MITTEL  ●           │
│ ╎                                                            │
│ ╎  Sortiment bereinigen                                      │
│ ╎  298 Produkte zeigen ≥3 Monate rückläufigen Umsatz         │
│ ╎                                                            │
│ ╎  ▸ Evidenz ansehen (298 Produkte, Regel: revenue_decline)  │
│ ╎  ▸ Verlauf: 3 ähnliche Empfehlungen in den letzten 90 T.   │
│ ╎                                                            │
│ ╎  [ Akzeptieren ]  [ Verwerfen ]   👍 👎  · Lauf #a7c2…     │
│ ╎                                                            │
│ ╎  zuletzt aktualisiert: vor 12 Min · Quelle: rules v0.4     │
└──────────────────────────────────────────────────────────────┘
   4px left border in ai-accent
   subtle ai-bg-tint background
```

### 6.2 Required components (every recommendation, no exceptions)

1. **Visual marker** — violet 4 px left border + sparkle ✦
2. **Priority badge** with semantic dot — NIEDRIG / MITTEL / HOCH / KRITISCH. No emojis.
3. **Title** — the action in one imperative sentence
4. **Reason** — one concrete sentence with a number; hedged where uncertain ("vermutlich", "deutet auf …")
5. **Evidence drilldown** (`st.expander` styled): which rule fired (with thresholds), top-N affected rows, underlying KPI deltas. Sourced from `src/decision_agent.py` and `src/semantic.py`.
6. **History link** — count of similar recommendations in the last 90 days and their accept/reject rate. Sourced from `src/decision_log.py`.
7. **Decision affordance** — `[Akzeptieren]` / `[Verwerfen]` buttons writing to `decision_log.log_decision_outcome(...)`.
8. **Feedback affordance** — 👍 / 👎 writing to critic data (`src/critic.py`). **Separate from accept/reject** because a user can correctly reject a good recommendation (timing) or pragmatically accept a bad one.
9. **Trace-ID** — Mono font, small, clickable → opens full agent-run detail
10. **Freshness stamp** — relative time + source version ("rules v0.4")

### 6.3 Three surfaces

| Surface | Where | Content |
|---|---|---|
| Overview | Right column, single card | Top recommendation only (highest priority) |
| Agent / Empfehlungen | Vertical list, filterable | All open recs (with evidence expanded by default) + filter to show closed |
| Agent / Verlauf | AgGrid table | Row per run: date, priority, title, status, feedback. Click → detail drawer. |

### 6.4 State transitions

- **Akzeptieren** → recommendation disappears from Overview, appears in Verlauf with status `akzeptiert`
- **Verwerfen** → recommendation disappears from Overview, appears in Verlauf with status `verworfen`
- **Overview shows only open recommendations** to avoid status-badge clutter
- **`Agent / Empfehlungen` page** can filter by status (default: open)
- **Follow-up tracking** (was the action taken, did revenue recover) is **out of scope** for this redesign — the dataset is static 2010–2011, so it cannot be meaningfully validated

### 6.5 Chat page

The existing `src/agent_chat.py` (Ollama-backed) is re-rendered with parallel visual language:

- Chat bubbles with avatar indicator
- AI responses on `ai-bg-tint` with sparkle icon; user messages neutral
- When the response cites KPIs/rows, they render inline as small pills with trace-ID (e.g. `[298 Produkte ↗]`) clickable → opens the same evidence drilldown
- Input row sticky at bottom, with **dynamically-generated suggestion chips above** the input — chips are derived from the current page context (e.g. on Customers page: "Warum sind die At-Risk-Kunden gestiegen?"; on Products: "Welche Produkte laufen aus?"). Implementation reads the active page key from session_state and selects from a context→chips map; falls back to a global default list.

### 6.6 Module layout

```python
# src/ui/agent_panel.py
def agent_recommendation_card(rec: Recommendation, *, show_evidence_default=False) -> None: ...
def agent_decision_buttons(rec_id: str) -> None: ...
def agent_evidence_drilldown(rec: Recommendation) -> None: ...
def agent_history_summary(rec: Recommendation) -> None: ...
```

These orchestrate existing modules (`decision_agent`, `decision_log`, `critic`, `semantic`) — they don't reimplement logic.

## 7. File Structure

### 7.1 New files

```
src/
├── ui/
│   ├── __init__.py
│   ├── theme.py             # token constants (single source of truth)
│   ├── viz_theme.py         # polish_light / polish_dark templates + polish()
│   ├── cards.py             # kpi_card(), section_card()
│   ├── agent_panel.py       # see §6.6
│   ├── navigation.py        # sidebar_nav() via sac.menu + top_bar()
│   └── filters.py           # global_date_range(), with_local_override()
├── pages/
│   ├── overview.py
│   ├── forecast.py
│   ├── customers.py
│   ├── products.py
│   ├── agent_recommendations.py
│   ├── agent_history.py
│   ├── agent_chat.py
│   ├── data_source.py       # NEW page
│   └── settings.py          # NEW page
└── (existing modules unchanged: data_processing, rfm_analysis,
   forecasting, product_analysis, customer_analysis,
   decision_agent, decision_log, critic, semantic, agent_chat)

.streamlit/
└── config.toml              # generated from theme.py via a small build script

scripts/
└── render_streamlit_config.py   # reads theme.py → writes .streamlit/config.toml
```

### 7.2 Slimmed `app.py`

```python
# app.py — radically smaller after redesign
import streamlit as st
from src.ui.navigation import sidebar_nav, top_bar
from src.ui import theme  # registers fonts, injects global CSS
from src.pages import (
    overview, forecast, customers, products,
    agent_recommendations, agent_history, agent_chat,
    data_source, settings,
)

st.set_page_config(page_title="RetailBI — Entscheidungsagent",
                   layout="wide", initial_sidebar_state="expanded")

theme.inject_global_css()
active = sidebar_nav()           # returns active page key
top_bar()                        # renders global date-range etc.

PAGES = {
    "overview": overview.render,
    "forecast": forecast.render,
    "customers": customers.render,
    "products": products.render,
    "agent_recommendations": agent_recommendations.render,
    "agent_history": agent_history.render,
    "agent_chat": agent_chat.render,
    "data_source": data_source.render,
    "settings": settings.render,
}
PAGES[active]()
```

### 7.3 Dependencies (`requirements.txt` additions)

```
streamlit>=1.50
streamlit-extras>=0.4.0
streamlit-shadcn-ui>=0.1.19
streamlit-antd-components>=0.3.0
streamlit-aggrid>=1.0.0
plotly>=5.20
```

### 7.4 Lib responsibility boundaries

| Lib | Allowed use | Disallowed |
|---|---|---|
| `streamlit-antd-components` | Sidebar menu (`sac.menu`), Steps, Segmented | Cards, buttons, badges |
| `streamlit-shadcn-ui` | `ui.tabs` within pages, `ui.date_range_picker`, `ui.hover_card`, `ui.badge` | Top-level navigation |
| `streamlit-extras` | `grid()`, `dataframe_explorer`, `mention` | Built-in `metric_cards` (we build `kpi_card()` ourselves to integrate sparkline) |
| `streamlit-aggrid` | Tables ≥ 100 rows or selection→downstream widgets (`agent_history`, `products`) | KPI summary tables ≤ 20 rows (use `st.dataframe`) |
| native `st.*` | Layout (columns, container), `st.dataframe`, `st.plotly_chart`, all forms | Where a shadcn variant exists for the same purpose |

### 7.5 The iframe constraint (acknowledged)

`streamlit-shadcn-ui` and `streamlit-elements` each render inside an isolated iframe and **cannot inherit CSS from the host document**. This means:

- Tokens must be defined twice: once as Python constants in `theme.py` (consumed by our own components and passed as props to shadcn components), once mirrored to `.streamlit/config.toml` (consumed by native Streamlit elements).
- `scripts/render_streamlit_config.py` generates `config.toml` from `theme.py` to keep them in sync. The script runs on `make config` and is checked by CI (token drift fails the build).

## 8. Migration Plan (Phases)

Phases are gated; each ends in a working, deployable dashboard. Order is fixed for phases 1–3 (foundation is load-bearing); phases 4–7 may be reordered or parallelized.

| Phase | Scope | Risk |
|---|---|---|
| **1. Foundation** | `theme.py`, `viz_theme.py`, `config.toml` build script. Every existing chart wrapped in `polish(fig)`. No structural change. | Low. Visible change: charts already cleaner. |
| 2. Cards | `kpi_card()` implemented; 4 overview KPIs migrated. Old CSS hacks in `app.py` removed. | Low. |
| 3. Navigation | Sidebar (`sac.menu`) + Top-Bar with global date-range. `app.py` restructured to page-dispatch. All current tabs lifted into `pages/*.py`. | **Highest.** Sole phase that restructures `app.py`. |
| 4. Page content | Polish per page: overview, forecast, customers, products. Charts to single-color + direct labels. Layout via `grid()`. | Low–Medium. |
| 5. Agent panel | `agent_panel.py`; overview-card on new look; `Agent / Empfehlungen` + `Agent / Verlauf` pages. | Medium. |
| 6. Chat page | Existing `agent_chat.py` re-wrapped with suggestion chips and AI-surface look. | Low. |
| 7. Data-source + Settings | Two new pages, mostly thin. | Low. |

Phase 1 was chosen as first because it changes nothing structurally — once charts look right, the bar for the rest is set.

## 9. Testing Strategy

- **Visual snapshot tests** (Playwright, already a project dependency via `.playwright-mcp`): one screenshot per page in `tests/visual/`. Existing `screenshot-tab*.png` files become the "before" reference baseline (kept in a `tests/visual/before/` folder for comparison; new baselines saved to `tests/visual/baseline/`).
- **Unit tests** for helpers in `src/ui/`:
  - `kpi_card()` formats values correctly (`£.0f`, `.1%`, M-suffix for large numbers); inverts color semantics when `higher_is_better=False`
  - `polish(fig)` applies the registered template and the requested options
  - `global_date_range()` returns a sensible default when session_state is empty
  - `theme.py` constants compile into a valid `config.toml`
- **Smoke tests per page** using Streamlit's `AppTest`: each page loads without exceptions and the expected KPI labels appear.

## 10. Out of Scope (Explicit)

The following are deliberately excluded from this redesign:

- **Dark mode rollout** — tokens reserved, `polish_dark` built, but UI toggle and full surface coverage are a future phase
- **Follow-up status on accepted recommendations** — "did revenue recover?" requires live data; out of scope with the static 2010–2011 dataset
- **Custom React components** — the Streamlit-iframe constraints are accepted; no custom component is needed for this redesign
- **Mobile responsive design** — Streamlit's mobile behavior is acceptable for an internal dashboard; not a target
- **i18n** — interface stays in German; settings page reserves the slot for future locale switching
- **Authentication / multi-user state** — single-user assumption preserved

## 11. References

Inspiration & rationale sources consulted during research:

- Linear — [Dashboards best practices](https://linear.app/now/dashboards-best-practices), [How we redesigned the UI](https://linear.app/now/how-we-redesigned-the-linear-ui)
- Stripe — [Accessible color systems](https://stripe.com/blog/accessible-color-systems), [Empty state pattern](https://docs.stripe.com/stripe-apps/patterns/empty-state)
- Vercel — [Geist Colors](https://vercel.com/geist/colors), [Observability](https://vercel.com/products/observability)
- PostHog — [Dashboards docs](https://posthog.com/docs/product-analytics/dashboards), [Analyze data with AI](https://posthog.com/docs/product-analytics/analyze-data-ai)
- Tremor — [tremor.so](https://www.tremor.so/), [Area chart defaults](https://www.tremor.so/docs/visualizations/area-chart)
- shadcn/ui — [Dashboard example](https://ui.shadcn.com/examples/dashboard)
- Streamlit — [Theming docs](https://docs.streamlit.io/develop/concepts/configuration/theming), [Custom-component limitations](https://docs.streamlit.io/develop/concepts/custom-components/components-v1/limitations)
- Carbon Design System — [Data viz color palettes](https://carbondesignsystem.com/data-visualization/color-palettes/)
- Okabe–Ito palette — [hex reference](https://conceptviz.app/blog/okabe-ito-palette-hex-codes-complete-reference)
