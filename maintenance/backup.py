import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import time
import uuid
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

from flask import current_app, g


BACKUP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "backups"
)

FORMATO_BACKUP = "jams-adega-backup"
VERSAO_BACKUP = 1
EXTENSOES_BACKUP = (".zip", ".db")
TABELAS_OBRIGATORIAS = {
    "usuarios", "empresa", "categorias", "produtos", "clientes",
    "mesas", "comandas", "itens_comanda", "vendas", "itens_venda",
}


def _ensure_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def _db_path():
    return current_app.config["DATABASE"]


def _uploads_path():
    return current_app.config.get(
        "BACKUP_UPLOADS_DIR",
        os.path.join(current_app.static_folder, "uploads"),
    )


def _agora_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _nome_valido(nome):
    if not isinstance(nome, str) or not nome:
        return False
    if os.path.basename(nome) != nome or "/" in nome or "\\" in nome:
        return False
    return nome.lower().endswith(EXTENSOES_BACKUP)


def _arquivos_backup():
    _ensure_dir()
    for nome in os.listdir(BACKUP_DIR):
        if nome.lower() == "audit.db":
            continue
        if not _nome_valido(nome):
            continue
        caminho = os.path.join(BACKUP_DIR, nome)
        if os.path.isfile(caminho):
            yield nome, caminho


def _sha256(caminho):
    digest = hashlib.sha256()
    with open(caminho, "rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def _sha256_zip(zf, nome):
    digest = hashlib.sha256()
    with zf.open(nome, "r") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def _snapshot_sqlite(origem, destino):
    origem_uri = Path(origem).resolve().as_uri() + "?mode=ro"
    src = sqlite3.connect(origem_uri, uri=True, timeout=30)
    dst = sqlite3.connect(destino)
    try:
        src.backup(dst)
        dst.commit()
    finally:
        dst.close()
        src.close()


def _inspecionar_db(caminho):
    if not os.path.isfile(caminho) or os.path.getsize(caminho) == 0:
        return None, "O arquivo do banco está vazio ou não existe"
    try:
        uri = Path(caminho).resolve().as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=20)
        try:
            integridade = conn.execute("PRAGMA integrity_check").fetchone()
            if not integridade or integridade[0] != "ok":
                detalhe = integridade[0] if integridade else "sem resposta"
                return None, f"Falha de integridade SQLite: {detalhe}"

            fks = conn.execute("PRAGMA foreign_key_check").fetchall()
            if fks:
                return None, f"O backup contém {len(fks)} vínculo(s) inválido(s)"

            tabelas = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                ).fetchall()
            }
            ausentes = sorted(TABELAS_OBRIGATORIAS - tabelas)
            if ausentes:
                return None, "Tabelas obrigatórias ausentes: " + ", ".join(ausentes)

            contagens = {}
            for tabela in sorted(tabelas):
                nome_seguro = tabela.replace('"', '""')
                contagens[tabela] = conn.execute(
                    f'SELECT COUNT(*) FROM "{nome_seguro}"'
                ).fetchone()[0]
            return {
                "integridade": "ok",
                "tabelas": len(tabelas),
                "registros": sum(contagens.values()),
                "contagens": contagens,
            }, None
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return None, f"Arquivo SQLite inválido: {exc}"


def _configuracao_segura():
    return {
        "aplicacao": "Sistema de Gestão para Bar, Adega e Mesas",
        "formato_backup": FORMATO_BACKUP,
        "versao_backup": VERSAO_BACKUP,
        "criado_em": _agora_iso(),
        "banco_arquivo": os.path.basename(_db_path()),
        "sessao": {
            "cookie_httponly": bool(current_app.config.get("SESSION_COOKIE_HTTPONLY", True)),
            "cookie_samesite": current_app.config.get("SESSION_COOKIE_SAMESITE", "Lax"),
            "duracao_segundos": int(current_app.config.get("PERMANENT_SESSION_LIFETIME", 0).total_seconds())
            if hasattr(current_app.config.get("PERMANENT_SESSION_LIFETIME"), "total_seconds")
            else int(current_app.config.get("PERMANENT_SESSION_LIFETIME", 0) or 0),
        },
        "observacao": "Segredos e senhas do ambiente não são incluídos no pacote.",
    }


