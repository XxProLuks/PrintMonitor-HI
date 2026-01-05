# 📘 GUIA DE USO DOS INSTALADORES COMPLETOS

## ✅ TODAS AS 26 IDEIAS IMPLEMENTADAS!

---

## 📁 ARQUIVOS CRIADOS

### Instalador do Agente
- **Arquivo:** `agent/setup_agente_completo.iss`
- **Status:** ✅ Completo (26/26 funcionalidades)
- **Tamanho:** ~920 linhas

### Instalador do Servidor
- **Arquivo:** `serv/setup_servidor_completo.iss`
- **Status:** ✅ Completo (26/26 funcionalidades)
- **Tamanho:** ~600 linhas

---

## 🔄 COMO SUBSTITUIR OS ARQUIVOS ORIGINAIS

### Opção 1: Backup e Substituição (Recomendado)

```batch
# Fazer backup dos arquivos originais
copy agent\setup_agente.iss agent\setup_agente.iss.backup
copy serv\setup_servidor.iss serv\setup_servidor.iss.backup

# Substituir pelos completos
copy agent\setup_agente_completo.iss agent\setup_agente.iss
copy serv\setup_servidor_completo.iss serv\setup_servidor.iss
```

### Opção 2: Usar Diretamente

Os arquivos completos podem ser usados diretamente sem substituir os originais. Basta compilar:

```batch
# Compilar apenas os completos
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" agent\setup_agente_completo.iss
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" serv\setup_servidor_completo.iss
```

---

## 🎯 FUNCIONALIDADES IMPLEMENTADAS

### ✅ Instalação/Atualização/Reinstalação

**Como funciona:**
1. O instalador detecta automaticamente se já existe uma instalação
2. Se encontrar, oferece opção de atualizar ou reinstalar
3. Durante atualização, preserva configurações e faz backup automático

**Exemplo:**
```
Instalador detecta: Versão 0.9.0 instalada
→ Pergunta: "Deseja atualizar para versão 1.0.0?"
→ Se SIM: Faz backup e atualiza
→ Se NÃO: Cancela instalação
```

### ✅ Verificação Completa de Requisitos

**Verifica:**
- ✅ Windows 10 Build 17763+ (ou superior)
- ✅ Python 3.8+ instalado
- ✅ Espaço em disco (500 MB para agente, 1 GB para servidor)
- ✅ RAM disponível (2 GB recomendado para agente, 4 GB para servidor)

**Mensagens:**
- Erros críticos bloqueiam instalação
- Avisos permitem continuar com confirmação

### ✅ Backup Automático

**Agente:**
- Backup de `config.json` antes de atualizar
- Formato: `config.json.backup.YYYYMMDD-HHMMSS`
- Múltiplos backups mantidos

**Servidor:**
- Backup de `print_events.db` antes de atualizar
- Formato: `print_events.db.backup.YYYYMMDD-HHMMSS`
- Salvos em `{app}\backups\`

### ✅ Validação Avançada

**Agente:**
- Valida formato de IP (192.168.1.1)
- Valida porta (1-65535)
- Verifica se porta está em uso
- Testa conexão com servidor

**Servidor:**
- Valida porta (1-65535)
- Verifica se porta está em uso
- Alerta se porta já está sendo usada

### ✅ Página de Configuração Avançada

**Agente:**
- Nível de log (DEBUG/INFO/WARNING/ERROR)
- Tamanho máximo de log (MB)

**Servidor:**
- Nível de log (DEBUG/INFO/WARNING/ERROR)
- Tamanho máximo de log (MB)

### ✅ Seleção de Componentes

**Agente:**
- Agente Principal (obrigatório)
- Ferramentas Administrativas (opcional)
- Documentação (opcional)

**Servidor:**
- Servidor Principal (obrigatório)
- Módulos do Sistema (obrigatório)
- Templates Web (obrigatório)
- Arquivos Estáticos (obrigatório)
- Ferramentas Administrativas (opcional)
- Documentação (opcional)

### ✅ Ferramentas de Diagnóstico

**Scripts criados automaticamente:**
- `diagnostico.bat` - Verifica sistema completo
- Acessível pelo menu Iniciar

**Verifica:**
- Python instalado
- Processos em execução
- Tarefas agendadas (agente)
- Portas em uso (servidor)
- Arquivos principais
- Firewall (servidor)

### ✅ Log de Instalação

**Arquivo:** `{app}\install.log`

**Registra:**
- Data/hora de cada operação
- Modo de instalação (install/upgrade/reinstall)
- Todas as ações realizadas
- Erros e avisos

### ✅ Coleta de Informações do Sistema

**Arquivo:** `{app}\system_info.txt`

**Informações coletadas:**
- Versão do Windows
- Arquitetura
- Versão do Python
- Data/hora da instalação
- Versão instalada
- Modo de instalação
- Espaço em disco
- Configurações aplicadas

### ✅ Desinstalação Melhorada

**Agente:**
- Confirmação antes de desinstalar
- Para processos automaticamente
- Remove tarefa agendada
- Limpa logs e arquivos temporários
- Preserva backups

**Servidor:**
- Confirmação antes de desinstalar
- Para processos automaticamente
- Remove serviço Windows (se instalado)
- Remove regras de firewall
- Opção de manter banco de dados
- Limpa logs e backups

---

## 🚀 COMO USAR

### 1. Compilar os Instaladores

```batch
# Usar script automatizado
criar_instaladores.bat

