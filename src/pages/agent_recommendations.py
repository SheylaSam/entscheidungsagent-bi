"""Page: Agent — Empfehlungen, Verlauf, Critic.

Lifted from Tab 5 of app.py during Phase 3.  No logic changes.

Per spec §3, a later phase splits this into separate
``agent_history.py`` and an enhanced recommendations page.
"""
from __future__ import annotations

import json
import pandas as pd
import streamlit as st

from src.critic import analyze_decision_history
from src.decision_agent import generate_recommendations, generate_agent_run
from src.decision_log import list_agent_runs, log_agent_run, log_decision_outcome
from src.ui.legacy_renderers import (
    render_decision_panel,
    render_evidence_strip,
    render_agent_trace,
    render_guardrails,
)
from src.ui.page_loader import forecast_baseline, short_baseline_label, _json_default


def render(filters: dict) -> None:
    """Render the Empfehlungen page (agent run + trace + log + critic).

    Expects in ``filters``: actuals, forecast, rfm, declining, recs,
    forecast_baseline_mode.
    """
    actuals               = filters["actuals"]
    forecast              = filters["forecast"]
    rfm                   = filters["rfm"]
    declining             = filters["declining"]
    forecast_baseline_mode = filters["forecast_baseline_mode"]

    # ── lifted body ──────────────────────────────────────────────────────
    st.title("KI-Entscheidungsagent")
    st.caption("Priorisierte Managemententscheidung mit nachvollziehbarer Regelbasis")

    # ── Sliders ──────────────────────────────────────────────────────────────
    with st.expander("Regelparameter", expanded=False):
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            _ft_pct = st.slider(
                "Forecast-Rückgang (Regel 1)",
                min_value=-30, max_value=-1, value=-5, step=1,
                format="%d%%",
                help="Wie stark muss der Forecast fallen, damit Regel 1 anschlägt?",
            )
            forecast_threshold = _ft_pct / 100
        with col_s2:
            _ar_pct = st.slider(
                "At-Risk-Anteil (Regel 1)",
                min_value=5, max_value=50, value=20, step=1,
                format="%d%%",
                help="Wie hoch muss der At-Risk-Anteil sein, damit Regel 1 anschlägt?",
            )
            at_risk_threshold = _ar_pct / 100

    # ── Schwellwert-Kontext ───────────────────────────────────────────────────
        hist_changes = actuals['y'].pct_change().dropna()
        if len(hist_changes) > 0:
            hc1, hc2, hc3, hc4 = st.columns(4)
            hc1.metric("Ø monatliche Änderung", f"{hist_changes.mean():+.1%}")
            hc2.metric("Schlechtester Monat", f"{hist_changes.min():+.1%}")
            hc3.metric("Bester Monat", f"{hist_changes.max():+.1%}")
            hc4.metric("Aktueller At-Risk-Anteil", f"{(rfm['segment']=='At Risk').sum()/len(rfm):.1%}")

    # ── Live-Werte berechnen ──────────────────────────────────────────────────
    _future = forecast[forecast['ds'] > actuals['ds'].max()]
    _last, _last_label = forecast_baseline(actuals, forecast_baseline_mode)
    _last_short = short_baseline_label(_last_label)
    _next = _future['yhat'].iloc[0] if not _future.empty else 0
    _pct  = (_next - _last) / _last if _last > 0 else 0
    _ar_share = (rfm['segment'] == 'At Risk').sum() / len(rfm) if len(rfm) > 0 else 0
    _ar_count = (rfm['segment'] == 'At Risk').sum()
    _data_ok  = len(rfm) >= 10 and _next >= 0

    _c1a = _data_ok and _pct < forecast_threshold
    _c1b = _data_ok and _ar_share > at_risk_threshold
    _r1  = _c1a and _c1b
    if 'revenue_avg' in declining.columns and len(declining) > 0:
        _significant_declining = declining[
            declining['revenue_last_month'] < declining['revenue_avg'] * 0.5
        ]
    else:
        _significant_declining = declining
    _r2  = _data_ok and len(_significant_declining) > 0

    _champion_share = (rfm['segment'] == 'Champions').sum() / len(rfm) if len(rfm) > 0 else 0
    _new_share      = (rfm['segment'] == 'New').sum() / len(rfm) if len(rfm) > 0 else 0
    _top_n          = max(1, int(len(rfm) * 0.2))
    _top20_share    = (rfm['monetary'].sort_values(ascending=False).head(_top_n).sum()
                       / rfm['monetary'].sum()) if len(rfm) >= 5 else 0
    _r4 = _data_ok and _champion_share < 0.10
    _r5 = _data_ok and _new_share < 0.05
    _r6 = _data_ok and _top20_share > 0.80

    live_recs = generate_recommendations(
        forecast,
        rfm,
        declining,
        forecast_threshold,
        at_risk_threshold,
        actuals_df=actuals,
        comparison_value=_last,
    )
    agent_run = generate_agent_run(
        forecast,
        rfm,
        declining,
        forecast_threshold,
        at_risk_threshold,
        actuals_df=actuals,
        comparison_value=_last,
    )
    try:
        log_agent_run(agent_run)
    except OSError:
        pass

    render_decision_panel(live_recs[0], "Agenten-Empfehlung")
    render_evidence_strip([
        ("Vergleichsumsatz", f"£{_last:,.0f}"),
        ("Prognose nächster Monat", f"£{_next:,.0f}"),
        ("Abweichung zur Vergleichsbasis", f"{_pct:+.1%}"),
        ("At-Risk Kunden", f"{_ar_count:,} · {_ar_share:.1%}"),
        ("Rückläufige Produkte", f"{len(_significant_declining):,}"),
        ("Top-20 Umsatzanteil", f"{_top20_share:.0%}"),
    ])

    def _rule_box(title, priority_label, priority_color, conditions_html, fired: bool) -> str:
        border = priority_color if fired else '#334155'
        status_color = priority_color if fired else '#64748b'
        status_text = '● Ausgelöst' if fired else '○ Nicht ausgelöst'
        return f"""
        <div style="background:#1e293b;border:2px solid {border};padding:18px;border-radius:10px;height:100%;">
            <div style="font-size:13px;color:#94a3b8;margin-bottom:2px;">Priorität bei Auslösung</div>
            <div style="font-size:17px;font-weight:700;color:{priority_color};margin-bottom:12px;">{priority_label}</div>
            <div style="font-size:14px;color:#cbd5e1;margin-bottom:4px;font-weight:600">{title}</div>
            <hr style="border-color:#334155;margin:10px 0">
            {conditions_html}
            <hr style="border-color:#334155;margin:10px 0">
            <div style="font-size:13px;color:{status_color};font-weight:700">{status_text}</div>
        </div>"""

    def _cond_row(label: str, actual: str, threshold: str, met: bool) -> str:
        icon = '✓' if met else '×'
        return f'<div style="margin-bottom:6px;font-size:13px;color:#e2e8f0">{icon} {label}: <strong>{actual}</strong> <span style="color:#64748b">(Schwelle: {threshold})</span></div>'

    st.markdown('<div class="section-kicker">Regelbelege</div>', unsafe_allow_html=True)
    st.subheader("Regelstatus")

    col_r1, col_r2, col_r3 = st.columns(3)

    with col_r1:
        if not _data_ok:
            conds = _cond_row("Datenbasis", f"{len(rfm)} Kunden / Forecast {'negativ' if _next < 0 else 'ok'}", "≥10 Kunden, Forecast ≥0", False)
        else:
            conds = (
                _cond_row("Prognose nächster Monat", f"{_pct:+.1%}", f"< {forecast_threshold:.0%}", _c1a) +
                _cond_row("At-Risk-Anteil", f"{_ar_share:.1%} ({_ar_count} Kunden)", f"> {at_risk_threshold:.0%}", _c1b) +
                '<div style="font-size:12px;color:#64748b;margin-top:8px">Beide Bedingungen müssen erfüllt sein.</div>'
            )
        st.markdown(_rule_box("Reaktivierungskampagne", "HOCH", "#ef4444", conds, _r1), unsafe_allow_html=True)

    with col_r2:
        conds2 = _cond_row(
            "Signifikant rückläufige Produkte",
            str(len(_significant_declining)),
            "≥1",
            _r2,
        )
        if _r2:
            names = ', '.join(_significant_declining['description'].head(3).tolist())
            conds2 += f'<div style="font-size:12px;color:#94a3b8;margin-top:6px">{names}{"…" if len(_significant_declining) > 3 else ""}</div>'
        st.markdown(_rule_box("Sortiment bereinigen", "MITTEL", "#f59e0b", conds2, _r2), unsafe_allow_html=True)

    with col_r3:
        conds4 = _cond_row("Champion-Anteil", f"{_champion_share:.1%}", "≥ 10%", not _r4)
        st.markdown(_rule_box("Kundenbindung stärken", "MITTEL", "#f59e0b", conds4, _r4), unsafe_allow_html=True)

    col_r4, col_r5, col_r6 = st.columns(3)

    with col_r4:
        conds5 = _cond_row("Neukunden-Anteil", f"{_new_share:.1%}", "≥ 5%", not _r5)
        st.markdown(_rule_box("Neukundenakquisition prüfen", "MITTEL", "#f59e0b", conds5, _r5), unsafe_allow_html=True)

    with col_r5:
        conds6 = _cond_row("Top 20% Kunden, Umsatzanteil", f"{_top20_share:.0%}", "≤ 80%", not _r6)
        st.markdown(_rule_box("Klumpenrisiko", "MITTEL", "#f59e0b", conds6, _r6), unsafe_allow_html=True)

    with col_r6:
        _r3 = not any([_r1, _r2, _r4, _r5, _r6])
        _mittel_fired = [r for r in [_r2, _r4, _r5, _r6] if r]
        conds3 = (
            _cond_row("Keine HOCH-Regel ausgelöst", "ausgelöst" if _r1 else "—", "nicht ausgelöst", not _r1) +
            _cond_row("Keine MITTEL-Regel ausgelöst", f"{len(_mittel_fired)} ausgelöst" if _mittel_fired else "—", "nicht ausgelöst", not any(_mittel_fired)) +
            f'<div style="font-size:12px;color:#64748b;margin-top:8px">Champion-Anteil: {_champion_share:.1%}</div>'
        )
        st.markdown(_rule_box("Kein Handlungsbedarf", "TIEF", "#4ade80", conds3, _r3), unsafe_allow_html=True)

    if len(live_recs) > 1:
        with st.expander("Weitere Empfehlungen", expanded=False):
            for rec in live_recs[1:]:
                render_decision_panel(rec, "Weitere Empfehlung")

    st.divider()
    st.subheader("Agentic Trace")
    st.caption("Planung, Tool-Nutzung und Synthese der aktuellen Empfehlung.")
    render_agent_trace(agent_run['trace'])

    col_guard, col_approval = st.columns([1.2, 1])
    with col_guard:
        st.subheader("Guardrails")
        render_guardrails(agent_run['guardrails'])

    with col_approval:
        st.subheader("Human-in-the-Loop")
        if agent_run['approval_required']:
            st.warning("Operative Umsetzung benötigt Management-Freigabe.")
        else:
            st.success("Keine zwingende Freigabe nötig.")

        log_key = "decision_agent_log"
        if log_key not in st.session_state:
            st.session_state[log_key] = []

        selected_status = st.radio(
            "Entscheidungsstatus",
            ["Offen", "Freigegeben", "Zurückgestellt", "Abgelehnt"],
            horizontal=True,
            key="approval_status",
        )
        note = st.text_area(
            "Management-Notiz",
            placeholder="Kurz begründen, warum die Empfehlung freigegeben, zurückgestellt oder abgelehnt wird.",
            key="approval_note",
        )
        if st.button("Entscheidung protokollieren", type="primary"):
            entry = {
                'run_id': agent_run['run_id'],
                'status': selected_status,
                'note': note,
                'decision': live_recs[0]['decision'],
                'priority': live_recs[0]['priority'],
                'evidence': agent_run['evidence'],
            }
            st.session_state[log_key].insert(0, entry)
            log_decision_outcome(agent_run['run_id'], selected_status, note)
            st.success("Entscheidung wurde im Session-Memory protokolliert und für den Lern-Loop gespeichert.")

        st.download_button(
            "Agent Run als JSON exportieren",
            data=json.dumps(agent_run, ensure_ascii=False, indent=2, default=_json_default),
            file_name=f"decision-agent-run-{agent_run['run_id']}.json",
            mime="application/json",
        )

    if st.session_state.get("decision_agent_log"):
        st.subheader("Entscheidungslog / Memory")
        log_df = pd.DataFrame(st.session_state["decision_agent_log"])
        st.dataframe(
            log_df[['run_id', 'status', 'priority', 'decision', 'note']],
            use_container_width=True,
            hide_index=True,
        )

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
    st.subheader("Lern-Loop · Kritik-Komponente")
    st.caption(
        "Liest persistierte Agent-Runs und Entscheidungs-Outcomes und schlägt "
        "Schwellwert-Anpassungen vor. Read-only — Übernahme bleibt manuell."
    )
    critique = analyze_decision_history()
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        st.metric("Agent-Läufe gesamt", critique['run_count'])
    with col_c2:
        st.metric("Mit Outcome", critique['outcome_count'])
    with col_c3:
        approval_rate = critique['approval_rate']
        st.metric(
            "Freigabe-Quote",
            f"{approval_rate:.0%}" if approval_rate is not None else "n/a",
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
