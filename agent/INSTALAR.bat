@echo off
title Instalador do Agente - Print Monitor
echo.
echo ========================================
echo   INSTALADOR DO AGENTE
echo   Monitoramento de Impressao
echo ========================================
echo.

REM Verifica se está executando como administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERRO: Este script precisa ser executado como Administrador!
    echo.
    echo Clique com botao direito e selecione "Executar como administrador"
    pause
    exit /b 1
)

set SERVER_URL=http://192.168.1.27:5002/api/print_events

echo.
echo Configuracao do servidor:
echo   URL: %SERVER_URL%
echo.
set /p SERVER_URL="Digite a URL do servidor (ou Enter para usar o padrao): "
if "%SERVER_URL%"=="" set SERVER_URL=http://192.168.1.27:5002/api/print_events

echo.
echo Executando instalador PowerShell...
echo.

powershell.exe -ExecutionPolicy Bypass -File "%~dp0instalar_agente.ps1" -ServerURL "%SERVER_URL%"

if %errorLevel% neq 0 (
    echo.
    echo ERRO na instalacao!
    pause
    exit /b 1
)

echo.
echo Instalacao concluida!
pause

