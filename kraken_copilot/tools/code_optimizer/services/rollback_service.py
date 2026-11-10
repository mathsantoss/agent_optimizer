"""Serviço de restauração segura de backup (.bak) para pipelines."""
from pathlib import Path
from typing import Any

from kraken_copilot import config
from kraken_copilot.schemas import ToolResult
from kraken_copilot.tools.code_optimizer.services.file_service import (
    get_default_workspace_pipeline,
    get_file_tmp_paths,
    resolve_pipeline_path,
)


def execute_pipeline_rollback(file_path: str | Path | None = None) -> dict[str, Any]:
    """Restaura o arquivo a partir da cópia de segurança (.bak)."""
    try:
        if not file_path or not str(file_path).strip():
            file_path = get_default_workspace_pipeline()
        resolved_path = resolve_pipeline_path(file_path, allow_write=True)
        tmp_orig, _ = get_file_tmp_paths(resolved_path)
        backup_path = resolved_path.with_suffix(resolved_path.suffix + ".bak")

        chosen_backup = None
        if tmp_orig.is_file() and tmp_orig.stat().st_size > 0:
            chosen_backup = tmp_orig
        elif backup_path.is_file() and backup_path.stat().st_size > 0:
            chosen_backup = backup_path

        if chosen_backup is None:
            return ToolResult.fail(
                summary=f"Erro de rollback: nenhum backup válido encontrado para '{resolved_path.name}'.",
                operation="rollback_pipeline",
                errors=f"Arquivo de backup não encontrado ou vazio.",
                data={"file_path": file_path, "backup_file": str(tmp_orig.name)},
            ).model_dump()

        backup_content = chosen_backup.read_text(encoding="utf-8")
        resolved_path.write_text(backup_content, encoding="utf-8")

        try:
            rel_path = str(resolved_path.relative_to(config.PROJECT_ROOT))
        except ValueError:
            rel_path = str(resolved_path)

        return ToolResult.ok(
            summary=f"Rollback concluído com sucesso: '{rel_path}' restaurado a partir de '{chosen_backup.name}'.",
            operation="rollback_pipeline",
            data={"file_path": rel_path, "backup_file": str(chosen_backup.name)},
        ).model_dump()
    except Exception as err:
        return ToolResult.fail(
            summary=f"Erro ao executar rollback: {str(err)}",
            operation="rollback_pipeline",
            errors=str(err),
            data={"file_path": file_path, "backup_file": None},
        ).model_dump()

