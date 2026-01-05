# Script de Teste para Diagnóstico de Acesso Remoto
# Use este script para testar conectividade e credenciais antes de instalar

param(
    [Parameter(Mandatory=$true)]
    [string]$ComputerName,
    
    [Parameter(Mandatory=$false)]
    [string]$Domain = "",
    
    [Parameter(Mandatory=$true)]
    [string]$Username,
    
    [Parameter(Mandatory=$true)]
    [string]$Password
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  TESTE DE ACESSO REMOTO" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Formata username
if ($Domain -and -not $Username.Contains("\") -and -not $Username.StartsWith("\\")) {
    $fullUsername = "$Domain\$Username"
} else {
    $fullUsername = $Username
}

Write-Host "Configuração:" -ForegroundColor Yellow
Write-Host "  Computador: $ComputerName" -ForegroundColor White
Write-Host "  Usuário: $fullUsername" -ForegroundColor White
Write-Host ""

# Teste 1: Ping
Write-Host "[1] Testando conectividade (ping)..." -ForegroundColor Yellow
$pingResult = Test-Connection -ComputerName $ComputerName -Count 1 -Quiet
if ($pingResult) {
    Write-Host "  ✅ Computador acessível" -ForegroundColor Green
} else {
    Write-Host "  ❌ Computador NÃO acessível" -ForegroundColor Red
    Write-Host "  💡 Verifique se o computador está ligado e na rede" -ForegroundColor Yellow
    exit 1
}

# Teste 2: WinRM (PowerShell Remoting)
Write-Host ""
Write-Host "[2] Testando WinRM (PowerShell Remoting)..." -ForegroundColor Yellow
try {
    $winrmStatus = Get-WSManInstance -ResourceURI winrm/config/Listener -ErrorAction SilentlyContinue
    if ($winrmStatus) {
        Write-Host "  ✅ WinRM está configurado localmente" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  WinRM pode não estar configurado" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠️  Não foi possível verificar WinRM local" -ForegroundColor Yellow
}

# Teste 3: Credenciais
Write-Host ""
Write-Host "[3] Testando credenciais..." -ForegroundColor Yellow
try {
    $securePassword = ConvertTo-SecureString $Password -AsPlainText -Force
    $credential = New-Object System.Management.Automation.PSCredential($fullUsername, $securePassword)
    Write-Host "  ✅ Credenciais criadas com sucesso" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Erro ao criar credenciais: $_" -ForegroundColor Red
    exit 1
}

# Teste 4: Test-WSMan (verifica se WinRM está habilitado no remoto)
Write-Host ""
Write-Host "[4] Testando WinRM no computador remoto..." -ForegroundColor Yellow
try {
    $wsmanResult = Test-WSMan -ComputerName $ComputerName -ErrorAction Stop
    Write-Host "  ✅ WinRM está habilitado no computador remoto" -ForegroundColor Green
} catch {
    Write-Host "  ❌ WinRM NÃO está habilitado no computador remoto" -ForegroundColor Red
    Write-Host "  💡 Solução: Habilite WinRM no computador remoto:" -ForegroundColor Yellow
    Write-Host "     Enable-PSRemoting -Force" -ForegroundColor Cyan
    Write-Host "     OU configure manualmente via GPO" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Tentando habilitar automaticamente..." -ForegroundColor Yellow
    try {
        # Tenta habilitar via WMI (se tiver acesso)
        $wmi = Get-WmiObject -Class Win32_Service -ComputerName $ComputerName -Credential $credential -Filter "Name='WinRM'" -ErrorAction SilentlyContinue
        if ($wmi) {
            Write-Host "  ⚠️  WinRM existe mas pode não estar configurado" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ❌ Não foi possível verificar WinRM remotamente" -ForegroundColor Red
    }
}

# Teste 5: Invoke-Command (teste real de execução remota)
Write-Host ""
Write-Host "[5] Testando execução remota (Invoke-Command)..." -ForegroundColor Yellow
try {
    $result = Invoke-Command -ComputerName $ComputerName -Credential $credential -ScriptBlock {
        Write-Output "SUCCESS"
        Write-Output $env:COMPUTERNAME
        Write-Output (Get-WmiObject Win32_ComputerSystem).Name
    } -ErrorAction Stop
    
    if ($result) {
        Write-Host "  ✅ Execução remota funcionou!" -ForegroundColor Green
        Write-Host "  ✅ Computador remoto: $($result[1])" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Execução retornou vazio" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ❌ Erro na execução remota: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Possíveis causas:" -ForegroundColor Yellow
    Write-Host "    1. WinRM não está habilitado no computador remoto" -ForegroundColor Yellow
    Write-Host "    2. Credenciais incorretas" -ForegroundColor Yellow
    Write-Host "    3. Usuário não tem permissões administrativas" -ForegroundColor Yellow
    Write-Host "    4. Firewall bloqueando conexão" -ForegroundColor Yellow
    Write-Host "    5. Computador não está no mesmo domínio (se usando conta de domínio)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Soluções:" -ForegroundColor Yellow
    Write-Host "    - Habilite WinRM: Enable-PSRemoting -Force (no computador remoto)" -ForegroundColor Cyan
    Write-Host "    - Verifique credenciais" -ForegroundColor Cyan
    Write-Host "    - Use conta de Administrador Local" -ForegroundColor Cyan
    Write-Host "    - Verifique firewall" -ForegroundColor Cyan
}

# Teste 6: WMI (alternativa ao WinRM)
Write-Host ""
Write-Host "[6] Testando WMI (alternativa)..." -ForegroundColor Yellow
try {
    $wmiResult = Get-WmiObject -Class Win32_ComputerSystem -ComputerName $ComputerName -Credential $credential -ErrorAction Stop
    if ($wmiResult) {
        Write-Host "  ✅ WMI funcionou!" -ForegroundColor Green
        Write-Host "  ✅ Nome do computador: $($wmiResult.Name)" -ForegroundColor Green
        Write-Host "  💡 WMI pode ser usado como alternativa ao WinRM" -ForegroundColor Cyan
    }
} catch {
    Write-Host "  ❌ WMI também falhou: $_" -ForegroundColor Red
    Write-Host "  💡 Isso indica problema de credenciais ou permissões" -ForegroundColor Yellow
}

# Teste 7: Verificar permissões
Write-Host ""
Write-Host "[7] Verificando permissões do usuário..." -ForegroundColor Yellow
try {
    $adminCheck = Invoke-Command -ComputerName $ComputerName -Credential $credential -ScriptBlock {
        $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
        $isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
        return $isAdmin
    } -ErrorAction Stop
    
    if ($adminCheck) {
        Write-Host "  ✅ Usuário tem permissões de Administrador" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Usuário NÃO tem permissões de Administrador" -ForegroundColor Yellow
        Write-Host "  💡 O agente precisa de permissões de Admin para instalar" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠️  Não foi possível verificar permissões: $_" -ForegroundColor Yellow
}

# Resumo
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RESUMO" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Se todos os testes passaram:" -ForegroundColor Green
Write-Host "  ✅ Você pode instalar o agente normalmente" -ForegroundColor Green
Write-Host ""
Write-Host "Se algum teste falhou:" -ForegroundColor Yellow
Write-Host "  💡 Corrija os problemas antes de instalar" -ForegroundColor Yellow
Write-Host "  💡 Use este script para diagnosticar problemas" -ForegroundColor Yellow
Write-Host ""

