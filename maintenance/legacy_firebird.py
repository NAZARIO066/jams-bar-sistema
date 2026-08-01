"""Conversão segura de backups Firebird do Datacaixa para o formato JAMS."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from flask import current_app
from werkzeug.utils import secure_filename

from maintenance.backup import (
    _inspecionar_db,
    _snapshot_sqlite,
    criar_backup_convertido,
    restaurar_backup,
)


ROOT = Path(__file__).resolve().parents[1]
LEGACY_EXTENSIONS = {".fbk", ".fdb"}
MAX_LEGACY_BYTES = 512 * 1024 * 1024
IMPORT_TIMEOUT_SECONDS = 15 * 60


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _runtime_paths() -> tuple[Path, Path, Path]:
    runtime = Path(
        current_app.config.get("FIREBIRD_RUNTIME_DIR")
        or os.environ.get("FIREBIRD_RUNTIME_DIR")
        or ROOT / "data" / "firebird"
    ).resolve()
    if os.name == "nt":
        gbak = runtime / "gbak.exe"
        client = runtime / "fbclient.dll"
    else:
        gbak = runtime / "bin" / "gbak"
        client = runtime / "lib" / "libfbclient.so"
    return runtime, gbak, client


def status_runtime() -> dict:
    runtime, gbak, client = _runtime_paths()
    ready = gbak.is_file() and client.is_file()
    return {
        "pronto": ready,
        "diretorio": str(runtime),
        "gbak": str(gbak),
        "cliente": str(client),
        "erro": None if ready else (
            "Conversor Firebird 5 não instalado no servidor. "
            "Execute: python scripts/install_firebird_runtime.py"
        ),
    }


def _firebird_environment(runtime: Path, temp_dir: Path) -> dict:
    env = os.environ.copy()
    env["FIREBIRD"] = str(runtime)
    env["FIREBIRD_TMP"] = str(temp_dir)
    env["PATH"] = os.pathsep.join(
        [str(runtime), str(runtime / "bin"), env.get("PATH", "")]
    )
    if os.name != "nt":
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [str(runtime / "lib"), env.get("LD_LIBRARY_PATH", "")]
        )
    return env


def _run(command: list[str], env: dict, timeout: int = IMPORT_TIMEOUT_SECONDS) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("A conversão excedeu 15 minutos e foi cancelada com segurança.") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "falha sem detalhe").strip()
        raise RuntimeError(f"O Firebird recusou o backup: {detail[-1200:]}") from exc


def _restore_fbk(source: Path, destination: Path, gbak: Path, env: dict) -> None:
    _run([
        str(gbak), "-create_database", str(source), str(destination),
        "-user", "SYSDBA", "-password", "masterkey", "-verify",
    ], env)
    if not destination.is_file() or destination.stat().st_size == 0:
        raise RuntimeError("O FBK foi lido, mas o banco Firebird restaurado não foi criado.")


def _prepare_uploads(imported_images: Path, destination: Path) -> None:
    current_uploads = Path(
        current_app.config.get("BACKUP_UPLOADS_DIR")
        or Path(current_app.static_folder) / "uploads"
    )
    if current_uploads.is_dir():
        shutil.copytree(current_uploads, destination)
    else:
        destination.mkdir(parents=True)

    product_images = destination / "produtos"
    if product_images.exists():
        shutil.rmtree(product_images)
    product_images.mkdir(parents=True)
    for image in imported_images.iterdir():
        if image.is_file():
            shutil.copy2(image, product_images / image.name)


def importar_e_aplicar_datacaixa(arquivo, nome_original, usuario_id=None, usuario_nome=None):
    """Valida, converte em staging, empacota e aplica um .fbk/.fdb.

    O banco atual só é tocado na última etapa. A restauração nativa cria
    automaticamente uma cópia completa antes da troca e faz rollback se a
    validação posterior falhar.
    """
    extension = Path(nome_original or "").suffix.lower()
    if extension not in LEGACY_EXTENSIONS:
        return None, "Formato Datacaixa não suportado. Use .fbk ou .FDB"

    runtime_status = status_runtime()
    if not runtime_status["pronto"]:
        return None, runtime_status["erro"]
    runtime, gbak, client = _runtime_paths()

    safe_name = secure_filename(Path(nome_original).name) or f"backup_datacaixa{extension}"
    try:
        with tempfile.TemporaryDirectory(prefix="jams_datacaixa_") as temp_name:
            temp = Path(temp_name)
            uploaded = temp / safe_name
            arquivo.save(uploaded)
            size = uploaded.stat().st_size
            if size == 0:
                return None, "O arquivo enviado está vazio"
            if size > MAX_LEGACY_BYTES:
                return None, "O backup Datacaixa excede o limite de 512 MB"

            source_hash = _sha256(uploaded)
            env = _firebird_environment(runtime, temp)
            firebird_db = uploaded
            if extension == ".fbk":
                firebird_db = temp / "datacaixa_restaurado.fdb"
                _restore_fbk(uploaded, firebird_db, gbak, env)

            staging_db = temp / "bar_adega_convertido.db"
            _snapshot_sqlite(current_app.config["DATABASE"], staging_db)
            imported_images = temp / "imagens_importadas"
            report_file = temp / "relatorio_importacao.json"
            importer = ROOT / "migration" / "import_adega_firebird.py"
            _run([
                sys.executable, str(importer),
                "--source", str(firebird_db),
                "--fbclient", str(client),
                "--sqlite", str(staging_db),
                "--images-dir", str(imported_images),
                "--manifest", str(report_file),
            ], env)

            if not report_file.is_file():
                return None, "A conversão terminou sem gerar o relatório de validação"
            report = json.loads(report_file.read_text(encoding="utf-8"))
            if report.get("erros"):
                return None, f"A fonte contém {len(report['erros'])} registro(s) não importado(s). Operação cancelada."

            inspection, error = _inspecionar_db(staging_db)
            if error:
                return None, f"O banco convertido não passou na integridade: {error}"

            staging_uploads = temp / "uploads_convertidos"
            _prepare_uploads(imported_images, staging_uploads)
            converted, error = criar_backup_convertido(
                str(staging_db), str(staging_uploads),
                descricao=f"Convertido de {safe_name}",
                usuario_id=usuario_id,
                usuario_nome=usuario_nome or "Importação Datacaixa",
                fonte_hash=source_hash,
            )
            if error:
                return None, f"Falha ao criar o pacote convertido: {error}"

            ok, restore_error, safety_backup = restaurar_backup(converted["nome"])
            if not ok:
                return None, restore_error

            return {
                "nome": converted["nome"],
                "formato": f"Datacaixa ({extension})",
                "integridade": "ok",
                "aplicado": True,
                "backup_seguranca": safety_backup,
                "hash_fonte": source_hash,
                "tamanho_mb": round(size / (1024 * 1024), 2),
                "registros": inspection["registros"],
                "imagens": len(report.get("imagens") or []),
                "fonte": report.get("fonte") or {},
                "importados": report.get("importados") or {},
                "avisos": report.get("avisos") or [],
                "erros": report.get("erros") or [],
            }, None
    except Exception as exc:
        return None, f"Falha ao converter o backup Datacaixa: {exc}"
