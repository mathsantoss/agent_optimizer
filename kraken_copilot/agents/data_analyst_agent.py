"""Definição do Kraken Analyst Agent com suas 3 ferramentas públicas oficiais."""
from typing import Any
from google.adk.agents import Agent

from kraken_copilot.guardrails import (
    after_model_guardrail,
    after_tool_guardrail,
    before_model_guardrail,
    before_tool_guardrail,
)
from kraken_copilot.prompts.data_analyst import ANALYST_AGENT_INSTRUCTION
from kraken_copilot.skills import get_agent_skills_instruction
from kraken_copilot.tools.data_analyst import (
    analyze_dataset,
    query_dataset,
    search_knowledge_base,
    load_data_tool,
    missing_value_analysis_tool,
    univariate_analysis_tool,
    correlation_analysis_tool,
    outlier_detection_tool,
    target_relationship_tool,
    clean_dataset_tool,
    generate_visualizations_tool,
    export_report_tool,
    save_workspace_script_tool,
    evidently_quality_report_tool,
)


def create_kraken_analyst_agent(language_model: Any) -> Agent:
    """Instancia o Kraken Analyst com ferramentas orientadas a exploração, EDA profunda, limpeza e relatórios."""
    skills_text = get_agent_skills_instruction("kraken_analyst")
    full_instruction = f"{ANALYST_AGENT_INSTRUCTION}\n{skills_text}" if skills_text else ANALYST_AGENT_INSTRUCTION

    return Agent(
        name="kraken_analyst",
        model=language_model,
        description=(
            "Kraken Analyst — Agente Analista de Dados especialista em análise exploratória (EDA), verificação de qualidade, "
            "resumos estatísticos descritivos, detecção de outliers (IQR), matriz de correlação, limpeza de dados, "
            "geração de visualizações, exportação de relatórios analíticos e criação de scripts modulares no workspace."
        ),
        static_instruction=full_instruction,
        before_model_callback=before_model_guardrail,
        after_model_callback=after_model_guardrail,
        before_tool_callback=before_tool_guardrail,
        after_tool_callback=after_tool_guardrail,
        tools=[
            analyze_dataset,
            query_dataset,
            search_knowledge_base,
            load_data_tool,
            missing_value_analysis_tool,
            univariate_analysis_tool,
            correlation_analysis_tool,
            outlier_detection_tool,
            target_relationship_tool,
            clean_dataset_tool,
            generate_visualizations_tool,
            export_report_tool,
            save_workspace_script_tool,
            evidently_quality_report_tool,
        ],
    )

