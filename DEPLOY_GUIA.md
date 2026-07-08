# GUIA DE DEPLOY - JAM'S SISTEMA DE GESTÃO
## Deploy no Render.com (Plano Grátis)

---

## PRÉ-REQUISITOS

- Conta no GitHub (gratuita)
- Conta no Render (gratuita): https://render.com
- Git instalado no computador

---

## PASSO 1: SUBIR PROJETO NO GITHUB

### 1.1 Criar repositório no GitHub
1. Acesse https://github.com
2. Clique em **"+"** → **"New repository"**
3. Nome: `jams-bar-sistema`
4. **NÃO** marque "Add a README file" (já temos arquivos)
5. Clique em **"Create repository"**

### 1.2 Enviar projeto do seu computador
Abra o PowerShell na pasta do projeto e execute:

```powershell
cd "E:\SISTEMA DE GESTÃO PARA BAR, ADEGA E MESAS"

git init
git add .
git commit -m "Deploy inicial - Sistema JAM's"
git branch -M main
git remote add origin https://github.com/SEU-USERNAME/jams-bar-sistema.git
git push -u origin main
```

**IMPORTANTE:** Substitua `SEU-USERNAME` pelo seu usuário do GitHub.

---

## PASSO 2: CRIAR CONTA NO RENDER

1. Acesse https://render.com
2. Clique em **"Get Started for Free"**
3. Faça login com sua conta **Google** ou **GitHub**
4. Autorize o acesso ao GitHub

---

## PASSO 3: CRIAR SERVIÇO NO RENDER

1. No painel do Render, clique em **"New +"**
2. Selecione **"Web Service"**
3. Conecte sua conta GitHub se ainda não conectou
4. Procure o repositório `jams-bar-sistema`
5. Clique em **"Connect"**

---

## PASSO 4: CONFIGURAR O SERVIÇO

Preencha os campos assim:

| Campo | Valor |
|-------|-------|
| **Name** | `jams-bar-sistema` |
| **Region** | `Oregon (US West)` ou `Frankfurt (EU)` |
| **Branch** | `main` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app` |
| **Plan** | `Free` |

---

## PASSO 5: ADICIONAR VARIÁVEL DE AMBIENTE

1. Role para baixo até **"Environment Variables"**
2. Clique em **"Add Environment Variable"**
3. Adicione:

| Key | Value |
|-----|-------|
| `SECRET_KEY` | `jams-bar-secret-2026-producao` |
| `FLASK_DEBUG` | `0` |

4. Clique em **"Create Web Service"**

---

## PASSO 6: AGUARDAR DEPLOY

1. O Render vai baixar seu código e instalar dependências
2. Isso leva **2-5 minutos** na primeira vez
3. Você verá os logs rolando
4. Quando aparecer **"Your service is live"**, pronto!

---

## PASSO 7: ACESSAR O SISTEMA

O Render vai gerar uma URL como:
```
https://jams-bar-sistema.onrender.com
```

Acesse essa URL e faça login:
- **Admin:** `admin` / `Admin@2026#Jam's`
- **Funcionário:** `funcionario` / `Func@2026#Sistema`

---

## PROBLEMAS COMUNS

### "Application failed to respond"
- Verifique se o `Procfile` está correto
- Verifique os logs no painel do Render

### "Database is locked"
- O Render recria o banco a cada deploy (plano grátis)
- Para banco persistente, use o plano pago com disco persistente

### "SECRET_KEY not defined"
- Verifique se a variável de ambiente foi criada corretamente

---

## ATUALIZAR O SISTEMA

Para atualizar depois:

```powershell
git add .
git commit -m "Atualização do sistema"
git push
```

O Render vai fazer deploy automático!

---

## IMPORTANTE - LIMITAÇÕES DO PLANO GRÁTIS

1. **Banco de dados:** O SQLite é recriado a cada deploy
2. **Suspende após 15 min sem acesso:** Volta automaticamente quando alguém acessa
3. **512 MB de RAM:** Suficiente para o sistema
4. **100 GB de transferência:** Suficiente para uso normal

---

## URL FINAL DO SISTEMA

Depois de tudo pronto, sua URL será:
```
https://jams-bar-sistema.onrender.com
```

Guarde essa URL! É ela que você vai acessar de qualquer lugar.

---

**Dúvidas?** Me manda print que eu ajudo!
