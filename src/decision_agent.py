import pandas as pd
from datetime import datetime, timezone

from src.semantic import AgentThresholds, UtilityScore  # re-exported for backward compatibility

__all__ = [
    'AgentThresholds',
    'UtilityScore',
    'compute_agent_kpis',
    'evaluate_guardrails',
    'build_agent_run',
    'generate_agent_run',
    'generate_recommendations',
]


def _make_rec(priority: str, finding: str, decision: str, reasoning: str, utility: UtilityScore) -> dict:
    return {
        'priority': priority,
        'finding': finding,
        'decision': decision,
        'reasoning': reasoning,
        'utility': utility.score,
        'utility_components': {
            'expected_impact_gbp': utility.expected_impact_gbp,
            'urgency': utility.urgency,
            'confidence': utility.confidence,
        },
    }


def _forecast_context(forecast_df, actuals_df=None, comparison_value: float | None = None) -> dict:
    if actuals_df is not None and not actuals_df.empty:
        baseline = comparison_value if comparison_value is not None else actuals_df['y'].iloc[-1]
        future = forecast_df[forecast_df['ds'] > actuals_df['ds'].max()]
        next_forecast = None if future.empty else future['yhat'].iloc[0]
    else:
        history = forecast_df.iloc[:-3] if len(forecast_df) > 3 else forecast_df.iloc[:-1]
        future = forecast_df.tail(3) if len(forecast_df) > 3 else forecast_df.tail(1)
        baseline = None if history.empty else history['yhat'].iloc[-1]
        next_forecast = None if future.empty else future['yhat'].iloc[0]

    pct_change = None
    if baseline is not None and baseline > 0 and next_forecast is not None:
        pct_change = (next_forecast - baseline) / baseline

    return {
        'baseline': baseline,
        'next_forecast': next_forecast,
        'pct_change': pct_change,
        'future_months': len(future),
    }


def compute_agent_kpis(
    forecast_df,
    rfm_df,
    declining_df,
    thresholds: AgentThresholds | None = None,
    actuals_df=None,
    comparison_value: float | None = None,
) -> dict:
    """Single source of truth for the KPIs the agent layers consume.

    build_agent_run, generate_recommendations and the dashboard rule status
    panel all read from this dict, so KPIs cannot drift between layers.
    """
    if thresholds is None:
        thresholds = AgentThresholds()

    forecast_ctx = _forecast_context(forecast_df, actuals_df, comparison_value)
    customer_count = len(rfm_df)
    actual_months = 0 if actuals_df is None else len(actuals_df)

    if customer_count:
        at_risk_count = int((rfm_df['segment'] == 'At Risk').sum())
        champion_count = int((rfm_df['segment'] == 'Champions').sum())
        new_count = int((rfm_df['segment'] == 'New').sum())
    else:
        at_risk_count = champion_count = new_count = 0

    at_risk_share = at_risk_count / customer_count if customer_count else 0.0
    champion_share = champion_count / customer_count if customer_count else 0.0
    new_share = new_count / customer_count if customer_count else 0.0

    total_monetary = float(rfm_df['monetary'].sum()) if customer_count else 0.0
    avg_monetary = total_monetary / customer_count if customer_count else 0.0

    if customer_count >= 5 and rfm_df['monetary'].sum() > 0:
        top_n = max(1, int(customer_count * 0.2))
        top20_share = float(
            rfm_df['monetary'].sort_values(ascending=False).head(top_n).sum()
            / rfm_df['monetary'].sum()
        )
    else:
        top20_share = 0.0

    if 'revenue_avg' in declining_df.columns and len(declining_df) > 0:
        significant_declining = declining_df[
            declining_df['revenue_last_month']
            < declining_df['revenue_avg'] * thresholds.declining_product_share
        ]
    else:
        significant_declining = declining_df

    return {
        'thresholds': thresholds,
        'forecast': forecast_ctx,
        'customer_count': customer_count,
        'actual_months': actual_months,
        'at_risk_count': at_risk_count,
        'at_risk_share': at_risk_share,
        'champion_count': champion_count,
        'champion_share': champion_share,
        'new_count': new_count,
        'new_share': new_share,
        'top20_share': top20_share,
        'total_monetary': total_monetary,
        'avg_monetary': avg_monetary,
        'significant_declining': significant_declining,
    }


