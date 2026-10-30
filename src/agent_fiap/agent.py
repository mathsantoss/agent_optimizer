"""Definição do Agent FIAP (Orquestrador) e seus 2 sub-agentes especialistas:
- data_analyst_agent: Especialista em Análise de Dados, Estatística, SQL e Insights.
- code_optimizer_agent: Especialista em Otimização, Criação de Código, Pipelines e Feature Engineering.
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from .config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL
from .prompts import (
    AGENT_FIAP_INSTRUCTION,
    ANALYST_AGENT_INSTRUCTION,
    CODE_OPTIMIZER_AGENT_INSTRUCTION,
)
from .tools import (
    execute_sql_query,
    explore_dataset,
    generate_statistical_summary,
    list_datasets,
    read_file,
    run_pipeline,
    run_tests,
    save_file,
    search_knowledge_base,
)

# Instancia o modelo via LiteLLM diretamente com as variáveis do config.py (.env)
language_model = LiteLlm(
    model=LLM_MODEL,
    api_key=LLM_API_KEY,
    api_base=LLM_API_BASE,
)

# 1. Agente Analista de Dados
data_analyst_agent = Agent(
    name="data_analyst_agent",
    model=language_model,
    description=(
        "Agente Analista de Dados especialista em explorar datasets em pipeline/dados/, "
        "gerar resumos estatísticos, executar consultas SQL analíticas, recuperar regras "
        "de negócio via RAG e investigar insights, métricas e anomalias."
    ),
    static_instruction=ANALYST_AGENT_INSTRUCTION,
    tools=[
        list_datasets,
        explore_dataset,
        generate_statistical_summary,
        execute_sql_query,
        search_knowledge_base,
    ],
)

# 2. Agente Especialista em Otimização e Criação de Código / Feature Engineering
code_optimizer_agent = Agent(
    name="code_optimizer_agent",
    model=language_model,
    description=(
        "Agente especialista em otimização, criação e alteração de código e pipelines (pipeline/pipeline_prep.py), "
        "engenharia de features (Feature Engineering), refatoração em Python/Pandas/PySpark/Scikit-Learn, "
        "gravação física no disco e validação via execução do pipeline e testes automatizados."
    ),
    static_instruction=CODE_OPTIMIZER_AGENT_INSTRUCTION,
    tools=[
        read_file,
        save_file,
        run_pipeline,
        run_tests,
        list_datasets,
        explore_dataset,
        search_knowledge_base,
    ],
)

# Agente Principal Orquestrador
root_agent = Agent(
    name="agent_fiap",
    model=language_model,
    description=(
        "Assistente inteligente de Ciência de Dados, Analytics e Engenharia de Pipelines inspirado no Databricks Genie Code. "
        "Orquestra o Agente Analista de Dados (data_analyst_agent) e o Agente Especialista em Otimização e Criação de Código (code_optimizer_agent)."
    ),
    static_instruction=AGENT_FIAP_INSTRUCTION,
    sub_agents=[
        data_analyst_agent,
        code_optimizer_agent,
    ],
)
