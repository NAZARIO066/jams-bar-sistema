from flask import render_template, request, jsonify, session
from database import get_db
from auth import login_required, admin_required, log_auditoria
from datetime import date


def register_caixa_routes(app):

    @app.route("/caixa")
    @login_required
    def caixa():
        return render_template("caixa.html")

    @app.route("/api/caixa/status")
    @login_required
    def api_caixa_status():
        db = get_db()
        cx = db.execute("SELECT * FROM caixas WHERE usuario_id=? AND fechamento IS NULL ORDER BY id DESC LIMIT 1", (session["usuario_id"],)).fetchone()
        if not cx:
            return jsonify({"aberto": False})
        resumo = db.execute("""
            SELECT COUNT(*) as qtd, COALESCE(SUM(valor_total),0) as total
            FROM vendas WHERE date(data)=date(?) AND usuario_id=? AND status != 'cancelada'
        """, (cx["abertura"], session["usuario_id"])).fetchone()
        return jsonify({
            "aberto": True,
            "caixa": dict(cx),
            "vendas_hoje": dict(resumo)
        })

    @app.route("/api/caixa/abrir", methods=["POST"])
    @admin_required
    def api_caixa_abrir():
        db = get_db()
        aberto = db.execute("SELECT id FROM caixas WHERE usuario_id=? AND fechamento IS NULL", (session["usuario_id"],)).fetchone()
        if aberto:
            return jsonify({"ok": False, "erro": "Já existe caixa aberto"}), 400
        valor = float((request.json or {}).get("valor_inicial", 0))
        db.execute("INSERT INTO caixas (usuario_id, valor_inicial) VALUES (?,?)", (session["usuario_id"], valor))
        db.commit()
        log_auditoria("CAIXA_ABERTO", f"Caixa aberto com R$ {valor:.2f}")
        return jsonify({"ok": True})

    @app.route("/api/caixa/fechar", methods=["POST"])
    @admin_required
    def api_caixa_fechar():
        db = get_db()
        d = request.json or {}
        cx = db.execute("SELECT * FROM caixas WHERE usuario_id=? AND fechamento IS NULL ORDER BY id DESC LIMIT 1", (session["usuario_id"],)).fetchone()
        if not cx:
            return jsonify({"ok": False, "erro": "Nenhum caixa aberto"}), 400
        total = db.execute("SELECT COALESCE(SUM(valor_total),0) as t, COUNT(*) as c FROM vendas WHERE date(data)=date(?) AND usuario_id=? AND status != 'cancelada'", (cx["abertura"], session["usuario_id"])).fetchone()
        valor_final = float(d.get("valor_final", 0))
        sup = db.execute("SELECT COALESCE(SUM(valor),0) as t FROM suprimento_sangria WHERE caixa_id=? AND tipo='suprimento'", (cx["id"],)).fetchone()["t"]
        sang = db.execute("SELECT COALESCE(SUM(valor),0) as t FROM suprimento_sangria WHERE caixa_id=? AND tipo='sangria'", (cx["id"],)).fetchone()["t"]
        valor_esperado = cx["valor_inicial"] + total["t"] + sup - sang
        diferenca = round(valor_final - valor_esperado, 2)
        db.execute(
            "UPDATE caixas SET fechamento=CURRENT_TIMESTAMP, valor_final=?, total_vendas=?, quantidade_vendas=?, diferenca=?, observacao=? WHERE id=?",
            (valor_final, total["t"], total["c"], diferenca, d.get("observacao", ""), cx["id"])
        )
        db.commit()
        log_auditoria("CAIXA_FECHADO", f"Caixa fechado - R$ {total['t']:.2f} em {total['c']} vendas (dif: R$ {diferenca:.2f})")
        return jsonify({"ok": True, "total": total["t"], "qtd": total["c"], "diferenca": diferenca, "esperado": valor_esperado, "valor_final": valor_final})

    @app.route("/api/caixa/suprimento", methods=["POST"])
    @admin_required
    def api_caixa_suprimento():
        db = get_db()
        d = request.json or {}
        valor = float(d.get("valor", 0))
        motivo = d.get("motivo", "")
        if valor <= 0:
            return jsonify({"ok": False, "erro": "Valor inválido"}), 400
        cx = db.execute("SELECT * FROM caixas WHERE usuario_id=? AND fechamento IS NULL ORDER BY id DESC LIMIT 1",
                        (session["usuario_id"],)).fetchone()
        if not cx:
            return jsonify({"ok": False, "erro": "Nenhum caixa aberto"}), 400
        db.execute("INSERT INTO suprimento_sangria (caixa_id, usuario_id, tipo, valor, motivo) VALUES (?,?,?,?,?)",
                   (cx["id"], session["usuario_id"], "suprimento", valor, motivo))
        db.commit()
        log_auditoria("SUPRIMENTO", f"R$ {valor:.2f} - {motivo}")
        return jsonify({"ok": True})

    @app.route("/api/caixa/sangria", methods=["POST"])
    @admin_required
    def api_caixa_sangria():
        db = get_db()
        d = request.json or {}
        valor = float(d.get("valor", 0))
        motivo = d.get("motivo", "")
        if valor <= 0:
            return jsonify({"ok": False, "erro": "Valor inválido"}), 400
        cx = db.execute("SELECT * FROM caixas WHERE usuario_id=? AND fechamento IS NULL ORDER BY id DESC LIMIT 1",
                        (session["usuario_id"],)).fetchone()
        if not cx:
            return jsonify({"ok": False, "erro": "Nenhum caixa aberto"}), 400
        db.execute("INSERT INTO suprimento_sangria (caixa_id, usuario_id, tipo, valor, motivo) VALUES (?,?,?,?,?)",
                   (cx["id"], session["usuario_id"], "sangria", valor, motivo))
        db.commit()
        log_auditoria("SANGRIA", f"R$ {valor:.2f} - {motivo}")
        return jsonify({"ok": True})

    @app.route("/api/caixa/movimentacoes")
    @login_required
    def api_caixa_movimentacoes():
        db = get_db()
        cx = db.execute("SELECT * FROM caixas WHERE usuario_id=? AND fechamento IS NULL ORDER BY id DESC LIMIT 1",
                        (session["usuario_id"],)).fetchone()
        if not cx:
            return jsonify([])
        rows = db.execute("""
            SELECT ss.*, u.nome as usuario
            FROM suprimento_sangria ss LEFT JOIN usuarios u ON ss.usuario_id=u.id
            WHERE ss.caixa_id=? ORDER BY ss.data_hora DESC
        """, (cx["id"],)).fetchall()
        return jsonify([dict(r) for r in rows])