# ── Guardrails ───────────────────────────────────────────────────────────────
# Guardrails are computed once and consumed by both generate_recommendations
# (to enforce blocking conditions) and build_agent_run (to record status in the
# trace). The `blocks` flag distinguishes hard-stops (data unusable, return
# fallback rec) from soft signals (Human-in-the-Loop is required but does not
# prevent recommendation generation).

GUARDRAIL_MIN_CUSTOMERS = 'Mindestdatenbasis Kunden'
GUARDRAIL_FORECAST_PRESENT = 'Forecast-Zukunftsmonat vorhanden'
GUARDRAIL_FORECAST_NON_NEGATIVE = 'Forecast nicht negativ'
GUARDRAIL_HUMAN_APPROVAL = 'Human-in-the-Loop'


def evaluate_guardrails(kpis: dict, recommendations: list[dict] | None = None) -> list[dict]:
    """Return data-quality and process guardrails for a single agent run."""
    forecast_ctx = kpis['forecast']
    customer_count = kpis['customer_count']
    next_forecast = forecast_ctx['next_forecast']
    has_baseline = forecast_ctx['baseline'] is not None and forecast_ctx['baseline'] > 0

    guardrails = [
        {
            'name': GUARDRAIL_MIN_CUSTOMERS,
            'status': 'pass' if customer_count >= 10 else 'warn',
            'detail': f'{customer_count} Kunden im aktuellen Filter',
            'blocks': customer_count < 10,
        },
        {
            'name': GUARDRAIL_FORECAST_PRESENT,
            'status': 'pass' if (next_forecast is not None and has_baseline) else 'fail',
            'detail': f"{forecast_ctx['future_months']} zukünftige Forecast-Monate",
            'blocks': next_forecast is None or not has_baseline,
        },
        {
            'name': GUARDRAIL_FORECAST_NON_NEGATIVE,
            'status': 'pass' if (next_forecast is None or next_forecast >= 0) else 'warn',
            'detail': 'Negative Umsatzprognosen werden als nicht plausibel markiert',
            'blocks': next_forecast is not None and next_forecast < 0,
        },
    ]

    needs_approval = bool(recommendations) and recommendations[0]['priority'] in {'HOCH', 'MITTEL'}
    guardrails.append({
        'name': GUARDRAIL_HUMAN_APPROVAL,
        'status': 'required' if needs_approval else 'optional',
        'detail': 'Management-Freigabe vor operativer Umsetzung',
        'blocks': False,
    })
    return guardrails


def _guardrail(guardrails: list[dict], name: str) -> dict | None:
    return next((g for g in guardrails if g['name'] == name), None)


# ── Per-rule recommendation builders ─────────────────────────────────────────
# Each rule consumes the same KPI dict and returns a recommendation or None.
# Splitting them mirrors the rule table in the report 1:1 and keeps each
# rule's condition + finding + reasoning collocated.

def _forecast_confidence(actual_months: int) -> float:
    # Prophet typically needs 12+ months for reliable trend separation; below that, scale linearly.
    return min(1.0, actual_months / 12.0) if actual_months else 0.5


def _rule_forecast_at_risk(kpis: dict, thresholds: AgentThresholds) -> dict | None:
    pct_change = kpis['forecast']['pct_change']
    baseline = kpis['forecast']['baseline'] or 0.0
    if pct_change is None or pct_change >= thresholds.forecast_decline:
        return None
    if kpis['at_risk_share'] <= thresholds.at_risk_share:
        return None
    # Project the monthly decline over the next 6 months (conservative half-year horizon).
    expected_impact = abs(pct_change) * baseline * 6
    utility = UtilityScore(
        expected_impact_gbp=expected_impact,
        urgency=1.0,
        confidence=_forecast_confidence(kpis['actual_months']),
    )
    return _make_rec(
        priority='HOCH',
        finding=f'Umsatz-Forecast zeigt {pct_change:.1%} Rückgang nächsten Monat.',
        decision='Reaktivierungskampagne für At-Risk-Kunden starten.',
        reasoning=(
            f"{kpis['at_risk_count']} Kunden ({kpis['at_risk_share']:.1%}) im Segment "
            f"\"At Risk\" — kombiniert mit sinkendem Forecast erhöht sich Abwanderungsrisiko."
        ),
        utility=utility,
    )


