"""Ferramentas analíticas e de exploração de dados: catalogação, perfilamento, estatísticas e SQL."""
import json
from pathlib import Path
import sqlite3
import pandas as pd
import pyarrow.parquet as parquet

from .. import config

FORBIDDEN_SQL_COMMANDS = (
    "drop",
    "delete",
    "insert",
    "update",
    "alter",
    "create",
    "truncate",
    "replace",
)


def _list_dataset_files() -> list[Path]:
    """Retorna todos os arquivos .csv e .parquet disponíveis no diretório de dados."""
    if not config.DATA_DIR.exists():
        return []
    return [
        file_path
        for file_path in sorted(config.DATA_DIR.rglob("*"))
        if file_path.is_file() and file_path.suffix in (".csv", ".parquet")
    ]


def _read_dataframe(file_path: Path, max_rows: int | None = None) -> pd.DataFrame:
    """Carrega um arquivo CSV ou Parquet em um DataFrame Pandas com detecção automática de separador e codificação."""
    if file_path.suffix == ".parquet":
        if max_rows is None:
            return pd.read_parquet(file_path)
        parquet_file = parquet.ParquetFile(file_path)
        first_batch = next(parquet_file.iter_batches(batch_size=max_rows))
        return first_batch.to_pandas()

    try:
        return pd.read_csv(
            file_path,
            sep=None,
            engine="python",
            nrows=max_rows,
            encoding="utf-8-sig",
        )
    except UnicodeDecodeError:
        return pd.read_csv(
            file_path,
            sep=None,
            engine="python",
            nrows=max_rows,
            encoding="latin-1",
        )


def _find_dataset_file(dataset_name: str) -> Path | None:
    """Localiza o arquivo de dataset pelo nome com ou sem extensão."""
    dataset_files = _list_dataset_files()
    target_name = Path(dataset_name.strip()).name.lower()
    target_stem = Path(dataset_name.strip()).stem.lower()

    for file_path in dataset_files:
        file_stem = file_path.stem.lower()
        if file_path.name.lower() == target_name or file_stem == target_stem:
            return file_path
        if target_stem in file_stem or file_stem in target_stem:
            return file_path
    return None


