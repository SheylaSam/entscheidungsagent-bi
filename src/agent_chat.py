"""Natural-language chat agent with tool calling (Ollama, lokal).

Implements the slide 35-42 architecture: User Request → Reasoning Engine (LLM)
→ Tool Selection → Execute Tool → Observe Result → Answer. The Reasoning
Engine is a local Ollama model (e.g. llama3.2); tools are thin wrappers around
the existing deterministic BI pipeline (`compute_agent_kpis`,
`generate_recommendations`, forecast, RFM, declining products).

The deterministic logic stays the single source of truth. The LLM only picks
which tool to invoke and translates the structured result into a German
management answer.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable

import pandas as pd

from src.decision_agent import (
    AgentThresholds,
    compute_agent_kpis,
    evaluate_guardrails,
    generate_recommendations,
)


DEFAULT_MODEL = "llama3.2"


SYSTEM_PROMPT = """Du bist ein BI-Analyseagent für ein Retail-Dashboard.

Du hast Zugriff auf folgende Tools (jeweils ohne Argumente aufrufbar):

- top_recommendation()      → liefert die Empfehlung mit dem höchsten Utility-Score
- list_recommendations()    → liefert alle Empfehlungen sortiert nach Utility
- forecast_summary()        → liefert nächste Forecast-Werte + prozentuale Veränderung
- customer_breakdown()      → liefert Verteilung der Kundensegmente (Champions, At Risk, etc.)
- declining_products()      → liefert Liste der signifikant rückläufigen Produkte
- kpi_snapshot()            → liefert die wichtigsten KPIs (Kundenzahl, Umsatz, Shares)
- guardrails_status()       → prüft Datenqualität und Freigabeerfordernis

Regeln:
1. Antworte auf jede Userfrage in genau diesem Format:
   THOUGHT: <kurze Begründung welches Tool du brauchst>
   ACTION: tool_name() ODER none

2. Wähle das passendste einzelne Tool. Nutze `none`, wenn kein Tool nötig ist.

