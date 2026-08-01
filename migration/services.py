import os
import time
import uuid
from datetime import datetime
from flask import current_app, session
from database import get_db
from auth import log_auditoria

UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "migration_tmp"
)


def ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def salvar_arquivo(file_storage):
    ensure_upload_dir()
    original_name = file_storage.filename or "arquivo"
    safe_name = f"{int(time.time())}_{uuid.uuid4().hex[:8]}_{original_name}"
    filepath = os.path.join(UPLOAD_DIR, safe_name)
    file_storage.save(filepath)
    size = os.path.getsize(filepath)
    return {
        "caminho": filepath,
        "nome_original": original_name,
        "nome_seguro": safe_name,
        "tamanho": size,
        "tamanho_mb": round(size / (1024 * 1024), 2),
        "data_upload": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def obter_info_arquivo(filepath):
    if not os.path.exists(filepath):
        return None
    stat = os.stat(filepath)
    return {
        "caminho": filepath,
        "tamanho": stat.st_size,
        "tamanho_mb": round(stat.st_size / (1024 * 1024), 2),
        "data_modificacao": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
    }


def limpar_arquivo(filepath):
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
            return True
    except Exception:
        pass
    return False


def limpar_uploads_antigos(max_age_hours=24):
    ensure_upload_dir()
    now = time.time()
    cutoff = now - (max_age_hours * 3600)
    removed = 0
    for f in os.listdir(UPLOAD_DIR):
        fp = os.path.join(UPLOAD_DIR, f)
        if os.path.isfile(fp) and os.path.getmtime(fp) < cutoff:
            try:
                os.remove(fp)
                removed += 1
            except Exception:
                pass
    return removed


def salvar_sessao_migracao(dados):
    session["migracao"] = dados


def obter_sessao_migracao():
    return session.get("migracao", {})


def limpar_sessao_migracao():
    m = session.pop("migracao", None)
    if m and m.get("arquivo", {}).get("caminho"):
        limpar_arquivo(m["arquivo"]["caminho"])
    return m


def criar_backup_pre_importacao():
    db_path = current_app.config["DATABASE"]
    if not os.path.exists(db_path):
        return None, "Banco de dados não encontrado"
    ensure_upload_dir()
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup_name = f"pre_importacao_{ts}.db"
    backup_path = os.path.join(UPLOAD_DIR, backup_name)
    import shutil
    shutil.copy2(db_path, backup_path)
    log_auditoria("BACKUP_PRE_IMPORTACAO", f"Backup criado: {backup_name}")
    return backup_path, None
