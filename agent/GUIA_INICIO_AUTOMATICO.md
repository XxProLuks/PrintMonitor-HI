# 🚀 GUIA DE INÍCIO AUTOMÁTICO DO AGENTE

**Como garantir que o agente inicie automaticamente com o Windows**

---

## ✅ CONFIGURAÇÃO AUTOMÁTICA

O instalador já configura o início automático por padrão. Ao executar:

```powershell
.\instalar_agente.ps1 -ServerURL "http://servidor:5002/api/print_events"
```

A tarefa agendada é criada automaticamente com:
- ✅ Inicia ao iniciar o Windows (mesmo sem login)
- ✅ Inicia ao fazer login de qualquer usuário
- ✅ Executa como SYSTEM (máxima prioridade)
- ✅ Reinicia automaticamente em caso de falha

---

## 🔍 VERIFICAR SE ESTÁ CONFIGURADO

### **Método 1: Script de Verificação (Recomendado)**

```powershell
.\verificar_inicio_automatico.ps1
```

Ou simplesmente:

```batch
.\VERIFICAR_INICIO.bat
```

### **Método 2: PowerShell Manual**

```powershell
# Verificar se a tarefa existe
Get-ScheduledTask -TaskName "PrintMonitorAgent"

# Ver detalhes
Get-ScheduledTask -TaskName "PrintMonitorAgent" | Get-ScheduledTaskInfo

# Ver triggers (quando executa)
Get-ScheduledTask -TaskName "PrintMonitorAgent" | Select-Object -ExpandProperty Triggers
```

---

## ⚙️ CONFIGURAR MANUALMENTE

Se a tarefa não foi criada automaticamente:

### **Opção 1: Usar Script de Instalação**

```powershell
.\instalar_agente.ps1 -ServerURL "http://servidor:5002/api/print_events" -CreateTask
```

### **Opção 2: Criar Manualmente via PowerShell**

```powershell
$taskName = "PrintMonitorAgent"
$installPath = "C:\PrintMonitorAgent"
$pythonPath = "python"  # ou caminho completo

# Remove tarefa existente se houver
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

# Cria ação
$action = New-ScheduledTaskAction `
    -Execute $pythonPath `
    -Argument "$installPath\agente.py" `
    -WorkingDirectory $installPath

# Cria triggers
$triggerStartup = New-ScheduledTaskTrigger -AtStartup
$triggerStartup.Delay = "PT1M"  # Delay de 1 minuto

$triggerLogon = New-ScheduledTaskTrigger -AtLogOn

# Configurações
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

# Principal (executa como SYSTEM)
$principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

# Registra tarefa
Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger @($triggerStartup, $triggerLogon) `
    -Settings $settings `
    -Principal $principal `
    -Description "Agente de Monitoramento de Impressão" `
    -Force
```

---

## 🎯 TRIGGERS CONFIGURADOS

### **1. AtStartup (Ao Iniciar Sistema)**
- ✅ Executa quando o Windows inicia
- ✅ Funciona mesmo sem usuário logado
- ✅ Delay de 1 minuto (aguarda rede inicializar)
- ✅ Executa como SYSTEM

### **2. AtLogOn (Ao Fazer Login)**
- ✅ Executa quando qualquer usuário faz login
- ✅ Garante que o agente rode mesmo se o sistema já estava ligado
- ✅ Executa como usuário logado

---

## 🔧 GERENCIAR A TAREFA

### **Iniciar Manualmente**

```powershell
Start-ScheduledTask -TaskName "PrintMonitorAgent"
```

### **Parar**

```powershell
Stop-ScheduledTask -TaskName "PrintMonitorAgent"
```

### **Habilitar/Desabilitar**

```powershell
# Habilitar
Enable-ScheduledTask -TaskName "PrintMonitorAgent"

# Desabilitar
Disable-ScheduledTask -TaskName "PrintMonitorAgent"
```

### **Remover**

```powershell
Unregister-ScheduledTask -TaskName "PrintMonitorAgent" -Confirm:$false
```

---

## 🔍 VERIFICAR SE ESTÁ RODANDO

### **Verificar Processo**

```powershell
# Ver processos Python relacionados ao agente
Get-Process python* | Where-Object { $_.Path -like "*PrintMonitorAgent*" }

