import os
from flask import render_template, request, jsonify, session, send_file, abort
from auth import any_permission_required, permission_required
from maintenance.backup import (
    criar_backup, listar_backups, restaurar_backup, remover_backup,
    espaco_utilizado, obter_backup, importar_backup, contar_backups
)
from maintenance.legacy_firebird import importar_e_aplicar_datacaixa, status_runtime
from maintenance.diagnostics import diagnosticar_banco, verificar_fks_orfas, estatisticas_banco, recalcular_fiados
from maintenance.cleanup import (
    preview_limpeza, executar_limpeza, verificar_senha_admin,
    validar_confirmacao, obter_info_operacao
)
from maintenance.stats import obter_stats_dashboard
from maintenance.audit import log_maintenance, listar_auditoria


def register_maintenance_routes(app):

    @app.route("/manutencao")
    @permission_required("manutencao.acessar")
    def manutencao_dashboard():
        stats = obter_stats_dashboard()
        return render_template("manutencao.html", stats=stats)

    @app.route("/manutencao/backup")
    @any_permission_required("backup.gerar", "backup.restaurar")
    def manutencao_backup():
        backups = listar_backups(limite=100)
        return render_template(
            "manutencao_backup.html",
            backups=backups,
            total_backups=contar_backups(),
            firebird=status_runtime(),
        )

    @app.route("/manutencao/banco")
    @permission_required("manutencao.acessar")
    def manutencao_banco():
        return render_template("manutencao_banco.html")

    @app.route("/manutencao/limpeza")
    @permission_required("manutencao.acessar")
    def manutencao_limpeza():
        return render_template("manutencao_limpeza.html")

    @app.route("/manutencao/migracao")
    @permission_required("manutencao.acessar")
    def manutencao_migracao():
        backups = listar_backups()
        return render_template("manutencao_migracao.html", backups=backups)

    @app.route("/manutencao/auditoria")
    @permission_required("manutencao.acessar")
    def manutencao_auditoria():
        return render_template("manutencao_auditoria.html")

    @app.route("/api/manutencao/backup/criar", methods=["POST"])
    @permission_required("backup.gerar")
    def api_manutencao_backup_criar():
        data = request.get_json(silent=True) or {}
        desc = data.get("descricao", "")
        uid = session.get("usuario_id")
        uname = session.get("usuario_nome")
        resultado, erro = criar_backup(desc, usuario_id=uid, usuario_nome=uname)
        if erro:
            return jsonify({"ok": False, "erro": erro}), 500
        log_maintenance("Backup criado", "ok", f"Arquivo: {resultado['nome']}", uid, uname)
        return jsonify({"ok": True, "backup": resultado})

    @app.route("/api/manutencao/backup/listar")
    @any_permission_required("backup.gerar", "backup.restaurar")
    def api_manutencao_backup_listar():
        limite = min(max(request.args.get("limite", 100, type=int), 1), 500)
        offset = max(request.args.get("offset", 0, type=int), 0)
        backups = listar_backups(limite=limite, offset=offset)
        return jsonify({
            "ok": True,
            "backups": backups,
            "total": contar_backups(),
            "limite": limite,
            "offset": offset,
        })

    @app.route("/api/manutencao/backup/importar", methods=["POST"])
    @permission_required("backup.restaurar")
    def api_manutencao_backup_importar():
        arquivo = request.files.get("arquivo")
        if not arquivo or not arquivo.filename:
            return jsonify({"ok": False, "erro": "Selecione um arquivo .zip, .db, .fbk ou .FDB"}), 400
        if request.content_length and request.content_length > 1024 * 1024 * 1024:
            return jsonify({"ok": False, "erro": "O arquivo excede o limite de 1 GB"}), 413
        uid = session.get("usuario_id")
        uname = session.get("usuario_nome")
        extensao = os.path.splitext(arquivo.filename)[1].lower()
        if extensao in {".fbk", ".fdb"}:
            resultado, erro = importar_e_aplicar_datacaixa(
                arquivo, arquivo.filename, usuario_id=uid, usuario_nome=uname
            )
        else:
            resultado, erro = importar_backup(arquivo, arquivo.filename)
        if erro:
            log_maintenance("Importação de backup", "erro", erro, uid, uname)
            return jsonify({"ok": False, "erro": erro}), 400
        log_maintenance(
            "Backup importado", "ok",
            f"Arquivo: {resultado['nome']} | Registros: {resultado['registros']}"
            + (" | Datacaixa convertido e aplicado" if resultado.get("aplicado") else ""),
            uid, uname,
        )
        return jsonify({"ok": True, "backup": resultado})

    @app.route("/api/manutencao/backup/restaurar", methods=["POST"])
    @permission_required("backup.restaurar")
    def api_manutencao_backup_restaurar():
        data = request.get_json(silent=True) or {}
        nome = data.get("nome")
        if not nome:
            return jsonify({"ok": False, "erro": "Nome do backup não informado"}), 400
        uid = session.get("usuario_id")
        uname = session.get("usuario_nome")
        ok, erro, pre_backup = restaurar_backup(nome)
        if not ok:
            log_maintenance("Restauração de backup", "erro", f"Erro ao restaurar '{nome}': {erro}", uid, uname)
            return jsonify({"ok": False, "erro": erro}), 500
        detalhes = f"Restaurado: {nome}"
        if pre_backup:
            detalhes += f" | Backup de segurança: {pre_backup}"
        log_maintenance("Backup restaurado", "ok", detalhes, uid, uname)
        return jsonify({"ok": True, "mensagem": f"Backup '{nome}' restaurado com sucesso", "pre_backup": pre_backup})

    @app.route("/api/manutencao/backup/remover", methods=["POST"])
    @permission_required("backup.restaurar")
    def api_manutencao_backup_remover():
        data = request.get_json(silent=True) or {}
        nome = data.get("nome")
        if not nome:
            return jsonify({"ok": False, "erro": "Nome do backup não informado"}), 400
        uid = session.get("usuario_id")
        uname = session.get("usuario_nome")
        ok = remover_backup(nome)
        if not ok:
            return jsonify({"ok": False, "erro": "Backup não encontrado"}), 404
        log_maintenance("Backup removido", "ok", f"Arquivo: {nome}", uid, uname)
        return jsonify({"ok": True, "mensagem": f"Backup '{nome}' removido"})

    @app.route("/api/manutencao/backup/espaco")
    @any_permission_required("backup.gerar", "backup.restaurar")
    def api_manutencao_backup_espaco():
        espaco = espaco_utilizado()
        return jsonify({"ok": True, **espaco})

    @app.route("/api/manutencao/backup/download/<nome>")
    @permission_required("backup.gerar")
    def api_manutencao_backup_download(nome):
        caminho = obter_backup(nome)
        if not caminho:
            abort(404)
        uid = session.get("usuario_id")
        uname = session.get("usuario_nome")
        log_maintenance("Download de backup", "ok", f"Arquivo: {nome}", uid, uname)
        return send_file(caminho, as_attachment=True, download_name=nome)

    @app.route("/api/manutencao/banco/diagnostico")
    @permission_required("manutencao.acessar")
    def api_manutencao_diagnostico():
        uid = session.get("usuario_id")
        uname = session.get("usuario_nome")
        result = diagnosticar_banco()
        log_maintenance("Diagnóstico executado", "ok" if result.get("ok") else "erro",
                       f"Integridade: {'ok' if result.get('integridade') else 'falha'}", uid, uname)
        return jsonify(result)

    @app.route("/api/manutencao/banco/integridade")
    @permission_required("manutencao.acessar")
    def api_manutencao_integridade():
        uid = session.get("usuario_id")
        uname = session.get("usuario_nome")
        result = diagnosticar_banco()
        integ_ok = result.get("integridade")
        log_maintenance("Verificação de integridade", "ok" if integ_ok else "erro",
                       f"SQLite: {result.get('versao_sqlite', 'N/A')}", uid, uname)
        return jsonify({
            "ok": result.get("ok", False),
            "integridade": integ_ok,
            "versao_sqlite": result.get("versao_sqlite"),
            "tamanho_mb": result.get("tamanho_mb", 0),
        })

    @app.route("/api/manutencao/banco/estatisticas")
    @permission_required("manutencao.acessar")
    def api_manutencao_estatisticas():
        result = estatisticas_banco()
        return jsonify(result)

    @app.route("/api/manutencao/banco/fks")
    @permission_required("manutencao.acessar")
    def api_manutencao_fks():
        result = verificar_fks_orfas()
        return jsonify(result)

    @app.route("/api/manutencao/banco/recalcular_fiados", methods=["POST"])
    @permission_required("manutencao.acessar")
    def api_manutencao_recalcular_fiados():
        uid = session.get("usuario_id")
        uname = session.get("usuario_nome")
        result = recalcular_fiados()
        log_maintenance("Fiados recalculados", "ok" if result.get("ok") else "erro",
                       f"Clientes: {result.get('clientes_atualizados', 0)}", uid, uname)
        return jsonify(result)

    @app.route("/api/manutencao/limpeza/preview", methods=["POST"])
    @permission_required("manutencao.acessar")
    def api_manutencao_limpeza_preview():
        data = request.get_json(silent=True) or {}
        acao = data.get("acao", "")
        info = obter_info_operacao(acao)
        if not info:
            return jsonify({"ok": False, "erro": f"Operação desconhecida: {acao}"}), 400
        resultado = preview_limpeza(acao)
        return jsonify(resultado)

    @app.route("/api/manutencao/limpeza/confirmar", methods=["POST"])
    @permission_required("manutencao.acessar")
    def api_manutencao_limpeza_confirmar():
        data = request.get_json(silent=True) or {}
        acao = data.get("acao", "")
        senha = data.get("senha", "")
        confirmacao = data.get("confirmacao", "")

        if not acao:
            return jsonify({"ok": False, "erro": "Ação não informada"}), 400

        info = obter_info_operacao(acao)
        if not info:
            return jsonify({"ok": False, "erro": f"Operação desconhecida: {acao}"}), 400

        if not senha:
            return jsonify({"ok": False, "erro": "Senha do administrador não informada"}), 400

        if not verificar_senha_admin(senha):
            uid = session.get("usuario_id")
            uname = session.get("usuario_nome")
            log_maintenance(f"Tentativa de limpeza com senha inválida: {info['nome']}", "erro",
                           "Senha incorreta", uid, uname)
            return jsonify({"ok": False, "erro": "Senha do administrador incorreta"}), 403

        if not confirmacao:
            return jsonify({"ok": False, "erro": "Confirmação não informada"}), 400

        if not validar_confirmacao(confirmacao, acao):
            return jsonify({
                "ok": False,
                "erro": f"Confirmação incorreta. Digite exatamente: {info['confirmacao']}"
            }), 400

        uid = session.get("usuario_id")
        uname = session.get("usuario_nome")

        resultado = executar_limpeza(acao, usuario_id=uid, usuario_nome=uname)
        if not resultado["ok"]:
            return jsonify(resultado), 500

        return jsonify(resultado)

    @app.route("/api/manutencao/auditoria")
    @permission_required("manutencao.acessar")
    def api_manutencao_auditoria():
        limite = request.args.get("limite", 100, type=int)
        offset = request.args.get("offset", 0, type=int)
        dados = listar_auditoria(limite=limite, offset=offset)
        return jsonify({"ok": True, **dados})

    @app.route("/api/manutencao/stats")
    @permission_required("manutencao.acessar")
    def api_manutencao_stats():
        stats = obter_stats_dashboard()
        return jsonify({"ok": True, **stats})
