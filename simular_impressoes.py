#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Simulação de Impressões
Valida a lógica de cálculo de impressões em diferentes cenários
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Adicionar paths
sys.path.insert(0, 'serv')

from modules.calculo_impressao import (
    calcular_folhas_fisicas,
    calcular_custo,
    calcular_custo_comodato,
    normalizar_duplex,
    normalizar_paginas,
    normalizar_copias
)

print("=" * 80)
print("🧪 SIMULAÇÃO DE IMPRESSÕES - VALIDAÇÃO DE CÁLCULOS")
print("=" * 80)
print()

# Contador de testes
testes_passados = 0
testes_falhados = 0
resultados = []

def formatar_moeda(valor: float) -> str:
    """Formata valor como moeda brasileira"""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def testar_cenario(nome: str, config: Dict, esperado: Dict = None):
    """Testa um cenário de impressão"""
    global testes_passados, testes_falhados
    
    print(f"\n{'='*80}")
    print(f"📋 CENÁRIO: {nome}")
    print(f"{'='*80}")
    
    # Extrair parâmetros
    pages = config.get('pages', 0)
    duplex = config.get('duplex', False)
    copies = config.get('copies', 1)
    colorido = config.get('colorido', False)
    comodato = config.get('comodato', False)
    insumos_inclusos = config.get('insumos_inclusos', True)
    limite_mensal = config.get('limite_mensal', None)
    uso_mensal_atual = config.get('uso_mensal_atual', 0)
    custo_excedente = config.get('custo_excedente', None)
    preco_pb = config.get('preco_pb', 0.10)
    preco_color = config.get('preco_color', 0.50)
    
    # Calcular folhas físicas
    folhas_fisicas = calcular_folhas_fisicas(pages, duplex, copies)
    
    # Calcular custo
    if comodato:
        resultado_custo = calcular_custo_comodato(
            folhas=folhas_fisicas,
            comodato=True,
            insumos_inclusos=insumos_inclusos,
            limite_mensal=limite_mensal,
            uso_mensal_atual=uso_mensal_atual,
            custo_excedente=custo_excedente,
            preco_pb=preco_pb,
            preco_color=preco_color,
            colorido=colorido
        )
        custo_total = resultado_custo['custo']
        excedente = resultado_custo.get('excedente', 0)
        custo_excedente_calc = resultado_custo.get('custo_excedente', 0.0)
    else:
        custo_total = calcular_custo(folhas_fisicas, colorido, preco_pb, preco_color)
        resultado_custo = {'custo': custo_total, 'excedente': 0, 'custo_excedente': 0.0}
        excedente = 0
        custo_excedente_calc = 0.0
    
    # Exibir resultados
    print(f"\n📊 Parâmetros de Entrada:")
    print(f"   • Páginas lógicas: {pages}")
    print(f"   • Duplex: {'Sim' if duplex else 'Não'}")
    print(f"   • Cópias: {copies}")
    print(f"   • Colorido: {'Sim' if colorido else 'Não'}")
    print(f"   • Comodato: {'Sim' if comodato else 'Não'}")
    
    if comodato:
        print(f"   • Insumos Inclusos: {'Sim' if insumos_inclusos else 'Não'}")
        if limite_mensal:
            print(f"   • Limite Mensal: {limite_mensal:,} folhas")
            print(f"   • Uso Mensal Atual: {uso_mensal_atual:,} folhas")
            if custo_excedente:
                print(f"   • Custo Excedente: {formatar_moeda(custo_excedente)}/folha")
    
    print(f"\n💰 Resultados do Cálculo:")
    print(f"   • Folhas físicas: {folhas_fisicas:,}")
    print(f"   • Custo total: {formatar_moeda(custo_total)}")
    
    if comodato:
        print(f"   • Folhas excedentes: {excedente:,}")
        if custo_excedente_calc > 0:
            print(f"   • Custo excedente: {formatar_moeda(custo_excedente_calc)}")
    
    # Validação se esperado fornecido
    if esperado:
        print(f"\n✅ Validação:")
        validacoes = []
        
        if 'folhas_fisicas' in esperado:
            if folhas_fisicas == esperado['folhas_fisicas']:
                print(f"   ✅ Folhas físicas: {folhas_fisicas} (esperado: {esperado['folhas_fisicas']})")
                validacoes.append(True)
            else:
                print(f"   ❌ Folhas físicas: {folhas_fisicas} (esperado: {esperado['folhas_fisicas']})")
                validacoes.append(False)
        
        if 'custo' in esperado:
            tolerancia = esperado.get('tolerancia', 0.01)
            if abs(custo_total - esperado['custo']) <= tolerancia:
                print(f"   ✅ Custo: {formatar_moeda(custo_total)} (esperado: {formatar_moeda(esperado['custo'])})")
                validacoes.append(True)
            else:
                print(f"   ❌ Custo: {formatar_moeda(custo_total)} (esperado: {formatar_moeda(esperado['custo'])})")
                validacoes.append(False)
        
        if 'excedente' in esperado:
            if excedente == esperado['excedente']:
                print(f"   ✅ Excedente: {excedente} (esperado: {esperado['excedente']})")
                validacoes.append(True)
            else:
                print(f"   ❌ Excedente: {excedente} (esperado: {esperado['excedente']})")
                validacoes.append(False)
        
        if all(validacoes):
            testes_passados += 1
            print(f"\n   ✅ CENÁRIO PASSOU")
        else:
            testes_falhados += 1
            print(f"\n   ❌ CENÁRIO FALHOU")
    else:
        testes_passados += 1
        print(f"\n   ✅ CENÁRIO EXECUTADO (sem validação)")
    
    # Armazenar resultado
    resultados.append({
        'nome': nome,
        'config': config,
        'resultado': {
            'folhas_fisicas': folhas_fisicas,
            'custo_total': custo_total,
            'excedente': excedente,
            'custo_excedente': custo_excedente_calc
        },
        'esperado': esperado
    })

