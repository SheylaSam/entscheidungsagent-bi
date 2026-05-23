# Dashboard Redesign — Phase 6: Chat Polish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the Chat-Agent page from single-shot form input to a proper persistent chat conversation. AI bubbles get the violet AI-surface styling (matching the agent recommendation card); user bubbles stay neutral. Add a suggestion-chip row above the input that helps first-time users get started.

**Architecture:** The page becomes history-driven via `st.session_state["chat_history"]` — a list of `{role, content, trace?}` dicts. `st.chat_input` and `st.chat_message("user"|"assistant")` replace the current `st.text_area` + button pattern. A new `src/ui/chat_widgets.py` module hosts the suggestion-chip rendering and the default chip list. CSS rules targeting `[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"])` paint the assistant bubble with `ai-bg-tint` + violet 3px left border. The Ollama model selector and setup hints move into a collapsed expander above the chat so they don't dominate the page.

**Tech Stack:** Phases 1–5 stack. No new dependencies. Uses Streamlit's native chat API (`st.chat_input`, `st.chat_message`).

**Reference:** [`docs/superpowers/specs/2026-05-17-dashboard-redesign-design.md`](../specs/2026-05-17-dashboard-redesign-design.md) §6.5 (Chat page).

**Depends on:** Phases 1–5 merged.

