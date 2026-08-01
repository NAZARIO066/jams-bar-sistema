import os
import sqlite3

from werkzeug.security import generate_password_hash

from app import app


def _csrf_from(response):
    html = response.get_data(as_text=True)
    marker = 'name="_csrf_token" value="'
    return html.split(marker, 1)[1].split('"', 1)[0]


def _login(client, login=None, password=None):
    token = _csrf_from(client.get("/login"))
    return client.post(
        "/login",
        data={
            "login": login or os.environ["ADMIN_LOGIN"],
            "senha": password or os.environ["ADMIN_SENHA"],
            "_csrf_token": token,
        },
        follow_redirects=False,
    )


def _db():
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    return conn


def _create_user(client, profile_name="Atendente", login="teste_perfil", password="senha123", **flags):
    client.get("/login")
    conn = _db()
    profile_id = conn.execute("SELECT id FROM perfis_acesso WHERE nome=?", (profile_name,)).fetchone()["id"]
    cursor = conn.execute(
        """INSERT INTO usuarios
           (nome, login, senha, nivel, perfil_id, ativo, bloqueado, exigir_troca_senha)
           VALUES (?,?,?,?,?,?,?,?)""",
        (
            "Funcionário de Teste", login, generate_password_hash(password),
            "funcionario", profile_id, int(flags.get("ativo", 1)),
            int(flags.get("bloqueado", 0)), int(flags.get("exigir_troca_senha", 0)),
        ),
    )
    conn.commit()
    conn.close()
    return cursor.lastrowid


def test_seed_cria_cinco_perfis_e_permissoes(client):
    client.get("/login")
    conn = _db()
    profiles = {row[0] for row in conn.execute("SELECT nome FROM perfis_acesso")}
    permission_count = conn.execute("SELECT COUNT(*) FROM permissoes").fetchone()[0]
    conn.close()
    assert {"Administrador", "Gerente", "Caixa", "Atendente", "Estoquista"} <= profiles
    assert permission_count >= 30


def test_administrador_tem_todas_as_permissoes(client):
    assert _login(client).status_code == 302
    data = client.get("/api/perfis-permissoes").get_json()
    admin = next(profile for profile in data["perfis"] if profile["nome"] == "Administrador")
    assert set(data["padroes"][str(admin["id"])]) == {item["chave"] for item in data["permissoes"]}


def test_atendente_nao_ve_menu_financeiro_ou_administrativo(client):
    _create_user(client, login="atendente_menu")
    assert _login(client, "atendente_menu", "senha123").status_code == 302
    html = client.get("/").get_data(as_text=True)
    assert "PDV / Vendas" in html
    assert "Mesas" in html
    assert "Contas a Pagar" not in html
    assert "Usuários e Acessos" not in html


def test_acesso_direto_url_sem_permissao_retorna_403(client):
    _create_user(client, login="atendente_url")
    _login(client, "atendente_url", "senha123")
    assert client.get("/relatorios").status_code == 403
    assert "não tem permissão" in client.get("/usuarios").get_data(as_text=True)


def test_api_sem_permissao_retorna_json_403(client):
    _create_user(client, login="atendente_api")
    _login(client, "atendente_api", "senha123")
    response = client.get("/api/estoque")
    assert response.status_code == 403
    assert response.get_json()["codigo"] == "ACESSO_NEGADO"


