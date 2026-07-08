from datetime import datetime
from flask import render_template, request, jsonify, session
from database import get_db
from auth import login_required, log_auditoria
from services.estoque_service import baixar_estoque


def register_mesas_routes(app):

    @app.route("/mesas")
    @login_required
    def mesas():
        return render_template("mesas.html")

    @app.route("/api/mesas")
    @login_required
    def api_mesas_list():
        db = get_db()
        mesas = db.execute("""
            SELECT m.*, c.id as comanda_id, c.garcom_id,
                   u.nome as funcionario, g.nome as garcom_nome, c.abertura
            FROM mesas m
            LEFT JOIN comandas c ON c.mesa_id=m.id AND c.status='aberta'
            LEFT JOIN usuarios u ON c.usuario_id=u.id
            LEFT JOIN garcons g ON c.garcom_id=g.id
            ORDER BY m.numero
        """).fetchall()
        result = []
        for m in mesas:
            d = dict(m)
            if d.get("abertura"):
                try:
                    abertura = datetime.fromisoformat(d["abertura"])
                    delta = datetime.now() - abertura
                    horas = int(delta.total_seconds() // 3600)
                    minutos = int((delta.total_seconds() % 3600) // 60)
                    d["tempo"] = f"{horas:02d}h{minutos:02d}min"
                except Exception:
                    d["tempo"] = "--"
            else:
                d["tempo"] = "--"
            result.append(d)
        return jsonify(result)

    @app.route("/api/mesas/<int:mesa_id>/abrir", methods=["POST"])
    @login_required
    def abrir_mesa(mesa_id):
        db = get_db()
        mesa = db.execute("SELECT * FROM mesas WHERE id=?", (mesa_id,)).fetchone()
        if not mesa:
            return jsonify({"ok": False, "erro": "Mesa não encontrada"}), 404
        if mesa["status"] != "disponivel":
            return jsonify({"ok": False, "erro": "Mesa não está disponível"}), 400
        comanda_aberta = db.execute("SELECT id FROM comandas WHERE mesa_id=? AND status='aberta'", (mesa_id,)).fetchone()
        if comanda_aberta:
            return jsonify({"ok": False, "erro": "Mesa já possui comanda aberta"}), 400
        cliente_nome = ((request.json or {}).get("cliente_nome") or "").strip() or None
        garcom_id = (request.json or {}).get("garcom_id")
        cur = db.execute(
            "INSERT INTO comandas (mesa_id, usuario_id, cliente_nome, garcom_id) VALUES (?,?,?,?)",
            (mesa_id, session["usuario_id"], cliente_nome, garcom_id)
        )
        db.execute("UPDATE mesas SET status='ocupada', valor_atual=0, aberta_em=CURRENT_TIMESTAMP, reservada_para=? WHERE id=?", (cliente_nome, mesa_id))
        db.commit()
        log_auditoria("ABERTURA_MESA", f"Mesa {mesa['numero']} aberta para {cliente_nome or '—'} - comanda #{cur.lastrowid}")
        return jsonify({"ok": True, "comanda_id": cur.lastrowid})

    @app.route("/api/mesas/<int:mesa_id>/reservar", methods=["POST"])
    @login_required
    def reservar_mesa(mesa_id):
        db = get_db()
        nome = (request.json or {}).get("nome", "")
        db.execute("UPDATE mesas SET status='reservada', reservada_para=? WHERE id=?", (nome, mesa_id))
        db.commit()
        log_auditoria("RESERVA_MESA", f"Mesa {mesa_id} reservada para {nome}")
        return jsonify({"ok": True})

    @app.route("/api/mesas/<int:mesa_id>/liberar", methods=["POST"])
    @login_required
    def liberar_mesa(mesa_id):
        db = get_db()
        db.execute("UPDATE mesas SET status='disponivel', valor_atual=0, reservada_para=NULL WHERE id=?", (mesa_id,))
        db.commit()
        log_auditoria("LIBERAR_MESA", f"Mesa {mesa_id} liberada")
        return jsonify({"ok": True})

    @app.route("/api/comanda/<int:comanda_id>")
    @login_required
    def comanda_detalhes(comanda_id):
        db = get_db()
        comanda = db.execute("""
            SELECT c.*, m.numero as mesa_numero, u.nome as funcionario, g.nome as garcom_nome
            FROM comandas c JOIN mesas m ON c.mesa_id=m.id
            JOIN usuarios u ON c.usuario_id=u.id
            LEFT JOIN garcons g ON c.garcom_id=g.id
            WHERE c.id=?
        """, (comanda_id,)).fetchone()
        if not comanda:
            return jsonify({"erro": "Comanda não encontrada"}), 404
        itens = db.execute("""
            SELECT ic.*, p.nome as produto_nome
            FROM itens_comanda ic JOIN produtos p ON ic.produto_id=p.id
            WHERE ic.comanda_id=? ORDER BY ic.criado_em
        """, (comanda_id,)).fetchall()
        total = sum(i["subtotal"] for i in itens)
        return jsonify({"comanda": dict(comanda), "itens": [dict(i) for i in itens], "total": total})

    @app.route("/api/comanda/item/<int:item_id>", methods=["DELETE"])
    @login_required
    def comanda_remover_item(item_id):
        db = get_db()
        db.execute("DELETE FROM itens_comanda WHERE id=?", (item_id,))
        db.commit()
        log_auditoria("REMOVER_ITEM", f"Item {item_id} removido da comanda")
        return jsonify({"ok": True})

    @app.route("/api/comanda/<int:comanda_id>/adicionar", methods=["POST"])
    @login_required
    def comanda_adicionar(comanda_id):
        db = get_db()
        data = request.json or {}
        produto_id = data.get("produto_id")
        quantidade = float(data.get("quantidade", 1))
        observacao = (data.get("observacao") or "").strip() or None
        codigo = data.get("codigo_barras")
        if codigo and not produto_id:
            p = db.execute("SELECT * FROM produtos WHERE codigo_barras=? AND ativo=1", (codigo,)).fetchone()
            if not p:
                return jsonify({"ok": False, "erro": "Produto não encontrado"}), 404
            produto_id = p["id"]
        produto = db.execute("SELECT * FROM produtos WHERE id=? AND ativo=1", (produto_id,)).fetchone()
        if not produto:
            return jsonify({"ok": False, "erro": "Produto inválido"}), 400
        if produto["estoque"] < quantidade:
            return jsonify({"ok": False, "erro": f"Estoque insuficiente ({produto['estoque']} {produto['unidade']})"}), 400
        subtotal = produto["preco"] * quantidade
        db.execute(
            "INSERT INTO itens_comanda (comanda_id, produto_id, quantidade, preco_unitario, subtotal, observacao, usuario_id) VALUES (?,?,?,?,?,?,?)",
            (comanda_id, produto_id, quantidade, produto["preco"], subtotal, observacao, session["usuario_id"])
        )
        novo_total = db.execute("SELECT COALESCE(SUM(subtotal),0) as t FROM itens_comanda WHERE comanda_id=?", (comanda_id,)).fetchone()["t"]
        db.execute("UPDATE mesas SET valor_atual=? WHERE id=(SELECT mesa_id FROM comandas WHERE id=?)", (novo_total, comanda_id))
        db.commit()
        log_auditoria("ITEM_COMANDA", f"Comanda {comanda_id}: {quantidade}x {produto['nome']}")
        return jsonify({"ok": True, "subtotal": subtotal, "total_comanda": novo_total})

    @app.route("/api/comanda/<int:comanda_id>/reabrir", methods=["POST"])
    @login_required
    def comanda_reabrir(comanda_id):
        db = get_db()
        comanda = db.execute("SELECT * FROM comandas WHERE id=?", (comanda_id,)).fetchone()
        if not comanda:
            return jsonify({"ok": False, "erro": "Comanda não encontrada"}), 404
        if comanda["status"] != "fechada":
            return jsonify({"ok": False, "erro": "Comanda não está fechada"}), 400
        db.execute("UPDATE comandas SET status='aberta', fechamento=NULL WHERE id=?", (comanda_id,))
        db.execute("UPDATE mesas SET status='ocupada' WHERE id=?", (comanda["mesa_id"],))
        db.commit()
        log_auditoria("REABRIR_COMANDA", f"Comanda #{comanda_id} reaberta")
        return jsonify({"ok": True})

    @app.route("/api/comanda/<int:comanda_id>/cancelar", methods=["POST"])
    @login_required
    def comanda_cancelar(comanda_id):
        db = get_db()
        comanda = db.execute("SELECT * FROM comandas WHERE id=?", (comanda_id,)).fetchone()
        if not comanda:
            return jsonify({"ok": False, "erro": "Comanda não encontrada"}), 404
        if comanda["status"] == "cancelada":
            return jsonify({"ok": False, "erro": "Já cancelada"}), 400
        db.execute("UPDATE comandas SET status='cancelada', fechamento=CURRENT_TIMESTAMP WHERE id=?", (comanda_id,))
        db.execute("UPDATE mesas SET status='disponivel', valor_atual=0, reservada_para=NULL WHERE id=?", (comanda["mesa_id"],))
        db.commit()
        log_auditoria("CANCELAR_COMANDA", f"Comanda #{comanda_id} cancelada")
        return jsonify({"ok": True})

    @app.route("/api/comanda/<int:comanda_id>/transferir", methods=["POST"])
    @login_required
    def comanda_transferir(comanda_id):
        db = get_db()
        data = request.json or {}
        mesa_destino_id = data.get("mesa_destino_id")
        if not mesa_destino_id:
            return jsonify({"ok": False, "erro": "Selecione a mesa de destino"}), 400
        comanda = db.execute("SELECT * FROM comandas WHERE id=? AND status='aberta'", (comanda_id,)).fetchone()
        if not comanda:
            return jsonify({"ok": False, "erro": "Comanda não encontrada ou não está aberta"}), 404
        mesa_destino = db.execute("SELECT * FROM mesas WHERE id=?", (mesa_destino_id,)).fetchone()
        if not mesa_destino:
            return jsonify({"ok": False, "erro": "Mesa de destino não encontrada"}), 404
        if mesa_destino["status"] != "disponivel":
            return jsonify({"ok": False, "erro": "Mesa de destino não está disponível"}), 400
        mesa_origem_id = comanda["mesa_id"]
        db.execute("UPDATE comandas SET mesa_id=? WHERE id=?", (mesa_destino_id, comanda_id))
        db.execute("UPDATE mesas SET status='disponivel', valor_atual=0, reservada_para=NULL WHERE id=?", (mesa_origem_id,))
        novo_valor = db.execute("SELECT COALESCE(SUM(subtotal),0) as t FROM itens_comanda WHERE comanda_id=?", (comanda_id,)).fetchone()["t"]
        db.execute("UPDATE mesas SET status='ocupada', valor_atual=? WHERE id=?", (novo_valor, mesa_destino_id))
        db.execute("INSERT INTO historico_transferencias (comanda_id, mesa_origem_id, mesa_destino_id, usuario_id) VALUES (?,?,?,?)",
                   (comanda_id, mesa_origem_id, mesa_destino_id, session["usuario_id"]))
        db.commit()
        log_auditoria("TRANSFERIR_COMANDA", f"Comanda #{comanda_id} transferida Mesa {mesa_origem_id}→{mesa_destino_id}")
        return jsonify({"ok": True})

    @app.route("/api/comanda/<int:comanda_id>/trocar_garcom", methods=["POST"])
    @login_required
    def comanda_trocar_garcom(comanda_id):
        db = get_db()
        data = request.json or {}
        garcom_id = data.get("garcom_id")
        db.execute("UPDATE comandas SET garcom_id=? WHERE id=?", (garcom_id, comanda_id))
        db.commit()
        log_auditoria("TROCAR_GARCOM", f"Comanda #{comanda_id} garçom alterado para #{garcom_id}")
        return jsonify({"ok": True})

    @app.route("/api/mesas/<int:mesa_id>/fechar", methods=["POST"])
    @login_required
    def fechar_mesa(mesa_id):
        db = get_db()
        data = request.json or {}
        desconto = float(data.get("desconto", 0))
        forma = data.get("forma_pagamento", "Dinheiro")
        comanda = db.execute("SELECT * FROM comandas WHERE mesa_id=? AND status='aberta'", (mesa_id,)).fetchone()
        if not comanda:
            return jsonify({"ok": False, "erro": "Nenhuma comanda aberta"}), 400
        total = db.execute("SELECT COALESCE(SUM(subtotal),0) as t FROM itens_comanda WHERE comanda_id=?", (comanda["id"],)).fetchone()["t"]
        if desconto < 0:
            return jsonify({"ok": False, "erro": "Desconto não pode ser negativo"}), 400
        if desconto > total:
            return jsonify({"ok": False, "erro": "Desconto não pode ser maior que o total"}), 400
        total -= desconto
        cur = db.execute(
            "INSERT INTO vendas (comanda_id, mesa_id, usuario_id, valor_total, desconto, forma_pagamento, tipo) VALUES (?,?,?,?,?,?, 'mesa')",
            (comanda["id"], mesa_id, session["usuario_id"], total, desconto, forma)
        )
        venda_id = cur.lastrowid
        itens = db.execute("SELECT * FROM itens_comanda WHERE comanda_id=?", (comanda["id"],)).fetchall()
        for it in itens:
            db.execute(
                "INSERT INTO itens_venda (venda_id, produto_id, quantidade, preco_unitario, subtotal) VALUES (?,?,?,?,?)",
                (venda_id, it["produto_id"], it["quantidade"], it["preco_unitario"], it["subtotal"])
            )
            baixar_estoque(it["produto_id"], it["quantidade"], "Venda", session["usuario_id"])
        db.execute("UPDATE comandas SET status='fechada', fechamento=CURRENT_TIMESTAMP WHERE id=?", (comanda["id"],))
        db.execute("UPDATE mesas SET status='disponivel', valor_atual=0, reservada_para=NULL WHERE id=?", (mesa_id,))
        db.commit()
        log_auditoria("FECHAMENTO_MESA", f"Mesa {mesa_id} fechada - venda #{venda_id} - R$ {total:.2f}")
        return jsonify({"ok": True, "venda_id": venda_id, "total": total})
