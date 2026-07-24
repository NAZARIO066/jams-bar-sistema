# DOCUMENTAÇÃO COMPLETA - SISTEMA JAM'S BURGUER
## Histórico de Deploy - 08/07/2026

---

## RESUMO DO PROJETO

- **Nome:** JAM'S BURGUER - Sistema de Gestão para Bar, Adega e Mesas
- **Stack:** Python 3.12 / Flask 3.0.0 / SQLite / Gunicorn
- **Repositório GitHub:** https://github.com/NAZARIO066/jams-bar-sistema
- **URL do Sistema:** https://nazarioguaira.pythonanywhere.com
- **Hospedagem:** PythonAnywhere (plano gratuito)

---

## CREDENCIAIS DE ACESSO

> As credenciais estão definidas no `seed.py` e no banco de dados.
> Para alterar, edite o `seed.py` e faça push para o PythonAnywhere.

---

## HISTÓRICO DO DEPLOY (08/07/2026)

### Tentativas anteriores (não funcionaram):
1. **Firebase Hosting** - Só serve arquivos estáticos, não roda Flask
2. **Google Cloud Run** - Precisa de billing ativado (cartão de crédito)
3. **Render.com** - Pede cartão de crédito mesmo no plano grátis

### Deploy final (funcionou):
4. **PythonAnywhere** - Gratuito, sem cartão, suporta Flask nativamente

---

## COMO ACESSAR O SISTEMA

### Usuário/Cliente:
Acesse: **https://nazarioguaira.pythonanywhere.com**

### Para acessar o painel de administração do PythonAnywhere:
1. Acesse: **https://www.pythonanywhere.com**
2. Login: `nazarioguaira`
3. Senha: (a senha que você criou)

---

## MANUTENÇÃO - COMO MANTER O SISTEMA NO AR

### IMPORTANTE - A cada 30 dias:
1. Entre no PythonAnywhere
2. Vá na aba **"Web"**
3. Clique no botão amarelo **"Run until 1 month from today"**
4. Senão fizer isso, o site desativa

### Para recarregar o sistema (após atualizações):
1. Entre no PythonAnywhere
2. Vá na aba **"Web"**
3. Clique no botão verde **"Reload nazarioguaira.pythonanywhere.com"**

---

## COMO ATUALIZAR O SISTEMA

### Pelo computador (desenvolvimento):
```powershell
cd "E:\SISTEMA DE GESTÃO PARA BAR, ADEGA E MESAS"
git add .
git commit -m "Descrição da atualização"
git push
```

### Pelo PythonAnywhere (após o push):
1. Abra o console **Bash**
2. Rode:
```bash
cd ~/jams-bar-sistema && git pull
```
3. Vá na aba **"Web"** e clique em **"Reload"**

---

## ESTRUTURA DO PROJETO

```
jams-bar-sistema/
├── app.py              # Aplicação principal Flask
├── config.py           # Configurações (SECRET_KEY, etc)
├── database.py         # Banco de dados SQLite + Schema
├── auth.py             # Autenticação e auditoria
├── seed.py             # Dados iniciais (produtos, mesas, etc)
├── setup_prod.py       # Setup para produção
├── requirements.txt    # Dependências Python
├── Procfile            # Config para Render
├── render.yaml         # Config para Render
├── Dockerfile          # Config para Docker/Cloud Run
├── routes/             # Rotas da aplicação
│   ├── auth_routes.py      # Login/Logout
│   ├── dashboard_routes.py # Dashboard principal
│   ├── mesas_routes.py     # Gerenciamento de mesas
│   ├── vendas_routes.py    # PDV / Vendas diretas
│   ├── produtos_routes.py  # CRUD Produtos
│   ├── estoque_routes.py   # Controle de estoque
│   ├── clientes_routes.py  # Clientes e fiado
│   ├── caixa_routes.py     # Controle de caixa
│   ├── admin_routes.py     # Administração
│   └── relatorios_routes.py # Relatórios
├── services/           # Lógica de negócio
│   ├── venda_service.py
│   ├── fiado_service.py
│   └── estoque_service.py
├── templates/          # Templates HTML (15 arquivos)
├── static/             # CSS, imagens
└── tests/              # Testes
```

---

## FUNCIONALIDADES DO SISTEMA

1. **Dashboard** - KPIs, gráficos, vendas por hora
2. **Mesas** - 40 mesas, comandas, transferência
3. **PDV / Vendas** - Vendas diretas, código de barras
4. **Produtos** - CRUD, 27 produtos, 12 categorias
5. **Estoque** - Entradas/saídas, alertas
6. **Garçons** - Gerenciamento com comissão
7. **Caixa** - Abertura/fechamento, suprimento/sangria
8. **Clientes / Fiado** - Sistema de crédito completo
9. **Contas a Pagar** - Fornecedores, vencimento
10. **Relatórios** - Vendas, mesas, produtos, caixa
11. **Usuários** - Admin/Funcionário
12. **Auditoria** - Log de todas as ações

---

## VARIÁVEIS DE AMBIENTE

| Variável | Onde é usada |
|----------|--------------|
| `SECRET_KEY` | config.py (segurança) — gere uma chave forte e única |
| `FLASK_DEBUG` | app.py (modo produção) |

---

## COMANDOS ÚTEIS NO PYTHONANYWHERE

### Abrir console:
```bash
cd ~/jams-bar-sistema
```

### Ver logs de erro:
```bash
cat /var/www/nazarioguaira_pythonanywhere_com_wsgi.py
```

### Editar configuração WSGI:
```bash
nano /var/www/nazarioguaira_pythonanywhere_com_wsgi.py
```

### Verificar se o app está rodando:
```bash
ls ~/jams-bar-sistema/bar_adega.db
```

---

## TROCA DE SENHA (quando necessário)

Para trocar a senha do admin, edite o arquivo `seed.py` e mude a senha na função `seed_missing_data()` ou na tupla de criação. Depois faça push e pull no PythonAnywhere.

---

## LIMITAÇÕES ATUAIS

1. **Plano gratuito:** Site desativa após 30 dias sem login
2. **SQLite:** Banco de dados local (não compartilhado entre instâncias)
3. **512 MB de RAM:** Suficiente para uso normal
4. **Sem domínio próprio:** URL é nazarioguaira.pythonanywhere.com

---

## PRÓXIMOS PASSOS (se cliente aprovar)

1. **Plano pago PythonAnywhere** ($5/mês) - Site fica sempre no ar
2. **Domínio próprio** - Ex: jamsburguer.com.br
3. **Backup automático** do banco de dados
4. **Migração para PostgreSQL** (se precisar de mais performance)

---

## CONTATOS

- **GitHub:** https://github.com/NAZARIO066
- **PythonAnywhere:** nazarioguaira
- **Firebase:** nazarioguaira@gmail.com (projeto: jams-bar-sistema)

---

**Documento atualizado em: 08/07/2026**
