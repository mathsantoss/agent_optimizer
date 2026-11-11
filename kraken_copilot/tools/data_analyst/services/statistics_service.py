"""Serviço de análise estatística descritiva e detecção de outliers (IQR) em colunas numéricas."""
from pathlib import Path
from typing import Any
import pandas as pd

from kraken_copilot.tools.data_analyst.services.dataset_service import read_dataset_dataframe


def calculate_descriptive_statistics(
    file_path: Path,
    sample_size: int = 20_000,
) -> dict[str, Any]:
    """
    Calcula métricas descritivas para todas as colunas numéricas do dataset:
    média, desvio padrão, min, quartis, max, contagem de nulos e contagem de outliers (1.5 * IQR).
    """
    df = read_dataset_dataframe(file_path, max_rows=sample_size)
    if df.empty:
        return {
            "vazio": True,
            "mensagem": "Dataset vazio, sem dados numéricos para análise estatística.",
            "estatisticas": {},
            "total_linhas": 0,
            "amostragem_ativa": False,
        }

    total_rows = len(df)
    sampling_active = bool(total_rows >= sample_size)
    numeric_df = df.select_dtypes(include="number")

    if numeric_df.empty:
        return {
            "vazio": False,
            "mensagem": "O dataset não possui colunas numéricas para análise descritiva.",
            "estatisticas": {},
            "total_linhas": total_rows,
            "amostragem_ativa": sampling_active,
        }

    stats_desc = numeric_df.describe().transpose()
    target_cols = [c for c in ("count", "mean", "std", "min", "25%", "50%", "75%", "max") if c in stats_desc.columns]
    stats_table = stats_desc[target_cols].dropna(how="all")

    null_counts: list[int] = []
    outlier_counts: list[int] = []

    for col in stats_table.index:
        col_series = numeric_df[col].dropna()
        null_counts.append(int(numeric_df[col].isna().sum()))
        if len(col_series) > 0:
            q1 = float(col_series.quantile(0.25))
            q3 = float(col_series.quantile(0.75))
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            outliers_mask = (col_series < lower_bound) | (col_series > upper_bound)
            outlier_counts.append(int(outliers_mask.sum()))
        else:
            outlier_counts.append(0)

    stats_table["nulos"] = null_counts
    stats_table["outliers_iqr"] = outlier_counts

    try:
        markdown_representation = stats_table.round(2).to_markdown()
    except Exception:
        markdown_representation = stats_table.round(2).to_string()

    if sampling_active:
        markdown_representation += f"\n\n*(Nota: estatísticas calculadas sobre amostra de {sample_size} linhas)*"

    metrics_by_column: dict[str, dict[str, Any]] = {}
    outlier_chart_data: list[dict[str, Any]] = []
    media_chart_data: list[dict[str, Any]] = []
    total_outliers = int(sum(outlier_counts))

    for col in stats_table.index:
        row = stats_table.loc[col]
        metrics_by_column[str(col)] = {k: (round(float(v), 4) if isinstance(v, (int, float)) else v) for k, v in row.items()}
        media_val = round(float(row.get("mean", 0)), 2)
        outliers_val = int(row.get("outliers_iqr", 0))

        outlier_chart_data.append({
            "coluna": str(col),
            "outliers": outliers_val,
            "media": media_val,
        })
        if media_val > 0:
            media_chart_data.append({
                "coluna": str(col),
                "media": media_val,
            })

    graficos_sugeridos: list[dict[str, Any]] = []
    if total_outliers > 0:
        graficos_sugeridos.append({
            "type": "bar",
            "title": "Outliers Identificados por Coluna (Regra IQR)",
            "subtitle": f"Total de {total_outliers} valores além de 1.5x intervalo interquartil",
            "x": "coluna",
            "y": "outliers",
            "data": outlier_chart_data,
        })
    elif media_chart_data:
        # Se não há outliers, exibe comparativo das médias numéricas para evitar gráficos zerados
        graficos_sugeridos.append({
            "type": "bar",
            "title": "Comparativo das Médias das Colunas Numéricas",
            "subtitle": "Valores médios observados na amostra analítica",
            "x": "coluna",
            "y": "media",
            "data": media_chart_data,
        })

    return {
        "vazio": False,
        "total_linhas_avaliadas": total_rows,
        "amostragem_ativa": sampling_active,
        "limite_amostral": sample_size,
        "colunas_numericas": list(stats_table.index),
        "total_outliers_identificados": total_outliers,
        "tabela_markdown": markdown_representation,
        "metricas_por_coluna": metrics_by_column,
        "graficos_sugeridos": graficos_sugeridos,
    }

