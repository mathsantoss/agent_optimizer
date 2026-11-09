"""Kraken Planner — Planejador Híbrido do Kraken IA.

Combina lógica determinística em Python com chamadas ao LLM sob demanda:
- Planejamento determinístico (Python): utilizado quando a intenção da solicitação é clara,
  o fluxo é conhecido e a seleção de especialistas pode ser feita por regras confiáveis.
- Planejamento com LLM: acionado apenas quando há ambiguidade relevante, objetivos complexos
  não previstos nas regras, dependências condicionais/contextuais ou quando a classificação
  determinística não identifica um plano confiável.

Independentemente da estratégia utilizada, o Planner sempre produz e valida o mesmo contrato
`ExecutionPlan` antes de entregá-lo ao `KrakenCoordinatorAgent`.
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable, Literal

from kraken_ia.config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL
from kraken_ia.prompts.planner import PLANNER_AGENT_INSTRUCTION
from kraken_ia.schemas.plan import (
    ExecutionPlan,
    PlanStep,
    StepStatus,
)
from kraken_ia.tools.planner import (
    create_execution_plan,
    get_plan_status,
    replan_execution,
    update_plan_step,
)
from kraken_ia.tools.planner.plan_manager import (
    PlanManager,
    PlanValidationError,
    current_session_id_var,
    global_plan_manager,
    validate_execution_plan,
)

ANALYSIS_KEYWORDS: tuple[str, ...] = (
    "quais dados",
    "dados temos",
    "dados tem",
    "dados de vendas",
    "dados de venda",
    "dados_vendas",
    "dados processados",
    "dados_processados",
    "analis",
    "análise",
    "explorar",
    "explore",
    "estatístic",
    "estatistic",
    "estastisc",
    "estatisc",
    "sumário",
    "sumario",
    "resumo",
    "descrever",
    "descreva",
    "visão geral",
    "visao geral",
    "qualidade",
    "sql",
    "query",
    "select",
    "consulta",
    "dicionário",
    "dicionario",
    "resumo dos dados",
    "estrutura dos dados",
    "dataset",
    "tabela",
    "coluna",
    "nulo",
)

CODE_CREATION_KEYWORDS: tuple[str, ...] = (
    "crie um pipeline",
    "criar um pipeline",
    "crie pipeline",
    "criar pipeline",
    "gere um pipeline",
    "gerar pipeline",
    "construa um pipeline",
    "nova feature",
    "novas features",
    "crie feature",
    "criar feature",
    "adicione feature",
    "adicionar feature",
    "inclua feature",
    "implemente a feature",
    "implementar feature",
    "implemente feature",
    "implemente",
    "implementar",
    "engenharia de feature",
    "feature engineering",
    "feature store",
    "feature",
    "features",
    "nova coluna",
    "novas colunas",
    "criar coluna",
    "adicionar coluna",
    "variável",
    "variavel",
    "variáveis",
    "variaveis",
)

OPTIMIZER_KEYWORDS: tuple[str, ...] = (
    "otimiz",
    "benchmark",
    "gargalo",
    "performance",
    "aceler",
    "refator",
    "inspecione o pipeline",
    "inspecionar pipeline",
    "valide o pipeline",
    "validar pipeline",
    "aplicar",
    "aplique",
    "confirmar",
    "confirmo",
    "aprovo",
    "pode salvar",
    "pode aplicar",
    "sim, aplicar",
    "sim aplicar",
    "efetivar",
    "gravar",
)

SEQUENTIAL_CONNECTORS: tuple[str, ...] = (
    "depois",
    "em seguida",
    "após",
    "apos",
    "então",
    "entao",
    "sequencialmente",
    "primeiro",
    "segundo",
)

# Sinais de ambiguidade, condicionalidade contextual ou investigação complexa que justificam uso do LLM
AMBIGUITY_OR_COMPLEXITY_MARKERS: tuple[str, ...] = (
    "se houver",
    "se encontrar",
    "caso encontre",
    "caso haja",
    "caso contrário",
    "caso contrario",
    "dependendo d",
    "conforme o resultado",
    "se necessário",
    "se for necessário",
    "não sei por onde",
    "nao sei por onde",
    "qual a melhor abordagem",
    "descubra a causa raiz",
    "investigue a causa",
    "por que o modelo",
    "estruture uma estratégia",
    "estruture uma estrategia",
    "avalie diferentes alternativas",
    "compare abordagens",
)

REPLAN_SEMANTIC_MARKERS: tuple[str, ...] = (
    "target proxy",
    "proxy",
    "mudança de contexto",
    "mudanca de contexto",
    "nova regra de negócio",
    "nova regra de negocio",
    "ambiguidade",
    "reinterpretar",
    "redesenhar",
)


class KrakenPlanner:
    """
    Planejador Híbrido do Kraken IA (`kraken_planner`).

    Responsabilidades:
    - Interpretar o objetivo da solicitação e classificar sinais operacionais.
    - Decidir entre planejamento determinístico (Python) e planejamento com LLM.
    - Decompor solicitações em etapas (`PlanStep`) com dependências e ondas paralelas (`parallel_groups`).
    - Validar integralmente o contrato `ExecutionPlan` antes de entregá-lo ao `KrakenCoordinatorAgent`.
    - Realizar replanejamento (`replan`) preservando etapas concluídas e reavaliando dependências.
    """

    def __init__(
        self,
        model: Any = None,
        plan_manager: PlanManager | None = None,
        llm_callable: Callable[[str, str], str] | None = None,
    ) -> None:
        self.name = "kraken_planner"
        self.description = (
            "Kraken Planner — Planejador híbrido responsável por interpretar solicitações operacionais, "
            "elaborar planos estruturados (ExecutionPlan) via regras determinísticas em Python ou LLM sob demanda, "
            "validar dependências/paralelismo e apoiar o replanejamento."
        )
        self.model = model
        self.plan_manager = plan_manager or global_plan_manager
        self.llm_callable = llm_callable
        self.tools = [
            create_execution_plan,
            get_plan_status,
            update_plan_step,
            replan_execution,
        ]

    def classify_request(
        self,
        user_text: str,
        state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Realiza a classificação inicial da solicitação utilizando regras Python.
        Identifica especialistas candidatos, conectores sequenciais e sinais de ambiguidade/complexidade.
        """
        text = (user_text or "").strip()
        lower = text.lower()

        has_analysis = any(kw in lower for kw in ANALYSIS_KEYWORDS)
        has_code_keywords = any(kw in lower for kw in CODE_CREATION_KEYWORDS)
        has_optimizer = any(kw in lower for kw in OPTIMIZER_KEYWORDS)

        # Se houver aprovação pendente na sessão ou confirmação explícita do usuário
        if hasattr(state, "get"):
            wf = state.get("workflow_state")
            awaiting = bool(state.get("awaiting_user_approval")) or (
                hasattr(wf, "get") and bool(wf.get("awaiting_user_approval"))
            )
            if awaiting and any(w in lower for w in ("sim", "confirm", "aplicar", "aplique", "autorizo", "ok", "pode")):
                has_optimizer = True

        has_code_verbs = any(
            v in lower
            for v in (
                "crie",
                "criar",
                "gere",
                "gerar",
                "constru",
                "adicion",
                "inclua",
                "implement",
                "calcule",
                "calcular",
                "programe",
                "programar",
            )
        )
        has_code = has_code_keywords and (
            has_code_verbs
            or any(k in lower for k in ("pipeline", "engenharia", "feature store", "nova feature", "novas features"))
            or ("feature" in lower and not any(a in lower for a in ("quais", "quantas", "listar")))
        )

        has_seq_connector = any(
            re.search(rf"\b{re.escape(conn)}\b", lower) for conn in SEQUENTIAL_CONNECTORS
        )
        has_ambiguity = any(marker in lower for marker in AMBIGUITY_OR_COMPLEXITY_MARKERS)

        matched_specialists: list[str] = []
        if has_analysis:
            matched_specialists.append("kraken_analyst")
        if has_code:
            matched_specialists.append("kraken_code")
        if has_optimizer:
            matched_specialists.append("kraken_optimizer")

        return {
            "text": text,
            "has_analysis": has_analysis,
            "has_code": has_code,
            "has_optimizer": has_optimizer,
            "has_sequential_connector": has_seq_connector,
            "has_ambiguity_or_complexity": has_ambiguity,
            "matched_specialists": matched_specialists,
        }

    def decide_strategy(
        self,
        user_text: str,
        state: dict[str, Any] | None = None,
    ) -> Literal["deterministic", "llm"]:
        """
        Decide se o planejamento determinístico em Python é suficiente ou se uma chamada ao LLM é necessária.

        Retorna `'deterministic'` quando:
        - A intenção é clara, os especialistas são identificados por regras confiáveis e não há ambiguidade.
        - Ou quando `deterministic_mode` está ativo na sessão (salvo se `force_llm_planning` estiver ativo).

        Retorna `'llm'` quando:
        - A solicitação apresenta ambiguidade relevante ou dependências condicionais/contextuais.
        - Nenhum especialista conhecido foi identificado pelas regras determinísticas.
        """
        if hasattr(state, "get"):
            if bool(state.get("force_llm_planning", False)):
                return "llm"
            if bool(state.get("deterministic_mode", False)):
                return "deterministic"

        signals = self.classify_request(user_text, state=state)
        has_llm_backend = self.llm_callable is not None or self.model is not None

        if not has_llm_backend:
            return "deterministic"

        # Aciona LLM quando nenhuma regra de especialista casa claramente ou há ambiguidade/complexidade contextual
        if not signals["matched_specialists"] or signals["has_ambiguity_or_complexity"]:
            return "llm"

        return "deterministic"

    def should_use_llm(
        self,
        user_text: str,
        state: dict[str, Any] | None = None,
    ) -> bool:
        """Retorna True somente quando o planejamento exigir chamada ao LLM."""
        return self.decide_strategy(user_text, state=state) == "llm"

    def validate_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        """
        Valida o `ExecutionPlan` contra todos os requisitos de contrato antes de entregá-lo ao Coordinator:
        - Existência de especialistas permitidos.
        - Identificadores únicos das etapas.
        - Integridade das dependências e ausência de ciclos.
        - Critérios de sucesso definidos.
        - Consistência dos grupos de execução paralela.
        """
        return validate_execution_plan(plan)

    def create_plan(
        self,
        user_text: str,
        session_id: str | None = None,
        state: dict[str, Any] | None = None,
        force_new: bool = False,
    ) -> ExecutionPlan:
        """
        Elabora, valida e registra um `ExecutionPlan` estruturado usando a abordagem híbrida:
        1. Classifica a solicitação em Python e decide a estratégia ('deterministic' vs 'llm').
        2. Constrói as etapas por regras Python ou via LLM sob demanda (com fallback seguro).
        3. Valida o contrato do `ExecutionPlan` e atualiza o estado compartilhado da sessão.
        """
        resolved_session = session_id or (
            str(state["session_id"]) if hasattr(state, "get") and state.get("session_id") else None
        ) or current_session_id_var.get() or "default"

        if not force_new:
            existing = self.plan_manager.get_plan(session_id=resolved_session)
            if existing and existing.status in ("created", "in_progress", "replanned") and existing.steps:
                validated_existing = self.validate_plan(existing)
                self._sync_planner_state(validated_existing, "deterministic", state)
                return validated_existing

        signals = self.classify_request(user_text, state=state)
        strategy: str = self.decide_strategy(user_text, state=state)

        plan: ExecutionPlan | None = None
        if strategy == "llm":
            try:
                objective, criteria, llm_steps = self._build_llm_steps(signals["text"])
                candidate_plan = self.plan_manager.create_plan(
                    objective=objective,
                    steps=llm_steps,
                    success_criteria=criteria,
                    session_id=resolved_session,
                )
                plan = self.validate_plan(candidate_plan)
            except Exception:
                strategy = "deterministic_fallback"
                plan = None

        if plan is None:
            objective, criteria, det_steps = self._build_deterministic_steps(signals["text"], signals=signals)
            created_plan = self.plan_manager.create_plan(
                objective=objective,
                steps=det_steps,
                success_criteria=criteria,
                session_id=resolved_session,
            )
            plan = self.validate_plan(created_plan)

        self._sync_planner_state(plan, strategy, state)
        return plan

    def replan(
        self,
        reason: str,
        failed_step: PlanStep | None = None,
        failed_step_id: str = "",
        revised_steps: list[dict[str, Any]] | None = None,
        session_id: str | None = None,
        state: dict[str, Any] | None = None,
    ) -> ExecutionPlan:
        """
        Atualiza o `ExecutionPlan` quando uma etapa falha ou o contexto da execução muda:
        - Preserva etapas `COMPLETED` que continuam válidas.
        - Reavalia dependências das etapas restantes para não repetir atividades concluídas.
        - Utiliza LLM somente quando a falha/mudança exigir nova interpretação semântica.
        - Registra o motivo da revisão, incrementa a revisão e valida o plano resultante.
        """
        resolved_session = session_id or (
            str(state["session_id"]) if hasattr(state, "get") and state.get("session_id") else None
        ) or current_session_id_var.get() or "default"

        current_plan = self.plan_manager.get_plan(session_id=resolved_session)
        target_failed_id = str(failed_step.step_id if failed_step is not None else failed_step_id).strip()

        if current_plan and failed_step is None and target_failed_id:
            for s in current_plan.steps:
                if s.step_id == target_failed_id:
                    failed_step = s
                    break

        effective_revised_steps = revised_steps
        if effective_revised_steps is None and current_plan is not None:
            completed_ids = {s.step_id for s in current_plan.steps if s.status == StepStatus.COMPLETED}
            if self._should_use_llm_for_replan(reason, failed_step, state):
                try:
                    effective_revised_steps = self._build_llm_replan_steps(
                        current_plan, reason, failed_step, completed_ids
                    )
                except Exception:
                    effective_revised_steps = None

            if effective_revised_steps is None and failed_step is not None:
                effective_revised_steps = self._build_recovery_steps(
                    current_plan, failed_step, completed_ids
                )

        replanned = self.plan_manager.replan(
            reason=reason,
            failed_step_id=target_failed_id,
            revised_steps=effective_revised_steps,
            session_id=resolved_session,
        )
        validated = self.validate_plan(replanned)
        self._sync_planner_state(validated, "replan", state)
        return validated

    def update_step(
        self,
        step_id: str,
        status: str,
        result_summary: str = "",
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Atualiza o status de uma etapa individual do plano mantendo a consistência das dependências."""
        return self.plan_manager.update_step(
            step_id=step_id,
            status=status,
            result_summary=result_summary,
            session_id=session_id,
        )

    def get_plan(self, session_id: str | None = None) -> ExecutionPlan | None:
        """Retorna o plano ativo da sessão especificada."""
        return self.plan_manager.get_plan(session_id=session_id)

    def format_plan_markdown(self, plan: ExecutionPlan) -> str:
        """Formata o `ExecutionPlan` em tabela Markdown estruturada."""
        return self.plan_manager.format_plan_markdown(plan)

    def _sync_planner_state(
        self,
        plan: ExecutionPlan,
        strategy: str,
        state: dict[str, Any] | None,
    ) -> None:
        """Sincroniza o plano validado e a estratégia utilizada no `session.state` compartilhado."""
        if not hasattr(state, "get") or not hasattr(state, "__setitem__"):
            return
        plan_dump = plan.model_dump()
        state["execution_plan"] = plan_dump
        wf = state.get("workflow_state")
        if isinstance(wf, dict):
            if strategy != "replan":
                wf["planning_strategy"] = strategy
            log = wf.setdefault("execution_log", [])
            strategy_tag = f"planner_strategy:{strategy}"
            if strategy != "replan" and strategy_tag not in log:
                log.append(strategy_tag)
            if "planner_completed" not in log:
                log.append("planner_completed")
            wf["active_plan"] = plan_dump

    def _build_deterministic_steps(
        self,
        user_text: str,
        signals: dict[str, Any] | None = None,
    ) -> tuple[str, str, list[dict[str, Any]]]:
        """
        Constrói `(objective, success_criteria, steps)` usando regras determinísticas em Python
        para os fluxos operacionais conhecidos do Kraken IA.
        """
        sig = signals or self.classify_request(user_text)
        text = sig["text"]
        has_analysis = sig["has_analysis"]
        has_code = sig["has_code"]
        has_optimizer = sig["has_optimizer"]
        has_seq_connector = sig["has_sequential_connector"]

        if not has_analysis and not has_code and not has_optimizer:
            has_analysis = True

        steps: list[dict[str, Any]] = []

        if has_analysis and has_optimizer and not has_code:
            # Sem conector sequencial estrito ("depois", "em seguida"), análise de dados e
            # diagnóstico/otimização do pipeline atuam sobre recursos distintos e rodam em paralelo.
            dep_for_opt = ["1"] if has_seq_connector else []
            steps = [
                {
                    "step_id": "1",
                    "title": "Análise Exploratória e Diagnóstico dos Dados",
                    "agent": "kraken_analyst",
                    "description": f"Explorar catálogo, estrutura e estatísticas dos datasets para atender: {text}",
                    "dependencies": [],
                    "success_criteria": "Catálogo e diagnóstico estrutural/estatístico dos dados gerados sem erros.",
                    "requires_validation": False,
                    "max_retries": 1,
                },
                {
                    "step_id": "2",
                    "title": "Inspeção AST, Otimização e Benchmark do Pipeline",
                    "agent": "kraken_optimizer",
                    "description": (
                        "Inspecionar pipeline/pipeline_prep.py, propor otimização vetorizada com benchmark comparativo "
                        "(Antes vs Depois) em pipeline/tmp/ e solicitar confirmação explícita do usuário antes de alterar o arquivo oficial."
                    ),
                    "dependencies": dep_for_opt,
                    "success_criteria": "Diagnóstico AST e proposta de otimização com benchmark validados sem sobrescrever pipeline oficial sem aprovação.",
                    "requires_validation": True,
                    "max_retries": 2,
                },
            ]
        elif has_code and has_optimizer:
            # Otimização SEMPRE depende da criação/atualização prévia do pipeline de features.
            step_idx = 1
            prev_dep: list[str] = []
            if has_analysis:
                steps.append(
                    {
                        "step_id": str(step_idx),
                        "title": "Exploração Estrutural do Dataset",
                        "agent": "kraken_analyst",
                        "description": f"Analisar colunas, tipos e qualidade do dataset para embasar as features: {text}",
                        "dependencies": [],
                        "success_criteria": "Estrutura do dataset validada.",
                        "requires_validation": False,
                        "max_retries": 1,
                    }
                )
                prev_dep = [str(step_idx)]
                step_idx += 1

            code_step_id = str(step_idx)
            steps.append(
                {
                    "step_id": code_step_id,
                    "title": "Engenharia de Features e Geração do Pipeline",
                    "agent": "kraken_code",
                    "description": (
                        f"Projetar e validar features solicitadas ({text}) com preview em amostra e proposta segura para pipeline/pipeline_prep.py."
                    ),
                    "dependencies": prev_dep,
                    "success_criteria": "Features projetadas e validadas sem erros de sintaxe ou data leakage.",
                    "requires_validation": True,
                    "max_retries": 2,
                }
            )
            step_idx += 1

            steps.append(
                {
                    "step_id": str(step_idx),
                    "title": "Otimização de Performance e Benchmark do Pipeline",
                    "agent": "kraken_optimizer",
                    "description": (
                        "Inspecionar o pipeline gerado, propor otimizações vetorizadas, executar benchmark comparativo "
                        "e aguardar aprovação explícita do usuário para escrita definitiva."
                    ),
                    "dependencies": [code_step_id],
                    "success_criteria": "Inspeção AST, validação e benchmark concluídos após a etapa de criação do pipeline.",
                    "requires_validation": True,
                    "max_retries": 2,
                }
            )
        elif has_analysis and has_code:
            steps = [
                {
                    "step_id": "1",
                    "title": "Análise Exploratória do Dataset",
                    "agent": "kraken_analyst",
                    "description": f"Examinar estrutura, colunas e estatísticas do dataset: {text}",
                    "dependencies": [],
                    "success_criteria": "Diagnóstico estrutural e estatístico concluído.",
                    "requires_validation": False,
                    "max_retries": 1,
                },
                {
                    "step_id": "2",
                    "title": "Criação de Features no Pipeline",
                    "agent": "kraken_code",
                    "description": f"Projetar e testar novas features com base na análise prévia: {text}",
                    "dependencies": ["1"],
                    "success_criteria": "Preview e proposta de pipeline gerados sem erros.",
                    "requires_validation": True,
                    "max_retries": 2,
                },
            ]
        elif has_optimizer:
            steps = [
                {
                    "step_id": "1",
                    "title": "Diagnóstico AST, Proposta de Otimização e Benchmark",
                    "agent": "kraken_optimizer",
                    "description": (
                        f"Executar inspeção estática e otimização segura de pipeline/pipeline_prep.py ({text}), "
                        "gerando benchmark comparativo Antes vs Depois e preservando exigência de confirmação explícita do usuário."
                    ),
                    "dependencies": [],
                    "success_criteria": "Relatório de inspeção e proposta de otimização com benchmark gerados com sucesso.",
                    "requires_validation": True,
                    "max_retries": 2,
                }
            ]
        elif has_code:
            steps = [
                {
                    "step_id": "1",
                    "title": "Projeto e Validação de Pipeline de Features",
                    "agent": "kraken_code",
                    "description": f"Projetar features e gerar proposta de pipeline para a solicitação: {text}",
                    "dependencies": [],
                    "success_criteria": "Código de features gerado e validado em amostra sem erros.",
                    "requires_validation": True,
                    "max_retries": 2,
                }
            ]
        else:
            steps = [
                {
                    "step_id": "1",
                    "title": "Análise e Consulta de Dados",
                    "agent": "kraken_analyst",
                    "description": f"Executar diagnóstico exploratório/estatístico dos datasets disponíveis para responder: {text}",
                    "dependencies": [],
                    "success_criteria": "Dados analisados com métricas reais e resposta fundamentada.",
                    "requires_validation": False,
                    "max_retries": 1,
                }
            ]

        objective = text or "Executar solicitação operacional no Kraken IA"
        success_criteria = "Todas as etapas planejadas concluídas e validadas respeitando dependências e guardrails."
        return objective, success_criteria, steps

    def _build_recovery_steps(
        self,
        plan: ExecutionPlan,
        failed_step: PlanStep,
        completed_ids: set[str],
    ) -> list[dict[str, Any]]:
        """
        Constrói as etapas de recuperação determinística preservando etapas concluídas
        e reavaliando as dependências das etapas pendentes restantes.
        """
        valid_deps = [d for d in failed_step.dependencies if d in completed_ids]
        recovery_id = f"{failed_step.step_id}_recovery"

        if failed_step.agent in ("kraken_optimizer", "kraken_code"):
            recovery_step = {
                "step_id": recovery_id,
                "title": f"Diagnóstico Alternativo e Recuperação ({failed_step.title})",
                "agent": "kraken_analyst" if failed_step.agent == "kraken_code" else "kraken_optimizer",
                "description": (
                    f"Etapa de recuperação após falha na etapa '{failed_step.step_id}': "
                    "executar diagnóstico seguro de estrutura e apresentar evidências sem risco ao pipeline."
                ),
                "dependencies": valid_deps,
                "success_criteria": "Diagnóstico alternativo executado com sucesso.",
                "requires_validation": True,
                "max_retries": 1,
            }
        else:
            recovery_step = {
                "step_id": recovery_id,
                "title": f"Consulta Alternativa ao Catálogo ({failed_step.title})",
                "agent": "kraken_analyst",
                "description": "Listar catálogo de datasets disponíveis e estrutura básica como rota de contingência.",
                "dependencies": valid_deps,
                "success_criteria": "Catálogo de datasets obtido com sucesso.",
                "requires_validation": False,
                "max_retries": 1,
            }

        revised: list[dict[str, Any]] = [recovery_step]

        # Preserva etapas pendentes posteriores reavaliando dependências que apontavam para a etapa falha
        for s in plan.steps:
            if s.step_id in completed_ids or s.step_id == failed_step.step_id:
                continue
            if s.status == StepStatus.PENDING:
                remapped_deps = [
                    recovery_id if dep == failed_step.step_id else dep
                    for dep in s.dependencies
                ]
                revised.append(
                    {
                        "step_id": s.step_id,
                        "title": s.title,
                        "agent": s.agent,
                        "description": s.description,
                        "dependencies": remapped_deps,
                        "success_criteria": s.success_criteria,
                        "requires_validation": s.requires_validation,
                        "max_retries": s.max_retries,
                    }
                )

        return revised

    def _should_use_llm_for_replan(
        self,
        reason: str,
        failed_step: PlanStep | None = None,
        state: dict[str, Any] | None = None,
    ) -> bool:
        """
        Avalia se o replanejamento exige uma chamada ao LLM para nova interpretação semântica.
        Por padrão, falhas operacionais conhecidas usam recuperação determinística rápida.
        """
        if hasattr(state, "get"):
            if bool(state.get("force_llm_replan", False)):
                return True
            if bool(state.get("deterministic_mode", False)):
                return False

        has_llm_backend = self.llm_callable is not None or self.model is not None
        if not has_llm_backend:
            return False

        lower_reason = (reason or "").lower()
        return any(marker in lower_reason for marker in REPLAN_SEMANTIC_MARKERS)

    @staticmethod
    def _consolidate_consecutive_same_agent_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Consolida etapas consecutivas sequenciais atribuídas ao mesmo especialista.
        Evita a fragmentação excessiva onde o mesmo agente executa múltiplas vezes seguidas
        para uma única solicitação atômica (ex.: gerar pipeline, adicionar feature, visualizar).
        """
        if not steps or len(steps) <= 1:
            return steps

        consolidated: list[dict[str, Any]] = []
        id_alias_map: dict[str, str] = {}

        for step in steps:
            s_dict = dict(step)
            step_id = str(s_dict.get("step_id", ""))
            raw_deps = [str(d) for d in s_dict.get("dependencies", [])]
            resolved_deps = [id_alias_map.get(d, d) for d in raw_deps]

            if not consolidated:
                consolidated.append(s_dict)
                id_alias_map[step_id] = step_id
                continue

            last = consolidated[-1]
            last_id = str(last.get("step_id", ""))
            is_same_agent = s_dict.get("agent") == last.get("agent")
            is_sequential_to_last = (resolved_deps == [last_id]) or (not resolved_deps and len(consolidated) == 1)

            if is_same_agent and is_sequential_to_last:
                # Funde com a etapa anterior do mesmo especialista
                last_title = str(last.get("title") or "")
                new_title = str(s_dict.get("title") or "")
                if new_title and new_title.lower() not in last_title.lower():
                    last["title"] = f"{last_title} e {new_title}".strip()

                last_desc = str(last.get("description") or "")
                new_desc = str(s_dict.get("description") or "")
                if new_desc and new_desc.lower() not in last_desc.lower():
                    last["description"] = f"{last_desc} {new_desc}".strip()

                last_crit = str(last.get("success_criteria") or "")
                new_crit = str(s_dict.get("success_criteria") or "")
                if new_crit and new_crit.lower() not in last_crit.lower():
                    last["success_criteria"] = f"{last_crit} {new_crit}".strip()

                last["requires_validation"] = bool(last.get("requires_validation") or s_dict.get("requires_validation"))
                last["max_retries"] = max(int(last.get("max_retries", 1)), int(s_dict.get("max_retries", 1)))
                id_alias_map[step_id] = last_id
            else:
                s_dict["dependencies"] = resolved_deps
                consolidated.append(s_dict)
                id_alias_map[step_id] = step_id

        # Reindexa step_ids para manter a sequência limpa 1, 2, ...
        final_id_map: dict[str, str] = {}
        for idx, s in enumerate(consolidated, start=1):
            old_id = str(s.get("step_id", idx))
            new_id = str(idx)
            final_id_map[old_id] = new_id
            s["step_id"] = new_id

        for s in consolidated:
            new_deps = []
            for d in s.get("dependencies", []):
                mapped = final_id_map.get(str(d))
                if mapped and mapped != s["step_id"] and mapped not in new_deps:
                    new_deps.append(mapped)
            s["dependencies"] = new_deps

        return consolidated

    def _build_llm_steps(self, user_text: str) -> tuple[str, str, list[dict[str, Any]]]:
        """
        Utiliza o LLM sob demanda para interpretar solicitações ambíguas ou complexas
        e converter o resultado nos parâmetros de construção de um `ExecutionPlan`.
        """
        user_prompt = (
            f"Solicitação operacional do usuário:\n{user_text}\n\n"
            "Elabore o plano de execução em JSON válido contendo 'objective', 'success_criteria' e 'steps'."
        )
        raw_response = self._call_llm(PLANNER_AGENT_INSTRUCTION, user_prompt)
        parsed = self._parse_llm_json(raw_response)

        objective = str(parsed.get("objective") or user_text or "Executar solicitação operacional").strip()
        success_criteria = str(
            parsed.get("success_criteria")
            or "Todas as etapas planejadas concluídas e validadas respeitando dependências e guardrails."
        ).strip()
        raw_steps = parsed.get("steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            raise PlanValidationError("Resposta do LLM não contém uma lista válida de 'steps'.")

        consolidated_steps = self._consolidate_consecutive_same_agent_steps(raw_steps)
        return objective, success_criteria, consolidated_steps

    def _build_llm_replan_steps(
        self,
        plan: ExecutionPlan,
        reason: str,
        failed_step: PlanStep | None,
        completed_ids: set[str],
    ) -> list[dict[str, Any]]:
        """Solicita ao LLM uma nova decomposição para as etapas restantes preservando as etapas já concluídas."""
        completed_summary = [
            {"step_id": s.step_id, "title": s.title, "agent": s.agent, "result_summary": s.result_summary}
            for s in plan.steps
            if s.step_id in completed_ids
        ]
        failed_info = (
            f"Etapa falha: {failed_step.step_id} ({failed_step.title} - {failed_step.agent})"
            if failed_step
            else "Mudança de contexto operacional"
        )
        user_prompt = (
            f"Objetivo original: {plan.objective}\n"
            f"Etapas já concluídas (NÃO repetir): {json.dumps(completed_summary, ensure_ascii=False)}\n"
            f"{failed_info}\n"
            f"Motivo do replanejamento: {reason}\n\n"
            "Retorne em JSON o campo 'steps' apenas com as novas etapas pendentes necessárias para concluir o objetivo."
        )
        raw_response = self._call_llm(PLANNER_AGENT_INSTRUCTION, user_prompt)
        parsed = self._parse_llm_json(raw_response)
        raw_steps = parsed.get("steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            raise PlanValidationError("Resposta de replanejamento do LLM não contém 'steps' válidos.")
        return self._consolidate_consecutive_same_agent_steps(raw_steps)

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Executa uma chamada enxuta ao LLM configurado quando o planejamento híbrido exigir."""
        if self.llm_callable is not None:
            return self.llm_callable(system_prompt, user_prompt)

        import litellm

        model_name = getattr(self.model, "model", None) or (
            self.model if isinstance(self.model, str) else None
        ) or LLM_MODEL

        kwargs: dict[str, Any] = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
        }
        if LLM_API_KEY:
            kwargs["api_key"] = LLM_API_KEY
        if LLM_API_BASE:
            kwargs["api_base"] = LLM_API_BASE

        response = litellm.completion(**kwargs)
        choices = getattr(response, "choices", None) or (
            response.get("choices") if isinstance(response, dict) else []
        )
        if not choices:
            raise RuntimeError("LLM retornou resposta sem choices.")
        first_choice = choices[0]
        message = getattr(first_choice, "message", None) or (
            first_choice.get("message") if isinstance(first_choice, dict) else {}
        )
        content = getattr(message, "content", None) or (
            message.get("content") if isinstance(message, dict) else ""
        )
        return str(content or "").strip()

    @staticmethod
    def _parse_llm_json(raw_text: str) -> dict[str, Any]:
        """Extrai e valida um dicionário JSON a partir da resposta textual do LLM."""
        if not raw_text or not raw_text.strip():
            raise PlanValidationError("Resposta vazia recebida do LLM no planejamento.")

        cleaned = re.sub(r"<(thought|thinking)>.*?</\1>", "", raw_text, flags=re.DOTALL | re.IGNORECASE).strip()
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL | re.IGNORECASE)
        candidate = fenced.group(1) if fenced else cleaned

        if not candidate.startswith("{"):
            brace_match = re.search(r"\{.*\}", candidate, flags=re.DOTALL)
            if brace_match:
                candidate = brace_match.group(0)

        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise PlanValidationError(f"Falha ao decodificar JSON de planejamento do LLM: {exc}") from exc

        if not isinstance(parsed, dict):
            raise PlanValidationError("O retorno JSON do LLM para o plano deve ser um objeto.")

        return parsed


# Instância padrão do planejador híbrido para uso direto
default_planner = KrakenPlanner()


def synthesize_plan_for_request(
    user_text: str,
    session_id: str | None = None,
    force_new: bool = False,
    state: dict[str, Any] | None = None,
) -> ExecutionPlan:
    """Função utilitária de conveniência que delega a criação do plano ao `KrakenPlanner`."""
    return default_planner.create_plan(
        user_text=user_text,
        session_id=session_id,
        state=state,
        force_new=force_new,
    )
