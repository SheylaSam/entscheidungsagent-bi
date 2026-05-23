# Report Updates — Anpassungen für die docx-Datei

Diese Datei enthält alle Textblöcke, die in den Word-Report eingefügt oder ersetzt werden müssen, damit der Report den aktuellen Stand des Codes widerspiegelt (Utility-Score, Chat-Agent, Learning Loop).

Jeder Block ist klar markiert mit `[ERSETZE …]` oder `[NEU EINFÜGEN nach …]`.
Reihenfolge: erst die kapitelweisen Updates, dann zwei komplett neue Kapitel.

---

## 1) [ERSETZE] Management Summary (S. III)

> Diese Arbeit realisiert ein interaktives Business-Intelligence-Dashboard mit einem **mehrstufig aufgebauten KI-Entscheidungsagenten** für den Online Retail II Datensatz — 1.07 Millionen Transaktionen eines britischen Online-Geschenkshops aus den Jahren 2009 bis 2011. Das System leitet aus den Daten **priorisierte, nutzenbasierte Handlungsempfehlungen** für das Management ab. Im Kern arbeiten sechs deterministisch geprüfte Regeln; jede Empfehlung wird zusätzlich mit einem **numerischen Utility-Score in £** (erwarteter Geschäftsimpact × Dringlichkeit × Konfidenz) bewertet und nach Nutzen sortiert. Die Empfehlung trägt damit eine quantifizierte Geschäftsgrundlage, nicht nur ein kategorisches Prioritätslabel.
>
> Über diesen deterministischen Kern legt das Projekt **zwei lernfreundliche Erweiterungen**: (1) einen **Natural-Language-Chat-Agent** auf Basis eines lokalen Ollama-Modells, der Tools deterministisch aufruft und so die Folie-33-Architektur (User Request → Reasoning Engine → Tool Selection → Execute → Observe → Answer) 1:1 umsetzt, sowie (2) eine **Kritik-Komponente** als Read-only-Lern-Loop, die aus dem Decision-Log Vorschläge für Schwellwert-Anpassungen ableitet (Russell & Norvig, lernender Agent, Vorlesung Woche 12).
>
> Die Architektur folgt dem 5-Layer-Prinzip aus Vorlesung Woche 10 (Datenquellen, Data Platform, Semantic Layer, AI Analytics Layer, Decision Layer). Theoretisch deckt der Agent damit **alle fünf Stufen der Russell-&-Norvig-Klassifikation** ab — von modellbasiert-zielbasiert über nutzenbasiert bis lernend. Tech-Stack: Python, Streamlit, SQLite, Prophet, Ollama (lokal). 80 automatisierte Tests, ein persistenter JSON-Entscheidungslog mit getrenntem Outcome-Log, Human-in-the-Loop-Guardrails und ein sichtbarer Agent-Trace sichern Auditierbarkeit, Reproduzierbarkeit und Verantwortlichkeit ab.

---

## 2) [ERSETZE] Kapitel 3.1 «Einordnung»

