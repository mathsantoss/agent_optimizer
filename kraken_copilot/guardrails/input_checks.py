"""Guardrails de validação de entrada (segurança de conteúdo, comandos e prompt injection)."""
from kraken_copilot.audit_logger import record_guardrail_event
from kraken_copilot.guardrails.constants import (
    DESTRUCTIVE_COMMAND_PATTERNS,
    PROMPT_INJECTION_PATTERNS,
    SEXUAL_CONTENT_PATTERNS,
)
from kraken_copilot.schemas.guardrail import GuardrailCheckResult


def check_content_safety(text: str) -> GuardrailCheckResult:
    """
    Verifica se a mensagem contém solicitações ou conteúdos com teor sexual/adulto
    ou comandos destrutivos de sistema. Retorna GuardrailCheckResult com resposta educada.
    """
    if not text or not text.strip():
        return GuardrailCheckResult(allowed=True)

    for pattern in SEXUAL_CONTENT_PATTERNS:
        if pattern.search(text):
            record_guardrail_event(
                "CONTENT_SAFETY",
                "check_content_safety",
                "BLOQUEADO",
                "Conteúdo com teor sexual ou adulto bloqueado pelo guardrail.",
            )
            return GuardrailCheckResult(
                allowed=False,
                category="SEXUAL_CONTENT",
                polite_response=(
                    "Como assistente corporativo de engenharia de dados, analytics e pipelines da Kraken Copilot, "
                    "meu foco é estritamente técnico e profissional. Não abordo nem processo conteúdos com teor sexual ou adulto. "
                    "Como posso ajudar com a exploração de dados, pipelines ou métricas do seu projeto?"
                ),
                reason="Conteúdo com teor sexual ou adulto detectado.",
            )

    for pattern in DESTRUCTIVE_COMMAND_PATTERNS:
        if pattern.search(text):
            record_guardrail_event(
                "DESTRUCTIVE_COMMAND",
                "check_content_safety",
                "BLOQUEADO",
                "Comando destrutivo de sistema detectado.",
            )
            return GuardrailCheckResult(
                allowed=False,
                category="DESTRUCTIVE_COMMAND",
                polite_response=(
                    "Comando de alto risco não autorizado. O Kraken Copilot executa operações apenas em "
                    "ambientes sandbox e arquivos do workspace permitidos."
                ),
                reason="Comando destrutivo detectado.",
            )

    return GuardrailCheckResult(allowed=True)


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


def check_input_guardrails(text: str) -> GuardrailCheckResult:
    """Executa a bateria completa de guardrails de entrada (conteúdo sexual, comandos e prompt injection)."""
    safety = check_content_safety(text)
    if not safety.allowed:
        return safety

    injection_msg = check_prompt_injection(text)
    if injection_msg:
        return GuardrailCheckResult(
            allowed=False,
            category="PROMPT_INJECTION",
            polite_response=injection_msg,
            reason="Tentativa de sobrescrever diretrizes do sistema (Prompt Injection).",
        )

    return GuardrailCheckResult(allowed=True)

