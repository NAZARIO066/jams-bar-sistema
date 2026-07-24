from flask import render_template, request, jsonify, session
from database import get_db
from auth import login_required, admin_required, log_auditoria
from services.estoque_service import registrar_entrada, produto_existe


def register_estoque_routes(app):

    @app.route("/estoque")
    @login_required
    def estoque():
        return render_template("estoque.html")

    @app.route("/api/estoque")
    @login_required
    def api_estoque_list():
        db = get_db()
        rows = db.execute("""
            SELECT p.*, c.nome as categoria
            FROM produtos p LEFT JOIN categorias c ON p.categoria_id=c.id
            WHERE p.ativo=1 ORDER BY p.nome
        """).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["critico"] = d["estoque"] <= d["estoque_minimo"]
            d["zerado"] = d["estoque"] <= 0
            result.append(d)
        return jsonify(result)

    @app.route("/api/estoque/entrada", methods=["POST"])
    @admin_required
    def api_estoque_entrada():
        d = request.json or {}
        pid = d.get("produto_id")
        qtd = float(d.get("quantidade", 0))
        obs = d.get("observacao", "")
        if qtd <= 0:
            return jsonify({"ok": False, "erro": "Quantidade inválida"}), 400
        p = produto_existe(pid)
        if not p:
            return jsonify({"ok": False, "erro": "Produto não encontrado ou inativo"}), 404
        registrar_entrada(pid, qtd, session["usuario_id"], obs)
        db = get_db()
        db.commit()
        log_auditoria("ENTRADA_ESTOQUE", f"Produto #{pid} +{qtd}")
        return jsonify({"ok": True})

    @app.route("/api/estoque/saida", methods=["POST"])
    @admin_required
    def api_estoque_saida():
        db = get_db()
        d = request.json or {}
        pid = d.get("produto_id")
        qtd = float(d.get("quantidade", 0))
        motivo = d.get("motivo", "Ajuste")
        if qtd <= 0:
            return jsonify({"ok": False, "erro": "Quantidade inválida"}), 400
        p = produto_existe(pid)
        if not p:
            return jsonify({"ok": False, "erro": "Produto não encontrado ou inativo"}), 404
        if p["estoque"] < qtd:
            return jsonify({"ok": False, "erro": "Estoque insuficiente"}), 400
        db.execute("UPDATE produtos SET estoque = estoque - ? WHERE id=?", (qtd, pid))
        db.execute(
            "INSERT INTO movimentacoes (produto_id, tipo, quantidade, motivo, usuario_id) VALUES (?,?,?,?,?)",
            (pid, "saida", qtd, motivo, session["usuario_id"])
        )
        db.commit()
        log_auditoria("SAIDA_ESTOQUE", f"Produto #{pid} -{qtd} ({motivo})")
        return jsonify({"ok": True})

    @app.route("/api/movimentacoes")
    @login_required
    def api_movimentacoes():
        db = get_db()
        rows = db.execute("""
            SELECT m.*, p.nome as produto, u.nome as usuario
            FROM movimentacoes m JOIN produtos p ON m.produto_id=p.id
            LEFT JOIN usuarios u ON m.usuario_id=u.id
            ORDER BY m.data_hora DESC LIMIT 200
        """).fetchall()
        return jsonify([dict(r) for r in rows])