def _rule_declining_products(kpis: dict, thresholds: AgentThresholds) -> dict | None:
    significant = kpis['significant_declining']
    if len(significant) == 0:
        return None
    monthly_loss = float((significant['revenue_avg'] - significant['revenue_last_month']).sum())
    expected_impact = monthly_loss * 12
    utility = UtilityScore(expected_impact_gbp=expected_impact, urgency=0.7, confidence=0.8)
    product_list = ', '.join(significant['description'].head(5).tolist())
    return _make_rec(
        priority='MITTEL',
        finding=(
            f'{len(significant)} Produkte zeigen ≥3 Monate rückläufigen Umsatz und '
            f'Monatsumsatz < {int(thresholds.declining_product_share * 100)}% des Produktdurchschnitts.'
        ),
        decision='Sortiment bereinigen: betroffene Produkte prüfen und ggf. absetzen.',
        reasoning=f'Betroffene Produkte: {product_list}.',
        utility=utility,
    )


def _rule_low_champion_share(kpis: dict, thresholds: AgentThresholds) -> dict | None:
    if kpis['champion_share'] >= thresholds.champion_share:
        return None
    gap = thresholds.champion_share - kpis['champion_share']
    expected_impact = gap * kpis['customer_count'] * kpis['avg_monetary']
    utility = UtilityScore(expected_impact_gbp=expected_impact, urgency=0.4, confidence=0.7)
    return _make_rec(
        priority='MITTEL',
        finding=(
            f"Champion-Anteil zu niedrig: nur {kpis['champion_share']:.1%} der Kunden sind "
            f"Top-Käufer ({kpis['champion_count']} Personen)."
        ),
        decision='Kundenbindungsprogramm aufbauen: Loyal-Kunden aktiv zu Champions entwickeln.',
        reasoning='Ein gesunder Kundenstamm hat typischerweise 15–25% Champions. Darunter fehlt die Basis für stabile Wiederholungsumsätze.',
        utility=utility,
    )


def _rule_low_new_customers(kpis: dict, thresholds: AgentThresholds) -> dict | None:
    if kpis['new_share'] >= thresholds.new_customer_share:
        return None
    gap = thresholds.new_customer_share - kpis['new_share']
    # Neukunden tragen anfangs weniger als Champions — halber Gewichtungsfaktor.
    expected_impact = gap * kpis['customer_count'] * kpis['avg_monetary'] * 0.5
    utility = UtilityScore(expected_impact_gbp=expected_impact, urgency=0.4, confidence=0.6)
    return _make_rec(
        priority='MITTEL',
        finding=(
            f"Neukunden-Anteil kritisch niedrig: nur {kpis['new_share']:.1%} der Kunden sind "
            f"Neukunden ({kpis['new_count']} Personen)."
        ),
        decision='Neukundenakquisition prüfen: Marketing-Kanäle und Erstbestellangebote ausbauen.',
        reasoning='Ohne kontinuierlichen Neukunden-Zufluss schrumpft der Kundenstamm langfristig, da bestehende Kunden natürlich abwandern.',
        utility=utility,
    )


def _rule_top20_concentration(kpis: dict, thresholds: AgentThresholds) -> dict | None:
    if kpis['top20_share'] <= thresholds.top_customer_revenue_share:
        return None
    # Annahme: 20% des konzentrierten Umsatzes sind bei Abwanderung eines Grosskunden gefährdet.
    expected_impact = kpis['top20_share'] * kpis['total_monetary'] * 0.20
    utility = UtilityScore(expected_impact_gbp=expected_impact, urgency=0.5, confidence=0.9)
    return _make_rec(
        priority='MITTEL',
        finding=f"Klumpenrisiko: Top 20% der Kunden generieren {kpis['top20_share']:.0%} des Umsatzes.",
        decision='Kundenstamm diversifizieren: Abhängigkeit von wenigen Schlüsselkunden reduzieren.',
        reasoning='Hohe Umsatzkonzentration bedeutet hohes Risiko — der Verlust weniger Grosskunden kann den Gesamtumsatz stark beeinflussen.',
        utility=utility,
    )


