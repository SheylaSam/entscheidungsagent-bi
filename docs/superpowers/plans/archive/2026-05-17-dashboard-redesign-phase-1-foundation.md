# Dashboard Redesign — Phase 1: Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the design-token foundation and a single shared Plotly polish layer so every chart in the dashboard immediately renders with consistent typography, colors, gridlines, hover, and margins — without any structural changes to navigation, layout, or component libraries.

**Architecture:** Tokens live as Python constants in `src/ui/theme.py` (single source of truth). A generator script renders `.streamlit/config.toml` from those constants so native Streamlit theming stays in sync with custom code. A Plotly module `src/ui/viz_theme.py` registers `polish_light` / `polish_dark` templates and exposes a `polish(fig, ...)` function applied at the last step before `st.plotly_chart` for every existing chart in `app.py`.

**Tech Stack:** Streamlit ≥ 1.50 (theme features), Plotly ≥ 5.20, pytest, tomli/tomllib. No new component libraries are introduced in this phase.

**Reference:** [`docs/superpowers/specs/2026-05-17-dashboard-redesign-design.md`](../specs/2026-05-17-dashboard-redesign-design.md) §1, §2, §5.

**Out of scope for this phase:** Sidebar, page-dispatch, KPI-card refactor, agent panel, new pages, dark-mode rollout. Those are Phases 2–7 in the spec.

---

## File Plan

**Create:**
- `src/ui/__init__.py` — empty package marker
- `src/ui/theme.py` — design token constants
- `src/ui/viz_theme.py` — Plotly templates + `polish()` + `PLOTLY_CONFIG`
- `scripts/__init__.py` — empty package marker
- `scripts/render_streamlit_config.py` — generates `.streamlit/config.toml` from `theme.py`
- `.streamlit/config.toml` — generated, committed
- `tests/test_ui_theme.py` — token tests
- `tests/test_ui_viz_theme.py` — Plotly template tests
- `tests/test_render_streamlit_config.py` — config generator tests
- `Makefile` — `make config` target so the generator is discoverable

**Modify:**
- `requirements.txt` — bump streamlit, add tomli for Python < 3.11
- `app.py` — wrap every existing `st.plotly_chart(fig, ...)` site with `polish(fig)` and pass `theme=None, config=PLOTLY_CONFIG`. 14 sites total. No other changes in this phase.

**Do not touch:**
- Any `src/*.py` other than what's listed
- The `tests/` files for existing modules
- `README.md` (updates land later phases)

---

## Task 1: Bump Streamlit dependency

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Check current versions**

Run: `pip show streamlit plotly | grep -E "Name|Version"`
Expected output includes `streamlit 1.33.0` (current) and `plotly 5.21.0`.

- [ ] **Step 2: Update `requirements.txt`**

Replace the existing streamlit/plotly lines:

```
streamlit==1.33.0
```

with:

```
streamlit>=1.50,<2.0
plotly>=5.20,<6.0
tomli>=2.0; python_version < "3.11"
```

(Leave `pandas`, `prophet`, `openpyxl`, `pytest` lines untouched.)

- [ ] **Step 3: Install updated dependencies**

Run: `pip install -r requirements.txt`
Expected: streamlit is upgraded to ≥ 1.50; no errors.

- [ ] **Step 4: Verify versions**

Run: `python -c "import streamlit, plotly; print(streamlit.__version__, plotly.__version__)"`
Expected: streamlit ≥ 1.50, plotly ≥ 5.20.

- [ ] **Step 5: Smoke-check that the existing app still imports**