> Vorlesung Woche 12 klassifiziert intelligente Agenten nach Russell & Norvig in fünf Stufen: einfache Reflex-Agenten, modellbasierte Reflex-Agenten, modellbasierte zielbasierte Agenten, **modellbasierte nutzenbasierte Agenten** und **lernende Agenten**. Der hier umgesetzte Agent deckt — bewusst gestaffelt — die drei höheren Stufen ab:
>
> - **Modellbasiert + zielbasiert** (Stufe 3): Sein internes «Modell der Umgebung» besteht aus den sechs Regeln und Schwellwerten in `src/semantic.py`; sein Ziel — definiert im Code als «Priorisierte BI-Entscheidung für Management vorbereiten» — leitet alle Aktionen.
> - **Nutzenbasiert** (Stufe 4): Jede Regel berechnet zusätzlich einen **Utility-Score in £** als Produkt aus erwartetem Geschäftsimpact, Dringlichkeit und Konfidenz (`UtilityScore` in `src/semantic.py`). Empfehlungen werden nach diesem Score sortiert. Eine Empfehlung der Kategorie HOCH mit £30'000 Risiko rangiert damit vor einer MITTEL-Empfehlung mit £2'000 — eine Differenzierung, die ein rein zielbasierter Agent nicht leisten könnte (vgl. Folie 17, «Modellbasierte, nutzenbasierte Agenten»).
> - **Lernend** (Stufe 5): Eine separate Kritik-Komponente (`src/critic.py`) liest persistierte Agent-Läufe und Entscheidungs-Outcomes (Freigegeben/Abgelehnt/Zurückgestellt) und schlägt Schwellwert-Anpassungen vor. Sie folgt der in Folie 18 dargestellten Schleife «Kritik → Lernelement → Leistungselement» und ist bewusst **read-only** umgesetzt: Der Agent passt sich nicht selbst an, sondern macht datenbasierte Vorschläge für den Anwender. So bleibt Reproduzierbarkeit erhalten — bei gleichzeitiger struktureller Erfüllung der Lern-Loop-Definition.
>
> Vorlesung Woche 11 bietet eine zweite Perspektive entlang der Achsen Autonomie und Nutzerinteraktion. Der Kern-Agent ist ein **Decision Recommendation System**: niedrige Autonomie, analytisch, vorbereitet statt ausführt. Über den **Natural-Language-Chat-Layer** (Kapitel 4.4) erweitert das System diese Einordnung um eine **Chatbot-/Copilot-Komponente** (Folie 32 «Agentic AI in BI») — ohne dabei die deterministische Reproduzierbarkeit des Kerns aufzugeben, weil das LLM ausschliesslich Tools aufruft und nicht selbst rechnet.

---

## 3) [ERSETZE] Kapitel 3.2 «Warum regelbasiert statt LLM-basiert?» → neu **«Warum regelbasierter Kern + LLM-Layer drumherum?»**

> Vorlesung Woche 5 formuliert eine Goldene Regel der Modellierung: «Beginnen Sie mit einem deterministischen Modell — und fügen Sie Stochastik nur hinzu, wenn die Unsicherheit entscheidend ist.» Diese Regel begründet den Aufbau in **zwei Schichten**:
>
> **Schicht 1 — deterministischer Kern.** Sechs Regeln + Utility-Scoring sind in `src/decision_agent.py` als reine Python-Funktionen implementiert. Gleicher Input erzeugt jederzeit den gleichen Output. Drei Argumente sind hier zentral:
>
> 1. **Reproduzierbarkeit** — gleicher Input erzeugt jederzeit den gleichen Output. Genau das, was Woche 5 als unnötige Stochastik beschreibt, wenn man es in den Kern legt.
> 2. **Auditierbarkeit** — jede Regel hat eine explizite Bedingung; die Begründung jeder Empfehlung nennt die konkreten Datenpunkte. Der persistente Entscheidungslog (`logs/agent_runs/`) macht jeden Lauf retrospektiv prüfbar — exakt die «Entscheidungslog mit Nachvollziehbarkeit» aus Woche 10.
> 3. **Kostenprofil** — keine API-Aufrufe für die Empfehlungslogik, kein Halluzinationsrisiko in der Entscheidungssubstanz.
>
> **Schicht 2 — LLM-Layer als Sprach-Interface.** Über dem Kern liegt ein optionaler Chat-Agent (`src/agent_chat.py`, Kapitel 4.4), der ein lokales Ollama-Modell als Reasoning Engine nutzt. Das LLM **wählt aus sieben definierten Tools** das passende aus und übersetzt das deterministische Tool-Ergebnis in eine deutsche Antwort. **Die Substanz der Entscheidung bleibt deterministisch — das LLM ist nur der Sprach-Übersetzer.** Damit wird die in Folie 32 («Stufen Agentic AI») skizzierte Leiter Chatbot → Tool Calling → Agent Loop → Memory praktisch implementiert, ohne die Reproduzierbarkeitsanforderung aus Woche 5 aufzugeben.
>
> Diese Zwei-Schichten-Logik adressiert zugleich das «Black-Box-Problem» (Vorlesung Woche 7): Der Anwender bekommt eine natürlichsprachliche Antwort, kann aber jederzeit über den sichtbaren Trace die exakten Tool-Ergebnisse einsehen — vorne Sprache, hinten Determinismus.

