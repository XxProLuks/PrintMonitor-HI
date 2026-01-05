#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para importar impressoras de um arquivo CSV
Formato do CSV:
    printer_name,ip,sector,tipo
    Kyocera ECOSYS M2040dn,192.168.1.100,TI,duplex
    HP LaserJet Pro,192.168.1.101,Administração,simplex
"""

import sqlite3
import os
import csv
import sys

# Caminho do banco de dados
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "serv", "print_events.db")

# Arquivo CSV de entrada
CSV_FILE = "impressoras_rede.csv"


def importar_csv(csv_file):
    """
    Importa impressoras de um arquivo CSV
    """
    if not os.path.exists(csv_file):
        print(f"❌ ERRO: Arquivo CSV não encontrado: {csv_file}")
        print(f"   Crie um arquivo CSV com o formato:")
        print(f"   printer_name,ip,sector,tipo")
        print(f"   Kyocera ECOSYS M2040dn,192.168.1.100,TI,duplex")
        return False
    
    if not os.path.exists(DB):
        print(f"❌ ERRO: Banco de dados não encontrado em: {DB}")
        return False
    
    try:
        conn = sqlite3.connect(DB)
        cursor = conn.cursor()
        
        # Verifica se a coluna IP existe
        cursor.execute("PRAGMA table_info(printers)")
        columns = [col[1] for col in cursor.fetchall()]
        has_ip_column = 'ip' in columns
        
        if not has_ip_column:
            cursor.execute("ALTER TABLE printers ADD COLUMN ip TEXT")
            conn.commit()
        
        # Lê CSV
        print(f"📖 Lendo arquivo: {csv_file}")
        impressoras = []
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                printer_name = row.get('printer_name', '').strip()
                ip = row.get('ip', '').strip()
                sector = row.get('sector', '').strip()
                tipo = row.get('tipo', 'simplex').strip().lower()
                
                if printer_name:
                    impressoras.append({
                        'printer_name': printer_name,
                        'ip': ip,
                        'sector': sector,
                        'tipo': tipo if tipo in ['duplex', 'simplex'] else 'simplex'
                    })
        
        if not impressoras:
            print("   ⚠️  Nenhuma impressora encontrada no CSV")
            return False
        
        print(f"   ✅ {len(impressoras)} impressoras encontradas no CSV")
        print("\n" + "="*70)
        print("📋 IMPORTANDO IMPRESSORAS")
        print("="*70)
        
        cadastradas = 0
        atualizadas = 0
        
        for imp in impressoras:
            printer_name = imp['printer_name']
            ip = imp['ip']
            sector = imp['sector']
            tipo = imp['tipo']
            
            # Verifica se já existe
            cursor.execute(
                "SELECT printer_name FROM printers WHERE printer_name = ?",
                (printer_name,)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Atualiza
                cursor.execute(
                    "UPDATE printers SET sector = ?, tipo = ?, ip = ? WHERE printer_name = ?",
                    (sector, tipo, ip, printer_name)
                )
                print(f"   🔄 [ATUALIZADA] {printer_name}")
                atualizadas += 1
            else:
                # Insere
                cursor.execute(
                    "INSERT INTO printers (printer_name, sector, tipo, ip) VALUES (?, ?, ?, ?)",
                    (printer_name, sector, tipo, ip)
                )
                print(f"   ✅ [CADASTRADA] {printer_name}")
                cadastradas += 1
        
        conn.commit()
        conn.close()
        
        print("\n" + "="*70)
        print(f"✅ IMPORTAÇÃO CONCLUÍDA!")
        print(f"   📊 {cadastradas} impressoras cadastradas")
        print(f"   🔄 {atualizadas} impressoras atualizadas")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO ao importar CSV: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("="*70)
    print("📥 IMPORTADOR DE IMPRESSORAS (CSV)")
    print("="*70)
    print(f"\n📝 Arquivo CSV: {CSV_FILE}")
    print("\n📋 Formato esperado:")
    print("   printer_name,ip,sector,tipo")
    print("   Kyocera ECOSYS M2040dn,192.168.1.100,TI,duplex")
    print("   HP LaserJet Pro,192.168.1.101,Administração,simplex")
    print("\n" + "="*70 + "\n")
    
    # Permite especificar arquivo diferente
    csv_file = sys.argv[1] if len(sys.argv) > 1 else CSV_FILE
    
    sucesso = importar_csv(csv_file)
    
    if sucesso:
        print("\n✅ Impressoras importadas com sucesso!")
    else:
        print("\n❌ Erro ao importar impressoras.")
        sys.exit(1)

