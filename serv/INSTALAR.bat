@echo off
title Instalador do Servidor - Print Monitor
echo.
echo ========================================
echo   INSTALADOR DO SERVIDOR
echo   Sistema de Monitoramento de Impressao
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

echo Executando instalador PowerShell...
echo.

powershell.exe -ExecutionPolicy Bypass -File "%~dp0instalar_servidor.ps1" %*

if %errorLevel% neq 0 (
    echo.
    echo ERRO na instalacao!
    pause
    exit /b 1
)

echo.
echo Instalacao concluida!
pause

