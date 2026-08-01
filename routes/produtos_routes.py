import os
import unicodedata

from flask import current_app, render_template, request, jsonify, session, url_for
from database import get_db
from auth import any_permission_required, log_auditoria, permission_required


def _normalizar_busca(valor):
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    return " ".join("".join(c for c in texto if not unicodedata.combining(c)).casefold().split())


def _produto_com_imagem(row):
    produto = dict(row)
    produto["imagem_url"] = None
    pasta = os.path.join(current_app.static_folder, "uploads", "produtos")
    for extensao in ("bmp", "png", "jpg", "jpeg", "webp"):
        nome = f"produto_{produto['id']}.{extensao}"
        if os.path.isfile(os.path.join(pasta, nome)):
            produto["imagem_url"] = url_for("static", filename=f"uploads/produtos/{nome}")
            break
    return produto


def register_produtos_routes(app):

    @app.route("/produtos")
    @permission_required("produtos.visualizar")
    def produtos():
        return render_template("produtos.html")

    @app.route("/api/produtos")
    @any_permission_required("produtos.visualizar", "pdv.acessar", "mesas.acessar", "estoque.visualizar")
    def api_produtos_list():
        db = get_db()
        rows = db.execute("""
            SELECT p.*, c.nome as categoria
            FROM produtos p LEFT JOIN categorias c ON p.categoria_id=c.id
            WHERE p.ativo=1 ORDER BY p.nome
        """).fetchall()
        return jsonify([_produto_com_imagem(r) for r in rows])

    @app.route("/api/produtos", methods=["POST"])
    @permission_required("produtos.cadastrar")
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
    @permission_required("produtos.alterar")
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
    @permission_required("produtos.alterar")
    def api_produto_delete(pid):
        db = get_db()
        db.execute("UPDATE produtos SET ativo=0 WHERE id=?", (pid,))
        db.commit()
        log_auditoria("EXCLUIR_PRODUTO", f"Produto #{pid} desativado")
        return jsonify({"ok": True})

    @app.route("/api/categorias")
    @any_permission_required("produtos.visualizar", "pdv.acessar", "mesas.acessar", "estoque.visualizar")
    def api_categorias():
        db = get_db()
        rows = db.execute("SELECT * FROM categorias ORDER BY nome").fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route("/api/categorias", methods=["POST"])
    @permission_required("produtos.cadastrar")
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
    @any_permission_required("produtos.visualizar", "pdv.acessar", "mesas.acessar")
    def api_buscar_produto():
        termo = request.args.get("q", "").strip()
        codigo = request.args.get("codigo", "").strip()
        db = get_db()
        if codigo:
            p = db.execute("""
                SELECT p.*, c.nome AS categoria
                FROM produtos p
                LEFT JOIN categorias c ON c.id=p.categoria_id
                WHERE trim(p.codigo_barras)=? AND p.ativo=1
            """, (codigo,)).fetchone()
            return jsonify(_produto_com_imagem(p) if p else {})
        if termo:
            rows = db.execute("""
                SELECT p.*, c.nome AS categoria FROM produtos p
                LEFT JOIN categorias c ON p.categoria_id = c.id
                WHERE p.ativo=1
                ORDER BY p.nome COLLATE NOCASE
            """).fetchall()
            consulta = _normalizar_busca(termo)
            encontrados = []
            for row in rows:
                produto = dict(row)
                campos = (
                    produto.get("nome"),
                    produto.get("codigo_barras"),
                    produto.get("categoria"),
                    produto.get("id"),
                )
                if any(consulta in _normalizar_busca(campo) for campo in campos):
                    encontrados.append(row)
            encontrados.sort(key=lambda row: (
                not _normalizar_busca(row["nome"]).startswith(consulta),
                _normalizar_busca(row["nome"]),
            ))
            return jsonify([_produto_com_imagem(r) for r in encontrados[:30]])
        return jsonify([])

    @app.route("/api/produtos/mais_vendidos")
    @permission_required("pdv.acessar")
    def api_produtos_mais_vendidos():
        db = get_db()
        rows = db.execute("""
            SELECT p.id, p.nome, p.preco, p.estoque, p.unidade,
                   COALESCE(SUM(CASE WHEN v.id IS NOT NULL THEN iv.quantidade ELSE 0 END), 0) as total_vendido
            FROM produtos p
            LEFT JOIN itens_venda iv ON iv.produto_id = p.id
            LEFT JOIN vendas v ON iv.venda_id = v.id AND v.status != 'cancelada'
            WHERE p.ativo=1
            GROUP BY p.id
            ORDER BY total_vendido DESC, p.nome COLLATE NOCASE
        """).fetchall()
        produtos = [dict(r) for r in rows]

        def grupo_rapido(produto):
            nome = produto["nome"].casefold()
            if any(termo in nome for termo in ("cigar", "gudan", "eigth", "eight")) or nome.startswith("lm "):
                return "cigarro"
            if "dose" in nome:
                return "dose"
            return None

        cigarros = [p for p in produtos if grupo_rapido(p) == "cigarro"][:3]
        doses = [p for p in produtos if grupo_rapido(p) == "dose"][:4]
        destaques = cigarros + doses
        ids_destaques = {p["id"] for p in destaques}

        lista = destaques + [p for p in produtos if p["id"] not in ids_destaques]
        lista = lista[:12]
        for produto in lista:
            produto["destaque"] = grupo_rapido(produto)
        return jsonify(lista)

    @app.route("/api/produtos/grupos-acesso-rapido")
    @permission_required("pdv.acessar")
    def api_grupos_acesso_rapido():
        """Agrupa somente SKUs reais já cadastrados para a operação rápida."""
        db = get_db()
        rows = db.execute(
            """SELECT p.*, c.nome AS categoria
               FROM produtos p
               LEFT JOIN categorias c ON c.id=p.categoria_id
               WHERE p.ativo=1
               ORDER BY CASE WHEN p.estoque>0 THEN 0 ELSE 1 END, p.nome COLLATE NOCASE"""
        ).fetchall()
        groups = {
            "cigarros-soltos": {
                "slug": "cigarros-soltos", "nome": "Cigarros soltos", "icone": "cigarette",
                "descricao": "Unidades e tipos soltos cadastrados", "produtos": [],
            },
            "doses": {
                "slug": "doses", "nome": "Doses", "icone": "wine",
                "descricao": "Bebidas vendidas por dose", "produtos": [],
            },
            "fichas-jogos": {
                "slug": "fichas-jogos", "nome": "Fichas de sinuca e jogos", "icone": "circle-dot",
                "descricao": "Fichas reais de bilhar, sinuca e fliperama", "produtos": [],
            },
            "fracionados": {
                "slug": "fracionados", "nome": "Por peso e medida", "icone": "scale",
                "descricao": "Itens fracionados por kg ou litro", "produtos": [],
            },
        }
        for row in rows:
            product = _produto_com_imagem(row)
            name = _normalizar_busca(product["nome"])
            unit = str(product.get("unidade") or "UN").upper()
            if "dose" in name:
                groups["doses"]["produtos"].append(product)
            elif (
                "cigar" in name and "solt" in name
            ) or any(term in name for term in ("gudan solto", "eigth solto", "eight solto")):
                groups["cigarros-soltos"]["produtos"].append(product)
            elif "ficha" in name and any(term in name for term in ("sinuca", "bilhar", "fliperama")):
                groups["fichas-jogos"]["produtos"].append(product)
            elif unit in {"KG", "L", "LT"} and len(name.replace(".", "").strip()) > 1:
                groups["fracionados"]["produtos"].append(product)

        result = []
        for group in groups.values():
            if not group["produtos"]:
                continue
            group["quantidade"] = len(group["produtos"])
            group["disponiveis"] = sum(1 for product in group["produtos"] if float(product["estoque"] or 0) > 0)
            result.append(group)
        return jsonify(result)
