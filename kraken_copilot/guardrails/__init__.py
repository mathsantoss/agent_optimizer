"""Guardrails determinísticos e callbacks do Google ADK para o Kraken Copilot.

Módulos:
- constants: Constantes, limites e expressões regulares compiladas.
- input_checks: Verificação de segurança de entrada (conteúdo sexual, comandos destrutivos e prompt injection).
- sanitizers: Sanitização de saídas do modelo e dados não confiáveis de datasets externos.
- integrity: Verificação de integridade dos arquivos brutos via snapshot SHA-256.
- callbacks: Callbacks nativos do ciclo de vida do Google ADK (before/after model e tool).
"""

from kraken_copilot.guardrails.callbacks import (
    after_model_guardrail,
    after_tool_guardrail,
    before_model_guardrail,
    before_tool_guardrail,
)
from kraken_copilot.guardrails.constants import (
    DESTRUCTIVE_COMMAND_PATTERNS,
    FAKE_TOOL_CALL_TAG_PATTERN,
    FOREIGN_SCRIPT_PATTERN,
    MAX_AGENT_TRANSFERS,
    MAX_CELL_STRING_LENGTH,
    MAX_SAVE_FILE_ATTEMPTS,
    PROMPT_INJECTION_PATTERNS,
    SEXUAL_CONTENT_PATTERNS,
    THOUGHT_PATTERNS,
)
from kraken_copilot.guardrails.input_checks import (
    check_content_safety,
    check_input_guardrails,
    check_prompt_injection,
)
from kraken_copilot.guardrails.integrity import (
    capture_data_dir_snapshot,
    verify_data_dir_integrity,
)
from kraken_copilot.guardrails.sanitizers import (
    sanitize_model_text,
    sanitize_untrusted_data_text,
)

__all__ = [
    # Constantes e padrões
    "MAX_SAVE_FILE_ATTEMPTS",
    "MAX_AGENT_TRANSFERS",
    "MAX_CELL_STRING_LENGTH",
    "FOREIGN_SCRIPT_PATTERN",
    "FAKE_TOOL_CALL_TAG_PATTERN",
    "THOUGHT_PATTERNS",
    "PROMPT_INJECTION_PATTERNS",
    "SEXUAL_CONTENT_PATTERNS",
    "DESTRUCTIVE_COMMAND_PATTERNS",
    # Verificações de entrada
    "check_content_safety",
    "check_prompt_injection",
    "check_input_guardrails",
    # Sanitização
    "sanitize_model_text",
    "sanitize_untrusted_data_text",
    # Integridade de dados
    "capture_data_dir_snapshot",
    "verify_data_dir_integrity",
    # Callbacks Google ADK
    "before_model_guardrail",
    "after_model_guardrail",
    "before_tool_guardrail",
    "after_tool_guardrail",
]

