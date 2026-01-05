# 📦 COMO CRIAR OS INSTALADORES SETUP (.EXE)

**Guia completo passo a passo para criar instaladores profissionais**

---

## 🎯 O QUE VOCÊ VAI APRENDER

Neste guia você aprenderá:
1. Como instalar o Inno Setup Compiler
2. Como compilar os instaladores
3. Como personalizar os instaladores
4. Como distribuir os arquivos .exe

---

## 📋 PASSO 1: INSTALAR O INNO SETUP

### **1.1. Download**

1. Acesse: https://jrsoftware.org/isdl.php
2. Baixe a versão mais recente (recomendado: 6.x)
3. Execute o instalador baixado

### **1.2. Instalação**

1. Execute o arquivo baixado (ex: `innosetup-6.x.x.exe`)
2. Siga o assistente de instalação
3. Aceite os termos e instale normalmente
4. **Importante:** Anote o caminho de instalação (geralmente: `C:\Program Files (x86)\Inno Setup 6`)

### **1.3. Verificar Instalação**

Abra o PowerShell e execute:

```powershell
# Verifica se está instalado
Test-Path "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
```

Se retornar `True`, está instalado corretamente!

---

## 📋 PASSO 2: PREPARAR OS ARQUIVOS

### **2.1. Estrutura de Arquivos**

Certifique-se de que os arquivos estão organizados assim:

```
Monitoramento1/
├── serv/
│   ├── servidor.py
│   ├── modules/
│   ├── templates/
│   ├── static/
│   ├── setup_servidor.iss    ← Script do instalador
│   └── ...
├── agent/
│   ├── agente.py
│   ├── requirements.txt
│   ├── config.json.example
│   ├── setup_agente.iss      ← Script do instalador
│   └── ...
└── criar_instaladores.bat    ← Script para compilar
```

### **2.2. Verificar Arquivos Necessários**

**Para o Servidor:**
- ✅ `serv/servidor.py`
- ✅ `serv/modules/` (pasta completa)
- ✅ `serv/templates/` (pasta completa)
- ✅ `serv/static/` (pasta completa)
- ✅ `serv/setup_servidor.iss`

**Para o Agente:**
- ✅ `agent/agente.py`
- ✅ `agent/requirements.txt`
- ✅ `agent/config.json.example`
- ✅ `agent/setup_agente.iss`

---

## 📋 PASSO 3: CRIAR OS INSTALADORES

### **Método 1: Script Automático (MAIS FÁCIL) ⭐**

#### **3.1. Usando Batch (Windows)**

```batch
# Na raiz do projeto
criar_instaladores.bat
```

O script vai:
1. Procurar o Inno Setup automaticamente
2. Compilar o instalador do servidor
3. Compilar o instalador do agente
4. Gerar os arquivos .exe em `dist\`

#### **3.2. Usando PowerShell**

```powershell
# Na raiz do projeto
.\criar_instaladores.ps1
```

---

### **Método 2: Manual (Mais Controle)**

#### **3.3. Abrir Inno Setup Compiler**

1. Abra o **Inno Setup Compiler** (procure no menu Iniciar)
2. Você verá a interface do Inno Setup

#### **3.4. Compilar Instalador do Servidor**

1. No Inno Setup, clique em **File > Open**
2. Navegue até `serv\setup_servidor.iss`
3. Abra o arquivo
4. Clique em **Build > Compile** (ou pressione **F9**)
5. Aguarde a compilação
6. O instalador será gerado em `dist\PrintMonitorServer_Setup.exe`

#### **3.5. Compilar Instalador do Agente**

1. No Inno Setup, clique em **File > Open**
2. Navegue até `agent\setup_agente.iss`
3. Abra o arquivo
4. Clique em **Build > Compile** (ou pressione **F9**)
5. Aguarde a compilação
6. O instalador será gerado em `dist\PrintMonitorAgent_Setup.exe`

---

## 📋 PASSO 4: VERIFICAR OS INSTALADORES

### **4.1. Localização**

Os instaladores serão gerados em:

```
dist/
├── PrintMonitorServer_Setup.exe    ← Instalador do servidor
└── PrintMonitorAgent_Setup.exe    ← Instalador do agente
```

### **4.2. Testar os Instaladores**

1. **Teste em máquina limpa** (ou VM)
2. Execute `PrintMonitorServer_Setup.exe`
3. Siga o assistente de instalação
4. Verifique se tudo foi instalado corretamente
5. Repita para `PrintMonitorAgent_Setup.exe`

---

## 🎨 PASSO 5: PERSONALIZAR OS INSTALADORES

### **5.1. Editar Nome e Versão**

Abra o arquivo `.iss` e edite:

```pascal
#define MyAppName "Print Monitor Server"    // Nome do aplicativo
#define MyAppVersion "1.0.0"                 // Versão
#define MyAppPublisher "Sua Empresa"        // Publicador
```

### **5.2. Adicionar Ícone**

1. Coloque um arquivo `.ico` na pasta
2. Edite o script:

```pascal
SetupIconFile=icone.ico
```

### **5.3. Adicionar Licença**

1. Crie um arquivo `LICENSE.txt`
2. Edite o script:

```pascal
LicenseFile=LICENSE.txt
```

### **5.4. Mudar Diretório de Instalação**

```pascal
DefaultDirName={autopf}\PrintMonitor\Server
// Opções:
// {autopf} = Program Files
// {localappdata} = AppData\Local
// {userdocs} = Documentos do usuário
```

---

## 🔧 PASSO 6: ENTENDENDO OS SCRIPTS .ISS

### **6.1. Estrutura Básica**

```pascal
[Setup]
// Configurações gerais do instalador

