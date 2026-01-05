# Script de Desinstalação do Agente de Monitoramento de Impressão

# Verifica se está executando como administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ Este script precisa ser executado como Administrador!" -ForegroundColor Red
    Write-Host "💡 Clique com botão direito e selecione 'Executar como administrador'" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DESINSTALAÇÃO DO AGENTE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$taskName = "PrintMonitorAgent"

# Verifica se a tarefa existe
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if (-not $existingTask) {
    Write-Host "ℹ️  Tarefa '$taskName' não encontrada. Nada para desinstalar." -ForegroundColor Yellow
    pause
    exit 0
}

Write-Host "📋 Tarefa encontrada: $taskName" -ForegroundColor Cyan

# Para a tarefa se estiver rodando
try {
    Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    Write-Host "⏹️  Tarefa parada" -ForegroundColor Yellow
} catch {
    Write-Host "⚠️  Não foi possível parar a tarefa (pode não estar rodando)" -ForegroundColor Yellow
}

# Remove a tarefa
try {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "✅ Tarefa removida com sucesso!" -ForegroundColor Green
} catch {
    Write-Host "❌ Erro ao remover tarefa: $_" -ForegroundColor Red
    pause
    exit 1
}

# Pergunta se deseja remover logs e arquivos
$removeFiles = Read-Host "Deseja remover logs e arquivos de configuração? (S/N)"
if ($removeFiles -eq "S" -or $removeFiles -eq "s") {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $logDir = Join-Path $scriptDir "logs"
    $wrapperScript = Join-Path $scriptDir "run_agent_hidden.bat"
    $stateFile = Join-Path $scriptDir "agent_state.json"
    
    if (Test-Path $logDir) {
        Remove-Item -Path $logDir -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "🗑️  Logs removidos" -ForegroundColor Yellow
    }
    
    if (Test-Path $wrapperScript) {
        Remove-Item -Path $wrapperScript -Force -ErrorAction SilentlyContinue
        Write-Host "🗑️  Script wrapper removido" -ForegroundColor Yellow
    }
    
    if (Test-Path $stateFile) {
        Remove-Item -Path $stateFile -Force -ErrorAction SilentlyContinue
        Write-Host "🗑️  Estado do agente removido" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "✅ Desinstalação concluída!" -ForegroundColor Green
pause

