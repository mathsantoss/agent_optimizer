"""Serviço de perfilamento de datasets: esquema, qualidade de dados, chaves e amostragem."""
from pathlib import Path
from typing import Any
import pandas as pd

from agent_fiap import config
from agent_fiap.guardrails import sanitize_untrusted_data_text
from agent_fiap.schemas import ColumnProfile, DateRangeSummary
from agent_fiap.tools.data_analyst.services.dataset_service import read_dataset_dataframe


def profile_dataset_structure(
    file_path: Path,
    sample_size: int = 10_000,
) -> dict[str, Any]:
    """
    Gera o diagnóstico de estrutura e qualidade do dataset a partir de uma amostra controlada.
    Informa explicitamente se houve amostragem e sanitiza os dados contra prompt injection.
    """
    df = read_dataset_dataframe(file_path, max_rows=sample_size)
    if df.empty:
        return {
            "arquivo": str(file_path.name),
            "total_linhas_amostradas": 0,
            "amostragem_ativa": False,
            "vazio": True,
            "mensagem": "Dataset vazio (0 linhas ou 0 bytes).",
            "colunas": {},
            "linhas_duplicadas": 0,
            "chaves_candidatas": [],
            "periodo_temporal": "Nenhum dado temporal disponível",
            "amostra_3_linhas": [],
        }

    total_rows = len(df)
    sampling_active = bool(total_rows >= sample_size)
    duplicate_count = int(df.duplicated().sum())

    columns_metadata: dict[str, dict[str, Any]] = {}
    date_ranges: dict[str, dict[str, str]] = {}
    candidate_keys: list[str] = []

    for column_name in df.columns:
        col_series = df[column_name]
        unique_count = int(col_series.nunique(dropna=True))
        null_count = int(col_series.isna().sum())
        null_percentage = round((null_count / total_rows) * 100, 2) if total_rows > 0 else 0.0

        profile = ColumnProfile(
            data_type=str(col_series.dtype),
            unique_values=unique_count,
            null_count=null_count,
            null_percentage=null_percentage,
        )
        columns_metadata[str(column_name)] = {
            "tipo": profile.data_type,
            "valores_unicos": profile.unique_values,
            "nulos": profile.null_count,
            "percentual_nulos": profile.null_percentage,
        }

        col_lower = str(column_name).lower()
        is_unique_not_null = total_rows > 0 and null_count == 0 and unique_count == total_rows
        is_id_name = col_lower == "id" or col_lower.startswith("id_") or col_lower.endswith("_id")
        if is_unique_not_null or (is_id_name and null_count == 0):
            candidate_keys.append(str(column_name))

        if any(kw in col_lower for kw in ("date", "data", "created", "updated", "timestamp", "time")):
            try:
                datetime_series = pd.to_datetime(col_series, errors="coerce")
                if datetime_series.notna().sum() > 0:
                    summary = DateRangeSummary(
                        start_date=str(datetime_series.min()),
                        end_date=str(datetime_series.max()),
                    )
                    date_ranges[str(column_name)] = {
                        "inicio": summary.start_date,
                        "fim": summary.end_date,
                    }
            except Exception:
                pass

    # Amostra das primeiras 3 linhas com sanitização de texto não confiável
    raw_sample = df.head(3).to_dict(orient="records")
    sanitized_sample = [
        {col: sanitize_untrusted_data_text(val) for col, val in row.items()}
        for row in raw_sample
    ]

    try:
        rel_path = str(file_path.relative_to(config.PROJECT_ROOT))
    except ValueError:
        rel_path = str(file_path)

    return {
        "arquivo": rel_path,
        "tabela_sql": file_path.stem.replace("-", "_"),
        "total_linhas_amostradas": total_rows,
        "amostragem_ativa": sampling_active,
        "limite_amostra": sample_size if sampling_active else total_rows,
        "linhas_duplicadas": duplicate_count,
        "chaves_candidatas": candidate_keys,
        "periodo_temporal": date_ranges if date_ranges else "Nenhuma coluna de data detectada",
        "colunas": columns_metadata,
        "amostra_3_linhas": sanitized_sample,
    }

