"""Contratos comuns e padronização de respostas de ferramentas e serviços."""
from __future__ import annotations
import json
from typing import Any
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Contrato padronizado para respostas estruturadas de ferramentas e serviços."""

    success: bool = Field(default=True, description="Indica se a operação foi executada com sucesso")
    operation: str = Field(default="", description="Identificador da ferramenta ou sub-operação executada")
    summary: str = Field(description="Resumo claro do resultado em linguagem natural para o agente e usuário")
    data: dict[str, Any] = Field(default_factory=dict, description="Payload de dados estruturados da operação")
    warnings: list[str] = Field(default_factory=list, description="Alertas operacionais ou informativos não impeditivos")
    errors: list[str] = Field(default_factory=list, description="Lista de erros impeditivos caso ocorram")

    @classmethod
    def ok(
        cls,
        summary: str,
        operation: str = "",
        data: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
    ) -> ToolResult:
        """Cria uma resposta de sucesso padronizada."""
        return cls(
            success=True,
            operation=operation,
            summary=summary,
            data=data or {},
            warnings=warnings or [],
            errors=[],
        )

    @classmethod
    def fail(
        cls,
        summary: str,
        operation: str = "",
        errors: list[str] | str | None = None,
        data: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
    ) -> ToolResult:
        """Cria uma resposta de erro padronizada."""
        err_list: list[str] = []
        if isinstance(errors, str):
            err_list = [errors]
        elif isinstance(errors, list):
            err_list = errors
        elif errors is None and summary:
            err_list = [summary]
        return cls(
            success=False,
            operation=operation,
            summary=summary,
            data=data or {},
            warnings=warnings or [],
            errors=err_list,
        )

    def to_json(self) -> str:
        """Serializa o resultado para string JSON formatada com suporte a tipos diversos."""
        return json.dumps(self.model_dump(), ensure_ascii=False, indent=2, default=str)

