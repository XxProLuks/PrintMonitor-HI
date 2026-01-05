@echo off
REM Script wrapper para instalação do agente
REM Facilita a execução para usuários não técnicos

echo ========================================
echo   INSTALADOR DO AGENTE
echo ========================================
echo.

REM Verifica se PowerShell está disponível
powershell -Command "exit 0" >nul 2>&1
if errorlevel 1 (
    echo ERRO: PowerShell nao encontrado!
    pause
    exit /b 1
)

REM Executa o script PowerShell como administrador
powershell -ExecutionPolicy Bypass -File "%~dp0install_agent.ps1"

if errorlevel 1 (
    echo.
    echo ERRO na instalacao!
    pause
    exit /b 1
)

exit /b 0

