"""Mecanismo de Descoberta e Aplicação de Skills do Google ADK para os Agentes do Kraken Copilot."""
from kraken_copilot.schemas.skills import SkillInfo
from kraken_copilot.skills.loader import (
    _get_skills_dir,
    create_adk_skill_toolset,
    create_skill_enabled_agent,
    discover_skills,
    get_agent_skills_instruction,
    get_skill_content,
    load_adk_skill,
    load_adk_skills,
)

__all__ = [
    "SkillInfo",
    "_get_skills_dir",
    "create_adk_skill_toolset",
    "create_skill_enabled_agent",
    "discover_skills",
    "get_agent_skills_instruction",
    "get_skill_content",
    "load_adk_skill",
    "load_adk_skills",
]
