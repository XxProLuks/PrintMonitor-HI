# Script para instalação remota do agente em múltiplos computadores da rede
# Requer: PowerShell Remoting habilitado e credenciais administrativas

param(
    [Parameter(Mandatory=$true)]
    [string[]]$Computers,
    
    [Parameter(Mandatory=$false)]
    [string]$Username = "",
    
    [Parameter(Mandatory=$false)]
    [string]$Password = "",
    
    [Parameter(Mandatory=$false)]
    [string]$AgentPath = "",
    
    [Parameter(Mandatory=$false)]
    [string]$PythonPath = "",
    
    [switch]$SkipVerification = $false
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  INSTALAÇÃO REMOTA DO AGENTE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Determina caminho do agente
if ([string]::IsNullOrEmpty($AgentPath)) {
    $AgentPath = Split-Path -Parent $MyInvocation.MyCommand.Path
}

if (-not (Test-Path (Join-Path $AgentPath "agente.py"))) {
    Write-Host "❌ Arquivo agente.py não encontrado em: $AgentPath" -ForegroundColor Red
    exit 1
}

Write-Host "📁 Caminho do agente: $AgentPath" -ForegroundColor Cyan
Write-Host "🖥️  Computadores: $($Computers -join ', ')" -ForegroundColor Cyan
Write-Host ""

# Solicita credenciais se não fornecidas
if ([string]::IsNullOrEmpty($Username)) {
    $Username = Read-Host "Digite o usuário administrativo"
}

if ([string]::IsNullOrEmpty($Password)) {
    $securePassword = Read-Host "Digite a senha" -AsSecureString
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
    $Password = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
}

# Cria credencial
$securePassword = ConvertTo-SecureString $Password -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential($Username, $securePassword)

# Cria script de instalação temporário para copiar
$installScriptContent = Get-Content (Join-Path $AgentPath "install_agent.ps1") -Raw

$results = @()

foreach ($computer in $Computers) {
    Write-Host ""
    Write-Host "🖥️  Processando: $computer" -ForegroundColor Cyan
    Write-Host "────────────────────────────────────────" -ForegroundColor Gray
    
    try {
        # Testa conectividade
        if (-not $SkipVerification) {
            $ping = Test-Connection -ComputerName $computer -Count 1 -Quiet
            if (-not $ping) {
                Write-Host "❌ $computer : Não acessível (ping falhou)" -ForegroundColor Red
                $results += [PSCustomObject]@{
                    Computer = $computer
                    Status = "Falhou"
                    Message = "Não acessível"
                }
                continue
            }
        }
        
        # Cria diretório remoto para o agente
        $remotePath = "\\$computer\C$\PrintMonitorAgent"
        
        Write-Host "📦 Copiando arquivos para $computer..." -ForegroundColor Yellow
        
        # Cria diretório remoto
        if (-not (Test-Path $remotePath)) {
            New-Item -ItemType Directory -Path $remotePath -Force | Out-Null
        }
        
        # Copia arquivos do agente
        Copy-Item -Path "$AgentPath\*" -Destination $remotePath -Recurse -Force -Exclude "*.log","__pycache__","*.pyc"
        
        Write-Host "✅ Arquivos copiados" -ForegroundColor Green
        
        # Executa instalação remota
        Write-Host "🔧 Executando instalação remota..." -ForegroundColor Yellow
        
        $installCommand = @"
`$ErrorActionPreference = 'Stop'
cd 'C:\PrintMonitorAgent'
. .\install_agent.ps1 -PythonPath '$PythonPath' -Force
"@
        
        Invoke-Command -ComputerName $computer -Credential $credential -ScriptBlock {
            param($cmd, $path)
            Set-Location $path
            Invoke-Expression $cmd
        } -ArgumentList $installCommand, "C:\PrintMonitorAgent" -ErrorAction Stop
        
        Write-Host "✅ $computer : Instalação concluída com sucesso!" -ForegroundColor Green
        $results += [PSCustomObject]@{
            Computer = $computer
            Status = "Sucesso"
            Message = "Instalado com sucesso"
        }
        
    } catch {
        Write-Host "❌ $computer : Erro - $_" -ForegroundColor Red
        $results += [PSCustomObject]@{
            Computer = $computer
            Status = "Falhou"
            Message = $_.Exception.Message
        }
    }
}

# Resumo
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RESUMO DA INSTALAÇÃO" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$successCount = ($results | Where-Object { $_.Status -eq "Sucesso" }).Count
$failCount = ($results | Where-Object { $_.Status -eq "Falhou" }).Count

Write-Host "✅ Sucesso: $successCount" -ForegroundColor Green
Write-Host "❌ Falhas: $failCount" -ForegroundColor Red
Write-Host ""

$results | Format-Table -AutoSize

Write-Host ""
Write-Host "📝 Para verificar o status em cada computador:" -ForegroundColor Cyan
Write-Host "   Invoke-Command -ComputerName COMPUTADOR -Credential `$cred -ScriptBlock { Get-ScheduledTask -TaskName 'PrintMonitorAgent' | Get-ScheduledTaskInfo }" -ForegroundColor Gray

