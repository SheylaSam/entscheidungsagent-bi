# Dashboard Redesign — Phase 3: Navigation & Page Dispatch — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 6-tab strip with a sidebar-based menu, lift each tab's body into its own page file under `src/pages/`, and reduce `app.py` to a thin dispatcher. The KPI cards, Plotly polish, and design tokens from Phases 1–2 keep working without modification.

**Architecture:** A new `src/ui/navigation.py` module renders the sidebar menu using `streamlit-antd-components` (`sac.menu`). A new `src/ui/legacy_renderers.py` houses the existing `render_decision_panel`/`render_evidence_strip`/etc. helpers + their CSS until Phase 5 replaces them. A new `src/ui/page_loader.py` houses the cached data-loaders (`load_all`, `load_backtest`, etc.) + the small `forecast_baseline`/`short_baseline_label` helpers. Each page lives at `src/pages/<name>.py` and exports a `render(filters: dict) -> None` function. `app.py` becomes: imports → page config → CSS → sidebar widgets (filters) + `sidebar_nav()` → dispatch.

**Tech Stack:** `streamlit-antd-components` is the only new dep this phase. `streamlit-shadcn-ui` (top-bar date picker) and the agent sub-page split (`agent_history.py`) are deferred to Phase 4 / Phase 7.

**Reference:** [`docs/superpowers/specs/2026-05-17-dashboard-redesign-design.md`](../specs/2026-05-17-dashboard-redesign-design.md) §3, §7.

**Depends on:** Phases 1 & 2 merged.

**Out of scope:**
- `streamlit-shadcn-ui` (Phase 4 will swap the date slider for shadcn `date_range_picker`)
- A top-bar component (deferred — existing sidebar filters keep working)
- Splitting agent recommendations into separate `agent_history.py` + `agent_chat` sub-pages (the *Chat* page already exists separately; *History* split is Phase 7)
- New "Datenquelle" / "Einstellungen" pages (Phase 7)
- Filtering pages by the global date-range — already wired through the existing slider; no new filter behavior in this phase

---

## File Plan

**Create:**
- `src/ui/navigation.py` — `sidebar_nav()` using `sac.menu`; returns active page key
- `src/ui/legacy_renderers.py` — shared helpers moved out of `app.py`: `priority_meta`, `format_utility`, `render_decision_panel`, `render_evidence_strip`, `render_action_list`, `render_agent_trace`, `render_guardrails`, plus the inline `<style>` block that defines `.decision-panel`/`.evidence-strip`/`.action-list` etc.
- `src/ui/page_loader.py` — cached data-loaders moved out of `app.py`: `get_countries`, `load_backtest`, `load_all`, `load_customer_country`, `load_monthly_product`, `load_revenue_by_country`, `forecast_baseline`, `short_baseline_label`. Each remains decorated with `@st.cache_data` exactly as today.
- `src/pages/__init__.py` — empty package marker
- `src/pages/overview.py` — was Tab 1 (Übersicht)
- `src/pages/forecast.py` — was Tab 2 (Forecast)
- `src/pages/customers.py` — was Tab 3 (Kunden RFM)
- `src/pages/products.py` — was Tab 4 (Produkte)
- `src/pages/agent_recommendations.py` — was Tab 5 (KI-Entscheid)
- `src/pages/chat.py` — was Tab 6 (Chat-Agent)
- `tests/test_ui_navigation.py` — minimal AppTest smoke for the sidebar
- `tests/test_pages_smoke.py` — one shallow test per page (module import + `render` is callable)

**Modify:**
- `requirements.txt` — add `streamlit-antd-components>=0.3.0,<0.4`
- `app.py` — radically slimmed down (target ~80 lines): imports, `set_page_config`, CSS injection, data loading, sidebar filters, `sidebar_nav()` → dispatch table

---

## Conventions for Page Files

Every page file follows the same shape so reading one is enough to know all of them:

