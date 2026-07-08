# PRD CONSOLIDADO — SISTEMA DE GESTÃO PARA BAR, ADEGA E MESAS

**Versão:** 2.1 (consolidada)
**Status:** Pronto para desenvolvimento
**Stack Base:** Flask (Python) + SQLite + HTML/CSS/JS
**Stack Mobile:** React Native ou Flutter
**Stack Tempo Real:** WebSocket / Socket.IO
**Stack Notificações:** Firebase Cloud Messaging (FCM)

---

## 1. VISÃO GERAL

Criar um sistema moderno, rápido e intuitivo para gerenciamento completo de um estabelecimento (bar, adega, tabacaria ou distribuidora), contemplando vendas, mesas, estoque, usuários, auditoria, relatórios, dashboard em tempo real, **aplicativo mobile para o administrador**, **notificações push** e **sincronização em tempo real**.

O sistema deve permitir que o proprietário acompanhe toda a operação do estabelecimento em tempo real, inclusive remotamente, pelo celular.

---

## 2. PERFIS DE USUÁRIO

### 2.1 Administrador
Acesso total ao sistema (web e mobile).

**Permissões:**
- Gerenciar produtos
- Gerenciar estoque
- Gerenciar usuários
- Gerenciar mesas
- Visualizar relatórios
- Visualizar dashboards completos
- Consultar auditorias
- Configurar sistema
- Acessar aplicativo mobile
- Receber notificações push
- Executar logout remoto

### 2.2 Funcionário
Acesso restrito ao sistema (apenas web/POS local).

**Pode:**
- Realizar vendas
- Abrir mesas
- Fechar mesas
- Consultar estoque
- Registrar movimentações autorizadas

**Não pode:**
- Excluir produtos
- Alterar permissões
- Visualizar auditorias completas
- Acessar configurações administrativas
- Acessar aplicativo mobile

---

## 3. SISTEMA WEB (FRENTE DE CAIXA / SALÃO)

### 3.1 Dashboard em Tempo Real
Atualização automática sem necessidade de recarregar a página (polling 5–10s ou WebSocket).

**Indicadores exibidos:**
- Faturamento do dia
- Faturamento do mês
- Vendas em andamento
- Mesas ocupadas
- Mesas livres
- Mesas reservadas
- Ticket médio
- Total de pedidos no dia
- Produtos vendidos no dia
- Produtos mais vendidos
- Estoque crítico
- Entradas de estoque (dia)
- Saídas de estoque (dia)

**Gráficos:**
- Vendas por hora (identificar horários de pico)
- Vendas por dia (últimos 7 e 30 dias)
- Produtos mais vendidos (ranking visual)
- Ocupação das mesas (donut)
- Entradas x Saídas de estoque

---

## 4. GESTÃO DE MESAS

### 4.1 Status
- **Disponível** — Mesa livre
- **Ocupada** — Possui consumo em andamento
- **Reservada** — Reservada para cliente
- **Em Fechamento** — Conta sendo encerrada

### 4.2 Mapa Visual do Salão
Exibição visual de todas as mesas em grid.

**Cada mesa exibe:**
- Número da mesa
- Status (cor/badge)
- Tempo de ocupação
- Valor consumido

```
┌─────────────┐
│ Mesa 01     │
│ ● Ocupada   │
│ 01h35min    │
│ R$ 187,90   │
└─────────────┘
```

### 4.3 Controle de Consumo
Ao lançar um pedido:
- Produto é vinculado à mesa
- Estoque é atualizado automaticamente
- Consumo é atualizado em tempo real
- Item registrado na comanda ativa

### 4.4 Comandas

**Abrir Comanda**
- Mesa
- Data / Hora (automático)
- Funcionário responsável (sessão)

**Adicionar Produtos**
- Leitor de código de barras
- Busca manual por nome
- Seleção por categoria

**Fechar Comanda**
- Gera venda automaticamente
- Atualiza estoque
- Atualiza relatórios
- Libera a mesa
- Suporte a desconto e múltiplas formas de pagamento

---

## 5. CADASTRO DE PRODUTOS

### 5.1 Campos
- Nome
- Categoria
- Código de barras
- Preço
- Estoque atual
- Estoque mínimo
- Unidade de medida

### 5.2 Categorias padrão
- Vinhos
- Whisky
- Vodka
- Gin
- Cervejas
- Refrigerantes
- Energéticos
- Água
- Petiscos
- Porções
- Drinks
- Outros

