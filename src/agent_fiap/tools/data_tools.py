"""Ferramentas analíticas e de dados: exploração rica, resumo estatístico, SQL e RAG."""
import json
from pathlib import Path
import sqlite3
import pandas as pd
from .. import config
from .dados import listar_datasets as _listar_arquivos, ler_dataset
from .rag import buscar as _buscar_rag

FORBIDDEN_SQL = ("drop", "delete", "insert", "update", "alter", "create", "truncate", "replace")


def _safe_float(v):
    try:
        return float(v)
    except (ValueError, TypeError):
        return v


def _greatest(*args):
    valid = [a for a in args if a is not None]
    if not valid:
        return None
    try:
        return max(valid, key=_safe_float)
    except Exception:
        return max(valid)


def _least(*args):
    valid = [a for a in args if a is not None]
    if not valid:
        return None
    try:
        return min(valid, key=_safe_float)
    except Exception:
        return min(valid)


def _encontrar_arquivo(nome_dataset: str) -> Path | None:
    """Encontra o arquivo correspondente em DATA_DIR pelo nome ou stem."""
    arquivos = _listar_arquivos()
    alvo = Path(nome_dataset.strip()).name.lower()
    alvo_stem = Path(nome_dataset.strip()).stem.lower()

    for p in arquivos:
        p_stem = p.stem.lower()
        if p.name.lower() == alvo or p_stem == alvo_stem:
            return p
        if alvo_stem in p_stem or p_stem in alvo_stem:
            return p
    return None


def listar_datasets() -> str:
    """
    Lista todos os datasets (.csv e .parquet) disponíveis em pipeline/dados/.
    Retorna o nome do arquivo, a tabela correspondente para SQL e o tamanho.
    """
    arquivos = _listar_arquivos()
    if not arquivos:
        return "Nenhum dataset encontrado no diretório de dados (pipeline/dados/)."

    itens = []
    for p in arquivos:
        tabela = p.stem.replace("-", "_")
        tamanho_kb = round(p.stat().st_size / 1024, 1)
        itens.append({
            "arquivo": str(p.relative_to(config.PROJECT_ROOT)),
            "tabela_sql": tabela,
            "tamanho": f"{tamanho_kb} KB"
        })
    return json.dumps(itens, ensure_ascii=False, indent=2)


