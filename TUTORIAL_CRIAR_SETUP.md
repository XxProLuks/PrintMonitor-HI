# 🎓 TUTORIAL: CRIANDO SEU PRIMEIRO INSTALADOR SETUP

**Guia visual passo a passo para iniciantes**

---

## 🎯 OBJETIVO

Criar um instalador executável (.exe) profissional que:
- Instala o servidor ou agente automaticamente
- Configura tudo necessário
- Cria atalhos e tarefas agendadas
- Pode ser distribuído facilmente

---

## 📋 PASSO A PASSO COMPLETO

### **PASSO 1: INSTALAR O INNO SETUP** ⏱️ 5 minutos

#### **1.1. Baixar**

1. Abra seu navegador
2. Acesse: **https://jrsoftware.org/isdl.php**
3. Clique em **Download Inno Setup** (versão mais recente)
4. Salve o arquivo (ex: `innosetup-6.2.2.exe`)

#### **1.2. Instalar**

1. Execute o arquivo baixado
2. Clique em **Next** nas telas
3. Aceite os termos
4. Escolha o diretório (padrão está OK)
5. Clique em **Install**
6. Aguarde a instalação
7. Clique em **Finish**

✅ **Pronto!** Inno Setup instalado.

---

### **PASSO 2: PREPARAR OS ARQUIVOS** ⏱️ 2 minutos

#### **2.1. Verificar Estrutura**

Certifique-se de estar na raiz do projeto:

```
C:\Users\giovanni.HI\Pictures\Monitoramento1\
```

#### **2.2. Verificar Arquivos**

Os arquivos necessários já estão criados:
- ✅ `serv\setup_servidor.iss`
- ✅ `agent\setup_agente.iss`
- ✅ `criar_instaladores.bat`
- ✅ `criar_instaladores.ps1`

---

### **PASSO 3: CRIAR OS INSTALADORES** ⏱️ 5 minutos

#### **Opção A: Método Automático (RECOMENDADO)** ⭐

1. **Abra o PowerShell ou CMD** como Administrador
2. **Navegue até o projeto:**
   ```powershell
   cd "C:\Users\giovanni.HI\Pictures\Monitoramento1"
   ```
3. **Execute o script:**
   ```batch
   criar_instaladores.bat
   ```
4. **Aguarde a compilação** (pode demorar 1-2 minutos)
5. **Pronto!** Os instaladores estarão em `dist\`

#### **Opção B: Método Manual (Mais Controle)**

1. **Abra o Inno Setup Compiler**
   - Menu Iniciar → Inno Setup → Inno Setup Compiler

2. **Para o Servidor:**
   - File → Open
   - Navegue até `serv\setup_servidor.iss`
   - Abra
   - Build → Compile (ou F9)
   - Aguarde

3. **Para o Agente:**
   - File → Open
   - Navegue até `agent\setup_agente.iss`
   - Abra
   - Build → Compile (ou F9)
   - Aguarde

---

### **PASSO 4: VERIFICAR OS RESULTADOS** ⏱️ 1 minuto

#### **4.1. Localizar os Instaladores**

Abra o explorador de arquivos e vá até:

```
C:\Users\giovanni.HI\Pictures\Monitoramento1\dist\
```

Você deve ver:
- `PrintMonitorServer_Setup.exe` (instalador do servidor)
- `PrintMonitorAgent_Setup.exe` (instalador do agente)

#### **4.2. Verificar Tamanho**

Os arquivos devem ter alguns MB cada (dependendo do conteúdo).

---

### **PASSO 5: TESTAR OS INSTALADORES** ⏱️ 10 minutos

#### **5.1. Testar Instalador do Servidor**

1. Execute `PrintMonitorServer_Setup.exe`
2. Siga o assistente:
   - Escolha diretório de instalação
   - Escolha opções (firewall, serviço)
   - Aguarde instalação
3. Verifique se foi instalado corretamente

#### **5.2. Testar Instalador do Agente**

1. Execute `PrintMonitorAgent_Setup.exe`
2. Siga o assistente:
   - Digite IP do servidor (ex: `192.168.1.27`)
   - Digite porta (ex: `5002`)
   - Escolha opções
   - Aguarde instalação
3. Verifique se foi instalado corretamente

---

## 🎨 PERSONALIZAÇÃO BÁSICA

### **Mudar Nome e Versão**

1. Abra `serv\setup_servidor.iss` (ou `agent\setup_agente.iss`)
2. Encontre as linhas:

```pascal
#define MyAppName "Print Monitor Server"
#define MyAppVersion "1.0.0"
```

3. Altere para:

```pascal
#define MyAppName "Meu Sistema de Monitoramento"
#define MyAppVersion "2.0.0"
```

4. Recompile

### **Adicionar Ícone**

1. Coloque um arquivo `.ico` na pasta `serv\` ou `agent\`
2. Edite o script `.iss`:

```pascal
SetupIconFile=icone.ico
```

3. Recompile

---

## 🔍 ENTENDENDO O QUE ACONTECE

### **Durante a Compilação:**

1. **Inno Setup lê o script .iss**
2. **Coleta todos os arquivos** listados em `[Files]`
3. **Comprime tudo** usando LZMA
4. **Cria o executável** com interface de instalação
5. **Gera o arquivo .exe** em `dist\`

### **O que o Instalador Faz:**

1. **Extrai arquivos** para o diretório escolhido
2. **Executa scripts** de configuração
3. **Cria atalhos** no menu e desktop
4. **Configura tarefas** agendadas (agente)
5. **Registra no sistema** para desinstalação

---

## 📊 COMPARAÇÃO DOS MÉTODOS

| Método | Facilidade | Controle | Tempo |
|--------|------------|----------|-------|
| **Script Automático** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 2 min |
| **Inno Setup GUI** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 5 min |
| **Linha de Comando** | ⭐⭐⭐ | ⭐⭐⭐⭐ | 3 min |

---

## 🎯 EXEMPLO PRÁTICO COMPLETO

### **Cenário: Criar Instalador do Agente**

```powershell
# 1. Abrir PowerShell como Admin
# 2. Ir para o projeto
cd "C:\Users\giovanni.HI\Pictures\Monitoramento1"

