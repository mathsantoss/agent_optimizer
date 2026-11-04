"""Ferramentas públicas expostas ao Code Optimizer Agent no Google ADK:
1. inspect_pipeline: diagnóstico estático AST, leitura de arquivos, identificação de gargalos e oportunidades.
2. optimize_pipeline: proposta e execução de otimizações com autorização explícita, backup e benchmark.
3. validate_pipeline: validação completa (estática, testes, execução controlada e benchmark de equivalência).
"""
import ast
import json
from typing import Any

from agent_fiap.audit_logger import record_code_validation_event, record_guardrail_event
from agent_fiap.schemas import ToolResult
from agent_fiap.tools.code_optimizer.services.ast_service import (
    find_ast_security_violations,
    inspect_source_code_ast,
    verify_pipeline_contract_preservation,
)
from agent_fiap.tools.code_optimizer.services.benchmark_service import run_pipeline_benchmark
from agent_fiap.tools.code_optimizer.services.execution_service import execute_pipeline_script
from agent_fiap.tools.code_optimizer.services.file_service import (
    read_source_file,
    resolve_pipeline_path,
    write_source_file,
)
from agent_fiap.tools.code_optimizer.services.profiling_service import execute_and_profile_pipeline
from agent_fiap.tools.code_optimizer.services.rollback_service import execute_pipeline_rollback
from agent_fiap.tools.code_optimizer.services.testing_service import run_automated_tests


def inspect_pipeline(
    file_path: str = "pipeline/pipeline_prep.py",
) -> str:
    """
    Inspeciona um pipeline existente de forma estritamente somente-leitura.
    Analisa estrutura, funções, imports, detecta violações de segurança, gargalos de performance,
    riscos de data leakage e oportunidades de otimização sem alterar nenhum arquivo no disco.

    Args:
        file_path: Caminho do script de pipeline (padrão: 'pipeline/pipeline_prep.py').

    Returns:
        JSON com diagnóstico detalhado, problemas classificados por gravidade e recomendações.
    """
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

    return ToolResult.ok(
        summary=summary_text,
        operation="inspect_pipeline",
        data={
            "file_path": rel_path,
            "line_count": report.line_count,
            "imported_modules": report.imported_modules,
            "defined_functions": report.defined_functions,
            "has_run_entrypoint": report.has_run_entrypoint,
            "has_main_guard": report.has_main_guard,
            "issues": [issue.model_dump() for issue in report.issues],
            "resumo_apontamentos": {"por_severidade": by_severity, "por_categoria": by_category},
            "conteudo_atual": content if report.line_count <= 250 else "(conteúdo extenso omitido no sumário)",
        },
        warnings=[f"{cnt} apontamento(s) de severidade '{sev}'" for sev, cnt in by_severity.items() if sev in ("high", "medium")],
    ).to_json()


def optimize_pipeline(
    file_path: str = "pipeline/pipeline_prep.py",
    proposed_code: str = "",
    confirmed_by_user: bool = False,
    run_benchmark: bool = True,
) -> str:
    """
    Propõe e aplica otimizações de código em um pipeline existente de forma segura.
    Exige aprovação explícita (confirmed_by_user=True) antes de qualquer gravação em disco.
    Cria backup (.bak), valida sintaxe/segurança AST, testa e compara equivalência funcional (benchmark).

    Args:
        file_path: Caminho do pipeline alvo (padrão: 'pipeline/pipeline_prep.py').
        proposed_code: Código Python otimizado proposto.
        confirmed_by_user: Confirmação do usuário. Se False, elabora e exibe a proposta sem gravar no disco.
                           Se True, aplica alterações, cria backup e roda validações.
        run_benchmark: Se True, executa benchmark comparativo de performance e testes após gravar.

    Returns:
        JSON estruturado com o resultado da proposta ou da aplicação, métricas comparativas e alertas.
    """
    clean_target = file_path.strip()
    clean_code = proposed_code.strip()

    read_res = read_source_file(clean_target)
    current_code = read_res.get("content", "")
    rel_path = read_res.get("file_path", clean_target)

    # 1. Fase de Proposta (sem confirmação explícita): NÃO altera arquivos no disco!
    if not confirmed_by_user:
        if not clean_code:
            payload = {
                "success": False,
                "operation": "optimize_pipeline:proposal",
                "summary": "Para propor uma otimização, forneça o 'proposed_code'.",
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

        summary_proposal = (
            f"Proposta de otimização para '{rel_path}' elaborada com sucesso. "
            "NENHUM arquivo foi alterado no disco ainda. "
            "Apresente o plano e as mudanças ao usuário e solicite aprovação explícita. "
            "Para aplicar a gravação física no disco e rodar os benchmarks, invoque 'optimize_pipeline' com 'confirmed_by_user=True'."
        )

        payload = {
            "success": True,
            "operation": "optimize_pipeline:proposal",
            "summary": summary_proposal,
            "data": {
                "file_path": rel_path,
                "linhas_originais": len(current_code.splitlines()),
                "linhas_propostas": len(clean_code.splitlines()),
                "requer_confirmacao": True,
                "instrucao_confirmacao": "Chame optimize_pipeline(file_path=..., proposed_code=..., confirmed_by_user=True)",
            },
            "warnings": proposal_warnings,
            "errors": [],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    # 2. Fase de Aplicação Autorizada (confirmed_by_user=True)
    if not clean_code:
        payload = {
            "success": False,
            "operation": "optimize_pipeline:apply",
            "summary": "Não é possível aplicar alteração com código proposto vazio.",
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
        bench_res = run_pipeline_benchmark(
            baseline_file_path=f"{clean_target}.bak",
            candidate_file_path=clean_target,
        )
        benchmark_data = bench_res.get("data")
        if not bench_res.get("success"):
            apply_warnings.append(bench_res.get("summary", "Benchmark não pôde ser concluído."))

    summary_final = (
        f"Pipeline '{rel_path}' otimizado e gravado com SUCESSO no disco "
        f"({write_res.get('line_count')} linhas). Backup salvo em '{write_res.get('backup_file')}'. "
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
    file_path: str = "pipeline/pipeline_prep.py",
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
        file_path: Caminho do script de pipeline a validar (padrão: 'pipeline/pipeline_prep.py').
        run_tests: Se True, executa os testes do projeto via pytest.
        run_profile: Se True, executa profiling medindo tempo e memória.
        compare_with_baseline: Se True, compara com o snapshot ou baseline (.bak).
        rollback_on_failure: Se True, restaura o backup (.bak) se testes ou execução falharem.

    Returns:
        JSON com o diagnóstico detalhado discriminando cada nível de validação.
    """
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
        from agent_fiap.tools.code_optimizer.services.benchmark_service import clean_snapshot_key, load_profile_snapshot
        bak_candidate = Path(config.PROJECT_ROOT) / f"{clean_path}.bak"
        clean_key = clean_snapshot_key(clean_path)
        has_baseline = bak_candidate.is_file() or load_profile_snapshot(f"baseline::{clean_key}") is not None

        if has_baseline:
            benchmark_output = run_pipeline_benchmark(
                baseline_file_path=f"{clean_path}.bak",
                candidate_file_path=clean_path,
            )
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

