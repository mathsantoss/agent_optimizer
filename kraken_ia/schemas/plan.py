"""Esquemas de dados para o Kraken Planner (Planos de Execução Estruturados)."""
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class StepStatus(str, Enum):
    """Status possíveis para uma etapa de um plano de execução."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PlanStep(BaseModel):
    """Representação de uma etapa individual dentro do plano de execução."""
    step_id: str = Field(..., description="Identificador único e sequencial da etapa (ex: '1', '2', '3')")
    title: str = Field(..., description="Título curto e autoexplicativo da etapa")
    agent: str = Field(..., description="Agente especialista responsável: 'kraken_analyst', 'kraken_code' ou 'kraken_optimizer'")
    description: str = Field(..., description="Instruções claras e específicas sobre o que deve ser realizado nesta etapa")
    dependencies: list[str] = Field(default_factory=list, description="Lista de IDs de etapas prévias que devem ser concluídas antes desta")
    status: StepStatus = Field(default=StepStatus.PENDING, description="Status de execução da etapa")
    result_summary: str | None = Field(default=None, description="Resumo das saídas, descobertas ou erros obtidos na execução")


class ExecutionPlan(BaseModel):
    """Representação estruturada de um plano completo de tarefas."""
    plan_id: str = Field(..., description="Identificador único do plano (ex: 'plan_20261106_001')")
    objective: str = Field(..., description="Objetivo central e contextualizado da solicitação")
    steps: list[PlanStep] = Field(default_factory=list, description="Sequência de etapas planejadas para alcançar o objetivo")
    success_criteria: str = Field(..., description="Critérios claros e mensuráveis para validar a conclusão com sucesso")
    current_step_id: str | None = Field(default=None, description="ID da etapa atualmente em execução")
    status: str = Field(default="created", description="Estado geral do plano: 'created', 'in_progress', 'completed', 'failed', 'replanned'")
    revision: int = Field(default=1, description="Contador de versão do plano (incrementado a cada replanejamento)")
    replan_reason: str | None = Field(default=None, description="Motivo do último replanejamento, se aplicável")
