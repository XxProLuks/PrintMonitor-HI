# ============================================================================
# Script para Habilitar Event Log ID 307 Completamente
# Execute como Administrador
# ============================================================================

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "HABILITANDO EVENT LOG DE IMPRESSAO (ID 307)" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verifica se está como Admin
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[ERRO] Este script precisa ser executado como Administrador!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Solucao:" -ForegroundColor Yellow
    Write-Host "  1. Clique com botao direito no PowerShell" -ForegroundColor Yellow
    Write-Host "  2. Escolha 'Executar como Administrador'" -ForegroundColor Yellow
    Write-Host "  3. Execute este script novamente" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host "[OK] Executando como Administrador" -ForegroundColor Green
Write-Host ""

# 2. Habilita o Event Log
Write-Host "[1] Habilitando Event Log de PrintService..." -ForegroundColor Yellow

try {
    wevtutil set-log "Microsoft-Windows-PrintService/Operational" /enabled:true
    Write-Host "    [OK] Event Log habilitado" -ForegroundColor Green
} catch {
    Write-Host "    [ERRO] Falha ao habilitar: $_" -ForegroundColor Red
}

# 3. Aumenta tamanho do log (para não perder eventos)
Write-Host "[2] Aumentando tamanho do log..." -ForegroundColor Yellow

try {
    wevtutil set-log "Microsoft-Windows-PrintService/Operational" /maxsize:52428800
    Write-Host "    [OK] Tamanho aumentado para 50MB" -ForegroundColor Green
} catch {
    Write-Host "    [AVISO] Nao foi possivel aumentar tamanho" -ForegroundColor Yellow
}

# 4. Limpa eventos antigos (opcional)
Write-Host "[3] Deseja limpar eventos antigos? (Isso pode ajudar)" -ForegroundColor Yellow
Write-Host "    Digite 'S' para SIM ou 'N' para NAO: " -NoNewline
$resposta = Read-Host

if ($resposta -eq 'S' -or $resposta -eq 's') {
    try {
        wevtutil clear-log "Microsoft-Windows-PrintService/Operational"
        Write-Host "    [OK] Log limpo" -ForegroundColor Green
    } catch {
        Write-Host "    [ERRO] Falha ao limpar: $_" -ForegroundColor Red
    }
} else {
    Write-Host "    [INFO] Log nao foi limpo" -ForegroundColor Cyan
}

# 5. Reinicia o serviço de impressão
Write-Host "[4] Reiniciando servico de impressao..." -ForegroundColor Yellow

try {
    Restart-Service -Name Spooler -Force
    Write-Host "    [OK] Servico reiniciado" -ForegroundColor Green
} catch {
    Write-Host "    [ERRO] Falha ao reiniciar: $_" -ForegroundColor Red
}

# 6. Verifica configuração
Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "VERIFICACAO" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

$logInfo = wevtutil get-log "Microsoft-Windows-PrintService/Operational"

Write-Host "Configuracao atual:" -ForegroundColor White
Write-Host ""
Write-Host ($logInfo | Select-String "enabled")
Write-Host ($logInfo | Select-String "maxSize")
Write-Host ""

# 7. Testa captura
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "TESTE DE CAPTURA" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Agora faca uma impressao de teste..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Pressione Enter apos fazer a impressao..."
Read-Host

# Verifica se evento foi capturado
Write-Host "Verificando eventos..." -ForegroundColor Yellow

try {
    $eventos = Get-WinEvent -FilterHashtable @{
        LogName='Microsoft-Windows-PrintService/Operational'
        ID=307
        StartTime=(Get-Date).AddMinutes(-5)
    } -MaxEvents 10 -ErrorAction SilentlyContinue
    
    if ($eventos) {
        Write-Host ""
        Write-Host "[OK] EVENTO ID 307 DETECTADO!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Total de eventos nos ultimos 5 minutos: $($eventos.Count)" -ForegroundColor Green
        Write-Host ""
        Write-Host "Ultimo evento:" -ForegroundColor White
        $ultimo = $eventos[0]
        Write-Host "  TimeCreated: $($ultimo.TimeCreated)"
        Write-Host "  Message: $($ultimo.Message.Substring(0, [Math]::Min(200, $ultimo.Message.Length)))..."
        Write-Host ""
        Write-Host "[OK] O AGENTE VAI CAPTURAR AGORA!" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "[AVISO] Nenhum evento ID 307 encontrado" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Possiveis causas:" -ForegroundColor Yellow
        Write-Host "  1. Impressao nao gerou evento (muito rapida)" -ForegroundColor Yellow
        Write-Host "  2. Servico de log ainda nao sincronizou" -ForegroundColor Yellow
        Write-Host "  3. Impressora nao gera eventos ID 307" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Tente:" -ForegroundColor Yellow
        Write-Host "  1. Aguardar 30 segundos" -ForegroundColor Yellow
        Write-Host "  2. Fazer outra impressao" -ForegroundColor Yellow
        Write-Host "  3. Executar este script novamente" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[ERRO] Falha ao verificar eventos: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "PROXIMO PASSO" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Se viu '[OK] EVENTO ID 307 DETECTADO', inicie o agente:" -ForegroundColor White
Write-Host "   cd agent" -ForegroundColor Cyan
Write-Host "   python agente.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Se NAO viu evento, use modo WMI:" -ForegroundColor White
Write-Host "   python monitor_hibrido_completo.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Ou force modo WMI no agente:" -ForegroundColor White
Write-Host "   Edite config.json e adicione:" -ForegroundColor Cyan
Write-Host '   "use_wmi_backup": true' -ForegroundColor Cyan
Write-Host ""

