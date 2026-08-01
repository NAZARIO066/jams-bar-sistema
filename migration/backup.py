import os
import shutil
import time
from auth import log_auditoria


def criar_backup(db_path):
    if not os.path.exists(db_path):
        return None, "Banco de dados não encontrado"
    from migration.services import UPLOAD_DIR
    backup_dir = UPLOAD_DIR
    os.makedirs(backup_dir, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_pre_importacao_{ts}.db"
    backup_path = os.path.join(backup_dir, backup_name)
    shutil.copy2(db_path, backup_path)
    log_auditoria("BACKUP_MIGRACAO", f"Backup de segurança: {backup_name}")
    return backup_path, None


