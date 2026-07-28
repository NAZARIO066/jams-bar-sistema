import re
import sqlite3
from database import get_db


TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2}(\.\d+)?)?$")

FK_RULES = [
    ("comandas", "mesa_id", "mesas", "id"),
    ("comandas", "usuario_id", "usuarios", "id"),
    ("comandas", "garcom_id", "garcons", "id"),
    ("itens_comanda", "comanda_id", "comandas", "id"),
    ("itens_comanda", "produto_id", "produtos", "id"),
    ("itens_comanda", "usuario_id", "usuarios", "id"),
    ("vendas", "comanda_id", "comandas", "id"),
    ("vendas", "mesa_id", "mesas", "id"),
    ("vendas", "usuario_id", "usuarios", "id"),
    ("itens_venda", "venda_id", "vendas", "id"),
    ("itens_venda", "produto_id", "produtos", "id"),
    ("movimentacoes", "produto_id", "produtos", "id"),
    ("movimentacoes", "usuario_id", "usuarios", "id"),
    ("fiado", "cliente_id", "clientes", "id"),
    ("fiado", "venda_id", "vendas", "id"),
    ("fiado", "usuario_id", "usuarios", "id"),
    ("caixas", "usuario_id", "usuarios", "id"),
    ("contas_pagar", "usuario_id", "usuarios", "id"),
    ("suprimento_sangria", "caixa_id", "caixas", "id"),
    ("suprimento_sangria", "usuario_id", "usuarios", "id"),
    ("historico_transferencias", "comanda_id", "comandas", "id"),
    ("historico_transferencias", "mesa_origem_id", "mesas", "id"),
    ("historico_transferencias", "mesa_destino_id", "mesas", "id"),
    ("historico_transferencias", "usuario_id", "usuarios", "id"),
    ("auditoria", "usuario_id", "usuarios", "id"),
    ("produtos", "categoria_id", "categorias", "id"),
]

TIMESTAMP_COLUMNS = [
    ("usuarios", "criado_em"),
    ("comandas", "abertura"),
    ("comandas", "fechamento"),
    ("vendas", "data"),
    ("itens_comanda", "criado_em"),
    ("movimentacoes", "data_hora"),
    ("clientes", "criado_em"),
    ("fiado", "data_hora"),
    ("auditoria", "data_hora"),
    ("caixas", "abertura"),
    ("caixas", "fechamento"),
    ("garcons", "criado_em"),
    ("contas_pagar", "criado_em"),
    ("suprimento_sangria", "data_hora"),
    ("historico_transferencias", "data_hora"),
]


def validar_foreign_keys_orfas(db=None):
    own_db = db is None
    if own_db:
        db = get_db()
    orfas = []
    for tabela, coluna, ref_tabela, ref_coluna in FK_RULES:
        try:
            rows = db.execute(
                f"SELECT t.{coluna} as val, COUNT(*) as c FROM {tabela} t "
                f"LEFT JOIN {ref_tabela} r ON t.{coluna} = r.{ref_coluna} "
                f"WHERE t.{coluna} IS NOT NULL AND r.{ref_coluna} IS NULL "
                f"GROUP BY t.{coluna}"
            ).fetchall()
            for row in rows:
                orfas.append({
                    "tabela": tabela,
                    "coluna": coluna,
                    "ref_tabela": ref_tabela,
                    "valor_orfao": row["val"],
                    "qtd_registros": row["c"],
                })
        except Exception:
            pass
    if own_db:
        db.close()
    return orfas


def validar_formato_timestamps(db=None):
    own_db = db is None
    if own_db:
        db = get_db()
    erros = []
    for tabela, coluna in TIMESTAMP_COLUMNS:
        try:
            rows = db.execute(
                f"SELECT id, {coluna} as val FROM {tabela} "
                f"WHERE {coluna} IS NOT NULL AND {coluna} != '' "
                f"LIMIT 500"
            ).fetchall()
            for row in rows:
                val = row["val"]
                if val and not TIMESTAMP_PATTERN.match(str(val)):
                    erros.append({
                        "tabela": tabela,
                        "coluna": coluna,
                        "id": row["id"],
                        "valor": str(val),
                    })
        except Exception:
            pass
    if own_db:
        db.close()
    return erros


def validar_saldo_devedor(db=None):
    own_db = db is None
    if own_db:
        db = get_db()
    problemas = []
    try:
        rows = db.execute("""
            SELECT c.id, c.nome, c.saldo_devedor,
                   COALESCE(SUM(f.valor - f.valor_pago), 0) as saldo_real
            FROM clientes c
            LEFT JOIN fiado f ON f.cliente_id = c.id AND f.tipo = 'compra' AND (f.valor - f.valor_pago) > 0.01
            GROUP BY c.id
            HAVING ABS(c.saldo_devedor - saldo_real) > 0.01
        """).fetchall()
        for row in rows:
            problemas.append({
                "cliente_id": row["id"],
                "nome": row["nome"],
                "saldo_armazenado": round(row["saldo_devedor"], 2),
                "saldo_real": round(row["saldo_real"], 2),
                "diferenca": round(row["saldo_devedor"] - row["saldo_real"], 2),
            })
    except Exception:
        pass
    if own_db:
        db.close()
    return problemas


def corrigir_saldo_devedor(db=None):
    own_db = db is None
    if own_db:
        db = get_db()
    clientes = db.execute("SELECT id FROM clientes").fetchall()
    count = 0
    for cli in clientes:
        row = db.execute("""
            SELECT COALESCE(SUM(valor - valor_pago), 0) as saldo
            FROM fiado WHERE cliente_id=? AND tipo='compra' AND (valor - valor_pago) > 0.01
        """, (cli["id"],)).fetchone()
        saldo = max(0, round(row["saldo"], 2))
        db.execute("UPDATE clientes SET saldo_devedor=? WHERE id=?", (saldo, cli["id"]))
        count += 1
    if own_db:
        db.commit()
        db.close()
    return count


def validar_empresa_singleton(db=None):
    own_db = db is None
    if own_db:
        db = get_db()
    resultado = {"total_registros": 0, "duplicatas": False}
    try:
        row = db.execute("SELECT COUNT(*) as c FROM empresa").fetchone()
        resultado["total_registros"] = row["c"]
        resultado["duplicatas"] = row["c"] > 1
    except Exception:
        pass
    if own_db:
        db.close()
    return resultado


def limpar_empresa_duplicatas(db=None):
    own_db = db is None
    if own_db:
        db = get_db()
    count = 0
    try:
        empresa = db.execute("SELECT id FROM empresa ORDER BY id ASC LIMIT 1").fetchone()
        if empresa:
            db.execute("DELETE FROM empresa WHERE id != ?", (empresa["id"],))
            count = db.total_changes
    except Exception:
        pass
    if own_db:
        db.commit()
        db.close()
    return count


def executar_antes_importacao(db=None):
    own_db = db is None
    if own_db:
        db = get_db()
    resultados = {
        "orfas_fk": [],
        "timestamps_invalidos": [],
        "saldo_devedor_desatualizado": [],
        "empresa_duplicada": False,
    }
    resultados["orfas_fk"] = validar_foreign_keys_orfas(db)
    resultados["timestamps_invalidos"] = validar_formato_timestamps(db)
    resultados["saldo_devedor_desatualizado"] = validar_saldo_devedor(db)
    empresa_info = validar_empresa_singleton(db)
    resultados["empresa_duplicada"] = empresa_info["duplicatas"]
    if own_db:
        db.close()
    return resultados