### 5.3 Leitor de Código de Barras
Funcionalidade obrigatória.

**Fluxo ao escanear:**
1. Identifica produto pelo código
2. Busca informações
3. Adiciona à venda/comanda
4. Atualiza estoque

---

## 6. CONTROLE DE ESTOQUE

### 6.1 Movimentações

**Entrada**
- Produto
- Quantidade
- Usuário
- Data / Hora
- Observação

**Saída**
- Produto
- Quantidade
- Motivo (Venda, Perda, Quebra, Consumo interno, Ajuste)
- Usuário
- Data / Hora

### 6.2 Atualização em Tempo Real
Toda movimentação deve refletir imediatamente no sistema.

### 6.3 Alertas Automáticos
- **Estoque Baixo:** "⚠ Estoque crítico: Heineken Long Neck"
- **Produto Zerado:** "🚨 Produto indisponível"

---

## 7. SISTEMA DE VENDAS

### 7.1 Venda Direta (PDV balcão)
1. Escanear/selecionar produto
2. Adicionar itens ao carrinho
3. Calcular total
4. Aplicar desconto (opcional)
5. Escolher forma de pagamento
6. Finalizar venda

### 7.2 Venda por Mesa
1. Abrir mesa
2. Adicionar consumo
3. Fechar conta (gera venda + libera mesa)

### 7.3 Formas de Pagamento
- Dinheiro
- PIX
- Cartão de Crédito
- Cartão de Débito
- Outros

### 7.4 Fechamento de Caixa
Ao encerrar o turno, o sistema gera:
- Total vendido
- Quantidade de vendas
- Valor médio por venda (ticket médio)
- Produtos mais vendidos
- Horário de abertura
- Horário de fechamento
- Valor inicial em caixa
- Valor final conferido
- Diferenças encontradas

### 7.5 Notificação ao Proprietário
Quando o caixa for fechado, o administrador recebe push com:
- Funcionário responsável
- Data / horário
- Total vendido
- Quantidade de pedidos
- Diferenças encontradas

---

## 8. RELATÓRIOS

### 8.1 Relatório de Vendas
**Filtros:** Hoje, Ontem, Semana, Mês, Período personalizado
**Exibe:** Lista de vendas, totais, ticket médio, ranking por funcionário.

### 8.2 Relatório por Mesa
**Exibe:** Mesa, total consumido, tempo médio ocupada, quantidade de pedidos.

### 8.3 Relatório de Produtos
- Mais vendidos
- Menos vendidos
- Produtos sem movimentação

### 8.4 Relatório de Estoque
- Estoque atual
- Estoque crítico
- Produtos zerados
- Histórico de movimentações

### 8.5 Relatório de Caixa
- Aberturas e fechamentos
- Diferenças
- Totais por turno / operador

---

## 9. AUDITORIA

### 9.1 Eventos registrados
- Login / Logout
- Abertura de mesa
- Fechamento de mesa
- Venda (direta e por mesa)
- Entrada de estoque
- Saída de estoque
- Alteração de produto
- Exclusão de produto
- Criação / edição de usuários
- Abertura / fechamento de caixa
- Tentativas de acesso não autorizado

### 9.2 Campos do log
- Usuário (id + nome)
- Ação
- Data / Hora
- IP
- Dispositivo / User-Agent
- Detalhes adicionais (JSON)

---

## 10. SEGURANÇA

### 10.1 Requisitos gerais
- Senhas criptografadas (hash + salt — bcrypt/argon2)
- Controle por permissões
- Sessões seguras (HttpOnly, SameSite, expiração)
- Backup automático diário
- Histórico permanente de auditoria
- HTTPS obrigatório em produção

### 10.2 Segurança Mobile (App Admin)
- **JWT (Access Token + Refresh Token)**
- **Criptografia de dados em trânsito (TLS) e em repouso**
- **Sessões seguras com expiração curta**
- **Logout remoto** — encerra sessões de dispositivos conectados
- **Registro de dispositivos conectados** — controle de sessões ativas
- Bloqueio após tentativas inválidas
- Possibilidade de revogar tokens de um dispositivo específico

---

## 11. BANCO DE DADOS

### 11.1 Tabelas principais

**usuarios**
`id, nome, login, senha_hash, nivel, ativo, criado_em`

**mesas**
`id, numero, capacidade, status, valor_atual, aberta_em, reservada_para`

**categorias**
`id, nome`

**produtos**
`id, nome, categoria_id, codigo_barras, preco, estoque, estoque_minimo, unidade, ativo, criado_em`