**Out of scope:**
- Dynamic context-aware chips (the spec mentioned generating chips based on the user's previous page — defer; static curated chips cover the use case)
- Inline KPI/row-count pills inside AI responses (requires parsing the LLM output for citations — deferrable; could be added later)
- shadcn `date_range_picker` swap (still deferred to Phase 7 if at all)
- Persisting chat history across page reloads (currently session-scoped; persistence is a future Phase 7 concern)

---

## File Plan

**Create:**
- `src/ui/chat_widgets.py` — `SUGGESTION_CHIPS` constant + `render_suggestion_chips()` function
- `tests/test_ui_chat_widgets.py` — unit tests for the chip module

**Modify:**
- `src/ui/theme.py` — extend `global_css()` with chat-bubble CSS (`.chat-suggestion-chip` button styling + assistant-bubble targeting)
- `tests/test_ui_theme.py` — assert the new CSS rules exist
- `src/pages/chat.py` — rebuild around `st.chat_input` + `st.chat_message` + history-in-session-state + suggestion chips

---

## Task 1: Chat CSS in `theme.global_css()`

Extend the global CSS with two blocks: AI-assistant bubble styling (matching the agent card's violet accent) and the suggestion-chip button polish.

**Files:**
- Modify: `src/ui/theme.py`
- Modify: `tests/test_ui_theme.py`

- [ ] **Step 1: Append failing tests**

```python
def test_global_css_styles_chat_assistant_bubble():
    css = theme.global_css()
    # The assistant chat-message bubble is tinted with the AI background
    assert "chatAvatarIcon-assistant" in css
    assert theme.AI_BG_TINT in css


def test_global_css_defines_suggestion_chip_class():
    css = theme.global_css()
    assert ".chat-suggestion-chip" in css
```

- [ ] **Step 2: Run, verify fail**

`pytest tests/test_ui_theme.py -v` → 2 new tests FAIL.

- [ ] **Step 3: Extend `global_css()`**

Locate the closing `</style>` tag inside `global_css()` (after the `.agent-*` rules added in Phase 5). Just before that closing tag, insert:

```css
/* ── Chat bubbles ─────────────────────────────────────────────── */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {{
    background: {AI_BG_TINT};
    border-left: 3px solid {AI_ACCENT};
    border-radius: {CARD_RADIUS_REM};
    padding: 12px 16px;
    margin-bottom: 8px;
}}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {{
    background: {BG_CARD};
    border-radius: {CARD_RADIUS_REM};
    padding: 12px 16px;
    margin-bottom: 8px;
}}

/* ── Suggestion-chip buttons above the chat input ─────────────── */
.chat-suggestion-chip > button {{
    background: {BG_PAGE} !important;
    border: 1px solid {BORDER} !important;
    color: {BODY} !important;
    font-family: {FONT_FAMILY} !important;
    font-size: 13px !important;
    padding: 6px 14px !important;
    border-radius: 999px !important;
    transition: background 0.15s ease, border-color 0.15s ease;
}}
.chat-suggestion-chip > button:hover {{
    background: {AI_BG_TINT} !important;
    border-color: {AI_ACCENT} !important;
    color: {AI_ACCENT} !important;
}}
```

Same brace-doubling rules as Phase 5 (CSS rule delimiters `{{` `}}`, token references single-braced).

- [ ] **Step 4: Run, verify pass**

```bash
pytest tests/test_ui_theme.py -v
pytest tests/ -q | tail -3
```

- [ ] **Step 5: Commit**

```bash
git add src/ui/theme.py tests/test_ui_theme.py
git commit -m "feat(ui): chat-bubble + suggestion-chip CSS in global_css()"
```

---

## Task 2: `src/ui/chat_widgets.py` — suggestion chips

A small module with one default chip list + a render helper. The helper takes a list of chip strings and a Streamlit key prefix; on click, it sets `st.session_state["chat_pending_prompt"]` (a sentinel the chat page reads and submits on the next rerun).

**Files:**
- Create: `src/ui/chat_widgets.py`
- Create: `tests/test_ui_chat_widgets.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for src/ui/chat_widgets.py."""
from src.ui import chat_widgets


def test_default_suggestion_chips_exists():
    chips = chat_widgets.SUGGESTION_CHIPS
    assert isinstance(chips, tuple)
    assert len(chips) >= 3
    assert all(isinstance(c, str) and len(c) > 0 for c in chips)


def test_chips_are_unique():
    assert len(set(chat_widgets.SUGGESTION_CHIPS)) == len(chat_widgets.SUGGESTION_CHIPS)


def test_render_suggestion_chips_is_callable():
    assert callable(chat_widgets.render_suggestion_chips)
```

- [ ] **Step 2: Run, verify fail**

`pytest tests/test_ui_chat_widgets.py -v` → ModuleNotFoundError.

- [ ] **Step 3: Create `src/ui/chat_widgets.py`**

```python
"""Reusable widgets for the Chat-Agent page.

Currently exposes the default suggestion-chip set and a render helper
that emits them as a row of pill-styled buttons above the chat input.
"""
from __future__ import annotations

from typing import Iterable


SUGGESTION_CHIPS: tuple[str, ...] = (
    "Was sollten wir diesen Monat tun?",
    "Welche Produkte zeigen Rückgang?",
    "Wie sehen die At-Risk-Kunden aus?",
    "Wie zuverlässig ist der Forecast?",
)


_PENDING_KEY = "chat_pending_prompt"


def render_suggestion_chips(
    chips: Iterable[str] | None = None,
    *,
    key_prefix: str = "chip",
) -> None:
    """Render a row of clickable suggestion chips.

    Each chip is a Streamlit button wrapped in a div with class
    ``chat-suggestion-chip`` so the global CSS can re-style it as a
    pill.  Clicking a chip writes the chip text into
    ``st.session_state[_PENDING_KEY]``, which the chat page then reads
    and submits as if the user had typed it.
    """
    import streamlit as st

    chip_list = list(chips) if chips is not None else list(SUGGESTION_CHIPS)
    if not chip_list:
        return

    cols = st.columns(len(chip_list))
    for i, (col, chip) in enumerate(zip(cols, chip_list)):
        with col:
            st.markdown('<div class="chat-suggestion-chip">',
                        unsafe_allow_html=True)
            if st.button(chip, key=f"{key_prefix}_{i}", use_container_width=True):
                st.session_state[_PENDING_KEY] = chip
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


def pop_pending_prompt() -> str | None:
    """Return and clear any pending prompt set by chip click."""
    import streamlit as st
    return st.session_state.pop(_PENDING_KEY, None)
```

- [ ] **Step 4: Run, verify pass**

```bash
pytest tests/test_ui_chat_widgets.py -v
pytest tests/ -q | tail -3
```

- [ ] **Step 5: Commit**

```bash
git add src/ui/chat_widgets.py tests/test_ui_chat_widgets.py
git commit -m "feat(ui): chat suggestion-chip widget + default chip set"
```

---

## Task 3: Rebuild `src/pages/chat.py` around `st.chat_*` API

The page transforms from single-shot form into a persistent conversation. State lives in `st.session_state["chat_history"]` (list of message dicts). Suggestion chips show when history is empty.

**Files:**
- Modify: `src/pages/chat.py`

- [ ] **Step 1: Read the current page**

Familiarize yourself with the imports, the `AgentContext` and `AAIAgent` interface in `src/agent_chat.py`, and which keys the page reads from `filters`.

```bash
grep -n "AgentContext\|AAIAgent" src/agent_chat.py | head -10
```

The current chat dispatches one question via `agent.chat(user_question)` which returns an object with `.answer` and `.trace`. That signature stays — we're just wrapping it in a multi-turn UI.

- [ ] **Step 2: Replace the page body**

Replace the entire `def render(filters):` body with:

```python
def render(filters: dict) -> None:
    """Render the Chat-Agent page (multi-turn conversation)."""
    actuals             = filters["actuals"]
    forecast            = filters["forecast"]
    rfm                 = filters["rfm"]
    declining           = filters["declining"]
    agent_forecast_base = filters["agent_forecast_base"]

    st.title("Chat-Agent")
    st.caption(
        "Natürlichsprachlicher Layer mit Tool-Calling (Ollama lokal). "
        "Der LLM wählt ein Tool, ruft die deterministische BI-Logik auf und "
        "antwortet auf Deutsch."
    )

    with st.expander("Setup & Modell", expanded=False):
        st.markdown(
            "1. Ollama installieren: <https://ollama.com>\n"
            "2. Modell laden: `ollama pull llama3.2`\n"
            "3. Python-Paket: `pip install ollama`\n"
            "4. Ollama läuft als Hintergrunddienst — keine API-Keys nötig."
        )
        model_name = st.text_input("Ollama-Modell", value="llama3.2",
                                   key="chat_model_name")

    # ── History in session state ─────────────────────────────────────────
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # Render the history (each item is {role, content, trace?})
    for i, msg in enumerate(st.session_state["chat_history"]):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("trace"):
                with st.expander("Agent-Trace (Think → Act → Observe → Answer)",
                                 expanded=False):
                    for step in msg["trace"]:
                        st.markdown(f"**{step.get('step', '').upper()}**")
                        st.json({k: v for k, v in step.items() if k != "step"})

    # ── Suggestion chips when history is empty ────────────────────────────
    if not st.session_state["chat_history"]:
        st.markdown("**Wo möchtest du starten?**")
        render_suggestion_chips()

    # ── Input + dispatch ─────────────────────────────────────────────────
    pending = pop_pending_prompt()
    user_input = st.chat_input("Frage an den Agent…") or pending

    if user_input:
        # Echo user message + persist
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state["chat_history"].append(
            {"role": "user", "content": user_input}
        )

        # Build context + run agent
        ctx = AgentContext(
            forecast_df=forecast,
            rfm_df=rfm,
            declining_df=declining,
            actuals_df=actuals,
            comparison_value=agent_forecast_base,
        )
        agent = AAIAgent(ctx, model=st.session_state.get("chat_model_name",
                                                        "llama3.2"))

        with st.chat_message("assistant"):
            with st.spinner("Agent denkt nach…"):
                try:
                    result = agent.chat(user_input)
                except OllamaNotAvailable as exc:
                    err = str(exc)
                    st.error(err)
                    st.session_state["chat_history"].append(
                        {"role": "assistant", "content": f"⚠️ {err}"}
                    )
                    return
                except Exception as exc:                     # noqa: BLE001
                    err = f"Ollama-Fehler: {exc}"
                    st.error(err)
                    st.session_state["chat_history"].append(
                        {"role": "assistant", "content": f"⚠️ {err}"}
                    )
                    return

            st.markdown(result.answer)
            with st.expander("Agent-Trace (Think → Act → Observe → Answer)",
                             expanded=False):
                for step in result.trace:
                    st.markdown(f"**{step.get('step', '').upper()}**")
                    st.json({k: v for k, v in step.items() if k != "step"})

        st.session_state["chat_history"].append(
            {"role": "assistant",
             "content": result.answer,
             "trace": result.trace}
        )
```

Imports at the top of `src/pages/chat.py`:

```python
"""Page: Chat-Agent."""
from __future__ import annotations

import streamlit as st

from src.agent_chat import AAIAgent, AgentContext, OllamaNotAvailable
from src.ui.chat_widgets import render_suggestion_chips, pop_pending_prompt
```

- [ ] **Step 3: Optional polish — clear-history button**

Above the suggestion chips (inside the `if not history:` block), or in the expander, add a tiny "Verlauf löschen" button when history exists:

```python
if st.session_state["chat_history"]:
    if st.button("Verlauf löschen", key="chat_clear"):
        st.session_state["chat_history"] = []
        st.rerun()
```

Place this somewhere reasonable — e.g. just above the chat_input.

- [ ] **Step 4: Smoke**

```bash
python -c "from src.pages import chat" 2>&1 | head -5
python -c "import app" 2>&1 | head -5
pytest tests/ -q | tail -3
```

Expected: clean import, all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/pages/chat.py
git commit -m "feat(chat): persistent multi-turn chat with bubbles + suggestion chips"
```

---

## Task 4: Final smoke + handoff

- [ ] **Step 1: Full test sweep**

```bash
pytest tests/ -q | tail -5
```

- [ ] **Step 2: Audit**

```bash
grep -c "st.text_area\|st.button.*Frage absenden" src/pages/chat.py
```
Expected: 0 (old single-shot form is gone).

```bash
grep -c "st.chat_input\|st.chat_message" src/pages/chat.py
```
Expected: ≥ 2 (we use both).

- [ ] **Step 3: Headless smoke**

```bash
streamlit run app.py --server.headless true --server.port 8595 > /tmp/p6smoke.log 2>&1 &
PID=$!
sleep 4
curl -s -o /dev/null -w "HTTP %{http_code}\n" "http://localhost:8595"
curl -s "http://localhost:8595/_stcore/health"
kill $PID 2>/dev/null
wait $PID 2>/dev/null
```

Expected: HTTP 200 + `ok`.

- [ ] **Step 4: User handoff**

Walk the user through:
- **Chat-Agent page on first visit**: 4 suggestion-chip pills appear above the chat input. Clicking a chip submits the question immediately.
- **After the first exchange**: chips disappear; the conversation is visible as alternating bubbles. Assistant bubbles have violet left border + `ai-bg-tint` background; user bubbles are neutral.
- **Each assistant message** has a collapsible "Agent-Trace" expander.
- **Verlauf löschen button** resets the conversation.
- **Setup & Modell expander** is collapsed by default — the page no longer feels like a form.

---

## Definition of Done — Phase 6

- [ ] `pytest tests/` is green
- [ ] `streamlit run app.py` runs without exceptions; Chat-Agent page renders the new multi-turn UI
- [ ] `src/pages/chat.py` uses `st.chat_input` and `st.chat_message`
- [ ] No `st.text_area` for user prompt remains on the chat page
- [ ] Suggestion chips appear when history is empty; disappear after first exchange
- [ ] Assistant bubbles have the violet accent styling (visible against the user bubbles)
- [ ] `chat_widgets.SUGGESTION_CHIPS` is the single source of truth for the default chip set

## What's Next (Phase 7 preview)

Phase 7 is the last full phase: split `agent_recommendations.py` into `agent_history.py` (a dedicated AgGrid-backed history table) and a slimmed-down recommendations page. Add the two new pages from the spec (Datenquelle, Einstellungen) so the sidebar gets its bottom-half items. Optionally retire the legacy `render_evidence_strip` calls if a cleaner replacement makes sense.
