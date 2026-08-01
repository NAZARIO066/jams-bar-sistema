import os
from datetime import date, timedelta
from flask import render_template, request, jsonify, session
from database import get_db
from auth import permission_required


def register_relatorios_routes(app):

    @app.route("/relatorios")
    @permission_required("relatorios.visualizar", "financeiro.visualizar")
    def relatorios():
        return render_template("relatorios.html")

    @app.route("/api/relatorios/vendas")
    @permission_required("relatorios.visualizar", "financeiro.visualizar")
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
    @permission_required("relatorios.visualizar", "financeiro.visualizar")
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
    @permission_required("relatorios.visualizar", "financeiro.visualizar")
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
    @permission_required("relatorios.visualizar", "financeiro.visualizar")
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
    @permission_required("relatorios.visualizar", "financeiro.visualizar")
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
    @permission_required("relatorios.visualizar", "financeiro.visualizar")
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
    @permission_required("relatorios.visualizar", "financeiro.visualizar")
    def api_rel_fluxo_caixa():
        db = get_db()
        inicio = request.args.get("inicio", date.today().isoformat())
        fim = request.args.get("fim", date.today().isoformat())
        vendas = db.execute("""
            SELECT COALESCE(SUM(valor_total),0) as total, COUNT(*) as qtd
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
    @permission_required("relatorios.visualizar", "financeiro.visualizar")
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
    @permission_required("relatorios.visualizar", "financeiro.visualizar")
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

    # ── Impressão A4 de Relatórios ─────────────────────────────────────────

    def _empresa_ctx():
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
        from datetime import datetime
        return datetime.now().strftime("%d/%m/%Y %H:%M")

    def _periodo_label(inicio, fim):
        return f"{inicio} a {fim}"

    def _fmt(val, tipo="moeda"):
        if val is None:
            return "—"
        if tipo == "moeda":
            return f"R$ {float(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        if tipo == "data":
            try:
                from datetime import datetime as dt
                return dt.fromisoformat(str(val)).strftime("%d/%m/%Y %H:%M")
            except Exception:
                return str(val)[:16]
        if tipo == "data_curta":
            try:
                from datetime import datetime as dt
                return dt.fromisoformat(str(val)).strftime("%d/%m/%Y")
            except Exception:
                return str(val)[:10]
        return str(val)

    @app.route("/imprimir/relatorio/<tipo>")
    @permission_required("relatorios.visualizar", "financeiro.visualizar", "impressao.imprimir")
    def imprimir_relatorio(tipo):
        db = get_db()
        inicio = request.args.get("inicio", date.today().isoformat())
        fim = request.args.get("fim", date.today().isoformat())
        empresa = _empresa_ctx()
        now = _now_str()
        periodo = _periodo_label(inicio, fim)

        if tipo == "vendas":
            vendas = db.execute("""
                SELECT v.*, u.nome as funcionario, m.numero as mesa
                FROM vendas v JOIN usuarios u ON v.usuario_id=u.id
                LEFT JOIN mesas m ON v.mesa_id=m.id
                WHERE date(v.data) BETWEEN ? AND ? ORDER BY v.data DESC
            """, (inicio, fim)).fetchall()
            totais = db.execute("""
                SELECT COALESCE(SUM(valor_total),0) as total, COUNT(*) as qtd,
                       COALESCE(AVG(valor_total),0) as ticket
                FROM vendas WHERE date(data) BETWEEN ? AND ? AND status != 'cancelada'
            """, (inicio, fim)).fetchone()
            headers = [
                {"label": "#", "key": "id", "css": "text-center"},
                {"label": "Data", "key": "data_fmt"},
                {"label": "Tipo", "key": "tipo_badge", "css": "text-center"},
                {"label": "Mesa", "key": "mesa", "css": "text-center"},
                {"label": "Funcionário", "key": "funcionario"},
                {"label": "Pagamento", "key": "forma_pagamento"},
                {"label": "Total", "key": "total_fmt", "css": "text-right font-bold"},
            ]
            rows = []
            for v in vendas:
                tipo_b = f'<span class="badge-print {"blue" if v["tipo"]=="mesa" else "gray"}">{v["tipo"]}</span>'
                rows.append({
                    "id": v["id"],
                    "data_fmt": _fmt(v["data"], "data"),
                    "tipo_badge": tipo_b,
                    "mesa": v["mesa"] or "—",
                    "funcionario": v["funcionario"],
                    "forma_pagamento": v["forma_pagamento"] or "—",
                    "total_fmt": _fmt(v["valor_total"]),
                })
            summary = [
                {"label": "Total Vendido", "value": _fmt(totais["total"]), "color": "blue"},
                {"label": "Qtd Vendas", "value": str(totais["qtd"])},
                {"label": "Ticket Médio", "value": _fmt(totais["ticket"])},
                {"label": "Período", "value": periodo},
            ]
            return render_template("prints/relatorio.html",
                titulo="Relatório de Vendas", periodo=periodo, empresa=empresa, now=now,
                summary=summary, sections=[{"headers": headers, "rows": rows, "footer": None}])

        elif tipo == "mesas":
            rows_db = db.execute("""
                SELECT m.numero, COUNT(v.id) as pedidos, COALESCE(SUM(v.valor_total),0) as total
                FROM mesas m LEFT JOIN vendas v ON v.mesa_id=m.id AND v.status != 'cancelada'
                GROUP BY m.id ORDER BY total DESC
            """).fetchall()
            headers = [
                {"label": "Mesa", "key": "numero", "css": "text-center"},
                {"label": "Pedidos", "key": "pedidos", "css": "text-center"},
                {"label": "Total", "key": "total_fmt", "css": "text-right font-bold"},
            ]
            rows = [{"numero": f"Mesa {r['numero']:02d}", "pedidos": r["pedidos"], "total_fmt": _fmt(r["total"])} for r in rows_db]
            total_geral = sum(r["total"] for r in rows_db)
            summary = [
                {"label": "Total Geral", "value": _fmt(total_geral), "color": "blue"},
                {"label": "Mesas", "value": str(len(rows_db))},
            ]
            return render_template("prints/relatorio.html",
                titulo="Relatório por Mesa", periodo=periodo, empresa=empresa, now=now,
                summary=summary, sections=[{"headers": headers, "rows": rows}])

        elif tipo == "produtos":
            mais = db.execute("""
                SELECT p.nome, SUM(iv.quantidade) as qtd, SUM(iv.subtotal) as total
                FROM itens_venda iv JOIN vendas v ON iv.venda_id=v.id
                JOIN produtos p ON iv.produto_id=p.id
                WHERE date(v.data) >= date('now','-30 days') AND v.status != 'cancelada'
                GROUP BY p.id ORDER BY qtd DESC LIMIT 20
            """).fetchall()
            headers = [
                {"label": "Produto", "key": "nome"},
                {"label": "Qtd", "key": "qtd", "css": "text-right"},
                {"label": "Total", "key": "total_fmt", "css": "text-right font-bold"},
            ]
            rows = [{"nome": r["nome"], "qtd": r["qtd"], "total_fmt": _fmt(r["total"])} for r in mais]
            return render_template("prints/relatorio.html",
                titulo="Produtos Mais Vendidos (30 dias)", periodo=periodo, empresa=empresa, now=now,
                summary=[], sections=[{"headers": headers, "rows": rows}])

        elif tipo == "vendas_produto":
            rows_db = db.execute("""
                SELECT p.nome, COALESCE(c.nome, 'Sem categoria') as categoria,
                       SUM(iv.quantidade) as qtd, SUM(iv.subtotal) as total
                FROM itens_venda iv JOIN vendas v ON iv.venda_id=v.id
                JOIN produtos p ON iv.produto_id=p.id
                LEFT JOIN categorias c ON p.categoria_id=c.id
                WHERE date(v.data) BETWEEN ? AND ? AND v.status != 'cancelada'
                GROUP BY p.id ORDER BY total DESC
            """, (inicio, fim)).fetchall()
            headers = [
                {"label": "Produto", "key": "nome"},
                {"label": "Categoria", "key": "categoria"},
                {"label": "Qtd", "key": "qtd", "css": "text-right"},
                {"label": "Total", "key": "total_fmt", "css": "text-right font-bold"},
            ]
            rows = [{"nome": r["nome"], "categoria": r["categoria"], "qtd": r["qtd"], "total_fmt": _fmt(r["total"])} for r in rows_db]
            total_itens = sum(r["qtd"] for r in rows_db)
            summary = [{"label": "Total Produtos", "value": f"{total_itens} itens vendidos", "color": "blue"}]
            return render_template("prints/relatorio.html",
                titulo="Vendas por Produto", periodo=periodo, empresa=empresa, now=now,
                summary=summary, sections=[{"headers": headers, "rows": rows}])

        elif tipo == "vendas_categoria":
            rows_db = db.execute("""
                SELECT COALESCE(c.nome, 'Sem categoria') as categoria,
                       SUM(iv.quantidade) as qtd, SUM(iv.subtotal) as total
                FROM itens_venda iv JOIN vendas v ON iv.venda_id=v.id
                JOIN produtos p ON iv.produto_id=p.id
                LEFT JOIN categorias c ON p.categoria_id=c.id
                WHERE date(v.data) BETWEEN ? AND ? AND v.status != 'cancelada'
                GROUP BY c.id ORDER BY total DESC
            """, (inicio, fim)).fetchall()
            total_geral = sum(r["total"] for r in rows_db)
            headers = [
                {"label": "Categoria", "key": "categoria"},
                {"label": "Qtd Itens", "key": "qtd", "css": "text-right"},
                {"label": "Total", "key": "total_fmt", "css": "text-right font-bold"},
                {"label": "%", "key": "perc", "css": "text-right"},
            ]
            rows = []
            for r in rows_db:
                perc = f"{(r['total']/total_geral*100):.1f}%" if total_geral > 0 else "0%"
                rows.append({"categoria": r["categoria"], "qtd": r["qtd"], "total_fmt": _fmt(r["total"]), "perc": perc})
            summary = [{"label": "Total Categorias", "value": f"{len(rows_db)} categorias", "color": "blue"}]
            return render_template("prints/relatorio.html",
                titulo="Vendas por Categoria", periodo=periodo, empresa=empresa, now=now,
                summary=summary, sections=[{"headers": headers, "rows": rows}])

        elif tipo == "fluxo_caixa":
            vendas_row = db.execute("""
                SELECT SUM(valor_total) as total, COUNT(*) as qtd
                FROM vendas WHERE date(data) BETWEEN ? AND ? AND status != 'cancelada'
            """, (inicio, fim)).fetchone()
            sup = db.execute("""
                SELECT COALESCE(SUM(valor),0) as total FROM suprimento_sangria
                WHERE tipo='suprimento' AND date(data_hora) BETWEEN ? AND ?
            """, (inicio, fim)).fetchone()
            sang = db.execute("""
                SELECT COALESCE(SUM(valor),0) as total FROM suprimento_sangria
                WHERE tipo='sangria' AND date(data_hora) BETWEEN ? AND ?
            """, (inicio, fim)).fetchone()
            saldo = (vendas_row["total"] or 0) + (sup["total"] or 0) - (sang["total"] or 0)
            headers = [
                {"label": "Descrição", "key": "desc"},
                {"label": "Valor", "key": "valor_fmt", "css": "text-right font-bold"},
            ]
            rows = [
                {"desc": "Vendas", "valor_fmt": f'<span class="text-green">{_fmt(vendas_row["total"])}</span>'},
                {"desc": "Suprimentos", "valor_fmt": f'<span class="text-green">{_fmt(sup["total"])}</span>'},
                {"desc": "Sangrias", "valor_fmt": f'<span class="text-red">{_fmt(sang["total"])}</span>'},
                {"desc": "SALDO", "valor_fmt": f'<strong>{_fmt(saldo)}</strong>'},
            ]
            summary = [
                {"label": "Entradas", "value": _fmt(vendas_row["total"]), "color": "green"},
                {"label": "Saídas", "value": _fmt(sang["total"]), "color": "red"},
                {"label": "Saldo", "value": _fmt(saldo), "color": "blue"},
            ]
            return render_template("prints/relatorio.html",
                titulo="Fluxo de Caixa", periodo=periodo, empresa=empresa, now=now,
                summary=summary, sections=[{"headers": headers, "rows": rows}])

        elif tipo == "sangrias":
            rows_db = db.execute("""
                SELECT ss.*, u.nome as usuario FROM suprimento_sangria ss
                LEFT JOIN usuarios u ON ss.usuario_id=u.id
                WHERE ss.tipo='sangria' AND date(ss.data_hora) BETWEEN ? AND ?
                ORDER BY ss.data_hora DESC
            """, (inicio, fim)).fetchall()
            total = sum(r["valor"] for r in rows_db)
            headers = [
                {"label": "Data", "key": "data_fmt"},
                {"label": "Valor", "key": "valor_fmt", "css": "text-right font-bold"},
                {"label": "Motivo", "key": "motivo"},
                {"label": "Usuário", "key": "usuario"},
            ]
            rows = [{"data_fmt": _fmt(r["data_hora"], "data"), "valor_fmt": _fmt(r["valor"]), "motivo": r["motivo"] or "—", "usuario": r["usuario"] or "—"} for r in rows_db]
            summary = [
                {"label": "Total Sangrias", "value": _fmt(total), "color": "red"},
                {"label": "Qtd Sangrias", "value": str(len(rows_db))},
            ]
            return render_template("prints/relatorio.html",
                titulo="Sangrias no Período", periodo=periodo, empresa=empresa, now=now,
                summary=summary, sections=[{"headers": headers, "rows": rows}])

        elif tipo == "suprimentos":
            rows_db = db.execute("""
                SELECT ss.*, u.nome as usuario FROM suprimento_sangria ss
                LEFT JOIN usuarios u ON ss.usuario_id=u.id
                WHERE ss.tipo='suprimento' AND date(ss.data_hora) BETWEEN ? AND ?
                ORDER BY ss.data_hora DESC
            """, (inicio, fim)).fetchall()
            total = sum(r["valor"] for r in rows_db)
            headers = [
                {"label": "Data", "key": "data_fmt"},
                {"label": "Valor", "key": "valor_fmt", "css": "text-right font-bold"},
                {"label": "Motivo", "key": "motivo"},
                {"label": "Usuário", "key": "usuario"},
            ]
            rows = [{"data_fmt": _fmt(r["data_hora"], "data"), "valor_fmt": _fmt(r["valor"]), "motivo": r["motivo"] or "—", "usuario": r["usuario"] or "—"} for r in rows_db]
            summary = [
                {"label": "Total Suprimentos", "value": _fmt(total), "color": "green"},
                {"label": "Qtd Suprimentos", "value": str(len(rows_db))},
            ]
            return render_template("prints/relatorio.html",
                titulo="Suprimentos no Período", periodo=periodo, empresa=empresa, now=now,
                summary=summary, sections=[{"headers": headers, "rows": rows}])

        elif tipo == "estoque":
            produtos = db.execute("""
                SELECT p.nome, COALESCE(c.nome,'—') as categoria, p.estoque, p.estoque_minimo,
                       p.preco, p.unidade
                FROM produtos p LEFT JOIN categorias c ON p.categoria_id=c.id
                WHERE p.ativo=1 ORDER BY p.nome
            """).fetchall()
            headers = [
                {"label": "Produto", "key": "nome"},
                {"label": "Categoria", "key": "categoria"},
                {"label": "Estoque", "key": "estoque", "css": "text-center"},
                {"label": "Mínimo", "key": "estoque_minimo", "css": "text-center"},
                {"label": "Preço", "key": "preco_fmt", "css": "text-right"},
            ]
            rows = []
            for p in produtos:
                estoque_cls = "text-red" if p["estoque"] <= 0 else ("text-red" if p["estoque"] <= p["estoque_minimo"] else "")
                estoque_str = f'<span class="{estoque_cls}">{p["estoque"]} {p["unidade"]}</span>' if estoque_cls else f'{p["estoque"]} {p["unidade"]}'
                rows.append({"nome": p["nome"], "categoria": p["categoria"], "estoque": estoque_str, "estoque_minimo": p["estoque_minimo"], "preco_fmt": _fmt(p["preco"])})
            summary = [{"label": "Produtos Ativos", "value": str(len(produtos)), "color": "blue"}]
            return render_template("prints/relatorio.html",
                titulo="Relatório de Estoque", periodo=periodo, empresa=empresa, now=now,
                summary=summary, sections=[{"headers": headers, "rows": rows}])

        elif tipo == "produtos_cadastro":
            produtos = db.execute("""
                SELECT p.nome, COALESCE(c.nome,'—') as categoria, p.codigo_barras,
                       p.preco, p.estoque, p.estoque_minimo, p.unidade
                FROM produtos p LEFT JOIN categorias c ON p.categoria_id=c.id
                WHERE p.ativo=1 ORDER BY p.nome
            """).fetchall()
            headers = [
                {"label": "Produto", "key": "nome"},
                {"label": "Categoria", "key": "categoria"},
                {"label": "Cód. Barras", "key": "codigo_barras"},
                {"label": "Preço", "key": "preco_fmt", "css": "text-right font-bold"},
                {"label": "Estoque", "key": "estoque_str", "css": "text-center"},
            ]
            rows = [{"nome": r["nome"], "categoria": r["categoria"], "codigo_barras": r["codigo_barras"] or "—", "preco_fmt": _fmt(r["preco"]), "estoque_str": f'{r["estoque"]} {r["unidade"]}'} for r in produtos]
            return render_template("prints/relatorio.html",
                titulo="Relatório de Produtos", periodo=periodo, empresa=empresa, now=now,
                summary=[], sections=[{"headers": headers, "rows": rows}])

        elif tipo == "clientes":
            clientes = db.execute("""
                SELECT nome, telefone, cpf, limite_fiado, saldo_devedor FROM clientes
                WHERE ativo=1 ORDER BY nome
            """).fetchall()
            headers = [
                {"label": "Nome", "key": "nome"},
                {"label": "Telefone", "key": "telefone"},
                {"label": "CPF", "key": "cpf"},
                {"label": "Limite", "key": "limite_fmt", "css": "text-right"},
                {"label": "Saldo Devedor", "key": "saldo_fmt", "css": "text-right font-bold"},
            ]
            rows = [{"nome": c["nome"], "telefone": c["telefone"] or "—", "cpf": c["cpf"] or "—", "limite_fmt": _fmt(c["limite_fiado"]), "saldo_fmt": _fmt(c["saldo_devedor"])} for c in clientes]
            com_fiado = [c for c in clientes if c["saldo_devedor"] > 0]
            total_devedor = sum(c["saldo_devedor"] for c in com_fiado)
            summary = [
                {"label": "Total Clientes", "value": str(len(clientes))},
                {"label": "Com Fiado", "value": str(len(com_fiado)), "color": "red"},
                {"label": "Total a Receber", "value": _fmt(total_devedor), "color": "red"},
            ]
            return render_template("prints/relatorio.html",
                titulo="Relatório de Clientes", periodo=periodo, empresa=empresa, now=now,
                summary=summary, sections=[{"headers": headers, "rows": rows}])

        elif tipo == "contas_pagar":
            contas = db.execute("""
                SELECT c.*, u.nome as usuario FROM contas_pagar c
                LEFT JOIN usuarios u ON c.usuario_id=u.id
                ORDER BY c.vencimento DESC
            """).fetchall()
            headers = [
                {"label": "Vencimento", "key": "vencimento_fmt"},
                {"label": "Fornecedor", "key": "fornecedor"},
                {"label": "Descrição", "key": "descricao"},
                {"label": "Valor", "key": "valor_fmt", "css": "text-right font-bold"},
                {"label": "Status", "key": "status_badge", "css": "text-center"},
            ]
            rows = []
            for c in contas:
                st = c["status"]
                badge_cls = "green" if st == "pago" else ("red" if st == "atrasado" else ("gray" if st == "cancelado" else "yellow"))
                rows.append({
                    "vencimento_fmt": _fmt(c["vencimento"], "data_curta"),
                    "fornecedor": c["fornecedor"],
                    "descricao": c["descricao"],
                    "valor_fmt": _fmt(c["valor"]),
                    "status_badge": f'<span class="badge-print {badge_cls}">{st.upper()}</span>',
                })
            pendentes = [c for c in contas if c["status"] == "pendente"]
            atrasadas = [c for c in contas if c["status"] == "atrasado"]
            summary = [
                {"label": "Pendentes", "value": str(len(pendentes)), "color": "blue"},
                {"label": "Atrasadas", "value": str(len(atrasadas)), "color": "red"},
                {"label": "Total Pendente", "value": _fmt(sum(c["valor"] for c in pendentes))},
                {"label": "Total Atrasado", "value": _fmt(sum(c["valor"] for c in atrasadas)), "color": "red"},
            ]
            return render_template("prints/relatorio.html",
                titulo="Relatório de Contas a Pagar", periodo=periodo, empresa=empresa, now=now,
                summary=summary, sections=[{"headers": headers, "rows": rows}])

        elif tipo == "caixa":
            caixa = db.execute("""
                SELECT c.*, u.nome as usuario FROM caixas c
                LEFT JOIN usuarios u ON c.usuario_id=u.id
                ORDER BY c.abertura DESC LIMIT 1
            """).fetchone()
            if not caixa:
                return "Nenhum caixa registrado", 404
            movs = db.execute("""
                SELECT ss.*, u.nome as usuario FROM suprimento_sangria ss
                LEFT JOIN usuarios u ON ss.usuario_id=u.id
                WHERE ss.caixa_id=?
                ORDER BY ss.data_hora
            """, (caixa["id"],)).fetchall()
            headers = [
                {"label": "Data/Hora", "key": "data_fmt"},
                {"label": "Tipo", "key": "tipo_badge", "css": "text-center"},
                {"label": "Valor", "key": "valor_fmt", "css": "text-right font-bold"},
                {"label": "Motivo", "key": "motivo"},
                {"label": "Usuário", "key": "usuario"},
            ]
            rows = []
            for m in movs:
                badge_cls = "green" if m["tipo"] == "suprimento" else "red"
                rows.append({
                    "data_fmt": _fmt(m["data_hora"], "data"),
                    "tipo_badge": f'<span class="badge-print {badge_cls}">{m["tipo"].upper()}</span>',
                    "valor_fmt": f'<span class="{"text-green" if m["tipo"]=="suprimento" else "text-red"}">{"+" if m["tipo"]=="suprimento" else "- "} {_fmt(m["valor"])}</span>',
                    "motivo": m["motivo"] or "—",
                    "usuario": m["usuario"] or "—",
                })
            abertura = _fmt(caixa["valor_inicial"])
            fechamento = _fmt(caixa["valor_final"]) if caixa["valor_final"] else "—"
            diff = _fmt(caixa["diferenca"]) if caixa["diferenca"] else "—"
            summary = [
                {"label": "Abertura", "value": abertura},
                {"label": "Fechamento", "value": fechamento},
                {"label": "Diferença", "value": diff, "color": "red" if caixa["diferenca"] and caixa["diferenca"] != 0 else ""},
            ]
            return render_template("prints/relatorio.html",
                titulo="Relatório de Caixa", periodo=periodo, empresa=empresa, now=now,
                summary=summary, sections=[{"headers": headers, "rows": rows}])

        return "Tipo de relatório inválido", 400
