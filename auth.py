from datetime import datetime, timedelta
from flask import request, session, g
from functools import wraps
from database import get_db
import threading

def check_login_rate_limit(login):
    db = get_db()
    limiar = (datetime.now() - timedelta(minutes=5)).isoformat()
    count = db.execute(
        "SELECT COUNT(*) as c FROM login_attempts WHERE login=? AND criado_em>=?",
        (login, limiar)
    ).fetchone()["c"]
    return count < 5

def record_login_attempt(login):
    db = get_db()
    db.execute("INSERT INTO login_attempts (login) VALUES (?)", (login,))
    db.commit()
    limiar = (datetime.now() - timedelta(minutes=5)).isoformat()
    db.execute("DELETE FROM login_attempts WHERE login=? AND criado_em<?", (login, limiar))
    db.commit()

def log_auditoria(acao, detalhes=None, usuario_id=None, usuario_nome=None):
    db = get_db()
    uid = usuario_id or session.get("usuario_id")
    unome = usuario_nome or session.get("usuario_nome")
    db.execute(
        "INSERT INTO auditoria (usuario_id, usuario_nome, acao, detalhes, ip, user_agent) VALUES (?,?,?,?,?,?)",
        (uid, unome, acao, detalhes, request.remote_addr if request else None,
         (request.user_agent.string[:200] if request and request.user_agent else None))
    )
    db.commit()

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "usuario_id" not in session:
            from flask import redirect, url_for
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "usuario_id" not in session:
            from flask import redirect, url_for
            return redirect(url_for("login"))
        if session.get("usuario_nivel") != "admin":
            from flask import abort
            abort(403)
        return view(*args, **kwargs)
    return wrapped

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
