"""Exportação centralizada dos prompts e instruções dos agentes."""
from kraken_copilot.prompts.code_optimizer import CODE_OPTIMIZER_AGENT_INSTRUCTION
from kraken_copilot.prompts.common import COMMON_GUIDELINES
from kraken_copilot.prompts.data_analyst import ANALYST_AGENT_INSTRUCTION
from kraken_copilot.prompts.feature_engineer import FEATURE_ENGINEER_AGENT_INSTRUCTION
from kraken_copilot.prompts.orchestrator import KRAKEN_COPILOT_INSTRUCTION

__all__ = [
    "COMMON_GUIDELINES",
    "KRAKEN_COPILOT_INSTRUCTION",
    "ANALYST_AGENT_INSTRUCTION",
    "FEATURE_ENGINEER_AGENT_INSTRUCTION",
    "CODE_OPTIMIZER_AGENT_INSTRUCTION",
]
