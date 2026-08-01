import sqlite3
from flask import g, current_app

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    db.commit()

SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    login TEXT NOT NULL UNIQUE,
    senha TEXT NOT NULL,
    nivel TEXT NOT NULL CHECK(nivel IN ('admin','funcionario')),
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    perfil_id INTEGER REFERENCES perfis_acesso(id),
    bloqueado INTEGER NOT NULL DEFAULT 0,
    exigir_troca_senha INTEGER NOT NULL DEFAULT 0,
    ultimo_acesso TIMESTAMP,
    senha_alterada_em TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mesas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero INTEGER NOT NULL UNIQUE,
    capacidade INTEGER DEFAULT 4,
    status TEXT NOT NULL DEFAULT 'disponivel' CHECK(status IN ('disponivel','ocupada','reservada','fechando')),
    valor_atual REAL NOT NULL DEFAULT 0,
    aberta_em TIMESTAMP,
    reservada_para TEXT
);

CREATE TABLE IF NOT EXISTS categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    categoria_id INTEGER REFERENCES categorias(id),
    codigo_barras TEXT UNIQUE,
    preco REAL NOT NULL DEFAULT 0,
    estoque REAL NOT NULL DEFAULT 0,
    estoque_minimo REAL NOT NULL DEFAULT 0,
    unidade TEXT NOT NULL DEFAULT 'UN',
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS comandas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mesa_id INTEGER NOT NULL REFERENCES mesas(id),
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    garcom_id INTEGER REFERENCES garcons(id) ON DELETE SET NULL,
    cliente_nome TEXT,
    abertura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fechamento TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'aberta' CHECK(status IN ('aberta','fechada','cancelada'))
);

CREATE TABLE IF NOT EXISTS itens_comanda (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comanda_id INTEGER NOT NULL REFERENCES comandas(id) ON DELETE CASCADE,
    produto_id INTEGER NOT NULL REFERENCES produtos(id),
    quantidade REAL NOT NULL,
    preco_unitario REAL NOT NULL,
    subtotal REAL NOT NULL,
    observacao TEXT,
    usuario_id INTEGER REFERENCES usuarios(id),
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vendas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comanda_id INTEGER REFERENCES comandas(id),
    mesa_id INTEGER REFERENCES mesas(id),
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    valor_total REAL NOT NULL,
    desconto REAL NOT NULL DEFAULT 0,
    forma_pagamento TEXT,
    data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tipo TEXT NOT NULL CHECK(tipo IN ('mesa','direta')),
    status TEXT NOT NULL DEFAULT 'ativa' CHECK(status IN ('ativa','cancelada'))
);

CREATE TABLE IF NOT EXISTS itens_venda (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venda_id INTEGER NOT NULL REFERENCES vendas(id) ON DELETE CASCADE,
    produto_id INTEGER NOT NULL REFERENCES produtos(id),
    quantidade REAL NOT NULL,
    preco_unitario REAL NOT NULL,
    subtotal REAL NOT NULL,
    observacao TEXT
);

CREATE TABLE IF NOT EXISTS movimentacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id INTEGER NOT NULL REFERENCES produtos(id),
    tipo TEXT NOT NULL CHECK(tipo IN ('entrada','saida')),
    quantidade REAL NOT NULL,
    motivo TEXT,
    usuario_id INTEGER REFERENCES usuarios(id),
    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    observacao TEXT
);

CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    telefone TEXT,
    cpf TEXT,
    endereco TEXT,
    limite_fiado REAL NOT NULL DEFAULT 0,
    saldo_devedor REAL NOT NULL DEFAULT 0,
    observacao TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fiado (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id),
    venda_id INTEGER REFERENCES vendas(id),
    tipo TEXT NOT NULL CHECK(tipo IN ('compra','pagamento')),
    valor REAL NOT NULL,
    valor_pago REAL NOT NULL DEFAULT 0,
    data_vencimento DATE,
    usuario_id INTEGER REFERENCES usuarios(id),
    observacao TEXT,
    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fiado_cliente ON fiado(cliente_id);

CREATE TABLE IF NOT EXISTS auditoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER REFERENCES usuarios(id),
    usuario_nome TEXT,
    acao TEXT NOT NULL,
    detalhes TEXT,
    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip TEXT,
    user_agent TEXT
);

CREATE TABLE IF NOT EXISTS caixas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    abertura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fechamento TIMESTAMP,
    valor_inicial REAL DEFAULT 0,
    valor_final REAL,
    total_vendas REAL DEFAULT 0,
    quantidade_vendas INTEGER DEFAULT 0,
    diferenca REAL DEFAULT 0,
    observacao TEXT
);

