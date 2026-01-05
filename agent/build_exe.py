"""
Script para compilar agente.py em executável .exe
Isso elimina a necessidade de Python instalado nos computadores remotos
"""

import PyInstaller.__main__
import sys
import os
from pathlib import Path

def build_exe():
    """Compila agente.py em executável"""
    
    agent_path = Path(__file__).parent
    agent_script = agent_path / "agente.py"
    
    if not agent_script.exists():
        print("❌ Erro: agente.py não encontrado!")
        return False
    
    print("🔨 Compilando agente.py em executável...")
    print("   Isso pode demorar alguns minutos...")
    print()
    
    # Opções do PyInstaller
    options = [
        str(agent_script),
        '--name=PrintMonitorAgent',
        '--onefile',  # Cria um único arquivo .exe
        '--windowed',  # Sem console (executa em background)
        '--noconfirm',  # Não pede confirmação
        '--clean',  # Limpa cache antes de compilar
        '--distpath=dist',  # Pasta de saída
        '--workpath=build',  # Pasta temporária
        '--specpath=build',  # Pasta para .spec
        '--add-data=config.json;.',  # Inclui config.json
        '--hidden-import=win32evtlog',  # Importa módulo necessário
        '--hidden-import=win32evtlogutil',
        '--hidden-import=win32api',
        '--hidden-import=win32con',
        '--hidden-import=win32security',
        '--hidden-import=requests',
        '--hidden-import=json',
        '--hidden-import=threading',
        '--hidden-import=time',
        '--hidden-import=datetime',
        '--hidden-import=logging',
        '--hidden-import=pathlib',
    ]
    
    try:
        PyInstaller.__main__.run(options)
        
        exe_path = agent_path / "dist" / "PrintMonitorAgent.exe"
        if exe_path.exists():
            print()
            print("✅ Compilação concluída com sucesso!")
            print(f"   Executável criado em: {exe_path}")
            print()
            print("📦 Próximos passos:")
            print("   1. O executável está em: dist/PrintMonitorAgent.exe")
            print("   2. Use este .exe em vez de agente.py")
            print("   3. Não precisa de Python instalado nos computadores remotos!")
            return True
        else:
            print("❌ Erro: Executável não foi criado")
            return False
            
    except Exception as e:
        print(f"❌ Erro durante compilação: {e}")
        print()
        print("💡 Solução:")
        print("   1. Instale PyInstaller: pip install pyinstaller")
        print("   2. Execute novamente este script")
        return False


if __name__ == "__main__":
    # Verifica se PyInstaller está instalado
    try:
        import PyInstaller
    except ImportError:
        print("❌ PyInstaller não está instalado!")
        print()
        print("📦 Para instalar:")
        print("   pip install pyinstaller")
        print()
        sys.exit(1)
    
    success = build_exe()
    sys.exit(0 if success else 1)

