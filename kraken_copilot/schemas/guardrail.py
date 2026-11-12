"""Schemas Pydantic para validação e auditoria de guardrails de segurança e integridade."""
from typing import Any
from pydantic import BaseModel, Field


class GuardrailCheckResult(BaseModel):
    """Resultado estruturado da validação de guardrails de entrada e saída."""

    allowed: bool = Field(
        default=True,
        description="Indica se a mensagem ou ação é permitida e segura para prosseguir.",
    )
    category: str = Field(
        default="safe",
        description="Categoria detectada pelo guardrail: 'safe', 'sexual_content', 'destructive_command', 'jailbreak', 'forbidden_path', etc.",
    )
    polite_response: str | None = Field(
        default=None,
        description="Mensagem educada e profissional retornada ao usuário caso o guardrail bloqueie a solicitação.",
    )
    reason: str | None = Field(
        default=None,
        description="Justificativa técnica da decisão do guardrail para fins de log e auditoria.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadados adicionais da verificação do guardrail.",
    )