Run: `python -c "import app" 2>&1 | head -20` (from project root)
Expected: no exception (Streamlit will warn about being run outside `streamlit run`; that's fine).

- [ ] **Step 6: Commit**

```bash
git add requirements.txt
git commit -m "build(deps): bump streamlit to >=1.50 for theming features"
```

---

## Task 2: Create the design-tokens module

**Files:**
- Create: `src/ui/__init__.py`
- Create: `src/ui/theme.py`
- Create: `tests/test_ui_theme.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_ui_theme.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ui_theme.py -v`
Expected: all tests FAIL with `ModuleNotFoundError: No module named 'src.ui'` or similar.

- [ ] **Step 3: Create the package marker**

Create `src/ui/__init__.py` as an empty file:

```python
"""UI primitives, design tokens, and Plotly polish layer."""
```

- [ ] **Step 4: Create `src/ui/theme.py`**

Create `src/ui/theme.py`:

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_ui_theme.py -v`
Expected: all 8 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/ui/__init__.py src/ui/theme.py tests/test_ui_theme.py
git commit -m "feat(ui): add design tokens module (theme.py)"
```

---

## Task 3: Streamlit config generator

**Files:**
- Create: `scripts/__init__.py`
- Create: `scripts/render_streamlit_config.py`
- Create: `tests/test_render_streamlit_config.py`
- Create: `Makefile`

The generator reads `src/ui/theme.py` and emits a complete `.streamlit/config.toml`. This is the only mechanism that should write that file — never hand-edit it.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_render_streamlit_config.py`:

```python
"""Tests for the config generator. Verifies the produced TOML is valid
and that key token values from theme.py end up in the right TOML slots."""
from pathlib import Path

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_render_streamlit_config.py -v`
Expected: all tests FAIL with `ModuleNotFoundError: No module named 'scripts'`.

- [ ] **Step 3: Create the package marker**

Create `scripts/__init__.py` as empty file:

```python
"""Build/codegen scripts kept out of the runtime package."""
```

- [ ] **Step 4: Create `scripts/render_streamlit_config.py`**

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_render_streamlit_config.py -v`
Expected: all 8 tests PASS.

- [ ] **Step 6: Create `Makefile`**

```makefile
.PHONY: config test

config:
	python -m scripts.render_streamlit_config

test:
	pytest tests/ -v
```

- [ ] **Step 7: Generate the real config file**

Run: `make config`
Expected output: `wrote /Users/sheyla/Projects/Entscheidungsagent-BI/.streamlit/config.toml`

- [ ] **Step 8: Verify the generated file is valid TOML**

Run: `python -c "import tomllib; print(tomllib.loads(open('.streamlit/config.toml').read())['theme']['primaryColor'])"`
(On Python < 3.11 use `tomli` instead of `tomllib`.)
Expected output: `#6C5CE7`

- [ ] **Step 9: Commit**

```bash
git add scripts/__init__.py scripts/render_streamlit_config.py \
        tests/test_render_streamlit_config.py Makefile .streamlit/config.toml
git commit -m "feat(ui): generate .streamlit/config.toml from design tokens"
```

---

## Task 4: Plotly polish module — template registration

This task creates the templates and the `polish()` function with **just the template-application path**. Per-chart options (y_format, reference line) come in Task 5 to keep this task small.

**Files:**
- Create: `src/ui/viz_theme.py`
- Create: `tests/test_ui_viz_theme.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_ui_viz_theme.py`:

```python
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
    # Dark template paints the paper explicitly (no transparency).


def test_hover_is_x_unified():
    tpl = pio.templates["polish_light"]
    assert tpl.layout.hovermode == "x unified"


def test_polish_returns_the_same_figure():
    fig = px.bar(x=["a", "b"], y=[1, 2])
    out = viz_theme.polish(fig)
    assert out is fig  # in-place, returns same ref


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ui_viz_theme.py -v`
Expected: all tests FAIL with `ModuleNotFoundError: No module named 'src.ui.viz_theme'`.

- [ ] **Step 3: Implement `src/ui/viz_theme.py`**

```python
"""Plotly polish layer.

Two templates (`polish_light`, `polish_dark`) registered at import time,
plus a `polish(fig, ...)` function applied as the last step before
`st.plotly_chart`. PLOTLY_CONFIG is the matching `config=` argument.

Usage:
    fig = px.line(df, x="month", y="revenue")
    fig = polish(fig)
    st.plotly_chart(fig, config=PLOTLY_CONFIG,
                    use_container_width=True, theme=None)

NOTE: pass `theme=None` to `st.plotly_chart` — otherwise Streamlit
overrides our template.
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

from src.ui import theme


def _build_template(dark: bool) -> go.layout.Template:
    if dark:
        paper = "#0B0F17"
        plot = "#0B0F17"
        grid = "#1F2937"
        axis = "#94A3B8"
        text = "#CBD5E1"
    else:
        paper = "rgba(0,0,0,0)"
        plot = "rgba(0,0,0,0)"
        grid = theme.GRIDLINE
        axis = theme.MUTED
        text = theme.BODY

    return go.layout.Template(
        layout=go.Layout(
            paper_bgcolor=paper,
            plot_bgcolor=plot,
            font=dict(family=theme.FONT_FAMILY,
                      size=theme.FONT_SIZES_PX["BODY"] - 1,  # 13
                      color=text),
            title=dict(
                font=dict(family=theme.HEADING_FAMILY,
                          size=theme.FONT_SIZES_PX["CARD_H2"],
                          color=theme.HEADING if not dark else "#F1F5F9"),
                x=0, xanchor="left", pad=dict(t=4, b=12),
            ),
            margin=dict(l=48, r=16, t=40, b=40),
            colorway=list(theme.CHART_CATEGORICAL),
            xaxis=dict(
                showgrid=False, zeroline=False, showline=False,
                ticks="outside", tickcolor=grid,
                tickfont=dict(color=axis, size=theme.FONT_SIZES_PX["CHART_TICK"]),
                title=dict(font=dict(color=axis, size=theme.FONT_SIZES_PX["CHART_TICK"])),
            ),
            yaxis=dict(
                showgrid=True, gridcolor=grid, gridwidth=1,
                zeroline=False, showline=False, ticks="",
                tickfont=dict(color=axis, size=theme.FONT_SIZES_PX["CHART_TICK"]),
                title=dict(font=dict(color=axis, size=theme.FONT_SIZES_PX["CHART_TICK"])),
            ),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02,
                xanchor="left", x=0,
                bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)",
                font=dict(color=axis, size=theme.FONT_SIZES_PX["CHART_TICK"]),
            ),
            hovermode="x unified",
            hoverlabel=dict(
                bgcolor=theme.HEADING if not dark else "#1F2937",
                bordercolor=theme.HEADING if not dark else "#1F2937",
                font=dict(family=theme.FONT_FAMILY,
                          size=theme.FONT_SIZES_PX["CHART_TICK"],
                          color="#F8FAFC"),
            ),
            modebar=dict(
                orientation="v", bgcolor="rgba(0,0,0,0)",
                color=axis, activecolor=text,
            ),
        )
    )


pio.templates["polish_light"] = _build_template(dark=False)
pio.templates["polish_dark"] = _build_template(dark=True)
pio.templates.default = "polish_light"


PLOTLY_CONFIG: dict = {
    "displayModeBar": False,
    "displaylogo": False,
    "responsive": True,
    "scrollZoom": False,
    "modeBarButtonsToRemove": [
        "select2d", "lasso2d", "autoScale2d", "toggleSpikelines",
    ],
}


def polish(fig: go.Figure, *, dark: bool = False) -> go.Figure:
    """Apply the polished template to ``fig``.

    Returns the same Figure for fluent chaining. This is the minimal
    surface; per-chart options (y_format, reference line, hide_legend)
    are added in Task 5.
    """
    fig.update_layout(template="polish_dark" if dark else "polish_light")
    return fig
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ui_viz_theme.py -v`
Expected: all 12 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ui/viz_theme.py tests/test_ui_viz_theme.py
git commit -m "feat(ui): register polish_light/dark Plotly templates and polish()"
```

---

## Task 5: Polish module — per-chart options

Extend `polish()` with the per-chart options promised in the spec: `y_format`, `reference` line, `reference_label`, `hide_legend`, and unified hover-template normalization.

**Files:**
- Modify: `src/ui/viz_theme.py`
- Modify: `tests/test_ui_viz_theme.py`

- [ ] **Step 1: Append failing tests to `tests/test_ui_viz_theme.py`**

Append to the existing file:

```python
def test_polish_applies_y_format():
    fig = go.Figure(go.Bar(x=["a", "b"], y=[1, 2]))
    viz_theme.polish(fig, y_format=",.0f")
    assert fig.layout.yaxis.tickformat == ",.0f"


def test_polish_adds_reference_line():
    fig = go.Figure(go.Bar(x=["a", "b"], y=[1, 2]))
    viz_theme.polish(fig, reference=1.5, reference_label="Ziel")
    # The hline is rendered as a shape on the layout.
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
    # Default-None means Plotly decides; we just don't force it off.
    assert fig.layout.showlegend is not False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ui_viz_theme.py -v`
Expected: 5 new tests FAIL (TypeError: unexpected keyword 'y_format' etc.).

- [ ] **Step 3: Replace the `polish` function in `src/ui/viz_theme.py`**

Replace the existing minimal `polish()` with:

```python
def polish(
    fig: go.Figure,
    *,
    dark: bool = False,
    y_format: str | None = None,
    reference: float | None = None,
    reference_label: str = "Ziel",
    hide_legend: bool = False,
) -> go.Figure:
    """Apply the polished template + optional per-chart niceties.

    Parameters
    ----------
    fig:
        The figure to mutate.
    dark:
        Apply ``polish_dark`` instead of ``polish_light``.
    y_format:
        Plotly tick-format string for the y-axis (e.g. ``",.0f"``,
        ``"£,.0f"``, ``".1%"``).
    reference:
        If given, draw a dotted horizontal reference line at this y
        value.  Annotated top-right with ``reference_label``.
    reference_label:
        Text for the reference-line annotation (only used when
        ``reference`` is given).
    hide_legend:
        Force-hide the legend (use this when you have direct labels).

    Returns
    -------
    The same Figure object, for fluent chaining.
    """
    fig.update_layout(template="polish_dark" if dark else "polish_light")

    if y_format is not None:
        fig.update_yaxes(tickformat=y_format)

    if reference is not None:
        fig.add_hline(
            y=reference,
            line_dash="dot",
            line_width=1,
            line_color=theme.FAINT,
            annotation_text=f"{reference_label}: {reference:,.0f}",
            annotation_position="top right",
            annotation_font=dict(
                size=theme.FONT_SIZES_PX["FOOTNOTE"],
                color=theme.FAINT,
            ),
        )

    if hide_legend:
        fig.update_layout(showlegend=False)

    return fig
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ui_viz_theme.py -v`
Expected: all 17 tests PASS (12 original + 5 new).

- [ ] **Step 5: Commit**

```bash
git add src/ui/viz_theme.py tests/test_ui_viz_theme.py
git commit -m "feat(ui): polish() supports y_format, reference, hide_legend"
```

---

## Task 6: Wire `polish()` into `app.py` — Übersicht (Tab 1)

Two charts (Umsatztrend bar, Kundensegmente horizontal bar). The current code manually sets `marker_color`, hardcoded heights, and per-segment color maps. We strip the manual styling and let the template drive it. **Exception:** keep the segment-color rules — we'll revisit those in Phase 4 (per-page polish). For now, keep the existing `color_discrete_map` so the chart stays semantically the same.

**Files:**
- Modify: `app.py` (lines ~498–513)

- [ ] **Step 1: Add the import**

In `app.py`, locate the import block at the top of the file (around line 1–16). Add this import after the existing `src.` imports:

```python
from src.ui.viz_theme import polish, PLOTLY_CONFIG
```

- [ ] **Step 2: Update the Umsatztrend chart**

In `app.py`, replace this block (currently around lines 498–502):

```python
        fig = px.bar(actuals.tail(12), x='ds', y='y', labels={'ds': '', 'y': 'Umsatz (£)'})
        fig.update_traces(marker_color='#60a5fa')
        fig.update_layout(height=300, margin=dict(t=10, b=0), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
```

with:

```python
        fig = px.bar(actuals.tail(12), x='ds', y='y', labels={'ds': '', 'y': ''})
        fig.update_layout(height=300)
        fig = polish(fig, y_format=',.0f', hide_legend=True)
        st.plotly_chart(fig, use_container_width=True,
                        theme=None, config=PLOTLY_CONFIG)
```

Notes: y-axis title removed (the section subheader "Umsatztrend" already says it); `marker_color` removed (template colorway picks blue by default); margin removed (template sets it).

- [ ] **Step 3: Update the Kundensegmente chart**

Replace this block (currently around lines 510–513):

```python
        fig2 = px.bar(seg_counts, x='Anzahl', y='Segment', orientation='h',
                      color='Segment', color_discrete_map=color_map)
        fig2.update_layout(height=300, margin=dict(t=10, b=0), showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)
```

with:

```python
        fig2 = px.bar(seg_counts, x='Anzahl', y='Segment', orientation='h',
                      color='Segment', color_discrete_map=color_map)
        fig2.update_layout(height=300)
        fig2 = polish(fig2, hide_legend=True)
        st.plotly_chart(fig2, use_container_width=True,
                        theme=None, config=PLOTLY_CONFIG)
```

(The `color_discrete_map` is intentionally preserved — it's a deliberate semantic mapping per segment. Recoloring per the new palette comes in Phase 4 of the spec.)

- [ ] **Step 4: Run the app and visually verify**

Run: `streamlit run app.py`
Open the app in the browser. On the Übersicht tab, verify:
- Both charts render without errors
- No more modebar floating top-right
- No gridlines on x-axis
- Hover shows a single dark tooltip with all series

If a chart fails to render or looks broken, stop here and fix before continuing.

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "refactor(app): apply polish() to Übersicht charts"
```

---

## Task 7: Wire `polish()` into `app.py` — Forecast (Tab 2)

Four charts: main forecast bar/error bar (line 564–593), backtest (637–654), trend (665–676), yearly (686–697).

**Files:**
- Modify: `app.py` (lines ~564–697)

- [ ] **Step 1: Update the main forecast chart**

Locate the block at ~line 585–593:

```python
    fig.update_layout(
        height=430,
        barmode='group',
        xaxis_title='',
        yaxis_title='Umsatz (£)',
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        margin=dict(t=20, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)
```

Replace with:

```python
    fig.update_layout(
        height=430,
        barmode='group',
        xaxis_title='',
        yaxis_title='',
    )
    fig = polish(fig, y_format=',.0f', reference=forecast_base_value,
                 reference_label='Vergleichsbasis')
    st.plotly_chart(fig, use_container_width=True,
                    theme=None, config=PLOTLY_CONFIG)
```

Note: the existing `fig.add_hline(y=forecast_base_value, ...)` earlier in the file (line 583) becomes redundant — **delete those 2 lines (583–584):**

```python
    fig.add_hline(y=forecast_base_value, line_dash='dot', line_color='#94a3b8',
                  annotation_text='Vergleichsbasis', annotation_position='top left')
```

(polish() now draws the reference line consistently.)

- [ ] **Step 2: Update the backtest chart**

Locate around line 637–654. Find the `st.plotly_chart(fig_bt, use_container_width=True)` line and replace its preceding `fig_bt.update_layout(...)` + chart call with:

```python
        fig_bt.update_layout(height=380, xaxis_title='', yaxis_title='')
        fig_bt = polish(fig_bt, y_format=',.0f')
        st.plotly_chart(fig_bt, use_container_width=True,
                        theme=None, config=PLOTLY_CONFIG)
```

(Remove the `legend=...`, `margin=...` keys that are already in the file; the template handles them.)

- [ ] **Step 3: Update the trend and yearly charts**

Same pattern — locate each `st.plotly_chart(fig_trend, ...)` and `st.plotly_chart(fig_yearly, ...)` call (around lines 676 and 697). For each, strip the `legend=...` and `margin=...` from the preceding `update_layout`, then add a `polish(...)` call before the chart call and pass `theme=None, config=PLOTLY_CONFIG`:

```python
            fig_trend = polish(fig_trend, y_format=',.0f')
            st.plotly_chart(fig_trend, use_container_width=True,
                            theme=None, config=PLOTLY_CONFIG)
```

```python
                fig_yearly = polish(fig_yearly, y_format=',.0f')
                st.plotly_chart(fig_yearly, use_container_width=True,
                                theme=None, config=PLOTLY_CONFIG)
```

- [ ] **Step 4: Visual verification**

Run: `streamlit run app.py` (or refresh the open browser)
Navigate to the Forecast tab. Verify all four charts render, reference line is present on the main chart, no modebar, no vertical gridlines.

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "refactor(app): apply polish() to Forecast tab charts"
```

---

## Task 8: Wire `polish()` into `app.py` — Kunden RFM (Tab 3)

Two charts: RFM scatter (line 709) and customer-country bar (line 748).

**Files:**
- Modify: `app.py` (lines ~709–758)

- [ ] **Step 1: Update the RFM scatter**

Locate `st.plotly_chart(fig, use_container_width=True)` at ~line 715. Update the preceding `fig` setup to remove inline color/margin/height overrides, then add `polish()`:

```python
        fig = px.scatter(rfm, x='recency', y='frequency', size='monetary',
                         color='segment', hover_data=['monetary'])
        fig.update_layout(height=400)
        fig = polish(fig)
        st.plotly_chart(fig, use_container_width=True,
                        theme=None, config=PLOTLY_CONFIG)
```

Keep `color='segment'` — the template's colorway will color the segments from the categorical palette.

- [ ] **Step 2: Update the country bar chart**

Locate `st.plotly_chart(fig_c, use_container_width=True)` at ~line 758. Update its preceding setup similarly:

```python
        fig_c.update_layout(height=400, xaxis_title='', yaxis_title='')
        fig_c = polish(fig_c, y_format=',.0f', hide_legend=True)
        st.plotly_chart(fig_c, use_container_width=True,
                        theme=None, config=PLOTLY_CONFIG)
```

- [ ] **Step 3: Visual verification**

Refresh app. Navigate to Kunden RFM tab. Verify both charts render.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "refactor(app): apply polish() to Kunden RFM tab charts"
```

---

## Task 9: Wire `polish()` into `app.py` — Produkte (Tab 4)

Three charts: top products (782), trend (814), country (836).

**Files:**
- Modify: `app.py` (lines ~782–845)

- [ ] **Step 1: Update top-products chart**

At ~line 782–786:

```python
            fig = px.bar(top_products, x='revenue', y='description', orientation='h',
                         labels={'revenue': '', 'description': ''})
            fig.update_layout(height=420)
            fig = polish(fig, y_format=',.0f', hide_legend=True)
            selection = st.plotly_chart(fig, use_container_width=True,
                                        theme=None, config=PLOTLY_CONFIG,
                                        on_select='rerun')
```

(`on_select='rerun'` is the current behavior — preserved.)

- [ ] **Step 2: Update trend chart (~line 814)**

```python
            fig_trend.update_layout(height=320, xaxis_title='', yaxis_title='')
            fig_trend = polish(fig_trend, y_format=',.0f')
            st.plotly_chart(fig_trend, use_container_width=True,
                            theme=None, config=PLOTLY_CONFIG)
```

- [ ] **Step 3: Update country chart (~line 836)**

```python
        fig_country.update_layout(height=380, xaxis_title='', yaxis_title='')
        fig_country = polish(fig_country, y_format=',.0f', hide_legend=True)
        st.plotly_chart(fig_country, use_container_width=True,
                        theme=None, config=PLOTLY_CONFIG)
```

- [ ] **Step 4: Visual verification**

Refresh the app. Navigate through Produkte tab. Verify all three charts render and select-on-bar still works for the top-products chart.

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "refactor(app): apply polish() to Produkte tab charts"
```

---

## Task 10: Wire `polish()` into `app.py` — KI-Entscheid (Tab 5)

Check `app.py` lines 850–1206 for any remaining `st.plotly_chart` calls.

**Files:**
- Modify: `app.py`

- [ ] **Step 1: List remaining chart sites**

Run: `grep -n "st.plotly_chart" app.py`
Expected: every site found should now have `theme=None, config=PLOTLY_CONFIG`. Any site that does not is in Tab 5 (KI-Entscheid) and needs to be migrated.

- [ ] **Step 2: For each remaining site, apply the same pattern**

For every `st.plotly_chart(fig_x, use_container_width=True)` that is *not* yet using `polish`:
1. Add `fig_x = polish(fig_x, y_format=',.0f')` (use `y_format=',.0f'` as the default; choose `'£,.0f'` for currency, `'.1%'` for ratios)
2. Change the chart call to `st.plotly_chart(fig_x, use_container_width=True, theme=None, config=PLOTLY_CONFIG)`

If a chart should hide its legend (1-series chart, direct labels), add `hide_legend=True` to the `polish()` call.

- [ ] **Step 3: Verify all `st.plotly_chart` calls now use polish + config**

Run: `grep -n "st.plotly_chart" app.py | grep -v "config=PLOTLY_CONFIG"`
Expected: no output (every chart call has the polish wiring).

Also verify:

Run: `grep -c "polish(" app.py`
Expected: ≥ 14 (one polish call per chart).

- [ ] **Step 4: Visual verification**

Refresh the app. Click through all five tabs. Verify no chart raises an exception, no modebar appears anywhere, and charts visually use the new template (no vertical gridlines, faint horizontal gridlines, transparent background, dark unified hover).

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "refactor(app): apply polish() to KI-Entscheid tab charts"
```

---

## Task 11: README and developer docs

A short doc so future contributors know how to use `polish()` and the token system.

**Files:**
- Create: `src/ui/README.md`

- [ ] **Step 1: Write `src/ui/README.md`**

```markdown
# UI Foundation

Design tokens and Plotly polish layer for the Retail BI dashboard.
Implements Phase 1 of `docs/superpowers/specs/2026-05-17-dashboard-redesign-design.md`.

## Tokens

All design tokens live in `src/ui/theme.py` as Python constants
(colors, typography, spacing, radius). This file is the **single
source of truth**. Streamlit's native theme (`.streamlit/config.toml`)
is **generated** from these constants — never hand-edit `config.toml`.

```bash
# After editing theme.py, regenerate the Streamlit config:
make config
```

## Plotly polish

Every Plotly figure in the app must pass through `polish(fig, ...)` as
the last step before `st.plotly_chart`. The function applies the
registered template (transparent background, faint horizontal
gridlines, no vertical gridlines, no modebar, unified dark hover,
Okabe–Ito categorical palette) plus optional per-chart niceties.

```python
from src.ui.viz_theme import polish, PLOTLY_CONFIG

fig = px.line(df, x="month", y="revenue")
fig = polish(fig, y_format=",.0f",
             reference=target, reference_label="Ziel")

st.plotly_chart(
    fig,
    use_container_width=True,
    theme=None,                # IMPORTANT: disable Streamlit's auto-restyle
    config=PLOTLY_CONFIG,
)
```

### `polish()` options

| Parameter | Type | Purpose |
|---|---|---|
| `dark` | bool | Apply `polish_dark` instead of `polish_light` |
| `y_format` | str | Plotly tickformat (`",.0f"`, `"£,.0f"`, `".1%"`) |
| `reference` | float | Dotted reference line at this y value |
| `reference_label` | str | Annotation text for the reference line |
| `hide_legend` | bool | Force-hide the legend (for charts with direct labels) |

### `PLOTLY_CONFIG`

Pass `config=PLOTLY_CONFIG` to every `st.plotly_chart` call.
This hides the modebar and the Plotly logo, enables responsive
sizing, and disables scroll-zoom.
```

- [ ] **Step 2: Commit**

```bash
git add src/ui/README.md
git commit -m "docs(ui): explain the design-token + polish() workflow"
```

---

## Task 12: CI guard — fail if `config.toml` is out of sync

Prevents silent drift: if someone edits `theme.py` and forgets to run `make config`, this test fails.

**Files:**
- Modify: `tests/test_render_streamlit_config.py`

- [ ] **Step 1: Append the drift test**

Append to `tests/test_render_streamlit_config.py`:

```python
def test_committed_config_matches_current_theme():
    """If this fails, run `make config` and commit the result."""
    expected = gen.render()
    actual = (gen.PROJECT_ROOT / ".streamlit" / "config.toml").read_text()
    assert actual == expected, (
        "Committed .streamlit/config.toml is out of date.\n"
        "Run `make config` and commit the regenerated file."
    )
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_render_streamlit_config.py::test_committed_config_matches_current_theme -v`
Expected: PASS (we just generated it in Task 3).

- [ ] **Step 3: Confirm it catches drift**

Edit `src/ui/theme.py` and temporarily change `PRIMARY = "#6C5CE7"` to `PRIMARY = "#000000"`. Run the test. Expected: FAIL with the helpful message.

Revert the theme.py edit (do **not** commit the black-primary value).

- [ ] **Step 4: Commit**

```bash
git add tests/test_render_streamlit_config.py
git commit -m "test(ui): guard against drift between theme.py and config.toml"
```

---

## Task 13: Full test sweep + final smoke test

Catch any regressions one last time.

- [ ] **Step 1: Run the full test suite**

Run: `pytest tests/ -v`
Expected: all tests pass — both the new tests added in this phase and the pre-existing tests for `decision_agent`, `decision_log`, `agent_chat`, `critic`.

If any pre-existing test fails, investigate before continuing — it may indicate that the Streamlit version bump broke something unrelated.

- [ ] **Step 2: Manual smoke**

Run: `streamlit run app.py`
Walk through all 5 tabs. For each, confirm:
- Page loads without exception (check terminal for tracebacks)
- All charts render
- No modebar appears on any chart
- Hover shows the dark unified tooltip
- Font has changed to Inter (visible difference from before)

- [ ] **Step 3: Compare against the "before" screenshots**

The `screenshot-tab*.png` files in the repo root are the pre-redesign baseline. Open each tab in the running app and compare visually against the corresponding screenshot. You should observe:
- Same data, same layout
- Cleaner chart styling (no gridlines on x, only faint y, no modebar)
- Inter font instead of default
- Transparent chart backgrounds — charts blend into the page

No code change is needed in this step; this is the human checkpoint that Phase 1 actually achieved its goal.

- [ ] **Step 4: Final commit (if any cleanup needed)**

If you made any tweaks during the smoke test, commit them. Otherwise skip.

```bash
# only if there are changes:
git status
git add <files>
git commit -m "chore(ui): smoke-test cleanup"
```

---

## Definition of Done — Phase 1

All of the following must be true:

- [ ] `pytest tests/` is green
- [ ] `streamlit run app.py` runs without exceptions on any tab
- [ ] `grep -c "polish(" app.py` returns ≥ 14
- [ ] No `st.plotly_chart` call in `app.py` is missing `theme=None` + `config=PLOTLY_CONFIG`
- [ ] `.streamlit/config.toml` is committed and matches the output of `make config`
- [ ] `src/ui/README.md` exists and describes how to use `polish()` + token edits
- [ ] All commits are atomic per task

## What's Next (Phase 2 preview)

Phase 2 will introduce the `kpi_card()` helper and replace the four overview `st.metric` calls. Phase 3 then restructures `app.py` around a sidebar + page-dispatch architecture. The work in this plan is intentionally non-disruptive — it does not change navigation, layout, or any component library, so it can ship independently and the visual win is already meaningful.
