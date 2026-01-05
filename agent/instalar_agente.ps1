# ============================================================================
# INSTALADOR DO AGENTE DE MONITORAMENTO
# ============================================================================
# Instala e configura o agente em um computador Windows
# ============================================================================

param(
    [Parameter(Mandatory=$false)]
    [string]$ServerURL = "http://192.168.1.27:5002/api/print_events",
    
    [Parameter(Mandatory=$false)]
    [string]$PythonPath = "",
    
    [Parameter(Mandatory=$false)]
    [string]$InstallPath = "C:\PrintMonitorAgent",
    
    [switch]$SkipDependencies = $false,
    [switch]$Force = $false,
    [switch]$CreateTask = $true
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  INSTALADOR DO AGENTE" -ForegroundColor Cyan
Write-Host "  Monitoramento de Impressão" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verifica se está executando como administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ Este script precisa ser executado como Administrador!" -ForegroundColor Red
    Write-Host "💡 Clique com botão direito e selecione 'Executar como administrador'" -ForegroundColor Yellow
    pause
    exit 1
}

# Determina caminhos
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$agentePy = Join-Path $scriptDir "agente.py"
$requirementsFile = Join-Path $scriptDir "requirements.txt"

# Verifica se agente.py existe
if (-not (Test-Path $agentePy)) {
    Write-Host "❌ Arquivo agente.py não encontrado em: $scriptDir" -ForegroundColor Red
    exit 1
}

Write-Host "📁 Diretório do agente: $scriptDir" -ForegroundColor Cyan
Write-Host "📁 Diretório de instalação: $InstallPath" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# 1. VERIFICA PYTHON
# ============================================================================

Write-Host "🔍 Verificando Python..." -ForegroundColor Yellow

if ([string]::IsNullOrEmpty($PythonPath)) {
    $pythonExe = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonExe) {
        $pythonExe = Get-Command python3 -ErrorAction SilentlyContinue
    }
    
    if ($pythonExe) {
        $PythonPath = $pythonExe.Source
    } else {
        Write-Host "❌ Python não encontrado!" -ForegroundColor Red
        Write-Host "💡 Instale Python 3.8 ou superior de: https://www.python.org/downloads/" -ForegroundColor Yellow
        Write-Host "💡 Certifique-se de marcar 'Add Python to PATH' durante a instalação" -ForegroundColor Yellow
        pause
        exit 1
    }
}

$pythonVersion = & $PythonPath --version 2>&1
Write-Host "✅ Python encontrado: $pythonVersion" -ForegroundColor Green
Write-Host "   Caminho: $PythonPath" -ForegroundColor Gray
Write-Host ""

# Verifica versão mínima (3.8)
$versionMatch = $pythonVersion -match "Python (\d+)\.(\d+)"
if ($versionMatch) {
    $major = [int]$matches[1]
    $minor = [int]$matches[2]
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 8)) {
        Write-Host "❌ Python 3.8 ou superior é necessário!" -ForegroundColor Red
        Write-Host "   Versão atual: $pythonVersion" -ForegroundColor Yellow
        pause
        exit 1
    }
}

# ============================================================================
# 2. COPIA ARQUIVOS
# ============================================================================

Write-Host "📦 Copiando arquivos do agente..." -ForegroundColor Yellow

if (Test-Path $InstallPath) {
    if ($Force) {
        Write-Host "   Removendo instalação anterior..." -ForegroundColor Gray
        Remove-Item $InstallPath -Recurse -Force
    } else {
        Write-Host "⚠️  Diretório de instalação já existe: $InstallPath" -ForegroundColor Yellow
        $overwrite = Read-Host "   Deseja sobrescrever? (S/N)"
        if ($overwrite -ne "S" -and $overwrite -ne "s") {
            Write-Host "❌ Instalação cancelada" -ForegroundColor Red
            exit 0
        }
        Remove-Item $InstallPath -Recurse -Force
    }
}

# Cria diretório de instalação
New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $InstallPath "logs") -Force | Out-Null

# Copia arquivos
Write-Host "   Copiando arquivos..." -ForegroundColor Gray
$filesToCopy = @(
    "agente.py",
    "requirements.txt",
    "config.json.example"
)

foreach ($file in $filesToCopy) {
    $source = Join-Path $scriptDir $file
    if (Test-Path $source) {
        Copy-Item $source -Destination $InstallPath -Force
        Write-Host "   ✅ $file" -ForegroundColor Gray
    }
}

# Copia config.json se existir
$configSource = Join-Path $scriptDir "config.json"
if (Test-Path $configSource) {
    Copy-Item $configSource -Destination $InstallPath -Force
    Write-Host "   ✅ config.json (mantido)" -ForegroundColor Gray
} else {
    # Cria config.json a partir do exemplo
    $configExample = Join-Path $InstallPath "config.json.example"
    if (Test-Path $configExample) {
        $configContent = Get-Content $configExample -Raw
        $configContent = $configContent -replace '"server_url":\s*"[^"]*"', "`"server_url`": `"$ServerURL`""
        $configContent | Out-File -FilePath (Join-Path $InstallPath "config.json") -Encoding UTF8 -Force
        Write-Host "   ✅ config.json criado" -ForegroundColor Gray
    }
}

