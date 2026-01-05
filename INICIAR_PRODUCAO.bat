@echo off
REM Script para iniciar o servidor em producao
REM Execute este arquivo para iniciar o Print Monitor em producao

echo ======================================================================
echo INICIANDO PRINT MONITOR EM PRODUCAO
echo ======================================================================
echo.
echo Servidor sera iniciado na porta 5002
echo Acesse: http://localhost:5002
echo.
echo Credenciais:
echo   Usuario: admin
echo   Senha: 157398
echo.
echo Para parar o servidor, feche esta janela ou pressione Ctrl+C
echo.
echo ======================================================================
echo.

python start_production_waitress.py

pause

