@echo off
title Verificar Inicio Automatico - Print Monitor Agent
echo.
echo Verificando configuracao de inicio automatico...
echo.

powershell.exe -ExecutionPolicy Bypass -File "%~dp0verificar_inicio_automatico.ps1"

pause