**comandas**
`id, mesa_id, usuario_id, abertura, fechamento, status`

**itens_comanda**
`id, comanda_id, produto_id, quantidade, preco_unitario, subtotal, usuario_id, criado_em`

**vendas**
`id, comanda_id, mesa_id, usuario_id, valor_total, desconto, forma_pagamento, data, tipo`

**itens_venda**
`id, venda_id, produto_id, quantidade, preco_unitario, subtotal`

**movimentacoes**
`id, produto_id, tipo, quantidade, motivo, usuario_id, data_hora, observacao`

**caixas**
`id, usuario_id, abertura, fechamento, valor_inicial, valor_final, total_vendas, quantidade_vendas, observacao`

**auditoria**
`id, usuario_id, usuario_nome, acao, detalhes, data_hora, ip, user_agent`

**dispositivos** *(novo — para app mobile)*
`id, usuario_id, device_id, plataforma, modelo, app_version, ultimo_acesso, ip, refresh_token_hash, ativo`

**sessoes_mobile** *(novo)*
`id, usuario_id, dispositivo_id, access_token_hash, refresh_token_hash, expira_em, criado_em, revogado`

**notificacoes** *(novo)*
`id, usuario_id, tipo, titulo, mensagem, dados_json, lida, criada_em`

**configuracoes** *(novo)*
`id, chave, valor, descricao` — (ex.: valor mínimo para alerta de venda alta, tokens FCM, etc.)

**impressoras** *(novo — impressão)*
`id, nome, tipo, modelo, largura_mm, vias, conexao, endereco, padrao, ativa, criado_em`

**historico_impressoes** *(novo — impressão)*
`id, usuario_id, tipo_documento, referencia_id, mesa_id, impressora_id, reimpressao, data_hora, status, observacao`

---

## 12. VISUAL DO SISTEMA (WEB + MOBILE)

- Dashboard profissional
- Visual premium
- Gráficos elegantes
- Ícones intuitivos
- Layout responsivo
- **Modo claro e escuro** (web e mobile)
- Atualização em tempo real
- Interface simples para funcionários (foco em agilidade no balcão)
- Paleta sóbria com destaque em âmbar/dourado (referência a bar/adega)

---

## 13. DIFERENCIAIS (RESUMO)

- Controle de mesas em tempo real
- Controle de comandas
- Estoque automático
- Leitor de código de barras
- Dashboard completo (web)
- Relatórios avançados
- Auditoria total
- Sistema rápido e intuitivo
- **App mobile premium para o administrador**
- **Notificações push em tempo real**
- **Sincronização instantânea web ↔ mobile**
- **Segurança avançada (JWT + refresh + logout remoto)**
- **Impressão de comandas, pedidos e comprovantes (térmica 80mm / P98)**
- **Reimpressão e histórico de impressões**
- **Impressão opcional em qualquer operação**

---

## 14. APLICATIVO MOBILE — ADMINISTRADOR

### 14.1 Plataformas
- Android
- iOS

### 14.2 Tecnologia sugerida
- **React Native** (compartilhar lógica com front web) **ou Flutter** (UI nativa premium)

### 14.3 Funcionalidades do App Admin

**Login seguro**
- Usuário
- Senha
- Refresh token automático
- Biometria (Face ID / digital) — opcional

**Dashboard Mobile em Tempo Real**
- Faturamento do dia
- Faturamento do mês
- Quantidade de vendas
- Mesas ocupadas / livres / reservadas
- Estoque crítico
- Produtos mais vendidos
- Ticket médio
- Atualização automática via WebSocket

**Monitoramento de Mesas**
- Visualizar todas as mesas
- Status (Livre, Ocupada, Reservada, Em fechamento)
- Tempo de ocupação
- Valor consumido

**Estoque em Tempo Real**
- Estoque atual de cada produto
- Produtos com estoque baixo
- Produtos zerados
- Últimas movimentações

**Relatórios Mobile**
- Diário
- Semanal
- Mensal
- Período personalizado
- Filtros rápidos (categoria, forma de pagamento, operador)

**Notificações Push**
- Caixa fechado
- Estoque crítico
- Produto zerado
- Venda acima de valor configurado
- Grande volume de vendas em curto período
- Tentativa de acesso não autorizado
- Login em novo dispositivo

**Segurança Mobile**
- Visualizar dispositivos conectados
- Revogar acesso de um dispositivo
- Logout remoto global
- Logs de acesso

