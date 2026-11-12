"""Contratos de dados estruturados para engenharia de features (Pandas e PySpark)."""
from typing import Any
from pydantic import BaseModel, Field


class FeatureSpec(BaseModel):
    """Especificação de uma feature individual criada ou planejada."""

    name: str = Field(description="Nome da coluna da feature gerada")
    category: str = Field(
        description="Categoria da feature: temporal, agregacao, ratio, window_rolling, lag, encoding ou custom"
    )
    framework: str = Field(default="pandas", description="Framework de dados: pandas ou pyspark")
    expression: str = Field(description="Expressão lógica ou fórmula da feature")
    description: str = Field(description="Descrição de negócio e utilidade da feature para modelos de ML")


class FeaturePipelinePlan(BaseModel):
    """Plano de construção de um pipeline de features completo ou incremental."""

    pipeline_name: str = Field(description="Nome descritivo do pipeline de features")
    framework: str = Field(default="pandas", description="Framework utilizado: pandas ou pyspark")
    target_file_path: str = Field(description="Caminho do arquivo de script no workspace (ex.: krakenlake/workspace/meu_pipeline.py)")
    source_dataset: str = Field(description="Dataset base de entrada")
    features: list[FeatureSpec] = Field(default_factory=list, description="Lista de features especificadas no plano")
    code: str = Field(default="", description="Código Python/PySpark gerado para o pipeline")


class FeaturePreviewSummary(BaseModel):
    """Resumo da execução de prévia de features em amostra."""

    source_dataset: str = Field(description="Dataset utilizado na prévia")
    framework: str = Field(default="pandas", description="Framework de cálculo avaliado")
    total_sample_rows: int = Field(description="Quantidade de linhas avaliadas na amostra")
    new_features_count: int = Field(description="Quantidade de novas colunas geradas")
    new_columns: list[str] = Field(default_factory=list, description="Nomes das novas colunas criadas")
    sample_preview: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Amostra das primeiras linhas com as novas features calculadas",
    )
    null_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Contagem de nulos nas novas colunas geradas",
    )

