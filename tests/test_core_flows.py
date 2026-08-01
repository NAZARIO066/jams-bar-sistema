import os
import re

from app import app
from database import get_db


def login_admin(client):
    response = client.get("/login")
    token = re.search(rb'name="_csrf_token"\s+value="([^"]+)"', response.data).group(1).decode()
    response = client.post(
        "/login",
        data={
            "login": os.environ["ADMIN_LOGIN"],
            "senha": os.environ["ADMIN_SENHA"],
            "_csrf_token": token,
        },
    )
    assert response.status_code == 302


def produto_com_estoque(client, minimo=5):
    produtos = client.get("/api/produtos").get_json()
    return next(produto for produto in produtos if produto["estoque"] >= minimo)


def abrir_comanda(client):
    mesa = next(mesa for mesa in client.get("/api/mesas").get_json() if mesa["status"] == "disponivel")
    response = client.post(f"/api/mesas/{mesa['id']}/abrir", json={"cliente_nome": "Teste"})
    assert response.status_code == 200
    return mesa, response.get_json()["comanda_id"]


def test_adicionar_e_remover_item_preserva_estoque(client):
    login_admin(client)
    produto = produto_com_estoque(client)
    _, comanda_id = abrir_comanda(client)
    estoque_inicial = produto["estoque"]

    response = client.post(
        f"/api/comanda/{comanda_id}/adicionar",
        json={"produto_id": produto["id"], "quantidade": 2},
    )
    assert response.status_code == 200
    estoque_reservado = client.get(f"/api/buscar_produto?codigo={produto['codigo_barras']}").get_json()["estoque"]
    assert estoque_reservado == estoque_inicial - 2

    item_id = client.get(f"/api/comanda/{comanda_id}").get_json()["itens"][0]["id"]
    response = client.delete(f"/api/comanda/item/{item_id}")
    assert response.status_code == 200
    estoque_final = client.get(f"/api/buscar_produto?codigo={produto['codigo_barras']}").get_json()["estoque"]
    assert estoque_final == estoque_inicial


def test_venda_direta_rejeita_quantidade_negativa(client):
    login_admin(client)
    produto = produto_com_estoque(client)
    response = client.post(
        "/api/venda/direta",
        json={
            "itens": [{"produto_id": produto["id"], "quantidade": -1}],
            "forma_pagamento": "Dinheiro",
        },
    )
    assert response.status_code == 400
    assert response.get_json()["ok"] is False


def test_pagamento_parcial_e_abatido_no_fechamento(client):
    login_admin(client)
    produto = produto_com_estoque(client)
    mesa, comanda_id = abrir_comanda(client)
    estoque_inicial = produto["estoque"]
    preco = produto["preco"]

    client.post(
        f"/api/comanda/{comanda_id}/adicionar",
        json={"produto_id": produto["id"], "quantidade": 2},
    )
    item_id = client.get(f"/api/comanda/{comanda_id}").get_json()["itens"][0]["id"]
    parcial = client.post(
        f"/api/comanda/{comanda_id}/pagamento_parcial",
        json={
            "itens": [{"item_id": item_id, "quantidade": 1}],
            "forma_pagamento": "PIX",
        },
    )
    assert parcial.status_code == 200
    assert parcial.get_json()["restante"] == preco

    fechamento = client.post(
        f"/api/mesas/{mesa['id']}/fechar",
        json={"desconto": 0, "forma_pagamento": "Dinheiro"},
    )
    dados = fechamento.get_json()
    assert fechamento.status_code == 200
    assert dados["pago_anteriormente"] == preco
    assert dados["valor_cobrado"] == preco
    assert dados["total"] == preco * 2
    estoque_final = client.get(f"/api/buscar_produto?codigo={produto['codigo_barras']}").get_json()["estoque"]
    assert estoque_final == estoque_inicial - 2


def test_cancelamento_de_venda_fiada_recalcula_saldo(client):
    login_admin(client)
    produto = produto_com_estoque(client)
    cliente = client.post(
        "/api/clientes",
        json={"nome": "Cliente Cancelamento", "limite_fiado": 1000},
    ).get_json()
    venda = client.post(
        "/api/venda/direta",
        json={
            "itens": [{"produto_id": produto["id"], "quantidade": 1}],
            "forma_pagamento": "Fiado",
            "cliente_id": cliente["id"],
            "dias_vencimento": 30,
        },
    ).get_json()
    assert venda["ok"] is True

    response = client.post(f"/api/venda/{venda['venda_id']}/cancelar")
    assert response.status_code == 200
    dados_cliente = client.get(f"/api/clientes/{cliente['id']}/fiado").get_json()
    assert dados_cliente["cliente"]["saldo_devedor"] == 0


