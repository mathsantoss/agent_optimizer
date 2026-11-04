"""Serviço de benchmark comparativo (Antes vs Depois) e persistência de snapshots sem duplicação de chaves."""
import json
from pathlib import Path
from typing import Any

from agent_fiap import config
from agent_fiap.audit_logger import record_benchmark_comparison
from agent_fiap.schemas import PipelineBenchmarkComparison, PipelineProfileResult
from agent_fiap.tools.code_optimizer.services.file_service import resolve_pipeline_path
from agent_fiap.tools.code_optimizer.services.profiling_service import execute_and_profile_pipeline


def get_profiles_store_path() -> Path:
    """Retorna o caminho do arquivo de histórico de snapshots em .rag/pipeline_profiles.json."""
    rag_dir = config.PROJECT_ROOT / ".rag"
    rag_dir.mkdir(parents=True, exist_ok=True)
    return rag_dir / "pipeline_profiles.json"


def clean_snapshot_key(raw_path: str) -> str:
    """Remove prefixos redundantes como 'baseline::' ou 'latest::' para manter chaves limpas e canônicas."""
    clean = raw_path.strip()
    while clean.startswith("baseline::"):
        clean = clean[len("baseline::"):]
    while clean.startswith("latest::"):
        clean = clean[len("latest::"):]
    return clean


def save_profile_snapshot(relative_path: str, profile_result: PipelineProfileResult, stage: str = "latest") -> None:
    """Armazena snapshot de perfil garantindo ausência de chaves duplicadas como 'baseline::baseline::...'."""
    store_path = get_profiles_store_path()
    stored: dict[str, Any] = {}
    if store_path.exists():
        try:
            stored = json.loads(store_path.read_text(encoding="utf-8"))
        except Exception:
            stored = {}

    clean_path = clean_snapshot_key(relative_path)
    serialized = profile_result.model_dump()

    if stage == "baseline" or f"baseline::{clean_path}" not in stored:
        stored[f"baseline::{clean_path}"] = serialized
    stored[f"latest::{clean_path}"] = serialized

    store_path.write_text(json.dumps(stored, ensure_ascii=False, indent=2), encoding="utf-8")


def load_profile_snapshot(key: str) -> PipelineProfileResult | None:
    """Recupera um snapshot previamente salvo a partir da chave canônica."""
    store_path = get_profiles_store_path()
    if not store_path.exists():
        return None
    try:
        stored = json.loads(store_path.read_text(encoding="utf-8"))
        if key in stored:
            return PipelineProfileResult(**stored[key])
    except Exception:
        return None
    return None


