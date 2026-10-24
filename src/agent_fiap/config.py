"""Caminhos do projeto e regras de acesso a arquivos."""
import os
from pathlib import Path

PROJECT_ROOT = Path(os.getenv("AGENT_FIAP_ROOT", Path(__file__).resolve().parents[2])).resolve()
DATA_DIR = (PROJECT_ROOT / os.getenv("AGENT_FIAP_DATA_DIR", "pipeline/dados")).resolve()
KNOWLEDGE_DIR = PROJECT_ROOT / "docs" / "conhecimento"  # documentos opcionais para o RAG

# O agente só lê nestas pastas e só escreve nas pastas de escrita.
READ_DIRS = [PROJECT_ROOT / d for d in ("pipeline", "src", "tests", "docs")]
WRITE_DIRS = [PROJECT_ROOT / d for d in ("pipeline", "tests")]


def safe_path(path: str, write: bool = False) -> Path:
    """Resolve `path` e garante que está numa pasta permitida (bloqueia '..' e symlinks)."""
    p = Path(path).expanduser()
    p = (p if p.is_absolute() else PROJECT_ROOT / p).resolve()
    allowed = WRITE_DIRS if write else READ_DIRS
    if not any(p == d or d in p.parents for d in allowed):
        nomes = ", ".join(d.name + "/" for d in allowed)
        raise PermissionError(f"Acesso negado: '{path}' fora das pastas permitidas ({nomes}).")
    return p