Write-Host "✅ Arquivos copiados!" -ForegroundColor Green
Write-Host ""

# ============================================================================
# 3. INSTALA DEPENDÊNCIAS
# ============================================================================

if (-not $SkipDependencies) {
    Write-Host "📦 Instalando dependências..." -ForegroundColor Yellow
    
    if (Test-Path $requirementsFile) {
        Write-Host "   Usando: $requirementsFile" -ForegroundColor Gray
        
        # Atualiza pip primeiro
        Write-Host "   Atualizando pip..." -ForegroundColor Gray
        & $PythonPath -m pip install --upgrade pip --quiet
        
        # Instala dependências
        Write-Host "   Instalando pacotes (isso pode demorar alguns minutos)..." -ForegroundColor Gray
        & $PythonPath -m pip install -r $requirementsFile
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Erro ao instalar dependências!" -ForegroundColor Red
            Write-Host "💡 Tente executar manualmente: pip install -r requirements.txt" -ForegroundColor Yellow
            pause
            exit 1
        }
        
        Write-Host "✅ Dependências instaladas com sucesso!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Arquivo requirements.txt não encontrado" -ForegroundColor Yellow
        Write-Host "   Instalando dependências básicas..." -ForegroundColor Gray
        
        $basicDeps = @(
            "pywin32>=300",
            "requests>=2.25.0"
        )
        
        foreach ($dep in $basicDeps) {
            Write-Host "   Instalando $dep..." -ForegroundColor Gray
            & $PythonPath -m pip install $dep --quiet
        }
        
        Write-Host "✅ Dependências básicas instaladas!" -ForegroundColor Green
    }
    Write-Host ""
}

# ============================================================================
# 4. CRIA TAREFA AGENDADA
# ============================================================================

if ($CreateTask) {
    Write-Host "⏰ Criando Tarefa Agendada..." -ForegroundColor Yellow
    
    $taskName = "PrintMonitorAgent"
    $taskDescription = "Agente de Monitoramento de Impressão - Inicia automaticamente com o Windows"
    
    # Remove tarefa existente se houver
    $existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        if ($Force) {
            Write-Host "   Removendo tarefa existente..." -ForegroundColor Gray
            Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
        } else {
            Write-Host "⚠️  Tarefa '$taskName' já existe!" -ForegroundColor Yellow
            $overwrite = Read-Host "   Deseja substituir? (S/N)"
            if ($overwrite -eq "S" -or $overwrite -eq "s") {
                Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
            } else {
                $CreateTask = $false
            }
        }
    }
    
    if ($CreateTask) {
        # Cria diretório de logs se não existir
        $logDir = Join-Path $InstallPath "logs"
        if (-not (Test-Path $logDir)) {
            New-Item -ItemType Directory -Path $logDir -Force | Out-Null
        }
        
        # Cria script wrapper para executar em segundo plano
        $wrapperScript = Join-Path $InstallPath "run_agent_hidden.bat"
        $pythonPathEscaped = $PythonPath -replace '"', '""'
        $agentPathEscaped = "$InstallPath\agente.py" -replace '"', '""'
        $logDirEscaped = $logDir -replace '"', '""'
        
        $wrapperContent = @"
@echo off
REM Script wrapper para executar agente em segundo plano
cd /d "$InstallPath"
"$pythonPathEscaped" "$agentPathEscaped" >> "$logDirEscaped\agent_output.log" 2>&1
"@
        
        Set-Content -Path $wrapperScript -Value $wrapperContent -Encoding ASCII -Force
        Write-Host "   ✅ Script wrapper criado" -ForegroundColor Gray
        
        # Cria ação (executar script wrapper)
        $action = New-ScheduledTaskAction `
            -Execute $wrapperScript `
            -WorkingDirectory $InstallPath
        
        # Cria trigger 1: Ao iniciar sistema (mesmo sem login)
        $triggerStartup = New-ScheduledTaskTrigger -AtStartup
        $triggerStartup.Delay = "PT1M"  # Delay de 1 minuto para aguardar rede
        
        # Cria trigger 2: Ao fazer login (caso sistema já esteja ligado)
        $triggerLogon = New-ScheduledTaskTrigger -AtLogOn
        
        # Configurações da tarefa
        $settings = New-ScheduledTaskSettingsSet `
            -AllowStartIfOnBatteries `
            -DontStopIfGoingOnBatteries `
            -StartWhenAvailable `
            -RunOnlyIfNetworkAvailable:$false `  # Executa mesmo sem rede (tentará reconectar)
            -RestartCount 3 `
            -RestartInterval (New-TimeSpan -Minutes 1) `
            -ExecutionTimeLimit (New-TimeSpan -Hours 0) `  # Sem limite de tempo
            -MultipleInstances IgnoreNew  # Ignora se já estiver rodando
        
        # Cria principal (executar como SYSTEM para rodar mesmo sem usuário logado)
        # Isso garante que o agente rode mesmo quando ninguém está logado
        $principal = New-ScheduledTaskPrincipal `
            -UserId "SYSTEM" `
            -LogonType ServiceAccount `
            -RunLevel Highest
        
        # Registra tarefa
        try {
            Register-ScheduledTask `
                -TaskName $taskName `
                -Action $action `
                -Trigger @($triggerStartup, $triggerLogon) `
                -Settings $settings `
                -Principal $principal `
                -Description $taskDescription `
                -Force | Out-Null
            
            Write-Host "✅ Tarefa agendada criada: $taskName" -ForegroundColor Green
            Write-Host "   - Inicia ao iniciar Windows (mesmo sem login)" -ForegroundColor Gray
            Write-Host "   - Inicia ao fazer login de qualquer usuário" -ForegroundColor Gray
            Write-Host "   - Executa como SYSTEM (máxima prioridade)" -ForegroundColor Gray
            Write-Host "   - Reinicia automaticamente em caso de falha (até 3x)" -ForegroundColor Gray
            Write-Host "   - Logs em: $logDir\agent_output.log" -ForegroundColor Gray
            
            # Tenta iniciar a tarefa imediatamente
            try {
                Start-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
                Write-Host "   - Tarefa iniciada automaticamente" -ForegroundColor Gray
            } catch {
                Write-Host "   - Tarefa criada (será iniciada no próximo boot/login)" -ForegroundColor Gray
            }
        } catch {
            Write-Host "⚠️  Erro ao criar tarefa: $_" -ForegroundColor Yellow
            Write-Host "   Tentando criar como usuário atual..." -ForegroundColor Yellow
            
            # Fallback: cria como usuário atual
            $principalFallback = New-ScheduledTaskPrincipal `
                -UserId "$env:USERDOMAIN\$env:USERNAME" `
                -LogonType Interactive `
                -RunLevel Highest
            
            Register-ScheduledTask `
                -TaskName $taskName `
                -Action $action `
                -Trigger @($triggerLogon) `  # Só ao fazer login neste caso
                -Settings $settings `
                -Principal $principalFallback `
                -Description $taskDescription `
                -Force | Out-Null
            
            Write-Host "✅ Tarefa criada como usuário atual (inicia apenas ao fazer login)" -ForegroundColor Green
        }
    }
    Write-Host ""
}

