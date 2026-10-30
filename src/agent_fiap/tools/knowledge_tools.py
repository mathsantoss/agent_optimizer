"""Ferramentas de busca semântica (RAG) com indexação incremental por hash, chunking estruturado e reranking."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import chromadb

from .. import config
from ..schemas import KnowledgeChunkMetadata, KnowledgeIndexSyncReport

SUPPORTED_KNOWLEDGE_EXTENSIONS = (".json", ".yaml", ".yml", ".md", ".txt", ".sql")
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _get_rag_directory() -> Path:
    """Retorna o diretório de persistência do índice ChromaDB e do manifesto de sincronização."""
    return config.PROJECT_ROOT / ".rag"


def _get_knowledge_collection():
    """Inicializa o cliente persistente do ChromaDB e retorna a coleção de conhecimento."""
    rag_directory = _get_rag_directory()
    rag_directory.mkdir(parents=True, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=str(rag_directory))
    return chroma_client.get_or_create_collection("conhecimento")


def _resolve_knowledge_directory() -> Path | None:
    """
    Localiza o diretório da base de conhecimento priorizando pipeline/dados/conhecimento
    (config.KNOWLEDGE_DIR) com fallback para docs/conhecimento em fixtures de teste.
    """
    if config.KNOWLEDGE_DIR.exists():
        return config.KNOWLEDGE_DIR
    fallback_directory = config.PROJECT_ROOT / "docs" / "conhecimento"
    if fallback_directory.exists():
        return fallback_directory
    docs_root = config.PROJECT_ROOT / "docs"
    if docs_root.exists():
        return docs_root
    return None


def _parse_frontmatter(raw_text: str) -> tuple[dict[str, str], str]:
    """
    Extrai metadados de cabeçalho YAML frontmatter (delimited por ---) ou comentários SQL,
    retornando um dicionário de metadados e o corpo limpo do documento.
    """
    metadata: dict[str, str] = {}
    body_text = raw_text.strip()

    frontmatter_match = FRONTMATTER_PATTERN.match(body_text)
    if frontmatter_match:
        frontmatter_block = frontmatter_match.group(1)
        body_text = body_text[frontmatter_match.end():].strip()
        for line in frontmatter_block.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip().lower()] = value.strip().strip("\"'")
        return metadata, body_text

    reading_header = True
    remaining_lines = []
    for line in body_text.splitlines():
        stripped_line = line.strip()
        if reading_header and stripped_line.startswith("--"):
            comment_content = stripped_line.lstrip("-").strip()
            if ":" in comment_content:
                key, value = comment_content.split(":", 1)
                metadata[key.strip().lower()] = value.strip()
        else:
            reading_header = False
            remaining_lines.append(line)

    if metadata and remaining_lines:
        body_text = "\n".join(remaining_lines).strip()

    return metadata, body_text


def _extract_json_or_yaml_chunks(raw_text: str, file_suffix: str) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """
    Converte arquivos estruturados (.json, .yaml, .yml) de Dicionário de Dados em múltiplos chunks
    semânticos (Visão Geral, Colunas e Tipos, Métricas Derivadas) preservando metadados.
    """
    parsed_data = None
    if file_suffix == ".json":
        parsed_data = json.loads(raw_text)
    else:
        try:
            import yaml  # type: ignore
            parsed_data = yaml.safe_load(raw_text)
        except Exception:
            parsed_data = None

    if not isinstance(parsed_data, dict):
        return {}, [("Geral", raw_text)]

    raw_metadata = parsed_data.get("metadata", {})
    if not isinstance(raw_metadata, dict):
        raw_metadata = {}

    normalized_metadata = {
        "categoria": str(
            raw_metadata.get("category")
            or raw_metadata.get("categoria")
            or parsed_data.get("category")
            or "dicionario_dados"
        ),
        "tabela": str(
            raw_metadata.get("table")
            or raw_metadata.get("tabela")
            or parsed_data.get("table")
            or ""
        ),
        "linguagem": file_suffix.lstrip("."),
        "atualizado_em": str(
            raw_metadata.get("updated_at")
            or raw_metadata.get("atualizado_em")
            or parsed_data.get("updated_at")
            or ""
        ),
    }

    sections: list[tuple[str, str]] = []
    table_name = normalized_metadata["tabela"] or "dataset"
    description = parsed_data.get("description", "")
    primary_keys = parsed_data.get("primary_key_candidates", [])
    columns = parsed_data.get("columns", [])
    derived_metrics = parsed_data.get("derived_metrics_and_conventions", [])

    # Chunk 1: Visão Geral e Chaves da Tabela
    overview_lines = [f"Tabela: {table_name}"]
    if description:
        overview_lines.append(f"Descrição: {description}")
    if primary_keys:
        overview_lines.append(f"Chaves Candidatas (PK): {', '.join(str(key) for key in primary_keys)}")
    if isinstance(columns, list) and columns:
        column_names = [str(col.get("name", "")) for col in columns if isinstance(col, dict)]
        overview_lines.append(f"Colunas disponíveis ({len(column_names)}): {', '.join(column_names)}")
    sections.append(("Visão Geral e Esquema", "\n".join(overview_lines)))

    # Chunk 2: Dicionário Detalhado de Colunas
    if isinstance(columns, list) and columns:
        column_lines = [f"Dicionário de Colunas da Tabela {table_name}:"]
        for column_item in columns:
            if isinstance(column_item, dict):
                col_name = column_item.get("name", "")
                col_type = column_item.get("data_type", "")
                col_desc = column_item.get("description", "")
                col_unit = f" [Unidade: {column_item['unit']}]" if column_item.get("unit") else ""
                column_lines.append(f"- {col_name} ({col_type}){col_unit}: {col_desc}")
        sections.append(("Dicionário de Colunas", "\n".join(column_lines)))

    # Chunk 3: Métricas Derivadas e Regras de Cálculo
    if isinstance(derived_metrics, list) and derived_metrics:
        metric_lines = [f"Métricas Derivadas e Convenções da Tabela {table_name}:"]
        for metric_item in derived_metrics:
            if isinstance(metric_item, dict):
                metric_name = metric_item.get("name", "")
                metric_formula = metric_item.get("formula", "")
                metric_desc = metric_item.get("description", "")
                metric_lines.append(f"- {metric_name} = `{metric_formula}`: {metric_desc}")
        sections.append(("Métricas e Convenções de Cálculo", "\n".join(metric_lines)))

    return normalized_metadata, sections


def _split_into_sections(body_text: str, file_suffix: str) -> list[tuple[str, str]]:
    """
    Divide documentos Markdown em seções lógicas baseadas em subtítulos ('## ').
    Para arquivos curtos ou scripts SQL, mantém o conteúdo em um único bloco.
    """
    if file_suffix != ".md" or "\n## " not in f"\n{body_text}":
        return [("Geral", body_text)]

    sections: list[tuple[str, str]] = []
    raw_parts = re.split(r"(?m)^##\s+", body_text)

    preamble = raw_parts[0].strip()
    if preamble:
        sections.append(("Introdução", preamble))

    for part in raw_parts[1:]:
        lines = part.strip().splitlines()
        if not lines:
            continue
        section_title = lines[0].strip()
        section_content = "\n".join(lines[1:]).strip()
        formatted_section = f"## {section_title}\n{section_content}".strip()
        sections.append((section_title, formatted_section))

    return sections if sections else [("Geral", body_text)]


def synchronize_knowledge_index() -> KnowledgeIndexSyncReport:
    """
    Sincroniza incrementalmente o índice RAG com os arquivos de conhecimento:
    - Calcula hash SHA-256 do conteúdo de cada chunk.
    - Atualiza apenas chunks novos ou cujo hash de conteúdo foi alterado.
    - Remove da coleção chunks órfãos referentes a arquivos/seções excluídos da origem.
    - Registra a data/hora da última indexação em .rag/index_manifest.json.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    collection = _get_knowledge_collection()
    knowledge_directory = _resolve_knowledge_directory()

    existing_records = collection.get(include=["metadatas"])
    existing_ids: list[str] = existing_records.get("ids", []) if existing_records else []
    existing_metadatas: list[dict] = existing_records.get("metadatas", []) if existing_records else []
    existing_hash_by_id: dict[str, str] = {
        record_id: (metadata or {}).get("content_hash", "")
        for record_id, metadata in zip(existing_ids, existing_metadatas)
    }

    if not knowledge_directory or not knowledge_directory.exists():
        if existing_ids:
            collection.delete(ids=existing_ids)
        empty_report = KnowledgeIndexSyncReport(
            last_indexed_at=now_iso,
            total_active_chunks=0,
            added_or_updated_chunks=0,
            unchanged_chunks=0,
            removed_chunks=len(existing_ids),
        )
        return empty_report

    document_files = [
        file_path
        for file_path in sorted(knowledge_directory.rglob("*"))
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_KNOWLEDGE_EXTENSIONS
    ]

    active_chunk_ids: set[str] = set()
    upsert_ids: list[str] = []
    upsert_documents: list[str] = []
    upsert_metadatas: list[dict[str, str]] = []
    unchanged_count = 0

    for file_path in document_files:
        raw_content = file_path.read_text(encoding="utf-8", errors="ignore").strip()
        if not raw_content:
            continue

        relative_path = str(file_path.relative_to(config.PROJECT_ROOT))
        file_suffix = file_path.suffix.lower()

        if file_suffix in (".json", ".yaml", ".yml"):
            parsed_metadata, sections = _extract_json_or_yaml_chunks(raw_content, file_suffix)
            default_language = file_suffix.lstrip(".")
        else:
            parsed_metadata, body_text = _parse_frontmatter(raw_content)
            sections = _split_into_sections(body_text, file_suffix)
            default_language = "sql" if file_suffix == ".sql" else "markdown"

        for section_index, (section_title, section_text) in enumerate(sections):
            cleaned_section = section_text.strip()
            if not cleaned_section:
                continue

            chunk_identifier = hashlib.sha1(
                f"{relative_path}::{section_index}::{section_title}".encode("utf-8")
            ).hexdigest()
            content_hash = hashlib.sha256(cleaned_section.encode("utf-8")).hexdigest()
            active_chunk_ids.add(chunk_identifier)

            if existing_hash_by_id.get(chunk_identifier) == content_hash:
                unchanged_count += 1
                continue

            structured_metadata = KnowledgeChunkMetadata(
                source_path=relative_path,
                file_name=file_path.name,
                section_title=section_title,
                category=parsed_metadata.get("categoria", "dicionario_dados"),
                related_table=parsed_metadata.get("tabela", ""),
                language=parsed_metadata.get("linguagem", default_language),
                updated_at=parsed_metadata.get("atualizado_em", ""),
                content_hash=content_hash,
                indexed_at=now_iso,
            )

            upsert_ids.append(chunk_identifier)
            upsert_documents.append(cleaned_section)
            upsert_metadatas.append({
                "origem": structured_metadata.source_path,
                "nome": structured_metadata.file_name,
                "secao": structured_metadata.section_title,
                "categoria": structured_metadata.category,
                "tabela": structured_metadata.related_table,
                "linguagem": structured_metadata.language,
                "atualizado_em": structured_metadata.updated_at,
                "content_hash": structured_metadata.content_hash,
                "indexed_at": structured_metadata.indexed_at,
            })

    # Remove documentos/chunks que foram excluídos da pasta de origem
    removed_ids = [
        existing_id for existing_id in existing_hash_by_id if existing_id not in active_chunk_ids
    ]
    if removed_ids:
        collection.delete(ids=removed_ids)

    if upsert_ids:
        collection.upsert(
            ids=upsert_ids,
            documents=upsert_documents,
            metadatas=upsert_metadatas,
        )

    sync_report = KnowledgeIndexSyncReport(
        last_indexed_at=now_iso,
        total_active_chunks=len(active_chunk_ids),
        added_or_updated_chunks=len(upsert_ids),
        unchanged_chunks=unchanged_count,
        removed_chunks=len(removed_ids),
    )

    manifest_path = _get_rag_directory() / "index_manifest.json"
    manifest_path.write_text(
        json.dumps(sync_report.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return sync_report


def index_knowledge_documents() -> int:
    """
    Executa a sincronização incremental da base de conhecimento em pipeline/dados/conhecimento/
    e retorna o total de chunks ativos no índice.
    """
    sync_report = synchronize_knowledge_index()
    return sync_report.total_active_chunks


def _compute_hybrid_relevance_score(
    query: str,
    document_text: str,
    metadata: dict,
    semantic_distance: float,
) -> float:
    """
    Calcula score híbrido combinando similaridade semântica vetorial e sobreposição lexical
    de termos da pergunta no texto, seção, categoria e tabela do candidato.
    """
    semantic_score = 1.0 / (1.0 + max(0.0, float(semantic_distance)))
    query_tokens = {
        token
        for token in re.findall(r"[a-zA-ZÀ-ÿ0-9_]+", query.lower())
        if len(token) > 2
    }
    if not query_tokens:
        return round(semantic_score, 4)

    searchable_target = " ".join([
        document_text.lower(),
        str(metadata.get("secao", "")).lower(),
        str(metadata.get("tabela", "")).lower(),
        str(metadata.get("categoria", "")).lower(),
    ])
    matched_tokens = sum(1 for token in query_tokens if token in searchable_target)
    lexical_overlap = matched_tokens / len(query_tokens)

    combined_score = (0.70 * semantic_score) + (0.30 * lexical_overlap)
    return round(combined_score, 4)


def search_knowledge_base(
    query: str,
    category_filter: str = "",
    table_filter: str = "",
    top_k: int = 3,
) -> str:
    """
    Consulta o Dicionário de Dados e convenções de negócio em pipeline/dados/conhecimento/.
    Realiza sincronização incremental automática, aplica filtros opcionais (categoria/tabela)
    e retorna os trechos mais relevantes ordenados por relevância.
    """
    sync_report = synchronize_knowledge_index()
    if sync_report.total_active_chunks == 0:
        return "Nenhum documento encontrado na base de conhecimento (pipeline/dados/conhecimento/)."

    collection = _get_knowledge_collection()
    collection_count = collection.count()
    if collection_count == 0:
        return "Nenhum conhecimento indexado disponível para consulta."

    # Amplia o pool de candidatos para reordenação (reranking)
    candidate_pool_size = min(max(top_k * 3, 6), collection_count)

    query_result = collection.query(
        query_texts=[query],
        n_results=candidate_pool_size,
        include=["documents", "metadatas", "distances"],
    )
    if not query_result or not query_result.get("documents") or not query_result["documents"][0]:
        return "Nenhum conhecimento relevante encontrado para esta consulta."

    documents = query_result["documents"][0]
    metadatas = query_result["metadatas"][0]
    distances = (
        query_result["distances"][0]
        if query_result.get("distances") and query_result["distances"][0]
        else [0.5] * len(documents)
    )

    normalized_category_filter = category_filter.strip().lower()
    normalized_table_filter = table_filter.strip().lower()

    ranked_candidates = []
    for document_text, metadata, distance in zip(documents, metadatas, distances):
        metadata_dict = metadata or {}
        if normalized_category_filter and normalized_category_filter not in str(metadata_dict.get("categoria", "")).lower():
            continue
        if normalized_table_filter and normalized_table_filter not in str(metadata_dict.get("tabela", "")).lower():
            continue

        relevance_score = _compute_hybrid_relevance_score(
            query=query,
            document_text=document_text,
            metadata=metadata_dict,
            semantic_distance=distance,
        )
        ranked_candidates.append((relevance_score, document_text, metadata_dict))

    if not ranked_candidates:
        return (
            f"Nenhum documento atendeu aos filtros informados "
            f"(category_filter='{category_filter}', table_filter='{table_filter}')."
        )

    ranked_candidates.sort(key=lambda item: item[0], reverse=True)
    selected_candidates = ranked_candidates[: max(1, top_k)]

    formatted_excerpts = []
    for index, (relevance_score, document_text, metadata_dict) in enumerate(selected_candidates, start=1):
        source_path = metadata_dict.get("origem", "desconhecido")
        section_title = metadata_dict.get("secao", "Geral")
        category = metadata_dict.get("categoria", "dicionario_dados")
        related_table = metadata_dict.get("tabela", "")
        updated_at = metadata_dict.get("atualizado_em", "N/A")
        content_hash_short = str(metadata_dict.get("content_hash", ""))[:8]

        table_info = f" | Tabela: {related_table}" if related_table else ""
        header = (
            f"[{index}] Fonte: {source_path} (Seção: {section_title} | "
            f"Categoria: {category}{table_info} | Atualizado: {updated_at} | "
            f"Hash: {content_hash_short} | Relevância: {relevance_score})"
        )
        formatted_excerpts.append(f"{header}\n{document_text[:1200]}")

    return "\n\n---\n\n".join(formatted_excerpts)
