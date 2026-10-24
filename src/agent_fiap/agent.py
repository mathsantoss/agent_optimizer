"""Definição do Agent FIAP unificado utilizando Google ADK e LiteLLM."""
import os
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from .prompts import AGENT_FIAP_INSTRUCTION
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

# Configuração do modelo Ollama via LiteLLM
MODEL_NAME = os.getenv("OLLAMA_MODEL", "ollama_chat/qwen2.5:14b")
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")

llm_model = LiteLlm(
    model=MODEL_NAME,
    api_base=OLLAMA_API_BASE,
    api_key="ollama",
)

# Agente Principal Unificado (estilo Databricks Genie Code)
root_agent = Agent(
    name="agent_fiap",
    model=llm_model,
    description=(
        "Assistente unificado de Ciência de Dados, Analytics e Engenharia de Pipelines inspirado no Databricks Genie Code. "
        "Explora datasets, executa queries SQL analíticas, cria, otimiza, salva no disco e executa pipelines em pipeline/pipeline_prep.py."
    ),
    instruction=AGENT_FIAP_INSTRUCTION,
    tools=[
        listar_datasets,
        explorar_dataset,
        resumo_estatistico,
        consultar_sql,
        buscar_conhecimento,
        ler_arquivo,
        salvar_arquivo,
        executar_pipeline,
        executar_testes,
    ],
)
