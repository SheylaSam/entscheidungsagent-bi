"""Page: Chat-Agent.

Lifted from Tab 6 of app.py during Phase 3.  No logic changes.
"""
from __future__ import annotations

import streamlit as st

from src.agent_chat import AAIAgent, AgentContext, OllamaNotAvailable


def render(filters: dict) -> None:
    """Render the Chat-Agent page.

    Expects in ``filters``:
        actuals, forecast, rfm, declining, recs, agent_forecast_base
    """
    actuals            = filters["actuals"]
    forecast           = filters["forecast"]
    rfm                = filters["rfm"]
    declining          = filters["declining"]
    agent_forecast_base = filters["agent_forecast_base"]

    # ── lifted body ──────────────────────────────────────────────────────
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
