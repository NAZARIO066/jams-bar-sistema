import os
import time
import sqlite3
import shutil
from datetime import datetime
from flask import current_app


def _db_path():
    return current_app.config["DATABASE"]


_DELETION_ORDER = [
    "itens_venda",
    "itens_comanda",
    "suprimento_sangria",
    "historico_transferencias",
    "fiado",
    "vendas",
    "comandas",
    "caixas",
    "movimentacoes",
    "contas_pagar",
    "clientes",
    "auditoria",
    "login_attempts",
]

_OPERATIONS = {
    "vendas": {
        "nome": "Limpar Vendas",
        "descricao": "Remove todo o histórico de vendas, itens de venda e registros de fiado vinculados.",
        "tabelas": ["itens_venda", "vendas", "fiado"],
        "tabelas_afetadas": ["itens_venda", "vendas", "fiado"],
        "confirmacao": "CONFIRMAR LIMPEZA",
        "nivel": "medio",
    },
    "comandas": {
        "nome": "Limpar Comandas",
        "descricao": "Remove todas as comandas (abertas, fechadas, canceladas) e seus itens.",
        "tabelas": ["itens_comanda", "comandas"],
        "tabelas_afetadas": ["itens_comanda", "comandas"],
        "confirmacao": "CONFIRMAR LIMPEZA",
        "nivel": "medio",
    },
    "caixa": {
        "nome": "Limpar Caixa",
        "descricao": "Remove registros de caixa, suprimentos e sangrias.",
        "tabelas": ["suprimento_sangria", "caixas"],
        "tabelas_afetadas": ["suprimento_sangria", "caixas"],
        "confirmacao": "CONFIRMAR LIMPEZA",
        "nivel": "medio",
    },
    "estoque": {
        "nome": "Limpar Movimentações de Estoque",
        "descricao": "Remove todo o histórico de movimentações de entrada e saída do estoque.",
        "tabelas": ["movimentacoes"],
        "tabelas_afetadas": ["movimentacoes"],
        "confirmacao": "CONFIRMAR LIMPEZA",
        "nivel": "medio",
    },
    "clientes": {
        "nome": "Limpar Clientes",
        "descricao": "Remove todos os clientes cadastrados e seus vínculos de fiado.",
        "tabelas": ["fiado", "clientes"],
        "tabelas_afetadas": ["fiado", "clientes"],
        "confirmacao": "CONFIRMAR LIMPEZA",
        "nivel": "alto",
    },
    "fornecedores": {
        "nome": "Limpar Fornecedores",
        "descricao": "Remove todos os registros de contas a pagar (fornecedores).",
        "tabelas": ["contas_pagar"],
        "tabelas_afetadas": ["contas_pagar"],
        "confirmacao": "CONFIRMAR LIMPEZA",
        "nivel": "medio",
    },
    "funcionarios": {
        "nome": "Limpar Funcionários",
        "descricao": "Remove todos os funcionários (exceto administradores).",
        "tabelas": ["usuarios"],
        "tabelas_afetadas": ["usuarios"],
        "confirmacao": "CONFIRMAR LIMPEZA",
        "nivel": "alto",
    },
    "reset": {
        "nome": "Reset Inteligente",
        "descricao": "Restaura o sistema para estado inicial, preservando empresa, admin, categorias, produtos e configurações.",
        "tabelas": ["itens_venda", "itens_comanda", "suprimento_sangria", "historico_transferencias",
                     "fiado", "vendas", "comandas", "caixas", "movimentacoes", "contas_pagar",
                     "clientes", "usuarios", "auditoria", "login_attempts"],
        "tabelas_afetadas": ["vendas", "comandas", "caixas", "movimentacoes", "clientes",
                              "fiado", "contas_pagar", "usuarios", "auditoria", "login_attempts"],
        "confirmacao": "RESETAR SISTEMA",
        "nivel": "critico",
    },
}


def obter_info_operacao(acao):
    return _OPERATIONS.get(acao)


def verificar_senha_admin(senha):
    db_path = _db_path()
    if not os.path.exists(db_path):
        return False
    try:
        from werkzeug.security import check_password_hash
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        user = conn.execute(
            "SELECT senha FROM usuarios WHERE login='admin' AND nivel='admin' AND ativo=1"
        ).fetchone()
        conn.close()
        if not user:
            return False
        return check_password_hash(user["senha"], senha)
    except Exception:
        return False


def validar_confirmacao(texto, acao):
    info = _OPERATIONS.get(acao)
    if not info:
        return False
    return texto.strip().upper() == info["confirmacao"]


