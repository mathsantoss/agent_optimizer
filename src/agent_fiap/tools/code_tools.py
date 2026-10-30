"""Ferramentas de engenharia de código: leitura, análise estática AST, gravação segura, execução, profiling e benchmark."""
import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

from .. import config
from ..schemas import (
    CodeAnalysisReport,
    CodeDiagnosticIssue,
    PipelineBenchmarkComparison,
    PipelineProfileResult,
)
from ..utils import resolve_safe_path

FORBIDDEN_CODE_CALLS = {
    "eval",
    "exec",
    "os.system",
    "shutil.rmtree",
}

PROFILER_RUNNER_SCRIPT = """
import contextlib
import hashlib
import importlib.machinery
import importlib.util
import io
import json
import runpy
import sys
import time
import tracemalloc
from pathlib import Path

target_file = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(target_file.parent))

stdout_buffer = io.StringIO()
stderr_buffer = io.StringIO()
rows_processed = None
column_count = None
output_columns = []
output_signature_hash = None
return_code = 0

tracemalloc.start()
start_time = time.perf_counter()

try:
    with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
        loader = importlib.machinery.SourceFileLoader("__profiled_pipeline__", str(target_file))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)

        returned_value = None
        if hasattr(module, "run") and callable(module.run):
            returned_value = module.run()
        elif hasattr(module, "executar_pipeline") and callable(module.executar_pipeline):
            returned_value = module.executar_pipeline()
        else:
            module_globals = runpy.run_path(str(target_file), run_name="__main__")
            for candidate_value in module_globals.values():
                if type(candidate_value).__name__ == "DataFrame":
                    returned_value = candidate_value

        if returned_value is None:
            for candidate_value in module.__dict__.values():
                if type(candidate_value).__name__ == "DataFrame":
                    returned_value = candidate_value
                    break

        if returned_value is not None and type(returned_value).__name__ == "DataFrame":
            rows_processed = int(len(returned_value))
            output_columns = [str(col) for col in returned_value.columns]
            column_count = len(output_columns)
            try:
                import pandas as pd
                sorted_columns = sorted(output_columns)
                normalized_df = returned_value[sorted_columns].copy()
                row_hashes = pd.util.hash_pandas_object(normalized_df, index=False).values.tobytes()
                output_signature_hash = hashlib.sha256(row_hashes).hexdigest()[:16]
            except Exception:
                output_signature_hash = hashlib.sha256(
                    f"{rows_processed}:{sorted(output_columns)}".encode("utf-8")
                ).hexdigest()[:16]
except Exception as execution_error:
    return_code = 1
    stderr_buffer.write(f"{type(execution_error).__name__}: {execution_error}\\n")

duration_seconds = round(time.perf_counter() - start_time, 4)
_, peak_bytes = tracemalloc.get_traced_memory()
tracemalloc.stop()
peak_memory_megabytes = round(peak_bytes / (1024 * 1024), 3)

payload = {
    "return_code": return_code,
    "duration_seconds": duration_seconds,
    "peak_memory_megabytes": peak_memory_megabytes,
    "rows_processed": rows_processed,
    "column_count": column_count,
    "output_columns": output_columns,
    "output_signature_hash": output_signature_hash,
    "standard_output": stdout_buffer.getvalue().strip(),
    "standard_error": stderr_buffer.getvalue().strip(),
}
print("__PROFILE_JSON_START__")
print(json.dumps(payload, ensure_ascii=False))
print("__PROFILE_JSON_END__")
sys.exit(return_code)
"""


def _resolve_project_file(file_path: str, allow_write: bool = False) -> Path:
    """Resolve caminhos relativos do projeto, aceitando 'pipeline_prep.py' como atalho para 'pipeline/pipeline_prep.py'."""
    normalized_path = file_path.strip()
    if normalized_path == "pipeline_prep.py":
        normalized_path = "pipeline/pipeline_prep.py"
    elif normalized_path == "pipeline_prep.py.bak":
        normalized_path = "pipeline/pipeline_prep.py.bak"
    return resolve_safe_path(normalized_path, allow_write=allow_write)


