# Ativação do importador Datacaixa no PythonAnywhere

Esta versão aceita backups Firebird 5 do programa antigo nos formatos `.fbk`
e `.FDB`. O runtime Firebird não é versionado no GitHub; ele deve ser instalado
uma vez dentro da conta do PythonAnywhere.

## Atualização

No console Bash do PythonAnywhere:

```bash
cd ~/jams-bar-sistema
git pull --ff-only origin main
pip install -r requirements.txt
python scripts/install_firebird_runtime.py
```

Antes de `pip`, ative o ambiente virtual configurado na aba **Web**, caso a
aplicação use um. Se não usar, execute o `pip` da mesma versão Python mostrada
nessa aba, com `--user`.

Se o download direto for bloqueado, envie para a pasta do projeto o pacote
oficial `Firebird-5.0.4.1812-0-linux-x64.tar.gz` e execute:

```bash
python scripts/install_firebird_runtime.py --archive Firebird-5.0.4.1812-0-linux-x64.tar.gz
```

O instalador também confere a assinatura SHA-256 nessa modalidade.

Depois, recarregue a aplicação na aba **Web**. Abra
`/manutencao/backup` e confirme a mensagem **Conversor Datacaixa pronto**.

## Homologação obrigatória

1. Envie primeiro uma cópia do `.fbk` ou `.FDB`.
2. Aguarde a conversão terminar; o pedido pode levar alguns minutos.
3. Confirme no retorno as quantidades de produtos, clientes e vendas.
4. Confira Produtos, Estoque, Clientes/Fiado e Relatórios.
5. No histórico devem existir dois ZIPs: `convertido_datacaixa_...` e
   `pre_restauracao_...`.

O segundo ZIP é a cópia automática do sistema imediatamente antes da troca.
Se a validação do banco convertido falhar, a importação é cancelada; se a
troca falhar, o sistema tenta recuperar automaticamente essa cópia.

## Observação de espaço

O runtime privado ocupa aproximadamente 67 MB depois de instalado. Confira a
quota de disco da conta antes da primeira importação, pois o `.fbk`, o banco
temporário e os dois ZIPs de segurança coexistem durante o processo.
