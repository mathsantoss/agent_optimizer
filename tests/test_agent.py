"""Testes automatizados para o Agent FIAP (Orquestrador, Agente Analista e Agente Otimizador) e suas ferramentas."""
import json
from pathlib import Path
from agent_fiap.agent import code_optimizer_agent, data_analyst_agent, root_agent
from agent_fiap.tools import code_tools, data_tools, knowledge_tools


def test_multi_agent_structure():
    """Valida a separação entre o Orquestrador, o Agente Analista e o Agente Otimizador."""
    assert root_agent.name == "agent_fiap"
    sub_agent_names = [agent.name for agent in root_agent.sub_agents]
    assert "data_analyst_agent" in sub_agent_names
    assert "code_optimizer_agent" in sub_agent_names

    # Ferramentas do Agente Analista de Dados
    analyst_tools = [tool.__name__ for tool in data_analyst_agent.tools]
    for expected_tool in [
        "list_datasets",
        "explore_dataset",
        "generate_statistical_summary",
        "execute_sql_query",
        "search_knowledge_base",
    ]:
        assert expected_tool in analyst_tools, f"Ferramenta {expected_tool} não encontrada no data_analyst_agent."

    # Ferramentas do Agente Especialista em Otimização e Criação de Código
    optimizer_tools = [tool.__name__ for tool in code_optimizer_agent.tools]
    for expected_tool in [
        "read_file",
        "analyze_pipeline_code",
        "profile_pipeline",
        "save_file",
        "run_pipeline",
        "compare_pipeline_runs",
        "run_tests",
        "list_datasets",
        "explore_dataset",
        "search_knowledge_base",
    ]:
        assert expected_tool in optimizer_tools, f"Ferramenta {expected_tool} não encontrada no code_optimizer_agent."


def test_list_datasets():
    """Testa a descoberta dinâmica de datasets ignorando a subpasta conhecimento."""
    result = data_tools.list_datasets()
    assert "tabela_sql" in result
    assert "dicionario_vendas" not in result


def test_explore_dataset():
    """Testa a inspeção de esquema, duplicatas, chaves candidatas e amostra de dados."""
    result = data_tools.explore_dataset("dados_vendas")
    parsed_data = json.loads(result)
    assert "colunas" in parsed_data
    assert "linhas_duplicadas" in parsed_data
    assert "chaves_candidatas" in parsed_data
    assert "amostra_3_linhas" in parsed_data
    first_column_metadata = next(iter(parsed_data["colunas"].values()))
    assert "percentual_nulos" in first_column_metadata


def test_generate_statistical_summary():
    """Testa a geração de resumo estatístico com percentis, nulos e detecção de outliers (IQR)."""
    result = data_tools.generate_statistical_summary("dados_vendas")
    assert "mean" in result.lower()
    assert "max" in result.lower()
    assert "outliers_iqr" in result.lower()
    assert "nulos" in result.lower()


def test_execute_sql_query_read_and_greatest():
    """Testa execução de consulta SQL com GREATEST entre duas colunas."""
    result = data_tools.execute_sql_query(
        "SELECT id_venda, GREATEST(preco_unitario, desconto) as maior_preco FROM dados_vendas LIMIT 3"
    )
    assert "erro" not in result.lower()
    assert "maior_preco" in result


def test_execute_sql_query_blocks_write_and_ast_validation():
    """Garante que comandos de escrita/DDL e erros de sintaxe são bloqueados pelo validador AST."""
    drop_result = data_tools.execute_sql_query("DROP TABLE dados_vendas")
    assert "proibido" in drop_result.lower()

    delete_result = data_tools.execute_sql_query("DELETE FROM dados_vendas")
    assert "proibido" in delete_result.lower()

    update_result = data_tools.execute_sql_query("UPDATE dados_vendas SET quantity = 0")
    assert "proibido" in update_result.lower()

    syntax_error_result = data_tools.execute_sql_query("SELECT FROM WHERE (")
    assert "erro" in syntax_error_result.lower()


