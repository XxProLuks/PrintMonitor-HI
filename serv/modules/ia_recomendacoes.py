"""
Módulo de Recomendação Inteligente de Configurações
Sistema que aprende preferências de usuários e sugere configurações ideais
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import math

# Usa módulo centralizado de cálculos
from modules.calculo_impressao import calcular_folhas_fisicas

logger = logging.getLogger(__name__)


def analisar_preferencias_usuario(conn: sqlite3.Connection, usuario: str, 
                                  dias: int = 90) -> Dict:
    """
    Analisa preferências de impressão de um usuário
    
    Args:
        conn: Conexão com banco de dados
        usuario: Nome do usuário
        dias: Período de análise
        
    Returns:
        Dicionário com preferências detectadas
    """
    try:
        data_inicio = datetime.now() - timedelta(days=dias)
        
        query = """
            SELECT 
                e.color_mode,
                e.duplex,
                e.pages_printed,
                e.paper_size,
                e.document_name
            FROM events e
            WHERE e.user = ? AND e.date >= ?
        """
        
        rows = conn.execute(query, (usuario, data_inicio.isoformat())).fetchall()
        
        if not rows:
            return {
                'usuario': usuario,
                'total_impressoes': 0,
                'preferencias': {}
            }
        
        total = len(rows)
        color_count = sum(1 for r in rows if r[0] == 'Color')
        duplex_count = sum(1 for r in rows if r[1] == 1)
        
        # Tamanhos de papel mais usados
        paper_sizes = {}
        for row in rows:
            size = row[3] or 'A4'
            paper_sizes[size] = paper_sizes.get(size, 0) + 1
        
        tamanho_preferido = max(paper_sizes.items(), key=lambda x: x[1])[0] if paper_sizes else 'A4'
        
        return {
            'usuario': usuario,
            'total_impressoes': total,
            'preferencias': {
                'color_percentual': (color_count / total * 100) if total > 0 else 0,
                'duplex_percentual': (duplex_count / total * 100) if total > 0 else 0,
                'tamanho_preferido': tamanho_preferido,
                'prefere_color': color_count > total * 0.5,
                'prefere_duplex': duplex_count > total * 0.5
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao analisar preferências: {e}")
        return {}


def recomendar_configuracao(conn: sqlite3.Connection, usuario: str, 
                            documento: str = '', paginas: int = 0) -> Dict:
    """
    Recomenda configuração ideal para uma impressão
    
    Args:
        conn: Conexão com banco de dados
        usuario: Nome do usuário
        documento: Nome do documento (opcional)
        paginas: Número de páginas (opcional)
        
    Returns:
        Dicionário com recomendações
    """
    try:
        preferencias = analisar_preferencias_usuario(conn, usuario)
        
        if not preferencias or preferencias.get('total_impressoes', 0) == 0:
            # Sem histórico, usa recomendações padrão
            return {
                'color_mode': 'Black & White' if paginas > 10 else 'Color',
                'duplex': 1 if paginas >= 4 else 0,
                'paper_size': 'A4',
                'confianca': 0.5,
                'motivo': 'Sem histórico do usuário'
            }
        
        pref = preferencias.get('preferencias', {})
        
        # Recomendações baseadas em histórico
        recomendacoes = {
            'color_mode': 'Color' if pref.get('prefere_color', False) else 'Black & White',
            'duplex': 1 if pref.get('prefere_duplex', False) or paginas >= 4 else 0,
            'paper_size': pref.get('tamanho_preferido', 'A4'),
            'confianca': 0.8,
            'motivo': 'Baseado no histórico do usuário'
        }
        
        # Ajustes baseados em número de páginas
        if paginas > 0:
            if paginas >= 10 and recomendacoes['duplex'] == 0:
                recomendacoes['duplex'] = 1
                recomendacoes['motivo'] += ' (muitas páginas, use duplex)'
            
            if paginas > 50:
                recomendacoes['color_mode'] = 'Black & White'
                recomendacoes['motivo'] += ' (documento grande, use B&W)'
        
        return recomendacoes
        
    except Exception as e:
        logger.error(f"Erro ao recomendar configuração: {e}")
        return {
            'color_mode': 'Black & White',
            'duplex': 0,
            'paper_size': 'A4',
            'confianca': 0.0,
            'erro': str(e)
        }

