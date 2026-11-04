"""Contratos de dados estruturados para análise estática AST, perfilamento e benchmark de pipelines."""
from pydantic import BaseModel, Field


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
    column_hashes: dict[str, str] = Field(
        default_factory=dict,
        description="Hashes determinísticos individuais por coluna para verificação estrita de equivalência",
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
    equivalence_details: str = Field(description="Explicação amigável sobre a equivalência dos dados de saída")

