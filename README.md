# JAM'S BURGUER - Sistema de Gestão para Bar, Adega e Mesas

Sistema completo para gestão de bar, adega e mesas com controle de comandas, vendas, estoque, clientes, fiado, caixa e relatórios.

## Funcionalidades

- **Mesas e Comandas**: Abertura, fechamento, transferência, reabertura
- **Vendas Diretas**: Carrinho rápido, busca com autocomplete, múltiplas formas de pagamento
- **Estoque**: Controle de entrada/saída, estoque mínimo, alertas
- **Clientes**: Cadastro, histórico, saldo devedor, limite de fiado
- **Caixa**: Abertura/fechamento, suprimentos, sangrias
- **Relatórios**: Vendas (por produto/categoria/garçom), fluxo de caixa, cancelamentos
- **Administração**: Usuários, garçons, contas a pagar, auditoria, backup
- **Manutenção**: Diagnóstico, integridade, limpeza, estatísticas
- **Migração**: Wizard de importação (SQLite, SQL, Excel, CSV)

## Requisitos

- Python 3.11+
- pip

## Instalação Local

```bash
# Clone o repositório
git clone https://github.com/NAZARIO066/jams-bar-sistema.git
cd jams-bar-sistema

# Crie o ambiente virtual
python -m venv venv

# Ative o ambiente
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instale as dependências
pip install -r requirements.txt
```

## Configuração das Variáveis de Ambiente

1. Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

2. Edite o `.env` com seus valores:

```ini
# Gere uma chave secreta com:
# python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=seu-token-hex-aqui-com-64-caracteres

FLASK_DEBUG=0

ADMIN_LOGIN=admin
ADMIN_SENHA=sua-senha-administrador-aqui

FUNC_LOGIN=funcionario
FUNC_SENHA=sua-senha-funcionario-aqui
```

## Criação do Primeiro Administrador

O primeiro administrador e funcionário são criados automaticamente na primeira execução com base nas variáveis definidas no `.env`.

## Execução Local

```bash
python app.py
```

O sistema iniciará em `http://localhost:5000`.

## Execução dos Testes

```bash
# Executa toda a suíte de testes
python -m pytest tests/test_api.py -v

# Executa um grupo específico
python -m pytest tests/test_api.py::TestAuth -v
```

Os testes utilizam um banco de dados temporário e isolado. O banco de produção nunca é acessado durante os testes.

## Backup e Restauração

Via interface administrativa:
1. Acesse `/manutencao/backup`
2. Clique em "Criar Backup"
3. Use "Restaurar" para recuperar um backup anterior

Via linha de comando:
```bash
# Backup manual
python -c "from app import app; from database import get_db; import shutil; shutil.copy(app.config['DATABASE'], 'backup_manual.db')"
```

## Banco de Dados

O sistema usa SQLite por padrão. O arquivo do banco (`*.db`) não é versionado no Git.

**Limitações conhecidas do SQLite:**
- Escrita concorrente limitada (recomendado máximo de 10-15 usuários simultâneos)
- Sem armazenamento persistente em cloud (necessário volume externo)

Para produção com muitos usuários simultâneos, recomenda-se migrar para PostgreSQL.

## Estrutura do Projeto

```
.
├── app.py                  # Inicialização do Flask
├── config.py               # Configurações (variáveis de ambiente)
├── database.py             # Conexão com banco e schema SQL
├── auth.py                 # Autenticação, autorização, rate limiting
├── seed.py                 # Dados iniciais (categorias, produtos, etc.)
├── routes/                 # Rotas da API
│   ├── auth_routes.py
│   ├── dashboard_routes.py
│   ├── mesas_routes.py
│   ├── vendas_routes.py
│   ├── produtos_routes.py
│   ├── estoque_routes.py
│   ├── clientes_routes.py
│   ├── caixa_routes.py
│   ├── admin_routes.py
│   ├── relatorios_routes.py
│   ├── pagamento_routes.py
│   └── migration_routes.py
├── services/               # Lógica de negócio
│   ├── venda_service.py
│   ├── estoque_service.py
│   ├── fiado_service.py
│   └── migration_service.py
├── maintenance/            # Módulo de manutenção
├── migration/              # Wizard de migração de dados
├── templates/              # Templates Jinja2
├── static/                 # Arquivos estáticos (CSS, uploads)
└── tests/                  # Testes automatizados
```

## Deploy

Arquivos de deploy legados estão incluídos como referência (`Dockerfile`, `Procfile`, `render.yaml`).
O deploy será configurado em etapa separada.
