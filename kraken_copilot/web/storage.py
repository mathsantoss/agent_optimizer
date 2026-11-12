"""Gerenciador de persistência SQLite para conversas e execuções do Kraken Copilot."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from kraken_copilot.config import LOGS_DIR

DB_FILE = LOGS_DIR / "kraken_copilot.db"


class Storage:
    """Persistência segura em SQLite para sessões, histórico de chat, execuções e auditoria de guardrails."""

    def __init__(self, db_path: Path = DB_FILE) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=15.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    titulo TEXT NOT NULL,
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL,
                    mensagens TEXT NOT NULL DEFAULT '[]'
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_atualizado ON sessions(atualizado_em DESC);"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS executions (
                    id TEXT PRIMARY KEY,
                    dados TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_executions_atualizado ON executions(atualizado_em DESC);"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    category TEXT NOT NULL,
                    action TEXT NOT NULL,
                    status TEXT NOT NULL,
                    details TEXT
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);"
            )

    def append_audit_log(
        self,
        category: str,
        action: str,
        status: str,
        details: str | dict[str, Any] = "",
    ) -> None:
        """Registra um evento de auditoria/guardrail no SQLite."""
        agora = datetime.now(timezone.utc).isoformat()
        det_str = json.dumps(details, ensure_ascii=False) if isinstance(details, (dict, list)) else str(details)
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO audit_logs (timestamp, category, action, status, details) VALUES (?, ?, ?, ?, ?)",
                    (agora, category, action, status, det_str),
                )
        except Exception:
            pass

    def list_audit_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        """Lista os eventos de auditoria e guardrails mais recentes gravados no SQLite."""
        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, timestamp, category, action, status, details FROM audit_logs ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                )
                rows = cur.fetchall()
                return [dict(r) for r in rows]
        except Exception:
            return []

    def cleanup_empty_sessions(self) -> int:
        """Remove sessões vazias acumuladas sem mensagens criadas há mais de 2 horas."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                DELETE FROM sessions 
                WHERE (mensagens = '[]' OR mensagens = '' OR mensagens IS NULL)
                  AND id NOT IN (SELECT id FROM sessions ORDER BY criado_em DESC LIMIT 3)
                """
            )
            removidas = cur.rowcount
            conn.commit()
            return removidas

    def list_sessions(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, titulo, criado_em, atualizado_em, mensagens FROM sessions ORDER BY atualizado_em DESC"
            )
            rows = cur.fetchall()
            resultado = []
            for r in rows:
                try:
                    msgs = json.loads(r["mensagens"])
                except Exception:
                    msgs = []
                resultado.append(
                    {
                        "id": r["id"],
                        "titulo": r["titulo"],
                        "criado_em": r["criado_em"],
                        "atualizado_em": r["atualizado_em"],
                        "total_mensagens": len(msgs),
                    }
                )
            return resultado

    def create_session(self, titulo: str = "Nova conversa") -> Dict[str, Any]:
        sess_id = f"sess-{uuid.uuid4().hex[:12]}"
        agora = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO sessions (id, titulo, criado_em, atualizado_em, mensagens) VALUES (?, ?, ?, ?, ?)",
                (sess_id, titulo, agora, agora, "[]"),
            )
        return {
            "id": sess_id,
            "titulo": titulo,
            "criado_em": agora,
            "atualizado_em": agora,
            "mensagens": [],
        }

    def update_session_title(self, session_id: str, novo_titulo: str) -> bool:
        """Atualiza o título de uma conversa existente."""
        agora = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE sessions SET titulo = ?, atualizado_em = ? WHERE id = ?",
                (novo_titulo.strip() or "Conversa sem título", agora, session_id),
            )
            return cur.rowcount > 0

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, titulo, criado_em, atualizado_em, mensagens FROM sessions WHERE id = ?",
                (session_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            try:
                msgs = json.loads(row["mensagens"])
            except Exception:
                msgs = []
            return {
                "id": row["id"],
                "titulo": row["titulo"],
                "criado_em": row["criado_em"],
                "atualizado_em": row["atualizado_em"],
                "mensagens": msgs,
            }

    def append_message(
        self,
        session_id: str,
        role: str,
        texto: str,
        execucao_id: Optional[str] = None,
        metadados: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        sessao = self.get_session(session_id)
        if not sessao:
            sessao = self.create_session()
            session_id = sessao["id"]

        agora = datetime.now(timezone.utc).isoformat()
        meta = metadados or {}
        msg = {
            "id": f"msg-{uuid.uuid4().hex[:8]}",
            "role": role,
            "texto": texto,
            "especialista": meta.get("especialista"),
            "timestamp": agora,
            "execucao_id": execucao_id,
            "has_approval_request": meta.get("has_approval_request", False),
            "proposed_code": meta.get("proposed_code"),
            "diff_info": meta.get("diff_info"),
            "ferramentas_executadas": meta.get("ferramentas_executadas", []),
            "sugestoes_acoes": meta.get("sugestoes_acoes", []),
            "benchmark_metrics": meta.get("benchmark_metrics"),
            "metadados": meta,
        }
        mensagens = sessao.get("mensagens", [])
        mensagens.append(msg)

        novo_titulo = sessao["titulo"]
        if role == "user" and (sessao.get("titulo") == "Nova conversa" or len(mensagens) <= 2):
            primeira_linha = texto.strip().split("\n")[0][:45]
            if primeira_linha:
                novo_titulo = primeira_linha + ("…" if len(texto) > 45 else "")

        with self._get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET titulo = ?, atualizado_em = ?, mensagens = ? WHERE id = ?",
                (
                    novo_titulo,
                    agora,
                    json.dumps(mensagens, ensure_ascii=False),
                    session_id,
                ),
            )
        return msg

    def delete_session(self, session_id: str) -> bool:
        """Exclui uma sessão de conversa do banco SQLite."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            return cur.rowcount > 0

    def save_execution(self, exec_id: str, dados: Dict[str, Any]) -> None:
        agora = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO executions (id, dados, atualizado_em)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    dados = excluded.dados,
                    atualizado_em = excluded.atualizado_em
                """,
                (exec_id, json.dumps(dados, ensure_ascii=False), agora),
            )

    def get_execution(self, exec_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT dados FROM executions WHERE id = ?", (exec_id,))
            row = cur.fetchone()
            if not row:
                return None
            try:
                return json.loads(row["dados"])
            except Exception:
                return None


# Instância singleton global de storage SQLite
storage = Storage()
