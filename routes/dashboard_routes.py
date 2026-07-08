from flask import render_template, jsonify
from database import get_db
from auth import login_required
from datetime import date


def register_dashboard_routes(app):

    @app.route("/")
    @login_required
    def dashboard():
        return render_template("dashboard.html")

    @app.route("/api/dashboard")
    @login_required
    def api_dashboard():
        db = get_db()
        hoje = date.today().isoformat()
        inicio_mes = date.today().replace(day=1).isoformat()

        vendas_dia = db.execute(
            "SELECT COALESCE(SUM(valor_total),0) as t, COUNT(*) as c FROM vendas WHERE date(data)=?", (hoje,)
        ).fetchone()

        faturamento_mes = db.execute(
            "SELECT COALESCE(SUM(valor_total),0) as t FROM vendas WHERE date(data)>=?", (inicio_mes,)
        ).fetchone()["t"]

        status_mesas = {r["status"]: r["c"] for r in
            db.execute("SELECT status, COUNT(*) as c FROM mesas GROUP BY status").fetchall()}

        produtos_vendidos = db.execute(
            "SELECT COALESCE(SUM(quantidade),0) as q FROM itens_venda iv JOIN vendas v ON iv.venda_id=v.id WHERE date(v.data)=?",
            (hoje,)
        ).fetchone()["q"]

        estoque_critico = db.execute(
            "SELECT COUNT(*) as c FROM produtos WHERE ativo=1 AND estoque <= estoque_minimo"
        ).fetchone()["c"]

        produtos_top = db.execute("""
            SELECT p.nome, SUM(iv.quantidade) as qtd, SUM(iv.subtotal) as total
            FROM itens_venda iv JOIN vendas v ON iv.venda_id=v.id
            JOIN produtos p ON iv.produto_id=p.id
            WHERE date(v.data)=? GROUP BY p.id ORDER BY qtd DESC LIMIT 5
        """, (hoje,)).fetchall()

        vendas_hora = db.execute("""
            SELECT strftime('%H', data) as hora, COUNT(*) as qtd, SUM(valor_total) as total
            FROM vendas WHERE date(data)=? GROUP BY hora ORDER BY hora
        """, (hoje,)).fetchall()

        vendas_7dias = db.execute("""
            SELECT date(data) as dia, COUNT(*) as qtd, SUM(valor_total) as total
            FROM vendas WHERE date(data) >= date(?, '-6 days')
            GROUP BY dia ORDER BY dia
        """, (hoje,)).fetchall()

        contas = {r["status"]: dict(r) for r in
            db.execute("SELECT status, COUNT(*) as c, COALESCE(SUM(valor),0) as total FROM contas_pagar WHERE status IN ('pendente','atrasado') GROUP BY status").fetchall()}

        return jsonify({
            "faturamento_dia": vendas_dia["t"],
            "faturamento_mes": faturamento_mes,
            "total_pedidos": vendas_dia["c"],
            "mesas_ocupadas": status_mesas.get("ocupada", 0),
            "mesas_livres": status_mesas.get("disponivel", 0),
            "mesas_reservadas": status_mesas.get("reservada", 0),
            "total_mesas": sum(status_mesas.values()),
            "ticket_medio": (vendas_dia["t"] / vendas_dia["c"]) if vendas_dia["c"] else 0,
            "produtos_vendidos": produtos_vendidos,
            "estoque_critico": estoque_critico,
            "produtos_top": [dict(r) for r in produtos_top],
            "vendas_hora": [dict(r) for r in vendas_hora],
            "vendas_7dias": [dict(r) for r in vendas_7dias],
            "ocupacao": [{"status": k, "c": v} for k, v in status_mesas.items()],
            "contas_pagar_pendentes": contas.get("pendente", {"c": 0, "total": 0}),
            "contas_pagar_atrasadas": contas.get("atrasado", {"c": 0, "total": 0}),
        })
