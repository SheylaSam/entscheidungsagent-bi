"""Design tokens — single source of truth.

These constants drive `.streamlit/config.toml` (via
`scripts/render_streamlit_config.py`) AND custom UI code. They MUST
NOT diverge. Update tokens here, then run `make config` to regenerate
the Streamlit config file.

See: docs/superpowers/specs/2026-05-17-dashboard-redesign-design.md §2
"""
from __future__ import annotations

# ── Surfaces ────────────────────────────────────────────────────────────────
BG_PAGE = "#FFFFFF"
BG_CARD = "#F8FAFC"
BG_SIDEBAR = "#0F1020"
BORDER = "#E2E8F0"
GRIDLINE = "#F1F5F9"

# ── Text ────────────────────────────────────────────────────────────────────
HEADING = "#0F172A"
BODY = "#334155"
MUTED = "#64748B"
FAINT = "#94A3B8"

# ── Brand accent (active nav, primary CTA only) ─────────────────────────────
PRIMARY = "#6C5CE7"

# ── Semantic (status only) ──────────────────────────────────────────────────
POSITIVE = "#16A34A"
NEGATIVE = "#DC2626"
WARNING = "#D97706"
INFO = "#2563EB"

# ── AI accent (Decision-Agent panels & chat) ────────────────────────────────
AI_ACCENT = "#7C3AED"
AI_BG_TINT = "#F5F3FF"

# ── RFM segment semantics ───────────────────────────────────────────────────
# Maps each RFM segment to a semantic color used by Overview's
# Kundensegmente chart and the Kunden page.  Charts get gray bars with
# colored accents on Champions/Loyal (positive) and At Risk/Lost
# (negative); Others/New are neutral.
SEGMENT_SEMANTICS: dict[str, str] = {
    "Champions": POSITIVE,
    "Loyal":     POSITIVE,
    "At Risk":   NEGATIVE,
    "Lost":      NEGATIVE,
    "Others":    MUTED,
    "New":       MUTED,
}

# ── Chart categorical palette (Okabe-Ito, colorblind-safe, max 6) ───────────
CHART_HERO = "#0072B2"
CHART_CATEGORICAL: tuple[str, ...] = (
    CHART_HERO,    # blue       — default "hero" series
    "#E69F00",     # orange
    "#009E73",     # green
    "#CC79A7",     # purple
    "#56B4E9",     # sky
    "#6B7280",     # gray       — "other" / baseline
)

# ── Sequential blue scale (heatmaps) ────────────────────────────────────────
SEQUENTIAL_BLUE: tuple[str, ...] = (
    "#EFF6FF", "#BFDBFE", "#60A5FA", "#2563EB", "#1E3A8A",
)

# ── Spacing & radius ────────────────────────────────────────────────────────
CARD_PADDING_PX = 24
CARD_GAP_PX = 16
CARD_RADIUS_REM = "0.75rem"
BUTTON_RADIUS_REM = "0.5rem"
PAGE_MAX_WIDTH_PX = 1280

# ── Typography ──────────────────────────────────────────────────────────────
FONT_FAMILY = (
    "Inter, -apple-system, BlinkMacSystemFont, "
    '"Segoe UI", Roboto, system-ui, sans-serif'
)
MONO_FAMILY = (
    '"JetBrains Mono", ui-monospace, SFMono-Regular, '
    'Menlo, Consolas, monospace'
)
HEADING_FAMILY = FONT_FAMILY  # Inter covers both; one family by design

FONT_SIZES_PX: dict[str, int] = {
    "PAGE_H1":     24,
    "CARD_H2":     15,
    "KPI_NUMBER":  32,
    "KPI_LABEL":   12,
    "KPI_DELTA":   13,
    "BODY":        14,
    "CHART_TICK":  12,
    "TABLE_CELL":  13,
    "FOOTNOTE":    11,
}

# Google-Fonts URL for the @import in CSS / config.toml font slot
INTER_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Inter:wght@400;500;600&display=swap"
)
JETBRAINS_MONO_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=JetBrains+Mono:wght@400;500&display=swap"
)


# ── Global CSS injection ────────────────────────────────────────────────────
def global_css() -> str:
    """Return the complete <style> block to inject once per page.

    Sources two Google Fonts (Inter, JetBrains Mono), forces tabular
    figures wherever numbers appear, sets card padding/border tokens,
    hides the default Streamlit chrome (footer/main-menu), and defines
    the .kpi-* class hierarchy used by src/ui/cards.py.
    """
    return f"""
<style>
@import url("{INTER_URL}");
@import url("{JETBRAINS_MONO_URL}");

/* ── Page chrome ──────────────────────────────────────────────── */
.block-container {{
    padding-top: 2rem;
    padding-bottom: 4rem;
    max-width: {PAGE_MAX_WIDTH_PX}px;
}}
#MainMenu, footer {{ visibility: hidden; }}

/* ── Tabular figures everywhere numbers live ──────────────────── */
.kpi-number, .stDataFrame td, [data-testid="stMetricValue"] {{
    font-variant-numeric: tabular-nums;
    font-feature-settings: "tnum" 1, "cv11" 1;
}}

/* ── KPI card layout (used by src/ui/cards.kpi_card) ──────────── */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.kpi-card) {{
    border: 1px solid {BORDER};
    border-radius: {CARD_RADIUS_REM};
    padding: {CARD_PADDING_PX}px;
    background: {BG_PAGE};
}}
.kpi-card {{
    display: flex;
    flex-direction: column;
    gap: 6px;
}}
.kpi-label {{
    display: flex;
    align-items: center;
    gap: 6px;
    color: {MUTED};
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZES_PX["KPI_LABEL"]}px;
    font-weight: 500;
    letter-spacing: 0.02em;
    text-transform: uppercase;
}}
.kpi-tooltip {{
    color: {FAINT};
    cursor: help;
    font-size: {FONT_SIZES_PX["KPI_LABEL"]}px;
}}
.kpi-number {{
    color: {HEADING};
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZES_PX["KPI_NUMBER"]}px;
    font-weight: 600;
    line-height: 1.1;
    margin-top: 2px;
}}
.kpi-delta {{
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZES_PX["KPI_DELTA"]}px;
    font-weight: 500;
    margin-bottom: 4px;
}}
.kpi-delta.is-muted {{ color: {MUTED}; }}
.kpi-delta-period {{ color: {MUTED}; margin-left: 6px; font-weight: 400; }}
</style>
""".strip()


def inject_global_css() -> None:
    """Call once near the top of the Streamlit script."""
    import streamlit as st  # imported lazily so tests can import this module
    st.markdown(global_css(), unsafe_allow_html=True)