3. Du bekommst danach das Tool-Ergebnis und antwortest dem User auf Deutsch in maximal 3 Sätzen.
"""


# ── Tool registry ────────────────────────────────────────────────────────────


@dataclass
class AgentContext:
    """Holds the dataframes the deterministic tools operate on.

    Kept separate from the agent class so tools can be unit-tested without
    spinning up an LLM connection.
    """
    forecast_df: pd.DataFrame
    rfm_df: pd.DataFrame
    declining_df: pd.DataFrame
    actuals_df: pd.DataFrame | None = None
    comparison_value: float | None = None
    thresholds: AgentThresholds = field(default_factory=AgentThresholds)

    def kpis(self) -> dict:
        return compute_agent_kpis(
            self.forecast_df,
            self.rfm_df,
            self.declining_df,
            self.thresholds,
            self.actuals_df,
            self.comparison_value,
        )

    def recommendations(self) -> list[dict]:
        return generate_recommendations(
            self.forecast_df,
            self.rfm_df,
            self.declining_df,
            self.thresholds.forecast_decline,
            self.thresholds.at_risk_share,
            self.actuals_df,
            self.comparison_value,
        )


def tool_top_recommendation(ctx: AgentContext) -> dict:
    recs = ctx.recommendations()
    if not recs:
        return {'message': 'Keine Empfehlung erzeugt (Guardrail blockiert).'}
    top = recs[0]
    return {
        'priority': top['priority'],
        'decision': top['decision'],
        'finding': top['finding'],
        'utility_gbp': top['utility'],
    }


def tool_list_recommendations(ctx: AgentContext) -> list[dict]:
    return [
        {
            'priority': r['priority'],
            'decision': r['decision'],
            'utility_gbp': r['utility'],
        }
        for r in ctx.recommendations()
    ]


def tool_forecast_summary(ctx: AgentContext) -> dict:
    kpis = ctx.kpis()
    fc = kpis['forecast']
    return {
        'baseline_gbp': fc['baseline'],
        'next_forecast_gbp': fc['next_forecast'],
        'pct_change': fc['pct_change'],
        'future_months': fc['future_months'],
    }


def tool_customer_breakdown(ctx: AgentContext) -> dict:
    kpis = ctx.kpis()
    return {
        'total_customers': kpis['customer_count'],
        'champions': kpis['champion_count'],
        'at_risk': kpis['at_risk_count'],
        'new': kpis['new_count'],
        'champion_share': kpis['champion_share'],
        'at_risk_share': kpis['at_risk_share'],
        'new_share': kpis['new_share'],
        'top20_revenue_share': kpis['top20_share'],
    }


def tool_declining_products(ctx: AgentContext) -> list[dict]:
    significant = ctx.kpis()['significant_declining']
    if len(significant) == 0:
        return []
    return [
        {
            'stock_code': row.get('stock_code', ''),
            'description': row.get('description', ''),
            'revenue_avg': float(row['revenue_avg']),
            'revenue_last_month': float(row['revenue_last_month']),
        }
        for _, row in significant.head(10).iterrows()
    ]


def tool_kpi_snapshot(ctx: AgentContext) -> dict:
    kpis = ctx.kpis()
    return {
        'customer_count': kpis['customer_count'],
        'actual_months': kpis['actual_months'],
        'total_revenue_gbp': kpis['total_monetary'],
        'avg_customer_revenue_gbp': kpis['avg_monetary'],
        'forecast_pct_change': kpis['forecast']['pct_change'],
    }


def tool_guardrails_status(ctx: AgentContext) -> list[dict]:
    return [
        {'name': g['name'], 'status': g['status'], 'detail': g['detail'], 'blocks': g['blocks']}
        for g in evaluate_guardrails(ctx.kpis())
    ]


TOOLS: dict[str, Callable[[AgentContext], Any]] = {
    'top_recommendation': tool_top_recommendation,
    'list_recommendations': tool_list_recommendations,
    'forecast_summary': tool_forecast_summary,
    'customer_breakdown': tool_customer_breakdown,
    'declining_products': tool_declining_products,
    'kpi_snapshot': tool_kpi_snapshot,
    'guardrails_status': tool_guardrails_status,
}


# ── LLM agent loop ───────────────────────────────────────────────────────────


_ACTION_RE = re.compile(r'ACTION\s*:\s*([a-zA-Z_]+)\s*\(\s*\)', re.IGNORECASE)
_THOUGHT_RE = re.compile(r'THOUGHT\s*:\s*(.+?)(?:\n|$)', re.IGNORECASE | re.DOTALL)


def parse_action(text: str) -> tuple[str, str | None]:
    """Extract THOUGHT and tool name from the LLM's first turn output.

    Returns (thought, tool_name_or_none). Kept as a pure function so we can
    unit-test the parser without calling Ollama.
    """
    thought_match = _THOUGHT_RE.search(text)
    thought = thought_match.group(1).strip() if thought_match else text.strip()

    action_match = _ACTION_RE.search(text)
    if not action_match:
        return thought, None
    name = action_match.group(1).lower()
    if name == 'none' or name not in TOOLS:
        return thought, None
    return thought, name


class OllamaNotAvailable(RuntimeError):
    pass


def _ollama_chat(model: str, prompt: str) -> str:
    """Thin wrapper so tests can monkey-patch this single call."""
    try:
        import ollama  # type: ignore
    except ImportError as exc:
        raise OllamaNotAvailable(
            'Das Python-Paket `ollama` ist nicht installiert. Bitte `pip install ollama` ausführen '
            'und Ollama lokal starten (https://ollama.com).'
        ) from exc
    response = ollama.chat(
        model=model,
        messages=[{'role': 'user', 'content': prompt}],
    )
    return response['message']['content']


@dataclass
class ChatResult:
    answer: str
    trace: list[dict]


class AAIAgent:
    """Local-LLM agent that picks a tool, observes the result and answers in German."""

    def __init__(
        self,
        context: AgentContext,
        model: str = DEFAULT_MODEL,
        llm_call: Callable[[str, str], str] | None = None,
    ):
        self.context = context
        self.model = model
        self._llm_call = llm_call or _ollama_chat

    def chat(self, user_question: str) -> ChatResult:
        trace: list[dict] = []

        # Step 1: Think — let the LLM pick a tool.
        first_prompt = f"{SYSTEM_PROMPT}\n\nUSER FRAGE:\n{user_question}\n"
        first_reply = self._llm_call(self.model, first_prompt)
        thought, tool_name = parse_action(first_reply)
        trace.append({'step': 'think', 'thought': thought, 'tool': tool_name or 'none'})

        # Step 2: Act + Observe — run the tool if one was selected.
        if tool_name is None:
            trace.append({'step': 'observe', 'output': 'Kein Tool aufgerufen.'})
            return ChatResult(answer=first_reply.strip(), trace=trace)

        observation = TOOLS[tool_name](self.context)
        trace.append({'step': 'act', 'tool': tool_name, 'output': observation})

        # Step 3: Answer — give the tool result back to the LLM for synthesis.
        observation_json = json.dumps(observation, ensure_ascii=False, default=str)
        synth_prompt = (
            f"Userfrage: {user_question}\n\n"
            f"Tool `{tool_name}` lieferte folgendes Resultat (JSON):\n{observation_json}\n\n"
            f"Antworte dem User in maximal 3 deutschen Sätzen. Nenne konkrete Zahlen aus dem Resultat. "
            f"Schreibe keine Tool-Syntax in die Antwort."
        )
        final_reply = self._llm_call(self.model, synth_prompt)
        trace.append({'step': 'answer', 'output': final_reply.strip()})

        return ChatResult(answer=final_reply.strip(), trace=trace)
