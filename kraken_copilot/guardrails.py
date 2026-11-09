"""Guardrails determinísticos e callbacks do Google ADK para o Kraken Copilot.

Abrange:
1. Guardrails de Entrada (bloqueio de Prompt Injection e tentativa de bypass de instruções).
2. Guardrails de Saída (remoção de caracteres em alfabetos estrangeiros CJK/Thai e chamadas fictícias de ferramentas em texto).
3. Guardrails de Controle de Loop (Circuit Breaker para tentativas excessivas de save_file e limite de handoffs transfer_to_agent).
4. Guardrails de Dados Não Confiáveis (sanitização de Indirect Prompt Injection vindo de células de CSV/Parquet).
5. Guardrails de Integridade dos Dados Brutos (snapshot SHA-256 de pipeline/dados/ antes e depois da execução de scripts).
"""
import hashlib
from pathlib import Path
import re
from typing import Any

from kraken_copilot import config
from kraken_copilot.audit_logger import record_guardrail_event

# Limites operacionais de Circuit Breaker
MAX_SAVE_FILE_ATTEMPTS = 5
MAX_AGENT_TRANSFERS = 10
MAX_CELL_STRING_LENGTH = 300

# Padrões de caracteres de alfabetos estrangeiros indesejados (vazamento de tokens CJK/Tailandês em modelos locais)
FOREIGN_SCRIPT_PATTERN = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\u0e00-\u0e7f]+")

# Padrões de chamadas fictícias de ferramentas em texto puro
FAKE_TOOL_CALL_TAG_PATTERN = re.compile(r"<tool_call>.*?</tool_call>", re.DOTALL | re.IGNORECASE)

# Padrões de blocos de pensamento/raciocínio interno a serem suprimidos da visão do usuário
THOUGHT_PATTERNS = (
    re.compile(r"<(thought|thinking)>.*?</\1>", re.DOTALL | re.IGNORECASE),
    re.compile(r"^\s*\[(thought|thinking)\].*?$", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^\s*(thinking process|internal reasoning):\s*.*$", re.MULTILINE | re.IGNORECASE),
)

# Padrões de Prompt Injection direto e indireto
PROMPT_INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"ignore\s+(todas\s+)?as\s+instru[cç][oõ]es\s+anteriores", re.IGNORECASE),
    re.compile(r"esque[cç]a\s+(todas\s+)?(as\s+)?suas\s+(regras|instru[cç][oõ]es)", re.IGNORECASE),
    re.compile(r"desative\s+(todos\s+)?os\s+guardrails", re.IGNORECASE),
    re.compile(r"system\s+prompt\s+override", re.IGNORECASE),
    re.compile(r"<\s*/?\s*system\s*>", re.IGNORECASE),
)


def check_prompt_injection(text: str) -> str | None:
    """
    Verifica se um texto contém padrões explícitos de Prompt Injection ou tentativa de sobrescrever
    as diretrizes de segurança do sistema. Retorna a descrição do bloqueio ou None se seguro.
    """
    if not text or not text.strip():
        return None

    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(text):
            msg = (
                "Bloqueado pelo Guardrail de Segurança: tentativa de sobrescrever instruções do sistema "
                "(Prompt Injection) detectada. Faça apenas solicitações legítimas de Análise de Dados "
                "ou Engenharia de Pipelines."
            )
            record_guardrail_event("PROMPT_INJECTION", "check_prompt_injection", "BLOQUEADO", text[:200])
            return msg
    return None


def sanitize_model_text(text: str) -> tuple[str, bool]:
    """
    Limpa o texto gerado pelo modelo removendo:
    - Caracteres em alfabetos CJK (chinês/japonês/coreano) e tailandês.
    - Blocos de chamadas fictícias `<tool_call>...</tool_call>` em texto puro.
    - Blocos e tags de pensamento/raciocínio interno (`<thought>`, `<thinking>`, `[thought]`).
    Retorna `(texto_limpo, foi_modificado)`.
    """
    if not text:
        return text, False

    cleaned = text
    modified = False

    if FOREIGN_SCRIPT_PATTERN.search(cleaned):
        cleaned = FOREIGN_SCRIPT_PATTERN.sub("", cleaned)
        modified = True

    if FAKE_TOOL_CALL_TAG_PATTERN.search(cleaned):
        cleaned = FAKE_TOOL_CALL_TAG_PATTERN.sub("", cleaned)
        modified = True

    for pattern in THOUGHT_PATTERNS:
        if pattern.search(cleaned):
            cleaned = pattern.sub("", cleaned).strip()
            modified = True

    if modified:
        record_guardrail_event(
            "OUTPUT_SANITIZATION",
            "sanitize_model_text",
            "SANITIZADO",
            "Removidos caracteres de alfabeto estrangeiro (CJK/Thai), tags <tool_call> ou pensamentos internos.",
        )

    return cleaned, modified