```python
"""Page: <user-facing name>.

Lifted from <tab N> of app.py during Phase 3.  Visual updates and the AI
panel redesign happen in later phases.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.express as px           # if used
import plotly.graph_objects as go     # if used

from src.ui.viz_theme import polish, PLOTLY_CONFIG
from src.ui.cards import kpi_card, prev_period_delta    # if used
from src.ui.legacy_renderers import (
    render_decision_panel,
    render_evidence_strip,
    # only what this page actually uses
)
from src.ui.page_loader import (
    load_all,
    forecast_baseline,
    short_baseline_label,
    # only what this page actually uses
)
# Domain modules that the page calls into directly:
from src.decision_agent import generate_recommendations
# etc.


def render(filters: dict) -> None:
    """Render the page. ``filters`` carries shared sidebar state.

    Expected keys: ``start_date`` (date), ``end_date`` (date),
    ``countries`` (tuple), ``forecast_baseline_mode`` (str).
    """
    # ... the body lifted from the original tab ...
```

`filters` is a plain dict so it's trivial to pass around and easy to extend without breaking callers.

---

## Task 1: Add `streamlit-antd-components` dep

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Append the new line to `requirements.txt`**

Add (alphabetically near the other streamlit lines):

```
streamlit-antd-components>=0.3.0,<0.4
```

- [ ] **Step 2: Install**

```bash
pip install -r requirements.txt
```

Expected: streamlit-antd-components installs without conflicts.

- [ ] **Step 3: Smoke-import**

```bash
python -c "import streamlit_antd_components as sac; print(sac.__version__)"
```