---

## 4) [ERSETZE] Kapitel 3.3 «Bausteine»

> Vorlesung Woche 11 nennt fünf Grundbausteine eines Agenten: Ziel, Modell, Tools, Memory und Guardrails. Im implementierten System lassen sich diese Bausteine konkret den Code-Modulen zuordnen — mit den seit der ersten Iteration hinzugekommenen Erweiterungen klar gekennzeichnet:
>
> - **Ziel** — fest definiert in `build_agent_run()` als «Priorisierte BI-Entscheidung für Management vorbereiten».
> - **Modell** — deterministische Regel-Engine (`src/decision_agent.py`). Jede Regel ist eine eigene Funktion (`_rule_forecast_at_risk`, `_rule_declining_products` …) und konsumiert das gleiche KPI-Dictionary aus `compute_agent_kpis()`. **Erweiterung:** Jede Regel berechnet zusätzlich einen `UtilityScore` (Folie 17, nutzenbasierte Agenten).
> - **Tools** — die «Werkzeuge» des Agenten sind die analytischen Module: `rfm_analysis`, `forecasting`, `product_analysis`. **Erweiterung:** Sieben dieser Funktionen sind zusätzlich als formale Tools für den Chat-Agent registriert (`src/agent_chat.py`, Folie 36, «Tool Definition»), so dass das LLM sie kontrolliert aufrufen kann.
> - **Memory** — kurzfristig im Streamlit Session State, langfristig als JSON-Archiv unter `logs/agent_runs/<run_id>.json`. **Erweiterung:** Ein separates Outcome-Log (`logs/agent_runs/<run_id>.outcome.json`) speichert die manuelle Management-Freigabe — Voraussetzung für den Lern-Loop (Kapitel 4.5).
> - **Guardrails** — als Funktion `evaluate_guardrails()` implementiert. Drei datenqualitative Guardrails sind blockierend; ein Prozess-Guardrail (Human-in-the-Loop) markiert hochpriorisierte Empfehlungen als freigabepflichtig — entsprechend der Forderung aus Woche 10: «Menschen behalten finale Entscheidungsverantwortung.»

---

## 5) [ERSETZE] Kapitel 3.4 «Die 6 Entscheidungsregeln» — Tabelle erweitern

Bestehende Tabelle bleibt, aber **neue Spalte «Utility-Berechnung»** rechts anhängen:

| # | Bedingung | Entscheid | Priorität | **Utility-Berechnung** |
|---|---|---|---|---|
| 1 | Forecast < −5 % UND At-Risk-Anteil > 20 % | Reaktivierungskampagne starten | HOCH | |Δ%| × Baseline × 6 Mt × Konfidenz |
| 2 | ≥ 1 Produkt mit ≥ 3 Mt Rückgang und < 50 % Ø | Sortiment bereinigen | MITTEL | Σ(Ø − letzter Monat) × 12 × 0.8 |
| 3 | Champion-Anteil < 10 % | Kundenbindungsprogramm | MITTEL | Gap × Kundenzahl × Ø-Monetary × 0.7 |
| 4 | Neukunden-Anteil < 5 % | Neukundenakquisition | MITTEL | Gap × Kundenzahl × Ø-Monetary × 0.5 × 0.6 |
| 5 | Top-20 % > 80 % Umsatz | Klumpenrisiko reduzieren | MITTEL | Top20-Anteil × Gesamtumsatz × 0.2 × 0.9 |
| 6 | Keine Regel zutreffend | Kein Handlungsbedarf | TIEF | 0 |

**Ergänzungssatz nach der Tabelle:**

> Der Utility-Score ist als annualisierter Geschäftsimpact in £ formuliert, multipliziert mit Dringlichkeit (0–1) und Konfidenz (0–1). Damit lassen sich Empfehlungen unterschiedlicher Regeln nicht nur kategorisch (HOCH/MITTEL/TIEF), sondern **quantitativ ranken** — Folie 17 («Modellbasierte, nutzenbasierte Agenten»). Beispiel: Eine HOCH-Empfehlung mit £30'000 Risiko rangiert vor einer MITTEL-Empfehlung mit £2'000.

