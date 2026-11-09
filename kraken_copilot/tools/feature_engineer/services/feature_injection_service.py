"""Serviço de inserção de novas features em pipelines existentes preservando contratos."""
from pathlib import Path
from typing import Any
import ast

from kraken_copilot import config
from kraken_copilot.schemas import ToolResult
from kraken_copilot.tools.code_optimizer.services.file_service import (
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

    # Prioridade de funções de transformação para injeção da feature
    target_prefixes = (
        "def engenharia_features(",
        "def criar_features(",
        "def transform(",
        "def run(",
        "def executar_pipeline(",
    )

    lines = original_code.splitlines()
    return_index = -1
    return_line = ""

    # 1. Procura na função de engenharia ou execução principal
    for prefix in target_prefixes:
        in_target_func = False
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(prefix):
                in_target_func = True
            elif in_target_func and (stripped.startswith("def ") or (line and not line.startswith(" ") and not line.startswith("\t"))):
                in_target_func = False

            if in_target_func and stripped.startswith("return "):
                return_index = idx
                return_line = line
                break
        if return_index != -1:
            break

    # 2. Fallback: insere antes do primeiro return no arquivo
    if return_index == -1:
        for idx, line in enumerate(lines):
            if line.strip().startswith("return "):
                return_index = idx
                return_line = line
                break

    if return_index == -1:
        return original_code, "Não foi possível localizar o ponto de retorno ('return df') no pipeline."

    # Detecta a indentação exata da linha de retorno para manter a formatação do código original
    indent = return_line[: len(return_line) - len(return_line.lstrip())] or "    "

    comment_line = f"{indent}# Nova Feature: {description}" if description else f"{indent}# Nova Feature gerada"
    if fw == "pyspark":
        code_line = f"{indent}df = df.withColumn('{clean_name}', {clean_expr})"
    else:
        code_line = f"{indent}df['{clean_name}'] = {clean_expr}"

    feature_block = f"\n{comment_line}\n{code_line}"
    lines.insert(return_index, feature_block)
    updated_code = "\n".join(lines) + "\n"

    # Valida sintaxe Python do código gerado
    try:
        ast.parse(updated_code)
    except SyntaxError as err:
        return original_code, f"A expressão gerou código com erro de sintaxe: {err}"

    return updated_code, None

