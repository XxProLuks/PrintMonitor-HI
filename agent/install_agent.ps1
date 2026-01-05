# Script de Instalação do Agente de Monitoramento de Impressão
# Executa o agente em segundo plano e inicia automaticamente com o Windows

param(
    [string]$PythonPath = "",
    [string]$AgentPath = "",
    [switch]$Force = $false
)

# Verifica se está executando como administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ Este script precisa ser executado como Administrador!" -ForegroundColor Red
    Write-Host "💡 Clique com botão direito e selecione 'Executar como administrador'" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  INSTALAÇÃO DO AGENTE DE MONITORAMENTO" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Determina caminhos
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$agentExe = Join-Path $scriptDir "PrintMonitorAgent.exe"
$agentScript = Join-Path $scriptDir "agente.py"

# Verifica se existe executável compilado (.exe) - PREFERENCIAL
$useExe = $false
$agentPath = $null
$executablePath = $null

if (Test-Path $agentExe) {
    Write-Host "✅ Executável .exe encontrado: $agentExe" -ForegroundColor Green
    Write-Host "   (Não precisa de Python instalado!)" -ForegroundColor Cyan
    $useExe = $true
    $agentPath = $agentExe
    $executablePath = $agentExe
} elseif (Test-Path $agentScript) {
    Write-Host "✅ Script Python encontrado: $agentScript" -ForegroundColor Green
    Write-Host "   (Precisa de Python instalado)" -ForegroundColor Yellow
    
    # Se não especificado, tenta encontrar Python
    if ([string]::IsNullOrEmpty($PythonPath)) {
        # Tenta python primeiro
        $pythonExe = Get-Command python -ErrorAction SilentlyContinue
        if (-not $pythonExe) {
            $pythonExe = Get-Command python3 -ErrorAction SilentlyContinue
        }
        if (-not $pythonExe) {
            # Tenta caminhos comuns
            $commonPaths = @(
                "$env:LOCALAPPDATA\Programs\Python\Python*\python.exe",
                "$env:ProgramFiles\Python*\python.exe",
                "$env:ProgramFiles(x86)\Python*\python.exe",
                "C:\Python*\python.exe",
                "C:\Program Files\Python*\python.exe"
            )
            foreach ($path in $commonPaths) {
                $found = Get-ChildItem -Path $path -ErrorAction SilentlyContinue | Select-Object -First 1
                if ($found) {
                    $pythonExe = $found
                    break
                }
            }
        }
        
        if (-not $pythonExe) {
            Write-Host "❌ Python não encontrado!" -ForegroundColor Red
            Write-Host "💡 Opções:" -ForegroundColor Yellow
            Write-Host "   1. Instale Python: https://www.python.org/downloads/" -ForegroundColor Yellow
            Write-Host "   2. OU compile o agente em .exe: .\build_exe.bat" -ForegroundColor Yellow
            Write-Host "   3. OU especifique o caminho: .\install_agent.ps1 -PythonPath 'C:\Python39\python.exe'" -ForegroundColor Yellow
            pause
            exit 1
        }
        
        $PythonPath = if ($pythonExe -is [System.Management.Automation.CommandInfo]) {
            $pythonExe.Source
        } else {
            $pythonExe.FullName
        }
    }
    
    Write-Host "✅ Python encontrado: $PythonPath" -ForegroundColor Green
    $agentPath = $agentScript
    $executablePath = $PythonPath
} else {
    Write-Host "❌ Nenhum agente encontrado!" -ForegroundColor Red
    Write-Host "   Procurou por:" -ForegroundColor Yellow
    Write-Host "   - $agentExe" -ForegroundColor Yellow
    Write-Host "   - $agentScript" -ForegroundColor Yellow
    Write-Host "" -ForegroundColor Yellow
    Write-Host "💡 Para compilar em .exe: .\build_exe.bat" -ForegroundColor Yellow
    pause
    exit 1
}

# Nome da tarefa
$taskName = "PrintMonitorAgent"

# Verifica se a tarefa já existe
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($existingTask -and -not $Force) {
    Write-Host ""
    Write-Host "⚠️  Tarefa '$taskName' já existe!" -ForegroundColor Yellow
    $response = Read-Host "Deseja reinstalar? (S/N)"
    if ($response -ne "S" -and $response -ne "s") {
        Write-Host "❌ Instalação cancelada" -ForegroundColor Red
        pause
        exit 0
    }
    # Remove tarefa existente
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "🗑️  Tarefa antiga removida" -ForegroundColor Yellow
}

