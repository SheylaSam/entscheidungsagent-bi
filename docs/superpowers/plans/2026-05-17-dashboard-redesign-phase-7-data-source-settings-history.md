# Dashboard Redesign — Phase 7: Datenquelle + Einstellungen + Agent-History — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close out the redesign by (a) creating the two new sidebar pages from the spec (Datenquelle, Einstellungen), (b) splitting the agent recommendations page into a focused "Empfehlungen" page + a dedicated "Verlauf" history page, and (c) wiring all three into the sidebar navigation.

**Architecture:** Three new page modules under `src/pages/`. The split: history-related sections (persisted runs list, decision log, Critic) move from `agent_recommendations.py` into a new `agent_history.py`. The recommendations page stays focused on the current agent run (live recs + rule status + trace + guardrails + human-in-the-loop). The sidebar grows by 3 entries (`agent_history`, `data_source`, `settings`); the Agent group now has 3 items (Empfehlungen, Verlauf, Chat) and the two new "system" entries sit at the bottom of the sidebar.

**Tech Stack:** Phases 1–6 stack. No new dependencies (we keep `st.dataframe` for the history table — `streamlit-aggrid` was discussed but not needed to ship this phase).

**Reference:** [`docs/superpowers/specs/2026-05-17-dashboard-redesign-design.md`](../specs/2026-05-17-dashboard-redesign-design.md) §3.1 (page mapping), §3 (sidebar groups).

**Depends on:** Phases 1–6 merged.

**Out of scope:**
- `streamlit-aggrid` adoption (would be nice for filterable history; defer)
- Dark-mode toggle in Einstellungen (no dark-mode rollout yet — leave a placeholder note)
- Moving the Mindestumsatz Produkt slider from sidebar to Einstellungen (kept in sidebar; users expect filters there)
- Per-user persistence of Einstellungen (session-state only)

---

## File Plan

**Create:**
- `src/pages/data_source.py`
- `src/pages/settings.py`
- `src/pages/agent_history.py`
- `tests/test_pages_smoke.py` — already exists; parametrized test list grows by 3 entries

**Modify:**
- `src/ui/navigation.py` — extend `PAGE_KEYS`, `PAGE_LABELS`, `_PAGE_ICONS`, `_menu_items()` for the three new pages
- `tests/test_ui_navigation.py` — update the canonical order test
- `src/pages/agent_recommendations.py` — remove the sections that moved to `agent_history.py`
- `app.py` — extend `PAGES` dispatch table

---

## Sidebar Layout (after Phase 7)

```
ANALYTICS
  Übersicht
  Forecast
  Kunden
  Produkte

AGENT
  Empfehlungen        ← live agent run, rule status, trace, accept/reject
  Verlauf             ← NEW: persisted runs, decision outcomes, Critic
  Chat-Agent

SYSTEM                ← NEW group
  Datenquelle         ← NEW: DB status, freshness, rebuild button
  Einstellungen       ← NEW: model defaults, info
```

The Empfehlungen / Verlauf split is the "Section 3" promise that we deferred during Phase 3 — now landing.

---

## Task 1: Extend `src/ui/navigation.py`

Three new page keys. The canonical order test in `tests/test_ui_navigation.py` needs to be updated.

**Files:**
- Modify: `src/ui/navigation.py`
- Modify: `tests/test_ui_navigation.py`

- [ ] **Step 1: Update the canonical-order test**

In `tests/test_ui_navigation.py`, replace the existing `test_page_keys_exact_order` assertion with:

```python
def test_page_keys_exact_order():
    assert navigation.PAGE_KEYS == (
        "overview", "forecast", "customers", "products",
        "agent_recs", "agent_history", "chat",
        "data_source", "settings",
    )
```

Add one new test:

```python
def test_system_pages_in_labels():
    for key in ("data_source", "settings"):
        assert key in navigation.PAGE_LABELS
        assert key in navigation.PAGE_KEYS
```

- [ ] **Step 2: Run, verify they fail**

`pytest tests/test_ui_navigation.py -v` → 2 tests fail.

- [ ] **Step 3: Extend `navigation.py`**

Update the four module-level constants/functions:

