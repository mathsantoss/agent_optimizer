"""Ferramentas públicas oficiais expostas exclusivamente ao Kraken Planner."""
from typing import Any

from kraken_copilot.tools.planner.plan_manager import PlanValidationError, global_plan_manager


def create_execution_plan(
    objective: str,
    steps: list[dict[str, Any]],
    success_criteria: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Cria um plano de execução estruturado decompondo uma solicitação operacional em etapas com dependências.

    Args:
        objective: Objetivo central e claro a ser atingido com a execução do plano.
        steps: Lista de dicionários representando as etapas planejadas. Cada etapa deve conter:
            - 'step_id': identificador único sequencial (ex: '1', '2', '3')
            - 'title': título descritivo da etapa
            - 'agent': agente especialista ('kraken_analyst', 'kraken_code' ou 'kraken_optimizer')
            - 'description': instruções precisas do que deve ser executado pelo especialista
            - 'dependencies': lista de IDs das etapas precedentes obrigatórias (ex: ['1'])
            - 'success_criteria': critério mensurável de validação da etapa (opcional)
        success_criteria: Critérios mensuráveis e objetivos para validar a conclusão do plano.
        session_id: Identificador opcional da sessão (resolvido automaticamente quando omitido).

    Returns:
        Dicionário com o plano formatado em Markdown, ondas de paralelismo, status e detalhes operacionais.
    """
    if not objective or not objective.strip():
        return {"error": "O campo 'objective' é obrigatório para criar um plano de execução."}
    if not steps or not isinstance(steps, list):
        return {"error": "O campo 'steps' deve conter uma lista não vazia de etapas a serem executadas."}
    if not success_criteria or not success_criteria.strip():
        return {"error": "O campo 'success_criteria' é obrigatório para definir os critérios de conclusão."}

    try:
        plan = global_plan_manager.create_plan(
            objective=objective,
            steps=steps,
            success_criteria=success_criteria,
            session_id=session_id,
        )
    except PlanValidationError as exc:
        return {"status": "error", "error": str(exc)}

    return {
        "status": "success",
        "plan_id": plan.plan_id,
        "session_id": plan.session_id,
        "revision": plan.revision,
        "total_steps": len(plan.steps),
        "current_step_id": plan.current_step_id,
        "parallel_groups": plan.parallel_groups,
        "markdown": global_plan_manager.format_plan_markdown(plan),
    }


def get_plan_status(session_id: str | None = None) -> dict[str, Any]:
    """Consulta o estado atual do plano de execução em andamento na sessão, etapas concluídas e próximas ações.

    Args:
        session_id: Identificador opcional da sessão.

    Returns:
        Dicionário com a visualização atual do plano, etapa corrente e indicação das próximas etapas elegíveis.
    """
    plan = global_plan_manager.get_plan(session_id=session_id)
    if not plan:
        return {
            "status": "empty",
            "message": "Nenhum plano ativo no momento. Use 'create_execution_plan' para planejar a solicitação.",
        }

    ready_steps = global_plan_manager.get_ready_steps(session_id=session_id)
    return {
        "status": "success",
        "plan_id": plan.plan_id,
        "session_id": plan.session_id,
        "plan_status": plan.status,
        "current_step_id": plan.current_step_id,
        "ready_step_ids": [s.step_id for s in ready_steps],
        "revision": plan.revision,
        "markdown": global_plan_manager.format_plan_markdown(plan),
    }


def update_plan_step(
    step_id: str,
    status: str,
    result_summary: str = "",
    session_id: str | None = None,
) -> dict[str, Any]:
    """Atualiza o status de uma etapa individual do plano após a execução pelo especialista e avalia dependências.

    Args:
        step_id: Identificador da etapa que está sendo atualizada (ex: '1', '2').
        status: Novo status da etapa ('in_progress', 'completed', 'failed', 'skipped').
        result_summary: Resumo objetivo dos resultados obtidos, métricas observadas ou motivo da falha.
        session_id: Identificador opcional da sessão.

    Returns:
        Dicionário com o status atualizado do plano, próxima etapa elegível e visualização Markdown.
    """
    if not step_id:
        return {"error": "O campo 'step_id' é obrigatório."}
    if not status:
        return {"error": "O campo 'status' é obrigatório ('in_progress', 'completed', 'failed', 'skipped')."}

    return global_plan_manager.update_step(
        step_id=step_id,
        status=status,
        result_summary=result_summary,
        session_id=session_id,
    )


def replan_execution(
    reason: str,
    failed_step_id: str = "",
    revised_steps: list[dict[str, Any]] | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Replaneja o fluxo de execução quando uma etapa falha, encontra dados inesperados ou necessita de ajuste de rota.

    Args:
        reason: Justificativa clara do motivo do replanejamento (ex: 'colunas ausentes', 'falha no teste do pipeline').
        failed_step_id: ID da etapa que falhou ou motivou o ajuste (opcional).
        revised_steps: Nova lista de etapas pendentes revisadas para substituir as anteriores não concluídas (opcional).
        session_id: Identificador opcional da sessão.

    Returns:
        Dicionário com o plano revisado em Markdown, nova revisão e próxima etapa.
    """
    if not reason or not reason.strip():
        return {"error": "O campo 'reason' é obrigatório para registrar a causa do replanejamento."}

    try:
        plan = global_plan_manager.replan(
            reason=reason,
            failed_step_id=failed_step_id,
            revised_steps=revised_steps,
            session_id=session_id,
        )
    except PlanValidationError as exc:
        return {"status": "error", "error": str(exc)}

    return {
        "status": "replanned",
        "plan_id": plan.plan_id,
        "session_id": plan.session_id,
        "revision": plan.revision,
        "replan_reason": plan.replan_reason,
        "current_step_id": plan.current_step_id,
        "parallel_groups": plan.parallel_groups,
        "markdown": global_plan_manager.format_plan_markdown(plan),
    }
