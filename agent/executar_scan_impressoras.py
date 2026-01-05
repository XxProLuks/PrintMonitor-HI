#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para executar o scan de impressoras de rede
Pode ser executado manualmente ou agendado via Task Scheduler
"""

import sys
import os

# Adiciona o diretório do agente ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scanner_rede_impressoras import scan_rede_impressoras
import asyncio

if __name__ == "__main__":
    try:
        print("="*80)
        print("SCAN DE IMPRESSORAS DE REDE - HOSPITAL")
        print("="*80)
        print()
        
        total = asyncio.run(scan_rede_impressoras())
        
        print()
        print("="*80)
        print(f"[OK] Scan concluido com sucesso!")
        print(f"     Total de impressoras detectadas: {total}")
        print("="*80)
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n[AVISO] Scan interrompido pelo usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERRO FATAL] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

