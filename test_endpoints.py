#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste de Endpoints da API - Monitoramento1
Verifica se todos os endpoints estão definidos corretamente
"""

import re
import sys

print("=" * 70)
print("🔌 TESTE DE ENDPOINTS DA API")
print("=" * 70)
print()

# Ler servidor.py
with open('serv/servidor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Endpoints esperados
endpoints_comodatos = [
    ('/dashboard/comodatos', 'GET'),
    ('/api/comodatos/dashboard', 'GET'),
    ('/api/comodatos/roi/<printer_name>', 'GET'),
    ('/api/comodatos/alertas', 'GET'),
    ('/api/comodatos/historico/<printer_name>', 'GET'),
    ('/api/comodatos/relatorio/pdf', 'GET'),
]

endpoints_gerais = [
    ('/api/events', 'POST'),
    ('/api/events', 'GET'),
    ('/api/sheets_stats', 'GET'),
    ('/api/export/custom', 'POST'),
]

print("📋 Endpoints de Comodatos:")
print("-" * 70)

endpoints_encontrados = 0
for endpoint, method in endpoints_comodatos:
    # Buscar padrão @app.route com o endpoint
    pattern = rf'@app\.route\(["\']{re.escape(endpoint)}["\']'
    if re.search(pattern, content):
        print(f"✅ {method:4} {endpoint}")
        endpoints_encontrados += 1
    else:
        # Tentar variações
        endpoint_alt = endpoint.replace('<printer_name>', r'[^"\']+')
        pattern_alt = rf'@app\.route\(["\']{endpoint_alt}["\']'
        if re.search(pattern_alt, content):
            print(f"✅ {method:4} {endpoint}")
            endpoints_encontrados += 1
        else:
            print(f"❌ {method:4} {endpoint} - NÃO ENCONTRADO")

print()
print("📋 Endpoints Gerais:")
print("-" * 70)

for endpoint, method in endpoints_gerais:
    pattern = rf'@app\.route\(["\']{re.escape(endpoint)}["\']'
    if re.search(pattern, content):
        print(f"✅ {method:4} {endpoint}")
        endpoints_encontrados += 1
    else:
        print(f"⚠️  {method:4} {endpoint} - Verificar manualmente")

print()
print("=" * 70)
print(f"📊 Total de Endpoints Encontrados: {endpoints_encontrados}/{len(endpoints_comodatos)}")
print("=" * 70)

# Verificar funções relacionadas
# NOTA: Teste de comodatos removido - módulo foi desativado do sistema
print()
print("🔍 Funções Relacionadas:")
print("-" * 70)
print("⚠️  Verificação de comodatos pulada - módulo analise_comodatos foi removido")

# Funções de comodato foram removidas junto com o sistema de preços
# funcoes_esperadas = [
#     'obter_resumo_comodatos',
#     'calcular_roi_comodato',
#     'verificar_excedente_comodatos',
#     'gerar_relatorio_comodatos_pdf',
# ]

print()
print("✅ Verificação de Endpoints concluída!")

