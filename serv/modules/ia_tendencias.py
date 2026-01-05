"""
Módulo de Análise de Tendências e Padrões
IA que identifica tendências de longo prazo e padrões ocultos nos dados
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import math
from collections import defaultdict

# Usa módulo centralizado de cálculos
from modules.calculo_impressao import calcular_folhas_fisicas

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


def analisar_tendencia_crescimento(conn: sqlite3.Connection, meses: int = 6) -> Dict:
    """
    Analisa tendência de crescimento/redução de impressões
    
    Args:
        conn: Conexão com banco de dados
        meses: Período de análise
        
    Returns:
        Dicionário com análise de tendência
    """
    try:
        data_inicio = datetime.now() - timedelta(days=meses * 30)
        
        query = """
            SELECT 
                DATE(e.date) as data,
                e.pages_printed,
                e.duplex
            FROM events e
            WHERE e.date >= ?
            ORDER BY e.date ASC
        """
        
        rows = conn.execute(query, (data_inicio.isoformat(),)).fetchall()
        
        if not rows:
            return {
                'tendencia': 'sem_dados',
                'crescimento_percentual': 0
            }
        
        # Agrupa por mês
        por_mes = defaultdict(lambda: {'paginas': 0, 'impressoes': 0})
        
        for row in rows:
            data_str = row[0]
            try:
                if isinstance(data_str, str):
                    dt = datetime.strptime(data_str, '%Y-%m-%d')
                else:
                    dt = data_str
                
                mes_ano = dt.strftime('%Y-%m')
                folhas = calcular_folhas_fisicas(row[1] or 0, row[2])
                
                por_mes[mes_ano]['paginas'] += folhas
                por_mes[mes_ano]['impressoes'] += 1
            except:
                pass
        
        meses_ordenados = sorted(por_mes.items())
        
        if len(meses_ordenados) < 2:
            return {
                'tendencia': 'insuficiente',
                'crescimento_percentual': 0
            }
        
        # Calcula tendência
        primeiro_mes = meses_ordenados[0][1]['paginas']
        ultimo_mes = meses_ordenados[-1][1]['paginas']
        
        if primeiro_mes > 0:
            crescimento = ((ultimo_mes - primeiro_mes) / primeiro_mes) * 100
        else:
            crescimento = 100 if ultimo_mes > 0 else 0
        
        # Classifica tendência
        if crescimento > 10:
            tendencia = 'crescimento_alto'
        elif crescimento > 0:
            tendencia = 'crescimento'
        elif crescimento > -10:
            tendencia = 'estavel'
        else:
            tendencia = 'reducao'
        
        return {
            'tendencia': tendencia,
            'crescimento_percentual': crescimento,
            'primeiro_mes': primeiro_mes,
            'ultimo_mes': ultimo_mes,
            'dados_mensais': [
                {'mes': mes, 'paginas': dados['paginas'], 'impressoes': dados['impressoes']}
                for mes, dados in meses_ordenados
            ]
        }
        
    except Exception as e:
        logger.error(f"Erro ao analisar tendência: {e}")
        return {
            'tendencia': 'erro',
            'crescimento_percentual': 0,
            'erro': str(e)
        }


def analisar_padroes_sazonais(conn: sqlite3.Connection, anos: int = 2) -> Dict:
    """
    Analisa padrões sazonais (ex: mais impressões em dezembro)
    
    Args:
        conn: Conexão com banco de dados
        anos: Anos de histórico
        
    Returns:
        Dicionário com padrões sazonais
    """
    try:
        data_inicio = datetime.now() - timedelta(days=anos * 365)
        
        query = """
            SELECT 
                e.date,
                e.pages_printed,
                e.duplex
            FROM events e
            WHERE e.date >= ?
        """
        
        rows = conn.execute(query, (data_inicio.isoformat(),)).fetchall()
        
        if not rows:
            return {
                'padroes': {}
            }
        
        # Agrupa por mês
        por_mes = defaultdict(lambda: {'paginas': 0, 'impressoes': 0})
        
        for row in rows:
            data_evento = datetime.fromisoformat(row[0]) if isinstance(row[0], str) else row[0]
            mes = data_evento.month
            folhas = calcular_folhas_fisicas(row[1] or 0, row[2])
            
            por_mes[mes]['paginas'] += folhas
            por_mes[mes]['impressoes'] += 1
        
        # Calcula média por mês
        meses_nomes = {
            1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
            5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
            9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
        }
        
        padroes = {}
        for mes, dados in por_mes.items():
            padroes[meses_nomes[mes]] = {
                'paginas': dados['paginas'],
                'impressoes': dados['impressoes'],
                'media_paginas': dados['paginas'] / anos if anos > 0 else dados['paginas']
            }
        
        # Identifica picos
        media_geral = sum(d['paginas'] for d in padroes.values()) / len(padroes) if padroes else 0
        picos = [
            {'mes': mes, 'paginas': dados['paginas'], 'desvio': dados['paginas'] - media_geral}
            for mes, dados in padroes.items()
            if dados['paginas'] > media_geral * 1.2
        ]
        
        return {
            'padroes': padroes,
            'picos': sorted(picos, key=lambda x: x['paginas'], reverse=True),
            'media_geral': media_geral
        }
        
    except Exception as e:
        logger.error(f"Erro ao analisar padrões sazonais: {e}")
        return {
            'padroes': {},
            'erro': str(e)
        }


def obter_insights_tendencias(conn: sqlite3.Connection) -> Dict:
    """
    Obtém insights gerais sobre tendências
    
    Args:
        conn: Conexão com banco de dados
        
    Returns:
        Dicionário com insights
    """
    try:
        tendencia = analisar_tendencia_crescimento(conn, meses=6)
        sazonal = analisar_padroes_sazonais(conn, anos=2)
        
        insights = []
        
        # Insight sobre crescimento
        if tendencia.get('tendencia') == 'crescimento_alto':
            insights.append({
                'tipo': 'alerta',
                'titulo': 'Crescimento acelerado detectado',
                'mensagem': f'Crescimento de {tendencia.get("crescimento_percentual", 0):.1f}% nos últimos 6 meses',
                'acao': 'Revisar orçamento e políticas de impressão'
            })
        elif tendencia.get('tendencia') == 'reducao':
            insights.append({
                'tipo': 'positivo',
                'titulo': 'Redução de impressões',
                'mensagem': f'Redução de {abs(tendencia.get("crescimento_percentual", 0)):.1f}% nos últimos 6 meses',
                'acao': 'Manter políticas de economia'
            })
        
        # Insight sobre sazonalidade
        if sazonal.get('picos'):
            pico = sazonal['picos'][0]
            insights.append({
                'tipo': 'info',
                'titulo': 'Padrão sazonal identificado',
                'mensagem': f'Pico de impressões em {pico["mes"]}',
                'acao': 'Planejar estoque e recursos para este período'
            })
        
        return {
            'tendencia': tendencia,
            'sazonal': sazonal,
            'insights': insights,
            'data_analise': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter insights: {e}")
        return {
            'erro': str(e)
        }

