"""Definição da Arquitetura de Orquestração e Planejamento Híbrido do Kraken IA:
- `root_agent` (`kraken_ia`): Ponto de entrada (`KrakenOrchestratorAgent`). Roteia saudações diretamente
  e encaminha solicitações operacionais ao planejador híbrido (`kraken_planner`) e ao coordenador (`kraken_coordinator`).
- `kraken_planner` (`KrakenPlanner`): Componente interno de planejamento híbrido que combina lógica
  determinística em Python com chamadas ao LLM sob demanda, entregando um `ExecutionPlan` validado.
- `kraken_coordinator` (`KrakenCoordinatorAgent`): Coordena determinísticamente os especialistas
  (`kraken_analyst`, `kraken_code`, `kraken_optimizer`) e o validador (`kraken_validator`) usando
  `ParallelAgent` (para etapas independentes) e `LoopAgent` (para validação iterativa e correção).
"""
from google.adk.models.lite_llm import LiteLlm

from kraken_ia.agents import (
    KrakenCoordinatorAgent,
    KrakenOrchestratorAgent,
    KrakenPlanner,
    KrakenValidatorAgent,
    create_kraken_analyst_agent,
    create_kraken_code_agent,
    create_kraken_optimizer_agent,
)
from kraken_ia.config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL
from kraken_ia.guardrails import (
    after_model_guardrail,
    after_tool_guardrail,
    before_model_guardrail,
    before_tool_guardrail,
)
from kraken_ia.prompts.orchestrator import KRAKEN_IA_INSTRUCTION

# Instancia o modelo via LiteLLM diretamente com as variáveis do config.py (.env)
language_model = LiteLlm(
    model=LLM_MODEL,
    api_key=LLM_API_KEY,
    api_base=LLM_API_BASE,
)

# 1. Agente Analista de Dados (Kraken Analyst - 3 ferramentas públicas)
kraken_analyst_agent = create_kraken_analyst_agent(language_model)

# 2. Agente Especialista em Feature Engineering e Pipelines (Kraken Code - 3 ferramentas públicas)
kraken_code_agent = create_kraken_code_agent(language_model)

# 3. Agente Especialista em Otimização de Código e Benchmarks (Kraken Optimizer - 3 ferramentas públicas)
kraken_optimizer_agent = create_kraken_optimizer_agent(language_model)

# 4. Agente Validador Determinístico Pós-Etapa (Kraken Validator)
kraken_validator_agent = KrakenValidatorAgent(name="kraken_validator")

# 5. Planejador Híbrido (Kraken Planner - Python determinístico + LLM sob demanda)
kraken_planner = KrakenPlanner(model=language_model)
kraken_planner_agent = kraken_planner

# 6. Agente Coordenador Determinístico de Execução (encapsula os especialistas e o validador)
kraken_coordinator_agent = KrakenCoordinatorAgent(
    name="kraken_coordinator",
    planner=kraken_planner,
    sub_agents=[
        kraken_analyst_agent,
        kraken_code_agent,
        kraken_optimizer_agent,
        kraken_validator_agent,
    ],
)

# 7. Agente Principal Orquestrador (Kraken IA)
# Nota: Os especialistas NÃO estão diretamente em root_agent.sub_agents, impedindo bypass do Planner/Coordinator.
root_agent = KrakenOrchestratorAgent(
    name="kraken_ia",
    model=language_model,
    planner=kraken_planner,
    description=(
        "Assistente inteligente de Ciência de Dados, Analytics, Feature Engineering e Engenharia de Pipelines. "
        "Roteia saudações diretamente e encaminha solicitações operacionais ao fluxo estruturado "
        "(kraken_planner -> kraken_coordinator -> especialistas)."
    ),
    static_instruction=KRAKEN_IA_INSTRUCTION,
    before_model_callback=before_model_guardrail,
    after_model_callback=after_model_guardrail,
    before_tool_callback=before_tool_guardrail,
    after_tool_callback=after_tool_guardrail,
    sub_agents=[
        kraken_coordinator_agent,
    ],
)
