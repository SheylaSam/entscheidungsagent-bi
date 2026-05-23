"""Legacy renderers — kept until Phase 5 replaces them with the new AI panel.

These were originally inline in app.py.  Moving them here so pages can
import without circular dependencies.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd


_LEGACY_CSS = """<style>
    .decision-panel {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-left: 5px solid var(--accent);
        border-radius: 8px;
        padding: 20px 22px;
        margin: 8px 0 18px;
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
        gap: 10px;
        margin: 0 0 20px;
    }
    .action-item {
        background: #111827;
        border: 1px solid #1f2937;
        border-left: 4px solid var(--accent);
        border-radius: 8px;
        padding: 12px 14px;
        color: #e5e7eb;
        font-size: 14px;
        line-height: 1.35;
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
</style>"""


def inject_legacy_css() -> None:
    """Inject the legacy <style> block.

    Call once near the top of app.py, after `theme.inject_global_css()`.
    """
    st.markdown(_LEGACY_CSS, unsafe_allow_html=True)


# ── then the 7 functions, copied verbatim from app.py ─────────────────────

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