# 3. Executar script
.\criar_instaladores.ps1

# 4. Aguardar (vê mensagens de progresso)
# 5. Verificar resultado
dir dist\

# 6. Testar
.\dist\PrintMonitorAgent_Setup.exe
```

---

## 🐛 PROBLEMAS COMUNS

### **"Inno Setup não encontrado"**

**Solução:**
```powershell
# Verificar se está instalado
Test-Path "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

# Se False, instale o Inno Setup
# Se True, o script deve encontrá-lo automaticamente
```

### **"Erro ao compilar"**

**Soluções:**
1. Verifique se todos os arquivos existem
2. Verifique se os caminhos estão corretos
3. Veja a aba "Output" no Inno Setup para detalhes

### **"Instalador não executa"**

**Soluções:**
1. Execute como Administrador
2. Verifique se não está bloqueado pelo Windows
3. Verifique antivírus

---

## 💡 DICAS PRO

### **1. Compilação Rápida**

Use o script batch - é mais rápido:
```batch
criar_instaladores.bat
```

### **2. Testar em VM**

Sempre teste em máquina limpa ou VM antes de distribuir.

### **3. Versionar**

Mantenha versões organizadas:
```
dist/
├── v1.0.0/
└── v1.1.0/
```

### **4. Logs**

O Inno Setup gera logs úteis em:
```
serv\Output\setup_servidor.log
```

---

## ✅ CHECKLIST RÁPIDO

Antes de criar:

- [ ] Inno Setup instalado
- [ ] Arquivos do projeto presentes
- [ ] Scripts .iss sem erros
- [ ] Pasta `dist\` criada (ou será criada automaticamente)

Após criar:

- [ ] Instaladores gerados em `dist\`
- [ ] Tamanho dos arquivos razoável
- [ ] Testados em máquina limpa
- [ ] Funcionando corretamente

---

## 🎓 PRÓXIMOS PASSOS

Agora que você sabe criar os instaladores:

1. **Personalize** os scripts .iss
2. **Adicione ícones** e banners
3. **Teste** em diferentes máquinas
4. **Distribua** para usuários

---

## 📚 RECURSOS

- **Documentação Inno Setup:** https://jrsoftware.org/ishelp/
- **Exemplos:** https://jrsoftware.org/is3/examples.php
- **Fórum:** https://groups.google.com/g/innosetup

---

**Pronto! Você agora sabe criar instaladores setup! 🎉**

**Dúvidas?** Consulte `COMO_CRIAR_SETUP.md` para mais detalhes.


