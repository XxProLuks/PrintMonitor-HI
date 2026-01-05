#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifica estrutura do banco de dados"""

import sqlite3
import os

db_path = 'serv/print_events.db'

if not os.path.exists(db_path):
    print("⚠️  Banco de dados não encontrado. Será criado na primeira execução do servidor.")
    exit(0)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("📊 Estrutura do Banco de Dados")
print("=" * 70)

# Listar tabelas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tabelas = [row[0] for row in cursor.fetchall()]
print(f"\n📋 Tabelas encontradas ({len(tabelas)}):")
for tabela in sorted(tabelas):
    print(f"   ✅ {tabela}")

# Verificar colunas principais
tabelas_importantes = ['events', 'printers', 'comodatos']
print("\n🔍 Colunas das Tabelas Principais:")

for tabela in tabelas_importantes:
    if tabela in tabelas:
        cursor.execute(f"PRAGMA table_info({tabela})")
        colunas = cursor.fetchall()
        print(f"\n   📌 {tabela}:")
        for col in colunas:
            print(f"      - {col[1]} ({col[2]})")

# Verificar dados
print("\n📊 Estatísticas:")
if 'events' in tabelas:
    cursor.execute("SELECT COUNT(*) FROM events")
    total_events = cursor.fetchone()[0]
    print(f"   Eventos: {total_events}")

if 'printers' in tabelas:
    cursor.execute("SELECT COUNT(*) FROM printers")
    total_printers = cursor.fetchone()[0]
    print(f"   Impressoras: {total_printers}")

if 'comodatos' in tabelas:
    cursor.execute("SELECT COUNT(*) FROM comodatos WHERE ativo = 1")
    total_comodatos = cursor.fetchone()[0]
    print(f"   Comodatos Ativos: {total_comodatos}")

conn.close()
print("\n✅ Verificação concluída!")

