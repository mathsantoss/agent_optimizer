"""Definição do Agent FIAP (Orquestrador) e seus 3 sub-agentes especialistas:
- data_analyst_agent: Análise exploratória, qualidade, SQL, estatística e Dicionário de Dados.
- feature_engineer_agent: Engenharia de features para ML em Pandas e PySpark, pipelines e transformações.
- code_optimizer_agent: Diagnóstico estático AST, otimização, benchmark (Antes vs Depois) e validação.
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from agent_fiap.agents import (
    create_code_optimizer_agent,
    create_data_analyst_agent,
    create_feature_engineer_agent,
)
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

# 2. Agente Especialista em Feature Engineering para ML (3 ferramentas públicas)
feature_engineer_agent = create_feature_engineer_agent(language_model)

# 3. Agente Especialista em Otimização de Código e Pipelines (3 ferramentas públicas)
code_optimizer_agent = create_code_optimizer_agent(language_model)

# 4. Agente Principal Orquestrador (inspirado no Databricks Genie Code)
root_agent = Agent(
    name="agent_fiap",
    model=language_model,
    description=(
        "Assistente inteligente de Ciência de Dados, Analytics, Feature Engineering e Engenharia de Pipelines inspirado no Databricks Genie Code. "
        "Orquestra o Agente Analista de Dados (data_analyst_agent), o Especialista em Feature Engineering (feature_engineer_agent) e o Otimizador de Código (code_optimizer_agent)."
    ),
    static_instruction=AGENT_FIAP_INSTRUCTION,
    before_model_callback=before_model_guardrail,
    after_model_callback=after_model_guardrail,
    before_tool_callback=before_tool_guardrail,
    after_tool_callback=after_tool_guardrail,
    sub_agents=[
        data_analyst_agent,
        feature_engineer_agent,
        code_optimizer_agent,
    ],
)
