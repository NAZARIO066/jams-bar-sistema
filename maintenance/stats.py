import os
import sqlite3
from datetime import datetime


def _db_path():
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "bar_adega.db"
    )


def _calcular_saude(integridade_ok, fks_orfas_total, total_backups, tamanho_mb):
    pontos = 100
    if not integridade_ok:
        pontos -= 40
    if fks_orfas_total > 0:
        pontos -= min(fks_orfas_total * 5, 30)
    if total_backups == 0:
        pontos -= 15
    if tamanho_mb > 500:
        pontos -= 10
    elif tamanho_mb > 100:
        pontos -= 5
    if pontos >= 85:
        return "Excelente", pontos
    elif pontos >= 65:
        return "Boa", pontos
    elif pontos >= 40:
        return "Atenção", pontos
    else:
        return "Crítica", pontos


def obter_stats_dashboard():
    result = {
        "total_backups": 0,
        "ultima_analise": None,
        "integridade_ok": None,
        "compatibilidade": None,
        "espaco_banco_mb": 0,
        "espaco_backups_mb": 0,
        "total_tabelas": 0,
        "total_registros": 0,
        "espaco_livre_bytes": 0,
        "espaco_livre_mb": 0,
        "data_backup_mais_recente": None,
        "saude": "Desconhecido",
        "saude_pontos": 0,
    }

    db = _db_path()
    if os.path.exists(db):
        result["espaco_banco_mb"] = round(os.path.getsize(db) / (1024 * 1024), 2)
        try:
            conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            cur = conn.cursor()

            integrity = cur.execute("PRAGMA integrity_check").fetchone()
            result["integridade_ok"] = integrity[0] == "ok" if integrity else False

            tables = cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            result["total_tabelas"] = len(tables)

            for (tname,) in tables:
                try:
                    count = cur.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
                    result["total_registros"] += count
                except Exception:
                    pass

            try:
                freelist = cur.execute("PRAGMA freelist_count").fetchone()
                page_size = cur.execute("PRAGMA page_size").fetchone()
                if freelist and page_size:
                    result["espaco_livre_bytes"] = freelist[0] * page_size[0]
                    result["espaco_livre_mb"] = round(result["espaco_livre_bytes"] / (1024 * 1024), 2)
            except Exception:
                pass

            conn.close()
        except Exception:
            pass

    from maintenance.backup import BACKUP_DIR, contar_backups, ultimo_backup
    result["total_backups"] = contar_backups()
    lb = ultimo_backup()
    if lb:
        result["data_backup_mais_recente"] = lb["data"]

    if os.path.exists(BACKUP_DIR):
        total_size = 0
        for f in os.listdir(BACKUP_DIR):
            if f.endswith(".db") and not f.endswith(".meta") and not f.endswith(".db-journal") and not f.endswith(".db-wal"):
                fp = os.path.join(BACKUP_DIR, f)
                if os.path.isfile(fp):
                    total_size += os.path.getsize(fp)
        result["espaco_backups_mb"] = round(total_size / (1024 * 1024), 2)

    fks_orfas_total = 0
    try:
        from maintenance.diagnostics import verificar_fks_orfas
        fks = verificar_fks_orfas()
        fks_orfas_total = fks.get("total", 0)
    except Exception:
        pass

    saude, pontos = _calcular_saude(
        result["integridade_ok"] or False,
        fks_orfas_total,
        result["total_backups"],
        result["espaco_banco_mb"],
    )
    result["saude"] = saude
    result["saude_pontos"] = pontos

    result["ultima_analise"] = datetime.now().strftime("%d/%m/%Y")
    result["compatibilidade"] = None

    return result
