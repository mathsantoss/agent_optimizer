"""Definição do Data Analyst Agent com suas 3 ferramentas públicas oficiais."""
from typing import Any
from google.adk.agents import Agent

from agent_fiap.guardrails import (
    after_model_guardrail,
    after_tool_guardrail,
    before_model_guardrail,
    before_tool_guardrail,
)
from agent_fiap.prompts.data_analyst import ANALYST_AGENT_INSTRUCTION
from agent_fiap.tools.data_analyst import (
    analyze_dataset,
    query_dataset,
    search_knowledge_base,
)


def create_data_analyst_agent(language_model: Any) -> Agent:
    """Instancia o Agente Analista de Dados com exatamente 3 ferramentas públicas orientadas a objetivos."""
    return Agent(
        name="data_analyst_agent",
        model=language_model,
        description=(
            "Agente Analista de Dados especialista em análise exploratória, verificação de qualidade, "
            "resumos estatísticos descritivos, consultas SQL analíticas e consulta ao Dicionário de Dados."
        ),
        static_instruction=ANALYST_AGENT_INSTRUCTION,
        before_model_callback=before_model_guardrail,
        after_model_callback=after_model_guardrail,
        before_tool_callback=before_tool_guardrail,
        after_tool_callback=after_tool_guardrail,
        tools=[
            analyze_dataset,
            query_dataset,
            search_knowledge_base,
        ],
    )
