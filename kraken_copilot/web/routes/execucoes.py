"""Rotas da API para auditoria de execuções, percurso de observabilidade e decisão humana."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from kraken_copilot.web.schemas.execucoes import DecisaoInput, DecisaoResponse
from kraken_copilot.web.storage import storage

router = APIRouter(prefix="/api/execucoes", tags=["execucoes"])


@router.get("/{exec_id}")
async def obter_execucao(exec_id: str):
    """Retorna os detalhes de auditoria e percurso de observabilidade de uma execução."""
    dados = storage.get_execution(exec_id)
    if not dados:
        raise HTTPException(status_code=404, detail="Execução não encontrada.")
    return dados


@router.post("/{exec_id}/decisao", response_model=DecisaoResponse)
async def registrar_decisao(exec_id: str, decisao: DecisaoInput):
    """Registra uma aprovação ou rejeição humana (HITL) para uma execução."""
    dados = storage.get_execution(exec_id)
    if not dados:
        raise HTTPException(status_code=404, detail="Execução não encontrada.")

    agora = datetime.now(timezone.utc).isoformat()
    status_decisao = "aprovado" if decisao.aprovar else "rejeitado"
    registro_decisao = {
        "aprovar": decisao.aprovar,
        "aprovado": decisao.aprovar,
        "motivo": decisao.motivo,
        "decidido_em": agora,
        "usuario": "engenheiro_humano",
    }
    dados["decisao_humana"] = registro_decisao
    dados["status_decisao"] = status_decisao

    etapa = {
        "tipo": "decisao_humana",
        "titulo": f"Decisão Humana: {'Aprovado ✅' if decisao.aprovar else 'Rejeitado ❌'}",
        "descricao": f"Engenheiro registrou {status_decisao}. Motivo: {decisao.motivo or 'Nenhum'}",
        "resultado": registro_decisao,
        "timestamp": agora,
    }
    dados.setdefault("steps", []).append(etapa)
    dados.setdefault("etapas", []).append(etapa)

    storage.save_execution(exec_id, dados)
    return {
        "status": status_decisao,
        "aprovado": decisao.aprovar,
        "decidido_em": agora,
        "motivo": decisao.motivo,
    }
