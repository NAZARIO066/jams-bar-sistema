from migration.import_adega_firebird import validate_source


def test_validacao_datacaixa_aceita_contagens_de_backup_futuro():
    data = {
        "categorias": [{"ID_GRUPO_PRODUTO": 1}],
        "produtos": [{"ID_PRODUTO": 1}],
        "clientes": [{"ID_HOSPEDE": 1}],
        "vendas": [{"ID_VENDA": 99}],
        "itens_venda": [{"ID_VENDA_ITEM": 5, "ID_PRODUTO": 1, "ID_VENDA": 99}],
        "creditos": [{"ID_CREDITO": 7, "ID_HOSPEDE": 1}],
        "funcionarios": [],
        "mesas": [],
        "caixas": [],
        "pedidos_abertos": [],
        "hotel": [{"ID_HOTEL": 1}],
        "compras_count": 0,
        "estoque_saidas_count": 0,
    }

    counts = validate_source(data)

    assert counts["produtos"] == 1
    assert counts["vendas"] == 1
    assert counts["itens_venda"] == 1
