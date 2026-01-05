#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para recalcular sheets_used (folhas físicas) de todos os eventos existentes.

Execute este script após adicionar a coluna sheets_used ao banco de dados
para preencher os valores dos eventos antigos.

Uso:
    python recalcular_folhas.py
"""

import sqlite3
import os
import sys
import math
from datetime import datetime

# Adiciona o diretório atual ao path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importa função de cálculo centralizada
try:
    from modules.calculo_impressao import calcular_folhas_fisicas
except ImportError:
    # Fallback se módulo não disponível
    def calcular_folhas_fisicas(pages, duplex, copies=1):
        if pages is None or pages <= 0:
            return 0
        faces = pages * (copies or 1)
        if duplex == 1 or duplex is True:
            return math.ceil(faces / 2)
        return faces


def recalcular_todos_eventos(db_path: str = 'print_events.db'):
    """
    Recalcula sheets_used para todos os eventos no banco de dados.
    
    Args:
        db_path: Caminho para o banco de dados SQLite
    """
    print("=" * 60)
    print("RECÁLCULO DE FOLHAS FÍSICAS (sheets_used)")
    print("=" * 60)
    
    if not os.path.exists(db_path):
        print(f"❌ Banco de dados não encontrado: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Verifica se a coluna sheets_used existe
    columns = [col[1] for col in cursor.execute("PRAGMA table_info(events)").fetchall()]
    if 'sheets_used' not in columns:
        print("⚠️ Coluna sheets_used não existe. Adicionando...")
        cursor.execute("ALTER TABLE events ADD COLUMN sheets_used INTEGER")
        conn.commit()
        print("✅ Coluna sheets_used adicionada!")
    
    # Verifica se a coluna copies existe
    if 'copies' not in columns:
        print("⚠️ Coluna copies não existe. Adicionando...")
        cursor.execute("ALTER TABLE events ADD COLUMN copies INTEGER DEFAULT 1")
        conn.commit()
        print("✅ Coluna copies adicionada!")
    
    # Conta total de eventos
    total = cursor.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    print(f"\n📊 Total de eventos no banco: {total}")
    
    # Conta eventos sem sheets_used
    sem_calculo = cursor.execute(
        "SELECT COUNT(*) FROM events WHERE sheets_used IS NULL"
    ).fetchone()[0]
    print(f"📝 Eventos sem sheets_used: {sem_calculo}")
    
    if sem_calculo == 0:
        print("\n✅ Todos os eventos já possuem sheets_used calculado!")
        conn.close()
        return True
    
    print(f"\n🔄 Recalculando {sem_calculo} eventos...")
    
    # Busca eventos sem sheets_used
    eventos = cursor.execute("""
        SELECT id, pages_printed, duplex, copies, printer_name
        FROM events 
        WHERE sheets_used IS NULL
    """).fetchall()
    
    atualizados = 0
    erros = 0
    
    for evento in eventos:
        try:
            event_id = evento['id']
            pages = evento['pages_printed'] or 1
            duplex = evento['duplex']
            copies = evento['copies'] or 1
            
            # Calcula folhas físicas
            sheets_used = calcular_folhas_fisicas(pages, duplex, copies)
            
            # Atualiza no banco
            cursor.execute(
                "UPDATE events SET sheets_used = ? WHERE id = ?",
                (sheets_used, event_id)
            )
            atualizados += 1
            
            # Progress feedback
            if atualizados % 100 == 0:
                print(f"   Processados: {atualizados}/{sem_calculo}")
                
        except Exception as e:
            erros += 1
            print(f"   ❌ Erro no evento {evento['id']}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Recálculo concluído!")
    print(f"   - Eventos atualizados: {atualizados}")
    print(f"   - Erros: {erros}")
    print("=" * 60)
    
    return erros == 0


def mostrar_estatisticas(db_path: str = 'print_events.db'):
    """Mostra estatísticas após o recálculo."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n📊 ESTATÍSTICAS APÓS RECÁLCULO:")
    print("-" * 40)
    
    # Total de páginas vs folhas
    stats = cursor.execute("""
        SELECT 
            SUM(pages_printed) as total_paginas,
            SUM(sheets_used) as total_folhas,
            SUM(CASE WHEN duplex = 1 THEN 1 ELSE 0 END) as eventos_duplex,
            SUM(CASE WHEN duplex = 0 OR duplex IS NULL THEN 1 ELSE 0 END) as eventos_simplex
        FROM events
    """).fetchone()
    
    total_paginas = stats[0] or 0
    total_folhas = stats[1] or 0
    eventos_duplex = stats[2] or 0
    eventos_simplex = stats[3] or 0
    
    economia = total_paginas - total_folhas if total_paginas > total_folhas else 0
    
    print(f"   Total de páginas lógicas: {total_paginas:,}")
    print(f"   Total de folhas físicas:  {total_folhas:,}")
    print(f"   Economia com duplex:      {economia:,} folhas")
    print(f"   Eventos em duplex:        {eventos_duplex:,}")
    print(f"   Eventos em simplex:       {eventos_simplex:,}")
    
    if total_paginas > 0:
        percentual_economia = (economia / total_paginas) * 100
        print(f"   Percentual de economia:   {percentual_economia:.1f}%")
    
    conn.close()


if __name__ == '__main__':
    print(f"\n⏰ Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Determina caminho do banco
    db_path = 'print_events.db'
    if not os.path.exists(db_path):
        # Tenta caminho alternativo
        script_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(script_dir, 'print_events.db')
    
    if recalcular_todos_eventos(db_path):
        mostrar_estatisticas(db_path)
    
    print(f"\n⏰ Finalizado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

