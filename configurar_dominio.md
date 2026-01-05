# 🌐 CONFIGURAÇÃO DE DOMÍNIO

**Guia para configurar um domínio personalizado para o Print Monitor**

---

## 📋 PRÉ-REQUISITOS

1. Domínio registrado (ex: `monitor.empresa.com`)
2. Acesso ao painel de DNS do domínio
3. IP público do servidor

---

## 🔧 CONFIGURAÇÃO DNS

### **1. Registrar Registro A**

No painel de DNS do seu domínio, adicione um registro **A**:

```
Tipo: A
Nome: monitor (ou @ para domínio raiz)
Valor: IP_DO_SERVIDOR
TTL: 3600 (ou padrão)
```

**Exemplo:**
- Domínio: `empresa.com`
- Subdomínio: `monitor.empresa.com`
- IP: `192.168.1.100`

### **2. Verificar Propagação**

Aguarde alguns minutos e verifique se o DNS está propagado:

```bash
# Linux/Mac
nslookup monitor.empresa.com
dig monitor.empresa.com

# Windows
nslookup monitor.empresa.com
```

---

## 🔒 CONFIGURAR HTTPS

Após configurar o DNS, configure HTTPS:

### **Opção 1: Script Automatizado (Linux)**

```bash
sudo chmod +x configurar_https.sh
sudo ./configurar_https.sh
```

### **Opção 2: Manual**

Siga as instruções em `GUIA_DEPLOY_RAPIDO.md` seção "Configurar HTTPS (Nginx)".

---

## ⚙️ ATUALIZAR CONFIGURAÇÕES

### **1. Atualizar .env**

```env
# Adicionar URL do servidor
SERVER_URL=https://monitor.empresa.com
```

### **2. Atualizar agent/config.json**

```json
{
  "server_url": "https://monitor.empresa.com/api/print_events"
}
```

---

## 🧪 TESTAR CONFIGURAÇÃO

### **1. Verificar DNS:**

```bash
ping monitor.empresa.com
```

### **2. Verificar HTTPS:**

```bash
curl -I https://monitor.empresa.com/health
```

### **3. Acessar no navegador:**

```
https://monitor.empresa.com
```

---

## 🔄 ATUALIZAR AGENTES

Após configurar o domínio, atualize todos os agentes:

```powershell
# Windows - Atualizar config.json em todos os agentes
$servers = @("PC01", "PC02", "PC03")
foreach ($server in $servers) {
    $config = @{
        server_url = "https://monitor.empresa.com/api/print_events"
    } | ConvertTo-Json
    Invoke-Command -ComputerName $server -ScriptBlock {
        $config | Out-File -FilePath "C:\Monitoramento\agent\config.json" -Encoding UTF8
    }
}
```

---

## 📝 EXEMPLOS DE CONFIGURAÇÃO

### **Exemplo 1: Subdomínio**

```
Domínio: empresa.com
Subdomínio: monitor.empresa.com
Registro DNS: A → monitor → 192.168.1.100
```

### **Exemplo 2: Domínio Dedicado**

```
Domínio: printmonitor.com
Registro DNS: A → @ → 192.168.1.100
```

### **Exemplo 3: Múltiplos Subdomínios**

```
monitor.empresa.com → Servidor principal
api.monitor.empresa.com → API (opcional)
```

---

## ⚠️ TROUBLESHOOTING

### **DNS não resolve:**

1. Verifique se o registro A está correto
2. Aguarde propagação (pode levar até 48 horas)
3. Verifique TTL do registro

### **Certificado SSL não funciona:**

1. Verifique se o DNS está propagado
2. Certifique-se de que a porta 80 está aberta
3. Verifique logs do Certbot: `journalctl -u certbot`

### **Agentes não conectam:**

1. Verifique URL em `agent/config.json`
2. Verifique firewall (porta 443)
3. Teste conexão: `curl https://monitor.empresa.com/health`

---

**Última atualização:** 2024-12-04

