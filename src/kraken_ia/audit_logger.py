"""Adaptador de eventos de auditoria integrado ao OpenTelemetry (Loki / Grafana).

Encaminha os eventos de benchmark, profiling, diagnósticos de código, análises de dados
e guardrails diretamente para o coletor OpenTelemetry via `emit_telemetry_log`, sem criar
arquivos locais na pasta `logs/`.
"""
import logging
from typing import Any

from kraken_ia.observability import emit_telemetry_log


def log_text_event(
    category: str,
    action: str,
    status: str,
    message: str,
) -> None:
    """Encaminha evento cronológico estruturado para o OpenTelemetry Logs (Loki)."""
    emit_telemetry_log(
        "audit_event",
        level=logging.INFO,
        category=category.upper(),
        action=action,
        status=status.upper(),
        summary=str(message)[:240],
    )


def record_benchmark_comparison(comparison_data: dict[str, Any]) -> None:
    """Encaminha métricas comparativas Antes vs Depois (`compare_pipeline_runs`) para o OpenTelemetry."""
    equivalent = bool(comparison_data.get("results_equivalent", False))
    emit_telemetry_log(
        "benchmark_comparison",
        level=logging.INFO,
        baseline_file=str(comparison_data.get("baseline_file", "")),
        candidate_file=str(comparison_data.get("candidate_file", "")),
        baseline_duration_seconds=comparison_data.get("baseline_duration_seconds"),
        candidate_duration_seconds=comparison_data.get("candidate_duration_seconds"),
        speedup_percentage=comparison_data.get("speedup_percentage"),
        memory_reduction_percentage=comparison_data.get("memory_reduction_percentage"),
        results_equivalent=equivalent,
        status="APROVADA" if equivalent else "REPROVADA",
    )


def record_pipeline_profile(profile_data: dict[str, Any]) -> None:
    """Encaminha métricas de profiling (`profile_pipeline`) para o OpenTelemetry."""
    emit_telemetry_log(
        "pipeline_profile",
        level=logging.INFO,
        file_path=str(profile_data.get("file_path", "")),
        execution_status=str(profile_data.get("execution_status", "info")),
        duration_seconds=profile_data.get("duration_seconds"),
        peak_memory_megabytes=profile_data.get("peak_memory_megabytes"),
        rows_processed=profile_data.get("rows_processed"),
        column_count=profile_data.get("column_count"),
        output_signature_hash=str(profile_data.get("output_signature_hash", "")),
    )


def record_code_validation_event(
    action: str = "validate_pipeline",
    file_path: str = "",
    status: str = "SUCESSO",
    details: dict[str, Any] | str = "",
    **kwargs: Any,
) -> None:
    """Encaminha etapas de engenharia e validação de código para o OpenTelemetry."""
    actual_file_path = file_path or kwargs.get("pipeline_name", "")
    actual_action = action or kwargs.get("action", "validate_pipeline")
    actual_status = status or kwargs.get("status", "SUCESSO")
    actual_details = details or kwargs.get("issues_found") or kwargs.get("details", "")

    emit_telemetry_log(
        "code_validation",
        level=logging.INFO,
        action=actual_action,
        file_path=str(actual_file_path),
        status=str(actual_status),
        summary=str(actual_details)[:240],
    )


def record_data_analysis_event(
    action: str,
    target: str,
    status: str,
    summary_metrics: dict[str, Any] | str,
) -> None:
    """Encaminha eventos de exploração de dados, estatísticas, SQL e RAG para o OpenTelemetry."""
    emit_telemetry_log(
        "data_analysis",
        level=logging.INFO,
        action=action,
        target=target,
        status=status,
        summary=str(summary_metrics)[:240],
    )


def record_guardrail_event(
    guardrail_type: str,
    source: str,
    status: str,
    description: str,
) -> None:
    """Encaminha acionamentos de guardrails para o OpenTelemetry."""
    emit_telemetry_log(
        "guardrail_audit",
        level=logging.WARNING,
        guardrail_type=guardrail_type,
        source=source,
        status=status,
        description=str(description)[:240],
    )
