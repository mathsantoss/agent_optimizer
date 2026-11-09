"""Definição do Kraken Copilot (Orquestrador) e seus 3 sub-agentes especialistas:
- kraken_analyst: Análise exploratória, qualidade, SQL, estatística e Dicionário de Dados.
- kraken_code: Engenharia de features para ML em Pandas e PySpark, pipelines e transformações.
- kraken_optimizer: Diagnóstico estático AST, otimização, benchmark (Antes vs Depois) e validação.
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from kraken_copilot.agents import (
    create_kraken_analyst_agent,
    create_kraken_code_agent,
    create_kraken_optimizer_agent,
)
from kraken_copilot.config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL
from kraken_copilot.guardrails import (
    after_model_guardrail,
    after_tool_guardrail,
    before_model_guardrail,
    before_tool_guardrail,
)
from kraken_copilot.prompts.orchestrator import KRAKEN_COPILOT_INSTRUCTION

# Instancia o modelo via LiteLLM diretamente com as variáveis do config.py (.env)
language_model = LiteLlm(
    model=LLM_MODEL,
    api_key=LLM_API_KEY,
    api_base=LLM_API_BASE,
)

# 1. Agente Analista de Dados (Kraken Analyst - 3 ferramentas públicas)
kraken_analyst_agent = create_kraken_analyst_agent(language_model)

# 2. Agente Especialista em Feature Engineering e Pipelines (Kraken Code - 3 ferramentas públicas)
kraken_code_agent = create_kraken_code_agent(language_model)

# 3. Agente Especialista em Otimização de Código e Benchmarks (Kraken Optimizer - 3 ferramentas públicas)
kraken_optimizer_agent = create_kraken_optimizer_agent(language_model)

# 4. Agente Principal Orquestrador (Kraken Copilot)
root_agent = Agent(
    name="kraken_copilot",
    model=language_model,
    description=(
        "Kraken Copilot — Assistente inteligente de Ciência de Dados, Analytics, Feature Engineering e Engenharia de Pipelines inspirado no Databricks Genie Code. "
        "Orquestra o Agente Analista de Dados (kraken_analyst), o Especialista em Feature Engineering (kraken_code) e o Otimizador de Código (kraken_optimizer)."
    ),
    static_instruction=KRAKEN_COPILOT_INSTRUCTION,
    before_model_callback=before_model_guardrail,
    after_model_callback=after_model_guardrail,
    before_tool_callback=before_tool_guardrail,
    after_tool_callback=after_tool_guardrail,
    sub_agents=[
        kraken_analyst_agent,
        kraken_code_agent,
        kraken_optimizer_agent,
    ],
)

# Aliases de conveniência
kraken_copilot = root_agent
data_analyst_agent = kraken_analyst_agent
feature_engineer_agent = kraken_code_agent
code_optimizer_agent = kraken_optimizer_agent