# Cria diretório de logs se não existir
$logDir = Join-Path $scriptDir "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

# Cria script wrapper que redireciona saída para arquivo
$wrapperScript = Join-Path $scriptDir "run_agent_hidden.bat"
$logDirEscaped = $logDir -replace '"', '""'
$scriptDirEscaped = $scriptDir -replace '"', '""'

if ($useExe) {
    # Usa executável .exe diretamente
    $agentPathEscaped = $agentPath -replace '"', '""'
    $wrapperContent = @"
@echo off
cd /d "$scriptDirEscaped"
"$agentPathEscaped" >> "$logDirEscaped\agent_output.log" 2>&1
"@
    Write-Host "✅ Usando executável .exe (sem necessidade de Python)" -ForegroundColor Green
} else {
    # Usa Python com script .py
    $pythonPathEscaped = $executablePath -replace '"', '""'
    $agentPathEscaped = $agentPath -replace '"', '""'
    $wrapperContent = @"
@echo off
cd /d "$scriptDirEscaped"
"$pythonPathEscaped" "$agentPathEscaped" >> "$logDirEscaped\agent_output.log" 2>&1
"@
    Write-Host "✅ Usando Python com script .py" -ForegroundColor Green
}

Set-Content -Path $wrapperScript -Value $wrapperContent -Encoding ASCII
Write-Host "✅ Script wrapper criado" -ForegroundColor Green

# Cria ação da tarefa
$action = New-ScheduledTaskAction -Execute $wrapperScript -WorkingDirectory $scriptDir

# Cria trigger: ao iniciar o sistema
$trigger = New-ScheduledTaskTrigger -AtStartup

# Cria trigger adicional: ao fazer login (caso o sistema já esteja ligado)
$trigger2 = New-ScheduledTaskTrigger -AtLogOn

# Configurações da tarefa
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable:$false `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

# Cria principal (executa como SYSTEM para rodar mesmo sem usuário logado)
$principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

# Registra a tarefa
try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger @($trigger, $trigger2) `
        -Settings $settings `
        -Principal $principal `
        -Description "Agente de Monitoramento de Impressão - Executa em segundo plano" `
        -Force | Out-Null
    
    Write-Host ""
    Write-Host "✅ Tarefa agendada criada com sucesso!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Detalhes da instalação:" -ForegroundColor Cyan
    Write-Host "   Nome da tarefa: $taskName" -ForegroundColor White
    if ($useExe) {
        Write-Host "   Tipo: Executável .exe (sem Python necessário)" -ForegroundColor White
        Write-Host "   Agente: $agentPath" -ForegroundColor White
    } else {
        Write-Host "   Tipo: Script Python (.py)" -ForegroundColor White
        Write-Host "   Python: $executablePath" -ForegroundColor White
        Write-Host "   Agente: $agentPath" -ForegroundColor White
    }
    Write-Host "   Logs: $logDir\agent_output.log" -ForegroundColor White
    Write-Host ""
    
    # Pergunta se deseja iniciar agora
    $startNow = Read-Host "Deseja iniciar o agente agora? (S/N)"
    if ($startNow -eq "S" -or $startNow -eq "s") {
        Start-ScheduledTask -TaskName $taskName
        Write-Host "✅ Agente iniciado!" -ForegroundColor Green
        Start-Sleep -Seconds 2
        
        # Verifica se está rodando
        $taskInfo = Get-ScheduledTaskInfo -TaskName $taskName
        if ($taskInfo.LastRunTime) {
            Write-Host "✅ Agente está em execução (última execução: $($taskInfo.LastRunTime))" -ForegroundColor Green
        }
    }
    
    Write-Host ""
    Write-Host "📝 Comandos úteis:" -ForegroundColor Cyan
    Write-Host "   Ver status: Get-ScheduledTask -TaskName '$taskName' | Get-ScheduledTaskInfo" -ForegroundColor Gray
    Write-Host "   Iniciar: Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor Gray
    Write-Host "   Parar: Stop-ScheduledTask -TaskName '$taskName'" -ForegroundColor Gray
    Write-Host "   Desinstalar: .\uninstall_agent.ps1" -ForegroundColor Gray
    Write-Host ""
    
} catch {
    Write-Host "❌ Erro ao criar tarefa: $_" -ForegroundColor Red
    pause
    exit 1
}

Write-Host "✅ Instalação concluída!" -ForegroundColor Green
pause

