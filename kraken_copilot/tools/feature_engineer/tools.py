"""Ferramentas públicas expostas ao Feature Engineer Agent no Google ADK:
1. generate_feature_pipeline: projeta e gera pipelines de features completos em Pandas ou PySpark.
2. add_feature_to_pipeline: insere novas features calculadas em pipelines existentes com backup.
3. preview_features: prévia rápida de features calculadas em amostra com inspeção de nulos.
"""
from typing import Any

from kraken_copilot.audit_logger import record_code_validation_event
from kraken_copilot.schemas import ToolResult
from kraken_copilot.tools.data_analyst.services.dataset_service import (
    get_available_datasets_catalog,
)
from kraken_copilot.tools.data_analyst.services.knowledge_service import search_knowledge_service
from kraken_copilot.tools.code_optimizer.services.file_service import (
    get_default_workspace_pipeline,
    get_file_tmp_paths,
    get_pipeline_tmp_dir,
    read_source_file,
    resolve_pipeline_path,
    sync_pipeline_tmp_files,
    write_source_file,
)
from kraken_copilot.tools.feature_engineer.services.feature_injection_service import (
    inject_feature_into_pipeline_code,
)
from kraken_copilot.tools.feature_engineer.services.feature_preview_service import (
    preview_features_on_sample,
)
from kraken_copilot.tools.feature_engineer.services.pipeline_generator_service import (
    create_feature_pipeline_plan,
)


def _fetch_rag_context_for_dataset(dataset_name: str) -> list[dict[str, Any]]:
    """Recupera trechos de metadados e regras de negócio do RAG no krakenlake para enriquecer decisões de features."""
    try:
        rag_res = search_knowledge_service(
            query=f"{dataset_name} dicionario colunas regras negocio features",
            top_k=3,
        )
        if isinstance(rag_res, dict) and rag_res.get("success"):
            return (rag_res.get("data") or {}).get("resultados", [])
    except Exception:
        pass
    return []


