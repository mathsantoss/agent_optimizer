"""Sub-agentes especialistas, planejador híbrido e agentes de coordenação do Kraken Copilot."""
from kraken_copilot.agents.code_optimizer_agent import create_kraken_optimizer_agent
from kraken_copilot.agents.coordinator_agent import (
    KrakenCoordinatorAgent,
    KrakenOrchestratorAgent,
    KrakenValidatorAgent,
    classify_request_intent,
)
from kraken_copilot.agents.data_analyst_agent import create_kraken_analyst_agent
from kraken_copilot.agents.feature_engineer_agent import create_kraken_code_agent
from kraken_copilot.agents.planner_agent import KrakenPlanner, synthesize_plan_for_request
