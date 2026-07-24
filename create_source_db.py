"""Cria banco fonte realista para testar a migração via wizard."""
import os
import sqlite3
import random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads", "migration_tmp", "banco_fonte_realista.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON")

SCHEMA = """
CREATE TABLE IF NOT EXISTS empresa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    razao_social TEXT,
    nome_fantasia TEXT,
    cnpj TEXT,
    inscricao_estadual TEXT,
    endereco TEXT,
    telefone TEXT,
    email TEXT,
    horario_funcionamento TEXT,
    observacao TEXT
);
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    login TEXT NOT NULL UNIQUE,
    senha TEXT NOT NULL,
    nivel TEXT NOT NULL DEFAULT 'funcionario',
    ativo INTEGER DEFAULT 1,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS garcons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    telefone TEXT,
    comissao REAL DEFAULT 0,
    ativo INTEGER DEFAULT 1,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS mesas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero INTEGER NOT NULL UNIQUE,
    capacidade INTEGER DEFAULT 4,
    status TEXT DEFAULT 'disponivel',
    valor_atual REAL DEFAULT 0,
    aberta_em TIMESTAMP,
    reservada_para TEXT
);
CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    categoria_id INTEGER,
    codigo_barras TEXT,
    preco REAL NOT NULL DEFAULT 0,
    estoque REAL DEFAULT 0,
    estoque_minimo REAL DEFAULT 5,
    unidade TEXT DEFAULT 'un',
    ativo INTEGER DEFAULT 1,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (categoria_id) REFERENCES categorias(id)
);
CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    telefone TEXT,
    cpf TEXT,
    endereco TEXT,
    limite_fiado REAL DEFAULT 500,
    saldo_devedor REAL DEFAULT 0,
    observacao TEXT,
    ativo INTEGER DEFAULT 1,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS caixas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    abertura TIMESTAMP NOT NULL,
    fechamento TIMESTAMP,
    valor_inicial REAL DEFAULT 0,
    valor_final REAL,
    total_vendas REAL DEFAULT 0,
    quantidade_vendas INTEGER DEFAULT 0,
    diferenca REAL DEFAULT 0,
    observacao TEXT,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);
CREATE TABLE IF NOT EXISTS comandas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mesa_id INTEGER NOT NULL,
    usuario_id INTEGER NOT NULL,
    garcom_id INTEGER,
    cliente_nome TEXT,
    abertura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fechamento TIMESTAMP,
    status TEXT DEFAULT 'aberta',
    FOREIGN KEY (mesa_id) REFERENCES mesas(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    FOREIGN KEY (garcom_id) REFERENCES garcons(id)
);
CREATE TABLE IF NOT EXISTS itens_comanda (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comanda_id INTEGER NOT NULL,
    produto_id INTEGER NOT NULL,
    quantidade REAL NOT NULL DEFAULT 1,
    preco_unitario REAL NOT NULL,
    subtotal REAL NOT NULL,
    observacao TEXT,
    usuario_id INTEGER,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (comanda_id) REFERENCES comandas(id),
    FOREIGN KEY (produto_id) REFERENCES produtos(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);
CREATE TABLE IF NOT EXISTS vendas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comanda_id INTEGER,
    mesa_id INTEGER,
    usuario_id INTEGER NOT NULL,
    valor_total REAL NOT NULL DEFAULT 0,
    desconto REAL DEFAULT 0,
    forma_pagamento TEXT DEFAULT 'dinheiro',
    data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tipo TEXT NOT NULL DEFAULT 'mesa',
    status TEXT DEFAULT 'finalizada',
    FOREIGN KEY (comanda_id) REFERENCES comandas(id),
    FOREIGN KEY (mesa_id) REFERENCES mesas(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);
CREATE TABLE IF NOT EXISTS itens_venda (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venda_id INTEGER NOT NULL,
    produto_id INTEGER NOT NULL,
    quantidade REAL NOT NULL DEFAULT 1,
    preco_unitario REAL NOT NULL,
    subtotal REAL NOT NULL,
    observacao TEXT,
    FOREIGN KEY (venda_id) REFERENCES vendas(id),
    FOREIGN KEY (produto_id) REFERENCES produtos(id)
);
CREATE TABLE IF NOT EXISTS movimentacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    quantidade REAL NOT NULL,
    motivo TEXT,
    usuario_id INTEGER,
    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    observacao TEXT,
    FOREIGN KEY (produto_id) REFERENCES produtos(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);
CREATE TABLE IF NOT EXISTS fiado (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,
    venda_id INTEGER,
    tipo TEXT NOT NULL DEFAULT 'saida',
    valor REAL NOT NULL,
    valor_pago REAL DEFAULT 0,
    data_vencimento DATE,
    usuario_id INTEGER,
    observacao TEXT,
    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id),
    FOREIGN KEY (venda_id) REFERENCES vendas(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);
CREATE TABLE IF NOT EXISTS contas_pagar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fornecedor TEXT NOT NULL,
    descricao TEXT NOT NULL,
    valor REAL NOT NULL,
    vencimento DATE NOT NULL,
    pagamento DATE,
    status TEXT DEFAULT 'pendente',
    usuario_id INTEGER,
    observacao TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);
CREATE TABLE IF NOT EXISTS suprimento_sangria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caixa_id INTEGER NOT NULL,
    usuario_id INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    valor REAL NOT NULL,
    motivo TEXT,
    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (caixa_id) REFERENCES caixas(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);
CREATE TABLE IF NOT EXISTS historico_transferencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comanda_id INTEGER NOT NULL,
    mesa_origem_id INTEGER NOT NULL,
    mesa_destino_id INTEGER NOT NULL,
    usuario_id INTEGER NOT NULL,
    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    observacao TEXT,
    FOREIGN KEY (comanda_id) REFERENCES comandas(id),
    FOREIGN KEY (mesa_origem_id) REFERENCES mesas(id),
    FOREIGN KEY (mesa_destino_id) REFERENCES mesas(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);
CREATE TABLE IF NOT EXISTS auditoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    usuario_nome TEXT,
    acao TEXT NOT NULL,
    detalhes TEXT,
    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip TEXT,
    user_agent TEXT,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);
CREATE TABLE IF NOT EXISTS login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login TEXT NOT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

conn.executescript(SCHEMA)

now = datetime(2026, 7, 20, 10, 0, 0)

# Empresa
conn.execute(
    "INSERT INTO empresa (razao_social, nome_fantasia, cnpj, inscricao_estadual, endereco, telefone, email, horario_funcionamento) VALUES (?,?,?,?,?,?,?,?)",
    ("Jam's Burguer ME", "JAM'S BURGUER", "12.345.678/0001-99", "123456789",
     "Rua Principal, 100 - Centro", "(44) 99999-0000", "contato@jamsburguer.com.br",
     "Seg-Sex 10:00-23:00, Sab-Dom 10:00-00:00")
)

# Usuarios (admin + 3 funcionarios)
admin_hash = generate_password_hash("Admin@2026#Jam's")
func_hash = generate_password_hash("Func@2026#Sistema")
conn.execute("INSERT INTO usuarios (nome, login, senha, nivel) VALUES (?,?,?,?)", ("Administrador", "admin", admin_hash, "admin"))
conn.execute("INSERT INTO usuarios (nome, login, senha, nivel) VALUES (?,?,?,?)", ("Carlos Silva", "funcionario", func_hash, "funcionario"))
conn.execute("INSERT INTO usuarios (nome, login, senha, nivel) VALUES (?,?,?,?)", ("Ana Souza", "ana", func_hash, "funcionario"))
conn.execute("INSERT INTO usuarios (nome, login, senha, nivel) VALUES (?,?,?,?)", ("Pedro Lima", "pedro", func_hash, "funcionario"))

# Categorias
categorias = [
    "Vinhos", "Whisky", "Vodka", "Gin", "Cervejas", "Refrigerantes",
    "Energeticos", "Agua", "Petiscos", "Porcoes", "Drinks", "Outros"
]
cat_ids = {}
for c in categorias:
    cur = conn.execute("INSERT INTO categorias (nome) VALUES (?)", (c,))
    cat_ids[c] = cur.lastrowid

# Garcons
garcons = ["João Alves", "Maria Ferreira", "Lucas Costa", "Fernanda Ramos", "Rafael Gomes"]
garcom_ids = []
for g in garcons:
    telefone = f"(44) 9{random.randint(1000,9999)}-{random.randint(1000,9999)}"
    cur = conn.execute("INSERT INTO garcons (nome, telefone, comissao) VALUES (?,?,?)",
                       (g, telefone, random.uniform(5, 15)))
    garcom_ids.append(cur.lastrowid)

# Mesas (40 mesas)
mesa_ids = []
for i in range(1, 41):
    cap = random.choice([2, 4, 4, 6, 8])
    cur = conn.execute("INSERT INTO mesas (numero, capacidade, status) VALUES (?,?,?)",
                       (i, cap, "disponivel"))
    mesa_ids.append(cur.lastrowid)

# Produtos (~80 produtos realistas)
produtos_data = [
    ("Cerveja Skol 350ml", "Cervejas", 6.00, 200, 30),
    ("Cerveja Brahma 350ml", "Cervejas", 6.00, 180, 30),
    ("Cerveja Heineken 350ml", "Cervejas", 9.00, 120, 20),
    ("Cerveja Stella Artois 350ml", "Cervejas", 10.00, 80, 15),
    ("Cerveja Amstel 350ml", "Cervejas", 7.00, 100, 20),
    ("Cerveja Original 350ml", "Cervejas", 8.00, 90, 15),
    ("Cerveja Eisenbahn 350ml", "Cervejas", 7.50, 60, 10),
    ("Chopp Brahma 500ml", "Cervejas", 8.00, 50, 10),
    ("Coca-Cola 350ml", "Refrigerantes", 5.00, 150, 30),
    ("Guaraná Antarctica 350ml", "Refrigerantes", 4.50, 120, 30),
    ("Fanta Laranja 350ml", "Refrigerantes", 4.50, 80, 20),
    ("Sprite 350ml", "Refrigerantes", 4.50, 70, 20),
    ("Pepsi 350ml", "Refrigerantes", 4.50, 60, 15),
    ("Guaraná Zero 350ml", "Refrigerantes", 4.50, 50, 10),
    ("Água mineral 500ml", "Agua", 3.00, 200, 40),
    ("Água com gás 500ml", "Agua", 4.00, 80, 15),
    ("Red Bull 250ml", "Energeticos", 8.00, 60, 15),
    ("Monster 473ml", "Energeticos", 10.00, 40, 10),
    ("Vodka Smirnoff 900ml", "Vodka", 65.00, 10, 3),
    ("Vodka Absolut 1L", "Vodka", 120.00, 5, 2),
    ("Gin Gordon's 700ml", "Gin", 85.00, 8, 3),
    ("Gin Tanqueray 700ml", "Gin", 110.00, 5, 2),
    ("Whisky Red Label 1L", "Whisky", 95.00, 8, 3),
    ("Whisky Jack Daniel's 1L", "Whisky", 180.00, 5, 2),
    ("Whisky Jameson 700ml", "Whisky", 140.00, 6, 2),
    ("Vinho Tinto Santa Helena 750ml", "Vinhos", 35.00, 12, 4),
    ("Vinho Branco Miolo 750ml", "Vinhos", 38.00, 8, 3),
    ("Vinho Rosé Aurora 750ml", "Vinhos", 40.00, 6, 2),
    ("Petisco de bolinho de bacalhau (6un)", "Petiscos", 22.00, 0, 0),
    ("Petisco de croquete (4un)", "Petiscos", 18.00, 0, 0),
    ("Petisco de espetinho de frango (4un)", "Petiscos", 20.00, 0, 0),
    ("Porção de batata frita", "Porcoes", 25.00, 0, 0),
    ("Porção de frango à passarinho", "Porcoes", 35.00, 0, 0),
    ("Porção de peixe frito", "Porcoes", 40.00, 0, 0),
    ("Porção de calabresa acebolada", "Porcoes", 30.00, 0, 0),
    ("Porção de mandioca frita", "Porcoes", 22.00, 0, 0),
    ("Porção de picanha (500g)", "Porcoes", 65.00, 0, 0),
    ("Drink Caipirinha", "Drinks", 18.00, 0, 0),
    ("Drink Mojito", "Drinks", 22.00, 0, 0),
    ("Drink Gin Tônica", "Drinks", 20.00, 0, 0),
    ("Drink Cosmopolitan", "Drinks", 25.00, 0, 0),
    ("Drink Old Fashioned", "Drinks", 28.00, 0, 0),
    ("Drink Margarita", "Drinks", 22.00, 0, 0),
    ("Drink Piña Colada", "Drinks", 24.00, 0, 0),
    ("Suco natural de laranja", "Outros", 10.00, 0, 0),
    ("Suco natural de limão", "Outros", 9.00, 0, 0),
    ("Limonada suíça", "Outros", 12.00, 0, 0),
    ("Água de coco", "Outros", 8.00, 30, 10),
    ("Chopp gelado 500ml", "Cervejas", 9.00, 40, 10),
]
produto_ids = []
for nome, cat, preco, estoque, est_min in produtos_data:
    cur = conn.execute(
        "INSERT INTO produtos (nome, categoria_id, preco, estoque, estoque_minimo) VALUES (?,?,?,?,?)",
        (nome, cat_ids[cat], preco, estoque, est_min)
    )
    produto_ids.append(cur.lastrowid)

# Clientes (30 clientes)
clientes_nomes = [
    ("João da Silva", "44999001100", "123.456.789-00"),
    ("Maria Oliveira", "44999002200", "234.567.890-11"),
    ("Pedro Santos", "44999003300", "345.678.901-22"),
    ("Ana Pereira", "44999004400", "456.789.012-33"),
    ("Lucas Costa", "44999005500", "567.890.123-44"),
    ("Juliana Lima", "44999006600", "678.901.234-55"),
    ("Marcos Almeida", "44999007700", "789.012.345-66"),
    ("Fernanda Ribeiro", "44999008800", "890.123.456-77"),
    ("Rafael Martins", "44999009900", "901.234.567-88"),
    ("Camila Rodrigues", "44999100000", "012.345.678-99"),
    ("Bruno Ferreira", "44999101100", "111.222.333-44"),
    ("Patricia Araujo", "44999102200", "222.333.444-55"),
    ("Thiago Melo", "44999103300", "333.444.555-66"),
    ("Amanda Barbosa", "44999104400", "444.555.666-77"),
    ("Felipe Gomes", "44999105500", "555.666.777-88"),
    ("Renata Dias", "44999106600", "666.777.888-99"),
    ("Diego Carvalho", "44999107700", "777.888.999-00"),
    ("Isabela Nunes", "44999108800", "888.999.000-11"),
    ("Gustavo Ramos", "44999109900", "999.000.111-22"),
    ("Bianca Correia", "44999200000", "000.111.222-33"),
    ("Eduardo Pires", "44999201100", "112.233.445-56"),
    ("Letícia Campos", "44999202200", "223.344.556-67"),
    ("Marcelo Teixeira", "44999203300", "334.455.667-78"),
    ("Tatiane Lopes", "44999204400", "445.566.778-89"),
    ("Anderson Vieira", "44999205500", "556.677.889-90"),
    ("Priscila Monteiro", "44999206600", "667.788.990-01"),
    ("Fábio Nascimento", "44999207700", "778.899.001-12"),
    ("Gabriela Freitas", "44999208800", "889.900.112-23"),
    ("Roberto Sampaio", "44999209900", "990.011.223-34"),
    ("Vanessa Cardoso", "44999300000", "001.122.334-45"),
]
cliente_ids = []
for nome, tel, cpf in clientes_nomes:
    limite = random.choice([300, 500, 800, 1000, 1500])
    cur = conn.execute(
        "INSERT INTO clientes (nome, telefone, cpf, limite_fiado, saldo_devedor) VALUES (?,?,?,?,?)",
        (nome, tel, cpf, limite, 0)
    )
    cliente_ids.append(cur.lastrowid)

# Gerar vendas nos ultimos 7 dias
FORMAS = ["dinheiro", "cartao_credito", "cartao_debito", "pix", "fiado"]
STATUSES_VENDA = ["finalizada", "finalizada", "finalizada", "cancelada"]

caixa_user_id = 2  # Carlos

for day_offset in range(7):
    day = now - timedelta(days=day_offset)
    n_vendas = random.randint(8, 25)

    # Abrir caixa no dia
    caixa_abertura = day.replace(hour=10, minute=0, second=0)
    caixa_fechamento = day.replace(hour=23, minute=30, second=0)
    valor_inicial = 200.00
    cur = conn.execute(
        "INSERT INTO caixas (usuario_id, abertura, fechamento, valor_inicial, valor_final, total_vendas, quantidade_vendas) VALUES (?,?,?,?,?,?,?)",
        (caixa_user_id, caixa_abertura.isoformat(), caixa_fechamento.isoformat(),
         valor_inicial, 0, 0, 0)
    )
    caixa_id = cur.lastrowid
    caixa_total = 0
    caixa_qtd = 0

    for vi in range(n_vendas):
        hora_venda = day.replace(hour=random.randint(10, 22), minute=random.randint(0, 59))
        mesa_idx = random.randint(0, len(mesa_ids) - 1)
        mesa_id = mesa_ids[mesa_idx]
        usuario_id = random.choice([2, 3, 4])
        garcom_id = random.choice(garcom_ids)
        forma = random.choice(FORMAS)
        status_venda = random.choice(STATUSES_VENDA)
        tipo_venda = "mesa"

        # Criar comanda
        cur = conn.execute(
            "INSERT INTO comandas (mesa_id, usuario_id, garcom_id, abertura, fechamento, status) VALUES (?,?,?,?,?,?)",
            (mesa_id, usuario_id, garcom_id, hora_venda.isoformat(),
             (hora_venda + timedelta(minutes=random.randint(20, 90))).isoformat(),
             "fechada" if status_venda == "finalizada" else "cancelada")
        )
        comanda_id = cur.lastrowid

        # Itens da comanda (1 a 6 itens)
        n_itens = random.randint(1, 6)
        valor_total = 0
        for _ in range(n_itens):
            prod_idx = random.randint(0, len(produto_ids) - 1)
            prod_id = produto_ids[prod_idx]
            preco = produtos_data[prod_idx][2]
            qtd = random.choice([1, 1, 1, 2, 2, 3])
            subtotal = preco * qtd
            valor_total += subtotal

            conn.execute(
                "INSERT INTO itens_comanda (comanda_id, produto_id, quantidade, preco_unitario, subtotal, usuario_id) VALUES (?,?,?,?,?,?)",
                (comanda_id, prod_id, qtd, preco, subtotal, usuario_id)
            )

            # Movimentacao de estoque
            conn.execute(
                "INSERT INTO movimentacoes (produto_id, tipo, quantidade, motivo, usuario_id, data_hora) VALUES (?,?,?,?,?,?)",
                (prod_id, "saida", qtd, f"Venda - Comanda #{comanda_id}", usuario_id, hora_venda.isoformat())
            )

        desconto = 0
        if random.random() < 0.05:
            desconto = round(valor_total * random.uniform(0.05, 0.15), 2)

        # Criar venda
        cur = conn.execute(
            "INSERT INTO vendas (comanda_id, mesa_id, usuario_id, valor_total, desconto, forma_pagamento, data, tipo, status) VALUES (?,?,?,?,?,?,?,?,?)",
            (comanda_id, mesa_id, usuario_id, round(valor_total - desconto, 2), desconto,
             forma, hora_venda.isoformat(), tipo_venda, status_venda)
        )
        venda_id = cur.lastrowid

        # Itens da venda (espelhar itens comanda)
        conn.execute(
            "INSERT INTO itens_venda (venda_id, produto_id, quantidade, preco_unitario, subtotal) SELECT ?, produto_id, quantidade, preco_unitario, subtotal FROM itens_comanda WHERE comanda_id=?",
            (venda_id, comanda_id)
        )

        if status_venda == "finalizada":
            caixa_total += valor_total - desconto
            caixa_qtd += 1

    # Fechar caixa
    conn.execute(
        "UPDATE caixas SET total_vendas=?, quantidade_vendas=?, valor_final=?, diferenca=? WHERE id=?",
        (round(caixa_total, 2), caixa_qtd, round(valor_inicial + caixa_total, 2),
         round(random.uniform(-5, 5), 2), caixa_id)
    )

    # Suprimento/sangria (0-2 por dia)
    for _ in range(random.randint(0, 2)):
        tipo_ss = random.choice(["suprimento", "sangria"])
        valor_ss = round(random.uniform(20, 200), 2)
        motivo_ss = "Troco" if tipo_ss == "suprimento" else "Sangria de caixa"
        conn.execute(
            "INSERT INTO suprimento_sangria (caixa_id, usuario_id, tipo, valor, motivo, data_hora) VALUES (?,?,?,?,?,?)",
            (caixa_id, usuario_id, tipo_ss, valor_ss, motivo_ss, hora_venda.isoformat())
        )

# Fiados (alguns clientes devendo)
fiado_venda_ids = [vid for vid, in conn.execute("SELECT id FROM vendas WHERE forma_pagamento='fiado' AND status='finalizada'").fetchall()][:15]
for vid in fiado_venda_ids:
    venda = conn.execute("SELECT usuario_id, valor_total FROM vendas WHERE id=?", (vid,)).fetchone()
    cliente_id = random.choice(cliente_ids)
    data_venda = conn.execute("SELECT data FROM vendas WHERE id=?", (vid,)).fetchone()[0]
    vencimento = (datetime.fromisoformat(data_venda) + timedelta(days=30)).date().isoformat()
    valor_pago = round(venda[1] * random.uniform(0, 1), 2) if random.random() < 0.3 else 0
    conn.execute(
        "INSERT INTO fiado (cliente_id, venda_id, tipo, valor, valor_pago, data_vencimento, usuario_id) VALUES (?,?,?,?,?,?,?)",
        (cliente_id, vid, "saida", venda[1], valor_pago, vencimento, venda[0])
    )
    if valor_pago == 0:
        conn.execute(
            "UPDATE clientes SET saldo_devedor = saldo_devedor + ? WHERE id=?",
            (venda[1], cliente_id)
        )

# Contas a pagar
fornecedores = [
    ("Cervejaria Central", "Entrega de cervejas - Jul/2026", 2500.00, "2026-07-25"),
    ("Distribuidora Bebidas Ltda", "Refrigerantes e águas", 1200.00, "2026-07-28"),
    ("Frigorífico Boi Gordo", "Carnes para porções", 3800.00, "2026-07-30"),
    ("Hortifruti Verdão", "Frutas e verduras frescas", 800.00, "2026-08-01"),
    ("Empório dos Vinhos", "Vinhos importados", 1500.00, "2026-08-05"),
    ("Limpe Total Ltda", "Produtos de limpeza", 350.00, "2026-08-10"),
    ("Seguradora Protege", "Seguro do estabelecimento", 450.00, "2026-08-15"),
    ("Aluguel Imóvel Comercial", "Aluguel julho", 3500.00, "2026-07-10"),
    ("Eletropaulo", "Conta de luz julho", 1200.00, "2026-07-20"),
    ("Sanasa", "Conta de água julho", 280.00, "2026-07-18"),
]
for forn, desc, valor, venc in fornecedores:
    status = "pago" if venc < "2026-07-22" else random.choice(["pendente", "pendente", "atrasada" if venc < "2026-07-24" else "pendente"])
    pagamento = venc if status == "pago" else None
    conn.execute(
        "INSERT INTO contas_pagar (fornecedor, descricao, valor, vencimento, pagamento, status, usuario_id) VALUES (?,?,?,?,?,?,?)",
        (forn, desc, valor, venc, pagamento, status, 1)
    )

# Historico de transferencias (2-3)
for _ in range(random.randint(2, 3)):
    com = random.choice(conn.execute("SELECT id FROM comandas LIMIT 5").fetchall())
    orig = random.choice(mesa_ids[:10])
    dest = random.choice(mesa_ids[10:20])
    if orig != dest:
        conn.execute(
            "INSERT INTO historico_transferencias (comanda_id, mesa_origem_id, mesa_destino_id, usuario_id, observacao) VALUES (?,?,?,?,?)",
            (com[0], orig, dest, 2, "Transferencia solicitada pelo cliente")
        )

# Auditoria (alguns registros)
acoes = [
    ("LOGIN", "Login realizado com sucesso"),
    ("VENDA_CRIADA", "Nova venda registrada"),
    ("CAIXA_ABERTO", "Caixa aberto com R$ 200,00"),
    ("CAIXA_FECHADO", "Caixa fechado"),
    ("CLIENTE_CRIADO", "Novo cliente cadastrado"),
    ("PRODUTO_ALTERADO", "Preço de produto alterado"),
]
for _ in range(20):
    acao, detalhe = random.choice(acoes)
    conn.execute(
        "INSERT INTO auditoria (usuario_id, usuario_nome, acao, detalhes, data_hora, ip) VALUES (?,?,?,?,?,?)",
        (random.choice([1, 2, 3, 4]), ["Administrador", "Carlos", "Ana", "Pedro"][random.randint(0, 3)],
         acao, detalhe, (now - timedelta(days=random.randint(0, 7), hours=random.randint(0, 23))).isoformat(),
         "192.168.1." + str(random.randint(100, 200)))
    )

conn.commit()

# Contagens finais
print("=== BANCO FONTE CRIADO COM SUCESSO ===")
print(f"Caminho: {DB_PATH}")
tabelas = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
total = 0
for (t,) in tabelas:
    c = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    if c > 0:
        print(f"  {t}: {c}")
    total += c
print(f"  TOTAL: {total} registros")
size = os.path.getsize(DB_PATH)
print(f"  Tamanho: {size/1024:.1f} KB")
conn.close()
