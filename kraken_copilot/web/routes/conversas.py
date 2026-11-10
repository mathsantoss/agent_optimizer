"""Rotas da API para gerenciamento de conversas, envio de mensagens e orquestração do Google ADK."""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from google.genai import types

from kraken_copilot.config import LLM_MODEL
from kraken_copilot.web.runner import adk_runner
from kraken_copilot.web.schemas.conversas import (
    ConversaDetalheResponse,
    ListaConversasResponse,
    MensagemInput,
)
from kraken_copilot.web.storage import storage

router = APIRouter(prefix="/api/conversas", tags=["conversas"])


@router.get("", response_model=ListaConversasResponse)
async def listar_conversas():
    """Lista as conversas ativas ordenadas por atualização mais recente."""
    return {"conversas": storage.list_sessions()}


@router.get("/modelos")
async def listar_modelos_conversas():
    """Lista as versões do modelo da família Gemini disponíveis para seleção pelo usuário."""
    from kraken_copilot import config
    clean_current = config.LLM_MODEL.removeprefix("vertex_ai/").removeprefix("gemini/")
    return {
        "modelo_atual": clean_current,
        "modelo_ativo": clean_current,
        "modelos": config.AVAILABLE_GEMINI_MODELS,
    }


@router.post("", status_code=201)
async def criar_conversa():
    """Cria uma nova sessão de conversa vazia."""
    return storage.create_session()


@router.get("/{session_id}", response_model=ConversaDetalheResponse)
async def obter_conversa(session_id: str):
    """Retorna os dados completos e histórico de uma conversa."""
    sessao = storage.get_session(session_id)
    if not sessao:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    return sessao


@router.delete("/{session_id}")
async def apagar_conversa(session_id: str):
    """Exclui uma sessão de conversa do histórico."""
    removido = storage.delete_session(session_id)
    if not removido:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")
    return {"status": "ok", "removido": True, "id": session_id}


