# 🧪 COMO TESTAR OS INSTALADORES

**Guia para testar os instaladores antes de distribuir**

---

## ✅ CHECKLIST DE TESTES

### **Antes de Testar:**

- [ ] Instaladores compilados com sucesso
- [ ] Arquivos .exe em `dist\`
- [ ] Máquina de teste preparada (ou VM)

---

## 🧪 TESTE 1: INSTALADOR DO SERVIDOR

### **Passo 1: Executar Instalador**

1. Execute `dist\PrintMonitorServer_Setup.exe`
2. Observe a interface do instalador

### **Passo 2: Seguir Assistente**

1. **Tela de Boas-vindas**
   - ✅ Interface aparece corretamente
   - ✅ Textos legíveis

2. **Seleção de Diretório**
   - ✅ Diretório padrão sugerido
   - ✅ Pode mudar diretório

3. **Tarefas Opcionais**
   - ✅ Checkbox "Configurar Firewall" aparece
   - ✅ Checkbox "Instalar como Serviço" aparece
   - ✅ Pode marcar/desmarcar

4. **Instalação**
   - ✅ Barra de progresso funciona
   - ✅ Mensagens de status aparecem
   - ✅ Não trava durante instalação

### **Passo 3: Verificar Instalação**

```powershell
# Verificar se arquivos foram instalados
Test-Path "C:\Program Files\PrintMonitor\Server\servidor.py"

# Verificar se serviço foi criado (se selecionado)
Get-Service -Name "PrintMonitorServer" -ErrorAction SilentlyContinue

# Verificar regra de firewall (se selecionado)
Get-NetFirewallRule -DisplayName "PrintMonitor Server" -ErrorAction SilentlyContinue
```

### **Passo 4: Testar Funcionamento**

```powershell
# Iniciar servidor
cd "C:\Program Files\PrintMonitor\Server"
python servidor.py
```

### **Passo 5: Desinstalar**

1. Painel de Controle → Programas → Desinstalar
2. Ou: Menu Iniciar → Print Monitor → Desinstalar
3. Verificar se tudo foi removido

---

## 🧪 TESTE 2: INSTALADOR DO AGENTE

### **Passo 1: Executar Instalador**

1. Execute `dist\PrintMonitorAgent_Setup.exe`
2. Observe a interface

### **Passo 2: Seguir Assistente**

1. **Tela de Boas-vindas**
   - ✅ Interface aparece

2. **Configuração do Servidor**
   - ✅ Campo "IP do Servidor" aparece
   - ✅ Campo "Porta do Servidor" aparece
   - ✅ Valores padrão preenchidos
   - ✅ Validação funciona (teste IP inválido)
   - ✅ Validação funciona (teste porta inválida)

3. **Tarefas Opcionais**
   - ✅ "Iniciar automaticamente" marcado por padrão
   - ✅ "Instalar dependências" marcado por padrão
   - ✅ "Testar conexão" marcado por padrão

4. **Instalação**
   - ✅ Progresso visível
   - ✅ Mensagens de status

### **Passo 3: Verificar Instalação**

```powershell
# Verificar arquivos
Test-Path "C:\Program Files\PrintMonitor\Agent\agente.py"
Test-Path "C:\Program Files\PrintMonitor\Agent\config.json"

# Verificar tarefa agendada
Get-ScheduledTask -TaskName "PrintMonitorAgent"

# Verificar configuração
Get-Content "C:\Program Files\PrintMonitor\Agent\config.json"
```

### **Passo 4: Verificar Início Automático**

```powershell
# Verificar tarefa
.\agent\verificar_inicio_automatico.ps1

# Ou manualmente
Get-ScheduledTask -TaskName "PrintMonitorAgent" | Get-ScheduledTaskInfo
```

### **Passo 5: Testar Funcionamento**

```powershell
# Iniciar agente manualmente
cd "C:\Program Files\PrintMonitor\Agent"
python agente.py
```

### **Passo 6: Reiniciar e Verificar**

1. Reinicie o computador
2. Verifique se o agente inicia automaticamente
3. Verifique logs

---

## 🐛 TESTES DE ERRO

### **Teste 1: IP Inválido**

1. Execute instalador do agente
2. Digite IP inválido (ex: `999.999.999.999`)
3. ✅ Deve mostrar erro de validação

### **Teste 2: Porta Inválida**

1. Execute instalador do agente
2. Digite porta inválida (ex: `99999`)
3. ✅ Deve mostrar erro de validação

### **Teste 3: Servidor Inacessível**

1. Execute instalador do agente
2. Digite IP de servidor que não existe
3. Marque "Testar conexão"
4. ✅ Deve avisar mas permitir continuar

### **Teste 4: Sem Python**

1. Desinstale Python temporariamente
2. Execute instalador
3. ✅ Deve avisar mas permitir continuar

---

## 📊 RELATÓRIO DE TESTES

Após testar, preencha:

```
✅ Instalador do Servidor:
   [ ] Interface funciona
   [ ] Instala arquivos corretamente
   [ ] Configura firewall (se selecionado)
   [ ] Cria serviço (se selecionado)
   [ ] Desinstala completamente

✅ Instalador do Agente:
   [ ] Interface funciona
   [ ] Validação de IP funciona
   [ ] Validação de porta funciona
   [ ] Instala arquivos corretamente
   [ ] Cria tarefa agendada
   [ ] Configura config.json
   [ ] Inicia automaticamente após reiniciar
   [ ] Desinstala completamente

✅ Testes de Erro:
   [ ] Validação de IP inválido
   [ ] Validação de porta inválida
   [ ] Teste de conexão com servidor offline
   [ ] Instalação sem Python
```

---

## 💡 DICAS DE TESTE

1. **Use VM** para testes limpos
2. **Teste em diferentes versões** do Windows
3. **Teste como usuário comum** e como admin
4. **Teste desinstalação** completa
5. **Verifique logs** após instalação

---

**Boa sorte com os testes!** 🧪


