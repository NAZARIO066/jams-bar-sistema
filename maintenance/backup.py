import os
import time
import shutil
from datetime import datetime


BACKUP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "static", "uploads", "backups"
)


def _ensure_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def _db_path():
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "bar_adega.db"
    )


def criar_backup(descricao="", usuario_id=None, usuario_nome=None):
    _ensure_dir()
    db = _db_path()
    if not os.path.exists(db):
        return None, "Banco de dados não encontrado"
    ts = time.strftime("%Y%m%d_%H%M%S")
    nome = f"backup_{ts}.db"
    dest = os.path.join(BACKUP_DIR, nome)
    shutil.copy2(db, dest)
    meta_path = dest + ".meta"
    with open(meta_path, "w", encoding="utf-8") as f:
        f.write(f"{descricao}\n{datetime.now().isoformat()}\n{os.path.getsize(dest)}\n{usuario_id or ''}\n{usuario_nome or ''}")
    return {
        "nome": nome,
        "caminho": dest,
        "tamanho": os.path.getsize(dest),
        "tamanho_mb": round(os.path.getsize(dest) / (1024 * 1024), 2),
        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "descricao": descricao,
        "usuario": usuario_nome,
    }, None


def listar_backups():
    _ensure_dir()
    backups = []
    for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
        if not f.endswith(".db") or f.endswith(".meta"):
            continue
        fp = os.path.join(BACKUP_DIR, f)
        if not os.path.isfile(fp):
            continue
        stat = os.stat(fp)
        desc = ""
        usuario = ""
        data_iso = ""
        meta = fp + ".meta"
        if os.path.exists(meta):
            try:
                with open(meta, "r", encoding="utf-8") as mf:
                    lines = mf.read().splitlines()
                    desc = lines[0].strip() if len(lines) > 0 else ""
                    data_iso = lines[1].strip() if len(lines) > 1 else ""
                    usuario = lines[4].strip() if len(lines) > 4 else ""
            except Exception:
                pass
        backups.append({
            "nome": f,
            "tamanho_mb": round(stat.st_size / (1024 * 1024), 2),
            "tamanho_bytes": stat.st_size,
            "data": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "descricao": desc,
            "usuario": usuario,
        })
    return backups


def obter_backup(nome):
    _ensure_dir()
    fp = os.path.join(BACKUP_DIR, nome)
    if not os.path.exists(fp) or not fp.endswith(".db"):
        return None
    if not os.path.isfile(fp):
        return None
    return fp


def restaurar_backup(nome):
    src = obter_backup(nome)
    if not src:
        return False, "Backup não encontrado", None
    db = _db_path()
    if not os.path.exists(db):
        return False, "Banco de dados atual não encontrado", None
    ts = time.strftime("%Y%m%d_%H%M%S")
    pre_name = f"pre_restauracao_{ts}.db"
    pre_path = os.path.join(BACKUP_DIR, pre_name)
    try:
        shutil.copy2(db, pre_path)
        pre_meta = pre_path + ".meta"
        with open(pre_meta, "w", encoding="utf-8") as f:
            f.write(f"Backup automático pré-restauração\n{datetime.now().isoformat()}\n{os.path.getsize(pre_path)}\n\nSistema")
    except Exception as e:
        return False, f"Erro ao criar backup pré-restauração: {e}", None
    try:
        shutil.copy2(src, db)
        return True, None, pre_name
    except Exception as e:
        try:
            shutil.copy2(pre_path, db)
        except Exception:
            pass
        return False, f"Erro ao restaurar: {e}. Backup de segurança restaurado.", pre_name


def remover_backup(nome):
    fp = obter_backup(nome)
    if not fp:
        return False
    meta = fp + ".meta"
    try:
        os.remove(fp)
        if os.path.exists(meta):
            os.remove(meta)
        return True
    except Exception:
        return False


def espaco_utilizado():
    _ensure_dir()
    total = 0
    for f in os.listdir(BACKUP_DIR):
        if f.endswith(".db") and not f.endswith(".meta") and not f.endswith(".db-journal") and not f.endswith(".db-wal"):
            fp = os.path.join(BACKUP_DIR, f)
            if os.path.isfile(fp):
                total += os.path.getsize(fp)
    return {
        "bytes": total,
        "mb": round(total / (1024 * 1024), 2),
    }


def contar_backups():
    _ensure_dir()
    count = 0
    for f in os.listdir(BACKUP_DIR):
        if f.endswith(".db") and not f.endswith(".meta") and not f.endswith(".db-journal") and not f.endswith(".db-wal"):
            fp = os.path.join(BACKUP_DIR, f)
            if os.path.isfile(fp):
                count += 1
    return count


def ultimo_backup():
    _ensure_dir()
    latest = None
    latest_time = 0
    for f in os.listdir(BACKUP_DIR):
        if f.endswith(".db") and not f.endswith(".meta") and not f.endswith(".db-journal") and not f.endswith(".db-wal"):
            fp = os.path.join(BACKUP_DIR, f)
            if os.path.isfile(fp):
                mt = os.path.getmtime(fp)
                if mt > latest_time:
                    latest_time = mt
                    latest = {
                        "nome": f,
                        "data": datetime.fromtimestamp(mt).strftime("%Y-%m-%d %H:%M:%S"),
                    }
    return latest