Expected: a version string ≥ 0.3.0.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "build(deps): add streamlit-antd-components for sidebar menu"
```

---

## Task 2: Extract legacy renderers into `src/ui/legacy_renderers.py`

A pure cut-and-paste move: lift the renderer functions + their associated `<style>` block out of `app.py` so pages can import them without circular references. **No behavior changes.**

**Files:**
- Create: `src/ui/legacy_renderers.py`
- Modify: `app.py` (delete the moved code, add import)

- [ ] **Step 1: Create `src/ui/legacy_renderers.py`**

Copy these functions verbatim from `app.py` (currently at the line numbers shown — verify by grep):

- `priority_meta(priority: str) -> dict` (~line 342)
- `format_utility(rec: dict) -> str` (~line 350)
- `render_decision_panel(rec, eyebrow="Management-Entscheid")` (~line 363)
- `render_evidence_strip(items)` (~line 381)
- `render_action_list(recommendations)` (~line 390)
- `render_agent_trace(trace)` (~line 411)
- `render_guardrails(guardrails)` (~line 423)

Each function's imports are `streamlit as st`, `pandas as pd`. Add the file header:

```python
"""Legacy renderers — kept until Phase 5 replaces them with the new AI panel.

These were originally inline in app.py.  Moving them here so pages can
import without circular dependencies.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd


_LEGACY_CSS = """
<style>
    .decision-panel {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-left: 5px solid var(--accent);
        border-radius: 8px;
        padding: 20px 22px;
        margin: 8px 0 18px;
        line-height: 1.35;
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
        gap: 12px;
        margin: 10px 0 18px;
    }
    .action-item {
        background: #111827;
        border: 1px solid #1f2937;
        border-left: 4px solid var(--accent);
        border-radius: 8px;
        padding: 14px 16px;
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
"""


def inject_legacy_css() -> None:
    """Inject the styles required by the renderers below.

    Called once near the top of app.py, after `theme.inject_global_css()`.
    """
    st.markdown(_LEGACY_CSS, unsafe_allow_html=True)


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
```

Verify the function bodies above match the current `app.py` content (use `git diff` of your edit against the original to be sure — minor whitespace differences are fine, behavior must be identical).

- [ ] **Step 2: Update `app.py`**

In `app.py`, delete the original function definitions of `priority_meta`, `format_utility`, `render_decision_panel`, `render_evidence_strip`, `render_action_list`, `render_agent_trace`, `render_guardrails`.

Also delete the inline `<style>` block at lines 25–66 (the one that defines `.decision-panel` etc.). It now lives in `legacy_renderers.inject_legacy_css()`.

At the import block at the top of `app.py`, add:

```python
from src.ui.legacy_renderers import (
    priority_meta, format_utility,
    render_decision_panel, render_evidence_strip,
    render_action_list, render_agent_trace, render_guardrails,
    inject_legacy_css,
)
```

After the existing `ui_theme.inject_global_css()` call, add:

```python
inject_legacy_css()
```

- [ ] **Step 3: Smoke**

```bash
python -c "import app" 2>&1 | head -10
```

Expected: no traceback.

```bash
streamlit run app.py
```
(can't run from agent; the implementer should at minimum confirm `import app` does not raise.)

- [ ] **Step 4: Commit**

```bash
git add src/ui/legacy_renderers.py app.py
git commit -m "refactor(ui): move legacy renderers + CSS into src/ui/legacy_renderers"
```

## Task 3: Extract data loaders into `src/ui/page_loader.py`

Same shape as Task 2: pure move, no behavior change. Carries the `@st.cache_data` decorations so caching keeps working.

**Files:**
- Create: `src/ui/page_loader.py`
- Modify: `app.py`

- [ ] **Step 1: Create `src/ui/page_loader.py`**

```python
"""Cached data loaders + small per-page helpers.

Pages call into these instead of duplicating SQL. Caching keys are
keyed by the function args so distinct date-range/country selections
each get their own cache entry.

Moved here from app.py during Phase 3.  No behavior change.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.customer_analysis import (
    load_primary_customer_country, summarize_segments_by_country,
)
from src.data_processing import get_connection
from src.forecasting import load_forecast, run_backtest
from src.product_analysis import load_product_analysis
from src.rfm_analysis import load_rfm
```

Then move the following functions from `app.py` into this file **verbatim** (decorators included). Find each by grep:

- `get_countries()` (~line 164)
- `load_backtest(start_date, end_date, countries)` (~line 219)
- `load_all(start_date, end_date, countries, forecast_horizon)` (~line 230)
- `load_customer_country(start_date, end_date, countries)` (~line 257)
- `load_monthly_product(start_date, end_date, countries)` (~line 267)
- `load_revenue_by_country(start_date, end_date, countries)` (~line 288)
- `forecast_baseline(actuals_df, mode)` (~line 444)
- `short_baseline_label(label)` (~line 450)
- `_json_default(value)` (~line 436)

If any of these has a different signature than listed, transcribe what's actually in `app.py` — don't trust the line numbers above blindly.

- [ ] **Step 2: Update `app.py`**

Delete the original function definitions in `app.py`. Add to the import block:

```python
from src.ui.page_loader import (
    get_countries, load_backtest, load_all,
    load_customer_country, load_monthly_product, load_revenue_by_country,
    forecast_baseline, short_baseline_label, _json_default,
)
```

Some imports that `app.py` had at top *only* because of these moved helpers (e.g. `load_rfm`, `load_forecast`, etc.) are now consumed only by `page_loader.py`. Leave them in `app.py` for now — pages will need them too, and we'll prune in Task 11 once pages exist.

- [ ] **Step 3: Smoke**

```bash
python -c "import app" 2>&1 | head -10
```
Expected: no traceback.

- [ ] **Step 4: Commit**

```bash
git add src/ui/page_loader.py app.py
git commit -m "refactor(ui): move data loaders into src/ui/page_loader"
```

---

## Task 4: `src/ui/navigation.py` — sidebar nav

**Files:**
- Create: `src/ui/navigation.py`
- Create: `tests/test_ui_navigation.py`

The sidebar is split into TWO blocks:
1. **Top**: navigation menu (`sac.menu`) — selecting a page sets `st.session_state["active_page"]`.
2. **Below the menu**: existing date-range slider + forecast settings (these stay where they are; we just call `render_filters_sidebar()` from `app.py` after the nav).

We render the nav with `streamlit-antd-components` (`sac.menu`). Icons come from sac's bundled lucide-icon names.

- [ ] **Step 1: Write a small unit test**

Create `tests/test_ui_navigation.py`:

```python
"""Minimal unit tests for the navigation module.

The actual `sac.menu` render is covered by an AppTest in
tests/test_pages_smoke.py; here we just verify the public surface
exists and that PAGE_KEYS/labels stay in sync.
"""
from src.ui import navigation


def test_page_keys_match_labels():
    assert set(navigation.PAGE_KEYS) == set(navigation.PAGE_LABELS.keys())


def test_default_active_page_is_overview():
    assert navigation.DEFAULT_PAGE == "overview"


def test_page_keys_exact_order():
    """Order in PAGE_KEYS drives sidebar item order — pin it."""
    assert navigation.PAGE_KEYS == (
        "overview", "forecast", "customers", "products",
        "agent_recs", "chat",
    )
```

- [ ] **Step 2: Run, verify it fails**

```bash
pytest tests/test_ui_navigation.py -v
```
Expected: ModuleNotFoundError.

- [ ] **Step 3: Create `src/ui/navigation.py`**

```python
"""Sidebar navigation built with streamlit-antd-components.

Public API:
    PAGE_KEYS     -- canonical ordered tuple of page keys
    PAGE_LABELS   -- key -> display label
    DEFAULT_PAGE  -- the key shown on first visit
    sidebar_nav() -> str   -- renders the menu, returns the active key
"""
from __future__ import annotations

import streamlit as st
import streamlit_antd_components as sac


PAGE_KEYS: tuple[str, ...] = (
    "overview", "forecast", "customers", "products",
    "agent_recs", "chat",
)

PAGE_LABELS: dict[str, str] = {
    "overview":   "Übersicht",
    "forecast":   "Forecast",
    "customers":  "Kunden",
    "products":   "Produkte",
    "agent_recs": "Empfehlungen",
    "chat":       "Chat-Agent",
}

# Lucide icon names (sac bundles them) — keep this small list curated.
_PAGE_ICONS: dict[str, str] = {
    "overview":   "bar-chart",
    "forecast":   "trending-up",
    "customers":  "users",
    "products":   "package",
    "agent_recs": "sparkles",
    "chat":       "message-square",
}

DEFAULT_PAGE: str = "overview"


def _menu_items() -> list[sac.MenuItem]:
    return [
        sac.MenuItem(label="ANALYTICS", type="group", children=[
            sac.MenuItem(PAGE_LABELS["overview"],   icon=_PAGE_ICONS["overview"]),
            sac.MenuItem(PAGE_LABELS["forecast"],   icon=_PAGE_ICONS["forecast"]),
            sac.MenuItem(PAGE_LABELS["customers"],  icon=_PAGE_ICONS["customers"]),
            sac.MenuItem(PAGE_LABELS["products"],   icon=_PAGE_ICONS["products"]),
        ]),
        sac.MenuItem(label="AGENT", type="group", children=[
            sac.MenuItem(PAGE_LABELS["agent_recs"], icon=_PAGE_ICONS["agent_recs"]),
            sac.MenuItem(PAGE_LABELS["chat"],       icon=_PAGE_ICONS["chat"]),
        ]),
    ]


def sidebar_nav() -> str:
    """Render the sidebar menu; return the active page key.

    The label-to-key mapping is internal — callers only ever see keys,
    so renaming a label later doesn't break dispatch.
    """
    with st.sidebar:
        selected_label = sac.menu(
            items=_menu_items(),
            index=PAGE_KEYS.index(
                st.session_state.get("active_page", DEFAULT_PAGE)
            ) + 1,  # +1 because group headers count as items in sac
            open_all=True,
            indent=18,
            size="md",
            key="sidebar_nav_menu",
        )

    # Reverse-map label → key.  Fall back to DEFAULT_PAGE if sac returns
    # a group header (shouldn't happen with open_all=True, but defensive).
    label_to_key = {v: k for k, v in PAGE_LABELS.items()}
    active_key = label_to_key.get(selected_label, DEFAULT_PAGE)
    st.session_state["active_page"] = active_key
    return active_key
```

**Note on the `index=` calculation:** `sac.menu` counts every entry including group headers when computing the `index`. The exact `+1` adjustment may need to be `+2` depending on whether each group header is an item. If the page doesn't open to "Übersicht" by default after Task 11's smoke test, adjust this number and re-test. Acceptable fix: hard-code `index=1` for the very first run.

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_ui_navigation.py -v
```
Expected: 3/3 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ui/navigation.py tests/test_ui_navigation.py
git commit -m "feat(ui): sidebar nav via streamlit-antd-components"
```

---

## Task 5: Lift Tab 1 (Übersicht) → `src/pages/overview.py`

**Files:**
- Create: `src/pages/__init__.py`
- Create: `src/pages/overview.py`

- [ ] **Step 1: Create the package marker**

Create `src/pages/__init__.py` containing:

```python
"""Page modules.  Each exposes ``render(filters: dict) -> None``."""
```

- [ ] **Step 2: Lift the Tab-1 body into `src/pages/overview.py`**

In `app.py`, the Tab-1 block currently sits between the comment `# ── Tab 1 ────...` (around line 459) and `# ── Tab 2 ────...` (around line 583). Lift its content into `src/pages/overview.py`. **Do not change any logic** — only wrap in a `render(filters)` function and add the file header + imports.

Inputs the page needs (read from `filters` dict):
- `actuals` — pre-loaded forecast actuals dataframe
- `forecast` — pre-loaded forecast dataframe
- `rfm` — pre-loaded RFM dataframe
- `recs` — pre-loaded recommendations
- `forecast_baseline_mode` — sidebar setting
- `next_forecast` — derived

Cleaner approach: pass the **raw loaded data** in `filters` (under keys like `actuals`, `forecast`, `rfm`, `recs`, `forecast_baseline_mode`) and compute the derived state inside `render()`. The page is then self-contained.

```python
"""Page: Übersicht (Overview).

Lifted from Tab 1 of app.py during Phase 3.  No logic changes.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd

from src.data_processing import get_connection
from src.ui.cards import kpi_card, prev_period_delta
from src.ui.legacy_renderers import render_decision_panel, render_action_list
from src.ui.page_loader import forecast_baseline, short_baseline_label
from src.ui.viz_theme import polish, PLOTLY_CONFIG


def render(filters: dict) -> None:
    actuals       = filters["actuals"]
    forecast      = filters["forecast"]
    rfm           = filters["rfm"]
    recs          = filters["recs"]
    forecast_baseline_mode = filters["forecast_baseline_mode"]

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
        st.markdown('<div class="section-kicker">Weitere Massnahmen</div>',
                    unsafe_allow_html=True)
        render_action_list(recs[1:4])

    # ── KPI-Strip (was render_evidence_strip in Phase 2) ────────────────────
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
            tooltip="Prognose des Monatsumsatzes mit Prophet.",
        )

    st.markdown('<div class="section-kicker">Belege</div>', unsafe_allow_html=True)
    col_left, col_mid = st.columns([1.35, 1])

    # NOTE: The two charts that follow (Umsatztrend bar + Kundensegmente
    # bar) live below the comment "section-kicker Belege" in the current
    # app.py.  Copy them verbatim — they already use polish() + PLOTLY_CONFIG
    # from Phase 1.
    with col_left:
        st.subheader("Umsatztrend")
        import plotly.express as px
        fig = px.bar(actuals.tail(12), x='ds', y='y',
                     labels={'ds': '', 'y': ''})
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
```

When you lift the body, **read the current Tab-1 block carefully**. If anything differs from the snippet above (e.g., the WIP commit added new behavior), preserve the difference. The snippet above represents what the spec expects — your job is to reflect reality.

- [ ] **Step 3: Smoke import**

```bash
python -c "from src.pages import overview; print(callable(overview.render))"
```
Expected: `True`.

- [ ] **Step 4: Commit**

```bash
git add src/pages/__init__.py src/pages/overview.py
git commit -m "feat(pages): lift Übersicht tab into src/pages/overview.py"
```

---

## Task 6: Lift Tab 2 (Forecast) → `src/pages/forecast.py`

**Files:**
- Create: `src/pages/forecast.py`

- [ ] **Step 1: Identify the Tab-2 body**

In `app.py`, Tab 2's body sits between the comments `# ── Tab 2 ────...` (~line 583) and `# ── Tab 3 ────...` (~line 769). It's large (~180 lines): contains the forecast recommendation panel, evidence strip, main forecast bar chart, forecast table, backtest section with optional charts.

- [ ] **Step 2: Lift it**

Create `src/pages/forecast.py` with this skeleton, then transplant the Tab-2 body verbatim into `render()`:

```python
"""Page: Forecast & Umsatzrisiko.

Lifted from Tab 2 of app.py during Phase 3.  No logic changes.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.ui.legacy_renderers import render_decision_panel, render_evidence_strip
from src.ui.page_loader import (
    forecast_baseline, short_baseline_label, load_backtest,
)
from src.ui.viz_theme import polish, PLOTLY_CONFIG


def render(filters: dict) -> None:
    actuals               = filters["actuals"]
    forecast              = filters["forecast"]
    forecast_baseline_mode = filters["forecast_baseline_mode"]
    start_date            = filters["start_date"]
    end_date              = filters["end_date"]
    countries             = filters["countries"]

    # ── [paste the entire Tab-2 body here, replacing references to
    #     module-level helpers with the imported names if needed] ──
    ...
```

**Carefully copy** the Tab-2 body. Replace any reference to `from src.X import Y` that's no longer at the top of `app.py` with a local import inside `render()` or at the page-module level.

- [ ] **Step 3: Smoke**

```bash
python -c "from src.pages import forecast; print(callable(forecast.render))"
```

- [ ] **Step 4: Commit**

```bash
git add src/pages/forecast.py
git commit -m "feat(pages): lift Forecast tab into src/pages/forecast.py"
```

---

## Task 7: Lift Tab 3 (Kunden RFM) → `src/pages/customers.py`

**Files:**
- Create: `src/pages/customers.py`

- [ ] **Step 1: Lift the Tab-3 body**

Tab 3 sits between `# ── Tab 3 ────...` (~line 769) and `# ── Tab 4 ────...` (~line 847).

```python
"""Page: Kunden (RFM).

Lifted from Tab 3 of app.py during Phase 3.  No logic changes.
"""
from __future__ import annotations

import streamlit as st
import plotly.express as px

from src.ui.legacy_renderers import render_decision_panel, render_evidence_strip
from src.ui.page_loader import load_customer_country
from src.ui.viz_theme import polish, PLOTLY_CONFIG


def render(filters: dict) -> None:
    rfm        = filters["rfm"]
    start_date = filters["start_date"]
    end_date   = filters["end_date"]
    countries  = filters["countries"]

    # ── [paste Tab-3 body verbatim, preserving the country chart's
    #     update_xaxes(tickformat='.0%') restored in commit a8a3eaf] ──
    ...
```

**Important:** the country chart has `coloraxis_showscale=False`, `yaxis={'categoryorder': 'total ascending'}`, and `fig.update_xaxes(tickformat='.0%')` — all of which were carefully restored in commit `a8a3eaf`. Preserve them exactly.

- [ ] **Step 2: Smoke + commit**

```bash
python -c "from src.pages import customers; print(callable(customers.render))"
git add src/pages/customers.py
git commit -m "feat(pages): lift Kunden RFM tab into src/pages/customers.py"
```

---

## Task 8: Lift Tab 4 (Produkte) → `src/pages/products.py`

**Files:**
- Create: `src/pages/products.py`

- [ ] **Step 1: Lift the Tab-4 body**

Tab 4 sits between `# ── Tab 4 ────...` (~line 847) and `# ── Tab 5 ────...` (~line 940).

```python
"""Page: Produkte.

Lifted from Tab 4 of app.py during Phase 3.  No logic changes.
"""
from __future__ import annotations

import streamlit as st
import plotly.express as px

from src.ui.legacy_renderers import render_decision_panel, render_evidence_strip
from src.ui.page_loader import load_monthly_product, load_revenue_by_country
from src.ui.viz_theme import polish, PLOTLY_CONFIG


def render(filters: dict) -> None:
    # ... lifted body ...
    ...
```

The top-products chart has `on_select='rerun'` and `key='top_products_chart'` — preserve both. The country chart has `coloraxis_showscale=False`, `categoryorder='total ascending'`, and `update_xaxes(tickformat=',.0f')` from commit `dc529f5` — preserve all of them.

- [ ] **Step 2: Smoke + commit**

```bash
python -c "from src.pages import products; print(callable(products.render))"
git add src/pages/products.py
git commit -m "feat(pages): lift Produkte tab into src/pages/products.py"
```

---

## Task 9: Lift Tab 5 (KI-Entscheid) → `src/pages/agent_recommendations.py`

**Files:**
- Create: `src/pages/agent_recommendations.py`

- [ ] **Step 1: Lift the Tab-5 body**

Tab 5 sits between `# ── Tab 5 ────...` (~line 940) and `# ── Tab 6: Chat-Agent ────...` (~line 1245). This is the biggest tab (~300 lines): agent run, trace, guardrails, recommendations, decision log, critic.

```python
"""Page: Agent — Empfehlungen, Verlauf, Critic.

Lifted from Tab 5 of app.py during Phase 3.  No logic changes.

A later phase (per spec §3) splits this into separate
``agent_history.py`` and an enhanced recommendations page.
"""
from __future__ import annotations

import json
import streamlit as st
import pandas as pd

from src.decision_agent import generate_agent_run
from src.decision_log import list_agent_runs, log_agent_run, log_decision_outcome
from src.critic import analyze_decision_history
from src.ui.legacy_renderers import (
    render_decision_panel, render_evidence_strip,
    render_agent_trace, render_guardrails,
)
from src.ui.page_loader import _json_default


def render(filters: dict) -> None:
    # ... lifted body ...
    ...
```

This tab uses `st.metric` extensively in the Critic sub-section. Those metric cards will appear in Streamlit's default look (no dark background — Phase 2's cleanup intentionally removed that hack). Phase 5 replaces them.