---

## 6) [NEU EINFÜGEN nach Kapitel 4.3] — Kapitel 4.4 «Natural-Language-Layer mit Tool Calling»

> Folie 32 («Stufen Agentic AI») skizziert die Leiter Chatbot → Tool Calling → Agent Loop → Multi-Agent → Memory → Autonomous Workflow. Der deterministische Kern des Projekts hat bereits Tools (Folie 36, «Tool Definition»), Memory (Decision-Log) und Guardrails. Um die Brücke zu einem **agentischen Sprach-Interface** zu schlagen, ist in `src/agent_chat.py` ein zusätzlicher Chat-Layer implementiert, der die in den Folien 35–42 dargestellte Architektur 1:1 umsetzt:
>
> ```
> User Request → Reasoning Engine (LLM, lokal) → Tool Selection → Execute Tool → Observe Result → Answer
> ```
>
> **LLM-Wahl: lokal statt API.** Als Reasoning Engine kommt **Ollama mit dem Modell `llama3.2` lokal auf dem Laptop** zum Einsatz (Folie 41, «Option A: komplett gratis & lokal mit Ollama»). Drei Gründe:
> - **Datenschutz** — Geschäftsdaten verlassen das System nicht. Direkte Antwort auf die in Folie 28 erhobene Mitarbeitersorge «Personal privacy» und «Data leaks».
> - **Kosten** — keine API-Gebühren.
> - **Reproduzierbarkeit** — der Tool-Output bleibt deterministisch; das LLM übersetzt nur in Sprache.
>
> **Tool-Definition.** Sieben Tools sind als Python-Funktionen registriert: `top_recommendation`, `list_recommendations`, `forecast_summary`, `customer_breakdown`, `declining_products`, `kpi_snapshot`, `guardrails_status`. Alle Tools rufen die deterministische Kernlogik auf und geben strukturierte JSON-Resultate zurück.
>
> **Agent-Loop.** Der Loop folgt dem in Folie 36 genannten Kernkonzept «Think → Act → Observe → Repeat»:
> 1. **Think** — System-Prompt + Userfrage werden an das LLM geschickt. Das LLM antwortet im Format `THOUGHT: …\nACTION: tool_name()` (Folie 42, «Antwortformat»).
> 2. **Act** — der Tool-Name wird per Regex extrahiert. Unbekannte Tool-Namen werden abgelehnt.
> 3. **Observe** — das gewählte Tool wird ausgeführt; das strukturierte Resultat wird an das LLM zurückgegeben.
> 4. **Answer** — das LLM synthetisiert eine deutsche Antwort in maximal drei Sätzen.
>
> **Sichtbarer Trace.** Im Dashboard (Tab «Chat-Agent») wird der vollständige Trace ausgeklappt angezeigt — Thought, gewähltes Tool, Tool-Output (JSON), finale Antwort. Damit kann der Anwender die natürlichsprachliche Antwort jederzeit gegen die deterministischen Tool-Resultate prüfen — die in Folie 28 formulierte Sorge «Inaccuracy» wird konstruktiv adressiert.
>
> **Halluzinationsrisiko und Mitigation.** Da das LLM ausschliesslich auf strukturierte Tool-Outputs zugreift und alle Tools ohne Argumente aufgerufen werden, kann es keine Datenpunkte erfinden. Theoretisch verbleibt ein Restrisiko bei der Antwort-Synthese (Folie 28, «Inaccuracy» mit 50 % Mitarbeitersorge). Drei strukturelle Mitigationen:
> - keine Tool-Argumente → keine erfundenen Parameter
> - sichtbarer Trace → manuell überprüfbare Antwort
> - 3-Sätze-Cap → wenig Spielraum für freie Formulierung

---

## 7) [NEU EINFÜGEN nach Kapitel 4.4] — Kapitel 4.5 «Lern-Loop: die Kritik-Komponente»

