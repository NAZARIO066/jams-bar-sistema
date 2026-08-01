import os
from datetime import datetime
from flask import render_template, request, jsonify, redirect, url_for, session
from auth import permission_required
from database import get_db
from migration.validators import validar_upload_completo
from migration.services import (
    salvar_arquivo,
    obter_info_arquivo,
    limpar_uploads_antigos,
    salvar_sessao_migracao,
    obter_sessao_migracao,
    limpar_sessao_migracao,
    criar_backup_pre_importacao,
)
from migration.backup import criar_backup


def register_wizard_routes(app):

    @app.route("/migracao")
    @permission_required("migracao.acessar")
    def migracao_index():
        limpar_uploads_antigos()
        return redirect(url_for("migracao_etapa1"))

    @app.route("/migracao/etapa1")
    @permission_required("migracao.acessar")
    def migracao_etapa1():
        limpar_sessao_migracao()
        return render_template("migracao_etapa1.html")

    @app.route("/migracao/etapa2", methods=["GET", "POST"])
    @permission_required("migracao.acessar")
    def migracao_etapa2():
        if request.method == "GET":
            tipo = request.args.get("tipo")
            if tipo and tipo in ("sqlite", "sql", "excel", "csv"):
                dados = obter_sessao_migracao()
                dados["tipo_fonte"] = tipo
                salvar_sessao_migracao(dados)
            else:
                dados = obter_sessao_migracao()
                if not dados.get("tipo_fonte"):
                    return redirect(url_for("migracao_etapa1"))
            return render_template("migracao_etapa2.html", tipo=dados["tipo_fonte"])

        file = request.files.get("arquivo")
        if not file or not file.filename:
            return jsonify({"ok": False, "erro": "Nenhum arquivo enviado"}), 400

        filename = file.filename
        file.seek(0, 2)
        size = file.tell()
        file.seek(0)

        validacao = validar_upload_completo(filename, size)
        if not validacao["valido"]:
            return jsonify({"ok": False, "erro": validacao["erros"][0]}), 400

        info = salvar_arquivo(file)
        dados = obter_sessao_migracao()
        dados["arquivo"] = info
        dados["validacao"] = validacao
        dados["data_upload"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        salvar_sessao_migracao(dados)

        return jsonify({
            "ok": True,
            "nome": info["nome_original"],
            "tamanho_mb": info["tamanho_mb"],
            "tipo": validacao["tipo_detectado"],
            "extensao": validacao["extensao"],
            "data": dados["data_upload"],
        })

    @app.route("/api/migracao/analisar", methods=["POST"])
    @permission_required("migracao.acessar")
    def api_migracao_analisar():
        dados = obter_sessao_migracao()
        if not dados.get("arquivo"):
            return jsonify({"ok": False, "erro": "Nenhum arquivo para analisar"}), 400

        filepath = dados["arquivo"]["caminho"]
        if not os.path.exists(filepath):
            return jsonify({"ok": False, "erro": "Arquivo não encontrado no servidor"}), 400

        from migration.importer import analisar_arquivo
        resultado = analisar_arquivo(filepath, dados["tipo_fonte"])
        resultado_dict = resultado.to_dict()

        resultado_dict["_filepath"] = filepath

        dados["analise"] = resultado_dict

        from migration.compatibility import CompatibilityAnalyzer
        compat_analyzer = CompatibilityAnalyzer(resultado_dict)
        compat_report = compat_analyzer.analyze()
        dados["compatibilidade"] = compat_report

        salvar_sessao_migracao(dados)

        resp = jsonify(resultado_dict)
        return resp

    @app.route("/migracao/etapa3")
    @permission_required("migracao.acessar")
    def migracao_etapa3():
        dados = obter_sessao_migracao()
        if not dados.get("arquivo"):
            return redirect(url_for("migracao_etapa1"))
        analise = dados.get("analise")
        if not analise:
            return redirect(url_for("migracao_etapa2"))
        compat = dados.get("compatibilidade")
        return render_template("migracao_etapa3.html", dados=dados, analise=analise, compat=compat)

    @app.route("/migracao/etapa4")
    @permission_required("migracao.acessar")
    def migracao_etapa4():
        dados = obter_sessao_migracao()
        if not dados.get("arquivo"):
            return redirect(url_for("migracao_etapa1"))
        compat = dados.get("compatibilidade")
        pode_importar = compat.get("pode_importar", True) if compat else True
        return render_template("migracao_etapa4.html", dados=dados, compat=compat, pode_importar=pode_importar)

    @app.route("/api/migracao/upload", methods=["POST"])
    @permission_required("migracao.acessar")
    def api_migracao_upload():
        file = request.files.get("arquivo")
        if not file or not file.filename:
            return jsonify({"ok": False, "erro": "Nenhum arquivo enviado"}), 400

        filename = file.filename
        file.seek(0, 2)
        size = file.tell()
        file.seek(0)

        validacao = validar_upload_completo(filename, size)
        if not validacao["valido"]:
            return jsonify({"ok": False, "erro": validacao["erros"][0]}), 400

        info = salvar_arquivo(file)
        dados = obter_sessao_migracao()
        dados["arquivo"] = info
        dados["validacao"] = validacao
        dados["data_upload"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        salvar_sessao_migracao(dados)

        return jsonify({
            "ok": True,
            "nome": info["nome_original"],
            "tamanho_mb": info["tamanho_mb"],
            "tipo": validacao["tipo_detectado"],
            "extensao": validacao["extensao"],
            "data": dados["data_upload"],
        })

    @app.route("/api/migracao/confirmar", methods=["POST"])
    @permission_required("migracao.acessar")
    def api_migracao_confirmar():
        dados = obter_sessao_migracao()
        if not dados.get("arquivo"):
            return jsonify({"ok": False, "erro": "Nenhum arquivo selecionado"}), 400

        compat = dados.get("compatibilidade")
        if compat and not compat.get("pode_importar", True):
            return jsonify({"ok": False, "erro": "Importação bloqueada: existem erros críticos de compatibilidade"}), 400

        backup_path, erro = criar_backup_pre_importacao()
        if erro:
            return jsonify({"ok": False, "erro": erro}), 500

        from migration.importer import importar_dados
        resultado = importar_dados(
            dados["arquivo"]["caminho"],
            dados["tipo_fonte"],
            dados.get("opcoes")
        )
        limpar_sessao_migracao()
        return jsonify(resultado)

    @app.route("/api/migracao/cancelar", methods=["POST"])
    @permission_required("migracao.acessar")
    def api_migracao_cancelar():
        limpar_sessao_migracao()
        return jsonify({"ok": True})

    @app.route("/api/migracao/compatibilidade")
    @permission_required("migracao.acessar")
    def api_migracao_compatibilidade():
        dados = obter_sessao_migracao()
        if not dados.get("compatibilidade"):
            return jsonify({"ok": False, "erro": "Nenhuma análise de compatibilidade disponível"}), 400
        return jsonify(dados["compatibilidade"])

    @app.route("/migracao/relatorio/json")
    @permission_required("migracao.acessar")
    def migracao_relatorio_json():
        dados = obter_sessao_migracao()
        compat = dados.get("compatibilidade")
        if not compat:
            return jsonify({"erro": "Relatório não disponível"}), 400
        from flask import Response
        import json
        return Response(
            json.dumps(compat, ensure_ascii=False, indent=2),
            mimetype="application/json",
            headers={"Content-Disposition": "attachment;filename=relatorio_compatibilidade.json"},
        )

    @app.route("/migracao/relatorio/html")
    @permission_required("migracao.acessar")
    def migracao_relatorio_html():
        dados = obter_sessao_migracao()
        compat = dados.get("compatibilidade")
        if not compat:
            return "Relatório não disponível", 400
        from migration.compatibility import gerar_relatorio_html
        html = gerar_relatorio_html(compat)
        from flask import Response
        return Response(
            html,
            mimetype="text/html",
            headers={"Content-Disposition": "attachment;filename=relatorio_compatibilidade.html"},
        )
