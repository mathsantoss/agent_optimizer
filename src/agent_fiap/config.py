"""Configurações centralizadas do projeto e variáveis de ambiente (.env)."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env na raiz do repositório
_REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_REPO_ROOT / ".env", override=False)

# Diretórios do projeto
PROJECT_ROOT = Path(os.getenv("AGENT_FIAP_ROOT", _REPO_ROOT)).resolve()
DATA_DIR = (PROJECT_ROOT / os.getenv("AGENT_FIAP_DATA_DIR", "pipeline/dados")).resolve()
KNOWLEDGE_DIR = PROJECT_ROOT / "docs" / "conhecimento"  # documentos opcionais para o RAG

# O agente só lê nestas pastas e só escreve nas pastas de escrita.
READ_DIRS = [PROJECT_ROOT / d for d in ("pipeline", "src", "tests", "docs")]
WRITE_DIRS = [PROJECT_ROOT / d for d in ("pipeline", "tests")]

# Configuração do Modelo via LiteLLM (lida diretamente do .env)
LLM_MODEL = os.getenv("LLM_MODEL", "ollama_chat/qwen3.6:35b-a3b")
LLM_API_KEY = os.getenv("LLM_API_KEY") or None
LLM_API_BASE = os.getenv("LLM_API_BASE") or None
