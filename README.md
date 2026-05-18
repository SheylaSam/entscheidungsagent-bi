# Entscheidungsagent-BI

Regelbasiertes Business-Intelligence-Dashboard mit KI-Entscheidungsagent für den Online Retail II Datensatz — entwickelt als Abschlussprojekt eines BI-Kurses.

---

## Dataset

**Online Retail II** — UCI Machine Learning Repository
- Link: https://archive.ics.uci.edu/dataset/502/online+retail+ii
- 1.07 Millionen Transaktionen eines britischen Online-Geschenkshops (2009–2011)
- Enthält: InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country

---

## Quickstart

```bash
git clone <repo-url>
cd Entscheidungsagent-BI
pip install -r requirements.txt
streamlit run app.py
```

Das Dashboard ist danach unter http://localhost:8501 erreichbar.

Beim **ersten Start** lädt die App den Online-Retail-II-Datensatz automatisch
vom UCI ML Repository herunter (~45 MB, ~30–90 Sekunden). Danach steht
ein lokaler SQLite-Snapshot unter `data/retail.db` zur Verfügung — alle
weiteren Starts sind sofort verfügbar.

**Eigene Daten:** Auf der Seite *Datenquelle* (Sidebar → System) kannst
du eine andere Excel-Datei im selben Online-Retail-II-Schema hochladen
und die aktive Datenbank ersetzen.

---

## Tech-Entscheide

### Python + Streamlit statt R + Shiny

| Kriterium | Python + Streamlit | R + Shiny |
|---|---|---|
| KI-Bibliotheken | Prophet, scikit-learn nativ verfügbar | Wrapper mit Einschränkungen |
| Einheitliche Pipeline | Datenverarbeitung, Modell und UI in einer Sprache | Sprachgrenze zwischen Analyse und App |
| Kurskonsistenz | Week 08 verwendete Python (SimpleAutoencoder.py, Prophet) | Neues Toolset nötig |
| Boilerplate | Minimal — eine Datei reicht fur ein Dashboard | Reaktives Programmiermodell, mehr Setup |
| Portfolio-Relevanz | Python ist Industriestandard fur Data Science und MLOps | Nischenanwendung im akademischen Umfeld |

### SQLite statt MySQL/PostgreSQL

- **Portabel**: Die gesamte Datenbank ist eine einzige `.db`-Datei — kein Server, keine Konfiguration.
- **Auto-generiert**: `build_database()` erstellt und befüllt die DB beim ersten `streamlit run app.py`.
- **Ausreichend**: Fur ein Read-only BI-Dashboard mit einem Datensatz dieser Grösse ist SQLite vollständig ausreichend — keine parallelen Schreibzugriffe nötig.

---

## Architektur

```
Excel (.xlsx)
     |
     v
data_processing.py  ──►  SQLite (.db)
                               |
                               v
                           Pandas DataFrames
                          /        |        \
                         v         v         v
               rfm_analysis  forecasting  product_analysis
               (Segmente)    (Prophet)    (Top/Declining)
                          \        |        /
                           v       v       v
                         decision_agent.py
                         (Regelbasierter KI-Agent)
                               |
                               v
                           app.py
                     (Streamlit Dashboard)
```

---

## Dashboard-Struktur

Die Navigation läuft über eine Sidebar mit drei Gruppen — *Analytics*, *Agent*, *System*.

