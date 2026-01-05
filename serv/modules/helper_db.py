"""
Módulo de Funções Auxiliares que Requerem Acesso ao Banco de Dados
===================================================================

Este módulo contém funções auxiliares que precisam acessar o banco de dados
para realizar cálculos ou obter informações.

IMPORTANTE: Estas funções devem receber a conexão como parâmetro para
            permitir uso com connection pooling.
"""

import sqlite3
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def obter_duplex_da_impressora(conn: sqlite3.Connection, printer_name: str, duplex_evento: Optional[int] = None) -> int:
    """
    Obtém o valor duplex baseado no tipo da impressora cadastrada.
    Se a impressora não estiver cadastrada, usa o valor do evento como fallback.
    
    Args:
        conn: Conexão com banco de dados
        printer_name: Nome da impressora
        duplex_evento: Valor duplex do evento (fallback se impressora não cadastrada)
    
    Returns:
        1 se duplex, 0 se simplex, ou None se desconhecido
    """
    if not printer_name or printer_name == "Sem Nome":
        return duplex_evento if duplex_evento is not None else 0
    
    try:
        # Busca tipo da impressora cadastrada
        cursor = conn.execute(
            "SELECT tipo FROM printers WHERE printer_name = ?",
            (printer_name,)
        )
        tipo_row = cursor.fetchone()
        
        if tipo_row and tipo_row[0]:
            tipo_impressora = tipo_row[0].lower()
            # Converte tipo para duplex (1 = duplex, 0 = simplex)
            return 1 if tipo_impressora == 'duplex' else 0
        else:
            # Impressora não cadastrada, usa valor do evento como fallback
            return duplex_evento if duplex_evento is not None else 0
    except Exception as e:
        logger.debug(f"Erro ao buscar tipo da impressora '{printer_name}': {e}")
        return duplex_evento if duplex_evento is not None else 0


def custo_unitario_por_data(conn: sqlite3.Connection, data_evento: str, color_mode: Optional[str] = None, get_config_func=None) -> float:
    """
    Calcula o custo unitário por página somando os custos dos materiais vigentes na data.
    
    Args:
        conn: Conexão com banco de dados
        data_evento: Data do evento
        color_mode: 'Color' ou 'Black & White' (None para ambos)
        get_config_func: Função para obter configurações (opcional)
    
    Returns:
        Custo unitário por página
    """
    try:
        conn.row_factory = sqlite3.Row
        query = """
            SELECT preco, rendimento, nome FROM materiais
            WHERE date(data_inicio) <= date(?)
            ORDER BY data_inicio DESC
        """
        materiais = conn.execute(query, (data_evento,)).fetchall()
    except Exception as e:
        logger.error(f"Erro ao buscar materiais: {e}")
        return 0.0

    custo_total = 0.0
    
    # Obtém multiplicador de cor da configuração
    multiplicador_cor = 2.0  # Default
    if get_config_func:
        try:
            multiplicador_cor = float(get_config_func('color_multiplier', '2.0'))
        except (ValueError, TypeError):
            pass
    
    # Aplica multiplicador baseado no modo de cor
    if color_mode == 'Color':
        mult = multiplicador_cor
    elif color_mode == 'Black & White':
        mult = 1.0
    else:
        mult = 1.0
    
    for mat in materiais:
        if mat["rendimento"] and mat["rendimento"] > 0:
            custo_unitario = mat["preco"] / mat["rendimento"]
            # Aplica multiplicador se for material de cor (toner/ink)
            nome_mat = mat["nome"].lower() if mat["nome"] else ""
            if "color" in nome_mat or "cor" in nome_mat or "toner" in nome_mat:
                custo_unitario *= mult
            custo_total += custo_unitario
    
    return custo_total


def obter_tipo_impressora(conn: sqlite3.Connection, printer_name: str) -> Optional[str]:
    """
    Obtém o tipo de uma impressora cadastrada.
    
    Args:
        conn: Conexão com banco de dados
        printer_name: Nome da impressora
    
    Returns:
        Tipo da impressora ('duplex' ou 'simplex') ou None se não encontrada
    """
    if not printer_name or printer_name == "Sem Nome":
        return None
    
    try:
        cursor = conn.execute(
            "SELECT tipo FROM printers WHERE printer_name = ?",
            (printer_name,)
        )
        tipo_row = cursor.fetchone()
        
        if tipo_row and tipo_row[0]:
            return tipo_row[0].lower()
        return None
    except Exception as e:
        logger.debug(f"Erro ao buscar tipo da impressora '{printer_name}': {e}")
        return None

