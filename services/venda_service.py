from datetime import date, timedelta
from database import get_db
from services.estoque_service import baixar_estoque
from services.fiado_service import recalcular_saldo_devedor


def processar_venda_direta(itens, desconto, forma_pagamento, usuario_id, cliente_id=None, dias_vencimento=30, acrescimo=0):
    db = get_db()
    total = 0
    linhas = []
    for it in itens:
        p = db.execute("SELECT * FROM produtos WHERE id=? AND ativo=1", (it["produto_id"],)).fetchone()
        if not p:
            return {"ok": False, "erro": f"Produto {it['produto_id']} inválido"}, 400
        q = float(it["quantidade"])
        if p["estoque"] < q:
            return {"ok": False, "erro": f"Estoque insuficiente: {p['nome']}"}, 400
        sub = p["preco"] * q
        total += sub
        linhas.append((p, q, sub, it.get("observacao", "")))

    if desconto < 0:
        return {"ok": False, "erro": "Desconto não pode ser negativo"}, 400
    if desconto > total:
        return {"ok": False, "erro": "Desconto não pode ser maior que o total"}, 400
    total = total - desconto + acrescimo

    cur = db.execute(
        "INSERT INTO vendas (usuario_id, valor_total, desconto, forma_pagamento, tipo) VALUES (?,?,?,?, 'direta')",
        (usuario_id, total, desconto, forma_pagamento)
    )
    venda_id = cur.lastrowid
    for p, q, sub, obs in linhas:
        db.execute(
            "INSERT INTO itens_venda (venda_id, produto_id, quantidade, preco_unitario, subtotal, observacao) VALUES (?,?,?,?,?,?)",
            (venda_id, p["id"], q, p["preco"], sub, obs or None)
        )
        baixar_estoque(p["id"], q, "Venda", usuario_id)

    if forma_pagamento == "Fiado" and cliente_id:
        venc = (date.today() + timedelta(days=dias_vencimento)).isoformat()
        db.execute(
            "INSERT INTO fiado (cliente_id, venda_id, tipo, valor, usuario_id, data_vencimento) VALUES (?,?,?,?,?,?)",
            (cliente_id, venda_id, "compra", total, usuario_id, venc)
        )
        db.execute("UPDATE clientes SET saldo_devedor = saldo_devedor + ? WHERE id=?", (total, cliente_id))

    db.commit()
    return {"ok": True, "venda_id": venda_id, "total": total}, 200


def cancelar_venda(venda_id, usuario_id):
    db = get_db()
    venda = db.execute("SELECT * FROM vendas WHERE id=?", (venda_id,)).fetchone()
    if not venda:
        return {"ok": False, "erro": "Venda não encontrada"}, 404
    if venda["status"] == "cancelada":
        return {"ok": False, "erro": "Venda já foi cancelada"}, 400
    itens = db.execute("SELECT * FROM itens_venda WHERE venda_id=?", (venda_id,)).fetchall()
    for item in itens:
        db.execute("UPDATE produtos SET estoque = estoque + ? WHERE id=?", (item["quantidade"], item["produto_id"]))
        db.execute(
            "INSERT INTO movimentacoes (produto_id, tipo, quantidade, motivo, usuario_id, observacao) VALUES (?,?,?,?,?,?)",
            (item["produto_id"], "entrada", item["quantidade"], "Cancelamento", usuario_id, f"Venda #{venda_id}")
        )
    db.execute("UPDATE vendas SET status='cancelada' WHERE id=?", (venda_id,))
    if venda["forma_pagamento"] == "Fiado":
        fiado = db.execute("SELECT * FROM fiado WHERE venda_id=?", (venda_id,)).fetchone()
        if fiado:
            db.execute("UPDATE fiado SET tipo='cancelado' WHERE venda_id=?", (venda_id,))
            recalcular_saldo_devedor(fiado["cliente_id"])
    db.commit()
    return {"ok": True, "mensagem": f"Venda #{venda_id} cancelada com sucesso"}, 200
