# 🔐 GUIA: Como Configurar SECRET_KEY

**Data:** 2024  
**Versão:** 1.0.0

---

## 📋 O QUE É SECRET_KEY?

A `SECRET_KEY` é uma chave secreta usada pelo Flask para:
- Assinar cookies de sessão
- Proteger contra CSRF (Cross-Site Request Forgery)
- Criptografar dados sensíveis

**⚠️ IMPORTANTE:** Nunca compartilhe ou commite a SECRET_KEY no código!

---

## 🎯 GERAR UMA SECRET_KEY SEGURA

### **Método 1: Python (Recomendado)**

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**Exemplo de saída:**
```
a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
```

### **Método 2: Python (Alternativo)**

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### **Método 3: OpenSSL (Linux/Mac)**

```bash
openssl rand -hex 32
```

### **Método 4: PowerShell (Windows)**

```powershell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Minimum 0 -Maximum 256 }))
```

---

## 🔧 CONFIGURAR SECRET_KEY

### **1. Windows (PowerShell)**

#### **Opção A: Variável de Ambiente do Sistema (Permanente)**

1. Abra o PowerShell como **Administrador**
2. Execute:

```powershell
# Gerar chave
$secretKey = python -c "import secrets; print(secrets.token_hex(32))"

# Configurar para o usuário atual
[System.Environment]::SetEnvironmentVariable("SECRET_KEY", $secretKey, "User")

# Ou para todo o sistema (requer admin)
[System.Environment]::SetEnvironmentVariable("SECRET_KEY", $secretKey, "Machine")
```

3. **Reinicie o terminal** ou execute:
```powershell
$env:SECRET_KEY = [System.Environment]::GetEnvironmentVariable("SECRET_KEY", "User")
```

#### **Opção B: Variável de Ambiente da Sessão (Temporária)**

```powershell
# Gerar e definir
$env:SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))"
```

⚠️ **Nota:** Esta configuração é perdida ao fechar o terminal.

#### **Opção C: Arquivo .env (Recomendado para Desenvolvimento)**

1. Crie um arquivo `.env` na raiz do projeto (mesmo nível de `serv/`):

```env
SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
FLASK_ENV=development
```

2. O arquivo `.env` será carregado automaticamente pelo `python-dotenv`.

⚠️ **IMPORTANTE:** Adicione `.env` ao `.gitignore` para não commitar a chave!

---

### **2. Linux/Mac (Bash)**

#### **Opção A: Variável de Ambiente do Sistema (Permanente)**

1. Adicione ao arquivo `~/.bashrc` ou `~/.zshrc`:

```bash
# Gerar chave
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
```

2. Ou adicione manualmente:

```bash
export SECRET_KEY="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2"
```

3. Recarregue o arquivo:
```bash
source ~/.bashrc
# ou
source ~/.zshrc
```

#### **Opção B: Variável de Ambiente da Sessão (Temporária)**

```bash
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
```

#### **Opção C: Arquivo .env (Recomendado)**

1. Crie arquivo `.env` na raiz do projeto:

```env
SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
FLASK_ENV=development
```

2. Adicione ao `.gitignore`:
```
.env
```

---

### **3. Produção (Servidor)**

#### **Opção A: Variáveis de Ambiente do Sistema**

**Linux (systemd):**

1. Crie arquivo `/etc/environment` ou use o arquivo de serviço:

```ini
[Service]
Environment="SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2"
Environment="FLASK_ENV=production"
```

**Windows (Serviço):**

Configure via interface do Windows ou PowerShell:

```powershell
[System.Environment]::SetEnvironmentVariable("SECRET_KEY", "sua-chave-aqui", "Machine")
```

#### **Opção B: Docker**

No `docker-compose.yml`:

```yaml
services:
  servidor:
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - FLASK_ENV=production
```

E defina no `.env` do Docker ou via `docker run`:

```bash
docker run -e SECRET_KEY="sua-chave-aqui" ...
```

#### **Opção C: Serviços de Cloud (AWS, Azure, GCP)**

**AWS (Elastic Beanstalk):**
- Configure via Console → Configuration → Environment Properties

**Azure (App Service):**
- Configure via Portal → Configuration → Application Settings

**GCP (Cloud Run):**
- Configure via `gcloud run deploy --set-env-vars SECRET_KEY=...`

---

## ✅ VERIFICAR SE ESTÁ CONFIGURADA

### **Windows (PowerShell)**

```powershell
echo $env:SECRET_KEY
```

### **Linux/Mac (Bash)**

```bash
echo $SECRET_KEY
```

