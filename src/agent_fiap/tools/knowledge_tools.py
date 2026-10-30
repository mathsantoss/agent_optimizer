"""Ferramentas de busca semântica (RAG) em documentação e regras de negócio usando ChromaDB."""
import hashlib
import chromadb
from .. import config

CHROMA_DIRECTORY = config.PROJECT_ROOT / ".rag"


def _get_knowledge_collection():
    """Inicializa o cliente persistente do ChromaDB e retorna a coleção de conhecimento."""
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIRECTORY))
    return chroma_client.get_or_create_collection("conhecimento")


def index_knowledge_documents() -> int:
    """Indexa arquivos .md, .txt e .sql encontrados na pasta docs/."""
    documentation_directory = config.PROJECT_ROOT / "docs"
    if not documentation_directory.exists():
        return 0

    collection = _get_knowledge_collection()
    document_files = [
        file_path
        for file_path in sorted(documentation_directory.rglob("*"))
        if file_path.is_file() and file_path.suffix in (".md", ".txt", ".sql")
    ]
    if not document_files:
        return 0

    document_ids = []
    document_contents = []
    document_metadatas = []

    for file_path in document_files:
        text_content = file_path.read_text(encoding="utf-8", errors="ignore").strip()
        if not text_content:
            continue
        relative_path = str(file_path.relative_to(config.PROJECT_ROOT))
        document_id = hashlib.sha1(relative_path.encode()).hexdigest()
        document_ids.append(document_id)
        document_contents.append(text_content)
        document_metadatas.append({"origem": relative_path, "nome": file_path.name})

    if document_ids:
        collection.upsert(
            ids=document_ids,
            documents=document_contents,
            metadatas=document_metadatas,
        )
    return len(document_ids)


def search_knowledge_base(query: str) -> str:
    """
    Busca regras de negócio, dicionários de dados, documentação ou exemplos em docs/ via RAG.
    """
    collection = _get_knowledge_collection()
    if collection.count() == 0 and index_knowledge_documents() == 0:
        return "Nenhum documento encontrado em docs/ para indexar."

    query_result = collection.query(
        query_texts=[query],
        n_results=min(3, collection.count()),
    )
    if not query_result or not query_result["documents"] or not query_result["documents"][0]:
        return "Nenhum conhecimento relevante encontrado para esta consulta."

    formatted_excerpts = []
    for index, (document_text, metadata) in enumerate(
        zip(query_result["documents"][0], query_result["metadatas"][0]),
        start=1,
    ):
        source_path = metadata.get("origem", "desconhecido")
        formatted_excerpts.append(f"[{index}] Fonte: {source_path}\n{document_text[:1000]}")
    return "\n\n---\n\n".join(formatted_excerpts)