# ============================================================================
# CENÁRIOS DE TESTE
# ============================================================================

print("\n🚀 INICIANDO SIMULAÇÕES...\n")

# ============================================================================
# GRUPO 1: Cálculo Básico de Folhas Físicas
# ============================================================================

print("\n" + "="*80)
print("📦 GRUPO 1: CÁLCULO BÁSICO DE FOLHAS FÍSICAS")
print("="*80)

# Teste 1.1: Impressão Simples (Simplex, 1 cópia)
testar_cenario(
    "Impressão Simples - 10 páginas, Simplex, 1 cópia",
    {
        'pages': 10,
        'duplex': False,
        'copies': 1
    },
    {
        'folhas_fisicas': 10,
        'custo': 1.00  # 10 folhas × R$ 0,10 (P&B)
    }
)

# Teste 1.2: Impressão Duplex
testar_cenario(
    "Impressão Duplex - 10 páginas, Duplex, 1 cópia",
    {
        'pages': 10,
        'duplex': True,
        'copies': 1
    },
    {
        'folhas_fisicas': 5,  # 10 páginas ÷ 2
        'custo': 0.50
    }
)

# Teste 1.3: Múltiplas Cópias
testar_cenario(
    "Múltiplas Cópias - 10 páginas, Simplex, 3 cópias",
    {
        'pages': 10,
        'duplex': False,
        'copies': 3
    },
    {
        'folhas_fisicas': 30,  # 10 páginas × 3 cópias
        'custo': 3.00
    }
)

# Teste 1.4: Duplex + Múltiplas Cópias
testar_cenario(
    "Duplex + Cópias - 20 páginas, Duplex, 2 cópias",
    {
        'pages': 20,
        'duplex': True,
        'copies': 2
    },
    {
        'folhas_fisicas': 20,  # (20 ÷ 2) × 2 cópias
        'custo': 2.00
    }
)

# ============================================================================
# GRUPO 2: Cálculo de Custos (P&B vs Colorido)
# ============================================================================

print("\n" + "="*80)
print("🎨 GRUPO 2: CÁLCULO DE CUSTOS (P&B vs COLORIDO)")
print("="*80)

# Teste 2.1: Impressão P&B
testar_cenario(
    "Impressão P&B - 100 folhas",
    {
        'pages': 100,
        'duplex': False,
        'copies': 1,
        'colorido': False,
        'preco_pb': 0.10,
        'preco_color': 0.50
    },
    {
        'folhas_fisicas': 100,
        'custo': 10.00  # 100 × R$ 0,10
    }
)

