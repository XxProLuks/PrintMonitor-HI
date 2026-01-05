@echo off
REM Script para iniciar o servidor em produção usando Waitress (Windows)
REM Waitress é um servidor WSGI adequado para produção

echo ======================================================================
echo 🚀 INICIANDO SERVIDOR EM PRODUÇÃO (Waitress)
echo ======================================================================
echo.

REM Verifica se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERRO: Python não está instalado ou não está no PATH
    pause
    exit /b 1
)

REM Verifica se Waitress está instalado
python -c "import waitress" >nul 2>&1
if errorlevel 1 (
    echo ❌ ERRO: Waitress não está instalado!
    echo    Instale com: pip install waitress
    pause
    exit /b 1
)

REM Executa o script Python
python start_production_waitress.py

if errorlevel 1 (
    echo.
    echo ❌ ERRO ao iniciar servidor
    pause
    exit /b 1
)

pause

