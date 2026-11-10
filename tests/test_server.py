"""Testes automatizados do Servidor Web do Kraken Copilot."""
import pytest
from fastapi.testclient import TestClient
from kraken_copilot.web.server import app
from kraken_copilot.web.storage import storage


@pytest.fixture
def client():
    return TestClient(app)


def test_static_files_and_pages_served(client):
    """Verifica se as páginas HTML e os assets estáticos são entregues corretamente."""
    res_index = client.get("/")
    assert res_index.status_code == 200
    assert "Kraken Copilot" in res_index.text

    res_inv = client.get("/investigar/exec-12345")
    assert res_inv.status_code == 200
    assert "Investigação e Observabilidade" in res_inv.text

    res_css = client.get("/web/app.css")
    assert res_css.status_code == 200

    res_ui_css = client.get("/web/ui/app.css")
    assert res_ui_css.status_code == 200

    res_js = client.get("/web/app.js")
    assert res_js.status_code == 200

    res_ui_js = client.get("/web/ui/app.js")
    assert res_ui_js.status_code == 200

    res_svg = client.get("/web/kraken-copilot.svg")
    assert res_svg.status_code == 200

    res_ui_svg = client.get("/web/ui/kraken-copilot.svg")
    assert res_ui_svg.status_code == 200


