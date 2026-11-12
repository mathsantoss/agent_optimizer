"""Roteador dedicado à integração oficial CopilotKit e Google ADK via protocolo AG-UI."""
import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse

logger = logging.getLogger("kraken_copilot.web.routes.copilotkit")
copilotkit_router = APIRouter(prefix="/api/copilotkit", tags=["copilotkit"])


@copilotkit_router.get("/info")
@copilotkit_router.post("/info")
async def copilotkit_info_endpoint():
    """Metadados e descoberta de agentes CopilotKit."""
    return JSONResponse({
        "agents": [
            {
                "name": "default",
                "description": "Kraken Copilot - Assistente Google ADK de Engenharia e Otimização de Dados",
            }
        ],
        "version": "1.87.0",
    })


def mount_copilotkit_adk(app) -> None:
    """Monta o middleware e o endpoint do Google ADK no app FastAPI."""
    try:
        from ag_ui_adk import ADKAgent, add_adk_fastapi_endpoint
        from kraken_copilot.agent import kraken_copilot

        copilotkit_adk_agent = ADKAgent(
            adk_agent=kraken_copilot,
            app_name="kraken-copilot",
            user_id="default-user",
            use_in_memory_services=True,
        )
        add_adk_fastapi_endpoint(app, copilotkit_adk_agent, path="/api/copilotkit")
        logger.info("Endpoint CopilotKit AG-UI montado com sucesso em /api/copilotkit")
    except Exception as exc:
        logger.warning("Falha ao montar endpoint CopilotKit AG-UI: %s", exc)

