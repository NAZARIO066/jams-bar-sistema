from datetime import datetime, timedelta
from flask import abort, flash, jsonify, redirect, request, session, g, url_for
from functools import wraps
from database import get_db
from permissions import get_user_with_profile, has_permission, is_admin

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
            return redirect(url_for("login"))
        user = _active_session_user()
        if user is None:
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "erro": "Sua sessão não está mais ativa. Entre novamente."}), 401
            flash("Sua sessão não está mais ativa. Entre novamente.", "danger")
            return redirect(url_for("login"))
        if user["exigir_troca_senha"] and request.endpoint not in {"alterar_senha", "logout"}:
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "erro": "Troca de senha obrigatória antes de continuar."}), 403
            return redirect(url_for("alterar_senha"))
        return view(*args, **kwargs)
    return wrapped


def _active_session_user():
    """Valida em cada requisição para aplicar bloqueios sem exigir novo login."""
    cached = getattr(g, "current_user", None)
    if cached is not None:
        return cached
    user_id = session.get("usuario_id")
    if not user_id:
        return None
    user = get_user_with_profile(user_id)
    if not user or not user["ativo"] or user["bloqueado"]:
        try:
            if user:
                log_auditoria(
                    "SESSAO_BLOQUEADA",
                    "Sessão encerrada porque o usuário foi desativado ou bloqueado",
                    usuario_id=user["id"],
                    usuario_nome=user["nome"],
                )
        finally:
            session.clear()
        return None
    g.current_user = user
    session["usuario_nome"] = user["nome"]
    session["usuario_nivel"] = user["nivel"]
    session["usuario_perfil"] = user["perfil_nome"] or "Funcionário"
    return user


def _deny_permission(required):
    keys = ", ".join(required)
    try:
        log_auditoria(
            "ACESSO_NEGADO",
            f"Permissão necessária: {keys}; rota: {request.method} {request.path}",
        )
    except Exception:
        pass
    message = "Você não tem permissão para acessar ou executar esta ação."
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "erro": message, "codigo": "ACESSO_NEGADO"}), 403
    abort(403, description=message)


def permission_required(*permissions, any_of=False):
    """Exige todas as permissões informadas, ou qualquer uma com any_of=True."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "usuario_id" not in session:
                return redirect(url_for("login"))
            user = _active_session_user()
            if user is None:
                if request.path.startswith("/api/"):
                    return jsonify({"ok": False, "erro": "Sua sessão não está mais ativa. Entre novamente."}), 401
                return redirect(url_for("login"))
            if user["exigir_troca_senha"] and request.endpoint not in {"alterar_senha", "logout"}:
                if request.path.startswith("/api/"):
                    return jsonify({"ok": False, "erro": "Troca de senha obrigatória antes de continuar."}), 403
                return redirect(url_for("alterar_senha"))
            checks = [has_permission(key) for key in permissions]
            allowed = any(checks) if any_of else all(checks)
            if not allowed:
                return _deny_permission(permissions)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def any_permission_required(*permissions):
    return permission_required(*permissions, any_of=True)


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect(url_for("login"))
        user = _active_session_user()
        if user is None:
            return redirect(url_for("login"))
        if not is_admin(user):
            return _deny_permission(("administrador",))
        return view(*args, **kwargs)
    return wrapped

