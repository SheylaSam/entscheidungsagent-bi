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
    assert "JetBrains" in theme.MONO_FAMILY
    # Size scale roles defined in spec §2.2
    for role in ("PAGE_H1", "CARD_H2", "KPI_NUMBER", "KPI_LABEL",
                 "KPI_DELTA", "BODY", "CHART_TICK", "TABLE_CELL", "FOOTNOTE"):
        assert role in theme.FONT_SIZES_PX, f"missing size for role {role}"


def test_inject_global_css_returns_a_style_block():
    css = theme.global_css()
    assert "<style>" in css and "</style>" in css


def test_global_css_imports_inter_font():
    css = theme.global_css()
    assert "Inter" in css
    assert "fonts.googleapis.com" in css


def test_global_css_enables_tabular_nums_on_kpi_class():
    css = theme.global_css()
    assert ".kpi-number" in css
    assert "tabular-nums" in css


def test_global_css_defines_kpi_label_delta_classes():
    css = theme.global_css()
    for cls in (".kpi-label", ".kpi-number", ".kpi-delta", ".kpi-card"):
        assert cls in css, f"missing rule for {cls}"


def test_global_css_uses_token_values():
    css = theme.global_css()
    assert theme.MUTED in css
    assert theme.HEADING in css
    assert theme.BORDER in css


def test_segment_semantics_has_known_segments():
    expected_segments = {"Champions", "Loyal", "At Risk", "Lost", "New", "Others"}
    assert set(theme.SEGMENT_SEMANTICS.keys()) >= expected_segments


def test_segment_semantics_maps_to_token_colors():
    valid = {theme.POSITIVE, theme.NEGATIVE, theme.MUTED, theme.FAINT}
    for seg, color in theme.SEGMENT_SEMANTICS.items():
        assert color in valid, f"{seg!r} → {color!r} not in {valid}"


def test_champions_and_loyal_are_positive():
    assert theme.SEGMENT_SEMANTICS["Champions"] == theme.POSITIVE
    assert theme.SEGMENT_SEMANTICS["Loyal"] == theme.POSITIVE


def test_at_risk_and_lost_are_negative():
    assert theme.SEGMENT_SEMANTICS["At Risk"] == theme.NEGATIVE
    assert theme.SEGMENT_SEMANTICS["Lost"] == theme.NEGATIVE


def test_global_css_defines_agent_card_classes():
    css = theme.global_css()
    for cls in (".agent-card", ".agent-marker", ".agent-title",
                ".agent-priority-badge", ".agent-meta", ".agent-finding"):
        assert cls in css, f"missing rule for {cls}"


def test_global_css_agent_marker_uses_ai_accent():
    css = theme.global_css()
    assert theme.AI_ACCENT in css
    assert "4px" in css  # border-left width


def test_global_css_styles_chat_assistant_bubble():
    css = theme.global_css()
    assert "chatAvatarIcon-assistant" in css
    assert theme.AI_BG_TINT in css


def test_global_css_defines_suggestion_chip_class():
    css = theme.global_css()
    assert ".chat-suggestion-chip" in css
