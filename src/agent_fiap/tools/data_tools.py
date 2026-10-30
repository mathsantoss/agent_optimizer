"""Ferramentas analíticas e de exploração de dados: catalogação, perfilamento, estatísticas e SQL."""
import json
from pathlib import Path
import sqlite3
import pandas as pd
import pyarrow.parquet as parquet
import sqlglot
from sqlglot import exp as sql_expressions

from .. import config
from ..schemas import ColumnProfile, DateRangeSummary

FORBIDDEN_SQL_COMMANDS = (
    "drop",
    "delete",
    "insert",
    "update",
    "alter",
    "create",
    "truncate",
    "replace",
    "attach",
    "detach",
    "pragma",
)

FORBIDDEN_AST_EXPRESSIONS = (
    sql_expressions.Drop,
    sql_expressions.Delete,
    sql_expressions.Insert,
    sql_expressions.Update,
    sql_expressions.Create,
    sql_expressions.Alter,
    sql_expressions.Command,
)


def _list_dataset_files() -> list[Path]:
    """Retorna todos os arquivos .csv e .parquet disponíveis no diretório de dados (ignorando a subpasta conhecimento)."""
    if not config.DATA_DIR.exists():
        return []
    return [
        file_path
        for file_path in sorted(config.DATA_DIR.rglob("*"))
        if file_path.is_file()
        and file_path.suffix in (".csv", ".parquet")
        and not file_path.is_relative_to(config.KNOWLEDGE_DIR)
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


def _validate_readonly_sql(query: str) -> str | None:
    """
    Valida se a consulta SQL é estritamente de leitura (SELECT) utilizando análise léxica
    e árvore sintática abstrata (AST) via SQLGlot. Retorna mensagem de erro ou None se válida.
    """
    normalized_query = query.strip().lower()
    if not normalized_query:
        return "Erro: a consulta SQL não pode ser vazia."

    for forbidden_command in FORBIDDEN_SQL_COMMANDS:
        if normalized_query.startswith(forbidden_command) or f" {forbidden_command} " in f" {normalized_query} ":
            return f"Erro: comando '{forbidden_command.upper()}' proibido. Apenas consultas SELECT são permitidas."

    try:
        parsed_statements = sqlglot.parse(query)
    except Exception as parse_error:
        return f"Erro de sintaxe SQL detectado pelo validador AST: {str(parse_error)}"

    if not parsed_statements or any(statement is None for statement in parsed_statements):
        return "Erro: consulta SQL inválida ou vazia."

    for statement in parsed_statements:
        if isinstance(statement, FORBIDDEN_AST_EXPRESSIONS):
            return f"Erro: operação '{statement.key.upper()}' proibida pela política somente-leitura."
        for forbidden_node in statement.find_all(*FORBIDDEN_AST_EXPRESSIONS):
            return f"Erro: cláusula '{forbidden_node.key.upper()}' proibida. Apenas consultas SELECT são permitidas."
        if not isinstance(statement, (sql_expressions.Select, sql_expressions.Union, sql_expressions.Subquery)):
            return "Erro: apenas instruções SELECT de leitura são permitidas."

    return None


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
    quantidade de duplicatas, chaves candidatas, colunas com tipos de dados,
    contagem e percentual de nulos, intervalo temporal e amostra real das primeiras 3 linhas.
    """
    file_path = _find_dataset_file(dataset_name)
    if not file_path:
        available_datasets = [item.stem for item in _list_dataset_files()]
        return f"Dataset '{dataset_name}' não encontrado. Disponíveis: {available_datasets}"

    try:
        sample_dataframe = _read_dataframe(file_path, max_rows=10_000)
        total_rows = len(sample_dataframe)
        duplicate_row_count = int(sample_dataframe.duplicated().sum())
        columns_metadata: dict[str, dict] = {}
        date_ranges: dict[str, dict] = {}
        candidate_keys: list[str] = []

        for column_name in sample_dataframe.columns:
            column_series = sample_dataframe[column_name]
            unique_count = int(column_series.nunique(dropna=True))
            null_count = int(column_series.isna().sum())
            null_percentage = round((null_count / total_rows) * 100, 2) if total_rows > 0 else 0.0

            column_profile = ColumnProfile(
                data_type=str(column_series.dtype),
                unique_values=unique_count,
                null_count=null_count,
                null_percentage=null_percentage,
            )
            columns_metadata[column_name] = {
                "tipo": column_profile.data_type,
                "valores_unicos": column_profile.unique_values,
                "nulos": column_profile.null_count,
                "percentual_nulos": column_profile.null_percentage,
            }

            normalized_column_name = column_name.lower()
            is_unique_not_null = total_rows > 0 and null_count == 0 and unique_count == total_rows
            is_identifier_column = (
                normalized_column_name == "id"
                or normalized_column_name.startswith("id_")
                or normalized_column_name.endswith("_id")
            )
            if is_unique_not_null or (is_identifier_column and null_count == 0):
                candidate_keys.append(column_name)

            if any(keyword in normalized_column_name for keyword in ("date", "data", "created", "updated")):
                try:
                    datetime_series = pd.to_datetime(column_series, errors="coerce")
                    if datetime_series.notna().sum() > 0:
                        date_summary = DateRangeSummary(
                            start_date=str(datetime_series.min()),
                            end_date=str(datetime_series.max()),
                        )
                        date_ranges[column_name] = {
                            "inicio": date_summary.start_date,
                            "fim": date_summary.end_date,
                        }
                except Exception:
                    pass

        profile_result = {
            "arquivo": str(file_path.relative_to(config.PROJECT_ROOT)),
            "tabela_sql": file_path.stem.replace("-", "_"),
            "total_linhas_amostradas": total_rows,
            "linhas_duplicadas": duplicate_row_count,
            "chaves_candidatas": candidate_keys,
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
    percentis 25%/50%/75%, máximo, contagem de nulos e quantidade de outliers via IQR)
    das colunas numéricas do dataset informado.
    """
    file_path = _find_dataset_file(dataset_name)
    if not file_path:
        available_datasets = [item.stem for item in _list_dataset_files()]
        return f"Dataset '{dataset_name}' não encontrado. Disponíveis: {available_datasets}"

    try:
        dataframe = _read_dataframe(file_path, max_rows=20_000)
        numeric_dataframe = dataframe.select_dtypes(include="number")
        if numeric_dataframe.empty:
            return f"O dataset '{dataset_name}' não possui colunas numéricas para resumo estatístico."

        statistics_table = numeric_dataframe.describe().transpose()
        selected_columns = [
            column for column in ("count", "mean", "std", "min", "25%", "50%", "75%", "max")
            if column in statistics_table.columns
        ]
        statistics_table = statistics_table[selected_columns].dropna(how="all")

        # Adiciona contagem de nulos e detecção de outliers pelo critério de Tukey (1.5 * IQR)
        null_counts = []
        outlier_counts = []
        for column_name in statistics_table.index:
            column_series = numeric_dataframe[column_name].dropna()
            null_counts.append(int(numeric_dataframe[column_name].isna().sum()))
            if len(column_series) > 0:
                first_quartile = column_series.quantile(0.25)
                third_quartile = column_series.quantile(0.75)
                interquartile_range = third_quartile - first_quartile
                lower_bound = first_quartile - 1.5 * interquartile_range
                upper_bound = third_quartile + 1.5 * interquartile_range
                outliers_mask = (column_series < lower_bound) | (column_series > upper_bound)
                outlier_counts.append(int(outliers_mask.sum()))
            else:
                outlier_counts.append(0)

        statistics_table["nulos"] = null_counts
        statistics_table["outliers_iqr"] = outlier_counts

        try:
            return statistics_table.round(2).to_markdown()
        except Exception:
            return statistics_table.round(2).to_string()
    except Exception as error:
        return f"Erro ao gerar resumo estatístico: {str(error)}"


def execute_sql_query(query: str) -> str:
    """
    Valida a sintaxe SQL via SQLGlot e executa uma consulta somente-leitura (SELECT)
    sobre os datasets disponíveis em pipeline/dados/.
    O nome de cada tabela corresponde ao nome do arquivo sem extensão (exibido em list_datasets).
    Suporta funções analíticas como GREATEST, LEAST, CONCAT, YEAR e MONTH.
    """
    validation_error = _validate_readonly_sql(query)
    if validation_error:
        return validation_error

    normalized_query = query.strip().lower()
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
