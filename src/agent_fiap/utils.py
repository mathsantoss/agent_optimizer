"""Funções utilitárias do projeto Agent FIAP."""
from pathlib import Path
from . import config


def safe_path(path: str, write: bool = False) -> Path:
    """Resolve `path` e garante que está numa pasta permitida (bloqueia '..' e symlinks)."""
    p = Path(path).expanduser()
    p = (p if p.is_absolute() else config.PROJECT_ROOT / p).resolve()
    allowed = config.WRITE_DIRS if write else config.READ_DIRS
    if not any(p == d or d in p.parents for d in allowed):
        nomes = ", ".join(d.name + "/" for d in allowed)
        raise PermissionError(f"Acesso negado: '{path}' fora das pastas permitidas ({nomes}).")
    return p

