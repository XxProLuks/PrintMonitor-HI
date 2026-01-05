# ============================================================================
# VERIFICAR INÍCIO AUTOMÁTICO DO AGENTE
# ============================================================================
# Verifica se o agente está configurado para iniciar automaticamente
# ============================================================================

$taskName = "PrintMonitorAgent"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  VERIFICAÇÃO DE INÍCIO AUTOMÁTICO" -ForegroundColor Cyan
Write-Host "  Print Monitor Agent" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verifica se a tarefa existe
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if (-not $task) {
    Write-Host "❌ Tarefa agendada '$taskName' NÃO encontrada!" -ForegroundColor Red
    Write-Host ""
    Write-Host "💡 Para criar a tarefa, execute:" -ForegroundColor Yellow
    Write-Host "   .\instalar_agente.ps1 -CreateTask" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

Write-Host "✅ Tarefa agendada encontrada: $taskName" -ForegroundColor Green
Write-Host ""

# Informações da tarefa
$taskInfo = Get-ScheduledTaskInfo -TaskName $taskName
$taskDetails = Get-ScheduledTask -TaskName $taskName

Write-Host "📋 INFORMAÇÕES DA TAREFA:" -ForegroundColor Cyan
Write-Host "   Estado: $($taskDetails.State)" -ForegroundColor White
Write-Host "   Habilitada: $($taskDetails.Enabled)" -ForegroundColor White
Write-Host "   Descrição: $($taskDetails.Description)" -ForegroundColor White
Write-Host ""

# Triggers (quando executa)
Write-Host "⏰ TRIGGERS (Quando executa):" -ForegroundColor Cyan
$triggers = $taskDetails.Triggers
if ($triggers.Count -eq 0) {
    Write-Host "   ⚠️  Nenhum trigger configurado!" -ForegroundColor Yellow
} else {
    foreach ($trigger in $triggers) {
        $triggerType = $trigger.CimClass.CimClassName
        Write-Host "   - Tipo: $triggerType" -ForegroundColor White
        
        if ($triggerType -like "*StartupTrigger*") {
            Write-Host "     → Inicia ao iniciar o Windows" -ForegroundColor Gray
            if ($trigger.Delay) {
                Write-Host "     → Delay: $($trigger.Delay)" -ForegroundColor Gray
            }
        } elseif ($triggerType -like "*LogonTrigger*") {
            Write-Host "     → Inicia ao fazer login" -ForegroundColor Gray
        }
    }
}
Write-Host ""

# Principal (quem executa)
Write-Host "👤 PRINCIPAL (Quem executa):" -ForegroundColor Cyan
$principal = $taskDetails.Principal
Write-Host "   Usuário: $($principal.UserId)" -ForegroundColor White
Write-Host "   Tipo de Login: $($principal.LogonType)" -ForegroundColor White
Write-Host "   Nível de Execução: $($principal.RunLevel)" -ForegroundColor White
Write-Host ""

# Ação (o que executa)
Write-Host "⚙️  AÇÃO (O que executa):" -ForegroundColor Cyan
$action = $taskDetails.Actions[0]
Write-Host "   Executável: $($action.Execute)" -ForegroundColor White
Write-Host "   Argumentos: $($action.Arguments)" -ForegroundColor White
Write-Host "   Diretório: $($action.WorkingDirectory)" -ForegroundColor White
Write-Host ""

# Configurações
Write-Host "⚙️  CONFIGURAÇÕES:" -ForegroundColor Cyan
$settings = $taskDetails.Settings
Write-Host "   Iniciar quando disponível: $($settings.StartWhenAvailable)" -ForegroundColor White
Write-Host "   Permitir iniciar em bateria: $($settings.AllowStartIfOnBatteries)" -ForegroundColor White
Write-Host "   Não parar ao ir para bateria: $($settings.DontStopIfGoingOnBatteries)" -ForegroundColor White
Write-Host "   Reiniciar em caso de falha: $($settings.RestartCount) vezes" -ForegroundColor White
if ($settings.RestartInterval) {
    Write-Host "   Intervalo de reinício: $($settings.RestartInterval)" -ForegroundColor White
}
Write-Host ""

# Status de execução
Write-Host "📊 STATUS DE EXECUÇÃO:" -ForegroundColor Cyan
if ($taskInfo.LastRunTime) {
    Write-Host "   Última execução: $($taskInfo.LastRunTime)" -ForegroundColor White
} else {
    Write-Host "   ⚠️  Nunca foi executada" -ForegroundColor Yellow
}

if ($taskInfo.LastTaskResult -eq 0) {
    Write-Host "   Último resultado: ✅ Sucesso (0)" -ForegroundColor Green
} elseif ($taskInfo.LastTaskResult) {
    Write-Host "   Último resultado: ❌ Erro ($($taskInfo.LastTaskResult))" -ForegroundColor Red
}

if ($taskInfo.NextRunTime) {
    Write-Host "   Próxima execução: $($taskInfo.NextRunTime)" -ForegroundColor White
} else {
    Write-Host "   Próxima execução: Não agendada" -ForegroundColor Gray
}
Write-Host ""

# Verifica se o processo está rodando
Write-Host "🔍 PROCESSO:" -ForegroundColor Cyan
$processes = Get-Process python* -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*PrintMonitorAgent*" -or
    $_.CommandLine -like "*agente.py*"
}

