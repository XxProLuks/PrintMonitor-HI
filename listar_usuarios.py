#!/usr/bin/env python3
"""Script para listar usuários cadastrados no sistema"""
import sqlite3
import os

# Caminho do banco de dados
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, 'serv', 'print_events.db')

if not os.path.exists(DB):
    print(f"❌ Banco de dados não encontrado em: {DB}")
    exit(1)

try:
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    
    # Busca todos os usuários
    cursor.execute("SELECT username, is_admin FROM login ORDER BY username")
    users = cursor.fetchall()
    
    if users:
        print("=" * 60)
        print("👥 USUÁRIOS CADASTRADOS NO SISTEMA")
        print("=" * 60)
        print()
        
        for username, is_admin in users:
            admin_status = "✅ Admin" if is_admin else "👤 Usuário"
            print(f"  • {username:20s} - {admin_status}")
        
        print()
        print("=" * 60)
        print(f"Total: {len(users)} usuário(s)")
        print("=" * 60)
    else:
        print("⚠️  Nenhum usuário encontrado no banco de dados.")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Erro ao consultar usuários: {e}")
    exit(1)

