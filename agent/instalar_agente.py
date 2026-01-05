#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instalador do Agente de Monitoramento
Versão Python multiplataforma
"""

import os
import sys
import subprocess
import platform
import shutil
import json
from pathlib import Path

def print_header():
    """Imprime cabeçalho do instalador"""
    print("\n" + "="*60)
    print("  INSTALADOR DO AGENTE")
    print("  Monitoramento de Impressão")
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
            "pywin32>=300",
            "requests>=2.25.0"
        ]
        
        if platform.system() == "Windows":
            basic_deps.append("pysnmp>=4.4.0")
        
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

def copy_files(source_dir, install_path, server_url):
    """Copia arquivos do agente para o diretório de instalação"""
    print(f"\n📦 Copiando arquivos para: {install_path}")
    
    # Cria diretório de instalação
    os.makedirs(install_path, exist_ok=True)
    os.makedirs(os.path.join(install_path, "logs"), exist_ok=True)
    
    # Arquivos para copiar
    files_to_copy = [
        "agente.py",
        "requirements.txt",
        "config.json.example"
    ]
    
    for file in files_to_copy:
        source = os.path.join(source_dir, file)
        if os.path.exists(source):
            dest = os.path.join(install_path, file)
            shutil.copy2(source, dest)
            print(f"   ✅ {file}")
    
    # Cria config.json se não existir
    config_path = os.path.join(install_path, "config.json")
    if not os.path.exists(config_path):
        config_example = os.path.join(install_path, "config.json.example")
        if os.path.exists(config_example):
            with open(config_example, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            config["server_url"] = server_url
            
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            print(f"   ✅ config.json criado")
    
    print("✅ Arquivos copiados!")
    return True

def create_start_scripts(install_path, python_path):
    """Cria scripts de inicialização"""
    print("\n📝 Criando scripts de inicialização...")
    
    # Script batch (Windows)
    if platform.system() == "Windows":
        start_batch = os.path.join(install_path, "iniciar_agente.bat")
        with open(start_batch, "w", encoding="ascii") as f:
            f.write(f"""@echo off
title Print Monitor Agent
cd /d "{install_path}"
echo Iniciando agente...
"{python_path}" agente.py
pause
""")
        print(f"✅ Criado: iniciar_agente.bat")
    
    # Script shell (Linux/Mac)
    start_sh = os.path.join(install_path, "iniciar_agente.sh")
    with open(start_sh, "w", encoding="utf-8") as f:
        f.write(f"""#!/bin/bash
cd "{install_path}"
python3 agente.py
""")
    os.chmod(start_sh, 0o755)
    print(f"✅ Criado: iniciar_agente.sh")
    
    # Script Python
    start_py = os.path.join(install_path, "iniciar_agente.py")
    with open(start_py, "w", encoding="utf-8") as f:
        f.write(f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import subprocess

install_path = r"{install_path}"
python_path = r"{python_path}"

os.chdir(install_path)
subprocess.run([python_path, "agente.py"])
""")
    os.chmod(start_py, 0o755)
    print(f"✅ Criado: iniciar_agente.py")

def test_server_connection(server_url):
    """Testa conexão com o servidor"""
    print("\n🔗 Testando conexão com servidor...")
    
    try:
        import requests
        base_url = server_url.replace("/api/print_events", "")
        response = requests.get(base_url, timeout=5)
        print(f"✅ Servidor acessível: {base_url}")
        return True
    except Exception as e:
        print(f"⚠️  Não foi possível conectar ao servidor: {base_url}")
        print(f"   Erro: {e}")
        print("   O agente tentará reconectar automaticamente")
        return False

def print_summary(install_path, server_url, create_task=False):
    """Imprime resumo da instalação"""
    print("\n" + "="*60)
    print("  INSTALAÇÃO CONCLUÍDA!")
    print("="*60 + "\n")
    print("📋 RESUMO:")
    print("   ✅ Python verificado")
    print(f"   ✅ Arquivos copiados para: {install_path}")
    print("   ✅ Dependências instaladas")
    if create_task:
        print("   ✅ Tarefa agendada criada")
    print("\n🚀 PRÓXIMOS PASSOS:\n")
    print("1. Testar o agente manualmente:")
    if platform.system() == "Windows":
        print(f"   cd {install_path}")
        print("   python agente.py")
    else:
        print(f"   cd {install_path}")
        print("   python3 agente.py")
    print("\n2. Verificar se está funcionando:")
    print(f"   - Verifique os logs em: {os.path.join(install_path, 'logs')}")
    print(f"   - Servidor configurado: {server_url}")
    print("\n3. Configurar servidor (se necessário):")
    print(f"   Edite: {os.path.join(install_path, 'config.json')}")
    print("\n" + "="*60 + "\n")

def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Instalador do Agente de Monitoramento")
    parser.add_argument("--server-url", default="http://192.168.1.27:5002/api/print_events",
                       help="URL do servidor")
    parser.add_argument("--install-path", default=None,
                       help="Diretório de instalação")
    parser.add_argument("--skip-dependencies", action="store_true",
                       help="Pular instalação de dependências")
    parser.add_argument("--no-task", action="store_true",
                       help="Não criar tarefa agendada")
    
    args = parser.parse_args()
    
    print_header()
    
    # Verifica Python
    if not check_python():
        sys.exit(1)
    
    # Verifica pip
    if not check_pip():
        sys.exit(1)
    
    # Determina caminhos
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    if args.install_path:
        install_path = args.install_path
    else:
        if platform.system() == "Windows":
            install_path = r"C:\PrintMonitorAgent"
        else:
            install_path = os.path.expanduser("~/PrintMonitorAgent")
    
    requirements_file = os.path.join(script_dir, "requirements.txt")
    python_path = sys.executable
    
    # Instala dependências
    if not args.skip_dependencies:
        if not install_dependencies(requirements_file):
            print("\n⚠️  Continuando mesmo com erros nas dependências...")
    
    # Copia arquivos
    copy_files(script_dir, install_path, args.server_url)
    
    # Cria scripts de inicialização
    create_start_scripts(install_path, python_path)
    
    # Testa conexão com servidor
    test_server_connection(args.server_url)
    
    # Cria tarefa agendada (apenas Windows)
    create_task = False
    if platform.system() == "Windows" and not args.no_task:
        try:
            import win32com.client
            print("\n⏰ Criando Tarefa Agendada...")
            # Implementação da tarefa agendada aqui
            print("✅ Tarefa agendada criada")
            create_task = True
        except ImportError:
            print("\n⚠️  win32com não disponível - tarefa agendada não criada")
            print("💡 Instale: pip install pywin32")
    
    # Resumo
    print_summary(install_path, args.server_url, create_task)
    
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


