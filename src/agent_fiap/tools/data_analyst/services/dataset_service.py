"""Serviço de gerenciamento, catalogação e carregamento seguro de datasets (CSV e Parquet)."""
from pathlib import Path
import pandas as pd
import pyarrow.parquet as parquet

from agent_fiap import config

SUPPORTED_DATASET_EXTENSIONS = (".csv", ".parquet", ".json", ".jsonl", ".txt")


def list_dataset_files(data_dir: Path | None = None) -> list[Path]:
    """Retorna todos os arquivos .csv e .parquet disponíveis no diretório de dados (ignorando a subpasta conhecimento)."""
    target_dir = data_dir or config.DATA_DIR
    if not target_dir or not target_dir.exists():
        return []
    return [
        file_path
        for file_path in sorted(target_dir.rglob("*"))
        if file_path.is_file()
        and file_path.suffix.lower() in SUPPORTED_DATASET_EXTENSIONS
        and not (config.KNOWLEDGE_DIR.exists() and file_path.is_relative_to(config.KNOWLEDGE_DIR))
        and "conhecimento" not in file_path.parts
    ]


def get_available_datasets_catalog(data_dir: Path | None = None) -> list[dict[str, str | float]]:
    """Gera o catálogo de datasets disponíveis com nome amigável, caminho relativo e tamanho."""
    files = list_dataset_files(data_dir=data_dir)
    catalog: list[dict[str, str | float]] = []
    for file_path in files:
        table_name = file_path.stem.replace("-", "_")
        try:
            rel_path = str(file_path.relative_to(config.PROJECT_ROOT))
        except ValueError:
            rel_path = str(file_path)
        size_kb = round(file_path.stat().st_size / 1024, 1)
        catalog.append({
            "nome": file_path.stem,
            "tabela": table_name,
            "arquivo": rel_path,
            "tabela_sql": table_name,
            "formato": file_path.suffix.lstrip(".").lower(),
            "tamanho": f"{size_kb} KB",
        })
    return catalog


def resolve_dataset_file(dataset_name: str, data_dir: Path | None = None) -> tuple[Path | None, str | None]:
    """
    Localiza o arquivo de dataset pelo nome de forma inequívoca.
    Prioriza correspondência exata de nome ou stem antes de buscar correspondência parcial.
    Retorna (caminho_arquivo, erro_ou_ambiguidade).
    """
    clean_name = dataset_name.strip()
    if not clean_name:
        return None, "Nome do dataset não pode ser vazio."

    dataset_files = list_dataset_files(data_dir=data_dir)
    if not dataset_files:
        return None, "Nenhum dataset encontrado no diretório de dados."

    target_lower = Path(clean_name).name.lower()
    target_stem_lower = Path(clean_name).stem.lower()

    # 1. Correspondência exata pelo nome completo ou stem
    exact_matches: list[Path] = []
    for file_path in dataset_files:
        if file_path.name.lower() == target_lower or file_path.stem.lower() == target_stem_lower:
            exact_matches.append(file_path)

    if len(exact_matches) == 1:
        return exact_matches[0], None
    if len(exact_matches) > 1:
        # Se houver mais de um com extensões diferentes (.csv e .parquet), prioriza a extensão especificada ou parquet
        for match in exact_matches:
            if match.name.lower() == target_lower:
                return match, None
        return exact_matches[0], None

    # 2. Correspondência parcial (apenas se for inequívoca)
    partial_matches = [
        file_path
        for file_path in dataset_files
        if target_stem_lower in file_path.stem.lower()
    ]
    if len(partial_matches) == 1:
        return partial_matches[0], None
    if len(partial_matches) > 1:
        candidates = [p.name for p in partial_matches]
        return None, f"Nome ambíguo '{dataset_name}'. Múltiplos datasets encontrados: {candidates}."

    available = [p.stem for p in dataset_files]
    return None, f"Dataset '{dataset_name}' não encontrado. Disponíveis: {available}."


def read_dataset_dataframe(file_path: Path, max_rows: int | None = None) -> pd.DataFrame:
    """
    Carrega um arquivo CSV ou Parquet em um DataFrame Pandas.
    Trata graciosamente arquivos vazios (0 bytes ou 0 registros).
    """
    if not file_path.exists() or file_path.stat().st_size == 0:
        return pd.DataFrame()

    if file_path.suffix.lower() == ".parquet":
        try:
            parquet_file = parquet.ParquetFile(file_path)
            if parquet_file.metadata.num_rows == 0:
                return pd.DataFrame()
            if max_rows is None:
                return pd.read_parquet(file_path)
            batch_iter = parquet_file.iter_batches(batch_size=max_rows)
            try:
                first_batch = next(batch_iter)
                return first_batch.to_pandas()
            except StopIteration:
                return pd.DataFrame()
        except Exception:
            try:
                df = pd.read_parquet(file_path)
                return df.head(max_rows) if max_rows else df
            except Exception:
                return pd.DataFrame()

    # Tratamento para JSON e JSONL
    if file_path.suffix.lower() in (".json", ".jsonl"):
        try:
            try:
                df = pd.read_json(file_path)
            except ValueError:
                df = pd.read_json(file_path, lines=True)
            return df.head(max_rows) if max_rows else df
        except Exception:
            return pd.DataFrame()

    # Tratamento para CSV e TXT (delimitado)
    try:
        return pd.read_csv(
            file_path,
            sep=None,
            engine="python",
            nrows=max_rows,
            encoding="utf-8-sig",
        )
    except (UnicodeDecodeError, pd.errors.EmptyDataError):
        try:
            return pd.read_csv(
                file_path,
                sep=None,
                engine="python",
                nrows=max_rows,
                encoding="latin-1",
            )
        except Exception:
            return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

