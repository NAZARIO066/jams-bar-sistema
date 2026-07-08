import os
import time
from datetime import date
from flask import render_template, request, jsonify, session
from werkzeug.security import generate_password_hash
from database import get_db
from auth import login_required, admin_required, log_auditoria


def register_admin_routes(app):

    # =================== USUÁRIOS ===================

    @app.route("/usuarios")
    @admin_required
    def usuarios():
        return render_template("usuarios.html")

    @app.route("/api/usuarios")
    @admin_required
    def api_usuarios_list():
        db = get_db()
        rows = db.execute("SELECT id, nome, login, nivel, ativo, criado_em FROM usuarios ORDER BY nome").fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route("/api/usuarios", methods=["POST"])
    @admin_required
    def api_usuario_create():
        db = get_db()
        d = request.json or {}
        try:
            db.execute(
                "INSERT INTO usuarios (nome, login, senha, nivel) VALUES (?,?,?,?)",
                (d.get("nome"), d.get("login"), generate_password_hash(d.get("senha", "123456")), d.get("nivel", "funcionario"))
            )
            db.commit()
        except Exception:
            return jsonify({"ok": False, "erro": "Login já existe"}), 400
        log_auditoria("CRIAR_USUARIO", f"Usuário {d.get('login')} criado")
        return jsonify({"ok": True})

    @app.route("/api/usuarios/<int:uid>", methods=["PUT"])
    @admin_required
    def api_usuario_update(uid):
        db = get_db()
        d = request.json or {}
        if d.get("senha"):
            db.execute("UPDATE usuarios SET nome=?, login=?, nivel=?, ativo=?, senha=? WHERE id=?",
                       (d.get("nome"), d.get("login"), d.get("nivel"), int(bool(d.get("ativo", True))),
                        generate_password_hash(d["senha"]), uid))
        else:
            db.execute("UPDATE usuarios SET nome=?, login=?, nivel=?, ativo=? WHERE id=?",
                       (d.get("nome"), d.get("login"), d.get("nivel"), int(bool(d.get("ativo", True))), uid))
        db.commit()
        log_auditoria("EDITAR_USUARIO", f"Usuário #{uid} atualizado")
        return jsonify({"ok": True})

    @app.route("/api/usuarios/<int:uid>", methods=["DELETE"])
    @admin_required
    def api_usuario_delete(uid):
        if uid == session.get("usuario_id"):
            return jsonify({"ok": False, "erro": "Não é possível excluir o próprio usuário"}), 400
        db = get_db()
        db.execute("UPDATE usuarios SET ativo=0 WHERE id=?", (uid,))
        db.commit()
        log_auditoria("EXCLUIR_USUARIO", f"Usuário #{uid} desativado")
        return jsonify({"ok": True})

    # =================== AUDITORIA ===================

    @app.route("/auditoria")
    @admin_required
    def auditoria():
        return render_template("auditoria.html")

    @app.route("/api/auditoria")
    @admin_required
    def api_auditoria():
        db = get_db()
        rows = db.execute("SELECT * FROM auditoria ORDER BY data_hora DESC LIMIT 500").fetchall()
        return jsonify([dict(r) for r in rows])

    # =================== GARÇONS ===================

    @app.route("/garcons")
    @login_required
    def garcons():
        return render_template("garcons.html")

    @app.route("/api/garcons")
    @login_required
    def api_garcons_list():
        db = get_db()
        rows = db.execute("SELECT * FROM garcons ORDER BY nome").fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route("/api/garcons", methods=["POST"])
    @admin_required
    def api_garcon_create():
        db = get_db()
        d = request.json or {}
        nome = (d.get("nome") or "").strip()
        if not nome:
            return jsonify({"ok": False, "erro": "Nome obrigatório"}), 400
        cur = db.execute("INSERT INTO garcons (nome, telefone, comissao) VALUES (?,?,?)",
                         (nome, d.get("telefone"), float(d.get("comissao", 0))))
        db.commit()
        log_auditoria("CRIAR_GARCOM", f"Garçom {nome} criado")
        return jsonify({"ok": True, "id": cur.lastrowid})

    @app.route("/api/garcons/<int:gid>", methods=["PUT"])
    @admin_required
    def api_garcon_update(gid):
        db = get_db()
        d = request.json or {}
        db.execute("UPDATE garcons SET nome=?, telefone=?, comissao=?, ativo=? WHERE id=?",
                   (d.get("nome"), d.get("telefone"), float(d.get("comissao", 0)),
                    int(bool(d.get("ativo", True))), gid))
        db.commit()
        log_auditoria("EDITAR_GARCOM", f"Garçom #{gid} atualizado")
        return jsonify({"ok": True})

    @app.route("/api/garcons/<int:gid>", methods=["DELETE"])
    @admin_required
    def api_garcon_delete(gid):
        db = get_db()
        db.execute("UPDATE garcons SET ativo=0 WHERE id=?", (gid,))
        db.commit()
        log_auditoria("EXCLUIR_GARCOM", f"Garçom #{gid} desativado")
        return jsonify({"ok": True})

    # =================== CONTAS A PAGAR ===================

    @app.route("/contas_pagar")
    @login_required
    def contas_pagar():
        return render_template("contas_pagar.html")

    @app.route("/api/contas_pagar")
    @login_required
    def api_contas_pagar_list():
        db = get_db()
        filtro = request.args.get("status", "todos")
        query = "SELECT * FROM contas_pagar"
        params = []
        if filtro == "pendente":
            query += " WHERE status='pendente'"
        elif filtro == "pago":
            query += " WHERE status='pago'"
        elif filtro == "atrasado":
            query += " WHERE status='atrasado'"
        query += " ORDER BY vencimento ASC"
        rows = db.execute(query, params).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route("/api/contas_pagar", methods=["POST"])
    @login_required
    def api_contas_pagar_create():
        db = get_db()
        d = request.json or {}
        fornecedor = (d.get("fornecedor") or "").strip()
        descricao = (d.get("descricao") or "").strip()
        valor = float(d.get("valor", 0))
        vencimento = d.get("vencimento")
        if not fornecedor or not descricao or valor <= 0 or not vencimento:
            return jsonify({"ok": False, "erro": "Preencha todos os campos obrigatórios"}), 400
        cur = db.execute(
            "INSERT INTO contas_pagar (fornecedor, descricao, valor, vencimento, usuario_id, observacao) VALUES (?,?,?,?,?,?)",
            (fornecedor, descricao, valor, vencimento, session["usuario_id"], d.get("observacao"))
        )
        db.commit()
        log_auditoria("CRIAR_CONTA_PAGAR", f"Conta a pagar #{cur.lastrowid} - {fornecedor} R$ {valor:.2f}")
        return jsonify({"ok": True, "id": cur.lastrowid})

    @app.route("/api/contas_pagar/<int:cid>/pagar", methods=["POST"])
    @login_required
    def api_contas_pagar_pagar(cid):
        db = get_db()
        db.execute("UPDATE contas_pagar SET status='pago', pagamento=date('now') WHERE id=?", (cid,))
        db.commit()
        log_auditoria("PAGAR_CONTA", f"Conta #{cid} marcada como paga")
        return jsonify({"ok": True})

    @app.route("/api/contas_pagar/<int:cid>", methods=["DELETE"])
    @login_required
    def api_contas_pagar_delete(cid):
        db = get_db()
        db.execute("UPDATE contas_pagar SET status='cancelado' WHERE id=?", (cid,))
        db.commit()
        log_auditoria("CANCELAR_CONTA_PAGAR", f"Conta #{cid} cancelada")
        return jsonify({"ok": True})

    @app.route("/api/contas_pagar/verificar_atrasadas")
    @login_required
    def api_verificar_atrasadas():
        db = get_db()
        db.execute("UPDATE contas_pagar SET status='atrasado' WHERE status='pendente' AND vencimento < date('now')")
        db.commit()
        return jsonify({"ok": True})

    # =================== ALERTAS ===================

    @app.route("/api/alertas")
    @login_required
    def api_alertas():
        db = get_db()
        criticos = db.execute("SELECT nome, estoque, estoque_minimo FROM produtos WHERE ativo=1 AND estoque <= estoque_minimo").fetchall()
        zerados = [c for c in criticos if c["estoque"] <= 0]
        return jsonify({
            "criticos": [dict(c) for c in criticos],
            "zerados": [dict(z) for z in zerados],
        })

    # =================== CONFIG / LOGO ===================

    @app.route("/api/config/logo", methods=["POST"])
    @admin_required
    def api_upload_logo():
        if "logo" not in request.files:
            return jsonify({"ok": False, "erro": "Nenhum arquivo enviado"}), 400
        f = request.files["logo"]
        if not f.filename:
            return jsonify({"ok": False, "erro": "Arquivo vazio"}), 400
        ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
        if ext not in ("png", "jpg", "jpeg", "gif", "svg", "webp"):
            return jsonify({"ok": False, "erro": "Formato não permitido. Use PNG, JPG, GIF, SVG ou WebP"}), 400
        header = f.read(8)
        f.seek(0)
        magic_valid = any(header.startswith(m) for m in [b"\x89PNG\r\n", b"\xff\xd8", b"GIF87a", b"GIF89a", b"RIFF"])
        if not magic_valid and ext not in ("svg",):
            return jsonify({"ok": False, "erro": "Arquivo inválido ou corrompido"}), 400
        upload_dir = os.path.join(app.static_folder, "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        f.save(os.path.join(upload_dir, "logo.png"))
        log_auditoria("ALTERAR_LOGO", "Logo do sistema alterada")
        return jsonify({"ok": True, "timestamp": int(time.time())})

    @app.route("/api/config/logo", methods=["DELETE"])
    @admin_required
    def api_remover_logo():
        logo_path = os.path.join(app.static_folder, "uploads", "logo.png")
        if os.path.exists(logo_path):
            os.remove(logo_path)
            log_auditoria("REMOVER_LOGO", "Logo do sistema removida")
        return jsonify({"ok": True})
