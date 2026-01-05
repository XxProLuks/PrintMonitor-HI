# 🚀 GUIA COMPLETO DE DEPLOY DO AGENTE NA REDE

**Data:** 2024  
**Versão:** 2.0.0

---

## 📋 ÍNDICE

1. [Visão Geral](#visão-geral)
2. [Requisitos](#requisitos)
3. [Métodos de Instalação](#métodos-de-instalação)
4. [Instalação em Massa](#instalação-em-massa)
5. [Verificação e Monitoramento](#verificação-e-monitoramento)
6. [Troubleshooting](#troubleshooting)

---

## 🎯 VISÃO GERAL

Este guia explica como instalar o agente de monitoramento de impressão em múltiplos computadores da rede de forma automatizada.

### **Opções Disponíveis:**

1. ✅ **Instalação Individual** - Um computador por vez
2. ✅ **Instalação em Massa** - Múltiplos computadores simultaneamente
3. ✅ **Descoberta Automática** - Encontra computadores na rede automaticamente
4. ✅ **Via GPO** - Instalação via Group Policy (Active Directory)
5. ✅ **Instalador MSI** - Instalação via Windows Installer

---

## 📋 REQUISITOS

### **No Computador de Controle (onde executa o deploy):**

- ✅ Windows 10/11 ou Windows Server
- ✅ PowerShell 5.1 ou superior
- ✅ Permissões de Administrador de Domínio (para instalação remota)
- ✅ Acesso à rede (compartilhamentos administrativos habilitados)
- ✅ PowerShell Remoting habilitado nos computadores remotos

### **Nos Computadores Alvo:**

- ✅ Windows 7 ou superior
- ✅ Python 3.6+ OU executável compilado (.exe)
- ✅ Conectividade de rede com o servidor
- ✅ Event Log 307 habilitado (pode ser habilitado automaticamente)

---

## 🚀 MÉTODOS DE INSTALAÇÃO

### **MÉTODO 1: Script PowerShell Avançado (RECOMENDADO)**

O script `DEPLOY_REDE_COMPLETO.ps1` oferece a solução mais completa:

#### **Instalação em Computadores Específicos:**

```powershell
# Como Administrador
cd C:\caminho\para\agent

# Instalar em computadores específicos
.\DEPLOY_REDE_COMPLETO.ps1 -Install -Computers @("PC01", "PC02", "PC03") -ServerURL "http://192.168.1.27:5002/api/print_events"
```

#### **Instalação via Arquivo de Lista:**

```powershell
# Criar arquivo computadores.txt:
# PC01
# PC02
# PC03
# # Comentários são ignorados

# Instalar
.\DEPLOY_REDE_COMPLETO.ps1 -Install -ComputerListFile "computadores.txt" -ServerURL "http://192.168.1.27:5002/api/print_events"
```

#### **Descoberta Automática e Instalação:**

```powershell
# Descobre computadores automaticamente e instala
.\DEPLOY_REDE_COMPLETO.ps1 -Install -Discover -ServerURL "http://192.168.1.27:5002/api/print_events"
```

#### **Parâmetros Disponíveis:**

| Parâmetro | Descrição | Exemplo |
|-----------|-----------|---------|
| `-Install` | Instala o agente | `-Install` |
| `-Uninstall` | Desinstala o agente | `-Uninstall` |
| `-Status` | Verifica status | `-Status` |
| `-Update` | Atualiza instalação existente | `-Update` |
| `-Computers` | Lista de computadores | `-Computers @("PC01", "PC02")` |
| `-ComputerListFile` | Arquivo com lista | `-ComputerListFile "lista.txt"` |
| `-Discover` | Descobre computadores automaticamente | `-Discover` |
| `-ServerURL` | URL do servidor | `-ServerURL "http://192.168.1.27:5002/api/print_events"` |
| `-Domain` | Domínio do usuário | `-Domain "MEUDOMINIO"` |
| `-Username` | Usuário administrativo | `-Username "admin"` |
| `-EnableEventLog` | Habilita Event Log 307 automaticamente | `-EnableEventLog` |
| `-Force` | Força reinstalação | `-Force` |

---

### **MÉTODO 2: Interface Gráfica**

Para usuários não técnicos, use a interface gráfica:

```cmd
# Duplo clique em:
instalar_agente.bat
```

**Funcionalidades:**
- ✅ Descoberta automática de computadores
- ✅ Seleção visual de computadores
- ✅ Configuração de credenciais
- ✅ Instalação em massa
- ✅ Verificação de status

---

### **MÉTODO 3: Via Group Policy (GPO)**

Para instalação em toda a organização via Active Directory:

#### **Passo 1: Preparar Arquivos**

1. Copie a pasta `agent` para um compartilhamento de rede:
   ```
   \\servidor\deploy\PrintMonitorAgent\
   ```

2. Crie um script de instalação GPO:
   ```powershell
   # install_via_gpo.ps1
   $agentPath = "\\servidor\deploy\PrintMonitorAgent"
   $localPath = "C:\PrintMonitorAgent"
   
   # Copia arquivos
   Copy-Item "$agentPath\*" -Destination $localPath -Recurse -Force
   
   # Executa instalação
   & "$localPath\install_agent.ps1" -Force
   ```

#### **Passo 2: Configurar GPO**

1. Abra **Group Policy Management**
2. Crie uma nova GPO ou edite existente
3. Navegue até: **Computer Configuration > Policies > Windows Settings > Scripts > Startup**
4. Adicione o script `install_via_gpo.ps1`
5. Configure para executar como **SYSTEM**

#### **Passo 3: Aplicar GPO**

1. Vincule a GPO à OU desejada
2. Aguarde a próxima reinicialização dos computadores
3. Verifique a instalação

**Documentação completa:** Veja `CONFIGURAR_VIA_GPO.md`

---

### **MÉTODO 4: Instalador MSI (Windows Installer)**

Para distribuição via SCCM, Intune ou instalação manual:

#### **Criar Instalador MSI:**

```powershell
# Requer WiX Toolset instalado
# Compila o agente em .exe primeiro
.\build_exe.bat

# Cria MSI usando WiX
# (requer arquivo .wxs configurado)
```

**Vantagens:**
- ✅ Instalação silenciosa
- ✅ Integração com SCCM/Intune
- ✅ Desinstalação limpa
- ✅ Atualizações automáticas

---

## 📦 INSTALAÇÃO EM MASSA

### **Cenário 1: Instalação em Lista de Computadores**

```powershell
# 1. Crie arquivo computadores.txt
@"
PC01
PC02
PC03
PC04
"@ | Out-File -FilePath "computadores.txt" -Encoding UTF8

# 2. Execute instalação
.\DEPLOY_REDE_COMPLETO.ps1 `
    -Install `
    -ComputerListFile "computadores.txt" `
    -ServerURL "http://192.168.1.27:5002/api/print_events" `
    -Domain "MEUDOMINIO" `
    -EnableEventLog
```

### **Cenário 2: Instalação em Toda a OU do AD**

```powershell
# 1. Descobre computadores da OU
$computers = Get-ADComputer -Filter * -SearchBase "OU=Computadores,DC=dominio,DC=local" | Select-Object -ExpandProperty Name

# 2. Instala em todos
.\DEPLOY_REDE_COMPLETO.ps1 `
    -Install `
    -Computers $computers `
    -ServerURL "http://192.168.1.27:5002/api/print_events" `
    -EnableEventLog
```

### **Cenário 3: Instalação com Descoberta Automática**

```powershell
# Descobre e instala automaticamente
.\DEPLOY_REDE_COMPLETO.ps1 `
    -Install `
    -Discover `
    -ServerURL "http://192.168.1.27:5002/api/print_events" `
    -EnableEventLog `
    -Force
```

---

## ✅ VERIFICAÇÃO E MONITORAMENTO

### **Verificar Status de Múltiplos Computadores:**

```powershell
.\DEPLOY_REDE_COMPLETO.ps1 -Status -Computers @("PC01", "PC02", "PC03")
```

### **Verificar Status via Arquivo:**

```powershell
.\DEPLOY_REDE_COMPLETO.ps1 -Status -ComputerListFile "computadores.txt"
```

### **Verificar Status de Todos (Descoberta):**

```powershell
.\DEPLOY_REDE_COMPLETO.ps1 -Status -Discover
```

### **Verificação Manual (PowerShell Remoto):**

```powershell
$cred = Get-Credential
Invoke-Command -ComputerName "PC01" -Credential $cred -ScriptBlock {
    Get-ScheduledTask -TaskName "PrintMonitorAgent" | Get-ScheduledTaskInfo
}
```

---

## 🔄 ATUALIZAÇÃO EM MASSA

### **Atualizar Agente em Múltiplos Computadores:**

```powershell
.\DEPLOY_REDE_COMPLETO.ps1 `
    -Update `
    -ComputerListFile "computadores.txt" `
    -ServerURL "http://192.168.1.27:5002/api/print_events"
```

**O que faz:**
1. Desinstala versão antiga
2. Copia novos arquivos
3. Reinstala com nova versão
4. Mantém configurações existentes

---

## 🗑️ DESINSTALAÇÃO EM MASSA

### **Desinstalar de Múltiplos Computadores:**

```powershell
.\DEPLOY_REDE_COMPLETO.ps1 -Uninstall -ComputerListFile "computadores.txt"
```

**Atenção:** Remove a tarefa agendada, mas **NÃO** remove os arquivos por segurança.

---

## 🔧 TROUBLESHOOTING

### **Problema: "Acesso Negado"**

**Solução:**
1. Verifique credenciais administrativas
2. Verifique se PowerShell Remoting está habilitado:
   ```powershell
   Enable-PSRemoting -Force
   ```
3. Verifique firewall:
   ```powershell
   Enable-NetFirewallRule -DisplayName "Windows Remote Management*"
   ```

### **Problema: "Computador não acessível"**

**Solução:**
1. Verifique conectividade:
   ```powershell
   Test-Connection -ComputerName "PC01"
   ```
2. Verifique compartilhamentos administrativos:
   ```powershell
   Test-Path "\\PC01\C$"
   ```

### **Problema: "Python não encontrado"**

**Solução:**
1. Compile o agente em .exe:
   ```cmd
   .\build_exe.bat
   ```
2. OU especifique caminho do Python:
   ```powershell
   -PythonPath "C:\Python39\python.exe"
   ```

### **Problema: "Event Log 307 não habilitado"**

**Solução:**
1. Use o parâmetro `-EnableEventLog`:
   ```powershell
   -EnableEventLog
   ```
2. OU execute manualmente em cada computador:
   ```powershell
   .\habilitar_event_log_307.ps1
   ```

---

## 📊 EXEMPLOS COMPLETOS

### **Exemplo 1: Instalação Completa em 10 Computadores**

```powershell
# 1. Criar lista
$computers = @("PC01", "PC02", "PC03", "PC04", "PC05", "PC06", "PC07", "PC08", "PC09", "PC10")
$computers | Out-File -FilePath "computadores.txt" -Encoding UTF8

# 2. Instalar
.\DEPLOY_REDE_COMPLETO.ps1 `
    -Install `
    -ComputerListFile "computadores.txt" `
    -ServerURL "http://192.168.1.27:5002/api/print_events" `
    -Domain "MEUDOMINIO" `
    -EnableEventLog `
    -Force

# 3. Verificar
.\DEPLOY_REDE_COMPLETO.ps1 -Status -ComputerListFile "computadores.txt"
```

### **Exemplo 2: Instalação Automática em Toda a Rede**

```powershell
# Descobre e instala automaticamente
.\DEPLOY_REDE_COMPLETO.ps1 `
    -Install `
    -Discover `
    -ServerURL "http://192.168.1.27:5002/api/print_events" `
    -Domain "MEUDOMINIO" `
    -EnableEventLog `
    -Force
```

### **Exemplo 3: Atualização em Massa**

```powershell
# Atualiza todos os computadores com nova versão
.\DEPLOY_REDE_COMPLETO.ps1 `
    -Update `
    -ComputerListFile "computadores.txt" `
    -ServerURL "http://192.168.1.27:5002/api/print_events"
```

---

## 📝 CHECKLIST DE DEPLOY

### **Antes do Deploy:**

- [ ] Servidor de monitoramento configurado e acessível
- [ ] URL do servidor conhecida
- [ ] Credenciais administrativas disponíveis
- [ ] Lista de computadores preparada (ou descoberta automática)
- [ ] Agente compilado em .exe OU Python instalado nos alvos
- [ ] PowerShell Remoting habilitado nos alvos
- [ ] Firewall configurado corretamente

### **Durante o Deploy:**

- [ ] Executar script como Administrador
- [ ] Verificar conectividade com computadores
- [ ] Monitorar progresso da instalação
- [ ] Verificar logs de erros

### **Após o Deploy:**

- [ ] Verificar status de todos os computadores
- [ ] Testar impressão em alguns computadores
- [ ] Verificar se eventos chegam ao servidor
- [ ] Documentar computadores instalados

---

## 🎯 MELHORES PRÁTICAS

1. **Teste Primeiro:** Sempre teste em 1-2 computadores antes de fazer deploy em massa
2. **Backup:** Faça backup das configurações antes de atualizar
3. **Documentação:** Mantenha lista atualizada de computadores instalados
4. **Monitoramento:** Configure alertas para verificar se agentes estão funcionando
5. **Atualizações:** Planeje janelas de manutenção para atualizações

---

## 📚 DOCUMENTAÇÃO RELACIONADA

- `TUTORIAL_INSTALACAO_COMPLETA.md` - Tutorial detalhado
- `CONFIGURAR_VIA_GPO.md` - Instalação via Group Policy
- `COMPILAR_EM_EXE.md` - Como compilar em executável
- `CHECKLIST_INSTALACAO.md` - Checklist de instalação

---

**Última atualização:** 2024

