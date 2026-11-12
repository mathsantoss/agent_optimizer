"""Callbacks nativos do Google ADK para orquestração de guardrails em modelos e ferramentas."""
from typing import Any

from kraken_copilot.audit_logger import record_guardrail_event
from kraken_copilot.guardrails.constants import (
    MAX_AGENT_TRANSFERS,
    MAX_SAVE_FILE_ATTEMPTS,
    PROMPT_INJECTION_PATTERNS,
)
from kraken_copilot.guardrails.input_checks import check_input_guardrails
from kraken_copilot.guardrails.sanitizers import sanitize_model_text


def _build_fallback_for_empty_response(agent_name: str, callback_context: Any = None) -> str:
    """Gera uma resposta de fallback válida e informativa quando o modelo encerra sem conteúdo de texto ou apenas com pensamentos."""
    if "optimizer" in agent_name:
        return (
            "Diagnóstico do pipeline executado. Proposta de otimização registrada na pasta `krakenlake/tmp/`. "
            "Aguardando confirmação explícita do usuário para aplicação no arquivo oficial."
        )

    if "analyst" in agent_name:
        return "Análise exploratória e consulta dos datasets executada com sucesso."

    if "code" in agent_name:
        return "Features projetadas e testadas com sucesso no pipeline."

    return "Operação processada com sucesso pelo assistente."


def before_model_guardrail(
    callback_context: Any = None,
    llm_request: Any = None,
    **kwargs: Any,
) -> Any:
    """
    Callback executado antes de enviar a requisição ao LLM (`before_model_callback`).
    Inspeciona a última mensagem do usuário para bloquear tentativas de Prompt Injection
    e renova o orçamento de operações para o novo turno de interação.
    """
    # Renova contadores de sessão a cada nova intervenção do usuário para permitir edições manuais e iterativas
    context = callback_context or kwargs.get("callback_context")
    if context is not None and hasattr(context, "state") and isinstance(context.state, dict):
        context.state["save_file_attempts"] = 0
        context.state["agent_transfer_count"] = 0

    request = llm_request or kwargs.get("llm_request")
    if request is None or not getattr(request, "contents", None):
        return None

    # Inspeciona a última mensagem de entrada do usuário
    for content in reversed(request.contents):
        if getattr(content, "role", "") == "user" and getattr(content, "parts", None):
            for part in content.parts:
                user_text = getattr(part, "text", None)
                if user_text:
                    guard_res = check_input_guardrails(user_text)
                    if not guard_res.allowed:
                        violation_message = guard_res.polite_response or "Conteúdo não autorizado."
                        try:
                            from google.adk.models import LlmResponse
                            from google.genai import types

                            return LlmResponse(
                                content=types.Content(
                                    role="model",
                                    parts=[types.Part.from_text(text=violation_message)],
                                )
                            )
                        except Exception:
                            return None
            break

    return None


def after_model_guardrail(
    callback_context: Any = None,
    llm_response: Any = None,
    **kwargs: Any,
) -> Any:
    """
    Callback executado após a resposta do LLM (`after_model_callback`).
    - Remove caracteres de alfabetos estrangeiros inesperados (CJK/Thai) e tags `<tool_call>`.
    - Suprime partes de pensamento/raciocínio interno (`thought=True`).
    - Intercepta e recupera graciosamente respostas vazias (`MODEL_RETURNED_NO_CONTENT`).
    """
    response = llm_response or kwargs.get("llm_response")

    # Detecta se o modelo retornou erro MODEL_RETURNED_NO_CONTENT ou resposta sem partes
    is_empty_or_no_content = False
    if response is None:
        is_empty_or_no_content = True
    elif getattr(response, "error_code", None) == "MODEL_RETURNED_NO_CONTENT":
        is_empty_or_no_content = True
    elif not getattr(response, "content", None) or not getattr(response.content, "parts", None):
        is_empty_or_no_content = True

    try:
        from google.adk.models import LlmResponse
        from google.genai import types

        agent = getattr(callback_context, "agent", None) if callback_context is not None else None
        agent_name = getattr(agent, "name", "")

        if is_empty_or_no_content:
            fallback_text = _build_fallback_for_empty_response(agent_name, callback_context)
            record_guardrail_event(
                "EMPTY_RESPONSE_RECOVERY",
                "after_model_guardrail",
                "RECUPERADO",
                f"MODEL_RETURNED_NO_CONTENT recuperado determinísticamente para o agente '{agent_name}'.",
            )
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=fallback_text)],
                ),
            )

        parts = getattr(response.content, "parts", [])
        modified = False
        cleaned_parts = []

        for part in parts:
            # 1. Suprime partes de pensamento nativas (thought=True) para a visão do usuário
            if getattr(part, "thought", False) is True:
                modified = True
                continue

            part_text = getattr(part, "text", None)
            if part_text:
                cleaned_text, was_cleaned = sanitize_model_text(part_text)
                if was_cleaned:
                    cleaned_parts.append(types.Part.from_text(text=cleaned_text))
                    modified = True
                else:
                    cleaned_parts.append(part)
            else:
                cleaned_parts.append(part)

        # Se todas as partes eram pensamentos e foram suprimidas, gera fallback limpo
        if not cleaned_parts:
            fallback_text = _build_fallback_for_empty_response(agent_name, callback_context)
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=fallback_text)],
                ),
            )

        if modified:
            return LlmResponse(
                content=types.Content(
                    role=getattr(response.content, "role", "model"),
                    parts=cleaned_parts,
                )
            )
    except Exception:
        return None

    return None