[Files]
// Arquivos a serem instalados

[Tasks]
// Tarefas opcionais (checkboxes)

[Run]
// Comandos a executar após instalação

[Icons]
// Atalhos no menu e desktop

[Code]
// Código Pascal para lógica customizada
```

### **6.2. Seção [Setup]**

```pascal
[Setup]
AppName={#MyAppName}              // Nome do aplicativo
AppVersion={#MyAppVersion}        // Versão
DefaultDirName={autopf}\...       // Diretório padrão
PrivilegesRequired=admin          // Requer admin
WizardStyle=modern                // Estilo moderno
```

### **6.3. Seção [Files]**

```pascal
[Files]
Source: "arquivo.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "pasta\*"; DestDir: "{app}\pasta"; Flags: recursesubdirs
```

### **6.4. Seção [Tasks]**

```pascal
[Tasks]
Name: "task1"; Description: "Descrição"; Flags: checkedonce
```

### **6.5. Seção [Code]**

```pascal
[Code]
function InitializeSetup(): Boolean;
begin
  // Código executado antes da instalação
  Result := True;
end;
```

---

## 🚀 PASSO 7: COMPILAR E DISTRIBUIR

### **7.1. Compilação Rápida**

```batch
# Execute na raiz do projeto
criar_instaladores.bat
```

### **7.2. Compilação com Opções**

No Inno Setup Compiler:
- **Build > Compile** - Compila normalmente
- **Build > Compile (F9)** - Atalho de teclado
- **Build > Build** - Compila e executa o instalador

### **7.3. Distribuir**

1. Copie os arquivos `.exe` de `dist\`
2. Distribua para os usuários
3. Eles só precisam executar o `.exe`

---

## 📚 EXEMPLOS PRÁTICOS

### **Exemplo 1: Compilar Apenas o Servidor**

```powershell
# No PowerShell
$innoPath = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
& $innoPath "serv\setup_servidor.iss"
```

### **Exemplo 2: Compilar Apenas o Agente**

```powershell
# No PowerShell
$innoPath = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
& $innoPath "agent\setup_agente.iss"
```

### **Exemplo 3: Compilar Ambos**

```batch
# Batch
criar_instaladores.bat
```

---

## 🐛 TROUBLESHOOTING

### **Problema: Inno Setup não encontrado**

**Solução:**
```powershell
# Verificar caminhos possíveis
$paths = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
)
foreach ($path in $paths) {
    if (Test-Path $path) {
        Write-Host "Encontrado: $path"
    }
}
```

### **Problema: Erro ao compilar**

**Soluções:**
1. Verifique se todos os arquivos referenciados existem
2. Verifique se os caminhos estão corretos
3. Verifique a sintaxe do script .iss
4. Veja a aba "Output" no Inno Setup para detalhes do erro

### **Problema: Instalador muito grande**

**Soluções:**
1. Use compressão LZMA (já está configurado)
2. Remova arquivos desnecessários
3. Use `SolidCompression=yes` (já está configurado)

---

## 💡 DICAS E TRUQUES

### **1. Compilação Silenciosa**

```powershell
# Compilar sem abrir interface
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "serv\setup_servidor.iss" /O"dist"
```

### **2. Múltiplas Versões**

Crie pastas diferentes para cada versão:
```
dist/
├── v1.0.0/
│   ├── PrintMonitorServer_Setup.exe
│   └── PrintMonitorAgent_Setup.exe
└── v1.1.0/
    ├── PrintMonitorServer_Setup.exe
    └── PrintMonitorAgent_Setup.exe
```

### **3. Assinatura Digital (Produção)**

Para produção, assine os instaladores:
```pascal
[Setup]
SignTool=signtool
```

### **4. Logs de Compilação**

O Inno Setup gera logs em:
```
serv\Output\setup_servidor.log
agent\Output\setup_agente.log
```

---

## 📖 RECURSOS ADICIONAIS

### **Documentação Oficial:**
- https://jrsoftware.org/ishelp/

### **Exemplos:**
- https://jrsoftware.org/is3/examples.php

### **Traduções:**
- https://jrsoftware.org/files/istrans/

---

## ✅ CHECKLIST FINAL

Antes de distribuir:

- [ ] Inno Setup instalado
- [ ] Todos os arquivos necessários presentes
- [ ] Scripts .iss sem erros
- [ ] Instaladores compilados com sucesso
- [ ] Testados em máquina limpa
- [ ] Verificados tamanhos dos arquivos
- [ ] Documentação atualizada

---

## 🎯 RESUMO RÁPIDO

1. **Instalar Inno Setup** → https://jrsoftware.org/isdl.php
2. **Executar script** → `criar_instaladores.bat`
3. **Aguardar compilação** → Arquivos em `dist\`
4. **Testar** → Executar os .exe gerados
5. **Distribuir** → Copiar os .exe para usuários

---

**Pronto! Agora você sabe como criar os instaladores setup!** 🎉


