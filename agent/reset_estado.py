"""
Script para resetar o estado do agente de monitoramento.

Este script:
1. Remove o arquivo agent_state.json (que contém o último record processado)
2. Limpa o cache de eventos 805 (se existir)
3. Força o agente a reprocessar todos os eventos na próxima execução

USO:
    python reset_estado.py

OU execute diretamente:
    python -c "import os; os.remove('agent/agent_state.json') if os.path.exists('agent/agent_state.json') else None; print('Estado resetado!')"
"""

import os
import sys
import json
from pathlib import Path

# Configura encoding UTF-8 para Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python < 3.7
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

def reset_agent_state():
    """Reseta o estado do agente"""
    # Pega o diretório do script
    script_dir = Path(__file__).parent
    state_file = script_dir / "agent_state.json"
    
    print("=" * 60)
    print("   RESET DO ESTADO DO AGENTE DE MONITORAMENTO")
    print("=" * 60)
    print()
    
    # Verifica se o arquivo existe
    if state_file.exists():
        try:
            # Lê o estado atual para mostrar informações
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
                last_record = state.get('highest_record_processed', 0)
                last_update = state.get('last_update', 'N/A')
                print(f"📊 Estado atual:")
                print(f"   - Último record processado: {last_record}")
                print(f"   - Última atualização: {last_update}")
                print()
            
            # Remove o arquivo
            os.remove(state_file)
            print("✅ Arquivo agent_state.json removido com sucesso!")
            print()
            print("⚠️  ATENÇÃO:")
            print("   - O agente irá reprocessar TODOS os eventos na próxima execução")
            print("   - Isso pode gerar duplicatas no servidor se os eventos já foram enviados")
            print("   - Use apenas se quiser forçar uma sincronização completa")
            print()
            print("💡 Dica: Para evitar duplicatas, use a opção --force no servidor")
            print("   ou limpe os dados antigos antes de executar o agente novamente")
            
        except Exception as e:
            print(f"❌ Erro ao remover arquivo: {e}")
            return False
    else:
        print("ℹ️  Arquivo agent_state.json não encontrado")
        print("   O agente já está sem estado (processará todos os eventos)")
    
    print()
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = reset_agent_state()
    sys.exit(0 if success else 1)

