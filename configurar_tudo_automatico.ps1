# Script para configurar tudo automaticamente (Windows)
# Configura firewall, altera senha e prepara para HTTPS

$ErrorActionPreference = "Stop"

Write-Host "======================================================================"
Write-Host "CONFIGURACAO AUTOMATICA COMPLETA - PRINT MONITOR"
Write-Host "======================================================================"
Write-Host ""

# 1. Configurar Firewall
Write-Host "Passo 1: Configurando firewall..." -ForegroundColor Blue
$rule = Get-NetFirewallRule -DisplayName "Print Monitor" -ErrorAction SilentlyContinue
if ($rule) {
    Write-Host "OK: Regra de firewall ja existe" -ForegroundColor Green
} else {
    try {
        New-NetFirewallRule -DisplayName "Print Monitor" -Direction Inbound -LocalPort 5002 -Protocol TCP -Action Allow -Description "Print Monitor Server" | Out-Null
        Write-Host "OK: Regra de firewall criada para porta 5002" -ForegroundColor Green
    } catch {
        Write-Host "AVISO: Nao foi possivel criar regra de firewall automaticamente" -ForegroundColor Yellow
        Write-Host "   Execute manualmente como Administrador:" -ForegroundColor Yellow
        Write-Host "   New-NetFirewallRule -DisplayName 'Print Monitor' -Direction Inbound -LocalPort 5002 -Protocol TCP -Action Allow" -ForegroundColor Yellow
    }
}
Write-Host ""

# 2. Gerar senha segura e alterar senha do admin
Write-Host "Passo 2: Alterando senha do administrador..." -ForegroundColor Blue
$novaSenha = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 16 | ForEach-Object {[char]$_})
Write-Host "   Gerando senha segura..." -ForegroundColor Yellow
python alterar_senha_admin.py $novaSenha
Write-Host ""
Write-Host "IMPORTANTE: Guarde estas credenciais!" -ForegroundColor Yellow
Write-Host "   Usuario: admin" -ForegroundColor Cyan
Write-Host "   Senha: $novaSenha" -ForegroundColor Cyan
Write-Host ""
$salvar = Read-Host "Deseja salvar as credenciais em um arquivo? (s/N)"
if ($salvar -eq "s") {
    $credenciais = @"
Print Monitor - Credenciais de Acesso
======================================
Usuario: admin
Senha: $novaSenha
Data: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

IMPORTANTE: Guarde este arquivo em local seguro!
"@
    $credenciais | Out-File -FilePath "credenciais_admin.txt" -Encoding UTF8
    Write-Host "OK: Credenciais salvas em credenciais_admin.txt" -ForegroundColor Green
    Write-Host "   IMPORTANTE: Delete este arquivo apos anotar as credenciais!" -ForegroundColor Yellow
}
Write-Host ""

# 3. Criar arquivo de configuração de domínio
Write-Host "Passo 3: Criando configuracoes de dominio..." -ForegroundColor Blue
$dominio = Read-Host "Digite o dominio (ou pressione Enter para pular): "
if ($dominio) {
    $configDominio = @"
# Configuracao de Dominio - Print Monitor
DOMINIO=$dominio
SERVER_URL=https://$dominio
AGENT_SERVER_URL=https://$dominio/api/print_events

# Para configurar HTTPS, veja:
# - configurar_https.sh (Linux)
# - GUIA_DEPLOY_RAPIDO.md
"@
    $configDominio | Out-File -FilePath "config_dominio.env" -Encoding UTF8
    Write-Host "OK: Configuracao de dominio salva em config_dominio.env" -ForegroundColor Green
    Write-Host ""
    Write-Host "Para configurar HTTPS:" -ForegroundColor Yellow
    Write-Host "   1. Configure DNS apontando para este servidor" -ForegroundColor Yellow
    Write-Host "   2. No Linux, execute: sudo ./configurar_https.sh" -ForegroundColor Yellow
    Write-Host "   3. Veja GUIA_DEPLOY_RAPIDO.md para mais detalhes" -ForegroundColor Yellow
} else {
    Write-Host "OK: Configuracao de dominio pulada" -ForegroundColor Green
}
Write-Host ""

# 4. Resumo
Write-Host "======================================================================"
Write-Host "CONFIGURACAO AUTOMATICA CONCLUIDA!"
Write-Host "======================================================================"
Write-Host ""
Write-Host "Configuracoes aplicadas:" -ForegroundColor Green
Write-Host "  - Firewall: Porta 5002 aberta"
Write-Host "  - Senha do admin: Alterada"
if ($dominio) {
    Write-Host "  - Dominio: $dominio configurado"
}
Write-Host ""
Write-Host "Proximos passos:" -ForegroundColor Yellow
Write-Host "  1. Inicie o servidor: python start_production_waitress.py"
Write-Host "  2. Acesse: http://localhost:5002"
Write-Host "  3. Faca login com as credenciais geradas"
if ($dominio) {
    Write-Host "  4. Configure HTTPS seguindo as instrucoes em config_dominio.env"
}
Write-Host ""
Write-Host "======================================================================"

