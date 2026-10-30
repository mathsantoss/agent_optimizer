"""Definição do Agent FIAP (Orquestrador) e seus 2 sub-agentes especialistas:
- agente_analista: Especialista em Análise de Dados, Estatística, SQL e Insights.
- agente_otimizador: Especialista em Otimização, Criação de Código, Pipelines e Feature Engineering.
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from .config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL
from .prompts import (
    AGENT_FIAP_INSTRUCTION,
    ANALYST_AGENT_INSTRUCTION,
    CODE_OPTIMIZER_AGENT_INSTRUCTION,
)
from .tools.data_tools import (
    listar_datasets,
    explorar_dataset,
    resumo_estatistico,
    consultar_sql,
    buscar_conhecimento,
)
from .tools.code_tools import (
    ler_arquivo,
    salvar_arquivo,
    executar_pipeline,
    executar_testes,
)

# Instancia o modelo via LiteLLM diretamente com as variáveis do config.py (.env)
llm_model = LiteLlm(
    model=LLM_MODEL,
    api_key=LLM_API_KEY,
    api_base=LLM_API_BASE,
)

# 1. Agente Analista de Dados
agente_analista = Agent(
    name="agente_analista",
    model=llm_model,
    description=(
        "Agente Analista de Dados especialista em explorar datasets em pipeline/dados/, "
        "gerar resumos estatísticos, executar consultas SQL analíticas, recuperar regras "
        "de negócio via RAG e investigar insights, métricas e anomalias."
    ),
    static_instruction=ANALYST_AGENT_INSTRUCTION,
    tools=[
        listar_datasets,
        explorar_dataset,
        resumo_estatistico,
        consultar_sql,
        buscar_conhecimento,
    ],
)

# 2. Agente Especialista em Otimização e Criação de Código / Feature Engineering
agente_otimizador = Agent(
    name="agente_otimizador",
    model=llm_model,
    description=(
        "Agente especialista em otimização, criação e alteração de código e pipelines (pipeline/pipeline_prep.py), "
        "engenharia de features (Feature Engineering), refatoração em Python/Pandas/PySpark/Scikit-Learn, "
        "gravação física no disco e validação via execução do pipeline e testes automatizados."
    ),
    static_instruction=CODE_OPTIMIZER_AGENT_INSTRUCTION,
    tools=[
        ler_arquivo,
        salvar_arquivo,
        executar_pipeline,
        executar_testes,
        listar_datasets,
        explorar_dataset,
        buscar_conhecimento,
    ],
)

# Agente Principal Orquestrador
root_agent = Agent(
    name="agent_fiap",
    model=llm_model,
    description=(
        "Assistente inteligente de Ciência de Dados, Analytics e Engenharia de Pipelines inspirado no Databricks Genie Code. "
        "Orquestra o Agente Analista de Dados (agente_analista) e o Agente Especialista em Otimização e Criação de Código (agente_otimizador)."
    ),
    static_instruction=AGENT_FIAP_INSTRUCTION,
    sub_agents=[
        agente_analista,
        agente_otimizador,
    ],
)
