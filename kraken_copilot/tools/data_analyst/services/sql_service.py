"""Serviço de validação AST e execução segura de consultas SQL em memória (SQLite/SQLGlot)."""
from pathlib import Path
import re
import sqlite3
import time
from typing import Any
import pandas as pd
import sqlglot
from sqlglot import exp as sql_expressions

from kraken_copilot import config
from kraken_copilot.guardrails import sanitize_untrusted_data_text
from kraken_copilot.schemas import ToolResult
from kraken_copilot.tools.data_analyst.services.dataset_service import list_dataset_files, read_dataset_dataframe

FORBIDDEN_SQL_STATEMENTS = (
    sql_expressions.Drop,
    sql_expressions.Delete,
    sql_expressions.Insert,
    sql_expressions.Update,
    sql_expressions.Create,
    sql_expressions.Alter,
    sql_expressions.Command,
    sql_expressions.Transaction,
)

FORBIDDEN_KEYWORDS = {
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
    "load_extension",
    "vacuum",
}


def _validate_sql_query(query: str, allowed_table_names: set[str]) -> tuple[list[sql_expressions.Expression] | None, str | None]:
    """
    Valida a consulta SQL via parser AST (SQLGlot):
    - Impede múltiplos comandos.
    - Garante que seja estritamente SELECT ou UNION de leitura.
    - Bloqueia comandos DDL/DML sem depender de falsos positivos de substrings.
    - Bloqueia CROSS JOIN explícito ou JOIN cartesiano sem ON/USING.
    - Valida se as tabelas consultadas pertencem ao catálogo autorizado.
    """
    clean_query = query.strip()
    if not clean_query:
        return None, "Erro: consulta SQL não pode ser vazia."

    # Verifica se a primeira palavra é um comando proibido (evitando falsos positivos em nomes de colunas como 'created_at')
    first_token_match = re.match(r"^\s*([a-zA-Z_]+)", clean_query)
    if first_token_match:
        first_word = first_token_match.group(1).lower()
        if first_word in FORBIDDEN_KEYWORDS:
            return None, f"Erro: comando '{first_word.upper()}' proibido. Apenas consultas SELECT são permitidas."

    try:
        parsed_statements = sqlglot.parse(clean_query)
    except Exception as parse_error:
        return None, f"Erro de sintaxe SQL detectado pelo validador AST: {str(parse_error)}"

    if not parsed_statements or any(stmt is None for stmt in parsed_statements):
        return None, "Erro: consulta SQL inválida ou vazia."

    if len(parsed_statements) > 1:
        return None, "Erro de Guardrail SQL: múltiplas instruções SQL na mesma chamada são proibidas."

    statement = parsed_statements[0]

    # Verifica se o statement principal ou sub-nós contêm operações de escrita/modificação
    if isinstance(statement, FORBIDDEN_SQL_STATEMENTS):
        return None, f"Erro: operação '{statement.key.upper()}' proibida pela política de somente-leitura."

    for forbidden_node in statement.find_all(*FORBIDDEN_SQL_STATEMENTS):
        return None, f"Erro: cláusula proibida '{forbidden_node.key.upper()}'. Apenas SELECT é permitido."

    # Bloqueia produtos cartesianos perigosos (CROSS JOIN ou JOIN sem condição ON/USING)
    for join_node in statement.find_all(sql_expressions.Join):
        join_kind = (join_node.args.get("kind") or "").upper()
        if join_kind == "CROSS" or (not join_node.args.get("on") and not join_node.args.get("using")):
            return None, "Erro de Guardrail SQL: JOIN cartesiano sem condição ON/USING bloqueado para proteção de memória."

    if not isinstance(statement, (sql_expressions.Select, sql_expressions.Union, sql_expressions.Subquery)):
        return None, "Erro: apenas instruções SELECT de leitura analítica são permitidas."

    # Identifica tabelas referenciadas na consulta
    referenced_tables: set[str] = set()
    for table_node in statement.find_all(sql_expressions.Table):
        t_name = table_node.name.lower()
        if t_name:
            referenced_tables.add(t_name)

    # Verifica se há tentativa de consultar tabelas inexistentes ou de sistema
    if allowed_table_names and referenced_tables:
        unknown_tables = referenced_tables - allowed_table_names
        if unknown_tables:
            return None, f"Tabela(s) desconhecida(s) ou não autorizada(s): {sorted(unknown_tables)}. Disponíveis: {sorted(allowed_table_names)}."

    return parsed_statements, None


