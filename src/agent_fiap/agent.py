"""Definição do Agent FIAP (Orquestrador) e seus 2 sub-agentes especialistas:
- data_analyst_agent: Especialista em análise exploratória, qualidade, SQL, estatística e Dicionário de Dados.
  Ferramentas públicas: analyze_dataset, query_dataset, search_knowledge_base.
- code_optimizer_agent: Especialista em diagnóstico AST, proposta e aplicação de otimizações, benchmark e validação.
  Ferramentas públicas: inspect_pipeline, optimize_pipeline, validate_pipeline.
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from agent_fiap.agents import create_code_optimizer_agent, create_data_analyst_agent
from agent_fiap.config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL
from agent_fiap.guardrails import (
    after_model_guardrail,
    after_tool_guardrail,
    before_model_guardrail,
    before_tool_guardrail,
)
from agent_fiap.prompts.orchestrator import AGENT_FIAP_INSTRUCTION

# Instancia o modelo via LiteLLM diretamente com as variáveis do config.py (.env)
language_model = LiteLlm(
    model=LLM_MODEL,
    api_key=LLM_API_KEY,
    api_base=LLM_API_BASE,
)

# 1. Agente Analista de Dados (3 ferramentas públicas)
data_analyst_agent = create_data_analyst_agent(language_model)

# 2. Agente Especialista em Otimização de Código e Pipelines (3 ferramentas públicas)
code_optimizer_agent = create_code_optimizer_agent(language_model)

# 3. Agente Principal Orquestrador (inspirado no Databricks Genie Code)
root_agent = Agent(
    name="agent_fiap",
    model=language_model,
    description=(
        "Assistente inteligente de Ciência de Dados, Analytics e Engenharia de Pipelines inspirado no Databricks Genie Code. "
        "Orquestra o Agente Analista de Dados (data_analyst_agent) e o Agente Especialista em Otimização de Código (code_optimizer_agent)."
    ),
    static_instruction=AGENT_FIAP_INSTRUCTION,
    before_model_callback=before_model_guardrail,
    after_model_callback=after_model_guardrail,
    before_tool_callback=before_tool_guardrail,
    after_tool_callback=after_tool_guardrail,
    sub_agents=[
        data_analyst_agent,
        code_optimizer_agent,
    ],
)


