"""Mecanismo de Descoberta e Aplicação de Skills do Google ADK para os Agentes do Kraken Copilot.
Permite carregar e orquestrar skills nativas do Google ADK (google.adk.skills e google.adk.tools.skill_toolset)
instaladas em `.agents/skills/` (ex.: via `npx skills add <repo>`) de forma extensível para qualquer domínio
(gráficos, engenharia de features, refatoração de código, machine learning, integrações externas, etc.).
"""
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

from google.adk.agents import Agent
from google.adk.skills import (
    Skill,
    load_skill_from_dir,
    load_skills_from_dir,
)
from google.adk.tools import skill_toolset
from google.adk.tools.skill_toolset import SkillDiscoveryMode, SkillToolset

from kraken_copilot import config


@dataclass
class SkillInfo:
    """Metadados de uma skill instalada."""
    name: str
    description: str
    directory: Path
    skill_file: Path
    references: list[str] = field(default_factory=list)
    recipes: list[str] = field(default_factory=list)


def _get_skills_dir(base_dir: Path | None = None) -> Path:
    """Retorna o diretório base de skills (.agents/skills)."""
    root = base_dir or config.PROJECT_ROOT
    return root / ".agents" / "skills"


# ==============================================================================
# 1. INTEGRAÇÃO NATIVA COM GOOGLE ADK SKILLS (load_skill_from_dir & SkillToolset)
# ==============================================================================

def load_adk_skills(skills_dir: Path | None = None) -> list[Skill]:
    """
    Carrega todas as skills nativas do Google ADK encontradas em `.agents/skills/`.
    Retorna uma lista de instâncias `google.adk.skills.models.Skill`.
    """
    target_dir = skills_dir or _get_skills_dir()
    if not target_dir.exists() or not target_dir.is_dir():
        return []
    try:
        return load_skills_from_dir(target_dir)
    except Exception:
        # Fallback individual caso alguma skill possua erro de parsing
        skills: list[Skill] = []
        for child in sorted(target_dir.iterdir()):
            if child.is_dir() and (child / "SKILL.md").exists():
                try:
                    s = load_skill_from_dir(child)
                    if s:
                        skills.append(s)
                except Exception:
                    continue
        return skills


def load_adk_skill(skill_name_or_path: str | Path, base_dir: Path | None = None) -> Skill | None:
    """
    Carrega uma skill específica do Google ADK pelo nome ou caminho de diretório.
    Exemplo: load_adk_skill("graphy-charts") ou load_adk_skill(Path(".../weather-skill"))
    """
    if isinstance(skill_name_or_path, Path):
        path = skill_name_or_path
    else:
        path = _get_skills_dir(base_dir) / skill_name_or_path

    if not path.exists() or not path.is_dir():
        return None

    try:
        return load_skill_from_dir(path)
    except Exception:
        return None


def create_adk_skill_toolset(
    skills: list[Skill | str] | None = None,
    additional_tools: list[Any] | None = None,
    discovery_mode: SkillDiscoveryMode = SkillDiscoveryMode.LAZY,
    script_timeout: int = 300,
) -> SkillToolset:
    """
    Constrói um `SkillToolset` do Google ADK a partir de uma lista de skills (objetos Skill ou nomes de pastas)
    e ferramentas adicionais opcionais.
    
    Permite aos agentes executar dinamicamente:
    - list_skills
    - load_skill
    - load_skill_resource
    - run_skill_script
    - ferramentas adicionais vinculadas ao toolset
    """
    resolved_skills: list[Skill] = []
    if skills is None:
        resolved_skills = load_adk_skills()
    else:
        for item in skills:
            if isinstance(item, Skill):
                resolved_skills.append(item)
            elif isinstance(item, str):
                s = load_adk_skill(item)
                if s:
                    resolved_skills.append(s)

    return skill_toolset.SkillToolset(
        skills=resolved_skills,
        additional_tools=additional_tools,
        discovery_mode=discovery_mode,
        script_timeout=script_timeout,
    )


def create_skill_enabled_agent(
    name: str,
    skills: list[Skill | str] | None = None,
    additional_tools: list[Any] | None = None,
    model: Any = None,
    description: str = "",
    instruction: str = "",
    discovery_mode: SkillDiscoveryMode = SkillDiscoveryMode.LAZY,
) -> Agent:
    """
    Cria um Agente Google ADK habilitado com Skills através de um SkillToolset nativo.
    
    Exemplo de uso:
        graphy_skill = load_adk_skill("graphy-charts")
        agent = create_skill_enabled_agent(
            name="chart_visualizer",
            skills=[graphy_skill],
            instruction="Especialista em criar gráficos usando o Graphy SDK."
        )
    """
    from kraken_copilot.agent import language_model
    selected_model = model or language_model

    toolset = create_adk_skill_toolset(
        skills=skills,
        additional_tools=additional_tools,
        discovery_mode=discovery_mode,
    )

    return Agent(
        name=name,
        model=selected_model,
        description=description or f"Agente especialista Google ADK com suporte a skills.",
        instruction=instruction or "Você é um assistente especialista habilitado com skills modulares para executar tarefas avançadas.",
        tools=[toolset],
    )


