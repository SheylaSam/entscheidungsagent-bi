"""Tests for design tokens. Tokens are constants; tests guard against typos
and against silent drift from the spec."""
import re

from src.ui import theme


HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def test_brand_accent_is_violet():
    assert theme.PRIMARY == "#6C5CE7"


def test_chart_hero_is_blue_not_violet():
    """Charts use blue as hero; violet is reserved for nav + AI."""
    assert theme.CHART_HERO == "#0072B2"
    assert theme.CHART_HERO != theme.PRIMARY


def test_semantic_colors_are_consistent_with_spec():
    assert theme.POSITIVE == "#16A34A"
    assert theme.NEGATIVE == "#DC2626"
    assert theme.WARNING == "#D97706"
    assert theme.INFO == "#2563EB"


def test_ai_accent_is_distinct_from_primary():
    assert theme.AI_ACCENT == "#7C3AED"
    assert theme.AI_BG_TINT == "#F5F3FF"


def test_chart_categorical_palette_has_six_colorblind_safe_colors():
    """Okabe-Ito ordered, 6 colors, all valid hex."""
    assert len(theme.CHART_CATEGORICAL) == 6
    assert theme.CHART_CATEGORICAL[0] == theme.CHART_HERO
    for c in theme.CHART_CATEGORICAL:
        assert HEX_RE.match(c), f"{c!r} is not a 6-digit hex color"


def test_all_color_constants_are_valid_hex():
    color_names = [
        "BG_PAGE", "BG_CARD", "BG_SIDEBAR", "BORDER", "GRIDLINE",
        "HEADING", "BODY", "MUTED", "FAINT",
        "PRIMARY", "POSITIVE", "NEGATIVE", "WARNING", "INFO",
        "AI_ACCENT", "AI_BG_TINT", "CHART_HERO",
    ]
    for name in color_names:
        value = getattr(theme, name)
        assert HEX_RE.match(value), f"theme.{name} = {value!r} is not a 6-digit hex color"


def test_spacing_and_radius_constants_exist():
    assert theme.CARD_PADDING_PX == 24
    assert theme.CARD_GAP_PX == 16
    assert theme.CARD_RADIUS_REM == "0.75rem"
    assert theme.BUTTON_RADIUS_REM == "0.5rem"
    assert theme.PAGE_MAX_WIDTH_PX == 1280


def test_typography_constants_exist():
    assert theme.FONT_FAMILY.startswith("Inter")
    assert theme.MONO_FAMILY.startswith("JetBrains")
    # Size scale roles defined in spec §2.2
    for role in ("PAGE_H1", "CARD_H2", "KPI_NUMBER", "KPI_LABEL",
                 "KPI_DELTA", "BODY", "CHART_TICK", "TABLE_CELL", "FOOTNOTE"):
        assert role in theme.FONT_SIZES_PX, f"missing size for role {role}"
