"""Serviço de análise estática e diagnósticos de código via AST (Segurança, Performance, Qualidade e Contratos)."""
import ast
from typing import Any

from kraken_copilot.schemas import CodeAnalysisReport, CodeDiagnosticIssue

FORBIDDEN_CODE_CALLS = {
    "eval",
    "exec",
    "compile",
    "__import__",
    "os.system",
    "os.popen",
    "os.remove",
    "os.unlink",
    "os.rmdir",
    "os.removedirs",
    "shutil.rmtree",
    "shutil.move",
    "subprocess.run",
    "subprocess.Popen",
    "subprocess.call",
    "subprocess.check_output",
    "subprocess.check_call",
    "socket.socket",
    "urllib.request.urlopen",
    "requests.get",
    "requests.post",
    "requests.put",
    "requests.delete",
}

FORBIDDEN_IMPORT_MODULES = {
    "subprocess",
    "socket",
    "shutil",
    "ctypes",
    "webbrowser",
    "ftplib",
    "telnetlib",
    "xmlrpc",
}

DATA_WRITE_METHODS = {
    "to_csv",
    "to_parquet",
    "to_json",
    "to_excel",
    "to_pickle",
    "to_feather",
}


def _get_call_name(call_node: ast.Call) -> str:
    """Retorna o nome qualificado de uma chamada de função na AST."""
    if isinstance(call_node.func, ast.Name):
        return call_node.func.id
    if isinstance(call_node.func, ast.Attribute):
        if isinstance(call_node.func.value, ast.Name):
            return f"{call_node.func.value.id}.{call_node.func.attr}"
        if isinstance(call_node.func.value, ast.Attribute) and isinstance(call_node.func.value.value, ast.Name):
            return f"{call_node.func.value.value.id}.{call_node.func.value.attr}.{call_node.func.attr}"
        return call_node.func.attr
    return ""


def _is_raw_data_write_call(call_node: ast.Call) -> str | None:
    """Verifica se uma chamada tenta gravar arquivos dentro de pipeline/dados/."""
    qualified_call = _get_call_name(call_node)
    method_name = call_node.func.attr if isinstance(call_node.func, ast.Attribute) else qualified_call

    if method_name in DATA_WRITE_METHODS and call_node.args:
        first_arg = call_node.args[0]
        if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
            norm_target = first_arg.value.replace("\\", "/").lower()
            if "krakenlake/catalog" in norm_target or "catalog/sources" in norm_target or "pipeline/dados" in norm_target or ("dados_vendas" in norm_target and norm_target.endswith(".csv")):
                return f"Tentativa de sobrescrever dados brutos protegidos via `.{method_name}('{first_arg.value}')`."

    if qualified_call == "open" and len(call_node.args) >= 1:
        first_arg = call_node.args[0]
        mode = "r"
        if len(call_node.args) >= 2 and isinstance(call_node.args[1], ast.Constant):
            mode = str(call_node.args[1].value)
        for kw in call_node.keywords:
            if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                mode = str(kw.value.value)

        if any(f in mode for f in ("w", "a", "x", "+")):
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                norm_target = first_arg.value.replace("\\", "/").lower()
                if "krakenlake/catalog" in norm_target or "catalog/sources" in norm_target or "pipeline/dados" in norm_target or ("dados_vendas" in norm_target and norm_target.endswith(".csv")):
                    return f"Tentativa de abrir dados brutos em modo escrita (`open('{first_arg.value}', '{mode}')`)."
    return None


