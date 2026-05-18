"""Page: Agent — Verlauf.

Persisted agent runs, recorded decision outcomes, and the Critic
(Lern-Loop) analysis.  Split out of agent_recommendations.py during
Phase 7.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.critic import analyze_decision_history
from src.decision_log import list_agent_runs
from src.ui.cards import kpi_card


def render(filters: dict) -> None:
    st.title("Agent — Verlauf")
    st.caption(
        "Persistierte Agent-Läufe, geloggte Entscheidungen (Akzeptiert / "
        "Verworfen / 👍 / 👎) und die Critic-Analyse über die Historie."
    )

    # ── Session-Memory Entscheidungslog ───────────────────────────────────────
    if st.session_state.get("decision_agent_log"):
        st.subheader("Entscheidungslog / Memory", anchor=False)
        log_df = pd.DataFrame(st.session_state["decision_agent_log"])
        st.dataframe(
            log_df[['run_id', 'status', 'priority', 'decision', 'note']],
            use_container_width=True,
            hide_index=True,
        )

    # ── Persistierte Agent-Runs ───────────────────────────────────────────────
    persisted_runs = list_agent_runs(limit=10)
    if persisted_runs:
        with st.expander(f"Persistierte Agent-Runs ({len(persisted_runs)})", expanded=False):
            st.caption(
                "Jeder Agent-Lauf wird unter `logs/agent_runs/<run_id>.json` archiviert — "
                "Empfehlung, Evidence, Trace und Guardrails bleiben so nachvollziehbar."
            )
            st.dataframe(
                pd.DataFrame([
                    {
                        'run_id': r['run_id'],
                        'priorität': r['top_priority'],
                        'empfehlungen': r['recommendation_count'],
                        'freigabe nötig': r['approval_required'],
                    }
                    for r in persisted_runs
                ]),
                use_container_width=True,
                hide_index=True,
            )

    # ── Lern-Loop / Kritik-Komponente (Russell & Norvig Fig. 2.15, Folie 18) ──
    st.divider()
    st.subheader("Lern-Loop · Kritik-Komponente", anchor=False)
    st.caption(
        "Liest persistierte Agent-Runs und Entscheidungs-Outcomes und schlägt "
        "Schwellwert-Anpassungen vor. Read-only — Übernahme bleibt manuell."
    )
    critique = analyze_decision_history()
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        kpi_card(
            label="Agent-Läufe gesamt",
            value=critique['run_count'],
            value_format="{:,.0f}",
            delta_pct=None,
            delta_period="",
            higher_is_better=True,
            sparkline=None,
        )
    with col_c2:
        kpi_card(
            label="Mit Outcome",
            value=critique['outcome_count'],
            value_format="{:,.0f}",
            delta_pct=None,
            delta_period="",
            higher_is_better=True,
            sparkline=None,
        )
    with col_c3:
        approval_rate = critique['approval_rate']
        kpi_card(
            label="Freigabe-Quote",
            value=approval_rate,
            value_format="{:.1%}",
            delta_pct=None,
            delta_period="",
            higher_is_better=True,
            sparkline=None,
        )

    if critique['priority_distribution']:
        st.write("**Verteilung der Top-Prioritäten:**")
        st.dataframe(
            pd.DataFrame(
                [{'Priorität': k, 'Anzahl': v} for k, v in critique['priority_distribution'].items()]
            ),
            use_container_width=True,
            hide_index=True,
        )

    if critique['suggestions']:
        st.write("**Vorschläge des Kritik-Agents:**")
        for s in critique['suggestions']:
            if s['threshold']:
                st.warning(
                    f"**{s['threshold']}**: aktuell `{s['current_default']}`, "
                    f"vorgeschlagen `{s['suggested']}`.  \n{s['reasoning']}"
                )
            else:
                st.info(s['reasoning'])
    elif critique['run_count'] >= 3:
        st.success("Keine Anpassungen nötig — Schwellwerte produzieren akzeptierte Empfehlungen.")
    else:
        st.info(
            f"Noch zu wenig Datenbasis für Vorschläge "
            f"(mindestens 3 Läufe + Outcomes nötig, aktuell {critique['run_count']} Läufe / "
            f"{critique['outcome_count']} Outcomes)."
        )
