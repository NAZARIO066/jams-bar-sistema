"""Perfis e permissões do sistema.

O nível legado (admin/funcionario) é preservado para compatibilidade, mas toda
autorização nova passa pelas permissões efetivas do perfil e pelas exceções do
usuário.
"""

from flask import g, session


PERMISSION_DEFINITIONS = (
    ("pdv.acessar", "Acessar o PDV", "Vendas", "Visualizar o caixa de venda direta."),
    ("vendas.abrir", "Abrir venda", "Vendas", "Iniciar e incluir itens em uma venda."),
    ("vendas.fechar", "Fechar venda", "Vendas", "Concluir uma venda e registrar o pagamento."),
    ("vendas.cancelar_item", "Cancelar item", "Vendas", "Remover item de comanda e devolver estoque."),
    ("vendas.cancelar", "Cancelar venda", "Vendas", "Cancelar uma venda ou comanda completa."),
    ("vendas.desconto", "Conceder desconto", "Vendas", "Aplicar desconto em vendas e mesas."),
    ("vendas.alterar_preco", "Alterar preço na venda", "Vendas", "Autorizar preço diferente do cadastro quando o fluxo existir."),
    ("mesas.acessar", "Acessar mesas", "Mesas", "Visualizar o salão e as comandas."),
    ("mesas.abrir", "Abrir mesa", "Mesas", "Abrir, reservar, transferir e adicionar itens."),
    ("mesas.fechar", "Fechar mesa", "Mesas", "Fechar mesa e registrar seu pagamento."),
    ("clientes.acessar", "Acessar clientes", "Cadastros", "Visualizar clientes e fiado."),
    ("clientes.alterar", "Alterar clientes", "Cadastros", "Cadastrar, editar, desativar e receber fiado."),
    ("produtos.visualizar", "Visualizar produtos", "Cadastros", "Consultar catálogo, preços e produtos."),
    ("produtos.cadastrar", "Cadastrar produtos", "Cadastros", "Criar produtos e categorias."),
    ("produtos.alterar", "Alterar produtos", "Cadastros", "Editar ou desativar produtos."),
    ("estoque.visualizar", "Visualizar estoque", "Estoque", "Consultar saldo e movimentações."),
    ("estoque.movimentar", "Movimentar estoque", "Estoque", "Registrar entradas e saídas manuais."),
    ("garcons.acessar", "Acessar garçons", "Cadastros", "Visualizar equipe de atendimento."),
    ("garcons.alterar", "Alterar garçons", "Cadastros", "Cadastrar, editar ou desativar garçons."),
    ("caixa.acessar", "Acessar caixa", "Financeiro", "Visualizar status e movimentos do caixa."),
    ("caixa.movimentar", "Movimentar caixa", "Financeiro", "Abrir, fechar, suprir ou realizar sangria."),
    ("relatorios.visualizar", "Visualizar relatórios", "Relatórios", "Acessar relatórios operacionais."),
    ("financeiro.visualizar", "Visualizar valores financeiros", "Relatórios", "Visualizar faturamento, caixa, lucro e valores sensíveis."),
    ("contas.acessar", "Acessar contas", "Financeiro", "Visualizar contas a pagar."),
    ("contas.alterar", "Alterar contas", "Financeiro", "Cadastrar, pagar ou cancelar contas."),
    ("fornecedores.acessar", "Acessar fornecedores", "Financeiro", "Acessar dados de fornecedores quando o módulo estiver disponível."),
    ("impressao.imprimir", "Imprimir", "Operação", "Imprimir comprovantes e comandas."),
    ("impressao.reimprimir", "Reimprimir", "Operação", "Abrir novamente documentos já emitidos."),
    ("configuracoes.acessar", "Acessar configurações", "Administração", "Alterar logo e dados da empresa."),
    ("usuarios.criar", "Criar e editar usuários", "Administração", "Cadastrar, editar, bloquear e redefinir senha de usuários."),
    ("permissoes.alterar", "Alterar permissões", "Administração", "Personalizar perfis e permissões dos usuários."),
    ("auditoria.visualizar", "Visualizar auditoria", "Administração", "Consultar ações e tentativas negadas."),
    ("backup.gerar", "Gerar backup", "Administração", "Criar e baixar cópias de segurança."),
    ("backup.restaurar", "Restaurar backup", "Administração", "Restaurar uma cópia de segurança."),
    ("migracao.acessar", "Acessar migração", "Administração", "Importar e validar bases externas."),
    ("manutencao.acessar", "Acessar manutenção", "Administração", "Executar diagnósticos e rotinas de manutenção."),
)

ALL_PERMISSION_KEYS = {item[0] for item in PERMISSION_DEFINITIONS}

PROFILE_DEFAULTS = {
    "Administrador": {
        "descricao": "Acesso total ao sistema.",
        "permissoes": ALL_PERMISSION_KEYS,
    },
    "Gerente": {
        "descricao": "Gestão operacional e financeira, sem administração de usuários ou restauração.",
        "permissoes": ALL_PERMISSION_KEYS - {
            "usuarios.criar", "permissoes.alterar", "backup.restaurar",
            "migracao.acessar", "manutencao.acessar",
        },
    },
    "Caixa": {
        "descricao": "PDV, atendimento, clientes, mesas e impressão.",
        "permissoes": {
            "pdv.acessar", "vendas.abrir", "vendas.fechar", "vendas.cancelar_item",
            "vendas.desconto", "mesas.acessar", "mesas.abrir", "mesas.fechar",
            "clientes.acessar", "produtos.visualizar", "caixa.acessar",
            "garcons.acessar", "impressao.imprimir", "impressao.reimprimir",
        },
    },
    "Atendente": {
        "descricao": "Atendimento de mesas e vendas, sem acesso financeiro ou administrativo.",
        "permissoes": {
            "pdv.acessar", "vendas.abrir", "vendas.fechar", "vendas.cancelar_item",
            "mesas.acessar", "mesas.abrir", "mesas.fechar", "clientes.acessar",
            "produtos.visualizar", "garcons.acessar", "impressao.imprimir",
        },
    },
    "Estoquista": {
        "descricao": "Cadastro de produtos e controle de estoque.",
        "permissoes": {
            "produtos.visualizar", "produtos.cadastrar", "produtos.alterar",
            "estoque.visualizar", "estoque.movimentar",
        },
    },
}


