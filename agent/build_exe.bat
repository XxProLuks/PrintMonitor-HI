@echo off
REM Script para compilar agente em executável .exe

echo ========================================
echo COMPILANDO AGENTE EM EXECUTAVEL
echo ========================================
echo.

REM Verifica se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado!
    echo.
    echo Instale Python primeiro: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Verifica se PyInstaller está instalado
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo [INFO] PyInstaller nao encontrado. Instalando...
    pip install pyinstaller
    if errorlevel 1 (
        echo [ERRO] Falha ao instalar PyInstaller
        pause
        exit /b 1
    )
)

REM Compila
echo [INFO] Compilando agente.py em executavel...
echo.
python build_exe.py

if errorlevel 1 (
    echo.
    echo [ERRO] Compilacao falhou!
    pause
    exit /b 1
)

echo.
echo ========================================
echo COMPILACAO CONCLUIDA!
echo ========================================
echo.
echo O executavel esta em: dist\PrintMonitorAgent.exe
echo.
echo Use este .exe em vez de agente.py
echo Nao precisa de Python instalado nos computadores remotos!
echo.
pause

