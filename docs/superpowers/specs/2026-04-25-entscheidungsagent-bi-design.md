# Design Spec: BI Entscheidungsagent — Online Retail II

**Datum:** 2026-04-25  
**Student:** Sheyla Sampietro  
**Kurs:** Business Intelligence  
**Abgabe:** ~1 Woche vor Prüfung  
**Umfang:** ~10 Seiten Solo-Projekt

---

## Ziel

Ein interaktives BI-Dashboard mit integriertem KI-Entscheidungsagenten für einen UK-basierten Online-Retailer. Der Agent analysiert Umsatz, Kundensegmente und Produktperformance und leitet daraus konkrete Managemententscheide ab.

---

## Dataset

**Online Retail II** (UCI ML Repository)  
- 2 Sheets: Year 2009-2010 (525k Zeilen), Year 2010-2011 (542k Zeilen)  
- 8 Spalten: Invoice, StockCode, Description, Quantity, InvoiceDate, Price, Customer ID, Country  
- ~1.07 Mio. Transaktionen total, UK-basierter Geschenkartikel-Shop

---

## Tech Stack

| Schicht | Tool |
|---|---|
| Datenverarbeitung | Python + Pandas |
| Visualisierung | Plotly |
| Dashboard | Streamlit |
| Forecasting | Prophet (Facebook) |
| Versionierung | GitHub |

---

## Architektur

```
Excel (online_retail_II.xlsx)
    ↓
Pandas (Bereinigung, Feature Engineering)
    ↓
┌─────────────────────────────────────────┐
│  Analyse-Schicht                        │
│  ├── Prophet → Umsatz-Forecast          │
│  ├── RFM → Kundensegmentierung          │
│  └── Produkt-Analyse → Performance      │
└─────────────────────────────────────────┘
    ↓
KI-Entscheidungsagent (regelbasiert)
    ↓
Streamlit Dashboard (5 Tabs)
```

---

## Dashboard — 5 Tabs

### Tab 1: Übersicht (Executive View)
- 4 KPI-Kacheln: Gesamtumsatz, Aktive Kunden, Bestellungen, Forecast-Delta
- Mini-Umsatz-Trendchart
- Mini-Kundensegment-Balken
- KI-Alert-Box (kompakte Empfehlung)

### Tab 2: Umsatz-Forecast
- Historischer Monatsumsatz (Liniendiagramm)
- Prophet-Forecast für 3 Monate mit Konfidenzintervall
- Saisonalitäts-Decomposition (Trend / Woche / Jahr)

### Tab 3: Kunden RFM
- RFM-Segmentierung: Champions, Loyal, At Risk, Lost, New
- Scatter Plot: Recency vs. Frequency (Farbe = Segment)
- Tabelle: Anzahl Kunden pro Segment + Umsatzanteil

### Tab 4: Produkt-Performance
- Top 10 Produkte nach Umsatz (Balkendiagramm)
- Bottom 10 Produkte: 3 Monate rückläufig
- Umsatz nach Kategorie / Land

### Tab 5: KI-Entscheid
- Vollständige strukturierte Empfehlung
- Begründung (welche Daten führten zum Entscheid)
- Priorität: Hoch / Mittel / Tief
- Konkrete Massnahmen

---

## KI-Entscheidungslogik

Regelbasierter Agent, der alle drei Analysen kombiniert:

```
WENN  Forecast < Vormonat um > 5%
UND   At-Risk-Kunden-Anteil > 20%
DANN  → Reaktivierungskampagne für At-Risk-Segment (Priorität: HOCH)

WENN  Produkt hat ≥ 3 Monate sinkenden Umsatz
UND   Monats-Umsatz < 50% des Produktdurchschnitts
DANN  → Produkt aus Sortiment nehmen (Priorität: MITTEL)

WENN  Champion-Kunden-Anteil steigt
UND   Forecast ≥ 0%
DANN  → Kein Handlungsbedarf (Priorität: TIEF)
```

Jede Empfehlung enthält:
- **Befund**: Was die Daten zeigen
- **Entscheid**: Konkrete Massnahme
- **Begründung**: Welche Metriken den Entscheid ausgelöst haben
- **Priorität**: Hoch / Mittel / Tief

---

## GitHub Repo-Struktur

```
entscheidungsagent-bi/
├── data/
│   └── online_retail_II.xlsx
├── src/
│   ├── data_processing.py
│   ├── forecasting.py
│   ├── rfm_analysis.py
│   ├── product_analysis.py
│   └── decision_agent.py
├── app.py
├── requirements.txt
├── README.md
└── docs/
    └── report.pdf
```

---

## Abgrenzung (nicht im Scope)

- Kein LLM/Chat-Interface (Ansatz 3 wurde bewusst weggelassen)
- Keine Datenbankanbindung (Excel als Datenquelle reicht)
- Kein Cloud-Deployment (lokal lauffähig reicht für Abgabe)