```python
PAGE_KEYS: tuple[str, ...] = (
    "overview", "forecast", "customers", "products",
    "agent_recs", "agent_history", "chat",
    "data_source", "settings",
)

PAGE_LABELS: dict[str, str] = {
    "overview":      "Übersicht",
    "forecast":      "Forecast",
    "customers":     "Kunden",
    "products":      "Produkte",
    "agent_recs":    "Empfehlungen",
    "agent_history": "Verlauf",
    "chat":          "Chat-Agent",
    "data_source":   "Datenquelle",
    "settings":      "Einstellungen",
}

_PAGE_ICONS: dict[str, str] = {
    "overview":      "bar-chart",
    "forecast":      "graph-up",
    "customers":     "people",
    "products":      "box",
    "agent_recs":    "stars",
    "agent_history": "clock-history",
    "chat":          "chat-dots",
    "data_source":   "database",
    "settings":      "gear",
}
```

Then update `_menu_items()` so the AGENT group has three children and a new SYSTEM group is appended:

```python
def _menu_items() -> list:
    return [
        sac.MenuItem(label="ANALYTICS", type="group", children=[
            sac.MenuItem(PAGE_LABELS["overview"],   icon=_PAGE_ICONS["overview"]),
            sac.MenuItem(PAGE_LABELS["forecast"],   icon=_PAGE_ICONS["forecast"]),
            sac.MenuItem(PAGE_LABELS["customers"],  icon=_PAGE_ICONS["customers"]),
            sac.MenuItem(PAGE_LABELS["products"],   icon=_PAGE_ICONS["products"]),
        ]),
        sac.MenuItem(label="AGENT", type="group", children=[
            sac.MenuItem(PAGE_LABELS["agent_recs"],    icon=_PAGE_ICONS["agent_recs"]),
            sac.MenuItem(PAGE_LABELS["agent_history"], icon=_PAGE_ICONS["agent_history"]),
            sac.MenuItem(PAGE_LABELS["chat"],          icon=_PAGE_ICONS["chat"]),
        ]),
        sac.MenuItem(label="SYSTEM", type="group", children=[
            sac.MenuItem(PAGE_LABELS["data_source"], icon=_PAGE_ICONS["data_source"]),
            sac.MenuItem(PAGE_LABELS["settings"],    icon=_PAGE_ICONS["settings"]),
        ]),
    ]
```

- [ ] **Step 4: Run, verify pass**

```bash
pytest tests/test_ui_navigation.py -v
pytest tests/ -q | tail -3
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add src/ui/navigation.py tests/test_ui_navigation.py
git commit -m "feat(nav): add data_source, settings, agent_history sidebar entries"
```

---

## Task 2: `src/pages/data_source.py`

Shows the DB connection status, data freshness, and a rebuild button. Read-only / one button.

**Files:**
- Create: `src/pages/data_source.py`

- [ ] **Step 1: Implement the page**

```python
"""Page: Datenquelle.

Read-only overview of the SQLite database that backs the dashboard
plus a rebuild button.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.data_processing import DB_PATH, build_database, get_connection
from src.ui.cards import kpi_card


def render(filters: dict) -> None:
    st.title("Datenquelle")
    st.caption(
        "Online Retail II (UCI ML Repository) · 2009–2011 · "
        "SQLite-Snapshot lokal, kein Live-Feed."
    )

    db_exists = DB_PATH.exists()
    db_size_mb: float | None = None
    n_rows = 0
    n_customers = 0
    min_date = max_date = None

    if db_exists:
        db_size_mb = DB_PATH.stat().st_size / (1024 * 1024)
        conn = get_connection()
        n_rows = pd.read_sql("SELECT COUNT(*) AS n FROM transactions", conn)["n"].iloc[0]
        n_customers = pd.read_sql(
            "SELECT COUNT(DISTINCT customer_id) AS n FROM transactions "
            "WHERE customer_id IS NOT NULL",
            conn,
        )["n"].iloc[0]
        bounds = pd.read_sql(
            "SELECT MIN(invoice_date) AS mn, MAX(invoice_date) AS mx FROM transactions",
            conn,
        )
        min_date = bounds["mn"].iloc[0]
        max_date = bounds["mx"].iloc[0]

    # ── Status row ────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        kpi_card(
            label="Status",
            value=("OK" if db_exists else "FEHLT"),
            value_format="{}",
            delta_pct=None, delta_period="", higher_is_better=True,
            sparkline=None,
            tooltip=f"SQLite-Datei: {DB_PATH}",
        )
    with c2:
        kpi_card(
            label="Transaktionen",
            value=int(n_rows) if db_exists else None,
            value_format="{:,.0f}",
            delta_pct=None, delta_period="", higher_is_better=True,
            sparkline=None,
        )
    with c3:
        kpi_card(
            label="Distinct Kunden",
            value=int(n_customers) if db_exists else None,
            value_format="{:,.0f}",
            delta_pct=None, delta_period="", higher_is_better=True,
            sparkline=None,
        )
    with c4:
        kpi_card(
            label="Dateigrösse",
            value=db_size_mb if db_size_mb is not None else None,
            value_format="{:.1f} MB",
            delta_pct=None, delta_period="", higher_is_better=True,
            sparkline=None,
        )

    # ── Date range + path ─────────────────────────────────────────────────
    st.subheader("Zeitraum", anchor=False)
    if db_exists and min_date and max_date:
        st.markdown(
            f"**Erste Transaktion:** {min_date}  \n"
            f"**Letzte Transaktion:** {max_date}"
        )
    else:
        st.warning("Datenbank fehlt — bitte unten neu aufbauen.")

    st.subheader("Speicherort", anchor=False)
    st.code(str(DB_PATH.resolve()))

    # ── Rebuild action ────────────────────────────────────────────────────
    st.subheader("Aktionen", anchor=False)
    if st.button("Datenbank neu aufbauen",
                 help="Liest die Excel-Quelle erneut und schreibt SQLite "
                      "neu (~30–90 Sekunden beim ersten Mal)."):
        with st.spinner("Importiere Daten…"):
            build_database()
        st.success("Datenbank wurde neu aufgebaut.")
        st.rerun()
```

