# Script de deploy automatizado para producao (Windows PowerShell)
# Configura e inicia o servidor em producao

$ErrorActionPreference = "Stop"

Write-Host "======================================================================"
Write-Host "DEPLOY AUTOMATIZADO - PRINT MONITOR"
Write-Host "======================================================================"
Write-Host ""

# Diretorio base
$BASE_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $BASE_DIR

# 1. Verificar Python
Write-Host "Passo 1: Verificando Python..." -ForegroundColor Blue
try {
    $pythonVersion = python --version 2>&1
    Write-Host "OK: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERRO: Python nao encontrado!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 2. Criar arquivo .env se nao existir
Write-Host "Passo 2: Configurando arquivo .env..." -ForegroundColor Blue
if (-not (Test-Path ".env")) {
    Write-Host "   Criando arquivo .env..." -ForegroundColor Yellow
    
    # Gerar SECRET_KEY
    $secretKey = python -c "import secrets; print(secrets.token_hex(32))" 2>&1
    
    # Criar conteudo do .env
    $envContent = @"
# Configuracoes de Producao - Print Monitor
SECRET_KEY=$secretKey
FLASK_ENV=production
ENVIRONMENT=production
DEBUG=False
HOST=0.0.0.0
PORT=5002
DB_NAME=print_events.db
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
SESSION_LIFETIME=3600
DB_POOL_MAX_CONNECTIONS=10
DB_POOL_TIMEOUT=5.0
LOG_LEVEL=INFO
"@
    
    $envContent | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "OK: Arquivo .env criado com SECRET_KEY gerada" -ForegroundColor Green
} else {
    Write-Host "OK: Arquivo .env ja existe" -ForegroundColor Green
}
Write-Host ""

# 3. Instalar dependencias
Write-Host "Passo 3: Instalando dependencias..." -ForegroundColor Blue
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
pip install waitress --quiet
Write-Host "OK: Dependencias instaladas" -ForegroundColor Green
Write-Host ""

# 4. Criar diretorios necessarios
Write-Host "Passo 4: Criando diretorios..." -ForegroundColor Blue
New-Item -ItemType Directory -Force -Path "serv\backups" | Out-Null
New-Item -ItemType Directory -Force -Path "serv\logs" | Out-Null
Write-Host "OK: Diretorios criados" -ForegroundColor Green
Write-Host ""

# 5. Verificar banco de dados
Write-Host "Passo 5: Verificando banco de dados..." -ForegroundColor Blue
if (-not (Test-Path "serv\print_events.db")) {
    Write-Host "   Criando banco de dados..." -ForegroundColor Yellow
    Set-Location serv
    try {
        python -c "from servidor import init_db; init_db()" 2>&1 | Out-Null
    } catch {
        python recreate_database.py 2>&1 | Out-Null
    }
    Set-Location ..
    Write-Host "OK: Banco de dados criado" -ForegroundColor Green
} else {
    Write-Host "OK: Banco de dados ja existe" -ForegroundColor Green
}
Write-Host ""

# 6. Resumo
Write-Host "======================================================================"
Write-Host "DEPLOY CONCLUIDO COM SUCESSO!"
Write-Host "======================================================================"
Write-Host ""
Write-Host "Para iniciar o servidor, execute:"
Write-Host "   python start_production_waitress.py"
Write-Host ""
Write-Host "Ou use o script batch:"
Write-Host "   start_production_waitress.bat"
Write-Host ""
Write-Host "======================================================================"

