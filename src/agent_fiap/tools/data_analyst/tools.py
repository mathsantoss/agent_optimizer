"""Ferramentas públicas expostas ao Data Analyst Agent no Google ADK:
1. analyze_dataset: exploração, estrutura, qualidade e estatísticas de datasets.
2. query_dataset: consultas analíticas SQL em memória com validação AST.
3. search_knowledge_base: recuperação semântica e Dicionário de Dados no ChromaDB.
"""
import json
from typing import Any

from agent_fiap.audit_logger import record_data_analysis_event
from agent_fiap.tools.data_analyst.services.dataset_service import (
    get_available_datasets_catalog,
    resolve_dataset_file,
)
from agent_fiap.tools.data_analyst.services.knowledge_service import search_knowledge_service
from agent_fiap.tools.data_analyst.services.profiling_service import profile_dataset_structure
from agent_fiap.tools.data_analyst.services.sql_service import execute_sql_service
from agent_fiap.tools.data_analyst.services.statistics_service import calculate_descriptive_statistics


def analyze_dataset(
    dataset_name: str = "",
    operation: str = "full",
    sample_size: int = 10_000,
) -> str:
    """
    Realiza a análise exploratória, verificação de estrutura, qualidade ou estatística de um dataset.

    Args:
        dataset_name: Nome do dataset (ex.: 'dados_vendas' ou 'dados_vendas.csv').
                      Se vazio ou 'list', retorna o catálogo de todos os datasets disponíveis.
        operation: Tipo de análise a executar:
                   - 'overview': catálogo de datasets ou resumo básico.
                   - 'structure': colunas, tipos, nulos, duplicatas, chaves e período temporal.
                   - 'statistics': resumo estatístico descritivo das colunas numéricas e outliers IQR.
                   - 'sample': amostra das primeiras linhas com sanitização.
                   - 'full': análise abrangente (estrutura + estatísticas descritivas + amostra).
        sample_size: Limite de linhas amostradas para proteção de memória (padrão: 10.000).

    Returns:
        JSON estruturado contendo status, resumo analítico, métricas e alertas de amostragem.
    """
    clean_target = dataset_name.strip()
    norm_op = operation.strip().lower() if operation else "full"

    # Se não especificou dataset ou pediu catálogo, lista os disponíveis
    if not clean_target or clean_target == "list" or norm_op == "overview" and not clean_target:
        catalog = get_available_datasets_catalog()
        record_data_analysis_event(
            action="analyze_dataset",
            target="catalogo",
            status="SUCESSO",
            summary_metrics={"total_datasets": len(catalog)},
        )
        payload = {
            "success": True,
            "operation": "analyze_dataset:catalog",
            "summary": f"{len(catalog)} dataset(s) disponível(is) em pipeline/dados/.",
            "data": {"datasets": catalog},
            "warnings": [],
            "errors": [],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    file_path, resolution_error = resolve_dataset_file(clean_target)
    if resolution_error or file_path is None:
        payload = {
            "success": False,
            "operation": f"analyze_dataset:{norm_op}",
            "summary": resolution_error or "Dataset não encontrado.",
            "data": {"dataset_solicitado": dataset_name},
            "warnings": [],
            "errors": [resolution_error or "Dataset não encontrado."],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    # Executa os serviços internos conforme a operação desejada
    structure_info: dict[str, Any] | None = None
    statistics_info: dict[str, Any] | None = None

    if norm_op in ("structure", "sample", "full"):
        structure_info = profile_dataset_structure(file_path, sample_size=sample_size)

    if norm_op in ("statistics", "full"):
        statistics_info = calculate_descriptive_statistics(file_path, sample_size=sample_size)

    # Consolida os dados no retorno padronizado
    consolidated_data: dict[str, Any] = {
        "dataset": file_path.stem,
        "arquivo": str(file_path.name),
    }
    warnings: list[str] = []

    if structure_info:
        if structure_info.get("vazio"):
            warnings.append("O arquivo está vazio (0 bytes ou 0 linhas).")
        if structure_info.get("amostragem_ativa"):
            warnings.append(f"Análise estrutural baseada em amostra de {structure_info.get('total_linhas_amostradas')} linhas.")
        if norm_op == "sample":
            consolidated_data["amostra_linhas"] = structure_info.get("amostra_3_linhas", [])
        else:
            consolidated_data["estrutura"] = structure_info

    if statistics_info:
        if statistics_info.get("amostragem_ativa"):
            warnings.append(f"Estatísticas descritivas calculadas sobre amostra de {statistics_info.get('limite_amostral')} linhas.")
        consolidated_data["estatisticas"] = statistics_info

    record_data_analysis_event(
        action=f"analyze_dataset:{norm_op}",
        target=file_path.stem,
        status="SUCESSO",
        summary_metrics={
            "operacao": norm_op,
            "amostragem_ativa": bool(warnings),
            "linhas_avaliadas": structure_info.get("total_linhas_amostradas") if structure_info else (statistics_info.get("total_linhas_avaliadas") if statistics_info else 0),
        },
    )

    summary_msg = f"Análise '{norm_op}' do dataset '{file_path.stem}' concluída com sucesso."
    payload = {
        "success": True,
        "operation": f"analyze_dataset:{norm_op}",
        "summary": summary_msg,
        "data": consolidated_data,
        "warnings": warnings,
        "errors": [],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def query_dataset(
    query: str,
    max_rows: int = 50,
) -> str:
    """
    Executa uma consulta SQL analítica (SELECT) nos datasets disponíveis em pipeline/dados/.
    As tabelas recebem o nome dos arquivos sem hífen/extensão (ex.: dados_vendas).

    Args:
        query: Consulta SQL analítica em formato ANSI/SQLite (somente SELECT permitido).
        max_rows: Limite de linhas retornadas (padrão: 50).

    Returns:
        JSON com a tabela formatada, registros, colunas e métricas de execução.
    """
    result = execute_sql_service(query, max_rows=max_rows)
    record_data_analysis_event(
        action="query_dataset",
        target=query[:120],
        status="SUCESSO" if result.get("success") else "ERRO_SQL",
        summary_metrics={
            "linhas": result.get("data", {}).get("total_linhas_retornadas", 0) if result.get("data") else 0,
            "sucesso": result.get("success", False),
        },
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


def search_knowledge_base(
    query: str,
    category_filter: str = "",
    table_filter: str = "",
    top_k: int = 3,
) -> str:
    """
    Consulta o Dicionário de Dados, regras de negócio e definições em pipeline/dados/conhecimento/.

    Args:
        query: Pergunta ou termos conceituais a buscar (ex.: 'faturamento price_x regra').
        category_filter: Filtro opcional por categoria (ex.: 'dicionario_dados', 'regras_negocio').
        table_filter: Filtro opcional pelo nome da tabela (ex.: 'dados_vendas').
        top_k: Quantidade máxima de trechos mais relevantes a retornar (padrão: 3).

    Returns:
        JSON estruturado com os trechos recuperados, scores de relevância e referências de origem.
    """
    result = search_knowledge_service(
        query=query,
        category_filter=category_filter,
        table_filter=table_filter,
        top_k=top_k,
    )
    record_data_analysis_event(
        action="search_knowledge_base",
        target=query[:100],
        status="SUCESSO" if result.get("success") else "ALERTA",
        summary_metrics={
            "total_recuperado": result.get("data", {}).get("total_recuperado", 0) if result.get("data") else 0,
            "maior_relevancia": result.get("data", {}).get("maior_relevancia", 0.0) if result.get("data") else 0.0,
        },
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)

