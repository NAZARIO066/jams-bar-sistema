from flask import render_template, request, jsonify, session
from database import get_db
from auth import login_required, admin_required, log_auditoria
from services.fiado_service import calcular_status_fiado, recalcular_saldo_devedor


def register_clientes_routes(app):

    @app.route("/clientes")
    @login_required
    def clientes():
        return render_template("clientes.html")

    @app.route("/api/clientes")
    @login_required
    def api_clientes_list():
        db = get_db()
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(200, max(1, int(request.args.get("per_page", 50))))
        offset = (page - 1) * per_page
        total = db.execute("SELECT COUNT(*) as c FROM clientes WHERE ativo=1").fetchone()["c"]
        rows = db.execute("""
            SELECT c.*,
                (SELECT data_vencimento FROM fiado
                 WHERE cliente_id=c.id AND tipo='compra' AND (valor - valor_pago) > 0.01
                 ORDER BY data_vencimento ASC LIMIT 1
                ) as proximo_vencimento,
                (SELECT COUNT(*) FROM fiado
                 WHERE cliente_id=c.id AND tipo='compra' AND (valor - valor_pago) > 0.01
                 AND data_vencimento IS NOT NULL AND data_vencimento < date('now')
                ) as qtd_vencidos
            FROM clientes c WHERE c.ativo=1 ORDER BY c.nome LIMIT ? OFFSET ?
        """, (per_page, offset)).fetchall()
        result = []
        for c in rows:
            d = dict(c)
            d["tem_vencido"] = bool(d.pop("qtd_vencidos", 0))
            prox_venc = d.pop("proximo_vencimento", None)
            if prox_venc:
                status, dias = calcular_status_fiado(prox_venc)
                d["dias_vencimento"] = dias
                d["proximo_vencimento"] = prox_venc
                d["status_fiado"] = status
            else:
                d["status_fiado"] = "normal"
                d["dias_vencimento"] = None
            result.append(d)
        return jsonify({"data": result, "total": total, "page": page, "per_page": per_page})

    @app.route("/api/fiados")
    @login_required
    def api_fiados_list():
        db = get_db()
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(200, max(1, int(request.args.get("per_page", 50))))
        offset = (page - 1) * per_page
        cliente_id = request.args.get("cliente_id", type=int)
        tipo = request.args.get("tipo")
        query = """
            SELECT f.*, c.nome as cliente_nome, u.nome as usuario_nome
            FROM fiado f
            JOIN clientes c ON f.cliente_id=c.id
            LEFT JOIN usuarios u ON f.usuario_id=u.id
        """
        params = []
        conditions = []
        if cliente_id:
            conditions.append("f.cliente_id=?")
            params.append(cliente_id)
        if tipo:
            conditions.append("f.tipo=?")
            params.append(tipo)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY f.data_hora DESC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])
        rows = db.execute(query, params).fetchall()
        total_query = "SELECT COUNT(*) as c FROM fiado f JOIN clientes c ON f.cliente_id=c.id"
        if conditions:
            total_query += " WHERE " + " AND ".join(conditions)
        total = db.execute(total_query, params[:-2]).fetchone()["c"]
        result = []
        for f in rows:
            d = dict(f)
            d["saldo"] = d["valor"] - d.get("valor_pago", 0)
            if d["tipo"] == "compra" and d.get("data_vencimento") and d["saldo"] > 0.01:
                status, dias = calcular_status_fiado(d["data_vencimento"])
                d["dias_vencimento"] = dias
                d["status"] = status
            result.append(d)
        return jsonify({"data": result, "total": total, "page": page, "per_page": per_page})

    @app.route("/api/clientes", methods=["POST"])
    @admin_required
    def api_cliente_create():
        db = get_db()
        d = request.json or {}
        cur = db.execute(
            "INSERT INTO clientes (nome, telefone, cpf, endereco, limite_fiado, observacao) VALUES (?,?,?,?,?,?)",
            (d.get("nome"), d.get("telefone"), d.get("cpf"), d.get("endereco"),
             float(d.get("limite_fiado", 0)), d.get("observacao"))
        )
        db.commit()
        log_auditoria("CRIAR_CLIENTE", f"Cliente {d.get('nome')} criado")
        return jsonify({"ok": True, "id": cur.lastrowid})

    @app.route("/api/clientes/<int:cid>", methods=["PUT"])
    @admin_required
    def api_cliente_update(cid):
        db = get_db()
        d = request.json or {}
        db.execute(
            "UPDATE clientes SET nome=?, telefone=?, cpf=?, endereco=?, limite_fiado=?, observacao=? WHERE id=?",
            (d.get("nome"), d.get("telefone"), d.get("cpf"), d.get("endereco"),
             float(d.get("limite_fiado", 0)), d.get("observacao"), cid)
        )
        db.commit()
        log_auditoria("EDITAR_CLIENTE", f"Cliente #{cid} atualizado")
        return jsonify({"ok": True})

    @app.route("/api/clientes/<int:cid>", methods=["DELETE"])
    @admin_required
    def api_cliente_delete(cid):
        db = get_db()
        db.execute("UPDATE clientes SET ativo=0 WHERE id=?", (cid,))
        db.commit()
        log_auditoria("EXCLUIR_CLIENTE", f"Cliente #{cid} desativado")
        return jsonify({"ok": True})

    @app.route("/api/clientes/<int:cid>/fiado")
    @login_required
    def api_cliente_fiado(cid):
        db = get_db()
        cli = db.execute("SELECT * FROM clientes WHERE id=?", (cid,)).fetchone()
        if not cli:
            return jsonify({"erro": "Cliente não encontrado"}), 404
        movs = db.execute("""
            SELECT f.*, u.nome as usuario, v.id as venda_id
            FROM fiado f LEFT JOIN usuarios u ON f.usuario_id=u.id
            LEFT JOIN vendas v ON f.venda_id=v.id
            WHERE f.cliente_id=? ORDER BY f.data_vencimento ASC, f.data_hora DESC LIMIT 200
        """, (cid,)).fetchall()
        lista = []
        for m in movs:
            d = dict(m)
            d["saldo"] = d["valor"] - d.get("valor_pago", 0)
            if d["tipo"] == "compra" and d.get("data_vencimento") and d["saldo"] > 0.01:
                status, dias = calcular_status_fiado(d["data_vencimento"])
                d["dias_vencimento"] = dias
                d["status"] = status
            lista.append(d)
        return jsonify({"cliente": dict(cli), "movimentacoes": lista})

    @app.route("/api/clientes/<int:cid>/pagamento", methods=["POST"])
    @admin_required
    def api_cliente_pagamento(cid):
        db = get_db()
        d = request.json or {}
        valor = float(d.get("valor", 0))
        obs = d.get("observacao", "")
        if valor <= 0:
            return jsonify({"ok": False, "erro": "Valor inválido"}), 400
        cli = db.execute("SELECT * FROM clientes WHERE id=?", (cid,)).fetchone()
        if not cli:
            return jsonify({"ok": False, "erro": "Cliente não encontrado"}), 404
        restante = valor
        dividas = db.execute("""
            SELECT id, valor, valor_pago FROM fiado
            WHERE cliente_id=? AND tipo='compra' AND (valor - valor_pago) > 0.01
            ORDER BY data_vencimento ASC, data_hora ASC
        """, (cid,)).fetchall()
        for d_ in dividas:
            if restante <= 0.01:
                break
            saldo = d_["valor"] - d_["valor_pago"]
            abate = min(saldo, restante)
            db.execute("UPDATE fiado SET valor_pago = valor_pago + ? WHERE id=?", (abate, d_["id"]))
            restante -= abate
        db.execute(
            "INSERT INTO fiado (cliente_id, tipo, valor, usuario_id, observacao) VALUES (?,?,?,?,?)",
            (cid, "pagamento", valor, session["usuario_id"], obs)
        )
        recalcular_saldo_devedor(cid)
        db.commit()
        log_auditoria("PAGAMENTO_FIADO", f"Cliente {cli['nome']} pagou R$ {valor:.2f}")
        return jsonify({"ok": True})

    @app.route("/api/clientes/buscar")
    @login_required
    def api_clientes_buscar():
        q = request.args.get("q", "").strip()
        db = get_db()
        if q:
            like = f"%{q}%"
            rows = db.execute("SELECT * FROM clientes WHERE ativo=1 AND (nome LIKE ? OR cpf LIKE ? OR telefone LIKE ?) ORDER BY nome LIMIT 20", (like, like, like)).fetchall()
        else:
            rows = db.execute("SELECT * FROM clientes WHERE ativo=1 ORDER BY nome LIMIT 50").fetchall()
        return jsonify([dict(r) for r in rows])
