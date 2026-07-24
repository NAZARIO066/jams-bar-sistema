from datetime import date, timedelta
from flask import render_template, request, jsonify, session
from database import get_db
from auth import login_required, admin_required


def register_relatorios_routes(app):

    @app.route("/relatorios")
    @login_required
    def relatorios():
        return render_template("relatorios.html")

    @app.route("/api/relatorios/vendas")
    @login_required
    def api_rel_vendas():
        db = get_db()
        inicio = request.args.get("inicio")
        fim = request.args.get("fim")
        hoje = date.today()
        if not inicio or not fim:
            inicio = fim = hoje.isoformat()
        vendas = db.execute("""
            SELECT v.*, u.nome as funcionario, m.numero as mesa
            FROM vendas v JOIN usuarios u ON v.usuario_id=u.id
            LEFT JOIN mesas m ON v.mesa_id=m.id
            WHERE date(v.data) BETWEEN ? AND ? ORDER BY v.data DESC
        """, (inicio, fim)).fetchall()
        totais = db.execute("""
            SELECT COALESCE(SUM(valor_total),0) as total, COUNT(*) as qtd, COALESCE(AVG(valor_total),0) as ticket
            FROM vendas WHERE date(data) BETWEEN ? AND ? AND status != 'cancelada'
        """, (inicio, fim)).fetchone()
        return jsonify({
            "vendas": [dict(v) for v in vendas],
            "totais": dict(totais),
            "inicio": inicio,
            "fim": fim,
        })

    @app.route("/api/relatorios/mesas")
    @login_required
    def api_rel_mesas():
        db = get_db()
        rows = db.execute("""
            SELECT m.numero, COUNT(v.id) as pedidos, COALESCE(SUM(v.valor_total),0) as total,
                   COALESCE(AVG((julianday(v.data) - julianday(c.abertura)) * 24), 0) as horas_media
            FROM mesas m
            LEFT JOIN vendas v ON v.mesa_id=m.id AND v.status != 'cancelada'
            LEFT JOIN comandas c ON v.comanda_id=c.id
            GROUP BY m.id ORDER BY total DESC
        """).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route("/api/relatorios/produtos")
    @login_required
    def api_rel_produtos():
        db = get_db()
        mais = db.execute("""
            SELECT p.nome, SUM(iv.quantidade) as qtd, SUM(iv.subtotal) as total
            FROM itens_venda iv JOIN vendas v ON iv.venda_id=v.id
            JOIN produtos p ON iv.produto_id=p.id
            WHERE date(v.data) >= date('now','-30 days') AND v.status != 'cancelada'
            GROUP BY p.id ORDER BY qtd DESC LIMIT 20
        """).fetchall()
        menos = db.execute("""
            SELECT p.nome, COALESCE(SUM(iv.quantidade),0) as qtd
            FROM produtos p LEFT JOIN itens_venda iv ON iv.produto_id=p.id
            LEFT JOIN vendas v ON iv.venda_id=v.id AND date(v.data) >= date('now','-30 days') AND v.status != 'cancelada'
            WHERE p.ativo=1 GROUP BY p.id ORDER BY qtd ASC LIMIT 20
        """).fetchall()
        sem_mov = db.execute("""
            SELECT p.nome, p.estoque FROM produtos p
            WHERE p.ativo=1 AND p.id NOT IN (
                SELECT DISTINCT produto_id FROM itens_venda iv
                JOIN vendas v ON iv.venda_id=v.id
                WHERE date(v.data) >= date('now','-30 days') AND v.status != 'cancelada'
            )
        """).fetchall()
        return jsonify({
            "mais_vendidos": [dict(r) for r in mais],
            "menos_vendidos": [dict(r) for r in menos],
            "sem_movimentacao": [dict(r) for r in sem_mov],
        })

    @app.route("/api/relatorios/vendas_produto")
    @login_required
    def api_rel_vendas_produto():
        db = get_db()
        inicio = request.args.get("inicio", date.today().isoformat())
        fim = request.args.get("fim", date.today().isoformat())
        rows = db.execute("""
            SELECT p.nome, COALESCE(c.nome, 'Sem categoria') as categoria,
                   SUM(iv.quantidade) as qtd, SUM(iv.subtotal) as total
            FROM itens_venda iv JOIN vendas v ON iv.venda_id=v.id
            JOIN produtos p ON iv.produto_id=p.id
            LEFT JOIN categorias c ON p.categoria_id=c.id
            WHERE date(v.data) BETWEEN ? AND ? AND v.status != 'cancelada'
            GROUP BY p.id ORDER BY total DESC
        """, (inicio, fim)).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route("/api/relatorios/vendas_categoria")
    @login_required
    def api_rel_vendas_categoria():
        db = get_db()
        inicio = request.args.get("inicio", date.today().isoformat())
        fim = request.args.get("fim", date.today().isoformat())
        rows = db.execute("""
            SELECT COALESCE(c.nome, 'Sem categoria') as categoria, SUM(iv.quantidade) as qtd, SUM(iv.subtotal) as total
            FROM itens_venda iv JOIN vendas v ON iv.venda_id=v.id
            JOIN produtos p ON iv.produto_id=p.id
            LEFT JOIN categorias c ON p.categoria_id=c.id
            WHERE date(v.data) BETWEEN ? AND ? AND v.status != 'cancelada'
            GROUP BY c.id ORDER BY total DESC
        """, (inicio, fim)).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route("/api/relatorios/vendas_garcom")
    @login_required
    def api_rel_vendas_garcom():
        db = get_db()
        inicio = request.args.get("inicio", date.today().isoformat())
        fim = request.args.get("fim", date.today().isoformat())
        rows = db.execute("""
            SELECT COALESCE(g.nome, 'Sem garçom') as garcom, COUNT(DISTINCT v.id) as pedidos, SUM(v.valor_total) as total
            FROM vendas v
            LEFT JOIN comandas c ON v.comanda_id=c.id
            LEFT JOIN garcons g ON c.garcom_id=g.id
            WHERE v.tipo='mesa' AND date(v.data) BETWEEN ? AND ? AND v.status != 'cancelada'
            GROUP BY g.id ORDER BY total DESC
        """, (inicio, fim)).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route("/api/relatorios/fluxo_caixa")
    @admin_required
    def api_rel_fluxo_caixa():
        db = get_db()
        inicio = request.args.get("inicio", date.today().isoformat())
        fim = request.args.get("fim", date.today().isoformat())
        vendas = db.execute("""
            SELECT SUM(valor_total) as total, COUNT(*) as qtd
            FROM vendas WHERE date(data) BETWEEN ? AND ? AND status != 'cancelada'
        """, (inicio, fim)).fetchone()
        suprimentos = db.execute("""
            SELECT COALESCE(SUM(valor),0) as total FROM suprimento_sangria
            WHERE tipo='suprimento' AND date(data_hora) BETWEEN ? AND ?
        """, (inicio, fim)).fetchone()
        sangrias = db.execute("""
            SELECT COALESCE(SUM(valor),0) as total FROM suprimento_sangria
            WHERE tipo='sangria' AND date(data_hora) BETWEEN ? AND ?
        """, (inicio, fim)).fetchone()
        return jsonify({
            "vendas": dict(vendas),
            "suprimentos": dict(suprimentos),
            "sangrias": dict(sangrias),
            "saldo": (vendas["total"] or 0) + (suprimentos["total"] or 0) - (sangrias["total"] or 0)
        })

    @app.route("/api/relatorios/sangrias")
    @admin_required
    def api_rel_sangrias():
        db = get_db()
        inicio = request.args.get("inicio", date.today().isoformat())
        fim = request.args.get("fim", date.today().isoformat())
        rows = db.execute("""
            SELECT ss.*, u.nome as usuario FROM suprimento_sangria ss
            LEFT JOIN usuarios u ON ss.usuario_id=u.id
            WHERE ss.tipo='sangria' AND date(ss.data_hora) BETWEEN ? AND ?
            ORDER BY ss.data_hora DESC
        """, (inicio, fim)).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route("/api/relatorios/suprimentos")
    @admin_required
    def api_rel_suprimentos():
        db = get_db()
        inicio = request.args.get("inicio", date.today().isoformat())
        fim = request.args.get("fim", date.today().isoformat())
        rows = db.execute("""
            SELECT ss.*, u.nome as usuario FROM suprimento_sangria ss
            LEFT JOIN usuarios u ON ss.usuario_id=u.id
            WHERE ss.tipo='suprimento' AND date(ss.data_hora) BETWEEN ? AND ?
            ORDER BY ss.data_hora DESC
        """, (inicio, fim)).fetchall()
        return jsonify([dict(r) for r in rows])
