"""Rotas da API para exploração de dados, outputs do pipeline e documentação técnica."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/dados", tags=["dados"])


def _diretorios_permitidos() -> List[Path]:
    from kraken_copilot.config import REPOSITORY_ROOT
    dirs = [
        (REPOSITORY_ROOT / "krakenlake" / "catalog").resolve(),
        (REPOSITORY_ROOT / "krakenlake" / "workspace").resolve(),
        (REPOSITORY_ROOT / "krakenlake" / "saida").resolve(),
        (REPOSITORY_ROOT / "krakenlake" / "datalake").resolve(),
        (REPOSITORY_ROOT / "docs").resolve(),
    ]
    return [d for d in dirs if d.exists()]


@router.get("/arquivos")
async def listar_arquivos_dados():
    """Lista e categoriza os arquivos em estrutura hierárquica dinâmica:
    - DATALAKE (CSV, JSON, PARQUET - apenas tipos existentes)
    - OUTPUTS (CSV, JSON, PARQUET - apenas tipos existentes)
    - DOCUMENTAÇÕES (MARKDOWN, PDF - apenas tipos existentes)
    """
    from kraken_copilot.config import REPOSITORY_ROOT
    arquivos = []
    diretorios = _diretorios_permitidos()

    extensoes_permitidas = (".csv", ".pdf", ".json", ".parquet", ".md", ".markdown", ".txt", ".py")

    for d in diretorios:
        if not d.exists():
            continue
        for p in d.rglob("*"):
            if p.is_file() and p.suffix.lower() in extensoes_permitidas:
                rel = p.relative_to(REPOSITORY_ROOT).as_posix()
                ext = p.suffix.lower().lstrip(".")
                stat = p.stat()

                if rel.startswith("pipeline/saida") or rel.startswith("krakenlake/saida"):
                    secao = "OUTPUTS"
                    secao_ordem = 3
                    subcategoria = ext.upper()
                    sub_ordem = 1 if ext == "csv" else (2 if ext == "json" else 3)
                    categoria = "dados_saida"
                    categoria_nome = "⚡ Saída do Pipeline (Gerados)"

                elif rel.startswith("docs") or "documentation" in rel.lower():
                    secao = "DOCUMENTAÇÕES"
                    secao_ordem = 4
                    if ext in ("md", "markdown"):
                        subcategoria = "MARKDOWN"
                        sub_ordem = 1
                    else:
                        subcategoria = ext.upper()
                        sub_ordem = 2 if ext == "pdf" else 3
                    categoria = "documentacao"
                    categoria_nome = "📕 Documentação Técnica"

                elif "metadados" in rel.lower() or "dicionario" in rel.lower():
                    secao = "METADADOS"
                    secao_ordem = 2
                    subcategoria = ext.upper()
                    sub_ordem = 1 if ext == "json" else 2
                    categoria = "metadados"
                    categoria_nome = "🏷️ Metadados & Dicionários"

                elif "workspace" in rel.lower() and ext == "py":
                    secao = "WORKSPACE"
                    secao_ordem = 5
                    subcategoria = "PYTHON"
                    sub_ordem = 1
                    categoria = "workspace"
                    categoria_nome = "💻 Scripts do Workspace"

                else:
                    secao = "DATALAKE"
                    secao_ordem = 1
                    subcategoria = ext.upper()
                    sub_ordem = 1 if ext == "csv" else (2 if ext == "parquet" else 3)
                    categoria = "dados_entrada"
                    categoria_nome = "📥 Data Sources (Datalake)"

                is_metadados = (ext == "json" and ("dicionario" in rel.lower() or "conhecimento" in rel.lower() or "schema" in rel.lower()))

                arquivos.append({
                    "nome": p.name,
                    "caminho": rel,
                    "tipo": ext,
                    "secao": secao,
                    "secao_ordem": secao_ordem,
                    "subcategoria": subcategoria,
                    "sub_ordem": sub_ordem,
                    "is_metadados": is_metadados,
                    "categoria": categoria,
                    "categoria_nome": categoria_nome,
                    "tamanho_kb": round(stat.st_size / 1024, 2),
                    "modificado_em": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                })

    arquivos.sort(key=lambda x: (x["secao_ordem"], x["sub_ordem"], x["nome"]))

    arvore = {}
    for a in arquivos:
        sec = a.get("secao")
        sub = a.get("subcategoria")
        if sec not in arvore:
            arvore[sec] = {}
        if sub not in arvore[sec]:
            arvore[sec][sub] = []
        arvore[sec][sub].append(a)

    # Compatibilidade com testes legados que esperam JSON (metadados/dicionários) dentro de DATALAKE
    if "METADADOS" in arvore:
        if "DATALAKE" not in arvore:
            arvore["DATALAKE"] = {}
        for sub, items in arvore["METADADOS"].items():
            if sub not in arvore["DATALAKE"]:
                arvore["DATALAKE"][sub] = []
            arvore["DATALAKE"][sub].extend(items)

    return {"arquivos": arquivos, "arvore": arvore}


@router.get("/workspace/arquivos")
async def listar_arquivos_workspace():
    """Lista todos os arquivos python disponíveis no workspace do krakenlake."""
    from kraken_copilot.config import REPOSITORY_ROOT
    ws_dir = (REPOSITORY_ROOT / "krakenlake" / "workspace").resolve()
    if not ws_dir.exists():
        ws_dir = (REPOSITORY_ROOT / "pipeline").resolve()

    arquivos = []
    if ws_dir.exists():
        for p in sorted(ws_dir.glob("*.py")):
            if not p.name.startswith((".", "_")) and not p.name.endswith(".bak"):
                try:
                    lines = len(p.read_text(encoding="utf-8", errors="ignore").splitlines())
                except Exception:
                    lines = 0
                arquivos.append({
                    "nome": p.name,
                    "caminho": p.relative_to(REPOSITORY_ROOT).as_posix(),
                    "linhas": lines,
                })
    return {"arquivos": arquivos, "padrao": arquivos[0]["nome"] if arquivos else ""}


@router.get("/arquivo")
async def obter_conteudo_arquivo(caminho: str, limite: int = 50):
    """Retorna o conteúdo estruturado de um arquivo CSV, PARQUET, JSON ou MARKDOWN."""
    from kraken_copilot.config import REPOSITORY_ROOT
    p = (REPOSITORY_ROOT / caminho).resolve()

    # Validação de segurança contra directory traversal
    permitido = any(p == d or d in p.parents for d in _diretorios_permitidos())
    if not permitido or not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado ou fora do escopo permitido.")

    ext = p.suffix.lower()

    # 1. Arquivos Markdown / Texto
    if ext in (".md", ".markdown", ".txt"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                conteudo = f.read()
            return {
                "tipo": "markdown",
                "caminho": caminho,
                "nome": p.name,
                "conteudo": conteudo,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao ler markdown: {e}")

    # 2. Arquivos JSON
    if ext == ".json":
        try:
            with open(p, "r", encoding="utf-8") as f:
                dados = json.load(f)
            return {
                "tipo": "json",
                "caminho": caminho,
                "nome": p.name,
                "dados": dados,
                "conteudo": dados,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao ler JSON: {e}")

    # 3. Arquivos CSV
    if ext == ".csv":
        try:
            import pandas as pd
            df = pd.read_csv(p, nrows=limite)
            total_linhas = sum(1 for _ in open(p, "r", encoding="utf-8", errors="ignore")) - 1
            colunas = list(df.columns)
            linhas = df.fillna("").to_dict(orient="records")
            return {
                "tipo": "csv",
                "caminho": caminho,
                "nome": p.name,
                "total_linhas": max(total_linhas, len(linhas)),
                "limite": limite,
                "colunas": colunas,
                "linhas": linhas,
                "amostrado": total_linhas > limite,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao ler CSV: {e}")

    # 4. Arquivos Parquet
    if ext == ".parquet":
        try:
            import pandas as pd
            df = pd.read_parquet(p)
            total_linhas = len(df)
            df_amostra = df.head(limite)
            colunas = list(df_amostra.columns)
            linhas = df_amostra.fillna("").to_dict(orient="records")
            return {
                "tipo": "parquet",
                "caminho": caminho,
                "nome": p.name,
                "total_linhas": total_linhas,
                "limite": limite,
                "colunas": colunas,
                "linhas": linhas,
                "amostrado": total_linhas > limite,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao ler Parquet: {e}")

    # 5. Arquivo PDF (retorna metadados básicos)
    if ext == ".pdf":
        return {
            "tipo": "pdf",
            "caminho": caminho,
            "nome": p.name,
            "tamanho_kb": round(p.stat().st_size / 1024, 2),
        }

    # 6. Arquivo Python (código-fonte do workspace)
    if ext == ".py":
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                conteudo = f.read()

            # Se o arquivo estiver no workspace, garante snapshot inicial em tmp/<stem>_original.bak
            if "workspace" in str(p.parent) and conteudo.strip():
                try:
                    from kraken_copilot.tools.code_optimizer.services.file_service import snapshot_workspace_file
                    snapshot_workspace_file(p, content=conteudo)
                except Exception:
                    pass

            return {
                "tipo": "python",
                "caminho": caminho,
                "nome": p.name,
                "conteudo": conteudo,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao ler script Python: {e}")

    raise HTTPException(status_code=400, detail="Formato de arquivo não suportado para visualização.")


@router.get("/documento")
async def visualizar_documento(caminho: str):
    """Retorna o documento diretamente para visualização/leitura no navegador (ex: application/pdf)."""
    from kraken_copilot.config import REPOSITORY_ROOT
    p = (REPOSITORY_ROOT / caminho).resolve()
    permitido = any(p == d or d in p.parents for d in _diretorios_permitidos())
    if not permitido or not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    if p.suffix.lower() == ".pdf":
        return FileResponse(
            p,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{p.name}"'},
        )
    return FileResponse(
        p,
        headers={"Content-Disposition": f'inline; filename="{p.name}"'},
    )


@router.get("/download")
async def baixar_arquivo(caminho: str):
    """Download direto de um arquivo permitido."""
    from kraken_copilot.config import REPOSITORY_ROOT
    p = (REPOSITORY_ROOT / caminho).resolve()
    permitido = any(p == d or d in p.parents for d in _diretorios_permitidos())
    if not permitido or not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    return FileResponse(p, filename=p.name)


@router.get("/diff")
async def obter_diff_arquivo(caminho: str = ""):
    """Gera o diff comparativo entre o snapshot original e o código atual ou proposta otimizada."""
    import difflib
    from kraken_copilot.config import PROJECT_ROOT
    from kraken_copilot.tools.code_optimizer.services.file_service import (
        get_default_workspace_pipeline,
        get_file_tmp_paths,
        resolve_pipeline_path,
        snapshot_workspace_file,
    )

    try:
        if not caminho or not str(caminho).strip():
            return {
                "arquivo": "",
                "caminho": "",
                "adicoes": 0,
                "remocoes": 0,
                "linhas": [],
                "raw_diff": "",
                "original_code": "",
                "current_code": "",
                "proposed_code": "",
            }
        resolved = resolve_pipeline_path(caminho, allow_write=False)
        curr_text = resolved.read_text(encoding="utf-8") if resolved.is_file() else ""

        tmp_orig, tmp_opt = get_file_tmp_paths(resolved)

        # 1. Recupera o código baseline (original congelado no contexto)
        if tmp_orig.is_file() and tmp_orig.stat().st_size > 0:
            orig_text = tmp_orig.read_text(encoding="utf-8")
        else:
            orig_text = curr_text
            if curr_text.strip():
                snapshot_workspace_file(resolved, content=curr_text)

        # 2. Recupera a proposta candidata em tmp/<stem>_otimizado.bak se houver
        if tmp_opt.is_file() and tmp_opt.stat().st_size > 0:
            prop_text = tmp_opt.read_text(encoding="utf-8")
        else:
            prop_text = curr_text

        # 3. Compara baseline vs proposta (se houver proposta pendente), ou baseline vs atual
        if prop_text.strip() and prop_text.strip() != orig_text.strip():
            diff_lines = list(difflib.unified_diff(
                orig_text.splitlines(keepends=True),
                prop_text.splitlines(keepends=True),
                fromfile=f"a/{resolved.name} (original)",
                tofile=f"b/{resolved.name} (proposta)",
            ))
        else:
            diff_lines = list(difflib.unified_diff(
                orig_text.splitlines(keepends=True),
                curr_text.splitlines(keepends=True),
                fromfile=f"a/{resolved.name} (original)",
                tofile=f"b/{resolved.name} (workspace)",
            ))

        adicoes = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
        remocoes = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))

        linhas_estruturadas = []
        for l in diff_lines:
            clean_l = l.rstrip("\r\n")
            if clean_l.startswith("@@"):
                tipo = "hunk"
            elif clean_l.startswith("+") and not clean_l.startswith("+++"):
                tipo = "add"
            elif clean_l.startswith("-") and not clean_l.startswith("---"):
                tipo = "del"
            else:
                tipo = "ctx"
            linhas_estruturadas.append({"tipo": tipo, "texto": clean_l})

        return {
            "arquivo": resolved.name,
            "caminho": str(resolved.relative_to(PROJECT_ROOT)),
            "adicoes": adicoes,
            "remocoes": remocoes,
            "linhas": linhas_estruturadas,
            "raw_diff": "".join(diff_lines),
            "original_code": orig_text,
            "current_code": curr_text,
            "proposed_code": prop_text,
        }
    except Exception as err:
        return {
            "arquivo": caminho,
            "adicoes": 0,
            "remocoes": 0,
            "linhas": [],
            "raw_diff": "",
            "original_code": "",
            "current_code": "",
            "proposed_code": "",
            "erro": str(err),
        }
