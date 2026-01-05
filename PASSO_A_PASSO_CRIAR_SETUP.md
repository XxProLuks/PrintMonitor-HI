# 🎯 PASSO A PASSO: CRIAR SEU PRIMEIRO INSTALADOR

**Guia visual e prático - Siga os passos na ordem!**

---

## ✅ VERIFICAÇÃO INICIAL

Você já tem:
- ✅ Inno Setup instalado (confirmado!)
- ✅ Arquivos do projeto
- ✅ Scripts .iss prontos

**Agora só falta compilar!** 🚀

---

## 🚀 MÉTODO MAIS FÁCIL (3 PASSOS)

### **PASSO 1: Abrir PowerShell**

1. Pressione `Windows + X`
2. Escolha **"Windows PowerShell (Admin)"** ou **"Terminal (Admin)"**
3. Navegue até o projeto:

```powershell
cd "C:\Users\giovanni.HI\Pictures\Monitoramento1"
```

### **PASSO 2: Executar Script**

```batch
criar_instaladores.bat
```

Ou se preferir PowerShell:

```powershell
.\criar_instaladores.ps1
```

### **PASSO 3: Aguardar**

O script vai:
1. ✅ Procurar Inno Setup (já encontrou!)
2. ✅ Compilar instalador do servidor
3. ✅ Compilar instalador do agente
4. ✅ Gerar arquivos em `dist\`

**Tempo estimado: 2-5 minutos**

---

## 📁 ONDE ESTÃO OS INSTALADORES?

Após compilar, os arquivos estarão em:

```
C:\Users\giovanni.HI\Pictures\Monitoramento1\dist\
├── PrintMonitorServer_Setup.exe    ← Instalador do servidor
└── PrintMonitorAgent_Setup.exe      ← Instalador do agente
```

---

## 🎨 MÉTODO MANUAL (PASSO A PASSO VISUAL)

Se preferir fazer manualmente:

### **PASSO 1: Abrir Inno Setup**

1. Menu Iniciar → Digite "Inno Setup"
2. Clique em **"Inno Setup Compiler"**

### **PASSO 2: Compilar Servidor**

1. No Inno Setup, clique em **File → Open**
2. Navegue até: `C:\Users\giovanni.HI\Pictures\Monitoramento1\serv\`
3. Selecione `setup_servidor.iss`
4. Clique em **Abrir**
5. Clique em **Build → Compile** (ou pressione **F9**)
6. Aguarde a compilação
7. Veja a mensagem: **"Compile succeeded!"**

### **PASSO 3: Compilar Agente**

1. No Inno Setup, clique em **File → Open**
2. Navegue até: `C:\Users\giovanni.HI\Pictures\Monitoramento1\agent\`
3. Selecione `setup_agente.iss`
4. Clique em **Abrir**
5. Clique em **Build → Compile** (ou pressione **F9**)
6. Aguarde a compilação
7. Veja a mensagem: **"Compile succeeded!"**

---

## 🧪 TESTAR OS INSTALADORES

### **Teste Rápido:**

1. Abra a pasta `dist\`
2. Execute `PrintMonitorServer_Setup.exe`
3. Siga o assistente
4. Verifique se instalou corretamente

---

## 📊 O QUE VOCÊ VÊ DURANTE A COMPILAÇÃO

### **No Inno Setup:**

```
[Compile Scripts]
Compiling [Code] section...
Compiling [Setup] section...
Compiling [Files] section...
Compiling [Icons] section...
Compiling [Tasks] section...
Compiling [Run] section...
Successfully compiled: PrintMonitorServer_Setup.exe
```

### **No Script Batch:**

```
Inno Setup encontrado: C:\Program Files (x86)\Inno Setup 6\ISCC.exe

Criando instalador do SERVIDOR...
[Compilando...]
OK! Instalador do servidor criado.

Criando instalador do AGENTE...
[Compilando...]
OK! Instalador do agente criado.

INSTALADORES CRIADOS COM SUCESSO!
```

---

## 🎯 COMANDO RÁPIDO

**Para criar os instaladores rapidamente:**

```batch
criar_instaladores.bat
```

**Pronto!** Os instaladores estarão em `dist\`

---

## 💡 DICAS

1. **Primeira vez?** Use o script batch - é mais fácil
2. **Quer personalizar?** Edite os arquivos `.iss` antes de compilar
3. **Erro?** Veja a aba "Output" no Inno Setup para detalhes
4. **Teste sempre** em máquina limpa antes de distribuir

---

## 🐛 SE ALGO DER ERRADO

### **Erro: "Inno Setup não encontrado"**

**Solução:** O script já encontrou! Se der erro, verifique:
```powershell
Test-Path "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
```

### **Erro: "Arquivo não encontrado"**

**Solução:** Verifique se está na pasta correta:
```powershell
pwd  # Deve mostrar: C:\Users\giovanni.HI\Pictures\Monitoramento1
```

### **Erro ao compilar**

**Solução:**
1. Abra o arquivo `.iss` no Inno Setup
2. Veja a aba "Output" para detalhes do erro
3. Verifique se todos os arquivos referenciados existem

---

## ✅ CHECKLIST FINAL

Antes de distribuir:

- [ ] Instaladores compilados
- [ ] Arquivos em `dist\`
- [ ] Testados em máquina limpa
- [ ] Funcionando corretamente

---

## 🎉 PRONTO!

Agora você sabe criar os instaladores! 

**Execute:**
```batch
criar_instaladores.bat
```

**E pronto!** 🚀

---

**Para mais detalhes, consulte:**
- `COMO_CRIAR_SETUP.md` - Guia completo
- `TUTORIAL_CRIAR_SETUP.md` - Tutorial detalhado
- `GUIA_INSTALADORES_SETUP.md` - Documentação técnica