def test_tentativa_negada_e_auditada(client):
    _create_user(client, login="atendente_audit")
    _login(client, "atendente_audit", "senha123")
    client.get("/api/estoque")
    conn = _db()
    row = conn.execute("SELECT acao, detalhes FROM auditoria ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    assert row["acao"] == "ACESSO_NEGADO"
    assert "estoque.visualizar" in row["detalhes"]


def test_caixa_acessa_pdv_mas_nao_relatorios(client):
    _create_user(client, profile_name="Caixa", login="caixa_teste")
    _login(client, "caixa_teste", "senha123")
    assert client.get("/vendas").status_code == 200
    assert client.get("/relatorios").status_code == 403


def test_estoquista_acessa_estoque_mas_nao_pdv(client):
    _create_user(client, profile_name="Estoquista", login="estoquista_teste")
    _login(client, "estoquista_teste", "senha123")
    assert client.get("/estoque").status_code == 200
    assert client.get("/vendas").status_code == 403


def test_estoque_tem_painel_de_prioridade_e_filtros_rapidos(client):
    assert _login(client).status_code == 302
    html = client.get("/estoque").get_data(as_text=True)
    assert "Atenção agora" in html
    assert "Saldo negativo" in html
    assert "Saúde do estoque" in html
    assert "Precisa repor" in html
    assert "Abaixo do mínimo" in html
    assert "Buscar produto, categoria ou código" in html
    assert "filtroStatus = 'atencao'" in html
    assert "abrirMov('entrada'," in html


def test_dashboard_oculta_valores_financeiros_do_atendente(client):
    _create_user(client, login="atendente_dash")
    _login(client, "atendente_dash", "senha123")
    data = client.get("/api/dashboard").get_json()
    assert data["pode_ver_financeiro"] is False
    assert data["faturamento_dia"] is None
    assert data["ticket_medio"] is None
    assert all("total" not in item for item in data["produtos_top"])


def test_admin_cria_usuario_com_permissoes_personalizadas(client):
    _login(client)
    config = client.get("/api/perfis-permissoes").get_json()
    attendant = next(profile for profile in config["perfis"] if profile["nome"] == "Atendente")
    selected = set(config["padroes"][str(attendant["id"])]) | {"estoque.visualizar"}
    response = client.post("/api/usuarios", json={
        "nome": "Acesso Personalizado", "login": "custom_access", "senha": "senha123",
        "perfil_id": attendant["id"], "ativo": True, "bloqueado": False,
        "exigir_troca_senha": False, "permissoes": sorted(selected),
    })
    assert response.status_code == 200
    client.get("/logout")
    _login(client, "custom_access", "senha123")
    assert client.get("/estoque").status_code == 200


def test_permissao_personalizada_persiste_apos_novo_login(client):
    _login(client)
    config = client.get("/api/perfis-permissoes").get_json()
    cashier = next(profile for profile in config["perfis"] if profile["nome"] == "Caixa")
    selected = set(config["padroes"][str(cashier["id"])]) | {"estoque.visualizar"}
    created = client.post("/api/usuarios", json={
        "nome": "Caixa Estoque", "login": "cash_stock", "senha": "senha123",
        "perfil_id": cashier["id"], "permissoes": sorted(selected),
    }).get_json()
    assert created["ok"]
    client.get("/logout")
    for _ in range(2):
        _login(client, "cash_stock", "senha123")
        assert client.get("/estoque").status_code == 200
        client.get("/logout")


def test_funcionario_nao_pode_alterar_proprias_permissoes(client):
    user_id = _create_user(client, profile_name="Gerente", login="gerente_self")
    conn = _db()
    conn.execute(
        "INSERT INTO usuario_permissoes (usuario_id, permissao_chave, permitido) VALUES (?,?,1)",
        (user_id, "usuarios.criar"),
    )
    conn.execute(
        "INSERT INTO usuario_permissoes (usuario_id, permissao_chave, permitido) VALUES (?,?,1)",
        (user_id, "permissoes.alterar"),
    )
    profile_id = conn.execute("SELECT perfil_id FROM usuarios WHERE id=?", (user_id,)).fetchone()[0]
    conn.commit()
    conn.close()
    _login(client, "gerente_self", "senha123")
    response = client.put(f"/api/usuarios/{user_id}", json={
        "nome": "Funcionário de Teste", "login": "gerente_self", "perfil_id": profile_id,
        "ativo": True, "bloqueado": False, "permissoes": ["permissoes.alterar"],
    })
    assert response.status_code == 403


def test_usuario_bloqueado_nao_entra(client):
    _create_user(client, login="bloqueado_login", bloqueado=1)
    response = _login(client, "bloqueado_login", "senha123")
    assert response.status_code == 403
    assert "bloqueado" in response.get_data(as_text=True).lower()


def test_usuario_inativo_nao_entra(client):
    _create_user(client, login="inativo_login", ativo=0)
    response = _login(client, "inativo_login", "senha123")
    assert response.status_code == 403
    assert "desativado" in response.get_data(as_text=True).lower()


def test_bloqueio_durante_sessao_e_imediato(client):
    user_id = _create_user(client, login="bloqueio_imediato")
    _login(client, "bloqueio_imediato", "senha123")
    conn = _db()
    conn.execute("UPDATE usuarios SET bloqueado=1 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    response = client.get("/api/dashboard")
    assert response.status_code == 401
    with client.session_transaction() as session:
        assert "usuario_id" not in session


def test_ultimo_acesso_e_atualizado_no_login(client):
    user_id = _create_user(client, login="ultimo_acesso")
    _login(client, "ultimo_acesso", "senha123")
    conn = _db()
    last_access = conn.execute("SELECT ultimo_acesso FROM usuarios WHERE id=?", (user_id,)).fetchone()[0]
    conn.close()
    assert last_access


def test_troca_obrigatoria_bloqueia_outros_fluxos(client):
    _create_user(client, login="troca_obrigatoria", exigir_troca_senha=1)
    response = _login(client, "troca_obrigatoria", "senha123")
    assert response.headers["Location"].endswith("/alterar-senha")
    assert client.get("/vendas").headers["Location"].endswith("/alterar-senha")


def test_troca_obrigatoria_salva_nova_senha(client):
    _create_user(client, login="troca_senha", exigir_troca_senha=1)
    _login(client, "troca_senha", "senha123")
    page = client.get("/alterar-senha")
    token = _csrf_from(page)
    response = client.post("/alterar-senha", data={
        "_csrf_token": token, "senha": "novaSenha456", "confirmacao": "novaSenha456",
    })
    assert response.status_code == 302
    client.get("/logout")
    assert _login(client, "troca_senha", "novaSenha456").status_code == 302


def test_nao_permite_desativar_proprio_admin(client):
    _login(client)
    users = client.get("/api/usuarios").get_json()
    current = next(user for user in users if user["nivel"] == "admin" and user["ativo"])
    response = client.put(f"/api/usuarios/{current['id']}", json={
        "nome": current["nome"], "login": current["login"], "perfil_id": current["perfil_id"],
        "ativo": False, "bloqueado": False, "permissoes": current["permissoes"],
    })
    assert response.status_code == 400


def test_grupos_rapidos_usam_produtos_cadastrados(client):
    _login(client)
    conn = _db()
    conn.executemany(
        "INSERT INTO produtos (nome, preco, estoque, unidade, ativo) VALUES (?,?,?,?,1)",
        [
            ("CIGARRO TESTE SOLTO", 2.5, 10, "UN"),
            ("DOSE TESTE ESPECIAL", 8.0, 7, "UN"),
            ("FICHA BILHAR / SINUCA TESTE", 2.0, 12, "UN"),
            ("ITEM TESTE POR PESO", 24.0, 4, "KG"),
        ],
    )
    conn.commit()
    conn.close()
    groups = client.get("/api/produtos/grupos-acesso-rapido").get_json()
    by_slug = {group["slug"]: group for group in groups}
    assert {"cigarros-soltos", "doses", "fichas-jogos", "fracionados"} <= set(by_slug)
    assert any(item["nome"] == "CIGARRO TESTE SOLTO" and item["preco"] == 2.5 for item in by_slug["cigarros-soltos"]["produtos"])
    assert any(item["nome"] == "DOSE TESTE ESPECIAL" and item["preco"] == 8.0 for item in by_slug["doses"]["produtos"])
    assert any(item["nome"] == "FICHA BILHAR / SINUCA TESTE" for item in by_slug["fichas-jogos"]["produtos"])


def test_venda_fracionada_calcula_e_baixa_estoque(client):
    _login(client)
    conn = _db()
    product_id = conn.execute(
        "INSERT INTO produtos (nome, preco, estoque, unidade, ativo) VALUES (?,?,?,?,1)",
        ("Produto Fracionado Teste", 20.0, 5.0, "L"),
    ).lastrowid
    conn.commit()
    conn.close()
    response = client.post("/api/venda/direta", json={
        "itens": [{"produto_id": product_id, "quantidade": 0.5}],
        "desconto": 0, "acrescimo": 0, "forma_pagamento": "PIX",
    })
    data = response.get_json()
    assert response.status_code == 200
    assert data["total"] == 10.0
    conn = _db()
    stock = conn.execute("SELECT estoque FROM produtos WHERE id=?", (product_id,)).fetchone()[0]
    quantity = conn.execute("SELECT quantidade FROM itens_venda WHERE venda_id=?", (data["venda_id"],)).fetchone()[0]
    movement = conn.execute("SELECT quantidade FROM movimentacoes WHERE produto_id=? ORDER BY id DESC LIMIT 1", (product_id,)).fetchone()[0]
    conn.close()
    assert stock == 4.5
    assert quantity == 0.5
    assert movement == 0.5


def test_desconto_sem_permissao_e_bloqueado_no_backend(client):
    _create_user(client, login="sem_desconto")
    _login(client, "sem_desconto", "senha123")
    conn = _db()
    product_id = conn.execute(
        "INSERT INTO produtos (nome, preco, estoque, unidade, ativo) VALUES (?,?,?,?,1)",
        ("Produto Desconto Teste", 10.0, 5.0, "UN"),
    ).lastrowid
    conn.commit()
    conn.close()
    response = client.post("/api/venda/direta", json={
        "itens": [{"produto_id": product_id, "quantidade": 1}],
        "desconto": 1, "forma_pagamento": "PIX",
    })
    assert response.status_code == 403
    assert "permissão" in response.get_json()["erro"]


def test_css_garante_icones_sem_interceptar_clique(client):
    css = client.get("/static/css/clean-theme.css").get_data(as_text=True)
    assert "button svg, button svg *" in css
    assert "touch-action: manipulation" in css


def test_pdv_prioriza_lista_rapida_sem_imagens(client):
    _login(client)
    html = client.get("/vendas").get_data(as_text=True)
    assert html.index('id="acesso-rapido"') < html.index('id="categorias"')
    assert 'class="catalog-drawer"' in html
    assert 'class="product-list"' in html
    assert "product-card-image" not in html


def test_login_tem_composicao_de_bebidas_formulario_e_lanche(client):
    html = client.get("/login").get_data(as_text=True)
    assert "tela-sistema-fernando.jpeg" in html
    assert "login-hero.png" in html
    assert "burger-cover" in html
    assert "brand-logo" in html
