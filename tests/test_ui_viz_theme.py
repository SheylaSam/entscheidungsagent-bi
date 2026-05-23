"""Tests for the Plotly polish module. Verify the templates are registered
with the right tokens and that polish(fig) applies the right template."""
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import pytest

from src.ui import theme, viz_theme


@pytest.fixture(autouse=True)
def _reset_default_template():
    """Each test starts with polish_light as the default."""
    pio.templates.default = "polish_light"
    yield


def test_templates_are_registered():
    assert "polish_light" in pio.templates
    assert "polish_dark" in pio.templates


def test_default_template_is_polish_light():
    assert pio.templates.default == "polish_light"


def test_light_template_uses_categorical_palette():
    tpl = pio.templates["polish_light"]
    assert tuple(tpl.layout.colorway) == theme.CHART_CATEGORICAL


def test_light_template_has_transparent_backgrounds():
    tpl = pio.templates["polish_light"]
    assert tpl.layout.paper_bgcolor == "rgba(0,0,0,0)"
    assert tpl.layout.plot_bgcolor == "rgba(0,0,0,0)"


def test_light_template_disables_vertical_gridlines():
    tpl = pio.templates["polish_light"]
    assert tpl.layout.xaxis.showgrid is False


def test_light_template_enables_faint_horizontal_gridlines():
    tpl = pio.templates["polish_light"]
    assert tpl.layout.yaxis.showgrid is True
    assert tpl.layout.yaxis.gridcolor == theme.GRIDLINE


def test_dark_template_uses_dark_paper():
    tpl = pio.templates["polish_dark"]
    assert tpl.layout.paper_bgcolor != "rgba(0,0,0,0)"


def test_hover_is_x_unified():
    tpl = pio.templates["polish_light"]
    assert tpl.layout.hovermode == "x unified"


def test_polish_returns_the_same_figure():
    fig = px.bar(x=["a", "b"], y=[1, 2])
    out = viz_theme.polish(fig)
    assert out is fig


def test_polish_applies_light_template_by_default():
    fig = px.bar(x=["a", "b"], y=[1, 2])
    viz_theme.polish(fig)
    assert fig.layout.template.layout.colorway == theme.CHART_CATEGORICAL


def test_polish_dark_applies_dark_template():
    fig = px.bar(x=["a", "b"], y=[1, 2])
    viz_theme.polish(fig, dark=True)
    assert fig.layout.template.layout.paper_bgcolor != "rgba(0,0,0,0)"


def test_plotly_config_disables_modebar():
    assert viz_theme.PLOTLY_CONFIG["displayModeBar"] is False
    assert viz_theme.PLOTLY_CONFIG["displaylogo"] is False
    assert viz_theme.PLOTLY_CONFIG["responsive"] is True


def test_polish_applies_y_format():
    fig = go.Figure(go.Bar(x=["a", "b"], y=[1, 2]))
    viz_theme.polish(fig, y_format=",.0f")
    assert fig.layout.yaxis.tickformat == ",.0f"


def test_polish_adds_reference_line():
    fig = go.Figure(go.Bar(x=["a", "b"], y=[1, 2]))
    viz_theme.polish(fig, reference=1.5, reference_label="Ziel")
    shapes = fig.layout.shapes or ()
    assert any(s.type == "line" for s in shapes)
    annotations = fig.layout.annotations or ()
    assert any("Ziel" in (a.text or "") for a in annotations)


def test_polish_without_reference_adds_no_line():
    fig = go.Figure(go.Bar(x=["a", "b"], y=[1, 2]))
    viz_theme.polish(fig)
    assert not (fig.layout.shapes or ())


def test_polish_hide_legend():
    fig = go.Figure(go.Bar(x=["a", "b"], y=[1, 2]))
    viz_theme.polish(fig, hide_legend=True)
    assert fig.layout.showlegend is False


def test_polish_default_keeps_legend_visible():
    fig = go.Figure(go.Bar(x=["a", "b"], y=[1, 2]))
    viz_theme.polish(fig)
    assert fig.layout.showlegend is not False
