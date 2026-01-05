@echo off
setlocal enabledelayedexpansion
title Criar Instaladores - Print Monitor
color 0A
echo.
echo ========================================
echo   CRIAR INSTALADORES SETUP (.EXE)
echo   Print Monitor System
echo ========================================
echo.
echo Este script vai compilar os instaladores usando Inno Setup.
echo.
pause
echo.

REM Verifica se Inno Setup está instalado
set "INNO_SETUP_PATH="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "INNO_SETUP_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "INNO_SETUP_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files (x86)\Inno Setup 5\ISCC.exe" (
    set "INNO_SETUP_PATH=C:\Program Files (x86)\Inno Setup 5\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 5\ISCC.exe" (
    set "INNO_SETUP_PATH=C:\Program Files\Inno Setup 5\ISCC.exe"
) else (
    echo.
    echo ERRO: Inno Setup nao encontrado!
    echo.
    echo Por favor, instale o Inno Setup Compiler:
    echo   https://jrsoftware.org/isdl.php
    echo.
    echo Ou use os instaladores Python/PowerShell diretamente.
    echo.
    pause
    exit /b 1
)

echo Inno Setup encontrado: !INNO_SETUP_PATH!
echo.

REM Cria diretório dist se não existir
if not exist "dist" mkdir dist

echo Criando instalador do SERVIDOR...
echo.
"!INNO_SETUP_PATH!" "serv\setup_servidor.iss"
if !errorLevel! neq 0 (
    echo.
    echo ERRO ao criar instalador do servidor!
    pause
    exit /b 1
)

echo.
echo Criando instalador do AGENTE...
echo.
"!INNO_SETUP_PATH!" "agent\setup_agente.iss"
if !errorLevel! neq 0 (
    echo.
    echo ERRO ao criar instalador do agente!
    pause
    exit /b 1
)

echo.
echo ========================================
echo   INSTALADORES CRIADOS COM SUCESSO!
echo ========================================
echo.
echo Arquivos gerados em: dist\
echo   - PrintMonitorServer_Setup.exe
echo   - PrintMonitorAgent_Setup.exe
echo.
pause
