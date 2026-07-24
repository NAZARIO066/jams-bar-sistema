import re
from datetime import datetime
from database import SCHEMA


EXPECTED_TABLES = {
    "usuarios": {
        "columns": {
            "id": "INTEGER",
            "nome": "TEXT",
            "login": "TEXT",
            "senha": "TEXT",
            "nivel": "TEXT",
            "ativo": "INTEGER",
            "criado_em": "TIMESTAMP",
        },
        "required": ["nome", "login", "senha", "nivel"],
    },
    "mesas": {
        "columns": {
            "id": "INTEGER",
            "numero": "INTEGER",
            "capacidade": "INTEGER",
            "status": "TEXT",
            "valor_atual": "REAL",
            "aberta_em": "TIMESTAMP",
            "reservada_para": "TEXT",
        },
        "required": ["numero"],
    },
    "categorias": {
        "columns": {
            "id": "INTEGER",
            "nome": "TEXT",
        },
        "required": ["nome"],
    },
    "produtos": {
        "columns": {
            "id": "INTEGER",
            "nome": "TEXT",
            "categoria_id": "INTEGER",
            "codigo_barras": "TEXT",
            "preco": "REAL",
            "estoque": "REAL",
            "estoque_minimo": "REAL",
            "unidade": "TEXT",
            "ativo": "INTEGER",
            "criado_em": "TIMESTAMP",
        },
        "required": ["nome"],
    },
    "comandas": {
        "columns": {
            "id": "INTEGER",
            "mesa_id": "INTEGER",
            "usuario_id": "INTEGER",
            "garcom_id": "INTEGER",
            "cliente_nome": "TEXT",
            "abertura": "TIMESTAMP",
            "fechamento": "TIMESTAMP",
            "status": "TEXT",
        },
        "required": ["mesa_id", "usuario_id"],
    },
    "itens_comanda": {
        "columns": {
            "id": "INTEGER",
            "comanda_id": "INTEGER",
            "produto_id": "INTEGER",
            "quantidade": "REAL",
            "preco_unitario": "REAL",
            "subtotal": "REAL",
            "observacao": "TEXT",
            "usuario_id": "INTEGER",
            "criado_em": "TIMESTAMP",
        },
        "required": ["comanda_id", "produto_id", "quantidade", "preco_unitario", "subtotal"],
    },
    "vendas": {
        "columns": {
            "id": "INTEGER",
            "comanda_id": "INTEGER",
            "mesa_id": "INTEGER",
            "usuario_id": "INTEGER",
            "valor_total": "REAL",
            "desconto": "REAL",
            "forma_pagamento": "TEXT",
            "data": "TIMESTAMP",
            "tipo": "TEXT",
            "status": "TEXT",
        },
        "required": ["usuario_id", "valor_total", "tipo"],
    },
    "itens_venda": {
        "columns": {
            "id": "INTEGER",
            "venda_id": "INTEGER",
            "produto_id": "INTEGER",
            "quantidade": "REAL",
            "preco_unitario": "REAL",
            "subtotal": "REAL",
            "observacao": "TEXT",
        },
        "required": ["venda_id", "produto_id", "quantidade", "preco_unitario", "subtotal"],
    },
    "movimentacoes": {
        "columns": {
            "id": "INTEGER",
            "produto_id": "INTEGER",
            "tipo": "TEXT",
            "quantidade": "REAL",
            "motivo": "TEXT",
            "usuario_id": "INTEGER",
            "data_hora": "TIMESTAMP",
            "observacao": "TEXT",
        },
        "required": ["produto_id", "tipo", "quantidade"],
    },
    "clientes": {
        "columns": {
            "id": "INTEGER",
            "nome": "TEXT",
            "telefone": "TEXT",
            "cpf": "TEXT",
            "endereco": "TEXT",
            "limite_fiado": "REAL",
            "saldo_devedor": "REAL",
            "observacao": "TEXT",
            "ativo": "INTEGER",
            "criado_em": "TIMESTAMP",
        },
        "required": ["nome"],
    },
    "fiado": {
        "columns": {
            "id": "INTEGER",
            "cliente_id": "INTEGER",
            "venda_id": "INTEGER",
            "tipo": "TEXT",
            "valor": "REAL",
            "valor_pago": "REAL",
            "data_vencimento": "DATE",
            "usuario_id": "INTEGER",
            "observacao": "TEXT",
            "data_hora": "TIMESTAMP",
        },
        "required": ["cliente_id", "tipo", "valor"],
    },
    "auditoria": {
        "columns": {
            "id": "INTEGER",
            "usuario_id": "INTEGER",
            "usuario_nome": "TEXT",
            "acao": "TEXT",
            "detalhes": "TEXT",
            "data_hora": "TIMESTAMP",
            "ip": "TEXT",
            "user_agent": "TEXT",
        },
        "required": ["acao"],
    },
    "caixas": {
        "columns": {
            "id": "INTEGER",
            "usuario_id": "INTEGER",
            "abertura": "TIMESTAMP",
            "fechamento": "TIMESTAMP",
            "valor_inicial": "REAL",
            "valor_final": "REAL",
            "total_vendas": "REAL",
            "quantidade_vendas": "INTEGER",
            "diferenca": "REAL",
            "observacao": "TEXT",
        },
        "required": ["usuario_id"],
    },
    "garcons": {
        "columns": {
            "id": "INTEGER",
            "nome": "TEXT",
            "telefone": "TEXT",
            "comissao": "REAL",
            "ativo": "INTEGER",
            "criado_em": "TIMESTAMP",
        },
        "required": ["nome"],
    },
    "contas_pagar": {
        "columns": {
            "id": "INTEGER",
            "fornecedor": "TEXT",
            "descricao": "TEXT",
            "valor": "REAL",
            "vencimento": "DATE",
            "pagamento": "DATE",
            "status": "TEXT",
            "usuario_id": "INTEGER",
            "observacao": "TEXT",
            "criado_em": "TIMESTAMP",
        },
        "required": ["fornecedor", "descricao", "valor", "vencimento"],
    },
    "suprimento_sangria": {
        "columns": {
            "id": "INTEGER",
            "caixa_id": "INTEGER",
            "usuario_id": "INTEGER",
            "tipo": "TEXT",
            "valor": "REAL",
            "motivo": "TEXT",
            "data_hora": "TIMESTAMP",
        },
        "required": ["tipo", "valor"],
    },
    "historico_transferencias": {
        "columns": {
            "id": "INTEGER",
            "comanda_id": "INTEGER",
            "mesa_origem_id": "INTEGER",
            "mesa_destino_id": "INTEGER",
            "usuario_id": "INTEGER",
            "data_hora": "TIMESTAMP",
            "observacao": "TEXT",
        },
        "required": ["mesa_origem_id", "mesa_destino_id"],
    },
    "login_attempts": {
        "columns": {
            "id": "INTEGER",
            "login": "TEXT",
            "criado_em": "TIMESTAMP",
        },
        "required": ["login"],
    },
    "empresa": {
        "columns": {
            "id": "INTEGER",
            "razao_social": "TEXT",
            "nome_fantasia": "TEXT",
            "cnpj": "TEXT",
            "inscricao_estadual": "TEXT",
            "endereco": "TEXT",
            "telefone": "TEXT",
            "email": "TEXT",
            "horario_funcionamento": "TEXT",
            "observacao": "TEXT",
        },
        "required": [],
    },
}

