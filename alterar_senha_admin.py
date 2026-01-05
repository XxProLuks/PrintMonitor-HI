#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para alterar senha do usuário admin
Execute este script para alterar a senha padrão do administrador
"""

import sys
import os
from werkzeug.security import generate_password_hash

# Adiciona o diretório serv ao path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, 'serv'))

# Caminho do banco de dados
DB = os.path.join(BASE_DIR, 'serv', 'print_events.db')

def alterar_senha_admin(nova_senha=None):
    """Altera a senha do usuário admin"""
    import sqlite3
    
    if not nova_senha:
        print("=" * 70)
        print("ALTERAR SENHA DO ADMINISTRADOR")
        print("=" * 70)
        print("")
        print("⚠️  IMPORTANTE: Altere a senha padrão (admin/123) imediatamente!")
        print("")
        nova_senha = input("Digite a nova senha para o usuário 'admin': ")
        
        if not nova_senha:
            print("❌ Senha não pode ser vazia!")
            return False
        
        confirmar = input("Confirme a senha: ")
        
        if nova_senha != confirmar:
            print("❌ Senhas não coincidem!")
            return False
    
    try:
        with sqlite3.connect(DB) as conn:
            # Verifica se usuário admin existe
            cursor = conn.execute("SELECT username FROM users WHERE username = ?", ('admin',))
            if not cursor.fetchone():
                print("❌ Usuário 'admin' não encontrado!")
                print("   Criando usuário admin...")
                conn.execute(
                    "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    ('admin', generate_password_hash(nova_senha), 'admin')
                )
                conn.commit()
                print("✅ Usuário 'admin' criado com nova senha")
            else:
                # Atualiza senha
                senha_hash = generate_password_hash(nova_senha)
                conn.execute(
                    "UPDATE users SET password = ? WHERE username = ?",
                    (senha_hash, 'admin')
                )
                conn.commit()
                print("✅ Senha do usuário 'admin' alterada com sucesso!")
            
            print("")
            print("=" * 70)
            print("CONFIGURAÇÃO CONCLUÍDA")
            print("=" * 70)
            print("")
            print("📋 Credenciais atualizadas:")
            print(f"   Usuário: admin")
            print(f"   Senha: {nova_senha}")
            print("")
            print("⚠️  IMPORTANTE: Guarde esta senha em local seguro!")
            print("=" * 70)
            return True
            
    except Exception as e:
        print(f"❌ Erro ao alterar senha: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Senha passada como argumento
        nova_senha = sys.argv[1]
        alterar_senha_admin(nova_senha)
    else:
        # Modo interativo
        alterar_senha_admin()

