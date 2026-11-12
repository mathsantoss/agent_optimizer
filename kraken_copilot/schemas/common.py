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
    schema_name: str | None = Field(default=None, description="Nome do modelo estruturado Pydantic (ex: KrakenBenchmark, KrakenDataProfile)")
    data: dict[str, Any] = Field(default_factory=dict, description="Payload de dados estruturados da operação")
    warnings: list[str] = Field(default_factory=list, description="Alertas operacionais ou informativos não impeditivos")
    errors: list[str] = Field(default_factory=list, description="Lista de erros impeditivos caso ocorram")

    @classmethod
    def ok(
        cls,
        summary: str,
        operation: str = "",
        data: dict[str, Any] | BaseModel | None = None,
        warnings: list[str] | None = None,
        schema_name: str | None = None,
    ) -> ToolResult:
        """Cria uma resposta de sucesso padronizada com suporte a Pydantic models."""
        resolved_schema = schema_name
        resolved_data: dict[str, Any] = {}
        if isinstance(data, BaseModel):
            resolved_schema = resolved_schema or data.__class__.__name__
            resolved_data = data.model_dump()
        elif isinstance(data, dict):
            resolved_data = data
            if not resolved_schema and "__schema__" in resolved_data:
                resolved_schema = str(resolved_data["__schema__"])

        return cls(
            success=True,
            operation=operation,
            summary=summary,
            schema_name=resolved_schema,
            data=resolved_data,
            warnings=warnings or [],
            errors=[],
        )

    @classmethod
    def fail(
        cls,
        summary: str,
        operation: str = "",
        errors: list[str] | str | None = None,
        data: dict[str, Any] | BaseModel | None = None,
        warnings: list[str] | None = None,
        schema_name: str | None = None,
    ) -> ToolResult:
        """Cria uma resposta de erro padronizada."""
        err_list: list[str] = []
        if isinstance(errors, str):
            err_list = [errors]
        elif isinstance(errors, list):
            err_list = errors
        elif errors is None and summary:
            err_list = [summary]

        resolved_schema = schema_name
        resolved_data: dict[str, Any] = {}
        if isinstance(data, BaseModel):
            resolved_schema = resolved_schema or data.__class__.__name__
            resolved_data = data.model_dump()
        elif isinstance(data, dict):
            resolved_data = data

        return cls(
            success=False,
            operation=operation,
            summary=summary,
            schema_name=resolved_schema,
            data=resolved_data,
            warnings=warnings or [],
            errors=err_list,
        )

    def to_json(self) -> str:
        """Serializa o resultado para string JSON formatada com suporte a tipos diversos."""
        return json.dumps(self.model_dump(), ensure_ascii=False, indent=2, default=str)

