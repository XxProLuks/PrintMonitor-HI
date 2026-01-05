"""
Módulo de Sistema de Pontuação de Eficiência
IA que atribui "scores" de eficiência para usuários, setores e impressoras
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
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


def calcular_score_eficiencia_usuario(conn: sqlite3.Connection, usuario: str, 
                                     dias: int = 30) -> Dict:
    """
    Calcula score de eficiência para um usuário
    
    Args:
        conn: Conexão com banco de dados
        usuario: Nome do usuário
        dias: Período de análise
        
    Returns:
        Dicionário com score e detalhes
    """
    try:
        data_inicio = datetime.now() - timedelta(days=dias)
        
        query = """
            SELECT 
                e.pages_printed,
                e.duplex,
                e.color_mode,
                e.date
            FROM events e
            WHERE e.user = ? AND e.date >= ?
        """
        
        rows = conn.execute(query, (usuario, data_inicio.isoformat())).fetchall()
        
        if not rows:
            return {
                'usuario': usuario,
                'score': 0,
                'nivel': 'sem_dados'
            }
        
        total_impressoes = len(rows)
        total_paginas = 0
        total_duplex = 0
        total_color = 0
        
        for row in rows:
            folhas = calcular_folhas_fisicas(row[0] or 0, row[1])
            total_paginas += folhas
            
            if row[1] == 1:
                total_duplex += 1
            
            if row[2] == 'Color':
                total_color += 1
        
        # Calcula métricas
        percentual_duplex = (total_duplex / total_impressoes * 100) if total_impressoes > 0 else 0
        percentual_color = (total_color / total_impressoes * 100) if total_impressoes > 0 else 0
        
        # Score base (0-100)
        score = 50  # Base
        
        # Bônus por uso de duplex
        if percentual_duplex > 50:
            score += 20
        elif percentual_duplex > 30:
            score += 10
        elif percentual_duplex > 10:
            score += 5
        
        # Penalidade por uso excessivo de cor
        if percentual_color > 50:
            score -= 20
        elif percentual_color > 30:
            score -= 10
        elif percentual_color > 10:
            score -= 5
        
        # Bônus por volume moderado
        media_diaria = total_paginas / dias if dias > 0 else 0
        if 10 <= media_diaria <= 100:
            score += 10
        elif media_diaria > 200:
            score -= 10
        
        # Normaliza score (0-100)
        score = max(0, min(100, score))
        
        # Classifica nível
        if score >= 80:
            nivel = 'excelente'
        elif score >= 60:
            nivel = 'bom'
        elif score >= 40:
            nivel = 'regular'
        else:
            nivel = 'precisa_melhorar'
        
        return {
            'usuario': usuario,
            'score': round(score, 1),
            'nivel': nivel,
            'total_impressoes': total_impressoes,
            'total_paginas': total_paginas,
            'percentual_duplex': round(percentual_duplex, 1),
            'percentual_color': round(percentual_color, 1),
            'media_diaria': round(media_diaria, 1),
            'fatores': {
                'duplex': 'alto' if percentual_duplex > 50 else 'medio' if percentual_duplex > 30 else 'baixo',
                'color': 'alto' if percentual_color > 50 else 'medio' if percentual_color > 30 else 'baixo',
                'volume': 'moderado' if 10 <= media_diaria <= 100 else 'alto' if media_diaria > 100 else 'baixo'
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao calcular score: {e}")
        return {
            'usuario': usuario,
            'score': 0,
            'nivel': 'erro',
            'erro': str(e)
        }


def calcular_score_eficiencia_setor(conn: sqlite3.Connection, setor: str, 
                                   dias: int = 30) -> Dict:
    """
    Calcula score de eficiência para um setor
    
    Args:
        conn: Conexão com banco de dados
        setor: Nome do setor
        dias: Período de análise
        
    Returns:
        Dicionário com score e detalhes
    """
    try:
        data_inicio = datetime.now() - timedelta(days=dias)
        
        query = """
            SELECT 
                e.user,
                e.pages_printed,
                e.duplex,
                e.color_mode
            FROM events e
            WHERE e.sector = ? AND e.date >= ?
        """
        
        rows = conn.execute(query, (setor, data_inicio.isoformat())).fetchall()
        
        if not rows:
            return {
                'setor': setor,
                'score': 0,
                'nivel': 'sem_dados'
            }
        
        # Calcula métricas do setor
        total_impressoes = len(rows)
        total_duplex = sum(1 for r in rows if r[2] == 1)
        total_color = sum(1 for r in rows if r[3] == 'Color')
        
        percentual_duplex = (total_duplex / total_impressoes * 100) if total_impressoes > 0 else 0
        percentual_color = (total_color / total_impressoes * 100) if total_impressoes > 0 else 0
        
        # Score baseado em métricas do setor
        score = 50
        
        if percentual_duplex > 50:
            score += 20
        elif percentual_duplex > 30:
            score += 10
        
        if percentual_color > 50:
            score -= 20
        elif percentual_color > 30:
            score -= 10
        
        score = max(0, min(100, score))
        
        nivel = 'excelente' if score >= 80 else 'bom' if score >= 60 else 'regular' if score >= 40 else 'precisa_melhorar'
        
        return {
            'setor': setor,
            'score': round(score, 1),
            'nivel': nivel,
            'total_impressoes': total_impressoes,
            'percentual_duplex': round(percentual_duplex, 1),
            'percentual_color': round(percentual_color, 1)
        }
        
    except Exception as e:
        logger.error(f"Erro ao calcular score do setor: {e}")
        return {
            'setor': setor,
            'score': 0,
            'nivel': 'erro',
            'erro': str(e)
        }


def obter_ranking_eficiencia(conn: sqlite3.Connection, tipo: str = 'usuario', 
                            dias: int = 30, limite: int = 10) -> List[Dict]:
    """
    Obtém ranking de eficiência
    
    Args:
        conn: Conexão com banco de dados
        tipo: 'usuario' ou 'setor'
        dias: Período de análise
        limite: Número de resultados
        
    Returns:
        Lista de rankings
    """
    try:
        if tipo == 'usuario':
            # Busca todos os usuários
            query = """
                SELECT DISTINCT user
                FROM events
                WHERE user IS NOT NULL AND user != ''
            """
            rows = conn.execute(query).fetchall()
            
            scores = []
            for row in rows:
                usuario = row[0]
                score_data = calcular_score_eficiencia_usuario(conn, usuario, dias)
                if score_data.get('score', 0) > 0:
                    scores.append(score_data)
            
            # Ordena por score
            scores.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            return scores[:limite]
        
        elif tipo == 'setor':
            # Busca todos os setores
            query = """
                SELECT DISTINCT sector
                FROM events
                WHERE sector IS NOT NULL AND sector != ''
            """
            rows = conn.execute(query).fetchall()
            
            scores = []
            for row in rows:
                setor = row[0]
                score_data = calcular_score_eficiencia_setor(conn, setor, dias)
                if score_data.get('score', 0) > 0:
                    scores.append(score_data)
            
            # Ordena por score
            scores.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            return scores[:limite]
        
        return []
        
    except Exception as e:
        logger.error(f"Erro ao obter ranking: {e}")
        return []