# Order matters: highest-priority rules first.
_RULES = (
    _rule_forecast_at_risk,
    _rule_declining_products,
    _rule_low_champion_share,
    _rule_low_new_customers,
    _rule_top20_concentration,
)


# Fallback / data-quality recs carry zero utility — they short-circuit the rule
# pipeline and are always returned as single-element lists, so sorting is moot.
_ZERO_UTILITY = UtilityScore(expected_impact_gbp=0.0, urgency=0.0, confidence=1.0)


def _data_thin_recommendation(kpis: dict) -> dict:
    return _make_rec(
        priority='MITTEL',
        finding=f"Datenbasis zu dünn: nur {kpis['customer_count']} Kunden im gewählten Zeitraum/Land.",
        decision='Filter anpassen oder breiteren Zeitraum wählen.',
        reasoning='Für eine zuverlässige Analyse werden mindestens 10 Kunden benötigt. Empfehlungen auf Basis weniger Datenpunkte sind statistisch nicht belastbar.',
        utility=_ZERO_UTILITY,
    )


def _negative_forecast_recommendation(next_forecast: float) -> dict:
    return _make_rec(
        priority='MITTEL',
        finding=f'Prophet-Forecast liefert negativen Umsatz (£{next_forecast:,.0f}) — nicht plausibel.',
        decision='Datenbasis prüfen: zu wenige Monate oder zu wenig Umsatz für zuverlässige Prognose.',
        reasoning='Ein negativer Forecast deutet auf unzureichende Datenmenge hin. Für einen belastbaren Forecast werden mindestens 6 Monate Umsatzdaten empfohlen.',
        utility=_ZERO_UTILITY,
    )


def _no_action_recommendation(kpis: dict) -> dict:
    pct_change = kpis['forecast']['pct_change']
    pct_str = f"{pct_change:+.1%}" if pct_change is not None else "n/a"
    return _make_rec(
        priority='TIEF',
        finding=f"Forecast: {pct_str}. Champion-Anteil: {kpis['champion_share']:.1%}.",
        decision='Kein unmittelbarer Handlungsbedarf.',
        reasoning='Alle KPIs im grünen Bereich. Reguläre Erfolgskontrolle genügt.',
        utility=_ZERO_UTILITY,
    )


def generate_recommendations(
    forecast_df,
    rfm_df,
    declining_df,
    forecast_threshold: float = -0.05,
    at_risk_threshold: float = 0.20,
    actuals_df=None,
    comparison_value: float | None = None,
    kpis: dict | None = None,
):
    if kpis is None:
        thresholds = AgentThresholds(
            forecast_decline=forecast_threshold,
            at_risk_share=at_risk_threshold,
        )
        kpis = compute_agent_kpis(
            forecast_df, rfm_df, declining_df, thresholds, actuals_df, comparison_value
        )
    thresholds = kpis['thresholds']

    guardrails = evaluate_guardrails(kpis)

    if _guardrail(guardrails, GUARDRAIL_MIN_CUSTOMERS)['blocks']:
        return [_data_thin_recommendation(kpis)]

    if _guardrail(guardrails, GUARDRAIL_FORECAST_PRESENT)['blocks']:
        return []

    if _guardrail(guardrails, GUARDRAIL_FORECAST_NON_NEGATIVE)['blocks']:
        return [_negative_forecast_recommendation(kpis['forecast']['next_forecast'])]

    recommendations = [rule(kpis, thresholds) for rule in _RULES]
    recommendations = [r for r in recommendations if r is not None]

    if not recommendations:
        recommendations.append(_no_action_recommendation(kpis))

    # Utility-based ranking: highest expected business impact first.
    recommendations.sort(key=lambda r: r['utility'], reverse=True)
    return recommendations


