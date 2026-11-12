"""Definição do Kraken Optimizer Agent com suas 3 ferramentas públicas oficiais."""
from typing import Any
from google.adk.agents import Agent

from kraken_copilot.guardrails import (
    after_model_guardrail,
    after_tool_guardrail,
    before_model_guardrail,
    before_tool_guardrail,
)
from kraken_copilot.prompts.code_optimizer import CODE_OPTIMIZER_AGENT_INSTRUCTION
from kraken_copilot.skills import get_agent_skills_instruction
from kraken_copilot.tools.code_optimizer import (
    inspect_pipeline,
    optimize_pipeline,
    validate_pipeline,
)


def create_kraken_optimizer_agent(language_model: Any) -> Agent:
    """Instancia o Kraken Optimizer com exatamente 3 ferramentas públicas orientadas a otimização de código."""
    skills_text = get_agent_skills_instruction("kraken_optimizer")
    full_instruction = f"{CODE_OPTIMIZER_AGENT_INSTRUCTION}\n{skills_text}" if skills_text else CODE_OPTIMIZER_AGENT_INSTRUCTION

    return Agent(
        name="kraken_optimizer",
        model=language_model,
        description=(
            "Kraken Optimizer — Agente especialista em diagnóstico estático (AST), proposta e aplicação de otimizações com autorização explícita, "
            "backup (.bak), testes automatizados e validação comparativa de benchmarks (Antes vs Depois) e equivalência funcional."
        ),
        static_instruction=full_instruction,
        before_model_callback=before_model_guardrail,
        after_model_callback=after_model_guardrail,
        before_tool_callback=before_tool_guardrail,
        after_tool_callback=after_tool_guardrail,
        tools=[
            inspect_pipeline,
            optimize_pipeline,
            validate_pipeline,
        ],
    )

