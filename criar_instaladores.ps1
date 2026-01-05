# ============================================================================
# SCRIPT PARA CRIAR INSTALADORES SETUP (.EXE)
# ============================================================================
# Compila os scripts Inno Setup em instaladores executáveis
# ============================================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CRIAR INSTALADORES SETUP (.EXE)" -ForegroundColor Cyan
Write-Host "  Print Monitor System" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Procura Inno Setup Compiler
$innoSetupPaths = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
    "C:\Program Files\Inno Setup 5\ISCC.exe"
)

$innoSetupPath = $null
foreach ($path in $innoSetupPaths) {
    if (Test-Path $path) {
        $innoSetupPath = $path
        break
    }
}

if (-not $innoSetupPath) {
    Write-Host "❌ Inno Setup não encontrado!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Por favor, instale o Inno Setup Compiler:" -ForegroundColor Yellow
    Write-Host "  https://jrsoftware.org/isdl.php" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Ou use os instaladores Python/PowerShell diretamente." -ForegroundColor Yellow
    Write-Host ""
    pause
    exit 1
}

Write-Host "✅ Inno Setup encontrado: $innoSetupPath" -ForegroundColor Green
Write-Host ""

# Cria diretório dist se não existir
if (-not (Test-Path "dist")) {
    New-Item -ItemType Directory -Path "dist" | Out-Null
}

# Compila instalador do servidor
Write-Host "🔨 Criando instalador do SERVIDOR..." -ForegroundColor Yellow
Write-Host ""

$servidorScript = Join-Path $PSScriptRoot "serv\setup_servidor.iss"
if (-not (Test-Path $servidorScript)) {
    Write-Host "❌ Arquivo não encontrado: $servidorScript" -ForegroundColor Red
    exit 1
}

$result = & $innoSetupPath $servidorScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erro ao criar instalador do servidor!" -ForegroundColor Red
    Write-Host "   Saída: $result" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "✅ Instalador do servidor criado!" -ForegroundColor Green
Write-Host ""

# Compila instalador do agente
Write-Host "🔨 Criando instalador do AGENTE..." -ForegroundColor Yellow
Write-Host ""

$agenteScript = Join-Path $PSScriptRoot "agent\setup_agente.iss"
if (-not (Test-Path $agenteScript)) {
    Write-Host "❌ Arquivo não encontrado: $agenteScript" -ForegroundColor Red
    exit 1
}

$result = & $innoSetupPath $agenteScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Erro ao criar instalador do agente!" -ForegroundColor Red
    Write-Host "   Saída: $result" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "✅ Instalador do agente criado!" -ForegroundColor Green
Write-Host ""

# Resumo
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  INSTALADORES CRIADOS COM SUCESSO!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📦 Arquivos gerados em: dist\" -ForegroundColor Cyan
Write-Host "   - PrintMonitorServer_Setup.exe" -ForegroundColor White
Write-Host "   - PrintMonitorAgent_Setup.exe" -ForegroundColor White
Write-Host ""
Write-Host "💡 Distribua esses arquivos .exe para instalação!" -ForegroundColor Yellow
Write-Host ""

pause


