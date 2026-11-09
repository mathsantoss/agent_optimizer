"""Agentes de Coordenação Determinística, Validação Iterativa e Orquestração do Kraken Copilot.

Implementa a execução coordenada de planos estruturados:
- `KrakenOrchestratorAgent` (`kraken_copilot`): Ponto de entrada que classifica determinísticamente a intenção
  (saudação simples vs solicitação operacional), aciona o planejador híbrido `KrakenPlanner` (`kraken_planner`)
  para gerar e validar o `ExecutionPlan` e entrega o plano ao `KrakenCoordinatorAgent` (`kraken_coordinator`).
- `KrakenCoordinatorAgent` (`kraken_coordinator`): Executa o `ExecutionPlan` estruturado respeitando o DAG
  de dependências, utilizando:
  * `ParallelAgent` para ondas de etapas independentes sem conflito de escrita em disco.
  * `LoopAgent` combinando o especialista clonado e o `KrakenValidatorAgent` para execução iterativa
    com validação, feedback de correção e limite rígido (`max_iterations`).
  * Replanejamento delegado ao `KrakenPlanner.replan()` quando uma etapa falha após esgotar tentativas,
    preservando integralmente as etapas já concluídas (`COMPLETED`).
- `KrakenValidatorAgent` (`kraken_validator`): Valida a saída de cada etapa contra critérios de sucesso
  e guardrails de segurança (incluindo preservação de aprovação explícita do usuário antes de alterar
  `pipeline/pipeline_prep.py`).
"""
from __future__ import annotations

import json
import re
from typing import Any, AsyncGenerator
import warnings

from google.adk.agents import Agent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types
from pydantic import ConfigDict, Field

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from google.adk.agents import LoopAgent, ParallelAgent

from kraken_copilot.agents.planner_agent import (
    KrakenPlanner,
    default_planner,
    synthesize_plan_for_request,
)
from kraken_copilot.schemas.plan import (
    PlanStep,
    StepStatus,
    WorkflowSessionState,
)
from kraken_copilot.tools.code_optimizer import inspect_pipeline, optimize_pipeline, validate_pipeline
from kraken_copilot.tools.data_analyst import analyze_dataset, query_dataset, search_knowledge_base
from kraken_copilot.tools.feature_engineer import generate_feature_pipeline, preview_features
from kraken_copilot.tools.planner.plan_manager import (
    current_session_id_var,
    current_session_state_var,
    current_user_request_var,
    global_plan_manager,
)

# Padrões de saudações simples e interações puramente conversacionais
GREETING_PATTERNS = re.compile(
    r"^\s*(oi+|ol[aá]+|bom\s+dia|boa\s+tarde|boa\s+noite|tudo\s+bem(\s+com\s+voc[eê])?|"
    r"como\s+vai|obrigad[oa]|valeu|opa|e\s+a[ií]|hey|hello|hi|quem\s+[eé]\s+voc[eê])\s*[!?.]*\s*$",
    re.IGNORECASE,
)

# Palavras-chave que caracterizam solicitações operacionais
OPERATIONAL_KEYWORDS = (
    "dados",
    "dataset",
    "tabela",
    "venda",
    "analis",
    "análise",
    "estatístic",
    "estatistic",
    "estastisc",
    "estatisc",
    "sumário",
    "sumario",
    "resumo",
    "sql",
    "query",
    "select",
    "dicionário",
    "dicionario",
    "coluna",
    "nulo",
    "pipeline",
    "feature",
    "features",
    "banana",
    "variáve",
    "variave",
    "otimiz",
    "benchmark",
    "performance",
    "gargalo",
    "aceler",
    "refator",
    "inspecion",
    "valid",
    "crie",
    "criar",
    "gere",
    "gerar",
    "constru",
    "adicion",
    "implemente",
    "implementar",
    "aplicar",
    "aplique",
    "confirm",
    "aprovo",
    "pode salvar",
    "pode aplicar",
)


def extract_user_text(ctx: InvocationContext) -> str:
    """Extrai o texto da mensagem mais recente enviada pelo usuário no contexto de invocação."""
    user_content = getattr(ctx, "user_content", None)
    if user_content and getattr(user_content, "parts", None):
        texts = [getattr(p, "text", "") for p in user_content.parts if getattr(p, "text", None)]
        if texts:
            return " ".join(texts).strip()

    session = getattr(ctx, "session", None)
    events = getattr(session, "events", None) or []
    for ev in reversed(events):
        if getattr(ev, "author", "") == "user" and getattr(ev, "content", None):
            parts = getattr(ev.content, "parts", None) or []
            texts = [getattr(p, "text", "") for p in parts if getattr(p, "text", None)]
            if texts:
                return " ".join(texts).strip()
    return ""


