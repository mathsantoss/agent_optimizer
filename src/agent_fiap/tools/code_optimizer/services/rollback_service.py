"""Serviço de restauração segura de backup (.bak) para pipelines."""
from pathlib import Path
from typing import Any

from agent_fiap import config
from agent_fiap.tools.code_optimizer.services.file_service import resolve_pipeline_path


def execute_pipeline_rollback(file_path: str = "pipeline/pipeline_prep.py") -> dict[str, Any]:
    """Restaura o arquivo a partir da cópia de segurança (.bak)."""
    try:
        resolved_path = resolve_pipeline_path(file_path, allow_write=True)
        backup_path = resolved_path.with_suffix(resolved_path.suffix + ".bak")

        if not backup_path.is_file() or backup_path.stat().st_size == 0:
            return {
                "success": False,
                "file_path": file_path,
                "backup_file": str(backup_path.name),
                "summary": f"Erro de rollback: nenhum backup válido encontrado em '{backup_path.name}'.",
                "errors": [f"Arquivo de backup '{backup_path.name}' não encontrado ou vazio."],
            }

        backup_content = backup_path.read_text(encoding="utf-8")
        resolved_path.write_text(backup_content, encoding="utf-8")

        try:
            rel_path = str(resolved_path.relative_to(config.PROJECT_ROOT))
        except ValueError:
            rel_path = str(resolved_path)

        return {
            "success": True,
            "file_path": rel_path,
            "backup_file": str(backup_path.name),
            "summary": f"Rollback concluído com sucesso: '{rel_path}' restaurado a partir de '{backup_path.name}'.",
            "errors": [],
        }
    except Exception as err:
        return {
            "success": False,
            "file_path": file_path,
            "backup_file": None,
            "summary": f"Erro ao executar rollback: {str(err)}",
            "errors": [str(err)],
        }