> Russell & Norvig (Vorlesung Woche 12, Folie 18) definieren den lernenden Agenten als höchste Stufe der Klassifikation: «Diese Agenten können aus Erfahrung lernen und ihr Verhalten anpassen.» Folie 18 zeigt die zugehörige Loop: **Kritik → Lernelement → Leistungselement → Problemgenerator.**
>
> Das Projekt schliesst diese Loop **read-only** ab: Die Komponente `src/critic.py` liest alle persistierten Agent-Läufe und die zugehörigen Entscheidungs-Outcomes (Freigegeben/Zurückgestellt/Abgelehnt) und leitet daraus diagnostische Statistiken sowie konkrete Vorschläge für Schwellwert-Anpassungen ab. Drei Heuristiken sind implementiert:
>
> 1. **High-Rejection-Heuristik.** Werden HOCH-Empfehlungen wiederholt zurückgestellt oder abgelehnt, schlägt der Critic einen strengeren Forecast-Decline-Schwellwert vor. Begründung: Der aktuelle Schwellwert produziert offenbar zu viele False-Positives.
> 2. **No-Action-Dominanz.** Sind über 70 % aller Läufe «kein Handlungsbedarf», schlägt der Critic einen sensibleren At-Risk-Schwellwert vor — relevante Signale werden möglicherweise nicht erkannt.
> 3. **Utility-Drift.** Wenn der durchschnittliche Top-Utility-Score sich über die Zeit deutlich verändert hat, wird darauf hingewiesen — ohne konkreten Schwellwert-Vorschlag, weil die Ursache (verändertes Risikoprofil vs. Datenproblem) menschlich beurteilt werden muss.
>
> **Warum read-only und nicht auto-adapt?** Folie 18 zeigt das Lern-Element grundsätzlich als selbst-anpassend. Im BI-Kontext wäre eine **automatische** Schwellwert-Anpassung jedoch problematisch:
> - Reproduzierbarkeit bricht — gleicher Datensatz, unterschiedliche Empfehlungen je nach Lernzustand.
> - Auditierbarkeit leidet — der zentrale Wert des Kerns geht verloren.
>
> Die hier gewählte Read-only-Variante erfüllt die Russell-&-Norvig-Definition strukturell (Kritik, Lernelement, Vorschlag), behält aber die Kontrolle beim Menschen. Diese Designentscheidung folgt dem in Vorlesung Woche 10 formulierten Prinzip «Menschen behalten finale Entscheidungsverantwortung» — auch über das Verhalten des Agenten selbst.

---

## 8) [ERSETZE] Kapitel 5.1 «5 Tabs im Überblick» → neu **«6 Tabs im Überblick»**

Bisherige fünf Tabs bleiben, danach einfügen:

> **Tab 6 — Chat-Agent**
>
> Natürlichsprachliches Sprach-Interface zum deterministischen Kern. Der Anwender stellt eine Frage in Deutsch (z. B. «Was sollten wir diesen Monat tun?»); das lokale LLM wählt das passende Tool, ruft die Kernlogik auf und gibt eine drei-Sätze-Antwort zurück. Der vollständige Agent-Trace ist ausklappbar sichtbar.
>
> *Abbildung 6: Tab 6 — Chat-Agent mit sichtbarem Tool-Trace*

---

## 9) [ERSETZE] Kapitel 5.3 «Qualitätssicherung»

Im ersten Bullet-Punkt **«62 automatisierte pytest-Tests»** → **«80 automatisierte pytest-Tests»**, und ergänze:

> Hinzugekommen sind Tests für den Utility-Score (Sortierung, Komponenten-Existenz, Bewertung von No-Action), den Chat-Agent (Tool-Parser, Tool-Ausführung, Loop mit Fake-LLM ohne Ollama-Abhängigkeit) und die Kritik-Komponente (Suggestion-Heuristiken, Outcome-Persistenz).

---

## 10) [ERSETZE] Kapitel 6.1 «Stärken & Grenzen des regelbasierten Ansatzes» — letzten Absatz **«Grenzen»** ersetzen

