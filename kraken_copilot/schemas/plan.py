"""Esquemas de dados para o Kraken Planner e o Contrato de Estado Compartilhado do Workflow."""
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

VALID_SPECIALIST_AGENTS: frozenset[str] = frozenset({
    "kraken_analyst",
    "kraken_code",
    "kraken_optimizer",
})


class StepStatus(str, Enum):
    """Status possíveis para uma etapa de um plano de execução."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepAttempt(BaseModel):
    """Registro de uma tentativa de execução/validação de uma etapa."""
    attempt: int = Field(..., description="Número sequencial da tentativa (1, 2, ...)")
    status: str = Field(..., description="Resultado da tentativa ('passed', 'failed', 'awaiting_approval')")
    summary: str = Field(default="", description="Resumo do resultado ou evidência produzida")
    error: str | None = Field(default=None, description="Detalhe do erro ou motivo de reprovação, se houver")


class PlanStep(BaseModel):
    """Representação de uma etapa individual dentro do plano de execução."""
    step_id: str = Field(..., description="Identificador único da etapa (ex: '1', '2', '3')")
    title: str = Field(..., description="Título curto e autoexplicativo da etapa")
    agent: str = Field(..., description="Agente especialista responsável: 'kraken_analyst', 'kraken_code' ou 'kraken_optimizer'")
    description: str = Field(..., description="Instruções claras e específicas sobre o que deve ser realizado nesta etapa")
    dependencies: list[str] = Field(default_factory=list, description="Lista de IDs de etapas prévias que devem ser concluídas antes desta")
    success_criteria: str = Field(
        default="Execução concluída sem erros e resultado validado.",
        description="Critério mensurável de sucesso para esta etapa específica",
    )
    status: StepStatus = Field(default=StepStatus.PENDING, description="Status de execução da etapa")
    result_summary: str | None = Field(default=None, description="Resumo das saídas, descobertas ou erros obtidos na execução")
    output_key: str | None = Field(default=None, description="Chave isolada no session.state para armazenar o resultado desta etapa")
    requires_validation: bool = Field(default=False, description="Indica se a etapa exige ciclo iterativo de validação e correção")
    max_retries: int = Field(default=2, ge=1, le=5, description="Limite máximo de tentativas no LoopAgent para esta etapa")
    attempt_count: int = Field(default=0, ge=0, description="Quantidade de tentativas já executadas para esta etapa")
    attempt_history: list[StepAttempt] = Field(default_factory=list, description="Histórico de tentativas e validações da etapa")
    awaiting_user_confirmation: bool = Field(
        default=False,
        description="Indica se a etapa gerou proposta que aguarda confirmação explícita do usuário para escrita em disco",
    )


class ExecutionPlan(BaseModel):
    """Representação estruturada de um plano completo de tarefas isolado por sessão."""
    plan_id: str = Field(..., description="Identificador único do plano (ex: 'plan_20261107_001')")
    session_id: str = Field(default="default", description="Identificador da sessão proprietária do plano")
    objective: str = Field(..., description="Objetivo central e contextualizado da solicitação")
    steps: list[PlanStep] = Field(default_factory=list, description="Sequência de etapas planejadas para alcançar o objetivo")
    success_criteria: str = Field(..., description="Critérios claros e mensuráveis para validar a conclusão com sucesso")
    current_step_id: str | None = Field(default=None, description="ID da etapa atualmente em execução ou próxima elegível")
    status: str = Field(
        default="created",
        description="Estado geral do plano: 'created', 'in_progress', 'completed', 'failed', 'replanned', 'awaiting_approval'",
    )
    revision: int = Field(default=1, description="Contador de versão do plano (incrementado a cada replanejamento)")
    replan_reason: str | None = Field(default=None, description="Motivo do último replanejamento, se aplicável")
    parallel_groups: list[list[str]] = Field(
        default_factory=list,
        description="Ondas topológicas de execução: listas de step_ids independentes que podem rodar em paralelo",
    )


class WorkflowSessionState(BaseModel):
    """Contrato estruturado do estado compartilhado da sessão entre Planner, Coordinator, Especialistas e Validator."""
    session_id: str = Field(default="default", description="ID da sessão do usuário no Google ADK")
    original_request: str = Field(default="", description="Solicitação original enviada pelo usuário")
    intent: str = Field(default="operational", description="Classificação determinística: 'greeting' ou 'operational'")
    planning_strategy: str = Field(
        default="deterministic",
        description="Estratégia interna adotada pelo KrakenPlanner ('deterministic', 'llm' ou 'deterministic_fallback')",
    )
    active_plan: ExecutionPlan | None = Field(default=None, description="Cópia estruturada do plano ativo na sessão")
    current_step_ids: list[str] = Field(default_factory=list, description="IDs das etapas em execução na onda atual")
    current_agent: str | None = Field(default=None, description="Agente especialista atualmente ativo")
    step_results: dict[str, Any] = Field(default_factory=dict, description="Resultados isolados por step_id")
    attempt_history: list[dict[str, Any]] = Field(default_factory=list, description="Histórico global de tentativas na sessão")
    failure_reasons: list[str] = Field(default_factory=list, description="Lista de motivos de falha registrados")
    awaiting_user_approval: bool = Field(
        default=False,
        description="True quando uma alteração sensível em arquivo aguarda confirmação explícita do usuário",
    )
    pending_approval_file: str | None = Field(default=None, description="Caminho do arquivo pendente de aprovação do usuário")
    final_result: str | None = Field(default=None, description="Resultado consolidado final entregue ao usuário")
    execution_log: list[str] = Field(default_factory=list, description="Trilha determinística de eventos de orquestração")