- [ ] **Step 2: Smoke**

```bash
python -c "from src.pages import data_source; print(callable(data_source.render))"
```
Expected: `True`.

- [ ] **Step 3: Commit**

```bash
git add src/pages/data_source.py
git commit -m "feat(pages): Datenquelle — DB status, freshness, rebuild button"
```

---

## Task 3: `src/pages/settings.py`

Light settings page. Mostly informational + a couple of preferences stored in `st.session_state`.

**Files:**
- Create: `src/pages/settings.py`

- [ ] **Step 1: Implement the page**

```python
"""Page: Einstellungen.

Session-scoped preferences and a small system info block.  No
persistent storage in this phase — Streamlit's session_state holds
whatever the user changes for the duration of the session.
"""
from __future__ import annotations

import streamlit as st


def render(filters: dict) -> None:
    st.title("Einstellungen")
    st.caption(
        "Session-basierte Präferenzen. Werte bleiben nur für die aktuelle "
        "Browser-Sitzung erhalten — kein persistentes User-Profil in dieser Phase."
    )

    st.subheader("Agent", anchor=False)
    current_model = st.session_state.get("chat_model_name", "llama3.2")
    new_model = st.text_input(
        "Ollama-Standardmodell",
        value=current_model,
        help="Wird vom Chat-Agent als Default verwendet. "
             "Auf der Chat-Seite überschreibbar.",
        key="settings_chat_model",
    )
    if new_model != current_model:
        st.session_state["chat_model_name"] = new_model
        st.toast("Modell aktualisiert.")

    st.subheader("Anzeige", anchor=False)
    st.markdown(
        "**Theme:** hell (Light Mode). "
        "Dark Mode ist als zukünftige Erweiterung vorgesehen — Tokens "
        "in `src/ui/theme.py` sind bereits dafür reserviert."
    )

    st.subheader("System", anchor=False)
    st.markdown(
        "- **Build:** Phases 1–7 (Dashboard Redesign)\n"
        "- **Tech-Stack:** Streamlit + Plotly + streamlit-antd-components\n"
        "- **Daten:** lokales SQLite, statischer Snapshot 2009–2011\n"
        "- **Decision-Log:** `data/logs/` (Akzept/Verwerf + 👍/👎)"
    )

    with st.expander("Session-State (Debug)", expanded=False):
        debug_keys = {
            k: v for k, v in st.session_state.items()
            if not k.startswith("FormSubmitter") and not k.startswith("sidebar_nav")
        }
        st.json(debug_keys, expanded=False)
```

- [ ] **Step 2: Smoke**

```bash
python -c "from src.pages import settings; print(callable(settings.render))"
```

- [ ] **Step 3: Commit**

