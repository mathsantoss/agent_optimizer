"""Serviço de inserção de novas features em pipelines existentes preservando contratos."""
from pathlib import Path
from typing import Any
import ast

from agent_fiap import config
from agent_fiap.schemas import ToolResult
from agent_fiap.tools.code_optimizer.services.file_service import (
    read_source_file,
    resolve_pipeline_path,
    write_source_file,
)


def inject_feature_into_pipeline_code(
    original_code: str,
    feature_name: str,
    expression: str,
    framework: str = "pandas",
    description: str = "",
) -> tuple[str, str | None]:
    """
    Insere o cálculo de uma nova feature dentro da função principal `run()` antes do retorno `return df`.
    Retorna (código_atualizado, erro_se_houver).
    """
    clean_name = feature_name.strip()
    clean_expr = expression.strip()
    fw = framework.strip().lower()

    if not clean_name or not clean_expr:
        return original_code, "Nome da feature e expressão não podem ser vazios."

    # Prepara o comando de cálculo conforme framework
    comment_line = f"    # Nova Feature: {description}" if description else "    # Nova Feature gerada"
    if fw == "pyspark":
        code_line = f"    df = df.withColumn('{clean_name}', {clean_expr})"
    else:
        code_line = f"    df['{clean_name}'] = {clean_expr}"

    feature_block = f"\n{comment_line}\n{code_line}\n"

    # Localiza o ponto de retorno na função run()
    lines = original_code.splitlines()
    return_index = -1
    in_run_func = False

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("def run(") or stripped.startswith("def executar_pipeline("):
            in_run_func = True
        elif in_run_func and (stripped.startswith("def ") or (line and not line.startswith(" ") and not line.startswith("\t"))):
            in_run_func = False

        if in_run_func and stripped.startswith("return "):
            return_index = idx

    if return_index == -1:
        # Fallback: insere antes do primeiro return no arquivo
        for idx, line in enumerate(lines):
            if line.strip().startswith("return "):
                return_index = idx
                break

    if return_index == -1:
        return original_code, "Não foi possível localizar o ponto de retorno ('return df') no pipeline."

    lines.insert(return_index, feature_block)
    updated_code = "\n".join(lines) + "\n"

    # Valida sintaxe Python do código gerado
    try:
        ast.parse(updated_code)
    except SyntaxError as err:
        return original_code, f"A expressão gerou código com erro de sintaxe: {err}"

    return updated_code, None