REQUIRED_INDEXES = [
    "fiado(cliente_id)",
    "vendas(data)",
    "movimentacoes(produto_id)",
    "itens_comanda(comanda_id)",
    "itens_venda(venda_id)",
    "itens_venda(produto_id)",
    "auditoria(data_hora)",
    "login_attempts(login)",
    "login_attempts(criado_em)",
    "comandas(mesa_id)",
    "comandas(status)",
    "contas_pagar(vencimento)",
    "contas_pagar(status)",
    "garcons(ativo)",
    "historico_transferencias(comanda_id)",
    "historico_transferencias(mesa_origem_id)",
    "suprimento_sangria(caixa_id)",
]


class CompatibilityAnalyzer:
    def __init__(self, analysis_result):
        self.result = analysis_result
        self.tipo = analysis_result.get("tipo_fonte", "")
        self.source_tables = self._build_source_tables()

    def _build_source_tables(self):
        tables = {}
        for tbl in self.result.get("tabelas", []):
            name = tbl.get("nome", "")
            tables[name] = {
                "name": name,
                "columns": tbl.get("cabecalhos", []),
                "record_count": tbl.get("registros", 0),
                "col_count": tbl.get("colunas", len(tbl.get("cabecalhos", []))),
            }
        if self.tipo == "sqlite":
            self._enrich_from_sqlite(tables)
        elif self.tipo == "sql":
            self._enrich_from_sql(tables)
        return tables

    def _enrich_from_sqlite(self, tables):
        import os
        import sqlite3 as sq3
        filepath = self.result.get("_filepath")
        if not filepath or not os.path.exists(filepath):
            return
        try:
            conn = sq3.connect(f"file:{filepath}?mode=ro", uri=True)
            cur = conn.cursor()
            db_tables = cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            for (tname,) in db_tables:
                try:
                    cols = cur.execute(f'PRAGMA table_info("{tname}")').fetchall()
                    col_names = [c[1] for c in cols]
                    col_types = {c[1]: c[2].upper() for c in cols}
                    count = cur.execute(f'SELECT COUNT(*) FROM "{tname}"').fetchone()[0]
                    if tname in tables:
                        tables[tname]["columns"] = col_names
                        tables[tname]["col_types"] = col_types
                        tables[tname]["record_count"] = count
                    else:
                        tables[tname] = {
                            "name": tname,
                            "columns": col_names,
                            "col_types": col_types,
                            "record_count": count,
                            "col_count": len(col_names),
                        }
                except Exception:
                    pass
            conn.close()
        except Exception:
            pass

    def _enrich_from_sql(self, tables):
        filepath = self.result.get("_filepath")
        if not filepath:
            return
        try:
            with open(filepath, "rb") as f:
                raw = f.read()
            import chardet
            enc = chardet.detect(raw).get("encoding", "utf-8") or "utf-8"
            content = raw.decode(enc, errors="replace")
            parsed = self.parse_sql_ddl(content)
            for tname, col_names in parsed.items():
                col_types = {c: "TEXT" for c in col_names}
                existing = tables.get(tname, {})
                count = existing.get("record_count", 0)
                tables[tname] = {
                    "name": tname,
                    "columns": col_names,
                    "col_types": col_types,
                    "record_count": count,
                    "col_count": len(col_names),
                }
        except Exception:
            pass

    @staticmethod
    def parse_sql_ddl(content):
        result = {}
        table_pattern = re.compile(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"']?(\w+)[`\"']?\s*\((.*?)\)",
            re.IGNORECASE | re.DOTALL,
        )
        for match in table_pattern.finditer(content):
            tname = match.group(1).lower()
            body = match.group(2)
            cols = []
            for line in body.split(","):
                line = line.strip()
                if not line or line.upper().startswith(("PRIMARY", "UNIQUE", "CHECK", "FOREIGN", "CONSTRAINT")):
                    continue
                parts = line.split()
                if parts:
                    col = parts[0].strip('`"\'[]').lower()
                    if col:
                        cols.append(col)
            if cols:
                result[tname] = cols
        return result

    def analyze(self):
        source = self.source_tables
        expected = EXPECTED_TABLES
        issues = []

        source_names = {n.lower() for n in source.keys()}
        expected_names = set(expected.keys())

        missing_tables = expected_names - source_names
        extra_tables = source_names - expected_names

        mapping = self._map_tables(source, expected)

        for tname in sorted(missing_tables):
            issues.append({
                "tipo": "tabela_ausente",
                "severidade": "critico",
                "tabela": tname,
                "mensagem": f"Tabela '{tname}' não encontrada no arquivo",
                "detalhes": f"Tabela requerida pelo sistema ausente na fonte de dados",
            })

        for tname in sorted(extra_tables):
            issues.append({
                "tipo": "tabela_extras",
                "severidade": "info",
                "tabela": tname,
                "mensagem": f"Tabela '{tname}' encontrada mas não é utilizada pelo sistema",
                "detalhes": "Dados desta tabela serão ignorados na importação",
            })

        matched_tables = []
        for source_name, expected_name in mapping.items():
            if not expected_name:
                continue
            exp = expected[expected_name]
            src = source.get(source_name, {})
            src_cols = [c.lower() for c in src.get("columns", [])]
            src_types = src.get("col_types", {})
            exp_cols = set(exp["columns"].keys())
            exp_required = set(exp.get("required", []))

            table_issues, table_score = self._compare_table(
                expected_name, src_cols, src_types, exp_cols, exp_required, exp
            )
            issues.extend(table_issues)
            matched_tables.append({
                "nome": expected_name,
                "compatibilidade": table_score,
                "colunas_encontradas": len(set(src_cols) & exp_cols),
                "colunas_totais": len(exp_cols),
                "registros": src.get("record_count", 0),
            })

        self._check_indexes(issues)
        self._check_data_issues(issues, source, expected, mapping)

        criticos = sum(1 for i in issues if i["severidade"] == "critico")
        avisos = sum(1 for i in issues if i["severidade"] == "aviso")
        informativos = sum(1 for i in issues if i["severidade"] == "info")

        if matched_tables:
            compat = sum(t["compatibilidade"] for t in matched_tables) / len(matched_tables)
        else:
            compat = 0.0 if missing_tables else 100.0

        if missing_tables and len(expected) > 0:
            coverage = len(matched_tables) / len(expected)
            coverage_score = coverage * 100
            compat = (compat + coverage_score) / 2

        compat = round(min(100.0, max(0.0, compat)), 1)
        classificacao = self._classificar(compat)

        return {
            "ok": self.result.get("ok", False),
            "tipo_fonte": self.tipo,
            "arquivo_nome": self.result.get("arquivo_nome", ""),
            "compatibilidade_index": compat,
            "classificacao": classificacao,
            "total_tabelas_esperadas": len(expected),
            "total_tabelas_encontradas": len(source),
            "total_tabelas_mapeadas": len(matched_tables),
            "total_registros": self.result.get("total_registros", 0),
            "pode_importar": criticos == 0,
            "tabelas": matched_tables,
            "issues": issues,
            "criticos": criticos,
            "avisos": avisos,
            "informativos": informativos,
        }

    def _map_tables(self, source, expected):
        mapping = {}
        for src_name in source:
            lower = src_name.lower().strip()
            if lower in expected:
                mapping[src_name] = lower
                continue
            best = None
            best_score = 0
            for exp_name in expected:
                if lower == exp_name:
                    score = 100
                elif lower.replace("_", "") == exp_name.replace("_", ""):
                    score = 95
                elif lower in exp_name or exp_name in lower:
                    score = 70
                else:
                    common = set(lower.split("_")) & set(exp_name.split("_"))
                    score = len(common) * 30 if common else 0
                if score > best_score:
                    best_score = score
                    best = exp_name
            if best_score >= 30:
                mapping[src_name] = best
            else:
                mapping[src_name] = None
        return mapping

    def _compare_table(self, tname, src_cols, src_types, exp_cols, exp_required, exp_def):
        issues = []
        src_set = set(c.lower() for c in src_cols)

        matched_cols = src_set & exp_cols
        missing_cols = exp_cols - src_set
        extra_cols = src_set - exp_cols

        for col in sorted(exp_required & missing_cols):
            issues.append({
                "tipo": "coluna_obrigatoria_ausente",
                "severidade": "critico",
                "tabela": tname,
                "mensagem": f"Coluna obrigatória '{col}' ausente na tabela '{tname}'",
                "detalhes": "Coluna essencial para o funcionamento do sistema",
            })

        for col in sorted(missing_cols - exp_required):
            issues.append({
                "tipo": "coluna_ausente",
                "severidade": "aviso",
                "tabela": tname,
                "mensagem": f"Coluna '{col}' não encontrada na tabela '{tname}'",
                "detalhes": "Coluna opcional ausente; dados serão preenchidos com valores padrão",
            })

        for col in sorted(extra_cols):
            issues.append({
                "tipo": "coluna_extras",
                "severidade": "info",
                "tabela": tname,
                "mensagem": f"Coluna extra '{col}' na tabela '{tname}'",
                "detalhes": "Coluna não mapeada; será ignorada na importação",
            })

        if src_types:
            for col in sorted(matched_cols):
                exp_type = exp_def["columns"].get(col, "")
                src_type = src_types.get(col, "")
                if exp_type and src_type and not self._types_compatible(src_type, exp_type):
                    issues.append({
                        "tipo": "tipo_incompativel",
                        "severidade": "aviso",
                        "tabela": tname,
                        "mensagem": f"Tipo incompatível para '{col}' em '{tname}': {src_type} → {exp_type}",
                        "detalhes": "A conversão de tipo pode causar perda de dados",
                    })

        if not src_cols:
            return issues, 0.0

        base = len(matched_cols) / len(exp_cols) * 100 if exp_cols else 0
        if extra_cols:
            base = max(0, base - len(extra_cols) * 2)

        critical_in_table = sum(
            1 for i in issues
            if i["severidade"] == "critico" and i["tabela"] == tname
        )
        if critical_in_table:
            return issues, 0.0

        return issues, round(min(100.0, base), 1)

    @staticmethod
    def _types_compatible(src_type, exp_type):
        src = src_type.upper().split("(")[0].strip()
        exp = exp_type.upper().split("(")[0].strip()
        if src == exp:
            return True
        compat = {
            "INTEGER": {"INTEGER", "INT", "BIGINT", "SMALLINT", "TINYINT", "BOOLEAN", "NUMERIC"},
            "REAL": {"REAL", "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC"},
            "TEXT": {"TEXT", "VARCHAR", "CHAR", "STRING", "CLOB", "NVARCHAR"},
            "TIMESTAMP": {"TIMESTAMP", "DATETIME", "DATE", "TEXT"},
            "DATE": {"DATE", "TEXT", "TIMESTAMP"},
        }
        return exp in compat.get(src, set()) or src in compat.get(exp, set())

    def _check_indexes(self, issues):
        if self.tipo != "sqlite":
            return
        filepath = self.result.get("_filepath")
        if not filepath:
            return
        try:
            import sqlite3 as sq3
            conn = sq3.connect(f"file:{filepath}?mode=ro", uri=True)
            cur = conn.cursor()
            idx_rows = cur.execute(
                "SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"
            ).fetchall()
            existing_idx = set()
            for (sql,) in idx_rows:
                m = re.search(r"ON\s+(\w+)\s*\(([^)]+)\)", sql, re.IGNORECASE)
                if m:
                    tbl = m.group(1).lower()
                    cols = ",".join(sorted(c.strip().lower() for c in m.group(2).split(",")))
                    existing_idx.add(f"{tbl}({cols})")
            conn.close()
            for idx_def in REQUIRED_INDEXES:
                tbl_name = idx_def.split("(")[0]
                m = re.search(r"\(([^)]+)\)", idx_def)
                if m:
                    cols = ",".join(sorted(c.strip().lower() for c in m.group(1).split(",")))
                    normalized = f"{tbl_name}({cols})"
                    if normalized not in existing_idx:
                        issues.append({
                            "tipo": "indice_ausente",
                            "severidade": "info",
                            "tabela": tbl_name,
                            "mensagem": f"Índice ausente: {idx_def}",
                            "detalhes": "O sistema criará este índice automaticamente",
                        })
        except Exception:
            pass

    def _check_data_issues(self, issues, source, expected, mapping):
        for source_name, expected_name in mapping.items():
            if not expected_name:
                continue
            src = source.get(source_name, {})
            exp = expected.get(expected_name, {})
            if src.get("record_count", 0) == 0:
                issues.append({
                    "tipo": "tabela_vazia",
                    "severidade": "aviso",
                    "tabela": expected_name,
                    "mensagem": f"Tabela '{expected_name}' está vazia",
                    "detalhes": "Nenhum registro encontrado para importação",
                })
            if self.tipo == "sqlite":
                self._check_null_required(expected_name, src, exp, issues)

    def _check_null_required(self, tname, src, exp, issues):
        filepath = self.result.get("_filepath")
        if not filepath:
            return
        try:
            import sqlite3 as sq3
            conn = sq3.connect(f"file:{filepath}?mode=ro", uri=True)
            cur = conn.cursor()
            src_cols = [c.lower() for c in src.get("columns", [])]
            required = exp.get("required", [])
            exp_col_map = exp.get("columns", {})
            for col in required:
                if col not in src_cols:
                    continue
                try:
                    exp_type = exp_col_map.get(col, "TEXT").upper()
                    if "TIMESTAMP" in exp_type or "DATE" in exp_type:
                        count = cur.execute(
                            f'SELECT COUNT(*) FROM "{tname}" WHERE "{col}" IS NULL OR "{col}" = ""'
                        ).fetchone()[0]
                    else:
                        count = cur.execute(
                            f'SELECT COUNT(*) FROM "{tname}" WHERE "{col}" IS NULL'
                        ).fetchone()[0]
                    if count > 0:
                        issues.append({
                            "tipo": "valores_nulos",
                            "severidade": "aviso",
                            "tabela": tname,
                            "mensagem": f"{count} registro(s) com '{col}' nulo/vazio em '{tname}'",
                            "detalhes": "Registros com valores obrigatórios ausentes",
                        })
                except Exception:
                    pass
            conn.close()
        except Exception:
            pass

    @staticmethod
    def _classificar(pct):
        if pct >= 90:
            return "Excelente"
        if pct >= 70:
            return "Bom"
        if pct >= 50:
            return "Parcial"
        return "Incompatível"