### **Python**

```python
import os
secret_key = os.getenv('SECRET_KEY')
if secret_key:
    print(f"✅ SECRET_KEY configurada (tamanho: {len(secret_key)})")
else:
    print("❌ SECRET_KEY não configurada")
```

---

## 🚀 TESTAR A CONFIGURAÇÃO

### **1. Iniciar o Servidor**

```bash
cd serv
python servidor.py
```

### **2. Verificar os Logs**

**Se configurada corretamente:**
```
✅ Servidor iniciado sem avisos sobre SECRET_KEY
```

**Se não configurada (desenvolvimento):**
```
⚠️  SECRET_KEY não definida - usando chave temporária gerada.
   ⚠️  Esta chave será diferente a cada reinício em desenvolvimento.
   💡 Para produção, defina SECRET_KEY em variáveis de ambiente.
```

**Se não configurada (produção):**
```
❌ ERRO CRÍTICO: SECRET_KEY não está definida em produção!
   Defina a variável de ambiente SECRET_KEY antes de iniciar o servidor.
```

---

## 📝 EXEMPLO PRÁTICO COMPLETO

### **Desenvolvimento Local (Windows)**

1. **Gerar chave:**
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

2. **Criar arquivo `.env` na raiz do projeto:**
```env
SECRET_KEY=SUA_CHAVE_GERADA_AQUI
FLASK_ENV=development
DB_NAME=print_events.db
```

3. **Verificar `.gitignore`:**
```
.env
*.env
```

4. **Iniciar servidor:**
```powershell
cd serv
python servidor.py
```

### **Produção (Linux com systemd)**

1. **Gerar chave:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

2. **Criar arquivo de serviço `/etc/systemd/system/print-monitor.service`:**
```ini
[Unit]
Description=Print Monitor Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/print-monitor/serv
Environment="SECRET_KEY=SUA_CHAVE_GERADA_AQUI"
Environment="FLASK_ENV=production"
ExecStart=/usr/bin/python3 /opt/print-monitor/serv/servidor.py
Restart=always

[Install]
WantedBy=multi-user.target
```

3. **Recarregar e iniciar:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable print-monitor
sudo systemctl start print-monitor
```

---

## ⚠️ BOAS PRÁTICAS

### **✅ FAZER:**

1. ✅ **Gerar chave única** para cada ambiente (dev, staging, prod)
2. ✅ **Usar arquivo `.env`** em desenvolvimento
3. ✅ **Usar variáveis de ambiente** em produção
4. ✅ **Adicionar `.env` ao `.gitignore`**
5. ✅ **Rotacionar chaves** periodicamente em produção
6. ✅ **Armazenar chaves** em gerenciador de secrets (AWS Secrets Manager, Azure Key Vault, etc.)

### **❌ NÃO FAZER:**

1. ❌ **Nunca commitar** SECRET_KEY no código
2. ❌ **Nunca usar** a mesma chave em dev e prod
3. ❌ **Nunca compartilhar** chaves via email/chat
4. ❌ **Nunca usar** chaves simples como "123" ou "secret"
5. ❌ **Nunca expor** chaves em logs ou mensagens de erro

---

## 🔍 TROUBLESHOOTING

### **Problema: "SECRET_KEY não está definida em produção"**

**Solução:**
1. Verifique se a variável está definida: `echo $SECRET_KEY`
2. Verifique se `FLASK_ENV=production` está configurado
3. Reinicie o servidor após configurar

### **Problema: "Chave temporária diferente a cada reinício"**

**Solução:**
- Isso é esperado em desenvolvimento
- Configure `SECRET_KEY` no `.env` para manter consistência

### **Problema: "Sessões não persistem"**

**Solução:**
- Verifique se a SECRET_KEY está configurada corretamente
- Verifique se não está mudando entre reinícios (em produção)

---

## 📚 REFERÊNCIAS

- [Flask - Configuration](https://flask.palletsprojects.com/en/2.3.x/config/)
- [Python secrets module](https://docs.python.org/3/library/secrets.html)
- [python-dotenv](https://pypi.org/project/python-dotenv/)

---

## ✅ CHECKLIST

- [ ] Gerar SECRET_KEY segura
- [ ] Configurar variável de ambiente ou arquivo `.env`
- [ ] Adicionar `.env` ao `.gitignore`
- [ ] Verificar se está configurada (`echo $SECRET_KEY`)
- [ ] Testar iniciando o servidor
- [ ] Verificar logs para confirmar

---

**Data:** 2024  
**Versão:** 1.0.0

