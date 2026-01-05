# ============================================================================
# SCRIPT DE DEPLOY EM MASSA DO AGENTE NA REDE
# ============================================================================
# Instala o agente de monitoramento em múltiplos computadores da rede
# Suporta: Descoberta automática, instalação remota, verificação de status
# ============================================================================

param(
    [Parameter(Mandatory=$false)]
    [string[]]$Computers = @(),
    
    [Parameter(Mandatory=$false)]
    [string]$ComputerListFile = "",
    
    [Parameter(Mandatory=$false)]
    [string]$Domain = "",
    
    [Parameter(Mandatory=$false)]
    [string]$Username = "",
    
    [Parameter(Mandatory=$false)]
    [string]$Password = "",
    
    [Parameter(Mandatory=$false)]
    [string]$ServerURL = "",
    
    [Parameter(Mandatory=$false)]
    [string]$AgentPath = "",
    
    [Parameter(Mandatory=$false)]
    [string]$PythonPath = "",
    
    [switch]$Discover = $false,
    [switch]$Install = $false,
    [switch]$Uninstall = $false,
    [switch]$Status = $false,
    [switch]$Update = $false,
    [switch]$SkipVerification = $false,
    [switch]$EnableEventLog = $false,
    [switch]$Force = $false
)

# ============================================================================
# CONFIGURAÇÃO E INICIALIZAÇÃO
# ============================================================================

$ErrorActionPreference = "Stop"
$scriptVersion = "2.0.0"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Cores para output
function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

# Banner
Write-ColorOutput "="*70 "Cyan"
Write-ColorOutput "  DEPLOY DO AGENTE DE MONITORAMENTO - REDE COMPLETA" "Cyan"
Write-ColorOutput "  Versão: $scriptVersion" "Cyan"
Write-ColorOutput "="*70 "Cyan"
Write-Host ""

# Verifica se está como administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-ColorOutput "❌ Este script precisa ser executado como Administrador!" "Red"
    Write-ColorOutput "💡 Clique com botão direito e selecione 'Executar como administrador'" "Yellow"
    pause
    exit 1
}

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

function Get-AgentPath {
    if ([string]::IsNullOrEmpty($AgentPath)) {
        $AgentPath = $scriptDir
    }
    
    if (-not (Test-Path (Join-Path $AgentPath "agente.py"))) {
        Write-ColorOutput "❌ Arquivo agente.py não encontrado em: $AgentPath" "Red"
        exit 1
    }
    
    return $AgentPath
}

function Get-ComputerList {
    $computers = @()
    
    # Se lista de computadores fornecida diretamente
    if ($Computers.Count -gt 0) {
        $computers = $Computers
    }
    # Se arquivo de lista fornecido
    elseif (-not [string]::IsNullOrEmpty($ComputerListFile)) {
        if (Test-Path $ComputerListFile) {
            $computers = Get-Content $ComputerListFile | Where-Object { 
                $_.Trim() -ne "" -and -not $_.StartsWith("#") 
            } | ForEach-Object { $_.Trim() }
        } else {
            Write-ColorOutput "❌ Arquivo de lista não encontrado: $ComputerListFile" "Red"
            exit 1
        }
    }
    # Se modo descoberta ativado
    elseif ($Discover) {
        Write-ColorOutput "🔍 Descobrindo computadores na rede..." "Yellow"
        $computers = Discover-NetworkComputers
    }
    # Se nenhum método especificado, pergunta
    else {
        Write-ColorOutput "📋 Nenhuma lista de computadores fornecida." "Yellow"
        Write-ColorOutput "💡 Opções:" "Yellow"
        Write-ColorOutput "   1. Use -Computers @('PC01', 'PC02', ...)" "Gray"
        Write-ColorOutput "   2. Use -ComputerListFile 'computadores.txt'" "Gray"
        Write-ColorOutput "   3. Use -Discover para descobrir automaticamente" "Gray"
        Write-Host ""
        $choice = Read-Host "Deseja descobrir computadores automaticamente? (S/N)"
        if ($choice -eq "S" -or $choice -eq "s") {
            $computers = Discover-NetworkComputers
        } else {
            exit 0
        }
    }
    
    if ($computers.Count -eq 0) {
        Write-ColorOutput "❌ Nenhum computador encontrado!" "Red"
        exit 1
    }
    
    return $computers
}

