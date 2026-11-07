"""Ferramentas públicas expostas ao Feature Engineer Agent no Google ADK:
1. generate_feature_pipeline: projeta e gera pipelines de features completos em Pandas ou PySpark.
2. add_feature_to_pipeline: insere novas features calculadas em pipelines existentes com backup.
3. preview_features: prévia rápida de features calculadas em amostra com inspeção de nulos.
"""
from typing import Any

from kraken_ia.audit_logger import record_code_validation_event
from kraken_ia.schemas import ToolResult
from kraken_ia.tools.code_optimizer.services.file_service import (
    read_source_file,
    resolve_pipeline_path,
    write_source_file,
)
from kraken_ia.tools.feature_engineer.services.feature_injection_service import (
    inject_feature_into_pipeline_code,
)
from kraken_ia.tools.feature_engineer.services.feature_preview_service import (
    preview_features_on_sample,
)
from kraken_ia.tools.feature_engineer.services.pipeline_generator_service import (
    create_feature_pipeline_plan,
)


def generate_feature_pipeline(
    dataset_name: str = "dados_vendas",
    framework: str = "pandas",
    target_file_path: str = "pipeline/pipeline_prep.py",
    features: list[dict[str, Any]] | None = None,
    save_to_disk: bool = False,
) -> str:
    """
    Projeta e gera um pipeline completo de Feature Engineering em Pandas ou PySpark para Machine Learning.
    Suporta qualquer dataset e permite especificar features customizadas ou inferir automaticamente.

    Args:
        dataset_name: Nome do dataset fonte em pipeline/dados/ ou arquivo arbitrário.
        framework: Framework de dados desejado: 'pandas' ou 'pyspark'.
        target_file_path: Caminho do arquivo alvo do pipeline (padrão único: 'pipeline/pipeline_prep.py').
        features: Lista opcional de dicionários com as features a criar (name, expression, category, description).
                  Se omitido, infere dinamicamente do schema do dataset.
        save_to_disk: Se True, grava o pipeline gerado no disco. Se False, exibe a proposta e o código para aprovação.

    Returns:
        JSON com as especificações das features geradas, código do pipeline e status.
    """
    fw = framework.strip().lower()
    if fw not in ("pandas", "pyspark"):
        return ToolResult.fail(
            summary=f"Framework inválido '{framework}'. Escolha entre 'pandas' ou 'pyspark'.",
            operation="generate_feature_pipeline",
        ).to_json()

    clean_target = target_file_path.strip()
    clean_dataset = dataset_name.strip()
    plan = create_feature_pipeline_plan(
        dataset_name=clean_dataset,
        framework=fw,
        target_file_path=clean_target,
        features=features,
    )

    data_payload: dict[str, Any] = {
        "framework": fw,
        "dataset_origem": dataset_name,
        "arquivo_alvo": clean_target,
        "total_features_planejadas": len(plan.features),
        "features": [f.model_dump() for f in plan.features],
        "codigo_gerado": plan.code,
        "gravado_em_disco": False,
    }

    if not save_to_disk:
        summary_msg = (
            f"Plano de Feature Engineering ({fw.upper()}) elaborado com sucesso com "
            f"{len(plan.features)} features planejadas para o dataset '{dataset_name}'. "
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
        write_res = write_source_file(resolved_path, plan.code)
        if not write_res.get("success"):
            return ToolResult.fail(
                summary=f"Falha ao salvar o pipeline no disco: {write_res.get('error')}",
                operation="generate_feature_pipeline:apply",
                errors=write_res.get("error", "Erro ao gravar"),
            ).to_json()

        data_payload["gravado_em_disco"] = True
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
    file_path: str = "pipeline/pipeline_prep.py",
    feature_name: str = "",
    expression: str = "",
    framework: str = "pandas",
    description: str = "",
    confirmed_by_user: bool = False,
) -> str:
    """
    Insere uma nova feature específica em um script de pipeline existente (Pandas ou PySpark) de forma segura.

    Args:
        file_path: Caminho do script de pipeline existente (padrão: 'pipeline/pipeline_prep.py').
        feature_name: Nome identificador da nova coluna (ex.: 'ticket_medio_cliente').
        expression: Expressão de cálculo da feature (ex.: "df['quantity'] * df['price_x']").
        framework: Framework utilizado: 'pandas' ou 'pyspark'.
        description: Explicação de negócio da feature.
        confirmed_by_user: Se False, apresenta a prévia da alteração no código. Se True, grava e cria backup (.bak).

    Returns:
        JSON com o status, diff da alteração e confirmação de gravação.
    """
    clean_target = file_path.strip()
    clean_name = feature_name.strip()
    clean_expr = expression.strip()
    fw = framework.strip().lower()

    if not clean_name or not clean_expr:
        return ToolResult.fail(
            summary="Para adicionar uma feature, forneça 'feature_name' e 'expression'.",
            operation="add_feature_to_pipeline",
            errors=["Parâmetros obrigatórios ausentes."],
        ).to_json()

    read_res = read_source_file(clean_target)
    if not read_res.get("success"):
        return ToolResult.fail(
            summary=f"Arquivo '{clean_target}' não pôde ser lido: {read_res.get('error')}",
            operation="add_feature_to_pipeline",
            errors=read_res.get("error", "Arquivo não encontrado"),
        ).to_json()

    current_code = read_res.get("content", "")
    new_code, error = inject_feature_into_pipeline_code(
        original_code=current_code,
        feature_name=clean_name,
        expression=clean_expr,
        framework=fw,
        description=description,
    )

    if error:
        return ToolResult.fail(
            summary=f"Não foi possível injetar a feature: {error}",
            operation="add_feature_to_pipeline",
            errors=error,
        ).to_json()

    if not confirmed_by_user:
        return ToolResult.ok(
            summary=(
                f"Proposta de inclusão da feature '{clean_name}' elaborada para '{clean_target}'. "
                "Nenhum arquivo foi alterado no disco. Solicite confirmação ao usuário antes de gravar."
            ),
            operation="add_feature_to_pipeline:proposal",
            data={
                "arquivo": clean_target,
                "feature": clean_name,
                "framework": fw,
                "expressao": clean_expr,
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
            "feature": clean_name,
            "backup_criado": write_res.get("backup_created"),
            "arquivo_backup": write_res.get("backup_file"),
            "linhas_totais": write_res.get("line_count"),
        },
    ).to_json()


