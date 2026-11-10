"""Configurações centralizadas do projeto e variáveis de ambiente (.env)."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env na raiz do repositório
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPOSITORY_ROOT / ".env", override=False)

os.environ.setdefault("ADK_SUPPRESS_GEMINI_LITELLM_WARNINGS", "true")
os.environ.setdefault("LITELLM_LOG", "ERROR")

try:
    import logging
    import litellm

    litellm.suppress_debug_info = True
    litellm.set_verbose = False
    if hasattr(litellm, "verbose_logger"):
        litellm.verbose_logger.setLevel(logging.WARNING)
    logging.getLogger("LiteLLM").setLevel(logging.WARNING)
except Exception:
    pass

# Diretórios do projeto
PROJECT_ROOT = Path(os.getenv("KRAKEN_COPILOT_ROOT", REPOSITORY_ROOT)).resolve()
DATA_DIR = (PROJECT_ROOT / os.getenv("KRAKEN_COPILOT_DATA_DIR", "pipeline/dados")).resolve()
KNOWLEDGE_DIR = DATA_DIR / "conhecimento"
LOGS_DIR = (PROJECT_ROOT / os.getenv("KRAKEN_COPILOT_LOGS_DIR", "logs")).resolve()

# Diretórios autorizados para leitura e escrita pelo agente
READ_DIRS = [PROJECT_ROOT / directory for directory in ("pipeline", "kraken_copilot", "tests", "docs", "logs")]
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


# Versões homologadas da família Gemini disponíveis para seleção pelo usuário (2.5 Flash, 3.x em diante e Argon)
AVAILABLE_GEMINI_MODELS = [
    {
        "id": "gemini-2.5-flash",
        "nome": "Gemini 2.5 Flash",
        "descricao": "Rápido, inteligente e equilibrado (Padrão)",
        "tag": "Padrão",
    },
    {
        "id": "gemini-2.5-flash-lite",
        "nome": "Gemini 2.5 Flash-Lite",
        "descricao": "Ultra-rápido, ágil e eficiente para tarefas diretas",
        "tag": "Lite",
    },
    {
        "id": "gemini-3-flash-preview",
        "nome": "Gemini 3 Flash Preview",
        "descricao": "Inteligência de fronteira e busca avançada",
        "tag": "Geração 3",
    },
    {
        "id": "gemini-3.1-flash-lite",
        "nome": "Gemini 3.1 Flash-Lite",
        "descricao": "Otimizado para agentes e processamento veloz de dados",
        "tag": "Lite 3.1",
    },
    {
        "id": "gemini-3.1-pro-preview",
        "nome": "Gemini 3.1 Pro Preview",
        "descricao": "Raciocínio profundo e multimodalidade de última geração",
        "tag": "Pro 3.1",
    },
    {
        "id": "gemini-3.5-flash-lite",
        "nome": "Gemini 3.5 Flash-Lite",
        "descricao": "Maior throughput da família 3.5 para extração e parsing",
        "tag": "Lite 3.5",
    },
    {
        "id": "gemini-3.5-flash",
        "nome": "Gemini 3.5 Flash",
        "descricao": "Velocidade e performance para cargas contínuas",
        "tag": "Flash 3.5",
    },
    {
        "id": "gemini-3.6-flash",
        "nome": "Gemini 3.6 Flash",
        "descricao": "Equilíbrio agêntico com capacidades multimodais",
        "tag": "Flash 3.6",
    },
    {
        "id": "gemini-3.7-flash",
        "nome": "Gemini 3.7 Flash",
        "descricao": "Alta velocidade para coding diário e chamadas de ferramentas",
        "tag": "Flash 3.7",
    },
    {
        "id": "gemini-3.8-flash",
        "nome": "Gemini 3.8 Flash",
        "descricao": "Engenharia de software e agentes autônomos complexos",
        "tag": "Flash 3.8",
    },
    {
        "id": "gemini-4-argon",
        "nome": "Gemini 4 Argon",
        "descricao": "Modelo de fronteira máxima para engenharia de software complexa",
        "tag": "Argon",
    },
]
