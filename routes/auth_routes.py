import hmac
import logging
import secrets
import sqlite3
from datetime import datetime

from flask import flash, make_response, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from database import get_db
from auth import login_required, log_auditoria, check_login_rate_limit, record_login_attempt


def _get_or_create_csrf_token():
    """Mantém o token estável enquanto a sessão anônima continuar válida."""
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_hex(24)
        session["_csrf_token"] = token
    return token


def _login_response(status_code=200):
    response = make_response(
        render_template("login.html", csrf_token=_get_or_create_csrf_token()),
        status_code,
    )
    # Evita que o navegador restaure um formulário de login com token antigo.
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


def _redirect_without_cache(endpoint):
    response = redirect(url_for(endpoint))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


def register_auth_routes(app):

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            _get_or_create_csrf_token()
            return _login_response()

        csrf_token = request.form.get("_csrf_token", "")
        expected_token = session.get("_csrf_token", "")
        if (
            not csrf_token
            or not expected_token
            or not hmac.compare_digest(csrf_token, expected_token)
        ):
            # Remove todo estado antigo e já devolve um formulário utilizável.
            session.clear()
            _get_or_create_csrf_token()
            flash("Sua sessão expirou. Tente entrar novamente.", "danger")
            return _login_response(400)

        login_user = request.form.get("login", "").strip()
        senha = request.form.get("senha", "")

        try:
            if not check_login_rate_limit(login_user):
                try:
                    log_auditoria("LOGIN_BLOQUEADO", f"Tentativas excessivas para {login_user}")
                except Exception:
                    logging.exception("Falha ao registrar bloqueio de login na auditoria")
                flash("Muitas tentativas. Aguarde 5 minutos.", "danger")
                return _login_response(429)

            db = get_db()
            user = db.execute(
                """SELECT u.*, p.nome AS perfil_nome
                   FROM usuarios u
                   LEFT JOIN perfis_acesso p ON p.id=u.perfil_id
                   WHERE u.login=?""",
                (login_user,),
            ).fetchone()
            if user and check_password_hash(user["senha"], senha):
                if not user["ativo"]:
                    log_auditoria(
                        "LOGIN_NEGADO_INATIVO", "Tentativa de acesso com usuário desativado",
                        usuario_id=user["id"], usuario_nome=user["nome"],
                    )
                    flash("Este usuário está desativado. Procure o administrador.", "danger")
                    return _login_response(403)
                if user["bloqueado"]:
                    log_auditoria(
                        "LOGIN_NEGADO_BLOQUEADO", "Tentativa de acesso com usuário bloqueado",
                        usuario_id=user["id"], usuario_nome=user["nome"],
                    )
                    flash("Este usuário está bloqueado. Procure o administrador.", "danger")
                    return _login_response(403)
                session.clear()
                session.permanent = True
                session["usuario_id"] = user["id"]
                session["usuario_nome"] = user["nome"]
                session["usuario_nivel"] = user["nivel"]
                session["usuario_perfil"] = user["perfil_nome"] or "Funcionário"
                session["_csrf_token"] = secrets.token_hex(24)
                db.execute("UPDATE usuarios SET ultimo_acesso=? WHERE id=?", (datetime.now().isoformat(timespec="seconds"), user["id"]))
                db.commit()
                try:
                    log_auditoria("LOGIN", f"Usuário {user['nome']} entrou no sistema")
                except Exception:
                    # Auditoria não pode deixar uma sessão autenticada presa em erro.
                    logging.exception("Falha ao registrar login na auditoria")
                if user["exigir_troca_senha"]:
                    flash("Defina uma nova senha antes de continuar.", "warning")
                    return _redirect_without_cache("alterar_senha")
                return _redirect_without_cache("dashboard")

            record_login_attempt(login_user)
            flash("Usuário ou senha incorretos.", "danger")
            return _login_response(401)

        except sqlite3.OperationalError:
            logging.exception("Servidor de autenticação indisponível")
            flash("Servidor de autenticação indisponível. Tente novamente em instantes.", "danger")
            return _login_response(503)
        except sqlite3.DatabaseError:
            logging.exception("Falha de conexão com o banco de autenticação")
            flash("Falha de conexão com o banco de dados. Tente novamente.", "danger")
            return _login_response(503)
        except Exception:
            logging.exception("Erro interno de autenticação")
            flash("Erro interno de autenticação. Tente novamente.", "danger")
            return _login_response(500)

    @app.route("/alterar-senha", methods=["GET", "POST"])
    @login_required
    def alterar_senha():
        if request.method == "POST":
            token = request.form.get("_csrf_token", "")
            expected = session.get("_csrf_token", "")
            if not token or not expected or not hmac.compare_digest(token, expected):
                flash("Sua sessão expirou. Atualize a página e tente novamente.", "danger")
                return render_template("alterar_senha.html", csrf_token=_get_or_create_csrf_token()), 400
            senha = request.form.get("senha", "")
            confirmacao = request.form.get("confirmacao", "")
            if len(senha) < 6:
                flash("A nova senha deve ter pelo menos 6 caracteres.", "danger")
            elif senha != confirmacao:
                flash("A confirmação da senha não confere.", "danger")
            else:
                db = get_db()
                db.execute(
                    """UPDATE usuarios
                       SET senha=?, exigir_troca_senha=0, senha_alterada_em=?
                       WHERE id=?""",
                    (generate_password_hash(senha), datetime.now().isoformat(timespec="seconds"), session["usuario_id"]),
                )
                db.commit()
                session["_csrf_token"] = secrets.token_hex(24)
                log_auditoria("ALTERAR_SENHA", "Usuário alterou a própria senha")
                flash("Senha alterada com segurança.", "success")
                return _redirect_without_cache("dashboard")
        return render_template("alterar_senha.html", csrf_token=_get_or_create_csrf_token())

    @app.route("/logout")
    def logout():
        usuario_id = session.get("usuario_id")
        usuario_nome = session.get("usuario_nome")
        try:
            if usuario_id:
                log_auditoria(
                    "LOGOUT",
                    f"Usuário {usuario_nome} saiu",
                    usuario_id=usuario_id,
                    usuario_nome=usuario_nome,
                )
        except Exception:
            logging.exception("Falha ao registrar logout na auditoria")
        finally:
            # Elimina todos os dados autenticados e substitui o cookie por uma
            # sessão anônima nova, com outro token de formulário.
            session.clear()
            session.permanent = False
            session["_csrf_token"] = secrets.token_hex(24)

        return _redirect_without_cache("login")
