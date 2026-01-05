#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para iniciar o servidor em produção usando Waitress (Windows/Linux/Mac)
Waitress é um servidor WSGI adequado para produção
"""

import os
import sys
from pathlib import Path

# Adiciona o diretório serv ao path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR / 'serv'))

# Carrega variáveis de ambiente do .env
try:
    from dotenv import load_dotenv
    env_path = BASE_DIR / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Arquivo .env carregado: {env_path}")
    else:
        print(f"⚠️  Arquivo .env não encontrado em {env_path}")
        print("   Usando variáveis de ambiente do sistema")
except ImportError:
    print("⚠️  python-dotenv não instalado. Usando variáveis de ambiente do sistema")

# Verifica se Waitress está instalado
try:
    from waitress import serve
except ImportError:
    print("❌ ERRO: Waitress não está instalado!")
    print("   Instale com: pip install waitress")
    sys.exit(1)

# Importa o app Flask
try:
    from serv.servidor import app
except ImportError as e:
    print(f"❌ ERRO ao importar servidor: {e}")
    sys.exit(1)

if __name__ == "__main__":
    # Configurações
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5002))
    
    # Verifica ambiente
    flask_env = os.getenv('FLASK_ENV', 'development')
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    if flask_env != 'production':
        print("⚠️  AVISO: FLASK_ENV não está definido como 'production'")
        print(f"   Valor atual: {flask_env}")
        resposta = input("   Continuar mesmo assim? (s/N): ")
        if resposta.lower() != 's':
            print("❌ Cancelado. Configure FLASK_ENV=production antes de continuar.")
            sys.exit(1)
    
    if debug:
        print("⚠️  AVISO: DEBUG está habilitado. Desabilite em produção!")
        resposta = input("   Continuar mesmo assim? (s/N): ")
        if resposta.lower() != 's':
            print("❌ Cancelado. Configure DEBUG=False antes de continuar.")
            sys.exit(1)
    
    # Verifica SECRET_KEY
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key or secret_key == 'sua-chave-secreta-aqui':
        print("❌ ERRO: SECRET_KEY não está configurada!")
        print("   Configure SECRET_KEY no arquivo .env ou variáveis de ambiente")
        sys.exit(1)
    
    print("=" * 70)
    print("🚀 INICIANDO SERVIDOR EM PRODUÇÃO (Waitress)")
    print("=" * 70)
    print(f"📍 Host: {host}")
    print(f"🔌 Porta: {port}")
    print(f"🌍 Ambiente: {flask_env}")
    print(f"🔐 SECRET_KEY: {'✅ Configurada' if secret_key else '❌ Não configurada'}")
    print(f"🐛 Debug: {debug}")
    print("=" * 70)
    print("")
    print("✅ Servidor iniciado com sucesso!")
    print(f"🌐 Acesse: http://{host if host != '0.0.0.0' else 'localhost'}:{port}")
    print("")
    print("⚠️  Para parar o servidor, pressione Ctrl+C")
    print("=" * 70)
    print("")
    
    # Inicia servidor Waitress
    try:
        serve(
            app,
            host=host,
            port=port,
            threads=4,  # Número de threads
            channel_timeout=120,  # Timeout de 2 minutos
            cleanup_interval=30,  # Limpeza a cada 30 segundos
            asyncore_use_poll=True
        )
    except KeyboardInterrupt:
        print("\n\n⏹️  Servidor interrompido pelo usuário")
    except Exception as e:
        print(f"\n\n❌ ERRO ao iniciar servidor: {e}")
        sys.exit(1)

