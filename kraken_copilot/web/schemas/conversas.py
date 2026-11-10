"""Modelos Pydantic para rotas de conversas e mensagens."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MensagemInput(BaseModel):
    """Payload de envio de mensagem pelo usuário."""
    texto: str = Field(min_length=1, max_length=10000, description="Texto da mensagem enviada")
    modelo: Optional[str] = Field(default=None, description="Versão do modelo da família Gemini selecionado pelo usuário")


class MensagemResponse(BaseModel):
    """Estrutura de uma mensagem na conversa."""
    id: str
    role: str
    texto: str
    timestamp: str
    especialista: Optional[str] = None
    execucao_id: Optional[str] = None
    metadados: Dict[str, Any] = Field(default_factory=dict)


class ConversaResumoResponse(BaseModel):
    """Resumo de uma sessão de conversa para a listagem."""
    id: str
    titulo: str
    criado_em: str
    atualizado_em: str
    total_mensagens: int


class ListaConversasResponse(BaseModel):
    """Lista de conversas do usuário."""
    conversas: List[ConversaResumoResponse]


class ConversaDetalheResponse(BaseModel):
    """Detalhes completos de uma sessão de conversa."""
    id: str
    titulo: str
    criado_em: str
    atualizado_em: str
    mensagens: List[Dict[str, Any]] = Field(default_factory=list)

