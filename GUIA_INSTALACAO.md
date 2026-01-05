# 📦 GUIA COMPLETO DE INSTALAÇÃO

**Sistema de Monitoramento de Impressão**

Este guia explica como instalar tanto o **Servidor** quanto o **Agente** do sistema.

---

## 🎯 ÍNDICE

1. [Instalação do Servidor](#instalação-do-servidor)
2. [Instalação do Agente](#instalação-do-agente)
3. [Verificação](#verificação)
4. [Troubleshooting](#troubleshooting)

---

## 🖥️ INSTALAÇÃO DO SERVIDOR

### **Método 1: Script PowerShell (Windows - RECOMENDADO)**

```powershell
# Como Administrador
cd serv
.\instalar_servidor.ps1
```

**Parâmetros opcionais:**
```powershell
# Especificar porta
.\instalar_servidor.ps1 -Port 5002

# Configurar firewall automaticamente
.\instalar_servidor.ps1 -ConfigureFirewall

# Criar serviço Windows
.\instalar_servidor.ps1 -InstallService

# Pular instalação de dependências
.\instalar_servidor.ps1 -SkipDependencies
```

### **Método 2: Script Python (Multiplataforma)**

```bash
# Windows
cd serv
python instalar_servidor.py

# Linux/Mac
cd serv
python3 instalar_servidor.py
```

### **Método 3: Instalação Manual**

1. **Instalar Python 3.8+**
   - Download: https://www.python.org/downloads/
   - Marcar "Add Python to PATH"

2. **Instalar dependências:**
```bash
pip install -r requirements.txt
```

3. **Inicializar banco de dados:**
```python
python servidor.py
# Na primeira execução, o banco é criado automaticamente
```

4. **Configurar firewall (Windows):**
```powershell
New-NetFirewallRule -DisplayName "PrintMonitor Server" `
    -Direction Inbound -Protocol TCP -LocalPort 5002 -Action Allow
```

---

## 📱 INSTALAÇÃO DO AGENTE

### **Método 1: Script PowerShell (Windows - RECOMENDADO)**

```powershell
# Como Administrador
cd agent
.\instalar_agente.ps1 -ServerURL "http://192.168.1.27:5002/api/print_events"
```

**Parâmetros opcionais:**
```powershell
# Especificar diretório de instalação
.\instalar_agente.ps1 -InstallPath "C:\PrintMonitorAgent" -ServerURL "http://servidor:5002/api/print_events"

# Não criar tarefa agendada
.\instalar_agente.ps1 -ServerURL "http://servidor:5002/api/print_events" -CreateTask:$false

# Forçar reinstalação
.\instalar_agente.ps1 -ServerURL "http://servidor:5002/api/print_events" -Force
```

### **Método 2: Script Python (Multiplataforma)**

```bash
# Windows
cd agent
python instalar_agente.py --server-url "http://192.168.1.27:5002/api/print_events"

# Linux/Mac
cd agent
python3 instalar_agente.py --server-url "http://servidor:5002/api/print_events"
```

**Parâmetros opcionais:**
```bash
# Especificar diretório de instalação
python instalar_agente.py --install-path "C:\PrintMonitorAgent" --server-url "http://servidor:5002/api/print_events"

# Pular dependências
python instalar_agente.py --skip-dependencies --server-url "http://servidor:5002/api/print_events"

# Não criar tarefa agendada
python instalar_agente.py --no-task --server-url "http://servidor:5002/api/print_events"
```

### **Método 3: Instalação Manual**

1. **Instalar Python 3.8+**

2. **Copiar arquivos:**
```bash
# Criar diretório
mkdir C:\PrintMonitorAgent
cd C:\PrintMonitorAgent

# Copiar arquivos do agente
copy agent\agente.py .
copy agent\requirements.txt .
copy agent\config.json.example config.json
```

3. **Editar config.json:**
```json
{
    "server_url": "http://192.168.1.27:5002/api/print_events",
    "check_interval": 5,
    "retry_interval": 30
}
```

4. **Instalar dependências:**
```bash
pip install -r requirements.txt
```

5. **Criar Tarefa Agendada (Windows):**
```powershell
$action = New-ScheduledTaskAction -Execute "python" -Argument "C:\PrintMonitorAgent\agente.py"
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName "PrintMonitorAgent" -Action $action -Trigger $trigger
```

---

## ✅ VERIFICAÇÃO

### **Verificar Servidor:**

1. **Iniciar servidor:**
```bash
cd serv
python servidor.py
```

2. **Acessar no navegador:**
```
http://localhost:5002
```

3. **Login padrão:**
   - Usuário: `admin`
   - Senha: (verifique o console na primeira execução)

### **Verificar Agente:**

1. **Testar manualmente:**
```bash
cd C:\PrintMonitorAgent
python agente.py
```

2. **Verificar logs:**
```bash
# Windows
type C:\PrintMonitorAgent\logs\print_monitor.log

# Linux/Mac
cat ~/PrintMonitorAgent/logs/print_monitor.log
```

3. **Verificar tarefa agendada (Windows):**
```powershell
Get-ScheduledTask -TaskName PrintMonitorAgent
```

4. **Verificar se está enviando eventos:**
   - Acesse o dashboard do servidor
   - Verifique se aparecem eventos de impressão

---

## 🔧 TROUBLESHOOTING

### **Problema: Python não encontrado**

**Solução:**
- Instale Python 3.8+ de https://www.python.org/downloads/
- Marque "Add Python to PATH" durante instalação
- Reinicie o terminal/PowerShell

### **Problema: Erro ao instalar dependências**

**Solução:**
```bash
# Atualizar pip
python -m pip install --upgrade pip

# Instalar manualmente
pip install Flask pandas openpyxl python-dotenv werkzeug
```

### **Problema: Servidor não inicia**

**Solução:**
- Verifique se a porta 5002 está livre
- Verifique se o firewall permite conexões
- Verifique os logs em `serv/logs/`

### **Problema: Agente não conecta ao servidor**

**Solução:**
- Verifique a URL do servidor em `config.json`
- Verifique se o servidor está rodando
- Verifique firewall/rede
- Verifique logs do agente

### **Problema: Tarefa agendada não funciona**

**Solução:**
```powershell
# Verificar tarefa
Get-ScheduledTask -TaskName PrintMonitorAgent

# Verificar histórico
Get-WinEvent -LogName Microsoft-Windows-TaskScheduler/Operational | Where-Object {$_.Message -like "*PrintMonitorAgent*"}

# Recriar tarefa
.\instalar_agente.ps1 -ServerURL "http://servidor:5002/api/print_events" -Force
```

---

## 📚 PRÓXIMOS PASSOS

Após instalação:

1. **Servidor:**
   - Configure SECRET_KEY em variáveis de ambiente
   - Configure backup automático
   - Configure SSL/HTTPS (produção)

2. **Agente:**
   - Verifique se está enviando eventos
   - Configure monitoramento
   - Configure alertas

---

## 💡 DICAS

- **Sempre teste primeiro** em ambiente de desenvolvimento
- **Use -Force** apenas quando necessário (reinstalação)
- **Mantenha backups** do banco de dados
- **Documente configurações** personalizadas
- **Monitore logs** regularmente

---

**Para mais informações:**
- `serv/instalar_servidor.ps1` - Instalador do servidor (PowerShell)
- `serv/instalar_servidor.py` - Instalador do servidor (Python)
- `agent/instalar_agente.ps1` - Instalador do agente (PowerShell)
- `agent/instalar_agente.py` - Instalador do agente (Python)


