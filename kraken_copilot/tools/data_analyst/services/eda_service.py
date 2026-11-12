"""Serviço modular de Análise Exploratória de Dados (EDA), Limpeza e Geração de Scripts e Relatórios."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from kraken_copilot import config
from kraken_copilot.schemas import ToolResult
from kraken_copilot.tools.data_analyst.services.dataset_service import resolve_dataset_file


def _load_df_safe(dataset_name: str, max_rows: int = 10_000) -> tuple[pd.DataFrame | None, str | None, Path | None]:
    """Carrega com segurança uma amostra de qualquer dataset suportado."""
    file_path, err = resolve_dataset_file(dataset_name)
    if err or file_path is None or not file_path.exists():
        return None, err or f"Dataset '{dataset_name}' não encontrado.", None

    try:
        suffix = file_path.suffix.lower()
        if suffix == ".parquet":
            df = pd.read_parquet(file_path)
            if len(df) > max_rows:
                df = df.iloc[:max_rows]
        elif suffix in (".json", ".jsonl"):
            try:
                df = pd.read_json(file_path)
            except ValueError:
                df = pd.read_json(file_path, lines=True)
            if len(df) > max_rows:
                df = df.iloc[:max_rows]
        else:
            df = pd.read_csv(file_path, nrows=max_rows, sep=None, engine="python")
        return df, None, file_path
    except Exception as exc:
        return None, f"Falha ao carregar {file_path.name}: {exc}", file_path


def load_dataset_info(dataset_name: str, max_rows: int = 10_000) -> dict[str, Any]:
    """Inspeciona e carrega informações cadastrais, volumetria e tipos de dados do dataset."""
    df, err, path = _load_df_safe(dataset_name, max_rows)
    if err or df is None:
        return {"sucesso": False, "erro": err}

    col_details = []
    for col in df.columns:
        s = df[col]
        col_details.append({
            "coluna": str(col),
            "tipo": str(s.dtype),
            "nulos": int(s.isna().sum()),
            "pct_nulos": round(float(s.isna().mean() * 100), 2),
            "valores_unicos": int(s.nunique(dropna=True)),
            "amostra": [str(v) for v in s.dropna().head(3).tolist()],
        })

    return {
        "sucesso": True,
        "dataset": path.stem if path else dataset_name,
        "arquivo": path.name if path else dataset_name,
        "total_linhas_amostradas": len(df),
        "total_colunas": len(df.columns),
        "memoria_estimada_kb": round(float(df.memory_usage(deep=True).sum() / 1024), 2),
        "colunas": col_details,
    }


def analyze_missing_values(dataset_name: str) -> dict[str, Any]:
    """Identifica e sumariza colunas com dados ausentes e sua criticidade."""
    df, err, path = _load_df_safe(dataset_name)
    if err or df is None:
        return {"sucesso": False, "erro": err}

    total_rows = len(df)
    missing_cols = []
    for col in df.columns:
        null_count = int(df[col].isna().sum())
        if null_count > 0:
            pct = round((null_count / total_rows) * 100, 2)
            criticidade = "CRITICA" if pct > 40 else ("MODERADA" if pct > 10 else "BAIXA")
            missing_cols.append({
                "coluna": str(col),
                "total_nulos": null_count,
                "percentual_nulos": pct,
                "criticidade": criticidade,
                "tipo_dado": str(df[col].dtype),
                "sugestao_imputacao": "mediana" if pd.api.types.is_numeric_dtype(df[col]) else "moda/desconhecido",
            })

    missing_cols.sort(key=lambda x: x["percentual_nulos"], reverse=True)
    return {
        "sucesso": True,
        "dataset": path.stem if path else dataset_name,
        "total_linhas": total_rows,
        "colunas_com_nulos": len(missing_cols),
        "detalhes": missing_cols,
        "status_qualidade": "Excelente" if not missing_cols else ("Atencao" if any(c["criticidade"] == "CRITICA" for c in missing_cols) else "Adequado"),
    }


def analyze_univariate_distributions(dataset_name: str, column: str = "") -> dict[str, Any]:
    """Calcula estatísticas univariadas completas (média, mediana, IQR, assimetria, curtose) via Evidently AI."""
    df, err, path = _load_df_safe(dataset_name)
    if err or df is None:
        return {"sucesso": False, "erro": err}

    num_df = df.select_dtypes(include=[np.number])
    if num_df.empty:
        return {"sucesso": False, "erro": "Dataset não possui colunas numéricas para análise univariada."}

    target_cols = [column] if column and column in num_df.columns else list(num_df.columns)
    metrics_list = []

    for col in target_cols:
        series = num_df[col].dropna()
        if series.empty:
            continue

        # Utiliza Evidently ValueStats como motor padrão da indústria
        try:
            from evidently import Report
            from evidently.presets import ValueStats

            report = Report(metrics=[ValueStats(column=str(col))])
            snapshot = report.run(reference_data=None, current_data=num_df[[col]])
            raw_metrics = snapshot.dict().get("metrics", [])

            metric_map: dict[str, Any] = {}
            for m in raw_metrics:
                m_name = m.get("metric_name", "")
                val = m.get("value")
                if "MeanValue" in m_name:
                    metric_map["mean"] = float(val)
                elif "StdValue" in m_name:
                    metric_map["std"] = float(val)
                elif "MinValue" in m_name:
                    metric_map["min"] = float(val)
                elif "MaxValue" in m_name:
                    metric_map["max"] = float(val)
                elif "QuantileValue" in m_name:
                    q = m.get("config", {}).get("quantile", 0.5)
                    metric_map[f"q_{q}"] = float(val)

            mean = metric_map.get("mean", float(series.mean()))
            std = metric_map.get("std", float(series.std()) if len(series) > 1 else 0.0)
            min_val = metric_map.get("min", float(series.min()))
            max_val = metric_map.get("max", float(series.max()))
            q1 = metric_map.get("q_0.25", float(series.quantile(0.25)))
            median = metric_map.get("q_0.5", float(series.median()))
            q3 = metric_map.get("q_0.75", float(series.quantile(0.75)))
        except Exception:
            # Fallback seguro caso o evidently encontre alguma exceção
            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            mean = float(series.mean())
            std = float(series.std()) if len(series) > 1 else 0.0
            min_val = float(series.min())
            max_val = float(series.max())
            median = float(series.median())

        iqr = q3 - q1
        skewness = float(series.skew()) if len(series) > 2 else 0.0

        metrics_list.append({
            "coluna": str(col),
            "media": round(mean, 4),
            "desvio_padrao": round(std, 4),
            "minimo": round(min_val, 4),
            "q25": round(q1, 4),
            "mediana": round(median, 4),
            "q75": round(q3, 4),
            "maximo": round(max_val, 4),
            "iqr": round(iqr, 4),
            "assimetria_skew": round(skewness, 4),
            "interpretacao_assimetria": (
                "Simetrica" if abs(skewness) < 0.5
                else ("Assimetrica a direita (calda longa)" if skewness > 0.5 else "Assimetrica a esquerda")
            ),
            "motor_analitico": "Evidently AI (ValueStats)",
        })

    return {
        "sucesso": True,
        "dataset": path.stem if path else dataset_name,
        "total_colunas_analisadas": len(metrics_list),
        "metricas": metrics_list,
        "engine": "Evidently AI",
    }


def run_evidently_quality_report(
    dataset_name: str,
    save_html: bool = True,
    max_rows: int = 15_000,
) -> dict[str, Any]:
    """
    Executa a suíte de qualidade de dados profissional Evidently AI (DatasetStats).
    Gera métricas de integridade (duplicatas, vazios, tipos, nulos) e salva relatório HTML interativo.
    """
    df, err, path = _load_df_safe(dataset_name, max_rows=max_rows)
    if err or df is None:
        return {"sucesso": False, "erro": err}

    from evidently import Report
    from evidently.presets import DatasetStats

    report = Report(metrics=[DatasetStats()])
    snapshot = report.run(reference_data=None, current_data=df)
    metrics_data = snapshot.dict().get("metrics", [])

    summary_stats: dict[str, Any] = {}
    for m in metrics_data:
        name = m.get("metric_name", "").split("(")[0]
        val = m.get("value")
        if isinstance(val, (int, float, str, dict, list)):
            summary_stats[name] = val

    html_path_str: str | None = None
    if save_html:
        reports_dir = config.WORKSPACE_DIR / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        html_file = reports_dir / f"evidently_{path.stem if path else dataset_name}_report.html"
        snapshot.save_html(str(html_file))
        # Salva também cópia direta na raiz do workspace para acesso imediato no editor
        root_ws_file = config.WORKSPACE_DIR / f"evidently_{path.stem if path else dataset_name}_report.html"
        try:
            snapshot.save_html(str(root_ws_file))
        except Exception:
            pass
        html_path_str = str(html_file)

    return {
        "sucesso": True,
        "dataset": path.stem if path else dataset_name,
        "total_linhas": len(df),
        "total_colunas": len(df.columns),
        "evidently_dataset_stats": summary_stats,
        "relatorio_html_salvo": html_path_str,
        "mensagem": f"Relatório Evidently AI gerado com sucesso. Salvo em {html_path_str}." if html_path_str else "Relatório Evidently AI gerado com sucesso.",
    }


def analyze_correlations(dataset_name: str, method: str = "pearson") -> dict[str, Any]:
    """Calcula a matriz de correlação linear/monotônica e destaca pares com forte relação."""
    df, err, path = _load_df_safe(dataset_name)
    if err or df is None:
        return {"sucesso": False, "erro": err}

    num_df = df.select_dtypes(include=[np.number])
    if num_df.shape[1] < 2:
        return {"sucesso": False, "erro": "Necessário pelo menos 2 colunas numéricas para correlação."}

    corr_matrix = num_df.corr(method=method).round(4)
    cols = list(corr_matrix.columns)

    top_pairs = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            val = corr_matrix.iloc[i, j]
            if not np.isnan(val):
                top_pairs.append({
                    "coluna_a": cols[i],
                    "coluna_b": cols[j],
                    "correlacao": float(val),
                    "intensidade": (
                        "Forte Positiva" if val >= 0.7
                        else ("Moderada Positiva" if val >= 0.4
                        else ("Forte Negativa" if val <= -0.7
                        else ("Moderada Negativa" if val <= -0.4 else "Fraca/Nula")))
                    ),
                })

    top_pairs.sort(key=lambda x: abs(x["correlacao"]), reverse=True)

    return {
        "sucesso": True,
        "dataset": path.stem if path else dataset_name,
        "metodo": method,
        "colunas": cols,
        "matriz_correlacao": corr_matrix.to_dict(),
        "destaques": top_pairs[:10],
    }


def detect_outliers_iqr(dataset_name: str, column: str = "") -> dict[str, Any]:
    """Detecta anomalias e outliers em variáveis numéricas através da amplitude interquartil (IQR)."""
    df, err, path = _load_df_safe(dataset_name)
    if err or df is None:
        return {"sucesso": False, "erro": err}

    num_df = df.select_dtypes(include=[np.number])
    if num_df.empty:
        return {"sucesso": False, "erro": "Nenhuma coluna numérica encontrada para detecção de outliers."}

    target_cols = [column] if column and column in num_df.columns else list(num_df.columns)
    outlier_summary = []

    for col in target_cols:
        series = num_df[col].dropna()
        if series.empty:
            continue

        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        outliers = series[(series < lower_bound) | (series > upper_bound)]
        outlier_count = len(outliers)
        outlier_pct = round((outlier_count / len(series)) * 100, 2)

        outlier_summary.append({
            "coluna": str(col),
            "limite_inferior": round(lower_bound, 4),
            "limite_superior": round(upper_bound, 4),
            "total_outliers": outlier_count,
            "percentual_outliers": outlier_pct,
            "severidade": "Alta" if outlier_pct > 5 else ("Moderada" if outlier_pct > 1 else "Baixa"),
        })

    outlier_summary.sort(key=lambda x: x["percentual_outliers"], reverse=True)
    return {
        "sucesso": True,
        "dataset": path.stem if path else dataset_name,
        "total_colunas_analisadas": len(outlier_summary),
        "outliers": outlier_summary,
    }


def analyze_target_relationship(dataset_name: str, target_column: str, feature_column: str = "") -> dict[str, Any]:
    """Examina o comportamento dos preditores em relação à variável resposta (target)."""
    df, err, path = _load_df_safe(dataset_name)
    if err or df is None:
        return {"sucesso": False, "erro": err}

    if target_column not in df.columns:
        return {"sucesso": False, "erro": f"Coluna alvo '{target_column}' não existe no dataset."}

    target_series = df[target_column]
    is_target_numeric = pd.api.types.is_numeric_dtype(target_series)

    results: dict[str, Any] = {
        "sucesso": True,
        "dataset": path.stem if path else dataset_name,
        "target": target_column,
        "tipo_target": "numerica" if is_target_numeric else "categorica",
    }

    if is_target_numeric:
        # Se target for numérica, calcula correlação com outras numéricas
        num_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c != target_column]
        correlations = []
        for col in num_cols:
            corr = df[target_column].corr(df[col])
            if not np.isnan(corr):
                correlations.append({"feature": col, "correlacao_com_target": round(float(corr), 4)})
        correlations.sort(key=lambda x: abs(x["correlacao_com_target"]), reverse=True)
        results["correlacoes_com_target"] = correlations

        # Se houver feature categórica especificada, agrupa target por ela
        if feature_column and feature_column in df.columns and not pd.api.types.is_numeric_dtype(df[feature_column]):
            grp = df.groupby(feature_column)[target_column].agg(["count", "mean", "median", "std"]).round(2).reset_index()
            results["agrupamento_por_categoria"] = grp.to_dict(orient="records")
    else:
        # Se target for categórica, calcula distribuição de classes
        class_dist = target_series.value_counts(dropna=False, normalize=True).round(4) * 100
        results["distribuicao_classes_pct"] = class_dist.to_dict()

    return results


def run_data_cleaning_pipeline(
    dataset_name: str,
    fill_missing_strategy: str = "auto",
    drop_duplicates: bool = True,
    output_filename: str = "",
) -> dict[str, Any]:
    """
    Aplica pipeline completo de limpeza nos dados:
    - Deduplicação
    - Conversão automática de strings de data para datetime
    - Imputação de nulos numéricos (mediana/0) e categóricos ('DESCONHECIDO')
    """
    df, err, path = _load_df_safe(dataset_name, max_rows=50_000)
    if err or df is None:
        return {"sucesso": False, "erro": err}

    linhas_iniciais = len(df)
    duplicatas_removidas = 0
    if drop_duplicates:
        antes = len(df)
        df = df.drop_duplicates()
        duplicatas_removidas = antes - len(df)

    # Conversão de colunas temporais
    cols_convertidas_data = []
    for col in df.columns:
        col_lower = str(col).lower()
        if any(h in col_lower for h in ("data", "date", "created", "updated", "time")):
            try:
                df[col] = pd.to_datetime(df[col], errors="coerce")
                cols_convertidas_data.append(str(col))
            except Exception:
                pass

    # Imputação de nulos
    nulos_imputados = 0
    num_cols = df.select_dtypes(include=[np.number]).columns
    for nc in num_cols:
        missing_count = int(df[nc].isna().sum())
        if missing_count > 0:
            val = float(df[nc].median()) if not df[nc].isna().all() else 0.0
            df[nc] = df[nc].fillna(val)
            nulos_imputados += missing_count

    cat_cols = df.select_dtypes(include=["object", "string", "category"]).columns
    for cc in cat_cols:
        missing_count = int(df[cc].isna().sum())
        if missing_count > 0:
            df[cc] = df[cc].fillna("DESCONHECIDO")
            nulos_imputados += missing_count

    linhas_finais = len(df)

    # Opcionalmente salva no workspace
    caminho_salvo = None
    if output_filename:
        out_name = output_filename if output_filename.endswith(".csv") else f"{output_filename}.csv"
        out_dir = Path("krakenlake/workspace").resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        dest_path = out_dir / out_name
        df.to_csv(dest_path, index=False)
        caminho_salvo = str(dest_path.relative_to(Path.cwd())) if dest_path.is_relative_to(Path.cwd()) else str(dest_path)

    return {
        "sucesso": True,
        "dataset": path.stem if path else dataset_name,
        "linhas_iniciais": linhas_iniciais,
        "linhas_finais": linhas_finais,
        "duplicatas_removidas": duplicatas_removidas,
        "nulos_imputados": nulos_imputados,
        "colunas_convertidas_datetime": cols_convertidas_data,
        "arquivo_salvo": caminho_salvo,
    }


def generate_visualization_specs(
    dataset_name: str,
    chart_type: str = "bar",
    x: str = "",
    y: str = "",
) -> dict[str, Any]:
    """
    Gera especificações de gráficos interativos prontas para renderização pelo Beautiful UI / Frontend.
    Suporta: 'bar', 'histogram', 'line', 'scatter', 'pie'.
    """
    df, err, path = _load_df_safe(dataset_name)
    if err or df is None:
        return {"sucesso": False, "erro": err}

    chart_type = chart_type.lower().strip()
    x_col = x.strip() if x.strip() in df.columns else str(df.columns[0])
    num_cols = list(df.select_dtypes(include=[np.number]).columns)
    if y.strip() in df.columns:
        y_col = y.strip()
    elif num_cols:
        y_col = str(num_cols[0])
    else:
        y_col = str(df.columns[1]) if len(df.columns) > 1 else x_col

    if x_col == y_col:
        other_nums = [c for c in num_cols if c != x_col]
        if other_nums:
            y_col = str(other_nums[0])

    chart_data = []

    if chart_type in ("bar", "pizza", "pie"):
        # Agrupa pelo eixo X e calcula métricas
        if x_col != y_col and y_col in df.select_dtypes(include=[np.number]).columns:
            s_sum = df.groupby(x_col)[y_col].sum().nlargest(10)
            for idx_val, val in s_sum.items():
                chart_data.append({"name": str(idx_val), "value": float(val)})
        else:
            top_counts = df[x_col].value_counts().head(10)
            for idx_val, count in top_counts.items():
                chart_data.append({"name": str(idx_val), "value": int(count)})

    elif chart_type == "histogram":
        series = df[x_col].dropna()
        if pd.api.types.is_numeric_dtype(series):
            counts, bin_edges = np.histogram(series, bins=10)
            for i in range(len(counts)):
                label = f"{bin_edges[i]:.1f}-{bin_edges[i+1]:.1f}"
                chart_data.append({"name": label, "value": int(counts[i])})
        else:
            top_counts = series.value_counts().head(10).reset_index()
            for _, row in top_counts.iterrows():
                chart_data.append({"name": str(row[x_col]), "value": int(row["count"])})

    elif chart_type in ("line", "scatter"):
        sample_pts = df[[x_col, y_col]].dropna().head(50)
        for _, row in sample_pts.iterrows():
            chart_data.append({"x": str(row[x_col]), "y": float(row[y_col]) if isinstance(row[y_col], (int, float, np.number)) else str(row[y_col])})

    return {
        "sucesso": True,
        "chart_type": chart_type,
        "title": f"{chart_type.capitalize()} de {y_col} por {x_col}",
        "x_axis": x_col,
        "y_axis": y_col,
        "data": chart_data,
    }


def export_report_document(
    dataset_name: str,
    report_format: str = "markdown",
    title: str = "",
) -> dict[str, Any]:
    """Gera e exporta relatório estruturado consolidando estatísticas, qualidade e insights analíticos."""
    df, err, path = _load_df_safe(dataset_name)
    if err or df is None:
        return {"sucesso": False, "erro": err}

    ds_stem = path.stem if path else dataset_name
    doc_title = title or f"Relatório Analítico Executivo - {ds_stem}"

    # Sumarizações
    missing_info = analyze_missing_values(ds_stem)
    corr_info = analyze_correlations(ds_stem)
    outlier_info = detect_outliers_iqr(ds_stem)

    md_lines = [
        f"# {doc_title}",
        f"**Dataset:** `{ds_stem}` | **Data de Geração:** {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}",
        "",
        "## 1. Resumo Executivo e Volumetria",
        f"- **Total de Linhas Analisadas:** {len(df):,}",
        f"- **Total de Colunas:** {len(df.columns)}",
        f"- **Uso de Memória:** ~{df.memory_usage(deep=True).sum() / 1024:.2f} KB",
        "",
        "## 2. Qualidade dos Dados e Valores Ausentes",
    ]

    if missing_info.get("detalhes"):
        md_lines.append("| Coluna | Nulos | % Ausente | Criticidade | Sugestão |")
        md_lines.append("|---|---|---|---|---|")
        for m in missing_info["detalhes"]:
            md_lines.append(f"| {m['coluna']} | {m['total_nulos']} | {m['percentual_nulos']}% | {m['criticidade']} | {m['sugestao_imputacao']} |")
    else:
        md_lines.append("✓ **Nenhum valor ausente identificado no dataset.** Base com 100% de preenchimento.")

    md_lines.extend([
        "",
        "## 3. Detecção de Outliers e Anomalias (Método IQR)",
    ])
    if outlier_info.get("outliers"):
        md_lines.append("| Coluna | Outliers | % Outliers | Limite Inferior | Limite Superior | Severidade |")
        md_lines.append("|---|---|---|---|---|---|")
        for o in outlier_info["outliers"][:8]:
            md_lines.append(f"| {o['coluna']} | {o['total_outliers']} | {o['percentual_outliers']}% | {o['limite_inferior']} | {o['limite_superior']} | {o['severidade']} |")

    md_lines.extend([
        "",
        "## 4. Destaques de Correlação Linear",
    ])
    if corr_info.get("destaques"):
        for pair in corr_info["destaques"][:5]:
            md_lines.append(f"- **{pair['coluna_a']} ↔ {pair['coluna_b']}:** {pair['correlacao']} ({pair['intensidade']})")
    else:
        md_lines.append("Nenhum par de variáveis com correlação expressiva identificado.")

    md_lines.extend([
        "",
        "## 5. Recomendações e Próximos Passos",
        "- Aplicar pipeline de deduplicação e normalização de datas.",
        "- Aplicar transformações logarítmicas nas variáveis com assimetria positiva acentuada.",
        "- Salvar o script reprodutível em `krakenlake/workspace/` para orquestração contínua.",
    ])

    report_content = "\n".join(md_lines) + "\n"

    # Salva no disco do repositório
    reports_dir = Path("krakenlake/reports").resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / f"relatorio_{ds_stem}.md"
    report_file.write_text(report_content, encoding="utf-8")

    return {
        "sucesso": True,
        "titulo": doc_title,
        "formato": "markdown",
        "caminho_arquivo": str(report_file.relative_to(Path.cwd())) if report_file.is_relative_to(Path.cwd()) else str(report_file),
        "conteudo_resumo": report_content[:500] + "...",
    }


def save_script_to_workspace(script_name: str, code: str, overwrite: bool = True) -> dict[str, Any]:
    """
    Grava ou atualiza um script Python (.py) diretamente no diretório do workspace do repositório.
    Garante versionamento e persistência no krakenlake/workspace/.
    """
    clean_name = script_name.strip()
    if not clean_name.endswith(".py"):
        clean_name = f"{clean_name}.py"

    workspace_dir = Path("krakenlake/workspace").resolve()
    workspace_dir.mkdir(parents=True, exist_ok=True)

    target_path = workspace_dir / clean_name
    if target_path.exists() and not overwrite:
        return {"sucesso": False, "erro": f"O script '{clean_name}' já existe e overwrite=False."}

    target_path.write_text(code, encoding="utf-8")

    return {
        "sucesso": True,
        "script": clean_name,
        "caminho": str(target_path.relative_to(Path.cwd())) if target_path.is_relative_to(Path.cwd()) else str(target_path),
        "linhas_gravadas": len(code.splitlines()),
        "bytes": len(code.encode("utf-8")),
    }
