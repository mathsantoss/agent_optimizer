"""Definição do agente principal do Agent FIAP."""

import os

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from .prompts import ROOT_AGENT_INSTRUCTION
from .tools import *


MODEL_NAME = os.getenv(
    "OLLAMA_MODEL",
    "ollama_chat/qwen2.5:14b",
)

OLLAMA_API_BASE = os.getenv(
    "OLLAMA_API_BASE",
    "http://localhost:11434",
)


root_agent = Agent(
    name="agent_fiap",
    model=LiteLlm(
        model=MODEL_NAME,
        api_base=OLLAMA_API_BASE,
        api_key="ollama",
    ),
    description=(
        "Assistente de ciência de dados para analisar, desenvolver, "
        "revisar e otimizar código Python, SQL, Pandas e PySpark."
    ),
    instruction=ROOT_AGENT_INSTRUCTION,
    tools=[
    ],
)