# Ou verificar pelo nome do script
Get-Process python* | Where-Object { $_.CommandLine -like "*agente.py*" }
```

### **Verificar Logs**

```powershell
# Ver últimas linhas do log
Get-Content "C:\PrintMonitorAgent\logs\agent_output.log" -Tail 20

# Ver log do Python
Get-Content "C:\PrintMonitorAgent\print_monitor.log" -Tail 20
```

### **Verificar Status da Tarefa**

```powershell
Get-ScheduledTask -TaskName "PrintMonitorAgent" | Get-ScheduledTaskInfo
```

---

## 🐛 TROUBLESHOOTING

### **Problema: Agente não inicia automaticamente**

**Soluções:**

1. **Verificar se a tarefa existe:**
```powershell
Get-ScheduledTask -TaskName "PrintMonitorAgent"
```

2. **Verificar se está habilitada:**
```powershell
$task = Get-ScheduledTask -TaskName "PrintMonitorAgent"
$task.Enabled  # Deve ser True
```

3. **Verificar triggers:**
```powershell
Get-ScheduledTask -TaskName "PrintMonitorAgent" | Select-Object -ExpandProperty Triggers
```

4. **Verificar permissões:**
   - A tarefa precisa ser criada como Administrador
   - Se criada como usuário, só inicia quando esse usuário faz login

5. **Recriar a tarefa:**
```powershell
.\instalar_agente.ps1 -ServerURL "http://servidor:5002/api/print_events" -Force
```

---

### **Problema: Agente inicia mas para logo depois**

**Soluções:**

1. **Verificar logs:**
```powershell
Get-Content "C:\PrintMonitorAgent\logs\agent_output.log" -Tail 50
```

2. **Verificar se Python está no PATH:**
```powershell
python --version
```

3. **Verificar se o servidor está acessível:**
```powershell
Test-NetConnection -ComputerName SERVIDOR -Port 5002
```

4. **Verificar configuração:**
```powershell
Get-Content "C:\PrintMonitorAgent\config.json"
```

---

### **Problema: Tarefa executa mas não aparece processo**

**Soluções:**

1. **Verificar se está usando caminho absoluto:**
   - Use caminho completo do Python
   - Use caminho completo do agente.py

2. **Verificar script wrapper:**
```powershell
Get-Content "C:\PrintMonitorAgent\run_agent_hidden.bat"
```

3. **Executar manualmente para testar:**
```powershell
cd C:\PrintMonitorAgent
python agente.py
```

---

## 📋 CHECKLIST DE VERIFICAÇÃO

Após instalação, verifique:

- [ ] Tarefa agendada existe: `Get-ScheduledTask -TaskName "PrintMonitorAgent"`
- [ ] Tarefa está habilitada: `$task.Enabled = True`
- [ ] Tem trigger AtStartup configurado
- [ ] Tem trigger AtLogOn configurado
- [ ] Executa como SYSTEM (ou usuário com permissões)
- [ ] Script wrapper existe: `C:\PrintMonitorAgent\run_agent_hidden.bat`
- [ ] Logs estão sendo gerados: `C:\PrintMonitorAgent\logs\agent_output.log`
- [ ] Processo está rodando após reiniciar

---

## 💡 DICAS

1. **Sempre teste após instalação:**
   ```powershell
   .\verificar_inicio_automatico.ps1
   ```

2. **Reinicie o computador** para testar início automático

3. **Verifique logs regularmente** para garantir que está funcionando

4. **Use SYSTEM como principal** para garantir que rode mesmo sem login

5. **Configure delay de 1 minuto** no AtStartup para aguardar rede

---

## 📚 ARQUIVOS RELACIONADOS

- `instalar_agente.ps1` - Script de instalação (cria tarefa automaticamente)
- `verificar_inicio_automatico.ps1` - Script de verificação
- `VERIFICAR_INICIO.bat` - Atalho para verificação
- `run_agent_hidden.bat` - Script wrapper (criado automaticamente)
- `uninstall_agent.ps1` - Remove tarefa agendada

---

**Última atualização:** 2024-12-08