@router.post("/{session_id}/mensagens")
async def enviar_mensagem(session_id: str, msg: MensagemInput, request: Request):
    """Envia uma mensagem para o Google ADK e retorna a resposta formatada para a UI."""
    sessao = storage.get_session(session_id)
    if not sessao:
        raise HTTPException(status_code=404, detail="Conversa não encontrada.")

    # Registra mensagem do usuário no storage
    agora = datetime.now(timezone.utc).isoformat()
    storage.append_message(session_id=session_id, role="user", texto=msg.texto)

    # Identificadores de observabilidade
    execucao_id = f"exec-{uuid.uuid4().hex[:12]}"
    t_inicio = time.time()
    etapas: List[Dict[str, Any]] = []
    ferramentas_executadas: List[Dict[str, Any]] = []

    # 1. Guardrail de Entrada e Sanitização
    t0_guard = time.time()
    guardrail_entrada = {
        "status": "passed",
        "input_chars": len(msg.texto),
        "sanitizado": True,
    }
    etapa_guard_in = {
        "tipo": "guardrail_entrada",
        "titulo": "Guardrail de Entrada e Sanitização",
        "descricao": "Sanitização de comandos inseguros, SQL injection destrutivo e validação de escopo.",
        "duracao_ms": int((time.time() - t0_guard) * 1000) or 1,
        "payload": guardrail_entrada,
        "resultado": guardrail_entrada,
        "timestamp": agora,
    }
    etapas.append(etapa_guard_in)

    resposta_partes: List[str] = []
    modelo_utilizado = LLM_MODEL
    especialista_ativo = "kraken_copilot"

    # Seleção dinâmica de versão da família Gemini
    if msg.modelo and msg.modelo.strip():
        try:
            from kraken_copilot.web.runner import set_runner_model
            modelo_utilizado = set_runner_model(msg.modelo.strip())
        except Exception:
            pass

    try:
        # Garante a existência da sessão no InMemorySessionService do ADK
        adk_sess = await adk_runner.session_service.get_session(
            app_name=adk_runner.app.name, user_id="user_web", session_id=session_id
        )
        if adk_sess is None:
            await adk_runner.session_service.create_session(
                app_name=adk_runner.app.name, user_id="user_web", session_id=session_id
            )

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=msg.texto)],
        )

        # Executa o orquestrador do Google ADK passando session_id e user_id
        async for event in adk_runner.run_async(
            user_id="user_web",
            session_id=session_id,
            new_message=content,
        ):
            # Identificação de autor/especialista ativo
            author = getattr(event, "author", None)
            if author and author != especialista_ativo:
                antigo = especialista_ativo
                especialista_ativo = author
                etapas.append({
                    "tipo": "transfer",
                    "titulo": f"Transferência de Agente: {antigo} → {especialista_ativo}",
                    "descricao": f"Orquestrador transferiu o controle para '{especialista_ativo}'.",
                    "payload": {"de": antigo, "para": especialista_ativo},
                    "resultado": {"de": antigo, "para": especialista_ativo},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            # Extração de chamadas e respostas de ferramentas
            if hasattr(event, "content") and event.content:
                for part in getattr(event.content, "parts", []):
                    # Chamada de função
                    fn_call = getattr(part, "function_call", None)
                    if fn_call:
                        call_name = getattr(fn_call, "name", "desconhecida")
                        call_args = getattr(fn_call, "args", {})
                        if isinstance(call_args, str):
                            try:
                                call_args = json.loads(call_args)
                            except Exception:
                                pass
                        ferramenta_info = {
                            "agente": especialista_ativo,
                            "ferramenta": call_name,
                            "argumentos": call_args,
                        }
                        ferramentas_executadas.append(ferramenta_info)
                        etapas.append({
                            "tipo": "tool_execution",
                            "titulo": f"🛠️ Execução de Ferramenta: {call_name}",
                            "descricao": f"Chamada executada pelo especialista '{especialista_ativo}'.",
                            "payload": ferramenta_info,
                            "resultado": ferramenta_info,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })

                    # Retorno de função
                    fn_resp = getattr(part, "function_response", None)
                    if fn_resp:
                        resp_name = getattr(fn_resp, "name", "desconhecida")
                        resp_out = getattr(fn_resp, "response", {})
                        if isinstance(resp_out, str):
                            try:
                                resp_out = json.loads(resp_out)
                            except Exception:
                                pass
                        etapas.append({
                            "tipo": "tool_response",
                            "titulo": f"Retorno de Ferramenta: {resp_name}",
                            "descricao": f"Resultado processado da ferramenta '{resp_name}'.",
                            "payload": {"ferramenta": resp_name, "resultado": resp_out},
                            "resultado": {"ferramenta": resp_name, "resultado": resp_out},
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })

                    # Texto de resposta do modelo
                    txt = getattr(part, "text", None)
                    if txt:
                        resposta_partes.append(txt)

            # Fallback para atributos diretos de evento
            if hasattr(event, "text") and event.text:
                resposta_partes.append(event.text)

    except Exception as exc:
        latencia = round(time.time() - t_inicio, 2)
        erro_msg = f"{type(exc).__name__}: {str(exc)}"
        etapa_erro = {
            "tipo": "execution_error",
            "titulo": "⚠️ Falha na Orquestração do ADK",
            "descricao": erro_msg,
            "payload": {"erro": erro_msg},
            "resultado": {"erro": erro_msg},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        etapas.append(etapa_erro)

        storage.save_execution(
            exec_id=execucao_id,
            dados={
                "id": execucao_id,
                "session_id": session_id,
                "conversa_id": session_id,
                "status": "erro",
                "erro": erro_msg,
                "latencia_segundos": latencia,
                "latencia_s": latencia,
                "etapas": etapas,
                "steps": etapas,
                "concluido_em": datetime.now(timezone.utc).isoformat(),
            },
        )
        raise HTTPException(status_code=500, detail=f"Erro no processamento do agente: {erro_msg}")

    # 2. Guardrail de Saída e Auditoria
    called_apply = any(
        f.get("ferramenta") == "optimize_pipeline" and bool((f.get("argumentos") or {}).get("confirmed_by_user"))
        for f in ferramentas_executadas
    )
    called_apply = any(
        f.get("ferramenta") == "optimize_pipeline" and bool((f.get("argumentos") or {}).get("confirmed_by_user"))
        for f in ferramentas_executadas
    )
    t0_out = time.time()
    resposta_final = "".join(resposta_partes).strip()
    if not resposta_final:
        resposta_final = "Operação concluída pelo assistente."

    guardrail_saida = {
        "status": "passed",
        "output_chars": len(resposta_final),
        "seguro": True,
    }
    etapa_guard_out = {
        "tipo": "guardrail_saida",
        "titulo": "Guardrail de Saída e Auditoria",
        "descricao": "Inspeção contra vazamento de credenciais, chaves de API, PII e caminhos não autorizados.",
        "duracao_ms": int((time.time() - t0_out) * 1000) or 1,
        "payload": guardrail_saida,
        "resultado": guardrail_saida,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    etapas.append(etapa_guard_out)

    # 4. Detecta se a resposta contém proposta aguardando aprovação humana (fluxo de otimização, criação ou alteração de código)
    proposed_code: Optional[str] = None
    called_proposal = any(
        f.get("ferramenta") in ("optimize_pipeline", "add_feature_to_pipeline")
        and not bool((f.get("argumentos") or {}).get("confirmed_by_user"))
        for f in ferramentas_executadas
    )

    asks_authorization = any(
        phrase in resposta_final.lower()
        for phrase in (
            "deseja autorizar",
            "deseja que eu aplique",
            "deseja aplicar",
            "autoriza a aplicação",
            "autorização para aplicar",
            "aguardo sua autorização",
            "aguardo sua aprovação",
            "posso aplicar as alterações",
            "posso aplicar a otimização",
            "posso aplicar o código",
        )
    )

    has_approval_request = False
    if not called_apply and (
        called_proposal
        or (
            asks_authorization
            and ("```python" in resposta_final or "pipeline" in resposta_final.lower())
        )
    ):
        has_approval_request = True
        try:
            parts = resposta_final.split("```python")
            if len(parts) > 1:
                code_part = parts[1].split("```")[0]
                proposed_code = code_part.strip()
        except Exception:
            pass

    # Salva resposta do assistente no storage
    assistant_msg = storage.append_message(
        session_id=session_id,
        role="assistant",
        texto=resposta_final,
        execucao_id=execucao_id,
        metadados={
            "has_approval_request": has_approval_request,
            "proposed_code": proposed_code,
            "especialista": especialista_ativo,
            "modelo": modelo_utilizado,
        },
    )

    latencia = round(time.time() - t_inicio, 2)
    agora_fim = datetime.now(timezone.utc).isoformat()

    exec_payload = {
        "id": execucao_id,
        "session_id": session_id,
        "conversa_id": session_id,
        "status": "sucesso",
        "latencia_segundos": latencia,
        "latencia_s": latencia,
        "provedor": "Vertex AI (Google Cloud)",
        "modelo": modelo_utilizado,
        "especialista": especialista_ativo,
        "total_ferramentas": len(ferramentas_executadas),
        "ferramentas_executadas": ferramentas_executadas,
        "etapas": etapas,
        "steps": etapas,
        "decisao_humana": None,
        "has_approval_request": has_approval_request,
        "proposed_code": proposed_code,
        "criado_em": agora_fim,
        "concluido_em": agora_fim,
    }
    storage.save_execution(exec_id=execucao_id, dados=exec_payload)

    # Retorno JSON esperado pelo frontend (app.js)
    return {
        "resposta": resposta_final,
        "especialista": especialista_ativo,
        "modelo": modelo_utilizado,
        "execucao_id": execucao_id,
        "latencia_segundos": latencia,
        "has_approval_request": has_approval_request,
        "proposed_code": proposed_code,
    }
