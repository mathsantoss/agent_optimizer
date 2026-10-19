import os
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from .prompts import ROOT_AGENT_INSTRUCTION
from .tools.file_tools import ler_arquivo, escrever_arquivo
from .tools.data_tools import explorar_esquema_dados

MODEL_NAME = os.getenv("OLLAMA_MODEL", "ollama_chat/qwen2.5:14b")
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")

root_agent = Agent(
    name="agent_fiap",
    model=LiteLlm(
        model=MODEL_NAME,
        api_base=OLLAMA_API_BASE,
        api_key="ollama", # Ollama não precisa de chave real
    ),
    description=(
        "Assistente de ciência de dados para analisar, desenvolver, "
        "revisar e otimizar código Python, SQL, Pandas e PySpark."
    ),
    instruction=ROOT_AGENT_INSTRUCTION,
    tools=[
        ler_arquivo,
        escrever_arquivo,
        explorar_esquema_dados
    ],
)