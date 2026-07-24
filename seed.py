import os
from werkzeug.security import generate_password_hash
from database import get_db

ADMIN_LOGIN = os.environ.get("ADMIN_LOGIN", "admin")
ADMIN_SENHA = os.environ.get("ADMIN_SENHA", "Admin@2026#Jam's")
FUNC_LOGIN = os.environ.get("FUNC_LOGIN", "funcionario")
FUNC_SENHA = os.environ.get("FUNC_SENHA", "Func@2026#Sistema")

CATEGORIAS = [
    "Vinhos", "Whisky", "Vodka", "Gin", "Cervejas", "Refrigerantes",
    "Energéticos", "Água", "Petiscos", "Porções", "Drinks", "Outros"
]

PRODUTOS = [
    # Cervejas
    ("Heineken Long Neck 330ml", "Cervejas", "7891991010924", 8.90, 48, 12, "UN"),
    ("Brahma Long Neck 330ml", "Cervejas", "7891149102748", 5.50, 60, 15, "UN"),
    ("Original Long Neck 330ml", "Cervejas", "7891991010931", 7.50, 36, 12, "UN"),
    ("Stella Artois 275ml", "Cervejas", "5410228015017", 9.90, 24, 8, "UN"),
    # Whisky
    ("Johnnie Walker Red 1L", "Whisky", "5000267023625", 89.90, 6, 2, "UN"),
    ("Jack Daniel's 1L", "Whisky", "082184090446", 159.90, 4, 2, "UN"),
    ("Ballantine's 1L", "Whisky", "5010106113632", 79.90, 5, 2, "UN"),
    # Vodka
    ("Smirnoff 998ml", "Vodka", "7893218000012", 39.90, 8, 3, "UN"),
    ("Absolut 1L", "Vodka", "7312040017047", 79.90, 5, 2, "UN"),
    # Gin
    ("Tanqueray 750ml", "Gin", "5000281025363", 119.90, 4, 2, "UN"),
    # Vinhos
    ("Vinho Tinto Reservado 750ml", "Vinhos", "7804320020013", 49.90, 12, 4, "UN"),
    ("Vinho Branco Suave 750ml", "Vinhos", "7804320020020", 39.90, 10, 4, "UN"),
    # Refrigerantes
    ("Coca-Cola 350ml", "Refrigerantes", "7894900011517", 6.00, 60, 20, "UN"),
    ("Coca-Cola 2L", "Refrigerantes", "7894900700015", 12.00, 24, 8, "UN"),
    ("Guaraná Antarctica 350ml", "Refrigerantes", "7891991010934", 5.50, 48, 15, "UN"),
    # Energéticos
    ("Red Bull 250ml", "Energéticos", "9002490100070", 12.00, 36, 12, "UN"),
    # Água
    ("Água Crystal 500ml", "Água", "7894900027013", 4.00, 80, 24, "UN"),
    ("Água com gás 500ml", "Água", "7894900027020", 5.00, 40, 12, "UN"),
    # Petiscos
    ("Amendoim Torrado 100g", "Petiscos", "7891118000010", 8.00, 30, 10, "UN"),
    ("Batata Frita 150g", "Petiscos", "7891118000027", 15.00, 20, 8, "UN"),
    # Porções
    ("Porção Calabresa 500g", "Porções", "9999000000001", 35.00, 999, 0, "UN"),
    ("Porção Batata Frita 500g", "Porções", "9999000000002", 32.00, 999, 0, "UN"),
    ("Porção Frango à Passarinho 500g", "Porções", "9999000000003", 45.00, 999, 0, "UN"),
    # Drinks
    ("Caipirinha", "Drinks", "9999000000010", 18.00, 999, 0, "UN"),
    ("Mojito", "Drinks", "9999000000011", 22.00, 999, 0, "UN"),
    ("Gin Tônica", "Drinks", "9999000000012", 25.00, 999, 0, "UN"),
]