def test_analyze_pipeline_code_detects_bottlenecks(monkeypatch):
    """Valida a detecção estática via AST de groupby repetido, to_datetime repetido, divisão e inplace=True."""
    from agent_fiap import config

    fixture_pipeline = Path(__file__).parent / "fixtures" / "projeto" / "pipeline" / "pipeline_prep.py"
    monkeypatch.setattr(config, "READ_DIRS", [fixture_pipeline.parent])
    monkeypatch.setattr(config, "PROJECT_ROOT", fixture_pipeline.parent.parent)

    analysis_output = code_tools.analyze_pipeline_code(str(fixture_pipeline))
    report = json.loads(analysis_output)

    assert report["has_run_entrypoint"] is True
    assert "calcular_metricas" in report["defined_functions"]

    descriptions = " ".join(issue["description"] for issue in report["issues"])
    categories = {issue["category"] for issue in report["issues"]}
    evidence_types = {issue["evidence_type"] for issue in report["issues"]}

    assert "groupby" in descriptions
    assert "to_datetime" in descriptions
    assert "inplace=True" in descriptions
    assert "Divisão direta" in descriptions
    assert "performance" in categories
    assert "quality" in categories
    assert "data_leakage" in categories
    assert "confirmed" in evidence_types
    assert "probable" in evidence_types


def test_read_and_save_file(tmp_path, monkeypatch):
    """Testa leitura, escrita segura, bloqueio de chamadas inseguras e backup automático via save_file."""
    from agent_fiap import config

    monkeypatch.setattr(config, "WRITE_DIRS", [tmp_path])
    monkeypatch.setattr(config, "READ_DIRS", [tmp_path])
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)

    target_file = tmp_path / "teste_script.py"

    # Arquivo vazio retorna aviso amigável
    target_file.touch()
    empty_result = code_tools.read_file(str(target_file))
    assert "vazio" in empty_result.lower()

    # Validação de sintaxe Python
    syntax_error_result = code_tools.save_file(str(target_file), "def invalido(:\n   pass")
    assert "erro de sintaxe" in syntax_error_result.lower()

    # Bloqueio de código inseguro via AST
    security_error_result = code_tools.save_file(str(target_file), "import os\nos.system('rm -rf /')")
    assert "erro de segurança" in security_error_result.lower()

    # Escrita válida
    write_result = code_tools.save_file(str(target_file), "print('versao_1')")
    assert "sucesso" in write_result.lower()

    # Leitura com conteúdo gravado
    read_result = code_tools.read_file(str(target_file))
    assert read_result == "print('versao_1')"

    # Backup automático ao sobrescrever
    code_tools.save_file(str(target_file), "print('versao_2')")
    assert (tmp_path / "teste_script.py.bak").read_text() == "print('versao_1')"
    assert (tmp_path / "teste_script.py").read_text() == "print('versao_2')"


def test_run_pipeline(tmp_path, monkeypatch):
    """Testa a execução de pipeline com retorno de sucesso e medição de tempo."""
    from agent_fiap import config

    monkeypatch.setattr(config, "READ_DIRS", [tmp_path])
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)

    script_file = tmp_path / "script_ok.py"
    script_file.write_text("print('EXECUTOU_COM_SUCESSO')")
    result = code_tools.run_pipeline(str(script_file))
    assert "SUCESSO" in result
    assert "s!" in result
    assert "EXECUTOU_COM_SUCESSO" in result


