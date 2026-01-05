# Script simplificado para instalação em múltiplos computadores
# Versão simplificada do deploy_agent.ps1 para uso mais fácil

param(
    [Parameter(Mandatory=$true)]
    [string]$ComputerList,
    
    [Parameter(Mandatory=$false)]
    [string]$Domain = "",
    
    [switch]$Install = $false,
    [switch]$Uninstall = $false,
    [switch]$Status = $false
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  GERENCIAMENTO REMOTO DO AGENTE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Lê lista de computadores
if (Test-Path $ComputerList) {
    $computers = Get-Content $ComputerList | Where-Object { $_.Trim() -ne "" -and -not $_.StartsWith("#") }
} else {
    # Tenta interpretar como lista separada por vírgula
    $computers = $ComputerList -split "," | ForEach-Object { $_.Trim() }
}

if ($computers.Count -eq 0) {
    Write-Host "❌ Nenhum computador encontrado na lista" -ForegroundColor Red
    exit 1
}

Write-Host "🖥️  Computadores encontrados: $($computers.Count)" -ForegroundColor Cyan
$computers | ForEach-Object { Write-Host "   - $_" -ForegroundColor Gray }
Write-Host ""

# Solicita credenciais
if ([string]::IsNullOrEmpty($Domain)) {
    $Domain = Read-Host "Digite o domínio (ou deixe vazio para usar formato DOMINIO\usuario)"
}

$username = Read-Host "Digite o usuário administrativo"
$securePassword = Read-Host "Digite a senha" -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
$password = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

# Formata username
if ($Domain -and -not $username.Contains("\")) {
    $username = "$Domain\$username"
}

$securePassword = ConvertTo-SecureString $password -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential($username, $securePassword)

$agentPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$results = @()

foreach ($computer in $computers) {
    Write-Host ""
    Write-Host "🖥️  Processando: $computer" -ForegroundColor Cyan
    Write-Host "────────────────────────────────────────" -ForegroundColor Gray
    
    try {
        # Testa conectividade
        $ping = Test-Connection -ComputerName $computer -Count 1 -Quiet -ErrorAction SilentlyContinue
        if (-not $ping) {
            Write-Host "❌ Não acessível (ping falhou)" -ForegroundColor Red
            $results += [PSCustomObject]@{
                Computer = $computer
                Status = "Falhou"
                Message = "Não acessível"
            }
            continue
        }
        
        if ($Install) {
            # Instalação
            Write-Host "📦 Copiando arquivos..." -ForegroundColor Yellow
            $remotePath = "\\$computer\C$\PrintMonitorAgent"
            
            if (-not (Test-Path $remotePath)) {
                New-Item -ItemType Directory -Path $remotePath -Force | Out-Null
            }
            
            Copy-Item -Path "$agentPath\*" -Destination $remotePath -Recurse -Force -Exclude "*.log","__pycache__","*.pyc","*.bat" -ErrorAction Stop
            
            Write-Host "🔧 Executando instalação..." -ForegroundColor Yellow
            
            Invoke-Command -ComputerName $computer -Credential $credential -ScriptBlock {
                param($path)
                Set-Location $path
                $ErrorActionPreference = 'Stop'
                . .\install_agent.ps1 -Force
            } -ArgumentList "C:\PrintMonitorAgent" -ErrorAction Stop
            
            Write-Host "✅ Instalação concluída!" -ForegroundColor Green
            $results += [PSCustomObject]@{
                Computer = $computer
                Status = "Sucesso"
                Message = "Instalado"
            }
            
        } elseif ($Uninstall) {
            # Desinstalação
            Write-Host "🗑️  Removendo agente..." -ForegroundColor Yellow
            
            Invoke-Command -ComputerName $computer -Credential $credential -ScriptBlock {
                param($taskName)
                $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
                if ($task) {
                    Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
                    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
                    return "Removido"
                } else {
                    return "Não encontrado"
                }
            } -ArgumentList "PrintMonitorAgent" -ErrorAction Stop
            
            Write-Host "✅ Desinstalação concluída!" -ForegroundColor Green
            $results += [PSCustomObject]@{
                Computer = $computer
                Status = "Sucesso"
                Message = "Desinstalado"
            }
            
        } elseif ($Status) {
            # Verificação de status
            $statusInfo = Invoke-Command -ComputerName $computer -Credential $credential -ScriptBlock {
                param($taskName)
                $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
                if ($task) {
                    $info = Get-ScheduledTaskInfo -TaskName $taskName
                    $process = Get-Process python* -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*PrintMonitorAgent*" }
                    
                    return @{
                        Exists = $true
                        State = $task.State
                        LastRun = $info.LastRunTime
                        ProcessRunning = ($process -ne $null)
                    }
                } else {
                    return @{ Exists = $false }
                }
            } -ArgumentList "PrintMonitorAgent" -ErrorAction Stop
            
            if ($statusInfo.Exists) {
                Write-Host "✅ Tarefa encontrada" -ForegroundColor Green
                Write-Host "   Estado: $($statusInfo.State)" -ForegroundColor White
                Write-Host "   Última execução: $($statusInfo.LastRun)" -ForegroundColor White
                Write-Host "   Processo: $(if ($statusInfo.ProcessRunning) { 'Rodando' } else { 'Parado' })" -ForegroundColor White
                
                $results += [PSCustomObject]@{
                    Computer = $computer
                    Status = "OK"
                    Message = "Estado: $($statusInfo.State)"
                }
            } else {
                Write-Host "❌ Tarefa não encontrada" -ForegroundColor Red
                $results += [PSCustomObject]@{
                    Computer = $computer
                    Status = "Não instalado"
                    Message = "Tarefa não existe"
                }
            }
        }
        
    } catch {
        Write-Host "❌ Erro: $_" -ForegroundColor Red
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
Write-Host "  RESUMO" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$results | Format-Table -AutoSize

$successCount = ($results | Where-Object { $_.Status -eq "Sucesso" -or $_.Status -eq "OK" }).Count
Write-Host "✅ Sucesso: $successCount / $($computers.Count)" -ForegroundColor Green

