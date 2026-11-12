"""Adaptador de eventos de auditoria integrado ao SQLite e OpenTelemetry (Loki / Grafana).

Grava eventos estruturados de benchmark, profiling, diagnósticos de código, análises de dados
e guardrails diretamente no banco SQLite (`logs/kraken_copilot.db`) e encaminha para o coletor
OpenTelemetry via `emit_telemetry_log`, sem criar arquivos JSON soltos na pasta `logs/`.
"""
import logging
from typing import Any

from kraken_copilot.observability import emit_telemetry_log


def _record_to_sqlite(category: str, action: str, status: str, details: Any = "") -> None:
    """Grava o evento no banco SQLite corporativo."""
    try:
        from kraken_copilot.web.storage import storage
        storage.append_audit_log(category=category, action=action, status=status, details=details)
    except Exception:
        pass


def log_text_event(
    category: str,
    action: str,
    status: str,
    message: str,
) -> None:
    """Registra evento cronológico estruturado no SQLite e no OpenTelemetry Logs (Loki)."""
    _record_to_sqlite(category=category.upper(), action=action, status=status.upper(), details=message)
    emit_telemetry_log(
        "audit_event",
        level=logging.INFO,
        category=category.upper(),
        action=action,
        status=status.upper(),
        summary=str(message)[:240],
    )


def record_benchmark_comparison(comparison_data: dict[str, Any]) -> None:
    """Registra métricas comparativas Antes vs Depois (`compare_pipeline_runs`) no SQLite e OpenTelemetry."""
    equivalent = bool(comparison_data.get("results_equivalent", False))
    _record_to_sqlite(
        category="BENCHMARK",
        action="compare_pipeline_runs",
        status="APROVADA" if equivalent else "REPROVADA",
        details=comparison_data,
    )
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
    """Registra métricas de profiling (`profile_pipeline`) no SQLite e OpenTelemetry."""
    _record_to_sqlite(
        category="PROFILING",
        action="profile_pipeline",
        status=str(profile_data.get("execution_status", "info")).upper(),
        details=profile_data,
    )
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
    """Registra etapas de engenharia e validação de código no SQLite e OpenTelemetry."""
    actual_file_path = file_path or kwargs.get("pipeline_name", "")
    actual_action = action or kwargs.get("action", "validate_pipeline")
    actual_status = status or kwargs.get("status", "SUCESSO")
    actual_details = details or kwargs.get("issues_found") or kwargs.get("details", "")

    _record_to_sqlite(
        category="CODE_VALIDATION",
        action=actual_action,
        status=str(actual_status).upper(),
        details={"file_path": str(actual_file_path), "details": str(actual_details)},
    )
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
    """Registra eventos de exploração de dados, estatísticas e SQL no SQLite e OpenTelemetry."""
    _record_to_sqlite(
        category="DATA_ANALYSIS",
        action=action,
        status=status.upper(),
        details={"target": target, "metrics": summary_metrics},
    )
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
    """Registra acionamentos de guardrails no SQLite e no OpenTelemetry."""
    _record_to_sqlite(
        category=f"GUARDRAIL_{guardrail_type.upper()}",
        action=source,
        status=status.upper(),
        details=description,
    )
    emit_telemetry_log(
        "guardrail_audit",
        level=logging.WARNING,
        guardrail_type=guardrail_type,
        source=source,
        status=status,
        description=str(description)[:240],
    )