- [ ] **Step 2: Smoke + commit**

```bash
python -c "from src.pages import agent_recommendations; print(callable(agent_recommendations.render))"
git add src/pages/agent_recommendations.py
git commit -m "feat(pages): lift KI-Entscheid tab into src/pages/agent_recommendations.py"
```

---

## Task 10: Lift Tab 6 (Chat-Agent) → `src/pages/chat.py`

**Files:**
- Create: `src/pages/chat.py`

- [ ] **Step 1: Lift the Tab-6 body**

Tab 6 starts at `# ── Tab 6: Chat-Agent ────...` (~line 1245) and runs to the end of the file.

```python
"""Page: Chat-Agent.

Lifted from Tab 6 of app.py during Phase 3.  No logic changes.
"""
from __future__ import annotations

import streamlit as st

from src.agent_chat import AAIAgent, AgentContext, OllamaNotAvailable


def render(filters: dict) -> None:
    # ... lifted body ...
    ...
```

- [ ] **Step 2: Smoke + commit**

```bash
python -c "from src.pages import chat; print(callable(chat.render))"
git add src/pages/chat.py
git commit -m "feat(pages): lift Chat-Agent tab into src/pages/chat.py"
```

---

## Task 11: Rewrite `app.py` as thin dispatcher

This is the moment of truth: with all pages lifted, `app.py` becomes ~80 lines.

