"""Page: Chat-Agent.

Persistent multi-turn chat with Ollama tool-calling.  AI bubbles get
the violet AI-surface styling; user bubbles stay neutral.  Suggestion
chips show only when the history is empty (first-visit onboarding).
"""
from __future__ import annotations

import streamlit as st

from src.agent_chat import AAIAgent, AgentContext, OllamaNotAvailable
from src.ui.chat_widgets import pop_pending_prompt, render_suggestion_chips


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
        st.text_input("Ollama-Modell", value="llama3.2", key="chat_model_name")

    # ── History in session state ─────────────────────────────────────────
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    history = st.session_state["chat_history"]

    # Render history
    for msg in history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            trace = msg.get("trace")
            if trace:
                with st.expander(
                    "Agent-Trace (Think → Act → Observe → Answer)",
                    expanded=False,
                ):
                    for step in trace:
                        st.markdown(f"**{step.get('step', '').upper()}**")
                        st.json({k: v for k, v in step.items() if k != "step"})

    # Suggestion chips only on first visit
    if not history:
        st.markdown("**Wo möchtest du starten?**")
        render_suggestion_chips()
    else:
        # Clear-history convenience
        if st.button("Verlauf löschen", key="chat_clear"):
            st.session_state["chat_history"] = []
            st.rerun()

    # Input: native chat_input OR a chip-click pending prompt
    pending = pop_pending_prompt()
    user_input = st.chat_input("Frage an den Agent…") or pending

    if not user_input:
        return

    # Echo the user turn + persist
    with st.chat_message("user"):
        st.markdown(user_input)
    history.append({"role": "user", "content": user_input})

    # Run agent
    ctx = AgentContext(
        forecast_df=forecast,
        rfm_df=rfm,
        declining_df=declining,
        actuals_df=actuals,
        comparison_value=agent_forecast_base,
    )
    agent = AAIAgent(
        ctx,
        model=st.session_state.get("chat_model_name", "llama3.2"),
    )

    with st.chat_message("assistant"):
        with st.spinner("Agent denkt nach…"):
            try:
                result = agent.chat(user_input)
            except OllamaNotAvailable as exc:
                err = str(exc)
                st.error(err)
                history.append({"role": "assistant", "content": f"⚠️ {err}"})
                return
            except Exception as exc:                          # noqa: BLE001
                err = f"Ollama-Fehler: {exc}"
                st.error(err)
                history.append({"role": "assistant", "content": f"⚠️ {err}"})
                return

        st.markdown(result.answer)
        with st.expander(
            "Agent-Trace (Think → Act → Observe → Answer)",
            expanded=False,
        ):
            for step in result.trace:
                st.markdown(f"**{step.get('step', '').upper()}**")
                st.json({k: v for k, v in step.items() if k != "step"})

    history.append({
        "role": "assistant",
        "content": result.answer,
        "trace": result.trace,
    })
