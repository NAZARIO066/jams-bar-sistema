from datetime import date, timedelta
from flask import render_template, request, jsonify, session
from database import get_db
from auth import login_required, log_auditoria
from services.venda_service import processar_venda_direta
from services.fiado_service import tem_fiado_vencido


def register_vendas_routes(app):

    @app.route("/vendas")
    @login_required
    def vendas():
        return render_template("vendas.html")

    @app.route("/api/venda/direta", methods=["POST"])
    @login_required
    def api_venda_direta():
        d = request.json or {}
        itens = d.get("itens", [])
        desconto = float(d.get("desconto", 0))
        forma = d.get("forma_pagamento", "Dinheiro")
        cliente_id = d.get("cliente_id")
        dias_vencimento = int(d.get("dias_vencimento", 30))

        if not itens:
            return jsonify({"ok": False, "erro": "Nenhum item"}), 400

        if forma == "Fiado":
            if not cliente_id:
                return jsonify({"ok": False, "erro": "Selecione um cliente para fiado"}), 400
            db = get_db()
            cli = db.execute("SELECT * FROM clientes WHERE id=? AND ativo=1", (cliente_id,)).fetchone()
            if not cli:
                return jsonify({"ok": False, "erro": "Cliente inválido"}), 400
            if tem_fiado_vencido(cliente_id):
                return jsonify({"ok": False, "erro": "\U0001f6ab Cliente com fiado VENCIDO! Quite as dívidas antes de nova compra."}), 400
            total_temp = sum(
                float(it.get("quantidade", 0)) * (db.execute("SELECT preco FROM produtos WHERE id=?", (it["produto_id"],)).fetchone() or {}).get("preco", 0)
                for it in itens
            )
            if cli["limite_fiado"] > 0 and cli["saldo_devedor"] + total_temp > cli["limite_fiado"]:
                return jsonify({"ok": False, "erro": f"Limite de fiado excedido (disponível: R$ {cli['limite_fiado']-cli['saldo_devedor']:.2f})"}), 400

        resultado, status = processar_venda_direta(
            itens=itens, desconto=desconto, forma_pagamento=forma,
            usuario_id=session["usuario_id"],
            cliente_id=cliente_id, dias_vencimento=dias_vencimento
        )
        if not resultado.get("ok"):
            return jsonify(resultado), status
        log_auditoria("VENDA_DIRETA", f"Venda #{resultado['venda_id']} - R$ {resultado['total']:.2f} - {forma}")
        return jsonify(resultado), status
