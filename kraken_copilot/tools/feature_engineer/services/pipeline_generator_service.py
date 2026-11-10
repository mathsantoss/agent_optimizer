"""Serviço de geração dinâmica e agnóstica de pipelines de Feature Engineering em Pandas e PySpark."""
from pathlib import Path
import re
from typing import Any
import pandas as pd

from kraken_copilot import config
from kraken_copilot.schemas import FeaturePipelinePlan, FeatureSpec
from kraken_copilot.tools.data_analyst.services.dataset_service import (
    get_available_datasets_catalog,
    list_dataset_files,
    resolve_dataset_file,
)


def resolve_dataset_smart(dataset_name: str, fallback_if_empty: bool = False) -> tuple[Path | None, str | None]:
    """
    Resolve o arquivo de dataset com suporte a linguagem natural (ex: 'dados de venda' -> 'dados_vendas.csv').
    Preserva o comportamento exato para nomes explícitos de outras bases (ex: 'clientes_telecom').
    """
    clean = (dataset_name or "").strip()
    if clean:
        exact_path, err = resolve_dataset_file(clean)
        if exact_path is not None:
            return exact_path, None

    files = list_dataset_files()
    if not files:
        return None, "Nenhum dataset encontrado no catálogo."

    if not clean or clean.lower() in ("auto", "default", "padrao", "padrão", "catalogo", "catálogo"):
        if fallback_if_empty:
            return files[0], None
        return None, "Dataset não especificado."

    stopwords = {"de", "da", "do", "das", "dos", "no", "na", "em", "base", "dataset", "tabela", "arquivo", "csv", "parquet"}
    raw_tokens = [t.rstrip("s") for t in re.split(r"[\s_\-./]+", clean.lower()) if t and t not in stopwords]
    if raw_tokens:
        best_file = None
        best_score = 0
        for f in files:
            f_tokens = [ft.rstrip("s") for ft in re.split(r"[\s_\-./]+", f.stem.lower()) if ft]
            # Exige correspondência de token significativo (não apenas 'dado')
            matched = [t for t in raw_tokens if any(t == ft or (len(t) >= 4 and (t in ft or ft in t)) for ft in f_tokens)]
            meaningful = [t for t in matched if t not in ("dado", "data")]
            if meaningful and len(matched) > best_score:
                best_score = len(matched)
                best_file = f
        if best_file is not None:
            return best_file, None

    if fallback_if_empty and len(files) == 1:
        return files[0], None

    return None, f"Dataset '{dataset_name}' não encontrado."


