# STATUS DO PROJETO — Sistema de Gestão Bar, Adega e Mesas

> Documento para continuidade. Leia isto antes de continuar o desenvolvimento.

**Data:** 06/06/2026
**Stack:** Flask (Python) + SQLite + HTML/CSS/JS (Tailwind + Chart.js + html5-qrcode)
**Versão:** 2.1 do PRD + módulo de Clientes/Fiado

---

## 1. COMO RODAR

```powershell
cd "D:\SISTEMA DE GESTÃO PARA BAR, ADEGA E MESAS"
python app.py
```

Acessar: **http://localhost:5000**
**Login admin:** `admin` / `admin123`
**Login funcionário:** `funcionario` / `123456`

Para parar: `Ctrl+C` no terminal.

---

## 2. ESTRUTURA DE ARQUIVOS

```
D:\SISTEMA DE GESTÃO PARA BAR, ADEGA E MESAS\
├── app.py                  # Rotas Flask (todas as APIs + páginas)
├── auth.py                 # Decoradores login_required/admin_required + log_auditoria
├── config.py               # Configurações (SECRET_KEY, DB path)
├── database.py             # Conexão SQLite + SCHEMA de todas as tabelas
├── seed.py                 # Dados iniciais (admin, funcionário, produtos, mesas, clientes, fiados)
├── fix.py                  # Script manual para corrigir/popular banco (criado em sessão)
├── requirements.txt        # Flask==3.0.0, Werkzeug==3.0.1
├── PRD.md                  # Documento de requisitos v2.1
├── STATUS.md               # ESTE DOCUMENTO
├── bar_adega.db            # Banco SQLite (gerado automaticamente)
│
├── templates\              # Templates Jinja2
│   ├── base.html           # Layout base (sidebar, header, dark mode, alertas)
│   ├── login.html          # Tela de login
│   ├── dashboard.html      # Dashboard com gráficos (Chart.js)
│   ├── mesas.html          # Mapa visual de mesas + abrir comanda
│   ├── vendas.html         # PDV (venda direta) + leitor código barras + fiado
│   ├── produtos.html       # CRUD produtos + leitor webcam
│   ├── estoque.html        # Estoque + entradas/saídas + alertas
│   ├── caixa.html          # Abertura/fechamento de caixa
│   ├── relatorios.html     # Filtros período + totais
│   ├── clientes.html       # CRUD clientes + módulo fiado
│   ├── usuarios.html       # CRUD usuários (só admin)
│   ├── auditoria.html      # Logs de auditoria (só admin)
│   └── erro.html           # Páginas 403/404
│
└── static\css\
    └── style.css           # Variáveis CSS tema claro/escuro, mesa-card, badges, modal
```

---

## 3. BANCO DE DADOS (SQLite)

**Arquivo:** `bar_adega.db` (criado automaticamente na primeira execução).

### Tabelas principais:

| Tabela | Função |
|--------|--------|
| `usuarios` | Login, senha hash, nível (admin/funcionario) |
| `mesas` | 20 mesas, status, valor_atual, cliente_nome |
| `comandas` | Comandas abertas por mesa, com `cliente_nome` |
| `itens_comanda` | Itens lançados na comanda |
| `categorias` | Categorias de produtos |
| `produtos` | ~25 produtos com código de barras |
| `vendas` | Vendas (tipo=mesa ou direta) |
| `itens_venda` | Itens de cada venda |
| `movimentacoes` | Entradas/saídas de estoque |
| `caixas` | Abertura/fechamento de caixa |
| `auditoria` | Log de todas ações sensíveis |
| `clientes` | Clientes cadastrados |
| `fiado` | Movimentações de fiado (compras e pagamentos) |

### Colunas importantes adicionadas em sessão:

- `comandas.cliente_nome` (migração automática)
- `fiado.data_vencimento` (DATE)
- `fiado.valor_pago` (REAL, default 0)

**Migrações** rodam automaticamente no `before_request` em `app.py`. Recriar do zero: apagar `bar_adega.db` e rodar `python app.py` novamente.

---

## 4. FUNCIONALIDADES IMPLEMENTADAS ✅

### Web completo
- [x] Login com sessão Flask + logout
- [x] Dashboard com 8 KPIs + 4 gráficos em tempo real (atualiza a cada 8s)
- [x] Mapa de mesas (20 mesas) com status colorido (livre/ocupada/reservada/fechando)
- [x] Abrir mesa com nome do cliente opcional
- [x] Comanda: adicionar produtos (busca ou código de barras), remover item, fechar conta
- [x] PDV venda direta com carrinho, desconto, múltiplas formas de pagamento
- [x] CRUD produtos com leitor de código de barras via webcam (html5-qrcode)
- [x] Controle de estoque: entrada/saída com motivo, alertas em tempo real
- [x] Caixa: abertura/fechamento com cálculo automático
- [x] Relatórios: hoje/ontem/semana/mês/custom + por mesa + top produtos
- [x] CRUD usuários (apenas admin)
- [x] Auditoria: log de todas ações com IP + user-agent

### Módulo Clientes / Fiado
- [x] CRUD clientes com limite de fiado
- [x] Venda fiado via PDV com seleção de cliente
- [x] Vencimento de fiado configurável (padrão 30 dias)
- [x] Status colorido: 🟢 EM DIA / 🟡 VENCE EM X DIAS / 🟣 VENCE EM X DIAS / 🔴 VENCIDO
- [x] Borda colorida na linha da tabela
- [x] Histórico de fiado com data de vencimento por item
- [x] Baixa FIFO no pagamento (quita os mais antigos primeiro)
- [x] **Bloqueio de venda fiado se cliente tem fiado vencido** 🚫
- [x] Modal de detalhes do fiado com saldo + histórico

