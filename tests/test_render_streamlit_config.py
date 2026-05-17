"""Tests for the config generator. Verifies the produced TOML is valid
and that key token values from theme.py end up in the right TOML slots."""
try:
    import tomllib  # py311+
except ImportError:                              # pragma: no cover
    import tomli as tomllib  # type: ignore

from scripts import render_streamlit_config as gen
from src.ui import theme


def test_render_produces_valid_toml():
    text = gen.render()
    parsed = tomllib.loads(text)
    assert "theme" in parsed


def test_render_writes_primary_color_to_theme_block():
    parsed = tomllib.loads(gen.render())
    assert parsed["theme"]["primaryColor"] == theme.PRIMARY


def test_render_writes_chart_categorical_palette():
    parsed = tomllib.loads(gen.render())
    assert list(parsed["theme"]["chartCategoricalColors"]) == list(theme.CHART_CATEGORICAL)


def test_render_writes_dark_sidebar_block():
    parsed = tomllib.loads(gen.render())
    assert parsed["theme"]["sidebar"]["backgroundColor"] == theme.BG_SIDEBAR


def test_render_writes_font_family_with_google_url():
    parsed = tomllib.loads(gen.render())
    font_value = parsed["theme"]["font"]
    assert font_value.startswith("Inter:")
    assert "fonts.googleapis.com" in font_value


def test_render_writes_base_radius():
    parsed = tomllib.loads(gen.render())
    assert parsed["theme"]["baseRadius"] == theme.CARD_RADIUS_REM


def test_write_creates_streamlit_config_file(tmp_path, monkeypatch):
    target = tmp_path / ".streamlit" / "config.toml"
    monkeypatch.setattr(gen, "TARGET_PATH", target)
    gen.write()
    assert target.exists()
    parsed = tomllib.loads(target.read_text())
    assert parsed["theme"]["primaryColor"] == theme.PRIMARY


def test_write_is_idempotent(tmp_path, monkeypatch):
    target = tmp_path / ".streamlit" / "config.toml"
    monkeypatch.setattr(gen, "TARGET_PATH", target)
    gen.write()
    first = target.read_text()
    gen.write()
    second = target.read_text()
    assert first == second


def test_committed_config_matches_current_theme():
    """If this fails, run `make config` and commit the result."""
    expected = gen.render()
    actual = (gen.PROJECT_ROOT / ".streamlit" / "config.toml").read_text()
    assert actual == expected, (
        "Committed .streamlit/config.toml is out of date.\n"
        "Run `make config` and commit the regenerated file."
    )