function Discover-NetworkComputers {
    Write-ColorOutput "🔍 Escaneando rede local..." "Yellow"
    
    $computers = @()
    
    try {
        # Método 1: Active Directory (se disponível)
        try {
            Import-Module ActiveDirectory -ErrorAction SilentlyContinue
            $adComputers = Get-ADComputer -Filter {Enabled -eq $true} -Properties Name | Select-Object -ExpandProperty Name
            if ($adComputers) {
                Write-ColorOutput "✅ Encontrados $($adComputers.Count) computadores no Active Directory" "Green"
                $computers = $adComputers
            }
        } catch {
            Write-ColorOutput "⚠️ Active Directory não disponível, usando método alternativo" "Yellow"
        }
        
        # Método 2: Net View (fallback)
        if ($computers.Count -eq 0) {
            Write-ColorOutput "🔍 Usando 'net view' para descobrir computadores..." "Yellow"
            $netView = net view 2>$null | Where-Object { $_ -match '\\\\([^\\]+)' } | ForEach-Object {
                if ($_ -match '\\\\([^\\]+)') {
                    $matches[1]
                }
            }
            $computers = $netView | Where-Object { $_ -ne "" }
        }
        
        # Método 3: Ping scan na sub-rede local
        if ($computers.Count -eq 0) {
            Write-ColorOutput "🔍 Escaneando sub-rede local..." "Yellow"
            $localIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } | Select-Object -First 1).IPAddress
            if ($localIP) {
                $subnet = $localIP -replace '\.\d+$', ''
                $computers = 1..254 | ForEach-Object -Parallel {
                    $ip = "$using:subnet.$_"
                    if (Test-Connection -ComputerName $ip -Count 1 -Quiet -TimeoutSeconds 1) {
                        try {
                            $hostname = [System.Net.Dns]::GetHostEntry($ip).HostName
                            $hostname -replace '\.\w+$', ''
                        } catch {
                            $ip
                        }
                    }
                } -ThrottleLimit 50 | Where-Object { $_ -ne $null }
            }
        }
        
    } catch {
        Write-ColorOutput "⚠️ Erro na descoberta: $_" "Yellow"
    }
    
    if ($computers.Count -eq 0) {
        Write-ColorOutput "⚠️ Nenhum computador descoberto automaticamente" "Yellow"
        Write-ColorOutput "💡 Use -Computers ou -ComputerListFile para especificar manualmente" "Yellow"
    } else {
        Write-ColorOutput "✅ Encontrados $($computers.Count) computadores" "Green"
    }
    
    return $computers
}

