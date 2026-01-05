@echo off
title Print Monitor Agent
cd /d "%~dp0"
echo Iniciando agente de monitoramento...
python agente.py
if %errorLevel% neq 0 (
    echo.
    echo Erro ao iniciar agente!
    pause
)


