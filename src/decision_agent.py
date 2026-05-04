import pandas as pd
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentThresholds:
    forecast_decline: float = -0.05
    at_risk_share: float = 0.20
    declining_product_share: float = 0.50
    champion_share: float = 0.10
    new_customer_share: float = 0.05
    top_customer_revenue_share: float = 0.80


def generate_recommendations(
    forecast_df,
    rfm_df,
    declining_df,
    forecast_threshold: float = -0.05,
    at_risk_threshold: float = 0.20,
    actuals_df=None,
):
    thresholds = AgentThresholds(
        forecast_decline=forecast_threshold,
        at_risk_share=at_risk_threshold,
    )
    recommendations = []

    if len(rfm_df) < 10:
        recommendations.append({
            'priority': 'MITTEL',
            'finding': f'Datenbasis zu dünn: nur {len(rfm_df)} Kunden im gewählten Zeitraum/Land.',
            'decision': 'Filter anpassen oder breiteren Zeitraum wählen.',
            'reasoning': 'Für eine zuverlässige Analyse werden mindestens 10 Kunden benötigt. Empfehlungen auf Basis weniger Datenpunkte sind statistisch nicht belastbar.',
        })
        return recommendations

    if actuals_df is not None and not actuals_df.empty:
        last_actual = actuals_df['y'].iloc[-1]
        future = forecast_df[forecast_df['ds'] > actuals_df['ds'].max()]
        if future.empty:
            return recommendations
        next_forecast = future['yhat'].iloc[0]
    else:
        history = forecast_df.iloc[:-3] if len(forecast_df) > 3 else forecast_df.iloc[:-1]
        future = forecast_df.tail(3) if len(forecast_df) > 3 else forecast_df.tail(1)
        if history.empty or future.empty:
            return recommendations
        last_actual = history['yhat'].iloc[-1]
        next_forecast = future['yhat'].iloc[0]

    if last_actual <= 0:
        return recommendations

    pct_change = (next_forecast - last_actual) / last_actual
    at_risk_share = (rfm_df['segment'] == 'At Risk').sum() / len(rfm_df) if len(rfm_df) > 0 else 0

    if next_forecast < 0:
        recommendations.append({
            'priority': 'MITTEL',
            'finding': f'Prophet-Forecast liefert negativen Umsatz (£{next_forecast:,.0f}) — nicht plausibel.',
            'decision': 'Datenbasis prüfen: zu wenige Monate oder zu wenig Umsatz für zuverlässige Prognose.',
            'reasoning': 'Ein negativer Forecast deutet auf unzureichende Datenmenge hin. Für einen belastbaren Forecast werden mindestens 6 Monate Umsatzdaten empfohlen.',
        })
        return recommendations

    if pct_change < thresholds.forecast_decline and at_risk_share > thresholds.at_risk_share:
        at_risk_count = (rfm_df['segment'] == 'At Risk').sum()
        recommendations.append({
            'priority': 'HOCH',
            'finding': f'Umsatz-Forecast zeigt {pct_change:.1%} Rückgang nächsten Monat.',
            'decision': 'Reaktivierungskampagne für At-Risk-Kunden starten.',
            'reasoning': f'{at_risk_count} Kunden ({at_risk_share:.1%}) im Segment "At Risk" — kombiniert mit sinkendem Forecast erhöht sich Abwanderungsrisiko.',
        })

    if len(declining_df) > 0:
        if 'revenue_avg' in declining_df.columns:
            significant = declining_df[
                declining_df['revenue_last_month']
                < declining_df['revenue_avg'] * thresholds.declining_product_share
            ]
        else:
            significant = declining_df
        if len(significant) > 0:
            product_list = ', '.join(significant['description'].head(5).tolist())
            recommendations.append({
                'priority': 'MITTEL',
                'finding': f'{len(significant)} Produkte zeigen ≥3 Monate rückläufigen Umsatz und Monatsumsatz < 50% des Produktdurchschnitts.',
                'decision': 'Sortiment bereinigen: betroffene Produkte prüfen und ggf. absetzen.',
                'reasoning': f'Betroffene Produkte: {product_list}.',
            })

    champion_share = (rfm_df['segment'] == 'Champions').sum() / len(rfm_df)
    if champion_share < thresholds.champion_share:
        champion_count = (rfm_df['segment'] == 'Champions').sum()
        recommendations.append({
            'priority': 'MITTEL',
            'finding': f'Champion-Anteil zu niedrig: nur {champion_share:.1%} der Kunden sind Top-Käufer ({champion_count} Personen).',
            'decision': 'Kundenbindungsprogramm aufbauen: Loyal-Kunden aktiv zu Champions entwickeln.',
            'reasoning': 'Ein gesunder Kundenstamm hat typischerweise 15–25% Champions. Darunter fehlt die Basis für stabile Wiederholungsumsätze.',
        })

    new_share = (rfm_df['segment'] == 'New').sum() / len(rfm_df)
    if new_share < thresholds.new_customer_share:
        new_count = (rfm_df['segment'] == 'New').sum()
        recommendations.append({
            'priority': 'MITTEL',
            'finding': f'Neukunden-Anteil kritisch niedrig: nur {new_share:.1%} der Kunden sind Neukunden ({new_count} Personen).',
            'decision': 'Neukundenakquisition prüfen: Marketing-Kanäle und Erstbestellangebote ausbauen.',
            'reasoning': 'Ohne kontinuierlichen Neukunden-Zufluss schrumpft der Kundenstamm langfristig, da bestehende Kunden natürlich abwandern.',
        })

    if len(rfm_df) >= 5:
        top_n = max(1, int(len(rfm_df) * 0.2))
        sorted_monetary = rfm_df['monetary'].sort_values(ascending=False)
        top20_share = sorted_monetary.head(top_n).sum() / sorted_monetary.sum()
        if top20_share > thresholds.top_customer_revenue_share:
            recommendations.append({
                'priority': 'MITTEL',
                'finding': f'Klumpenrisiko: Top 20% der Kunden generieren {top20_share:.0%} des Umsatzes.',
                'decision': 'Kundenstamm diversifizieren: Abhängigkeit von wenigen Schlüsselkunden reduzieren.',
                'reasoning': 'Hohe Umsatzkonzentration bedeutet hohes Risiko — der Verlust weniger Grosskunden kann den Gesamtumsatz stark beeinflussen.',
            })

    if not recommendations:
        champion_share = (rfm_df['segment'] == 'Champions').sum() / len(rfm_df) if len(rfm_df) > 0 else 0
        recommendations.append({
            'priority': 'TIEF',
            'finding': f'Forecast: {pct_change:+.1%}. Champion-Anteil: {champion_share:.1%}.',
            'decision': 'Kein unmittelbarer Handlungsbedarf.',
            'reasoning': 'Alle KPIs im grünen Bereich. Reguläre Erfolgskontrolle genügt.',
        })

    return recommendations