def generate_feature_pipeline(
    dataset_name: str | None = None,
    framework: str = "pandas",
    target_file_path: str | None = None,
    features: list[dict[str, Any]] | None = None,
    save_to_disk: bool = False,
    proposed_code: str = "",
) -> str:
    """
    Projeta e gera um pipeline completo de Feature Engineering em Pandas ou PySpark para Machine Learning.
    Suporta qualquer dataset do catálogo (krakenlake/catalog/sources/) ou arquivo customizado, consultando RAG de metadados.

    Args:
        dataset_name: Nome do dataset fonte (ex: 'dados_vendas') ou caminho do arquivo. Se omitido, descobre automaticamente no catálogo.
        framework: Framework de dados desejado: 'pandas' ou 'pyspark'.
        target_file_path: Caminho do arquivo alvo do pipeline (opcional; descobre dinamicamente no workspace).
        features: Lista opcional de dicionários com as features a criar (name, expression, category, description).
                  Se omitido, infere dinamicamente do schema do dataset.
        save_to_disk: Se True, grava o pipeline gerado no disco. Se False, exibe a proposta e o código para aprovação.
        proposed_code: Código Python completo opcional caso o especialista deseje fornecer um pipeline customizado sob medida.

    Returns:
        JSON com as especificações das features geradas, código do pipeline, contexto RAG e status.
    """
    if not target_file_path or not str(target_file_path).strip():
        target_file_path = get_default_workspace_pipeline()
    fw = framework.strip().lower()
    if fw not in ("pandas", "pyspark"):
        return ToolResult.fail(
            summary=f"Framework inválido '{framework}'. Escolha entre 'pandas' ou 'pyspark'.",
            operation="generate_feature_pipeline",
        ).to_json()

    clean_target = target_file_path.strip()

    if not dataset_name or not str(dataset_name).strip():
        catalog = get_available_datasets_catalog()
        if catalog:
            clean_dataset = str(catalog[0]["nome"])
        else:
            return ToolResult.fail(
                summary="Nenhum dataset disponível encontrado no catálogo do KrakenLake (krakenlake/catalog/sources/).",
                operation="generate_feature_pipeline",
            ).to_json()
    else:
        clean_dataset = str(dataset_name).strip()

    plan = create_feature_pipeline_plan(
        dataset_name=clean_dataset,
        framework=fw,
        target_file_path=clean_target,
        features=features,
    )

    final_code = plan.code
    clean_custom_code = (proposed_code or "").strip()
    if clean_custom_code:
        import ast
        try:
            ast.parse(clean_custom_code)
            final_code = clean_custom_code
        except SyntaxError as syn_err:
            return ToolResult.fail(
                summary=f"O código proposto contém erro de sintaxe na linha {syn_err.lineno}: {syn_err.msg}",
                operation="generate_feature_pipeline",
                errors=str(syn_err),
            ).to_json()
    elif save_to_disk and not features:
        try:
            _, opt_tmp = get_file_tmp_paths(clean_target)
            if opt_tmp.is_file() and opt_tmp.stat().st_size > 0:
                final_code = opt_tmp.read_text(encoding="utf-8")
        except Exception:
            pass

    current_code = ""
    try:
        read_res = read_source_file(clean_target)
        if read_res.get("success"):
            current_code = read_res.get("content", "")
    except Exception:
        current_code = ""

    try:
        sync_pipeline_tmp_files(
            original_content=current_code,
            optimized_content=final_code,
            target_file=clean_target,
        )
    except Exception:
        pass

    rag_context = _fetch_rag_context_for_dataset(plan.source_dataset)

    data_payload: dict[str, Any] = {
        "framework": fw,
        "dataset_origem": plan.source_dataset,
        "arquivo_alvo": clean_target,
        "arquivo": clean_target,
        "file_path": clean_target,
        "total_features_planejadas": len(plan.features),
        "features": [f.model_dump() for f in plan.features],
        "codigo_gerado": final_code,
        "proposed_code": final_code,
        "contexto_rag_metadados": rag_context,
        "requer_confirmacao": not save_to_disk,
        "gravado_em_disco": False,
    }

    if not save_to_disk:
        summary_msg = (
            f"Plano de Feature Engineering ({fw.upper()}) elaborado com sucesso com "
            f"{len(plan.features)} features planejadas para o dataset '{plan.source_dataset}' em '{clean_target}'. "
            "Para gravar no disco, solicite a confirmação com save_to_disk=True."
        )
        return ToolResult.ok(
            summary=summary_msg,
            operation="generate_feature_pipeline:proposal",
            data=data_payload,
        ).to_json()

    # Gravação no disco
    try:
        resolved_path = resolve_pipeline_path(clean_target, allow_write=True)
        write_res = write_source_file(resolved_path, final_code)
        if not write_res.get("success"):
            return ToolResult.fail(
                summary=f"Falha ao salvar o pipeline no disco: {write_res.get('error')}",
                operation="generate_feature_pipeline:apply",
                errors=write_res.get("error", "Erro ao gravar"),
            ).to_json()

        data_payload["gravado_em_disco"] = True
        data_payload["requer_confirmacao"] = False
        data_payload["linhas_gravadas"] = write_res.get("line_count")
        data_payload["backup_criado"] = write_res.get("backup_created")

        record_code_validation_event(
            action="generate_feature_pipeline",
            file_path=clean_target,
            status="SUCESSO",
            details=f"{len(plan.features)} features geradas",
        )

        summary_msg = (
            f"Pipeline de Feature Engineering ({fw.upper()}) gravado com SUCESSO em '{clean_target}' "
            f"({write_res.get('line_count')} linhas). {len(plan.features)} features implementadas."
        )
        return ToolResult.ok(
            summary=summary_msg,
            operation="generate_feature_pipeline:apply",
            data=data_payload,
        ).to_json()

    except Exception as err:
        return ToolResult.fail(
            summary=f"Erro ao criar pipeline: {err}",
            operation="generate_feature_pipeline",
            errors=str(err),
        ).to_json()


