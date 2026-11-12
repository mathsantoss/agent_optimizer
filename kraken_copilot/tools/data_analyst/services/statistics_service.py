"""Serviço de análise estatística descritiva e detecção de outliers (IQR) em colunas numéricas."""
from pathlib import Path
from typing import Any
import pandas as pd

from kraken_copilot.schemas import KrakenStatisticalMetric, KrakenStatisticalReport
from kraken_copilot.tools.data_analyst.services.dataset_service import read_dataset_dataframe


def calculate_descriptive_statistics(
    file_path: Path,
    sample_size: int = 20_000,
    columns: list[str] | str | None = None,
) -> dict[str, Any]:
    """
    Calcula métricas descritivas no formato clássico de describe (Eixo X = colunas, Eixo Y = métricas):
    média, desvio padrão, min, quartis, max, contagem de nulos e contagem de outliers (1.5 * IQR).
    Permite filtrar colunas específicas quando solicitado pelo usuário.
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

    # Se o usuário definir colunas específicas, filtra
    if columns:
        if isinstance(columns, str):
            requested = [c.strip() for c in columns.split(",") if c.strip()]
        else:
            requested = list(columns)
        valid_cols = [c for c in requested if c in numeric_df.columns]
        if valid_cols:
            numeric_df = numeric_df[valid_cols]

    # Describe clássico (Eixo X = Colunas do dataset, Eixo Y = Métricas estatísticas)
    desc = numeric_df.describe()
    target_rows = [c for c in ("count", "mean", "std", "min", "25%", "50%", "75%", "max") if c in desc.index]
    stats_table = desc.loc[target_rows].copy()

    null_counts: dict[str, int] = {}
    outlier_counts: dict[str, int] = {}

    for col in numeric_df.columns:
        col_series = numeric_df[col].dropna()
        null_counts[col] = int(numeric_df[col].isna().sum())
        if len(col_series) > 0:
            q1 = float(col_series.quantile(0.25))
            q3 = float(col_series.quantile(0.75))
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            outliers_mask = (col_series < lower_bound) | (col_series > upper_bound)
            outlier_counts[col] = int(outliers_mask.sum())
        else:
            outlier_counts[col] = 0

    stats_table.loc["nulos"] = pd.Series(null_counts)
    stats_table.loc["outliers_iqr"] = pd.Series(outlier_counts)

    # Nomeia explicitamente o índice como "Métrica" para cabeçalho do markdown
    stats_table.index.name = "Métrica"

    try:
        markdown_representation = stats_table.round(2).reset_index().to_markdown(index=False)
    except Exception:
        markdown_representation = stats_table.round(2).reset_index().to_string(index=False)

    if sampling_active:
        markdown_representation += f"\n\n*(Nota: estatísticas calculadas sobre amostra de {sample_size} linhas)*"

    metrics_by_column: dict[str, dict[str, Any]] = {}
    outlier_chart_data: list[dict[str, Any]] = []
    media_chart_data: list[dict[str, Any]] = []
    total_outliers = int(sum(outlier_counts.values()))
    stat_metrics: list[KrakenStatisticalMetric] = []

    for col in stats_table.columns:
        col_series = stats_table[col]
        metrics_by_column[str(col)] = {k: (round(float(v), 4) if isinstance(v, (int, float)) else v) for k, v in col_series.items()}
        media_val = round(float(col_series.get("mean", 0)), 2)
        outliers_val = int(col_series.get("outliers_iqr", 0))

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

        q1 = float(col_series.get("25%", 0.0))
        q3 = float(col_series.get("75%", 0.0))
        iqr = q3 - q1
        stat_metrics.append(
            KrakenStatisticalMetric(
                coluna=str(col),
                media=round(float(col_series.get("mean", 0.0)), 4),
                desvio_padrao=round(float(col_series.get("std", 0.0)), 4),
                minimo=round(float(col_series.get("min", 0.0)), 4),
                q25=round(q1, 4),
                mediana=round(float(col_series.get("50%", 0.0)), 4),
                q75=round(q3, 4),
                maximo=round(float(col_series.get("max", 0.0)), 4),
                nulos=int(col_series.get("nulos", 0)),
                outliers_iqr=int(col_series.get("outliers_iqr", 0)),
                limite_inferior_iqr=round(q1 - 1.5 * iqr, 4),
                limite_superior_iqr=round(q3 + 1.5 * iqr, 4),
            )
        )

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

    kraken_statistical_report = KrakenStatisticalReport(
        dataset_nome=file_path.stem.replace("-", "_"),
        total_linhas_analisadas=total_rows,
        amostragem_ativa=sampling_active,
        total_outliers_geral=total_outliers,
        metricas_colunas=stat_metrics,
        tabela_markdown=markdown_representation,
        insights_estatisticos=[
            f"Detectados {total_outliers} outliers no total com base na regra IQR 1.5x." if total_outliers > 0 else "Nenhum outlier detectado.",
            f"Análise estatística realizada sobre {total_rows} registros.",
        ],
    )

    return {
        "vazio": False,
        "total_linhas_avaliadas": total_rows,
        "amostragem_ativa": sampling_active,
        "limite_amostral": sample_size,
        "colunas_numericas": list(stats_table.columns),
        "total_outliers_identificados": total_outliers,
        "tabela_markdown": markdown_representation,
        "metricas_por_coluna": metrics_by_column,
        "graficos_sugeridos": graficos_sugeridos,
        "kraken_statistical_report": kraken_statistical_report.model_dump(),
    }