def explorar_dataset(nome_dataset: str) -> str:
    """
    Inspeciona qualquer dataset gerando um resumo inteligente (estilo Genie):
    total de linhas, colunas, tipos, contagem de valores únicos, período de datas
    e uma amostra real das primeiras 3 linhas.
    Parâmetro: nome_dataset (nome do arquivo ou da tabela retornado por listar_datasets).
    """
    p = _encontrar_arquivo(nome_dataset)
    if not p:
        disponiveis = [f.stem for f in _listar_arquivos()]
        return f"Dataset '{nome_dataset}' não encontrado. Disponíveis: {disponiveis}"

    try:
        df_sample = ler_dataset(p, nrows=10_000)
        total_linhas = len(df_sample)
        
        colunas_info = {}
        datas_info = {}
        for col in df_sample.columns:
            dtype_str = str(df_sample[col].dtype)
            n_unicos = int(df_sample[col].nunique())
            n_nulos = int(df_sample[col].isna().sum())
            colunas_info[col] = {
                "tipo": dtype_str,
                "valores_unicos": n_unicos,
                "nulos": n_nulos
            }
            if "date" in col.lower() or "created" in col.lower() or "updated" in col.lower():
                try:
                    dt_series = pd.to_datetime(df_sample[col], errors="coerce")
                    if dt_series.notna().sum() > 0:
                        datas_info[col] = {
                            "inicio": str(dt_series.min()),
                            "fim": str(dt_series.max())
                        }
                except Exception:
                    pass

        res = {
            "arquivo": str(p.relative_to(config.PROJECT_ROOT)),
            "tabela_sql": p.stem.replace("-", "_"),
            "total_linhas_amostradas": total_linhas,
            "periodo_temporal": datas_info if datas_info else "Nenhuma coluna de data detectada",
            "colunas": colunas_info,
            "amostra_3_linhas": df_sample.head(3).to_dict(orient="records")
        }
        return json.dumps(res, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        return f"Erro ao explorar dataset '{nome_dataset}': {str(e)}"


def resumo_estatistico(nome_dataset: str) -> str:
    """
    Gera um resumo estatístico detalhado (médias, mínimos, máximos, percentis, contagens)
    das colunas numéricas do dataset informado.
    Use para responder perguntas sobre variações, preços médios e extremos.
    """
    p = _encontrar_arquivo(nome_dataset)
    if not p:
        disponiveis = [f.stem for f in _listar_arquivos()]
        return f"Dataset '{nome_dataset}' não encontrado. Disponíveis: {disponiveis}"

    try:
        df = ler_dataset(p, nrows=20_000)
        desc = df.describe().transpose()
        desc = desc[["count", "mean", "std", "min", "50%", "max"]].dropna(how="all")
        try:
            return desc.round(2).to_markdown()
        except Exception:
            return desc.round(2).to_string()
    except Exception as e:
        return f"Erro ao gerar resumo estatístico: {str(e)}"


def consultar_sql(query: str) -> str:
    """
    Executa uma consulta SQL (SELECT somente leitura) sobre os datasets disponíveis.
    O nome de cada tabela corresponde ao nome do arquivo sem extensão (exibido em listar_datasets).
    Suporta funções analíticas como GREATEST(col1, col2), LEAST(col1, col2), CONCAT, YEAR e MONTH.
    Retorna os resultados em formato tabular (máximo 50 linhas).
    """
    q_lower = query.strip().lower()
    for cmd in FORBIDDEN_SQL:
        if q_lower.startswith(cmd) or f" {cmd} " in f" {q_lower} ":
            return f"Erro: comando '{cmd.upper()}' proibido. Apenas consultas SELECT são permitidas."

    arquivos = _listar_arquivos()
    conn = sqlite3.connect(":memory:")

    # Registra funções customizadas para suporte a dialetos modernos (GREATEST, LEAST, CONCAT, etc.)
    conn.create_function("greatest", -1, _greatest)
    conn.create_function("least", -1, _least)
    conn.create_function("concat", -1, lambda *args: "".join(str(a) for a in args if a is not None))
    conn.create_function("year", 1, lambda d: int(str(d)[:4]) if d else None)
    conn.create_function("month", 1, lambda d: int(str(d)[5:7]) if d else None)

    try:
        carregadas = []
        for p in arquivos:
            tabela = p.stem.replace("-", "_").lower()
            if tabela in q_lower or p.stem.lower() in q_lower or (len(arquivos) == 1 and ("from" in q_lower)):
                df = ler_dataset(p, nrows=100_000)
                df.to_sql(tabela, conn, index=False, if_exists="replace")
                carregadas.append(tabela)

        if not carregadas:
            return f"Nenhuma tabela válida encontrada na query. Tabelas disponíveis: {[p.stem.replace('-', '_') for p in arquivos]}"

        df_res = pd.read_sql_query(query, conn)
        linhas_total = len(df_res)
        df_res = df_res.head(50)

        try:
            resultado = df_res.to_markdown(index=False)
        except Exception:
            resultado = df_res.to_string(index=False)
        aviso = f"\n\n(Exibindo {len(df_res)} de {linhas_total} linhas)" if linhas_total > 50 else ""
        return resultado + aviso
    except Exception as e:
        return f"Erro na execução SQL: {str(e)}"
    finally:
        conn.close()


def buscar_conhecimento(consulta: str) -> str:
    """
    Busca regras de negócio, documentação ou exemplos salvos em docs/ via RAG.
    """
    return _buscar_rag(consulta)
