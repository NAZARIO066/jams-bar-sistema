import re, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

client = app.test_client()
errors = []

def login(user="admin", pwd=None):
    if pwd is None:
        pwd = os.environ.get("ADMIN_SENHA", "admin")
    r = client.get("/login")
    m = re.search(rb'name="_csrf_token"\s+value="([^"]+)"', r.data)
    csrf = m.group(1).decode() if m else ""
    r = client.post("/login", data={"login": user, "senha": pwd, "_csrf_token": csrf})
    return r.status_code in (302, 200)

def api(method, path, data=None):
    if method == "GET":
        return client.get(path)
    elif method == "POST":
        return client.post(path, json=data)
    elif method == "PUT":
        return client.put(path, json=data)
    elif method == "DELETE":
        return client.delete(path)

def check(label, r, expect=200):
    status = r.status_code
    try:
        d = r.get_json()
        detail = json.dumps(d, ensure_ascii=False)[:200]
    except:
        detail = r.get_data(as_text=True)[:100].replace("\n"," ")
    ok = status == expect
    icon = "OK" if ok else "FAIL"
    print(f"  [{icon}] {label}: HTTP {status} | {detail}")
    if not ok:
        errors.append(f"{label}: expected {expect} got {status}")
    try:
        return r.get_json() or {}
    except:
        return {}

print("=" * 60)
print("  HOMOLOGACAO COMPLETA - DIA DE OPERACAO")
print("=" * 60)

# LOGIN
print("\n--- LOGIN ---")
ok = login()
print(f"  Login admin: {'OK' if ok else 'FALHA'}")
if not ok:
    print("  ABORT"); sys.exit(1)

# C1: Abertura de caixa
print("\n--- C1: ABERTURA DE CAIXA ---")
check("C1: Abrir caixa R$500", api("POST", "/api/caixa/abrir", {"valor_inicial": 500.00}))

# C2: Cadastro de cliente
print("\n--- C2: CADASTRO CLIENTE ---")
check("C2: Cadastrar cliente", api("POST", "/api/clientes", {
    "nome": "Carlos Homologacao", "telefone": "44999999999",
    "cpf": "12345678900", "limite_fiado": 500.00
}))

# C3: Cadastro de produtos
print("\n--- C3: CADASTRO PRODUTOS ---")
check("C3a: Categoria", api("POST", "/api/categorias", {"nome": "Cervejas Homologacao"}))
cats = api("GET", "/api/categorias").get_json()
cat_id = cats[-1]["id"] if cats else None
check("C3b: Brahma 600ml R$8", api("POST", "/api/produtos", {
    "nome": "Brahma 600ml H", "categoria_id": cat_id,
    "codigo_barras": "HOM001", "preco": 8.00, "estoque": 0,
    "estoque_minimo": 10, "unidade": "UN"
}))
check("C3c: Amstel 600ml R$9", api("POST", "/api/produtos", {
    "nome": "Amstel 600ml H", "categoria_id": cat_id,
    "preco": 9.00, "estoque": 0, "estoque_minimo": 10, "unidade": "UN"
}))
prods = api("GET", "/api/produtos").get_json()
brahma_id = next((p["id"] for p in prods if p["nome"] == "Brahma 600ml H"), None)
amstel_id = next((p["id"] for p in prods if p["nome"] == "Amstel 600ml H"), None)
print(f"  brahma_id={brahma_id}, amstel_id={amstel_id}")

# C4: Entrada de estoque
print("\n--- C4: ENTRADA ESTOQUE ---")
check("C4a: +50 Brahma", api("POST", "/api/estoque/entrada", {"produto_id": brahma_id, "quantidade": 50}))
check("C4b: +30 Amstel", api("POST", "/api/estoque/entrada", {"produto_id": amstel_id, "quantidade": 30}))
est = api("GET", "/api/estoque").get_json()
b = next((e for e in est if e["nome"] == "Brahma 600ml H"), None)
a = next((e for e in est if e["nome"] == "Amstel 600ml H"), None)
print(f"  Estoque: Brahma={b['estoque'] if b else '?'} | Amstel={a['estoque'] if a else '?'}")

