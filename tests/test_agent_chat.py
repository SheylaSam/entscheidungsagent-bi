import pandas as pd

from src.agent_chat import AAIAgent, AgentContext, parse_action, TOOLS


def _ctx():
    forecast = pd.DataFrame({
        'ds': pd.date_range('2010-01-01', periods=6, freq='MS'),
        'yhat': [1000, 1000, 1000, 850, 900, 950],
    })
    rfm = pd.DataFrame({
        'segment': ['At Risk'] * 25 + ['Champions'] * 75,
        'monetary': [1000.0] * 100,
    })
    declining = pd.DataFrame({
        'stock_code': ['X'],
        'description': ['Bad Product'],
        'revenue_last_month': [10.0],
        'revenue_avg': [100.0],
    })
    actuals = pd.DataFrame({
        'ds': pd.date_range('2010-01-01', periods=3, freq='MS'),
        'y': [1000.0, 1000.0, 1000.0],
    })
    return AgentContext(forecast_df=forecast, rfm_df=rfm, declining_df=declining, actuals_df=actuals)


def test_parse_action_extracts_tool_name():
    text = "THOUGHT: ich brauche die top empfehlung\nACTION: top_recommendation()"
    thought, tool = parse_action(text)
    assert tool == 'top_recommendation'
    assert 'top empfehlung' in thought.lower()


def test_parse_action_returns_none_for_unknown_tool():
    text = "THOUGHT: nichts\nACTION: invent_a_tool()"
    _, tool = parse_action(text)
    assert tool is None


def test_parse_action_returns_none_when_llm_says_none():
    text = "THOUGHT: brauche kein tool\nACTION: none"
    _, tool = parse_action(text)
    assert tool is None


def test_tool_top_recommendation_returns_priority_and_utility():
    out = TOOLS['top_recommendation'](_ctx())
    assert 'priority' in out
    assert 'utility_gbp' in out


def test_tool_forecast_summary_returns_pct_change():
    out = TOOLS['forecast_summary'](_ctx())
    assert 'pct_change' in out
    assert out['pct_change'] is not None


def test_tool_customer_breakdown_returns_segment_counts():
    out = TOOLS['customer_breakdown'](_ctx())
    assert out['total_customers'] == 100
    assert out['at_risk'] == 25


def test_tool_declining_products_returns_list():
    out = TOOLS['declining_products'](_ctx())
    assert isinstance(out, list)
    assert out[0]['description'] == 'Bad Product'


def test_aaiagent_chat_loop_uses_tool_and_synthesizes_answer():
    calls: list[str] = []

    def fake_llm(model: str, prompt: str) -> str:
        calls.append(prompt)
        if 'USER FRAGE' in prompt:
            return "THOUGHT: brauche top empfehlung\nACTION: top_recommendation()"
        return "Top-Empfehlung: Reaktivierungskampagne starten — Utility £30k."

    agent = AAIAgent(_ctx(), llm_call=fake_llm)
    result = agent.chat("Was sollten wir diesen Monat tun?")
    assert 'Reaktivierungskampagne' in result.answer
    assert any(step['step'] == 'act' and step['tool'] == 'top_recommendation' for step in result.trace)
    assert len(calls) == 2  # one Think prompt, one Answer prompt


def test_aaiagent_returns_first_reply_when_no_tool_chosen():
    def fake_llm(model: str, prompt: str) -> str:
        return "THOUGHT: keine berechnung nötig\nACTION: none"
    agent = AAIAgent(_ctx(), llm_call=fake_llm)
    result = agent.chat("Erkläre kurz was Utility bedeutet.")
    assert 'ACTION: none' in result.answer or 'keine' in result.answer.lower()
    assert all(step['step'] != 'act' for step in result.trace)
