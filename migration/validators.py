import os
import struct

ALLOWED_EXTENSIONS = {
    "sqlite": {"db", "sqlite", "sqlite3"},
    "sql": {"sql"},
    "excel": {"xlsx", "xls"},
    "csv": {"csv"},
}

MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

DANGEROUS_EXECUTABLES = {
    "exe", "bat", "cmd", "com", "msi", "pif", "scr", "vbs", "vbe",
    "js", "jse", "wsf", "wsh", "ps1", "psm1", "psd1", "reg",
    "dll", "sys", "cpl", "hta", "inf", "lnk",
}


def validar_extensao(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    for tipo, exts in ALLOWED_EXTENSIONS.items():
        if ext in exts:
            return True, tipo, ext
    return False, None, ext


def validar_tamanho(size_bytes):
    if size_bytes > MAX_FILE_SIZE_BYTES:
        return False, size_bytes / (1024 * 1024)
    return True, size_bytes


def is_executavel(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in DANGEROUS_EXECUTABLES


def validar_magic_bytes(filepath):
    try:
        with open(filepath, "rb") as f:
            header = f.read(16)
        if len(header) < 4:
            return False, "Arquivo vazio ou muito pequeno"
        if header[:16] == b"SQLite format 3\x00":
            return True, "sqlite"
        if header[:2] == b"\xff\xfe" or header[:2] == b"\xfe\xff":
            return True, "sql"
        if header[:4] == b"\xef\xbb\xbf" or header[:2] == b"\xff\xfe":
            return True, "sql"
        if header[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            return True, "excel"
        if header[:4] == b"PK\x03\x04":
            return True, "excel"
        first_line = header.decode("utf-8", errors="ignore").split("\n")[0].strip()
        if first_line and "," in first_line or ";" in first_line or "\t" in first_line:
            return True, "csv"
        return True, "desconhecido"
    except Exception as e:
        return False, f"Erro ao ler: {str(e)}"


def validar_upload_completo(filename, size_bytes):
    erros = []

    if is_executavel(filename):
        erros.append("Arquivo executável não é permitido por segurança")

    ok_ext, tipo, ext = validar_extensao(filename)
    if not ok_ext:
        erros.append(f"Extensão '.{ext}' não é suportada. Use: {', '.join(sorted(set().union(*ALLOWED_EXTENSIONS.values())))}")

    ok_tam, mb = validar_tamanho(size_bytes)
    if not ok_tam:
        erros.append(f"Arquivo muito grande ({mb:.1f} MB). Limite: {MAX_FILE_SIZE_MB} MB")

    return {
        "valido": len(erros) == 0,
        "erros": erros,
        "tipo_detectado": tipo,
        "extensao": ext,
        "tamanho_mb": round(size_bytes / (1024 * 1024), 2),
    }