# C5: Venda balcao
print("\n--- C5: VENDA BALCAO ---")
d = check("C5: Venda 2B+1A Dinheiro", api("POST", "/api/venda/direta", {
    "itens": [{"produto_id": brahma_id, "quantidade": 2}, {"produto_id": amstel_id, "quantidade": 1}],
    "forma_pagamento": "Dinheiro"
}))
venda_id = d.get("venda_id")
print(f"  Venda #{venda_id} Total=R${d.get('total',0):.2f}")
est = api("GET", "/api/estoque").get_json()
b = next((e for e in est if e["nome"] == "Brahma 600ml H"), None)
a = next((e for e in est if e["nome"] == "Amstel 600ml H"), None)
print(f"  Estoque pos-venda: Brahma={b['estoque'] if b else '?'} | Amstel={a['estoque'] if a else '?'}")
if b and b["estoque"] != 48:
    errors.append(f"Estoque Brahma esperado 48, got {b['estoque']}")
if a and a["estoque"] != 29:
    errors.append(f"Estoque Amstel esperado 29, got {a['estoque']}")

# C6: Abrir mesa
print("\n--- C6-C14: MESA + COMANDA + PAGAMENTOS ---")
mesas = api("GET", "/api/mesas").get_json()
mesa = next((m for m in mesas if m["status"] == "disponivel"), None)
if not mesa:
    print("  ERRO: Nenhuma mesa disponivel!"); errors.append("Nenhuma mesa")
else:
    mesa_id = mesa["id"]
    mesa_num = mesa["numero"]
    check(f"C6: Abrir mesa {mesa_num}", api("POST", f"/api/mesas/{mesa_id}/abrir", {"cliente_nome": "Carlos Homologacao"}))

    md = api("GET", "/api/mesas").get_json()
    mi = next((m for m in md if m["id"] == mesa_id), None)
    comanda_id = mi.get("comanda_id") if mi else None
    print(f"  Comanda #{comanda_id}")

    # C7
    print("\n--- C7: ITENS NA MESA ---")
    check("C7a: +3 Brahma", api("POST", f"/api/comanda/{comanda_id}/adicionar", {"produto_id": brahma_id, "quantidade": 3}))
    check("C7b: +2 Amstel", api("POST", f"/api/comanda/{comanda_id}/adicionar", {"produto_id": amstel_id, "quantidade": 2}))
    det = api("GET", f"/api/comanda/{comanda_id}").get_json()
    # total Esperado: 3*8 + 2*9 = 42
    print(f"  Itens: {len(det['itens'])} | Total: R${det['total']:.2f}")
    if abs(det["total"] - 42.0) > 0.01:
        errors.append(f"Total mesa esperado 42, got {det['total']}")
    for it in det["itens"]:
        print(f"    - {it['quantidade']}x {it['produto_nome']} = R${it['subtotal']:.2f}")

    # C8: Impressao comanda
    print("\n--- C8: IMPRESSAO COMANDA ---")
    r = api("GET", f"/imprimir/comanda/{comanda_id}")
    print(f"  HTTP {r.status_code} | {len(r.get_data())} bytes")
    if r.status_code != 200:
        errors.append(f"Impressao comanda: {r.status_code}")
    html = r.get_data(as_text=True)
    if "garcom" in html.lower() or "garçom" in html.lower():
        errors.append("REF_GARCOM na comanda!")
        print("  *** ALERTA: referencia a garcom encontrada! ***")

    # C9: Pagamento parcial
    print("\n--- C9: PAGAMENTO PARCIAL ---")
    item0_id = det["itens"][0]["id"]
    d = check("C9: Parcial 1 Brahma (R$8)", api("POST", f"/api/comanda/{comanda_id}/pagamento_parcial", {
        "itens": [{"item_id": item0_id, "quantidade": 1}],
        "forma_pagamento": "Dinheiro", "nome_pessoa": "Carlos"
    }))
    if d.get("restante") is not None:
        print(f"  Restante apos parcial: R${d['restante']:.2f}")
        if abs(d["restante"] - 34.0) > 0.01:
            errors.append(f"Restante pos-parcial esperado 34, got {d['restante']}")
    pgs = api("GET", f"/api/comanda/{comanda_id}/pagamentos").get_json()
    print(f"  Pago: R${pgs['total_pago']:.2f} | Restante: R${pgs['restante']:.2f}")

    # C10: Fechar mesa
    print("\n--- C10: FECHAR MESA (DINHEIRO) ---")
    d = check("C10: Fechar mesa", api("POST", f"/api/mesas/{mesa_id}/fechar", {"desconto": 0, "forma_pagamento": "Dinheiro"}))
    print(f"  Venda #{d.get('venda_id')} Total: R${d.get('total',0):.2f}")

