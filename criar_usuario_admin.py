#!/usr/bin/env python3
"""Script para criar ou resetar usuário administrador"""
import sqlite3
import os
from werkzeug.security import generate_password_hash

# Caminho do banco de dados
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, 'serv', 'print_events.db')

if not os.path.exists(DB):
    print(f"❌ Banco de dados não encontrado em: {DB}")
    exit(1)

try:
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    
    # Lista usuários existentes
    print("=" * 60)
    print("👥 USUÁRIOS EXISTENTES")
    print("=" * 60)
    cursor.execute("SELECT username, is_admin FROM login ORDER BY username")
    users = cursor.fetchall()
    
    if users:
        for username, is_admin in users:
            admin_status = "✅ Admin" if is_admin else "👤 Usuário"
            print(f"  • {username:20s} - {admin_status}")
    else:
        print("  ⚠️  Nenhum usuário encontrado")
    
    print()
    print("=" * 60)
    
    # Cria ou atualiza usuário admin
    username = "admin"
    password = "admin123"  # Senha padrão
    password_hash = generate_password_hash(password)
    
    # Verifica se o usuário já existe
    cursor.execute("SELECT username FROM login WHERE username = ?", (username,))
    exists = cursor.fetchone()
    
    if exists:
        # Atualiza senha do admin existente
        cursor.execute(
            "UPDATE login SET password = ?, is_admin = 1 WHERE username = ?",
            (password_hash, username)
        )
        print(f"✅ Senha do usuário '{username}' foi RESETADA!")
    else:
        # Cria novo usuário admin
        cursor.execute(
            "INSERT INTO login (username, password, is_admin) VALUES (?, ?, ?)",
            (username, password_hash, 1)
        )
        print(f"✅ Usuário '{username}' criado com sucesso!")
    
    conn.commit()
    
    print()
    print("=" * 60)
    print("🔐 CREDENCIAIS DE ACESSO")
    print("=" * 60)
    print(f"  Usuário: {username}")
    print(f"  Senha:   {password}")
    print("=" * 60)
    print()
    print("⚠️  IMPORTANTE: Altere a senha após o primeiro login!")
    print()
    
    conn.close()
    
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

