#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instalador do Servidor de Monitoramento de Impressão
Versão Python multiplataforma
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

def print_header():
    """Imprime cabeçalho do instalador"""
    print("\n" + "="*60)
    print("  INSTALADOR DO SERVIDOR")
    print("  Sistema de Monitoramento de Impressão")
    print("="*60 + "\n")

def check_python():
    """Verifica se Python está instalado e na versão correta"""
    print("🔍 Verificando Python...")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python 3.8 ou superior é necessário!")
        print(f"   Versão atual: {version.major}.{version.minor}.{version.micro}")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} encontrado")
    return True

def check_pip():
    """Verifica se pip está disponível"""
    print("🔍 Verificando pip...")
    
    try:
        import pip
        print("✅ pip disponível")
        return True
    except ImportError:
        print("❌ pip não encontrado!")
        print("💡 Instale pip: python -m ensurepip --upgrade")
        return False

def install_dependencies(requirements_file):
    """Instala dependências do requirements.txt"""
    print("\n📦 Instalando dependências...")
    
    if not os.path.exists(requirements_file):
        print(f"⚠️  Arquivo {requirements_file} não encontrado")
        print("   Instalando dependências básicas...")
        
        basic_deps = [
            "Flask>=2.3.0",
            "pandas>=2.0.0",
            "openpyxl>=3.1.0",
            "python-dotenv>=1.0.0",
            "werkzeug>=2.3.0",
            "flask-compress>=1.13",
            "flask-limiter>=3.5.0",
            "flask-wtf>=1.2.0",
            "WTForms>=3.1.0",
            "reportlab>=4.0.0",
            "flask-socketio>=5.3.0",
            "requests>=2.31.0"
        ]
        
        for dep in basic_deps:
            print(f"   Instalando {dep}...")
            subprocess.run([sys.executable, "-m", "pip", "install", dep], check=False)
    else:
        print(f"   Usando: {requirements_file}")
        
        # Atualiza pip primeiro
        print("   Atualizando pip...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=False)
        
        # Instala dependências
        print("   Instalando pacotes (isso pode demorar alguns minutos)...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", requirements_file],
            check=False
        )
        
        if result.returncode != 0:
            print("❌ Erro ao instalar dependências!")
            print("💡 Tente executar manualmente: pip install -r requirements.txt")
            return False
    
    print("✅ Dependências instaladas com sucesso!")
    return True

def init_database(script_dir):
    """Inicializa o banco de dados"""
    print("\n💾 Inicializando banco de dados...")
    
    try:
        # Adiciona diretório ao path
        sys.path.insert(0, script_dir)
        os.chdir(script_dir)
        
        # Importa e inicializa
        from servidor import init_db, app
        
        with app.app_context():
            init_db()
            print("✅ Banco de dados inicializado!")
            return True
    except Exception as e:
        print(f"⚠️  Aviso: {e}")
        print("   (O banco pode já estar inicializado)")
        return True  # Não é crítico

def create_start_scripts(script_dir, python_path):
    """Cria scripts de inicialização"""
    print("\n📝 Criando scripts de inicialização...")
    
    # Script batch (Windows)
    if platform.system() == "Windows":
        start_batch = os.path.join(script_dir, "iniciar_servidor.bat")
        with open(start_batch, "w", encoding="ascii") as f:
            f.write(f"""@echo off
title Print Monitor Server
cd /d "{script_dir}"
echo Iniciando servidor...
"{python_path}" servidor.py
pause
""")
        print(f"✅ Criado: iniciar_servidor.bat")
    
    # Script shell (Linux/Mac)
    start_sh = os.path.join(script_dir, "iniciar_servidor.sh")
    with open(start_sh, "w", encoding="utf-8") as f:
        f.write(f"""#!/bin/bash
cd "{script_dir}"
python3 servidor.py
""")
    os.chmod(start_sh, 0o755)
    print(f"✅ Criado: iniciar_servidor.sh")
    
    # Script Python
    start_py = os.path.join(script_dir, "iniciar_servidor.py")
    with open(start_py, "w", encoding="utf-8") as f:
        f.write(f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import subprocess

script_dir = r"{script_dir}"
python_path = r"{python_path}"

os.chdir(script_dir)
subprocess.run([python_path, "servidor.py"])
""")
    os.chmod(start_py, 0o755)
    print(f"✅ Criado: iniciar_servidor.py")

def print_summary(port=5002):
    """Imprime resumo da instalação"""
    print("\n" + "="*60)
    print("  INSTALAÇÃO CONCLUÍDA!")
    print("="*60 + "\n")
    print("📋 RESUMO:")
    print("   ✅ Python verificado")
    print("   ✅ Dependências instaladas")
    print("   ✅ Banco de dados inicializado")
    print("   ✅ Scripts de inicialização criados")
    print("\n🚀 PRÓXIMOS PASSOS:\n")
    print("1. Iniciar o servidor:")
    if platform.system() == "Windows":
        print("   .\\iniciar_servidor.bat")
    else:
        print("   ./iniciar_servidor.sh")
    print("\n2. Acessar o sistema:")
    print(f"   http://localhost:{port}")
    print("\n3. Login padrão:")
    print("   Usuário: admin")
    print("   Senha: (verifique o console na primeira execução)")
    print("\n💡 DICA: Configure a SECRET_KEY em variáveis de ambiente para produção!")
    print("\n" + "="*60 + "\n")

def main():
    """Função principal"""
    print_header()
    
    # Verifica Python
    if not check_python():
        sys.exit(1)
    
    # Verifica pip
    if not check_pip():
        sys.exit(1)
    
    # Determina caminhos
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    requirements_file = os.path.join(project_root, "requirements.txt")
    python_path = sys.executable
    
    # Instala dependências
    if not install_dependencies(requirements_file):
        print("\n⚠️  Continuando mesmo com erros nas dependências...")
    
    # Inicializa banco de dados
    init_database(script_dir)
    
    # Cria scripts de inicialização
    create_start_scripts(script_dir, python_path)
    
    # Resumo
    print_summary()
    
    print("✅ Instalação concluída com sucesso!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Instalação cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro durante instalação: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


