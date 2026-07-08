import sqlite3
from datetime import date, timedelta

con = sqlite3.connect("bar_adega.db")
con.row_factory = sqlite3.Row
c = con.cursor()

print("=== ANTES ===")
print("Total fiados:", c.execute("SELECT COUNT(*) FROM fiado").fetchone()[0])
print("Com data_vencimento:", c.execute("SELECT COUNT(*) FROM fiado WHERE data_vencimento IS NOT NULL").fetchone()[0])
print("Sem data_vencimento:", c.execute("SELECT COUNT(*) FROM fiado WHERE data_vencimento IS NULL").fetchone()[0])

# Apaga todos os fiados
c.execute("DELETE FROM fiado")
print("\nFiados apagados.")

# Cria 17 fiados com datas variadas
FIADOS = [
    ("Maria Oliveira", 89.90, -3),
    ("Ana Pereira", 150.00, -7),
    ("Marcos Almeida", 200.00, -1),
    ("Ana Pereira", 100.00, 2),
    ("Diego Fernandes", 75.00, 5),
    ("Fernanda Lima", 80.00, 4),
    ("Marcos Almeida", 120.00, 8),
    ("João da Silva", 250.00, 10),
    ("Lucas Mendes", 180.00, 7),
    ("Fernanda Lima", 120.00, 20),
    ("Pedro Santos", 300.00, 25),
    ("Camila Ribeiro", 90.00, 15),
    ("Bruno Carvalho", 500.00, 30),
    ("Patrícia Vieira", 220.00, 18),
    ("Juliana Rocha", 150.00, 22),
    ("Rafael Costa", 100.00, 14),
    ("Larissa Martins", 80.00, 28),
]
for nome, valor, dias in FIADOS:
    cli = c.execute("SELECT id FROM clientes WHERE nome=?", (nome,)).fetchone()
    if not cli:
        print(f"  Cliente nao encontrado: {nome}")
        continue
    venc = (date.today() + timedelta(days=dias)).isoformat()
    c.execute(
        "INSERT INTO fiado (cliente_id, tipo, valor, data_vencimento) VALUES (?,?,?,?)",
        (cli["id"], "compra", valor, venc)
    )
    print(f"  + {nome} R$ {valor} venc {venc}")

# Atualiza saldo_devedor
c.execute("""
    UPDATE clientes SET saldo_devedor = COALESCE((
        SELECT SUM(valor - valor_pago) FROM fiado
        WHERE fiado.cliente_id = clientes.id AND tipo='compra'
    ), 0)
""")
con.commit()

print("\n=== DEPOIS ===")
print("Total fiados:", c.execute("SELECT COUNT(*) FROM fiado").fetchone()[0])
print("Com data_vencimento:", c.execute("SELECT COUNT(*) FROM fiado WHERE data_vencimento IS NOT NULL").fetchone()[0])

print("\nClientes com saldo:")
for cli in c.execute("SELECT nome, saldo_devedor FROM clientes WHERE saldo_devedor > 0 ORDER BY nome"):
    print(f"  {cli['nome']}: R$ {cli['saldo_devedor']}")

con.close()
print("\nPRONTO! Atualize a pagina no navegador.")
