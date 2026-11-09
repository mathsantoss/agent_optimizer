"""Contratos de dados estruturados para a base de conhecimento (RAG), dicionário e busca semântica."""
from typing import Any
from pydantic import BaseModel, Field


class KnowledgeChunkMetadata(BaseModel):
    """Metadados enriquecidos de um trecho indexado na base de conhecimento (RAG)."""

    source_path: str = Field(description="Caminho relativo do arquivo de origem")
    file_name: str = Field(description="Nome do arquivo de origem")
    section_title: str = Field(default="Geral", description="Título da seção ou bloco do documento")
    category: str = Field(default="dicionario_dados", description="Categoria do documento")
    related_table: str = Field(default="", description="Tabela de dados relacionada")
    language: str = Field(default="json", description="Formato ou linguagem do conteúdo")
    updated_at: str = Field(default="", description="Data de atualização informada no documento")
    content_hash: str = Field(description="Hash SHA-256 do conteúdo do chunk para atualização incremental")
    indexed_at: str = Field(description="Timestamp ISO-8601 da última indexação do chunk")


class KnowledgeIndexSyncReport(BaseModel):
    """Relatório de sincronização incremental do índice RAG."""

    last_indexed_at: str = Field(default="", description="Data e hora ISO-8601 da sincronização")
    indexed_at: str = Field(default="", description="Data e hora ISO-8601 da sincronização (alias)")
    total_active_chunks: int = Field(default=0, description="Total de chunks ativos na coleção após sincronização")
    added_or_updated_chunks: int = Field(default=0, description="Quantidade de chunks novos ou alterados reindexados")
    unchanged_chunks: int = Field(default=0, description="Quantidade de chunks sem alteração reaproveitados")
    removed_chunks: int = Field(default=0, description="Quantidade de chunks órfãos removidos da coleção")
    synced_files: list[str] = Field(default_factory=list, description="Arquivos avaliados no ciclo de sincronização")

    def __init__(self, **data: Any):
        if "indexed_at" in data and not data.get("last_indexed_at"):
            data["last_indexed_at"] = data["indexed_at"]
        elif "last_indexed_at" in data and not data.get("indexed_at"):
            data["indexed_at"] = data["last_indexed_at"]
        super().__init__(**data)


class KnowledgeSearchResultItem(BaseModel):
    """Item individual retornado na recuperação semântica da base de conhecimento."""

    relevancia: float = Field(description="Pontuação de relevância combinada (0.0 a 1.0)")
    origem: str = Field(description="Arquivo de origem do trecho")
    secao: str = Field(default="Geral", description="Seção ou título do bloco de conhecimento")
    categoria: str = Field(default="dicionario_dados", description="Categoria do conteúdo")
    tabela: str = Field(default="", description="Nome da tabela relacionada se aplicável")
    atualizado_em: str = Field(default="N/A", description="Data da última revisão do documento")
    conteudo: str = Field(description="Texto descritivo recuperado")


class KnowledgeSearchResponse(BaseModel):
    """Contrato padronizado para respostas do serviço de busca semântica na base de conhecimento."""

    success: bool = Field(default=True, description="Indica se a operação de busca foi executada com sucesso")
    operation: str = Field(default="search_knowledge_base", description="Identificador da operação")
    summary: str = Field(description="Resumo claro do resultado da busca em linguagem natural")
    data: dict[str, Any] = Field(default_factory=dict, description="Dados estruturados da consulta e resultados")
    warnings: list[str] = Field(default_factory=list, description="Alertas ou avisos de escopo")
    errors: list[str] = Field(default_factory=list, description="Erros impeditivos se houver")