def build_agent_run(
    forecast_df,
    rfm_df,
    declining_df,
    recommendations: list[dict],
    forecast_threshold: float = -0.05,
    at_risk_threshold: float = 0.20,
    actuals_df=None,
    comparison_value: float | None = None,
    kpis: dict | None = None,
) -> dict:
    """Return an auditable agent run around the deterministic recommendation logic."""
    if kpis is None:
        thresholds = AgentThresholds(
            forecast_decline=forecast_threshold,
            at_risk_share=at_risk_threshold,
        )
        kpis = compute_agent_kpis(
            forecast_df, rfm_df, declining_df, thresholds, actuals_df, comparison_value
        )

    forecast_ctx = kpis['forecast']
    customer_count = kpis['customer_count']
    actual_months = kpis['actual_months']
    at_risk_count = kpis['at_risk_count']
    significant_declining = kpis['significant_declining']

    guardrails = evaluate_guardrails(kpis, recommendations)

    top_utility = recommendations[0]['utility'] if recommendations else 0.0
    evidence = {
        'baseline_revenue': forecast_ctx['baseline'],
        'next_forecast': forecast_ctx['next_forecast'],
        'forecast_change': forecast_ctx['pct_change'],
        'customer_count': customer_count,
        'actual_months': actual_months,
        'at_risk_count': at_risk_count,
        'at_risk_share': kpis['at_risk_share'],
        'champion_share': kpis['champion_share'],
        'new_customer_share': kpis['new_share'],
        'significant_declining_products': len(significant_declining),
        'top20_revenue_share': kpis['top20_share'],
        'top_utility_gbp': top_utility,
    }

    trace = [
        {
            'step': 1,
            'name': 'Ziel interpretieren',
            'tool': 'Planner',
            'output': 'Management-Risiken erkennen und priorisierte Entscheidungsvorlage erstellen.',
        },
        {
            'step': 2,
            'name': 'KPI-Semantik laden',
            'tool': 'Semantic Layer',
            'output': 'Umsatz, Forecast, At-Risk, Champions, Neukunden und Produktumsatz konsistent definiert.',
        },
        {
            'step': 3,
            'name': 'Datenqualitaet pruefen',
            'tool': 'Guardrails',
            'output': f'{customer_count} Kunden, {actual_months} Ist-Monate, {forecast_ctx["future_months"]} Forecast-Monate.',
        },
        {
            'step': 4,
            'name': 'Forecast-Risiko bewerten',
            'tool': 'Prophet Forecast',
            'output': 'Keine belastbare Abweichung berechenbar' if forecast_ctx['pct_change'] is None else f'{forecast_ctx["pct_change"]:+.1%} gegen Vergleichsbasis.',
        },
        {
            'step': 5,
            'name': 'Kunden- und Produktrisiken pruefen',
            'tool': 'RFM + Produktanalyse',
            'output': f'{at_risk_count} At-Risk-Kunden, {len(significant_declining)} signifikant ruecklaeufige Produkte.',
        },
        {
            'step': 6,
            'name': 'Empfehlung synthetisieren',
            'tool': 'Decision Layer',
            'output': (
                f"{recommendations[0]['decision']} "
                f"(Utility ≈ £{recommendations[0]['utility']:,.0f})"
                if recommendations else 'Keine Empfehlung erzeugt.'
            ),
        },
    ]

    approval_required = any(
        g['name'] == GUARDRAIL_HUMAN_APPROVAL and g['status'] == 'required' for g in guardrails
    )
    return {
        'run_id': datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f'),
        'goal': 'Priorisierte BI-Entscheidung fuer Management vorbereiten',
        'agent_type': 'Utility-basierter BI-Agent mit Human-in-the-Loop',
        'recommendations': recommendations,
        'evidence': evidence,
        'trace': trace,
        'guardrails': guardrails,
        'approval_required': approval_required,
    }


def generate_agent_run(
    forecast_df,
    rfm_df,
    declining_df,
    forecast_threshold: float = -0.05,
    at_risk_threshold: float = 0.20,
    actuals_df=None,
    comparison_value: float | None = None,
) -> dict:
    thresholds = AgentThresholds(
        forecast_decline=forecast_threshold,
        at_risk_share=at_risk_threshold,
    )
    kpis = compute_agent_kpis(
        forecast_df, rfm_df, declining_df, thresholds, actuals_df, comparison_value
    )
    recommendations = generate_recommendations(
        forecast_df,
        rfm_df,
        declining_df,
        forecast_threshold,
        at_risk_threshold,
        actuals_df,
        comparison_value,
        kpis=kpis,
    )
    return build_agent_run(
        forecast_df,
        rfm_df,
        declining_df,
        recommendations,
        forecast_threshold,
        at_risk_threshold,
        actuals_df,
        comparison_value,
        kpis=kpis,
    )
