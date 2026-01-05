"""
Módulo de Otimização Automática de Recursos
Sugere otimizações automáticas baseadas em padrões de uso
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import math

# Usa módulo centralizado de cálculos
from modules.calculo_impressao import calcular_folhas_fisicas, calcular_economia_duplex

logger = logging.getLogger(__name__)


def analisar_uso_impressoras(conn: sqlite3.Connection, dias: int = 30) -> Dict:
    """
    Analisa uso de impressoras para otimização
    
    Args:
        conn: Conexão com banco de dados
        dias: Período de análise
        
    Returns:
        Dicionário com análise de uso
    """
    try:
        data_inicio = datetime.now() - timedelta(days=dias)
        
        query = """
            SELECT 
                e.printer_name,
                e.pages_printed,
                e.duplex,
                e.color_mode,
                e.sector,
                COUNT(*) as total_impressoes
            FROM events e
            WHERE e.date >= ?
            GROUP BY e.printer_name
        """
        
        rows = conn.execute(query, (data_inicio.isoformat(),)).fetchall()
        
        impressoras = {}
        # OTIMIZAÇÃO: Busca todos os eventos de uma vez em vez de por impressora (evita N+1)
        printer_names = [row[0] for row in rows if row[0]]
        detalhes_por_impressora = {}
        
        if printer_names:
            # Busca todos os eventos de uma vez
            placeholders = ','.join(['?'] * len(printer_names))
            query_detalhes = f"""
                SELECT printer_name, pages_printed, duplex, color_mode, sector
                FROM events
                WHERE printer_name IN ({placeholders}) AND date >= ?
            """
            all_detalhes = conn.execute(query_detalhes, printer_names + [data_inicio.isoformat()]).fetchall()
            
            # Agrupa detalhes por impressora
            for det in all_detalhes:
                printer_name = det[0] or 'Desconhecida'
                if printer_name not in detalhes_por_impressora:
                    detalhes_por_impressora[printer_name] = []
                detalhes_por_impressora[printer_name].append(det[1:])  # [pages, duplex, color_mode, sector]
        
        for row in rows:
            printer_name = row[0] or 'Desconhecida'
            if printer_name not in impressoras:
                impressoras[printer_name] = {
                    'nome': printer_name,
                    'total_impressoes': 0,
                    'total_paginas': 0,
                    'impressoes_color': 0,
                    'impressoes_bw': 0,
                    'impressoes_duplex': 0,
                    'impressoes_simplex': 0,
                    'setores': set()
                }
            
            # Usa detalhes já carregados (sem query N+1)
            detalhes = detalhes_por_impressora.get(printer_name, [])
            
            for det in detalhes:
                # det é [pages_printed, duplex, color_mode, sector]
                pages = det[0] if len(det) > 0 else 0
                duplex = det[1] if len(det) > 1 else 0
                color_mode = det[2] if len(det) > 2 else None
                sector = det[3] if len(det) > 3 else None
                
                folhas = calcular_folhas_fisicas(pages or 0, duplex)
                impressoras[printer_name]['total_paginas'] += folhas
                impressoras[printer_name]['total_impressoes'] += 1
                
                if color_mode == 'Color':
                    impressoras[printer_name]['impressoes_color'] += 1
                else:
                    impressoras[printer_name]['impressoes_bw'] += 1
                
                if duplex == 1:
                    impressoras[printer_name]['impressoes_duplex'] += 1
                else:
                    impressoras[printer_name]['impressoes_simplex'] += 1
                
                if sector:
                    impressoras[printer_name]['setores'].add(sector)
        
        # Converte sets para listas
        for printer_name in impressoras:
            impressoras[printer_name]['setores'] = list(impressoras[printer_name]['setores'])
        
        return impressoras
        
    except Exception as e:
        logger.error(f"Erro ao analisar uso de impressoras: {e}")
        return {}


def sugerir_otimizacoes_duplex(conn: sqlite3.Connection, dias: int = 30) -> List[Dict]:
    """
    Sugere quando usar duplex baseado em padrões
    
    Args:
        conn: Conexão com banco de dados
        dias: Período de análise
        
    Returns:
        Lista de sugestões de otimização
    """
    try:
        data_inicio = datetime.now() - timedelta(days=dias)
        
        # Busca impressões simplex que poderiam ser duplex
        query = """
            SELECT 
                e.user,
                e.printer_name,
                e.pages_printed,
                e.document_name,
                e.date,
                e.sector
            FROM events e
            WHERE e.date >= ? 
                AND e.duplex = 0 
                AND e.pages_printed >= 4
            ORDER BY e.pages_printed DESC
            LIMIT 100
        """
        
        rows = conn.execute(query, (data_inicio.isoformat(),)).fetchall()
        
        sugestoes = []
        for row in rows:
            pages = row[2] or 0
            economia_potencial = math.ceil(pages / 2.0)  # Folhas economizadas com duplex
            
            sugestoes.append({
                'tipo': 'duplex',
                'usuario': row[0] or 'Desconhecido',
                'impressora': row[1] or 'Desconhecida',
                'documento': row[3] or '',
                'data': row[4],
                'paginas_atuais': pages,
                'paginas_economizadas': economia_potencial,
                'economia_percentual': (economia_potencial / pages * 100) if pages > 0 else 0,
                'setor': row[5] or 'Desconhecido',
                'prioridade': 'alta' if pages > 20 else 'media'
            })
        
        return sugestoes
        
    except Exception as e:
        logger.error(f"Erro ao sugerir otimizações duplex: {e}")
        return []


def sugerir_otimizacoes_cor(conn: sqlite3.Connection, dias: int = 30) -> List[Dict]:
    """
    Sugere quando usar B&W ao invés de cor
    
    Args:
        conn: Conexão com banco de dados
        dias: Período de análise
        
    Returns:
        Lista de sugestões
    """
    try:
        data_inicio = datetime.now() - timedelta(days=dias)
        
        # Busca impressões coloridas
        query = """
            SELECT 
                e.user,
                e.printer_name,
                e.pages_printed,
                e.duplex,
                e.document_name,
                e.date,
                e.sector
            FROM events e
            WHERE e.date >= ? 
                AND e.color_mode = 'Color'
            ORDER BY e.pages_printed DESC
            LIMIT 100
        """
        
        rows = conn.execute(query, (data_inicio.isoformat(),)).fetchall()
        
        sugestoes = []
        for row in rows:
            pages = row[2] or 0
            folhas = calcular_folhas_fisicas(pages, row[3])
            
            # Estima economia (cor geralmente custa 2x mais)
            custo_atual = folhas * 0.10  # Exemplo: R$ 0,10 por folha colorida
            custo_bw = folhas * 0.05    # Exemplo: R$ 0,05 por folha B&W
            economia = custo_atual - custo_bw
            
            sugestoes.append({
                'tipo': 'cor_para_bw',
                'usuario': row[0] or 'Desconhecido',
                'impressora': row[1] or 'Desconhecida',
                'documento': row[4] or '',
                'data': row[5],
                'paginas': folhas,
                'economia_estimada': economia,
                'setor': row[6] or 'Desconhecido',
                'prioridade': 'alta' if folhas > 50 else 'media'
            })
        
        return sugestoes
        
    except Exception as e:
        logger.error(f"Erro ao sugerir otimizações de cor: {e}")
        return []


def sugerir_distribuicao_impressoras(conn: sqlite3.Connection) -> List[Dict]:
    """
    Sugere melhor distribuição de impressoras por setor
    
    Args:
        conn: Conexão com banco de dados
        
    Returns:
        Lista de sugestões
    """
    try:
        # Analisa uso por setor
        query = """
            SELECT 
                e.sector,
                e.printer_name,
                COUNT(*) as total_impressoes,
                SUM(CASE WHEN e.pages_printed IS NOT NULL THEN e.pages_printed ELSE 0 END) as total_paginas
            FROM events e
            WHERE e.sector IS NOT NULL AND e.sector != ''
            GROUP BY e.sector, e.printer_name
        """
        
        rows = conn.execute(query).fetchall()
        
        # Agrupa por setor
        setores = {}
        for row in rows:
            setor = row[0]
            printer = row[1] or 'Desconhecida'
            impressoes = row[2]
            paginas = row[3] or 0
            
            if setor not in setores:
                setores[setor] = {
                    'impressoras': {},
                    'total_impressoes': 0,
                    'total_paginas': 0
                }
            
            setores[setor]['impressoras'][printer] = {
                'impressoes': impressoes,
                'paginas': paginas
            }
            setores[setor]['total_impressoes'] += impressoes
            setores[setor]['total_paginas'] += paginas
        
        # Gera sugestões
        sugestoes = []
        for setor, dados in setores.items():
            if len(dados['impressoras']) > 1:
                # Múltiplas impressoras no mesmo setor - pode otimizar
                impressoras_ordenadas = sorted(
                    dados['impressoras'].items(),
                    key=lambda x: x[1]['impressoes'],
                    reverse=True
                )
                
                principal = impressoras_ordenadas[0]
                outras = impressoras_ordenadas[1:]
                
                for outra_impressora, dados_outra in outras:
                    if dados_outra['impressoes'] < principal[1]['impressoes'] * 0.1:
                        # Impressora pouco usada - pode ser consolidada
                        sugestoes.append({
                            'tipo': 'consolidacao',
                            'setor': setor,
                            'impressora_principal': principal[0],
                            'impressora_consolidar': outra_impressora,
                            'impressoes_consolidar': dados_outra['impressoes'],
                            'economia_estimada': dados_outra['impressoes'] * 0.02,  # Exemplo
                            'prioridade': 'baixa'
                        })
        
        return sugestoes
        
    except Exception as e:
        logger.error(f"Erro ao sugerir distribuição: {e}")
        return []


def obter_otimizacoes_completas(conn: sqlite3.Connection, dias: int = 30) -> Dict:
    """
    Obtém todas as sugestões de otimização
    
    Args:
        conn: Conexão com banco de dados
        dias: Período de análise
        
    Returns:
        Dicionário com todas as otimizações
    """
    try:
        sugestoes_duplex = sugerir_otimizacoes_duplex(conn, dias)
        sugestoes_cor = sugerir_otimizacoes_cor(conn, dias)
        sugestoes_distribuicao = sugerir_distribuicao_impressoras(conn)
        
        # Calcula economia total estimada
        economia_duplex = sum(s.get('paginas_economizadas', 0) * 0.05 for s in sugestoes_duplex)
        economia_cor = sum(s.get('economia_estimada', 0) for s in sugestoes_cor)
        economia_distribuicao = sum(s.get('economia_estimada', 0) for s in sugestoes_distribuicao)
        
        return {
            'sugestoes_duplex': sugestoes_duplex,
            'sugestoes_cor': sugestoes_cor,
            'sugestoes_distribuicao': sugestoes_distribuicao,
            'total_sugestoes': len(sugestoes_duplex) + len(sugestoes_cor) + len(sugestoes_distribuicao),
            'economia_total_estimada': economia_duplex + economia_cor + economia_distribuicao,
            'economia_duplex': economia_duplex,
            'economia_cor': economia_cor,
            'economia_distribuicao': economia_distribuicao,
            'analise_impressoras': analisar_uso_impressoras(conn, dias)
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter otimizações completas: {e}")
        return {
            'sugestoes_duplex': [],
            'sugestoes_cor': [],
            'sugestoes_distribuicao': [],
            'total_sugestoes': 0,
            'economia_total_estimada': 0,
            'erro': str(e)
        }

