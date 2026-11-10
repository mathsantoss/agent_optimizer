"""Serviço de profiling e instrumentação de pipelines: tempo, memória (tracemalloc), hashes e execução única."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from kraken_copilot import config
from kraken_copilot.guardrails import capture_data_dir_snapshot, verify_data_dir_integrity
from kraken_copilot.schemas import PipelineProfileResult
from kraken_copilot.tools.code_optimizer.services.file_service import resolve_pipeline_path

PROFILING_DEFAULT_TIMEOUT_SECONDS = 120

# Script Python executado em subprocesso isolado para medição precisa de memória, tempo e extração dinâmica de schema
ISOLATED_PROFILER_SCRIPT = """
import contextlib
import hashlib
import io
import json
import runpy
import sys
import time
import traceback
import tracemalloc
from pathlib import Path

target_file = Path(sys.argv[1]).resolve()
sample_limit = int(sys.argv[2]) if len(sys.argv) > 2 else 0
sys.path.insert(0, str(target_file.parent))

stdout_buffer = io.StringIO()
stderr_buffer = io.StringIO()
rows_processed = None
full_dataset_rows = None
column_count = None
output_columns = []
output_signature_hash = None
column_hashes = {}
return_code = 0

if sample_limit > 0:
    # Modo de amostragem dinâmica para baselines lentos (O(N^2) / iterrows / sleep):
    # Neutraliza sleeps e amostra leituras do pandas preservando a contagem real de linhas do dataset
    time.sleep = lambda *a, **kw: None
    try:
        import pandas as pd
        _orig_read_csv = pd.read_csv
        _orig_read_parquet = pd.read_parquet
        _orig_read_json = pd.read_json

        def _sampled_read_csv(*args, **kwargs):
            global full_dataset_rows
            df_full = _orig_read_csv(*args, **kwargs)
            if full_dataset_rows is None or len(df_full) > full_dataset_rows:
                full_dataset_rows = int(len(df_full))
            return df_full.head(sample_limit).copy()

        def _sampled_read_parquet(*args, **kwargs):
            global full_dataset_rows
            df_full = _orig_read_parquet(*args, **kwargs)
            if full_dataset_rows is None or len(df_full) > full_dataset_rows:
                full_dataset_rows = int(len(df_full))
            return df_full.head(sample_limit).copy()

        def _sampled_read_json(*args, **kwargs):
            global full_dataset_rows
            df_full = _orig_read_json(*args, **kwargs)
            if full_dataset_rows is None or len(df_full) > full_dataset_rows:
                full_dataset_rows = int(len(df_full))
            return df_full.head(sample_limit).copy()

        pd.read_csv = _sampled_read_csv
        pd.read_parquet = _sampled_read_parquet
        pd.read_json = _sampled_read_json
    except Exception:
        pass

tracemalloc.start()
start_time = time.perf_counter()

try:
    with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
        # Execução única via runpy.run_path sob escopo __main__
        module_globals = runpy.run_path(str(target_file), run_name="__main__")

        returned_value = None
        # 1. Verifica se a execução de __main__ já gerou um DataFrame nas variáveis globais (evita dupla execução)
        for preferred_key in ("resultado", "df_features", "df_final", "resultado_final", "df"):
            cand_val = module_globals.get(preferred_key)
            if cand_val is not None and type(cand_val).__name__ == "DataFrame" and len(cand_val) > 0:
                returned_value = cand_val
                break

        if returned_value is None:
            for val in reversed(list(module_globals.values())):
                if type(val).__name__ == "DataFrame" and len(val) > 0:
                    returned_value = val
                    break

        # 2. Se nenhum DataFrame foi produzido no __main__, aciona o entrypoint explicitamente
        if returned_value is None:
            if "run" in module_globals and callable(module_globals["run"]):
                returned_value = module_globals["run"]()
            elif "executar_pipeline" in module_globals and callable(module_globals["executar_pipeline"]):
                returned_value = module_globals["executar_pipeline"]()

        # 3. Fallback caso o entrypoint tenha retornado DataFrame vazio ou populado global
        if returned_value is None:
            for val in reversed(list(module_globals.values())):
                if type(val).__name__ == "DataFrame":
                    returned_value = val
                    break

        if returned_value is not None and type(returned_value).__name__ == "DataFrame":
            rows_processed = int(full_dataset_rows) if (sample_limit > 0 and full_dataset_rows is not None) else int(len(returned_value))
            # Ignora coluna residual 'index' ou 'level_0' gerada por reset_index() sem drop=True
            output_columns = [str(c) for c in returned_value.columns if str(c) not in ("index", "level_0")]
            column_count = len(output_columns)
            try:
                import pandas as pd
                sorted_cols = sorted(output_columns)
                normalized_df = returned_value[sorted_cols].copy()
                for c_name in sorted_cols:
                    c_series = normalized_df[c_name]
                    if pd.api.types.is_float_dtype(c_series):
                        c_series = c_series.round(6)
                        normalized_df[c_name] = c_series
                    c_bytes = pd.util.hash_pandas_object(c_series, index=False).values.tobytes()
                    column_hashes[c_name] = hashlib.sha256(c_bytes).hexdigest()[:16]
                row_bytes = pd.util.hash_pandas_object(normalized_df, index=False).values.tobytes()
                output_signature_hash = hashlib.sha256(row_bytes).hexdigest()[:16]
            except Exception:
                output_signature_hash = hashlib.sha256(f"{rows_processed}:{sorted(output_columns)}".encode("utf-8")).hexdigest()[:16]

