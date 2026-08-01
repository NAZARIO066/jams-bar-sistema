import os
import sqlite3
from datetime import datetime


AUDIT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "backups", "audit.db"
)


def _get_audit_db():
    os.makedirs(os.path.dirname(AUDIT_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(AUDIT_DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS maintenance_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT NOT NULL,
            usuario_id INTEGER,
            usuario_nome TEXT,
            operacao TEXT NOT NULL,
            resultado TEXT,
            detalhes TEXT
        )
    """)
    conn.commit()
    return conn


def log_maintenance(operacao, resultado="ok", detalhes=None, usuario_id=None, usuario_nome=None):
    conn = _get_audit_db()
    try:
        conn.execute(
            "INSERT INTO maintenance_audit (data_hora, usuario_id, usuario_nome, operacao, resultado, detalhes) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), usuario_id, usuario_nome,
             operacao, resultado, detalhes)
        )
        conn.commit()
    finally:
        conn.close()


def listar_auditoria(limite=100, offset=0):
    conn = _get_audit_db()
    try:
        rows = conn.execute(
            "SELECT data_hora, usuario_nome, operacao, resultado, detalhes "
            "FROM maintenance_audit ORDER BY id DESC LIMIT ? OFFSET ?",
            (limite, offset)
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM maintenance_audit").fetchone()[0]
        return {
            "registros": [
                {
                    "data_hora": r[0],
                    "usuario": r[1] or "Sistema",
                    "operacao": r[2],
                    "resultado": r[3],
                    "detalhes": r[4],
                }
                for r in rows
            ],
            "total": total,
        }
    finally:
        conn.close()
