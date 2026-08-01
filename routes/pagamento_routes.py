import os
from flask import request, jsonify, session, render_template
from database import get_db
from auth import any_permission_required, has_permission, log_auditoria, permission_required
from datetime import datetime
from services.fiado_service import tem_fiado_vencido


def register_pagamento_routes(app):

    @app.route("/api/comanda/<int:comanda_id>/pagamento_parcial", methods=["POST"])
    @permission_required("mesas.fechar", "vendas.fechar")
    def pagamento_parcial(comanda_id):
        db = get_db()
        data = request.json or {}
        itens_pagamento = data.get("itens", [])
        forma = data.get("forma_pagamento", "Dinheiro")
        nome_pessoa = (data.get("nome_pessoa") or "").strip() or None
        cliente_id = data.get("cliente_id")
        try:
            desconto = float(data.get("desconto", 0))
        except (TypeError, ValueError):
            return jsonify({"ok": False, "erro": "Desconto inválido"}), 400
        if desconto < 0:
            return jsonify({"ok": False, "erro": "Desconto não pode ser negativo"}), 400
        if desconto > 0 and not has_permission("vendas.desconto"):
            log_auditoria("ACESSO_NEGADO", f"Tentativa de desconto em pagamento parcial da comanda {comanda_id}")
            return jsonify({"ok": False, "erro": "Você não tem permissão para conceder desconto."}), 403
        if forma not in {"Dinheiro", "PIX", "Crédito", "Débito", "Fiado"}:
            return jsonify({"ok": False, "erro": "Forma de pagamento inválida"}), 400
        if not itens_pagamento:
            return jsonify({"ok": False, "erro": "Nenhum item selecionado"}), 400
        comanda = db.execute(
            "SELECT * FROM comandas WHERE id=? AND status='aberta'", (comanda_id,)
        ).fetchone()
        if not comanda:
            return jsonify({"ok": False, "erro": "Comanda não encontrada ou fechada"}), 400
        if forma == "Fiado":
            if not cliente_id:
                return jsonify({"ok": False, "erro": "Selecione um cliente para fiado"}), 400
            cli = db.execute(
                "SELECT * FROM clientes WHERE id=? AND ativo=1", (cliente_id,)
            ).fetchone()
            if not cli:
                return jsonify({"ok": False, "erro": "Cliente inválido"}), 400
            if tem_fiado_vencido(cliente_id):
                return jsonify({"ok": False, "erro": "Cliente com fiado vencido"}), 400
        total_pago = 0
        itens_processados = []
        for item_pag in itens_pagamento:
            item_id = item_pag["item_id"]
            qtd_paga = float(item_pag.get("quantidade", 1))
            item = db.execute(
                "SELECT * FROM itens_comanda WHERE id=? AND comanda_id=?",
                (item_id, comanda_id),
            ).fetchone()
            if not item:
                continue
            ja_pago = db.execute(
                "SELECT COALESCE(SUM(quantidade_paga), 0) as total_pago "
                "FROM pagamentos_parciais_itens WHERE item_comanda_id=?",
                (item_id,),
            ).fetchone()["total_pago"]
            disponivel = item["quantidade"] - ja_pago
            if qtd_paga > disponivel:
                qtd_paga = disponivel
            if qtd_paga <= 0:
                continue
            valor_item = item["preco_unitario"] * qtd_paga
            total_pago += valor_item
            itens_processados.append(
                {
                    "item_id": item_id,
                    "qtd": qtd_paga,
                    "valor": valor_item,
                }
            )
        if total_pago <= 0:
            return jsonify({"ok": False, "erro": "Nenhum item disponível para pagamento"}), 400
        if desconto > total_pago:
            return jsonify({"ok": False, "erro": "Desconto não pode ser maior que o pagamento"}), 400
        if desconto > 0:
            total_pago -= desconto
        if forma == "Fiado" and cli["limite_fiado"] > 0 and cli["saldo_devedor"] + total_pago > cli["limite_fiado"]:
            return jsonify({"ok": False, "erro": "Limite de fiado excedido"}), 400
        cur = db.execute(
            "INSERT INTO pagamentos_parciais "
            "(comanda_id, usuario_id, valor_total, desconto, forma_pagamento, nome_pessoa, cliente_id) "
            "VALUES (?,?,?,?,?,?,?)",
            (
                comanda_id,
                session["usuario_id"],
                total_pago,
                desconto,
                forma,
                nome_pessoa,
                cliente_id if forma == "Fiado" else None,
            ),
        )
        pagamento_id = cur.lastrowid
        for ip in itens_processados:
            db.execute(
                "INSERT INTO pagamentos_parciais_itens "
                "(pagamento_parcial_id, item_comanda_id, quantidade_paga, valor_unitario, subtotal) "
                "VALUES (?,?,?,?,?)",
                (pagamento_id, ip["item_id"], ip["qtd"], ip["valor"] / ip["qtd"], ip["valor"]),
            )
        if forma == "Fiado" and cliente_id:
            from datetime import date, timedelta

            venc = (date.today() + timedelta(days=30)).isoformat()
            db.execute(
                "INSERT INTO fiado (cliente_id, tipo, valor, usuario_id, data_vencimento, observacao) "
                "VALUES (?,?,?,?,?,?)",
                (cliente_id, "compra", total_pago, session["usuario_id"], venc, f"Pagamento parcial #{pagamento_id}"),
            )
            db.execute(
                "UPDATE clientes SET saldo_devedor = saldo_devedor + ? WHERE id=?",
                (total_pago, cliente_id),
            )
        total_comanda = db.execute(
            "SELECT COALESCE(SUM(subtotal), 0) as t FROM itens_comanda WHERE comanda_id=?",
            (comanda_id,),
        ).fetchone()["t"]
        total_ja_pago = db.execute(
            "SELECT COALESCE(SUM(valor_total), 0) as t FROM pagamentos_parciais WHERE comanda_id=?",
            (comanda_id,),
        ).fetchone()["t"]
        restante = max(0, total_comanda - total_ja_pago)
        db.commit()
        return jsonify(
            {
                "ok": True,
                "pagamento_id": pagamento_id,
                "valor_pago": total_pago,
                "restante": restante,
                "total_comanda": total_comanda,
            }
        )

    @app.route("/api/comanda/<int:comanda_id>/pagamentos")
    @permission_required("mesas.acessar")
    def pagamentos_comanda(comanda_id):
        db = get_db()
        pagamentos = db.execute(
            "SELECT pp.*, u.nome as usuario FROM pagamentos_parciais pp "
            "LEFT JOIN usuarios u ON pp.usuario_id=u.id "
            "WHERE pp.comanda_id=? ORDER BY pp.data_hora DESC",
            (comanda_id,),
        ).fetchall()
        result = []
        for p in pagamentos:
            d = dict(p)
            itens = db.execute(
                "SELECT ppi.*, ic.produto_id, pr.nome as produto_nome "
                "FROM pagamentos_parciais_itens ppi "
                "JOIN itens_comanda ic ON ppi.item_comanda_id=ic.id "
                "JOIN produtos pr ON ic.produto_id=pr.id "
                "WHERE ppi.pagamento_parcial_id=?",
                (p["id"],),
            ).fetchall()
            d["itens"] = [dict(i) for i in itens]
            result.append(d)
        total_comanda = db.execute(
            "SELECT COALESCE(SUM(subtotal), 0) as t FROM itens_comanda WHERE comanda_id=?",
            (comanda_id,),
        ).fetchone()["t"]
        total_pago = db.execute(
            "SELECT COALESCE(SUM(valor_total), 0) as t FROM pagamentos_parciais WHERE comanda_id=?",
            (comanda_id,),
        ).fetchone()["t"]
        return jsonify(
            {
                "pagamentos": result,
                "total_comanda": total_comanda,
                "total_pago": total_pago,
                "restante": max(0, total_comanda - total_pago),
            }
        )

    @app.route("/api/config/acesso_rapido", methods=["GET"])
    @permission_required("pdv.acessar")
    def get_acesso_rapido():
        db = get_db()
        config = db.execute(
            "SELECT * FROM config_acesso_rapido WHERE id=1"
        ).fetchone()
        if not config:
            db.execute(
                "INSERT OR IGNORE INTO config_acesso_rapido (id, modo) VALUES (1, 'automatico')"
            )
            db.commit()
            config = db.execute(
                "SELECT * FROM config_acesso_rapido WHERE id=1"
            ).fetchone()
        produtos_fixos = []
        if config["modo"] in ("manual", "misto"):
            fixos = db.execute(
                "SELECT p.id, p.nome, p.preco, p.estoque, p.unidade "
                "FROM acesso_rapido_produtos arp "
                "JOIN produtos p ON arp.produto_id=p.id AND p.ativo=1 "
                "ORDER BY arp.ordem"
            ).fetchall()
            produtos_fixos = [dict(r) for r in fixos]
        return jsonify({"modo": config["modo"], "produtos_fixos": produtos_fixos})

    @app.route("/api/config/acesso_rapido", methods=["POST"])
    @permission_required("configuracoes.acessar")
    def save_acesso_rapido():
        db = get_db()
        data = request.json or {}
        modo = data.get("modo", "automatico")
        if modo not in ("manual", "automatico", "misto"):
            return jsonify({"ok": False, "erro": "Modo inválido"}), 400
        produto_ids = data.get("produto_ids", [])
        db.execute(
            "INSERT OR REPLACE INTO config_acesso_rapido (id, modo) VALUES (1, ?)",
            (modo,),
        )
        db.execute("DELETE FROM acesso_rapido_produtos")
        for idx, pid in enumerate(produto_ids):
            db.execute(
                "INSERT INTO acesso_rapido_produtos (produto_id, ordem) VALUES (?, ?)",
                (pid, idx),
            )
        db.commit()
        return jsonify({"ok": True})

    @app.route("/api/mesas/disponiveis")
    @permission_required("mesas.acessar")
    def mesas_disponiveis():
        db = get_db()
        mesas = db.execute(
            "SELECT id, numero, capacidade FROM mesas WHERE status='disponivel' ORDER BY numero"
        ).fetchall()
        return jsonify([dict(m) for m in mesas])

    # ── Impressão Térmica ────────────────────────────────────────────────────

    def _get_empresa_ctx():
        db = get_db()
        row = db.execute("SELECT * FROM empresa WHERE id=1").fetchone()
        logo_path = os.path.join("static", "uploads", "logo.png")
        logo_url = "/" + logo_path if os.path.exists(logo_path) else None
        e = dict(row) if row else {}
        return {
            "nome": e.get("nome_fantasia") or e.get("razao_social") or "JAM'S BURGUER",
            "endereco": e.get("endereco", ""),
            "telefone": e.get("telefone", ""),
            "cnpj": e.get("cnpj", ""),
            "logo": logo_url,
        }

    def _now_str():
        return datetime.now().strftime("%d/%m/%Y %H:%M")

    @app.route("/imprimir/comanda/<int:comanda_id>")
    @any_permission_required("impressao.imprimir", "impressao.reimprimir")
    def imprimir_comanda(comanda_id):
        db = get_db()
        comanda = db.execute("""
            SELECT c.*, m.numero as mesa_numero, u.nome as funcionario
            FROM comandas c
            JOIN mesas m ON c.mesa_id=m.id
            JOIN usuarios u ON c.usuario_id=u.id
            WHERE c.id=?
        """, (comanda_id,)).fetchone()
        if not comanda:
            return "Comanda não encontrada", 404
        itens = db.execute("""
            SELECT ic.*, p.nome as produto_nome
            FROM itens_comanda ic
            JOIN produtos p ON ic.produto_id=p.id
            WHERE ic.comanda_id=? ORDER BY ic.criado_em
        """, (comanda_id,)).fetchall()
        total = sum(i["subtotal"] for i in itens)
        return render_template(
            "prints/comanda.html",
            comanda=comanda,
            itens=itens,
            total=total,
            empresa=_get_empresa_ctx(),
            now=_now_str(),
            width=80,
        )

    @app.route("/imprimir/venda/<int:venda_id>")
    @any_permission_required("impressao.imprimir", "impressao.reimprimir")
    def imprimir_venda(venda_id):
        db = get_db()
        venda = db.execute("""
            SELECT v.*, v.valor_total as total, v.data as data_venda,
                   u.nome as funcionario, cm.cliente_nome
            FROM vendas v
            JOIN usuarios u ON v.usuario_id=u.id
            LEFT JOIN comandas cm ON v.comanda_id=cm.id
            WHERE v.id=?
        """, (venda_id,)).fetchone()
        if not venda:
            return "Venda não encontrada", 404
        itens = db.execute("""
            SELECT iv.*, p.nome as produto_nome
            FROM itens_venda iv
            JOIN produtos p ON iv.produto_id=p.id
            WHERE iv.venda_id=? ORDER BY iv.id
        """, (venda_id,)).fetchall()
        return render_template(
            "prints/comprovante_venda.html",
            venda=venda,
            itens=itens,
            empresa=_get_empresa_ctx(),
            now=_now_str(),
            width=80,
        )

    @app.route("/imprimir/mesa/<int:comanda_id>")
    @any_permission_required("impressao.imprimir", "impressao.reimprimir")
    def imprimir_mesa(comanda_id):
        db = get_db()
        comanda = db.execute("""
            SELECT c.*, m.numero as mesa_numero, u.nome as funcionario
            FROM comandas c
            JOIN mesas m ON c.mesa_id=m.id
            JOIN usuarios u ON c.usuario_id=u.id
            WHERE c.id=?
        """, (comanda_id,)).fetchone()
        if not comanda:
            return "Comanda não encontrada", 404
        itens = db.execute("""
            SELECT ic.*, p.nome as produto_nome
            FROM itens_comanda ic
            JOIN produtos p ON ic.produto_id=p.id
            WHERE ic.comanda_id=? ORDER BY ic.criado_em
        """, (comanda_id,)).fetchall()
        total = sum(i["subtotal"] for i in itens)
        pagamentos = db.execute(
            "SELECT * FROM pagamentos_parciais WHERE comanda_id=? ORDER BY data_hora",
            (comanda_id,),
        ).fetchall()
        total_pago = sum(p["valor_total"] for p in pagamentos)
        restante = max(0, total - total_pago)
        return render_template(
            "prints/comprovante_mesa.html",
            comanda=comanda,
            itens=itens,
            total=total,
            desconto=0,
            acrescimo=0,
            valor_recebido=total_pago if total_pago > 0 else None,
            troco=0,
            empresa=_get_empresa_ctx(),
            now=_now_str(),
            width=80,
        )

    @app.route("/imprimir/parcial/<int:pagamento_id>")
    @any_permission_required("impressao.imprimir", "impressao.reimprimir")
    def imprimir_parcial(pagamento_id):
        db = get_db()
        pagamento = db.execute(
            "SELECT pp.*, m.numero as mesa_numero "
            "FROM pagamentos_parciais pp "
            "JOIN comandas c ON pp.comanda_id=c.id "
            "JOIN mesas m ON c.mesa_id=m.id "
            "WHERE pp.id=?",
            (pagamento_id,),
        ).fetchone()
        if not pagamento:
            return "Pagamento não encontrado", 404
        comanda = db.execute(
            "SELECT * FROM comandas WHERE id=?", (pagamento["comanda_id"],)
        ).fetchone()
        itens_pagos = db.execute(
            "SELECT ppi.*, p.nome as produto_nome "
            "FROM pagamentos_parciais_itens ppi "
            "JOIN itens_comanda ic ON ppi.item_comanda_id=ic.id "
            "JOIN produtos p ON ic.produto_id=p.id "
            "WHERE ppi.pagamento_parcial_id=?",
            (pagamento_id,),
        ).fetchall()
        total_comanda = db.execute(
            "SELECT COALESCE(SUM(subtotal), 0) as t FROM itens_comanda WHERE comanda_id=?",
            (pagamento["comanda_id"],),
        ).fetchone()["t"]
        total_pago_geral = db.execute(
            "SELECT COALESCE(SUM(valor_total), 0) as t FROM pagamentos_parciais WHERE comanda_id=?",
            (pagamento["comanda_id"],),
        ).fetchone()["t"]
        saldo_restante = max(0, total_comanda - total_pago_geral)
        return render_template(
            "prints/comprovante_parcial.html",
            comanda=comanda,
            pagamento=pagamento,
            itens_pagos=itens_pagos,
            pagante=pagamento["nome_pessoa"] or "",
            saldo_restante=saldo_restante,
            empresa=_get_empresa_ctx(),
            now=_now_str(),
            width=80,
        )