def _convert_to_float(value):
    """Converte o valor para ponto flutuante quando possível para comparação numérica."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return value


def _sql_greatest(*values):
    """Implementa a função SQL GREATEST ignorando valores nulos."""
    valid_values = [value for value in values if value is not None]
    if not valid_values:
        return None
    try:
        return max(valid_values, key=_convert_to_float)
    except Exception:
        return max(valid_values)


def _sql_least(*values):
    """Implementa a função SQL LEAST ignorando valores nulos."""
    valid_values = [value for value in values if value is not None]
    if not valid_values:
        return None
    try:
        return min(valid_values, key=_convert_to_float)
    except Exception:
        return min(valid_values)


def list_datasets() -> str:
    """
    Lista todos os datasets (.csv e .parquet) disponíveis em pipeline/dados/.
    Retorna o caminho relativo do arquivo, o nome da tabela SQL e o tamanho em KB.
    """
    dataset_files = _list_dataset_files()
    if not dataset_files:
        return "Nenhum dataset encontrado no diretório de dados (pipeline/dados/)."

    catalog_items = []
    for file_path in dataset_files:
        table_name = file_path.stem.replace("-", "_")
        file_size_kilobytes = round(file_path.stat().st_size / 1024, 1)
        catalog_items.append({
            "arquivo": str(file_path.relative_to(config.PROJECT_ROOT)),
            "tabela_sql": table_name,
            "tamanho": f"{file_size_kilobytes} KB",
        })
    return json.dumps(catalog_items, ensure_ascii=False, indent=2)


def explore_dataset(dataset_name: str) -> str:
    """
    Inspeciona um dataset gerando um perfil completo: total de linhas amostradas,
    colunas, tipos de dados, contagem de valores únicos e nulos, intervalo temporal
    e amostra real das primeiras 3 linhas.
    """
    file_path = _find_dataset_file(dataset_name)
    if not file_path:
        available_datasets = [item.stem for item in _list_dataset_files()]
        return f"Dataset '{dataset_name}' não encontrado. Disponíveis: {available_datasets}"

    try:
        sample_dataframe = _read_dataframe(file_path, max_rows=10_000)
        columns_metadata = {}
        date_ranges = {}

        for column_name in sample_dataframe.columns:
            columns_metadata[column_name] = {
                "tipo": str(sample_dataframe[column_name].dtype),
                "valores_unicos": int(sample_dataframe[column_name].nunique()),
                "nulos": int(sample_dataframe[column_name].isna().sum()),
            }
            if any(keyword in column_name.lower() for keyword in ("date", "data", "created", "updated")):
                try:
                    datetime_series = pd.to_datetime(sample_dataframe[column_name], errors="coerce")
                    if datetime_series.notna().sum() > 0:
                        date_ranges[column_name] = {
                            "inicio": str(datetime_series.min()),
                            "fim": str(datetime_series.max()),
                        }
                except Exception:
                    pass

        profile_result = {
            "arquivo": str(file_path.relative_to(config.PROJECT_ROOT)),
            "tabela_sql": file_path.stem.replace("-", "_"),
            "total_linhas_amostradas": len(sample_dataframe),
            "periodo_temporal": date_ranges if date_ranges else "Nenhuma coluna de data detectada",
            "colunas": columns_metadata,
            "amostra_3_linhas": sample_dataframe.head(3).to_dict(orient="records"),
        }
        return json.dumps(profile_result, ensure_ascii=False, indent=2, default=str)
    except Exception as error:
        return f"Erro ao explorar dataset '{dataset_name}': {str(error)}"


def generate_statistical_summary(dataset_name: str) -> str:
    """
    Gera um resumo estatístico descritivo (contagem, média, desvio padrão, mínimo,
    mediana e máximo) das colunas numéricas do dataset informado.
    """
    file_path = _find_dataset_file(dataset_name)
    if not file_path:
        available_datasets = [item.stem for item in _list_dataset_files()]
        return f"Dataset '{dataset_name}' não encontrado. Disponíveis: {available_datasets}"

    try:
        dataframe = _read_dataframe(file_path, max_rows=20_000)
        statistics_table = dataframe.describe().transpose()
        statistics_table = statistics_table[["count", "mean", "std", "min", "50%", "max"]].dropna(how="all")
        try:
            return statistics_table.round(2).to_markdown()
        except Exception:
            return statistics_table.round(2).to_string()
    except Exception as error:
        return f"Erro ao gerar resumo estatístico: {str(error)}"


def execute_sql_query(query: str) -> str:
    """
    Executa uma consulta SQL (somente SELECT) sobre os datasets disponíveis.
    O nome de cada tabela corresponde ao nome do arquivo sem extensão (exibido em list_datasets).
    Suporta funções analíticas como GREATEST, LEAST, CONCAT, YEAR e MONTH.
    """
    normalized_query = query.strip().lower()
    for forbidden_command in FORBIDDEN_SQL_COMMANDS:
        if normalized_query.startswith(forbidden_command) or f" {forbidden_command} " in f" {normalized_query} ":
            return f"Erro: comando '{forbidden_command.upper()}' proibido. Apenas consultas SELECT são permitidas."

    dataset_files = _list_dataset_files()
    connection = sqlite3.connect(":memory:")

    # Registra funções SQL analíticas compatíveis com dialetos modernos
    connection.create_function("greatest", -1, _sql_greatest)
    connection.create_function("least", -1, _sql_least)
    connection.create_function(
        "concat",
        -1,
        lambda *values: "".join(str(value) for value in values if value is not None),
    )
    connection.create_function("year", 1, lambda date_value: int(str(date_value)[:4]) if date_value else None)
    connection.create_function("month", 1, lambda date_value: int(str(date_value)[5:7]) if date_value else None)

    try:
        loaded_tables = []
        for file_path in dataset_files:
            table_name = file_path.stem.replace("-", "_").lower()
            is_table_referenced = (
                table_name in normalized_query
                or file_path.stem.lower() in normalized_query
                or (len(dataset_files) == 1 and "from" in normalized_query)
            )
            if is_table_referenced:
                dataframe = _read_dataframe(file_path, max_rows=100_000)
                dataframe.to_sql(table_name, connection, index=False, if_exists="replace")
                loaded_tables.append(table_name)

        if not loaded_tables:
            available_tables = [item.stem.replace("-", "_") for item in dataset_files]
            return f"Nenhuma tabela válida encontrada na query. Tabelas disponíveis: {available_tables}"

        result_dataframe = pd.read_sql_query(query, connection)
        total_rows = len(result_dataframe)
        limited_dataframe = result_dataframe.head(50)

        try:
            formatted_output = limited_dataframe.to_markdown(index=False)
        except Exception:
            formatted_output = limited_dataframe.to_string(index=False)

        truncation_notice = (
            f"\n\n(Exibindo {len(limited_dataframe)} de {total_rows} linhas)"
            if total_rows > 50
            else ""
        )
        return formatted_output + truncation_notice
    except Exception as error:
        return f"Erro na execução SQL: {str(error)}"
    finally:
        connection.close()