def _escrever_meta(caminho, dados):
    with open(caminho + ".meta", "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)


def _ler_meta(caminho):
    meta = caminho + ".meta"
    if not os.path.exists(meta):
        return {}
    try:
        with open(meta, "r", encoding="utf-8") as arquivo:
            texto = arquivo.read()
        try:
            return json.loads(texto)
        except json.JSONDecodeError:
            linhas = texto.splitlines()
            return {
                "descricao": linhas[0].strip() if linhas else "",
                "criado_em": linhas[1].strip() if len(linhas) > 1 else "",
                "usuario": linhas[4].strip() if len(linhas) > 4 else "",
            }
    except OSError:
        return {}


def _criar_pacote(nome, descricao="", usuario_id=None, usuario_nome=None,
                  db_origem=None, uploads_origem=None):
    _ensure_dir()
    db = db_origem or _db_path()
    if not os.path.exists(db):
        return None, "Banco de dados não encontrado"

    destino = os.path.join(BACKUP_DIR, nome)
    temp_destino = destino + f".{uuid.uuid4().hex}.tmp.zip"
    arquivos_manifesto = []

    try:
        with tempfile.TemporaryDirectory(prefix="jams_backup_") as temp_dir:
            snapshot = os.path.join(temp_dir, "bar_adega.db")
            _snapshot_sqlite(db, snapshot)
            inspecao, erro = _inspecionar_db(snapshot)
            if erro:
                return None, f"Não foi possível validar o banco antes do backup: {erro}"

            with zipfile.ZipFile(temp_destino, "w", compression=zipfile.ZIP_DEFLATED,
                                 allowZip64=True) as zf:
                db_arc = "database/bar_adega.db"
                zf.write(snapshot, db_arc)
                arquivos_manifesto.append({
                    "caminho": db_arc,
                    "tamanho": os.path.getsize(snapshot),
                    "sha256": _sha256(snapshot),
                })

                uploads = uploads_origem if uploads_origem is not None else _uploads_path()
                if os.path.isdir(uploads):
                    for raiz, dirs, arquivos in os.walk(uploads):
                        dirs.sort()
                        for arquivo_nome in sorted(arquivos):
                            origem = os.path.join(raiz, arquivo_nome)
                            relativo = os.path.relpath(origem, uploads).replace(os.sep, "/")
                            arcname = f"static/uploads/{relativo}"
                            zf.write(origem, arcname)
                            arquivos_manifesto.append({
                                "caminho": arcname,
                                "tamanho": os.path.getsize(origem),
                                "sha256": _sha256(origem),
                            })

                config_json = json.dumps(
                    _configuracao_segura(), ensure_ascii=False, indent=2
                ).encode("utf-8")
                config_arc = "config/config_snapshot.json"
                zf.writestr(config_arc, config_json)
                arquivos_manifesto.append({
                    "caminho": config_arc,
                    "tamanho": len(config_json),
                    "sha256": hashlib.sha256(config_json).hexdigest(),
                })

                env_exemplo = os.path.join(current_app.root_path, ".env.example")
                if os.path.isfile(env_exemplo):
                    env_arc = "config/.env.example"
                    zf.write(env_exemplo, env_arc)
                    arquivos_manifesto.append({
                        "caminho": env_arc,
                        "tamanho": os.path.getsize(env_exemplo),
                        "sha256": _sha256(env_exemplo),
                    })

                manifesto = {
                    "formato": FORMATO_BACKUP,
                    "versao": VERSAO_BACKUP,
                    "criado_em": _agora_iso(),
                    "descricao": descricao.strip(),
                    "usuario_id": usuario_id,
                    "usuario": usuario_nome or "Sistema",
                    "banco": inspecao,
                    "arquivos": arquivos_manifesto,
                }
                zf.writestr(
                    "manifest.json",
                    json.dumps(manifesto, ensure_ascii=False, indent=2).encode("utf-8"),
                )

            validacao, erro = validar_backup(temp_destino)
            if erro:
                return None, f"O pacote criado não passou na validação: {erro}"
            os.replace(temp_destino, destino)

        agora = datetime.now()
        meta = {
            "descricao": descricao.strip(),
            "criado_em": agora.astimezone().isoformat(timespec="seconds"),
            "usuario_id": usuario_id,
            "usuario": usuario_nome or "Sistema",
            "formato": validacao["formato"],
            "integridade": "ok",
        }
        _escrever_meta(destino, meta)
        tamanho = os.path.getsize(destino)
        return {
            "nome": nome,
            "caminho": destino,
            "tamanho": tamanho,
            "tamanho_bytes": tamanho,
            "tamanho_mb": round(tamanho / (1024 * 1024), 2),
            "data": agora.strftime("%Y-%m-%d %H:%M:%S"),
            "descricao": descricao.strip(),
            "usuario": usuario_nome or "Sistema",
            "formato": "Completo (.zip)",
            "integridade": "ok",
        }, None
    except Exception as exc:
        return None, f"Erro ao criar backup completo: {exc}"
    finally:
        if os.path.exists(temp_destino):
            try:
                os.remove(temp_destino)
            except OSError:
                pass


def criar_backup(descricao="", usuario_id=None, usuario_nome=None):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return _criar_pacote(
        f"backup_{ts}.zip",
        descricao=descricao,
        usuario_id=usuario_id,
        usuario_nome=usuario_nome,
    )


def criar_backup_convertido(db_origem, uploads_origem, descricao="", usuario_id=None,
                            usuario_nome=None, fonte_hash=None):
    """Cria um pacote nativo validado a partir de uma conversão em staging."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    descricao_final = descricao.strip() or "Conversão de backup Datacaixa"
    if fonte_hash:
        descricao_final += f" | SHA-256: {fonte_hash}"
    return _criar_pacote(
        f"convertido_datacaixa_{ts}.zip",
        descricao=descricao_final,
        usuario_id=usuario_id,
        usuario_nome=usuario_nome,
        db_origem=db_origem,
        uploads_origem=uploads_origem,
    )


def validar_backup(caminho):
    if not os.path.isfile(caminho):
        return None, "Backup não encontrado"

    if caminho.lower().endswith(".db"):
        inspecao, erro = _inspecionar_db(caminho)
        if erro:
            return None, erro
        return {
            "formato": "Banco legado (.db)",
            "integridade": "ok",
            "banco": inspecao,
            "imagens": 0,
        }, None

    if not caminho.lower().endswith(".zip"):
        return None, "Formato não suportado. Use .zip ou .db"

    try:
        with zipfile.ZipFile(caminho, "r") as zf:
            nomes = zf.namelist()
            for nome in nomes:
                path = PurePosixPath(nome)
                if path.is_absolute() or ".." in path.parts or "\\" in nome:
                    return None, f"Caminho inseguro encontrado no pacote: {nome}"
            corrompido = zf.testzip()
            if corrompido:
                return None, f"Arquivo corrompido dentro do pacote: {corrompido}"
            if "manifest.json" not in nomes or "database/bar_adega.db" not in nomes:
                return None, "Pacote incompleto: manifest ou banco ausente"

            try:
                manifesto = json.loads(zf.read("manifest.json").decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                return None, f"Manifesto inválido: {exc}"
            if manifesto.get("formato") != FORMATO_BACKUP:
                return None, "Este ZIP não é um backup reconhecido do sistema"
            if manifesto.get("versao") != VERSAO_BACKUP:
                return None, "Versão de backup incompatível"

            declarados = manifesto.get("arquivos") or []
            for item in declarados:
                nome = item.get("caminho")
                if not nome or nome not in nomes:
                    return None, f"Arquivo declarado ausente: {nome or 'sem nome'}"
                if int(item.get("tamanho", -1)) != zf.getinfo(nome).file_size:
                    return None, f"Tamanho divergente no arquivo: {nome}"
                if item.get("sha256") != _sha256_zip(zf, nome):
                    return None, f"Assinatura divergente no arquivo: {nome}"

            with tempfile.TemporaryDirectory(prefix="jams_validar_") as temp_dir:
                db_temp = os.path.join(temp_dir, "bar_adega.db")
                with zf.open("database/bar_adega.db") as origem, open(db_temp, "wb") as destino:
                    shutil.copyfileobj(origem, destino, length=1024 * 1024)
                inspecao, erro = _inspecionar_db(db_temp)
                if erro:
                    return None, erro

            esperadas = (manifesto.get("banco") or {}).get("contagens")
            if esperadas and esperadas != inspecao["contagens"]:
                return None, "As contagens do banco não conferem com o manifesto"

            return {
                "formato": "Completo (.zip)",
                "integridade": "ok",
                "banco": inspecao,
                "imagens": sum(1 for n in nomes if n.startswith("static/uploads/") and not n.endswith("/")),
                "manifesto": manifesto,
            }, None
    except (OSError, zipfile.BadZipFile) as exc:
        return None, f"ZIP inválido ou corrompido: {exc}"


def listar_backups(limite=None, offset=0):
    backups = []
    arquivos = sorted(
        _arquivos_backup(),
        key=lambda item: os.path.getmtime(item[1]),
        reverse=True,
    )
    inicio = max(0, int(offset or 0))
    if limite is None:
        selecionados = arquivos[inicio:]
    else:
        selecionados = arquivos[inicio:inicio + max(0, int(limite))]
    for nome, caminho in selecionados:
        stat = os.stat(caminho)
        meta = _ler_meta(caminho)
        backups.append({
            "nome": nome,
            "tamanho_mb": round(stat.st_size / (1024 * 1024), 2),
            "tamanho_bytes": stat.st_size,
            "data": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "descricao": meta.get("descricao", ""),
            "usuario": meta.get("usuario", ""),
            "formato": meta.get("formato") or (
                "Completo (.zip)" if nome.lower().endswith(".zip") else "Banco legado (.db)"
            ),
            "integridade": meta.get("integridade", "não verificada"),
        })
    return backups


def obter_backup(nome):
    _ensure_dir()
    if not _nome_valido(nome):
        return None
    caminho = os.path.abspath(os.path.join(BACKUP_DIR, nome))
    raiz = os.path.abspath(BACKUP_DIR)
    if os.path.commonpath([caminho, raiz]) != raiz:
        return None
    return caminho if os.path.isfile(caminho) else None


def _fechar_conexao_da_requisicao():
    try:
        db = g.pop("db", None)
        if db is not None:
            db.close()
    except RuntimeError:
        pass


def _instalar_db(candidato):
    destino = _db_path()
    temp_destino = destino + f".{uuid.uuid4().hex}.restore"
    shutil.copy2(candidato, temp_destino)
    _fechar_conexao_da_requisicao()
    os.replace(temp_destino, destino)


def _instalar_uploads(pasta_extraida):
    destino = _uploads_path()
    pai = os.path.dirname(destino)
    os.makedirs(pai, exist_ok=True)
    staging = os.path.join(pai, f".uploads_restore_{uuid.uuid4().hex}")
    anterior = os.path.join(pai, f".uploads_anterior_{uuid.uuid4().hex}")
    shutil.copytree(pasta_extraida, staging)
    try:
        if os.path.exists(destino):
            os.replace(destino, anterior)
        os.replace(staging, destino)
        if os.path.exists(anterior):
            shutil.rmtree(anterior)
    except Exception:
        if os.path.exists(destino):
            shutil.rmtree(destino)
        if os.path.exists(anterior):
            os.replace(anterior, destino)
        raise
    finally:
        if os.path.exists(staging):
            shutil.rmtree(staging)


def _aplicar_backup(caminho):
    if caminho.lower().endswith(".db"):
        _instalar_db(caminho)
        return

    with tempfile.TemporaryDirectory(prefix="jams_restaurar_") as temp_dir:
        with zipfile.ZipFile(caminho, "r") as zf:
            db_temp = os.path.join(temp_dir, "bar_adega.db")
            with zf.open("database/bar_adega.db") as origem, open(db_temp, "wb") as destino:
                shutil.copyfileobj(origem, destino, length=1024 * 1024)

            uploads_temp = os.path.join(temp_dir, "uploads")
            os.makedirs(uploads_temp)
            for info in zf.infolist():
                prefixo = "static/uploads/"
                if not info.filename.startswith(prefixo) or info.is_dir():
                    continue
                relativo = PurePosixPath(info.filename[len(prefixo):])
                alvo = os.path.join(uploads_temp, *relativo.parts)
                os.makedirs(os.path.dirname(alvo), exist_ok=True)
                with zf.open(info) as origem, open(alvo, "wb") as destino:
                    shutil.copyfileobj(origem, destino, length=1024 * 1024)

        _instalar_db(db_temp)
        _instalar_uploads(uploads_temp)


def restaurar_backup(nome):
    origem = obter_backup(nome)
    if not origem:
        return False, "Backup não encontrado", None
    validacao, erro = validar_backup(origem)
    if erro:
        return False, f"Backup recusado antes da restauração: {erro}", None
    if not os.path.exists(_db_path()):
        return False, "Banco de dados atual não encontrado", None

    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    pre_nome = f"pre_restauracao_{ts}.zip"
    pre_info, pre_erro = _criar_pacote(
        pre_nome,
        descricao=f"Backup automático antes de restaurar {nome}",
        usuario_nome="Sistema",
    )
    if pre_erro:
        return False, f"Erro ao criar backup completo pré-restauração: {pre_erro}", None

    pre_caminho = pre_info["caminho"]
    try:
        _aplicar_backup(origem)
        pos, pos_erro = _inspecionar_db(_db_path())
        if pos_erro:
            raise RuntimeError(f"validação após restauração falhou: {pos_erro}")
        esperadas = validacao["banco"]["contagens"]
        if pos["contagens"] != esperadas:
            raise RuntimeError("contagens após restauração não conferem")
        return True, None, pre_nome
    except Exception as exc:
        try:
            _aplicar_backup(pre_caminho)
            return False, f"Erro ao restaurar: {exc}. O estado anterior foi recuperado.", pre_nome
        except Exception as rollback_exc:
            return False, (
                f"Erro ao restaurar: {exc}. A recuperação automática também falhou: "
                f"{rollback_exc}. Preserve o arquivo {pre_nome}."
            ), pre_nome


def importar_backup(arquivo, nome_original="backup_importado.zip"):
    _ensure_dir()
    extensao = os.path.splitext(nome_original)[1].lower()
    if extensao not in EXTENSOES_BACKUP:
        return None, "Formato não suportado. Selecione um arquivo .zip ou .db"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    nome = f"importado_{ts}{extensao}"
    destino = os.path.join(BACKUP_DIR, nome)
    temp_destino = destino + f".{uuid.uuid4().hex}.tmp{extensao}"
    try:
        arquivo.save(temp_destino)
        validacao, erro = validar_backup(temp_destino)
        if erro:
            return None, erro
        os.replace(temp_destino, destino)
        agora = datetime.now()
        _escrever_meta(destino, {
            "descricao": f"Importado de {os.path.basename(nome_original)}",
            "criado_em": agora.astimezone().isoformat(timespec="seconds"),
            "usuario": "Importação",
            "formato": validacao["formato"],
            "integridade": "ok",
        })
        tamanho = os.path.getsize(destino)
        return {
            "nome": nome,
            "tamanho_bytes": tamanho,
            "tamanho_mb": round(tamanho / (1024 * 1024), 2),
            "formato": validacao["formato"],
            "integridade": "ok",
            "registros": validacao["banco"]["registros"],
            "imagens": validacao.get("imagens", 0),
        }, None
    except Exception as exc:
        return None, f"Erro ao importar backup: {exc}"
    finally:
        if os.path.exists(temp_destino):
            try:
                os.remove(temp_destino)
            except OSError:
                pass


def remover_backup(nome):
    caminho = obter_backup(nome)
    if not caminho:
        return False
    try:
        os.remove(caminho)
        meta = caminho + ".meta"
        if os.path.exists(meta):
            os.remove(meta)
        return True
    except OSError:
        return False


def espaco_utilizado():
    total = sum(os.path.getsize(caminho) for _, caminho in _arquivos_backup())
    return {"bytes": total, "mb": round(total / (1024 * 1024), 2)}


def contar_backups():
    return sum(1 for _ in _arquivos_backup())


def ultimo_backup():
    arquivos = list(_arquivos_backup())
    if not arquivos:
        return None
    nome, caminho = max(arquivos, key=lambda item: os.path.getmtime(item[1]))
    return {
        "nome": nome,
        "data": datetime.fromtimestamp(os.path.getmtime(caminho)).strftime("%Y-%m-%d %H:%M:%S"),
    }
