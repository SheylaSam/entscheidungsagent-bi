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