def infer_candidate_features_from_schema(
    df: pd.DataFrame,
    framework: str = "pandas",
) -> list[FeatureSpec]:
    """
    Inspeciona dinamicamente os tipos de dados e nomes das colunas de qualquer DataFrame
    e deriva receitas de features matemáticas, temporais e relacionais sem regras hardcoded de domínio.
    """
    fw = framework.strip().lower()
    inferred: list[FeatureSpec] = []

    datetime_cols: list[str] = []
    numeric_cols: list[str] = []
    categorical_cols: list[str] = []

    # 1. Classificação dinâmica de colunas por tipo e semântica
    for col in df.columns:
        col_str = str(col)
        col_series = df[col]
        col_lower = col_str.lower()

        # Detecção de colunas temporais (dtype datetime ou padrões de nomenclatura de data/hora)
        if pd.api.types.is_datetime64_any_dtype(col_series) or any(
            hint in col_lower for hint in ("date", "data", "created", "updated", "timestamp", "time", "_dt", "hora")
        ):
            datetime_cols.append(col_str)
        elif pd.api.types.is_numeric_dtype(col_series):
            # Ignora IDs com alta cardinalidade para cálculos aritméticos diretos
            if not (col_lower.endswith("_id") or col_lower.startswith("id_") or col_lower == "id"):
                numeric_cols.append(col_str)
        elif pd.api.types.is_string_dtype(col_series) or pd.api.types.is_object_dtype(col_series):
            unique_count = col_series.nunique()
            if 1 < unique_count <= 500:
                categorical_cols.append(col_str)

    # 2. Geração de Features Temporais
    for dt_col in datetime_cols[:2]:
        if fw == "pyspark":
            inferred.extend([
                FeatureSpec(
                    name=f"{dt_col}_year",
                    category="temporal",
                    framework="pyspark",
                    expression=f"F.year(F.col('{dt_col}'))",
                    description=f"Ano extraído da coluna temporal '{dt_col}'",
                ),
                FeatureSpec(
                    name=f"{dt_col}_month",
                    category="temporal",
                    framework="pyspark",
                    expression=f"F.month(F.col('{dt_col}'))",
                    description=f"Mês extraído da coluna temporal '{dt_col}' (1 a 12)",
                ),
                FeatureSpec(
                    name=f"{dt_col}_dayofweek",
                    category="temporal",
                    framework="pyspark",
                    expression=f"F.dayofweek(F.col('{dt_col}'))",
                    description=f"Dia da semana da coluna '{dt_col}' (1=Domingo a 7=Sábado)",
                ),
                FeatureSpec(
                    name=f"{dt_col}_is_weekend",
                    category="temporal",
                    framework="pyspark",
                    expression=f"F.when(F.dayofweek(F.col('{dt_col}')).isin(1, 7), 1).otherwise(0)",
                    description=f"Flag binária indicando final de semana para '{dt_col}'",
                ),
            ])
        else:
            inferred.extend([
                FeatureSpec(
                    name=f"{dt_col}_year",
                    category="temporal",
                    framework="pandas",
                    expression=f"df['{dt_col}'].dt.year",
                    description=f"Ano extraído da coluna temporal '{dt_col}'",
                ),
                FeatureSpec(
                    name=f"{dt_col}_month",
                    category="temporal",
                    framework="pandas",
                    expression=f"df['{dt_col}'].dt.month",
                    description=f"Mês extraído da coluna temporal '{dt_col}' (1 a 12)",
                ),
                FeatureSpec(
                    name=f"{dt_col}_dayofweek",
                    category="temporal",
                    framework="pandas",
                    expression=f"df['{dt_col}'].dt.dayofweek",
                    description=f"Dia da semana da coluna '{dt_col}' (0=Segunda a 6=Domingo)",
                ),
                FeatureSpec(
                    name=f"{dt_col}_is_weekend",
                    category="temporal",
                    framework="pandas",
                    expression=f"df['{dt_col}'].dt.dayofweek.isin([5, 6]).astype(int)",
                    description=f"Flag binária indicando final de semana para '{dt_col}'",
                ),
            ])

    # 3. Geração de Features Aritméticas e Ratios Numéricos
    if len(numeric_cols) >= 2:
        col_a, col_b = numeric_cols[0], numeric_cols[1]
        if fw == "pyspark":
            inferred.extend([
                FeatureSpec(
                    name=f"diff_{col_a}_{col_b}",
                    category="ratio",
                    framework="pyspark",
                    expression=f"F.col('{col_a}') - F.col('{col_b}')",
                    description=f"Diferença aritmética absoluta ({col_a} - {col_b})",
                ),
                FeatureSpec(
                    name=f"ratio_{col_a}_{col_b}",
                    category="ratio",
                    framework="pyspark",
                    expression=f"F.when(F.col('{col_b}') == 0, 0).otherwise(F.col('{col_a}') / F.col('{col_b}'))",
                    description=f"Razão normalizada com proteção contra divisão por zero ({col_a} / {col_b})",
                ),
            ])
        else:
            inferred.extend([
                FeatureSpec(
                    name=f"diff_{col_a}_{col_b}",
                    category="ratio",
                    framework="pandas",
                    expression=f"df['{col_a}'] - df['{col_b}']",
                    description=f"Diferença aritmética absoluta ({col_a} - {col_b})",
                ),
                FeatureSpec(
                    name=f"ratio_{col_a}_{col_b}",
                    category="ratio",
                    framework="pandas",
                    expression=f"(df['{col_a}'] / df['{col_b}'].replace(0, np.nan)).fillna(0.0)",
                    description=f"Razão normalizada com proteção contra divisão por zero ({col_a} / {col_b})",
                ),
                FeatureSpec(
                    name=f"interacao_{col_a}_x_{col_b}",
                    category="interaction",
                    framework="pandas",
                    expression=f"df['{col_a}'].fillna(0) * df['{col_b}'].fillna(0)",
                    description=f"Produto de interação multiplicativa ({col_a} * {col_b}, ex: volume financeiro/transacional)",
                ),
            ])

    # Transformação logarítmica para variáveis numéricas contínuas
    for num_col in numeric_cols[:2]:
        if fw == "pyspark":
            inferred.append(
                FeatureSpec(
                    name=f"log_{num_col}",
                    category="transform",
                    framework="pyspark",
                    expression=f"F.log1p(F.greatest(F.lit(0), F.col('{num_col}')))",
                    description=f"Transformação logarítmica suavizada log1p({num_col}) para redução de assimetria",
                )
            )
        else:
            inferred.append(
                FeatureSpec(
                    name=f"log_{num_col}",
                    category="transform",
                    framework="pandas",
                    expression=f"np.log1p(np.maximum(0, df['{num_col}']))",
                    description=f"Transformação logarítmica suavizada log1p({num_col}) para redução de assimetria",
                )
            )

    # 4. Geração de Agregações de Grupo (Entidade x Métrica)
    if categorical_cols and numeric_cols:
        cat_col = categorical_cols[0]
        num_col = numeric_cols[0]
        if fw == "pyspark":
            inferred.extend([
                FeatureSpec(
                    name=f"media_{num_col}_por_{cat_col}",
                    category="agregacao",
                    framework="pyspark",
                    expression=f"F.avg('{num_col}').over(Window.partitionBy('{cat_col}'))",
                    description=f"Média de '{num_col}' agregada por '{cat_col}' via Window partitionBy",
                ),
                FeatureSpec(
                    name=f"contagem_por_{cat_col}",
                    category="agregacao",
                    framework="pyspark",
                    expression=f"F.count('{num_col}').over(Window.partitionBy('{cat_col}'))",
                    description=f"Contagem total de registros agregados por '{cat_col}'",
                ),
            ])
        else:
            inferred.extend([
                FeatureSpec(
                    name=f"media_{num_col}_por_{cat_col}",
                    category="agregacao",
                    framework="pandas",
                    expression=f"df.groupby('{cat_col}')['{num_col}'].transform('mean')",
                    description=f"Média de '{num_col}' agregada por '{cat_col}' vetorizada com transform",
                ),
                FeatureSpec(
                    name=f"contagem_por_{cat_col}",
                    category="agregacao",
                    framework="pandas",
                    expression=f"df.groupby('{cat_col}')['{num_col}'].transform('count')",
                    description=f"Contagem total de registros agregados por '{cat_col}' vetorizada com transform",
                ),
            ])

    return inferred


