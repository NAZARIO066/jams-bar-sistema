import secrets
from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from database import get_db
from auth import log_auditoria, check_login_rate_limit, record_login_attempt


def register_auth_routes(app):

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            csrf_token = request.form.get("_csrf_token", "")
            if not csrf_token or csrf_token != session.get("_csrf_token"):
                flash("Sessão inválida. Tente novamente.", "danger")
                return render_template("login.html"), 400
            login_user = request.form.get("login", "").strip()
            senha = request.form.get("senha", "")
            if not check_login_rate_limit(login_user):
                log_auditoria("LOGIN_BLOQUEADO", f"Tentativas excessivas para {login_user}")
                flash("Muitas tentativas. Aguarde 5 minutos.", "danger")
                return render_template("login.html"), 429
            db = get_db()
            user = db.execute("SELECT * FROM usuarios WHERE login=? AND ativo=1", (login_user,)).fetchone()
            if user and check_password_hash(user["senha"], senha):
                record_login_attempt(login_user)
                session.permanent = True
                session["usuario_id"] = user["id"]
                session["usuario_nome"] = user["nome"]
                session["usuario_nivel"] = user["nivel"]
                log_auditoria("LOGIN", f"Usuário {user['nome']} entrou no sistema")
                return redirect(url_for("dashboard"))
            record_login_attempt(login_user)
            flash("Login ou senha inválidos", "danger")
        session["_csrf_token"] = secrets.token_hex(16)
        return render_template("login.html", csrf_token=session["_csrf_token"])

    @app.route("/logout")
    def logout():
        log_auditoria("LOGOUT", f"Usuário {session.get('usuario_nome')} saiu")
        session.clear()
        return redirect(url_for("login"))