def add_feature_to_pipeline(
    file_path: str | None = None,
    feature_name: str = "",
    expression: str = "",
    proposed_code: str = "",
    framework: str = "pandas",
    description: str = "",
    confirmed_by_user: bool = False,
) -> str:
    """
    Adiciona uma nova feature ao pipeline. A LLM compreende o script existente e pode fornecer diretamente
    o código completo e limpo reescrito em 'proposed_code', ou especificar 'feature_name' e 'expression'.

    Args:
        file_path: Caminho do script de pipeline existente (opcional; descobre dinamicamente no workspace).
        feature_name: Nome identificador da nova coluna (ex.: 'ticket_medio_cliente').
        expression: Expressão de cálculo da feature (ex.: "df['quantity'] * df['price_x']").
        proposed_code: Código Python completo reescrito pela LLM com a feature incorporada de forma limpa e idiomática.
        framework: Framework utilizado: 'pandas' ou 'pyspark'.
        description: Explicação de negócio da feature.
        confirmed_by_user: Se False, apresenta a proposta com diff para aprovação no chat. Se True, grava e cria backup (.bak).

    Returns:
        JSON com o status, diff da alteração e confirmação de gravação.
    """
    if not file_path or not str(file_path).strip():
        file_path = get_default_workspace_pipeline()
    clean_target = file_path.strip()
    clean_name = feature_name.strip()
    clean_expr = expression.strip()
    clean_proposed = proposed_code.strip()
    fw = framework.strip().lower()

    read_res = read_source_file(clean_target)
    if not read_res.get("success"):
        return ToolResult.fail(
            summary=f"Arquivo '{clean_target}' não pôde ser lido: {read_res.get('error')}",
            operation="add_feature_to_pipeline",
            errors=read_res.get("error", "Arquivo não encontrado"),
        ).to_json()

    current_code = read_res.get("content", "")

    # Se confirmou aplicação sem passar código novamente, recupera proposta pendente de tmp/<stem>_otimizado.bak
    if confirmed_by_user and not clean_proposed and not (clean_name and clean_expr):
        try:
            _, opt_tmp = get_file_tmp_paths(clean_target)
            if opt_tmp.is_file() and opt_tmp.stat().st_size > 0:
                clean_proposed = opt_tmp.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    # Se a LLM forneceu o código completo compreendido e reescrito
    if clean_proposed:
        import ast
        try:
            ast.parse(clean_proposed)
            new_code = clean_proposed
        except SyntaxError as syn_err:
            return ToolResult.fail(
                summary=f"O código proposto pela LLM contém erro de sintaxe na linha {syn_err.lineno}: {syn_err.msg}",
                operation="add_feature_to_pipeline",
                errors=str(syn_err),
            ).to_json()
    else:
        if not clean_name or not clean_expr:
            return ToolResult.fail(
                summary="Forneça 'proposed_code' com o script reescrito, ou passe 'feature_name' e 'expression'.",
                operation="add_feature_to_pipeline",
                errors=["Parâmetros obrigatórios ausentes."],
            ).to_json()

        # Se o arquivo alvo no workspace estiver vazio (0 linhas), gera um pipeline completo do zero incluindo a feature!
        if not current_code.strip():
            catalog = get_available_datasets_catalog()
            default_ds = str(catalog[0]["nome"]) if catalog else "dados_vendas"
            plan = create_feature_pipeline_plan(
                dataset_name=default_ds,
                framework=fw,
                target_file_path=clean_target,
                features=[
                    {
                        "name": clean_name,
                        "category": "custom",
                        "expression": clean_expr,
                        "description": description or f"Feature {clean_name}",
                    }
                ],
            )
            new_code = plan.code
        else:
            new_code, error = inject_feature_into_pipeline_code(
                original_code=current_code,
                feature_name=clean_name,
                expression=clean_expr,
                framework=fw,
                description=description,
            )
            if error:
                return ToolResult.fail(
                    summary=f"Não foi possível incorporar a feature: {error}",
                    operation="add_feature_to_pipeline",
                    errors=error,
                ).to_json()

    # Sincroniza arquivos temporários de backup e proposta para habilitar o Diff e ApprovalCard por arquivo
    try:
        sync_pipeline_tmp_files(
            original_content=current_code,
            optimized_content=new_code,
            target_file=clean_target,
        )
    except Exception:
        pass

    if not confirmed_by_user:
        return ToolResult.ok(
            summary=(
                f"Proposta de inclusão da feature '{clean_name or 'nova_feature'}' elaborada para '{clean_target}'. "
                "O código completo e o diff estão prontos. Deseja aprovar e aplicar no script do workspace?"
            ),
            operation="add_feature_to_pipeline:proposal",
            data={
                "arquivo": clean_target,
                "file_path": clean_target,
                "feature": clean_name or "nova_feature",
                "framework": fw,
                "expressao": clean_expr,
                "proposed_code": new_code,
                "codigo_gerado": new_code,
                "requer_confirmacao": True,
                "trecho_codigo": f"# {description}\ndf['{clean_name}'] = {clean_expr}" if fw == "pandas" else f"df = df.withColumn('{clean_name}', {clean_expr})",
            },
        ).to_json()

    resolved_path = resolve_pipeline_path(clean_target, allow_write=True)
    write_res = write_source_file(resolved_path, new_code)
    if not write_res.get("success"):
        return ToolResult.fail(
            summary=f"Erro ao salvar arquivo atualizado: {write_res.get('error')}",
            operation="add_feature_to_pipeline:apply",
            errors=write_res.get("error", "Erro de gravação"),
        ).to_json()

    record_code_validation_event(
        action=f"add_feature:{clean_name}",
        file_path=clean_target,
        status="SUCESSO",
        details=f"Feature {clean_name} adicionada ao pipeline",
    )

    return ToolResult.ok(
        summary=(
            f"Feature '{clean_name}' adicionada com SUCESSO ao pipeline '{clean_target}'. "
            f"Backup seguro salvo em '{write_res.get('backup_file')}'."
        ),
        operation="add_feature_to_pipeline:apply",
        data={
            "arquivo": clean_target,
            "file_path": clean_target,
            "feature": clean_name,
            "backup_criado": write_res.get("backup_created"),
            "arquivo_backup": write_res.get("backup_file"),
            "linhas_totais": write_res.get("line_count"),
        },
    ).to_json()