def gerar_relatorio_html(report):
    issues_criticos = [i for i in report["issues"] if i["severidade"] == "critico"]
    issues_avisos = [i for i in report["issues"] if i["severidade"] == "aviso"]
    issues_info = [i for i in report["issues"] if i["severidade"] == "info"]

    if report["compatibilidade_index"] >= 90:
        cor_barra = "#4ade80"
    elif report["compatibilidade_index"] >= 70:
        cor_barra = "#D4AF37"
    elif report["compatibilidade_index"] >= 50:
        cor_barra = "#fb923c"
    else:
        cor_barra = "#f87171"

    def render_issue(i):
        sev = i["severidade"]
        if sev == "critico":
            icon = "✖"
            cor = "#f87171"
        elif sev == "aviso":
            icon = "⚠"
            cor = "#fbbf24"
        else:
            icon = "ℹ"
            cor = "#60a5fa"
        return f'''<div style="padding:8px 12px;border-bottom:1px solid rgba(255,255,255,0.05);">
            <span style="color:{cor};font-weight:bold;">{icon}</span>
            <span style="color:#fff;font-weight:500;">{i["mensagem"]}</span>
            <div style="color:#999;font-size:11px;margin-top:2px;">{i["detalhes"]}</div>
        </div>'''

    issues_html = "".join(render_issue(i) for i in report["issues"]) if report["issues"] else '<div style="padding:12px;color:#4ade80;">Nenhum problema encontrado.</div>'

    tabelas_rows = ""
    for t in report["tabelas"]:
        pct = t["compatibilidade"]
        if pct >= 90:
            cor_t = "#4ade80"
        elif pct >= 70:
            cor_t = "#D4AF37"
        elif pct >= 50:
            cor_t = "#fb923c"
        else:
            cor_t = "#f87171"
        tabelas_rows += f'''<tr>
            <td style="padding:8px 12px;color:#fff;">{t["nome"]}</td>
            <td style="padding:8px 12px;text-align:center;">
                <span style="color:{cor_t};font-weight:bold;">{pct}%</span>
            </td>
            <td style="padding:8px 12px;text-align:center;color:#999;">{t["colunas_encontradas"]}/{t["colunas_totais"]}</td>
            <td style="padding:8px 12px;text-align:center;color:#999;">{t["registros"]}</td>
        </tr>'''

    return f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Relatório de Compatibilidade - Migração</title>
