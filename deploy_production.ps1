# Script de deploy automatizado para produção (Windows PowerShell)
# Configura e inicia o servidor em produção

$ErrorActionPreference = "Stop"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "🚀 DEPLOY AUTOMATIZADO - PRINT MONITOR" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Diretório base
$BASE_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $BASE_DIR

# 1. Verificar Python
Write-Host "📋 Passo 1: Verificando Python..." -ForegroundColor Blue
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python não encontrado!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 2. Verificar/Criar ambiente virtual
Write-Host "📋 Passo 2: Configurando ambiente virtual..." -ForegroundColor Blue
if (-not (Test-Path "venv")) {
    Write-Host "   Criando ambiente virtual..." -ForegroundColor Yellow
    python -m venv venv
}
& "venv\Scripts\Activate.ps1"
Write-Host "✅ Ambiente virtual ativado" -ForegroundColor Green
Write-Host ""

# 3. Instalar dependências
Write-Host "📋 Passo 3: Instalando dependências..." -ForegroundColor Blue
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install waitress  # Servidor WSGI para Windows
Write-Host "✅ Dependências instaladas" -ForegroundColor Green
Write-Host ""

# 4. Verificar/Criar arquivo .env
Write-Host "📋 Passo 4: Configurando variáveis de ambiente..." -ForegroundColor Blue
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.production") {
        Write-Host "   Copiando .env.production para .env..." -ForegroundColor Yellow
        Copy-Item ".env.production" ".env"
        Write-Host "⚠️  IMPORTANTE: Revise o arquivo .env e ajuste as configurações!" -ForegroundColor Yellow
    } else {
        Write-Host "❌ Arquivo .env não encontrado e .env.production não existe!" -ForegroundColor Red
        Write-Host "   Crie um arquivo .env baseado em env.example" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✅ Arquivo .env já existe" -ForegroundColor Green
}

# Verifica SECRET_KEY
$envContent = Get-Content ".env" -Raw
if ($envContent -notmatch "SECRET_KEY=.*" -or $envContent -match "SECRET_KEY=sua-chave-secreta") {
    Write-Host "⚠️  SECRET_KEY não configurada ou usando valor padrão" -ForegroundColor Yellow
    Write-Host "   Gerando nova SECRET_KEY..." -ForegroundColor Yellow
    python gerar_secret_key.py
    Write-Host "   Adicione a SECRET_KEY gerada ao arquivo .env" -ForegroundColor Yellow
    Read-Host "   Pressione Enter após adicionar a SECRET_KEY ao .env"
}
Write-Host ""

# 5. Criar diretórios necessários
Write-Host "📋 Passo 5: Criando diretórios..." -ForegroundColor Blue
New-Item -ItemType Directory -Force -Path "serv\backups" | Out-Null
New-Item -ItemType Directory -Force -Path "serv\logs" | Out-Null
Write-Host "✅ Diretórios criados" -ForegroundColor Green
Write-Host ""

# 6. Inicializar banco de dados
Write-Host "📋 Passo 6: Verificando banco de dados..." -ForegroundColor Blue
if (-not (Test-Path "serv\print_events.db")) {
    Write-Host "   Criando banco de dados..." -ForegroundColor Yellow
    Set-Location serv
    try {
        python -c "from servidor import init_db; init_db()"
    } catch {
        python recreate_database.py
    }
    Set-Location ..
    Write-Host "✅ Banco de dados criado" -ForegroundColor Green
} else {
    Write-Host "✅ Banco de dados já existe" -ForegroundColor Green
}
Write-Host ""

# 7. Resumo
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "✅ DEPLOY CONCLUÍDO COM SUCESSO!" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Próximos passos:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Revise o arquivo .env e ajuste as configurações:"
Write-Host "   - SECRET_KEY (já configurada)"
Write-Host "   - FLASK_ENV=production"
Write-Host "   - DEBUG=False"
Write-Host "   - SESSION_COOKIE_SECURE=True (se usar HTTPS)"
Write-Host ""
Write-Host "2. Para iniciar o servidor:"
Write-Host "   - Execute: start_production_waitress.bat"
Write-Host "   - Ou: python start_production_waitress.py"
Write-Host ""
Write-Host "3. Configure firewall (se necessário):"
Write-Host "   New-NetFirewallRule -DisplayName 'Print Monitor' -Direction Inbound -LocalPort 5002 -Protocol TCP -Action Allow"
Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan

