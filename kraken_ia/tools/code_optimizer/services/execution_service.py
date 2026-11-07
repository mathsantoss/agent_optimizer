"""Serviço de execução controlada de pipelines com limite de tempo e proteção estrita de integridade de dados."""
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from kraken_ia import config
from kraken_ia.guardrails import capture_data_dir_snapshot, verify_data_dir_integrity
from kraken_ia.tools.code_optimizer.services.file_service import resolve_pipeline_path

PIPELINE_EXECUTION_TIMEOUT_SECONDS = 60


def execute_pipeline_script(
    file_path: str = "pipeline/pipeline_prep.py",
    timeout_seconds: int = PIPELINE_EXECUTION_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    Executa o script de pipeline com interpretador Python em subprocesso isolado.
    Monitora a integridade de pipeline/dados/ antes e depois da execução.
    """
    try:
        resolved_path = resolve_pipeline_path(file_path, allow_write=False)
        if not resolved_path.is_file() or resolved_path.stat().st_size == 0:
            return {
                "success": False,
                "file_path": file_path,
                "duration_seconds": 0.0,
                "output": "",
                "errors": [f"Arquivo '{file_path}' está vazio ou não existe para execução."],
            }

        try:
            rel_path = str(resolved_path.relative_to(config.PROJECT_ROOT))
        except ValueError:
            rel_path = str(resolved_path)

        data_snapshot_before = capture_data_dir_snapshot()
        start_ts = time.perf_counter()

        try:
            proc = subprocess.run(
                [sys.executable, str(resolved_path)],
                cwd=config.PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "file_path": rel_path,
                "duration_seconds": float(timeout_seconds),
                "output": "",
                "errors": [f"Execução do pipeline interrompida: excedeu o tempo limite de {timeout_seconds}s."],
            }

        elapsed = round(time.perf_counter() - start_ts, 3)

        # Checa guardrail de integridade de dados brutos
        violations = verify_data_dir_integrity(data_snapshot_before)
        if violations:
            return {
                "success": False,
                "file_path": rel_path,
                "duration_seconds": elapsed,
                "output": proc.stdout.strip(),
                "errors": ["VIOLAÇÃO DE GUARDRAIL DE INTEGRIDADE: " + " ".join(violations)],
            }

        if proc.returncode == 0:
            out_msg = proc.stdout.strip() if proc.stdout.strip() else "(executou com sucesso, sem saída padrão)"
            return {
                "success": True,
                "file_path": rel_path,
                "duration_seconds": elapsed,
                "output": out_msg,
                "errors": [],
            }

        return {
            "success": False,
            "file_path": rel_path,
            "duration_seconds": elapsed,
            "output": proc.stdout.strip(),
            "errors": [f"Falha na execução (código {proc.returncode}):\n{proc.stderr.strip()}"],
        }
    except Exception as err:
        return {
            "success": False,
            "file_path": file_path,
            "duration_seconds": 0.0,
            "output": "",
            "errors": [f"Erro ao executar pipeline: {str(err)}"],
        }

