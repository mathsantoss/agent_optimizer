"""Servidor Web do Kraken Copilot com interface própria, auditoria e percurso de observabilidade.

Estrutura modular FastAPI:
- /api/conversas -> kraken_copilot.web.routes.conversas
- /api/execucoes -> kraken_copilot.web.routes.execucoes
- /api/dados -> kraken_copilot.web.routes.dados
- /web, /web/ui, /ui -> arquivos estáticos do frontend (HTML, UI/CSS, JS, SVG)
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from kraken_copilot.web.routes import conversas_router, dados_router, execucoes_router
from kraken_copilot.web.runner import adk_runner
from kraken_copilot.web.storage import Storage, storage

# Diretório UI contendo os assets estáticos (.html, .svg, .js, .css)
CURRENT_DIR = Path(__file__).resolve().parent
UI_DIR = CURRENT_DIR / "ui"
INDEX_HTML = UI_DIR / "index.html"
INVESTIGACAO_HTML = UI_DIR / "investigacao.html"
DIST_DIR = UI_DIR / "dist"
DIST_INDEX_HTML = DIST_DIR / "index.html"
DIST_ASSETS_DIR = DIST_DIR / "assets"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida do servidor FastAPI."""
    yield


app = FastAPI(
    title="Kraken Copilot",
    description="Interface de Ciência de Dados, Analytics & Engenharia de Pipelines",
    version="1.0.0",
    lifespan=lifespan,
)

# Monta assets do bundle React compilado se existirem
if DIST_ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=DIST_ASSETS_DIR, check_dir=False), name="dist_assets")

# Monta arquivos estáticos do frontend em /web/ui, /ui e /web (retrocompatibilidade)
app.mount("/web/ui", StaticFiles(directory=UI_DIR, check_dir=False), name="web_ui")
app.mount("/ui", StaticFiles(directory=UI_DIR, check_dir=False), name="ui")
app.mount("/web", StaticFiles(directory=UI_DIR, check_dir=False), name="web")

# Registra os roteadores modulares da API REST
app.include_router(conversas_router)
app.include_router(execucoes_router)
app.include_router(dados_router)

# Integração Oficial CopilotKit via AG-UI ADK Middleware
@app.middleware("http")
async def copilotkit_info_interceptor(request: Request, call_next):
    """Intercepta chamadas de descoberta e runtime info do CopilotKit (/info ou probe com method=info)."""
    path = request.url.path.rstrip("/")
    if path == "/api/copilotkit/info":
        return JSONResponse({
            "agents": [
                {
                    "name": "default",
                    "description": "Kraken Copilot - Assistente Google ADK de Engenharia e Otimização de Dados",
                }
            ],
            "version": "1.87.0",
        })
    if path == "/api/copilotkit":
        if request.method == "GET":
            return JSONResponse({
                "agents": [
                    {
                        "name": "default",
                        "description": "Kraken Copilot - Assistente Google ADK de Engenharia e Otimização de Dados",
                    }
                ],
                "version": "1.87.0",
            })
        if request.method == "POST":
            try:
                body = await request.body()
                if body:
                    import json
                    parsed = json.loads(body.decode("utf-8"))
                    if parsed.get("method") == "info" or not parsed.get("threadId"):
                        return JSONResponse({
                            "agents": [
                                {
                                    "name": "default",
                                    "description": "Kraken Copilot - Assistente Google ADK de Engenharia e Otimização de Dados",
                                }
                            ],
                            "version": "1.87.0",
                        })
                async def receive():
                    return {"type": "http.request", "body": body}
                request._receive = receive
            except Exception:
                pass
    return await call_next(request)


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
except Exception as _copilot_err:
    import logging
    logging.getLogger("kraken_copilot").warning("CopilotKit AG-UI endpoint não montado: %s", _copilot_err)


@app.get("/kraken-copilot.svg")
async def rota_logo_kraken():
    """Serve o logotipo oficial do Kraken Copilot."""
    for p in (DIST_DIR / "kraken-copilot.svg", UI_DIR / "kraken-copilot.svg"):
        if p.exists():
            return FileResponse(p, media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Logo não encontrado.")


@app.get("/favicon.ico")
async def rota_favicon():
    """Serve o favicon da aplicação."""
    for p in (DIST_DIR / "kraken-copilot.svg", UI_DIR / "kraken-copilot.svg"):
        if p.exists():
            return FileResponse(p, media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Favicon não encontrado.")


@app.get("/api/modelos")
async def obter_modelos_api():
    """Retorna os modelos da família Gemini disponíveis."""
    from kraken_copilot import config
    clean_current = config.LLM_MODEL.removeprefix("vertex_ai/").removeprefix("gemini/")
    return {
        "modelo_atual": clean_current,
        "modelo_ativo": clean_current,
        "modelos": config.AVAILABLE_GEMINI_MODELS,
    }


# Rotas de Páginas HTML
@app.get("/")
async def rota_raiz():
    """Página principal de chat do Kraken Copilot."""
    if DIST_INDEX_HTML.exists():
        return FileResponse(DIST_INDEX_HTML)
    return FileResponse(INDEX_HTML)


@app.get("/investigar/{execucao_id}")
async def rota_investigacao(execucao_id: str):
    """Página de auditoria e percurso de observabilidade."""
    return FileResponse(INVESTIGACAO_HTML)


def run(host: str = "0.0.0.0", port: int = 8080, reload: bool = False) -> None:
    """Entrypoint Uvicorn idiomático para inicialização do servidor."""
    import uvicorn
    print(f"\n🌊 Iniciando Kraken Copilot Web UI em http://{host}:{port}\n")
    uvicorn.run("kraken_copilot.web.server:app", host=host, port=port, reload=reload)


def main() -> None:
    """Entrypoint CLI consumido por scripts de inicialização."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    reload = os.getenv("RELOAD", "false").lower() in ("true", "1", "yes")
    run(host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