CREATE INDEX IF NOT EXISTS idx_vendas_data ON vendas(data);
CREATE INDEX IF NOT EXISTS idx_movimentacoes_produto ON movimentacoes(produto_id);
CREATE INDEX IF NOT EXISTS idx_itens_comanda_comanda ON itens_comanda(comanda_id);
CREATE INDEX IF NOT EXISTS idx_itens_venda_venda ON itens_venda(venda_id);
CREATE INDEX IF NOT EXISTS idx_itens_venda_produto ON itens_venda(produto_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_data ON auditoria(data_hora);

CREATE TABLE IF NOT EXISTS garcons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    telefone TEXT,
    comissao REAL DEFAULT 0,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS contas_pagar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fornecedor TEXT NOT NULL,
    descricao TEXT NOT NULL,
    valor REAL NOT NULL,
    vencimento DATE NOT NULL,
    pagamento DATE,
    status TEXT NOT NULL DEFAULT 'pendente' CHECK(status IN ('pendente','pago','atrasado','cancelado')),
    usuario_id INTEGER REFERENCES usuarios(id),
    observacao TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS suprimento_sangria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caixa_id INTEGER REFERENCES caixas(id),
    usuario_id INTEGER REFERENCES usuarios(id),
    tipo TEXT NOT NULL CHECK(tipo IN ('suprimento','sangria')),
    valor REAL NOT NULL,
    motivo TEXT,
    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS historico_transferencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comanda_id INTEGER REFERENCES comandas(id),
    mesa_origem_id INTEGER REFERENCES mesas(id),
    mesa_destino_id INTEGER REFERENCES mesas(id),
    usuario_id INTEGER REFERENCES usuarios(id),
    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    observacao TEXT
);

CREATE TABLE IF NOT EXISTS login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login TEXT NOT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_login_attempts_login ON login_attempts(login);
CREATE INDEX IF NOT EXISTS idx_login_attempts_criado_em ON login_attempts(criado_em);

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

CREATE TABLE IF NOT EXISTS pagamentos_parciais (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comanda_id INTEGER NOT NULL REFERENCES comandas(id),
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    valor_total REAL NOT NULL,
    desconto REAL NOT NULL DEFAULT 0,
    forma_pagamento TEXT NOT NULL,
    nome_pessoa TEXT,
    cliente_id INTEGER REFERENCES clientes(id),
    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pagamentos_parciais_itens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pagamento_parcial_id INTEGER NOT NULL REFERENCES pagamentos_parciais(id) ON DELETE CASCADE,
    item_comanda_id INTEGER NOT NULL REFERENCES itens_comanda(id),
    quantidade_paga REAL NOT NULL,
    valor_unitario REAL NOT NULL,
    subtotal REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS config_acesso_rapido (
    id INTEGER PRIMARY KEY,
    modo TEXT NOT NULL DEFAULT 'automatico' CHECK(modo IN ('manual','automatico','misto'))
);

CREATE TABLE IF NOT EXISTS acesso_rapido_produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id INTEGER NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    ordem INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_comandas_mesa ON comandas(mesa_id);
CREATE INDEX IF NOT EXISTS idx_comandas_status ON comandas(status);
CREATE INDEX IF NOT EXISTS idx_contas_pagar_vencimento ON contas_pagar(vencimento);
CREATE INDEX IF NOT EXISTS idx_contas_pagar_status ON contas_pagar(status);
CREATE INDEX IF NOT EXISTS idx_garcons_ativo ON garcons(ativo);
CREATE INDEX IF NOT EXISTS idx_historico_transferencias_comanda ON historico_transferencias(comanda_id);
CREATE INDEX IF NOT EXISTS idx_historico_transferencias_origem ON historico_transferencias(mesa_origem_id);
CREATE INDEX IF NOT EXISTS idx_suprimento_sangria_caixa ON suprimento_sangria(caixa_id);
CREATE INDEX IF NOT EXISTS idx_pagamentos_parciais_comanda ON pagamentos_parciais(comanda_id);
CREATE INDEX IF NOT EXISTS idx_pagamentos_parciais_itens_pagamento ON pagamentos_parciais_itens(pagamento_parcial_id);
CREATE INDEX IF NOT EXISTS idx_pagamentos_parciais_itens_item ON pagamentos_parciais_itens(item_comanda_id);

CREATE TABLE IF NOT EXISTS perfis_acesso (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE,
    descricao TEXT,
    sistema INTEGER NOT NULL DEFAULT 1,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS permissoes (
    chave TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    grupo TEXT NOT NULL,
    descricao TEXT
);

CREATE TABLE IF NOT EXISTS perfil_permissoes (
    perfil_id INTEGER NOT NULL REFERENCES perfis_acesso(id) ON DELETE CASCADE,
    permissao_chave TEXT NOT NULL REFERENCES permissoes(chave) ON DELETE CASCADE,
    PRIMARY KEY (perfil_id, permissao_chave)
);

CREATE TABLE IF NOT EXISTS usuario_permissoes (
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    permissao_chave TEXT NOT NULL REFERENCES permissoes(chave) ON DELETE CASCADE,
    permitido INTEGER NOT NULL CHECK(permitido IN (0,1)),
    PRIMARY KEY (usuario_id, permissao_chave)
);

CREATE INDEX IF NOT EXISTS idx_perfil_permissoes_perfil ON perfil_permissoes(perfil_id);
CREATE INDEX IF NOT EXISTS idx_usuario_permissoes_usuario ON usuario_permissoes(usuario_id);
"""
