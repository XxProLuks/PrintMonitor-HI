@echo off
REM ============================================================================
REM INSTALADOR DO AGENTE EM REDE - INTERFACE SIMPLIFICADA
REM ============================================================================
REM Facilita a instalação do agente em múltiplos computadores da rede
REM ============================================================================

echo ============================================================================
echo   INSTALADOR DO AGENTE EM REDE
echo ============================================================================
echo.

REM Verifica se PowerShell está disponível
powershell -Command "exit 0" >nul 2>&1
if errorlevel 1 (
    echo ERRO: PowerShell nao encontrado!
    echo Instale o PowerShell 5.1 ou superior.
    pause
    exit /b 1
)

REM Executa o script PowerShell
powershell -ExecutionPolicy Bypass -File "%~dp0DEPLOY_REDE_COMPLETO.ps1" %*

if errorlevel 1 (
    echo.
    echo ERRO na execucao!
    pause
    exit /b 1
)

exit /b 0