function Get-Credentials {
    if ([string]::IsNullOrEmpty($Username)) {
        if (-not [string]::IsNullOrEmpty($Domain)) {
            $Username = Read-Host "Digite o usuário administrativo (domínio: $Domain)"
            if (-not $Username.Contains("\")) {
                $Username = "$Domain\$Username"
            }
        } else {
            $Username = Read-Host "Digite o usuário administrativo (formato: DOMINIO\usuario ou usuario)"
        }
    } elseif (-not [string]::IsNullOrEmpty($Domain) -and -not $Username.Contains("\")) {
        $Username = "$Domain\$Username"
    }
    
    if ([string]::IsNullOrEmpty($Password)) {
        $securePassword = Read-Host "Digite a senha" -AsSecureString
        $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
        $Password = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
    }
    
    $securePassword = ConvertTo-SecureString $Password -AsPlainText -Force
    return New-Object System.Management.Automation.PSCredential($Username, $securePassword)
}

function Test-ComputerAccess {
    param([string]$Computer, [PSCredential]$Credential)
    
    try {
        # Testa ping
        if (-not $SkipVerification) {
            $ping = Test-Connection -ComputerName $Computer -Count 1 -Quiet -ErrorAction SilentlyContinue
            if (-not $ping) {
                return @{ Success = $false; Message = "Ping falhou" }
            }
        }
        
        # Testa acesso remoto
        try {
            $session = New-PSSession -ComputerName $Computer -Credential $Credential -ErrorAction Stop
            Remove-PSSession $session
            return @{ Success = $true; Message = "Acessível" }
        } catch {
            return @{ Success = $false; Message = "Acesso remoto negado: $_" }
        }
    } catch {
        return @{ Success = $false; Message = "Erro: $_" }
    }
}

function Install-AgentOnComputer {
    param(
        [string]$Computer,
        [PSCredential]$Credential,
        [string]$AgentPath,
        [string]$ServerURL,
        [string]$PythonPath
    )
    
    Write-ColorOutput "🖥️  Processando: $Computer" "Cyan"
    Write-ColorOutput "────────────────────────────────────────" "Gray"
    
    try {
        # Testa acesso
        $access = Test-ComputerAccess -Computer $Computer -Credential $Credential
        if (-not $access.Success) {
            Write-ColorOutput "❌ $Computer : $($access.Message)" "Red"
            return @{ Computer = $Computer; Status = "Falhou"; Message = $access.Message }
        }
        
        # Cria diretório remoto
        $remotePath = "\\$Computer\C$\PrintMonitorAgent"
        Write-ColorOutput "📦 Copiando arquivos para $Computer..." "Yellow"
        
        if (-not (Test-Path $remotePath)) {
            New-Item -ItemType Directory -Path $remotePath -Force | Out-Null
        }
        
        # Copia arquivos (exclui logs e cache)
        $excludeItems = @("*.log", "__pycache__", "*.pyc", "*.db", "agent_state.json", "event_queue.db", "logs")
        Copy-Item -Path "$AgentPath\*" -Destination $remotePath -Recurse -Force -Exclude $excludeItems -ErrorAction Stop
        
        Write-ColorOutput "✅ Arquivos copiados" "Green"
        
        # Atualiza config.json com URL do servidor se fornecido
        if (-not [string]::IsNullOrEmpty($ServerURL)) {
            $configPath = Join-Path $remotePath "config.json"
            if (Test-Path $configPath) {
                $config = Get-Content $configPath | ConvertFrom-Json
                $config.server_url = $ServerURL
                $config | ConvertTo-Json | Set-Content $configPath -Encoding UTF8
                Write-ColorOutput "✅ Config.json atualizado com URL do servidor" "Green"
            }
        }
        
        # Habilita Event Log 307 se solicitado
        if ($EnableEventLog) {
            Write-ColorOutput "🔧 Habilitando Event Log 307..." "Yellow"
            $enableEventScript = {
                wevtutil sl Microsoft-Windows-PrintService/Operational /e:true 2>&1 | Out-Null
            }
            try {
                Invoke-Command -ComputerName $Computer -Credential $Credential -ScriptBlock $enableEventScript -ErrorAction SilentlyContinue
                Write-ColorOutput "✅ Event Log 307 habilitado" "Green"
            } catch {
                Write-ColorOutput "⚠️ Não foi possível habilitar Event Log 307 automaticamente" "Yellow"
            }
        }
        
        # Executa instalação remota
        Write-ColorOutput "🔧 Executando instalação remota..." "Yellow"
        
        $installScript = {
            param($Path, $PythonPath, $Force)
            
            $ErrorActionPreference = "Stop"
            Set-Location $Path
            
            # Verifica se já está instalado
            $task = Get-ScheduledTask -TaskName "PrintMonitorAgent" -ErrorAction SilentlyContinue
            if ($task -and -not $Force) {
                Write-Output "⚠️ Agente já instalado. Use -Force para reinstalar."
                return @{ Installed = $true; Message = "Já instalado" }
            }
            
            # Remove instalação anterior se Force
            if ($task -and $Force) {
                Unregister-ScheduledTask -TaskName "PrintMonitorAgent" -Confirm:$false -ErrorAction SilentlyContinue
            }
            
            # Determina executável
            $agentExe = Join-Path $Path "PrintMonitorAgent.exe"
            $agentScript = Join-Path $Path "agente.py"
            
            if (Test-Path $agentExe) {
                $executable = $agentExe
                $args = ""
            } elseif (Test-Path $agentScript) {
                if ([string]::IsNullOrEmpty($PythonPath)) {
                    $python = Get-Command python -ErrorAction SilentlyContinue
                    if (-not $python) {
                        return @{ Installed = $false; Message = "Python não encontrado" }
                    }
                    $executable = $python.Source
                } else {
                    $executable = $PythonPath
                }
                $args = "`"$agentScript`""
            } else {
                return @{ Installed = $false; Message = "Agente não encontrado" }
            }
            
            # Cria diretório de logs
            $logsDir = Join-Path $Path "logs"
            if (-not (Test-Path $logsDir)) {
                New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
            }
            
            # Cria tarefa agendada
            $action = New-ScheduledTaskAction -Execute $executable -Argument $args -WorkingDirectory $Path
            $trigger = New-ScheduledTaskTrigger -AtStartup
            $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
            $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
            
            Register-ScheduledTask -TaskName "PrintMonitorAgent" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Agente de Monitoramento de Impressão" -Force | Out-Null
            
            # Inicia a tarefa
            Start-ScheduledTask -TaskName "PrintMonitorAgent" | Out-Null
            
            return @{ Installed = $true; Message = "Instalado com sucesso" }
        }
        
        $result = Invoke-Command -ComputerName $Computer -Credential $Credential -ScriptBlock $installScript -ArgumentList "C:\PrintMonitorAgent", $PythonPath, $Force -ErrorAction Stop
        
        if ($result.Installed) {
            Write-ColorOutput "✅ $Computer : Instalação concluída!" "Green"
            return @{ Computer = $Computer; Status = "Sucesso"; Message = $result.Message }
        } else {
            Write-ColorOutput "❌ $Computer : $($result.Message)" "Red"
            return @{ Computer = $Computer; Status = "Falhou"; Message = $result.Message }
        }
        
    } catch {
        Write-ColorOutput "❌ $Computer : Erro - $_" "Red"
        return @{ Computer = $Computer; Status = "Falhou"; Message = $_.Exception.Message }
    }
}

function Uninstall-AgentOnComputer {
    param([string]$Computer, [PSCredential]$Credential)
    
    Write-ColorOutput "🗑️  Desinstalando de: $Computer" "Cyan"
    
    try {
        $uninstallScript = {
            # Remove tarefa agendada
            $task = Get-ScheduledTask -TaskName "PrintMonitorAgent" -ErrorAction SilentlyContinue
            if ($task) {
                Stop-ScheduledTask -TaskName "PrintMonitorAgent" -ErrorAction SilentlyContinue
                Unregister-ScheduledTask -TaskName "PrintMonitorAgent" -Confirm:$false -ErrorAction SilentlyContinue
            }
            
            # Remove diretório (opcional - comentado por segurança)
            # Remove-Item "C:\PrintMonitorAgent" -Recurse -Force -ErrorAction SilentlyContinue
            
            return @{ Uninstalled = $true; Message = "Desinstalado com sucesso" }
        }
        
        $result = Invoke-Command -ComputerName $Computer -Credential $Credential -ScriptBlock $uninstallScript -ErrorAction Stop
        
        if ($result.Uninstalled) {
            Write-ColorOutput "✅ $Computer : Desinstalado!" "Green"
            return @{ Computer = $Computer; Status = "Sucesso"; Message = $result.Message }
        } else {
            return @{ Computer = $Computer; Status = "Falhou"; Message = $result.Message }
        }
        
    } catch {
        Write-ColorOutput "❌ $Computer : Erro - $_" "Red"
        return @{ Computer = $Computer; Status = "Falhou"; Message = $_.Exception.Message }
    }
}

function Get-AgentStatus {
    param([string]$Computer, [PSCredential]$Credential)
    
    try {
        $statusScript = {
            $task = Get-ScheduledTask -TaskName "PrintMonitorAgent" -ErrorAction SilentlyContinue
            if ($task) {
                $taskInfo = Get-ScheduledTaskInfo -TaskName "PrintMonitorAgent"
                $process = Get-Process python* -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*PrintMonitorAgent*" } | Select-Object -First 1
                
                return @{
                    Installed = $true
                    Enabled = $task.State -eq "Running"
                    LastRun = $taskInfo.LastRunTime
                    NextRun = $taskInfo.NextRunTime
                    Running = $process -ne $null
                }
            } else {
                return @{ Installed = $false }
            }
        }
        
        $result = Invoke-Command -ComputerName $Computer -Credential $Credential -ScriptBlock $statusScript -ErrorAction Stop
        
        if ($result.Installed) {
            $status = if ($result.Running) { "✅ Rodando" } else { "⚠️ Parado" }
            Write-ColorOutput "$Computer : $status (Última execução: $($result.LastRun))" "Green"
        } else {
            Write-ColorOutput "$Computer : ❌ Não instalado" "Red"
        }
        
        return $result
        
    } catch {
        Write-ColorOutput "$Computer : ❌ Erro ao verificar - $_" "Red"
        return @{ Installed = $false; Error = $_.Exception.Message }
    }
}

# ============================================================================
# EXECUÇÃO PRINCIPAL
# ============================================================================

# Obtém caminho do agente
$agentPath = Get-AgentPath

# Obtém lista de computadores
$computers = Get-ComputerList

Write-ColorOutput "📋 Computadores a processar: $($computers.Count)" "Cyan"
$computers | ForEach-Object { Write-ColorOutput "   - $_" "Gray" }
Write-Host ""

# Obtém credenciais
$credential = Get-Credentials

# Obtém URL do servidor se não fornecido
if ([string]::IsNullOrEmpty($ServerURL)) {
    $configPath = Join-Path $agentPath "config.json"
    if (Test-Path $configPath) {
        $config = Get-Content $configPath | ConvertFrom-Json
        $ServerURL = $config.server_url
        Write-ColorOutput "📡 URL do servidor: $ServerURL" "Cyan"
    } else {
        $ServerURL = Read-Host "Digite a URL do servidor (ex: http://192.168.1.27:5002/api/print_events)"
    }
}

Write-Host ""

# Executa ação solicitada
$results = @()

if ($Install) {
    Write-ColorOutput "🚀 Iniciando instalação em $($computers.Count) computador(es)..." "Cyan"
    Write-Host ""
    
    foreach ($computer in $computers) {
        $result = Install-AgentOnComputer -Computer $computer -Credential $credential -AgentPath $agentPath -ServerURL $ServerURL -PythonPath $PythonPath
        $results += $result
        Write-Host ""
    }
    
} elseif ($Uninstall) {
    Write-ColorOutput "🗑️  Iniciando desinstalação em $($computers.Count) computador(es)..." "Cyan"
    Write-Host ""
    
    foreach ($computer in $computers) {
        $result = Uninstall-AgentOnComputer -Computer $computer -Credential $credential
        $results += $result
        Write-Host ""
    }
    
} elseif ($Status) {
    Write-ColorOutput "📊 Verificando status em $($computers.Count) computador(es)..." "Cyan"
    Write-Host ""
    
    foreach ($computer in $computers) {
        Get-AgentStatus -Computer $computer -Credential $credential
    }
    
} elseif ($Update) {
    Write-ColorOutput "🔄 Atualizando agente em $($computers.Count) computador(es)..." "Cyan"
    Write-Host ""
    
    foreach ($computer in $computers) {
        Write-ColorOutput "🔄 Atualizando: $computer" "Cyan"
        # Desinstala primeiro
        Uninstall-AgentOnComputer -Computer $computer -Credential $credential
        Write-Host ""
        # Instala novamente
        $result = Install-AgentOnComputer -Computer $computer -Credential $credential -AgentPath $agentPath -ServerURL $ServerURL -PythonPath $PythonPath -Force
        $results += $result
        Write-Host ""
    }
    
} else {
    Write-ColorOutput "❌ Nenhuma ação especificada!" "Red"
    Write-ColorOutput "💡 Use: -Install, -Uninstall, -Status ou -Update" "Yellow"
    exit 1
}

# Resumo final
if ($results.Count -gt 0) {
    Write-Host ""
    Write-ColorOutput "="*70 "Cyan"
    Write-ColorOutput "  RESUMO" "Cyan"
    Write-ColorOutput "="*70 "Cyan"
    Write-Host ""
    
    $successCount = ($results | Where-Object { $_.Status -eq "Sucesso" }).Count
    $failCount = ($results | Where-Object { $_.Status -eq "Falhou" }).Count
    
    Write-ColorOutput "✅ Sucesso: $successCount" "Green"
    Write-ColorOutput "❌ Falhas: $failCount" "Red"
    Write-Host ""
    
    $results | Format-Table -AutoSize
    
    Write-Host ""
    Write-ColorOutput "💡 Para verificar status:" "Cyan"
    Write-ColorOutput "   .\DEPLOY_REDE_COMPLETO.ps1 -Status -Computers @('PC01', 'PC02')" "Gray"
}

Write-Host ""
Write-ColorOutput "="*70 "Cyan"
Write-ColorOutput "  CONCLUÍDO" "Cyan"
Write-ColorOutput "="*70 "Cyan"

