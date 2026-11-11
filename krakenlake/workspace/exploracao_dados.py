"""Pipeline de Feature Engineering (Pandas) gerado para modelagem de Machine Learning."""
from pathlib import Path
import numpy as np
import pandas as pd


def run():
    """Executa a ingestão, limpeza e criação vetorizada de features em Pandas."""
    project_root = Path(__file__).resolve().parents[1]
    candidate_paths = [
        project_root / "krakenlake" / "catalog" / "sources" / "ibovespa.csv",
        project_root / "krakenlake" / "datalake" / "ibovespa.csv",
        Path("krakenlake/catalog/sources/ibovespa.csv").resolve(),
        Path("krakenlake/datalake/ibovespa.csv").resolve(),
        Path("ibovespa.csv").resolve(),
    ]
    data_path = None
    for p in candidate_paths:
        if p.exists():
            data_path = p
            break
    if data_path is None:
        data_path = Path("krakenlake/catalog/sources/ibovespa.csv").resolve()

    if not data_path.exists():
        raise FileNotFoundError(f"Dataset de entrada não encontrado: {data_path}")

    # 1. Ingestão segura dos dados
    if str(data_path).endswith('.parquet'):
        df = pd.read_parquet(data_path)
    elif str(data_path).endswith('.json') or str(data_path).endswith('.jsonl'):
        try:
            df = pd.read_json(data_path)
        except ValueError:
            df = pd.read_json(data_path, lines=True)
    else:
        df = pd.read_csv(data_path, sep=None, engine='python')

    # 3. Engenharia de Features (Vetorizada)
    # Diferença aritmética absoluta (qtd_teorica - participacao_relativa)
    df['diff_qtd_teorica_participacao_relativa'] = df['qtd_teorica'] - df['participacao_relativa']

    # Razão normalizada com proteção contra divisão por zero (qtd_teorica / participacao_relativa)
    df['ratio_qtd_teorica_participacao_relativa'] = (df['qtd_teorica'] / df['participacao_relativa'].replace(0, np.nan)).fillna(0.0)

    # Produto de interação multiplicativa (qtd_teorica * participacao_relativa, ex: volume financeiro/transacional)
    df['interacao_qtd_teorica_x_participacao_relativa'] = df['qtd_teorica'].fillna(0) * df['participacao_relativa'].fillna(0)

    # Transformação logarítmica suavizada log1p(qtd_teorica) para redução de assimetria
    df['log_qtd_teorica'] = np.log1p(np.maximum(0, df['qtd_teorica']))

    # Transformação logarítmica suavizada log1p(participacao_relativa) para redução de assimetria
    df['log_participacao_relativa'] = np.log1p(np.maximum(0, df['participacao_relativa']))

    # Média de 'qtd_teorica' agregada por 'codigo' vetorizada com transform
    df['media_qtd_teorica_por_codigo'] = df.groupby('codigo')['qtd_teorica'].transform('mean')

    # Contagem total de registros agregados por 'codigo' vetorizada com transform
    df['contagem_por_codigo'] = df.groupby('codigo')['qtd_teorica'].transform('count')

    return df


if __name__ == "__main__":
    features_df = run()
    print(f'Pipeline de features concluído com sucesso: {features_df.shape[0]} linhas x {features_df.shape[1]} colunas.')