# C11: Venda PIX
print("\n--- C11: VENDA PIX ---")
d = check("C11: Venda PIX 1 Brahma", api("POST", "/api/venda/direta", {
    "itens": [{"produto_id": brahma_id, "quantidade": 1}], "forma_pagamento": "PIX"
}))
print(f"  Venda PIX #{d.get('venda_id')} R${d.get('total',0):.2f}")

# C12: Venda Cartao Credito
print("\n--- C12: VENDA CARTAO CREDITO ---")
d = check("C12: Venda Credito 1 Amstel", api("POST", "/api/venda/direta", {
    "itens": [{"produto_id": amstel_id, "quantidade": 1}], "forma_pagamento": "Credito"
}))
print(f"  Venda Credito #{d.get('venda_id')} R${d.get('total',0):.2f}")

# C13: Venda Fiado
print("\n--- C13: VENDA FIADO ---")
clientes_resp = api("GET", "/api/clientes").get_json()
cli_list = clientes_resp if isinstance(clientes_resp, list) else clientes_resp.get("data", [])
cli = next((c for c in cli_list if c["nome"] == "Carlos Homologacao"), None)
if cli:
    d = check("C13: Venda Fiado 2 Brahma", api("POST", "/api/venda/direta", {
        "itens": [{"produto_id": brahma_id, "quantidade": 2}],
        "forma_pagamento": "Fiado", "cliente_id": cli["id"], "dias_vencimento": 30
    }))
    print(f"  Venda Fiado #{d.get('venda_id')} R${d.get('total',0):.2f}")
    fiado = api("GET", f"/api/clientes/{cli['id']}/fiado").get_json()
    saldo = fiado.get("cliente", {}).get("saldo_devedor", 0)
    print(f"  Saldo devedor: R${saldo:.2f}")
    if abs(saldo - 16.0) > 0.01:
        errors.append(f"Saldo devedor esperado 16, got {saldo}")
else:
    print("  SKIP: cliente nao encontrado")

# C14: Mesa 2 PIX
print("\n--- C14: MESA 2 (PIX) ---")
mesas = api("GET", "/api/mesas").get_json()
mesa2 = next((m for m in mesas if m["status"] == "disponivel"), None)
if mesa2:
    check(f"C14a: Abrir mesa {mesa2['numero']}", api("POST", f"/api/mesas/{mesa2['id']}/abrir", {"cliente_nome": ""}))
    md2 = api("GET", "/api/mesas").get_json()
    mi2 = next((m for m in md2 if m["id"] == mesa2["id"]), None)
    c2 = mi2.get("comanda_id")
    check("C14b: +1 Brahma", api("POST", f"/api/comanda/{c2}/adicionar", {"produto_id": brahma_id, "quantidade": 1}))
    check("C14c: +1 Amstel", api("POST", f"/api/comanda/{c2}/adicionar", {"produto_id": amstel_id, "quantidade": 1}))
    d = check("C14d: Fechar mesa PIX", api("POST", f"/api/mesas/{mesa2['id']}/fechar", {"desconto": 0, "forma_pagamento": "PIX"}))
    print(f"  Venda PIX mesa #{d.get('venda_id')} R${d.get('total',0):.2f}")

# C15: Comprovante
print("\n--- C15: COMPROVANTE VENDA ---")
vl = api("GET", "/api/relatorios/vendas?inicio=2026-01-01&fim=2026-12-31").get_json()
vendas = vl.get("vendas", [])
if vendas:
    vid = vendas[0]["id"]
    r = api("GET", f"/imprimir/venda/{vid}")
    print(f"  Venda #{vid}: HTTP {r.status_code} ({len(r.get_data())} bytes)")

# C16-C18
print("\n--- C16: SANGRIA ---")
check("C16: Sangria R$50", api("POST", "/api/caixa/sangria", {"valor": 50.00, "motivo": "Sangria homologacao"}))

