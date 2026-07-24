import os
import shutil
import time
from auth import log_auditoria


def criar_backup(db_path):
    if not os.path.exists(db_path):
        return None, "Banco de dados não encontrado"
    backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "uploads", "migration_tmp")
    os.makedirs(backup_dir, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_pre_importacao_{ts}.db"
    backup_path = os.path.join(backup_dir, backup_name)
    shutil.copy2(db_path, backup_path)
    log_auditoria("BACKUP_MIGRACAO", f"Backup de segurança: {backup_name}")
    return backup_path, None


def listar_backups(diretorio):
    backups = []
    if not os.path.exists(diretorio):
        return backups
    for f in sorted(os.listdir(diretorio), reverse=True):
        if f.startswith("backup_") or f.startswith("pre_importacao_"):
            fp = os.path.join(diretorio, f)
            stat = os.stat(fp)
            backups.append({
                "nome": f,
                "caminho": fp,
                "tamanho_mb": round(stat.st_size / (1024 * 1024), 2),
            })
    return backups
