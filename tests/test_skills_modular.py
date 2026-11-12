"""Testes unitários para o pacote kraken_copilot.skills."""
from pathlib import Path
from kraken_copilot.skills import (
    discover_skills,
    get_agent_skills_instruction,
    get_skill_content,
    _get_skills_dir,
)


def test_skills_dir_resolution():
    skills_dir = _get_skills_dir()
    assert skills_dir.exists()
    assert skills_dir.is_dir()
    assert (skills_dir / "graphy-charts").exists()


def test_discover_skills():
    skills = discover_skills()
    assert len(skills) > 0
    assert "graphy-charts" in skills
    assert "data-analysis" in skills

    graphy = skills["graphy-charts"]
    assert graphy.name == "graphy-charts"
    assert (graphy.directory / "SKILL.md").exists()


def test_get_skill_content():
    content = get_skill_content("graphy-charts")
    assert content is not None
    assert "graphy" in content.lower()


def test_get_agent_skills_instruction():
    instruction = get_agent_skills_instruction("kraken_analyst")
    assert "SKILLS INSTALADAS APLICADAS AO SEU REPERTÓRIO" in instruction
    assert "GRAPHY" in instruction

