import pandas as pd


def generate_recommendations(forecast_df, rfm_df, declining_df):
    recommendations = []
    actuals = forecast_df.iloc[:-3] if len(forecast_df) > 3 else forecast_df
    last_actual = actuals['yhat'].iloc[-1]
    next_forecast = forecast_df['yhat'].iloc[-1]
    pct_change = (next_forecast - last_actual) / last_actual if last_actual > 0 else 0
    at_risk_share = (rfm_df['segment'] == 'At Risk').sum() / len(rfm_df) if len(rfm_df) > 0 else 0

    if pct_change < -0.05 and at_risk_share > 0.20:
        at_risk_count = (rfm_df['segment'] == 'At Risk').sum()
        recommendations.append({
            'priority': 'HOCH',
            'finding': f'Umsatz-Forecast zeigt {pct_change:.1%} Rückgang nächsten Monat.',
            'decision': 'Reaktivierungskampagne für At-Risk-Kunden starten.',
            'reasoning': f'{at_risk_count} Kunden ({at_risk_share:.1%}) im Segment "At Risk" — kombiniert mit sinkendem Forecast erhöht sich Abwanderungsrisiko.',
        })

    if len(declining_df) > 0:
        product_list = ', '.join(declining_df['description'].head(5).tolist())
        recommendations.append({
            'priority': 'MITTEL',
            'finding': f'{len(declining_df)} Produkte zeigen ≥3 Monate rückläufigen Umsatz.',
            'decision': 'Sortiment bereinigen: betroffene Produkte prüfen und ggf. absetzen.',
            'reasoning': f'Betroffene Produkte: {product_list}.',
        })

    if not recommendations:
        champion_share = (rfm_df['segment'] == 'Champions').sum() / len(rfm_df) if len(rfm_df) > 0 else 0
        recommendations.append({
            'priority': 'TIEF',
            'finding': f'Forecast stabil ({pct_change:+.1%}). Champion-Anteil: {champion_share:.1%}.',
            'decision': 'Kein unmittelbarer Handlungsbedarf.',
            'reasoning': 'Alle KPIs im grünen Bereich. Reguläre Erfolgskontrolle genügt.',
        })

    return recommendations
