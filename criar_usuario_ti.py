#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script para criar usuário TI HI com permissão admin"""
import sqlite3
import os
from werkzeug.security import generate_password_hash

# Caminho do banco de dados
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, 'serv', 'print_events.db')

if not os.path.exists(DB):
    print(f"[ERRO] Banco de dados nao encontrado em: {DB}")
    exit(1)

try:
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    
    # Dados do novo usuário
    username = "TI HI"
    password = "157398378"
    is_admin = 1  # Admin
    password_hash = generate_password_hash(password)
    
    # Verifica se o usuário já existe
    cursor.execute("SELECT username FROM login WHERE username = ?", (username,))
    exists = cursor.fetchone()
    
    if exists:
        # Atualiza usuário existente
        cursor.execute(
            "UPDATE login SET password = ?, is_admin = ? WHERE username = ?",
            (password_hash, is_admin, username)
        )
        print(f"[OK] Usuario '{username}' foi ATUALIZADO!")
    else:
        # Cria novo usuário
        cursor.execute(
            "INSERT INTO login (username, password, is_admin) VALUES (?, ?, ?)",
            (username, password_hash, is_admin)
        )
        print(f"[OK] Usuario '{username}' criado com sucesso!")
    
    conn.commit()
    conn.close()
    
    print()
    print("=" * 60)
    print("CREDENCIAIS DE ACESSO")
    print("=" * 60)
    print(f"  Usuario: {username}")
    print(f"  Senha: {password}")
    print(f"  Permissao: {'Administrador' if is_admin else 'Usuario'}")
    print("=" * 60)
    print()
    print("[OK] Pronto! Voce ja pode fazer login com essas credenciais.")
    
except Exception as e:
    print(f"[ERRO] Erro ao criar usuario: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

