"""Ferramentas públicas expostas ao Code Optimizer Agent no Google ADK:
1. inspect_pipeline: diagnóstico estático AST, leitura de arquivos, identificação de gargalos e oportunidades.
2. optimize_pipeline: proposta e execução de otimizações com autorização explícita, backup e benchmark.
3. validate_pipeline: validação completa (estática, testes, execução controlada e benchmark de equivalência).
"""
import ast
import difflib
import json
from pathlib import Path
from typing import Any

from kraken_copilot import config
from kraken_copilot.audit_logger import record_code_validation_event, record_guardrail_event
from kraken_copilot.schemas import KrakenBenchmark, KrakenCodeDiff, ToolResult
from kraken_copilot.tools.code_optimizer.services.ast_service import (
    find_ast_security_violations,
    inspect_source_code_ast,
    verify_pipeline_contract_preservation,
)
from kraken_copilot.tools.code_optimizer.services.benchmark_service import run_pipeline_benchmark
from kraken_copilot.tools.code_optimizer.services.execution_service import execute_pipeline_script
from kraken_copilot.tools.code_optimizer.services.file_service import (
    get_default_workspace_pipeline,
    get_file_tmp_paths,
    get_pipeline_tmp_dir,
    read_source_file,
    resolve_pipeline_path,
    snapshot_workspace_file,
    sync_pipeline_tmp_files,
    write_source_file,
)
from kraken_copilot.tools.code_optimizer.services.profiling_service import execute_and_profile_pipeline
from kraken_copilot.tools.code_optimizer.services.rollback_service import execute_pipeline_rollback
from kraken_copilot.tools.code_optimizer.services.testing_service import run_automated_tests


