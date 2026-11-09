"""Gerenciador de Planos de Execução isolado por sessão e sincronizado com o session.state do ADK."""
from contextvars import ContextVar
from datetime import datetime
import threading
import uuid
from typing import Any

from kraken_copilot.schemas.plan import (
    VALID_SPECIALIST_AGENTS,
    ExecutionPlan,
    PlanStep,
    StepAttempt,
    StepStatus,
    WorkflowSessionState,
)

# ContextVars para vincular automaticamente a sessão ativa do Google ADK às chamadas de ferramentas
current_session_id_var: ContextVar[str] = ContextVar("kraken_current_session_id", default="default")
current_session_state_var: ContextVar[dict[str, Any] | None] = ContextVar("kraken_current_session_state", default=None)
current_user_request_var: ContextVar[str] = ContextVar("kraken_current_user_request", default="")


class PlanValidationError(ValueError):
    """Exceção lançada quando um plano contém dependências inválidas, agentes desconhecidos, critérios vazios ou ciclos."""


def _validate_and_compute_waves(steps: list[PlanStep]) -> list[list[str]]:
    """
    Valida integridade estrutural das etapas (IDs únicos, especialistas permitidos, critérios de sucesso definidos,
    dependências existentes e ausência de ciclos) e retorna as ondas topológicas (`parallel_groups`) via algoritmo de Kahn.
    """
    if not steps:
        return []

    step_map: dict[str, PlanStep] = {}
    for s in steps:
        if not s.step_id or not s.step_id.strip():
            raise PlanValidationError("Todas as etapas devem possuir um 'step_id' não vazio.")
        if s.step_id in step_map:
            raise PlanValidationError(f"ID de etapa duplicado detectado no plano: '{s.step_id}'.")
        if s.agent not in VALID_SPECIALIST_AGENTS:
            valid_list = ", ".join(sorted(VALID_SPECIALIST_AGENTS))
            raise PlanValidationError(
                f"Agente inválido '{s.agent}' na etapa '{s.step_id}'. Especialistas permitidos: {valid_list}."
            )
        if not s.success_criteria or not s.success_criteria.strip():
            raise PlanValidationError(
                f"A etapa '{s.step_id}' deve possuir 'success_criteria' definido e não vazio."
            )
        step_map[s.step_id] = s

    # Verifica existência de dependências e auto-referência
    in_degree: dict[str, int] = {s.step_id: 0 for s in steps}
    dependents: dict[str, list[str]] = {s.step_id: [] for s in steps}

    for s in steps:
        seen_deps: set[str] = set()
        for dep in s.dependencies:
            if dep == s.step_id:
                raise PlanValidationError(f"A etapa '{s.step_id}' não pode depender de si mesma.")
            if dep not in step_map:
                raise PlanValidationError(
                    f"A etapa '{s.step_id}' referencia uma dependência inexistente: '{dep}'."
                )
            if dep not in seen_deps:
                seen_deps.add(dep)
                in_degree[s.step_id] += 1
                dependents[dep].append(s.step_id)

    # Ordenação topológica em ondas (Kahn) para detectar ciclos e agrupar etapas paralelizáveis
    waves: list[list[str]] = []
    ready_queue = [s.step_id for s in steps if in_degree[s.step_id] == 0]
    visited_count = 0

    while ready_queue:
        current_wave = list(ready_queue)
        waves.append(current_wave)
        next_queue: list[str] = []
        for u in current_wave:
            visited_count += 1
            for v in dependents[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    next_queue.append(v)
        ready_queue = next_queue

    if visited_count != len(steps):
        cycle_nodes = [sid for sid, deg in in_degree.items() if deg > 0]
        raise PlanValidationError(
            f"Ciclo de dependência detectado no plano entre as etapas: {cycle_nodes}."
        )

    return waves


def validate_execution_plan(plan: ExecutionPlan) -> ExecutionPlan:
    """
    Valida integralmente o contrato de um `ExecutionPlan`:
    - Objetivo e critérios de sucesso definidos no plano e nas etapas.
    - Existência de especialistas permitidos.
    - Identificadores únicos das etapas.
    - Integridade das dependências e ausência de ciclos.
    - Consistência dos grupos de execução paralela (`parallel_groups`).
    """
    if not plan.objective or not plan.objective.strip():
        raise PlanValidationError("O plano deve possuir um 'objective' definido e não vazio.")
    if not plan.success_criteria or not plan.success_criteria.strip():
        raise PlanValidationError("O plano deve possuir 'success_criteria' definido e não vazio.")
    if not plan.steps:
        raise PlanValidationError("O plano deve conter pelo menos uma etapa ('steps').")

    expected_waves = _validate_and_compute_waves(plan.steps)

    if not plan.parallel_groups:
        plan.parallel_groups = expected_waves
        return plan

    step_by_id = {s.step_id: s for s in plan.steps}
    seen_in_groups: set[str] = set()

    for wave_idx, group in enumerate(plan.parallel_groups):
        if not group:
            raise PlanValidationError(f"Grupo paralelo vazio encontrado no índice {wave_idx}.")
        group_set = set(group)
        for sid in group:
            if sid not in step_by_id:
                raise PlanValidationError(
                    f"Grupo paralelo referencia etapa inexistente '{sid}'."
                )
            if sid in seen_in_groups:
                raise PlanValidationError(
                    f"Etapa '{sid}' duplicada em múltiplos grupos de execução paralela."
                )
            step_obj = step_by_id[sid]
            for dep in step_obj.dependencies:
                if dep in group_set:
                    raise PlanValidationError(
                        f"Inconsistência em parallel_groups: a etapa '{sid}' depende de '{dep}' no mesmo grupo paralelo."
                    )
                if dep not in seen_in_groups:
                    raise PlanValidationError(
                        f"Inconsistência em parallel_groups: a etapa '{sid}' aparece antes de sua dependência '{dep}'."
                    )
        seen_in_groups.update(group_set)

    if seen_in_groups != set(step_by_id.keys()):
        missing = sorted(set(step_by_id.keys()) - seen_in_groups)
        raise PlanValidationError(
            f"Inconsistência em parallel_groups: etapas ausentes dos grupos paralelos: {missing}."
        )

    return plan


class PlanManager:
    """
    Gerenciador seguro para threads e isolado por sessão dos planos de execução do Kraken Copilot.

    Garante:
    - Ausência de deadlock em `replan()` utilizando `threading.RLock()`.
    - Imutabilidade externa retornando sempre `model_copy(deep=True)`.
    - Isolamento por `session_id` e sincronização com `session.state`.
    - Validação completa do DAG e do contrato `ExecutionPlan`.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._plans_by_session: dict[str, ExecutionPlan] = {}

    def _resolve_session_id(self, session_id: str | None = None) -> str:
        """Resolve o identificador de sessão explícito ou obtém da ContextVar ativa."""
        if session_id and str(session_id).strip():
            return str(session_id).strip()
        return current_session_id_var.get() or "default"

    def _sync_to_context_state(self, plan: ExecutionPlan | None, session_id: str) -> None:
        """Sincroniza de forma segura uma cópia imutável do plano no session.state do ADK, se ativo."""
        state = current_session_state_var.get()
        if not hasattr(state, "get") or not hasattr(state, "__setitem__"):
            return
        state_session = state.get("session_id")
        if state_session and state_session != session_id:
            return
        if plan is None:
            state.pop("execution_plan", None)
            if isinstance(state.get("workflow_state"), dict):
                state["workflow_state"]["active_plan"] = None
            return

        plan_dump = plan.model_dump()
        state["execution_plan"] = plan_dump
        wf_state = state.get("workflow_state")
        if isinstance(wf_state, dict):
            wf_state["active_plan"] = plan_dump
        else:
            wf_obj = WorkflowSessionState(
                session_id=session_id,
                original_request=plan.objective,
                active_plan=plan.model_copy(deep=True),
            )
            state["workflow_state"] = wf_obj.model_dump()

    def load_from_session_state(self, session_id: str, state: Any | None) -> ExecutionPlan | None:
        """Hidrata o plano a partir do `session.state` do ADK caso ainda não esteja no cache da sessão."""
        if not hasattr(state, "get"):
            return self.get_plan(session_id=session_id)
        with self._lock:
            raw_plan = state.get("execution_plan")
            if isinstance(raw_plan, dict) and raw_plan.get("plan_id"):
                try:
                    hydrated = ExecutionPlan.model_validate(raw_plan)
                    hydrated.session_id = session_id
                    self._plans_by_session[session_id] = hydrated
                    return hydrated.model_copy(deep=True)
                except Exception:
                    pass
            return self.get_plan(session_id=session_id)

    def _build_step(self, idx: int, raw_step: dict[str, Any]) -> PlanStep:
        """Constrói e normaliza um objeto PlanStep a partir de um dicionário de entrada."""
        raw_id = str(raw_step.get("step_id") or idx).strip()
        agent = str(raw_step.get("agent", "")).strip().lower()
        deps = [str(d).strip() for d in raw_step.get("dependencies", []) if str(d).strip()]
        default_validation = agent in ("kraken_code", "kraken_optimizer")
        requires_val = bool(raw_step.get("requires_validation", default_validation))
        max_retries = int(raw_step.get("max_retries", 2 if requires_val else 1))
        max_retries = max(1, min(max_retries, 5))

        raw_criteria = raw_step.get("success_criteria")
        if raw_criteria is None:
            criteria = "Execução concluída pelo especialista sem erros e dentro dos guardrails."
        else:
            criteria = str(raw_criteria).strip()

        return PlanStep(
            step_id=raw_id,
            title=str(raw_step.get("title", f"Etapa {raw_id}")).strip(),
            agent=agent,
            description=str(raw_step.get("description", "")).strip(),
            dependencies=deps,
            success_criteria=criteria,
            status=StepStatus.PENDING,
            result_summary=raw_step.get("result_summary"),
            output_key=str(raw_step.get("output_key") or f"step_result_{raw_id}"),
            requires_validation=requires_val,
            max_retries=max_retries,
        )

    def create_plan(
        self,
        objective: str,
        steps: list[dict[str, Any]],
        success_criteria: str,
        session_id: str | None = None,
    ) -> ExecutionPlan:
        """Cria, valida o DAG de dependências e registra um novo plano isolado para a sessão."""
        resolved_session = self._resolve_session_id(session_id)
        with self._lock:
            plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
            parsed_steps = [self._build_step(idx, raw) for idx, raw in enumerate(steps, start=1)]
            waves = _validate_and_compute_waves(parsed_steps)

            first_ready_id = waves[0][0] if waves and waves[0] else (parsed_steps[0].step_id if parsed_steps else None)
            plan = ExecutionPlan(
                plan_id=plan_id,
                session_id=resolved_session,
                objective=objective.strip(),
                steps=parsed_steps,
                success_criteria=success_criteria.strip(),
                status="in_progress" if parsed_steps else "created",
                current_step_id=first_ready_id,
                revision=1,
                parallel_groups=waves,
            )
            validate_execution_plan(plan)
            self._plans_by_session[resolved_session] = plan
            self._sync_to_context_state(plan, resolved_session)
            return plan.model_copy(deep=True)

    def get_plan(self, session_id: str | None = None) -> ExecutionPlan | None:
        """Retorna uma cópia profunda (imutável para o chamador) do plano ativo da sessão."""
        resolved_session = self._resolve_session_id(session_id)
        with self._lock:
            plan = self._plans_by_session.get(resolved_session)
            if plan is None:
                return None
            return plan.model_copy(deep=True)

    def get_ready_steps(self, session_id: str | None = None) -> list[PlanStep]:
        """
        Retorna cópias profundas de todas as etapas `PENDING` cujas dependências estão `COMPLETED`.
        Se uma dependência estiver `FAILED` ou `SKIPPED`, a etapa dependente NÃO é considerada elegível.
        """
        resolved_session = self._resolve_session_id(session_id)
        with self._lock:
            plan = self._plans_by_session.get(resolved_session)
            if not plan:
                return []

            completed_ids = {s.step_id for s in plan.steps if s.status == StepStatus.COMPLETED}
            ready: list[PlanStep] = []
            for s in plan.steps:
                if s.status == StepStatus.PENDING and all(dep in completed_ids for dep in s.dependencies):
                    ready.append(s.model_copy(deep=True))
            return ready

    def record_step_attempt(
        self,
        step_id: str,
        status: str,
        summary: str,
        error: str | None = None,
        awaiting_user_confirmation: bool = False,
        session_id: str | None = None,
    ) -> PlanStep | None:
        """Registra uma tentativa de execução/validação no histórico da etapa e atualiza contadores."""
        resolved_session = self._resolve_session_id(session_id)
        with self._lock:
            plan = self._plans_by_session.get(resolved_session)
            if not plan:
                return None
            for s in plan.steps:
                if s.step_id == str(step_id):
                    s.attempt_count += 1
                    s.awaiting_user_confirmation = awaiting_user_confirmation
                    s.attempt_history.append(
                        StepAttempt(
                            attempt=s.attempt_count,
                            status=status,
                            summary=summary[:500] if summary else "",
                            error=error,
                        )
                    )
                    if summary:
                        s.result_summary = summary.strip()
                    self._sync_to_context_state(plan, resolved_session)
                    return s.model_copy(deep=True)
            return None

    def update_step(
        self,
        step_id: str,
        status: str,
        result_summary: str = "",
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Atualiza o status de uma etapa individual e recalcula o estado geral e próximas etapas elegíveis.
        Impede que uma etapa seja iniciada ou concluída caso alguma dependência não esteja concluída.
        """
        resolved_session = self._resolve_session_id(session_id)
        with self._lock:
            plan = self._plans_by_session.get(resolved_session)
            if not plan:
                return {"error": "Nenhum plano ativo encontrado na sessão atual. Crie um plano antes de atualizar etapas."}

            step_by_id = {s.step_id: s for s in plan.steps}
            target_step = step_by_id.get(str(step_id))

            if not target_step:
                return {"error": f"Etapa com ID '{step_id}' não encontrada no plano atual."}

            clean_status = status.strip().lower()
            try:
                new_status = StepStatus(clean_status)
            except ValueError:
                return {
                    "error": f"Status '{status}' inválido. Valores aceitos: pending, in_progress, completed, failed, skipped."
                }

            # Valida dependências antes de permitir IN_PROGRESS ou COMPLETED
            if new_status in (StepStatus.IN_PROGRESS, StepStatus.COMPLETED):
                unmet_deps = [
                    dep
                    for dep in target_step.dependencies
                    if step_by_id.get(dep) is None or step_by_id[dep].status != StepStatus.COMPLETED
                ]
                if unmet_deps:
                    return {
                        "error": (
                            f"Não é possível alterar a etapa '{step_id}' para '{new_status.value}' "
                            f"porque as dependências {unmet_deps} ainda não foram concluídas."
                        )
                    }

            target_step.status = new_status
            if result_summary:
                target_step.result_summary = result_summary.strip()

            completed_ids = {s.step_id for s in plan.steps if s.status == StepStatus.COMPLETED}
            ready_steps = [
                s
                for s in plan.steps
                if s.status == StepStatus.PENDING and all(dep in completed_ids for dep in s.dependencies)
            ]
            next_step = ready_steps[0] if ready_steps else None

            all_done = all(s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED) for s in plan.steps)
            has_failed = any(s.status == StepStatus.FAILED for s in plan.steps)
            awaiting_approval = any(s.awaiting_user_confirmation for s in plan.steps)

            if has_failed and not ready_steps:
                plan.status = "failed"
                plan.current_step_id = None
            elif all_done:
                plan.status = "awaiting_approval" if awaiting_approval else "completed"
                plan.current_step_id = None
            else:
                plan.status = "in_progress"
                plan.current_step_id = next_step.step_id if next_step else None

            self._sync_to_context_state(plan, resolved_session)

            return {
                "plan_id": plan.plan_id,
                "session_id": resolved_session,
                "updated_step_id": step_id,
                "step_status": target_step.status.value,
                "plan_status": plan.status,
                "next_step_id": next_step.step_id if next_step else None,
                "next_agent": next_step.agent if next_step else None,
                "next_description": next_step.description if next_step else None,
                "ready_step_ids": [s.step_id for s in ready_steps],
                "markdown": self.format_plan_markdown(plan),
            }

    def replan(
        self,
        reason: str,
        failed_step_id: str = "",
        revised_steps: list[dict[str, Any]] | None = None,
        session_id: str | None = None,
    ) -> ExecutionPlan:
        """
        Replaneja o fluxo de execução sem deadlock (usa RLock), mantendo etapas `COMPLETED`,
        reavaliando dependências das etapas restantes, validando o novo DAG e retornando cópia profunda.
        """
        resolved_session = self._resolve_session_id(session_id)
        with self._lock:
            plan = self._plans_by_session.get(resolved_session)
            if not plan:
                self.create_plan(
                    objective=f"Plano adaptado: {reason}",
                    steps=revised_steps or [],
                    success_criteria="Executar etapas replanejadas com sucesso.",
                    session_id=resolved_session,
                )
                internal_plan = self._plans_by_session[resolved_session]
                internal_plan.revision = 2
                internal_plan.replan_reason = reason.strip()
                internal_plan.status = "replanned"
                self._sync_to_context_state(internal_plan, resolved_session)
                return internal_plan.model_copy(deep=True)

            # Preserva cópias das etapas já concluídas
            completed_steps = [s.model_copy(deep=True) for s in plan.steps if s.status == StepStatus.COMPLETED]
            completed_ids = {s.step_id for s in completed_steps}

            candidate_steps: list[PlanStep] = list(completed_steps)
            if revised_steps:
                for idx, raw_step in enumerate(revised_steps, start=len(completed_steps) + 1):
                    raw_id = str(raw_step.get("step_id") or idx).strip()
                    if raw_id in completed_ids:
                        continue  # Nunca sobrescreve nem repete etapas já concluídas
                    candidate_steps.append(self._build_step(idx, raw_step))
            else:
                # Se nenhuma nova lista foi passada, reabre as etapas não concluídas
                for s in plan.steps:
                    if s.step_id not in completed_ids:
                        reopened = s.model_copy(deep=True)
                        if failed_step_id and reopened.step_id == str(failed_step_id):
                            reopened.status = StepStatus.PENDING
                        elif reopened.status == StepStatus.FAILED:
                            reopened.status = StepStatus.PENDING
                        candidate_steps.append(reopened)

            # Reavalia dependências das etapas restantes caso a etapa falha tenha sido substituída por recuperação
            valid_candidate_ids = {s.step_id for s in candidate_steps}
            clean_failed_id = str(failed_step_id).strip()
            replacement_id = f"{clean_failed_id}_recovery" if f"{clean_failed_id}_recovery" in valid_candidate_ids else None

            if clean_failed_id and clean_failed_id not in valid_candidate_ids:
                for s in candidate_steps:
                    if s.step_id in completed_ids:
                        continue
                    updated_deps: list[str] = []
                    for dep in s.dependencies:
                        if dep == clean_failed_id:
                            if replacement_id and replacement_id != s.step_id and replacement_id not in updated_deps:
                                updated_deps.append(replacement_id)
                        elif dep not in updated_deps:
                            updated_deps.append(dep)
                    s.dependencies = updated_deps

            waves = _validate_and_compute_waves(candidate_steps)

            plan.steps = candidate_steps
            plan.revision += 1
            plan.replan_reason = reason.strip()
            plan.status = "replanned"
            plan.parallel_groups = waves
            validate_execution_plan(plan)

            next_step: PlanStep | None = None
            for s in plan.steps:
                if s.status == StepStatus.PENDING and all(dep in completed_ids for dep in s.dependencies):
                    next_step = s
                    break

            plan.current_step_id = next_step.step_id if next_step else None
            self._sync_to_context_state(plan, resolved_session)
            return plan.model_copy(deep=True)

    def reset_plan(self, session_id: str | None = None, clear_all: bool = False) -> None:
        """Limpa o plano ativo da sessão especificada (ou todas as sessões quando `clear_all=True`)."""
        with self._lock:
            if clear_all or session_id is None:
                self._plans_by_session.clear()
                resolved = self._resolve_session_id(None)
                self._sync_to_context_state(None, resolved)
            else:
                resolved = self._resolve_session_id(session_id)
                self._plans_by_session.pop(resolved, None)
                self._sync_to_context_state(None, resolved)

    def format_plan_markdown(self, plan: ExecutionPlan) -> str:
        """Gera uma visualização tabular e estruturada do plano em Markdown."""
        status_badges = {
            StepStatus.PENDING: "⏳ Pendente",
            StepStatus.IN_PROGRESS: "▶ Em Andamento",
            StepStatus.COMPLETED: "✓ Concluída",
            StepStatus.FAILED: "✗ Falhou",
            StepStatus.SKIPPED: "⊘ Pulada",
        }

        agent_labels = {
            "kraken_analyst": "📊 Kraken Analyst",
            "kraken_code": "🔬 Kraken Code",
            "kraken_optimizer": "⚙️ Kraken Optimizer",
        }

        lines = [
            f"### 🗺️ Plano de Execução Estruturado (v{plan.revision})",
            f"**Objetivo**: {plan.objective}",
            f"**Critérios de Sucesso**: {plan.success_criteria}",
            f"**Status Geral**: `{plan.status.upper()}`",
        ]

        if plan.replan_reason:
            lines.append(f"> ⚠️ **Motivo do Replanejamento**: {plan.replan_reason}")

        lines.append("")
        lines.append("| Etapa | Título | Especialista | Dependências | Status | Resumo / Evidência |")
        lines.append("|:---:|:---|:---|:---:|:---:|:---|")

        for s in plan.steps:
            badge = status_badges.get(s.status, s.status.value)
            agent_label = agent_labels.get(s.agent, s.agent)
            deps = ", ".join(s.dependencies) if s.dependencies else "-"
            summary = (s.result_summary or "-").replace("\n", " ")
            if len(summary) > 80:
                summary = summary[:77] + "..."
            lines.append(f"| `{s.step_id}` | {s.title} | {agent_label} | {deps} | {badge} | {summary} |")

        if plan.current_step_id:
            lines.append(f"\n👉 **Próxima ação**: Executar Etapa `{plan.current_step_id}`.")

        return "\n".join(lines)


# Instância global singleton do gerenciador de planos (isolada internamente por session_id)
global_plan_manager = PlanManager()
