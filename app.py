import os
import logging
from flask import Flask, render_template, session
from datetime import datetime, date
from config import Config
from database import get_db, init_db, close_db
from auth import log_auditoria

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from routes.auth_routes import register_auth_routes
from routes.dashboard_routes import register_dashboard_routes
from routes.mesas_routes import register_mesas_routes
from routes.vendas_routes import register_vendas_routes
from routes.produtos_routes import register_produtos_routes
from routes.estoque_routes import register_estoque_routes
from routes.clientes_routes import register_clientes_routes
from routes.caixa_routes import register_caixa_routes
from routes.admin_routes import register_admin_routes
from routes.relatorios_routes import register_relatorios_routes

app = Flask(__name__)
app.config.from_object(Config)
app.teardown_appcontext(close_db)

register_auth_routes(app)
register_dashboard_routes(app)
register_mesas_routes(app)
register_vendas_routes(app)
register_produtos_routes(app)
register_estoque_routes(app)
register_clientes_routes(app)
register_caixa_routes(app)
register_admin_routes(app)
register_relatorios_routes(app)


# =================== INICIALIZAÇÃO ===================

_db_ready = False

@app.before_request
def ensure_db():
    global _db_ready
    if _db_ready:
        return
    if not os.path.exists(app.config["DATABASE"]):
        with app.app_context():
            from seed import seed_initial
            init_db()
            seed_initial()
    else:
        db = get_db()
        try:
            cols = [r["name"] for r in db.execute("PRAGMA table_info(comandas)").fetchall()]
            if "cliente_nome" not in cols:
                db.execute("ALTER TABLE comandas ADD COLUMN cliente_nome TEXT")
                db.commit()
        except Exception as e:
            logging.warning("Migração comandas.cliente_nome: %s", e)
        try:
            cols_f = [r["name"] for r in db.execute("PRAGMA table_info(fiado)").fetchall()]
            if "data_vencimento" not in cols_f:
                db.execute("ALTER TABLE fiado ADD COLUMN data_vencimento DATE")
                db.commit()
            if "valor_pago" not in cols_f:
                db.execute("ALTER TABLE fiado ADD COLUMN valor_pago REAL NOT NULL DEFAULT 0")
                db.commit()
        except Exception as e:
            logging.warning("Migração fiado: %s", e)
        try:
            from database import SCHEMA
            db.executescript(SCHEMA)
            db.commit()
        except Exception as e:
            logging.warning("Migração SCHEMA: %s", e)
        try:
            cols_cx = [r["name"] for r in db.execute("PRAGMA table_info(caixas)").fetchall()]
            if "diferenca" not in cols_cx:
                db.execute("ALTER TABLE caixas ADD COLUMN diferenca REAL NOT NULL DEFAULT 0")
                db.commit()
        except Exception as e:
            logging.warning("Migração caixas.diferenca: %s", e)
        try:
            cols_com = [r["name"] for r in db.execute("PRAGMA table_info(comandas)").fetchall()]
            if "garcom_id" not in cols_com:
                db.execute("ALTER TABLE comandas ADD COLUMN garcom_id INTEGER REFERENCES garcons(id)")
                db.commit()
        except Exception as e:
            logging.warning("Migração comandas.garcom_id: %s", e)
        try:
            cols_ic = [r["name"] for r in db.execute("PRAGMA table_info(itens_comanda)").fetchall()]
            if "observacao" not in cols_ic:
                db.execute("ALTER TABLE itens_comanda ADD COLUMN observacao TEXT")
                db.commit()
        except Exception as e:
            logging.warning("Migração itens_comanda.observacao: %s", e)
        try:
            cols_iv = [r["name"] for r in db.execute("PRAGMA table_info(itens_venda)").fetchall()]
            if "observacao" not in cols_iv:
                db.execute("ALTER TABLE itens_venda ADD COLUMN observacao TEXT")
                db.commit()
        except Exception as e:
            logging.warning("Migração itens_venda.observacao: %s", e)
        try:
            from seed import seed_missing_data
            seed_missing_data()
        except Exception as e:
            logging.warning("Dados complementares: %s", e)
    _db_ready = True


@app.context_processor
def inject_globals():
    logo_path = os.path.join(app.static_folder, "uploads", "logo.png")
    logo_timestamp = int(os.path.getmtime(logo_path)) if os.path.exists(logo_path) else 0
    return {
        "usuario_nivel": session.get("usuario_nivel"),
        "usuario_nome": session.get("usuario_nome"),
        "now": datetime.now,
        "hoje": date.today(),
        "logo_timestamp": logo_timestamp,
    }


# =================== ERROS ===================

@app.errorhandler(403)
def erro_403(e):
    return render_template("erro.html", codigo=403, mensagem="Acesso negado. Apenas administradores."), 403


@app.errorhandler(404)
def erro_404(e):
    return render_template("erro.html", codigo=404, mensagem="Página não encontrada"), 404


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