print("\n--- C17: SUPRIMENTO ---")
check("C17: Suprimento R$150", api("POST", "/api/caixa/suprimento", {"valor": 150.00, "motivo": "Suprimento homologacao"}))

movs = api("GET", "/api/caixa/movimentacoes").get_json()
print(f"  Movimentacoes: {len(movs)} registros")

print("\n--- C18: FECHAR CAIXA ---")
cx = api("GET", "/api/caixa/status").get_json()
vt = cx.get("vendas_hoje", {}).get("total", 0)
esp = 500 + 150 - 50 + vt
print(f"  Vendas hoje: R${vt:.2f} | Esperado caixa: R${esp:.2f}")
d = check("C18: Fechar caixa", api("POST", "/api/caixa/fechar", {"valor_final": esp, "observacao": "Fechamento homologacao"}))

# C19: Relatorios A4
print("\n--- C19: RELATORIOS A4 ---")
reports = [
    ("vendas", "inicio=2026-01-01&fim=2026-12-31"),
    ("mesas", ""),
    ("produtos", ""),
    ("vendas_produto", "inicio=2026-01-01&fim=2026-12-31"),
    ("vendas_categoria", "inicio=2026-01-01&fim=2026-12-31"),
    ("fluxo_caixa", "inicio=2026-01-01&fim=2026-12-31"),
    ("sangrias", "inicio=2026-01-01&fim=2026-12-31"),
    ("suprimentos", "inicio=2026-01-01&fim=2026-12-31"),
    ("estoque", ""),
    ("produtos_cadastro", ""),
    ("clientes", ""),
    ("contas_pagar", ""),
    ("caixa", ""),
]
for tipo, params in reports:
    url = f"/imprimir/relatorio/{tipo}" + (f"?{params}" if params else "")
    r = api("GET", url)
    icon = "OK" if r.status_code == 200 else f"FAIL({r.status_code})"
    html = r.get_data(as_text=True)
    gc = " [GARCOM!]" if ("garcom" in html.lower() or "garçom" in html.lower()) else ""
    print(f"  /imprimir/relatorio/{tipo}: {icon}{gc}")
    if r.status_code != 200:
        errors.append(f"Relatorio {tipo}: {r.status_code}")
    if gc:
        errors.append(f"REF_GARCOM no relatorio {tipo}")

# Comprovante mesa
md = api("GET", "/api/mesas").get_json()
for m in md:
    if m.get("comanda_id"):
        r = api("GET", f"/imprimir/mesa/{m['comanda_id']}")
        print(f"  /imprimir/mesa/{m['comanda_id']}: {'OK' if r.status_code == 200 else 'FAIL'}")
        break

# Parcial
pgs_resp = api("GET", f"/api/comanda/{comanda_id}/pagamentos").get_json()
if pgs_resp.get("pagamentos"):
    pid = pgs_resp["pagamentos"][0]["id"]
    r = api("GET", f"/imprimir/parcial/{pid}")
    print(f"  /imprimir/parcial/{pid}: {'OK' if r.status_code == 200 else 'FAIL'}")

# =====================================================
print("\n" + "=" * 60)
print("  VALIDACAO: ALERT/PROMPT NAS PAGINAS")
print("=" * 60)
pages = ["/relatorios", "/estoque", "/clientes", "/produtos", "/caixa", "/contas_pagar", "/mesas", "/vendas"]
for page in pages:
    r = api("GET", page)
    if r.status_code == 200:
        html = r.get_data(as_text=True)
        has_alert = "alert(" in html
        has_prompt = "prompt(" in html
        flags = []
        if has_alert: flags.append("ALERT")
        if has_prompt: flags.append("PROMPT")
        if flags:
            print(f"  {page}: {' '.join(flags)} encontrado(s)")
        else:
            print(f"  {page}: limpo")
    else:
        print(f"  {page}: HTTP {r.status_code}")

# =====================================================
print("\n" + "=" * 60)
if errors:
    print(f"  PROBLEMAS ENCONTRADOS: {len(errors)}")
    for e in errors:
        print(f"    - {e}")
else:
    print("  HOMOLOGACAO COMPLETA: SISTEMA HOMOLOGADO")
print("=" * 60)
