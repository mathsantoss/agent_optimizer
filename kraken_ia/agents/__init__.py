"""Sub-agentes especialistas, planejador híbrido e agentes de coordenação do Kraken IA."""
from kraken_ia.agents.code_optimizer_agent import create_kraken_optimizer_agent
from kraken_ia.agents.coordinator_agent import (
    KrakenCoordinatorAgent,
    KrakenOrchestratorAgent,
    KrakenValidatorAgent,
    classify_request_intent,
)
from kraken_ia.agents.data_analyst_agent import create_kraken_analyst_agent
from kraken_ia.agents.feature_engineer_agent import create_kraken_code_agent
from kraken_ia.agents.planner_agent import KrakenPlanner, synthesize_plan_for_request
