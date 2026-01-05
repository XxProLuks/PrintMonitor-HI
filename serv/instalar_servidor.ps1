# ============================================================================
# INSTALADOR DO SERVIDOR DE MONITORAMENTO DE IMPRESSÃO
# ============================================================================
# Instala e configura o servidor Flask com todas as dependências
# ============================================================================

param(
    [Parameter(Mandatory=$false)]
    [int]$Port = 5002,
    
    [Parameter(Mandatory=$false)]
    [string]$Host = "0.0.0.0",
    
    [Parameter(Mandatory=$false)]
    [string]$PythonPath = "",
    
    [switch]$InstallService = $false,
    [switch]$ConfigureFirewall = $false,
    [switch]$SkipDependencies = $false,
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  INSTALADOR DO SERVIDOR" -ForegroundColor Cyan
Write-Host "  Sistema de Monitoramento de Impressão" -ForegroundColor Cyan
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
$servidorPy = Join-Path $scriptDir "servidor.py"
$requirementsFile = Join-Path (Split-Path -Parent $scriptDir) "requirements.txt"

# Verifica se servidor.py existe
if (-not (Test-Path $servidorPy)) {
    Write-Host "❌ Arquivo servidor.py não encontrado em: $scriptDir" -ForegroundColor Red
    exit 1
}

Write-Host "📁 Diretório do servidor: $scriptDir" -ForegroundColor Cyan
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
# 2. INSTALA DEPENDÊNCIAS
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
        Write-Host "⚠️  Arquivo requirements.txt não encontrado em: $requirementsFile" -ForegroundColor Yellow
        Write-Host "   Instalando dependências básicas..." -ForegroundColor Gray
        
        $basicDeps = @(
            "Flask>=2.3.0",
            "pandas>=2.0.0",
            "openpyxl>=3.1.0",
            "python-dotenv>=1.0.0",
            "werkzeug>=2.3.0",
            "flask-compress>=1.13",
            "flask-limiter>=3.5.0",
            "flask-wtf>=1.2.0",
            "WTForms>=3.1.0",
            "reportlab>=4.0.0",
            "flask-socketio>=5.3.0",
            "requests>=2.31.0"
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
# 3. CRIA BANCO DE DADOS
# ============================================================================

Write-Host "💾 Inicializando banco de dados..." -ForegroundColor Yellow

# Executa servidor.py para inicializar o banco (primeira vez)
$initScript = @"
import sys
import os
sys.path.insert(0, r'$scriptDir')
os.chdir(r'$scriptDir')

# Importa e inicializa
from servidor import init_db, app
with app.app_context():
    init_db()
    print('✅ Banco de dados inicializado!')
"@

$initScript | & $PythonPath -c "exec(`$input)"

if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Aviso: Erro ao inicializar banco de dados (pode já existir)" -ForegroundColor Yellow
} else {
    Write-Host "✅ Banco de dados inicializado!" -ForegroundColor Green
}
Write-Host ""

# ============================================================================
# 4. CONFIGURA FIREWALL
# ============================================================================

if ($ConfigureFirewall) {
    Write-Host "🔥 Configurando Firewall do Windows..." -ForegroundColor Yellow
    
    try {
        # Remove regra existente se houver
        Remove-NetFirewallRule -DisplayName "PrintMonitor Server" -ErrorAction SilentlyContinue
        
        # Adiciona nova regra
        New-NetFirewallRule `
            -DisplayName "PrintMonitor Server" `
            -Direction Inbound `
            -Protocol TCP `
            -LocalPort $Port `
            -Action Allow `
            -Profile Any | Out-Null
        
        Write-Host "✅ Regra de firewall criada para porta $Port" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Erro ao configurar firewall: $_" -ForegroundColor Yellow
        Write-Host "💡 Configure manualmente no Firewall do Windows" -ForegroundColor Yellow
    }
    Write-Host ""
}

# ============================================================================
# 5. CRIA SERVIÇO WINDOWS (OPCIONAL)
# ============================================================================

if ($InstallService) {
    Write-Host "⚙️  Criando serviço do Windows..." -ForegroundColor Yellow
    
    $serviceName = "PrintMonitorServer"
    $serviceDisplayName = "Print Monitor Server"
    $serviceDescription = "Servidor de Monitoramento de Impressão"
    
    # Verifica se serviço já existe
    $existingService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    
    if ($existingService) {
        if ($Force) {
            Write-Host "   Removendo serviço existente..." -ForegroundColor Gray
            Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
            sc.exe delete $serviceName | Out-Null
            Start-Sleep -Seconds 2
        } else {
            Write-Host "⚠️  Serviço '$serviceName' já existe!" -ForegroundColor Yellow
            Write-Host "💡 Use -Force para reinstalar" -ForegroundColor Yellow
            $InstallService = $false
        }
    }
    
    if ($InstallService) {
        # Instala NSSM (Non-Sucking Service Manager) se não estiver instalado
        $nssmPath = Join-Path $scriptDir "nssm.exe"
        
        if (-not (Test-Path $nssmPath)) {
            Write-Host "   Baixando NSSM..." -ForegroundColor Gray
            $nssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
            $nssmZip = Join-Path $env:TEMP "nssm.zip"
            
            try {
                Invoke-WebRequest -Uri $nssmUrl -OutFile $nssmZip
                Expand-Archive -Path $nssmZip -DestinationPath $env:TEMP -Force
                
                # Copia nssm.exe (versão 64-bit)
                $nssmSource = Join-Path $env:TEMP "nssm-2.24\win64\nssm.exe"
                if (Test-Path $nssmSource) {
                    Copy-Item $nssmSource $nssmPath -Force
                } else {
                    # Tenta 32-bit
                    $nssmSource = Join-Path $env:TEMP "nssm-2.24\win32\nssm.exe"
                    Copy-Item $nssmSource $nssmPath -Force
                }
                
                Remove-Item $nssmZip -Force -ErrorAction SilentlyContinue
                Remove-Item (Join-Path $env:TEMP "nssm-2.24") -Recurse -Force -ErrorAction SilentlyContinue
            } catch {
                Write-Host "⚠️  Erro ao baixar NSSM: $_" -ForegroundColor Yellow
                Write-Host "💡 Instale manualmente ou use Tarefa Agendada" -ForegroundColor Yellow
                $InstallService = $false
            }
        }
        
        if ($InstallService -and (Test-Path $nssmPath)) {
            Write-Host "   Criando serviço..." -ForegroundColor Gray
            
            # Cria script de inicialização
            $startScript = Join-Path $scriptDir "start_server.bat"
            $startScriptContent = @"
@echo off
cd /d "$scriptDir"
"$PythonPath" servidor.py
"@
            $startScriptContent | Out-File -FilePath $startScript -Encoding ASCII -Force
            
            # Instala serviço via NSSM
            & $nssmPath install $serviceName "$PythonPath" "servidor.py"
            & $nssmPath set $serviceName AppDirectory "$scriptDir"
            & $nssmPath set $serviceName DisplayName "$serviceDisplayName"
            & $nssmPath set $serviceName Description "$serviceDescription"
            & $nssmPath set $serviceName Start SERVICE_AUTO_START
            & $nssmPath set $serviceName AppStdout "$scriptDir\logs\service.log"
            & $nssmPath set $serviceName AppStderr "$scriptDir\logs\service_error.log"
            
            Write-Host "✅ Serviço '$serviceName' criado!" -ForegroundColor Green
            Write-Host "💡 Para iniciar: Start-Service -Name $serviceName" -ForegroundColor Cyan
            Write-Host "💡 Para parar: Stop-Service -Name $serviceName" -ForegroundColor Cyan
        }
    }
    Write-Host ""
}

# ============================================================================
# 6. CRIA SCRIPTS DE INICIALIZAÇÃO
# ============================================================================

Write-Host "📝 Criando scripts de inicialização..." -ForegroundColor Yellow

# Script batch para iniciar servidor
$startBatch = Join-Path $scriptDir "iniciar_servidor.bat"
$startBatchContent = @"
@echo off
title Print Monitor Server
cd /d "$scriptDir"
echo Iniciando servidor na porta $Port...
"$PythonPath" servidor.py
pause
"@
$startBatchContent | Out-File -FilePath $startBatch -Encoding ASCII -Force
Write-Host "✅ Criado: iniciar_servidor.bat" -ForegroundColor Green

# Script PowerShell para iniciar servidor
$startPs1 = Join-Path $scriptDir "iniciar_servidor.ps1"
$startPs1Content = @"
# Inicia o servidor de monitoramento
Set-Location "$scriptDir"
& "$PythonPath" servidor.py
"@
$startPs1Content | Out-File -FilePath $startPs1 -Encoding UTF8 -Force
Write-Host "✅ Criado: iniciar_servidor.ps1" -ForegroundColor Green

Write-Host ""

# ============================================================================
# 7. RESUMO E PRÓXIMOS PASSOS
# ============================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  INSTALAÇÃO CONCLUÍDA!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 RESUMO:" -ForegroundColor Cyan
Write-Host "   ✅ Python verificado" -ForegroundColor Green
Write-Host "   ✅ Dependências instaladas" -ForegroundColor Green
Write-Host "   ✅ Banco de dados inicializado" -ForegroundColor Green
if ($ConfigureFirewall) {
    Write-Host "   ✅ Firewall configurado" -ForegroundColor Green
}
if ($InstallService) {
    Write-Host "   ✅ Serviço Windows criado" -ForegroundColor Green
}
Write-Host ""
Write-Host "🚀 PRÓXIMOS PASSOS:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Iniciar o servidor:" -ForegroundColor Yellow
Write-Host "   .\iniciar_servidor.bat" -ForegroundColor Gray
Write-Host "   ou" -ForegroundColor Gray
Write-Host "   .\iniciar_servidor.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Acessar o sistema:" -ForegroundColor Yellow
Write-Host "   http://localhost:$Port" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Login padrão:" -ForegroundColor Yellow
Write-Host "   Usuário: admin" -ForegroundColor Gray
Write-Host "   Senha: (verifique o console na primeira execução)" -ForegroundColor Gray
Write-Host ""
if ($InstallService) {
    Write-Host "4. Para iniciar como serviço:" -ForegroundColor Yellow
    Write-Host "   Start-Service -Name PrintMonitorServer" -ForegroundColor Gray
    Write-Host ""
}
Write-Host "💡 DICA: Configure a SECRET_KEY em variáveis de ambiente para produção!" -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

pause


