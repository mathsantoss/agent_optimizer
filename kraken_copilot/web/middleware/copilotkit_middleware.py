"""Middleware para interceptação de requisições de descoberta e runtime info do CopilotKit."""
import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class CopilotKitInfoMiddleware(BaseHTTPMiddleware):
    """
    Intercepta chamadas de descoberta e runtime info do CopilotKit (/info, GET /api/copilotkit e probes method=info)
    evitando que probes sem threadId caiam no handler de agente e gerem erro 422.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
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

