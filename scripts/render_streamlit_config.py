"""Generate .streamlit/config.toml from src/ui/theme.py.

This is the ONLY mechanism that writes .streamlit/config.toml. Run
`make config` after editing src/ui/theme.py. The file is committed so
production deploys don't depend on the script.
"""
from __future__ import annotations

from pathlib import Path

from src.ui import theme

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TARGET_PATH = PROJECT_ROOT / ".streamlit" / "config.toml"

_HEADER = """\
# This file is GENERATED from src/ui/theme.py via
# scripts/render_streamlit_config.py.  Do not edit by hand.
# To change a value: edit src/ui/theme.py, then run `make config`.
"""


def _toml_string(value: str) -> str:
    """Render a TOML string literal with proper quoting and escaping."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _toml_array(values: tuple[str, ...] | list[str]) -> str:
    inner = ", ".join(_toml_string(v) for v in values)
    return f"[{inner}]"


def render() -> str:
    """Return the full TOML text."""
    font_slot = f"Inter:{theme.INTER_URL}"
    mono_slot = f"JetBrains Mono:{theme.JETBRAINS_MONO_URL}"

    return (
        _HEADER
        + "\n"
        + "[theme]\n"
        + f'base = "light"\n'
        + f"primaryColor = {_toml_string(theme.PRIMARY)}\n"
        + f"backgroundColor = {_toml_string(theme.BG_PAGE)}\n"
        + f"secondaryBackgroundColor = {_toml_string(theme.BG_CARD)}\n"
        + f"textColor = {_toml_string(theme.HEADING)}\n"
        + f"borderColor = {_toml_string(theme.BORDER)}\n"
        + f"linkColor = {_toml_string(theme.PRIMARY)}\n"
        + f"baseRadius = {_toml_string(theme.CARD_RADIUS_REM)}\n"
        + f"buttonRadius = {_toml_string(theme.BUTTON_RADIUS_REM)}\n"
        + f"showWidgetBorder = false\n"
        + f"showSidebarBorder = true\n"
        + f"dataframeHeaderBackgroundColor = {_toml_string(theme.BG_CARD)}\n"
        + f"font = {_toml_string(font_slot)}\n"
        + f"headingFont = {_toml_string(font_slot)}\n"
        + f"codeFont = {_toml_string(mono_slot)}\n"
        + f"chartCategoricalColors = {_toml_array(theme.CHART_CATEGORICAL)}\n"
        + f"chartSequentialColors = {_toml_array(theme.SEQUENTIAL_BLUE)}\n"
        + "\n"
        + "[theme.sidebar]\n"
        + f"backgroundColor = {_toml_string(theme.BG_SIDEBAR)}\n"
        + f'textColor = "#FFFFFF"\n'
        + f"primaryColor = {_toml_string(theme.PRIMARY)}\n"
        + f"baseRadius = {_toml_string(theme.BUTTON_RADIUS_REM)}\n"
    )


def write() -> None:
    """Write `.streamlit/config.toml`. Idempotent."""
    TARGET_PATH.parent.mkdir(parents=True, exist_ok=True)
    TARGET_PATH.write_text(render())


if __name__ == "__main__":
    write()
    print(f"wrote {TARGET_PATH}")