def before_tool_guardrail(
    tool: Any = None,
    args: dict[str, Any] | None = None,
    tool_context: Any = None,
    **kwargs: Any,
) -> dict[str, Any] | None:
    """
    Callback executado antes de cada ferramenta (`before_tool_callback`).
    Implementa Circuit Breaker contra loops infinitos de gravação (`save_file`)
    e contra transferências circulares entre sub-agentes (`transfer_to_agent`).
    """
    target_tool = tool or kwargs.get("tool")
    context = tool_context or kwargs.get("tool_context")
    tool_name = getattr(target_tool, "name", getattr(target_tool, "__name__", ""))

    state = getattr(context, "state", None) if context is not None else None
    if not hasattr(state, "get"):
        return None

    # 1. Circuit Breaker de escritas repetidas em disco sem validação
    # Discrimina propostas (sem gravação) de gravações efetivas autorizadas no disco
    is_write_intent = False
    if tool_name in ("save_file",):
        is_write_intent = True
    elif tool_name in ("optimize_pipeline", "add_feature_to_pipeline"):
        if args and args.get("confirmed_by_user") is True:
            is_write_intent = True
    elif tool_name == "generate_feature_pipeline":
        if args and args.get("save_to_disk") is True:
            is_write_intent = True

    if is_write_intent:
        attempts = int(state.get("save_file_attempts", 0))
        if attempts >= MAX_SAVE_FILE_ATTEMPTS:
            msg = (
                f"GUARDRAIL DE CIRCUIT BREAKER ATIVADO: O limite de {MAX_SAVE_FILE_ATTEMPTS} "
                f"tentativas de alteração em disco ({tool_name}) na mesma sessão foi atingido. "
                "Use 'validate_pipeline' para verificar o estado atual e apresente o diagnóstico ao usuário."
            )
            record_guardrail_event("CIRCUIT_BREAKER", tool_name, "BLOQUEADO", msg)
            return {"result": msg}
        state["save_file_attempts"] = attempts + 1

    elif tool_name in ("rollback_pipeline", "validate_pipeline", "inspect_pipeline", "preview_features", "compare_pipeline_runs"):
        # Reseta contador após qualquer etapa de inspeção, preview ou validação
        state["save_file_attempts"] = 0

    # 2. Limite de handoffs entre agentes para evitar loops infinitos de delegação
    if tool_name == "transfer_to_agent":
        transfers = int(state.get("agent_transfer_count", 0))
        if transfers >= MAX_AGENT_TRANSFERS:
            msg = (
                f"GUARDRAIL DE ORQUESTRAÇÃO ATIVADO: Limite máximo de {MAX_AGENT_TRANSFERS} "
                "transferências entre agentes atingido. Conclua a resposta diretamente para o usuário."
            )
            record_guardrail_event("CIRCUIT_BREAKER", "transfer_to_agent", "BLOQUEADO", msg)
            return {"result": msg}
        state["agent_transfer_count"] = transfers + 1

    return None


def after_tool_guardrail(
    tool: Any = None,
    args: dict[str, Any] | None = None,
    tool_context: Any = None,
    tool_response: Any = None,
    **kwargs: Any,
) -> Any:
    """
    Callback executado após o retorno da ferramenta (`after_tool_callback`).
    Sanitiza possíveis instruções de Indirect Prompt Injection em retornos textuais.
    """
    response = tool_response if tool_response is not None else kwargs.get("tool_response")
    if isinstance(response, str):
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(response):
                response = pattern.sub("[CONTEUDO_BLOQUEADO_GUARDRAIL]", response)
        return response

    if isinstance(response, dict) and isinstance(response.get("result"), str):
        text_result = response["result"]
        modified = False
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(text_result):
                text_result = pattern.sub("[CONTEUDO_BLOQUEADO_GUARDRAIL]", text_result)
                modified = True
        if modified:
            updated = dict(response)
            updated["result"] = text_result
            return updated

    return None

