# Script para verificar status do agente em um ou múltiplos computadores

param(
    [Parameter(Mandatory=$false)]
    [string[]]$Computers = @("localhost"),
    
    [Parameter(Mandatory=$false)]
    [string]$Username = "",
    
    [Parameter(Mandatory=$false)]
    [string]$Password = "",
    
    [switch]$Remote = $false
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  VERIFICAÇÃO DE STATUS DO AGENTE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$taskName = "PrintMonitorAgent"

if ($Remote -and $Computers.Count -gt 0 -and $Computers[0] -ne "localhost") {
    # Verificação remota
    
    if ([string]::IsNullOrEmpty($Username)) {
        $Username = Read-Host "Digite o usuário administrativo"
    }
    
    if ([string]::IsNullOrEmpty($Password)) {
        $securePassword = Read-Host "Digite a senha" -AsSecureString
        $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
        $Password = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
    }
    
    $securePassword = ConvertTo-SecureString $Password -AsPlainText -Force
    $credential = New-Object System.Management.Automation.PSCredential($Username, $securePassword)
    
    foreach ($computer in $Computers) {
        Write-Host ""
        Write-Host "🖥️  Computador: $computer" -ForegroundColor Cyan
        Write-Host "────────────────────────────────────────" -ForegroundColor Gray
        
        try {
            $taskInfo = Invoke-Command -ComputerName $computer -Credential $credential -ScriptBlock {
                param($taskName)
                $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
                if ($task) {
                    $info = Get-ScheduledTaskInfo -TaskName $taskName
                    $process = Get-Process python* -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*PrintMonitorAgent*" }
                    
                    return @{
                        Task = $task
                        Info = $info
                        Process = $process
                        Exists = $true
                    }
                } else {
                    return @{ Exists = $false }
                }
            } -ArgumentList $taskName
            
            if ($taskInfo.Exists) {
                Write-Host "✅ Tarefa encontrada" -ForegroundColor Green
                Write-Host "   Estado: $($taskInfo.Task.State)" -ForegroundColor White
                Write-Host "   Última execução: $($taskInfo.Info.LastRunTime)" -ForegroundColor White
                Write-Host "   Próxima execução: $($taskInfo.Info.NextRunTime)" -ForegroundColor White
                Write-Host "   Último resultado: $($taskInfo.Info.LastTaskResult)" -ForegroundColor White
                
                if ($taskInfo.Process) {
                    Write-Host "✅ Processo Python em execução (PID: $($taskInfo.Process.Id))" -ForegroundColor Green
                } else {
                    Write-Host "⚠️  Processo Python não encontrado" -ForegroundColor Yellow
                }
            } else {
                Write-Host "❌ Tarefa não encontrada" -ForegroundColor Red
            }
            
        } catch {
            Write-Host "❌ Erro ao verificar: $_" -ForegroundColor Red
        }
    }
    
} else {
    # Verificação local
    
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    
    if (-not $task) {
        Write-Host "❌ Tarefa '$taskName' não encontrada" -ForegroundColor Red
        Write-Host "💡 Execute install_agent.ps1 para instalar" -ForegroundColor Yellow
        exit 1
    }
    
    Write-Host "✅ Tarefa encontrada: $taskName" -ForegroundColor Green
    Write-Host ""
    
    $taskInfo = Get-ScheduledTaskInfo -TaskName $taskName
    
    Write-Host "📋 Informações da Tarefa:" -ForegroundColor Cyan
    Write-Host "   Nome: $($task.TaskName)" -ForegroundColor White
    Write-Host "   Estado: $($task.State)" -ForegroundColor White
    Write-Host "   Última execução: $($taskInfo.LastRunTime)" -ForegroundColor White
    Write-Host "   Próxima execução: $($taskInfo.NextRunTime)" -ForegroundColor White
    Write-Host "   Último resultado: $($taskInfo.LastTaskResult)" -ForegroundColor White
    Write-Host "   Número de execuções: $($taskInfo.NumberOfMissedRuns)" -ForegroundColor White
    Write-Host ""
    
    # Verifica processo
    $processes = Get-Process python* -ErrorAction SilentlyContinue | Where-Object { 
        $_.Path -like "*PrintMonitorAgent*" -or 
        $_.CommandLine -like "*agente.py*" 
    }
    
    if ($processes) {
        Write-Host "✅ Processo Python em execução:" -ForegroundColor Green
        foreach ($proc in $processes) {
            Write-Host "   PID: $($proc.Id) | CPU: $($proc.CPU) | Memória: $([math]::Round($proc.WS/1MB, 2)) MB" -ForegroundColor White
        }
    } else {
        Write-Host "⚠️  Processo Python não encontrado" -ForegroundColor Yellow
        Write-Host "💡 A tarefa pode não estar executando ou o processo terminou" -ForegroundColor Yellow
    }
    
    Write-Host ""
    
    # Verifica logs
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $logFile = Join-Path $scriptDir "logs\agent_output.log"
    $pythonLog = Join-Path $scriptDir "print_monitor.log"
    
    Write-Host "📝 Logs:" -ForegroundColor Cyan
    if (Test-Path $logFile) {
        $logSize = (Get-Item $logFile).Length / 1KB
        $logModified = (Get-Item $logFile).LastWriteTime
        Write-Host "   agent_output.log: $([math]::Round($logSize, 2)) KB (modificado: $logModified)" -ForegroundColor White
    } else {
        Write-Host "   agent_output.log: Não encontrado" -ForegroundColor Yellow
    }
    
    if (Test-Path $pythonLog) {
        $logSize = (Get-Item $pythonLog).Length / 1KB
        $logModified = (Get-Item $pythonLog).LastWriteTime
        Write-Host "   print_monitor.log: $([math]::Round($logSize, 2)) KB (modificado: $logModified)" -ForegroundColor White
    } else {
        Write-Host "   print_monitor.log: Não encontrado" -ForegroundColor Yellow
    }
    
    Write-Host ""
    
    # Sugestões
    if ($task.State -ne "Running") {
        Write-Host "💡 Sugestão: A tarefa não está em execução. Execute:" -ForegroundColor Yellow
        Write-Host "   Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor Gray
    }
    
    if ($taskInfo.LastTaskResult -ne 0) {
        Write-Host "⚠️  Última execução retornou erro (código: $($taskInfo.LastTaskResult))" -ForegroundColor Yellow
        Write-Host "💡 Verifique os logs para mais detalhes" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "✅ Verificação concluída" -ForegroundColor Green