**Files:**
- Modify: `app.py`
- Create: `tests/test_pages_smoke.py`

- [ ] **Step 1: Replace `app.py` body**

Open `app.py`. Keep:
- The top-of-file imports (prune any that are no longer used)
- `st.set_page_config(...)`
- `ui_theme.inject_global_css()`
- `inject_legacy_css()` (from Task 2)
- `build_database()` initial-run logic
- The sidebar **filters** block (date slider, forecast settings) — keep as-is

Delete:
- All 6 `with tabN:` blocks
- The `tab1, tab2, ... = st.tabs([...])` line

After the sidebar filters block, add:

```python
# ── Load shared data once per run ───────────────────────────────────────────
from src.ui.page_loader import load_all  # local import OK; module-level fine too

actuals, forecast, rfm, declining, top_products, country_seg = load_all(
    start_date.isoformat(),
    end_date.isoformat(),
    tuple(selected_countries),
    forecast_horizon=3,
)

# Compute recommendations once
agent_forecast_base = (
    actuals.tail(3)['y'].mean()
    if forecast_baseline_mode == "Durchschnitt letzte 3 Monate" and len(actuals) >= 3
    else actuals['y'].iloc[-1]
)
recs = generate_recommendations(
    forecast, rfm, declining,
    actuals_df=actuals,
    comparison_value=agent_forecast_base,
)

filters = {
    "start_date": start_date,
    "end_date": end_date,
    "countries": tuple(selected_countries),
    "forecast_baseline_mode": forecast_baseline_mode,
    "actuals": actuals,
    "forecast": forecast,
    "rfm": rfm,
    "declining": declining,
    "top_products": top_products,
    "country_seg": country_seg,
    "recs": recs,
}

# ── Navigation + dispatch ───────────────────────────────────────────────────
from src.ui.navigation import sidebar_nav
from src.pages import (
    overview, forecast as forecast_page, customers, products,
    agent_recommendations, chat,
)

PAGES = {
    "overview":   overview.render,
    "forecast":   forecast_page.render,
    "customers":  customers.render,
    "products":   products.render,
    "agent_recs": agent_recommendations.render,
    "chat":       chat.render,
}

active = sidebar_nav()
PAGES[active](filters)
```

