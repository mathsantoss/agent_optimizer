from datetime import datetime
from typing import Final

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm


def pegar_horas() -> dict:
    """
    Retorna a hora atual do sistema no formato HH:MM:SS.
    """
    agora: Final[datetime] = datetime.now()
    hora_formatada: str = agora.strftime("%H:%M:%S")

    return {"text": hora_formatada}


ollama_endpoint = "http://localhost:11434"

root_agent = Agent(
    model=LiteLlm(
        model="ollama_chat/qwen2.5:14b",
        base_url=ollama_endpoint,
    ),
    name="root_agent",
    description="Você é um assistente que responde perguntas.",
    instruction="""Você é um agente inteligente.
    Você possui uma ferramenta chamada pegar_horas().
    Use essa ferramenta quando o usuário perguntar a hora atual.
    """,
    tools=[pegar_horas],
)