def generate_pandas_pipeline_code(
    dataset_name: str,
    features: list[FeatureSpec],
    dataset_file_rel: str = "",
) -> str:
    """Gera o código-fonte de um pipeline completo e performático de Feature Engineering em Pandas."""
    data_filename = dataset_file_rel or f"{dataset_name}.csv"

    # Detecta colunas que usam acessor .dt para conversão prévia de tipos
    temporal_cols_needed = set()
    for feat in features:
        expr = feat.expression
        if ".dt." in expr:
            import re
            matches = re.findall(r"df\['([^']+)'\]\.dt\.", expr)
            temporal_cols_needed.update(matches)

    lines = [
        '"""Pipeline de Feature Engineering (Pandas) gerado para modelagem de Machine Learning."""',
        "from pathlib import Path",
        "import numpy as np",
        "import pandas as pd",
        "",
        "",
        "def run():",
        '    """Executa a ingestão, limpeza e criação vetorizada de features em Pandas."""',
        "    project_root = Path(__file__).resolve().parents[1]",
        f'    candidate_paths = [',
        f'        project_root / "krakenlake" / "catalog" / "sources" / "{data_filename}",',
        f'        project_root / "krakenlake" / "datalake" / "{data_filename}",',
        f'        Path("krakenlake/catalog/sources/{data_filename}").resolve(),',
        f'        Path("krakenlake/datalake/{data_filename}").resolve(),',
        f'        Path("{data_filename}").resolve(),',
        f'    ]',
        "    data_path = None",
        "    for p in candidate_paths:",
        "        if p.exists():",
        "            data_path = p",
        "            break",
        "    if data_path is None:",
        f'        data_path = Path("krakenlake/catalog/sources/{data_filename}").resolve()',
        "",
        "    if not data_path.exists():",
        f'        raise FileNotFoundError(f"Dataset de entrada não encontrado: {{data_path}}")',
        "",
        "    # 1. Ingestão segura dos dados",
        "    if str(data_path).endswith('.parquet'):",
        "        df = pd.read_parquet(data_path)",
        "    elif str(data_path).endswith('.json') or str(data_path).endswith('.jsonl'):",
        "        try:",
        "            df = pd.read_json(data_path)",
        "        except ValueError:",
        "            df = pd.read_json(data_path, lines=True)",
        "    else:",
        "        df = pd.read_csv(data_path, sep=None, engine='python')",
        "",
    ]

    if temporal_cols_needed:
        lines.append("    # 2. Conversão otimizada de colunas temporais")
        for col_name in sorted(temporal_cols_needed):
            lines.append(f"    if '{col_name}' in df.columns:")
            lines.append(f"        df['{col_name}'] = pd.to_datetime(df['{col_name}'], errors='coerce')")
        lines.append("")

    lines.append("    # 3. Engenharia de Features (Vetorizada)")
    for feat in features:
        lines.append(f"    # {feat.description}")
        lines.append(f"    df['{feat.name}'] = {feat.expression}")
        lines.append("")

    lines.extend([
        "    return df",
        "",
        "",
        'if __name__ == "__main__":',
        "    features_df = run()",
        "    print(f'Pipeline de features concluído com sucesso: {features_df.shape[0]} linhas x {features_df.shape[1]} colunas.')",
    ])

    return "\n".join(lines) + "\n"


