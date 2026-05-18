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
