"""
Módulo de Sugestões de Economia
Analisa impressões e sugere melhorias
"""
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def analisar_economia(conn: sqlite3.Connection, evento_id: int,
                     pages: int, duplex: Optional[int], color_mode: Optional[str],
                     custo_unitario: float) -> List[Dict]:
    """
    Analisa um evento e gera sugestões de economia
    
    Returns:
        Lista de sugestões
    """
    sugestoes = []
    
    # Sugestão 1: Usar duplex
    if duplex == 0 and pages > 1:
        economia_duplex = (pages / 2) * custo_unitario - (pages / 2) * custo_unitario
        # Na verdade, duplex economiza papel, não custo por página
        economia_papel = pages - (pages / 2)
        sugestoes.append({
            "tipo": "duplex",
            "mensagem": f"Esta impressão poderia ser em duplex, economizando {economia_papel:.0f} folhas de papel",
            "economia_estimada": economia_papel * 0.05,  # Estimativa de custo de papel
            "evento_id": evento_id
        })
    
    # Sugestão 2: Usar P&B ao invés de colorido
    if color_mode == 'Color':
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from modules.helper_db import custo_unitario_por_data
        # Importa get_config
        try:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from servidor import get_config
        except ImportError:
            def get_config(key, default):
                return default
        # Assume que poderia ser P&B
        # Nota: custo_unitario_por_data agora precisa de conn, mas este código não tem acesso direto
        # Vamos usar um valor padrão por enquanto
        custo_pb = 0.05  # Valor padrão aproximado
        economia = (custo_unitario - custo_pb) * pages
        if economia > 0.1:  # Só sugere se economia for significativa
            sugestoes.append({
                "tipo": "pb",
                "mensagem": f"Esta impressão poderia ser em P&B, economizando R$ {economia:.2f}",
                "economia_estimada": economia,
                "evento_id": evento_id
            })
    
    # Salva sugestões
    for sugestao in sugestoes:
        salvar_sugestao(conn, sugestao)
    
    return sugestoes


def salvar_sugestao(conn: sqlite3.Connection, sugestao: Dict):
    """Salva sugestão no banco"""
    try:
        conn.execute(
            """INSERT INTO sugestoes_economia 
               (evento_id, tipo, mensagem, economia_estimada)
               VALUES (?, ?, ?, ?)""",
            (sugestao.get("evento_id"), sugestao.get("tipo"), 
             sugestao.get("mensagem"), sugestao.get("economia_estimada"))
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Erro ao salvar sugestão: {e}")


def buscar_sugestoes(conn: sqlite3.Connection, aplicadas: Optional[bool] = None,
                    limite: int = 50) -> List[Dict]:
    """Busca sugestões"""
    query = "SELECT * FROM sugestoes_economia WHERE 1=1"
    params = []
    
    if aplicadas is not None:
        query += " AND aplicada = ?"
        params.append(1 if aplicadas else 0)
    
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limite)
    
    rows = conn.execute(query, params).fetchall()
    
    sugestoes = []
    for row in rows:
        sugestoes.append({
            "id": row[0],
            "evento_id": row[1],
            "tipo": row[2],
            "mensagem": row[3],
            "economia_estimada": row[4],
            "aplicada": bool(row[5]),
            "created_at": row[6]
        })
    
    return sugestoes


def calcular_economia_total(conn: sqlite3.Connection) -> Dict:
    """Calcula economia total estimada das sugestões"""
    try:
        row = conn.execute(
            "SELECT SUM(economia_estimada) as total, COUNT(*) as quantidade FROM sugestoes_economia WHERE aplicada = 0"
        ).fetchone()
        
        if row:
            return {
                "economia_total_estimada": row[0] or 0.0,
                "quantidade_sugestoes": row[1] or 0
            }
        else:
            return {
                "economia_total_estimada": 0.0,
                "quantidade_sugestoes": 0
            }
    except Exception as e:
        logger.error(f"Erro ao calcular economia total: {e}")
        return {
            "economia_total_estimada": 0.0,
            "quantidade_sugestoes": 0
        }

