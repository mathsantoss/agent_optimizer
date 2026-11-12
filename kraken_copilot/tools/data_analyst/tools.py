"""Ferramentas públicas expostas ao Data Analyst Agent no Google ADK:
1. analyze_dataset: exploração, estrutura, qualidade e estatísticas de datasets.
2. query_dataset: consultas analíticas SQL em memória com validação AST.
3. search_knowledge_base: recuperação semântica e Dicionário de Dados no ChromaDB.
"""
import json
from typing import Any

from kraken_copilot.audit_logger import record_data_analysis_event
from kraken_copilot.schemas import ToolResult
from kraken_copilot.tools.data_analyst.services.dataset_service import (
    get_available_datasets_catalog,
    resolve_dataset_file,
)
from kraken_copilot.tools.data_analyst.services.knowledge_service import search_knowledge_service
from kraken_copilot.tools.data_analyst.services.profiling_service import profile_dataset_structure
from kraken_copilot.tools.data_analyst.services.sql_service import execute_sql_service
from kraken_copilot.tools.data_analyst.services.statistics_service import calculate_descriptive_statistics
from kraken_copilot.tools.data_analyst.services.eda_service import (
    load_dataset_info,
    analyze_missing_values,
    analyze_univariate_distributions,
    analyze_correlations,
    detect_outliers_iqr,
    analyze_target_relationship,
    run_data_cleaning_pipeline,
    generate_visualization_specs,
    export_report_document,
    save_script_to_workspace,
    run_evidently_quality_report,
)


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
        return ToolResult.ok(
            summary=f"{len(catalog)} dataset(s) disponível(is) no datalake (krakenlake/catalog/sources/).",
            operation="analyze_dataset:catalog",
            data={"datasets": catalog},
        ).to_json()

    file_path, resolution_error = resolve_dataset_file(clean_target)
    if resolution_error or file_path is None:
        return ToolResult.fail(
            summary=resolution_error or "Dataset não encontrado.",
            operation=f"analyze_dataset:{norm_op}",
            errors=resolution_error or "Dataset não encontrado.",
            data={"dataset_solicitado": dataset_name},
        ).to_json()

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
        if structure_info.get("kraken_data_profile"):
            consolidated_data["kraken_data_profile"] = structure_info.get("kraken_data_profile")

    if statistics_info:
        if statistics_info.get("amostragem_ativa"):
            warnings.append(f"Estatísticas descritivas calculadas sobre amostra de {statistics_info.get('limite_amostral')} linhas.")
        consolidated_data["estatisticas"] = statistics_info
        if statistics_info.get("kraken_statistical_report"):
            consolidated_data["kraken_statistical_report"] = statistics_info.get("kraken_statistical_report")

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
    return ToolResult.ok(
        summary=summary_msg,
        operation=f"analyze_dataset:{norm_op}",
        data=consolidated_data,
        warnings=warnings,
    ).to_json()


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


def load_data_tool(dataset_name: str, nrows: int = 10_000) -> str:
    """
    Carrega o dataset e retorna metadados cadastrais, volumetria, tipos de dados e amostra.

    Args:
        dataset_name: Nome do dataset no catálogo (ex.: 'dados_vendas' ou 'dados_vendas.csv').
        nrows: Limite de linhas amostradas para proteção de memória (padrão: 10.000).
    """
    result = load_dataset_info(dataset_name, max_rows=nrows)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


def missing_value_analysis_tool(dataset_name: str) -> str:
    """
    Sumariza colunas com dados faltantes (nulos), percentual de ausência e criticidade.

    Args:
        dataset_name: Nome do dataset no catálogo (ex.: 'dados_vendas').
    """
    result = analyze_missing_values(dataset_name)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


def univariate_analysis_tool(dataset_name: str, column: str = "") -> str:
    """
    Analisa a distribuição estatística de features numéricas (média, mediana, IQR, assimetria/skewness, curtose).

    Args:
        dataset_name: Nome do dataset (ex.: 'dados_vendas').
        column: Nome específico da coluna numérica (opcional; se vazio analisa todas).
    """
    result = analyze_univariate_distributions(dataset_name, column=column)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


