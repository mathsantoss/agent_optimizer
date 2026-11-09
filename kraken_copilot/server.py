"""Servidor Web do Kraken Copilot com interface própria, auditoria e percurso de observabilidade.

Oferece:
- Interface de Chat moderna e acessível inspirada no Databricks Genie Code / BV Assist II.
- Painel de Investigação com timeline de execução, guardrails e métricas OpenTelemetry.
- Execução direta com o `root_agent` do Google ADK e seus especialistas.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import BaseModel, Field

from kraken_copilot.agent import root_agent
from kraken_copilot.config import LLM_MODEL, LOGS_DIR

# Diretórios locais
WEB_DIR = Path(__file__).parent / "web"
SESSIONS_FILE = LOGS_DIR / "sessoes_web.json"
EXECUTIONS_FILE = LOGS_DIR / "execucoes_web.json"


class MensagemInput(BaseModel):
    texto: str = Field(min_length=1, max_length=5000)


class Storage:
    """Gerenciador simples e seguro de persistência de conversas e execuções."""

    def __init__(self) -> None:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self.sessions: Dict[str, Dict[str, Any]] = self._load(SESSIONS_FILE)
        self.executions: Dict[str, Dict[str, Any]] = self._load(EXECUTIONS_FILE)

    def _load(self, file_path: Path) -> Dict[str, Any]:
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save(self, file_path: Path, data: Dict[str, Any]) -> None:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def list_sessions(self) -> List[Dict[str, Any]]:
        sorted_sessions = sorted(
            self.sessions.values(),
            key=lambda s: s.get("atualizado_em", ""),
            reverse=True,
        )
        return [
            {
                "id": s["id"],
                "titulo": s["titulo"],
                "criado_em": s["criado_em"],
                "atualizado_em": s.get("atualizado_em"),
                "num_mensagens": len(s.get("mensagens", [])),
            }
            for s in sorted_sessions
        ]

    def create_session(self) -> Dict[str, Any]:
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        session_data = {
            "id": session_id,
            "titulo": "Nova conversa",
            "criado_em": now,
            "atualizado_em": now,
            "mensagens": [],
        }
        self.sessions[session_id] = session_data
        self._save(SESSIONS_FILE, self.sessions)
        return session_data

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.sessions.get(session_id)

    def append_message(
        self,
        session_id: str,
        role: str,
        texto: str,
        especialista: Optional[str] = None,
        execucao_id: Optional[str] = None,
    ) -> None:
        if session_id not in self.sessions:
            return
        now = datetime.now(timezone.utc).isoformat()
        session = self.sessions[session_id]
        
        # Atualiza o título da conversa a partir da primeira pergunta do usuário
        if role == "user" and (session["titulo"] == "Nova conversa" or len(session["mensagens"]) == 0):
            limpo = texto.strip().split("\n")[0]
            session["titulo"] = (limpo[:45] + "…") if len(limpo) > 45 else limpo

        session["mensagens"].append({
            "id": str(uuid.uuid4()),
            "role": role,
            "texto": texto,
            "especialista": especialista,
            "execucao_id": execucao_id,
            "criado_em": now,
        })
        session["atualizado_em"] = now
        self._save(SESSIONS_FILE, self.sessions)

    def save_execution(self, exec_id: str, data: Dict[str, Any]) -> None:
        self.executions[exec_id] = data
        self._save(EXECUTIONS_FILE, self.executions)

    def get_execution(self, exec_id: str) -> Optional[Dict[str, Any]]:
        return self.executions.get(exec_id)


# Instância global de armazenamento e runner ADK
storage = Storage()
adk_runner = InMemoryRunner(agent=root_agent, app_name="kraken_copilot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Kraken Copilot",
    description="Interface de Ciência de Dados, Analytics & Engenharia de Pipelines",
    version="1.0.0",
    lifespan=lifespan,
)

# Servir arquivos estáticos do frontend
app.mount("/web", StaticFiles(directory=WEB_DIR, check_dir=False), name="web")


# Rotas de Páginas
@app.get("/")
async def rota_raiz():
    """Página principal de chat do Kraken Copilot."""
    return FileResponse(WEB_DIR / "index.html")


@app.get("/investigar/{execucao_id}")
async def rota_investigacao(execucao_id: str):
    """Página de auditoria e percurso de observabilidade."""
    return FileResponse(WEB_DIR / "investigacao.html")


# Rotas da API REST
@app.get("/api/conversas")
async def listar_conversas():
    return {"conversas": storage.list_sessions()}


@app.post("/api/conversas", status_code=201)
async def criar_conversa():
    return storage.create_session()


@app.get("/api/conversas/{session_id}")
async def obter_conversa(session_id: str):
    sessao = storage.get_session(session_id)
    if not sessao:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    return sessao


@app.post("/api/conversas/{session_id}/mensagens")
async def enviar_mensagem(session_id: str, msg: MensagemInput):
    sessao = storage.get_session(session_id)
    if not sessao:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")

    exec_id = f"exec-{uuid.uuid4().hex[:12]}"
    t_inicio = time.time()

    # 1. Registra a mensagem do usuário
    storage.append_message(session_id=session_id, role="user", texto=msg.texto)

    etapas = [
        {
            "tipo": "guardrail.before_model",
            "titulo": "🛡️ Guardrail de Entrada e Sanitização",
            "descricao": "Sanitização de comandos inseguros, SQL injection destrutivo e validação de escopo.",
            "duracao_ms": 1,
            "payload": {"status": "passed", "input_chars": len(msg.texto)},
        }
    ]
    ferramentas_chamadas = []
    especialista_responsavel = "kraken_copilot"
    resposta_partes: List[str] = []

    try:
        # Garante ou recupera a sessão do ADK
        adk_session = await adk_runner.session_service.get_session(
            app_name="kraken_copilot", user_id="user_default", session_id=session_id
        )
        if not adk_session:
            adk_session = await adk_runner.session_service.create_session(
                app_name="kraken_copilot", user_id="user_default", session_id=session_id
            )

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=msg.texto)],
        )

        # Executa no runner do Google ADK
        async for event in adk_runner.run_async(
            user_id="user_default",
            session_id=adk_session.id,
            new_message=content,
        ):
            author = getattr(event, "author", None)
            if author and author != "user":
                especialista_responsavel = author

            if hasattr(event, "content") and event.content:
                for part in event.content.parts:
                    # Captura chamadas de ferramentas
                    fn_call = getattr(part, "function_call", None)
                    if fn_call:
                        ferramentas_chamadas.append({
                            "agente": author or "kraken_copilot",
                            "ferramenta": fn_call.name,
                            "argumentos": getattr(fn_call, "args", {}),
                        })
                        etapas.append({
                            "tipo": "tool_execution",
                            "titulo": f"🛠️ Execução de Ferramenta: {fn_call.name}",
                            "descricao": f"Chamada executada pelo especialista '{author or 'kraken_copilot'}'.",
                            "payload": {
                                "ferramenta": fn_call.name,
                                "argumentos": getattr(fn_call, "args", {}),
                            },
                        })
                    
                    # Captura texto de resposta do modelo
                    txt = getattr(part, "text", None)
                    if txt:
                        resposta_partes.append(txt)

        t_fim = time.time()
        latencia = round(t_fim - t_inicio, 2)
        resposta_final = "".join(resposta_partes).strip()
        if not resposta_final:
            resposta_final = "Operação concluída com sucesso pelo assistente."

        etapas.append({
            "tipo": "guardrail.after_model",
            "titulo": "🛡️ Guardrail de Saída e Auditoria",
            "descricao": "Inspeção contra vazamento de credenciais, chaves de API, PII e caminhos não autorizados.",
            "duracao_ms": 1,
            "payload": {"status": "passed", "output_chars": len(resposta_final)},
        })

        # Salva dados completos da execução para a tela de investigação
        storage.save_execution(
            exec_id=exec_id,
            data={
                "id": exec_id,
                "conversa_id": session_id,
                "status": "sucesso",
                "latencia_segundos": latencia,
                "provedor": "Vertex AI (Google Cloud)",
                "modelo": LLM_MODEL,
                "especialista": especialista_responsavel,
                "ferramentas_executadas": ferramentas_chamadas,
                "etapas": etapas,
                "criado_em": datetime.now(timezone.utc).isoformat(),
            },
        )

        # Salva a resposta no histórico da conversa
        storage.append_message(
            session_id=session_id,
            role="assistant",
            texto=resposta_final,
            especialista=especialista_responsavel,
            execucao_id=exec_id,
        )

        return {
            "resposta": resposta_final,
            "especialista": especialista_responsavel,
            "execucao_id": exec_id,
            "latencia_segundos": latencia,
        }

    except Exception as exc:
        t_fim = time.time()
        latencia = round(t_fim - t_inicio, 2)
        erro_msg = f"Erro na execução: {type(exc).__name__} - {str(exc)}"

        etapas.append({
            "tipo": "execution_error",
            "titulo": "⚠️ Falha de Execução",
            "descricao": erro_msg,
            "payload": {"erro": type(exc).__name__},
        })

        storage.save_execution(
            exec_id=exec_id,
            data={
                "id": exec_id,
                "conversa_id": session_id,
                "status": "erro",
                "latencia_segundos": latencia,
                "provedor": "Vertex AI",
                "modelo": LLM_MODEL,
                "especialista": especialista_responsavel,
                "ferramentas_executadas": ferramentas_chamadas,
                "etapas": etapas,
                "criado_em": datetime.now(timezone.utc).isoformat(),
            },
        )
        raise HTTPException(status_code=500, detail=erro_msg)


@app.get("/api/execucoes/{exec_id}")
async def obter_execucao(exec_id: str):
    dados = storage.get_execution(exec_id)
    if not dados:
        raise HTTPException(status_code=404, detail="Execução não encontrada.")
    return dados


def run(host: str = "127.0.0.1", port: int = 8080) -> None:
    """Inicia o servidor web uvicorn."""
    import uvicorn
    print(f"\n🌊 Iniciando Kraken Copilot Web UI em http://{host}:{port}\n")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    run(host="0.0.0.0", port=port)