### Visual / UX
- [x] Tema claro/escuro (botão no header, salva em localStorage)
- [x] Sidebar com gradiente (atualmente desativado a pedido do usuário - está escura)
- [x] Notificações toast
- [x] Modal de alertas (🔔) com produtos críticos/zerados
- [x] Relógio no header
- [x] Responsivo (mobile-friendly)
- [x] Badges com cores vibrantes e sombra (gradiente)
- [x] 15 clientes fictícios seedados com fiados em vários estados

---

## 5. DADOS DE TESTE (SEED)

### Produtos
~25 produtos nas categorias: Vinhos, Whisky, Vodka, Gin, Cervejas, Refrigerantes, Energéticos, Água, Petiscos, Porções, Drinks.

### Clientes fictícios (15)
Com telefones, CPFs, endereços, limites variados.
**Fiados seedados (17):** criados em `fix.py` e também no `ensure_db` (seed de teste). Cobre todos os status: vencido, alerta (5d), atenção (10d), em dia.

### Para resetar tudo:
```powershell
del bar_adega.db
python app.py
```

### Para apenas resetar fiados:
```powershell
python fix.py
```

---

## 6. BUGS CONHECIDOS / PENDÊNCIAS

### Bugs corrigidos em sessão:
- `init_db()` fora de contexto → envolto em `app.app_context()`
- `url_for("auth.login")` → corrigido para `url_for("login")`
- Template `{% if x := ... %}` removido (Jinja não aceita)
- `PARSE_DECLTYPES` no SQLite causava "Invalid Date" → removido
- `c.executemany("DELETE...")` faltando params → corrigido no `fix.py`

### Pendências funcionais (não implementado):
- ⏳ Impressão térmica (ESC/POS, 80mm, P98)
- ⏳ WebSocket para tempo real (atualmente usa polling)
- ⏳ App mobile do administrador
- ⏳ Notificações push (FCM)
- ⏳ Exportar relatórios PDF/Excel
- ⏳ Backup automático do banco
- ⏳ Impressão de comanda/pedido/comprovante

### Pequenos ajustes sugeridos:
- Vendas no PDV também poderia permitir fiado com calendário visual
- Histórico de fiado poderia agrupar por mês
- Filtro por status (vencido/em dia) na lista de clientes
- "Cobrar agora" direto do modal de fiado (botão WhatsApp)
- Editar vencimento de um fiado específico

---

## 7. DECISÕES TÉCNICAS IMPORTANTES

1. **SQLite** (não MySQL/PostgreSQL) → simplicidade, fácil backup
2. **Flask puro** (sem Flask-Login) → sessões nativas
3. **Tailwind via CDN** → sem build step
4. **Chart.js** para gráficos
5. **html5-qrcode** para leitor de código de barras
6. **Polling 8-10s** para tempo real (não WebSocket ainda)
7. **Senha hash** com `werkzeug.security`
8. **Auditoria** captura IP + User-Agent automaticamente
9. **Decorator `@login_required`** e `@admin_required` em `auth.py`
10. **`log_auditoria()`** chamado em ações sensíveis

---

## 8. PRÓXIMOS PASSOS SUGERIDOS

**Ordem de prioridade recomendada:**

1. **Impressão ESC/POS** — Usar `python-escpos` no backend, com botão "Imprimir?" no PDV/fechamento de mesa
2. **Exportar relatórios PDF** — `reportlab` ou `weasyprint`
3. **Backup automático diário** — APScheduler ou schedule, copia `bar_adega.db` para pasta `backups/`
4. **WebSocket** — `flask-socketio` para tempo real entre terminais
5. **App mobile** — React Native consumindo `/api/mobile/*` (endpoints já planejados no PRD)
6. **Sistema de impressão configurável** — tabela `impressoras` + templates por modelo

---

## 9. CONTEXTO DE USO (para entender o público)

- **Tipo de negócio:** Bar, Adega, Tabacaria, Distribuidora
- **Funcionários** (garçons/operadores) → acesso restrito (PDV + mesas + estoque)
- **Administrador/Dono** → acesso total, também pelo celular remotamente
- **Perfil do dono** → leigo em tecnologia, valoriza visual chamativo e textos em português claro
- **Fiado** é ESSENCIAL (clientes recorrentes que compram e pagam depois)
- **Prazo de fiado** varia (padrão 30 dias, configurável)
- **Estoque crítico** deve ser visualmente óbvio (badges coloridos + alertas)

---

## 10. CONTATO / LINKS ÚTEIS

- **PRD completo:** `PRD.md` (versão 2.1)
- **Flask docs:** https://flask.palletsprojects.com/
- **html5-qrcode:** https://github.com/mebjas/html5-qrcode
- **Chart.js:** https://www.chartjs.org/
- **python-escpos** (para impressão futura): https://github.com/python-escpos/python-escpos

---

## 11. COMO PEDIR AJUDA AO ASSISTENTE

Comandos úteis para dar continuidade:

- `"continue de onde parou"` — ele lê este STATUS.md
- `"implemente X do PRD"` — referencia o PRD.md
- `"o problema é Y, corrige"`
- `"adicione testes para X"`
- `"como faço deploy em rede local?"`
- `"gere dados de teste para X"`

**Sempre mencionar este arquivo `STATUS.md` no início da conversa para contextualizar.**

---

**Última atualização:** 06/06/2026 03:40
**Próxima sessão:** continuar conforme seção 8 (Prioridades)
