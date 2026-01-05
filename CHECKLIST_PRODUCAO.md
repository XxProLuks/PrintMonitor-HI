# 🚀 CHECKLIST PARA PRODUÇÃO

**Guia completo para colocar o projeto em produção**

---

## ⚠️ CRÍTICO - ANTES DE COLOCAR EM PRODUÇÃO

### ✅ **1. Configurar SECRET_KEY**

**OBRIGATÓRIO:** O sistema **FALHARÁ** em produção sem uma SECRET_KEY configurada.

#### Gerar SECRET_KEY:
```bash
python gerar_secret_key.py
```

#### Configurar SECRET_KEY:

**Opção 1: Arquivo `.env` (Recomendado)**
```bash
# Na raiz do projeto, crie .env
SECRET_KEY=sua-chave-gerada-aqui
FLASK_ENV=production
ENVIRONMENT=production
```

**Opção 2: Variável de Ambiente do Sistema**

**Windows (PowerShell):**
```powershell
[System.Environment]::SetEnvironmentVariable('SECRET_KEY', 'sua-chave-aqui', 'Machine')
[System.Environment]::SetEnvironmentVariable('FLASK_ENV', 'production', 'Machine')
```

**Linux/Mac:**
```bash
export SECRET_KEY="sua-chave-aqui"
export FLASK_ENV=production
# Adicionar ao ~/.bashrc ou ~/.profile para permanente
```

**Opção 3: Docker**
```yaml
# docker-compose.yml
environment:
  - SECRET_KEY=${SECRET_KEY}
```

> 📚 **Guia completo:** Veja `GUIA_CONFIGURAR_SECRET_KEY.md`

---

### ✅ **2. Configurar HTTPS/SSL**

**OBRIGATÓRIO:** Em produção, use HTTPS para proteger dados sensíveis.

#### Configurações no `.env`:
```env
SESSION_COOKIE_SECURE=True  # Obrigatório com HTTPS
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
```

#### Opções de HTTPS:

**A) Nginx/Apache como Proxy Reverso (Recomendado)**
```nginx
# Exemplo Nginx
server {
    listen 443 ssl;
    server_name seu-dominio.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:5002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**B) Certificado Let's Encrypt (Gratuito)**
```bash
# Instalar certbot
sudo apt-get install certbot python3-certbot-nginx

# Obter certificado
sudo certbot --nginx -d seu-dominio.com
```

**C) Flask com SSL direto (Não recomendado para produção)**
```python
# Apenas para testes - use proxy reverso em produção
app.run(ssl_context='adhoc')
```

---

### ✅ **3. Desabilitar Debug Mode**

**CRÍTICO:** Debug mode expõe informações sensíveis e permite execução de código.

#### Configurar:
```env
# .env
FLASK_ENV=production
ENVIRONMENT=production
DEBUG=False
```

#### Verificar no código:
```python
# serv/servidor.py já verifica:
debug = os.getenv('DEBUG', 'False').lower() == 'true'
```

---

### ✅ **4. Configurar Servidor WSGI (Não usar Flask dev server)**

**IMPORTANTE:** O servidor de desenvolvimento do Flask (`app.run()`) **NÃO é adequado para produção**.

#### Opção 1: Gunicorn (Linux/Mac) - Recomendado
```bash
# Instalar
pip install gunicorn

# Executar
gunicorn -w 4 -b 0.0.0.0:5002 --timeout 120 serv.servidor:app
```

#### Opção 2: Waitress (Windows/Linux/Mac) - Recomendado para Windows
```bash
# Instalar
pip install waitress

# Executar
waitress-serve --host=0.0.0.0 --port=5002 serv.servidor:app
```

#### Opção 3: uWSGI (Linux)
```bash
# Instalar
pip install uwsgi

# Executar
uwsgi --http :5002 --module serv.servidor:app --processes 4
```

#### Opção 4: Docker (Já configurado)
```bash
docker-compose up -d
```

---

### ✅ **5. Configurar Banco de Dados**

#### Backup do Banco de Dados:
```bash
# Fazer backup antes de produção
cp serv/print_events.db serv/backups/backup_pre_producao.db
```

#### Configurar Volume Persistente (Docker):
```yaml
# docker-compose.yml
volumes:
  - ./serv/print_events.db:/app/serv/print_events.db
  - ./serv/backups:/app/serv/backups
