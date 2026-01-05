# 📦 GUIA DE INSTALADORES SETUP (.EXE)

**Como criar e usar instaladores executáveis profissionais**

---

## 🎯 VISÃO GERAL

Este guia explica como criar instaladores executáveis (.exe) tipo "setup" para o sistema de monitoramento de impressão, usando **Inno Setup**.

Os instaladores criados são:
- ✅ **Profissionais** - Interface moderna e intuitiva
- ✅ **Completos** - Instalam tudo automaticamente
- ✅ **Configuráveis** - Opções durante instalação
- ✅ **Desinstaláveis** - Remoção completa via Painel de Controle

---

## 📋 REQUISITOS

### **Para Criar os Instaladores:**

1. **Inno Setup Compiler**
   - Download: https://jrsoftware.org/isdl.php
   - Versão recomendada: 6.x ou superior
   - Instale normalmente

2. **Arquivos do Projeto**
   - Todos os arquivos do servidor/agente devem estar presentes

---

## 🚀 CRIAR OS INSTALADORES

### **Método 1: Script Batch (Mais Fácil)**

```batch
# Execute na raiz do projeto
criar_instaladores.bat
```

### **Método 2: Script PowerShell**

```powershell
# Execute na raiz do projeto
.\criar_instaladores.ps1
```

### **Método 3: Manual (Inno Setup GUI)**

1. Abra o **Inno Setup Compiler**
2. Abra o arquivo:
   - `serv\setup_servidor.iss` (para servidor)
   - `agent\setup_agente.iss` (para agente)
3. Clique em **Build > Compile** (ou F9)
4. Os instaladores serão gerados em `dist\`

---

## 📦 INSTALADORES CRIADOS

Após compilar, você terá:

### **Servidor:**
- `dist\PrintMonitorServer_Setup.exe`
  - Instala o servidor completo
  - Configura firewall (opcional)
  - Cria serviço Windows (opcional)
  - Instala dependências Python

### **Agente:**
- `dist\PrintMonitorAgent_Setup.exe`
  - Instala o agente
  - Solicita URL do servidor durante instalação
  - Cria tarefa agendada (início automático)
  - Configura `config.json`

---

## 🎯 USAR OS INSTALADORES

### **Instalar Servidor:**

1. Execute `PrintMonitorServer_Setup.exe`
2. Siga o assistente de instalação
3. Escolha opções:
   - ✅ Configurar Firewall
   - ⬜ Instalar como Serviço
4. Aguarde a instalação
5. Pronto! O servidor está instalado

### **Instalar Agente:**

1. Execute `PrintMonitorAgent_Setup.exe`
2. Na primeira tela, digite a **URL do servidor**:
   ```
   http://192.168.1.27:5002/api/print_events
   ```
3. Siga o assistente
4. Escolha opções:
   - ✅ Iniciar automaticamente com o Windows
5. Aguarde a instalação
6. Pronto! O agente está instalado e configurado

---

## ⚙️ PERSONALIZAR OS INSTALADORES

### **Editar `serv\setup_servidor.iss`:**

```pascal
#define MyAppName "Print Monitor Server"      // Nome do aplicativo
#define MyAppVersion "1.0.0"                  // Versão
#define MyAppPublisher "Sua Empresa"          // Publicador
#define DefaultDirName "{autopf}\PrintMonitor\Server"  // Diretório padrão
```

### **Editar `agent\setup_agente.iss`:**

```pascal
#define MyAppName "Print Monitor Agent"       // Nome do aplicativo
#define MyAppVersion "1.0.0"                  // Versão
#define DefaultDirName "{autopf}\PrintMonitor\Agent"  // Diretório padrão
```

### **Adicionar Ícone:**

1. Coloque um arquivo `.ico` na pasta
2. Edite o script:
```pascal
SetupIconFile=icone.ico
```

### **Adicionar Licença:**

1. Crie um arquivo `LICENSE.txt`
2. Edite o script:
```pascal
LicenseFile=LICENSE.txt
```

---

## 🔧 ESTRUTURA DOS SCRIPTS

### **Seções Principais:**

- `[Setup]` - Configurações gerais
- `[Files]` - Arquivos a serem instalados
- `[Tasks]` - Tarefas opcionais (firewall, serviço, etc.)
- `[Run]` - Comandos a executar após instalação
- `[Icons]` - Atalhos no menu e desktop
- `[Code]` - Código Pascal para lógica customizada

---

## 📝 EXEMPLOS DE USO

### **Instalação Silenciosa (Servidor):**

```batch
PrintMonitorServer_Setup.exe /SILENT /TASKS="firewall"
```

### **Instalação Silenciosa (Agente):**

```batch
PrintMonitorAgent_Setup.exe /SILENT /SERVERURL="http://servidor:5002/api/print_events"
```

### **Desinstalação Silenciosa:**

```batch
"C:\Program Files\PrintMonitor\Server\unins000.exe" /SILENT
```

---

## 🎨 PERSONALIZAÇÃO AVANÇADA

### **Adicionar Página de Configuração:**

No script do agente, já existe uma página que solicita a URL do servidor. Você pode adicionar mais páginas:

```pascal
[Code]
procedure InitializeWizard;
begin
  // Criar nova página
  MyPage := CreateInputQueryPage(wpWelcome,
    'Configuração', 'Digite as configurações',
    'Configure o agente:');
  MyPage.Add('Porta:', False);
