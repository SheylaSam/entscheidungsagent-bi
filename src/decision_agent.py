import pandas as pd
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AgentThresholds:
    forecast_decline: float = -0.05
    at_risk_share: float = 0.20
    declining_product_share: float = 0.50
    champion_share: float = 0.10
    new_customer_share: float = 0.05
    top_customer_revenue_share: float = 0.80


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
        'significant_declining': significant_declining,
    }


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

    guardrails = [
        {
            'name': 'Mindestdatenbasis Kunden',
            'status': 'pass' if customer_count >= 10 else 'warn',
            'detail': f'{customer_count} Kunden im aktuellen Filter',
        },
        {
            'name': 'Forecast-Zukunftsmonat vorhanden',
            'status': 'pass' if forecast_ctx['next_forecast'] is not None else 'fail',
            'detail': f"{forecast_ctx['future_months']} zukünftige Forecast-Monate",
        },
        {
            'name': 'Forecast nicht negativ',
            'status': 'pass' if (forecast_ctx['next_forecast'] is None or forecast_ctx['next_forecast'] >= 0) else 'warn',
            'detail': 'Negative Umsatzprognosen werden als nicht plausibel markiert',
        },
        {
            'name': 'Human-in-the-Loop',
            'status': 'required' if recommendations and recommendations[0]['priority'] in {'HOCH', 'MITTEL'} else 'optional',
            'detail': 'Management-Freigabe vor operativer Umsetzung',
        },
    ]

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
            'output': recommendations[0]['decision'] if recommendations else 'Keine Empfehlung erzeugt.',
        },
    ]

    approval_required = any(g['name'] == 'Human-in-the-Loop' and g['status'] == 'required' for g in guardrails)
    return {
        'run_id': datetime.utcnow().strftime('%Y%m%d%H%M%S'),
        'goal': 'Priorisierte BI-Entscheidung fuer Management vorbereiten',
        'agent_type': 'Regelbasierter BI-Agent mit Human-in-the-Loop',
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
    recommendations = []

    if kpis['customer_count'] < 10:
        recommendations.append({
            'priority': 'MITTEL',
            'finding': f"Datenbasis zu dünn: nur {kpis['customer_count']} Kunden im gewählten Zeitraum/Land.",
            'decision': 'Filter anpassen oder breiteren Zeitraum wählen.',
            'reasoning': 'Für eine zuverlässige Analyse werden mindestens 10 Kunden benötigt. Empfehlungen auf Basis weniger Datenpunkte sind statistisch nicht belastbar.',
        })
        return recommendations

    forecast_ctx = kpis['forecast']
    last_actual = forecast_ctx['baseline']
    next_forecast = forecast_ctx['next_forecast']
    pct_change = forecast_ctx['pct_change']

    if next_forecast is None or last_actual is None or last_actual <= 0:
        return recommendations

    if next_forecast < 0:
        recommendations.append({
            'priority': 'MITTEL',
            'finding': f'Prophet-Forecast liefert negativen Umsatz (£{next_forecast:,.0f}) — nicht plausibel.',
            'decision': 'Datenbasis prüfen: zu wenige Monate oder zu wenig Umsatz für zuverlässige Prognose.',
            'reasoning': 'Ein negativer Forecast deutet auf unzureichende Datenmenge hin. Für einen belastbaren Forecast werden mindestens 6 Monate Umsatzdaten empfohlen.',
        })
        return recommendations

    if pct_change is not None and pct_change < thresholds.forecast_decline and kpis['at_risk_share'] > thresholds.at_risk_share:
        recommendations.append({
            'priority': 'HOCH',
            'finding': f'Umsatz-Forecast zeigt {pct_change:.1%} Rückgang nächsten Monat.',
            'decision': 'Reaktivierungskampagne für At-Risk-Kunden starten.',
            'reasoning': f"{kpis['at_risk_count']} Kunden ({kpis['at_risk_share']:.1%}) im Segment \"At Risk\" — kombiniert mit sinkendem Forecast erhöht sich Abwanderungsrisiko.",
        })

    significant_declining = kpis['significant_declining']
    if len(significant_declining) > 0:
        product_list = ', '.join(significant_declining['description'].head(5).tolist())
        recommendations.append({
            'priority': 'MITTEL',
            'finding': f'{len(significant_declining)} Produkte zeigen ≥3 Monate rückläufigen Umsatz und Monatsumsatz < 50% des Produktdurchschnitts.',
            'decision': 'Sortiment bereinigen: betroffene Produkte prüfen und ggf. absetzen.',
            'reasoning': f'Betroffene Produkte: {product_list}.',
        })

    if kpis['champion_share'] < thresholds.champion_share:
        recommendations.append({
            'priority': 'MITTEL',
            'finding': f"Champion-Anteil zu niedrig: nur {kpis['champion_share']:.1%} der Kunden sind Top-Käufer ({kpis['champion_count']} Personen).",
            'decision': 'Kundenbindungsprogramm aufbauen: Loyal-Kunden aktiv zu Champions entwickeln.',
            'reasoning': 'Ein gesunder Kundenstamm hat typischerweise 15–25% Champions. Darunter fehlt die Basis für stabile Wiederholungsumsätze.',
        })

    if kpis['new_share'] < thresholds.new_customer_share:
        recommendations.append({
            'priority': 'MITTEL',
            'finding': f"Neukunden-Anteil kritisch niedrig: nur {kpis['new_share']:.1%} der Kunden sind Neukunden ({kpis['new_count']} Personen).",
            'decision': 'Neukundenakquisition prüfen: Marketing-Kanäle und Erstbestellangebote ausbauen.',
            'reasoning': 'Ohne kontinuierlichen Neukunden-Zufluss schrumpft der Kundenstamm langfristig, da bestehende Kunden natürlich abwandern.',
        })

    if kpis['top20_share'] > thresholds.top_customer_revenue_share:
        recommendations.append({
            'priority': 'MITTEL',
            'finding': f"Klumpenrisiko: Top 20% der Kunden generieren {kpis['top20_share']:.0%} des Umsatzes.",
            'decision': 'Kundenstamm diversifizieren: Abhängigkeit von wenigen Schlüsselkunden reduzieren.',
            'reasoning': 'Hohe Umsatzkonzentration bedeutet hohes Risiko — der Verlust weniger Grosskunden kann den Gesamtumsatz stark beeinflussen.',
        })

    if not recommendations:
        pct_str = f"{pct_change:+.1%}" if pct_change is not None else "n/a"
        recommendations.append({
            'priority': 'TIEF',
            'finding': f"Forecast: {pct_str}. Champion-Anteil: {kpis['champion_share']:.1%}.",
            'decision': 'Kein unmittelbarer Handlungsbedarf.',
            'reasoning': 'Alle KPIs im grünen Bereich. Reguläre Erfolgskontrolle genügt.',
        })

    return recommendations