def preview_features(
    dataset_name: str | None = None,
    framework: str = "pandas",
    feature_name: str = "",
    expression: str = "",
    sample_rows: int = 100,
) -> str:
    """
    Executa uma prévia rápida em amostra de qualquer dataset para validar o cálculo e resultado de novas features,
    retornando também o catálogo de colunas e o contexto de metadados (RAG) do KrakenLake.

    Args:
        dataset_name: Nome do dataset no catálogo (ex: 'dados_vendas') ou caminho do arquivo. Se omitido, descobre automaticamente.
        framework: Framework: 'pandas' ou 'pyspark'.
        feature_name: Nome opcional de uma feature específica a calcular.
        expression: Expressão de cálculo da feature em Pandas/PySpark. Se vazio, infere e avalia features a partir do schema do dataset.
        sample_rows: Quantidade de linhas para a amostra de validação (padrão: 100).

    Returns:
        JSON estruturado com amostra dos dados gerados, novas colunas, verificação de nulos e contexto RAG.
    """
    if not dataset_name or not str(dataset_name).strip():
        catalog = get_available_datasets_catalog()
        clean_dataset = str(catalog[0]["nome"]) if catalog else "dados_vendas"
    else:
        clean_dataset = str(dataset_name).strip()

    custom_exprs = None
    if feature_name.strip() and expression.strip():
        custom_exprs = {feature_name.strip(): expression.strip()}

    summary = preview_features_on_sample(
        dataset_name=clean_dataset,
        feature_expressions=custom_exprs,
        framework=framework,
        sample_rows=sample_rows,
    )

    if summary.total_sample_rows == 0:
        return ToolResult.fail(
            summary=f"Não foi possível gerar a prévia para o dataset '{dataset_name}'.",
            operation="preview_features",
            errors=["Dataset não encontrado ou falha na leitura da amostra."],
        ).to_json()

    dump_data = summary.model_dump()
    dump_data["contexto_rag_metadados"] = _fetch_rag_context_for_dataset(summary.source_dataset)
    dump_data["datasets_disponiveis"] = get_available_datasets_catalog()

    return ToolResult.ok(
        summary=(
            f"Prévia executada com sucesso sobre {summary.total_sample_rows} linhas de '{summary.source_dataset}'. "
            f"{summary.new_features_count} feature(s) calculada(s): {', '.join(summary.new_columns)}."
        ),
        operation="preview_features",
        data=dump_data,
    ).to_json()