def test_acesso_rapido_prioriza_cigarros_e_doses(client):
    login_admin(client)
    client.post(
        "/api/produtos",
        json={"nome": "CIGARRO TESTE RÁPIDO", "preco": 2, "estoque": 10, "unidade": "UN"},
    )
    client.post(
        "/api/produtos",
        json={"nome": "DOSE TESTE RÁPIDO", "preco": 5, "estoque": 10, "unidade": "UN"},
    )

    produtos = client.get("/api/produtos/mais_vendidos").get_json()
    grupos = [produto["destaque"] for produto in produtos]
    primeiro_comum = next((i for i, grupo in enumerate(grupos) if grupo is None), len(grupos))

    assert "cigarro" in grupos
    assert "dose" in grupos
    assert all(grupo in ("cigarro", "dose") for grupo in grupos[:primeiro_comum])
    assert grupos.index("cigarro") < grupos.index("dose")


def test_comprovantes_cobrem_comanda_parcial_fechamento_e_venda(client):
    login_admin(client)
    produto = produto_com_estoque(client, minimo=8)
    mesa, comanda_id = abrir_comanda(client)
    client.post(
        f"/api/comanda/{comanda_id}/adicionar",
        json={"produto_id": produto["id"], "quantidade": 2},
    )

    comanda = client.get(f"/imprimir/comanda/{comanda_id}?autoprint=0")
    assert comanda.status_code == 200
    assert b"print-helper.js" in comanda.data
    assert re.search(rb"R\$ \d+,\d{2}", comanda.data)

    item_id = client.get(f"/api/comanda/{comanda_id}").get_json()["itens"][0]["id"]
    parcial = client.post(
        f"/api/comanda/{comanda_id}/pagamento_parcial",
        json={
            "itens": [{"item_id": item_id, "quantidade": 1}],
            "forma_pagamento": "PIX",
        },
    )
    pagamento_id = parcial.get_json()["pagamento_id"]
    comprovante_parcial = client.get(f"/imprimir/parcial/{pagamento_id}?autoprint=0")
    assert comprovante_parcial.status_code == 200
    assert b"PAGAMENTO PARCIAL" in comprovante_parcial.data
    assert b"print-helper.js" in comprovante_parcial.data

    fechamento = client.post(
        f"/api/mesas/{mesa['id']}/fechar",
        json={"desconto": 0, "forma_pagamento": "Dinheiro"},
    )
    assert fechamento.status_code == 200
    comprovante_mesa = client.get(f"/imprimir/mesa/{comanda_id}?autoprint=0")
    assert comprovante_mesa.status_code == 200
    assert b"FECHAMENTO DE MESA" in comprovante_mesa.data

    venda = client.post(
        "/api/venda/direta",
        json={
            "itens": [{"produto_id": produto["id"], "quantidade": 1}],
            "desconto": 0.5,
            "forma_pagamento": "Dinheiro",
        },
    )
    assert venda.status_code == 200
    comprovante_venda = client.get(
        f"/imprimir/venda/{venda.get_json()['venda_id']}?autoprint=0"
    )
    assert comprovante_venda.status_code == 200
    assert b"COMPROVANTE DE VENDA" in comprovante_venda.data
    assert b"Desconto" in comprovante_venda.data
    assert b"print-helper.js" in comprovante_venda.data


def test_tempo_de_mesa_nunca_fica_negativo(client):
    login_admin(client)
    mesa, comanda_id = abrir_comanda(client)
    with app.app_context():
        db = get_db()
        db.execute(
            "UPDATE comandas SET abertura=datetime('now', '+2 hours') WHERE id=?",
            (comanda_id,),
        )
        db.commit()
    atualizada = next(
        item for item in client.get("/api/mesas").get_json()
        if item["id"] == mesa["id"]
    )
    assert atualizada["tempo"] == "00min"