# ==============================================================================
# 2. DESCOBERTA E METADADOS DE SKILLS PARA O SISTEMA KRAKEN
# ==============================================================================

def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Extrai o frontmatter YAML (---\n...\n---) e o corpo markdown."""
    frontmatter: dict[str, str] = {}
    body = content

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if match:
        raw_yaml = match.group(1)
        body = match.group(2)
        for line in raw_yaml.splitlines():
            line = line.strip()
            if ":" in line:
                key, val = line.split(":", 1)
                frontmatter[key.strip().lower()] = val.strip().strip("\"'")

    return frontmatter, body.strip()


def discover_skills(base_dir: Path | None = None) -> dict[str, SkillInfo]:
    """
    Descobre todas as skills instaladas em `.agents/skills/` no workspace.
    """
    skills_dir = _get_skills_dir(base_dir)
    skills: dict[str, SkillInfo] = {}
    if not skills_dir.exists() or not skills_dir.is_dir():
        return skills

    for skill_path in sorted(skills_dir.iterdir()):
        if not skill_path.is_dir():
            continue

        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            continue

        try:
            content = skill_md.read_text(encoding="utf-8")
            meta, _ = _parse_frontmatter(content)
            name = meta.get("name", skill_path.name)
            desc = meta.get("description", f"Skill {skill_path.name}")

            refs = [p.name for p in (skill_path / "reference").glob("*.md")] if (skill_path / "reference").exists() else []
            recipes = [p.name for p in (skill_path / "recipes").glob("**/*.md")] if (skill_path / "recipes").exists() else []

            skills[name] = SkillInfo(
                name=name,
                description=desc,
                directory=skill_path,
                skill_file=skill_md,
                references=refs,
                recipes=recipes,
            )
        except Exception:
            continue

    return skills


def get_skill_content(skill_name: str, base_dir: Path | None = None) -> str | None:
    """Retorna o conteúdo completo do SKILL.md de uma skill específica."""
    skills = discover_skills(base_dir)
    skill = skills.get(skill_name)
    if not skill:
        return None
    try:
        return skill.skill_file.read_text(encoding="utf-8")
    except Exception:
        return None


def get_agent_skills_instruction(agent_name: str, base_dir: Path | None = None) -> str:
    """
    Gera dinamicamente a seção de instruções de skills aplicáveis a um agente específico
    com base nas skills do Google ADK instaladas em `.agents/skills/`.
    """
    skills = discover_skills(base_dir)
    if not skills:
        return ""

    relevant_skills: list[SkillInfo] = []

    if agent_name == "kraken_analyst":
        for name, info in skills.items():
            if any(k in name.lower() for k in ("graphy", "chart", "viz", "plot", "analytics")):
                relevant_skills.append(info)
    elif agent_name in ("kraken_code", "kraken_optimizer"):
        for name, info in skills.items():
            if any(k in name.lower() for k in ("diff", "patch", "code", "syntax")):
                relevant_skills.append(info)
    else:
        relevant_skills = list(skills.values())

    if not relevant_skills:
        return ""

    lines = [
        "\n==================================================",
        "SKILLS INSTALADAS APLICADAS AO SEU REPERTÓRIO (GOOGLE ADK SKILLS):",
        "==================================================",
    ]

    for skill in relevant_skills:
        lines.append(f"\n[SKILL ADK: {skill.name.upper()}]")
        lines.append(f"Descrição: {skill.description}")
        lines.append(f"Diretório: {skill.directory}")

        if "graphy" in skill.name:
            lines.append("Diretriz Graphy SDK (@graphysdk/react):")
            lines.append("- O frontend possui o Graphy SDK e renderizador vetorial multi-gráfico.")
            lines.append("- Estrutura padrão de especificação JSON em blocos ```chart:")
            lines.append("  { 'type': 'bar'|'line'|'area'|'donut'|'pie'|'scatter', 'title': '...', 'x': 'col_x', 'y': 'col_y', 'data': [...] }")
            lines.append("- Para dashboards compostos com múltiplos gráficos, utilize:")
            lines.append("  { 'charts': [ { 'type': 'line', ... }, { 'type': 'donut', ... } ] }")

    return "\n".join(lines)