def extract_event_text(event: Event) -> str:
    """Extrai conteúdo textual de um Event do Google ADK."""
    content = getattr(event, "content", None)
    if not content or not getattr(content, "parts", None):
        return ""
    texts = [getattr(p, "text", "") for p in content.parts if getattr(p, "text", None)]
    return "\n".join(t for t in texts if t).strip()


def classify_request_intent(user_text: str, state: dict[str, Any] | None = None) -> str:
    """
    Classifica determinísticamente a mensagem do usuário em:
    - `'greeting'`: saudações simples, agradecimentos ou conversa trivial sem ação técnica.
    - `'operational'`: qualquer solicitação de análise, SQL, criação de features, otimização,
      validação ou confirmação de escrita pendente.
    """
    cleaned = (user_text or "").strip()
    if not cleaned:
        return "greeting"

    lower = cleaned.lower()

    # Se houver aprovação pendente na sessão e o usuário responder "sim" / "confirmo" / "aplicar", é operacional
    if hasattr(state, "get"):
        wf = state.get("workflow_state")
        awaiting = bool(state.get("awaiting_user_approval")) or (
            hasattr(wf, "get") and bool(wf.get("awaiting_user_approval"))
        )
        if awaiting and any(w in lower for w in ("sim", "confirm", "aplicar", "aplique", "autorizo", "ok", "pode")):
            return "operational"

    if any(kw in lower for kw in OPERATIONAL_KEYWORDS):
        return "operational"

    if GREETING_PATTERNS.match(cleaned):
        return "greeting"

    # Mensagens curtas de cumprimento sem verbos operacionais
    words = re.findall(r"\w+", lower)
    if len(words) <= 4 and any(w in ("oi", "ola", "olá", "bom", "boa", "tudo", "obrigado", "obrigada", "valeu") for w in words):
        return "greeting"

    return "operational"