def init_access_control(db):
    """Cria e atualiza a estrutura de autorização sem remover dados existentes."""
    db.executescript(
        """
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

        CREATE INDEX IF NOT EXISTS idx_perfil_permissoes_perfil
            ON perfil_permissoes(perfil_id);
        CREATE INDEX IF NOT EXISTS idx_usuario_permissoes_usuario
            ON usuario_permissoes(usuario_id);
        """
    )

    columns = {row["name"] for row in db.execute("PRAGMA table_info(usuarios)").fetchall()}
    additions = {
        "perfil_id": "INTEGER REFERENCES perfis_acesso(id)",
        "bloqueado": "INTEGER NOT NULL DEFAULT 0",
        "exigir_troca_senha": "INTEGER NOT NULL DEFAULT 0",
        "ultimo_acesso": "TIMESTAMP",
        "senha_alterada_em": "TIMESTAMP",
    }
    for column, definition in additions.items():
        if column not in columns:
            db.execute(f"ALTER TABLE usuarios ADD COLUMN {column} {definition}")

    db.executemany(
        """INSERT INTO permissoes (chave, nome, grupo, descricao) VALUES (?,?,?,?)
           ON CONFLICT(chave) DO UPDATE SET
             nome=excluded.nome, grupo=excluded.grupo, descricao=excluded.descricao""",
        PERMISSION_DEFINITIONS,
    )

    profile_ids = {}
    for name, definition in PROFILE_DEFAULTS.items():
        db.execute(
            """INSERT INTO perfis_acesso (nome, descricao, sistema, ativo)
               VALUES (?,?,1,1)
               ON CONFLICT(nome) DO UPDATE SET descricao=excluded.descricao, ativo=1""",
            (name, definition["descricao"]),
        )
        profile_id = db.execute(
            "SELECT id FROM perfis_acesso WHERE nome=?", (name,)
        ).fetchone()["id"]
        profile_ids[name] = profile_id
        db.execute("DELETE FROM perfil_permissoes WHERE perfil_id=?", (profile_id,))
        db.executemany(
            "INSERT INTO perfil_permissoes (perfil_id, permissao_chave) VALUES (?,?)",
            [(profile_id, key) for key in sorted(definition["permissoes"])],
        )

    db.execute(
        "UPDATE usuarios SET perfil_id=? WHERE perfil_id IS NULL AND nivel='admin'",
        (profile_ids["Administrador"],),
    )
    db.execute(
        "UPDATE usuarios SET perfil_id=? WHERE perfil_id IS NULL AND nivel!='admin'",
        (profile_ids["Atendente"],),
    )
    db.commit()


def get_user_with_profile(user_id, db=None):
    if db is None:
        from database import get_db
        db = get_db()
    return db.execute(
        """SELECT u.*, p.nome AS perfil_nome
           FROM usuarios u
           LEFT JOIN perfis_acesso p ON p.id=u.perfil_id
           WHERE u.id=?""",
        (user_id,),
    ).fetchone()


def is_admin(user=None):
    if user is None:
        user = getattr(g, "current_user", None)
        if user is None and session.get("usuario_id"):
            user = get_user_with_profile(session["usuario_id"])
    return bool(user and (user["nivel"] == "admin" or user["perfil_nome"] == "Administrador"))


def permission_keys_for_user(user_id, db=None):
    if db is None:
        from database import get_db
        db = get_db()
    user = get_user_with_profile(user_id, db)
    if not user:
        return set()
    if is_admin(user):
        return set(ALL_PERMISSION_KEYS)
    keys = {
        row["permissao_chave"]
        for row in db.execute(
            "SELECT permissao_chave FROM perfil_permissoes WHERE perfil_id=?",
            (user["perfil_id"],),
        ).fetchall()
    }
    for row in db.execute(
        "SELECT permissao_chave, permitido FROM usuario_permissoes WHERE usuario_id=?",
        (user_id,),
    ).fetchall():
        if row["permitido"]:
            keys.add(row["permissao_chave"])
        else:
            keys.discard(row["permissao_chave"])
    return keys


def has_permission(key):
    if not session.get("usuario_id"):
        return False
    cache = getattr(g, "permission_keys", None)
    if cache is None:
        cache = permission_keys_for_user(session["usuario_id"])
        g.permission_keys = cache
    return key in cache


def effective_permissions_for_user(user_id, db=None):
    """Retorna todas as permissões com o estado efetivo para a tela administrativa."""
    if db is None:
        from database import get_db
        db = get_db()
    enabled = permission_keys_for_user(user_id, db)
    return [
        {
            "chave": key,
            "nome": name,
            "grupo": group,
            "descricao": description,
            "permitido": key in enabled,
        }
        for key, name, group, description in PERMISSION_DEFINITIONS
    ]
