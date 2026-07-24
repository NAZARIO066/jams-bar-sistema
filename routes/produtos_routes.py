from flask import render_template, request, jsonify, session
from database import get_db
from auth import login_required, admin_required, log_auditoria


def register_produtos_routes(app):

    @app.route("/produtos")
    @login_required
    def produtos():
        return render_template("produtos.html")

    @app.route("/api/produtos")
    @login_required
    def api_produtos_list():
        db = get_db()
        rows = db.execute("""
            SELECT p.*, c.nome as categoria
            FROM produtos p LEFT JOIN categorias c ON p.categoria_id=c.id
            WHERE p.ativo=1 ORDER BY p.nome
        """).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route("/api/produtos", methods=["POST"])
    @admin_required
    def api_produto_create():
        db = get_db()
        d = request.json or {}
        cur = db.execute(
            "INSERT INTO produtos (nome, categoria_id, codigo_barras, preco, estoque, estoque_minimo, unidade) VALUES (?,?,?,?,?,?,?)",
            (d.get("nome"), d.get("categoria_id") or None, d.get("codigo_barras") or None,
             float(d.get("preco", 0)), float(d.get("estoque", 0)), float(d.get("estoque_minimo", 0)), d.get("unidade", "UN"))
        )
        db.commit()
        log_auditoria("CRIAR_PRODUTO", f"Produto {d.get('nome')} criado")
        return jsonify({"ok": True, "id": cur.lastrowid})

    @app.route("/api/produtos/<int:pid>", methods=["PUT"])
    @admin_required
    def api_produto_update(pid):
        db = get_db()
        d = request.json or {}
        db.execute(
            "UPDATE produtos SET nome=?, categoria_id=?, codigo_barras=?, preco=?, estoque_minimo=?, unidade=? WHERE id=?",
            (d.get("nome"), d.get("categoria_id") or None, d.get("codigo_barras") or None,
             float(d.get("preco", 0)), float(d.get("estoque_minimo", 0)), d.get("unidade", "UN"), pid)
        )
        db.commit()
        log_auditoria("EDITAR_PRODUTO", f"Produto #{pid} atualizado")
        return jsonify({"ok": True})

    @app.route("/api/produtos/<int:pid>", methods=["DELETE"])
    @admin_required
    def api_produto_delete(pid):
        db = get_db()
        db.execute("UPDATE produtos SET ativo=0 WHERE id=?", (pid,))
        db.commit()
        log_auditoria("EXCLUIR_PRODUTO", f"Produto #{pid} desativado")
        return jsonify({"ok": True})

    @app.route("/api/categorias")
    @login_required
    def api_categorias():
        db = get_db()
        rows = db.execute("SELECT * FROM categorias ORDER BY nome").fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route("/api/categorias", methods=["POST"])
    @admin_required
    def api_categoria_create():
        db = get_db()
        nome = (request.json or {}).get("nome", "").strip()
        if not nome:
            return jsonify({"ok": False}), 400
        try:
            db.execute("INSERT INTO categorias (nome) VALUES (?)", (nome,))
            db.commit()
        except Exception:
            return jsonify({"ok": False, "erro": "Categoria já existe"}), 400
        return jsonify({"ok": True})

    @app.route("/api/buscar_produto")
    @login_required
    def api_buscar_produto():
        termo = request.args.get("q", "").strip()
        codigo = request.args.get("codigo", "").strip()
        db = get_db()
        if codigo:
            p = db.execute("SELECT * FROM produtos WHERE codigo_barras=? AND ativo=1", (codigo,)).fetchone()
            return jsonify(dict(p) if p else {})
        if termo:
            like = f"%{termo}%"
            rows = db.execute("""
                SELECT DISTINCT p.* FROM produtos p
                LEFT JOIN categorias c ON p.categoria_id = c.id
                WHERE p.ativo=1 AND (
                    p.nome LIKE ? OR p.codigo_barras LIKE ? OR c.nome LIKE ?
                ) LIMIT 20
            """, (like, like, like)).fetchall()
            return jsonify([dict(r) for r in rows])
        return jsonify([])

    @app.route("/api/produtos/mais_vendidos")
    @login_required
    def api_produtos_mais_vendidos():
        db = get_db()
        rows = db.execute("""
            SELECT p.id, p.nome, p.preco, p.estoque, p.unidade,
                   COALESCE(SUM(iv.quantidade), 0) as total_vendido
            FROM produtos p
            LEFT JOIN itens_venda iv ON iv.produto_id = p.id
            LEFT JOIN vendas v ON iv.venda_id = v.id AND v.status != 'cancelada'
            WHERE p.ativo=1
            GROUP BY p.id
            ORDER BY total_vendido DESC
            LIMIT 10
        """).fetchall()
        return jsonify([dict(r) for r in rows])
