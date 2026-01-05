# 📚 EXEMPLOS PRÁTICOS DE DEPLOY DO AGENTE

**Guia rápido com exemplos prontos para uso**

---

## 🚀 EXEMPLOS RÁPIDOS

### **1. Instalação Básica (3 computadores)**

```powershell
.\DEPLOY_REDE_COMPLETO.ps1 -Install -Computers @("PC01", "PC02", "PC03") -ServerURL "http://192.168.1.27:5002/api/print_events"
```

---

### **2. Instalação com Descoberta Automática**

```powershell
.\DEPLOY_REDE_COMPLETO.ps1 -Install -Discover -ServerURL "http://192.168.1.27:5002/api/print_events" -EnableEventLog
```

---

### **3. Instalação via Arquivo de Lista**

```powershell
# Criar arquivo computadores.txt:
# PC01
# PC02
# PC03

.\DEPLOY_REDE_COMPLETO.ps1 -Install -ComputerListFile "computadores.txt" -ServerURL "http://192.168.1.27:5002/api/print_events"
```

---

### **4. Instalação com Domínio**

```powershell
.\DEPLOY_REDE_COMPLETO.ps1 `
    -Install `
    -Computers @("PC01", "PC02") `
    -Domain "MEUDOMINIO" `
    -ServerURL "http://192.168.1.27:5002/api/print_events" `
    -EnableEventLog
```

---

### **5. Verificar Status**

```powershell
.\DEPLOY_REDE_COMPLETO.ps1 -Status -Computers @("PC01", "PC02", "PC03")
```

---

### **6. Atualizar Agente**

```powershell
.\DEPLOY_REDE_COMPLETO.ps1 -Update -ComputerListFile "computadores.txt" -ServerURL "http://192.168.1.27:5002/api/print_events"
```

---

### **7. Desinstalar**

```powershell
.\DEPLOY_REDE_COMPLETO.ps1 -Uninstall -Computers @("PC01", "PC02")
```

---

## 📋 EXEMPLOS AVANÇADOS

### **Instalação em Toda a OU do Active Directory**

```powershell
# Descobre computadores da OU
$computers = Get-ADComputer -Filter * -SearchBase "OU=Computadores,DC=empresa,DC=local" | Select-Object -ExpandProperty Name

# Instala em todos
.\DEPLOY_REDE_COMPLETO.ps1 `
    -Install `
    -Computers $computers `
    -ServerURL "http://servidor:5002/api/print_events" `
    -Domain "EMPRESA" `
    -EnableEventLog `
    -Force
```

---

### **Instalação com Verificação de Status**

```powershell
# 1. Instala
.\DEPLOY_REDE_COMPLETO.ps1 -Install -ComputerListFile "lista.txt" -ServerURL "http://servidor:5002/api/print_events"

# 2. Verifica status
.\DEPLOY_REDE_COMPLETO.ps1 -Status -ComputerListFile "lista.txt"
```

---

### **Instalação com Log Detalhado**

```powershell
# Salva output em arquivo
.\DEPLOY_REDE_COMPLETO.ps1 `
    -Install `
    -ComputerListFile "lista.txt" `
    -ServerURL "http://servidor:5002/api/print_events" `
    | Tee-Object -FilePath "deploy_log.txt"
```

---

## 🎯 CENÁRIOS COMUNS

### **Cenário 1: Primeira Instalação em 20 Computadores**

```powershell
# 1. Criar lista
$computers = 1..20 | ForEach-Object { "PC{0:D2}" -f $_ }
$computers | Out-File -FilePath "computadores.txt" -Encoding UTF8

# 2. Instalar
.\DEPLOY_REDE_COMPLETO.ps1 `
    -Install `
    -ComputerListFile "computadores.txt" `
    -ServerURL "http://192.168.1.27:5002/api/print_events" `
    -Domain "EMPRESA" `
    -EnableEventLog `
    -Force

# 3. Verificar
.\DEPLOY_REDE_COMPLETO.ps1 -Status -ComputerListFile "computadores.txt"
```

---

### **Cenário 2: Atualização de Versão**

```powershell
# Atualiza todos os computadores
.\DEPLOY_REDE_COMPLETO.ps1 `
    -Update `
    -ComputerListFile "computadores.txt" `
    -ServerURL "http://192.168.1.27:5002/api/print_events" `
    -Force
```

---

### **Cenário 3: Instalação em Novos Computadores**

```powershell
# Descobre novos computadores e instala
.\DEPLOY_REDE_COMPLETO.ps1 `
    -Install `
    -Discover `
    -ServerURL "http://192.168.1.27:5002/api/print_events" `
    -EnableEventLog
```

---

## 💡 DICAS

1. **Sempre teste primeiro** em 1-2 computadores
2. **Use -Force** apenas quando necessário (reinstalação)
3. **Use -EnableEventLog** para habilitar Event 307 automaticamente
4. **Mantenha lista atualizada** de computadores instalados
5. **Verifique status regularmente** após instalação

---

**Para mais informações, consulte:** `GUIA_DEPLOY_REDE.md`

