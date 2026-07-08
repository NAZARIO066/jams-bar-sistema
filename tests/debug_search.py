import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app import app

with app.test_client() as c:
    r = c.get('/login')
    match = re.search(rb'value="([a-f0-9]+)"', r.data)
    csrf = match.group(1).decode()
    c.post('/login', data={'login':'admin','senha':"Admin@2026#Jam's",'_csrf_token':csrf})
    
    r = c.get('/api/buscar_produto?q=CERVEJA')
    data = r.get_json()
    print('CERVEJA:', len(data), 'resultados')
    for p in data[:5]:
        print(f"  {p['nome']}")
    
    r = c.get('/api/buscar_produto?q=Heineken')
    data = r.get_json()
    print('Heineken:', len(data), 'resultados')
    for p in data:
        print(f"  {p['nome']}")
    
    r = c.get('/api/buscar_produto?q=cerveja')
    data = r.get_json()
    print('cerveja (lower):', len(data), 'resultados')
    for p in data[:5]:
        print(f"  {p['nome']}")
    
    r = c.get('/api/produtos/mais_vendidos')
    data = r.get_json()
    print('Mais vendidos:', len(data), 'resultados')
    for p in data:
        print(f"  {p['nome']} - {p['total_vendido']} vendidos")