# Teste 2.2: Impressão Colorida
testar_cenario(
    "Impressão Colorida - 100 folhas",
    {
        'pages': 100,
        'duplex': False,
        'copies': 1,
        'colorido': True,
        'preco_pb': 0.10,
        'preco_color': 0.50
    },
    {
        'folhas_fisicas': 100,
        'custo': 50.00  # 100 × R$ 0,50
    }
)

# ============================================================================
# GRUPO 3: Comodato com Insumos Inclusos (Sem Excedente)
# ============================================================================

print("\n" + "="*80)
print("📋 GRUPO 3: COMODATO - INSUMOS INCLUSOS (SEM EXCEDENTE)")
print("="*80)

# Teste 3.1: Comodato - Dentro do Limite
testar_cenario(
    "Comodato - Dentro do Limite (500 folhas de 5000)",
    {
        'pages': 100,
        'duplex': False,
        'copies': 1,
        'colorido': False,
        'comodato': True,
        'insumos_inclusos': True,
        'limite_mensal': 5000,
        'uso_mensal_atual': 500,
        'custo_excedente': 0.15,
        'preco_pb': 0.10,
        'preco_color': 0.50
    },
    {
        'folhas_fisicas': 100,
        'custo': 0.00,  # Dentro do limite, insumos inclusos
        'excedente': 0
    }
)

# Teste 3.2: Comodato - No Limite Exato
testar_cenario(
    "Comodato - No Limite Exato (5000 folhas de 5000)",
    {
        'pages': 100,
        'duplex': False,
        'copies': 1,
        'colorido': False,
        'comodato': True,
        'insumos_inclusos': True,
        'limite_mensal': 5000,
        'uso_mensal_atual': 4900,
        'custo_excedente': 0.15,
        'preco_pb': 0.10,
        'preco_color': 0.50
    },
    {
        'folhas_fisicas': 100,
        'custo': 0.00,  # Ainda dentro do limite (4900 + 100 = 5000)
        'excedente': 0
    }
)

# ============================================================================
# GRUPO 4: Comodato com Insumos Inclusos (COM EXCEDENTE)
# ============================================================================

print("\n" + "="*80)
print("⚠️  GRUPO 4: COMODATO - INSUMOS INCLUSOS (COM EXCEDENTE)")
print("="*80)

# Teste 4.1: Comodato - Excedendo o Limite
testar_cenario(
    "Comodato - Excedendo o Limite (4950 + 100 folhas de 5000)",
    {
        'pages': 100,
        'duplex': False,
        'copies': 1,
        'colorido': False,
        'comodato': True,
        'insumos_inclusos': True,
        'limite_mensal': 5000,
        'uso_mensal_atual': 4950,
        'custo_excedente': 0.15,
        'preco_pb': 0.10,
        'preco_color': 0.50
    },
    {
        'folhas_fisicas': 100,
        'custo': 7.50,  # 50 folhas excedentes × R$ 0,15
        'excedente': 50
    }
)

# Teste 4.2: Comodato - Totalmente Excedente
testar_cenario(
    "Comodato - Totalmente Excedente (5100 + 100 folhas de 5000)",
    {
        'pages': 100,
        'duplex': False,
        'copies': 1,
        'colorido': False,
        'comodato': True,
        'insumos_inclusos': True,
        'limite_mensal': 5000,
        'uso_mensal_atual': 5100,
        'custo_excedente': 0.15,
        'preco_pb': 0.10,
        'preco_color': 0.50
    },
    {
        'folhas_fisicas': 100,
        'custo': 15.00,  # 100 folhas excedentes × R$ 0,15
        'excedente': 100
    }
)

# ============================================================================
# GRUPO 5: Comodato SEM Insumos Inclusos
# ============================================================================

print("\n" + "="*80)
print("💼 GRUPO 5: COMODATO - SEM INSUMOS INCLUSOS")
print("="*80)

# Teste 5.1: Comodato - Sem Insumos, Dentro do Limite
testar_cenario(
    "Comodato - Sem Insumos, Dentro do Limite",
    {
        'pages': 100,
        'duplex': False,
        'copies': 1,
        'colorido': False,
        'comodato': True,
        'insumos_inclusos': False,
        'limite_mensal': 5000,
        'uso_mensal_atual': 500,
        'custo_excedente': 0.20,
        'preco_pb': 0.10,
        'preco_color': 0.50
    },
    {
        'folhas_fisicas': 100,
        'custo': 10.00,  # Paga pelos insumos normalmente (100 × R$ 0,10)
        'excedente': 0
    }
)

