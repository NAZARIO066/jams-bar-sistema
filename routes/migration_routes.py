from flask import jsonify
from database import get_db
from auth import admin_required
from services.migration_service import (
    validar_foreign_keys_orfas,
    validar_formato_timestamps,
    validar_saldo_devedor,
    corrigir_saldo_devedor,
    validar_empresa_singleton,
    limpar_empresa_duplicatas,
    executar_antes_importacao,
)


def register_migration_routes(app):

    @app.route("/api/migracao/validar", methods=["POST"])
    @admin_required
    def api_migracao_validar():
        db = get_db()
        resultados = executar_antes_importacao(db)
        total_problemas = (
            len(resultados["orfas_fk"])
            + len(resultados["timestamps_invalidos"])
            + len(resultados["saldo_devedor_desatualizado"])
            + (1 if resultados["empresa_duplicada"] else 0)
        )
        return jsonify({
            "ok": True,
            "total_problemas": total_problemas,
            "orfas_fk": resultados["orfas_fk"],
            "timestamps_invalidos": resultados["timestamps_invalidos"],
            "saldo_devedor_desatualizado": resultados["saldo_devedor_desatualizado"],
            "empresa_duplicada": resultados["empresa_duplicada"],
        })

    @app.route("/api/migracao/corrigir_saldo", methods=["POST"])
    @admin_required
    def api_migracao_corrigir_saldo():
        db = get_db()
        count = corrigir_saldo_devedor(db)
        db.commit()
        return jsonify({"ok": True, "clientes_corrigidos": count})

    @app.route("/api/migracao/corrigir_empresa", methods=["POST"])
    @admin_required
    def api_migracao_corrigir_empresa():
        db = get_db()
        info = validar_empresa_singleton(db)
        if info["duplicatas"]:
            limpar_empresa_duplicatas(db)
            db.commit()
        return jsonify({"ok": True, "empresa_duplicada_antes": info["duplicatas"]})

    @app.route("/api/migracao/status", methods=["GET"])
    @admin_required
    def api_migracao_status():
        db = get_db()
        tabelas = {}
        for nome in [
            "usuarios", "mesas", "categorias", "produtos", "comandas",
            "itens_comanda", "vendas", "itens_venda", "movimentacoes",
            "clientes", "fiado", "auditoria", "caixas", "garcons",
            "contas_pagar", "suprimento_sangria", "historico_transferencias",
            "login_attempts", "empresa",
        ]:
            try:
                row = db.execute(f"SELECT COUNT(*) as c FROM {nome}").fetchone()
                tabelas[nome] = row["c"]
            except Exception:
                tabelas[nome] = -1
        return jsonify({"ok": True, "tabelas": tabelas})
