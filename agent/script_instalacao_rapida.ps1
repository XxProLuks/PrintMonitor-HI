# ============================================================================
# SCRIPT DE INSTALAÇÃO RÁPIDA DO AGENTE
# ============================================================================
# Versão simplificada para instalação rápida em múltiplas máquinas
# ============================================================================

param(
    [Parameter(Mandatory=$false)]
    [string]$ServerURL = "http://192.168.1.27:5002/api/print_events",
    
    [Parameter(Mandatory=$false)]
    [string]$ComputerList = "",
    
    [Parameter(Mandatory=$false)]
    [string]$Domain = "",
    
    [switch]$Discover = $false,
    [switch]$Quick = $false
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  INSTALAÇÃO RÁPIDA DO AGENTE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Se modo Quick, usa configurações padrão
if ($Quick) {
    Write-Host "⚡ Modo RÁPIDO ativado" -ForegroundColor Yellow
    Write-Host ""
    
    if ($Discover) {
        Write-Host "🔍 Descobrindo computadores na rede..." -ForegroundColor Cyan
        .\DEPLOY_REDE_COMPLETO.ps1 `
            -Install `
            -Discover `
            -ServerURL $ServerURL `
            -EnableEventLog `
            -Force
    } else {
        Write-Host "❌ Modo Quick requer -Discover" -ForegroundColor Red
        Write-Host "   Use: .\script_instalacao_rapida.ps1 -Quick -Discover" -ForegroundColor Yellow
        exit 1
    }
    exit 0
}

# Modo interativo
Write-Host "Escolha o método de instalação:" -ForegroundColor Cyan
Write-Host "1. Lista de computadores (arquivo ou manual)" -ForegroundColor White
Write-Host "2. Descoberta automática na rede" -ForegroundColor White
Write-Host "3. Computadores específicos (digite nomes)" -ForegroundColor White
Write-Host ""

$opcao = Read-Host "Digite a opção (1-3)"

switch ($opcao) {
    "1" {
        if ([string]::IsNullOrEmpty($ComputerList)) {
            $ComputerList = Read-Host "Digite o caminho do arquivo com lista de computadores (ou deixe vazio para criar)"
        }
        
        if ([string]::IsNullOrEmpty($ComputerList)) {
            Write-Host "Criando arquivo de exemplo..." -ForegroundColor Yellow
            @"
# Lista de computadores para instalação
# Linhas começando com # são comentários
PC01
PC02
PC03
"@ | Out-File -FilePath "computadores.txt" -Encoding UTF8
            Write-Host "✅ Arquivo 'computadores.txt' criado. Edite e execute novamente." -ForegroundColor Green
            exit 0
        }
        
        .\DEPLOY_REDE_COMPLETO.ps1 `
            -Install `
            -ComputerListFile $ComputerList `
            -ServerURL $ServerURL `
            -EnableEventLog
    }
    
    "2" {
        Write-Host "🔍 Descobrindo computadores na rede..." -ForegroundColor Cyan
        .\DEPLOY_REDE_COMPLETO.ps1 `
            -Install `
            -Discover `
            -ServerURL $ServerURL `
            -EnableEventLog
    }
    
    "3" {
        $computersInput = Read-Host "Digite os nomes dos computadores (separados por vírgula)"
        $computers = $computersInput -split "," | ForEach-Object { $_.Trim() }
        
        if ($computers.Count -eq 0) {
            Write-Host "❌ Nenhum computador informado" -ForegroundColor Red
            exit 1
        }
        
        .\DEPLOY_REDE_COMPLETO.ps1 `
            -Install `
            -Computers $computers `
            -ServerURL $ServerURL `
            -EnableEventLog
    }
    
    default {
        Write-Host "❌ Opção inválida" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "✅ Instalação concluída!" -ForegroundColor Green
Write-Host ""
Write-Host "💡 Dica: Use o comando abaixo para verificar status:" -ForegroundColor Yellow
Write-Host "   .\DEPLOY_REDE_COMPLETO.ps1 -Status -ComputerListFile computadores.txt" -ForegroundColor Gray

