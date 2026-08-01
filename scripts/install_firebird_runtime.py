"""Instala um runtime privado do Firebird 5 para importar backups Datacaixa.

Não exige acesso administrativo. O pacote oficial é baixado, conferido por
SHA-256 e extraído em data/firebird, fora do controle de versão.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import shutil
import stat
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET = ROOT / "data" / "firebird"

PACKAGES = {
    "Windows": {
        "url": "https://github.com/FirebirdSQL/firebird/releases/download/v5.0.4/Firebird-5.0.4.1812-0-windows-x64.zip",
        "sha256": "01e844fce4d5f53272a76205dbc3a1ba4b782ab8e8eadcd808cdbccd9ce13b72",
        "kind": "zip",
    },
    "Linux": {
        "url": "https://github.com/FirebirdSQL/firebird/releases/download/v5.0.4/Firebird-5.0.4.1812-0-linux-x64.tar.gz",
        "sha256": "ab6a15a0258f38b022be496bb5e038c14e8628ce9acd0f9a06288a3baedd917b",
        "kind": "linux_tar",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_zip_extract(archive: Path, target: Path) -> None:
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            parts = PurePosixPath(info.filename.replace("\\", "/")).parts
            if not parts or ".." in parts:
                raise RuntimeError(f"Caminho inseguro no pacote: {info.filename}")
            destination = target.joinpath(*parts)
            if info.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as source, destination.open("wb") as output:
                shutil.copyfileobj(source, output)


def extract_linux(archive: Path, target: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="jams_firebird_outer_") as temp_name:
        temp = Path(temp_name)
        with tarfile.open(archive, "r:gz") as outer:
            buildroot_member = next(
                (m for m in outer.getmembers() if m.name.endswith("/buildroot.tar.gz")),
                None,
            )
            if not buildroot_member:
                raise RuntimeError("buildroot.tar.gz ausente no pacote oficial")
            extracted = outer.extractfile(buildroot_member)
            if extracted is None:
                raise RuntimeError("Não foi possível ler buildroot.tar.gz")
            buildroot = temp / "buildroot.tar.gz"
            with buildroot.open("wb") as output:
                shutil.copyfileobj(extracted, output)

        prefix = PurePosixPath("opt/firebird")
        with tarfile.open(buildroot, "r:gz") as inner:
            for member in inner.getmembers():
                clean = PurePosixPath(member.name.removeprefix("./"))
                if clean == prefix:
                    continue
                try:
                    relative = clean.relative_to(prefix)
                except ValueError:
                    continue
                if ".." in relative.parts or member.issym() or member.islnk():
                    continue
                destination = target.joinpath(*relative.parts)
                if member.isdir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                if not member.isfile():
                    continue
                source = inner.extractfile(member)
                if source is None:
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("wb") as output:
                    shutil.copyfileobj(source, output)
                os.chmod(destination, member.mode)


def install(target: Path, force: bool = False, archive: Path | None = None) -> Path:
    system = platform.system()
    if platform.machine().lower() not in {"amd64", "x86_64"}:
        raise RuntimeError("O instalador automático suporta servidores x64.")
    package = PACKAGES.get(system)
    if package is None:
        raise RuntimeError(f"Sistema operacional não suportado: {system}")

    if target.exists():
        if not force:
            raise RuntimeError(f"O runtime já existe em {target}. Use --force para reinstalar.")
        shutil.rmtree(target)

    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="jams_firebird_download_") as temp_name:
        download = Path(temp_name) / "firebird-package"
        if archive is not None:
            if not archive.is_file():
                raise RuntimeError(f"Pacote local não encontrado: {archive}")
            print("Conferindo o pacote local do Firebird 5.0.4...")
            shutil.copy2(archive, download)
        else:
            print("Baixando o pacote oficial do Firebird 5.0.4...")
            urllib.request.urlretrieve(package["url"], download)
        actual_hash = sha256(download)
        if actual_hash != package["sha256"]:
            raise RuntimeError(
                f"Assinatura do pacote divergente: {actual_hash}. Instalação cancelada."
            )
        target.mkdir(parents=True)
        if package["kind"] == "zip":
            safe_zip_extract(download, target)
        else:
            extract_linux(download, target)

    executable = target / ("gbak.exe" if system == "Windows" else "bin/gbak")
    client = target / ("fbclient.dll" if system == "Windows" else "lib/libfbclient.so")
    if not executable.is_file() or not client.is_file():
        raise RuntimeError("Instalação incompleta: gbak ou cliente Firebird ausente.")
    if system != "Windows":
        executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    print(f"Firebird pronto em: {target}")
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--archive", type=Path, help="Pacote oficial já baixado")
    args = parser.parse_args()
    archive = args.archive.resolve() if args.archive else None
    install(args.target.resolve(), force=args.force, archive=archive)


if __name__ == "__main__":
    main()
