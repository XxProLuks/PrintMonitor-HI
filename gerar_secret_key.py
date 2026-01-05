#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para Gerar SECRET_KEY
=============================

Gera uma SECRET_KEY segura para uso no Flask.
"""

import secrets

def gerar_secret_key():
    """Gera uma SECRET_KEY segura de 64 caracteres (32 bytes em hex)"""
    return secrets.token_hex(32)

if __name__ == "__main__":
    print("=" * 70)
    print("🔐 GERADOR DE SECRET_KEY")
    print("=" * 70)
    print()
    
    key = gerar_secret_key()
    
    print(f"Chave gerada: {key}")
    print()
    print("📋 Para usar:")
    print("   1. Copie a chave acima")
    print("   2. Adicione ao arquivo .env: SECRET_KEY=<chave>")
    print("   3. Ou defina como variável de ambiente")
    print()
    print("💡 Exemplo de arquivo .env:")
    print("   SECRET_KEY=" + key)
    print("   FLASK_ENV=development")
    print()
    print("=" * 70)