def inspect_pipeline(
    file_path: str | None = None,
) -> str:
    """
    Inspeciona um pipeline existente de forma estritamente somente-leitura.
    Analisa estrutura, funções, imports, detecta violações de segurança, gargalos de performance,
    riscos de data leakage e oportunidades de otimização sem alterar nenhum arquivo no disco.

    Args:
        file_path: Caminho do script de pipeline (opcional; se omitido, descobre dinamicamente no workspace).

    Returns:
        JSON com diagnóstico detalhado, problemas classificados por gravidade e recomendações.
    """
    if not file_path or not str(file_path).strip():
        file_path = get_default_workspace_pipeline()
    read_res = read_source_file(file_path)
    if not read_res.get("success"):
        record_code_validation_event("inspect_pipeline", file_path, "ERRO_LEITURA", read_res.get("error", ""))
        payload = {
            "success": False,
            "operation": "inspect_pipeline",
            "summary": read_res.get("error", "Arquivo não encontrado."),
            "data": None,
            "warnings": [],
            "errors": [read_res.get("error", "Arquivo não encontrado.")],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    content = read_res.get("content", "")
    rel_path = read_res.get("file_path", file_path)

    # Congela snapshot no tmp/<stem>_original.bak assim que entra no contexto
    if content:
        snapshot_workspace_file(rel_path, content=content)

    if read_res.get("is_empty"):
        payload = {
            "success": True,
            "operation": "inspect_pipeline",
            "summary": f"O arquivo '{rel_path}' existe e está vazio (0 bytes). Pronto para receber código.",
            "data": {
                "file_path": rel_path,
                "line_count": 0,
                "defined_functions": [],
                "issues": [],
            },
            "warnings": ["Arquivo vazio."],
            "errors": [],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    try:
        report = inspect_source_code_ast(content, relative_path=rel_path)
    except SyntaxError as syntax_err:
        err_msg = f"Erro de sintaxe Python na linha {syntax_err.lineno}: {syntax_err.msg}"
        record_code_validation_event("inspect_pipeline", rel_path, "ERRO_SINTAXE", err_msg)
        payload = {
            "success": False,
            "operation": "inspect_pipeline",
            "summary": err_msg,
            "data": {"file_path": rel_path, "linha_erro": syntax_err.lineno},
            "warnings": [],
            "errors": [err_msg],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    by_severity: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for issue in report.issues:
        by_severity[issue.severity] = by_severity.get(issue.severity, 0) + 1
        by_category[issue.category] = by_category.get(issue.category, 0) + 1

    record_code_validation_event(
        action="inspect_pipeline",
        file_path=rel_path,
        status="SUCESSO",
        details={
            "linhas": report.line_count,
            "funcoes": report.defined_functions,
            "total_apontamentos": len(report.issues),
            "por_severidade": by_severity,
        },
    )

    summary_text = (
        f"Inspeção concluída em '{rel_path}' ({report.line_count} linhas, {len(report.defined_functions)} funções). "
        f"{len(report.issues)} apontamento(s) identificado(s): {by_severity}."
    )

    ast_contracts = _extract_ast_function_contracts(content)

    return ToolResult.ok(
        summary=summary_text,
        operation="inspect_pipeline",
        data={
            "file_path": rel_path,
            "line_count": report.line_count,
            "imported_modules": report.imported_modules,
            "defined_functions": report.defined_functions,
            "contratos_funcoes_ast": ast_contracts,
            "has_run_entrypoint": report.has_run_entrypoint,
            "has_main_guard": report.has_main_guard,
            "issues": [issue.model_dump() for issue in report.issues],
            "resumo_apontamentos": {"por_severidade": by_severity, "por_categoria": by_category},
            "conteudo_atual": content if len(content) <= 300_000 else content[:300_000] + "\n# (truncado)",
            "dica_otimizacao": (
                "Para otimizar o pipeline: analise o 'conteudo_atual', 'contratos_funcoes_ast' e os apontamentos acima. "
                "Reescreva o código Python completo vetorizado preservando os caminhos de leitura originais, as funções "
                "e exatamente todos os nomes de colunas de saída (atenção a renomeações após merge/groupby). "
                "Em seguida, chame 'optimize_pipeline(file_path=..., proposed_code=..., confirmed_by_user=False)'."
            ),
        },
        warnings=[f"{cnt} apontamento(s) de severidade '{sev}'" for sev, cnt in by_severity.items() if sev in ("high", "medium")],
    ).to_json()


def _extract_ast_function_contracts(source_code: str) -> dict[str, Any]:
    """Extrai dinamicamente via AST os parâmetros e chaves/colunas manipuladas por cada função de qualquer script Python."""
    contracts: dict[str, Any] = {}
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return contracts

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            params = [arg.arg for arg in node.args.args]
            created_keys: list[str] = []
            for sub in ast.walk(node):
                # Captura chaves de dicionários literais (ex: resultados.append({"col": val}))
                if isinstance(sub, ast.Dict):
                    for k in sub.keys:
                        if isinstance(k, ast.Constant) and isinstance(k.value, str) and k.value not in created_keys:
                            created_keys.append(k.value)
                # Captura atribuições de colunas em DataFrames (ex: df["col"] = ... ou df.loc[i, "col"] = ...)
                elif isinstance(sub, ast.Assign):
                    for target in sub.targets:
                        if isinstance(target, ast.Subscript):
                            sl = target.slice
                            if isinstance(sl, ast.Constant) and isinstance(sl.value, str) and sl.value not in created_keys:
                                created_keys.append(sl.value)
                            elif isinstance(sl, ast.Tuple):
                                for elt in sl.elts:
                                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str) and elt.value not in created_keys:
                                        created_keys.append(elt.value)
            contracts[node.name] = {
                "parametros": params,
                "colunas_ou_chaves_criadas": created_keys,
            }
    return contracts


def optimize_pipeline(
    file_path: str | None = None,
    proposed_code: str = "",
    confirmed_by_user: bool = False,
    run_benchmark: bool = True,
) -> str:
    """
    Propõe e aplica otimizações de código em um pipeline existente de forma segura.
    Exige aprovação explícita (confirmed_by_user=True) antes de qualquer gravação em disco.
    Cria backup (.bak), valida sintaxe/segurança AST, testa e compara equivalência funcional (benchmark).

    Args:
        file_path: Caminho do pipeline alvo (opcional; se omitido, descobre dinamicamente no workspace).
        proposed_code: Código Python otimizado proposto.
        confirmed_by_user: Confirmação do usuário. Se False, elabora e exibe a proposta sem gravar no disco.
                           Se True, aplica alterações, cria backup e roda validações.
        run_benchmark: Se True, executa benchmark comparativo de performance e testes após gravar.

    Returns:
        JSON estruturado com o resultado da proposta ou da aplicação, métricas comparativas e alertas.
    """
    if not file_path or not str(file_path).strip():
        file_path = get_default_workspace_pipeline()
    clean_target = file_path.strip()
    clean_code = proposed_code.strip()

    read_res = read_source_file(clean_target)
    current_code = read_res.get("content", "")
    rel_path = read_res.get("file_path", clean_target)

    # 1. Fase de Proposta (sem confirmação explícita): NÃO altera arquivos no disco!
    orig_file, opt_file = get_file_tmp_paths(clean_target)

    if not confirmed_by_user:
        if not clean_code:
            if opt_file.is_file() and opt_file.stat().st_size > 0:
                clean_code = opt_file.read_text(encoding="utf-8").strip()
            else:
                payload = {
                    "success": False,
                    "operation": "optimize_pipeline:proposal",
                    "summary": (
                        "Para propor uma otimização, você (kraken_optimizer) deve fornecer o código Python completo reescrito "
                        "no parâmetro 'proposed_code'. Obtenha o código original via 'inspect_pipeline' (campo 'conteudo_atual'), "
                        "reescreva-o de forma vetorizada preservando os arquivos de entrada, funções e colunas originais, "
                        "e envie 'optimize_pipeline(file_path=..., proposed_code=..., confirmed_by_user=False)'."
                    ),
                    "data": {"file_path": rel_path},
                    "warnings": ["Nenhum código proposto fornecido."],
                    "errors": ["Código proposto vazio."],
                }
                return json.dumps(payload, ensure_ascii=False, indent=2)

        # Validação sintática prévia da proposta
        try:
            ast.parse(clean_code)
        except SyntaxError as syn_err:
            err_msg = f"A proposta contém erro de sintaxe na linha {syn_err.lineno}: {syn_err.msg}"
            payload = {
                "success": False,
                "operation": "optimize_pipeline:proposal",
                "summary": err_msg,
                "data": {"linha_erro": syn_err.lineno},
                "warnings": [],
                "errors": [err_msg],
            }
            return json.dumps(payload, ensure_ascii=False, indent=2)

        contract_violation = verify_pipeline_contract_preservation(current_code, clean_code)
        proposal_warnings = []
        if contract_violation:
            proposal_warnings.append(contract_violation)

        # 1. Salva e sincroniza fisicamente os 2 arquivos dinâmicos na pasta krakenlake/tmp/:
        #    - krakenlake/tmp/<stem>_original.bak (backup do original congelado)
        #    - krakenlake/tmp/<stem>_otimizado.bak (pipeline otimizado / proposta atual)
        tmp_original_path, tmp_opt_path = sync_pipeline_tmp_files(
            original_content=current_code,
            optimized_content=clean_code,
            target_file=clean_target,
        )

        # Executa benchmark comparativo da proposta sem alterar o arquivo original
        benchmark_proposal_data = None
        if run_benchmark:
            try:
                bench_res = run_pipeline_benchmark(
                    baseline_file_path=str(tmp_original_path),
                    candidate_file_path=str(tmp_opt_path),
                )
                benchmark_proposal_data = bench_res.get("data")
                if benchmark_proposal_data:
                    cand_status = benchmark_proposal_data.get("candidate_status")
                    comp = benchmark_proposal_data.get("comparison", {})
                    if cand_status == "error" or not comp.get("results_equivalent", True):
                        cand_err = benchmark_proposal_data.get("candidate_error") or comp.get("equivalence_details", "Erro na validação")
                        err_msg = (
                            f"O código proposto falhou durante o teste de execução/equivalência:\n{cand_err}\n\n"
                            f"Corrija imediatamente o problema no seu 'proposed_code' (verifique os nomes das colunas após merge/groupby) "
                            f"e chame 'optimize_pipeline(file_path=\"{rel_path}\", proposed_code=..., confirmed_by_user=False)' novamente "
                            f"antes de apresentar a proposta ao usuário."
                        )
                        payload = {
                            "success": False,
                            "operation": "optimize_pipeline:proposal",
                            "summary": err_msg,
                            "data": {
                                "file_path": rel_path,
                                "benchmark": benchmark_proposal_data,
                                "requer_correcao": True,
                            },
                            "warnings": proposal_warnings,
                            "errors": [cand_err],
                        }
                        return json.dumps(payload, ensure_ascii=False, indent=2)
            except Exception as bench_err:
                proposal_warnings.append(f"Benchmark prévio não pôde ser concluído: {bench_err}")

        summary_proposal = (
            f"Proposta de otimização para '{rel_path}' elaborada com sucesso.\n"
            f"Arquivos físicos salvos e sincronizados na pasta 'krakenlake/tmp/':\n"
            f"  1. Backup do original: '{tmp_original_path.relative_to(config.PROJECT_ROOT)}'\n"
            f"  2. Pipeline otimizado: '{tmp_opt_path.relative_to(config.PROJECT_ROOT)}'\n\n"
            f"O arquivo original '{rel_path}' NÃO foi alterado no disco e permanece com o código original até sua confirmação explícita.\n\n"
        )
        if benchmark_proposal_data and benchmark_proposal_data.get("tabela_markdown"):
            summary_proposal += (
                f"{benchmark_proposal_data['tabela_markdown']}\n\n"
                f"Deseja confirmar a aplicação dessa otimização para substituir definitivamente o arquivo original "
                f"'{rel_path}'? Responda confirmando para prosseguirmos."
            )
        else:
            summary_proposal += (
                f"Apresente a proposta ao usuário. Para aplicar a gravação física no disco e substituir "
                f"definitivamente '{rel_path}', invoque 'optimize_pipeline' com 'confirmed_by_user=True'."
            )

        diff_lines = list(
            difflib.unified_diff(
                current_code.splitlines(keepends=True),
                clean_code.splitlines(keepends=True),
                fromfile=f"a/{rel_path}",
                tofile=f"b/{rel_path}",
            )
        )
        raw_diff = "".join(diff_lines)
        adds = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
        dels = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))

        kraken_code_diff = KrakenCodeDiff(
            arquivo=Path(rel_path).name,
            arquivo_alvo=rel_path,
            original_code=current_code,
            proposed_code=clean_code,
            raw_diff=raw_diff,
            adicoes=adds,
            remocoes=dels,
            has_approval_request=True,
            tipo_transformacao="otimizacao",
            explicacao="Otimização vetorizada de loops e transformações com preservação de contratos.",
        )

        payload = {
            "success": True,
            "operation": "optimize_pipeline:proposal",
            "summary": summary_proposal,
            "data": {
                "file_path": rel_path,
                "linhas_originais": len(current_code.splitlines()),
                "linhas_propostas": len(clean_code.splitlines()),
                "benchmark": benchmark_proposal_data,
                "kraken_code_diff": kraken_code_diff.model_dump(),
                "requer_confirmacao": True,
                "instrucao_confirmacao": "Chame optimize_pipeline(file_path=..., proposed_code=..., confirmed_by_user=True)",
            },
            "warnings": proposal_warnings,
            "errors": [],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    # 2. Fase de Aplicação Autorizada (confirmed_by_user=True)
    if not clean_code:
        # Se clean_code não foi fornecido na confirmação, utiliza a proposta salva previamente em krakenlake/tmp/<stem>_otimizado.bak
        if opt_file.is_file() and opt_file.stat().st_size > 0:
            clean_code = opt_file.read_text(encoding="utf-8").strip()
        else:
            payload = {
                "success": False,
                "operation": "optimize_pipeline:apply",
                "summary": f"Não é possível aplicar: nenhum código proposto foi fornecido e não há proposta salva em '{opt_file.name}'.",
                "data": None,
                "errors": ["Código proposto vazio."],
            }
            return json.dumps(payload, ensure_ascii=False, indent=2)

    # Validação AST e de Segurança antes de tocar no disco
    try:
        new_tree = ast.parse(clean_code)
    except SyntaxError as syntax_error:
        err_msg = f"ERRO DE SINTAXE na linha {syntax_error.lineno}: {syntax_error.msg}. Alteração NÃO foi aplicada."
        record_code_validation_event("optimize_pipeline", rel_path, "BLOQUEADO_SINTAXE", err_msg)
        payload = {
            "success": False,
            "operation": "optimize_pipeline:apply",
            "summary": err_msg,
            "data": None,
            "errors": [err_msg],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    security_violations = find_ast_security_violations(new_tree)
    if security_violations:
        _, first_violation = security_violations[0]
        sec_msg = f"ERRO DE SEGURANÇA: {first_violation} O arquivo NÃO foi salvo."
        record_guardrail_event("AST_SECURITY", f"optimize_pipeline({rel_path})", "BLOQUEADO", first_violation)
        payload = {
            "success": False,
            "operation": "optimize_pipeline:apply",
            "summary": sec_msg,
            "data": None,
            "errors": [sec_msg],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    contract_error = verify_pipeline_contract_preservation(current_code, clean_code)
    if contract_error:
        record_guardrail_event("CONTRACT_GUARDRAIL", f"optimize_pipeline({rel_path})", "BLOQUEADO", contract_error)
        payload = {
            "success": False,
            "operation": "optimize_pipeline:apply",
            "summary": contract_error,
            "data": None,
            "errors": [contract_error],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    # Gravação física no disco com criação automática de backup (.bak)
    write_res = write_source_file(clean_target, clean_code, create_backup=True)
    if not write_res.get("success"):
        payload = {
            "success": False,
            "operation": "optimize_pipeline:apply",
            "summary": write_res.get("error", "Erro ao gravar arquivo."),
            "data": None,
            "errors": [write_res.get("error", "Erro ao gravar arquivo.")],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    record_code_validation_event(
        action="optimize_pipeline",
        file_path=rel_path,
        status="SALVO",
        details={"linhas": write_res.get("line_count"), "backup": write_res.get("backup_file")},
    )

    benchmark_data: dict[str, Any] | None = None
    tests_data: dict[str, Any] | None = None
    apply_warnings: list[str] = []
    apply_errors: list[str] = []

    if run_benchmark:
        # Executa testes automatizados
        tests_res = run_automated_tests(target_path="tests")
        tests_data = tests_res
        if not tests_res.get("success"):
            apply_warnings.append(f"Atenção: Testes automatizados falharam após a otimização.")

        # Executa benchmark comparativo Antes vs Depois
        base_file = str(orig_file) if orig_file.is_file() else f"{clean_target}.bak"
        bench_res = run_pipeline_benchmark(
            baseline_file_path=base_file,
            candidate_file_path=clean_target,
        )
        benchmark_data = bench_res.get("data")
        if not bench_res.get("success"):
            apply_warnings.append(bench_res.get("summary", "Benchmark não pôde ser concluído."))

    summary_final = (
        f"Pipeline '{rel_path}' otimizado e gravado com SUCESSO no disco "
        f"({write_res.get('line_count')} linhas). "
        f"Arquivos físicos mantidos em 'krakenlake/tmp/': '{orig_file.name}' e '{opt_file.name}'. "
        f"{'Benchmark executado.' if run_benchmark else ''}"
    )
    if benchmark_data and benchmark_data.get("tabela_markdown"):
        summary_final += f"\n\n{benchmark_data['tabela_markdown']}"

    return ToolResult.ok(
        summary=summary_final,
        operation="optimize_pipeline:apply",
        data={
            "file_path": rel_path,
            "linhas_gravadas": write_res.get("line_count"),
            "backup_criado": write_res.get("backup_created"),
            "arquivo_backup": write_res.get("backup_file"),
            "benchmark": benchmark_data,
            "testes": tests_data,
        },
        warnings=apply_warnings,
    ).to_json()


def validate_pipeline(
    file_path: str | None = None,
    run_tests: bool = True,
    run_profile: bool = True,
    compare_with_baseline: bool = True,
    rollback_on_failure: bool = False,
) -> str:
    """
    Valida a integridade e funcionamento do pipeline em múltiplos níveis:
    1. Validação estática: sintaxe Python e conformidade AST.
    2. Testes automatizados: execução com pytest.
    3. Execução controlada: tempo, memória e integridade dos dados brutos.
    4. Benchmark comparativo: equivalência dos resultados com a versão baseline (.bak).
    Permite rollback automático em caso de falha crítica caso solicitado.

    Args:
        file_path: Caminho do script de pipeline a validar (opcional; se omitido, descobre dinamicamente no workspace).
        run_tests: Se True, executa os testes do projeto via pytest.
        run_profile: Se True, executa profiling medindo tempo e memória.
        compare_with_baseline: Se True, compara com o snapshot ou baseline (.bak).
        rollback_on_failure: Se True, restaura o backup (.bak) se testes ou execução falharem.

    Returns:
        JSON com o diagnóstico detalhado discriminando cada nível de validação.
    """
    if not file_path or not str(file_path).strip():
        file_path = get_default_workspace_pipeline()
    clean_path = file_path.strip()
    read_res = read_source_file(clean_path)
    if not read_res.get("success"):
        payload = {
            "success": False,
            "operation": "validate_pipeline",
            "summary": read_res.get("error", "Arquivo não encontrado."),
            "data": None,
            "errors": [read_res.get("error", "Arquivo não encontrado.")],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    content = read_res.get("content", "")
    rel_path = read_res.get("file_path", clean_path)

    # Nível 1: Validação Estática
    try:
        syntax_tree = ast.parse(content)
        sec_violations = find_ast_security_violations(syntax_tree)
        static_status = "APROVADA" if not sec_violations else "FALHA_SEGURANCA"
    except SyntaxError as syn_err:
        err_msg = f"Erro de sintaxe Python na linha {syn_err.lineno}: {syn_err.msg}"
        record_code_validation_event("validate_pipeline", rel_path, "ERRO_SINTAXE", err_msg)
        payload = {
            "success": False,
            "operation": "validate_pipeline",
            "summary": f"Validação Estática REPROVADA: {err_msg}",
            "data": {"validacao_estatica": "REPROVADA", "linha": syn_err.lineno},
            "errors": [err_msg],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    # Nível 2: Execução de Testes
    tests_output: dict[str, Any] | None = None
    if run_tests:
        tests_output = run_automated_tests(target_path="tests")

    # Nível 3: Execução Controlada e Profiling
    resolved_path = resolve_pipeline_path(clean_path, allow_write=False)
    profile_output: dict[str, Any] | None = None
    if run_profile:
        profile_res = execute_and_profile_pipeline(resolved_path)
        profile_output = profile_res.model_dump()

    # Nível 4: Benchmark Comparativo com o Baseline
    benchmark_output: dict[str, Any] | None = None
    validation_warnings: list[str] = []
    if compare_with_baseline:
        from kraken_copilot.tools.code_optimizer.services.benchmark_service import clean_snapshot_key, load_profile_snapshot
        clean_key = clean_snapshot_key(clean_path)
        try:
            bak_candidate = resolve_pipeline_path(f"{clean_path}.bak", allow_write=False)
            has_bak_file = bak_candidate.is_file() and bak_candidate.stat().st_size > 0
        except Exception:
            has_bak_file = False

        orig_file, opt_file = get_file_tmp_paths(clean_path)
        has_tmp_base = orig_file.is_file() and orig_file.stat().st_size > 0
        has_baseline = has_tmp_base or has_bak_file or load_profile_snapshot(f"baseline::{clean_key}") is not None

        if has_baseline:
            base_choice = str(orig_file) if has_tmp_base else f"{clean_path}.bak"
            benchmark_output = run_pipeline_benchmark(
                baseline_file_path=base_choice,
                candidate_file_path=clean_path,
            )
            if not benchmark_output.get("success"):
                validation_warnings.append(benchmark_output.get("summary", "Benchmark apresentou divergências."))
        else:
            validation_warnings.append(
                f"Benchmark comparativo não executado: arquivo de backup '{clean_path}.bak' ainda não foi gerado."
            )

    # Avaliação Geral
    static_ok = static_status == "APROVADA"
    tests_ok = bool(tests_output.get("success", False)) if tests_output else True
    execution_ok = bool(profile_output.get("execution_status") == "success") if profile_output else True
    benchmark_ok = bool(benchmark_output.get("success", False)) if benchmark_output else True

    overall_success = static_ok and tests_ok and execution_ok and benchmark_ok

    rollback_applied = False
    if not overall_success and rollback_on_failure:
        rollback_res = execute_pipeline_rollback(clean_path)
        rollback_applied = rollback_res.get("success", False)

    summary_text = (
        f"Validação de '{rel_path}': "
        f"Estática={'OK' if static_ok else 'FALHA'}, "
        f"Testes={'OK' if tests_ok else ('FALHA' if tests_output else 'IGNORADO')}, "
        f"Execução={'OK' if execution_ok else ('FALHA' if profile_output else 'IGNORADO')}, "
        f"Benchmark={'OK' if benchmark_ok else ('FALHA' if benchmark_output else 'IGNORADO')}. "
        f"Status Geral: {'APROVADO' if overall_success else 'REPROVADO'}."
    )
    if benchmark_output and benchmark_output.get("data", {}).get("tabela_markdown"):
        summary_text += f"\n\n{benchmark_output['data']['tabela_markdown']}"

    record_code_validation_event(
        action="validate_pipeline",
        file_path=rel_path,
        status="APROVADO" if overall_success else "REPROVADO",
        details={
            "estatica": static_status,
            "testes": tests_ok,
            "execucao": execution_ok,
            "benchmark": benchmark_ok,
            "rollback_aplicado": rollback_applied,
        },
    )

    data_val = {
        "file_path": rel_path,
        "validacao_estatica": static_status,
        "testes_automatizados": tests_output,
        "perfil_execucao": profile_output,
        "benchmark_equivalencia": benchmark_output.get("data") if benchmark_output else None,
        "rollback_executado": rollback_applied,
    }

    if overall_success:
        return ToolResult.ok(
            summary=summary_text,
            operation="validate_pipeline",
            data=data_val,
            warnings=validation_warnings,
        ).to_json()
    else:
        return ToolResult.fail(
            summary=summary_text,
            operation="validate_pipeline",
            errors=["Pipeline apresentou falhas nas validações."],
            data=data_val,
            warnings=["Uma ou mais etapas de validação falharam."],
        ).to_json()

