# Relatório — ajustes visuais e PDV rápido

Data: 31/07/2026

## Resultado

As quatro correções enviadas por print foram implementadas: acabamento dos temas, nova tipografia, menu lateral com presença permanente e PDV transformado em uma operação rápida sem imagens.

## Backup anterior às alterações

- Pasta: `E:\BACKUP_AJUSTES_VISUAIS_20260731_233345`
- Projeto completo: `PROJETO_ANTES_AJUSTES_VISUAIS.tar.gz`
- Tamanho: 193.267.934 bytes
- SHA-256: `330E581234CC099756E2AE0B5FB7F07BED6A55F259384BC9F400C0B4AAE0280C`
- Banco separado: `BANCOS\bar_adega.db`
- SHA-256 do banco: `09B7DCD2D2E8F7CA69B4C156B0C555279BD0D04BF892F4F329A67728CD52848F`

## 1. Identidade visual geral

- O tema escuro deixou de usar preto puro e recebeu superfícies em carvão esverdeado, dourado controlado, melhor contraste e profundidade suave.
- O tema claro recebeu fundo creme mais uniforme, cartões brancos, bordas discretas e sombras leves.
- Os cartões do dashboard ficaram mais compactos, com ícones alinhados, valores mais legíveis e menor excesso de espaço.
- Os botões globais e controles superiores foram reduzidos sem perder a área segura de clique.
- O sino, o contador de alertas, o tema e o relógio passaram a formar um conjunto visual coerente.

## 2. Tipografia

- Títulos do sistema passaram a usar `Sora`, com desenho moderno e profissional.
- Textos operacionais continuam com `Manrope`.
- “Visão geral”, títulos de páginas, números dos cards e títulos internos receberam pesos e espaçamentos mais consistentes.

## 3. Menu lateral

- Os ícones aprovados foram mantidos.
- Cada item agora apresenta fundo, borda, ícone em cápsula e sombra discreta mesmo sem passar o mouse.
- O item ativo permanece mais destacado, com faixa dourada e ícone preenchido.
- Estados normal, hover, foco e clique ficaram visualmente distintos.
- O avatar com a letra “A” foi substituído por um ícone profissional de perfil/segurança e indicador de usuário ativo.
- O recolhimento, a expansão e o comportamento móvel foram preservados.

## 4. PDV rápido

- A grade de produtos com imagens foi removida da área principal.
- Nenhuma fotografia ou miniatura é carregada no novo PDV.
- O acesso rápido passou a ocupar o centro da operação.
- Foram exibidos quatro grupos reais, nesta ordem:
  1. Cigarros soltos — 5 cadastros;
  2. Doses — 24 cadastros;
  3. Fichas de sinuca e jogos — 2 cadastros;
  4. Por peso e medida — 1 cadastro.
- Os produtos de cada grupo aparecem como linhas compactas, mostrando somente nome, categoria/código, preço e disponibilidade.
- O catálogo completo foi preservado como opção secundária recolhida e só é carregado quando solicitado.
- Ao abrir o catálogo, foram carregadas 10 opções de categoria e 60 linhas, sem imagens.

## 5. Pesquisa e leitor

- A busca continua instantânea, com atraso técnico curto de 120 ms para evitar chamadas duplicadas.
- No teste com o texto `coca`, 13 produtos reais apareceram imediatamente.
- No teste com o código `7894900014211`, o produto correto foi localizado e lançado diretamente no carrinho por R$ 9,00.
- O item de teste foi removido do carrinho antes da entrega; nenhuma venda foi finalizada.
- O leitor USB continua funcionando mesmo sem foco manual no campo.
- A opção de leitura por câmera foi mantida em um botão menor.

## Arquivos modificados nesta rodada

- `static/css/clean-theme.css`
- `templates/base.html`
- `templates/vendas.html`
- `routes/produtos_routes.py`
- `tests/test_permissions_and_refinement.py`
- `RELATORIO_AJUSTES_VISUAIS_PDV_20260731.md`

## Testes e validações

- 40 testes direcionados aprovados.
- 314 testes completos aprovados em 380,44 segundos.
- 31 templates compilados sem erro.
- Nenhum erro JavaScript encontrado no navegador.
- Clique direto sobre o ícone do menu abriu corretamente o Dashboard.
- Tema claro e tema escuro inspecionados visualmente.
- Pesquisa, grupo de fichas, catálogo recolhível e leitura de código validados no navegador.

## Integridade e preservação dos dados

- Integridade SQLite: `ok`.
- Chaves estrangeiras inválidas: 0.

| Entidade | Antes | Depois |
|---|---:|---:|
| Categorias | 9 | 9 |
| Produtos | 265 | 265 |
| Clientes | 85 | 85 |
| Usuários | 4 | 4 |
| Vendas | 26.059 | 26.059 |
| Itens de venda | 45.521 | 45.521 |
| Movimentações | 47.620 | 47.620 |
| Mesas | 40 | 40 |

Somente a auditoria recebeu registros normais dos acessos realizados durante a validação. Nenhum estoque, produto ou venda real foi modificado.

## Observação operacional

Os produtos reais de cigarros soltos, doses e fichas estão atualmente com estoque zerado ou negativo. Eles aparecem corretamente no acesso rápido, mas continuam protegidos pela regra que impede vender sem estoque. Nenhuma quantidade fictícia foi criada.