If `selected_countries` isn't already defined in the sidebar block (the current app may use a different variable name), use whatever the sidebar produces.

- [ ] **Step 2: Prune unused imports in `app.py`**

After the rewrite, `app.py` should NOT import anything that's now only used inside `src/pages/*` or `src/ui/page_loader.py`. Run:

```bash
python -c "import app" 2>&1 | head -10
```
If clean, good. Then visually scan the import block — remove any `from src.X import Y` line that's no longer used in `app.py`.

- [ ] **Step 3: Smoke test the pages**

Create `tests/test_pages_smoke.py`:

```python
"""Shallow smoke tests for each page module.

These don't run the full Streamlit script — they just verify the
module imports successfully and exposes a callable ``render`` symbol.
Full end-to-end smoke happens via the manual `streamlit run app.py`
checkpoint after Task 12.
"""
import importlib
import pytest


PAGE_MODULES = [
    "src.pages.overview",
    "src.pages.forecast",
    "src.pages.customers",
    "src.pages.products",
    "src.pages.agent_recommendations",
    "src.pages.chat",
]


@pytest.mark.parametrize("module_name", PAGE_MODULES)
def test_page_module_imports_and_exposes_render(module_name):
    mod = importlib.import_module(module_name)
    assert hasattr(mod, "render"), f"{module_name} missing render()"
    assert callable(mod.render), f"{module_name}.render is not callable"
```