# ============================================================================
# 5. TESTA CONEXÃO COM SERVIDOR
# ============================================================================

Write-Host "🔗 Testando conexão com servidor..." -ForegroundColor Yellow

try {
    $baseUrl = $ServerURL -replace "/api/print_events$", ""
    $response = Invoke-WebRequest -Uri $baseUrl -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host "✅ Servidor acessível: $baseUrl" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Não foi possível conectar ao servidor: $baseUrl" -ForegroundColor Yellow
    Write-Host "   Verifique se o servidor está rodando e acessível" -ForegroundColor Yellow
    Write-Host "   O agente tentará reconectar automaticamente" -ForegroundColor Gray
}
Write-Host ""

# ============================================================================
# 6. RESUMO E PRÓXIMOS PASSOS
# ============================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  INSTALAÇÃO CONCLUÍDA!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 RESUMO:" -ForegroundColor Cyan
Write-Host "   ✅ Python verificado" -ForegroundColor Green
Write-Host "   ✅ Arquivos copiados para: $InstallPath" -ForegroundColor Green
Write-Host "   ✅ Dependências instaladas" -ForegroundColor Green
if ($CreateTask) {
    Write-Host "   ✅ Tarefa agendada criada" -ForegroundColor Green
}
Write-Host ""
Write-Host "🚀 PRÓXIMOS PASSOS:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Testar o agente manualmente:" -ForegroundColor Yellow
Write-Host "   cd $InstallPath" -ForegroundColor Gray
Write-Host "   python agente.py" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Verificar se está funcionando:" -ForegroundColor Yellow
Write-Host "   - O agente iniciará automaticamente no próximo login" -ForegroundColor Gray
Write-Host "   - Verifique os logs em: $InstallPath\logs\" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Configurar servidor (se necessário):" -ForegroundColor Yellow
Write-Host "   Edite: $InstallPath\config.json" -ForegroundColor Gray
Write-Host ""
if ($CreateTask) {
    Write-Host "4. Gerenciar tarefa agendada:" -ForegroundColor Yellow
    Write-Host "   - Ver: Get-ScheduledTask -TaskName PrintMonitorAgent" -ForegroundColor Gray
    Write-Host "   - Iniciar: Start-ScheduledTask -TaskName PrintMonitorAgent" -ForegroundColor Gray
    Write-Host "   - Parar: Stop-ScheduledTask -TaskName PrintMonitorAgent" -ForegroundColor Gray
    Write-Host ""
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

pause

