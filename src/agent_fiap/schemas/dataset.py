"""Contratos de dados estruturados para perfilamento, qualidade e exploração de datasets."""
from typing import Any
from pydantic import BaseModel, Field


class ColumnProfile(BaseModel):
    """Perfil estrutural e de qualidade de uma coluna de dataset."""

    data_type: str = Field(description="Tipo de dado inferido pelo Pandas/Arrow")
    unique_values: int = Field(description="Quantidade de valores distintos na coluna")
    null_count: int = Field(description="Quantidade de valores ausentes (nulos)")
    null_percentage: float = Field(description="Percentual de valores ausentes (0 a 100)")


class DateRangeSummary(BaseModel):
    """Intervalo temporal mínimo e máximo identificado em uma coluna de data."""

    start_date: str = Field(description="Menor data válida encontrada na coluna")
    end_date: str = Field(description="Maior data válida encontrada na coluna")


class DatasetProfile(BaseModel):
    """Perfil completo de inspeção de um dataset."""

    file_path: str = Field(description="Caminho relativo do arquivo no projeto")
    sql_table_name: str = Field(description="Nome da tabela correspondente para consultas SQL")
    sampled_row_count: int = Field(description="Total de linhas consideradas na amostra")
    duplicate_row_count: int = Field(description="Quantidade de linhas duplicadas detectadas")
    candidate_key_columns: list[str] = Field(
        default_factory=list,
        description="Colunas candidatas a chave primária ou identificador único",
    )
    temporal_ranges: dict[str, DateRangeSummary] | str = Field(
        description="Intervalos temporais detectados por coluna de data"
    )
    columns: dict[str, ColumnProfile] = Field(description="Metadados detalhados por coluna")
    sample_rows: list[dict[str, Any]] = Field(description="Amostra real das primeiras linhas")

