#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para cadastrar impressoras manualmente no banco de dados
Edite a lista IMPRESSORAS abaixo com suas impressoras e execute o script
"""

import sqlite3
import os
import sys

# Caminho do banco de dados
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "serv", "print_events.db")

# ============================================================================
# EDITAR AQUI: Adicione suas impressoras nesta lista
# ============================================================================
IMPRESSORAS = [
    {
        "printer_name": "Kyocera ECOSYS M2040dn - KMB8A35C",
        "ip": "192.168.1.100",  # Substitua pelo IP real
        "sector": "TI",
        "tipo": "duplex"  # "duplex" ou "simplex"
    },
    {
        "printer_name": "Kyocera ECOSYS M2040dn - KMDC968E",
        "ip": "192.168.1.101",  # Substitua pelo IP real
        "sector": "Administração",
        "tipo": "duplex"
    },
    {
        "printer_name": "Kyocera ECOSYS M2040dn - KME05B75",
        "ip": "192.168.1.102",  # Substitua pelo IP real
        "sector": "Recepção",
        "tipo": "duplex"
    },
    # Adicione mais impressoras aqui...
    # {
    #     "printer_name": "Nome da Impressora",
    #     "ip": "192.168.1.XXX",
    #     "sector": "Setor",
    #     "tipo": "duplex"  # ou "simplex"
    # },
]

# ============================================================================


def cadastrar_impressoras():
    """
    Cadastra as impressoras no banco de dados
    """
    if not os.path.exists(DB):
        print(f"❌ ERRO: Banco de dados não encontrado em: {DB}")
        print(f"   Certifique-se de que o servidor foi executado pelo menos uma vez.")
        return False
    
    try:
        conn = sqlite3.connect(DB)
        cursor = conn.cursor()
        
        # Verifica se a coluna IP existe na tabela printers
        cursor.execute("PRAGMA table_info(printers)")
        columns = [col[1] for col in cursor.fetchall()]
        has_ip_column = 'ip' in columns
        
        # Adiciona coluna IP se não existir
        if not has_ip_column:
            print("📝 Adicionando coluna 'ip' à tabela printers...")
            try:
                cursor.execute("ALTER TABLE printers ADD COLUMN ip TEXT")
                conn.commit()
                print("   ✅ Coluna 'ip' adicionada com sucesso!")
            except sqlite3.OperationalError as e:
                print(f"   ⚠️  Aviso ao adicionar coluna IP: {e}")
        
        # Cadastra cada impressora
        print("\n" + "="*70)
        print("📋 CADASTRANDO IMPRESSORAS")
        print("="*70)
        
        cadastradas = 0
        atualizadas = 0
        erros = 0
        
        for imp in IMPRESSORAS:
            printer_name = imp.get("printer_name", "").strip()
            sector = imp.get("sector", "").strip()
            ip = imp.get("ip", "").strip()
            tipo = imp.get("tipo", "simplex").strip().lower()
            
            if not printer_name:
                print(f"   ⚠️  Impressora sem nome - pulando...")
                erros += 1
                continue
            
            if tipo not in ["duplex", "simplex"]:
                print(f"   ⚠️  Tipo inválido para {printer_name} - usando 'simplex'")
                tipo = "simplex"
            
            # Verifica se já existe
            cursor.execute(
                "SELECT printer_name, sector, ip, tipo FROM printers WHERE printer_name = ?",
                (printer_name,)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Atualiza
                if has_ip_column:
                    cursor.execute(
                        "UPDATE printers SET sector = ?, tipo = ?, ip = ? WHERE printer_name = ?",
                        (sector, tipo, ip, printer_name)
                    )
                else:
                    cursor.execute(
                        "UPDATE printers SET sector = ?, tipo = ? WHERE printer_name = ?",
                        (sector, tipo, printer_name)
                    )
                print(f"   🔄 [ATUALIZADA] {printer_name}")
                print(f"      Setor: {sector} | IP: {ip} | Tipo: {tipo}")
                atualizadas += 1
            else:
                # Insere
                if has_ip_column:
                    cursor.execute(
                        "INSERT INTO printers (printer_name, sector, tipo, ip) VALUES (?, ?, ?, ?)",
                        (printer_name, sector, tipo, ip)
                    )
                else:
                    cursor.execute(
                        "INSERT INTO printers (printer_name, sector, tipo) VALUES (?, ?, ?)",
                        (printer_name, sector, tipo)
                    )
                print(f"   ✅ [CADASTRADA] {printer_name}")
                print(f"      Setor: {sector} | IP: {ip} | Tipo: {tipo}")
                cadastradas += 1
        
        conn.commit()
        conn.close()
        
        print("\n" + "="*70)
        print(f"✅ PROCESSO CONCLUÍDO!")
        print(f"   📊 {cadastradas} impressoras cadastradas")
        print(f"   🔄 {atualizadas} impressoras atualizadas")
        if erros > 0:
            print(f"   ⚠️  {erros} erros encontrados")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO ao cadastrar impressoras: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("="*70)
    print("🖨️  SCRIPT DE CADASTRO DE IMPRESSORAS")
    print("="*70)
    print("\n📝 INSTRUÇÕES:")
    print("   1. Edite a lista IMPRESSORAS neste arquivo")
    print("   2. Adicione o nome, IP, setor e tipo de cada impressora")
    print("   3. Execute este script novamente")
    print("\n" + "="*70 + "\n")
    
    if len(IMPRESSORAS) == 0:
        print("⚠️  Nenhuma impressora na lista!")
        print("   Edite o arquivo e adicione impressoras na lista IMPRESSORAS")
        sys.exit(1)
    
    sucesso = cadastrar_impressoras()
    
    if sucesso:
        print("\n✅ Impressoras cadastradas com sucesso!")
        print("   Acesse o sistema web para verificar.")
    else:
        print("\n❌ Erro ao cadastrar impressoras.")
        sys.exit(1)

