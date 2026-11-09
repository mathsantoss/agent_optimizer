"""Serviço de busca semântica (RAG) no ChromaDB com indexação incremental por hash, cache e threshold."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any
import chromadb

from kraken_copilot import config
from kraken_copilot.schemas import (
    KnowledgeChunkMetadata,
    KnowledgeIndexSyncReport,
    KnowledgeSearchResponse,
    KnowledgeSearchResultItem,
)

SUPPORTED_KNOWLEDGE_EXTENSIONS = (".json", ".yaml", ".yml", ".md", ".txt", ".sql")
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

_LAST_SYNC_TIMESTAMP: float = 0.0
_SYNC_CACHE_TTL_SECONDS: float = 30.0  # Evita checagem repetitiva no filesystem se foi sincronizado há menos de 30s


def get_rag_directory() -> Path:
    """Retorna o diretório de persistência do índice ChromaDB e do manifesto de sincronização."""
    return config.PROJECT_ROOT / ".rag"


def get_knowledge_collection():
    """Inicializa o cliente persistente do ChromaDB e retorna a coleção de conhecimento."""
    rag_dir = get_rag_directory()
    rag_dir.mkdir(parents=True, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=str(rag_dir))
    return chroma_client.get_or_create_collection("conhecimento")


def resolve_knowledge_directory() -> Path | None:
    """
    Localiza o diretório da base de conhecimento priorizando pipeline/dados/conhecimento
    (config.KNOWLEDGE_DIR) com fallback para docs/conhecimento em fixtures de teste.
    """
    if config.KNOWLEDGE_DIR.exists():
        return config.KNOWLEDGE_DIR
    fallback_dir = config.PROJECT_ROOT / "docs" / "conhecimento"
    if fallback_dir.exists():
        return fallback_dir
    docs_root = config.PROJECT_ROOT / "docs"
    if docs_root.exists():
        return docs_root
    return None


def _parse_frontmatter(raw_text: str) -> tuple[dict[str, str], str]:
    """Extrai metadados YAML frontmatter ou comentários SQL."""
    metadata: dict[str, str] = {}
    body_text = raw_text.strip()

    frontmatter_match = FRONTMATTER_PATTERN.match(body_text)
    if frontmatter_match:
        frontmatter_block = frontmatter_match.group(1)
        body_text = body_text[frontmatter_match.end():].strip()
        for line in frontmatter_block.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                metadata[k.strip().lower()] = v.strip().strip("\"'")
        return metadata, body_text

    reading_header = True
    remaining_lines = []
    for line in body_text.splitlines():
        stripped = line.strip()
        if reading_header and stripped.startswith("--"):
            comment_content = stripped.lstrip("-").strip()
            if ":" in comment_content:
                k, v = comment_content.split(":", 1)
                metadata[k.strip().lower()] = v.strip()
        else:
            reading_header = False
            remaining_lines.append(line)

    if metadata and remaining_lines:
        body_text = "\n".join(remaining_lines).strip()

    return metadata, body_text


def _extract_json_or_yaml_chunks(raw_text: str, file_suffix: str) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """Extrai múltiplos chunks estruturados de arquivos JSON/YAML de dicionários de dados."""
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
        "categoria": str(raw_metadata.get("category") or raw_metadata.get("categoria") or parsed_data.get("category") or "dicionario_dados"),
        "tabela": str(raw_metadata.get("table") or raw_metadata.get("tabela") or parsed_data.get("table") or ""),
        "linguagem": file_suffix.lstrip("."),
        "atualizado_em": str(raw_metadata.get("updated_at") or raw_metadata.get("atualizado_em") or "N/A"),
    }

    chunks: list[tuple[str, str]] = []
    overview_lines = [
        f"Tabela: {normalized_metadata['tabela']}",
        f"Categoria: {normalized_metadata['categoria']}",
        f"Descrição Geral: {parsed_data.get('description') or raw_metadata.get('description', '')}",
        f"Chaves Primárias: {parsed_data.get('primary_key', '')}",
        f"Grão dos Dados: {parsed_data.get('grain', '')}",
    ]
    chunks.append(("Visão Geral", "\n".join(line for line in overview_lines if line.split(": ", 1)[1])))

    columns = parsed_data.get("columns", [])
    if isinstance(columns, list) and columns:
        col_lines = ["Colunas e Tipos de Dados:"]
        for col in columns:
            if isinstance(col, dict):
                col_name = col.get("name", "")
                data_type = col.get("data_type") or col.get("type", "")
                desc = col.get("description", "")
                business_rule = col.get("business_rule", "")
                rule_text = f" [Regra: {business_rule}]" if business_rule else ""
                col_lines.append(f"- {col_name} ({data_type}): {desc}{rule_text}")
        chunks.append(("Colunas e Tipos", "\n".join(col_lines)))

    derived_metrics = parsed_data.get("derived_metrics", [])
    if isinstance(derived_metrics, list) and derived_metrics:
        metric_lines = ["Métricas Derivadas e Regras de Negócio:"]
        for metric in derived_metrics:
            if isinstance(metric, dict):
                m_name = metric.get("name", "")
                m_formula = metric.get("formula", "")
                m_desc = metric.get("description", "")
                metric_lines.append(f"- {m_name}: Fórmula `{m_formula}` | Descrição: {m_desc}")
        chunks.append(("Métricas Derivadas", "\n".join(metric_lines)))

    return normalized_metadata, chunks


def _chunk_text_document(raw_text: str, file_suffix: str) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """Segmenta documentos Markdown, SQL ou texto livre em seções estruturadas."""
    if file_suffix in (".json", ".yaml", ".yml"):
        return _extract_json_or_yaml_chunks(raw_text, file_suffix)

    metadata, body_text = _parse_frontmatter(raw_text)
    if not metadata.get("categoria"):
        metadata["categoria"] = "regras_negocio" if file_suffix in (".md", ".txt") else "consultas_sql"
    metadata["linguagem"] = file_suffix.lstrip(".")

    sections: list[tuple[str, str]] = []
    heading_pattern = re.compile(r"^(#{1,3}\s+.*)$", re.MULTILINE)
    split_parts = heading_pattern.split(body_text)

    if len(split_parts) > 1:
        current_title = "Introdução"
        idx = 0
        if not split_parts[0].strip():
            idx = 1
        while idx < len(split_parts):
            item = split_parts[idx].strip()
            if heading_pattern.match(item):
                current_title = item.lstrip("#").strip()
                content = split_parts[idx + 1].strip() if idx + 1 < len(split_parts) else ""
                if content:
                    sections.append((current_title, content))
                idx += 2
            else:
                if item:
                    sections.append((current_title, item))
                idx += 1
    else:
        sections.append(("Geral", body_text))

    return metadata, sections


def _load_manifest(rag_dir: Path) -> dict[str, str]:
    manifest_path = rag_dir / "index_manifest.json"
    if manifest_path.exists():
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_manifest(rag_dir: Path, manifest: dict[str, str]) -> None:
    manifest_path = rag_dir / "index_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def synchronize_knowledge_index(force: bool = False) -> KnowledgeIndexSyncReport:
    """
    Sincroniza incrementalmente os arquivos da base de conhecimento no ChromaDB.
    Usa hashes SHA-256 para indexar apenas conteúdos novos ou modificados.
    """
    global _LAST_SYNC_TIMESTAMP
    now_ts = datetime.now(timezone.utc).timestamp()

    rag_dir = get_rag_directory()
    knowledge_dir = resolve_knowledge_directory()

    if knowledge_dir is None or not knowledge_dir.exists():
        now_iso = datetime.now(timezone.utc).isoformat()
        return KnowledgeIndexSyncReport(
            last_indexed_at=now_iso,
            indexed_at=now_iso,
            total_active_chunks=0,
            added_or_updated_chunks=0,
            unchanged_chunks=0,
            removed_chunks=0,
            synced_files=[],
        )

    # Se já sincronizou recentemente e não é forçado, reutiliza o manifesto existente
    manifest = _load_manifest(rag_dir)
    if not force and (_LAST_SYNC_TIMESTAMP > 0) and (now_ts - _LAST_SYNC_TIMESTAMP < _SYNC_CACHE_TTL_SECONDS) and manifest:
        now_iso = datetime.now(timezone.utc).isoformat()
        return KnowledgeIndexSyncReport(
            last_indexed_at=now_iso,
            indexed_at=now_iso,
            total_active_chunks=len(manifest),
            added_or_updated_chunks=0,
            unchanged_chunks=len(manifest),
            removed_chunks=0,
            synced_files=[],
        )

    collection = get_knowledge_collection()
    knowledge_files = [
        f for f in sorted(knowledge_dir.rglob("*"))
        if f.is_file() and f.suffix.lower() in SUPPORTED_KNOWLEDGE_EXTENSIONS
    ]

    current_chunks_by_id: dict[str, tuple[str, dict[str, Any], str]] = {}
    synced_file_names: set[str] = set()

    for file_path in knowledge_files:
        try:
            raw_text = file_path.read_text(encoding="utf-8")
        except Exception:
            continue

        try:
            relative_source = str(file_path.relative_to(config.PROJECT_ROOT))
        except ValueError:
            relative_source = file_path.name
        synced_file_names.add(relative_source)

        doc_metadata, chunks = _chunk_text_document(raw_text, file_path.suffix.lower())
        for chunk_index, (section_title, chunk_content) in enumerate(chunks):
            if not chunk_content.strip():
                continue
            normalized_content = chunk_content.strip()
            content_hash = hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()
            chunk_id = hashlib.sha256(f"{relative_source}::{section_title}::{chunk_index}".encode("utf-8")).hexdigest()[:24]

            chunk_meta = {
                "chunk_id": chunk_id,
                "origem": relative_source,
                "secao": section_title,
                "categoria": str(doc_metadata.get("categoria", "dicionario_dados")),
                "tabela": str(doc_metadata.get("tabela", "")),
                "linguagem": str(doc_metadata.get("linguagem", file_path.suffix.lstrip("."))),
                "atualizado_em": str(doc_metadata.get("atualizado_em", "N/A")),
                "content_hash": content_hash,
            }
            current_chunks_by_id[chunk_id] = (normalized_content, chunk_meta, content_hash)

    added_or_updated = 0
    unchanged = 0
    ids_to_upsert: list[str] = []
    docs_to_upsert: list[str] = []
    metas_to_upsert: list[dict[str, Any]] = []

    for chunk_id, (content, meta, content_hash) in current_chunks_by_id.items():
        if manifest.get(chunk_id) == content_hash:
            unchanged += 1
        else:
            ids_to_upsert.append(chunk_id)
            docs_to_upsert.append(content)
            metas_to_upsert.append(meta)
            manifest[chunk_id] = content_hash
            added_or_updated += 1

    if ids_to_upsert:
        collection.upsert(ids=ids_to_upsert, documents=docs_to_upsert, metadatas=metas_to_upsert)

    # Remove chunks órfãos
    removed_count = 0
    orphan_ids = set(manifest.keys()) - set(current_chunks_by_id.keys())
    if orphan_ids:
        collection.delete(ids=list(orphan_ids))
        for orphan_id in orphan_ids:
            manifest.pop(orphan_id, None)
            removed_count += 1

    _save_manifest(rag_dir, manifest)
    _LAST_SYNC_TIMESTAMP = now_ts

    now_iso = datetime.now(timezone.utc).isoformat()
    return KnowledgeIndexSyncReport(
        last_indexed_at=now_iso,
        indexed_at=now_iso,
        total_active_chunks=len(current_chunks_by_id),
        added_or_updated_chunks=added_or_updated,
        unchanged_chunks=unchanged,
        removed_chunks=removed_count,
        synced_files=sorted(synced_file_names),
    )


def _compute_hybrid_relevance(
    query: str,
    document_text: str,
    metadata: dict[str, Any],
    semantic_distance: float,
) -> float:
    """Calcula score híbrido combinando proximidade semântica vetorial e overlap de termos."""
    semantic_score = max(0.0, 1.0 - (float(semantic_distance) / 2.0))
    query_tokens = {t for t in re.findall(r"[a-zA-ZÀ-ÿ0-9_]+", query.lower()) if len(t) > 2}
    if not query_tokens:
        return round(semantic_score, 4)

    search_target = " ".join([
        document_text.lower(),
        str(metadata.get("secao", "")).lower(),
        str(metadata.get("tabela", "")).lower(),
        str(metadata.get("categoria", "")).lower(),
    ])
    matches = sum(1 for t in query_tokens if t in search_target)
    lexical_overlap = matches / len(query_tokens)
    return round((0.70 * semantic_score) + (0.30 * lexical_overlap), 4)


def _build_search_response(
    summary: str,
    query: str,
    success: bool = True,
    items: list[KnowledgeSearchResultItem] | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
    formatted_text: str = "",
) -> dict[str, Any]:
    """Padroniza a resposta de busca semântica utilizando o schema KnowledgeSearchResponse."""
    selected_items = items or []
    item_dicts = [item.model_dump() for item in selected_items]
    response = KnowledgeSearchResponse(
        success=success,
        operation="search_knowledge_base",
        summary=summary,
        data={
            "query": query,
            "total_recuperado": len(selected_items),
            "maior_relevancia": selected_items[0].relevancia if selected_items else 0.0,
            "resultados": item_dicts,
            "texto_formatado": formatted_text,
        },
        warnings=warnings or [],
        errors=errors or [],
    )
    return response.model_dump()


def search_knowledge_service(
    query: str,
    category_filter: str = "",
    table_filter: str = "",
    top_k: int = 3,
    min_relevance: float = 0.25,
) -> dict[str, Any]:
    """
    Executa busca semântica híbrida no ChromaDB com filtros e threshold mínimo de relevância.
    """
    clean_query = query.strip()
    if not clean_query:
        return _build_search_response("Consulta não pode ser vazia.", query, success=False, errors=["Consulta vazia."])

    # Sincroniza se necessário (usa cache automático de TTL)
    sync_report = synchronize_knowledge_index()
    if sync_report.total_active_chunks == 0:
        return _build_search_response(
            "Nenhum documento encontrado na base de conhecimento (pipeline/dados/conhecimento/).",
            query,
            warnings=["Base de conhecimento vazia ou diretório não encontrado."],
        )

    collection = get_knowledge_collection()
    count = collection.count()
    if count == 0:
        return _build_search_response("Nenhum documento indexado disponível para consulta.", query)

    candidate_pool_size = min(max(top_k * 3, 6), count)
    query_result = collection.query(
        query_texts=[clean_query],
        n_results=candidate_pool_size,
        include=["documents", "metadatas", "distances"],
    )

    if not query_result or not query_result.get("documents") or not query_result["documents"][0]:
        return _build_search_response("Nenhum documento relevante encontrado para a consulta.", query)

    documents = query_result["documents"][0]
    metadatas = query_result["metadatas"][0]
    distances = query_result["distances"][0] if (query_result.get("distances") and query_result["distances"][0]) else [0.5] * len(documents)

    cat_norm = category_filter.strip().lower()
    tab_norm = table_filter.strip().lower()

    ranked: list[KnowledgeSearchResultItem] = []
    for doc_text, meta, dist in zip(documents, metadatas, distances):
        m_dict = meta or {}
        if cat_norm and cat_norm not in str(m_dict.get("categoria", "")).lower():
            continue
        if tab_norm and tab_norm not in str(m_dict.get("tabela", "")).lower():
            continue

        score = _compute_hybrid_relevance(clean_query, doc_text, m_dict, dist)
        if score < min_relevance:
            continue

        ranked.append(
            KnowledgeSearchResultItem(
                relevancia=score,
                origem=m_dict.get("origem", "desconhecido"),
                secao=m_dict.get("secao", "Geral"),
                categoria=m_dict.get("categoria", "dicionario_dados"),
                tabela=m_dict.get("tabela", ""),
                atualizado_em=m_dict.get("atualizado_em", "N/A"),
                conteudo=doc_text,
            )
        )

    ranked.sort(key=lambda item: item.relevancia, reverse=True)
    selected = ranked[: max(1, top_k)]

    if not selected:
        msg = "Nenhum documento atendeu aos critérios de relevância mínima e filtros informados."
        return _build_search_response(msg, query, warnings=[msg])

    # Formata em texto legível para o LLM sem expor hashes internos
    formatted_excerpts = []
    for idx, item in enumerate(selected, start=1):
        tbl = f" | Tabela: {item.tabela}" if item.tabela else ""
        header = f"[{idx}] Fonte: {item.origem} (Seção: {item.secao} | Categoria: {item.categoria}{tbl} | Relevância: {item.relevancia})"
        formatted_excerpts.append(f"{header}\n{item.conteudo[:1200]}")

    formatted_text = "\n\n---\n\n".join(formatted_excerpts)
    summary_msg = f"{len(selected)} trecho(s) relevante(s) recuperado(s) da base de conhecimento."

    return _build_search_response(
        summary_msg,
        query,
        items=selected,
        formatted_text=formatted_text,
    )

