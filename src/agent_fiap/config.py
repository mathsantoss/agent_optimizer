"""Configurações centralizadas do projeto e variáveis de ambiente (.env)."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env na raiz do repositório
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPOSITORY_ROOT / ".env", override=False)

# Diretórios do projeto
PROJECT_ROOT = Path(os.getenv("AGENT_FIAP_ROOT", REPOSITORY_ROOT)).resolve()
DATA_DIR = (PROJECT_ROOT / os.getenv("AGENT_FIAP_DATA_DIR", "pipeline/dados")).resolve()
KNOWLEDGE_DIR = PROJECT_ROOT / "docs" / "conhecimento"

# Diretórios autorizados para leitura e escrita pelo agente
READ_DIRS = [PROJECT_ROOT / directory for directory in ("pipeline", "src", "tests", "docs")]
WRITE_DIRS = [PROJECT_ROOT / directory for directory in ("pipeline", "tests")]

# Configuração do Modelo via LiteLLM (lida diretamente do .env)
LLM_MODEL = os.getenv("LLM_MODEL", "ollama_chat/qwen3.6:35b-a3b")
LLM_API_KEY = os.getenv("LLM_API_KEY") or None
LLM_API_BASE = os.getenv("LLM_API_BASE") or None
