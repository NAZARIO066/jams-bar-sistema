import os
import re
import sqlite3

import routes.auth_routes as auth_routes


def _csrf_from(response):
    match = re.search(rb'name="_csrf_token"\s+value="([^"]+)"', response.data)
    assert match, "A resposta de login deve sempre conter um token de segurança válido"
    return match.group(1).decode()


def _login(client, token=None, senha=None):
    if token is None:
        token = _csrf_from(client.get("/login"))
    return client.post(
        "/login",
        data={
            "login": os.environ["ADMIN_LOGIN"],
            "senha": senha if senha is not None else os.environ["ADMIN_SENHA"],
            "_csrf_token": token,
        },
        follow_redirects=False,
    )


def test_token_de_login_permanece_estavel_entre_abas(client):
    primeiro_token = _csrf_from(client.get("/login"))
    segundo_token = _csrf_from(client.get("/login"))

    assert primeiro_token == segundo_token
    assert _login(client, primeiro_token).status_code == 302


def test_login_logout_e_novo_login_funcionam_repetidamente(client):
    for _ in range(6):
        login = _login(client)
        assert login.status_code == 302
        assert login.headers["Location"].endswith("/")
        assert client.get("/").status_code == 200

        logout = client.get("/logout", follow_redirects=False)
        assert logout.status_code == 302
        assert logout.headers["Location"].endswith("/login")

        with client.session_transaction() as sess:
            assert "usuario_id" not in sess
            assert "usuario_nome" not in sess
            assert "usuario_nivel" not in sess
            assert sess.get("_csrf_token")


def test_token_expirado_devolve_mensagem_e_formulario_utilizavel(client):
    token_antigo = _csrf_from(client.get("/login"))
    with client.session_transaction() as sess:
        sess.clear()
        sess["_csrf_token"] = "outro-token-valido"

    expirado = _login(client, token_antigo)
    assert expirado.status_code == 400
    assert "Sua sessão expirou" in expirado.get_data(as_text=True)

    token_novo = _csrf_from(expirado)
    assert token_novo != token_antigo
    assert _login(client, token_novo).status_code == 302


def test_credenciais_incorretas_recebem_mensagem_correta(client):
    resposta = _login(client, senha="senha-incorreta")

    assert resposta.status_code == 401
    assert "Usuário ou senha incorretos." in resposta.get_data(as_text=True)
    _csrf_from(resposta)


def test_servidor_de_autenticacao_indisponivel_recebe_mensagem_correta(client, monkeypatch):
    monkeypatch.setattr(
        auth_routes,
        "check_login_rate_limit",
        lambda _login: (_ for _ in ()).throw(sqlite3.OperationalError("offline")),
    )

    resposta = _login(client)
    assert resposta.status_code == 503
    assert "Servidor de autenticação indisponível" in resposta.get_data(as_text=True)
    _csrf_from(resposta)


def test_falha_de_conexao_com_banco_recebe_mensagem_correta(client, monkeypatch):
    monkeypatch.setattr(
        auth_routes,
        "check_login_rate_limit",
        lambda _login: (_ for _ in ()).throw(sqlite3.DatabaseError("connection failed")),
    )

    resposta = _login(client)
    assert resposta.status_code == 503
    assert "Falha de conexão com o banco de dados" in resposta.get_data(as_text=True)
    _csrf_from(resposta)


def test_erro_interno_de_autenticacao_recebe_mensagem_correta(client, monkeypatch):
    monkeypatch.setattr(
        auth_routes,
        "check_login_rate_limit",
        lambda _login: (_ for _ in ()).throw(RuntimeError("unexpected")),
    )

    resposta = _login(client)
    assert resposta.status_code == 500
    assert "Erro interno de autenticação" in resposta.get_data(as_text=True)
    _csrf_from(resposta)


def test_falha_de_auditoria_nao_impede_logout_ou_novo_login(client, monkeypatch):
    assert _login(client).status_code == 302

    def falhar_auditoria(*_args, **_kwargs):
        raise sqlite3.OperationalError("audit offline")

    monkeypatch.setattr(auth_routes, "log_auditoria", falhar_auditoria)
    assert client.get("/logout", follow_redirects=False).status_code == 302

    with client.session_transaction() as sess:
        assert "usuario_id" not in sess

    # Restaura somente a auditoria para validar uma autenticação normal nova.
    monkeypatch.undo()
    assert _login(client).status_code == 302
