"""Leitura dos datasets em pipeline/dados (CSV e Parquet)."""
import pandas as pd
import pyarrow.parquet as pq

from .. import config


def listar_datasets() -> list:
    """Arquivos .csv/.parquet do diretório de dados."""
    return [p for p in sorted(config.DATA_DIR.rglob("*")) if p.suffix in (".csv", ".parquet") and p.is_file()]


def ler_dataset(path, nrows: int | None = None) -> pd.DataFrame:
    """Lê um dataset. Em CSV detecta o separador (, ; tab) e o encoding (UTF-8/Latin-1)."""
    if path.suffix == ".parquet":
        if nrows is None:
            return pd.read_parquet(path)
        return next(pq.ParquetFile(path).iter_batches(batch_size=nrows)).to_pandas()
    try:
        return pd.read_csv(path, sep=None, engine="python", nrows=nrows, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(path, sep=None, engine="python", nrows=nrows, encoding="latin-1")
