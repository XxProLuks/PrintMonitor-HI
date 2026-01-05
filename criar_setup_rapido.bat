@echo off
title Criar Instaladores Setup - Print Monitor
echo.
echo ========================================
echo   CRIAR INSTALADORES SETUP (.EXE)
echo   Print Monitor System
echo ========================================
echo.

REM Verifica se Inno Setup está instalado
set INNO_FOUND=0

if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
    set INNO_FOUND=1
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set INNO_PATH=C:\Program Files\Inno Setup 6\ISCC.exe
    set INNO_FOUND=1
) else if exist "C:\Program Files (x86)\Inno Setup 5\ISCC.exe" (
    set INNO_PATH=C:\Program Files (x86)\Inno Setup 5\ISCC.exe
    set INNO_FOUND=1
) else if exist "C:\Program Files\Inno Setup 5\ISCC.exe" (
    set INNO_PATH=C:\Program Files\Inno Setup 5\ISCC.exe
    set INNO_FOUND=1
)

if %INNO_FOUND%==0 (
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

echo Inno Setup encontrado: %INNO_PATH%
echo.

REM Cria diretório dist se não existir
if not exist "dist" mkdir dist

echo ========================================
echo   COMPILANDO INSTALADORES
echo ========================================
echo.

REM Compila instalador do servidor
echo [1/2] Compilando instalador do SERVIDOR...
echo.
"%INNO_PATH%" "serv\setup_servidor.iss"
if %errorLevel% neq 0 (
    echo.
    echo ERRO ao criar instalador do servidor!
    echo Verifique o arquivo serv\setup_servidor.iss
    pause
    exit /b 1
)
echo.
echo OK! Instalador do servidor criado.
echo.

REM Compila instalador do agente
echo [2/2] Compilando instalador do AGENTE...
echo.
"%INNO_PATH%" "agent\setup_agente.iss"
if %errorLevel% neq 0 (
    echo.
    echo ERRO ao criar instalador do agente!
    echo Verifique o arquivo agent\setup_agente.iss
    pause
    exit /b 1
)
echo.
echo OK! Instalador do agente criado.
echo.

REM Verifica se os arquivos foram criados
echo ========================================
echo   VERIFICANDO RESULTADOS
echo ========================================
echo.

if exist "dist\PrintMonitorServer_Setup.exe" (
    for %%A in ("dist\PrintMonitorServer_Setup.exe") do (
        echo [OK] PrintMonitorServer_Setup.exe
        echo      Tamanho: %%~zA bytes
    )
) else (
    echo [ERRO] PrintMonitorServer_Setup.exe nao encontrado!
)

if exist "dist\PrintMonitorAgent_Setup.exe" (
    for %%A in ("dist\PrintMonitorAgent_Setup.exe") do (
        echo [OK] PrintMonitorAgent_Setup.exe
        echo      Tamanho: %%~zA bytes
    )
) else (
    echo [ERRO] PrintMonitorAgent_Setup.exe nao encontrado!
)

echo.
echo ========================================
echo   INSTALADORES CRIADOS COM SUCESSO!
echo ========================================
echo.
echo Arquivos gerados em: dist\
echo.
echo   - PrintMonitorServer_Setup.exe
echo   - PrintMonitorAgent_Setup.exe
echo.
echo Pronto para distribuir!
echo.
pause


