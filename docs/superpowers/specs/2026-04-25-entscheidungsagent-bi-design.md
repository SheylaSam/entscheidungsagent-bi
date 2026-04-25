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
| Rohdaten | Excel (online_retail_II.xlsx) |
| Datenbank | SQLite (siehe Entscheid unten) |
| Datenverarbeitung | Python + Pandas |
| Visualisierung | Plotly |
| Dashboard | Streamlit |
| Forecasting | Prophet (Facebook) |
| Versionierung | GitHub |

### Datenbankentscheid: SQLite statt MySQL

Der Kurs verwendete MySQL (inkl. `MysqlConnector.py`). Für dieses Projekt wurde bewusst **SQLite** gewählt, weil:

1. **Portabilität**: SQLite ist eine einzige `.db`-Datei, kein Datenbankserver nötig. Jeder kann das Repo clonen und direkt starten.
2. **Reproduzierbarkeit**: MySQL erfordert Server-Installation und manuellen Import — SQLite wird automatisch beim ersten Start aus dem Excel befüllt.
3. **Scope-Angemessenheit**: Für ein Read-only BI-Dashboard ohne Concurrent Writes ist SQLite die richtige Wahl. MySQL würde künstliche Komplexität einführen ohne Mehrwert.

Das Prinzip (SQL-Queries, relationales Modell, DB-Abstraktionsschicht) ist identisch — nur die Engine ist leichtgewichtiger.

---

## Architektur

```
Excel (online_retail_II.xlsx)
    ↓ (einmaliger Import beim ersten Start)
SQLite Datenbank (retail.db)
    ↓ (SQL-Queries)
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
│   ├── online_retail_II.xlsx     # Rohdaten (via .gitignore ausgeschlossen, Download-Link in README)
│   └── retail.db                 # SQLite DB (auto-generiert beim ersten Start)
├── src/
│   ├── data_processing.py        # Excel → SQLite Import + Bereinigung
│   ├── forecasting.py            # Prophet Zeitreihe
│   ├── rfm_analysis.py           # RFM Segmentierung
│   ├── product_analysis.py       # Produkt-Performance
│   └── decision_agent.py         # Entscheidungsregeln & Empfehlungen
├── app.py                        # Streamlit Hauptapp (5 Tabs)
├── requirements.txt
├── .gitignore
├── README.md                     # Setup-Anleitung + Screenshots + Datenbankentscheid
└── docs/
    ├── superpowers/specs/        # Design-Dokumente
    └── report.pdf                # ~10-seitiger Bericht
```

---

## Abgrenzung (nicht im Scope)

- Kein LLM/Chat-Interface (Ansatz 3 wurde bewusst weggelassen)
- Kein MySQL-Server (SQLite reicht, siehe Datenbankentscheid)
- Kein Cloud-Deployment (lokal lauffähig reicht für Abgabe)