### 14.4 Dashboard Mobile Premium
- Interface premium com visual elegante
- Ícones modernos (Material Icons / Cupertino)
- Cards informativos
- Gráficos interativos (Chart.js / fl_chart)
- Totalmente responsivo
- **Modo claro e escuro**
- Inspirado em SaaS modernos (Stripe, Linear, Notion)

---

## 15. NOTIFICAÇÕES PUSH

### 15.1 Tecnologia
- **Firebase Cloud Messaging (FCM)** — Android + iOS

### 15.2 Tipos de notificação
- ✅ Caixa fechado
- ✅ Estoque crítico
- ✅ Produto zerado
- ✅ Venda acima de valor configurado (parâmetro em `configuracoes`)
- ✅ Grande movimentação de vendas (parâmetro de frequência)
- ✅ Tentativa de acesso não autorizado

### 15.3 Fluxo
1. Evento ocorre no sistema (ex.: caixa fechado)
2. Backend dispara notificação via FCM
3. App recebe push em tempo real
4. Toque abre tela relevante do app

---

## 16. SINCRONIZAÇÃO EM TEMPO REAL (WEB ↔ MOBILE)

### 16.1 Objetivo
Toda alteração no sistema principal deve refletir imediatamente no aplicativo (e vice-versa, quando aplicável).

**Exemplos:**
- Nova venda
- Nova comanda
- Fechamento de mesa
- Alteração de estoque
- Fechamento de caixa

### 16.2 Tecnologias sugeridas
- **WebSocket** (canal direto Flask-SocketIO)
- **Socket.IO** (cliente JS e cliente mobile)
- **Firebase Realtime Database** (alternativa)
- **Supabase Realtime** (alternativa)

### 16.3 Canais de evento
- `venda:criada`
- `mesa:atualizada`
- `estoque:movimentado`
- `caixa:fechado`
- `alerta:critico`
- `auditoria:login`

### 16.4 Funcionamento
- Backend emite evento no canal ao persistir mudança
- App mobile inscrito recebe push + atualiza UI
- Web revalida dados em cache (ex.: SWR) ou também escuta WS

---

## 17. APIs SUGERIDAS (ENDPOINTS NOVOS PARA MOBILE)

```
POST   /api/mobile/auth/login          -> retorna access + refresh token
POST   /api/mobile/auth/refresh        -> renova access token
POST   /api/mobile/auth/logout         -> revoga refresh
GET    /api/mobile/dashboard           -> indicadores tempo real
GET    /api/mobile/mesas               -> mapa de mesas
GET    /api/mobile/estoque             -> estoque + alertas
GET    /api/mobile/relatorios          -> filtros de período
GET    /api/mobile/notificacoes        -> listagem
POST   /api/mobile/dispositivo/registro -> registra device_id + token FCM
GET    /api/mobile/sessoes             -> dispositivos conectados
POST   /api/mobile/sessoes/<id>/revogar -> logout remoto
WS     /ws                             -> canal de tempo real
```

---

## 18. CRONOGRAMA DE IMPLEMENTAÇÃO (SUGESTÃO)

| Fase | Entrega | Estimativa |
|------|---------|------------|
| 1 | Web completo (MVC + auth + mesas + PDV + estoque + relatórios + auditoria) | ✅ Concluído (MVP web) |
| 2 | WebSocket no backend + canal de tempo real | 1 sprint |
| 3 | Endpoints `/api/mobile/*` com JWT + refresh | 1 sprint |
| 4 | App mobile (auth + dashboard + mesas + estoque) | 2 sprints |
| 5 | Notificações push (FCM) + registro de dispositivos | 1 sprint |
| 6 | Sincronização tempo real app ↔ web + logout remoto | 1 sprint |
| 7 | Polimento visual, modo escuro mobile, gráficos | 1 sprint |
| 8 | Sistema de impressão (ESC/POS, 80mm, P98, reimpressão, histórico) | 1 sprint |

---

## 19. CRITÉRIOS DE ACEITAÇÃO

- Funcionário consegue abrir mesa, lançar consumo e fechar conta sem reabrir tela.
- Estoque é baixado automaticamente em toda venda.
- Alerta visual aparece em ≤ 15s quando produto zera ou fica crítico.
- Relatórios exportáveis (futuro: PDF/Excel).
- App mobile reflete nova venda em ≤ 2s.
- Push de caixa fechado chega ao admin em ≤ 5s.
- Logout remoto invalida sessão no app em ≤ 2s.
- Todas as ações sensíveis ficam registradas em auditoria.
- Impressão de comprovante concluída em ≤ 3s em impressora online.
- Falha de impressora não bloqueia a venda — apenas exibe aviso e segue o fluxo.