end;
```

### **Verificar Requisitos:**

```pascal
function InitializeSetup(): Boolean;
begin
  // Verificar Python
  if not RegQueryStringValue(...) then
  begin
    MsgBox('Python não encontrado!', mbError, MB_OK);
    Result := False;
  end;
end;
```

---

## 🐛 TROUBLESHOOTING

### **Problema: Inno Setup não encontrado**

**Solução:**
- Instale o Inno Setup Compiler
- Ou use os instaladores Python/PowerShell diretamente

### **Problema: Erro ao compilar**

**Solução:**
- Verifique se todos os arquivos referenciados existem
- Verifique se os caminhos estão corretos
- Verifique a sintaxe do script .iss

### **Problema: Instalador não executa scripts PowerShell**

**Solução:**
- Verifique se o PowerShell está habilitado
- Execute como Administrador
- Verifique políticas de execução

---

## 📚 RECURSOS ADICIONAIS

### **Documentação Inno Setup:**
- https://jrsoftware.org/ishelp/

### **Exemplos:**
- https://jrsoftware.org/is3/examples.php

### **Traduções:**
- Os scripts já incluem suporte a Português e Inglês
- Mais idiomas: https://jrsoftware.org/files/istrans/

---

## ✅ CHECKLIST DE DISTRIBUIÇÃO

Antes de distribuir os instaladores:

- [ ] Testar instalação em máquina limpa
- [ ] Testar desinstalação completa
- [ ] Verificar se todos os arquivos são instalados
- [ ] Verificar se as configurações são aplicadas
- [ ] Testar em diferentes versões do Windows
- [ ] Verificar se não há arquivos faltando
- [ ] Testar instalação silenciosa
- [ ] Verificar tamanho dos instaladores

---

## 💡 DICAS

1. **Sempre teste** em máquina limpa antes de distribuir
2. **Mantenha versões** dos instaladores organizadas
3. **Documente mudanças** entre versões
4. **Use assinatura digital** para produção (opcional)
5. **Compacte os instaladores** se necessário (já estão comprimidos)

---

**Arquivos relacionados:**
- `serv\setup_servidor.iss` - Script do instalador do servidor
- `agent\setup_agente.iss` - Script do instalador do agente
- `criar_instaladores.bat` - Script para criar instaladores (batch)
- `criar_instaladores.ps1` - Script para criar instaladores (PowerShell)


