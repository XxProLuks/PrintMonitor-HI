@echo off
setlocal enabledelayedexpansion
title Usar Instaladores Completos
color 0B
echo.
echo ========================================
echo   SUBSTITUIR POR INSTALADORES COMPLETOS
echo   Print Monitor System
echo ========================================
echo.
echo Este script vai:
echo   1. Fazer backup dos arquivos originais
echo   2. Substituir pelos instaladores completos
echo   3. Verificar se os arquivos existem
echo.
pause
echo.

REM Verifica se os arquivos completos existem
if not exist "agent\setup_agente_completo.iss" (
    echo ERRO: agent\setup_agente_completo.iss nao encontrado!
    pause
    exit /b 1
)

if not exist "serv\setup_servidor_completo.iss" (
    echo ERRO: serv\setup_servidor_completo.iss nao encontrado!
    pause
    exit /b 1
)

echo Fazendo backup dos arquivos originais...
echo.

REM Backup do agente
if exist "agent\setup_agente.iss" (
    copy "agent\setup_agente.iss" "agent\setup_agente.iss.backup" >nul
    if !errorLevel! equ 0 (
        echo   [OK] Backup: agent\setup_agente.iss
    ) else (
        echo   [ERRO] Falha ao fazer backup de agent\setup_agente.iss
    )
) else (
    echo   [AVISO] agent\setup_agente.iss nao existe (primeira vez)
)

REM Backup do servidor
if exist "serv\setup_servidor.iss" (
    copy "serv\setup_servidor.iss" "serv\setup_servidor.iss.backup" >nul
    if !errorLevel! equ 0 (
        echo   [OK] Backup: serv\setup_servidor.iss
    ) else (
        echo   [ERRO] Falha ao fazer backup de serv\setup_servidor.iss
    )
) else (
    echo   [AVISO] serv\setup_servidor.iss nao existe (primeira vez)
)

echo.
echo Substituindo pelos instaladores completos...
echo.

REM Substitui agente
copy "agent\setup_agente_completo.iss" "agent\setup_agente.iss" >nul
if !errorLevel! equ 0 (
    echo   [OK] Substituido: agent\setup_agente.iss
) else (
    echo   [ERRO] Falha ao substituir agent\setup_agente.iss
    pause
    exit /b 1
)

REM Substitui servidor
copy "serv\setup_servidor_completo.iss" "serv\setup_servidor.iss" >nul
if !errorLevel! equ 0 (
    echo   [OK] Substituido: serv\setup_servidor.iss
) else (
    echo   [ERRO] Falha ao substituir serv\setup_servidor.iss
    pause
    exit /b 1
)

echo.
echo ========================================
echo   SUBSTITUICAO CONCLUIDA!
echo ========================================
echo.
echo Arquivos substituidos com sucesso!
echo.
echo Agora voce pode compilar os instaladores:
echo   criar_instaladores.bat
echo.
echo Ou restaurar os originais:
echo   copy agent\setup_agente.iss.backup agent\setup_agente.iss
echo   copy serv\setup_servidor.iss.backup serv\setup_servidor.iss
echo.
pause

