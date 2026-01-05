@echo off
REM Script para resetar o estado do agente (Windows)
REM Remove o arquivo agent_state.json para forçar reprocessamento completo

echo ============================================================
echo    RESET DO ESTADO DO AGENTE DE MONITORAMENTO
echo ============================================================
echo.

cd /d "%~dp0"

if exist "agent_state.json" (
    echo [INFO] Arquivo agent_state.json encontrado.
    echo [INFO] Removendo arquivo...
    del /F /Q "agent_state.json"
    
    if not exist "agent_state.json" (
        echo.
        echo [OK] Estado resetado com sucesso!
        echo.
        echo [ATENCAO] O agente ira reprocessar TODOS os eventos na proxima execucao.
        echo [ATENCAO] Isso pode gerar duplicatas no servidor se os eventos ja foram enviados.
        echo.
        echo [DICA] Para evitar duplicatas, limpe os dados antigos no servidor antes
        echo        de executar o agente novamente.
    ) else (
        echo [ERRO] Falha ao remover arquivo agent_state.json
        exit /b 1
    )
) else (
    echo [INFO] Arquivo agent_state.json nao encontrado.
    echo [INFO] O agente ja esta sem estado (processara todos os eventos).
)

echo.
echo ============================================================
pause