def preview_features(
    dataset_name: str = "dados_vendas",
    framework: str = "pandas",
    feature_name: str = "",
    expression: str = "",
    sample_rows: int = 100,
) -> str:
    """
    Executa uma prévia rápida em amostra de qualquer dataset para validar o cálculo e resultado de novas features.

    Args:
        dataset_name: Nome do dataset em pipeline/dados/ ou caminho do arquivo.
        framework: Framework: 'pandas' ou 'pyspark'.
        feature_name: Nome opcional de uma feature específica a calcular.
        expression: Expressão de cálculo da feature em Pandas/PySpark. Se vazio, infere e avalia features a partir do schema do dataset.
        sample_rows: Quantidade de linhas para a amostra de validação (padrão: 100).

    Returns:
        JSON estruturado com amostra dos dados gerados, novas colunas e verificação de nulos.
    """
    custom_exprs = None
    if feature_name.strip() and expression.strip():
        custom_exprs = {feature_name.strip(): expression.strip()}

    summary = preview_features_on_sample(
        dataset_name=dataset_name,
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

    return ToolResult.ok(
        summary=(
            f"Prévia executada com sucesso sobre {summary.total_sample_rows} linhas de '{dataset_name}'. "
            f"{summary.new_features_count} feature(s) calculada(s): {', '.join(summary.new_columns)}."
        ),
        operation="preview_features",
        data=summary.model_dump(),
    ).to_json()