def execute_sql_service(
    query: str,
    max_rows: int = 50,
    max_table_sample_rows: int = 50_000,
    timeout_seconds: int = 10,
) -> dict[str, Any]:
    """
    Executa a consulta SQL em um banco SQLite em memória carregando apenas as tabelas necessárias.
    Aplica limites de tempo e volume, além de sanitizar saídas contra prompt injection.
    """
    dataset_files = list_dataset_files()
    available_tables: dict[str, Path] = {
        f.stem.replace("-", "_").lower(): f for f in dataset_files
    }

    parsed_statements, validation_error = _validate_sql_query(query, set(available_tables.keys()))
    if validation_error:
        return ToolResult.fail(
            summary=validation_error,
            operation="query_dataset",
            errors=validation_error,
        ).model_dump()

    statement = parsed_statements[0]
    referenced_tables: list[str] = [
        t.name.lower() for t in statement.find_all(sql_expressions.Table) if t.name.lower() in available_tables
    ]
    # Se não identificou tabelas diretamente pelo AST (ex.: SELECT 1+1), permite sem carregar datasets
    unique_tables = sorted(set(referenced_tables))

    connection = sqlite3.connect(":memory:")

    # Registra funções úteis do dialeto ANSI/Databricks no SQLite
    connection.create_function("greatest", -1, lambda *args: max([a for a in args if a is not None], default=None))
    connection.create_function("least", -1, lambda *args: min([a for a in args if a is not None], default=None))
    connection.create_function("concat", -1, lambda *args: "".join(str(a) for a in args if a is not None))
    connection.create_function("year", 1, lambda val: pd.to_datetime(val).year if pd.notnull(val) else None)
    connection.create_function("month", 1, lambda val: pd.to_datetime(val).month if pd.notnull(val) else None)

    # Guardrail de timeout via progress_handler do SQLite
    start_time = time.perf_counter()

    def timeout_check():
        if time.perf_counter() - start_time > timeout_seconds:
            return 1
        return 0

    connection.set_progress_handler(timeout_check, 5000)

    try:
        sampled_tables: list[str] = []
        for table_name in unique_tables:
            file_path = available_tables[table_name]
            df = read_dataset_dataframe(file_path, max_rows=max_table_sample_rows)
            if len(df) >= max_table_sample_rows:
                sampled_tables.append(table_name)
            df.to_sql(table_name, connection, if_exists="replace", index=False)

        cursor = connection.cursor()
        cursor.execute(query)

        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        fetched_rows = cursor.fetchmany(max_rows + 1)
        total_fetched = len(fetched_rows)
        has_more = total_fetched > max_rows
        display_rows = fetched_rows[:max_rows]

        result_df = pd.DataFrame(display_rows, columns=columns) if columns else pd.DataFrame()

        # Sanitiza colunas de texto contra Indirect Prompt Injection
        for col_name in result_df.select_dtypes(include="object").columns:
            result_df[col_name] = result_df[col_name].map(sanitize_untrusted_data_text)

        try:
            markdown_table = result_df.to_markdown(index=False)
        except Exception:
            markdown_table = result_df.to_string(index=False)

        warnings: list[str] = []
        if has_more:
            warnings.append(f"Exibindo limite de {max_rows} linhas. Utilize filtros ou LIMIT na consulta.")
        if sampled_tables:
            warnings.append(f"Tabelas {sampled_tables} carregadas com limite amostral de {max_table_sample_rows} linhas.")

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return ToolResult.ok(
            summary=f"Consulta executada com sucesso ({len(result_df)} linhas em {elapsed_ms}ms).",
            operation="query_dataset",
            data={
                "query": query,
                "tabelas_consultadas": unique_tables,
                "total_linhas_retornadas": len(result_df),
                "colunas": columns,
                "tabela_markdown": markdown_table,
                "registros": result_df.to_dict(orient="records"),
            },
            warnings=warnings,
        ).model_dump()
    except Exception as err:
        err_str = str(err)
        if "interrupted" in err_str.lower():
            err_msg = f"Erro de Guardrail SQL: consulta excedeu o tempo limite de {timeout_seconds} segundos."
        else:
            err_msg = f"Erro na execução da consulta SQL: {err_str}"
        return ToolResult.fail(
            summary=err_msg,
            operation="query_dataset",
            errors=err_msg,
        ).model_dump()
    finally:
        connection.close()