if ($processes) {
    Write-Host "   ✅ Agente está em execução!" -ForegroundColor Green
    foreach ($proc in $processes) {
        Write-Host "   - PID: $($proc.Id), CPU: $([math]::Round($proc.CPU, 2))s, Memória: $([math]::Round($proc.WS / 1MB, 2)) MB" -ForegroundColor White
    }
} else {
    Write-Host "   ⚠️  Agente NÃO está em execução" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "💡 Para iniciar manualmente:" -ForegroundColor Yellow
    Write-Host "   Start-ScheduledTask -TaskName $taskName" -ForegroundColor Gray
}
Write-Host ""

# Verifica logs
$logFile = Join-Path $action.WorkingDirectory "logs\agent_output.log"
if (Test-Path $logFile) {
    Write-Host "📝 LOGS:" -ForegroundColor Cyan
    $logSize = (Get-Item $logFile).Length / 1KB
    Write-Host "   Arquivo: $logFile" -ForegroundColor White
    Write-Host "   Tamanho: $([math]::Round($logSize, 2)) KB" -ForegroundColor White
    
    $lastLines = Get-Content $logFile -Tail 3 -ErrorAction SilentlyContinue
    if ($lastLines) {
        Write-Host "   Últimas linhas:" -ForegroundColor White
        foreach ($line in $lastLines) {
            Write-Host "   $line" -ForegroundColor Gray
        }
    }
} else {
    Write-Host "📝 LOGS:" -ForegroundColor Cyan
    Write-Host "   ⚠️  Arquivo de log não encontrado: $logFile" -ForegroundColor Yellow
}
Write-Host ""

# Resumo
Write-Host "========================================" -ForegroundColor Cyan
if ($taskDetails.State -eq "Running" -or $processes) {
    Write-Host "  ✅ AGENTE CONFIGURADO E RODANDO" -ForegroundColor Green
} elseif ($taskDetails.Enabled) {
    Write-Host "  ⚠️  AGENTE CONFIGURADO MAS NÃO RODANDO" -ForegroundColor Yellow
} else {
    Write-Host "  ❌ AGENTE DESABILITADO" -ForegroundColor Red
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Comandos úteis
Write-Host "💡 COMANDOS ÚTEIS:" -ForegroundColor Cyan
Write-Host "   Iniciar: Start-ScheduledTask -TaskName $taskName" -ForegroundColor Gray
Write-Host "   Parar: Stop-ScheduledTask -TaskName $taskName" -ForegroundColor Gray
Write-Host "   Habilitar: Enable-ScheduledTask -TaskName $taskName" -ForegroundColor Gray
Write-Host "   Desabilitar: Disable-ScheduledTask -TaskName $taskName" -ForegroundColor Gray
Write-Host "   Ver detalhes: Get-ScheduledTask -TaskName $taskName | Format-List *" -ForegroundColor Gray
Write-Host ""