def generate_pyspark_pipeline_code(
    dataset_name: str,
    features: list[FeatureSpec],
    dataset_file_rel: str = "",
) -> str:
    """Gera o código-fonte de um pipeline distribuído de Feature Engineering em PySpark."""
    data_filename = dataset_file_rel or f"{dataset_name}.csv"

    # Verifica se Window é utilizado em alguma feature
    uses_window = any("Window" in feat.expression for feat in features)

    lines = [
        '"""Pipeline de Feature Engineering (PySpark) gerado para processamento distribuído e ML."""',
        "from pathlib import Path",
        "from pyspark.sql import SparkSession",
        "from pyspark.sql import functions as F",
    ]
    if uses_window:
        lines.append("from pyspark.sql.window import Window")
    lines.extend([
        "",
        "",
        "def get_spark_session():",
        '    """Inicializa ou obtém a sessão ativa do Apache Spark."""',
        "    return SparkSession.builder \\",
        '        .appName("KrakenIA-FeatureEngineering") \\',
        '        .master("local[*]") \\',
        "        .getOrCreate()",
        "",
        "",
        "def run():",
        '    """Executa a ingestão e transformações distribuídas de features em PySpark."""',
        "    spark = get_spark_session()",
        "    project_root = Path(__file__).resolve().parents[1]",
        f'    candidate_paths = [',
        f'        project_root / "krakenlake" / "catalog" / "sources" / "{data_filename}",',
        f'        project_root / "krakenlake" / "datalake" / "{data_filename}",',
        f'        Path("krakenlake/catalog/sources/{data_filename}").resolve(),',
        f'        Path("krakenlake/datalake/{data_filename}").resolve(),',
        f'        Path("{data_filename}").resolve(),',
        f'    ]',
        "    data_path = None",
        "    for p in candidate_paths:",
        "        if p.exists():",
        "            data_path = str(p)",
        "            break",
        "    if data_path is None:",
        f'        data_path = str(project_root / "krakenlake" / "catalog" / "sources" / "{data_filename}")',
        "",
        "    # 1. Ingestão distribuída",
        "    if data_path.endswith('.parquet'):",
        "        df = spark.read.parquet(data_path)",
        "    elif data_path.endswith('.json') or data_path.endswith('.jsonl'):",
        "        df = spark.read.json(data_path)",
        "    else:",
        "        df = spark.read.option('header', 'true').option('inferSchema', 'true').csv(data_path)",
        "",
        "    # 2. Criação de Features em PySpark",
    ])

    for feat in features:
        lines.append(f"    # {feat.description}")
        lines.append(f"    df = df.withColumn('{feat.name}', {feat.expression})")
        lines.append("")

    lines.extend([
        "    return df",
        "",
        "",
        'if __name__ == "__main__":',
        "    spark_df = run()",
        "    print(f'Pipeline PySpark concluído: {spark_df.count()} registros processados.')",
    ])

    return "\n".join(lines) + "\n"


