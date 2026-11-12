"""Módulo de rotas FastAPI do Kraken Copilot."""
from kraken_copilot.web.routes.conversas import router as conversas_router
from kraken_copilot.web.routes.copilotkit import copilotkit_router, mount_copilotkit_adk
from kraken_copilot.web.routes.dados import router as dados_router
from kraken_copilot.web.routes.execucoes import router as execucoes_router

__all__ = ["conversas_router", "copilotkit_router", "mount_copilotkit_adk", "dados_router", "execucoes_router"]