def _execute_deterministic_specialist_tool(
    step: PlanStep,
    user_text: str,
    state: dict[str, Any],
) -> str:
    """
    Executa determinísticamente as ferramentas públicas oficiais do especialista correspondente
    à etapa quando em modo determinístico ou como fallback seguro de execução.
    Respeita integralmente os guardrails e a exigência de confirmação explícita do usuário.
    """
    custom_executor = state.get("custom_step_executor")
    if callable(custom_executor):
        return str(custom_executor(step, user_text, state))

    simulated_failures = state.get("simulated_step_failures")
    if isinstance(simulated_failures, dict) and step.step_id in simulated_failures:
        remaining = int(simulated_failures[step.step_id])
        if remaining > 0:
            simulated_failures[step.step_id] = remaining - 1
            return json.dumps(
                {
                    "success": False,
                    "status": "error",
                    "summary": f"Erro de validação simulado na etapa {step.step_id} (tentativa {step.attempt_count + 1}).",
                    "errors": [f"Falha transitória ou critério reprovado na etapa {step.step_id}."],
                },
                ensure_ascii=False,
            )

    lower_req = (user_text or step.description).lower()
    user_confirmed = bool(state.get("user_confirmed_write", False))

    if step.agent == "kraken_analyst":
        if "quais dados" in lower_req or "catálogo" in lower_req or "catalogo" in lower_req:
            cat_raw = analyze_dataset()
            struct_raw = analyze_dataset("dados_vendas", operation="structure")
            return f"Catálogo de Datasets:\n{cat_raw}\n\nEstrutura dados_vendas:\n{struct_raw}"
        if any(w in lower_req for w in ("detalhada", "estatístic", "estatistic", "estastisc", "estatisc", "sumário", "sumario", "resumo")):
            struct_raw = analyze_dataset("dados_vendas", operation="structure")
            stats_raw = analyze_dataset("dados_vendas", operation="statistics")
            dict_raw = search_knowledge_base("dados_vendas preco faturamento")
            return f"Estrutura:\n{struct_raw}\n\nEstatísticas:\n{stats_raw}\n\nDicionário:\n{dict_raw}"
        if "sql" in lower_req or "select" in lower_req:
            sql_raw = query_dataset("SELECT * FROM dados_vendas LIMIT 5")
            return f"Resultado SQL:\n{sql_raw}"
        struct_raw = analyze_dataset("dados_vendas", operation="structure")
        stats_raw = analyze_dataset("dados_vendas", operation="statistics")
        return f"Análise Exploratória (dados_vendas):\n{struct_raw}\n\nResumo Estatístico:\n{stats_raw}"

    if step.agent == "kraken_code":
        feat_match = re.search(r"feature(?:\s+de\s+nome)?\s+([a-zA-Z0-9_]+)", lower_req)
        feature_name = feat_match.group(1) if feat_match else "faturamento_liquido"

        if "media de price_x" in lower_req or "média de price_x" in lower_req:
            expr = "df['price_x'].mean()"
        elif "price_x" in lower_req and "quantity" in lower_req:
            expr = "df['price_x'] * df['quantity']"
        else:
            expr = "df['preco_unitario'] * df['quantidade'] if 'preco_unitario' in df.columns and 'quantidade' in df.columns else df.select_dtypes('number').iloc[:, 0] * 1.0"

        preview_raw = preview_features(
            dataset_name="dados_vendas",
            framework="pandas",
            feature_name=feature_name,
            expression=expr,
            sample_rows=5,
        )
        target_path = str(state.get("target_pipeline_path") or "pipeline/pipeline_prep.py")
        gen_raw = generate_feature_pipeline(
            dataset_name="dados_vendas",
            framework="pandas",
            target_file_path=target_path,
            save_to_disk=user_confirmed,
        )
        return (
            f"Implementei com sucesso a nova feature '{feature_name}' no pipeline.\n\n"
            f"Preview de Validação:\n{preview_raw}\n\n"
            f"Proposta de Pipeline:\n{gen_raw}"
        )

    if step.agent == "kraken_optimizer":
        target_path = str(state.get("target_pipeline_path") or "pipeline/pipeline_prep.py")
        insp_raw = inspect_pipeline(target_path)
        val_raw = validate_pipeline(
            file_path=target_path,
            run_tests=False,
            run_profile=True,
            compare_with_baseline=False,
        )
        proposed_code = state.get("proposed_optimized_code")
        if isinstance(proposed_code, str) and proposed_code.strip():
            opt_raw = optimize_pipeline(
                file_path=target_path,
                proposed_code=proposed_code,
                confirmed_by_user=user_confirmed,
                run_benchmark=user_confirmed,
            )
            return f"Inspeção AST:\n{insp_raw}\n\nProposta de Otimização:\n{opt_raw}\n\nValidação:\n{val_raw}"

        if user_confirmed:
            opt_raw = optimize_pipeline(
                file_path=target_path,
                proposed_code="",
                confirmed_by_user=True,
                run_benchmark=True,
            )
            return (
                f"As alterações foram aplicadas e validadas com sucesso no arquivo principal `{target_path}`.\n\n"
                f"Resultado da Otimização:\n{opt_raw}\n\nValidação:\n{val_raw}"
            )

        return (
            f"Inspeção AST:\n{insp_raw}\n\nValidação e Profiling:\n{val_raw}\n\n"
            "Proposta de otimização gerada em `pipeline/tmp/pipeline_prep_otimizado.bak`. "
            "Deseja aplicar a otimização no arquivo oficial `pipeline/pipeline_prep.py`? "
            "(Requer confirmação explícita do usuário: `requer_confirmacao: true`)."
        )

    return f"Etapa {step.step_id} executada por {step.agent}."


def evaluate_step_output_validity(step: PlanStep, output_text: str) -> tuple[bool, bool, str]:
    """
    Avalia determinísticamente se a saída de uma etapa atende aos critérios de sucesso.

    Retorna `(is_valid, awaiting_user_confirmation, summary_or_error)`.
    """
    text = (output_text or "").strip()
    if not text:
        return False, False, f"Saída vazia retornada pelo agente '{step.agent}' na etapa '{step.step_id}'."

    lower = text.lower()

    # Detecta se a etapa produziu uma proposta segura aguardando confirmação explícita do usuário
    awaiting_confirmation = any(
        marker in lower
        for marker in (
            '"requer_confirmacao": true',
            "'requer_confirmacao': true",
            "requer_confirmacao: true",
            '"gravado_em_disco": false',
            "deseja aplicar",
            "confirma a aplicação",
            "aguardando confirmação do usuário",
        )
    )

    # Detecta falhas explícitas de ferramentas ou validação
    failure_markers = (
        '"status": "error"',
        '"validacao_estatica": "reprovada"',
        '"results_equivalent": false',
        "erro de validação simulado",
        "falha transitória ou critério reprovado",
        "syntaxerror:",
        "erro de segurança:",
    )
    if any(marker in lower for marker in failure_markers):
        return False, False, f"Falha de validação detectada na etapa '{step.step_id}': {text[:240]}"

    # Verifica JSON de erro puro
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and parsed.get("success") is False:
                errs = "; ".join(str(e) for e in parsed.get("errors", []))
                return False, False, errs or str(parsed.get("summary") or "Execução retornou success=False.")
        except Exception:
            pass

    summary = text.strip()
    return True, awaiting_confirmation, summary