```

#### Configurar Backup Automático:
O sistema já tem backup automático configurado (a cada 24 horas).

---

### ✅ **6. Configurar Firewall**

#### Portas necessárias:
- **5002** (ou porta configurada) - Servidor web
- **80** - HTTP (redirecionar para HTTPS)
- **443** - HTTPS

#### Exemplo (UFW - Linux):
```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

---

### ✅ **7. Configurar Logs**

#### Estrutura de Logs:
```bash
# Criar diretórios
mkdir -p serv/logs
mkdir -p agent/logs
```

#### Configurar Rotação de Logs:
```bash
# Linux - logrotate
/etc/logrotate.d/print-monitor
```

#### Configurar Nível de Log:
```env
# .env
LOG_LEVEL=INFO  # ou WARNING para produção
```

---

### ✅ **8. Configurar Variáveis de Ambiente**

#### Arquivo `.env` completo para produção:
```env
# ============================================================================
# CONFIGURAÇÕES DE PRODUÇÃO
# ============================================================================

# Segurança (OBRIGATÓRIO)
SECRET_KEY=sua-chave-secreta-gerada-com-gerar_secret_key.py
FLASK_ENV=production
ENVIRONMENT=production
DEBUG=False

# Servidor
HOST=0.0.0.0
PORT=5002

# Banco de Dados
DB_NAME=print_events.db

# Sessões (com HTTPS)
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
SESSION_LIFETIME=3600

# Connection Pool
DB_POOL_MAX_CONNECTIONS=10
DB_POOL_TIMEOUT=5.0

# Rate Limiting
RATELIMIT_STORAGE_URL=memory://

# Email (para alertas - opcional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu_email@gmail.com
SMTP_PASSWORD=sua_senha_app
SMTP_USE_TLS=True

# IA (opcional)
OPENAI_API_KEY=sk-sua-chave-aqui
GROQ_API_KEY=gsk_sua-chave-aqui

# Logs
LOG_LEVEL=INFO
```

---

### ✅ **9. Configurar Agente de Monitoramento**

#### Configurar `agent/config.json`:
```json
{
  "server_url": "https://seu-dominio.com/api/print_events",
  "check_interval": 5,
  "methods": ["powershell", "wmi", "eventlog"],
  "printers": ["*"]
}
```

#### Instalar Agente nos Computadores:
```powershell
# Usar script de deploy
.\agent\DEPLOY_REDE_COMPLETO.ps1 -Install -Computers @("PC01", "PC02")
```

> 📚 **Guia completo:** Veja `agent/GUIA_DEPLOY_REDE.md`

---

### ✅ **10. Configurar Usuários e Senhas**

#### Alterar Senha Padrão:
```bash
# Primeiro login: admin / 123
# ALTERAR IMEDIATAMENTE após primeiro acesso
```

#### Criar Usuários:
```bash
python criar_usuario_admin.py
python criar_usuario_ti.py
```

---

### ✅ **11. Configurar Monitoramento e Alertas**

#### Health Check:
O sistema já tem endpoint `/health` configurado.

#### Monitoramento (opcional):
- **Prometheus** - Métricas
- **Grafana** - Dashboards
- **Sentry** - Error tracking

---

### ✅ **12. Configurar Backup e Recuperação**

#### Backup Automático:
Já configurado (a cada 24 horas em `serv/backups/`).

#### Backup Manual:
```bash
# Copiar banco de dados
cp serv/print_events.db serv/backups/backup_manual_$(date +%Y%m%d_%H%M%S).db
```

#### Restaurar Backup:
```bash
# Parar servidor
# Substituir banco
cp serv/backups/backup_YYYYMMDD_HHMMSS.db serv/print_events.db
# Reiniciar servidor
```

---

### ✅ **13. Testar em Ambiente de Staging**