Run it:

```bash
pytest tests/test_pages_smoke.py -v
```
Expected: 6/6 PASS.

- [ ] **Step 4: Full test suite**

```bash
pytest tests/ -q 2>&1 | tail -10
```
Expected: all tests still pass (we expect ~150+ now).

- [ ] **Step 5: Final import smoke**

```bash
python -c "import app" 2>&1 | head -10
```
Expected: no traceback. ScriptRunContext warnings are fine.

- [ ] **Step 6: Commit**

```bash
git add app.py tests/test_pages_smoke.py
git commit -m "feat(app): replace tabs with sidebar nav + page dispatch"
```

---

## Task 12: Manual visual smoke + cleanup

- [ ] **Step 1: Run the app**

```bash
streamlit run app.py
```

Walk through every sidebar item:

- **Übersicht** — KPI cards + 2 charts render; decision panel still has its dark style
- **Forecast** — main chart + reference line + backtest section + tables
- **Kunden** — RFM scatter + country bar (percentage formatting + sorted by value)
- **Produkte** — top-products bar (clickable for drilldown!) + trend + country
- **Empfehlungen** (was KI-Entscheid) — full agent run + trace + guardrails + decision log + critic
- **Chat-Agent** — chat interface (Ollama required for actual replies)

Watch the terminal for tracebacks. The sidebar should now show two groups (ANALYTICS, AGENT) and the existing filter sliders below them.

