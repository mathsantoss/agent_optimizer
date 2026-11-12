"""Resultados estruturados (Pydantic & Pydantic-AI) para ferramentas do Kraken Copilot:
- KrakenBenchmark: Métricas comparativas de execução antes vs depois (tempo, memória, speedup, equivalência).
- KrakenDataProfile: Diagnóstico de estrutura, tipos de dados, valores ausentes e qualidade de datasets.
- KrakenCodeDiff: Propostas de alteração de código, unified diff, estatísticas de linhas e solicitação de aprovação.
- KrakenStatisticalReport: Resumo estatístico descritivo aprofundado, detecção de outliers (IQR) e distribuições.
"""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class KrakenBenchmark(BaseModel):
    """Resultado estruturado de benchmark comparativo de pipeline (Antes vs Depois)."""

    arquivo: str = Field(description="Nome ou caminho do arquivo testado")
    baseline_arquivo: str = Field(default="", description="Arquivo original de referência")
    status: str = Field(default="SUCESSO", description="Status da execução: SUCESSO, FALHA ou TIMEOUT")
    tempo_execucao_original: float = Field(default=0.0, description="Tempo de execução do baseline em segundos")
    tempo_execucao_otimizado: float = Field(default=0.0, description="Tempo de execução da versão candidata em segundos")
    speedup: float = Field(default=0.0, description="Percentual de speedup (positivo indica ganho de velocidade)")
    memoria_pico_original_mb: float = Field(default=0.0, description="Pico de memória original medido em MB")
    memoria_pico_otimizada_mb: float = Field(default=0.0, description="Pico de memória otimizado medido em MB")
    reducao_memoria_pct: float = Field(default=0.0, description="Percentual de redução no consumo de memória")
    linhas_baseline: int | None = Field(default=None, description="Total de linhas processadas pelo baseline")
    linhas_candidato: int | None = Field(default=None, description="Total de linhas processadas pela versão otimizada")
    equivalencia_preservada: bool = Field(default=True, description="Indica se os resultados são matematicamente equivalentes")
    detalhes_equivalencia: str = Field(default="Aprovada", description="Explicação técnica da validação de equivalência")
    tabela_markdown: str | None = Field(default=None, description="Tabela formatada em Markdown para renderização no chat")
    metricas_adicionais: dict[str, Any] = Field(default_factory=dict, description="Métricas extras de telemetria e perfilamento")

    @property
    def speedup_multiplicador(self) -> float:
        """Calcula o ganho em fator multiplicativo (ex: 2.5x mais rápido)."""
        if self.tempo_execucao_otimizado > 0:
            return round(self.tempo_execucao_original / self.tempo_execucao_otimizado, 2)
        return 1.0


class KrakenColumnInfo(BaseModel):
    """Metadados estruturados de uma coluna de dataset."""

    nome: str = Field(description="Nome da coluna")
    tipo: str = Field(description="Tipo de dado (ex: int64, float64, object, datetime64)")
    valores_unicos: int = Field(default=0, description="Contagem de valores distintos")
    nulos: int = Field(default=0, description="Total de registros nulos ou ausentes")
    percentual_nulos: float = Field(default=0.0, description="Percentual de nulos (0 a 100)")


class KrakenDataProfile(BaseModel):
    """Diagnóstico e perfilamento estruturado de dataset."""

    dataset_nome: str = Field(description="Nome de identificação do dataset no catálogo")
    arquivo: str = Field(description="Nome do arquivo físico correspondente")
    caminho: str = Field(default="", description="Caminho relativo completo no datalake")
    total_linhas: int = Field(default=0, description="Total de linhas amostradas ou presentes no dataset")
    total_colunas: int = Field(default=0, description="Total de colunas no dataset")
    tamanho_kb: float = Field(default=0.0, description="Tamanho em disco em kilobytes")
    amostragem_ativa: bool = Field(default=False, description="Indica se o perfilamento usou amostragem de linhas")
    linhas_duplicadas: int = Field(default=0, description="Total de registros duplicados detectados")
    chaves_candidatas: list[str] = Field(default_factory=list, description="Colunas candidatas a chave primária")
    periodo_temporal: dict[str, dict[str, str]] | str = Field(
        default_factory=dict,
        description="Datas mínimas e máximas identificadas em colunas temporais",
    )
    colunas: list[KrakenColumnInfo] = Field(default_factory=list, description="Perfil detalhado de cada coluna")
    amostra_linhas: list[dict[str, Any]] = Field(default_factory=list, description="Primeiras linhas sanitizadas para preview")
    alertas_qualidade: list[str] = Field(default_factory=list, description="Avisos sobre nulos, duplicatas ou desbalanceamento")


class KrakenCodeDiff(BaseModel):
    """Representação estruturada de proposta de alteração de código com diff e governança."""

    arquivo: str = Field(description="Nome do arquivo Python (ex: pipeline_prep.py)")
    arquivo_alvo: str = Field(default="", description="Caminho relativo do arquivo no workspace")
    original_code: str = Field(default="", description="Código original antes da transformação")
    proposed_code: str = Field(default="", description="Código proposto com melhorias e otimizações")
    raw_diff: str = Field(default="", description="Unified patch diff formatado para visualizadores de código")
    adicoes: int = Field(default=0, description="Número de linhas adicionadas (+)")
    remocoes: int = Field(default=0, description="Número de linhas removidas (-)")
    has_approval_request: bool = Field(default=True, description="Exige aprovação explícita do usuário antes de aplicar")
    tipo_transformacao: str = Field(
        default="otimizacao",
        description="Categoria da transformação: otimizacao, vetorizacao, feature_engineering ou correcao",
    )
    explicacao: str = Field(default="", description="Resumo técnico das mudanças efetuadas")


class KrakenStatisticalMetric(BaseModel):
    """Métricas numéricas descritivas calculadas sobre uma coluna."""

    coluna: str = Field(description="Nome da coluna numérica analisada")
    media: float = Field(description="Média aritmética dos valores")
    desvio_padrao: float = Field(description="Desvio padrão amostral")
    minimo: float = Field(description="Valor mínimo encontrado")
    q25: float = Field(description="Primeiro quartil (25%)")
    mediana: float = Field(description="Mediana ou segundo quartil (50%)")
    q75: float = Field(description="Terceiro quartil (75%)")
    maximo: float = Field(description="Valor máximo encontrado")
    nulos: int = Field(default=0, description="Quantidade de valores nulos na coluna")
    outliers_iqr: int = Field(default=0, description="Quantidade de outliers detectados pelo método IQR (1.5 * IQR)")
    limite_inferior_iqr: float | None = Field(default=None, description="Limite inferior para corte de outliers")
    limite_superior_iqr: float | None = Field(default=None, description="Limite superior para corte de outliers")


class KrakenStatisticalReport(BaseModel):
    """Relatório estruturado de análise estatística descritiva e detecção de anomalias."""

    dataset_nome: str = Field(description="Nome do dataset analisado")
    total_linhas_analisadas: int = Field(default=0, description="Quantidade de registros considerados no cálculo")
    amostragem_ativa: bool = Field(default=False, description="Indica se o cálculo estatístico foi realizado sobre amostra")
    total_outliers_geral: int = Field(default=0, description="Soma total de outliers identificados em todas as colunas")
    metricas_colunas: list[KrakenStatisticalMetric] = Field(
        default_factory=list,
        description="Métricas descritivas detalhadas por coluna numérica",
    )
    tabela_markdown: str | None = Field(default=None, description="Tabela descritiva formatada em Markdown")
    insights_estatisticos: list[str] = Field(default_factory=list, description="Interpretações estatísticas e de negócio")

