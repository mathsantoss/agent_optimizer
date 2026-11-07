"""Definição do Planner Agent (Kraken Planner) com suas ferramentas de planejamento estruturado."""
from typing import Any
from google.adk.agents import Agent

from kraken_ia.guardrails import (
    after_model_guardrail,
    after_tool_guardrail,
    before_model_guardrail,
    before_tool_guardrail,
)
from kraken_ia.prompts.planner import PLANNER_AGENT_INSTRUCTION
from kraken_ia.tools.planner import (
    create_execution_plan,
    get_plan_status,
    replan_execution,
    update_plan_step,
)


def create_kraken_planner_agent(language_model: Any) -> Agent:
    """Instancia o Kraken Planner com suas 4 ferramentas de planejamento estruturado."""
    return Agent(
        name="kraken_planner",
        model=language_model,
        description=(
            "Kraken Planner — Agente especialista em interpretação de solicitações complexas, decomposição em etapas sequenciais, "
            "geração de planos com dependências e critérios de sucesso, coordenação dos especialistas (Kraken Analyst, Kraken Code, Kraken Optimizer) "
            "e replanejamento em caso de falhas ou imprevistos."
        ),
        static_instruction=PLANNER_AGENT_INSTRUCTION,
        before_model_callback=before_model_guardrail,
        after_model_callback=after_model_guardrail,
        before_tool_callback=before_tool_guardrail,
        after_tool_callback=after_tool_guardrail,
        tools=[
            create_execution_plan,
            get_plan_status,
            update_plan_step,
            replan_execution,
        ],
    )

