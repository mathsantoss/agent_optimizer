"""Guardrails de verificação de integridade dos arquivos de dados brutos."""
import hashlib
from pathlib import Path

from kraken_copilot import config


def capture_data_dir_snapshot(data_dir: Path | None = None) -> dict[str, str]:
    """
    Captura hashes SHA-256 dos arquivos de dados em `pipeline/dados/` para verificar
    se a execução de um pipeline modificou ou corrompeu indevidamente os datasets brutos.
    """
    target_dir = data_dir or config.DATA_DIR
    if not target_dir or not target_dir.exists():
        return {}

    snapshot: dict[str, str] = {}
    for file_path in sorted(target_dir.rglob("*")):
        if file_path.is_file() and file_path.suffix.lower() in (".csv", ".parquet", ".json"):
            try:
                file_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
                snapshot[str(file_path)] = file_hash
            except Exception:
                continue
    return snapshot


def verify_data_dir_integrity(
    before_snapshot: dict[str, str],
    data_dir: Path | None = None,
) -> list[str]:
    """
    Compara o estado atual de `pipeline/dados/` com o snapshot anterior à execução.
    Retorna lista de violações caso algum arquivo de dados bruto tenha sido removido ou alterado.
    """
    if not before_snapshot:
        return []

    after_snapshot = capture_data_dir_snapshot(data_dir=data_dir)
    violations: list[str] = []

    for file_path_str, original_hash in before_snapshot.items():
        file_name = Path(file_path_str).name
        if file_path_str not in after_snapshot:
            violations.append(f"Arquivo de dados bruto removido durante a execução: '{file_name}'.")
        elif after_snapshot[file_path_str] != original_hash:
            violations.append(f"Arquivo de dados bruto modificado indevidamente durante a execução: '{file_name}'.")

    return violations

