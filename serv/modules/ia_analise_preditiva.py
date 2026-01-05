"""
Módulo de Análise Preditiva de Necessidades
Prever quando será necessário repor materiais (toner, papel) antes que acabem
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import math

# Usa módulo centralizado de cálculos
from modules.calculo_impressao import calcular_folhas_fisicas

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logger.warning("pandas não disponível. Funcionalidades limitadas.")

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False


def calcular_consumo_materiais(conn: sqlite3.Connection, dias: int = 30) -> Dict:
    """
    Calcula consumo de materiais (toner, papel)
    
    Args:
        conn: Conexão com banco de dados
        dias: Período de análise
        
    Returns:
        Dicionário com consumo de materiais
    """
    try:
        data_inicio = datetime.now() - timedelta(days=dias)
        
        query = """
            SELECT 
                e.printer_name,
                e.pages_printed,
                e.duplex,
                e.color_mode,
                e.date
            FROM events e
            WHERE e.date >= ?
        """
        
        rows = conn.execute(query, (data_inicio.isoformat(),)).fetchall()
        
        consumo = {
            'papel_total': 0,
            'toner_color': 0,
            'toner_bw': 0,
            'por_impressora': {}
        }
        
        for row in rows:
            printer = row[0] or 'Desconhecida'
            folhas = calcular_folhas_fisicas(row[1] or 0, row[2])
            color = row[3] == 'Color'
            
            consumo['papel_total'] += folhas
            
            if color:
                consumo['toner_color'] += folhas
            else:
                consumo['toner_bw'] += folhas
            
            if printer not in consumo['por_impressora']:
                consumo['por_impressora'][printer] = {
                    'papel': 0,
                    'toner_color': 0,
                    'toner_bw': 0
                }
            
            consumo['por_impressora'][printer]['papel'] += folhas
            if color:
                consumo['por_impressora'][printer]['toner_color'] += folhas
            else:
                consumo['por_impressora'][printer]['toner_bw'] += folhas
        
        # Calcula médias diárias
        consumo['papel_medio_dia'] = consumo['papel_total'] / dias if dias > 0 else 0
        consumo['toner_color_medio_dia'] = consumo['toner_color'] / dias if dias > 0 else 0
        consumo['toner_bw_medio_dia'] = consumo['toner_bw'] / dias if dias > 0 else 0
        
        return consumo
        
    except Exception as e:
        logger.error(f"Erro ao calcular consumo: {e}")
        return {}


def prever_reposicao_materiais(conn: sqlite3.Connection, 
                               capacidade_toner: int = 5000,
                               capacidade_papel: int = 10000) -> Dict:
    """
    Prever quando será necessário repor materiais
    
    Args:
        conn: Conexão com banco de dados
        capacidade_toner: Capacidade do toner (páginas)
        capacidade_papel: Capacidade do papel (folhas)
        
    Returns:
        Dicionário com previsões de reposição
    """
    try:
        # Calcula consumo dos últimos 30 dias
        consumo = calcular_consumo_materiais(conn, dias=30)
        
        if not consumo:
            return {
                'erro': 'Sem dados de consumo'
            }
        
        # Previsões simples baseadas em média
        papel_medio_dia = consumo.get('papel_medio_dia', 0)
        toner_color_medio_dia = consumo.get('toner_color_medio_dia', 0)
        toner_bw_medio_dia = consumo.get('toner_bw_medio_dia', 0)
        
        previsoes = {
            'papel': {},
            'toner_color': {},
            'toner_bw': {}
        }
        
        # Previsão de papel
        if papel_medio_dia > 0:
            dias_restantes = capacidade_papel / papel_medio_dia
            data_reposicao = datetime.now() + timedelta(days=dias_restantes)
            
            previsoes['papel'] = {
                'dias_restantes': int(dias_restantes),
                'data_reposicao': data_reposicao.strftime('%Y-%m-%d'),
                'consumo_medio_dia': papel_medio_dia,
                'alerta': dias_restantes < 7,
                'aviso': dias_restantes < 14
            }
        
        # Previsão de toner colorido
        if toner_color_medio_dia > 0:
            dias_restantes = capacidade_toner / toner_color_medio_dia
            data_reposicao = datetime.now() + timedelta(days=dias_restantes)
            
            previsoes['toner_color'] = {
                'dias_restantes': int(dias_restantes),
                'data_reposicao': data_reposicao.strftime('%Y-%m-%d'),
                'consumo_medio_dia': toner_color_medio_dia,
                'alerta': dias_restantes < 7,
                'aviso': dias_restantes < 14
            }
        
        # Previsão de toner B&W
        if toner_bw_medio_dia > 0:
            dias_restantes = capacidade_toner / toner_bw_medio_dia
            data_reposicao = datetime.now() + timedelta(days=dias_restantes)
            
            previsoes['toner_bw'] = {
                'dias_restantes': int(dias_restantes),
                'data_reposicao': data_reposicao.strftime('%Y-%m-%d'),
                'consumo_medio_dia': toner_bw_medio_dia,
                'alerta': dias_restantes < 7,
                'aviso': dias_restantes < 14
            }
        
        return {
            'previsoes': previsoes,
            'consumo_atual': consumo,
            'data_previsao': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao prever reposição: {e}")
        return {
            'erro': str(e)
        }


def sugerir_compra_materiais(conn: sqlite3.Connection) -> List[Dict]:
    """
    Sugere compra de materiais baseado em previsões
    
    Args:
        conn: Conexão com banco de dados
        
    Returns:
        Lista de sugestões de compra
    """
    try:
        previsoes = prever_reposicao_materiais(conn)
        
        if 'erro' in previsoes:
            return []
        
        sugestoes = []
        previsoes_data = previsoes.get('previsoes', {})
        
        # Sugestão de papel
        if 'papel' in previsoes_data:
            papel = previsoes_data['papel']
            if papel.get('alerta') or papel.get('aviso'):
                sugestoes.append({
                    'material': 'Papel',
                    'prioridade': 'alta' if papel.get('alerta') else 'media',
                    'dias_restantes': papel.get('dias_restantes', 0),
                    'data_reposicao': papel.get('data_reposicao'),
                    'quantidade_sugerida': 10000,  # Exemplo
                    'motivo': f'Reposição necessária em {papel.get("dias_restantes", 0)} dias'
                })
        
        # Sugestão de toner colorido
        if 'toner_color' in previsoes_data:
            toner_color = previsoes_data['toner_color']
            if toner_color.get('alerta') or toner_color.get('aviso'):
                sugestoes.append({
                    'material': 'Toner Colorido',
                    'prioridade': 'alta' if toner_color.get('alerta') else 'media',
                    'dias_restantes': toner_color.get('dias_restantes', 0),
                    'data_reposicao': toner_color.get('data_reposicao'),
                    'quantidade_sugerida': 2,  # Exemplo
                    'motivo': f'Reposição necessária em {toner_color.get("dias_restantes", 0)} dias'
                })
        
        # Sugestão de toner B&W
        if 'toner_bw' in previsoes_data:
            toner_bw = previsoes_data['toner_bw']
            if toner_bw.get('alerta') or toner_bw.get('aviso'):
                sugestoes.append({
                    'material': 'Toner Preto e Branco',
                    'prioridade': 'alta' if toner_bw.get('alerta') else 'media',
                    'dias_restantes': toner_bw.get('dias_restantes', 0),
                    'data_reposicao': toner_bw.get('data_reposicao'),
                    'quantidade_sugerida': 3,  # Exemplo
                    'motivo': f'Reposição necessária em {toner_bw.get("dias_restantes", 0)} dias'
                })
        
        return sugestoes
        
    except Exception as e:
        logger.error(f"Erro ao sugerir compra: {e}")
        return []