def test_profile_and_compare_pipeline_runs(tmp_path, monkeypatch):
    """Testa o profiling real (tempo, memória, linhas, hash) e o benchmark comparativo antes e depois."""
    from agent_fiap import config

    monkeypatch.setattr(config, "READ_DIRS", [tmp_path])
    monkeypatch.setattr(config, "WRITE_DIRS", [tmp_path])
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)

    baseline_code = (
        "import pandas as pd\n"
        "def run():\n"
        "    df = pd.DataFrame({'cliente': ['A', 'A', 'B'], 'valor': [10.0, 20.0, 30.0]})\n"
        "    df['soma'] = df.groupby('cliente')['valor'].transform('sum')\n"
        "    df['media'] = df.groupby('cliente')['valor'].transform('mean')\n"
        "    return df\n"
    )
    optimized_code = (
        "import pandas as pd\n"
        "def run():\n"
        "    df = pd.DataFrame({'cliente': ['A', 'A', 'B'], 'valor': [10.0, 20.0, 30.0]})\n"
        "    grouped = df.groupby('cliente')['valor']\n"
        "    df['soma'] = grouped.transform('sum')\n"
        "    df['media'] = grouped.transform('mean')\n"
        "    return df\n"
    )

    pipeline_file = tmp_path / "pipeline_prep.py"
    code_tools.save_file(str(pipeline_file), baseline_code)

    profile_output = code_tools.profile_pipeline(str(pipeline_file))
    profile_data = json.loads(profile_output)
    assert profile_data["execution_status"] == "success"
    assert profile_data["rows_processed"] == 3
    assert profile_data["column_count"] == 4
    assert profile_data["output_signature_hash"] is not None

    # Salva a versão otimizada (criando automaticamente pipeline_prep.py.bak)
    code_tools.save_file(str(pipeline_file), optimized_code)
    backup_file = tmp_path / "pipeline_prep.py.bak"

    comparison_output = code_tools.compare_pipeline_runs(
        baseline_file_path=str(backup_file),
        candidate_file_path=str(pipeline_file),
    )
    assert "Benchmark Comparativo de Pipeline" in comparison_output
    assert "Aprovada" in comparison_output
    assert '"results_equivalent": true' in comparison_output


def test_run_empty_pipeline(tmp_path, monkeypatch):
    """Testa execução de arquivo vazio retornando aviso claro."""
    from agent_fiap import config

    monkeypatch.setattr(config, "READ_DIRS", [tmp_path])
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)

    script_file = tmp_path / "vazio.py"
    script_file.touch()
    result = code_tools.run_pipeline(str(script_file))
    assert "vazio ou não existe" in result.lower()


def test_knowledge_incremental_sync_and_removal(tmp_path, monkeypatch):
    """Testa sincronização incremental por hash SHA-256, detecção de alterações e remoção de arquivos excluídos."""
    from agent_fiap import config

    knowledge_dir = tmp_path / "pipeline" / "dados" / "conhecimento"
    knowledge_dir.mkdir(parents=True)
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(config, "KNOWLEDGE_DIR", knowledge_dir)

    dictionary_file = knowledge_dir / "dicionario_vendas.json"
    dictionary_file.write_text(
        json.dumps({
            "metadata": {"category": "dicionario_dados", "table": "dados_vendas", "updated_at": "2026-10-30"},
            "description": "Tabela de vendas.",
            "columns": [{"name": "price_x", "data_type": "float", "description": "Preço praticado."}],
        }),
        encoding="utf-8",
    )

    extra_file = knowledge_dir / "temporario.md"
    extra_file.write_text("---\ncategoria: temporario\ntabela: temp\n---\n## Regra\nConteúdo temporário.", encoding="utf-8")

    # 1. Primeira indexação: adiciona todos os chunks
    first_sync = knowledge_tools.synchronize_knowledge_index()
    assert first_sync.added_or_updated_chunks > 0
    assert first_sync.unchanged_chunks == 0

    # 2. Segunda indexação sem mudanças: todos os chunks são identificados como inalterados pelo hash
    second_sync = knowledge_tools.synchronize_knowledge_index()
    assert second_sync.added_or_updated_chunks == 0
    assert second_sync.unchanged_chunks == first_sync.total_active_chunks

    # 3. Remoção de arquivo da origem: deve remover o chunk órfão do índice
    extra_file.unlink()
    third_sync = knowledge_tools.synchronize_knowledge_index()
    assert third_sync.removed_chunks == 1
    assert (tmp_path / ".rag" / "index_manifest.json").exists()


def test_search_knowledge_base():
    """Testa a busca no Dicionário de Dados JSON em pipeline/dados/conhecimento/ com filtros e reranking."""
    result = knowledge_tools.search_knowledge_base(
        query="price_x price_y faturamento dados_vendas",
        category_filter="dicionario_dados",
        table_filter="dados_vendas",
    )
    assert isinstance(result, str)
    assert "dicionario_vendas.json" in result
    assert "Relevância:" in result
    assert "Hash:" in result
