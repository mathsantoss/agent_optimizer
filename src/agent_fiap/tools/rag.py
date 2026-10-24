"""RAG simples e direto usando ChromaDB para documentos em docs/."""
import hashlib
from pathlib import Path
import chromadb
from .. import config

CHROMA_DIR = config.PROJECT_ROOT / ".rag"


def _get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection("conhecimento")


def indexar_documentos() -> int:
    """Indexa arquivos .md e .txt encontrados na pasta docs/."""
    docs_dir = config.PROJECT_ROOT / "docs"
    if not docs_dir.exists():
        return 0

    col = _get_collection()
    arquivos = list(docs_dir.rglob("*.md")) + list(docs_dir.rglob("*.txt"))
    if not arquivos:
        return 0

    ids, docs, metas = [], [], []
    for f in arquivos:
        conteudo = f.read_text(encoding="utf-8", errors="ignore").strip()
        if not conteudo:
            continue
        rel_path = str(f.relative_to(config.PROJECT_ROOT))
        doc_id = hashlib.sha1(rel_path.encode()).hexdigest()
        ids.append(doc_id)
        docs.append(conteudo)
        metas.append({"origem": rel_path, "nome": f.name})

    if ids:
        col.upsert(ids=ids, documents=docs, metadatas=metas)
    return len(ids)


def buscar(consulta: str, n_resultados: int = 3) -> str:
    """Busca trechos relevantes na base de conhecimento indexada."""
    col = _get_collection()
    if col.count() == 0:
        indexados = indexar_documentos()
        if indexados == 0:
            return "Nenhum documento encontrado em docs/ para indexar."

    res = col.query(query_texts=[consulta], n_results=min(n_resultados, col.count()))
    if not res or not res["documents"] or not res["documents"][0]:
        return "Nenhum conhecimento relevante encontrado para esta consulta."

    trechos = []
    for i, (doc, meta) in enumerate(zip(res["documents"][0], res["metadatas"][0]), 1):
        origem = meta.get("origem", "desconhecido")
        trechos.append(f"[{i}] Fonte: {origem}\n{doc[:1000]}")
    return "\n\n---\n\n".join(trechos)
