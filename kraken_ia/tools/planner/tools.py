"""Ferramentas públicas oficiais expostas exclusivamente ao Kraken Planner."""
from typing import Any

from kraken_ia.tools.planner.plan_manager import global_plan_manager


def create_execution_plan(
    objective: str,
    steps: list[dict[str, Any]],
    success_criteria: str,
) -> dict[str, Any]:
    """Cria um plano de execução estruturado decompondo uma solicitação complexa em etapas sequenciais entre especialistas.

    Args:
        objective: Objetivo central e claro a ser atingido com a execução do plano.
        steps: Lista de dicionários representando as etapas planejadas. Cada etapa deve conter:
            - 'step_id': identificador único sequencial (ex: '1', '2', '3')
            - 'title': título descritivo da etapa
            - 'agent': agente especialista ('kraken_analyst', 'kraken_code' ou 'kraken_optimizer')
            - 'description': instruções precisas do que deve ser executado pelo especialista
            - 'dependencies': lista de IDs das etapas precedentes obrigatórias (ex: ['1'])
        success_criteria: Critérios mensuráveis e objetivos para validar a conclusão do plano.

    Returns:
        Dicionário com o plano formatado em Markdown, status e detalhes operacionais.
    """
    if not objective or not objective.strip():
        return {"error": "O campo 'objective' é obrigatório para criar um plano de execução."}
    if not steps or not isinstance(steps, list):
        return {"error": "O campo 'steps' deve conter uma lista não vazia de etapas a serem executadas."}
    if not success_criteria or not success_criteria.strip():
        return {"error": "O campo 'success_criteria' é obrigatório para definir os critérios de conclusão."}

    plan = global_plan_manager.create_plan(
        objective=objective,
        steps=steps,
        success_criteria=success_criteria,
    )

    return {
        "status": "success",
        "plan_id": plan.plan_id,
        "revision": plan.revision,
        "total_steps": len(plan.steps),
        "current_step_id": plan.current_step_id,
        "markdown": global_plan_manager.format_plan_markdown(plan),
    }


def get_plan_status() -> dict[str, Any]:
    """Consulta o estado atual do plano de execução em andamento, etapas concluídas e próximas ações.

    Returns:
        Dicionário com a visualização atual do plano, etapa corrente e indicação do próximo especialista.
    """
    plan = global_plan_manager.get_plan()
    if not plan:
        return {
            "status": "empty",
            "message": "Nenhum plano ativo no momento. Use 'create_execution_plan' para planejar uma solicitação complexa.",
        }

    return {
        "status": "success",
        "plan_id": plan.plan_id,
        "plan_status": plan.status,
        "current_step_id": plan.current_step_id,
        "revision": plan.revision,
        "markdown": global_plan_manager.format_plan_markdown(plan),
    }


def update_plan_step(
    step_id: str,
    status: str,
    result_summary: str = "",
) -> dict[str, Any]:
    """Atualiza o status de uma etapa individual do plano após a execução pelo especialista e avalia dependências.

    Args:
        step_id: Identificador da etapa que está sendo atualizada (ex: '1', '2').
        status: Novo status da etapa ('in_progress', 'completed', 'failed', 'skipped').
        result_summary: Resumo objetivo dos resultados obtidos, métricas observadas ou motivo da falha.

    Returns:
        Dicionário com o status atualizado do plano, próxima etapa elegível e visualização Markdown.
    """
    if not step_id:
        return {"error": "O campo 'step_id' é obrigatório."}
    if not status:
        return {"error": "O campo 'status' é obrigatório ('in_progress', 'completed', 'failed', 'skipped')."}

    result = global_plan_manager.update_step(
        step_id=step_id,
        status=status,
        result_summary=result_summary,
    )
    return result


def replan_execution(
    reason: str,
    failed_step_id: str = "",
    revised_steps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Replaneja o fluxo de execução quando uma etapa falha, encontra dados inesperados ou necessita de ajuste de rota.

    Args:
        reason: Justificativa clara do motivo do replanejamento (ex: 'colunas ausentes', 'falha no teste do pipeline').
        failed_step_id: ID da etapa que falhou ou motivou o ajuste (opcional).
        revised_steps: Nova lista de etapas pendentes revisadas para substituir as anteriores não concluídas (opcional).

    Returns:
        Dicionário com o plano revisado em Markdown, nova revisão e próxima etapa.
    """
    if not reason or not reason.strip():
        return {"error": "O campo 'reason' é obrigatório para registrar a causa do replanejamento."}

    plan = global_plan_manager.replan(
        reason=reason,
        failed_step_id=failed_step_id,
        revised_steps=revised_steps,
    )

    return {
        "status": "replanned",
        "plan_id": plan.plan_id,
        "revision": plan.revision,
        "replan_reason": plan.replan_reason,
        "current_step_id": plan.current_step_id,
        "markdown": global_plan_manager.format_plan_markdown(plan),
    }
