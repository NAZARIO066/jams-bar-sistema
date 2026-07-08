"""
Script de setup para produção.
Executa automaticamente na primeira vez que o app roda no Render.
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def setup_database():
    """Inicializa o banco de dados e popula dados iniciais."""
    try:
        from app import app
        from database import init_db, get_db
        from seed import seed_initial, seed_missing_data

        with app.app_context():
            db_path = app.config["DATABASE"]
            logger.info("Caminho do banco: %s", db_path)

            if not os.path.exists(db_path):
                logger.info("Banco não encontrado. Criando...")
                init_db()
                seed_initial()
                logger.info("Banco criado e populado com sucesso!")
            else:
                logger.info("Banco já existe. Verificando migrações...")
                from app import ensure_db
                ensure_db()
                seed_missing_data()
                logger.info("Migrações aplicadas.")

            # Verificar tabelas
            db = get_db()
            tables = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            logger.info("Tabelas encontradas: %d", len(tables))
            for t in tables:
                logger.info("  - %s", t["name"])

            return True

    except Exception as e:
        logger.error("Erro ao configurar banco: %s", e)
        return False


def check_environment():
    """Verifica variáveis de ambiente importantes."""
    issues = []

    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        issues.append("SECRET_KEY não definida")

    if issues:
        for issue in issues:
            logger.error("PROBLEMA: %s", issue)
        return False

    logger.info("Variáveis de ambiente OK")
    return True


if __name__ == "__main__":
    logger.info("=== SETUP DE PRODUÇÃO - JAM'S SISTEMA ===")

    if not check_environment():
        logger.error("Corrija os problemas acima e tente novamente.")
        sys.exit(1)

    if setup_database():
        logger.info("Setup concluído com sucesso!")
    else:
        logger.error("Falha no setup.")
        sys.exit(1)
