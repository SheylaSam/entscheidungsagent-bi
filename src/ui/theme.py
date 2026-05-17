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
