"""Testes automatizados do Servidor Web do Kraken Copilot."""
import pytest
from fastapi.testclient import TestClient
from kraken_copilot.server import app, storage


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

    res_js = client.get("/web/app.js")
    assert res_js.status_code == 200

    res_svg = client.get("/web/kraken-copilot.svg")
    assert res_svg.status_code == 200


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

