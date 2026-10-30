"""Contratos de dados estruturados (Pydantic) para perfilamento de datasets, análise de código, benchmark e RAG."""
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


class CodeDiagnosticIssue(BaseModel):
    """Diagnóstico de gargalo de performance, qualidade, segurança ou vazamento de dados no código."""

    category: str = Field(
        description="Categoria do apontamento: performance, quality, data_leakage ou security"
    )
    evidence_type: str = Field(
        default="confirmed",
        description="Classificação da evidência: confirmed (confirmado), probable (provável) ou opportunity (oportunidade)",
    )
    severity: str = Field(description="Severidade do apontamento: high, medium ou low")
    line_number: int | None = Field(default=None, description="Linha aproximada no código-fonte")
    description: str = Field(description="Explicação clara do problema detectado")
    recommendation: str = Field(description="Sugestão técnica de refatoração ou correção")


class CodeAnalysisReport(BaseModel):
    """Relatório estruturado da análise estática (AST) de um script ou pipeline Python."""

    file_path: str = Field(description="Caminho relativo do arquivo analisado")
    line_count: int = Field(description="Total de linhas do arquivo")
    imported_modules: list[str] = Field(default_factory=list, description="Módulos importados no script")
    defined_functions: list[str] = Field(default_factory=list, description="Funções definidas no script")
    has_run_entrypoint: bool = Field(description="Indica se a função padrão 'run()' ou 'executar_pipeline()' está presente")
    has_main_guard: bool = Field(description="Indica se possui bloco 'if __name__ == \"__main__\":'")
    issues: list[CodeDiagnosticIssue] = Field(
        default_factory=list,
        description="Lista de oportunidades de otimização, riscos de leakage ou problemas detectados",
    )


class PipelineProfileResult(BaseModel):
    """Métricas reais de profiling de execução de um pipeline Python."""

    file_path: str = Field(description="Caminho relativo do script de pipeline perfilado")
    execution_status: str = Field(description="Status da execução: success ou error")
    return_code: int = Field(description="Código de retorno do processo")
    duration_seconds: float = Field(description="Tempo total de execução em segundos (perf_counter)")
    peak_memory_megabytes: float = Field(description="Pico de memória medido em MB (tracemalloc / RSS)")
    rows_processed: int | None = Field(default=None, description="Quantidade de linhas processadas no DataFrame final")
    column_count: int | None = Field(default=None, description="Quantidade de colunas no DataFrame final")
    output_columns: list[str] = Field(default_factory=list, description="Lista de colunas geradas pelo pipeline")
    output_signature_hash: str | None = Field(
        default=None,
        description="Hash determinístico dos dados de saída para verificação de equivalência",
    )
    standard_output: str = Field(default="", description="Saída padrão capturada na execução")
    standard_error: str = Field(default="", description="Erros ou avisos capturados na execução")
    profiled_at: str = Field(description="Timestamp ISO-8601 da coleta de métricas")


class PipelineBenchmarkComparison(BaseModel):
    """Resultado comparativo de benchmark entre duas execuções de pipeline (Antes vs Depois)."""

    baseline_file: str = Field(description="Arquivo ou referência da execução original (Antes)")
    candidate_file: str = Field(description="Arquivo ou referência da execução otimizada (Depois)")
    baseline_duration_seconds: float = Field(description="Tempo de execução original em segundos")
    candidate_duration_seconds: float = Field(description="Tempo de execução otimizado em segundos")
    speedup_percentage: float = Field(description="Redução percentual no tempo de execução (positivo indica melhoria)")
    baseline_peak_memory_megabytes: float = Field(description="Pico de memória original em MB")
    candidate_peak_memory_megabytes: float = Field(description="Pico de memória otimizado em MB")
    memory_reduction_percentage: float = Field(description="Redução percentual no pico de memória")
    baseline_rows: int | None = Field(default=None, description="Linhas processadas na versão original")
    candidate_rows: int | None = Field(default=None, description="Linhas processadas na versão otimizada")
    results_equivalent: bool = Field(description="Indica se a saída preservou a equivalência esperada")
    equivalence_details: str = Field(description="Explicação sobre a comparação dos resultados de saída")


class KnowledgeChunkMetadata(BaseModel):
    """Metadados enriquecidos de um trecho indexado na base de conhecimento (RAG)."""

    source_path: str = Field(description="Caminho relativo do arquivo de origem")
    file_name: str = Field(description="Nome do arquivo de origem")
    section_title: str = Field(default="Geral", description="Título da seção ou bloco do documento")
    category: str = Field(default="dicionario_dados", description="Categoria do documento")
    related_table: str = Field(default="", description="Tabela de dados relacionada")
    language: str = Field(default="json", description="Formato ou linguagem do conteúdo")
    updated_at: str = Field(default="", description="Data de atualização informada no documento")
    content_hash: str = Field(description="Hash SHA-256 do conteúdo do chunk para atualização incremental")
    indexed_at: str = Field(description="Timestamp ISO-8601 da última indexação do chunk")


class KnowledgeIndexSyncReport(BaseModel):
    """Relatório de sincronização incremental do índice RAG."""

    last_indexed_at: str = Field(description="Data e hora ISO-8601 da sincronização")
    total_active_chunks: int = Field(description="Total de chunks ativos na coleção após sincronização")
    added_or_updated_chunks: int = Field(description="Quantidade de chunks novos ou alterados reindexados")
    unchanged_chunks: int = Field(description="Quantidade de chunks sem alteração reaproveitados")
    removed_chunks: int = Field(description="Quantidade de chunks órfãos removidos da coleção")
