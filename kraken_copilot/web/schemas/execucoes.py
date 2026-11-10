"""Modelos Pydantic para rotas de execuções e aprovações humanas."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class DecisaoInput(BaseModel):
    """Payload para aprovação ou rejeição de execução com guardrail humano."""
    aprovar: bool = Field(description="True para aprovar a execução/alteração, False para rejeitar")
    motivo: Optional[str] = Field(default=None, max_length=1000, description="Justificativa opcional da decisão")


class DecisaoResponse(BaseModel):
    """Resposta da confirmação de decisão humana."""
    status: str
    aprovado: bool
    decidido_em: str
    motivo: Optional[str] = None

