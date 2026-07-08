import os, sys, re, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["FLASK_DEBUG"] = "0"

import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _login(client, login="admin", senha="Admin@2026#Jam's"):
    r = client.get("/login")
    match = re.search(rb'value="([a-f0-9]+)"', r.data)
    assert match, "CSRF token not found"
    csrf = match.group(1).decode()
    r = client.post("/login", data={"login": login, "senha": senha, "_csrf_token": csrf}, follow_redirects=True)
    assert r.status_code == 200
    return csrf


class TestAuth:
    def test_login_page_loads(self, client):
        r = client.get("/login")
        assert r.status_code == 200
        assert b"JAM'S" in r.data or b"csrf_token" in r.data

    def test_csrf_protection(self, client):
        r = client.post("/login", data={"login": "admin", "senha": "x", "_csrf_token": "invalid"})
        assert r.status_code == 400

    def test_login_success(self, client):
        _login(client)

    def test_logout(self, client):
        _login(client)
        r = client.get("/logout", follow_redirects=True)
        assert r.status_code == 200
        assert b"login" in r.data or b"USUARIO" in r.data


class TestAPI:
    def test_dashboard_api(self, client):
        _login(client)
        r = client.get("/api/dashboard")
        assert r.status_code == 200
        d = r.get_json()
        assert "faturamento_dia" in d

    def test_clientes_list(self, client):
        _login(client)
        r = client.get("/api/clientes")
        assert r.status_code == 200
        body = r.get_json()
        if isinstance(body, dict):
            assert "data" in body and "total" in body
            assert len(body["data"]) > 0
        else:
            assert isinstance(body, list)

    def test_mesas_list(self, client):
        _login(client)
        r = client.get("/api/mesas")
        assert r.status_code == 200
        mesas = r.get_json()
        assert isinstance(mesas, list)
        assert len(mesas) >= 20

    def test_produtos_list(self, client):
        _login(client)
        r = client.get("/api/produtos")
        assert r.status_code == 200
        prods = r.get_json()
        assert isinstance(prods, list)

    def test_categorias_list(self, client):
        _login(client)
        r = client.get("/api/categorias")
        assert r.status_code == 200
        cats = r.get_json()
        assert isinstance(cats, list)

    def test_garcons_list(self, client):
        _login(client)
        r = client.get("/api/garcons")
        assert r.status_code == 200
        gs = r.get_json()
        assert isinstance(gs, list)

    def test_estoque_list(self, client):
        _login(client)
        r = client.get("/api/estoque")
        assert r.status_code == 200
        est = r.get_json()
        assert isinstance(est, list)

    def test_alertas(self, client):
        _login(client)
        r = client.get("/api/alertas")
        assert r.status_code == 200
        d = r.get_json()
        assert "criticos" in d and "zerados" in d

    def test_contas_pagar(self, client):
        _login(client)
        r = client.get("/api/contas_pagar")
        assert r.status_code == 200
        c = r.get_json()
        assert isinstance(c, list)

    def test_movimentacoes(self, client):
        _login(client)
        r = client.get("/api/movimentacoes")
        assert r.status_code == 200
        m = r.get_json()
        assert isinstance(m, list)

    def test_auditoria(self, client):
        _login(client)
        r = client.get("/api/auditoria")
        assert r.status_code == 200
        a = r.get_json()
        assert isinstance(a, list)

    def test_caixa_status(self, client):
        _login(client)
        r = client.get("/api/caixa/status")
        assert r.status_code == 200
        s = r.get_json()
        assert "aberto" in s

    def test_buscar_produto(self, client):
        _login(client)
        r = client.get("/api/buscar_produto?q=Heineken")
        assert r.status_code == 200
        p = r.get_json()
        assert isinstance(p, list)

    def test_buscar_produto_codigo(self, client):
        _login(client)
        r = client.get("/api/buscar_produto?codigo=7891991010924")
        assert r.status_code == 200
        p = r.get_json()
        assert isinstance(p, dict)


class TestAdminEndpoints:
    def test_usuarios_list(self, client):
        _login(client)
        r = client.get("/api/usuarios")
        assert r.status_code == 200
        u = r.get_json()
        assert isinstance(u, list)
        assert len(u) >= 2


class TestRelatorios:
    def test_rel_vendas(self, client):
        _login(client)
        r = client.get("/api/relatorios/vendas?inicio=2026-01-01&fim=2026-12-31")
        assert r.status_code == 200
        d = r.get_json()
        assert "vendas" in d and "totais" in d

    def test_rel_mesas(self, client):
        _login(client)
        r = client.get("/api/relatorios/mesas")
        assert r.status_code == 200
        m = r.get_json()
        assert isinstance(m, list)

    def test_rel_produtos(self, client):
        _login(client)
        r = client.get("/api/relatorios/produtos")
        assert r.status_code == 200
        p = r.get_json()
        assert "mais_vendidos" in p

    def test_rel_fluxo_caixa(self, client):
        _login(client)
        r = client.get("/api/relatorios/fluxo_caixa?inicio=2026-01-01&fim=2026-12-31")
        assert r.status_code == 200
        f = r.get_json()
        assert "vendas" in f and "sangrias" in f and "suprimentos" in f

    def test_rel_garcom(self, client):
        _login(client)
        r = client.get("/api/relatorios/vendas_garcom?inicio=2026-01-01&fim=2026-12-31")
        assert r.status_code == 200
        g = r.get_json()
        assert isinstance(g, list)

    def test_rel_categoria(self, client):
        _login(client)
        r = client.get("/api/relatorios/vendas_categoria?inicio=2026-01-01&fim=2026-12-31")
        assert r.status_code == 200
        c = r.get_json()
        assert isinstance(c, list)


class TestRoutes:
    def test_pages_load(self, client):
        _login(client)
        pages = ["/", "/mesas", "/vendas", "/produtos", "/estoque", "/caixa",
                 "/clientes", "/relatorios", "/garcons", "/contas_pagar",
                 "/usuarios", "/auditoria"]
        for p in pages:
            r = client.get(p)
            assert r.status_code in (200, 302), f"{p} returned {r.status_code}"