def find_ast_security_violations(syntax_tree: ast.AST) -> list[tuple[int | None, str]]:
    """Identifica violações de segurança (imports bloqueados, chamadas perigosas e escrita em dados brutos)."""
    violations: list[tuple[int | None, str]] = []

    for node in ast.walk(syntax_tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_module = alias.name.split(".")[0]
                if root_module in FORBIDDEN_IMPORT_MODULES or alias.name in FORBIDDEN_IMPORT_MODULES:
                    violations.append((getattr(node, "lineno", None), f"Importação de módulo bloqueado: `{alias.name}`."))
        elif isinstance(node, ast.ImportFrom) and node.module:
            root_module = node.module.split(".")[0]
            if root_module in FORBIDDEN_IMPORT_MODULES or node.module in FORBIDDEN_IMPORT_MODULES:
                violations.append((getattr(node, "lineno", None), f"Importação de módulo bloqueado: `{node.module}`."))
        elif isinstance(node, ast.Call):
            qualified = _get_call_name(node)
            method = node.func.attr if isinstance(node.func, ast.Attribute) else qualified

            if qualified in FORBIDDEN_CODE_CALLS or method in ("unlink", "rmdir", "removedirs"):
                violations.append((getattr(node, "lineno", None), f"Uso de chamada de sistema bloqueada: `{qualified}`."))

            raw_write_err = _is_raw_data_write_call(node)
            if raw_write_err:
                violations.append((getattr(node, "lineno", None), raw_write_err))

    return violations


def verify_pipeline_contract_preservation(original_code: str, new_code: str) -> str | None:
    """Garante que a nova versão do pipeline não remova o ponto de entrada (run ou executar_pipeline)."""
    if not original_code or not original_code.strip():
        return None

    try:
        orig_tree = ast.parse(original_code)
        new_tree = ast.parse(new_code)
    except SyntaxError:
        return None

    orig_functions = {n.name for n in ast.walk(orig_tree) if isinstance(n, ast.FunctionDef)}
    new_functions = {n.name for n in ast.walk(new_tree) if isinstance(n, ast.FunctionDef)}

    had_entry = bool(orig_functions & {"run", "executar_pipeline"})
    has_entry = bool(new_functions & {"run", "executar_pipeline"})

    if had_entry and not has_entry:
        return "Violação de Contrato de Pipeline: o arquivo original possuía ponto de entrada ('run' ou 'executar_pipeline') e a nova versão o removeu."
    return None


def inspect_source_code_ast(source_code: str, relative_path: str = "script.py") -> CodeAnalysisReport:
    """Realiza o diagnóstico estático completo do código Python gerando relatório estruturado."""
    syntax_tree = ast.parse(source_code)
    imported_modules: list[str] = []
    defined_functions: list[str] = []
    has_main_guard = False
    issues: list[CodeDiagnosticIssue] = []

    groupby_locations: dict[str, list[int]] = {}
    to_datetime_locations: dict[str, list[int]] = {}
    has_datetime_ops = False
    has_global_agg = False

    # 1. Violações de segurança
    for line_no, sec_desc in find_ast_security_violations(syntax_tree):
        issues.append(
            CodeDiagnosticIssue(
                category="security",
                evidence_type="confirmed",
                severity="high",
                line_number=line_no,
                description=sec_desc,
                recommendation="Remova chamadas de sistema, rede, subprocessos ou gravação em pipeline/dados/.",
            )
        )

    # 2. Varredura estrutural e qualidade
    for node in ast.walk(syntax_tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)
        elif isinstance(node, ast.FunctionDef):
            defined_functions.append(node.name)
        elif isinstance(node, ast.If):
            # if __name__ == '__main__':
            if isinstance(node.test, ast.Compare):
                left = node.test.left
                if isinstance(left, ast.Name) and left.id == "__name__":
                    for comparator in node.test.comparators:
                        if isinstance(comparator, ast.Constant) and comparator.value == "__main__":
                            has_main_guard = True

        elif isinstance(node, ast.Call):
            qualified_call = _get_call_name(node)
            method_name = node.func.attr if isinstance(node.func, ast.Attribute) else qualified_call

            # Detecta iterrows ou itertuples
            if method_name in ("iterrows", "itertuples"):
                issues.append(
                    CodeDiagnosticIssue(
                        category="performance",
                        evidence_type="confirmed",
                        severity="high",
                        line_number=getattr(node, "lineno", None),
                        description=f"Iteração linha a linha detectada via `.{method_name}()`.",
                        recommendation="Substitua loops iterativos por operações vetorizadas do Pandas ou NumPy.",
                    )
                )

            # Detecta apply com lambda
            if method_name == "apply" and node.args and isinstance(node.args[0], ast.Lambda):
                issues.append(
                    CodeDiagnosticIssue(
                        category="performance",
                        evidence_type="probable",
                        severity="medium",
                        line_number=getattr(node, "lineno", None),
                        description="Uso de `.apply(lambda ...)` para transformações.",
                        recommendation="Prefira operações vetorizadas nativas, acessor `.dt` para datas ou `.str` para texto.",
                    )
                )

            # Detecta múltiplos groupbys na mesma chave
            if method_name == "groupby" and node.args:
                key_repr = ast.unparse(node.args[0])
                line_no = getattr(node, "lineno", 0)
                groupby_locations.setdefault(key_repr, []).append(line_no)
                has_global_agg = True

            # Detecta to_datetime repetidos
            if "to_datetime" in qualified_call and node.args:
                arg_repr = ast.unparse(node.args[0])
                line_no = getattr(node, "lineno", 0)
                to_datetime_locations.setdefault(arg_repr, []).append(line_no)
                has_datetime_ops = True

            # Detecta inplace=True
            for kw in node.keywords:
                if kw.arg == "inplace" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    issues.append(
                        CodeDiagnosticIssue(
                            category="quality",
                            evidence_type="confirmed",
                            severity="low",
                            line_number=getattr(node, "lineno", None),
                            description="Uso de `inplace=True` desencorajado em versões modernas do Pandas.",
                            recommendation="Atribua o resultado diretamente (ex.: `df = df.drop(...)`).",
                        )
                    )

            # Detecta data leakage via fit_transform global
            if method_name == "fit_transform":
                issues.append(
                    CodeDiagnosticIssue(
                        category="data_leakage",
                        evidence_type="probable",
                        severity="medium",
                        line_number=getattr(node, "lineno", None),
                        description="Chamada a `.fit_transform()` detectada no pipeline completo.",
                        recommendation="Aplique `.fit()` exclusivamente no conjunto de treino e `.transform()` na validação.",
                    )
                )

    # Consolida apontamentos de repetição
    for group_key, lines in groupby_locations.items():
        if len(lines) > 1:
            issues.append(
                CodeDiagnosticIssue(
                    category="performance",
                    evidence_type="confirmed",
                    severity="high",
                    line_number=lines[0],
                    description=f"Agrupamento `.groupby({group_key})` executado {len(lines)} vezes nas linhas {lines}.",
                    recommendation=f"Consolide em um único `.groupby({group_key}).agg(...)` seguido de merge/transform.",
                )
            )

    for dt_arg, lines in to_datetime_locations.items():
        if len(lines) > 1:
            issues.append(
                CodeDiagnosticIssue(
                    category="performance",
                    evidence_type="confirmed",
                    severity="medium",
                    line_number=lines[0],
                    description=f"Conversão `pd.to_datetime({dt_arg})` repetida {len(lines)} vezes nas linhas {lines}.",
                    recommendation="Converta a coluna uma única vez e reutilize o acessor `.dt`.",
                )
            )

    has_entrypoint = bool({"run", "executar_pipeline"} & set(defined_functions))
    if not has_entrypoint:
        issues.append(
            CodeDiagnosticIssue(
                category="quality",
                evidence_type="opportunity",
                severity="low",
                line_number=None,
                description="Nenhuma função padrão de entrada (`run()` ou `executar_pipeline()`) encontrada.",
                recommendation="Defina uma função `run()` clara para facilitar execuções programáticas e testes.",
            )
        )

    return CodeAnalysisReport(
        file_path=relative_path,
        line_count=len(source_code.splitlines()),
        imported_modules=sorted(set(imported_modules)),
        defined_functions=defined_functions,
        has_run_entrypoint=has_entrypoint,
        has_main_guard=has_main_guard,
        issues=issues,
    )