def correlation_analysis_tool(dataset_name: str, method: str = "pearson") -> str:
    """
    Calcula a matriz de correlação e destaca pares com forte correlação linear/monotônica.

    Args:
        dataset_name: Nome do dataset (ex.: 'dados_vendas').
        method: Método de correlação ('pearson' ou 'spearman', padrão: 'pearson').
    """
    result = analyze_correlations(dataset_name, method=method)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


def outlier_detection_tool(dataset_name: str, column: str = "") -> str:
    """
    Identifica anomalias e outliers através do método da amplitude interquartil (IQR).

    Args:
        dataset_name: Nome do dataset (ex.: 'dados_vendas').
        column: Coluna numérica específica a verificar (opcional).
    """
    result = detect_outliers_iqr(dataset_name, column=column)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


def target_relationship_tool(dataset_name: str, target_column: str, feature_column: str = "") -> str:
    """
    Visualiza e quantifica a relação entre preditores e uma variável alvo (target).

    Args:
        dataset_name: Nome do dataset (ex.: 'dados_vendas').
        target_column: Nome da coluna alvo (ex.: 'price_x' ou 'categoria').
        feature_column: Coluna opcional para agregação comparativa.
    """
    result = analyze_target_relationship(dataset_name, target_column=target_column, feature_column=feature_column)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


def clean_dataset_tool(
    dataset_name: str,
    fill_missing_strategy: str = "auto",
    drop_duplicates: bool = True,
    output_filename: str = "",
) -> str:
    """
    Executa o pipeline de Data Cleaning: preenche nulos, remove duplicatas e normaliza colunas temporais.

    Args:
        dataset_name: Nome do dataset de entrada.
        fill_missing_strategy: Estratégia de preenchimento ('auto', 'median', 'mean').
        drop_duplicates: Se deve remover linhas 100% duplicadas (padrão: True).
        output_filename: Nome opcional do arquivo limpo a gravar em krakenlake/workspace/.
    """
    result = run_data_cleaning_pipeline(
        dataset_name=dataset_name,
        fill_missing_strategy=fill_missing_strategy,
        drop_duplicates=drop_duplicates,
        output_filename=output_filename,
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


def generate_visualizations_tool(dataset_name: str, chart_type: str = "bar", x: str = "", y: str = "") -> str:
    """
    Gera especificações visuais de dados para renderização de gráficos interativos (barras, histogramas, linhas).

    Args:
        dataset_name: Nome do dataset.
        chart_type: Tipo de gráfico ('bar', 'histogram', 'line', 'scatter', 'pie').
        x: Coluna do eixo horizontal.
        y: Coluna do eixo vertical (métrica).
    """
    result = generate_visualization_specs(dataset_name, chart_type=chart_type, x=x, y=y)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


def export_report_tool(dataset_name: str, report_format: str = "markdown", title: str = "") -> str:
    """
    Gera um relatório analítico consolidado e o salva como documento Markdown/PDF em krakenlake/reports/.

    Args:
        dataset_name: Nome do dataset analisado.
        report_format: Formato ('markdown' ou 'pdf', padrão: 'markdown').
        title: Título customizado do documento (opcional).
    """
    result = export_report_document(dataset_name, report_format=report_format, title=title)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


def save_workspace_script_tool(script_name: str, code: str, overwrite: bool = True) -> str:
    """
    Cria ou atualiza um script Python (.py) diretamente no diretório do workspace do repositório (krakenlake/workspace/).

    Args:
        script_name: Nome do script com extensão (ex.: 'etl_vendas.py' ou 'pipeline_limpeza.py').
        code: Código Python formatado e encapsulado em funções 'def'.
        overwrite: Se deve sobrescrever caso já exista (padrão: True).
    """
    result = save_script_to_workspace(script_name=script_name, code=code, overwrite=overwrite)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


def evidently_quality_report_tool(dataset_name: str, save_html: bool = True) -> str:
    """
    Executa a suíte de qualidade de dados profissional Evidently AI para o dataset.
    Métricas prontas: linhas, colunas, tipos, contagem de nulos, linhas duplicadas, colunas vazias e quase constantes.
    Salva opcionalmente o relatório interativo HTML em krakenlake/workspace/reports/.

    Args:
        dataset_name: Nome do dataset cadastrado no catálogo (ex.: 'dados_vendas').
        save_html: Se deve exportar o dashboard interativo HTML (padrão: True).
    """
    result = run_evidently_quality_report(dataset_name=dataset_name, save_html=save_html)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)