| Gruppe | Seite | Inhalt |
|---|---|---|
| Analytics | Übersicht | Vier KPI-Karten (Gesamtumsatz, aktive Kunden, At-Risk-Kunden, Forecast) mit Sparkline und Δ%-Vergleich; Umsatz-Trend; Kundensegmente; Top-KI-Empfehlung |
| Analytics | Forecast | 3-Monats-Ausblick (Prophet, piecewise-linear) mit wählbarer Vergleichsbasis, Unsicherheitsband und Backtest-Modellgüte |
| Analytics | Kunden | RFM-Scatter (Recency × Frequency, Grösse = Monetary); Segmenttabelle; Top-10-At-Risk-Liste; Segmente nach Land |
| Analytics | Produkte | Top-N-Produkte nach Umsatz; signifikant rückläufige Produkte (≥3 Monate Rückgang + letzter Monat < 50 % Durchschnitt); Produkt-Drilldown |
| Agent | Empfehlungen | Alle Agent-Empfehlungen als Karten mit Befund, Entscheid, Begründung, Evidence-Drilldown (Regel-Tag, Nutzen-Score, betroffene Kunden/Produkte) sowie Akzeptieren/Verwerfen/👍/👎 |
| Agent | Verlauf | Persistierter Entscheidungs-Log (JSON) mit Outcome-Metriken aus der Critic-Komponente |
| Agent | Chat | Natural-Language-Chat mit Suggestion-Chips, der die Tools des Agenten deterministisch aufruft |
| System | Datenquelle | UCI-Auto-Download für den Standard-Datensatz, plus Upload eines eigenen Datensatzes im selben Schema |
| System | Einstellungen | Schwellwerte und Service-Aktionen |

---

## KI-Entscheidungslogik

Der Entscheidungsagent (`src/decision_agent.py`) kombiniert drei Datenquellen und wendet regelbasierte Logik an:

| Regel | Bedingung | Entscheid | Priorität |
|---|---|---|---|
| R1 | Forecast < -5% UND At-Risk-Anteil > 20% der Kundenbasis | Reaktivierungskampagne für At-Risk-Kunden starten | HOCH |
| R2 | ≥1 Produkt mit ≥3 Monaten rückläufigem Umsatz | Sortiment bereinigen: betroffene Produkte prüfen und ggf. absetzen | MITTEL |
| R3 | Champion-Anteil < 10% der Kundenbasis | Kundenbindungsprogramm aufbauen: Loyal-Kunden zu Champions entwickeln | MITTEL |
| R4 | Neukunden-Anteil < 5% der Kundenbasis | Neukundenakquisition ausbauen: Marketing-Kanäle und Erstbestellangebote prüfen | MITTEL |
| R5 | Top-20%-Kunden generieren >80% des Umsatzes | Kundenstamm diversifizieren: Abhängigkeit von Schlüsselkunden reduzieren | MITTEL |
| R6 | Keine der obigen Regeln trifft zu | Kein unmittelbarer Handlungsbedarf | TIEF |

Die Regeln werden sequenziell geprüft; mehrere Empfehlungen (z.B. R1 + R2 + R3 gleichzeitig) sind möglich. Jede Empfehlung enthält **Befund**, **Entscheid**, **Begründung** sowie einen Regel-Tag, einen Utility-Score und — wo es Sinn ergibt — eine Evidence-Tabelle mit den konkret betroffenen Kunden bzw. Produkten.

Die Standard-Schwellwerte sind im Code als `AgentThresholds` dokumentiert. R1 kann im Dashboard live angepasst werden; die übrigen Regeln bleiben bewusst deterministisch, damit Empfehlungen reproduzierbar und auditierbar bleiben.

Zusätzlich erzeugt `generate_agent_run()` einen auditierbaren Agentenlauf mit:

- **Agentic Trace**: Planung, KPI-Semantik, Datenqualitätsprüfung, Forecast-Bewertung, Risikoanalyse und Synthese.
- **Evidence Layer**: strukturierte Kennzahlen wie Vergleichsumsatz, Forecast-Abweichung, At-Risk-Anteil, rückläufige Produkte und Top-20-Umsatzanteil.
- **Guardrails**: Mindestdatenbasis, Forecast-Plausibilität, vorhandene Zukunftsmonate und Human-in-the-Loop-Pflicht.
- **Memory / Entscheidungslog**: Management-Entscheide können in der Streamlit-Session protokolliert und als JSON exportiert werden.

---

## Qualitätssicherung

```bash
pytest -q
```

Aktueller Stand: **194 Tests** über Datenbereinigung, RFM, Forecasting, Produktfilter, Länderlogik, Entscheidungsregeln, Agent-Run-Metadaten, Datensatz-Upload, UI-Komponenten (Karten, Theme, Navigation, Agent-Panel, Chat) und Page-Smoke-Tests.
