"""Schemas Pydantic para Skills do Google ADK e Kraken Copilot."""
from pathlib import Path
from pydantic import BaseModel, Field


class SkillInfo(BaseModel):
    """Metadados de uma skill instalada e descoberta no projeto."""
    name: str = Field(..., description="Nome identificador da skill")
    description: str = Field(..., description="Descrição e propósito da skill")
    directory: Path = Field(..., description="Caminho do diretório da skill")
    skill_file: Path = Field(..., description="Caminho para o arquivo SKILL.md")
    references: list[str] = Field(default_factory=list, description="Arquivos de referência encontrados")
    recipes: list[str] = Field(default_factory=list, description="Receitas e tutoriais disponíveis")

    model_config = {
        "arbitrary_types_allowed": True
    }

