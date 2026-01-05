# 🚀 GUIA DE DEPLOY RÁPIDO

**Deploy do Print Monitor em produção em 5 minutos**

---

## ⚡ DEPLOY AUTOMATIZADO

### **Windows (PowerShell como Administrador):**

```powershell
.\deploy_production.ps1
```

### **Linux/Mac:**

```bash
chmod +x deploy_production.sh
./deploy_production.sh
```

---

## 📋 DEPLOY MANUAL (Passo a Passo)

### **1. Gerar SECRET_KEY**

```bash
python gerar_secret_key.py
```

### **2. Criar arquivo .env**

```bash
# Copiar template
cp .env.production .env

# Editar .env e adicionar a SECRET_KEY gerada
```

### **3. Instalar dependências**

```bash
# Criar ambiente virtual (opcional mas recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt
pip install waitress     # Windows
pip install gunicorn    # Linux/Mac
```

### **4. Iniciar servidor**

#### **Windows:**
```bash
# Opção 1: Script batch
start_production_waitress.bat

# Opção 2: Python direto
python start_production_waitress.py
```

#### **Linux/Mac:**
```bash
# Opção 1: Script bash
chmod +x start_production_gunicorn.sh
./start_production_gunicorn.sh

# Opção 2: Gunicorn direto
cd serv
gunicorn -w 4 -b 0.0.0.0:5002 --timeout 120 servidor:app
```

---

## 🔧 CONFIGURAÇÃO COM SYSTEMD (Linux)

### **1. Copiar arquivo de serviço:**

```bash
sudo cp print-monitor.service /etc/systemd/system/
```

### **2. Editar caminhos no arquivo de serviço:**

Edite `/etc/systemd/system/print-monitor.service` e ajuste:
- `WorkingDirectory=/app/serv` → seu caminho
- `EnvironmentFile=/app/.env` → seu caminho do .env
- `ExecStart=/usr/local/bin/gunicorn` → caminho do gunicorn

### **3. Criar diretório de logs:**

```bash
sudo mkdir -p /var/log/print-monitor
sudo chown www-data:www-data /var/log/print-monitor
```

### **4. Ativar e iniciar serviço:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable print-monitor
sudo systemctl start print-monitor
```

### **5. Verificar status:**

```bash
sudo systemctl status print-monitor
sudo journalctl -u print-monitor -f  # Ver logs
```

---

## 🔒 CONFIGURAR HTTPS (Nginx)

### **1. Instalar Nginx:**

```bash
sudo apt-get update
sudo apt-get install nginx
```

### **2. Configurar site:**

Crie `/etc/nginx/sites-available/print-monitor`:

```nginx
server {
    listen 80;
    server_name seu-dominio.com;
    
    # Redirecionar HTTP para HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name seu-dominio.com;
    
    ssl_certificate /etc/letsencrypt/live/seu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/seu-dominio.com/privkey.pem;
    
    location / {
        proxy_pass http://127.0.0.1:5002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

### **3. Obter certificado SSL (Let's Encrypt):**

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d seu-dominio.com
```

### **4. Ativar site e reiniciar Nginx:**

```bash
sudo ln -s /etc/nginx/sites-available/print-monitor /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🔥 CONFIGURAR FIREWALL

### **Linux (UFW):**

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### **Windows (PowerShell como Administrador):**

```powershell
New-NetFirewallRule -DisplayName "Print Monitor" -Direction Inbound -LocalPort 5002 -Protocol TCP -Action Allow
```

---

## ✅ VERIFICAÇÃO PÓS-DEPLOY

### **1. Verificar se servidor está rodando:**

```bash
# Linux
sudo systemctl status print-monitor

# Windows
Get-Process python | Where-Object {$_.Path -like "*print*"}
```

### **2. Testar acesso:**

```bash
curl http://localhost:5002/health
```

### **3. Verificar logs:**

```bash
# Linux
sudo journalctl -u print-monitor -f

# Windows
Get-Content serv\servidor.log -Tail 50 -Wait
```

---

## 🐛 TROUBLESHOOTING

### **Erro: "SECRET_KEY não está definida"**

```bash
# Verificar .env
cat .env | grep SECRET_KEY

# Se não existir, gerar e adicionar
python gerar_secret_key.py
# Adicionar ao .env
```

### **Erro: "Port already in use"**

```bash
# Linux - Verificar processo
sudo lsof -i :5002

# Windows
netstat -ano | findstr :5002

# Matar processo
# Linux: sudo kill -9 <PID>
# Windows: taskkill /PID <PID> /F
```

### **Erro: "Permission denied"**

```bash
# Linux - Dar permissões
sudo chown -R www-data:www-data /app
sudo chmod +x start_production_gunicorn.sh
```

---

## 📚 DOCUMENTAÇÃO COMPLETA

Para mais detalhes, consulte:
- `CHECKLIST_PRODUCAO.md` - Checklist completo de produção
- `GUIA_CONFIGURAR_SECRET_KEY.md` - Configuração de SECRET_KEY
- `agent/GUIA_DEPLOY_REDE.md` - Deploy do agente

---

**Última atualização:** 2024-12-04

