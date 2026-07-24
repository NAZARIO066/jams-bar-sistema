import os
import re
import sqlite3
import time
from datetime import datetime


def _db_path():
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "bar_adega.db"
    )


def diagnosticar_banco():
    db = _db_path()
    if not os.path.exists(db):
        return {"ok": False, "erro": "Banco de dados não encontrado"}
    result = {
        "ok": True,
        "tamanho_mb": round(os.path.getsize(db) / (1024 * 1024), 2),
        "integridade": None,
        "tabelas": [],
        "total_registros": 0,
        "versao_sqlite": None,
        "tempo_resposta_ms": None,
    }
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        cur = conn.cursor()

        try:
            ver = cur.execute("PRAGMA compile_options").fetchall()
            for r in ver:
                if "VERSION" in r[0]:
                    result["versao_sqlite"] = r[0].split("=")[-1]
                    break
        except Exception:
            pass

        t0 = time.time()
        try:
            integrity = cur.execute("PRAGMA integrity_check").fetchone()
            result["integridade"] = integrity[0] == "ok"
        except Exception:
            result["integridade"] = False
        result["tempo_resposta_ms"] = round((time.time() - t0) * 1000, 2)

        tables = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()

        for (tname,) in tables:
            try:
                count = cur.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
                page_count = cur.execute(f'PRAGMA page_count("{tname}")').fetchone()[0]
                page_size_row = cur.execute("PRAGMA page_size").fetchone()
                page_size = page_size_row[0] if page_size_row else 4096
                tamanho_bytes = page_count * page_size
                result["tabelas"].append({
                    "nome": tname,
                    "registros": count,
                    "tamanho_bytes": tamanho_bytes,
                    "tamanho_kb": round(tamanho_bytes / 1024, 2),
                    "tamanho_mb": round(tamanho_bytes / (1024 * 1024), 2),
                })
                result["total_registros"] += count
            except Exception:
                result["tabelas"].append({"nome": tname, "registros": -1, "tamanho_bytes": 0, "tamanho_kb": 0, "tamanho_mb": 0})

        conn.close()
    except Exception as e:
        result["ok"] = False
        result["erro"] = str(e)

    from maintenance.backup import ultimo_backup
    lb = ultimo_backup()
    result["ultimo_backup"] = lb["data"] if lb else None
    result["ultimo_backup_nome"] = lb["nome"] if lb else None

    return result


def verificar_fks_orfas():
    db = _db_path()
    if not os.path.exists(db):
        return {"ok": False, "erro": "Banco não encontrado", "orfas": []}
    orfas = []
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        cur = conn.cursor()

        fk_checks = [
            ("produtos", "categoria_id", "categorias", "id"),
            ("comandas", "mesa_id", "mesas", "id"),
            ("comandas", "usuario_id", "usuarios", "id"),
            ("itens_comanda", "comanda_id", "comandas", "id"),
            ("itens_comanda", "produto_id", "produtos", "id"),
            ("vendas", "comanda_id", "comandas", "id"),
            ("vendas", "mesa_id", "mesas", "id"),
            ("vendas", "usuario_id", "usuarios", "id"),
            ("itens_venda", "venda_id", "vendas", "id"),
            ("itens_venda", "produto_id", "produtos", "id"),
            ("movimentacoes", "produto_id", "produtos", "id"),
            ("fiado", "cliente_id", "clientes", "id"),
            ("fiado", "venda_id", "vendas", "id"),
            ("caixas", "usuario_id", "usuarios", "id"),
            ("auditoria", "usuario_id", "usuarios", "id"),
            ("contas_pagar", "usuario_id", "usuarios", "id"),
            ("suprimento_sangria", "caixa_id", "caixas", "id"),
            ("suprimento_sangria", "usuario_id", "usuarios", "id"),
        ]

        for tbl, col, ref_tbl, ref_col in fk_checks:
            try:
                rows = cur.execute(
                    f'SELECT t."{col}" FROM "{tbl}" t '
                    f'LEFT JOIN "{ref_tbl}" r ON t."{col}" = r."{ref_col}" '
                    f'WHERE t."{col}" IS NOT NULL AND r."{ref_col}" IS NULL'
                ).fetchall()
                if rows:
                    orfas.append({
                        "tabela": tbl,
                        "coluna": col,
                        "referencia": f"{ref_tbl}.{ref_col}",
                        "quantidade": len(rows),
                        "exemplo": rows[0][0] if rows else None,
                    })
            except Exception:
                pass

        conn.close()
    except Exception as e:
        return {"ok": False, "erro": str(e), "orfas": []}

    return {"ok": True, "orfas": orfas, "total": len(orfas)}


def estatisticas_banco():
    db = _db_path()
    if not os.path.exists(db):
        return {"ok": False, "erro": "Banco não encontrado"}
    result = {"ok": True, "tabelas": [], "total_tabelas": 0, "total_registros": 0}
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        cur = conn.cursor()

        tables = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()

        for (tname,) in tables:
            try:
                count = cur.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
                result["tabelas"].append({"nome": tname, "registros": count})
                result["total_registros"] += count
                result["total_tabelas"] += 1
            except Exception:
                pass

        try:
            ver = cur.execute("PRAGMA user_version").fetchone()
            result["versao_user"] = ver[0] if ver else 0
        except Exception:
            result["versao_user"] = 0

        try:
            page_size = cur.execute("PRAGMA page_size").fetchone()[0]
            page_count = cur.execute("PRAGMA page_count").fetchone()[0]
            result["tamanho_bytes"] = page_size * page_count
            result["tamanho_mb"] = round((page_size * page_count) / (1024 * 1024), 2)
        except Exception:
            result["tamanho_bytes"] = 0
            result["tamanho_mb"] = 0

        conn.close()
    except Exception as e:
        result["ok"] = False
        result["erro"] = str(e)

    return result


def recalcular_fiados():
    db = _db_path()
    if not os.path.exists(db):
        return {"ok": False, "erro": "Banco não encontrado"}

    try:
        conn = sqlite3.connect(db)
        conn.execute("PRAGMA foreign_keys = ON")
        cur = conn.cursor()

        clientes = cur.execute("SELECT id FROM clientes").fetchall()
        atualizados = 0

        for (cid,) in clientes:
            compra = cur.execute(
                "SELECT COALESCE(SUM(valor), 0) FROM fiado WHERE cliente_id = ? AND tipo = 'compra'",
                (cid,)
            ).fetchone()[0]
            pagamento = cur.execute(
                "SELECT COALESCE(SUM(valor), 0) FROM fiado WHERE cliente_id = ? AND tipo = 'pagamento'",
                (cid,)
            ).fetchone()[0]
            saldo = round(compra - pagamento, 2)
            saldo = max(0.0, saldo)
            cur.execute(
                "UPDATE clientes SET saldo_devedor = ? WHERE id = ?",
                (saldo, cid)
            )
            atualizados += 1

        conn.commit()
        conn.close()
        return {"ok": True, "clientes_atualizados": atualizados}
    except Exception as e:
        return {"ok": False, "erro": str(e)}
