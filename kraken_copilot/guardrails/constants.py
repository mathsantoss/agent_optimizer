"""Constantes, limites operacionais e padrões regex utilizados pelos guardrails."""
import re

# Limites operacionais de Circuit Breaker
MAX_SAVE_FILE_ATTEMPTS: int = 5
MAX_AGENT_TRANSFERS: int = 10
MAX_CELL_STRING_LENGTH: int = 300

# Caracteres de alfabetos estrangeiros indesejados (CJK e Tailandês)
FOREIGN_SCRIPT_PATTERN: re.Pattern[str] = re.compile(
    r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\u0e00-\u0e7f]+"
)

# Chamadas fictícias de ferramentas em texto puro
FAKE_TOOL_CALL_TAG_PATTERN: re.Pattern[str] = re.compile(
    r"<tool_call>.*?</tool_call>", re.DOTALL | re.IGNORECASE
)

# Blocos de pensamento/raciocínio interno a serem suprimidos da visão do usuário
THOUGHT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"<(thought|thinking)>.*?</\1>", re.DOTALL | re.IGNORECASE),
    re.compile(r"^\s*\[(thought|thinking)\].*?$", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^\s*(thinking process|internal reasoning):\s*.*$", re.MULTILINE | re.IGNORECASE),
)

# Padrões de Prompt Injection direto e indireto
PROMPT_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"ignore\s+(todas\s+)?as\s+instru[cç][oõ]es\s+anteriores", re.IGNORECASE),
    re.compile(r"esque[cç]a\s+(todas\s+)?(as\s+)?suas\s+(regras|instru[cç][oõ]es)", re.IGNORECASE),
    re.compile(r"desative\s+(todos\s+)?os\s+guardrails", re.IGNORECASE),
    re.compile(r"system\s+prompt\s+override", re.IGNORECASE),
    re.compile(r"<\s*/?\s*system\s*>", re.IGNORECASE),
)

# Padrões de conteúdo sexual ou adulto inadequado
SEXUAL_CONTENT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(porn\w*|sexo\w*|sexual\w*|er[oó]tic\w*|conte[uú]do\s+adulto|hentai|orgasm\w*|masturba\w*|vagina\w*|p[eê]nis|nude[zs]\w*|prostitui\w*|gemid\w*)\b",
        re.IGNORECASE,
    ),
)

# Padrões de comandos destrutivos ao host/sistema
DESTRUCTIVE_COMMAND_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(rm\s+-rf\s+[/~]|mkfs\b|dd\s+if=|:\(\)\{\s*:\|:&\s*\};:|drop\s+database\b)",
        re.IGNORECASE,
    ),
)

