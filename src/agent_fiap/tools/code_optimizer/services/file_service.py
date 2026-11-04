"""Serviço de gerenciamento de arquivos: leitura segura, escrita autorizada, validação de caminhos e backups."""
from pathlib import Path
from typing import Any

from agent_fiap import config
from agent_fiap.utils import resolve_safe_path


def resolve_pipeline_path(file_path: str | Path = "pipeline/pipeline_prep.py", allow_write: bool = False) -> Path:
    """Resolve caminhos relativos do projeto, aceitando 'pipeline_prep.py' como atalho para 'pipeline/pipeline_prep.py'."""
    clean_path = str(file_path).strip()
    if clean_path in ("pipeline_prep.py", "pipeline_prep"):
        clean_path = "pipeline/pipeline_prep.py"
    elif clean_path in ("pipeline_prep.py.bak", "pipeline_prep.bak"):
        clean_path = "pipeline/pipeline_prep.py.bak"
    return resolve_safe_path(clean_path, allow_write=allow_write)


def read_source_file(file_path: str = "pipeline/pipeline_prep.py") -> dict[str, Any]:
    """Lê o conteúdo de um arquivo do projeto de forma segura."""
    try:
        resolved_path = resolve_pipeline_path(file_path, allow_write=False)
        if not resolved_path.is_file():
            return {
                "success": False,
                "file_path": file_path,
                "content": "",
                "line_count": 0,
                "is_empty": True,
                "error": f"Arquivo não encontrado: {file_path}",
            }

        content = resolved_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        is_empty = len(content.strip()) == 0

        try:
            rel_path = str(resolved_path.relative_to(config.PROJECT_ROOT))
        except ValueError:
            rel_path = str(resolved_path)

        return {
            "success": True,
            "file_path": rel_path,
            "content": content,
            "line_count": len(lines),
            "is_empty": is_empty,
            "error": None,
        }
    except Exception as err:
        return {
            "success": False,
            "file_path": file_path,
            "content": "",
            "line_count": 0,
            "is_empty": True,
            "error": f"Erro ao ler arquivo: {str(err)}",
        }


def create_backup_file(resolved_path: Path) -> Path | None:
    """Cria uma cópia de segurança (.bak) do arquivo caso ele exista e não esteja vazio."""
    if resolved_path.is_file() and resolved_path.stat().st_size > 0:
        backup_path = resolved_path.with_suffix(resolved_path.suffix + ".bak")
        backup_path.write_text(resolved_path.read_text(encoding="utf-8"), encoding="utf-8")
        return backup_path
    return None


def write_source_file(
    file_path: str = "pipeline/pipeline_prep.py",
    content: str = "",
    create_backup: bool = True,
) -> dict[str, Any]:
    """
    Grava o código no disco criando automaticamente backup (.bak) do arquivo original.
    Garante que o diretório de destino exista e respeite os diretórios permitidos.
    """
    if not content or not content.strip():
        return {
            "success": False,
            "file_path": file_path,
            "backup_created": False,
            "error": "O conteúdo do arquivo não pode ser vazio.",
        }

    try:
        resolved_path = resolve_pipeline_path(file_path, allow_write=True)
        resolved_path.parent.mkdir(parents=True, exist_ok=True)

        backup_path = None
        if create_backup:
            backup_path = create_backup_file(resolved_path)

        resolved_path.write_text(content, encoding="utf-8")
        lines = len(content.splitlines())

        try:
            rel_path = str(resolved_path.relative_to(config.PROJECT_ROOT))
        except ValueError:
            rel_path = str(resolved_path)

        return {
            "success": True,
            "file_path": rel_path,
            "line_count": lines,
            "backup_created": backup_path is not None,
            "backup_file": str(backup_path.name) if backup_path else None,
            "error": None,
        }
    except Exception as err:
        return {
            "success": False,
            "file_path": file_path,
            "backup_created": False,
            "error": f"Erro ao gravar arquivo: {str(err)}",
        }
