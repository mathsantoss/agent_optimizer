"""Modelos Pydantic para rotas de exploração de dados, artefatos e documentação."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ArquivoItemSchema(BaseModel):
    """Metadados de um arquivo no catálogo hierárquico."""
    nome: str
    caminho_relativo: str
    formato: str
    tamanho_bytes: int
    tamanho_formatado: str
    categoria: str
    subcategoria: str


class TipoArquivosSchema(BaseModel):
    """Agrupamento de arquivos por extensão/tipo."""
    tipo: str
    label: str
    total: int
    arquivos: List[ArquivoItemSchema] = Field(default_factory=list)


class SecaoHierarquicaSchema(BaseModel):
    """Seção principal da árvore (ex: DATALAKE, OUTPUTS, DOCUMENTAÇÕES)."""
    id: str
    label: str
    icone: str
    total_arquivos: int
    tipos: List[TipoArquivosSchema] = Field(default_factory=list)


class CatalogoArquivosResponse(BaseModel):
    """Resposta com seções hierárquicas populadas."""
    secoes: List[SecaoHierarquicaSchema] = Field(default_factory=list)

