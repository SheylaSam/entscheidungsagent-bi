"""Semantic Layer — single source of truth for KPI definitions and thresholds.

The Week-11 lecture's 5-layer BI-AI reference architecture places a Semantic
Layer between the Data Platform and the AI Analytics / Decision layers. Its job
is to give every consumer (dashboard, agent, downstream models) the same
definitions of what a KPI or a customer segment means, so different layers
cannot drift.

This module owns the canonical definitions; rfm_analysis, product_analysis and
decision_agent re-export from here for backward compatibility.
"""

from dataclasses import dataclass

import pandas as pd


# ── Decision thresholds ──────────────────────────────────────────────────────
# Used by the rule engine and the dashboard rule-status panel.
@dataclass(frozen=True)
class AgentThresholds:
    forecast_decline: float = -0.05
    at_risk_share: float = 0.20
    declining_product_share: float = 0.50
    champion_share: float = 0.10
    new_customer_share: float = 0.05
    top_customer_revenue_share: float = 0.80


# ── Customer segment definitions (RFM) ───────────────────────────────────────
# r = recency score 1–5 (5 = most recent), f = frequency score 1–5.
def assign_segment(row: pd.Series) -> str:
    r, f = row['r_score'], row['f_score']
    if r == 5 and f >= 4:
        return 'Champions'
    if f >= 3 and r >= 3:
        return 'Loyal'
    if r <= 2 and f >= 3:
        return 'At Risk'
    if r == 1 and f <= 2:
        return 'Lost'
    if r >= 4 and f == 1:
        return 'New'
    return 'Others'


SEGMENT_NAMES = ('Champions', 'Loyal', 'At Risk', 'Lost', 'New', 'Others')


# ── Product taxonomy ─────────────────────────────────────────────────────────
# Stock codes / descriptions that represent fees, postage or accounting
# adjustments rather than sellable products.
NON_PRODUCT_STOCK_CODES = frozenset({
    'POST',
    'POSTAGE',
    'BANK CHARGES',
    'C2',
    'D',
    'DOT',
    'M',
    'PADS',
})
