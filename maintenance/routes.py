import os
from flask import render_template, request, jsonify, session, send_file, abort
from auth import admin_required
from maintenance.backup import (
    criar_backup, listar_backups, restaurar_backup, remover_backup,
    espaco_utilizado, obter_backup
)
from maintenance.diagnostics import diagnosticar_banco, verificar_fks_orfas, estatisticas_banco, recalcular_fiados
from maintenance.cleanup import (
    preview_limpeza, executar_limpeza, verificar_senha_admin,
    validar_confirmacao, obter_info_operacao
)
from maintenance.stats import obter_stats_dashboard
from maintenance.audit import log_maintenance, listar_auditoria


def register_maintenance_routes(app):

    @app.route("/manutencao")
    @admin_required
    def manutencao_dashboard():
        stats = obter_stats_dashboard()
        return render_template("manutencao.html", stats=stats)

    @app.route("/manutencao/backup")
    @admin_required
    def manutencao_backup():
        backups = listar_backups()
        return render_template("manutencao_backup.html", backups=backups)

    @app.route("/manutencao/banco")
    @admin_required
    def manutencao_banco():
        return render_template("manutencao_banco.html")

    @app.route("/manutencao/limpeza")
    @admin_required
    def manutencao_limpeza():
        return render_template("manutencao_limpeza.html")

    @app.route("/manutencao/migracao")
    @admin_required
    def manutencao_migracao():
        backups = listar_backups()
        return render_template("manutencao_migracao.html", backups=backups)

    @app.route("/manutencao/auditoria")
    @admin_required
    def manutencao_auditoria():
        return render_template("manutencao_auditoria.html")

    @app.route("/api/manutencao/backup/criar", methods=["POST"])
    @admin_required
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
    @admin_required
    def api_manutencao_backup_listar():
        backups = listar_backups()
        return jsonify({"ok": True, "backups": backups, "total": len(backups)})

    @app.route("/api/manutencao/backup/restaurar", methods=["POST"])
    @admin_required
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
    @admin_required
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
    @admin_required
    def api_manutencao_backup_espaco():
        espaco = espaco_utilizado()
        return jsonify({"ok": True, **espaco})

    @app.route("/api/manutencao/backup/download/<nome>")
    @admin_required
    def api_manutencao_backup_download(nome):
        caminho = obter_backup(nome)
        if not caminho:
            abort(404)
        uid = session.get("usuario_id")
        uname = session.get("usuario_nome")
        log_maintenance("Download de backup", "ok", f"Arquivo: {nome}", uid, uname)
        return send_file(caminho, as_attachment=True, download_name=nome)

    @app.route("/api/manutencao/banco/diagnostico")
    @admin_required
    def api_manutencao_diagnostico():
        uid = session.get("usuario_id")
        uname = session.get("usuario_nome")
        result = diagnosticar_banco()
        log_maintenance("Diagnóstico executado", "ok" if result.get("ok") else "erro",
                       f"Integridade: {'ok' if result.get('integridade') else 'falha'}", uid, uname)
        return jsonify(result)

    @app.route("/api/manutencao/banco/integridade")
    @admin_required
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
    @admin_required
    def api_manutencao_estatisticas():
        result = estatisticas_banco()
        return jsonify(result)

    @app.route("/api/manutencao/banco/fks")
    @admin_required
    def api_manutencao_fks():
        result = verificar_fks_orfas()
        return jsonify(result)

    @app.route("/api/manutencao/banco/recalcular_fiados", methods=["POST"])
    @admin_required
    def api_manutencao_recalcular_fiados():
        uid = session.get("usuario_id")
        uname = session.get("usuario_nome")
        result = recalcular_fiados()
        log_maintenance("Fiados recalculados", "ok" if result.get("ok") else "erro",
                       f"Clientes: {result.get('clientes_atualizados', 0)}", uid, uname)
        return jsonify(result)

    @app.route("/api/manutencao/limpeza/preview", methods=["POST"])
    @admin_required
    def api_manutencao_limpeza_preview():
        data = request.get_json(silent=True) or {}
        acao = data.get("acao", "")
        info = obter_info_operacao(acao)
        if not info:
            return jsonify({"ok": False, "erro": f"Operação desconhecida: {acao}"}), 400
        resultado = preview_limpeza(acao)
        return jsonify(resultado)

    @app.route("/api/manutencao/limpeza/confirmar", methods=["POST"])
    @admin_required
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
    @admin_required
    def api_manutencao_auditoria():
        limite = request.args.get("limite", 100, type=int)
        offset = request.args.get("offset", 0, type=int)
        dados = listar_auditoria(limite=limite, offset=offset)
        return jsonify({"ok": True, **dados})

    @app.route("/api/manutencao/stats")
    @admin_required
    def api_manutencao_stats():
        stats = obter_stats_dashboard()
        return jsonify({"ok": True, **stats})