- [ ] **Step 2: Any quick fixes**

If you find a regression (most likely: a page references a helper that didn't get re-imported), fix it directly in the relevant page file and commit:

```bash
git add src/pages/<file>.py
git commit -m "fix(pages): <what was broken>"
```

- [ ] **Step 3: Final repository state check**

```bash
wc -l app.py
```
Expected: < 150 lines. (Was 1293.)

```bash
git log --oneline main..HEAD | wc -l
```
Just shows the running commit count for the branch.

```bash
git status --short
```
Expected: clean.

---

## Definition of Done — Phase 3

- [ ] `pytest tests/` is green
- [ ] `streamlit run app.py` renders every page reachable from the new sidebar without exception
- [ ] `app.py` is < 150 lines
- [ ] No `with tab` blocks remain in `app.py`
- [ ] `src/pages/` contains 6 page files, each exposing `render(filters)`
- [ ] `src/ui/navigation.py` exists and `sidebar_nav()` returns a page key
- [ ] `streamlit-antd-components` is in `requirements.txt`

## What's Next (Phase 4 preview)

Phase 4 polishes each page individually: replace the dark `render_decision_panel` style on Übersicht / Forecast / Kunden / Produkte with a quieter `section_card()`, swap remaining inline color choices for the chart-categorical tokens, replace the country sort-by-value bar with a fully Tremor-style "single hue + top-N accent" treatment, and (the visible win) swap the native date slider for `streamlit-shadcn-ui.date_range_picker` in the top-bar of every page. Phase 5 rebuilds the AI panel; Phase 6 polishes the chat; Phase 7 adds Datenquelle + Einstellungen pages and splits agent recommendations from agent history.
