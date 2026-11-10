"""Runner central do Google ADK para o Kraken Copilot com suporte a cache de contexto e troca dinâmica de modelos."""
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps import App
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner

from kraken_copilot import config
from kraken_copilot.agent import kraken_copilot

adk_app = App(
    name="kraken_copilot",
    root_agent=kraken_copilot,
    context_cache_config=ContextCacheConfig(),
)
adk_runner = InMemoryRunner(app=adk_app)

_LITE_LLM_CACHE: dict[str, LiteLlm] = {}

AVAILABLE_GEMINI_MODELS = config.AVAILABLE_GEMINI_MODELS


def resolve_gemini_model_name(model_name: str | None) -> str:
    """Resolve o identificador de modelo com prefixo adequado do provedor (vertex_ai/ ou gemini/)."""
    if not model_name or not model_name.strip():
        return config.LLM_MODEL
    clean = model_name.strip()
    if clean.startswith("vertex_ai/") or clean.startswith("gemini/"):
        return clean
    if config.GOOGLE_GENAI_USE_VERTEXAI:
        return f"vertex_ai/{clean}"
    return f"gemini/{clean}"


def set_runner_model(model_name: str) -> str:
    """Atualiza dinamicamente o modelo do kraken_copilot e de todos os subagentes."""
    resolved = resolve_gemini_model_name(model_name)
    if resolved not in _LITE_LLM_CACHE:
        _LITE_LLM_CACHE[resolved] = LiteLlm(
            model=resolved,
            api_key=config.LLM_API_KEY,
            api_base=config.LLM_API_BASE,
        )
    llm_instance = _LITE_LLM_CACHE[resolved]
    kraken_copilot.model = llm_instance
    for sub in getattr(kraken_copilot, "sub_agents", []):
        sub.model = llm_instance
    return resolved
