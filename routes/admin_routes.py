import os
import sqlite3
import time
from datetime import datetime
from datetime import date
from flask import render_template, request, jsonify, session, send_file
from werkzeug.security import generate_password_hash
from database import get_db
from auth import (
    any_permission_required, log_auditoria, permission_required,
)
from permissions import (
    ALL_PERMISSION_KEYS, PERMISSION_DEFINITIONS, effective_permissions_for_user,
    get_user_with_profile, has_permission, is_admin,
)


def register_admin_routes(app):

    # =================== USUÁRIOS ===================

    @app.route("/usuarios")
    @any_permission_required("usuarios.criar", "permissoes.alterar")
    def usuarios():
        return render_template("usuarios.html")

    @app.route("/api/usuarios")
    @any_permission_required("usuarios.criar", "permissoes.alterar")
    def api_usuarios_list():
        db = get_db()
        rows = db.execute(
            """SELECT u.id, u.nome, u.login, u.nivel, u.ativo, u.bloqueado,
                      u.exigir_troca_senha, u.ultimo_acesso, u.criado_em,
                      u.perfil_id, p.nome AS perfil_nome
               FROM usuarios u
               LEFT JOIN perfis_acesso p ON p.id=u.perfil_id
               ORDER BY u.nome"""
        ).fetchall()
        can_edit_permissions = has_permission("permissoes.alterar")
        result = []
        for row in rows:
            user = dict(row)
            user["permissoes"] = (
                [p["chave"] for p in effective_permissions_for_user(row["id"], db) if p["permitido"]]
                if can_edit_permissions else []
            )
            result.append(user)
        return jsonify(result)

    @app.route("/api/perfis-permissoes")
    @any_permission_required("usuarios.criar", "permissoes.alterar")
    def api_perfis_permissoes():
        db = get_db()
        profiles = db.execute(
            "SELECT id, nome, descricao FROM perfis_acesso WHERE ativo=1 ORDER BY id"
        ).fetchall()
        profile_permissions = {}
        for profile in profiles:
            profile_permissions[str(profile["id"])] = [
                row["permissao_chave"]
                for row in db.execute(
                    "SELECT permissao_chave FROM perfil_permissoes WHERE perfil_id=? ORDER BY permissao_chave",
                    (profile["id"],),
                ).fetchall()
            ]
        return jsonify({
            "perfis": [dict(row) for row in profiles],
            "permissoes": [
                {"chave": key, "nome": name, "grupo": group, "descricao": description}
                for key, name, group, description in PERMISSION_DEFINITIONS
            ],
            "padroes": profile_permissions,
            "pode_personalizar": has_permission("permissoes.alterar"),
        })

    def _profile(db, profile_id):
        try:
            profile_id = int(profile_id)
        except (TypeError, ValueError):
            return None
        return db.execute(
            "SELECT id, nome FROM perfis_acesso WHERE id=? AND ativo=1", (profile_id,)
        ).fetchone()

    def _save_permission_overrides(db, user_id, profile_id, selected):
        selected = set(selected or ()) & ALL_PERMISSION_KEYS
        defaults = {
            row["permissao_chave"]
            for row in db.execute(
                "SELECT permissao_chave FROM perfil_permissoes WHERE perfil_id=?",
                (profile_id,),
            ).fetchall()
        }
        db.execute("DELETE FROM usuario_permissoes WHERE usuario_id=?", (user_id,))
        overrides = []
        for key in sorted(ALL_PERMISSION_KEYS):
            if (key in selected) != (key in defaults):
                overrides.append((user_id, key, int(key in selected)))
        if overrides:
            db.executemany(
                "INSERT INTO usuario_permissoes (usuario_id, permissao_chave, permitido) VALUES (?,?,?)",
                overrides,
            )

    def _active_admin_count(db):
        return db.execute(
            """SELECT COUNT(*) AS total
               FROM usuarios u LEFT JOIN perfis_acesso p ON p.id=u.perfil_id
               WHERE u.ativo=1 AND u.bloqueado=0
                 AND (u.nivel='admin' OR p.nome='Administrador')"""
        ).fetchone()["total"]

    @app.route("/api/usuarios", methods=["POST"])
    @permission_required("usuarios.criar")
    def api_usuario_create():
        db = get_db()
        d = request.json or {}
        nome = str(d.get("nome") or "").strip()
        login = str(d.get("login") or "").strip()
        senha = str(d.get("senha") or "")
        profile = _profile(db, d.get("perfil_id"))
        if not nome or not login:
            return jsonify({"ok": False, "erro": "Nome e usuário são obrigatórios."}), 400
        if len(senha) < 6:
            return jsonify({"ok": False, "erro": "A senha deve ter pelo menos 6 caracteres."}), 400
        if not profile:
            return jsonify({"ok": False, "erro": "Selecione um perfil válido."}), 400
        if profile["nome"] == "Administrador" and not is_admin():
            return jsonify({"ok": False, "erro": "Somente um administrador pode criar outro administrador."}), 403
        if "permissoes" in d and not has_permission("permissoes.alterar"):
            return jsonify({"ok": False, "erro": "Você não pode personalizar permissões."}), 403
        try:
            cursor = db.execute(
                """INSERT INTO usuarios
                   (nome, login, senha, nivel, perfil_id, ativo, bloqueado, exigir_troca_senha, senha_alterada_em)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    nome, login, generate_password_hash(senha),
                    "admin" if profile["nome"] == "Administrador" else "funcionario",
                    profile["id"], int(bool(d.get("ativo", True))), int(bool(d.get("bloqueado", False))),
                    int(bool(d.get("exigir_troca_senha", False))), datetime.now().isoformat(timespec="seconds"),
                ),
            )
            if "permissoes" in d:
                _save_permission_overrides(db, cursor.lastrowid, profile["id"], d["permissoes"])
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            return jsonify({"ok": False, "erro": "Este usuário de acesso já existe."}), 400
        log_auditoria("CRIAR_USUARIO", f"Usuário {login} criado com perfil {profile['nome']}")
        return jsonify({"ok": True, "id": cursor.lastrowid})

    @app.route("/api/usuarios/<int:uid>", methods=["PUT"])
    @permission_required("usuarios.criar")
    def api_usuario_update(uid):
        db = get_db()
        d = request.json or {}
        target = get_user_with_profile(uid, db)
        if not target:
            return jsonify({"ok": False, "erro": "Usuário não encontrado."}), 404
        profile = _profile(db, d.get("perfil_id"))
        if not profile:
            return jsonify({"ok": False, "erro": "Selecione um perfil válido."}), 400
        if (target["perfil_nome"] == "Administrador" or profile["nome"] == "Administrador") and not is_admin():
            return jsonify({"ok": False, "erro": "Somente um administrador pode alterar administradores."}), 403
        if "permissoes" in d and not has_permission("permissoes.alterar"):
            return jsonify({"ok": False, "erro": "Você não pode personalizar permissões."}), 403
        if uid == session.get("usuario_id") and not is_admin() and "permissoes" in d:
            return jsonify({"ok": False, "erro": "Você não pode alterar as próprias permissões."}), 403
        ativo = int(bool(d.get("ativo", True)))
        bloqueado = int(bool(d.get("bloqueado", False)))
        will_be_admin = profile["nome"] == "Administrador"
        is_target_admin = target["nivel"] == "admin" or target["perfil_nome"] == "Administrador"
        if is_target_admin and (not will_be_admin or not ativo or bloqueado) and _active_admin_count(db) <= 1:
            return jsonify({"ok": False, "erro": "O sistema precisa manter ao menos um administrador ativo."}), 400
        if uid == session.get("usuario_id") and (not ativo or bloqueado):
            return jsonify({"ok": False, "erro": "Não é possível desativar ou bloquear a própria conta."}), 400
        nome = str(d.get("nome") or "").strip()
        login = str(d.get("login") or "").strip()
        if not nome or not login:
            return jsonify({"ok": False, "erro": "Nome e usuário são obrigatórios."}), 400
        try:
            values = [
                nome, login, "admin" if will_be_admin else "funcionario", profile["id"],
                ativo, bloqueado, int(bool(d.get("exigir_troca_senha", False))),
            ]
            sql = """UPDATE usuarios SET nome=?, login=?, nivel=?, perfil_id=?, ativo=?,
                     bloqueado=?, exigir_troca_senha=?"""
            senha = str(d.get("senha") or "")
            if senha:
                if len(senha) < 6:
                    return jsonify({"ok": False, "erro": "A senha deve ter pelo menos 6 caracteres."}), 400
                sql += ", senha=?, senha_alterada_em=?"
                values.extend([generate_password_hash(senha), datetime.now().isoformat(timespec="seconds")])
            sql += " WHERE id=?"
            values.append(uid)
            db.execute(sql, values)
            if "permissoes" in d:
                _save_permission_overrides(db, uid, profile["id"], d["permissoes"])
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            return jsonify({"ok": False, "erro": "Este usuário de acesso já existe."}), 400
        log_auditoria("EDITAR_USUARIO", f"Usuário #{uid} atualizado; perfil {profile['nome']}")
        return jsonify({"ok": True})

    @app.route("/api/usuarios/<int:uid>", methods=["DELETE"])
    @permission_required("usuarios.criar")
    def api_usuario_delete(uid):
        if uid == session.get("usuario_id"):
            return jsonify({"ok": False, "erro": "Não é possível excluir o próprio usuário"}), 400
        db = get_db()
        target = get_user_with_profile(uid, db)
        if not target:
            return jsonify({"ok": False, "erro": "Usuário não encontrado."}), 404
        if (target["nivel"] == "admin" or target["perfil_nome"] == "Administrador") and _active_admin_count(db) <= 1:
            return jsonify({"ok": False, "erro": "O sistema precisa manter ao menos um administrador ativo."}), 400
        db.execute("UPDATE usuarios SET ativo=0, bloqueado=1 WHERE id=?", (uid,))
        db.commit()
        log_auditoria("EXCLUIR_USUARIO", f"Usuário #{uid} desativado")
        return jsonify({"ok": True})

    # =================== AUDITORIA ===================

    @app.route("/auditoria")
    @permission_required("auditoria.visualizar")
    def auditoria():
        return render_template("auditoria.html")

    @app.route("/api/auditoria")
    @permission_required("auditoria.visualizar")
    def api_auditoria():
        db = get_db()
        rows = db.execute("SELECT * FROM auditoria ORDER BY data_hora DESC LIMIT 500").fetchall()
        return jsonify([dict(r) for r in rows])

    # =================== GARÇONS ===================

    @app.route("/garcons")
    @permission_required("garcons.acessar")
    def garcons():
        return render_template("garcons.html")

    @app.route("/api/garcons")
    @permission_required("garcons.acessar")
    def api_garcons_list():
        db = get_db()
        rows = db.execute("SELECT * FROM garcons ORDER BY nome").fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route("/api/garcons", methods=["POST"])
    @permission_required("garcons.alterar")
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
    @permission_required("garcons.alterar")
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
    @permission_required("garcons.alterar")
    def api_garcon_delete(gid):
        db = get_db()
        db.execute("UPDATE garcons SET ativo=0 WHERE id=?", (gid,))
        db.commit()
        log_auditoria("EXCLUIR_GARCOM", f"Garçom #{gid} desativado")
        return jsonify({"ok": True})

    # =================== CONTAS A PAGAR ===================

    @app.route("/contas_pagar")
    @permission_required("contas.acessar")
    def contas_pagar():
        return render_template("contas_pagar.html")

    @app.route("/api/contas_pagar")
    @permission_required("contas.acessar")
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
    @permission_required("contas.alterar")
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
    @permission_required("contas.alterar")
    def api_contas_pagar_pagar(cid):
        db = get_db()
        db.execute("UPDATE contas_pagar SET status='pago', pagamento=date('now') WHERE id=?", (cid,))
        db.commit()
        log_auditoria("PAGAR_CONTA", f"Conta #{cid} marcada como paga")
        return jsonify({"ok": True})

    @app.route("/api/contas_pagar/<int:cid>", methods=["DELETE"])
    @permission_required("contas.alterar")
    def api_contas_pagar_delete(cid):
        db = get_db()
        db.execute("UPDATE contas_pagar SET status='cancelado' WHERE id=?", (cid,))
        db.commit()
        log_auditoria("CANCELAR_CONTA_PAGAR", f"Conta #{cid} cancelada")
        return jsonify({"ok": True})

    @app.route("/api/contas_pagar/verificar_atrasadas")
    @permission_required("contas.acessar")
    def api_verificar_atrasadas():
        db = get_db()
        db.execute("UPDATE contas_pagar SET status='atrasado' WHERE status='pendente' AND vencimento < date('now')")
        db.commit()
        return jsonify({"ok": True})

    # =================== ALERTAS ===================

    @app.route("/api/alertas")
    @any_permission_required("estoque.visualizar", "pdv.acessar", "mesas.acessar")
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
    @permission_required("configuracoes.acessar")
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
    @permission_required("configuracoes.acessar")
    def api_remover_logo():
        logo_path = os.path.join(app.static_folder, "uploads", "logo.png")
        if os.path.exists(logo_path):
            os.remove(logo_path)
            log_auditoria("REMOVER_LOGO", "Logo do sistema removida")
        return jsonify({"ok": True})

    # =================== BACKUP ===================

    @app.route("/api/backup")
    @permission_required("backup.gerar")
    def api_backup():
        db_path = app.config["DATABASE"]
        if not os.path.exists(db_path):
            return jsonify({"ok": False, "erro": "Banco de dados não encontrado"}), 404
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"backup_bar_adega_{timestamp}.db"
        log_auditoria("BACKUP", f"Backup gerado: {filename}")
        return send_file(db_path, as_attachment=True, download_name=filename, mimetype="application/octet-stream")

    # =================== EMPRESA ===================

    @app.route("/api/empresa")
    @permission_required("configuracoes.acessar")
    def api_empresa_get():
        db = get_db()
        empresa = db.execute("SELECT * FROM empresa LIMIT 1").fetchone()
        return jsonify(dict(empresa) if empresa else {})

    @app.route("/api/empresa", methods=["POST"])
    @permission_required("configuracoes.acessar")
    def api_empresa_save():
        db = get_db()
        d = request.json or {}
        empresa = db.execute("SELECT id FROM empresa LIMIT 1").fetchone()
        if empresa:
            db.execute("""UPDATE empresa SET razao_social=?, nome_fantasia=?, cnpj=?, 
                inscricao_estadual=?, endereco=?, telefone=?, email=?, horario_funcionamento=?, observacao=? 
                WHERE id=?""", 
                (d.get("razao_social"), d.get("nome_fantasia"), d.get("cnpj"), 
                 d.get("inscricao_estadual"), d.get("endereco"), d.get("telefone"), 
                 d.get("email"), d.get("horario_funcionamento"), d.get("observacao"), empresa["id"]))
        else:
            db.execute("""INSERT INTO empresa (id, razao_social, nome_fantasia, cnpj, 
                inscricao_estadual, endereco, telefone, email, horario_funcionamento, observacao) 
                VALUES (1,?,?,?,?,?,?,?,?,?)""", 
                (d.get("razao_social"), d.get("nome_fantasia"), d.get("cnpj"), 
                 d.get("inscricao_estadual"), d.get("endereco"), d.get("telefone"), 
                 d.get("email"), d.get("horario_funcionamento"), d.get("observacao")))
        db.execute("DELETE FROM empresa WHERE id != 1")
        db.commit()
        log_auditoria("SALVAR_EMPRESA", "Dados da empresa atualizados")
        return jsonify({"ok": True})
