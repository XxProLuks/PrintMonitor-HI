"""
Módulo de Comparativo de Períodos
Compara mês atual vs anterior, trimestres, etc.
"""
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def comparar_periodos(conn: sqlite3.Connection, periodo_tipo: str = "mes", 
                     referencia: Optional[str] = None) -> Dict:
    """
    Compara dois períodos (atual vs anterior)
    
    Args:
        conn: Conexão com o banco
        periodo_tipo: 'mes', 'trimestre', 'ano', 'semana'
        referencia: 'user', 'setor', 'impressora' ou None para geral
    
    Returns:
        Dict com comparação dos períodos
    """
    hoje = datetime.now()
    
    if periodo_tipo == "mes":
        periodo_atual_inicio = hoje.replace(day=1).strftime("%Y-%m-%d")
        periodo_atual_fim = hoje.strftime("%Y-%m-%d")
        periodo_anterior_inicio = (hoje.replace(day=1) - timedelta(days=32)).replace(day=1).strftime("%Y-%m-%d")
        periodo_anterior_fim = (hoje.replace(day=1) - timedelta(days=1)).strftime("%Y-%m-%d")
    elif periodo_tipo == "trimestre":
        trimestre_atual = (hoje.month - 1) // 3 + 1
        mes_inicio_trimestre = (trimestre_atual - 1) * 3 + 1
        periodo_atual_inicio = hoje.replace(month=mes_inicio_trimestre, day=1).strftime("%Y-%m-%d")
        periodo_atual_fim = hoje.strftime("%Y-%m-%d")
        
        trimestre_anterior = trimestre_atual - 1 if trimestre_atual > 1 else 4
        ano_anterior = hoje.year if trimestre_atual > 1 else hoje.year - 1
        mes_inicio_trimestre_anterior = (trimestre_anterior - 1) * 3 + 1
        periodo_anterior_inicio = datetime(ano_anterior, mes_inicio_trimestre_anterior, 1).strftime("%Y-%m-%d")
        periodo_anterior_fim = (datetime(ano_anterior, mes_inicio_trimestre_anterior + 2, 28)).strftime("%Y-%m-%d")
    elif periodo_tipo == "ano":
        periodo_atual_inicio = hoje.replace(month=1, day=1).strftime("%Y-%m-%d")
        periodo_atual_fim = hoje.strftime("%Y-%m-%d")
        periodo_anterior_inicio = hoje.replace(year=hoje.year-1, month=1, day=1).strftime("%Y-%m-%d")
        periodo_anterior_fim = hoje.replace(year=hoje.year-1, month=12, day=31).strftime("%Y-%m-%d")
    else:  # semana
        dias_semana = hoje.weekday()
        inicio_semana_atual = hoje - timedelta(days=dias_semana)
        periodo_atual_inicio = inicio_semana_atual.strftime("%Y-%m-%d")
        periodo_atual_fim = hoje.strftime("%Y-%m-%d")
        inicio_semana_anterior = inicio_semana_atual - timedelta(days=7)
        periodo_anterior_inicio = inicio_semana_anterior.strftime("%Y-%m-%d")
        periodo_anterior_fim = (inicio_semana_atual - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Busca dados do período atual
    dados_atual = _buscar_dados_periodo(conn, periodo_atual_inicio, periodo_atual_fim, referencia)
    
    # Busca dados do período anterior
    dados_anterior = _buscar_dados_periodo(conn, periodo_anterior_inicio, periodo_anterior_fim, referencia)
    
    # Calcula variações
    variacao_impressoes = _calcular_variacao(dados_atual["total_impressos"], dados_anterior["total_impressos"])
    variacao_paginas = _calcular_variacao(dados_atual["total_paginas"], dados_anterior["total_paginas"])
    variacao_custo = _calcular_variacao(dados_atual["custo_total"], dados_anterior["custo_total"])
    
    return {
        "periodo_atual": {
            "inicio": periodo_atual_inicio,
            "fim": periodo_atual_fim,
            "dados": dados_atual
        },
        "periodo_anterior": {
            "inicio": periodo_anterior_inicio,
            "fim": periodo_anterior_fim,
            "dados": dados_anterior
        },
        "variacoes": {
            "impressoes": variacao_impressoes,
            "paginas": variacao_paginas,
            "custo": variacao_custo
        }
    }


def _buscar_dados_periodo(conn: sqlite3.Connection, inicio: str, fim: str, 
                          referencia: Optional[str]) -> Dict:
    """Busca dados agregados de um período"""
    query = """
        SELECT pages_printed, duplex, color_mode, date
        FROM events
        WHERE date(date) >= date(?) AND date(date) <= date(?)
    """
    params = [inicio, fim]
    
    if referencia:
        if referencia.startswith("user:"):
            user = referencia.split(":")[1]
            query += " AND user = ?"
            params.append(user)
        elif referencia.startswith("setor:"):
            setor = referencia.split(":")[1]
            query += " AND user IN (SELECT user FROM users WHERE sector = ?)"
            params.append(setor)
        elif referencia.startswith("impressora:"):
            printer = referencia.split(":")[1]
            query += " AND printer_name = ?"
            params.append(printer)
    
    rows = conn.execute(query, params).fetchall()
    
    total_impressos = len(rows)
    total_paginas = 0
    total_custo = 0.0
    
    # Importa função de cálculo de folhas físicas
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from modules.calculo_impressao import calcular_folhas_fisicas
    from modules.helper_db import custo_unitario_por_data
    
    for row in rows:
        pages = row[0] or 0
        duplex = row[1] if len(row) > 1 else None
        color_mode = row[2] if len(row) > 2 else None
        date_str = row[3] if len(row) > 3 else None
        
        folhas_fisicas = calcular_folhas_fisicas(pages, duplex)
        total_paginas += folhas_fisicas
        
        # Calcula custo
        if date_str:
            data_evento = date_str.split()[0] if " " in date_str else date_str
            if color_mode == 'Color':
                custo = custo_unitario_por_data(data_evento, 'Color')
            elif color_mode == 'Black & White':
                custo = custo_unitario_por_data(data_evento, 'Black & White')
            else:
                custo = custo_unitario_por_data(data_evento, None)
            
            total_custo += folhas_fisicas * custo
    
    return {
        "total_impressos": total_impressos,
        "total_paginas": total_paginas,
        "custo_total": round(total_custo, 2)
    }


def _calcular_variacao(valor_atual: float, valor_anterior: float) -> Dict:
    """Calcula variação percentual e absoluta"""
    if valor_anterior == 0:
        if valor_atual == 0:
            variacao_pct = 0.0
        else:
            variacao_pct = 100.0
    else:
        variacao_pct = ((valor_atual - valor_anterior) / valor_anterior) * 100
    
    variacao_abs = valor_atual - valor_anterior
    
    return {
        "percentual": round(variacao_pct, 2),
        "absoluta": round(variacao_abs, 2),
        "tendencia": "alta" if variacao_pct > 0 else "baixa" if variacao_pct < 0 else "estavel"
    }

