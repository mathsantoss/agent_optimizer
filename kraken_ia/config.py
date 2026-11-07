"""Configurações centralizadas do projeto e variáveis de ambiente (.env)."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env na raiz do repositório
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPOSITORY_ROOT / ".env", override=False)

# Diretórios do projeto
PROJECT_ROOT = Path(os.getenv("KRAKEN_IA_ROOT", REPOSITORY_ROOT)).resolve()
DATA_DIR = (PROJECT_ROOT / os.getenv("KRAKEN_IA_DATA_DIR", "pipeline/dados")).resolve()
KNOWLEDGE_DIR = DATA_DIR / "conhecimento"
LOGS_DIR = (PROJECT_ROOT / os.getenv("KRAKEN_IA_LOGS_DIR", "logs")).resolve()

# Diretórios autorizados para leitura e escrita pelo agente
READ_DIRS = [PROJECT_ROOT / directory for directory in ("pipeline", "kraken_ia", "tests", "docs", "logs")]
WRITE_DIRS = [PROJECT_ROOT / directory for directory in ("pipeline", "tests")]

# Configurações do Google Cloud / Vertex AI (autenticação via ADC gcloud)
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("VERTEXAI_PROJECT")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION") or os.getenv("VERTEXAI_LOCATION", "global")
GOOGLE_GENAI_USE_VERTEXAI = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() in ("true", "1")

if GOOGLE_CLOUD_PROJECT:
    os.environ["GOOGLE_CLOUD_PROJECT"] = GOOGLE_CLOUD_PROJECT
    os.environ["VERTEXAI_PROJECT"] = GOOGLE_CLOUD_PROJECT
if GOOGLE_CLOUD_LOCATION:
    os.environ["GOOGLE_CLOUD_LOCATION"] = GOOGLE_CLOUD_LOCATION
    os.environ["VERTEXAI_LOCATION"] = GOOGLE_CLOUD_LOCATION
if GOOGLE_GENAI_USE_VERTEXAI:
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

# Configuração do Modelo via LiteLLM (lida diretamente do .env)
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")
LLM_API_KEY = os.getenv("LLM_API_KEY") or None
LLM_API_BASE = os.getenv("LLM_API_BASE") or None

# Roteamento automático do provedor no LiteLLM
if GOOGLE_GENAI_USE_VERTEXAI or (LLM_MODEL and LLM_MODEL.startswith("vertex_ai/")):
    # Roteia chamadas para o Google Cloud Vertex AI com autenticação ADC
    if LLM_MODEL and not LLM_MODEL.startswith("vertex_ai/"):
        clean_model = LLM_MODEL.removeprefix("gemini/")
        LLM_MODEL = f"vertex_ai/{clean_model}"
else:
    # Google AI Studio (Gemini Studio API Key) ou Ollama local
    if LLM_MODEL and (LLM_MODEL.startswith("gemini-") or LLM_MODEL.startswith("gemma-")) and not LLM_MODEL.startswith("gemini/"):
        LLM_MODEL = f"gemini/{LLM_MODEL}"

    if LLM_API_KEY:
        if any(k in LLM_MODEL.lower() for k in ("gemini", "gemma")) and not os.getenv("GEMINI_API_KEY"):
            os.environ["GEMINI_API_KEY"] = LLM_API_KEY