FIADOS_EXEMPLO = [
    # (cliente_nome, valor, dias_para_vencimento)
    # Vermelho - vencidos
    ("Maria Oliveira", 89.90, -3),     # vencido há 3 dias
    ("Ana Pereira", 150.00, -7),       # vencido há 7 dias
    ("Marcos Almeida", 200.00, -1),    # vencido hoje
    # Amarelo - até 5 dias
    ("Ana Pereira", 100.00, 2),        # vence em 2 dias
    ("Diego Fernandes", 75.00, 5),     # vence em 5 dias
    ("Fernanda Lima", 80.00, 4),       # vence em 4 dias
    # Roxo - de 6 a 10 dias
    ("Marcos Almeida", 120.00, 8),     # vence em 8 dias
    ("João da Silva", 250.00, 10),     # vence em 10 dias
    ("Lucas Mendes", 180.00, 7),       # vence em 7 dias
    # Verde - mais de 10 dias
    ("Fernanda Lima", 120.00, 20),     # vence em 20 dias
    ("Pedro Santos", 300.00, 25),      # vence em 25 dias
    ("Camila Ribeiro", 90.00, 15),     # vence em 15 dias
    ("Bruno Carvalho", 500.00, 30),    # vence em 30 dias
    ("Patrícia Vieira", 220.00, 18),   # vence em 18 dias
    ("Juliana Rocha", 150.00, 22),     # vence em 22 dias
    ("Rafael Costa", 100.00, 14),      # vence em 14 dias
    ("Larissa Martins", 80.00, 28),    # vence em 28 dias
]


CLIENTES = [
    ("João da Silva", "(11) 98765-4321", "123.456.789-01", "Rua das Flores, 123 - SP", 500, 0, "Cliente antigo, sempre paga em dia"),
    ("Maria Oliveira", "(11) 99887-6655", "234.567.890-12", "Av. Brasil, 987 - SP", 300, 89.90, "Bebe Heineken toda sexta"),
    ("Carlos Souza", "(11) 91234-5678", "345.678.901-23", "Rua Bahia, 45 - SP", 200, 0, ""),
    ("Ana Pereira", "(11) 98888-1111", "456.789.012-34", "Rua Acre, 200 - SP", 1000, 350.50, "Devedor antigo - cobrar antes de servir"),
    ("Pedro Santos", "(11) 97777-2222", "567.890.123-45", "Rua Mato Grosso, 80 - SP", 400, 0, ""),
    ("Lucas Mendes", "(11) 96666-3333", "678.901.234-56", "Av. Paulista, 1000 - SP", 250, 0, ""),
    ("Fernanda Lima", "(11) 95555-4444", "789.012.345-67", "Rua Goiás, 33 - SP", 600, 120.00, "VIP - Whisky"),
    ("Rafael Costa", "(11) 94444-5555", "890.123.456-78", "Rua Paraná, 500 - SP", 150, 0, ""),
    ("Juliana Rocha", "(11) 93333-6666", "901.234.567-89", "Av. Rio Branco, 200 - SP", 800, 0, "Mesa fixa toda quinta"),
    ("Marcos Almeida", "(11) 92222-7777", "012.345.678-90", "Rua Santa Cruz, 70 - SP", 300, 200.00, "Promessa de pagamento dia 15"),
    ("Patrícia Vieira", "(11) 91111-8888", "111.222.333-44", "Rua São Bento, 88 - SP", 1000, 0, ""),
    ("Bruno Carvalho", "(11) 90000-9999", "222.333.444-55", "Av. Faria Lima, 1500 - SP", 2000, 0, "Cliente premium"),
    ("Camila Ribeiro", "(11) 98890-1234", "333.444.555-66", "Rua Augusta, 2000 - SP", 400, 0, ""),
    ("Diego Fernandes", "(11) 97789-2345", "444.555.666-77", "Rua Oscar Freire, 300 - SP", 500, 75.00, ""),
    ("Larissa Martins", "(11) 96678-3456", "555.666.777-88", "Rua Haddock Lobo, 600 - SP", 350, 0, ""),
]


