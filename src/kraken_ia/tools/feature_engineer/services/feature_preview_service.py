"""Serviço de cálculo e prévia em amostra de novas features para validação rápida e agnóstica."""
from pathlib import Path
from typing import Any
import re
import numpy as np
import pandas as pd

from kraken_ia import config
from kraken_ia.schemas import FeaturePreviewSummary
from kraken_ia.tools.data_analyst.services.dataset_service import (
    read_dataset_dataframe,
    resolve_dataset_file,
)
from kraken_ia.tools.feature_engineer.services.pipeline_generator_service import (
    infer_candidate_features_from_schema,
)


def preview_features_on_sample(
    dataset_name: str,
    feature_expressions: dict[str, str] | None = None,
    framework: str = "pandas",
    sample_rows: int = 100,
) -> FeaturePreviewSummary:
    """
    Executa o cálculo de features propostas sobre uma amostra segura de qualquer dataset
    para inspeção prévia de valores, tipos e nulos, sem regras hardcoded de domínio.
    """
    file_path, err = resolve_dataset_file(dataset_name)
    if err or file_path is None or not file_path.exists():
        return FeaturePreviewSummary(
            source_dataset=dataset_name,
            framework=framework,
            total_sample_rows=0,
            new_features_count=0,
            new_columns=[],
            sample_preview=[],
            null_counts={},
        )

    # 1. Carrega amostra segura
    try:
        df = read_dataset_dataframe(file_path, max_rows=sample_rows).copy()
        if df.empty:
            raise ValueError("Dataset vazio ou formato ilegível.")
    except Exception:
        return FeaturePreviewSummary(
            source_dataset=dataset_name,
            framework=framework,
            total_sample_rows=0,
            new_features_count=0,
            new_columns=[],
            sample_preview=[],
            null_counts={},
        )

    # 2. Determina expressões a calcular
    expressions = feature_expressions or {}
    if not expressions:
        inferred = infer_candidate_features_from_schema(df, framework=framework)
        expressions = {f.name: f.expression for f in inferred[:4]}

    # Se a expressão necessitar de acessor .dt, realiza conversão prévia da coluna temporal
    for expr in expressions.values():
        if ".dt." in expr:
            matches = re.findall(r"df\['([^']+)'\]\.dt\.", expr)
            for m in matches:
                if m in df.columns:
                    df[m] = pd.to_datetime(df[m], errors="coerce")

    new_cols: list[str] = []
    nulls_dict: dict[str, int] = {}

    # 3. Avaliação segura em escopo restrito
    safe_globals = {"pd": pd, "np": np}
    safe_locals = {"df": df}

    for feat_name, expr in expressions.items():
        try:
            computed = eval(expr, safe_globals, safe_locals)
            df[feat_name] = computed
            new_cols.append(feat_name)
            nulls_dict[feat_name] = int(df[feat_name].isna().sum())
        except Exception:
            continue

    # 4. Seleciona colunas contextuais da amostra (primeiras 5 colunas existentes + novas features)
    existing_sample_cols = [c for c in df.columns if c not in new_cols][:5]
    preview_cols = existing_sample_cols + new_cols
    preview_df = df[preview_cols].head(5)

    return FeaturePreviewSummary(
        source_dataset=dataset_name,
        framework=framework,
        total_sample_rows=len(df),
        new_features_count=len(new_cols),
        new_columns=new_cols,
        sample_preview=preview_df.to_dict(orient="records"),
        null_counts=nulls_dict,
    )
