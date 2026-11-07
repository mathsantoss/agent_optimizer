"""Gerenciador de Planos de Execução em memória para o Kraken Planner."""
from datetime import datetime
import threading
import uuid
from typing import Any

from kraken_ia.schemas.plan import ExecutionPlan, PlanStep, StepStatus


class PlanManager:
    """Gerenciador em memória, seguro para threads, do plano de execução ativo."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active_plan: ExecutionPlan | None = None

    def create_plan(self, objective: str, steps: list[dict[str, Any]], success_criteria: str) -> ExecutionPlan:
        """Cria e valida um novo plano de execução estruturado."""
        with self._lock:
            plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
            parsed_steps: list[PlanStep] = []

            for idx, raw_step in enumerate(steps, start=1):
                raw_id = str(raw_step.get("step_id") or idx)
                agent = str(raw_step.get("agent", "")).strip().lower()
                deps = [str(d) for d in raw_step.get("dependencies", [])]

                parsed_steps.append(
                    PlanStep(
                        step_id=raw_id,
                        title=str(raw_step.get("title", f"Etapa {raw_id}")),
                        agent=agent,
                        description=str(raw_step.get("description", "")),
                        dependencies=deps,
                        status=StepStatus.PENDING,
                        result_summary=raw_step.get("result_summary"),
                    )
                )

            plan = ExecutionPlan(
                plan_id=plan_id,
                objective=objective.strip(),
                steps=parsed_steps,
                success_criteria=success_criteria.strip(),
                status="in_progress" if parsed_steps else "created",
                current_step_id=parsed_steps[0].step_id if parsed_steps else None,
                revision=1,
            )
            self._active_plan = plan
            return plan

    def get_plan(self) -> ExecutionPlan | None:
        """Retorna o plano de execução ativo no momento."""
        with self._lock:
            return self._active_plan

    def update_step(self, step_id: str, status: str, result_summary: str = "") -> dict[str, Any]:
        """
        Atualiza o status de uma etapa individual e avalia as dependências das próximas etapas.
        """
        with self._lock:
            if not self._active_plan:
                return {"error": "Nenhum plano ativo encontrado. Crie um plano antes de atualizar etapas."}

            plan = self._active_plan
            target_step: PlanStep | None = None
            for s in plan.steps:
                if s.step_id == str(step_id):
                    target_step = s
                    break

            if not target_step:
                return {"error": f"Etapa com ID '{step_id}' não encontrada no plano atual."}

            clean_status = status.strip().lower()
            try:
                target_step.status = StepStatus(clean_status)
            except ValueError:
                return {"error": f"Status '{status}' inválido. Valores aceitos: pending, in_progress, completed, failed, skipped."}

            if result_summary:
                target_step.result_summary = result_summary.strip()

            # Encontra as etapas concluídas
            completed_ids = {s.step_id for s in plan.steps if s.status == StepStatus.COMPLETED}

            # Verifica o próximo passo elegível
            next_step: PlanStep | None = None
            all_done = True
            has_failed = False

            for s in plan.steps:
                if s.status == StepStatus.FAILED:
                    has_failed = True
                if s.status not in (StepStatus.COMPLETED, StepStatus.SKIPPED):
                    all_done = False
                    # Verifica se todas as dependências desta etapa já foram concluídas
                    if not next_step and all(dep in completed_ids for dep in s.dependencies):
                        next_step = s

            if all_done:
                plan.status = "completed"
                plan.current_step_id = None
            elif has_failed:
                plan.status = "failed"
            else:
                plan.status = "in_progress"
                plan.current_step_id = next_step.step_id if next_step else None

            return {
                "plan_id": plan.plan_id,
                "updated_step_id": step_id,
                "step_status": target_step.status.value,
                "plan_status": plan.status,
                "next_step_id": next_step.step_id if next_step else None,
                "next_agent": next_step.agent if next_step else None,
                "next_description": next_step.description if next_step else None,
                "markdown": self.format_plan_markdown(plan),
            }

    def replan(
        self,
        reason: str,
        failed_step_id: str = "",
        revised_steps: list[dict[str, Any]] | None = None,
    ) -> ExecutionPlan:
        """
        Replaneja o fluxo de execução mantendo o histórico de etapas concluídas e adaptando as pendentes.
        """
        with self._lock:
            if not self._active_plan:
                # Se não houver plano ativo, cria um novo a partir das etapas revisadas
                return self.create_plan(
                    objective=f"Plano adaptado: {reason}",
                    steps=revised_steps or [],
                    success_criteria="Executar etapas replanejadas com sucesso.",
                )

            plan = self._active_plan
            plan.revision += 1
            plan.replan_reason = reason.strip()
            plan.status = "replanned"

            # Se passos revisados foram fornecidos, mescla preservando passos já concluídos
            if revised_steps:
                completed_steps = [s for s in plan.steps if s.status == StepStatus.COMPLETED]
                new_steps: list[PlanStep] = list(completed_steps)

                completed_ids = {s.step_id for s in completed_steps}
                for idx, raw_step in enumerate(revised_steps, start=len(completed_steps) + 1):
                    raw_id = str(raw_step.get("step_id") or idx)
                    if raw_id in completed_ids:
                        continue  # Não sobrescreve etapas já executadas

                    agent = str(raw_step.get("agent", "")).strip().lower()
                    deps = [str(d) for d in raw_step.get("dependencies", [])]

                    new_steps.append(
                        PlanStep(
                            step_id=raw_id,
                            title=str(raw_step.get("title", f"Etapa {raw_id}")),
                            agent=agent,
                            description=str(raw_step.get("description", "")),
                            dependencies=deps,
                            status=StepStatus.PENDING,
                            result_summary=raw_step.get("result_summary"),
                        )
                    )
                plan.steps = new_steps

            # Atualiza o próximo passo elegível
            completed_ids = {s.step_id for s in plan.steps if s.status == StepStatus.COMPLETED}
            next_step: PlanStep | None = None
            for s in plan.steps:
                if s.status == StepStatus.PENDING and all(dep in completed_ids for dep in s.dependencies):
                    next_step = s
                    break

            plan.current_step_id = next_step.step_id if next_step else None
            return plan

    def reset_plan(self) -> None:
        """Limpa o plano ativo atual (usado para testes ou nova sessão)."""
        with self._lock:
            self._active_plan = None

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
            summary = s.result_summary or "-"
            # Limita tamanho para visualização tabular limpa
            if len(summary) > 60:
                summary = summary[:57] + "..."
            lines.append(f"| `{s.step_id}` | {s.title} | {agent_label} | {deps} | {badge} | {summary} |")

        if plan.current_step_id:
            lines.append(f"\n👉 **Próxima ação**: Executar Etapa `{plan.current_step_id}`.")

        return "\n".join(lines)


# Instância global singleton do gerenciador de planos
global_plan_manager = PlanManager()