> **Grenzen** — der Agent kann nur das erkennen, was in den sechs Regeln kodifiziert ist. Unbekannte Muster werden nicht entdeckt. Die Schwellwerte sind heuristisch und müssten in einer realen Anwendung iterativ kalibriert werden. Die in Kapitel 4.5 beschriebene Read-only-Lernschleife ist ein erster strukturierter Schritt in diese Richtung, ersetzt aber kein echtes adaptives Modell (z. B. ML-gestützte Anomalie-Erkennung). Auch der LLM-Layer hat klare Grenzen: Bei kleinen lokalen Modellen (llama3.2) sind subtile Fehler in der Antwort-Synthese — falsche Zahlenrundung, vertauschte Richtung, gemischte Einheiten — möglich. Der sichtbare Trace mindert dieses Risiko, eliminiert es aber nicht. In einer Produktionsumgebung wäre ein grösseres Modell oder ein Number-Guard (Regex-Check, dass jede Zahl in der Antwort im Tool-Output vorkommt) sinnvoll.

---

## 11) [ERSETZE] Kapitel 6.2 «Datenqualität, Governance, Halluzinationsrisiko» — Halluzinationsabsatz

> **Halluzinationsrisiko.** Im **deterministischen Kern**: null — keine generierten Texte, sondern vordefinierte Templates mit konkreten KPI-Zahlen. Im **LLM-Layer**: real, aber strukturell eingegrenzt durch (a) Tool-Calling ohne Argumente, (b) sichtbaren Agent-Trace im Dashboard und (c) lokale Ausführung, die zumindest die in Folie 28 genannten Sorgen «Data Leaks» und «Cybersecurity» adressiert. Folie 28 zeigt, dass **50 % der US-Beschäftigten Inaccuracy als Sorge bei GenAI nennen** — die hier gewählte Zwei-Schichten-Architektur reagiert direkt darauf: Sprachliche Form vom LLM, substanzielle Zahlen aus dem deterministischen Kern.

---

## 12) [ERSETZE] Kapitel 7 «Fazit & Ausblick» — Schluss-Absatz

> Vorlesung Woche 1 nennt als Vorteil von Intelligence Systems: «Many alternatives considered ⇒ More accurate conclusions ⇒ Effective and timely decisions.» Genau dies leistet das umgesetzte System auf seinem abgegrenzten Anwendungsfeld: Aus drei komplementären Analysen werden alternative Befunde erhoben, mit einem Utility-Score quantitativ verglichen und in eine priorisierte Entscheidungsvorlage verdichtet. Das Projekt zeigt, dass **die Spannung zwischen Determinismus und agentischer Sprachfähigkeit** nicht durch Verzicht auf eine Seite, sondern durch eine **klare Schichtung** auflösbar ist: regelbasierter Kern für die Substanz, LLM-Layer für die Sprache, Critic-Loop für die Lernfähigkeit. Die in Vorlesung Woche 10 vorgestellten fünf Layers sind im Code direkt wiedererkennbar; die in Folie 32 skizzierte Agentic-AI-Leiter ist bis zur Stufe Memory praktisch implementiert. Mögliche Erweiterungen für eine reale Anwendung: ein Multi-Agent-System mit spezialisierten Sub-Agenten pro Domäne (Forecast, Kunde, Produkt) gemäss Folie 47–49, ein Number-Guard-Postprozessor für den LLM-Layer sowie ein produktives Monitoring der Schwellwert-Drift über mehrere Quartale.

---

## 13) [ERSETZE] Architektur-Diagramm in Kapitel 4.1

Bisheriges ASCII-Diagramm um die zwei neuen Module ergänzen:

```
data/online_retail_II.xlsx (UCI Datenquelle)
        │
        ▼
src/data_processing.py — Cleaning, SQLite-Aufbau, Helper für SQL-Filter
        │
        ▼
data/retail.db (SQLite, indiziert auf invoice_date / country)
        │
        ▼
  ┌─────────────────┬─────────────────┬─────────────────┐
  │ rfm_analysis.py │ forecasting.py  │ product_analysis│
  │ Segmentierung   │ Prophet 3M FC   │ Trendanalyse    │
  └────────┬────────┴────────┬────────┴────────┬────────┘
           └─────────────────┴─────────────────┘
                             ▼
          src/semantic.py (Schwellwerte, Segmente, UtilityScore)
                             ▼
          src/decision_agent.py — KPIs, Guardrails, 6 Regeln + Utility-Sort
                             ▼
          src/decision_log.py → logs/agent_runs/<run_id>.json
                              + <run_id>.outcome.json (Human-in-the-Loop)
                             ▼
   ┌─────────────────────────┼─────────────────────────┐
   ▼                         ▼                         ▼
src/agent_chat.py        src/critic.py            app.py
(Ollama Tool-Calling,    (Read-only Lern-Loop,    (Streamlit, 6 Tabs,
 Folie 35-42)             Folie 18)                Live-Schwellwerte)
```

---

## 14) [ERWEITERN] Mapping-Tabelle (komplett neue Tabelle als Anhang oder am Ende von Kapitel 3)

Diese Tabelle ist ein **didaktisch starker Block**, der dem Dozenten in einer Tabelle zeigt: jeder Folien-Inhalt → konkrete Implementierung. Empfehlung: Direkt nach Kapitel 3.1 einfügen oder als Anhang B.

| Folie / Vorlesung | Konzept | Realisierung im Projekt |
|---|---|---|
| W10 5-Layer-Architektur | Datenquellen → Decision Layer | `data/` → `data_processing` → `semantic` → analytische Module → `decision_agent` |
| W11 5 Bausteine | Ziel, Modell, Tools, Memory, Guardrails | siehe Kapitel 3.3 |
| W12 / Folie 14 | Einfache Reflex-Agenten | bewusst nicht — Agent stützt sich auf Historie |
| W12 / Folie 15 | Modellbasierte Reflex-Agenten | Regelbasis als internes Modell |
| W12 / Folie 16 | Modellbasierte, zielbasierte Agenten | Ziel «Priorisierte BI-Entscheidung vorbereiten» |
| W12 / Folie 17 | Modellbasierte, **nutzenbasierte** Agenten | `UtilityScore` (Impact × Dringlichkeit × Konfidenz) |
| W12 / Folie 18 | **Lernende** Agenten | `critic.py` (read-only Lern-Loop) |
| W12 / Folie 28 | GenAI-Sorgen (Privacy, Inaccuracy) | Lokales Ollama, sichtbarer Trace, Number-Guard als Ausblick |
| W12 / Folie 32 | Agentic-AI-Stufen | Chatbot → Tool Calling → Agent Loop → Memory: alle implementiert |
| W12 / Folie 33 | Architektur eines Agenten | User Request → Reasoning Engine → Tool → Observe → Answer in `agent_chat.py` |
| W12 / Folie 35–40 | Tool-Calling-Code-Pattern | `TOOLS`-Dict + `parse_action` + Agent-Loop |
| W12 / Folie 41–42 | Ollama-Variante | `_ollama_chat` mit System-Prompt im THOUGHT/ACTION-Format |
| W10 «6 AI-BI-Regeln» | erklärbare Empfehlungen, KPIs zentral, Audit-Log | Befund/Begründung, `semantic.py`, `decision_log.py` |

---

## Reihenfolge zur Bearbeitung (empfohlen)

1. Management Summary ersetzen (Block 1)
2. Kapitel 3.1, 3.2, 3.3, 3.4 ersetzen (Blöcke 2–5)
3. Neue Kapitel 4.4 und 4.5 einfügen (Blöcke 6–7)
4. Tab-Liste und Qualitätssicherung anpassen (Blöcke 8–9)
5. Reflexion und Fazit (Blöcke 10–12)
6. Architektur-Diagramm + Mapping-Tabelle (Blöcke 13–14)

Geschätzter Aufwand im Word-Dokument: **45–60 Minuten** reine Copy-Paste-Arbeit, plus eventuell 15 Minuten Korrekturlesen am Stück.