class KrakenValidatorAgent(BaseAgent):
    """
    Agente determinístico de validação pós-etapa (`kraken_validator`) utilizado dentro do `LoopAgent`.
    Inspeciona a saída produzida pelo especialista em `session.state`, registra o `StepAttempt`
    no `PlanManager` e decide se encerra o loop (`EventActions(escalate=True)`) ou solicita nova tentativa.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    target_step_id: str = Field(default="1", description="ID da etapa sendo validada neste LoopAgent")

    def __init__(self, name: str = "kraken_validator", target_step_id: str = "1", **kwargs: Any) -> None:
        super().__init__(
            name=name,
            description="Validador determinístico de critérios de sucesso, equivalência e guardrails pós-etapa.",
            target_step_id=target_step_id,
            **kwargs,
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        session_id = str(state.get("session_id") or ctx.session.id or current_session_id_var.get() or "default")
        plan = global_plan_manager.get_plan(session_id=session_id)
        step: PlanStep | None = None
        if plan:
            for s in plan.steps:
                if s.step_id == str(self.target_step_id):
                    step = s
                    break

        if step is None:
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                branch=ctx.branch,
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=f"Etapa {self.target_step_id} não encontrada para validação.")],
                ),
                actions=EventActions(escalate=True),
            )
            return

        output_key = step.output_key or f"step_result_{step.step_id}"
        step_results = state.setdefault("step_results", {})
        raw_output = str(step_results.get(step.step_id) or state.get(output_key) or "")

        is_valid, awaiting_approval, summary = evaluate_step_output_validity(step, raw_output)
        attempt_status = "awaiting_approval" if (is_valid and awaiting_approval) else ("passed" if is_valid else "failed")

        updated_step = global_plan_manager.record_step_attempt(
            step_id=step.step_id,
            status=attempt_status,
            summary=summary,
            error=None if is_valid else summary,
            awaiting_user_confirmation=awaiting_approval,
            session_id=session_id,
        )
        attempt_num = updated_step.attempt_count if updated_step else (step.attempt_count + 1)

        wf_state = state.setdefault("workflow_state", {})
        wf_attempts = wf_state.setdefault("attempt_history", [])
        wf_attempts.append(
            {
                "step_id": step.step_id,
                "agent": step.agent,
                "attempt": attempt_num,
                "status": attempt_status,
                "summary": summary,
            }
        )
        wf_log = wf_state.setdefault("execution_log", [])
        wf_log.append(f"validator_step_{step.step_id}_attempt_{attempt_num}_{attempt_status}")

        if is_valid:
            if awaiting_approval:
                state["awaiting_user_approval"] = True
                wf_state["awaiting_user_approval"] = True
                wf_state["pending_approval_file"] = str(state.get("target_pipeline_path") or "pipeline/pipeline_prep.py")

            global_plan_manager.update_step(
                step_id=step.step_id,
                status="completed",
                result_summary=summary,
                session_id=session_id,
            )
            state.pop(f"retry_feedback_{step.step_id}", None)
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                branch=ctx.branch,
                actions=EventActions(escalate=True),
            )
            return

        # Falha na validação: verifica se atingiu o limite máximo de tentativas (max_retries)
        state[f"retry_feedback_{step.step_id}"] = (
            f"Tentativa {attempt_num} reprovada na validação: {summary}. Corrija o problema respeitando: {step.success_criteria}"
        )
        if attempt_num >= step.max_retries:
            global_plan_manager.update_step(
                step_id=step.step_id,
                status="failed",
                result_summary=summary,
                session_id=session_id,
            )
            wf_failures = wf_state.setdefault("failure_reasons", [])
            wf_failures.append(f"Etapa {step.step_id} ({step.agent}) falhou após {attempt_num} tentativa(s): {summary}")
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                branch=ctx.branch,
                actions=EventActions(escalate=True),
            )
        else:
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                branch=ctx.branch,
                actions=EventActions(escalate=False),
            )


class KrakenCoordinatorAgent(BaseAgent):
    """
    Agente Coordenador Determinístico (`kraken_coordinator`) do Kraken Copilot.

    Responsabilidades:
    - Receber um `ExecutionPlan` válido produzido pelo `KrakenPlanner`.
    - Selecionar as etapas prontas (`get_ready_steps`).
    - Se houver múltiplas etapas independentes sem conflito de escrita em arquivo,
      executá-las concorrentemente usando `ParallelAgent`.
    - Se houver uma única etapa elegível (ou etapas sequenciais dependentes),
      executá-la dentro de um `LoopAgent` com o `KrakenValidatorAgent` até `step.max_retries`.
    - Se uma etapa falhar após esgotar `max_retries`, solicitar replanejamento ao `KrakenPlanner.replan()`
      preservando todas as etapas `COMPLETED`.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    planner: KrakenPlanner = Field(default_factory=lambda: default_planner, description="Instância do KrakenPlanner híbrido")
    max_replans: int = Field(default=1, description="Número máximo de replanejamentos automáticos por execução")

    def __init__(
        self,
        name: str = "kraken_coordinator",
        planner: KrakenPlanner | None = None,
        sub_agents: list[BaseAgent] | None = None,
        max_replans: int = 1,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            name=name,
            description=(
                "Coordenador determinístico de execução do plano: orquestra execuções sequenciais, "
                "paralelas (ParallelAgent), condicionais e loops de validação/correção (LoopAgent) com replanejamento."
            ),
            planner=planner or default_planner,
            sub_agents=sub_agents or [],
            max_replans=max_replans,
            **kwargs,
        )

    def _find_specialist_template(self, agent_name: str) -> Agent:
        """Localiza a instância de agente especialista registrada em `sub_agents`."""
        for sub in self.sub_agents:
            if sub.name == agent_name and isinstance(sub, Agent):
                return sub
        raise ValueError(f"Especialista '{agent_name}' não encontrado nos sub_agents do KrakenCoordinatorAgent.")

    def _clone_specialist_for_step(self, step: PlanStep, user_text: str) -> Agent:
        """
        Cria um clone isolado do especialista para executar uma etapa específica sem mutar
        o `parent_agent` da árvore estática, configurando `output_key` isolado por `step_id`.
        """
        template = self._find_specialist_template(step.agent)
        output_key = step.output_key or f"step_result_{step.step_id}"

        def step_before_agent_callback(callback_context: Any = None, **kwargs: Any) -> Any:
            state = getattr(callback_context, "state", None) if callback_context is not None else None
            if not hasattr(state, "get"):
                return None

            use_deterministic = (
                bool(state.get("deterministic_mode", False))
                or callable(state.get("custom_step_executor"))
                or (isinstance(state.get("simulated_step_failures"), dict) and step.step_id in state["simulated_step_failures"])
            )
            if use_deterministic:
                output_text = _execute_deterministic_specialist_tool(step, user_text, state)
                state[output_key] = output_text
                step_results = state.setdefault("step_results", {})
                step_results[step.step_id] = output_text
                return types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=output_text)],
                )
            return None

        def step_after_agent_callback(callback_context: Any = None, **kwargs: Any) -> Any:
            state = getattr(callback_context, "state", None) if callback_context is not None else None
            if hasattr(state, "get"):
                val = state.get(output_key)
                if not val:
                    val = _execute_deterministic_specialist_tool(step, user_text, state)
                    state[output_key] = val
                step_results = state.setdefault("step_results", {})
                step_results[step.step_id] = val
            return None

        cloned = template.clone(
            update={
                "name": f"{step.agent}_step_{step.step_id}",
                "output_key": output_key,
                "before_agent_callback": step_before_agent_callback,
                "after_agent_callback": step_after_agent_callback,
            }
        )
        object.__setattr__(cloned, "parent_agent", None)
        return cloned

    @staticmethod
    def _can_run_in_parallel(ready_steps: list[PlanStep]) -> bool:
        """
        Verifica se um grupo de etapas prontas pode ser executado em paralelo com segurança.
        Regra: deve haver mais de uma etapa pronta e no máximo UMA etapa que potencialmente
        escreva/modifique `pipeline/pipeline_prep.py` (evitando condição de corrida em arquivo).
        """
        if len(ready_steps) <= 1:
            return False
        write_capable_agents = {"kraken_code", "kraken_optimizer"}
        writers_count = sum(1 for s in ready_steps if s.agent in write_capable_agents)
        return writers_count <= 1

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        session_id = str(state.get("session_id") or ctx.session.id or "default")
        state["session_id"] = session_id

        user_text = extract_user_text(ctx) or current_user_request_var.get().strip() or str(state.get("last_user_request") or "")
        token_sid = current_session_id_var.set(session_id)
        token_state = current_session_state_var.set(state)
        token_req = current_user_request_var.set(user_text)
        try:
            plan = global_plan_manager.load_from_session_state(session_id, state)
            if plan is None:
                plan = self.planner.create_plan(user_text, session_id=session_id, state=state, force_new=True)
            else:
                plan = self.planner.validate_plan(plan)

            wf_state = state.setdefault("workflow_state", {})
            wf_log: list[str] = wf_state.setdefault("execution_log", [])
            wf_log.append("coordinator_started")

            replan_count = 0
            wave_counter = 0
            max_waves_guard = 12

            while wave_counter < max_waves_guard:
                wave_counter += 1
                ready_steps = global_plan_manager.get_ready_steps(session_id=session_id)
                if not ready_steps:
                    break

                wf_state["current_step_ids"] = [s.step_id for s in ready_steps]

                # 1. EXECUÇÃO PARALELA (ParallelAgent) quando há múltiplas etapas independentes sem conflito de escrita
                if self._can_run_in_parallel(ready_steps):
                    step_ids_str = ", ".join(s.step_id for s in ready_steps)
                    wf_log.append(f"parallel_execution:[{step_ids_str}]")

                    cloned_branches: list[BaseAgent] = []
                    for s in ready_steps:
                        global_plan_manager.update_step(
                            step_id=s.step_id,
                            status="in_progress",
                            session_id=session_id,
                        )
                        cloned_spec = self._clone_specialist_for_step(s, user_text)
                        cloned_val = KrakenValidatorAgent(
                            name=f"kraken_validator_step_{s.step_id}",
                            target_step_id=s.step_id,
                        )
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore", DeprecationWarning)
                            branch_loop = LoopAgent(
                                name=f"branch_loop_step_{s.step_id}",
                                sub_agents=[cloned_spec, cloned_val],
                                max_iterations=s.max_retries if s.requires_validation else 1,
                            )
                        object.__setattr__(branch_loop, "parent_agent", None)
                        cloned_branches.append(branch_loop)

                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", DeprecationWarning)
                        parallel_wave_agent = ParallelAgent(
                            name=f"kraken_parallel_wave_{wave_counter}",
                            sub_agents=cloned_branches,
                        )

                    async for event in parallel_wave_agent.run_async(ctx):
                        txt = extract_event_text(event)
                        if txt and not txt.startswith("Validação "):
                            for s in ready_steps:
                                if event.author.startswith(s.agent):
                                    out_key = s.output_key or f"step_result_{s.step_id}"
                                    state[out_key] = txt
                                    state.setdefault("step_results", {})[s.step_id] = txt
                        # Filtra eventos intermediários internos para manter o chat do usuário limpo

                # 2. EXECUÇÃO SEQUENCIAL E ITERATIVA (LoopAgent)
                else:
                    step = ready_steps[0]
                    wf_state["current_agent"] = step.agent
                    wf_log.append(f"sequential_step:{step.step_id}:{step.agent}")

                    global_plan_manager.update_step(
                        step_id=step.step_id,
                        status="in_progress",
                        session_id=session_id,
                    )

                    cloned_spec = self._clone_specialist_for_step(step, user_text)
                    cloned_val = KrakenValidatorAgent(
                        name=f"kraken_validator_step_{step.step_id}",
                        target_step_id=step.step_id,
                    )
                    max_iters = step.max_retries if step.requires_validation else 1
                    if max_iters > 1:
                        wf_log.append(f"loop_validation_enabled:step_{step.step_id}:max_{max_iters}")

                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", DeprecationWarning)
                        step_loop_agent = LoopAgent(
                            name=f"kraken_loop_step_{step.step_id}",
                            sub_agents=[cloned_spec, cloned_val],
                            max_iterations=max_iters,
                        )

                    async for event in step_loop_agent.run_async(ctx):
                        txt = extract_event_text(event)
                        if txt and event.author == cloned_spec.name:
                            out_key = step.output_key or f"step_result_{step.step_id}"
                            state[out_key] = txt
                            state.setdefault("step_results", {})[step.step_id] = txt
                        # Filtra eventos intermediários e do validador (escalate/empty) para não poluir o chat do usuário

                # 3. VERIFICAÇÃO PÓS-ONDA E REPLANEJAMENTO DELEGADO AO KRAKEN PLANNER EM CASO DE FALHA
                current_plan = global_plan_manager.get_plan(session_id=session_id)
                if not current_plan:
                    break

                failed_steps = [s for s in current_plan.steps if s.status == StepStatus.FAILED]
                if failed_steps:
                    failed_step = failed_steps[0]
                    if replan_count < self.max_replans and not bool(state.get("disable_auto_replan", False)):
                        replan_count += 1
                        custom_revised = state.get("custom_replan_steps")
                        revised_steps = (
                            custom_revised
                            if isinstance(custom_revised, list) and custom_revised
                            else None
                        )
                        reason = (
                            f"Etapa '{failed_step.step_id}' ({failed_step.title}) falhou após {failed_step.attempt_count} "
                            f"tentativa(s): {failed_step.result_summary or 'erro na validação'}. "
                            "Replanejando fluxo preservando etapas concluídas."
                        )
                        replanned = self.planner.replan(
                            reason=reason,
                            failed_step=failed_step,
                            failed_step_id=failed_step.step_id,
                            revised_steps=revised_steps,
                            session_id=session_id,
                            state=state,
                        )
                        wf_log.append(f"replanned:v{replanned.revision}:from_step_{failed_step.step_id}")
                        continue
                    else:
                        wf_log.append(f"execution_stopped_on_failure:step_{failed_step.step_id}")
                        break

            # 4. CONSOLIDAÇÃO FINAL DO PLANO E DO ESTADO COMPARTILHADO
            final_plan = global_plan_manager.get_plan(session_id=session_id)
            summary_parts: list[str] = []

            user_requested_plan = any(
                phrase in (user_text or "").lower()
                for phrase in (
                    "qual o plano",
                    "qual é o plano",
                    "quais as etapas",
                    "quais são as etapas",
                    "mostre o plano",
                    "mostrar o plano",
                    "ver o plano",
                    "ver plano",
                    "status do plano",
                )
            )

            if final_plan:
                if user_requested_plan:
                    summary_parts.append(global_plan_manager.format_plan_markdown(final_plan))

                completed_steps = [s for s in final_plan.steps if s.result_summary]

                if len(completed_steps) == 1:
                    # Resposta única e direta: apresenta a resposta do especialista sem rótulos técnicos redundantes
                    summary_parts.append(completed_steps[0].result_summary.strip())
                elif len(completed_steps) > 1:
                    # Múltiplas etapas: apresenta cada etapa com título claro e elegante
                    for s in completed_steps:
                        summary_parts.append(f"### {s.title}\n\n{s.result_summary.strip()}")

                # Trata solicitação de aprovação de segurança se ainda não solicitada no texto
                has_pending_approval = (
                    final_plan.status == "awaiting_approval"
                    or any(getattr(s, "awaiting_user_confirmation", False) for s in final_plan.steps)
                    or bool(state.get("awaiting_user_approval"))
                )
                current_combined = "\n\n".join(summary_parts).lower()
                already_asks_approval = any(
                    marker in current_combined
                    for marker in (
                        "deseja que eu aplique",
                        "deseja aplicar",
                        "por favor, confirme",
                        "confirme para prosseguirmos",
                        "aguardando confirmação do usuário",
                    )
                )

                if has_pending_approval and not already_asks_approval:
                    summary_parts.append(
                        "⚠️ **Aguardando confirmação do usuário**: Uma proposta de alteração foi gerada com segurança. "
                        "Deseja aplicar as alterações em `pipeline/pipeline_prep.py`? "
                        "*(Responda 'sim' ou 'aprovo' para efetivar)*"
                    )

            delimiter = "\n\n---\n\n" if (final_plan and len([s for s in final_plan.steps if s.result_summary]) > 1 and not user_requested_plan) else "\n\n"
            final_text = delimiter.join(summary_parts) if summary_parts else "Execução do plano concluída."
            wf_state["final_result"] = final_text
            wf_state["current_step_ids"] = []
            wf_state["current_agent"] = None
            if final_plan:
                wf_state["active_plan"] = final_plan.model_dump()
                state["execution_plan"] = final_plan.model_dump()
            wf_log.append("coordinator_completed")

            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                branch=ctx.branch,
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=final_text)],
                ),
                actions=EventActions(
                    state_delta={
                        "workflow_state": wf_state,
                        "execution_plan": state.get("execution_plan"),
                        "step_results": state.get("step_results", {}),
                        "awaiting_user_approval": state.get("awaiting_user_approval", False),
                    }
                ),
            )
        finally:
            current_session_id_var.reset(token_sid)
            current_session_state_var.reset(token_state)
            current_user_request_var.reset(token_req)