```bash
git add src/pages/settings.py
git commit -m "feat(pages): Einstellungen — Ollama default, theme info, session debug"
```

---

## Task 4: Split — create `src/pages/agent_history.py` + trim `agent_recommendations.py`

Move the history-related sections out of `agent_recommendations.py`. The split point: everything from `st.subheader("Entscheidungslog / Memory", ...)` (around line 264) to the end of the page (including the Critic section) goes to the new file.

**Files:**
- Create: `src/pages/agent_history.py`
- Modify: `src/pages/agent_recommendations.py`

- [ ] **Step 1: Audit the source**

```bash
grep -n "st.subheader\|st.divider\|list_agent_runs\|analyze_decision_history\|Entscheidungslog\|Lern-Loop" src/pages/agent_recommendations.py
```

Confirm the rough section structure. The split point is the start of the "Entscheidungslog / Memory" section (`st.subheader("Entscheidungslog / Memory", anchor=False)`). Read the lines from there to end-of-file — that's what gets moved.

- [ ] **Step 2: Create `src/pages/agent_history.py`**

Skeleton:

```python
"""Page: Agent — Verlauf.

Persisted agent runs, recorded decision outcomes, and the Critic
(Lern-Loop) analysis.  Split out of agent_recommendations.py during
Phase 7.

Filters consumed:
    rfm, declining, forecast, actuals — passed to analyze_decision_history
    via its existing call site (no logic change).
"""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from src.critic import analyze_decision_history
from src.decision_log import list_agent_runs
from src.ui.cards import kpi_card
from src.ui.page_loader import _json_default


def render(filters: dict) -> None:
    st.title("Agent — Verlauf")
    st.caption(
        "Persistierte Agent-Läufe, geloggte Entscheidungen (Akzeptiert / "
        "Verworfen / 👍 / 👎) und die Critic-Analyse über die Historie."
    )

    # ── [the lifted body goes here] ────────────────────────────────────
    # 1. Entscheidungslog / Memory section (the table of session outcomes)
    # 2. Persisted Agent-Runs expander (list_agent_runs)
    # 3. Lern-Loop · Kritik-Komponente section (analyze_decision_history)
    #
    # Read the existing implementation in agent_recommendations.py from
    # `st.subheader("Entscheidungslog / Memory", ...)` to end-of-file and
    # paste verbatim, replacing `st.metric` with `kpi_card` (which was
    # already done in Phase 5 Task 4 for the Critic section).
```

When you transplant the body:
- Preserve every existing call (`list_agent_runs`, `analyze_decision_history`, `log_decision_outcome` if referenced).
- Preserve the existing `kpi_card` calls in the Critic section (Phase 5 already migrated them from `st.metric`).
- Read the existing file with the Read tool first to capture the exact code, then transplant.

Imports needed will include some that were in `agent_recommendations.py`'s import block — only re-import what the lifted code actually uses.

- [ ] **Step 3: Trim `src/pages/agent_recommendations.py`**

Open `src/pages/agent_recommendations.py`. Delete everything from the line `st.subheader("Entscheidungslog / Memory", anchor=False)` (around line 264) to the end of the `render(filters)` function.

