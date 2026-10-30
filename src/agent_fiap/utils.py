"""Funções utilitárias para validação e resolução segura de caminhos de arquivos."""
from pathlib import Path
from . import config


def resolve_safe_path(file_path: str, allow_write: bool = False) -> Path:
    """Resolve o caminho informado e garante que pertence a um diretório permitido do projeto."""
    expanded_path = Path(file_path).expanduser()
    resolved_path = (
        expanded_path if expanded_path.is_absolute() else config.PROJECT_ROOT / expanded_path
    ).resolve()

    allowed_directories = config.WRITE_DIRS if allow_write else config.READ_DIRS
    is_allowed = any(
        resolved_path == directory or directory in resolved_path.parents
        for directory in allowed_directories
    )

    if not is_allowed:
        directory_names = ", ".join(f"{directory.name}/" for directory in allowed_directories)
        raise PermissionError(
            f"Acesso negado: '{file_path}' está fora das pastas permitidas ({directory_names})."
        )

    return resolved_path
