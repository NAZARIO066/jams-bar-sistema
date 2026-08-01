"""Importa os dados reais da adega (Firebird) para o banco SQLite atual.

O importador preserva os usuários locais de acesso, substitui os dados
operacionais e executa toda a escrita do SQLite em uma única transação.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from collections import defaultdict
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

import fdb
from werkzeug.security import generate_password_hash


EXPECTED_SOURCE_COUNTS = {
    "categorias": 9,
    "produtos": 265,
    "clientes": 81,
    "vendas": 26058,
    "itens_venda": 45520,
    "creditos": 2356,
    "compras": 1604,
    "estoque_saidas": 440,
    "funcionarios": 10,
    "mesas": 40,
    "caixas": 732,
    "pedidos_abertos": 18,
}


def as_text(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "read"):
        value = value.read()
    if isinstance(value, bytes):
        value = value.decode("cp1252", errors="replace")
    return str(value).strip()


def as_float(value) -> float:
    if value is None:
        return 0.0
    return round(float(value), 6)


def combine_datetime(day, clock=None, preferred=None):
    if isinstance(preferred, datetime):
        return preferred.isoformat(sep=" ")
    if isinstance(day, datetime):
        return day.isoformat(sep=" ")
    if isinstance(day, date):
        clock = clock if isinstance(clock, time) else time.min
        return datetime.combine(day, clock).isoformat(sep=" ")
    return None


def compact_join(*parts) -> str:
    return ", ".join(part for part in (as_text(p) for p in parts) if part)


def fetch_dicts(cursor, sql: str, params=()):
    cursor.execute(sql, params)
    columns = [item[0].strip() for item in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def safe_login(value: str, source_id: int) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", as_text(value).lower()).strip("_") or "usuario"
    return f"legado_fdb_{base}_{source_id}"


def load_source(source: Path, fbclient: Path):
    fdb.load_api(str(fbclient))
    connection = fdb.connect(
        dsn=str(source), user="SYSDBA", password="masterkey", charset="WIN1252"
    )
    cursor = connection.cursor()
    try:
        data = {
            "categorias": fetch_dicts(cursor, """
                SELECT ID_GRUPO_PRODUTO, DESCRICAO
                FROM TGRUPOS_PRODUTOS ORDER BY ID_GRUPO_PRODUTO
            """),
            "produtos": fetch_dicts(cursor, """
                SELECT ID_PRODUTO, CODIGO, CODIGO_BARRAS, DESCRICAO,
                       ID_GRUPO_PRODUTO, PRECO_CUSTO, PRECO_VENDA,
                       ESTOQUE, ESTOQUE_MINIMO, UNIDADE, ATIVO,
                       CONTROLA_ESTOQUE, IMAGEM
                FROM TPRODUTOS ORDER BY ID_PRODUTO
            """),
            "clientes": fetch_dicts(cursor, """
                SELECT ID_HOSPEDE, NOME, CPF, ENDERECO, ENDERECO_COMPLEMENTO,
                       ENDERECO_NUMERO, BAIRRO, CEP, TELEFONE, CELULAR,
                       OBSERVACOES, OBSERVACOES_CRM, DATA_CADASTRO,
                       TOTAL_CREDITOS, LIMITE_CREDITOS, ATIVO
                FROM THOSPEDES ORDER BY ID_HOSPEDE
            """),
            "funcionarios": fetch_dicts(cursor, """
                SELECT ID_FUNCIONARIO, NOME, TELEFONE, CELULAR, COMISSAO, ATIVO
                FROM TFUNCIONARIOS ORDER BY ID_FUNCIONARIO
            """),
            "usuarios": fetch_dicts(cursor, """
                SELECT ID_USUARIO, USUARIO, NOME, ATIVO
                FROM TUSUARIOS ORDER BY ID_USUARIO
            """),
            "mesas": fetch_dicts(cursor, """
                SELECT ID_MESA, NUMERO, SITUACAO FROM TMESAS ORDER BY ID_MESA
            """),
            "formas": fetch_dicts(cursor, """
                SELECT ID_FORMAPGTO, NOME FROM TFORMAS_PGTO ORDER BY ID_FORMAPGTO
            """),
            "vendas_formas": fetch_dicts(cursor, """
                SELECT VF.ID_VENDA, VF.ID_FORMAPGTO, F.NOME, VF.VALOR
                FROM TVENDAS_FORMASPGTO VF
                LEFT JOIN TFORMAS_PGTO F ON F.ID_FORMAPGTO=VF.ID_FORMAPGTO
                ORDER BY VF.ID_VENDA, VF.ID_VENDA_FORMAPGTO
            """),
            "vendas": fetch_dicts(cursor, """
                SELECT ID_VENDA, ID_USUARIO, ID_CLIENTE, ID_CAIXA,
                       DATA, HORA, DATA_HORA_FECHAMENTO, VALOR_TOTAL,
                       VALOR_DESCONTO, ID_FORMAPGTO, CANCELADO
                FROM TVENDAS ORDER BY ID_VENDA
            """),
            "itens_venda": fetch_dicts(cursor, """
                SELECT ID_VENDA_ITEM, ID_VENDA, ID_PRODUTO, QUANTIDADE,
                       VALOR_UNITARIO, VALOR_TOTAL, VALOR_TOTAL_GERAL,
                       DESCRICAO_COMPLEMENTO
                FROM TVENDAS_ITENS ORDER BY ID_VENDA_ITEM
            """),
            "creditos": fetch_dicts(cursor, """
                SELECT ID_CREDITO, ID_HOSPEDE, ID_USUARIO, ID_VENDA,
                       DATA, DESCRICAO, VALOR, VALOR_REAL, TIPO
                FROM TCREDITOS ORDER BY ID_CREDITO
            """),
            "caixas": fetch_dicts(cursor, """
                SELECT ID_CAIXA, ID_USUARIO, ID_USUARIO_FECHAMENTO,
                       DATA_ABERTURA, HORA_ABERTURA, DATA_FECHAMENTO,
                       HORA_FECHAMENTO, ORIGEM
                FROM TCAIXAS ORDER BY ID_CAIXA
            """),
            "compras_itens": fetch_dicts(cursor, """
                SELECT I.ID_COMPRA_ITEM, I.ID_COMPRA, I.ID_PRODUTO,
                       I.QUANTIDADE, I.VALOR_UNITARIO, I.VALOR_TOTAL,
                       C.DATA, C.HORA, C.ID_USUARIO, C.NF, C.OBSERVACAO
                FROM TCOMPRAS_ITENS I
                JOIN TCOMPRAS C ON C.ID_COMPRA=I.ID_COMPRA
                ORDER BY I.ID_COMPRA_ITEM
            """),
            "estoque_itens": fetch_dicts(cursor, """
                SELECT I.ID_ESTOQUE_ITEM, I.ID_ESTOQUE, I.ID_PRODUTO,
                       I.QUANTIDADE, I.VALOR_UNITARIO, I.VALOR_TOTAL,
                       E.DATA, E.HORA, E.ID_USUARIO, E.OBSERVACAO, E.ID_VENDA
                FROM TESTOQUE_ITENS I
                JOIN TESTOQUE E ON E.ID_ESTOQUE=I.ID_ESTOQUE
                ORDER BY I.ID_ESTOQUE_ITEM
            """),
            "pedidos_abertos": fetch_dicts(cursor, """
                SELECT P.ID_PEDIDO, P.ID_USUARIO, P.ID_CLIENTE, P.ID_FUNCIONARIO,
                       P.ID_COMANDA, C.NUMERO AS NUMERO_COMANDA,
                       P.DATA_HORA_ABERTURA, P.VALOR_TOTAL_GERAL,
                       P.CLIENTE_NOME, P.OBSERVACAO
                FROM TPEDIDOS P
                JOIN TCOMANDAS C ON C.ID_COMANDA=P.ID_COMANDA
                WHERE P.SITUACAO='Aberto'
                ORDER BY P.ID_PEDIDO
            """),
            "pedidos_itens_abertos": fetch_dicts(cursor, """
                SELECT I.ID_PEDIDO_ITEM, I.ID_PEDIDO, I.ID_PRODUTO,
                       I.ID_USUARIO, I.ID_FUNCIONARIO, I.DATA_HORA_LANCTO,
                       I.QUANTIDADE, I.VALOR_UNITARIO, I.VALOR_TOTAL,
                       I.VALOR_TOTAL_GERAL, I.CANCELADO,
                       I.OBSERVACAO, I.DESCRICAO_COMPLEMENTO
                FROM TPEDIDOS_ITENS I
                JOIN TPEDIDOS P ON P.ID_PEDIDO=I.ID_PEDIDO
                WHERE P.SITUACAO='Aberto'
                ORDER BY I.ID_PEDIDO_ITEM
            """),
            "hotel": fetch_dicts(cursor, """
                SELECT FIRST 1 ID_HOTEL, NOME, NOME_FANTASIA, CNPJ, IE,
                       ENDERECO, ENDERECO_COMPLEMENTO, ENDERECO_NUMERO,
                       BAIRRO, CEP, TELEFONE, EMAIL
                FROM THOTEL ORDER BY ID_HOTEL
            """),
        }
        cursor.execute("SELECT COUNT(*) FROM TCOMPRAS")
        data["compras_count"] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM TESTOQUE")
        data["estoque_saidas_count"] = cursor.fetchone()[0]
        # Materializa BLOBs enquanto a conexão Firebird ainda está aberta.
        for value in data.values():
            if not isinstance(value, list):
                continue
            for row in value:
                for key, field in list(row.items()):
                    if hasattr(field, "read"):
                        row[key] = field.read()
        return data
    finally:
        connection.close()


def validate_source(data):
    actual = {
        "categorias": len(data["categorias"]),
        "produtos": len(data["produtos"]),
        "clientes": len(data["clientes"]),
        "vendas": len(data["vendas"]),
        "itens_venda": len(data["itens_venda"]),
        "creditos": len(data["creditos"]),
        "compras": data["compras_count"],
        "estoque_saidas": data["estoque_saidas_count"],
        "funcionarios": len(data["funcionarios"]),
        "mesas": len(data["mesas"]),
        "caixas": len(data["caixas"]),
        "pedidos_abertos": len(data["pedidos_abertos"]),
    }
    if actual != EXPECTED_SOURCE_COUNTS:
        raise RuntimeError(f"Contagens da fonte divergentes: esperado={EXPECTED_SOURCE_COUNTS}, atual={actual}")

    product_ids = {row["ID_PRODUTO"] for row in data["produtos"]}
    sale_ids = {row["ID_VENDA"] for row in data["vendas"]}
    client_ids = {row["ID_HOSPEDE"] for row in data["clientes"]}
    invalid_items = [row["ID_VENDA_ITEM"] for row in data["itens_venda"]
                     if row["ID_PRODUTO"] not in product_ids or row["ID_VENDA"] not in sale_ids]
    invalid_credits = [row["ID_CREDITO"] for row in data["creditos"]
                       if row["ID_HOSPEDE"] not in client_ids]
    if invalid_items or invalid_credits:
        raise RuntimeError(f"Referências inválidas na fonte: itens={invalid_items[:10]}, créditos={invalid_credits[:10]}")
    return actual


def import_into_sqlite(data, sqlite_path: Path):
    report = {
        "fonte": {},
        "importados": {},
        "avisos": [],
        "erros": [],
        "ajustes_saldo": 0,
    }
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        conn.execute("BEGIN IMMEDIATE")
        local_users = conn.execute("SELECT * FROM usuarios ORDER BY id").fetchall()
        admin = next((u for u in local_users if u["nivel"] == "admin" and u["ativo"]), None)
        if not admin:
            raise RuntimeError("Nenhum administrador local ativo para preservar o acesso.")
        admin_id = admin["id"]

        delete_order = [
            "acesso_rapido_produtos", "pagamentos_parciais_itens", "pagamentos_parciais",
            "historico_transferencias", "suprimento_sangria", "itens_comanda", "fiado",
            "itens_venda", "vendas", "comandas", "movimentacoes", "contas_pagar",
            "caixas", "garcons", "mesas", "clientes", "produtos", "categorias",
            "auditoria", "login_attempts", "empresa",
        ]
        for table in delete_order:
            conn.execute(f'DELETE FROM "{table}"')
        conn.execute("DELETE FROM usuarios WHERE login LIKE 'legado_fdb_%'")
        # Mantém apenas administradores locais para preservar o acesso ao sistema;
        # contas de funcionário da massa fictícia são substituídas pelo legado.
        conn.execute("DELETE FROM usuarios WHERE nivel<>'admin'")

        legacy_user_map = {}
        for user in data["usuarios"]:
            source_id = int(user["ID_USUARIO"])
            target_id = 100000 + source_id
            legacy_user_map[source_id] = target_id
            conn.execute("""
                INSERT INTO usuarios (id,nome,login,senha,nivel,ativo,criado_em)
                VALUES (?,?,?,?,?,?,?)
            """, (
                target_id,
                as_text(user["NOME"]) or as_text(user["USUARIO"]) or f"Usuário legado {source_id}",
                safe_login(user["USUARIO"], source_id),
                generate_password_hash(f"conta-legada-desativada-{source_id}"),
                "funcionario", 0, datetime.now().isoformat(sep=" "),
            ))

        def mapped_user(source_id):
            return legacy_user_map.get(source_id, admin_id)

        category_ids = set()
        for row in data["categorias"]:
            category_id = int(row["ID_GRUPO_PRODUTO"])
            category_ids.add(category_id)
            conn.execute("INSERT INTO categorias (id,nome) VALUES (?,?)", (
                category_id, as_text(row["DESCRICAO"]) or f"Categoria legado {category_id}"
            ))

        used_codes = set()
        image_payloads = {}
        products_without_category = 0
        products_negative_stock = 0
        products_zero_price = 0
        for row in data["produtos"]:
            product_id = int(row["ID_PRODUTO"])
            barcode = as_text(row["CODIGO_BARRAS"])
            internal_code = as_text(row["CODIGO"])
            product_code = barcode or internal_code or None
            if product_code and product_code in used_codes:
                report["avisos"].append(f"Código duplicado no produto {product_id}; código não importado.")
                product_code = None
            if product_code:
                used_codes.add(product_code)
            category_id = row["ID_GRUPO_PRODUTO"]
            if category_id not in category_ids:
                category_id = None
                products_without_category += 1
            price = as_float(row["PRECO_VENDA"])
            stock = as_float(row["ESTOQUE"])
            if price == 0:
                products_zero_price += 1
            if stock < 0:
                products_negative_stock += 1
            conn.execute("""
                INSERT INTO produtos
                    (id,nome,categoria_id,codigo_barras,preco,estoque,
                     estoque_minimo,unidade,ativo,criado_em)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                product_id, as_text(row["DESCRICAO"]), category_id, product_code,
                price, stock, as_float(row["ESTOQUE_MINIMO"]),
                as_text(row["UNIDADE"]) or "UN", 1 if as_text(row["ATIVO"]).upper() == "S" else 0,
                datetime.now().isoformat(sep=" "),
            ))
            blob = row["IMAGEM"]
            if blob is not None:
                payload = blob.read() if hasattr(blob, "read") else bytes(blob)
                image_payloads[product_id] = payload

        client_balances = {}
        incomplete_clients = 0
        for row in data["clientes"]:
            client_id = int(row["ID_HOSPEDE"])
            name = as_text(row["NOME"])
            if not name:
                name = f"Cliente legado sem nome (ID {client_id})"
                incomplete_clients += 1
            phone = as_text(row["CELULAR"]) or as_text(row["TELEFONE"])
            address = compact_join(
                as_text(row["ENDERECO"]), as_text(row["ENDERECO_NUMERO"]),
                as_text(row["ENDERECO_COMPLEMENTO"]), as_text(row["BAIRRO"]),
                as_text(row["CEP"]),
            )
            notes = "\n".join(filter(None, [as_text(row["OBSERVACOES"]), as_text(row["OBSERVACOES_CRM"])]))
            signed_credit = as_float(row["TOTAL_CREDITOS"])
            target_debt = max(0.0, round(-signed_credit, 2))
            client_balances[client_id] = target_debt
            created = row["DATA_CADASTRO"]
            conn.execute("""
                INSERT INTO clientes
                    (id,nome,telefone,cpf,endereco,limite_fiado,saldo_devedor,
                     observacao,ativo,criado_em)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                client_id, name, phone or None, as_text(row["CPF"]) or None,
                address or None, as_float(row["LIMITE_CREDITOS"]), target_debt,
                notes or None, 1 if as_text(row["ATIVO"]).upper() == "S" else 0,
                combine_datetime(created) or datetime.now().isoformat(sep=" "),
            ))

        for row in data["funcionarios"]:
            conn.execute("""
                INSERT INTO garcons (id,nome,telefone,comissao,ativo,criado_em)
                VALUES (?,?,?,?,?,?)
            """, (
                int(row["ID_FUNCIONARIO"]), as_text(row["NOME"]),
                as_text(row["CELULAR"]) or as_text(row["TELEFONE"]) or None,
                as_float(row["COMISSAO"]), 1 if as_text(row["ATIVO"]).upper() == "S" else 0,
                datetime.now().isoformat(sep=" "),
            ))

        mesa_by_number = {}
        for row in data["mesas"]:
            number_text = as_text(row["NUMERO"])
            number = int(number_text)
            mesa_id = int(row["ID_MESA"])
            mesa_by_number[number] = mesa_id
            conn.execute("""
                INSERT INTO mesas (id,numero,capacidade,status,valor_atual)
                VALUES (?,?,?,?,0)
            """, (mesa_id, number, 4, "disponivel"))

        form_names = {row["ID_FORMAPGTO"]: as_text(row["NOME"]) for row in data["formas"]}
        sale_forms = defaultdict(list)
        for row in data["vendas_formas"]:
            name = as_text(row["NOME"]) or form_names.get(row["ID_FORMAPGTO"], "Não informado")
            if name not in sale_forms[row["ID_VENDA"]]:
                sale_forms[row["ID_VENDA"]].append(name)

        sale_by_id = {row["ID_VENDA"]: row for row in data["vendas"]}
        active_sale_ids = set()
        for row in data["vendas"]:
            sale_id = int(row["ID_VENDA"])
            canceled = as_text(row["CANCELADO"]).upper() == "S"
            if not canceled:
                active_sale_ids.add(sale_id)
            forms = sale_forms.get(sale_id) or [form_names.get(row["ID_FORMAPGTO"], "Não informado")]
            payment = forms[0] if len(forms) == 1 else "Múltiplos / " + " + ".join(forms)
            conn.execute("""
                INSERT INTO vendas
                    (id,comanda_id,mesa_id,usuario_id,valor_total,desconto,
                     forma_pagamento,data,tipo,status)
                VALUES (?,NULL,NULL,?,?,?,?,?,'direta',?)
            """, (
                sale_id, mapped_user(row["ID_USUARIO"]), as_float(row["VALOR_TOTAL"]),
                as_float(row["VALOR_DESCONTO"]), payment,
                combine_datetime(row["DATA"], row["HORA"], row["DATA_HORA_FECHAMENTO"]),
                "cancelada" if canceled else "ativa",
            ))

        for row in data["itens_venda"]:
            subtotal = row["VALOR_TOTAL_GERAL"] if row["VALOR_TOTAL_GERAL"] is not None else row["VALOR_TOTAL"]
            conn.execute("""
                INSERT INTO itens_venda
                    (id,venda_id,produto_id,quantidade,preco_unitario,subtotal,observacao)
                VALUES (?,?,?,?,?,?,?)
            """, (
                int(row["ID_VENDA_ITEM"]), int(row["ID_VENDA"]), int(row["ID_PRODUTO"]),
                as_float(row["QUANTIDADE"]), as_float(row["VALOR_UNITARIO"]),
                as_float(subtotal), as_text(row["DESCRICAO_COMPLEMENTO"]) or None,
            ))

        sales_by_cash = defaultdict(lambda: [0, 0.0])
        for row in data["vendas"]:
            if row["ID_CAIXA"] is not None and as_text(row["CANCELADO"]).upper() != "S":
                sales_by_cash[row["ID_CAIXA"]][0] += 1
                sales_by_cash[row["ID_CAIXA"]][1] += as_float(row["VALOR_TOTAL"])
        for row in data["caixas"]:
            qty, total = sales_by_cash[row["ID_CAIXA"]]
            closing = combine_datetime(row["DATA_FECHAMENTO"], row["HORA_FECHAMENTO"])
            conn.execute("""
                INSERT INTO caixas
                    (id,usuario_id,abertura,fechamento,valor_inicial,valor_final,
                     total_vendas,quantidade_vendas,diferenca,observacao)
                VALUES (?,?,?,?,0,?,?,?,?,?)
            """, (
                int(row["ID_CAIXA"]), mapped_user(row["ID_USUARIO"]),
                combine_datetime(row["DATA_ABERTURA"], row["HORA_ABERTURA"]), closing,
                round(total, 2) if closing else None, round(total, 2), qty, 0,
                f"Importado do Datacaixa. Origem: {as_text(row['ORIGEM']) or 'não informada'}",
            ))

        payment_total_by_client = defaultdict(float)
        purchase_rows_by_client = defaultdict(list)
        for row in data["creditos"]:
            client_id = int(row["ID_HOSPEDE"])
            kind = "compra" if as_text(row["TIPO"]).upper() == "D" else "pagamento"
            value = abs(as_float(row["VALOR"] or row["VALOR_REAL"]))
            sale_id = row["ID_VENDA"] if row["ID_VENDA"] in sale_by_id else None
            conn.execute("""
                INSERT INTO fiado
                    (id,cliente_id,venda_id,tipo,valor,valor_pago,data_vencimento,
                     usuario_id,observacao,data_hora)
                VALUES (?,?,?,?,?,0,NULL,?,?,?)
            """, (
                int(row["ID_CREDITO"]), client_id, sale_id, kind, value,
                mapped_user(row["ID_USUARIO"]),
                f"Importado do Datacaixa: {as_text(row['DESCRICAO'])}".rstrip(),
                combine_datetime(row["DATA"]),
            ))
            if kind == "compra":
                purchase_rows_by_client[client_id].append([int(row["ID_CREDITO"]), value, 0.0])
            else:
                payment_total_by_client[client_id] += value

        for client_id, purchases in purchase_rows_by_client.items():
            remaining_payment = payment_total_by_client[client_id]
            for purchase in purchases:
                paid = min(purchase[1], remaining_payment)
                purchase[2] = paid
                remaining_payment -= paid
                if paid:
                    conn.execute("UPDATE fiado SET valor_pago=? WHERE id=?", (round(paid, 2), purchase[0]))

            open_balance = round(sum(value - paid for _, value, paid in purchases), 2)
            target_balance = client_balances.get(client_id, 0.0)
            difference = round(target_balance - open_balance, 2)
            if difference > 0.009:
                conn.execute("""
                    INSERT INTO fiado
                        (cliente_id,tipo,valor,valor_pago,usuario_id,observacao,data_hora)
                    VALUES (?,'compra',?,0,?,'Ajuste de saldo do backup legado',?)
                """, (client_id, difference, admin_id, datetime.now().isoformat(sep=" ")))
                report["ajustes_saldo"] += 1
            elif difference < -0.009:
                to_pay = -difference
                for purchase_id, value, already_paid in reversed(purchases):
                    available = value - already_paid
                    paid = min(available, to_pay)
                    if paid:
                        conn.execute("UPDATE fiado SET valor_pago=valor_pago+? WHERE id=?", (round(paid, 2), purchase_id))
                        to_pay -= paid
                    if to_pay <= 0.009:
                        break
                conn.execute("""
                    INSERT INTO fiado
                        (cliente_id,tipo,valor,valor_pago,usuario_id,observacao,data_hora)
                    VALUES (?,'pagamento',?,0,?,'Ajuste de saldo do backup legado',?)
                """, (client_id, -difference, admin_id, datetime.now().isoformat(sep=" ")))
                report["ajustes_saldo"] += 1

        for client_id, target_balance in client_balances.items():
            conn.execute("UPDATE clientes SET saldo_devedor=? WHERE id=?", (target_balance, client_id))

        open_order_ids = set()
        for row in data["pedidos_abertos"]:
            number = int(as_text(row["NUMERO_COMANDA"]))
            mesa_id = mesa_by_number.get(number)
            if mesa_id is None:
                report["erros"].append({"tipo": "pedido_aberto", "id": row["ID_PEDIDO"], "motivo": "comanda sem mesa equivalente"})
                continue
            order_id = int(row["ID_PEDIDO"])
            open_order_ids.add(order_id)
            garcom_id = row["ID_FUNCIONARIO"]
            conn.execute("""
                INSERT INTO comandas
                    (id,mesa_id,usuario_id,garcom_id,cliente_nome,abertura,status)
                VALUES (?,?,?,?,?,?,'aberta')
            """, (
                order_id, mesa_id, mapped_user(row["ID_USUARIO"]), garcom_id,
                as_text(row["CLIENTE_NOME"]) or f"Comanda {number:03d}",
                combine_datetime(row["DATA_HORA_ABERTURA"]),
            ))
            conn.execute("""
                UPDATE mesas SET status='ocupada', valor_atual=?, aberta_em=? WHERE id=?
            """, (as_float(row["VALOR_TOTAL_GERAL"]), combine_datetime(row["DATA_HORA_ABERTURA"]), mesa_id))

        imported_open_items = 0
        for row in data["pedidos_itens_abertos"]:
            if row["ID_PEDIDO"] not in open_order_ids or as_text(row["CANCELADO"]).upper() == "S":
                continue
            subtotal = row["VALOR_TOTAL_GERAL"] if row["VALOR_TOTAL_GERAL"] is not None else row["VALOR_TOTAL"]
            observation = " | ".join(filter(None, [as_text(row["OBSERVACAO"]), as_text(row["DESCRICAO_COMPLEMENTO"])]))
            conn.execute("""
                INSERT INTO itens_comanda
                    (id,comanda_id,produto_id,quantidade,preco_unitario,subtotal,
                     observacao,usuario_id,criado_em)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                int(row["ID_PEDIDO_ITEM"]), int(row["ID_PEDIDO"]), int(row["ID_PRODUTO"]),
                as_float(row["QUANTIDADE"]), as_float(row["VALOR_UNITARIO"]),
                as_float(subtotal), observation or None, mapped_user(row["ID_USUARIO"]),
                combine_datetime(row["DATA_HORA_LANCTO"]),
            ))
            imported_open_items += 1

        movement_rows = []
        for row in data["compras_itens"]:
            movement_rows.append((
                int(row["ID_PRODUTO"]), "entrada", abs(as_float(row["QUANTIDADE"])),
                f"Compra legado #{row['ID_COMPRA']}", mapped_user(row["ID_USUARIO"]),
                combine_datetime(row["DATA"], row["HORA"]),
                compact_join(f"NF {as_text(row['NF'])}" if as_text(row["NF"]) else "", row["OBSERVACAO"]),
            ))
        for row in data["estoque_itens"]:
            movement_rows.append((
                int(row["ID_PRODUTO"]), "saida", abs(as_float(row["QUANTIDADE"])),
                f"Saída de estoque legado #{row['ID_ESTOQUE']}", mapped_user(row["ID_USUARIO"]),
                combine_datetime(row["DATA"], row["HORA"]), as_text(row["OBSERVACAO"]) or None,
            ))
        for row in data["itens_venda"]:
            if row["ID_VENDA"] not in active_sale_ids:
                continue
            sale = sale_by_id[row["ID_VENDA"]]
            movement_rows.append((
                int(row["ID_PRODUTO"]), "saida", abs(as_float(row["QUANTIDADE"])),
                f"Venda legado #{row['ID_VENDA']}", mapped_user(sale["ID_USUARIO"]),
                combine_datetime(sale["DATA"], sale["HORA"], sale["DATA_HORA_FECHAMENTO"]),
                as_text(row["DESCRICAO_COMPLEMENTO"]) or None,
            ))
        for row in data["pedidos_itens_abertos"]:
            if row["ID_PEDIDO"] in open_order_ids and as_text(row["CANCELADO"]).upper() != "S":
                movement_rows.append((
                    int(row["ID_PRODUTO"]), "saida", abs(as_float(row["QUANTIDADE"])),
                    f"Comanda legado #{row['ID_PEDIDO']}", mapped_user(row["ID_USUARIO"]),
                    combine_datetime(row["DATA_HORA_LANCTO"]), as_text(row["OBSERVACAO"]) or None,
                ))
        conn.executemany("""
            INSERT INTO movimentacoes
                (produto_id,tipo,quantidade,motivo,usuario_id,data_hora,observacao)
            VALUES (?,?,?,?,?,?,?)
        """, movement_rows)

        hotel = data["hotel"][0]
        company_address = compact_join(
            hotel["ENDERECO"], hotel["ENDERECO_NUMERO"], hotel["ENDERECO_COMPLEMENTO"],
            hotel["BAIRRO"], hotel["CEP"],
        )
        conn.execute("""
            INSERT INTO empresa
                (id,razao_social,nome_fantasia,cnpj,inscricao_estadual,
                 endereco,telefone,email,observacao)
            VALUES (1,?,?,?,?,?,?,?,?)
        """, (
            as_text(hotel["NOME"]), as_text(hotel["NOME_FANTASIA"]),
            as_text(hotel["CNPJ"]), as_text(hotel["IE"]), company_address,
            as_text(hotel["TELEFONE"]), as_text(hotel["EMAIL"]),
            "Dados importados do backup Datacaixa de 30/07/2026.",
        ))

        table_counts = {}
        for table in [
            "categorias", "produtos", "clientes", "garcons", "mesas", "comandas",
            "itens_comanda", "vendas", "itens_venda", "fiado", "caixas",
            "movimentacoes", "contas_pagar",
        ]:
            table_counts[table] = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]

        expected_sqlite = {
            "categorias": len(data["categorias"]), "produtos": len(data["produtos"]),
            "clientes": len(data["clientes"]), "garcons": len(data["funcionarios"]),
            "mesas": len(data["mesas"]), "comandas": len(open_order_ids),
            "itens_comanda": imported_open_items, "vendas": len(data["vendas"]),
            "itens_venda": len(data["itens_venda"]), "caixas": len(data["caixas"]),
        }
        for table, expected in expected_sqlite.items():
            if table_counts[table] != expected:
                raise RuntimeError(f"Validação falhou em {table}: {table_counts[table]} != {expected}")

        fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
        if fk_errors:
            raise RuntimeError(f"Chaves estrangeiras inválidas: {fk_errors[:10]}")

        report["importados"] = table_counts
        report["importados"]["usuarios_legados_inativos"] = len(data["usuarios"])
        report["importados"]["imagens_produtos"] = len(image_payloads)
        report["importados"]["movimentos_compras"] = len(data["compras_itens"])
        report["importados"]["movimentos_saidas_estoque"] = len(data["estoque_itens"])
        report["importados"]["pedidos_abertos_fonte"] = len(data["pedidos_abertos"])
        report["fonte"] = EXPECTED_SOURCE_COUNTS.copy()
        report["avisos"].extend([
            f"{products_without_category} produtos permaneceram sem categoria porque a fonte não informa o grupo.",
            f"{products_zero_price} produtos vieram com preço zero.",
            f"{products_negative_stock} produtos vieram com estoque negativo.",
            f"{incomplete_clients} cliente inativo veio sem nome e recebeu identificação técnica pelo ID.",
            "O backup não contém cadastro real de fornecedores; contas a pagar permaneceu vazia.",
        ])
        audit_details = json.dumps({
            "fonte": "DATACAIXA_TESTE.FDB", "importados": report["importados"],
            "avisos": report["avisos"], "erros": report["erros"],
        }, ensure_ascii=False)
        conn.execute("""
            INSERT INTO auditoria (usuario_id,usuario_nome,acao,detalhes,data_hora)
            VALUES (?,?,?,?,?)
        """, (admin_id, admin["nome"], "importacao_backup_adega", audit_details,
              datetime.now().isoformat(sep=" ")))
        conn.commit()
        return report, image_payloads
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def write_images(images: dict[int, bytes], target: Path):
    if target.exists():
        raise RuntimeError(f"Diretório de imagens já existe: {target}")
    target.mkdir(parents=True)
    manifest = []
    for product_id, payload in sorted(images.items()):
        filename = f"produto_{product_id}.bmp"
        path = target / filename
        path.write_bytes(payload)
        manifest.append({
            "produto_id": product_id,
            "arquivo": filename,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        })
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--fbclient", required=True, type=Path)
    parser.add_argument("--sqlite", required=True, type=Path)
    parser.add_argument("--images-dir", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()

    for required in (args.source, args.fbclient, args.sqlite):
        if not required.is_file():
            raise SystemExit(f"Arquivo não encontrado: {required}")
    if args.manifest.exists():
        raise SystemExit(f"O relatório de destino já existe: {args.manifest}")

    data = load_source(args.source, args.fbclient)
    source_counts = validate_source(data)
    report, images = import_into_sqlite(data, args.sqlite)
    report["fonte"] = source_counts
    report["imagens"] = write_images(images, args.images_dir)
    report["integridade_sqlite"] = "ok"
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
