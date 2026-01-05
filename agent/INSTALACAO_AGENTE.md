# 📦 Guia de Instalação do Agente de Monitoramento

Este guia explica como instalar o agente de monitoramento de impressão em computadores Windows para execução em segundo plano e inicialização automática.

## 🎯 Opções de Instalação

### 1. Instalação Local (Computador Individual)

#### Método A: Script Batch (Recomendado para usuários não técnicos)

1. Navegue até a pasta `agent`
2. Clique com botão direito em `install_agent.bat`
3. Selecione **"Executar como administrador"**
4. Siga as instruções na tela

#### Método B: Script PowerShell (Mais controle)

1. Abra PowerShell como **Administrador**
2. Navegue até a pasta `agent`
3. Execute:
   ```powershell
   .\install_agent.ps1
   ```

**Parâmetros opcionais:**
```powershell
# Especificar caminho do Python
.\install_agent.ps1 -PythonPath "C:\Python39\python.exe"

# Forçar reinstalação
.\install_agent.ps1 -Force
```

### 2. Instalação Remota (Múltiplos Computadores)

Use o script `deploy_agent.ps1` para instalar em vários computadores da rede:

```powershell
# Exemplo: Instalar em 3 computadores
.\deploy_agent.ps1 -Computers @("PC01", "PC02", "PC03") -Username "DOMINIO\admin" -Password "senha123"
```

**Parâmetros:**
- `-Computers`: Array com nomes dos computadores
- `-Username`: Usuário administrativo (formato: DOMINIO\usuario)
- `-Password`: Senha do usuário
- `-AgentPath`: Caminho local dos arquivos do agente (opcional)
- `-PythonPath`: Caminho do Python nos computadores remotos (opcional)
- `-SkipVerification`: Pular verificação de conectividade

**Requisitos para instalação remota:**
- PowerShell Remoting habilitado nos computadores remotos
- Credenciais administrativas
- Firewall permitindo comunicação remota
- Compartilhamento de arquivos habilitado (para cópia dos arquivos)

## 🔧 O que a Instalação Faz

1. **Cria uma Tarefa Agendada do Windows** chamada `PrintMonitorAgent`
2. **Configura para iniciar automaticamente:**
   - Ao iniciar o Windows (mesmo sem usuário logado)
   - Ao fazer login de qualquer usuário
3. **Executa em segundo plano** (sem janela visível)
4. **Reinicia automaticamente** se o processo falhar (até 3 tentativas)

## 📋 Verificação e Gerenciamento

### Verificar Status

```powershell
# Ver informações da tarefa
Get-ScheduledTask -TaskName "PrintMonitorAgent" | Get-ScheduledTaskInfo

# Ver se está rodando
Get-ScheduledTask -TaskName "PrintMonitorAgent"
```

### Iniciar/Parar Manualmente

```powershell
# Iniciar
Start-ScheduledTask -TaskName "PrintMonitorAgent"

# Parar
Stop-ScheduledTask -TaskName "PrintMonitorAgent"
```

### Ver Logs

Os logs são salvos em:
```
agent\logs\agent_output.log
```

Também há logs do Python em:
```
agent\print_monitor.log
```

## 🗑️ Desinstalação

### Local

1. Execute `uninstall_agent.bat` como administrador, OU
2. Execute no PowerShell:
   ```powershell
   .\uninstall_agent.ps1
   ```

### Remota

```powershell
# Desinstalar em múltiplos computadores
$computers = @("PC01", "PC02", "PC03")
$cred = Get-Credential

foreach ($pc in $computers) {
    Invoke-Command -ComputerName $pc -Credential $cred -ScriptBlock {
        Unregister-ScheduledTask -TaskName "PrintMonitorAgent" -Confirm:$false
    }
}
```

## ⚙️ Configuração

O agente usa o arquivo `config.json` na pasta `agent`. Edite antes da instalação se necessário:

```json
{
    "server_url": "http://192.168.1.27:5002/api/print_events",
    "check_interval": 5,
    "retry_interval": 30,
    "max_retries": 3,
    "log_level": "INFO",
    "batch_size": 50,
    "process_all_on_start": true
}
```

## 🔍 Troubleshooting

### Agente não inicia

1. Verifique se Python está instalado e acessível
2. Verifique os logs em `agent\logs\agent_output.log`
3. Verifique se a tarefa está habilitada:
   ```powershell
   Get-ScheduledTask -TaskName "PrintMonitorAgent"
   ```

### Erro de permissão

- Execute os scripts como **Administrador**
- Verifique se o usuário tem permissões para criar tarefas agendadas

### Agente não conecta ao servidor

1. Verifique a URL do servidor em `config.json`
2. Teste conectividade de rede
3. Verifique firewall

### Verificar se está rodando

```powershell
# Ver processos Python relacionados
Get-Process python* | Where-Object { $_.Path -like "*PrintMonitorAgent*" }

# Ver última execução da tarefa
Get-ScheduledTask -TaskName "PrintMonitorAgent" | Get-ScheduledTaskInfo
```

## 📝 Notas Importantes

- O agente roda como **SYSTEM**, então funciona mesmo sem usuário logado
- A tarefa é criada com **prioridade alta** para garantir execução
- Logs são rotacionados automaticamente
- O estado do agente (último evento processado) é salvo em `agent_state.json`

## 🚀 Instalação Rápida para Testes

Para instalação rápida em um computador:

```powershell
# 1. Abra PowerShell como Administrador
# 2. Navegue até a pasta agent
cd C:\caminho\para\agent

# 3. Execute
.\install_agent.ps1

# 4. Quando perguntado, escolha iniciar agora (S)
```

## 📞 Suporte

Em caso de problemas:
1. Verifique os logs em `agent\logs\agent_output.log`
2. Verifique o log do Python em `agent\print_monitor.log`
3. Execute diagnóstico:
   ```powershell
   Get-ScheduledTask -TaskName "PrintMonitorAgent" | Format-List *
   Get-ScheduledTask -TaskName "PrintMonitorAgent" | Get-ScheduledTaskInfo | Format-List *
   ```

