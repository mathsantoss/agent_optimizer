"""Testes automatizados para o Agent FIAP (Orquestrador, Agente Analista e Agente Otimizador) e suas ferramentas."""
import json
import pytest
from agent_fiap.agent import root_agent, agente_analista, agente_otimizador
from agent_fiap.tools import data_tools, code_tools, rag


def test_estrutura_multi_agentes():
    """Valida a separação entre o Orquestrador, o Agente Analista e o Agente Otimizador sem perda de funcionalidades."""
    assert root_agent.name == "agent_fiap"
    nomes_subagentes = [ag.name for ag in root_agent.sub_agents]
    assert "agente_analista" in nomes_subagentes
    assert "agente_otimizador" in nomes_subagentes

    # Ferramentas do Agente Analista de Dados
    tools_analista = [t.__name__ for t in agente_analista.tools]
    for esp in [
        "listar_datasets",
        "explorar_dataset",
        "resumo_estatistico",
        "consultar_sql",
        "buscar_conhecimento",
    ]:
        assert esp in tools_analista, f"Ferramenta {esp} não encontrada no agente_analista."

    # Ferramentas do Agente Especialista em Otimização e Criação de Código
    tools_otimizador = [t.__name__ for t in agente_otimizador.tools]
    for esp in [
        "ler_arquivo",
        "salvar_arquivo",
        "executar_pipeline",
        "executar_testes",
        "listar_datasets",
        "explorar_dataset",
        "buscar_conhecimento",
    ]:
        assert esp in tools_otimizador, f"Ferramenta {esp} não encontrada no agente_otimizador."


def test_listar_datasets():
    """Testa a descoberta dinâmica de datasets."""
    res = data_tools.listar_datasets()
    assert "tabela_sql" in res


def test_explorar_dataset():
    """Testa a inspeção de esquema e amostra de dados genéricos."""
    res = data_tools.explorar_dataset("dados_vendas")
    dados = json.loads(res)
    assert "colunas" in dados
    assert "amostra_3_linhas" in dados


def test_resumo_estatistico():
    """Testa a geração de resumo estatístico do dataset."""
    res = data_tools.resumo_estatistico("dados_vendas")
    assert "mean" in res.lower()
    assert "max" in res.lower()


def test_consultar_sql_leitura_e_greatest():
    """Testa execução de consulta SQL com GREATEST entre duas colunas."""
    res = data_tools.consultar_sql("SELECT product, GREATEST(price_y, price_x) as maior_preco FROM dados_vendas LIMIT 3")
    assert "maior_preco" in res


def test_consultar_sql_bloqueio_escrita():
    """Garante que comandos de escrita/DDL são bloqueados."""
    res = data_tools.consultar_sql("DROP TABLE dados_vendas")
    assert "proibido" in res.lower()

    res2 = data_tools.consultar_sql("DELETE FROM dados_vendas")
    assert "proibido" in res2.lower()


def test_ler_e_salvar_arquivo(tmp_path, monkeypatch):
    """Testa leitura, escrita segura e backup automático via salvar_arquivo."""
    from agent_fiap import config
    monkeypatch.setattr(config, "WRITE_DIRS", [tmp_path])
    monkeypatch.setattr(config, "READ_DIRS", [tmp_path])
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)

    alvo = tmp_path / "teste_script.py"
    
    # Arquivo vazio retorna aviso amigável
    alvo.touch()
    res_vazio = code_tools.ler_arquivo(str(alvo))
    assert "vazio" in res_vazio.lower()

    # Validação de sintaxe Python
    res_erro = code_tools.salvar_arquivo(str(alvo), "def invalido(:\n   pass")
    assert "erro de sintaxe" in res_erro.lower()

    # Escrita válida
    res_escrita = code_tools.salvar_arquivo(str(alvo), "print('versao_1')")
    assert "sucesso" in res_escrita.lower()

    # Leitura com conteúdo gravado
    res_leitura = code_tools.ler_arquivo(str(alvo))
    assert res_leitura == "print('versao_1')"

    # Backup automático ao sobrescrever
    code_tools.salvar_arquivo(str(alvo), "print('versao_2')")
    assert (tmp_path / "teste_script.py.bak").read_text() == "print('versao_1')"
    assert (tmp_path / "teste_script.py").read_text() == "print('versao_2')"


def test_executar_pipeline(tmp_path, monkeypatch):
    """Testa a execução de pipeline com retorno de sucesso."""
    from agent_fiap import config
    monkeypatch.setattr(config, "READ_DIRS", [tmp_path])
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)

    script = tmp_path / "script_ok.py"
    script.write_text("print('EXECUTOU_COM_SUCESSO')")
    res = code_tools.executar_pipeline(str(script))
    assert "SUCESSO" in res
    assert "EXECUTOU_COM_SUCESSO" in res


def test_executar_pipeline_vazio(tmp_path, monkeypatch):
    """Testa execução de arquivo vazio retornando aviso claro."""
    from agent_fiap import config
    monkeypatch.setattr(config, "READ_DIRS", [tmp_path])
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)

    script = tmp_path / "vazio.py"
    script.touch()
    res = code_tools.executar_pipeline(str(script))
    assert "vazio ou não existe" in res.lower()


def test_rag_busca():
    """Testa funcionamento do RAG com ChromaDB."""
    resultado = data_tools.buscar_conhecimento("regras de negócio e métricas")
    assert isinstance(resultado, str)