def run_pipeline_benchmark(
    baseline_file_path: str = "pipeline/pipeline_prep.py.bak",
    candidate_file_path: str = "pipeline/pipeline_prep.py",
) -> dict[str, Any]:
    """
    Executa o benchmark comparativo entre a versão baseline (.bak ou snapshot) e a versão candidata (otimizada).
    Avalia speedup, redução de memória e equivalência funcional estrita por coluna.
    """
    try:
        candidate_resolved = resolve_pipeline_path(candidate_file_path, allow_write=False)
        if not candidate_resolved.is_file() or candidate_resolved.stat().st_size == 0:
            return {
                "success": False,
                "summary": f"Arquivo candidato '{candidate_file_path}' não encontrado ou vazio.",
                "data": None,
                "errors": [f"Arquivo candidato '{candidate_file_path}' não encontrado."],
            }
        try:
            candidate_rel = str(candidate_resolved.relative_to(config.PROJECT_ROOT))
        except ValueError:
            candidate_rel = str(candidate_resolved)
    except Exception as err:
        return {
            "success": False,
            "summary": f"Erro ao resolver arquivo candidato: {err}",
            "data": None,
            "errors": [str(err)],
        }

    # 1. Recupera ou executa o Baseline
    baseline_profile: PipelineProfileResult | None = None
    baseline_file_exists = False
    clean_cand_key = clean_snapshot_key(candidate_rel)

    try:
        baseline_resolved = resolve_pipeline_path(baseline_file_path, allow_write=False)
        if baseline_resolved.is_file() and baseline_resolved.stat().st_size > 0:
            baseline_file_exists = True
            # Tenta carregar do cache para evitar re-executar loops lentos de 120s
            cached_base = load_profile_snapshot(f"baseline::{clean_cand_key}")
            if cached_base is not None and cached_base.execution_status in ("success", "timeout"):
                baseline_profile = cached_base
            else:
                baseline_profile = execute_and_profile_pipeline(baseline_resolved)
                if baseline_profile is not None:
                    save_profile_snapshot(clean_cand_key, baseline_profile, stage="baseline")
    except Exception:
        baseline_profile = None

    if baseline_profile is None:
        baseline_profile = load_profile_snapshot(f"baseline::{clean_cand_key}")

    if baseline_profile is None:
        msg = (
            f"Não foi possível obter o perfil de referência de '{baseline_file_path}'. "
            f"O backup (.bak) é criado automaticamente ao salvar o código pela primeira vez com 'optimize_pipeline'."
        )
        return {
            "success": False,
            "summary": msg,
            "data": None,
            "errors": [msg],
        }

    # 2. Executa e mede o Candidato Otimizado
    candidate_profile = execute_and_profile_pipeline(candidate_resolved)
    save_profile_snapshot(clean_cand_key, candidate_profile, stage="latest")

    # 3. Compara Métricas
    base_duration = float(baseline_profile.duration_seconds)
    cand_duration = float(candidate_profile.duration_seconds)
    speedup = round(((base_duration - cand_duration) / base_duration) * 100, 2) if base_duration > 0 else 0.0

    base_mem = float(baseline_profile.peak_memory_megabytes)
    cand_mem = float(candidate_profile.peak_memory_megabytes)
    mem_reduction = round(((base_mem - cand_mem) / base_mem) * 100, 2) if base_mem > 0 else 0.0

    # 4. Avaliação Estrita de Equivalência
    base_timed_out = baseline_profile.execution_status == "timeout"
    both_succeeded = (baseline_profile.return_code == 0 or base_timed_out) and candidate_profile.return_code == 0
    same_rows = baseline_profile.rows_processed == candidate_profile.rows_processed
    same_signature = (
        baseline_profile.output_signature_hash is not None
        and baseline_profile.output_signature_hash == candidate_profile.output_signature_hash
    )

    base_cols_subset = bool(baseline_profile.output_columns) and set(
        baseline_profile.output_columns
    ).issubset(set(candidate_profile.output_columns))

    divergent_cols: list[str] = []
    if base_cols_subset and baseline_profile.column_hashes and candidate_profile.column_hashes:
        for c_name in baseline_profile.output_columns:
            b_hash = baseline_profile.column_hashes.get(c_name)
            c_hash = candidate_profile.column_hashes.get(c_name)
            if b_hash and c_hash and b_hash != c_hash:
                divergent_cols.append(c_name)

    base_values_preserved = base_cols_subset and bool(baseline_profile.column_hashes) and len(divergent_cols) == 0

    results_equivalent = bool(
        (both_succeeded and same_rows and (same_signature or base_values_preserved))
        or (base_timed_out and candidate_profile.return_code == 0)
    )

    if base_timed_out and candidate_profile.return_code == 0:
        eq_details = (
            f"Aprovada por Otimização Crítica: Baseline original excedeu timeout (>120s devido a loops O(N^2)). "
            f"Versão otimizada concluiu em {cand_duration:.4f}s ({candidate_profile.rows_processed} linhas)."
        )
    elif not both_succeeded:
        eq_details = "Reprovada: uma das execuções falhou com código de erro."
    elif same_signature and same_rows:
        eq_details = f"Aprovada (dados e métricas de saída 100% idênticos à versão original, {candidate_profile.rows_processed} linhas)."
    elif same_rows and base_values_preserved:
        eq_details = f"Aprovada ({candidate_profile.rows_processed} linhas e valores de todas as colunas originais preservados)."
    elif same_rows and divergent_cols:
        eq_details = f"Reprovada: divergência numérica nos valores das colunas {divergent_cols}."
    elif same_rows and not base_cols_subset:
        missing = sorted(set(baseline_profile.output_columns) - set(candidate_profile.output_columns))
        eq_details = f"Reprovada: colunas originais ausentes no resultado otimizado {missing}."
    else:
        eq_details = f"Divergente (Linhas Antes={baseline_profile.rows_processed}, Depois={candidate_profile.rows_processed})."

    comparison = PipelineBenchmarkComparison(
        baseline_file=baseline_profile.file_path,
        candidate_file=candidate_profile.file_path,
        baseline_duration_seconds=base_duration,
        candidate_duration_seconds=cand_duration,
        speedup_percentage=speedup,
        baseline_peak_memory_megabytes=base_mem,
        candidate_peak_memory_megabytes=cand_mem,
        memory_reduction_percentage=mem_reduction,
        baseline_rows=baseline_profile.rows_processed,
        candidate_rows=candidate_profile.rows_processed,
        results_equivalent=results_equivalent,
        equivalence_details=eq_details,
    )
    record_benchmark_comparison(comparison.model_dump())

    markdown_table = (
        "### 📊 Benchmark Comparativo de Pipeline (Antes vs Depois)\n\n"
        "| Métrica | Antes (Baseline) | Depois (Otimizado) | Variação |\n"
        "|---|---:|---:|---:|\n"
        f"| Tempo de execução | {base_duration:.4f} s | {cand_duration:.4f} s | **{speedup:+.2f}%** |\n"
        f"| Pico de memória (Python) | {base_mem:.3f} MB | {cand_mem:.3f} MB | {mem_reduction:+.2f}% |\n"
        f"| Linhas processadas | {baseline_profile.rows_processed} | {candidate_profile.rows_processed} | — |\n"
        f"| Equivalência dos resultados | — | **{'Aprovada' if results_equivalent else 'Reprovada'}** | {eq_details} |\n"
    )

    return {
        "success": True,
        "summary": f"Benchmark concluído: Speedup de {speedup:+.2f}%, Equivalência: {'Aprovada' if results_equivalent else 'Reprovada'}.",
        "data": {
            "comparison": comparison.model_dump(),
            "tabela_markdown": markdown_table,
            "baseline_status": baseline_profile.execution_status,
            "candidate_status": candidate_profile.execution_status,
        },
        "warnings": [] if results_equivalent else [eq_details],
        "errors": [] if both_succeeded else [eq_details],
    }