#### Checklist de Testes:
- [ ] Login funciona
- [ ] Dashboard carrega
- [ ] Eventos são recebidos do agente
- [ ] Cálculos estão corretos
- [ ] Relatórios funcionam
- [ ] Exportação funciona
- [ ] Backup automático funciona
- [ ] HTTPS funciona
- [ ] Logs estão sendo gerados

---

### ✅ **14. Configurar Domínio e DNS**

#### Configurar DNS:
```
A     @     192.168.1.100
A     www   192.168.1.100
```

#### Configurar Nginx/Apache:
Ver seção "Configurar HTTPS/SSL" acima.

---

### ✅ **15. Configurar Process Manager (Opcional mas Recomendado)**

#### Systemd (Linux):
```ini
# /etc/systemd/system/print-monitor.service
[Unit]
Description=Print Monitor Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/app/serv
Environment="SECRET_KEY=sua-chave"
Environment="FLASK_ENV=production"
ExecStart=/usr/local/bin/gunicorn -w 4 -b 0.0.0.0:5002 serv.servidor:app
Restart=always

[Install]
WantedBy=multi-user.target
```

#### PM2 (Node.js - funciona com Python):
```bash
npm install -g pm2
pm2 start gunicorn --name print-monitor -- -w 4 -b 0.0.0.0:5002 serv.servidor:app
pm2 save
pm2 startup
```

---

## 📋 CHECKLIST RÁPIDO

### **Antes de Colocar em Produção:**

- [ ] ✅ SECRET_KEY configurada e segura
- [ ] ✅ HTTPS/SSL configurado
- [ ] ✅ DEBUG=False
- [ ] ✅ Servidor WSGI configurado (Gunicorn/Waitress)
- [ ] ✅ Firewall configurado
- [ ] ✅ Logs configurados
- [ ] ✅ Backup automático funcionando
- [ ] ✅ Senha padrão alterada
- [ ] ✅ Variáveis de ambiente configuradas
- [ ] ✅ Agente configurado e testado
- [ ] ✅ Testes em staging realizados
- [ ] ✅ Domínio e DNS configurados
- [ ] ✅ Process manager configurado (opcional)

---

## 🚨 PROBLEMAS COMUNS EM PRODUÇÃO

### **1. Erro: "SECRET_KEY não está definida em produção"**
**Solução:** Configure `SECRET_KEY` em variáveis de ambiente ou `.env`

### **2. Erro: "Connection refused" do agente**
**Solução:** Verifique URL do servidor em `agent/config.json` e firewall

### **3. Erro: "Database is locked"**
**Solução:** Verifique se há múltiplas conexões simultâneas. Connection pooling já está configurado.

### **4. Performance lenta**
**Solução:** 
- Use servidor WSGI (Gunicorn/Waitress)
- Configure múltiplos workers
- Verifique connection pooling

### **5. Cookies não funcionam com HTTPS**
**Solução:** Configure `SESSION_COOKIE_SECURE=True` no `.env`

---

## 📚 DOCUMENTAÇÃO ADICIONAL

- `GUIA_CONFIGURAR_SECRET_KEY.md` - Configuração de SECRET_KEY
- `GUIA_CONFIGURACAO_COMODATOS.md` - Configuração de comodatos
- `CONFIGURACAO_OPENAI.md` - Configuração de IA (OpenAI)
- `CONFIGURAR_GROQ.md` - Configuração de IA (Groq)
- `agent/GUIA_DEPLOY_REDE.md` - Deploy do agente em rede
- `agent/INSTALACAO_AGENTE.md` - Instalação do agente

---

## 🎯 RESUMO - PASSOS ESSENCIAIS

1. **Gerar e configurar SECRET_KEY** ⚠️ CRÍTICO
2. **Configurar HTTPS/SSL** ⚠️ CRÍTICO
3. **Desabilitar DEBUG** ⚠️ CRÍTICO
4. **Usar servidor WSGI** (Gunicorn/Waitress) ⚠️ CRÍTICO
5. **Configurar firewall**
6. **Configurar logs**
7. **Testar em staging**
8. **Configurar backup**
9. **Alterar senha padrão**
10. **Configurar agente**

---

**Última atualização:** 2024-12-04