<style>
body {{ background:#0d0d0d; color:#fff; font-family:Inter,sans-serif; margin:0; padding:20px; }}
.container {{ max-width:800px; margin:0 auto; }}
h1 {{ color:#D4AF37; font-size:24px; margin-bottom:8px; }}
h2 {{ color:#D4AF37; font-size:18px; margin-top:24px; margin-bottom:12px; border-bottom:1px solid #333; padding-bottom:6px; }}
.header {{ text-align:center; margin-bottom:24px; }}
.score {{ font-size:48px; font-weight:bold; color:{cor_barra}; }}
.subtitle {{ color:#999; font-size:14px; }}
.bar {{ background:#222; border-radius:8px; height:12px; margin:12px 0; overflow:hidden; }}
.bar-fill {{ height:100%; border-radius:8px; background:{cor_barra}; width:{report["compatibilidade_index"]}%; }}
.stats {{ display:flex; gap:16px; margin:16px 0; }}
.stat {{ flex:1; background:#1a1a1a; border-radius:8px; padding:12px; text-align:center; border:1px solid #333; }}
.stat-num {{ font-size:24px; font-weight:bold; }}
.stat-label {{ font-size:12px; color:#999; margin-top:4px; }}
table {{ width:100%; border-collapse:collapse; background:#1a1a1a; border-radius:8px; overflow:hidden; }}
th {{ background:#111; padding:10px 12px; text-align:left; color:#D4AF37; font-size:12px; text-transform:uppercase; }}
.issue-list {{ background:#1a1a1a; border-radius:8px; border:1px solid #333; }}
.pode-importar {{ text-align:center; margin:20px 0; padding:12px; border-radius:8px; font-weight:bold; font-size:16px; }}
.footer {{ text-align:center; color:#666; font-size:11px; margin-top:24px; }}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>Relatório de Compatibilidade</h1>
<p class="subtitle">{report["arquivo_nome"]} — {report["tipo_fonte"].upper()}</p>
</div>
<div class="score">{report["compatibilidade_index"]}%</div>
<div class="bar"><div class="bar-fill"></div></div>
<p class="subtitle" style="text-align:center;">Classificação: <strong style="color:{cor_barra};">{report["classificacao"]}</strong></p>
<div class="stats">
<div class="stat"><div class="stat-num" style="color:#4ade80;">{report["total_tabelas_encontradas"]}</div><div class="stat-label">Tabelas encontradas</div></div>
<div class="stat"><div class="stat-num" style="color:#D4AF37;">{report["total_tabelas_mapeadas"]}</div><div class="stat-label">Mapeadas</div></div>
<div class="stat"><div class="stat-num" style="color:#60a5fa;">{report["total_registros"]}</div><div class="stat-label">Registros</div></div>
</div>
<div class="stats">
<div class="stat"><div class="stat-num" style="color:#f87171;">{report["criticos"]}</div><div class="stat-label">Críticos</div></div>
<div class="stat"><div class="stat-num" style="color:#fbbf24;">{report["avisos"]}</div><div class="stat-label">Avisos</div></div>
<div class="stat"><div class="stat-num" style="color:#60a5fa;">{report["informativos"]}</div><div class="stat-label">Informativos</div></div>
</div>
<h2>Compatibilidade por Tabela</h2>
<table>
<thead><tr><th>Tabela</th><th style="text-align:center;">Compat.</th><th style="text-align:center;">Colunas</th><th style="text-align:center;">Registros</th></tr></thead>
<tbody>{tabelas_rows}</tbody>
</table>
<h2>Problemas Encontrados</h2>
<div class="issue-list">{issues_html}</div>
<div class="pode-importar" style="{"background:rgba(22,163,74,0.15);color:#4ade80;border:1px solid rgba(22,163,74,0.3);" if report["pode_importar"] else "background:rgba(220,38,38,0.15);color:#f87171;border:1px solid rgba(220,38,38,0.3);"}">
{"✔ Importação permitida — nenhum erro crítico encontrado" if report["pode_importar"] else "✖ Importação bloqueada — erros críticos devem ser corrigidos primeiro"}
</div>
<div class="footer">Gerado em {datetime.now().strftime("%d/%m/%Y %H:%M:%S")} — Assistente de Migração JAM'S BURGUER</div>
</div>
</body>
</html>'''