def preview_limpeza(acao):
    db_path = _db_path()
    if not os.path.exists(db_path):
        return {"ok": False, "erro": "Banco de dados não encontrado"}

    info = _OPERATIONS.get(acao)
    if not info:
        return {"ok": False, "erro": f"Operação desconhecida: {acao}"}

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cur = conn.cursor()

        tabelas_info = []
        total_registros = 0

        if acao == "reset":
            for tname in info["tabelas"]:
                try:
                    count = cur.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
                    if count > 0:
                        tabelas_info.append({"tabela": tname, "registros": count})
                        total_registros += count
                except Exception:
                    pass
            count_admin = cur.execute(
                "SELECT COUNT(*) FROM usuarios WHERE nivel='admin'"
            ).fetchone()[0]
            count_func = cur.execute(
                "SELECT COUNT(*) FROM usuarios WHERE nivel='funcionario'"
            ).fetchone()[0]
            count_preservados = 0
            for preservar in ["empresa", "categorias", "produtos", "mesas"]:
                try:
                    c = cur.execute(f'SELECT COUNT(*) FROM "{preservar}"').fetchone()[0]
                    count_preservados += c
                except Exception:
                    pass
            count_preservados += count_admin
        else:
            for tname in info["tabelas"]:
                try:
                    count = cur.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
                    tabelas_info.append({"tabela": tname, "registros": count})
                    total_registros += count
                except Exception:
                    pass
            count_preservados = None

        conn.close()

        nivel = info["nivel"]
        if total_registros == 0:
            estimativa_seg = 0
        elif nivel == "critico":
            estimativa_seg = max(1, total_registros // 50)
        elif nivel == "alto":
            estimativa_seg = max(1, total_registros // 100)
        else:
            estimativa_seg = max(1, total_registros // 200)

        return {
            "ok": True,
            "acao": acao,
            "nome": info["nome"],
            "descricao": info["descricao"],
            "tabelas": tabelas_info,
            "total_registros": total_registros,
            "tabelas_afetadas": info["tabelas_afetadas"],
            "estimativa_segundos": estimativa_seg,
            "nivel": nivel,
            "confirmacao_necessaria": info["confirmacao"],
            "preservados": count_preservados,
        }
    except Exception as e:
        return {"ok": False, "erro": str(e)}


def _count_all(conn):
    counts = {}
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    for (tname,) in tables:
        try:
            counts[tname] = conn.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
        except Exception:
            counts[tname] = 0
    return counts


def _deletar_tabelas(conn, tabelas):
    deletados = {}
    for tname in _DELETION_ORDER:
        if tname in tabelas:
            try:
                count = conn.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
                conn.execute(f'DELETE FROM "{tname}"')
                deletados[tname] = count
            except Exception:
                deletados[tname] = 0
    return deletados


def _validar_integridade(conn):
    try:
        result = conn.execute("PRAGMA integrity_check").fetchone()
        return result[0] == "ok" if result else False
    except Exception:
        return False


def executar_limpeza(acao, usuario_id=None, usuario_nome=None):
    from maintenance.backup import criar_backup, restaurar_backup as rb
    from maintenance.audit import log_maintenance

    db_path = _db_path()
    if not os.path.exists(db_path):
        return {"ok": False, "erro": "Banco de dados não encontrado"}

    info = _OPERATIONS.get(acao)
    if not info:
        return {"ok": False, "erro": f"Operação desconhecida: {acao}"}

    t_inicio = time.time()

    backup_info, backup_err = criar_backup(
        f"Backup pré-limpeza: {info['nome']}",
        usuario_id=usuario_id,
        usuario_nome=usuario_nome,
    )
    if backup_err:
        return {"ok": False, "erro": f"Falha ao criar backup: {backup_err}"}

    backup_nome = backup_info["nome"]

    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")

        antes = _count_all(conn)

        if acao == "reset":
            deletados = _deletar_tabelas(conn, info["tabelas"])
            conn.execute(
                "UPDATE mesas SET status='disponivel', valor_atual=0, aberta_em=NULL, reservada_para=NULL"
            )
            conn.commit()
        elif acao == "funcionarios":
            try:
                count = conn.execute(
                    "SELECT COUNT(*) FROM usuarios WHERE nivel='funcionario'"
                ).fetchone()[0]
                conn.execute("DELETE FROM usuarios WHERE nivel='funcionario'")
                deletados = {"usuarios": count}
            except Exception:
                deletados = {"usuarios": 0}
            conn.commit()
        else:
            deletados = _deletar_tabelas(conn, info["tabelas"])
            conn.commit()

        integridade = _validar_integridade(conn)
        depois = _count_all(conn)
        conn.close()

        t_total = round(time.time() - t_inicio, 2)

        preservados = {}
        for tname, count in depois.items():
            if count > 0:
                preservados[tname] = count

        if not integridade:
            ok_rb, err_rb, pre_nome = rb(backup_nome)
            log_maintenance(
                f"Limpeza falhou (integridade): {info['nome']}",
                "erro",
                f"Backup restaurado: {backup_nome}",
                usuario_id,
                usuario_nome,
            )
            return {
                "ok": False,
                "erro": "Falha na verificação de integridade. Backup restaurado automaticamente.",
                "backup_restaurado": backup_nome,
                "integridade": False,
            }

        log_maintenance(
            f"Limpeza executada: {info['nome']}",
            "ok",
            f"Registros removidos: {sum(deletados.values())} | "
            f"Backup: {backup_nome} | "
            f"Tabelas: {', '.join(deletados.keys())} | "
            f"Integridade: ok | "
            f"Tempo: {t_total}s",
            usuario_id,
            usuario_nome,
        )

        return {
            "ok": True,
            "mensagem": f"{info['nome']} concluída com sucesso",
            "removidos": deletados,
            "total_removidos": sum(deletados.values()),
            "preservados": preservados,
            "backup_criado": backup_nome,
            "integridade": True,
            "tempo_segundos": t_total,
        }

    except Exception as e:
        try:
            ok_rb, err_rb, pre_nome = rb(backup_nome)
        except Exception:
            pass
        log_maintenance(
            f"Limpeza falhou (exceção): {info['nome']}",
            "erro",
            f"Erro: {e} | Backup restaurado: {backup_nome}",
            usuario_id,
            usuario_nome,
        )
        return {
            "ok": False,
            "erro": f"Erro durante execução: {e}. Backup restaurado automaticamente.",
            "backup_restaurado": backup_nome,
        }
