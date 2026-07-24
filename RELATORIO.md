# SISTEMA DE GESTÃO PARA BAR, ADEGA E MESAS — RELATÓRIO TÉCNICO

## 1. VISÃO GERAL

Sistema web completo para gestão de bar/adega/distribuidora com:
- **PDV** (balcão) + **controle de mesas e comandas** + **estoque** + **clientes/fiado** + **caixa** + **relatórios** + **auditoria**
- App mobile do administrador está planejado (não implementado)
- Sistema pronto, funcional, rodando localmente com dados de teste

## 2. STACK TÉCNICA

| Camada | Tecnologia |
|--------|-----------|
| Backend | **Flask (Python 3)** — monolitico, rotas modulares em `routes/` |
| Banco | **SQLite** (`bar_adega.db`) — sem dependência de servidor |
| Frontend | **HTML + CSS + JS** com **Tailwind CSS** (via CDN), **Chart.js**, **html5-qrcode** |
| Auth | Sessões Flask nativas + hash bcrypt + decorators `@login_required` / `@admin_required` |
| Testes | **pytest** (~30 testes de API e rotas) |

## 3. ESTRUTURA DE DIRETÓRIOS

```
├── app.py               # Entry point + rotas
├── auth.py               # Login, decorators, auditoria
├── config.py             # Config SECRET_KEY, DB
├── database.py           # Schema SQLite (~18 tabelas)
├── seed.py               # Seed de 25 produtos, 15 clientes, 20+ mesas
├── requirements.txt      # Flask, Werkzeug, python-dotenv, pytest
├── bar_adega.db          # Banco SQLite (gerado automático)
│
├── routes/               # 10 módulos de rotas
│   ├── auth_routes.py
│   ├── dashboard_routes.py
│   ├── mesas_routes.py
│   ├── vendas_routes.py
│   ├── produtos_routes.py
│   ├── estoque_routes.py
│   ├── clientes_routes.py
│   ├── caixa_routes.py
│   ├── admin_routes.py
│   └── relatorios_routes.py
│
├── services/             # Lógica de negócio
│   ├── venda_service.py
│   ├── estoque_service.py
│   └── fiado_service.py
│
├── templates/            # 15 templates Jinja2
├── static/css/           # style.css (tema claro/escuro)
├── tests/                # test_api.py
└── scripts/fix.py        # Script auxiliar
```

## 4. TABELAS DO BANCO (18 tabelas no total)

- `usuarios` — admin, funcionário (níveis, senha hash)
- `mesas` — 20-40 mesas (disponivel, ocupada, reservada, fechando)
- `comandas` + `itens_comanda` — consumo por mesa
- `categorias` — 12 categorias (Vinhos, Cervejas, Whisky, etc.)
- `produtos` — ~25 produtos com código de barras, estoque, preço
- `vendas` + `itens_venda` — vendas diretas e por mesa
- `movimentacoes` — entrada/saída de estoque
- `caixas` + `suprimento_sangria` — abertura/fechamento de caixa
- `clientes` + `fiado` — módulo completo de fiado (compra/pagamento FIFO)
- `auditoria` — log completo de ações (IP, user-agent)
- `garcons` — garçons com comissão
- `contas_pagar` — contas a pagar do estabelecimento
- `historico_transferencias` — transferência de itens entre mesas
- `login_attempts` — rate limiting de login

## 5. FUNCIONALIDADES IMPLEMENTADAS

**Módulo PDV:**
- Carrinho de compras, desconto, múltiplas formas de pagamento
- Integração com fiado (venda fiada com seleção de cliente)
- Leitor de código de barras via webcam (html5-qrcode)

**Módulo Mesas:**
- Mapa visual de 20-40 mesas com status colorido
- Abrir mesa com nome do cliente, adicionar/remover itens
- Fechar conta → gera venda automaticamente + baixa estoque

**Módulo Estoque:**
- Entrada e saída com motivo (Venda, Perda, Quebra, Consumo, Ajuste)
- Alertas automáticos de estoque crítico/zerado (toast + modal)

**Módulo Fiado:**
- CRUD clientes com limite de crédito
- Baixa FIFO (quita os mais antigos primeiro)
- Status colorido: 🟢 Em dia / 🟡 Alerta (5d) / 🟣 Atenção (10d) / 🔴 Vencido
- Bloqueio automático se cliente tem fiado vencido

**Dashboard:**
- 8 KPIs (faturamento dia/mês, mesas ocupadas, ticket médio, etc.)
- 4 gráficos Chart.js (vendas por hora, por dia, top produtos, ocupação)
- Atualização automática a cada 8s (polling)

**Caixa:**
- Abertura/fechamento com valor inicial, total vendas, diferenças
- Suprimento e sangria

**Relatórios:**
- Vendas (hoje/ontem/semana/mês/período customizado)
- Por mesa, por garçom, por categoria, fluxo de caixa
- Top produtos mais/menos vendidos

**Admin:**
- CRUD usuários, CRUD garçons, contas a pagar
- Auditoria completa (todas ações sensíveis registradas)

## 6. O QUE FALTA IMPLEMENTAR

| Funcionalidade | Prioridade |
|---------------|-----------|
| Impressão térmica (ESC/POS, 80mm/P98) | Alta |
| Exportar relatórios PDF/Excel | Média |
| WebSocket (substituir polling por tempo real) | Média |
| Backup automático diário | Média |
| App mobile administrador (React Native/Flutter) | Baixa |
| Notificações push (FCM) | Baixa |

## 7. CREDENCIAIS DE TESTE

> As credenciais estão definidas no `seed.py`. Consulte o arquivo para os valores atuais.

## 8. COMO RODA HOJE

```powershell
python app.py
# Acessa em http://localhost:5000
```

Zero dependências externas (SQLite embarcado, Tailwind via CDN). BD recriado automaticamente ao deletar `bar_adega.db`.

## 9. PONTOS PARA DISCUSSÃO COM FAB (deploy)

1. **Plataforma alvo:** Servidor Windows ou Linux? O sistema é Flask puro, roda em ambos.
2. **Banco de dados:** SQLite é suficiente para bar de pequeno/médio porte? Ou migrar para PostgreSQL?
3. **Exposição:** Acesso apenas LAN ou também externo (app mobile)?
4. **HTTPS:** Precisa de certificado SSL?
5. **Servidor WSGI:** Usar Waitress/Gunicorn ou só Flask dev?
6. **Serviço Windows:** Instalar como serviço do Windows ou rodar em VPS Linux?
7. **Backup:** Estratégia de backup do banco SQLite?
8. **Impressão térmica:** Necessário resolver antes do deploy?
9. **Rede local:** Vários terminais acessando ao mesmo tempo?