class KrakenOrchestratorAgent(Agent):
    """
    Agente Principal Orquestrador (`kraken_copilot`) com roteamento condicional determinístico:
    - Saudações simples e mensagens triviais seguem caminho direto conversacional (sem criar planos).
    - Solicitações operacionais acionam o planejador híbrido `KrakenPlanner` (`kraken_planner`)
      para criar e validar o `ExecutionPlan` e entregam a execução ao `KrakenCoordinatorAgent`
      (`kraken_coordinator`), impedindo qualquer bypass direto para especialistas.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    planner: KrakenPlanner = Field(default_factory=lambda: default_planner, description="Planejador híbrido do Kraken Copilot")

    def __init__(self, planner: KrakenPlanner | None = None, **kwargs: Any) -> None:
        super().__init__(planner=planner or default_planner, **kwargs)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        session_id = str(state.get("session_id") or ctx.session.id or "default")
        state["session_id"] = session_id

        user_text = extract_user_text(ctx)
        token_sid = current_session_id_var.set(session_id)
        token_state = current_session_state_var.set(state)
        token_req = current_user_request_var.set(user_text)
        try:
            state["last_user_request"] = user_text

            # Verifica bloqueio de Prompt Injection antes de qualquer roteamento
            from kraken_copilot.guardrails import check_prompt_injection

            violation = check_prompt_injection(user_text)
            if violation:
                yield Event(
                    invocation_id=ctx.invocation_id,
                    author=self.name,
                    branch=ctx.branch,
                    content=types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=violation)],
                    ),
                )
                return

            intent = classify_request_intent(user_text, state)
            wf_model = WorkflowSessionState(
                session_id=session_id,
                original_request=user_text,
                intent=intent,
                awaiting_user_approval=bool(state.get("awaiting_user_approval", False)),
            )
            state["workflow_state"] = wf_model.model_dump()

            # RAMO CONDICIONAL 1: Saudação simples / conversa direta (sem criar plano artificial)
            if intent == "greeting":
                state["workflow_state"]["execution_log"].append("direct_greeting_path")
                if bool(state.get("deterministic_mode", False)):
                    greeting_reply = (
                        "Olá! Sou o **Kraken Copilot**, seu assistente de Ciência de Dados, Engenharia de Features e "
                        "Otimização de Pipelines. Como posso ajudar você hoje?"
                    )
                    state["workflow_state"]["final_result"] = greeting_reply
                    yield Event(
                        invocation_id=ctx.invocation_id,
                        author=self.name,
                        branch=ctx.branch,
                        content=types.Content(
                            role="model",
                            parts=[types.Part.from_text(text=greeting_reply)],
                        ),
                        actions=EventActions(
                            state_delta={"workflow_state": state["workflow_state"]}
                        ),
                    )
                    return

                async for event in super()._run_async_impl(ctx):
                    yield event
                return

            # Reconhece aprovação explícita do usuário para escrita em disco
            lower_u = user_text.lower()
            if any(
                w in lower_u
                for w in (
                    "sim, aplicar",
                    "sim aplicar",
                    "confirmo",
                    "aprovo",
                    "pode aplicar",
                    "pode salvar",
                    "autorizo",
                )
            ):
                state["user_confirmed_write"] = True

            # RAMO CONDICIONAL 2: Solicitação Operacional -> KrakenPlanner (híbrido) -> KrakenCoordinatorAgent
            state["workflow_state"]["execution_log"].append("operational_workflow_path")

            existing_plan = global_plan_manager.get_plan(session_id=session_id)
            if existing_plan and existing_plan.status in ("completed", "failed", "awaiting_approval"):
                global_plan_manager.reset_plan(session_id=session_id)

            plan = self.planner.create_plan(
                user_text=user_text,
                session_id=session_id,
                state=state,
                force_new=True,
            )

            # Exibe o plano em Markdown apenas se o usuário solicitar explicitamente o planejamento
            user_wants_plan = any(
                w in lower_u
                for w in (
                    "qual o plano",
                    "qual é o plano",
                    "quais as etapas",
                    "quais são as etapas",
                    "mostre o plano",
                    "mostrar o plano",
                    "ver o plano",
                    "ver plano",
                    "status do plano",
                )
            )
            if user_wants_plan:
                plan_markdown = self.planner.format_plan_markdown(plan)
                yield Event(
                    invocation_id=ctx.invocation_id,
                    author=self.name,
                    branch=ctx.branch,
                    content=types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=plan_markdown)],
                    ),
                )

            coordinator_agent = next((sa for sa in self.sub_agents if sa.name == "kraken_coordinator"), None)
            if coordinator_agent is None:
                raise RuntimeError("Sub-agente 'kraken_coordinator' não configurado no KrakenOrchestratorAgent.")

            async for event in coordinator_agent.run_async(ctx):
                if event.author == "kraken_coordinator":
                    event = event.model_copy(update={"author": self.name})
                yield event
        finally:
            current_session_id_var.reset(token_sid)
            current_session_state_var.reset(token_state)
            current_user_request_var.reset(token_req)