def create_feature_pipeline_plan(
    dataset_name: str,
    framework: str = "pandas",
    target_file_path: str | None = None,
    features: list[FeatureSpec] | list[dict[str, Any]] | None = None,
) -> FeaturePipelinePlan:
    """Monta o plano de construção de pipeline de features com código e especificações completas para qualquer dataset."""
    from kraken_copilot.tools.code_optimizer.services.file_service import get_default_workspace_pipeline

    if not target_file_path:
        target_file_path = get_default_workspace_pipeline()
    fw = framework.strip().lower()

    # Normaliza features fornecidas
    selected_features: list[FeatureSpec] = []
    if features:
        for f in features:
            if isinstance(f, FeatureSpec):
                selected_features.append(f)
            elif isinstance(f, dict):
                selected_features.append(
                    FeatureSpec(
                        name=f.get("name", "feature_custom"),
                        category=f.get("category", "custom"),
                        framework=fw,
                        expression=f.get("expression", ""),
                        description=f.get("description", "Feature customizada"),
                    )
                )

    resolved_file, _ = resolve_dataset_smart(dataset_name, fallback_if_empty=not bool(selected_features))
    data_filename = resolved_file.name if resolved_file else f"{dataset_name}.csv"
    resolved_stem = resolved_file.stem if resolved_file else dataset_name

    # Se nenhuma feature foi especificada, infere dinamicamente a partir do schema real do arquivo
    if not selected_features:
        if resolved_file and resolved_file.exists():
            try:
                if resolved_file.suffix.lower() == ".parquet":
                    sample_df = pd.read_parquet(resolved_file).head(200)
                else:
                    sample_df = pd.read_csv(resolved_file, nrows=200)
                selected_features = infer_candidate_features_from_schema(sample_df, framework=fw)
            except Exception:
                selected_features = []

        if not selected_features:
            # Fallback genérico caso o arquivo não possua colunas detectáveis
            sample_expr = "df.iloc[:, 0] * 2" if fw == "pandas" else "F.col(df.columns[0]) * 2"
            selected_features = [
                FeatureSpec(
                    name="feature_transformada",
                    category="custom",
                    framework=fw,
                    expression=sample_expr,
                    description="Feature genérica inicial gerada para o dataset",
                )
            ]

    if fw == "pyspark":
        code = generate_pyspark_pipeline_code(resolved_stem, selected_features, data_filename)
    else:
        code = generate_pandas_pipeline_code(resolved_stem, selected_features, data_filename)

    return FeaturePipelinePlan(
        pipeline_name=f"pipeline_features_{fw}",
        framework=fw,
        target_file_path=target_file_path,
        source_dataset=resolved_stem,
        features=selected_features,
        code=code,
    )
