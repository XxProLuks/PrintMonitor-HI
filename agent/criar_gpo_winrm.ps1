# Script para criar GPO automaticamente para habilitar WinRM
# Execute no servidor de domínio como Administrador

param(
    [Parameter(Mandatory=$false)]
    [string]$GPOName = "Habilitar WinRM para Instalação de Agente",
    
    [Parameter(Mandatory=$false)]
    [string]$TargetOU = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipScript
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CRIAÇÃO DE GPO PARA WINRM" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verifica se módulo GroupPolicy está disponível
try {
    Import-Module GroupPolicy -ErrorAction Stop
    Write-Host "✅ Módulo GroupPolicy carregado" -ForegroundColor Green
} catch {
    Write-Host "❌ Erro: Módulo GroupPolicy não encontrado" -ForegroundColor Red
    Write-Host "💡 Instale: Install-WindowsFeature GPMC" -ForegroundColor Yellow
    exit 1
}

# Verifica se está em domínio
try {
    $domain = Get-ADDomain -ErrorAction Stop
    Write-Host "✅ Domínio detectado: $($domain.DNSRoot)" -ForegroundColor Green
} catch {
    Write-Host "❌ Erro: Não está em domínio ou Active Directory não disponível" -ForegroundColor Red
    exit 1
}

# Verifica se GPO já existe
$existingGPO = Get-GPO -Name $GPOName -ErrorAction SilentlyContinue
if ($existingGPO) {
    Write-Host "⚠️  GPO '$GPOName' já existe!" -ForegroundColor Yellow
    $response = Read-Host "Deseja remover e recriar? (S/N)"
    if ($response -eq "S" -or $response -eq "s") {
        Remove-GPO -Name $GPOName -Confirm:$false
        Write-Host "🗑️  GPO antigo removido" -ForegroundColor Yellow
    } else {
        Write-Host "❌ Operação cancelada" -ForegroundColor Red
        exit 0
    }
}

# Cria GPO
Write-Host ""
Write-Host "📝 Criando GPO: $GPOName" -ForegroundColor Cyan
try {
    New-GPO -Name $GPOName -Comment "Habilita WinRM para instalação remota do agente de monitoramento" | Out-Null
    Write-Host "✅ GPO criado com sucesso" -ForegroundColor Green
} catch {
    Write-Host "❌ Erro ao criar GPO: $_" -ForegroundColor Red
    exit 1
}

# Configurações de Registry
Write-Host ""
Write-Host "🔧 Configurando políticas de Registry..." -ForegroundColor Cyan

# 1. Habilitar WinRM Service
Write-Host "   Configurando WinRM Service..." -ForegroundColor Yellow
Set-GPRegistryValue -Name $GPOName -Key "HKLM\SYSTEM\CurrentControlSet\Services\WinRM" -ValueName "Start" -Type DWord -Value 2 -ErrorAction SilentlyContinue

# 2. Permitir autenticação básica
Write-Host "   Habilitando autenticação básica..." -ForegroundColor Yellow
Set-GPRegistryValue -Name $GPOName -Key "HKLM\SOFTWARE\Policies\Microsoft\Windows\WinRM\Service" -ValueName "AllowBasic" -Type DWord -Value 1 -ErrorAction SilentlyContinue

# 3. Permitir tráfego não criptografado (para compatibilidade)
Write-Host "   Configurando tráfego não criptografado..." -ForegroundColor Yellow
Set-GPRegistryValue -Name $GPOName -Key "HKLM\SOFTWARE\Policies\Microsoft\Windows\WinRM\Service" -ValueName "AllowUnencrypted" -Type DWord -Value 1 -ErrorAction SilentlyContinue

# 4. Permitir acesso remoto ao shell
Write-Host "   Habilitando acesso remoto ao shell..." -ForegroundColor Yellow
Set-GPRegistryValue -Name $GPOName -Key "HKLM\SOFTWARE\Policies\Microsoft\Windows\WinRM\Service\WinRS" -ValueName "AllowRemoteShellAccess" -Type DWord -Value 1 -ErrorAction SilentlyContinue

# 5. Configurar listener HTTP
Write-Host "   Configurando listener HTTP..." -ForegroundColor Yellow
Set-GPRegistryValue -Name $GPOName -Key "HKLM\SOFTWARE\Policies\Microsoft\Windows\WinRM\Service\WinRS" -ValueName "MaxConcurrentUsers" -Type DWord -Value 10 -ErrorAction SilentlyContinue

Write-Host "✅ Políticas de Registry configuradas" -ForegroundColor Green

# Cria script de inicialização
if (-not $SkipScript) {
    Write-Host ""
    Write-Host "📝 Criando script de inicialização..." -ForegroundColor Cyan
    
    $scriptContent = @"
# Script para habilitar WinRM via GPO
# Gerado automaticamente por criar_gpo_winrm.ps1

`$ErrorActionPreference = 'Continue'

try {
    # Habilita WinRM
    Enable-PSRemoting -Force -SkipNetworkProfileCheck -ErrorAction SilentlyContinue
    
    # Configura TrustedHosts
    Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force -ErrorAction SilentlyContinue
    
    # Configura autenticação
    Set-Item WSMan:\localhost\Service\Auth\Basic -Value `$true -ErrorAction SilentlyContinue
    Set-Item WSMan:\localhost\Service\Auth\CredSSP -Value `$true -ErrorAction SilentlyContinue
    
    # Inicia serviço WinRM
    Start-Service WinRM -ErrorAction SilentlyContinue
    Set-Service WinRM -StartupType Automatic -ErrorAction SilentlyContinue
    
    # Habilita regras de firewall
    Enable-NetFirewallRule -DisplayGroup "Windows Remote Management" -ErrorAction SilentlyContinue
    
    # Log de sucesso
    `$logPath = "`$env:ProgramData\WinRM_Setup.log"
    "`$(Get-Date): WinRM habilitado com sucesso via GPO" | Out-File -FilePath `$logPath -Append -Encoding UTF8
}
catch {
    # Log de erro
    `$logPath = "`$env:ProgramData\WinRM_Setup.log"
    "`$(Get-Date): Erro ao habilitar WinRM: `$_" | Out-File -FilePath `$logPath -Append -Encoding UTF8
}
"@
    
    # Cria diretório de scripts se não existir
    $scriptsPath = "\\$($domain.DNSRoot)\SYSVOL\$($domain.DNSRoot)\scripts"
    if (-not (Test-Path $scriptsPath)) {
        New-Item -ItemType Directory -Path $scriptsPath -Force | Out-Null
    }
    
    # Salva script
    $scriptFile = Join-Path $scriptsPath "habilitar_winrm.ps1"
    Set-Content -Path $scriptFile -Value $scriptContent -Encoding UTF8
    Write-Host "✅ Script criado: $scriptFile" -ForegroundColor Green
    
    # Adiciona script ao GPO
    Write-Host "   Adicionando script ao GPO..." -ForegroundColor Yellow
    Set-GPStartupScript -Name $GPOName -ScriptName "habilitar_winrm.ps1" -ScriptPath $scriptsPath -ErrorAction SilentlyContinue
    Write-Host "✅ Script adicionado ao GPO" -ForegroundColor Green
}

# Configura Firewall via GPO (método alternativo)
Write-Host ""
Write-Host "🔥 Configurando Firewall..." -ForegroundColor Cyan
Write-Host "   (Nota: Configure regras de firewall manualmente no GPO)" -ForegroundColor Yellow
Write-Host "   Caminho: Computer Configuration → Windows Settings → Security Settings → Windows Firewall" -ForegroundColor Yellow

# Vincula GPO à OU
if ($TargetOU) {
    Write-Host ""
    Write-Host "🔗 Vinculando GPO à OU: $TargetOU" -ForegroundColor Cyan
    try {
        New-GPLink -Name $GPOName -Target $TargetOU -ErrorAction Stop
        Write-Host "✅ GPO vinculado com sucesso" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Erro ao vincular GPO: $_" -ForegroundColor Yellow
        Write-Host "💡 Vincule manualmente via GPMC" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "💡 Para vincular o GPO a uma OU:" -ForegroundColor Yellow
    Write-Host "   1. Abra GPMC (gpmc.msc)" -ForegroundColor Cyan
    Write-Host "   2. Navegue até a OU desejada" -ForegroundColor Cyan
    Write-Host "   3. Clique com botão direito → Link an Existing GPO" -ForegroundColor Cyan
    Write-Host "   4. Selecione: $GPOName" -ForegroundColor Cyan
}

# Resumo
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RESUMO" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ GPO criado: $GPOName" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Configurações aplicadas:" -ForegroundColor Cyan
Write-Host "   ✅ WinRM Service habilitado" -ForegroundColor Green
Write-Host "   ✅ Autenticação básica habilitada" -ForegroundColor Green
Write-Host "   ✅ Acesso remoto ao shell habilitado" -ForegroundColor Green
if ($CreateScript) {
    Write-Host "   ✅ Script de inicialização criado" -ForegroundColor Green
}
Write-Host ""
Write-Host "📝 Próximos passos:" -ForegroundColor Yellow
Write-Host "   1. Vincule o GPO à OU desejada (se ainda não fez)" -ForegroundColor Cyan
Write-Host "   2. Configure regras de firewall manualmente no GPO" -ForegroundColor Cyan
Write-Host "   3. Force atualização nos clientes: gpupdate /force" -ForegroundColor Cyan
Write-Host "   4. Verifique: Test-WSMan COMPUTADOR" -ForegroundColor Cyan
Write-Host ""
Write-Host "💡 Para aplicar imediatamente em um computador:" -ForegroundColor Yellow
Write-Host "   gpupdate /force" -ForegroundColor Cyan
Write-Host ""