Inside the import block, remove imports that are now ONLY used by the moved code:
- `list_agent_runs` (only used by the Entscheidungslog section we're removing)
- `analyze_decision_history` (only Critic section)
- `_json_default` (used by JSON export inside the Entscheidungslog section)
- `kpi_card` if it's no longer used on this page — but the page should keep using kpi_card if any KPIs remain. Check first.

Keep these imports because they're still used in the trimmed page:
- `generate_agent_run`, `generate_recommendations` from `src.decision_agent`
- `log_agent_run`, `log_decision_outcome` from `src.decision_log`
- `render_decision_panel`, `render_evidence_strip` — removed in Phase 5; verify they're not back
- `render_agent_trace`, `render_guardrails` from `src.ui.legacy_renderers`
- `agent_recommendation_card` from `src.ui.agent_panel`

Run a grep AFTER the trim to confirm no dead imports:

```bash
grep -n "^from\|^import" src/pages/agent_recommendations.py
```

For each imported symbol, verify it's still referenced somewhere in the file. Remove any that aren't.

- [ ] **Step 4: Smoke for both files**

```bash
python -c "from src.pages import agent_history, agent_recommendations; \
  print(callable(agent_history.render), callable(agent_recommendations.render))"
```
Expected: `True True`.

```bash
python -c "import app" 2>&1 | head -5
pytest tests/ -q | tail -3
```

- [ ] **Step 5: Commit**

```bash
git add src/pages/agent_history.py src/pages/agent_recommendations.py
git commit -m "feat(pages): split agent recommendations from history"
```

---

## Task 5: Update `app.py` dispatch

Three new entries in the `PAGES` dict.

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Update imports**

Find the page imports line in `app.py`:

```python
from src.pages import (
    overview, forecast as forecast_page, customers, products,
    agent_recommendations, chat,
)
```

Extend it to:

```python
from src.pages import (
    overview, forecast as forecast_page, customers, products,
    agent_recommendations, agent_history, chat,
    data_source, settings,
)
```

- [ ] **Step 2: Extend the PAGES dict**

Find the `PAGES = {...}` dict. Add three entries so it reads:

```python
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
```

- [ ] **Step 3: Smoke**

```bash
python -c "import app" 2>&1 | head -5
pytest tests/ -q | tail -3
```

- [ ] **Step 4: Verify the smoke test list**

Open `tests/test_pages_smoke.py`. Add the three new module names to `PAGE_MODULES`:

```python
PAGE_MODULES = [
    "src.pages.overview",
    "src.pages.forecast",
    "src.pages.customers",
    "src.pages.products",
    "src.pages.agent_recommendations",
    "src.pages.agent_history",
    "src.pages.chat",
    "src.pages.data_source",
    "src.pages.settings",
]
```

Run:

```bash
pytest tests/test_pages_smoke.py -v
```
Expected: 9/9 PASS.

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_pages_smoke.py
git commit -m "feat(app): dispatch data_source, settings, agent_history pages"
```

---

## Task 6: Final smoke + handoff

- [ ] **Step 1: Full test sweep**

```bash
pytest tests/ -q | tail -5
```

- [ ] **Step 2: Audit**

```bash
grep -rn "Entscheidungslog / Memory\|list_agent_runs\|analyze_decision_history" src/pages/
```
Expected: matches only in `src/pages/agent_history.py` (not in `agent_recommendations.py`).

```bash
grep -c "render" src/pages/data_source.py src/pages/settings.py src/pages/agent_history.py
```
Expected: each ≥ 1 (each page has a `render` function).

- [ ] **Step 3: Headless smoke**

```bash
streamlit run app.py --server.headless true --server.port 8598 > /tmp/p7smoke.log 2>&1 &
PID=$!
sleep 5
curl -s -o /dev/null -w "HTTP %{http_code}\n" "http://localhost:8598"
curl -s "http://localhost:8598/_stcore/health"
kill $PID 2>/dev/null
wait $PID 2>/dev/null
```
Expected: HTTP 200 + `ok`.

- [ ] **Step 4: User handoff**

Click through:
- **Sidebar** → three new items visible: Verlauf, Datenquelle, Einstellungen
- **Empfehlungen** → focused on the CURRENT agent run; no longer shows persisted runs or Critic section
- **Verlauf** → shows persisted runs, decision outcomes, Critic-Metriken
- **Datenquelle** → 4 KPI cards (Status, Transaktionen, Distinct Kunden, Dateigrösse) + date range + rebuild button
- **Einstellungen** → Ollama-Modell input + theme/system info + session-state debug expander

---

## Definition of Done — Phase 7

- [ ] `pytest tests/` is green
- [ ] `streamlit run app.py` runs all 9 pages without exceptions
- [ ] Sidebar shows three groups: ANALYTICS (4), AGENT (3), SYSTEM (2)
- [ ] `src/pages/agent_recommendations.py` no longer contains "Entscheidungslog / Memory", "Persistierte Agent-Runs", or "Lern-Loop · Kritik" — those live in `src/pages/agent_history.py`
- [ ] `tests/test_pages_smoke.py` parametrizes over 9 page modules

## What's Next

Phase 7 is the last full phase in the spec. After this, the dashboard ships. Possible polish later (no full phase needed):
- Top-bar with shadcn `date_range_picker` (Phase 4 deferral)
- Dark mode rollout (tokens reserved, `polish_dark` exists)
- streamlit-aggrid for the Verlauf table (filterable, sortable)
- Per-user persistence of Einstellungen (e.g. into a JSON file or browser-side storage)
- Onboarding-style empty state on first visit (Stripe-pattern from spec §6.3)
