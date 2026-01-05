@echo off
setlocal enabledelayedexpansion
title Restaurar Instaladores Originais
color 0E
echo.
echo ========================================
echo   RESTAURAR INSTALADORES ORIGINAIS
echo   Print Monitor System
echo ========================================
echo.
echo Este script vai restaurar os arquivos originais
echo a partir dos backups criados.
echo.
pause
echo.

REM Restaura agente
if exist "agent\setup_agente.iss.backup" (
    copy "agent\setup_agente.iss.backup" "agent\setup_agente.iss" >nul
    if !errorLevel! equ 0 (
        echo   [OK] Restaurado: agent\setup_agente.iss
    ) else (
        echo   [ERRO] Falha ao restaurar agent\setup_agente.iss
    )
) else (
    echo   [AVISO] Backup de agent\setup_agente.iss nao encontrado
)

REM Restaura servidor
if exist "serv\setup_servidor.iss.backup" (
    copy "serv\setup_servidor.iss.backup" "serv\setup_servidor.iss" >nul
    if !errorLevel! equ 0 (
        echo   [OK] Restaurado: serv\setup_servidor.iss
    ) else (
        echo   [ERRO] Falha ao restaurar serv\setup_servidor.iss
    )
) else (
    echo   [AVISO] Backup de serv\setup_servidor.iss nao encontrado
)

echo.
echo ========================================
echo   RESTAURACAO CONCLUIDA!
echo ========================================
echo.
pause

