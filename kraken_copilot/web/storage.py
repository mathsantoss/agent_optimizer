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
LEGACY_SESSIONS_FILE = LOGS_DIR / "sessoes_web.json"
LEGACY_EXECUTIONS_FILE = LOGS_DIR / "execucoes_web.json"


class Storage:
    """Persistência segura em SQLite para sessões, histórico de chat e telemetria de auditoria."""

    def __init__(self, db_path: Path = DB_FILE) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._migrate_legacy_json()

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

    def _migrate_legacy_json(self) -> None:
        """Migra de forma transparente registros de arquivos JSON antigos para o SQLite."""
        try:
            if LEGACY_SESSIONS_FILE.exists():
                with open(LEGACY_SESSIONS_FILE, "r", encoding="utf-8") as f:
                    legacy_sessions = json.load(f)
                if isinstance(legacy_sessions, dict) and legacy_sessions:
                    with self._get_connection() as conn:
                        for s_id, s in legacy_sessions.items():
                            conn.execute(
                                """
                                INSERT OR IGNORE INTO sessions (id, titulo, criado_em, atualizado_em, mensagens)
                                VALUES (?, ?, ?, ?, ?)
                                """,
                                (
                                    s.get("id", s_id),
                                    s.get("titulo", "Nova conversa"),
                                    s.get("criado_em", datetime.now(timezone.utc).isoformat()),
                                    s.get("atualizado_em", datetime.now(timezone.utc).isoformat()),
                                    json.dumps(s.get("mensagens", []), ensure_ascii=False),
                                ),
                            )
            if LEGACY_EXECUTIONS_FILE.exists():
                with open(LEGACY_EXECUTIONS_FILE, "r", encoding="utf-8") as f:
                    legacy_execs = json.load(f)
                if isinstance(legacy_execs, dict) and legacy_execs:
                    with self._get_connection() as conn:
                        for e_id, e in legacy_execs.items():
                            conn.execute(
                                """
                                INSERT OR IGNORE INTO executions (id, dados, atualizado_em)
                                VALUES (?, ?, ?)
                                """,
                                (
                                    e_id,
                                    json.dumps(e, ensure_ascii=False),
                                    e.get("concluido_em") or datetime.now(timezone.utc).isoformat(),
                                ),
                            )
        except Exception:
            pass

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
        msg = {
            "id": f"msg-{uuid.uuid4().hex[:8]}",
            "role": role,
            "texto": texto,
            "especialista": (metadados or {}).get("especialista"),
            "timestamp": agora,
            "execucao_id": execucao_id,
            "metadados": metadados or {},
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
