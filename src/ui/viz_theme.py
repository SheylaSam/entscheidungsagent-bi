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
                      size=theme.FONT_SIZES_PX["BODY"] - 1,
                      color=text),
            title=dict(
                font=dict(family=theme.HEADING_FAMILY,
                          size=theme.FONT_SIZES_PX["CARD_H2"],
                          color=theme.HEADING if not dark else "#F1F5F9"),
                x=0, xanchor="left", pad=dict(t=4, b=12),
            ),
            margin=dict(l=80, r=16, t=56, b=40),
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
                title=dict(text=""),
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