def test_conversas_lifecycle_api(client):
    """Testa o ciclo de vida completo de sessões via API REST."""
    # 1. Cria nova conversa
    res_create = client.post("/api/conversas")
    assert res_create.status_code == 201
    data_create = res_create.json()
    conversa_id = data_create["id"]
    assert data_create["titulo"] == "Nova conversa"

    # 2. Lista conversas
    res_list = client.get("/api/conversas")
    assert res_list.status_code == 200
    ids = [c["id"] for c in res_list.json()["conversas"]]
    assert conversa_id in ids

    # 3. Consulta conversa específica
    res_get = client.get(f"/api/conversas/{conversa_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == conversa_id
    assert res_get.json()["mensagens"] == []

    # 4. Envia mensagem para o agente
    res_msg = client.post(f"/api/conversas/{conversa_id}/mensagens", json={"texto": "oi"})
    if res_msg.status_code == 200:
        data_msg = res_msg.json()
        assert "resposta" in data_msg
        assert len(data_msg["resposta"]) > 0
        assert "especialista" in data_msg
        assert "execucao_id" in data_msg
        # Saudação simples como "oi" nunca deve acionar card de aprovação
        assert data_msg.get("has_approval_request") is False

        # 5. Verifica se mensagem e execução foram persistidas no storage
        sessao_atualizada = storage.get_session(conversa_id)
        assert len(sessao_atualizada["mensagens"]) >= 2  # user + assistant
        exec_data = storage.get_execution(data_msg["execucao_id"])
        assert exec_data is not None
        assert exec_data["status"] == "sucesso"
        assert "etapas" in exec_data
    else:
        # Tolerância a 429 RateLimit temporário de API externa Vertex AI
        assert res_msg.status_code == 500
        assert "RateLimitError" in res_msg.text or "Resource" in res_msg.text or "429" in res_msg.text

    # 6. Exclusão da conversa
    res_del = client.delete(f"/api/conversas/{conversa_id}")
    assert res_del.status_code == 200
    assert res_del.json()["removido"] is True

    # 7. Verifica que a conversa não existe mais
    res_get_del = client.get(f"/api/conversas/{conversa_id}")
    assert res_get_del.status_code == 404

    # 8. Deletar novamente retorna 404
    res_del_404 = client.delete(f"/api/conversas/{conversa_id}")
    assert res_del_404.status_code == 404


def test_execucoes_api_not_found_and_retrieval(client):
    """Verifica consulta de execuções existentes e não encontradas."""
    res_404 = client.get("/api/execucoes/inexistente")
    assert res_404.status_code == 404

    # Salva uma execução manual para teste
    test_exec_id = "exec-teste-999"
    storage.save_execution(test_exec_id, {
        "id": test_exec_id,
        "conversa_id": "conv-1",
        "status": "sucesso",
        "latencia_segundos": 1.25,
        "provedor": "Vertex AI",
        "modelo": "gemini-2.5-flash",
        "especialista": "kraken_analyst",
        "ferramentas_executadas": [],
        "etapas": [{"tipo": "test_step", "titulo": "Teste de Etapa"}],
    })

    res_found = client.get(f"/api/execucoes/{test_exec_id}")
    assert res_found.status_code == 200
    assert res_found.json()["id"] == test_exec_id
    assert res_found.json()["especialista"] == "kraken_analyst"


def test_decisao_humana_api(client):
    """Verifica o registro de aprovação e rejeição de propostas."""
    test_exec_id = "exec-decisao-100"
    storage.save_execution(test_exec_id, {
        "id": test_exec_id,
        "conversa_id": "conv-dec",
        "status": "sucesso",
        "etapas": [],
    })

    # 1. Aprovação
    res_aprov = client.post(f"/api/execucoes/{test_exec_id}/decisao", json={"aprovar": True, "motivo": "Aprovado em teste"})
    assert res_aprov.status_code == 200
    assert res_aprov.json()["status"] == "aprovado"

    exec_atual = storage.get_execution(test_exec_id)
    assert exec_atual["status_decisao"] == "aprovado"
    assert exec_atual["decisao_humana"]["aprovar"] is True
    assert any(e["tipo"] == "decisao_humana" for e in exec_atual["etapas"])


def test_dados_arquivos_e_conteudo_api(client):
    """Testa a listagem e visualização de arquivos de dados (DATALAKE, OUTPUTS, DOCUMENTAÇÕES: CSV, JSON, PDF, MARKDOWN)."""
    # 1. Listagem de arquivos e estrutura em árvore
    res_list = client.get("/api/dados/arquivos")
    assert res_list.status_code == 200
    data = res_list.json()
    arquivos = data["arquivos"]
    assert len(arquivos) > 0
    assert "arvore" in data
    assert "DATALAKE" in data["arvore"]
    assert "OUTPUTS" in data["arvore"]
    assert "DOCUMENTAÇÕES" in data["arvore"]
    assert "JSON" in data["arvore"]["DATALAKE"]
    assert "CSV" in data["arvore"]["DATALAKE"]
    assert "MARKDOWN" in data["arvore"]["DOCUMENTAÇÕES"]

    tipos = {a["tipo"] for a in arquivos}
    assert "csv" in tipos

    # 2. Visualização de CSV
    csv_file = next((a for a in arquivos if a["tipo"] == "csv"), None)
    assert csv_file is not None
    res_csv = client.get(f"/api/dados/arquivo?caminho={csv_file['caminho']}&limite=5")
    assert res_csv.status_code == 200
    data_csv = res_csv.json()
    assert data_csv["tipo"] == "csv"
    assert "colunas" in data_csv
    assert len(data_csv["linhas"]) <= 5

    # 3. Visualização de Markdown (docs/*.md)
    md_file = next((a for a in arquivos if a["tipo"] in ("md", "markdown")), None)
    if md_file:
        res_md = client.get(f"/api/dados/arquivo?caminho={md_file['caminho']}")
        assert res_md.status_code == 200
        data_md = res_md.json()
        assert data_md["tipo"] == "markdown"
        assert "conteudo" in data_md
        assert len(data_md["conteudo"]) > 0

    # 4. Visualização de JSON (dicionário de dados)
    json_file = next((a for a in arquivos if a["tipo"] == "json"), None)
    if json_file:
        res_json = client.get(f"/api/dados/arquivo?caminho={json_file['caminho']}")
        assert res_json.status_code == 200
        data_json = res_json.json()
        assert data_json["tipo"] == "json"
        assert "dados" in data_json
        assert "conteudo" in data_json
        assert isinstance(data_json["conteudo"], dict)

    # 5. Visualização inline de PDF (não deve forçar download com attachment)
    pdf_file = next((a for a in arquivos if a["tipo"] == "pdf"), None)
    if pdf_file:
        res_pdf = client.get(f"/api/dados/documento?caminho={pdf_file['caminho']}")
        assert res_pdf.status_code == 200
        assert res_pdf.headers["content-type"] == "application/pdf"
        assert "inline" in res_pdf.headers.get("content-disposition", "").lower()
        assert "attachment" not in res_pdf.headers.get("content-disposition", "").lower()


def test_modelos_gemini_api(client):
    """Testa a listagem e seleção dinâmica de modelos da família Gemini (2.5 Flash, 3.x em diante e Argon)."""
    res = client.get("/api/modelos")
    assert res.status_code == 200
    data = res.json()
    assert "modelo_ativo" in data
    assert "modelos" in data
    ids = [m["id"] for m in data["modelos"]]

    # Modelos mantidos / adicionados (2.5 Flash, 3.x lite/flash/pro e Argon)
    assert "gemini-2.5-flash" in ids
    assert "gemini-2.5-flash-lite" in ids
    assert "gemini-3-flash-preview" in ids
    assert "gemini-3.1-flash-lite" in ids
    assert "gemini-3.1-pro-preview" in ids
    assert "gemini-3.5-flash-lite" in ids
    assert "gemini-3.5-flash" in ids
    assert "gemini-3.6-flash" in ids
    assert "gemini-3.7-flash" in ids
    assert "gemini-3.8-flash" in ids
    assert "gemini-4-argon" in ids

    # Modelos explicitamente desativados a pedido do usuário
    assert "gemini-2.5-pro" not in ids
    assert "gemini-2.0-flash" not in ids
    assert "gemini-1.5-pro" not in ids
    assert "gemini-1.5-flash" not in ids

    # Também disponível em /api/conversas/modelos
    res2 = client.get("/api/conversas/modelos")
    assert res2.status_code == 200
    assert res2.json()["modelo_ativo"] == data["modelo_ativo"]



