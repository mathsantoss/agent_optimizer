"""Testes automatizados para o Agent FIAP (Orquestrador, Agente Analista e Agente Otimizador) e suas ferramentas."""
import json
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
        "save_file",
        "run_pipeline",
        "run_tests",
        "list_datasets",
        "explore_dataset",
        "search_knowledge_base",
    ]:
        assert expected_tool in optimizer_tools, f"Ferramenta {expected_tool} não encontrada no code_optimizer_agent."


def test_list_datasets():
    """Testa a descoberta dinâmica de datasets."""
    result = data_tools.list_datasets()
    assert "tabela_sql" in result


def test_explore_dataset():
    """Testa a inspeção de esquema e amostra de dados."""
    result = data_tools.explore_dataset("dados_vendas")
    parsed_data = json.loads(result)
    assert "colunas" in parsed_data
    assert "amostra_3_linhas" in parsed_data


def test_generate_statistical_summary():
    """Testa a geração de resumo estatístico do dataset."""
    result = data_tools.generate_statistical_summary("dados_vendas")
    assert "mean" in result.lower()
    assert "max" in result.lower()


def test_execute_sql_query_read_and_greatest():
    """Testa execução de consulta SQL com GREATEST entre duas colunas."""
    result = data_tools.execute_sql_query(
        "SELECT product, GREATEST(price_y, price_x) as maior_preco FROM dados_vendas LIMIT 3"
    )
    assert "maior_preco" in result


def test_execute_sql_query_blocks_write_operations():
    """Garante que comandos de escrita/DDL são bloqueados."""
    drop_result = data_tools.execute_sql_query("DROP TABLE dados_vendas")
    assert "proibido" in drop_result.lower()

    delete_result = data_tools.execute_sql_query("DELETE FROM dados_vendas")
    assert "proibido" in delete_result.lower()


def test_read_and_save_file(tmp_path, monkeypatch):
    """Testa leitura, escrita segura e backup automático via save_file."""
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
    """Testa a execução de pipeline com retorno de sucesso."""
    from agent_fiap import config

    monkeypatch.setattr(config, "READ_DIRS", [tmp_path])
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)

    script_file = tmp_path / "script_ok.py"
    script_file.write_text("print('EXECUTOU_COM_SUCESSO')")
    result = code_tools.run_pipeline(str(script_file))
    assert "SUCESSO" in result
    assert "EXECUTOU_COM_SUCESSO" in result


def test_run_empty_pipeline(tmp_path, monkeypatch):
    """Testa execução de arquivo vazio retornando aviso claro."""
    from agent_fiap import config

    monkeypatch.setattr(config, "READ_DIRS", [tmp_path])
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)

    script_file = tmp_path / "vazio.py"
    script_file.touch()
    result = code_tools.run_pipeline(str(script_file))
    assert "vazio ou não existe" in result.lower()


def test_search_knowledge_base():
    """Testa funcionamento do RAG com ChromaDB."""
    result = knowledge_tools.search_knowledge_base("regras de negócio e métricas")
    assert isinstance(result, str)