def _get_profiles_store_path() -> Path:
    """Retorna o caminho do arquivo de histórico de perfis de execução em .rag/pipeline_profiles.json."""
    rag_directory = config.PROJECT_ROOT / ".rag"
    rag_directory.mkdir(parents=True, exist_ok=True)
    return rag_directory / "pipeline_profiles.json"


def _save_profile_snapshot(relative_path: str, profile_result: PipelineProfileResult) -> None:
    """Armazena o perfil coletado para permitir comparações posteriores de antes e depois."""
    store_path = _get_profiles_store_path()
    stored_profiles: dict = {}
    if store_path.exists():
        try:
            stored_profiles = json.loads(store_path.read_text(encoding="utf-8"))
        except Exception:
            stored_profiles = {}

    serialized = profile_result.model_dump()
    if f"baseline::{relative_path}" not in stored_profiles:
        stored_profiles[f"baseline::{relative_path}"] = serialized
    stored_profiles[f"latest::{relative_path}"] = serialized

    store_path.write_text(json.dumps(stored_profiles, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_profile_snapshot(key: str) -> PipelineProfileResult | None:
    """Carrega um snapshot de perfil de execução previamente salvo."""
    store_path = _get_profiles_store_path()
    if not store_path.exists():
        return None
    try:
        stored_profiles = json.loads(store_path.read_text(encoding="utf-8"))
        if key in stored_profiles:
            return PipelineProfileResult(**stored_profiles[key])
    except Exception:
        return None
    return None


def _get_call_name(call_node: ast.Call) -> str:
    """Retorna o nome qualificado de uma chamada de função ou método na AST."""
    if isinstance(call_node.func, ast.Name):
        return call_node.func.id
    if isinstance(call_node.func, ast.Attribute):
        if isinstance(call_node.func.value, ast.Name):
            return f"{call_node.func.value.id}.{call_node.func.attr}"
        return call_node.func.attr
    return ""


def _inspect_python_ast(source_code: str, relative_path: str) -> CodeAnalysisReport:
    """Analisa a árvore sintática (AST) de um código Python identificando estrutura, gargalos e riscos."""
    syntax_tree = ast.parse(source_code)
    imported_modules: list[str] = []
    defined_functions: list[str] = []
    has_main_guard = False
    issues: list[CodeDiagnosticIssue] = []

    groupby_locations_by_key: dict[str, list[int]] = {}
    to_datetime_locations_by_arg: dict[str, list[int]] = {}
    has_datetime_operations = False
    has_global_aggregation = False

    for node in ast.walk(syntax_tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)
        elif isinstance(node, ast.FunctionDef):
            defined_functions.append(node.name)
        elif isinstance(node, ast.If):
            try:
                condition_source = ast.unparse(node.test)
                if "__name__" in condition_source and "__main__" in condition_source:
                    has_main_guard = True
            except Exception:
                pass
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            if isinstance(node.left, ast.Subscript) and isinstance(node.right, ast.Subscript):
                issues.append(
                    CodeDiagnosticIssue(
                        category="quality",
                        evidence_type="probable",
                        severity="medium",
                        line_number=getattr(node, "lineno", None),
                        description=(
                            f"Divisão direta entre colunas detectada (`{ast.unparse(node)}`) "
                            "sem proteção explícita contra denominador zero."
                        ),
                        recommendation=(
                            "Proteja a operação contra divisão por zero usando `.replace(0, np.nan)` "
                            "ou `np.where(denominador != 0, numerador / denominador, 0.0)`."
                        ),
                    )
                )
        elif isinstance(node, ast.Call):
            qualified_call = _get_call_name(node)
            method_name = node.func.attr if isinstance(node.func, ast.Attribute) else qualified_call

            # 1. Verificação de segurança (Problema confirmado)
            if qualified_call in FORBIDDEN_CODE_CALLS:
                issues.append(
                    CodeDiagnosticIssue(
                        category="security",
                        evidence_type="confirmed",
                        severity="high",
                        line_number=getattr(node, "lineno", None),
                        description=f"Uso de chamada bloqueada por segurança: `{qualified_call}`.",
                        recommendation="Remova comandos de execução arbitrária ou deleção destrutiva.",
                    )
                )

            # 2. Detecção de loops lentos em DataFrames (.iterrows, .itertuples, .apply)
            if method_name in ("iterrows", "itertuples", "apply"):
                issues.append(
                    CodeDiagnosticIssue(
                        category="performance",
                        evidence_type="confirmed" if method_name in ("iterrows", "itertuples") else "opportunity",
                        severity="medium" if method_name == "apply" else "high",
                        line_number=getattr(node, "lineno", None),
                        description=f"Iteração linha a linha detectada via `.{method_name}()`.",
                        recommendation="Substitua por operações vetorizadas do Pandas/NumPy ou expressões nativas.",
                    )
                )

            # 3. Detecção de uso de inplace=True
            for keyword in node.keywords:
                if (
                    keyword.arg == "inplace"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is True
                ):
                    issues.append(
                        CodeDiagnosticIssue(
                            category="quality",
                            evidence_type="confirmed",
                            severity="low",
                            line_number=getattr(node, "lineno", None),
                            description=f"Uso de `inplace=True` em `.{method_name}()`, desencorajado no Pandas moderno.",
                            recommendation=f"Prefira atribuição explícita: `df = df.{method_name}(...)`.",
                        )
                    )

            # 4. Contabiliza chamadas a .groupby(...) por chave
            if method_name == "groupby" and node.args:
                has_global_aggregation = True
                key_representation = ast.unparse(node.args[0])
                groupby_locations_by_key.setdefault(key_representation, []).append(
                    getattr(node, "lineno", 0)
                )

            # 5. Contabiliza chamadas a pd.to_datetime(...) por argumento
            if method_name == "to_datetime" and node.args:
                has_datetime_operations = True
                arg_representation = ast.unparse(node.args[0])
                to_datetime_locations_by_arg.setdefault(arg_representation, []).append(
                    getattr(node, "lineno", 0)
                )

    for group_key, line_numbers in groupby_locations_by_key.items():
        if len(line_numbers) > 1:
            issues.append(
                CodeDiagnosticIssue(
                    category="performance",
                    evidence_type="confirmed",
                    severity="high",
                    line_number=line_numbers[0],
                    description=(
                        f"Agrupamento `.groupby({group_key})` executado {len(line_numbers)} vezes "
                        f"nas linhas {line_numbers}."
                    ),
                    recommendation=(
                        f"Consolide as agregações da chave {group_key} em um único "
                        "`.groupby(...).agg(...)` seguido de um único `.merge()` ou transformação."
                    ),
                )
            )

    for datetime_arg, line_numbers in to_datetime_locations_by_arg.items():
        if len(line_numbers) > 1:
            issues.append(
                CodeDiagnosticIssue(
                    category="performance",
                    evidence_type="confirmed",
                    severity="medium",
                    line_number=line_numbers[0],
                    description=(
                        f"Conversão `pd.to_datetime({datetime_arg})` repetida {len(line_numbers)} vezes "
                        f"nas linhas {line_numbers}."
                    ),
                    recommendation=(
                        f"Converta {datetime_arg} para datetime uma única vez, armazene na coluna/variável "
                        "e reutilize o acessor `.dt`."
                    ),
                )
            )

    if has_global_aggregation and has_datetime_operations:
        issues.append(
            CodeDiagnosticIssue(
                category="data_leakage",
                evidence_type="probable",
                severity="medium",
                line_number=None,
                description=(
                    "Agregação global por entidade detectada em conjunto com colunas temporais. "
                    "Em cenários de treinamento preditivo, agregações sem janela temporal podem causar data leakage."
                ),
                recommendation=(
                    "Para modelos preditivos temporais, garanta que as agregações considerem apenas "
                    "registros anteriores à data de referência ou sejam calculadas após o split temporal."
                ),
            )
        )

    has_run_entrypoint = "run" in defined_functions or "executar_pipeline" in defined_functions
    if not has_run_entrypoint:
        issues.append(
            CodeDiagnosticIssue(
                category="quality",
                evidence_type="opportunity",
                severity="low",
                line_number=None,
                description="Nenhuma função de ponto de entrada padrão (`run()` ou `executar_pipeline()`) encontrada.",
                recommendation="Defina uma função `run()` clara para facilitar a execução programática e testes.",
            )
        )

    return CodeAnalysisReport(
        file_path=relative_path,
        line_count=len(source_code.splitlines()),
        imported_modules=sorted(set(imported_modules)),
        defined_functions=defined_functions,
        has_run_entrypoint=has_run_entrypoint,
        has_main_guard=has_main_guard,
        issues=issues,
    )


def _execute_and_measure_pipeline(resolved_path: Path) -> PipelineProfileResult:
    """Executa um script Python sob instrumentação de tempo, memória (tracemalloc) e hash de saída."""
    now_iso = datetime.now(timezone.utc).isoformat()
    relative_path = str(resolved_path.relative_to(config.PROJECT_ROOT))

    completed_process = subprocess.run(
        [sys.executable, "-c", PROFILER_RUNNER_SCRIPT, str(resolved_path)],
        cwd=config.PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )

    raw_stdout = completed_process.stdout
    if "__PROFILE_JSON_START__" in raw_stdout and "__PROFILE_JSON_END__" in raw_stdout:
        json_segment = (
            raw_stdout.split("__PROFILE_JSON_START__", 1)[1]
            .split("__PROFILE_JSON_END__", 1)[0]
            .strip()
        )
        parsed_payload = json.loads(json_segment)
        return_code = int(parsed_payload.get("return_code", completed_process.returncode))
        return PipelineProfileResult(
            file_path=relative_path,
            execution_status="success" if return_code == 0 else "error",
            return_code=return_code,
            duration_seconds=float(parsed_payload.get("duration_seconds", 0.0)),
            peak_memory_megabytes=float(parsed_payload.get("peak_memory_megabytes", 0.0)),
            rows_processed=parsed_payload.get("rows_processed"),
            column_count=parsed_payload.get("column_count"),
            output_columns=parsed_payload.get("output_columns", []),
            output_signature_hash=parsed_payload.get("output_signature_hash"),
            standard_output=str(parsed_payload.get("standard_output", "")),
            standard_error=str(parsed_payload.get("standard_error", "")),
            profiled_at=now_iso,
        )

    return PipelineProfileResult(
        file_path=relative_path,
        execution_status="success" if completed_process.returncode == 0 else "error",
        return_code=completed_process.returncode,
        duration_seconds=0.0,
        peak_memory_megabytes=0.0,
        standard_output=completed_process.stdout.strip(),
        standard_error=completed_process.stderr.strip(),
        profiled_at=now_iso,
    )


def read_file(file_path: str = "pipeline/pipeline_prep.py") -> str:
    """
    Lê o conteúdo de um arquivo do projeto (padrão: 'pipeline/pipeline_prep.py').
    Se o arquivo estiver vazio, informa que está pronto para receber código via save_file.
    """
    try:
        resolved_path = _resolve_project_file(file_path, allow_write=False)
        if not resolved_path.is_file():
            return f"Arquivo não encontrado: {file_path}"

        file_content = resolved_path.read_text(encoding="utf-8")
        if not file_content.strip():
            relative_path = resolved_path.relative_to(config.PROJECT_ROOT)
            return (
                f"O arquivo '{relative_path}' existe e está atualmente vazio (0 bytes). "
                "Pronto para receber a implementação via 'save_file'."
            )
        return file_content
    except Exception as error:
        return f"Erro ao ler arquivo: {str(error)}"


def analyze_pipeline_code(file_path: str = "pipeline/pipeline_prep.py") -> str:
    """
    Realiza análise estática (AST) de um script Python do projeto (padrão: 'pipeline/pipeline_prep.py'),
    classificando apontamentos em confirmados (confirmed), prováveis (probable) e oportunidades (opportunity)
    quanto a performance (groupby/to_datetime repetidos, iterrows/apply), qualidade (inplace=True, divisão por zero)
    e riscos de data leakage.
    """
    try:
        resolved_path = _resolve_project_file(file_path, allow_write=False)
        if not resolved_path.is_file():
            return f"Arquivo não encontrado: {file_path}"

        source_code = resolved_path.read_text(encoding="utf-8")
        if not source_code.strip():
            return f"O arquivo '{file_path}' está vazio e não possui código para análise."

        relative_path = str(resolved_path.relative_to(config.PROJECT_ROOT))
        report = _inspect_python_ast(source_code, relative_path)
        return json.dumps(report.model_dump(), ensure_ascii=False, indent=2)
    except SyntaxError as syntax_error:
        return (
            f"Erro de sintaxe Python ao analisar '{file_path}' "
            f"(linha {syntax_error.lineno}): {syntax_error.msg}"
        )
    except Exception as error:
        return f"Erro ao analisar código '{file_path}': {str(error)}"


def save_file(file_path: str = "pipeline/pipeline_prep.py", content: str = "") -> str:
    """
    Salva ou atualiza código em um arquivo permitido do projeto (padrão: 'pipeline/pipeline_prep.py').
    Valida a sintaxe Python (.py) e verifica chamadas inseguras via AST antes de gravar,
    criando backup automático (.bak) se o arquivo já possuir conteúdo.
    """
    if not content.strip():
        return "Erro: o conteúdo do arquivo a ser salvo não pode ser vazio."

    try:
        resolved_path = _resolve_project_file(file_path, allow_write=True)

        # Valida a sintaxe Python e segurança via AST antes de persistir no disco
        if resolved_path.suffix == ".py":
            try:
                syntax_tree = ast.parse(content, filename=resolved_path.name)
            except SyntaxError as syntax_error:
                return (
                    f"ERRO DE SINTAXE Python na linha {syntax_error.lineno}: {syntax_error.msg}. "
                    "O arquivo NÃO foi salvo. Corrija o código."
                )

            for node in ast.walk(syntax_tree):
                if isinstance(node, ast.Call):
                    qualified_call = _get_call_name(node)
                    if qualified_call in FORBIDDEN_CODE_CALLS:
                        return (
                            f"ERRO DE SEGURANÇA: chamada '{qualified_call}' bloqueada pela política do projeto. "
                            "O arquivo NÃO foi salvo."
                        )

        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        if resolved_path.exists() and resolved_path.stat().st_size > 0:
            backup_path = resolved_path.with_suffix(resolved_path.suffix + ".bak")
            backup_path.write_text(resolved_path.read_text(encoding="utf-8"), encoding="utf-8")

        resolved_path.write_text(content, encoding="utf-8")
        line_count = len(content.splitlines())
        relative_path = resolved_path.relative_to(config.PROJECT_ROOT)
        return f"Arquivo '{relative_path}' salvo com SUCESSO com {line_count} linhas gravadas no disco."
    except Exception as error:
        return f"Erro ao salvar arquivo: {str(error)}"


def run_pipeline(file_path: str = "pipeline/pipeline_prep.py") -> str:
    """
    Executa o script do pipeline com Python em subprocesso para validar seu funcionamento
    e informa o tempo real de execução em segundos.
    """
    try:
        resolved_path = _resolve_project_file(file_path, allow_write=False)
        if not resolved_path.is_file() or resolved_path.stat().st_size == 0:
            return (
                f"Não é possível executar: o arquivo '{file_path}' está vazio ou não existe. "
                "Use a ferramenta 'save_file' para gravar o código antes de executar."
            )

        start_timestamp = time.perf_counter()
        completed_process = subprocess.run(
            [sys.executable, str(resolved_path)],
            cwd=config.PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=45,
        )
        elapsed_seconds = round(time.perf_counter() - start_timestamp, 3)

        if completed_process.returncode == 0:
            standard_output = completed_process.stdout.strip()
            output_message = standard_output if standard_output else "(executou sem erros de terminal)"
            return (
                f"Pipeline executado com SUCESSO em {elapsed_seconds}s!\n"
                f"Saída:\n{output_message}"
            )
        return (
            f"Erro na execução do pipeline após {elapsed_seconds}s "
            f"(exit code {completed_process.returncode}):\n{completed_process.stderr.strip()}"
        )
    except subprocess.TimeoutExpired:
        return "Execução do pipeline interrompida: excedeu o tempo limite de 45 segundos."
    except Exception as error:
        return f"Erro ao executar pipeline: {str(error)}"


def profile_pipeline(file_path: str = "pipeline/pipeline_prep.py") -> str:
    """
    Executa o profiling detalhado do pipeline medindo tempo de execução (perf_counter),
    pico de memória alocada em MB (tracemalloc), quantidade de linhas e colunas geradas,
    hash determinístico de saída e armazena o snapshot para benchmark comparativo.
    """
    try:
        resolved_path = _resolve_project_file(file_path, allow_write=False)
        if not resolved_path.is_file() or resolved_path.stat().st_size == 0:
            return f"Erro: o arquivo '{file_path}' está vazio ou não existe para profiling."

        profile_result = _execute_and_measure_pipeline(resolved_path)
        relative_path = str(resolved_path.relative_to(config.PROJECT_ROOT))
        _save_profile_snapshot(relative_path, profile_result)
        return json.dumps(profile_result.model_dump(), ensure_ascii=False, indent=2)
    except subprocess.TimeoutExpired:
        return "Profiling interrompido: a execução excedeu o limite de 60 segundos."
    except Exception as error:
        return f"Erro ao perfilar pipeline '{file_path}': {str(error)}"


def compare_pipeline_runs(
    baseline_file_path: str = "pipeline/pipeline_prep.py.bak",
    candidate_file_path: str = "pipeline/pipeline_prep.py",
) -> str:
    """
    Realiza benchmark comparativo real (Antes vs Depois) entre a versão original do pipeline
    (por padrão o backup 'pipeline/pipeline_prep.py.bak' ou o snapshot inicial salvo)
    e a versão otimizada ('pipeline/pipeline_prep.py').
    Compara tempo de execução, pico de memória (MB), linhas processadas e equivalência dos resultados.
    """
    try:
        candidate_resolved = _resolve_project_file(candidate_file_path, allow_write=False)
        if not candidate_resolved.is_file() or candidate_resolved.stat().st_size == 0:
            return f"Erro: arquivo candidato '{candidate_file_path}' não encontrado ou vazio."

        candidate_relative = str(candidate_resolved.relative_to(config.PROJECT_ROOT))

        # Determina o perfil de referência (Antes): executa o arquivo baseline (.bak) ou recupera snapshot salvo
        baseline_profile: PipelineProfileResult | None = None
        try:
            baseline_resolved = _resolve_project_file(baseline_file_path, allow_write=False)
            if baseline_resolved.is_file() and baseline_resolved.stat().st_size > 0:
                baseline_profile = _execute_and_measure_pipeline(baseline_resolved)
        except Exception:
            baseline_profile = None

        if baseline_profile is None:
            baseline_profile = _load_profile_snapshot(f"baseline::{candidate_relative}")

        if baseline_profile is None:
            return (
                f"Não foi encontrado o arquivo de referência '{baseline_file_path}' nem snapshot prévio "
                f"para '{candidate_relative}'. Execute 'profile_pipeline' antes de otimizar ou informe "
                "um arquivo baseline existente."
            )

        candidate_profile = _execute_and_measure_pipeline(candidate_resolved)
        _save_profile_snapshot(candidate_relative, candidate_profile)

        baseline_duration = baseline_profile.duration_seconds
        candidate_duration = candidate_profile.duration_seconds
        speedup_percentage = (
            round(((baseline_duration - candidate_duration) / baseline_duration) * 100, 2)
            if baseline_duration > 0
            else 0.0
        )

        baseline_memory = baseline_profile.peak_memory_megabytes
        candidate_memory = candidate_profile.peak_memory_megabytes
        memory_reduction_percentage = (
            round(((baseline_memory - candidate_memory) / baseline_memory) * 100, 2)
            if baseline_memory > 0
            else 0.0
        )

        # Avaliação de equivalência dos resultados
        both_succeeded = (
            baseline_profile.return_code == 0 and candidate_profile.return_code == 0
        )
        same_row_count = (
            baseline_profile.rows_processed == candidate_profile.rows_processed
        )
        same_signature = (
            baseline_profile.output_signature_hash is not None
            and baseline_profile.output_signature_hash == candidate_profile.output_signature_hash
        )
        baseline_cols_subset = set(baseline_profile.output_columns).issubset(
            set(candidate_profile.output_columns)
        )

        results_equivalent = bool(
            both_succeeded and same_row_count and (same_signature or baseline_cols_subset)
        )

        if not both_succeeded:
            equivalence_details = "Reprovada: uma das execuções falhou com código de erro."
        elif same_signature and same_row_count:
            equivalence_details = (
                f"Aprovada (Hash idêntico: {candidate_profile.output_signature_hash}, "
                f"{candidate_profile.rows_processed} linhas)."
            )
        elif same_row_count and baseline_cols_subset:
            equivalence_details = (
                f"Aprovada (Mesma contagem de {candidate_profile.rows_processed} linhas "
                "e todas as colunas originais preservadas)."
            )
        else:
            equivalence_details = (
                f"Divergente (Linhas Antes={baseline_profile.rows_processed}, "
                f"Depois={candidate_profile.rows_processed})."
            )

        comparison = PipelineBenchmarkComparison(
            baseline_file=baseline_profile.file_path,
            candidate_file=candidate_profile.file_path,
            baseline_duration_seconds=baseline_duration,
            candidate_duration_seconds=candidate_duration,
            speedup_percentage=speedup_percentage,
            baseline_peak_memory_megabytes=baseline_memory,
            candidate_peak_memory_megabytes=candidate_memory,
            memory_reduction_percentage=memory_reduction_percentage,
            baseline_rows=baseline_profile.rows_processed,
            candidate_rows=candidate_profile.rows_processed,
            results_equivalent=results_equivalent,
            equivalence_details=equivalence_details,
        )

        markdown_table = (
            "### Benchmark Comparativo de Pipeline (Antes vs Depois)\n\n"
            "| Métrica | Antes (Baseline) | Depois (Otimizado) | Variação |\n"
            "|---|---:|---:|---:|\n"
            f"| Tempo de execução | {baseline_duration:.4f} s | {candidate_duration:.4f} s | {speedup_percentage:+.2f}% |\n"
            f"| Pico de memória (Python) | {baseline_memory:.3f} MB | {candidate_memory:.3f} MB | {memory_reduction_percentage:+.2f}% |\n"
            f"| Linhas processadas | {baseline_profile.rows_processed} | {candidate_profile.rows_processed} | — |\n"
            f"| Equivalência dos resultados | — | {'Aprovada' if results_equivalent else 'Reprovada'} | {equivalence_details} |\n"
        )

        return f"{markdown_table}\n```json\n{json.dumps(comparison.model_dump(), ensure_ascii=False, indent=2)}\n```"
    except Exception as error:
        return f"Erro ao comparar execuções do pipeline: {str(error)}"


def run_tests(target_path: str = "tests") -> str:
    """
    Executa a suíte de testes automatizados do projeto com pytest.
    """
    try:
        resolved_path = resolve_safe_path(target_path, allow_write=False)
        completed_process = subprocess.run(
            [sys.executable, "-m", "pytest", str(resolved_path), "-q", "--no-header"],
            cwd=config.PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        combined_output = (completed_process.stdout + completed_process.stderr).strip()
        execution_status = "SUCESSO" if completed_process.returncode == 0 else "FALHA"
        return f"Resultado dos testes [{execution_status}]:\n{combined_output}"
    except Exception as error:
        return f"Erro ao executar testes: {str(error)}"