# Teste 5.2: Comodato - Sem Insumos, Com Excedente
testar_cenario(
    "Comodato - Sem Insumos, Com Excedente",
    {
        'pages': 100,
        'duplex': False,
        'copies': 1,
        'colorido': False,
        'comodato': True,
        'insumos_inclusos': False,
        'limite_mensal': 5000,
        'uso_mensal_atual': 4950,
        'custo_excedente': 0.20,
        'preco_pb': 0.10,
        'preco_color': 0.50
    },
    {
        'folhas_fisicas': 100,
        'custo': 20.00,  # Custo insumos (100 × R$ 0,10) + Excedente (50 × R$ 0,20) = R$ 10,00 + R$ 10,00
        'excedente': 50
    }
)

# ============================================================================
# GRUPO 6: Comodato SEM Limite
# ============================================================================

print("\n" + "="*80)
print("♾️  GRUPO 6: COMODATO - SEM LIMITE DE PÁGINAS")
print("="*80)

# Teste 6.1: Comodato - Sem Limite, Insumos Inclusos
testar_cenario(
    "Comodato - Sem Limite, Insumos Inclusos",
    {
        'pages': 1000,
        'duplex': False,
        'copies': 1,
        'colorido': False,
        'comodato': True,
        'insumos_inclusos': True,
        'limite_mensal': None,
        'uso_mensal_atual': 0,
        'custo_excedente': None,
        'preco_pb': 0.10,
        'preco_color': 0.50
    },
    {
        'folhas_fisicas': 1000,
        'custo': 0.00,  # Sem limite, tudo incluído
        'excedente': 0
    }
)

# ============================================================================
# GRUPO 7: Cenários Complexos
# ============================================================================

print("\n" + "="*80)
print("🔀 GRUPO 7: CENÁRIOS COMPLEXOS")
print("="*80)

# Teste 7.1: Duplex + Colorido + Comodato
testar_cenario(
    "Duplex Colorido em Comodato - 200 páginas, Duplex, 2 cópias",
    {
        'pages': 200,
        'duplex': True,
        'copies': 2,
        'colorido': True,
        'comodato': True,
        'insumos_inclusos': True,
        'limite_mensal': 1000,
        'uso_mensal_atual': 500,
        'custo_excedente': 0.25,
        'preco_pb': 0.10,
        'preco_color': 0.50
    },
    {
        'folhas_fisicas': 200,  # (200 ÷ 2) × 2 cópias
        'custo': 0.00,  # Dentro do limite (500 + 200 = 700 < 1000)
        'excedente': 0
    }
)

# Teste 7.2: Impressão Própria (Não Comodato)
testar_cenario(
    "Impressora Própria - 500 folhas P&B",
    {
        'pages': 500,
        'duplex': False,
        'copies': 1,
        'colorido': False,
        'comodato': False,
        'preco_pb': 0.10,
        'preco_color': 0.50
    },
    {
        'folhas_fisicas': 500,
        'custo': 50.00  # 500 × R$ 0,10
    }
)

# ============================================================================
# RESUMO FINAL
# ============================================================================

print("\n" + "="*80)
print("📊 RESUMO DAS SIMULAÇÕES")
print("="*80)
print(f"\n✅ Testes Passados: {testes_passados}")
print(f"❌ Testes Falhados: {testes_falhados}")
print(f"📈 Taxa de Sucesso: {(testes_passados/(testes_passados+testes_falhados)*100):.1f}%")

print("\n📋 Resumo por Cenário:")
for i, resultado in enumerate(resultados, 1):
    status = "✅" if resultado.get('esperado') and all([
        resultado['resultado']['folhas_fisicas'] == resultado['esperado'].get('folhas_fisicas', resultado['resultado']['folhas_fisicas']),
        abs(resultado['resultado']['custo_total'] - resultado['esperado'].get('custo', resultado['resultado']['custo_total'])) <= 0.01
    ]) else "ℹ️"
    print(f"   {status} {i}. {resultado['nome']}")

print("\n" + "="*80)
if testes_falhados == 0:
    print("🎉 TODAS AS SIMULAÇÕES PASSARAM!")
else:
    print("⚠️  ALGUMAS SIMULAÇÕES FALHARAM. Verifique os resultados acima.")
print("="*80)

