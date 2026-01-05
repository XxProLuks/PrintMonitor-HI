@echo off
title Print Monitor Server
cd /d "%~dp0"
echo Iniciando servidor de monitoramento...
python servidor.py
if %errorLevel% neq 0 (
    echo.
    echo Erro ao iniciar servidor!
    pause
)


