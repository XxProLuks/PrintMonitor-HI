"""
Módulo para geração de heatmaps de uso
"""
import sqlite3
from typing import Dict, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def gerar_heatmap_horarios(conn: sqlite3.Connection, dias: int = 30) -> Dict:
    """Gera heatmap de uso por horário do dia"""
    try:
        data_inicio = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')
        
        # Agrupa por hora do dia
        query = """
            SELECT 
                CAST(strftime('%H', datetime(date || ' ' || COALESCE(time, '00:00:00'))) AS INTEGER) as hora,
                COUNT(*) as total_impressos,
                SUM(CASE WHEN duplex = 1 THEN CEIL(pages_printed / 2.0) ELSE pages_printed END) as total_paginas
            FROM events
            WHERE date >= ?
            GROUP BY hora
            ORDER BY hora
        """
        
        rows = conn.execute(query, (data_inicio,)).fetchall()
        
        horas = []
        valores = []
        for row in rows:
            horas.append(f"{row[0]:02d}:00")
            valores.append(row[1])  # ou row[2] para páginas
        
        return {
            'labels': horas,
            'values': valores,
            'type': 'heatmap_horarios'
        }
    except Exception as e:
        logger.error(f"Erro ao gerar heatmap de horários: {e}")
        return {'labels': [], 'values': []}


def gerar_heatmap_setores(conn: sqlite3.Connection, dias: int = 30) -> Dict:
    """Gera heatmap de uso por setor"""
    try:
        data_inicio = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')
        
        query = """
            SELECT 
                COALESCE(sector, 'Sem Setor') as setor,
                COUNT(*) as total_impressos,
                SUM(CASE WHEN duplex = 1 THEN CEIL(pages_printed / 2.0) ELSE pages_printed END) as total_paginas
            FROM events
            WHERE date >= ?
            GROUP BY setor
            ORDER BY total_impressos DESC
        """
        
        rows = conn.execute(query, (data_inicio,)).fetchall()
        
        setores = []
        valores = []
        for row in rows:
            setores.append(row[0])
            valores.append(row[1])
        
        return {
            'labels': setores,
            'values': valores,
            'type': 'heatmap_setores'
        }
    except Exception as e:
        logger.error(f"Erro ao gerar heatmap de setores: {e}")
        return {'labels': [], 'values': []}


def gerar_heatmap_semanal(conn: sqlite3.Connection, semanas: int = 8) -> Dict:
    """Gera heatmap de uso por dia da semana"""
    try:
        data_inicio = (datetime.now() - timedelta(weeks=semanas)).strftime('%Y-%m-%d')
        
        query = """
            SELECT 
                strftime('%w', date) as dia_semana,
                CASE strftime('%w', date)
                    WHEN '0' THEN 'Domingo'
                    WHEN '1' THEN 'Segunda'
                    WHEN '2' THEN 'Terça'
                    WHEN '3' THEN 'Quarta'
                    WHEN '4' THEN 'Quinta'
                    WHEN '5' THEN 'Sexta'
                    WHEN '6' THEN 'Sábado'
                END as dia_nome,
                COUNT(*) as total
            FROM events
            WHERE date >= ?
            GROUP BY dia_semana
            ORDER BY dia_semana
        """
        
        rows = conn.execute(query, (data_inicio,)).fetchall()
        
        dias = []
        valores = []
        for row in rows:
            dias.append(row[1])
            valores.append(row[2])
        
        return {
            'labels': dias,
            'values': valores,
            'type': 'heatmap_semanal'
        }
    except Exception as e:
        logger.error(f"Erro ao gerar heatmap semanal: {e}")
        return {'labels': [], 'values': []}

