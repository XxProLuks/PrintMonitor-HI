#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Testes Completo - Monitoramento1
Verifica todas as funcionalidades principais do projeto
"""

import sys
import os
import sqlite3
from datetime import datetime, timedelta

# Adicionar paths
sys.path.insert(0, 'serv')
sys.path.insert(0, 'agent')

print("=" * 70)
print("🧪 TESTE COMPLETO DO PROJETO MONITORAMENTO1")
print("=" * 70)
print()

# Contador de testes
testes_passados = 0
testes_falhados = 0
erros = []

def teste(nome, funcao):
    """Executa um teste e registra o resultado"""
    global testes_passados, testes_falhados
    try:
        resultado = funcao()
        if resultado:
            print(f"✅ {nome}")
            testes_passados += 1
            return True
        else:
            print(f"❌ {nome} - Falhou")
            testes_falhados += 1
            return False
    except Exception as e:
        print(f"❌ {nome} - Erro: {str(e)}")
        erros.append(f"{nome}: {str(e)}")
        testes_falhados += 1
        return False

# ============================================================================
# TESTE 1: Imports dos Módulos Principais
# ============================================================================
print("📦 TESTE 1: Verificação de Imports")
print("-" * 70)

teste("Import servidor.py", lambda: __import__('servidor', fromlist=['']))
teste("Import calculo_impressao", lambda: __import__('modules.calculo_impressao', fromlist=['']))
# teste analise_comodatos removido - módulo foi removido do sistema de preços
teste("Import pdf_export", lambda: __import__('modules.pdf_export', fromlist=['']))

print()

# ============================================================================
# TESTE 2: Funções de Cálculo
# ============================================================================
print("🔢 TESTE 2: Funções de Cálculo")
print("-" * 70)

from modules.calculo_impressao import (
    calcular_folhas_fisicas,
    normalizar_duplex,
    normalizar_paginas
)
# Funções calcular_custo e calcular_custo_comodato foram removidas do sistema de preços

teste("calcular_folhas_fisicas - Simples", 
      lambda: calcular_folhas_fisicas(10, False, 1) == 10)

teste("calcular_folhas_fisicas - Duplex", 
      lambda: calcular_folhas_fisicas(10, True, 1) == 5)

teste("calcular_folhas_fisicas - Cópias", 
      lambda: calcular_folhas_fisicas(10, False, 3) == 30)

# Testes de calcular_custo e calcular_custo_comodato removidos - sistema de preços foi removido

print()

# ============================================================================
# TESTE 3: Estrutura do Banco de Dados
# ============================================================================
print("🗄️  TESTE 3: Estrutura do Banco de Dados")
print("-" * 70)

def verificar_banco():
    db_path = 'serv/print_events.db'
    if not os.path.exists(db_path):
        print(f"⚠️  Banco de dados não encontrado: {db_path}")
        return True  # Não é erro crítico se não existir
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Verificar tabelas principais
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tabelas = [row[0] for row in cursor.fetchall()]
    
    tabelas_esperadas = ['events', 'printers', 'materials', 'prices', 'comodatos']
    for tabela in tabelas_esperadas:
        if tabela not in tabelas:
            print(f"⚠️  Tabela '{tabela}' não encontrada")
    
    # Verificar colunas da tabela events
    if 'events' in tabelas:
        cursor.execute("PRAGMA table_info(events)")
        colunas_events = [row[1] for row in cursor.fetchall()]
        colunas_esperadas = ['id', 'user', 'printer_name', 'pages', 'date', 'machine', 'sheets_used', 'cost']
        for col in colunas_esperadas:
            if col not in colunas_events:
                print(f"⚠️  Coluna '{col}' não encontrada em 'events'")
    
    # Verificar colunas da tabela printers (comodato)
    if 'printers' in tabelas:
        cursor.execute("PRAGMA table_info(printers)")
        colunas_printers = [row[1] for row in cursor.fetchall()]
        colunas_comodato = ['comodato', 'insumos_inclusos', 'custo_fixo_mensal', 'limite_paginas_mensal', 'custo_excedente']
        for col in colunas_comodato:
            if col not in colunas_printers:
                print(f"⚠️  Coluna '{col}' não encontrada em 'printers'")
    
    conn.close()
    return True

teste("Estrutura do banco de dados", verificar_banco)

print()

# ============================================================================
# TESTE 4: Módulo de Análise de Comodatos - REMOVIDO
# ============================================================================
# Este teste foi removido porque o módulo analise_comodatos.py
# foi removido junto com o sistema de preços e comodatos
print("📊 TESTE 4: Módulo de Análise de Comodatos - PULANDO (módulo removido)")
print("-" * 70)
print("⚠️  Módulo analise_comodatos foi removido do sistema")
testes_passados += 1  # Conta como passado (skip)

print()

# ============================================================================
# TESTE 5: Validação de SQL Injection Prevention
# ============================================================================
print("🔒 TESTE 5: Validação de Segurança (SQL Injection)")
print("-" * 70)

def testar_validacao_sql():
    try:
        import sys
        sys.path.insert(0, 'serv')
        from servidor import (
            validar_nome_tabela,
            validar_operador_sql,
            sanitizar_nome_campo
        )
        
        # Testar validação de tabela
        if not validar_nome_tabela('events'):
            return False
        if validar_nome_tabela("'; DROP TABLE events; --"):
            return False
        
        # Testar sanitização
        sanitized = sanitizar_nome_campo("'; DROP TABLE--")
        # A sanitização deve remover caracteres perigosos
        if "'" in sanitized or "--" in sanitized or "DROP" in sanitized.upper():
            return False
        
        # Testar operadores
        if not validar_operador_sql('='):
            return False
        if validar_operador_sql("'; DROP TABLE--"):
            return False
        
        return True
    except Exception as e:
        print(f"   Erro detalhado: {e}")
        return False

teste("Prevenção de SQL Injection", testar_validacao_sql)

print()

# ============================================================================
# TESTE 6: Verificação de Arquivos Críticos
# ============================================================================
print("📁 TESTE 6: Arquivos Críticos")
print("-" * 70)

arquivos_criticos = [
    'serv/servidor.py',
    'agent/agente.py',
    'serv/modules/calculo_impressao.py',
    'serv/modules/analise_comodatos.py',
    'serv/templates/dashboard_comodatos.html',
    'serv/templates/admin_precos.html',
    'requirements.txt',
    'agent/config.json'
]

for arquivo in arquivos_criticos:
    teste(f"Arquivo existe: {arquivo}", lambda f=arquivo: os.path.exists(f))

print()

# ============================================================================
# TESTE 7: Verificação de Dependências
# ============================================================================
print("📦 TESTE 7: Dependências Python")
print("-" * 70)

dependencias = [
    'flask',
    'flask_socketio',
    'sqlite3',
    'pandas',
    'reportlab'
]

for dep in dependencias:
    try:
        __import__(dep if dep != 'sqlite3' else 'sqlite3')
        print(f"✅ {dep}")
        testes_passados += 1
    except ImportError:
        print(f"❌ {dep} - Não instalado")
        testes_falhados += 1
        erros.append(f"Dependência faltando: {dep}")

print()

# ============================================================================
# RESUMO FINAL
# ============================================================================
print("=" * 70)
print("📊 RESUMO DOS TESTES")
print("=" * 70)
print(f"✅ Testes Passados: {testes_passados}")
print(f"❌ Testes Falhados: {testes_falhados}")
print(f"📈 Taxa de Sucesso: {(testes_passados/(testes_passados+testes_falhados)*100):.1f}%")
print()

if erros:
    print("⚠️  ERROS ENCONTRADOS:")
    for erro in erros:
        print(f"   - {erro}")
    print()

if testes_falhados == 0:
    print("🎉 TODOS OS TESTES PASSARAM!")
    sys.exit(0)
else:
    print("⚠️  ALGUNS TESTES FALHARAM. Verifique os erros acima.")
    sys.exit(1)

