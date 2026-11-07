"""Definição do Code Optimizer Agent com suas 3 ferramentas públicas oficiais."""
from typing import Any
from google.adk.agents import Agent

from kraken_ia.guardrails import (
    after_model_guardrail,
    after_tool_guardrail,
    before_model_guardrail,
    before_tool_guardrail,
)
from kraken_ia.prompts.code_optimizer import CODE_OPTIMIZER_AGENT_INSTRUCTION
from kraken_ia.tools.code_optimizer import (
    inspect_pipeline,
    optimize_pipeline,
    validate_pipeline,
)


def create_code_optimizer_agent(language_model: Any) -> Agent:
    """Instancia o Agente Otimizador de Código com exatamente 3 ferramentas públicas orientadas a objetivos."""
    return Agent(
        name="code_optimizer_agent",
        model=language_model,
        description=(
            "Agente especialista em diagnóstico estático (AST), proposta e aplicação de otimizações com autorização explícita, "
            "backup (.bak), testes automatizados e validação comparativa de benchmarks (Antes vs Depois) e equivalência funcional."
        ),
        static_instruction=CODE_OPTIMIZER_AGENT_INSTRUCTION,
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

