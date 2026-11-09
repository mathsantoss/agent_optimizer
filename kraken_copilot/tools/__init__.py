"""Exportação centralizada das ferramentas públicas do Kraken Copilot.

Arquitetura com três agentes especialistas (3 ferramentas cada):
1. kraken_analyst:
   - analyze_dataset
   - query_dataset
   - search_knowledge_base
2. kraken_code:
   - generate_feature_pipeline
   - add_feature_to_pipeline
   - preview_features
3. kraken_optimizer:
   - inspect_pipeline
   - optimize_pipeline
   - validate_pipeline
"""
from kraken_copilot.tools.code_optimizer import (
    inspect_pipeline,
    optimize_pipeline,
    validate_pipeline,
)
from kraken_copilot.tools.data_analyst import (
    analyze_dataset,
    query_dataset,
    search_knowledge_base,
)
from kraken_copilot.tools.feature_engineer import (
    add_feature_to_pipeline,
    generate_feature_pipeline,
    preview_features,
)

__all__ = [
    "analyze_dataset",
    "query_dataset",
    "search_knowledge_base",
    "add_feature_to_pipeline",
    "generate_feature_pipeline",
    "preview_features",
    "inspect_pipeline",
    "optimize_pipeline",
    "validate_pipeline",
]