# Ou compilar manualmente
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" agent\setup_agente.iss
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" serv\setup_servidor.iss
```

### 2. Instalar o Servidor

1. Execute `PrintMonitorServer_Setup.exe`
2. Siga o assistente:
   - Configure porta (padrão: 5002)
   - Configure host (padrão: 0.0.0.0)
   - Escolha componentes
   - Configure opções avançadas (opcional)
3. Aguarde instalação
4. Acesse: `http://localhost:5002`

### 3. Instalar o Agente

1. Execute `PrintMonitorAgent_Setup.exe`
2. Siga o assistente:
   - Configure IP do servidor
   - Configure porta do servidor
   - Configure intervalos
   - Escolha componentes
   - Configure opções avançadas (opcional)
3. Aguarde instalação
4. O agente iniciará automaticamente

### 4. Atualizar Instalação Existente

1. Execute o instalador novamente
2. O instalador detectará versão anterior
3. Escolha atualizar
4. Configurações serão preservadas
5. Backup automático será criado

### 5. Desinstalar

**Agente:**
1. Painel de Controle → Programas → Desinstalar
2. Ou: Menu Iniciar → Print Monitor → Desinstalar
3. Confirme desinstalação
4. Processos serão parados automaticamente

**Servidor:**
1. Painel de Controle → Programas → Desinstalar
2. Ou: Menu Iniciar → Print Monitor → Desinstalar
3. Confirme desinstalação
4. Escolha se deseja manter banco de dados
5. Processos e serviços serão parados automaticamente

---

## 📋 CENÁRIOS DE USO

### Cenário 1: Instalação Limpa

```
1. Usuário executa instalador
2. Instalador verifica requisitos
3. Usuário configura servidor/agente
4. Instalador instala arquivos
5. Instalador configura sistema
6. Instalador cria ferramentas
7. Instalação concluída
```

### Cenário 2: Atualização

```
1. Usuário executa instalador
2. Instalador detecta versão anterior
3. Pergunta: "Atualizar de 0.9.0 para 1.0.0?"
4. Usuário confirma
5. Instalador faz backup automático
6. Instalador atualiza arquivos
7. Configurações preservadas
8. Atualização concluída
```

### Cenário 3: Reinstalação

```
1. Usuário executa instalador
2. Instalador detecta versão igual ou superior
3. Pergunta: "Reinstalar versão 1.0.0?"
4. Usuário confirma
5. Instalador faz backup
6. Instalador reinstala arquivos
7. Configurações preservadas
8. Reinstalação concluída
```

### Cenário 4: Desinstalação

```
1. Usuário inicia desinstalação
2. Instalador pergunta confirmação
3. (Servidor) Pergunta se deseja manter banco de dados
4. Instalador para processos
5. Instalador remove arquivos
6. Instalador remove configurações
7. Desinstalação concluída
```

---

## 🔧 TROUBLESHOOTING

### Problema: Instalador não detecta Python

**Solução:**
- Verifique se Python está instalado corretamente
- Verifique se Python está no PATH
- Tente reinstalar Python com opção "Add to PATH"

### Problema: Porta já está em uso

**Solução:**
- Escolha outra porta
- Pare o processo que está usando a porta
- Use `netstat -an | findstr :5002` para verificar

### Problema: Erro durante instalação

**Solução:**
- Verifique o log: `{app}\install.log`
- Verifique informações do sistema: `{app}\system_info.txt`
- Execute diagnóstico: Menu Iniciar → Diagnóstico do Sistema

### Problema: Desinstalação não remove tudo

**Solução:**
- Execute desinstalação novamente
- Remova manualmente: `C:\Program Files\PrintMonitor\`
- Limpe registro: `HKEY_LOCAL_MACHINE\SOFTWARE\PrintMonitor`

---

## 📊 COMPARAÇÃO: ANTES vs DEPOIS

### Antes (Versão Original)
- ❌ Sem detecção de atualização
- ❌ Sem backup automático
- ❌ Validação básica
- ❌ Sem ferramentas de diagnóstico
- ❌ Desinstalação simples

### Depois (Versão Completa)
- ✅ Detecção automática de instalação/atualização
- ✅ Backup automático antes de atualizar
- ✅ Validação completa de requisitos
- ✅ Ferramentas de diagnóstico incluídas
- ✅ Desinstalação inteligente com opções
- ✅ Log detalhado de instalação
- ✅ Coleta de informações do sistema
- ✅ Seleção de componentes
- ✅ Configuração avançada
- ✅ E muito mais!

---

## 🎯 PRÓXIMOS PASSOS

1. ✅ **Testar instalação limpa**
2. ✅ **Testar atualização**
3. ✅ **Testar desinstalação**
4. ⏳ **Criar ícones personalizados** (opcional)
5. ⏳ **Adicionar páginas de informação** (opcional)
6. ⏳ **Criar documentação de usuário**

---

## 📚 DOCUMENTAÇÃO RELACIONADA

- `IDEIAS_MELHORIAS_INSTALADORES.md` - Lista completa de ideias
- `RESUMO_MELHORIAS_INSTALADORES.md` - Resumo das implementações
- `TUTORIAL_CRIAR_SETUP.md` - Como criar os instaladores
- `GUIA_INSTALADORES_SETUP.md` - Guia de uso básico

---

**Última atualização:** 2024-12-08
**Versão:** 1.0.0 Completo

