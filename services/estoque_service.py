from database import get_db


def baixar_estoque(produto_id, quantidade, motivo, usuario_id):
    db = get_db()
    db.execute("UPDATE produtos SET estoque = estoque - ? WHERE id=?", (quantidade, produto_id))
    db.execute(
        "INSERT INTO movimentacoes (produto_id, tipo, quantidade, motivo, usuario_id) VALUES (?,?,?,?,?)",
        (produto_id, "saida", quantidade, motivo, usuario_id)
    )


def registrar_entrada(produto_id, quantidade, usuario_id, observacao=""):
    db = get_db()
    db.execute("UPDATE produtos SET estoque = estoque + ? WHERE id=?", (quantidade, produto_id))
    db.execute(
        "INSERT INTO movimentacoes (produto_id, tipo, quantidade, motivo, usuario_id, observacao) VALUES (?,?,?,?,?,?)",
        (produto_id, "entrada", quantidade, "Compra", usuario_id, observacao)
    )


def produto_existe(pid):
    db = get_db()
    return db.execute("SELECT id, estoque, nome FROM produtos WHERE id=? AND ativo=1", (pid,)).fetchone()
