# Relatório de importação dos dados reais da adega

Data da execução: 31/07/2026

## 1. Arquivos encontrados e analisados

| Arquivo | Formato | Tamanho | SHA-256 |
|---|---:|---:|---|
| `TELA CRIADO POR FERNANDO/ADEGA/backp sistema antigo/BCK_DATACAIXA-30072026-2055.fbk` | Backup lógico Firebird 5 | 38.674.944 bytes | `64BDD2E8CEDAB08B5F5ACAC600D0CDFF287D61F6026F1D2FD668F7B895234A63` |
| `TELA CRIADO POR FERNANDO/ADEGA/DATACAIXA_TESTE.FDB` | Banco Firebird 5 restaurado | 72.536.064 bytes | `D4DEEBC5ADCA8470CBFF4FC99F4F255DD931024348D87B2D855C90473A1B5C42` |

O `.fbk` foi restaurado novamente em uma área temporária somente para conferência. A restauração e o
`.FDB` convertido apresentaram as mesmas 94 tabelas, 1.569 campos, contagens, intervalos de IDs,
quantidades, estoques e totais monetários nos conjuntos relevantes. Por estar completo e consistente,
o arquivo usado como fonte da importação foi o `DATACAIXA_TESTE.FDB`, por meio de uma cópia temporária.
Os dois arquivos originais permaneceram com os hashes registrados antes da operação.

## 2. Backup preventivo

- Banco anterior: `data/backups/bar_adega_pre_importacao_real_20260731.db` — 778.240 bytes.
- Projeto completo anterior: `E:/BACKUP_COMPLETO_PROJETO_PRE_IMPORTACAO_20260731.tar.gz` — 174.770.977 bytes.

## 3. Dados substituídos

| Conjunto | Antes | Depois |
|---|---:|---:|
| Categorias | 14 | 9 |
| Produtos | 53 | 265 |
| Clientes | 17 | 81 |
| Funcionários/garçons | 5 | 10 |
| Mesas | 40 | 40 |
| Comandas abertas | 7 | 18 |
| Itens em comandas abertas | 10 | 75 |
| Vendas | 13 | 26.058 |
| Itens de venda | 13 | 45.520 |
| Lançamentos de fiado | 2 | 2.356 |
| Caixas | 2 | 732 |
| Movimentações | 24 | 47.618 |
| Pagamentos parciais fictícios | 2 | 0 |
| Auditoria fictícia | 172 | 1 registro da importação |

A empresa foi substituída pelos dados de `JAMS BURGUER CONVENIENCIA`. A conta administrativa local
foi preservada para manter o acesso. A conta genérica fictícia `Funcionário` foi removida. Os três
usuários históricos do Firebird foram importados como contas inativas e associados às vendas e caixas.

## 4. Registros processados

- 265 produtos, com nome/descrição, categoria quando informada, código de barras ou código interno,
  preço de venda, estoque, estoque mínimo, unidade e situação.
- 9 categorias.
- 81 clientes, incluindo dados de contato, documento, endereço, observações e saldos de fiado compatíveis.
- 26.058 vendas, das quais 11 estavam canceladas na fonte.
- 45.520 itens de venda.
- 2.356 lançamentos de crédito/fiado, com pagamentos distribuídos sobre as compras e saldo final validado.
- 732 caixas.
- 10 funcionários/garçons.
- 40 mesas; 18 ficaram ocupadas porque correspondem aos 18 pedidos ainda abertos no backup.
- 75 itens desses pedidos abertos.
- 47.618 movimentações: 1.604 entradas de compra, 440 saídas avulsas, 45.499 itens de vendas ativas e
  75 itens de comandas abertas.
- 20 imagens BMP de produtos, preservadas em `static/uploads/produtos/` e nomeadas pelo ID do produto.

Totais conferidos com a fonte:

- Soma dos preços cadastrados: R$ 3.030,85.
- Estoque agregado: -2.744 unidades.
- Total histórico de vendas: R$ 416.691,65.
- Quantidade histórica dos itens de venda: 85.062 unidades.
- Período das vendas: 12/04/2011 a 30/07/2026.

## 5. Avisos e dados não representáveis

Não ocorreu erro nem rejeição durante a importação. As seguintes limitações vêm da fonte ou do modelo
do sistema atual:

- 83 produtos não informam grupo/categoria no Firebird e permaneceram sem categoria.
- 7 produtos têm preço de venda igual a zero na fonte.
- 86 produtos têm estoque negativo na fonte; os valores foram mantidos sem correção artificial.
- 1 cliente inativo não possui nome e recebeu a identificação técnica `Cliente legado sem nome (ID 0)`.
- O backup não contém cadastro utilizável de fornecedores: há somente um registro de empresa vazio e
  nenhuma compra aponta para um fornecedor real. Nenhum fornecedor foi inventado e contas a pagar ficou vazia.
- O banco atual não possui campos para preço de custo, estoque máximo, NCM, CEST e detalhes tributários.
  Esses campos não foram inseridos em colunas inadequadas, preservando a estrutura do sistema.
- Quando um produto possui código interno e código de barras, o ID original e o código de barras foram
  preservados; nos produtos sem código de barras, o código interno foi usado no campo de código.
- As imagens foram preservadas e associadas pelo ID no nome do arquivo, sem mudar o layout das telas.

## 6. Validações finais

- `PRAGMA integrity_check`: `ok`.
- Erros de chaves estrangeiras: 0.
- Divergências entre saldo armazenado e compras de fiado abertas: 0.
- Login administrativo: aprovado.
- Dashboard, produtos, clientes, estoque, mesas, vendas, relatórios e manutenção: HTTP 200.
- Arquivos BMP: carregamento HTTP 200 com o tipo `image/bmp`.
- Suíte automatizada: 274 testes aprovados, nenhuma falha.

## 7. Arquivos criados ou modificados nesta importação

- `bar_adega.db` — dados operacionais substituídos.
- `requirements.txt` — dependência de leitura do Firebird registrada.
- `migration/import_adega_firebird.py` — importador transacional e auditável.
- `data/importacao_adega_20260731.json` — manifesto detalhado da execução.
- `static/uploads/produtos/produto_*.bmp` — 20 imagens extraídas.
- `data/backups/bar_adega_pre_importacao_real_20260731.db` — cópia do banco anterior.
- `E:/BACKUP_COMPLETO_PROJETO_PRE_IMPORTACAO_20260731.tar.gz` — cópia completa do projeto anterior.

