"""Serviço de execução automatizada de testes com pytest."""
from pathlib import Path
import subprocess
import sys
from typing import Any

from kraken_ia import config
from kraken_ia.utils import resolve_safe_path

PYTEST_DEFAULT_TIMEOUT_SECONDS = 60


def run_automated_tests(
    target_path: str = "tests",
    timeout_seconds: int = PYTEST_DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Executa a suíte de testes com pytest capturando stdout e código de retorno."""
    try:
        resolved_path = resolve_safe_path(target_path, allow_write=False)
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", str(resolved_path), "-q", "--no-header"],
            cwd=config.PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        combined_output = (proc.stdout + proc.stderr).strip()
        passed = proc.returncode == 0

        return {
            "success": passed,
            "target_path": target_path,
            "return_code": proc.returncode,
            "output": combined_output,
            "summary": "Testes APROVADOS." if passed else "Testes REPROVADOS.",
            "errors": [] if passed else [f"Pytest retornou falhas (exit code {proc.returncode})."],
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "target_path": target_path,
            "return_code": -1,
            "output": "",
            "summary": f"Execução de testes excedeu o limite de {timeout_seconds}s.",
            "errors": [f"Timeout de {timeout_seconds}s ao executar pytest."],
        }
    except Exception as err:
        return {
            "success": False,
            "target_path": target_path,
            "return_code": -1,
            "output": "",
            "summary": f"Erro ao disparar pytest: {str(err)}",
            "errors": [str(err)],
        }