def seed_initial():
    db = get_db()
    # Categorias
    for c in CATEGORIAS:
        try:
            db.execute("INSERT INTO categorias (nome) VALUES (?)", (c,))
        except Exception:
            pass
    db.commit()
    # Admin padrão
    admin = db.execute("SELECT id FROM usuarios WHERE login='admin'").fetchone()
    if not admin:
        db.execute(
            "INSERT INTO usuarios (nome, login, senha, nivel) VALUES (?,?,?,?)",
            ("Administrador", ADMIN_LOGIN, generate_password_hash(ADMIN_SENHA), "admin")
        )
        db.execute(
            "INSERT INTO usuarios (nome, login, senha, nivel) VALUES (?,?,?,?)",
            ("Funcionário", FUNC_LOGIN, generate_password_hash(FUNC_SENHA), "funcionario")
        )
    db.commit()
    # Produtos
    for p in PRODUTOS:
        nome, cat, cod, preco, estoque, est_min, un = p
        existe = db.execute("SELECT id FROM produtos WHERE codigo_barras=?", (cod,)).fetchone()
        if existe:
            continue
        cat_id = db.execute("SELECT id FROM categorias WHERE nome=?", (cat,)).fetchone()
        cat_id = cat_id["id"] if cat_id else None
        db.execute(
            "INSERT INTO produtos (nome, categoria_id, codigo_barras, preco, estoque, estoque_minimo, unidade) VALUES (?,?,?,?,?,?,?)",
            (nome, cat_id, cod, preco, estoque, est_min, un)
        )
    db.commit()
    # Mesas
    total = db.execute("SELECT COUNT(*) as c FROM mesas").fetchone()["c"]
    if total == 0:
        for i in range(1, 21):
            db.execute("INSERT INTO mesas (numero, capacidade) VALUES (?,?)", (i, 4 if i % 5 != 0 else 8))
    db.commit()
    # Clientes
    total_c = db.execute("SELECT COUNT(*) as c FROM clientes").fetchone()["c"]
    if total_c == 0:
        for c in CLIENTES:
            nome, tel, cpf, end, limite, saldo, obs = c
            db.execute(
                "INSERT INTO clientes (nome, telefone, cpf, endereco, limite_fiado, saldo_devedor, observacao) VALUES (?,?,?,?,?,?,?)",
                (nome, tel, cpf, end, limite, saldo, obs)
            )
    db.commit()


def seed_missing_data():
    db = get_db()
    from datetime import date, timedelta
    # Garçom padrão
    total_g = db.execute("SELECT COUNT(*) as c FROM garcons").fetchone()["c"]
    if total_g == 0:
        db.execute("INSERT INTO garcons (nome) VALUES (?)", ("Não definido",))
        db.commit()
    # Expandir mesas até 40
    total_m = db.execute("SELECT COUNT(*) as c FROM mesas").fetchone()["c"]
    if total_m < 40:
        for i in range(total_m + 1, 41):
            existe = db.execute("SELECT id FROM mesas WHERE numero=?", (i,)).fetchone()
            if not existe:
                db.execute("INSERT INTO mesas (numero, capacidade) VALUES (?,?)", (i, 4 if i % 5 != 0 else 8))
        db.commit()
    # Clientes (se vazio)
    total_c = db.execute("SELECT COUNT(*) as c FROM clientes").fetchone()["c"]
    if total_c == 0:
        for c in CLIENTES:
            nome, tel, cpf, end, limite, saldo, obs = c
            db.execute(
                "INSERT INTO clientes (nome, telefone, cpf, endereco, limite_fiado, saldo_devedor, observacao) VALUES (?,?,?,?,?,?,?)",
                (nome, tel, cpf, end, limite, saldo, obs)
            )
        db.commit()
    # Fiados sem data_vencimento
    sem_venc = db.execute("SELECT COUNT(*) as c FROM fiado WHERE data_vencimento IS NULL").fetchone()["c"]
    com_venc = db.execute("SELECT COUNT(*) as c FROM fiado WHERE data_vencimento IS NOT NULL").fetchone()["c"]
    if sem_venc > 0 and com_venc == 0:
        antigos = db.execute("SELECT id FROM fiado").fetchall()
        for i, a in enumerate(antigos):
            dias = [-7, -3, 2, 5, 8, 15, 20, 25][i % 8]
            db.execute("UPDATE fiado SET data_vencimento=? WHERE id=?", ((date.today() + timedelta(days=dias)).isoformat(), a["id"]))
        for cli_nome, valor, dias in FIADOS_EXEMPLO:
            cli = db.execute("SELECT id FROM clientes WHERE nome=?", (cli_nome,)).fetchone()
            if not cli:
                continue
            venc = (date.today() + timedelta(days=dias)).isoformat()
            existe = db.execute("SELECT id FROM fiado WHERE cliente_id=? AND tipo='compra' AND valor=? AND data_vencimento=?", (cli["id"], valor, venc)).fetchone()
            if not existe:
                db.execute(
                    "INSERT INTO fiado (cliente_id, tipo, valor, data_vencimento) VALUES (?,?,?,?)",
                    (cli["id"], "compra", valor, venc)
                )
        db.execute("""
            UPDATE clientes SET saldo_devedor = COALESCE((
                SELECT SUM(valor - valor_pago) FROM fiado
                WHERE fiado.cliente_id = clientes.id AND tipo='compra'
            ), 0)
        """)
        db.commit()
