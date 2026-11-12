"""Funções de sanitização de texto do modelo e dados não confiáveis."""
from typing import Any

from kraken_copilot.audit_logger import record_guardrail_event
from kraken_copilot.guardrails.constants import (
    FAKE_TOOL_CALL_TAG_PATTERN,
    FOREIGN_SCRIPT_PATTERN,
    MAX_CELL_STRING_LENGTH,
    PROMPT_INJECTION_PATTERNS,
    THOUGHT_PATTERNS,
)


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

