# ✅ Verificação e Instalação do Agente

## 📋 Checklist de Verificação

### 1. Dependências Python
```powershell
# Verificar se Python está instalado
python --version

# Instalar dependências obrigatórias
pip install pywin32 requests

# Dependências opcionais (recomendadas)
pip install wmi pysnmp
```

### 2. Permissões
- ✅ **Executar como Administrador** (recomendado para acesso completo ao Event Log)
- ✅ **Permissões de rede** para acessar o servidor
- ✅ **Permissões de leitura** no Event Log do Windows

### 3. Configuração
Edite o arquivo `config.json` (será criado automaticamente na primeira execução):

```json
{
    "server_url": "http://IP_DO_SERVIDOR:5002/api/print_events",
    "retry_interval": 30,
    "check_interval": 5,
    "max_retries": 3,
    "log_level": "INFO",
    "batch_size": 50,
    "process_all_on_start": true,
    "use_wmi_backup": true,
    "use_spool_interceptor": false,
    "use_snmp_validation": false,
    "snmp_community": "public"
}
```

**IMPORTANTE:** Altere `server_url` para o IP/domínio do seu servidor!

### 4. Testes Iniciais

#### Teste de Conexão com Servidor
```powershell
# O agente testa automaticamente na inicialização
python agente.py
```

#### Teste de Acesso ao Event Log
```powershell
# O agente testa automaticamente na inicialização
# Se falhar, execute como Administrador
```

#### Reset de Estado (se necessário)
```powershell
# Se precisar reprocessar todos os eventos
python agente.py --reset
```

### 5. Execução

#### Modo Manual
```powershell
python agente.py
```

#### Modo Serviço (Recomendado para Produção)
Crie uma tarefa agendada no Windows Task Scheduler:
- **Trigger:** Ao iniciar o sistema
- **Ação:** Executar `pythonw.exe` (sem janela)
- **Argumentos:** `C:\caminho\para\agente.py`
- **Diretório:** `C:\caminho\para\`
- **Executar como:** Conta com permissões de administrador

### 6. Verificação de Funcionamento

#### Logs
Verifique o arquivo `print_monitor.log`:
```powershell
Get-Content print_monitor.log -Tail 50
```

#### Verificar se está enviando eventos
Procure por mensagens como:
- `✅ X eventos enviados: Y inseridos, Z ignorados`
- `🆕 Encontrados X novos eventos`

#### Verificar fila local (se servidor offline)
```powershell
# O agente mantém eventos em event_queue.db quando servidor está offline
# Eles serão reenviados automaticamente quando servidor voltar
```

### 7. Problemas Comuns

#### ❌ "Erro ao conectar ao log de eventos"
**Solução:** Execute como Administrador

#### ❌ "Servidor indisponível"
**Solução:** 
- Verifique se o servidor está rodando
- Verifique firewall/antivírus
- Verifique URL no config.json

#### ❌ "Nenhum evento encontrado"
**Solução:**
- Verifique se há impressoras instaladas
- Verifique se há eventos no Event Log:
  ```powershell
  Get-WinEvent -LogName "Microsoft-Windows-PrintService/Operational" -MaxEvents 10
  ```

#### ❌ "Biblioteca não instalada"
**Solução:**
```powershell
pip install pywin32 requests wmi pysnmp
```

### 8. Estrutura de Arquivos

```
agent/
├── agente.py              # Script principal
├── config.json            # Configuração (criado automaticamente)
├── agent_state.json       # Estado do agente (criado automaticamente)
├── event_queue.db         # Fila de eventos pendentes (criado automaticamente)
└── print_monitor.log      # Log de execução
```

### 9. Monitoramento

#### Verificar Status
```powershell
# Ver últimas linhas do log
Get-Content print_monitor.log -Tail 20

# Verificar se processo está rodando
Get-Process python | Where-Object {$_.Path -like "*agente*"}
```

#### Estatísticas da Fila
O agente mostra automaticamente estatísticas da fila quando há eventos pendentes.

### 10. Atualização

Para atualizar o agente:
1. Pare o agente (se estiver rodando como serviço)
2. Substitua `agente.py` pelo novo arquivo
3. Reinicie o agente

**NOTA:** O estado (`agent_state.json`) é preservado, então não perderá o histórico.

## ✅ Status de Verificação

- [x] Código verificado e corrigido
- [x] Campos compatíveis com servidor
- [x] Tratamento de erros robusto
- [x] Fila persistente implementada
- [x] Retry automático configurado
- [x] Logging completo
- [x] Documentação criada

## 🚀 Pronto para Instalação!

O agente está verificado e pronto para ser instalado nas máquinas da rede.

