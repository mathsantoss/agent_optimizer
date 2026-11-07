"""Definição do Kraken Code Agent (Feature Engineering e Pipelines) com suas 3 ferramentas públicas oficiais."""
from typing import Any
from google.adk.agents import Agent

from kraken_ia.guardrails import (
    after_model_guardrail,
    after_tool_guardrail,
    before_model_guardrail,
    before_tool_guardrail,
)
from kraken_ia.prompts.feature_engineer import FEATURE_ENGINEER_AGENT_INSTRUCTION
from kraken_ia.tools.feature_engineer import (
    add_feature_to_pipeline,
    generate_feature_pipeline,
    preview_features,
)


def create_kraken_code_agent(language_model: Any) -> Agent:
    """Instancia o Kraken Code com 3 ferramentas públicas orientadas a Engenharia de Features."""
    return Agent(
        name="kraken_code",
        model=language_model,
        description=(
            "Kraken Code — Agente especialista em Engenharia de Features e Pipelines para Machine Learning. "
            "Cria pipelines completos de features ou inclui novas transformações em scripts existentes, "
            "com suporte completo em Pandas e PySpark, prévia em amostra e prevenção estrita de data leakage."
        ),
        static_instruction=FEATURE_ENGINEER_AGENT_INSTRUCTION,
        before_model_callback=before_model_guardrail,
        after_model_callback=after_model_guardrail,
        before_tool_callback=before_tool_guardrail,
        after_tool_callback=after_tool_guardrail,
        tools=[
            generate_feature_pipeline,
            add_feature_to_pipeline,
            preview_features,
        ],
    )

