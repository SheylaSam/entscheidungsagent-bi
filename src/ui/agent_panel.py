"""Agent recommendation card — the canonical AI-surface primitive.

Used everywhere the dashboard shows a generated recommendation.

See: docs/superpowers/specs/2026-05-17-dashboard-redesign-design.md §6
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Literal

from src.ui import theme

Variant = Literal["full", "compact"]


_PRIORITY_COLORS: dict[str, str] = {
    "KRITISCH": theme.NEGATIVE,
    "HOCH":     theme.NEGATIVE,
    "MITTEL":   theme.WARNING,
    "TIEF":     theme.POSITIVE,
}


def _priority_badge(priority: str) -> str:
    """HTML for a priority badge (uppercase pill with semantic dot)."""
    color = _PRIORITY_COLORS.get(priority.upper() if priority else "", theme.MUTED)
    return (
        f'<span class="agent-priority-badge" '
        f'style="background:{color}1A; color:{color};">'
        f'<span class="dot" style="background:{color}"></span>'
        f'PRIORITÄT {priority}'
        f'</span>'
    )


def _rec_id(rec: dict) -> str:
    """Existing rec_id or a stable 8-char fingerprint of decision+finding."""
    if rec.get("rec_id"):
        return str(rec["rec_id"])
    raw = f"{rec.get('decision', '')}|{rec.get('finding', '')}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]


def _freshness_line(rec: dict) -> str:
    """Short relative freshness label."""
    ts = rec.get("timestamp")
    if not ts:
        return "–"
    try:
        if isinstance(ts, str) and ts.endswith("Z"):
            ts_dt = datetime.fromisoformat(ts[:-1]).replace(tzinfo=timezone.utc)
        elif isinstance(ts, str):
            ts_dt = datetime.fromisoformat(ts)
        else:
            ts_dt = ts
    except ValueError:
        return str(ts)

    now = datetime.now(timezone.utc) if ts_dt.tzinfo else datetime.utcnow()
    delta = now - ts_dt
    seconds = delta.total_seconds()
    if seconds < 60:
        return "gerade eben"
    if seconds < 3600:
        return f"vor {int(seconds / 60)} Min"
    if seconds < 86400:
        return f"vor {int(seconds / 3600)} Std"
    days = int(seconds / 86400)
    if days < 30:
        return f"vor {days} Tag" + ("" if days == 1 else "en")
    return ts_dt.strftime("%Y-%m-%d")


def _marker_row_html(priority: str) -> str:
    badge = _priority_badge(priority)
    return (
        '<div class="agent-marker" style="display:flex;align-items:center;width:100%;">'
        '  <span class="agent-sparkle">✦</span>'
        '  <span>AGENT-EMPFEHLUNG</span>'
        f'  {badge}'
        '</div>'
    )


def _title_html(rec: dict) -> str:
    title = rec.get("decision") or "(unbenannte Empfehlung)"
    return f'<div class="agent-title">{title}</div>'


def _finding_html(rec: dict) -> str:
    parts: list[str] = []
    if rec.get("finding"):
        parts.append(rec["finding"])
    if rec.get("reasoning"):
        parts.append(rec["reasoning"])
    if not parts:
        return ""
    return f'<div class="agent-finding">{" ".join(parts)}</div>'


def _meta_html(rec: dict) -> str:
    rid = _rec_id(rec)
    freshness = _freshness_line(rec)
    source = rec.get("source_version", "rules v0.4")
    return (
        '<div class="agent-meta">'
        f'aktualisiert: {freshness} · Quelle: {source} · Trace #{rid}'
        '</div>'
    )


def agent_recommendation_card(
    rec: dict,
    *,
    variant: Variant = "full",
) -> None:
    """Render one recommendation card.

    Parameters
    ----------
    rec:
        Recommendation dict (see Phase-5 plan for expected keys).
    variant:
        ``"full"`` renders the complete card with evidence drilldown
        and action buttons.  ``"compact"`` renders a slim variant for
        stacked follow-up lists.
    """
    import streamlit as st

    rid = _rec_id(rec)
    css_class = "agent-card" + (" compact" if variant == "compact" else "")

    body_html = (
        f'<div class="{css_class}">'
        f'{_marker_row_html(rec.get("priority", "MITTEL"))}'
        f'{_title_html(rec)}'
        f'{_finding_html(rec)}'
        '</div>'
    )
    st.markdown(body_html, unsafe_allow_html=True)

    if variant == "compact":
        return

    with st.expander("Evidenz ansehen", expanded=False):
        rule = rec.get("rule", "–")
        st.markdown(f"**Regel:** `{rule}`")
        utility = rec.get("utility")
        if utility:
            comps = rec.get("utility_components", {}) or {}
            st.markdown(
                f"**Nutzen-Score:** £{utility:,.0f}  "
                f"_(Impact £{comps.get('expected_impact_gbp', 0):,.0f} · "
                f"Dringlichkeit {comps.get('urgency', 0):.2f} · "
                f"Konfidenz {comps.get('confidence', 0):.2f})_"
            )
        evidence_rows = rec.get("evidence_rows")
        if evidence_rows is not None:
            try:
                if hasattr(evidence_rows, "head"):
                    st.dataframe(evidence_rows.head(10),
                                 use_container_width=True, hide_index=True)
                elif len(evidence_rows) > 0:
                    st.dataframe(evidence_rows[:10],
                                 use_container_width=True, hide_index=True)
            except Exception:                                  # noqa: BLE001
                pass

    col_accept, col_reject, col_thumbs_up, col_thumbs_down, _ = st.columns(
        [1.2, 1.2, 0.4, 0.4, 4]
    )
    with col_accept:
        if st.button("Akzeptieren", key=f"accept_{rid}", type="primary"):
            from src.decision_log import log_decision_outcome
            try:
                log_decision_outcome(rid, "accepted")
                st.toast("Empfehlung akzeptiert.")
            except Exception as e:                             # noqa: BLE001
                st.warning(f"Konnte Outcome nicht loggen: {e}")
    with col_reject:
        if st.button("Verwerfen", key=f"reject_{rid}"):
            from src.decision_log import log_decision_outcome
            try:
                log_decision_outcome(rid, "rejected")
                st.toast("Empfehlung verworfen.")
            except Exception as e:                             # noqa: BLE001
                st.warning(f"Konnte Outcome nicht loggen: {e}")
    with col_thumbs_up:
        if st.button("👍", key=f"fb_up_{rid}", help="Empfehlung war hilfreich"):
            from src.decision_log import log_feedback
            log_feedback(rid, "up")
            st.toast("Feedback gespeichert.")
    with col_thumbs_down:
        if st.button("👎", key=f"fb_down_{rid}", help="Empfehlung war nicht hilfreich"):
            from src.decision_log import log_feedback
            log_feedback(rid, "down")
            st.toast("Feedback gespeichert.")

    st.markdown(_meta_html(rec), unsafe_allow_html=True)