---

## 20. SISTEMA DE IMPRESSÃO

### 20.1 Impressoras Compatíveis
- Impressoras térmicas 80mm (padrão)
- Impressora portátil P98 (compacta)
- Demais impressoras térmicas compatíveis com **ESC/POS**

### 20.2 Configuração de Impressora (apenas admin)
- Cadastro de **múltiplas impressoras**
- Definição de **impressora padrão**
- **Tipo de papel** (80mm, 58mm, P98)
- **Largura de impressão**
- **Quantidade de vias** por documento
- **Nome / identificação** da impressora
- **Conexão:** USB, Bluetooth, Rede/IP, WebUSB/WebSerial

### 20.3 Impressão Opcional (regra geral)
Em **todas** as operações de venda e fechamento de conta o sistema exibirá o diálogo:

> **"Imprimir comprovante?"**
> - ✅ Sim
> - ❌ Não

**A impressão nunca é obrigatória.** O usuário decide.

### 20.4 Tipos de Documento

**a) Comanda (abertura de mesa)**
- Número da comanda
- Número da mesa
- Data / Hora
- Funcionário responsável

**b) Pedido (itens lançados na mesa)**
- Mesa
- Produtos solicitados
- Quantidades
- Horário
- Modo: automático (config.) ou manual

**c) Fechamento de Mesa**
- Número da mesa
- Itens consumidos (produto, qtd, valor unitário, subtotal)
- Valor total
- Descontos aplicados
- Forma de pagamento
- Data / Hora
- Funcionário responsável

**d) Venda Direta (PDV balcão)**
- Produtos vendidos
- Quantidades
- Valor unitário
- Valor total
- Descontos
- Forma de pagamento
- Data / Hora

### 20.5 Formatação Inteligente por Modelo

| Modelo | Layout | Observação |
|--------|--------|------------|
| 80mm | Ampliado | Mais informações, melhor aproveitamento de largura |
| P98 | Compacto | Texto otimizado para papel reduzido |
| 58mm | Compacto | Texto reduzido, foco em itens e total |

O sistema detecta o modelo configurado e gera o layout adequado (template ESC/POS).

### 20.6 Reimpressão
- Disponível para **administradores**
- Reimpressão de comandas, pedidos, comprovantes e fechamentos
- Acesso pelo **histórico do sistema** (por venda / comanda / caixa)

### 20.7 Histórico de Impressões
Tabela `historico_impressoes` registra:
- Usuário que solicitou
- Tipo de documento (comanda, pedido, fechamento, venda direta, reimpressão)
- Referência (id da venda/comanda)
- Mesa (quando aplicável)
- Impressora utilizada
- Se foi reimpressão
- Data / Hora
- Status (ok / falha)
- Observação

### 20.8 Indicadores no Dashboard
- Quantidade de impressões do dia
- Reimpressões realizadas
- Impressora em uso (padrão)
- Status atual da impressora (online / offline / erro)

### 20.9 Tratamento de Erros
Caso a impressora esteja offline / falhe:

> **"Impressora indisponível. Deseja continuar sem imprimir?"**
> - 🔁 Tentar novamente
> - ➡️ Continuar (a venda é finalizada normalmente, e a falha é registrada no histórico)

**A falha NUNCA bloqueia a venda.**

### 20.10 Tecnologias Recomendadas
- **ESC/POS** (padrão de comandos)
- **WebUSB** (navegador → USB direto)
- **WebSerial** (navegador → serial)
- **Electron Print Service** (caso haja versão desktop empacotada)
- **Bluetooth** (P98 e similares)
- Biblioteca cliente sugerida: **escpos** / **escpos-usb** / **node-thermal-printer** (no app desktop) ou SDK nativa no mobile

### 20.11 Fluxo Resumido de Impressão
1. Usuário finaliza venda/fecha mesa
2. Sistema pergunta: **"Imprimir comprovante?"**
3. Se **Sim** → seleciona impressora (padrão ou específica) → gera template ESC/POS → envia
4. Se **Não** → segue sem imprimir
5. Em caso de falha → registra no histórico + exibe aviso + permite continuar
6. Reimpressões (admin) → buscam template original + reenviam

---

**FIM DO PRD — Versão 2.1 consolidada**
