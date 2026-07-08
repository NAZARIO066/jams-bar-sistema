from decimal import Decimal
from datetime import date, timedelta
from database import get_db
from services.estoque_service import baixar_estoque


def converter_para_reais(valor):
    return round(float(valor), 2)


def processar_venda_direta(itens, desconto, forma_pagamento, usuario_id, cliente_id=None, dias_vencimento=30):
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
    total -= desconto

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