except Exception as err:
    return_code = 1
    tb_str = traceback.format_exc(limit=4)
    stderr_buffer.write(f"{tb_str}\\n{type(err).__name__}: {err}\\n")

duration_seconds = round(time.perf_counter() - start_time, 4)
_, peak_bytes = tracemalloc.get_traced_memory()
tracemalloc.stop()
peak_mb = round(peak_bytes / (1024 * 1024), 3)

payload = {
    "return_code": return_code,
    "duration_seconds": duration_seconds,
    "peak_memory_megabytes": peak_mb,
    "rows_processed": rows_processed,
    "column_count": column_count,
    "output_columns": output_columns,
    "output_signature_hash": output_signature_hash if sample_limit == 0 else None,
    "column_hashes": column_hashes if sample_limit == 0 else {},
    "standard_output": stdout_buffer.getvalue().strip(),
    "standard_error": stderr_buffer.getvalue().strip(),
}
print("__PROFILE_JSON_START__")
print(json.dumps(payload, ensure_ascii=False))
print("__PROFILE_JSON_END__")
sys.exit(return_code)
"""


def execute_and_profile_pipeline(
    resolved_path: Path,
    timeout_seconds: int = PROFILING_DEFAULT_TIMEOUT_SECONDS,
    sample_rows: int = 0,
) -> PipelineProfileResult:
    """
    Executa o script de pipeline em processo isolado capturando métricas de performance,
    verificando a integridade dos dados brutos e tratando timeouts sem crashes.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        relative_path = str(resolved_path.relative_to(config.PROJECT_ROOT))
    except ValueError:
        relative_path = str(resolved_path)

    data_snapshot_before = capture_data_dir_snapshot()
    start_time = time.perf_counter()

    cmd = [sys.executable, "-c", ISOLATED_PROFILER_SCRIPT, str(resolved_path)]
    if sample_rows > 0:
        cmd.append(str(sample_rows))

    try:
        completed = subprocess.run(
            cmd,
            cwd=config.PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        elapsed = round(time.perf_counter() - start_time, 4)
        return PipelineProfileResult(
            file_path=relative_path,
            execution_status="timeout",
            return_code=-1,
            duration_seconds=float(timeout_seconds),
            peak_memory_megabytes=0.0,
            standard_output="",
            standard_error=f"Execução interrompida: excedeu o tempo limite configurado de {timeout_seconds} segundos (gargalo crítico de performance).",
            profiled_at=now_iso,
        )

    # Verifica se algum arquivo bruto foi violado
    integrity_violations = verify_data_dir_integrity(data_snapshot_before)

    raw_stdout = completed.stdout
    if "__PROFILE_JSON_START__" in raw_stdout and "__PROFILE_JSON_END__" in raw_stdout:
        json_str = (
            raw_stdout.split("__PROFILE_JSON_START__", 1)[1]
            .split("__PROFILE_JSON_END__", 1)[0]
            .strip()
        )
        parsed = json.loads(json_str)
        ret_code = int(parsed.get("return_code", completed.returncode))
        stderr_txt = str(parsed.get("standard_error", ""))

        if integrity_violations:
            ret_code = 1
            v_msg = "VIOLAÇÃO DE GUARDRAIL DE INTEGRIDADE: " + " ".join(integrity_violations)
            stderr_txt = f"{stderr_txt}\n{v_msg}".strip()

        return PipelineProfileResult(
            file_path=relative_path,
            execution_status="success" if ret_code == 0 else "error",
            return_code=ret_code,
            duration_seconds=float(parsed.get("duration_seconds", 0.0)),
            peak_memory_megabytes=float(parsed.get("peak_memory_megabytes", 0.0)),
            rows_processed=parsed.get("rows_processed"),
            column_count=parsed.get("column_count"),
            output_columns=parsed.get("output_columns", []),
            output_signature_hash=parsed.get("output_signature_hash"),
            column_hashes=parsed.get("column_hashes", {}),
            standard_output=str(parsed.get("standard_output", "")),
            standard_error=stderr_txt,
            profiled_at=now_iso,
        )

    ret_code = completed.returncode
    stderr_txt = completed.stderr.strip()
    if integrity_violations:
        ret_code = 1
        stderr_txt = f"{stderr_txt}\nVIOLAÇÃO DE GUARDRAIL: {' '.join(integrity_violations)}".strip()

    return PipelineProfileResult(
        file_path=relative_path,
        execution_status="success" if ret_code == 0 else "error",
        return_code=ret_code,
        duration_seconds=round(time.perf_counter() - start_time, 4),
        peak_memory_megabytes=0.0,
        standard_output=completed.stdout.strip(),
        standard_error=stderr_txt,
        profiled_at=now_iso,
    )


def profile_pipeline_service(
    file_path: str = "pipeline/pipeline_prep.py",
    timeout_seconds: int = PROFILING_DEFAULT_TIMEOUT_SECONDS,
) -> PipelineProfileResult:
    """Perfilamento seguro de pipeline resolvendo o caminho relativo."""
    resolved_path = resolve_pipeline_path(file_path, allow_write=False)
    return execute_and_profile_pipeline(resolved_path, timeout_seconds=timeout_seconds)