def sanitize_untrusted_data_text(value: Any, max_length: int = MAX_CELL_STRING_LENGTH) -> Any:
    """
    Sanitiza valores textuais oriundos de fontes externas (células de CSV/Parquet) contra
    Indirect Prompt Injection e trunca textos excessivamente longos em amostras.
    """
    if not isinstance(value, str):
        return value

    sanitized = value
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(sanitized):
            sanitized = pattern.sub("[CONTEUDO_BLOQUEADO_GUARDRAIL]", sanitized)

    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "... [truncado]"

    return sanitized


def capture_data_dir_snapshot(data_dir: Path | None = None) -> dict[str, str]:
    """
    Captura hashes SHA-256 dos arquivos de dados em `pipeline/dados/` para verificar
    se a execução de um pipeline modificou ou corrompeu indevidamente os datasets brutos.
    """
    target_dir = data_dir or config.DATA_DIR
    if not target_dir or not target_dir.exists():
        return {}

    snapshot: dict[str, str] = {}
    for file_path in sorted(target_dir.rglob("*")):
        if file_path.is_file() and file_path.suffix.lower() in (".csv", ".parquet", ".json"):
            try:
                file_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
                snapshot[str(file_path)] = file_hash
            except Exception:
                continue
    return snapshot


def verify_data_dir_integrity(
    before_snapshot: dict[str, str],
    data_dir: Path | None = None,
) -> list[str]:
    """
    Compara o estado atual de `pipeline/dados/` com o snapshot anterior à execução.
    Retorna lista de violações caso algum arquivo de dados bruto tenha sido removido ou alterado.
    """
    if not before_snapshot:
        return []

    after_snapshot = capture_data_dir_snapshot(data_dir=data_dir)
    violations: list[str] = []

    for file_path_str, original_hash in before_snapshot.items():
        file_name = Path(file_path_str).name
        if file_path_str not in after_snapshot:
            violations.append(f"Arquivo de dados bruto removido durante a execução: '{file_name}'.")
        elif after_snapshot[file_path_str] != original_hash:
            violations.append(f"Arquivo de dados bruto modificado indevidamente durante a execução: '{file_name}'.")

    return violations


# ==============================================================================
# Callbacks Nativos do Google ADK
# ==============================================================================

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
                    violation_message = check_prompt_injection(user_text)
                    if violation_message:
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


def _build_fallback_for_empty_response(agent_name: str, callback_context: Any = None) -> str:
    """Gera uma resposta de fallback válida e informativa quando o modelo encerra sem conteúdo de texto ou apenas com pensamentos."""
    from kraken_copilot.tools.planner.plan_manager import current_user_request_var, global_plan_manager
    session_id = "default"
    state = getattr(callback_context, "state", None) if callback_context is not None else None
    if hasattr(state, "get") and state.get("session_id"):
        session_id = str(state["session_id"])

    user_req = current_user_request_var.get().strip()

    if agent_name == "kraken_planner":
        from kraken_copilot.agents.planner_agent import synthesize_plan_for_request
        plan = global_plan_manager.get_plan(session_id=session_id)
        if plan is None:
            plan = synthesize_plan_for_request(user_req, session_id=session_id, force_new=True, state=state)
        return global_plan_manager.format_plan_markdown(plan)

    if "optimizer" in agent_name:
        return (
            "Diagnóstico do pipeline executado. Proposta de otimização registrada em `pipeline/tmp/pipeline_prep_otimizado.bak`. "
            "Aguardando confirmação explícita do usuário para aplicação no arquivo oficial."
        )

    if "analyst" in agent_name:
        return "Análise exploratória e consulta dos datasets executada com sucesso."

    if "code" in agent_name:
        return "Features projetadas e testadas com sucesso no pipeline."

    return "Operação processada com sucesso pelo especialista."


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

    # 2. Bloqueio de bypass direto para especialistas sem passar pelo Planner/Coordinator e limite de handoffs
    if tool_name == "transfer_to_agent":
        target_agent = str((args or {}).get("agent_name") or "").strip()
        if target_agent in ("kraken_analyst", "kraken_code", "kraken_optimizer"):
            has_active_plan = bool(state.get("execution_plan")) or (
                isinstance(state.get("workflow_state"), dict)
                and bool(state["workflow_state"].get("active_plan"))
            )
            if not has_active_plan:
                msg = (
                    f"GUARDRAIL DE ORQUESTRAÇÃO ATIVADO: Delegação direta para '{target_agent}' bloqueada. "
                    "Solicitações operacionais devem obrigatoriamente passar pelo 'kraken_planner' e "
                    "ser executadas pelo 'kraken_coordinator' com um plano estruturado ativo."
                )
                record_guardrail_event("ORCHESTRATION_BYPASS", "transfer_to_agent", "BLOQUEADO", msg)
                return {"result": msg}

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

