"""
Módulo de Quotas e Limites
Gerencia quotas por usuário, setor, etc.
"""
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def verificar_quota(conn: sqlite3.Connection, tipo: str, referencia: str, 
                   periodo: str = "mensal") -> Dict:
    """
    Verifica se quota foi excedida
    
    Args:
        conn: Conexão com o banco
        tipo: 'user', 'setor', 'impressora'
        referencia: Nome do usuário, setor ou impressora
        periodo: 'mensal', 'trimestral', 'anual'
    
    Returns:
        Dict com status da quota
    """
    # Busca quota configurada
    quota = buscar_quota(conn, tipo, referencia)
    
    if not quota:
        return {
            "tem_quota": False,
            "excedida": False,
            "uso_atual": 0,
            "limite": None,
            "percentual_usado": 0
        }
    
    # Calcula uso atual
    hoje = datetime.now()
    if periodo == "mensal":
        inicio = hoje.replace(day=1).strftime("%Y-%m-%d")
        fim = hoje.strftime("%Y-%m-%d")
        limite = quota.get("limite_mensal")
    elif periodo == "trimestral":
        trimestre = (hoje.month - 1) // 3 + 1
        mes_inicio = (trimestre - 1) * 3 + 1
        inicio = hoje.replace(month=mes_inicio, day=1).strftime("%Y-%m-%d")
        fim = hoje.strftime("%Y-%m-%d")
        limite = quota.get("limite_trimestral")
    else:  # anual
        inicio = hoje.replace(month=1, day=1).strftime("%Y-%m-%d")
        fim = hoje.strftime("%Y-%m-%d")
        limite = quota.get("limite_anual")
    
    if not limite:
        return {
            "tem_quota": True,
            "excedida": False,
            "uso_atual": 0,
            "limite": None,
            "percentual_usado": 0
        }
    
    # Calcula uso
    uso_atual = calcular_uso_periodo(conn, tipo, referencia, inicio, fim)
    percentual_usado = (uso_atual / limite) * 100 if limite > 0 else 0
    
    return {
        "tem_quota": True,
        "excedida": uso_atual >= limite,
        "uso_atual": uso_atual,
        "limite": limite,
        "percentual_usado": round(percentual_usado, 2),
        "restante": max(0, limite - uso_atual)
    }


def buscar_quota(conn: sqlite3.Connection, tipo: str, referencia: str) -> Optional[Dict]:
    """Busca quota configurada"""
    row = conn.execute(
        "SELECT * FROM quotas WHERE tipo = ? AND referencia = ? AND ativo = 1",
        (tipo, referencia)
    ).fetchone()
    
    if not row:
        return None
    
    return {
        "id": row[0],
        "tipo": row[1],
        "referencia": row[2],
        "limite_mensal": row[3],
        "limite_trimestral": row[4],
        "limite_anual": row[5],
        "periodo_inicio": row[6],
        "periodo_fim": row[7],
        "ativo": row[8]
    }


def calcular_uso_periodo(conn: sqlite3.Connection, tipo: str, referencia: str,
                        inicio: str, fim: str) -> int:
    """Calcula uso (páginas) em um período"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from modules.calculo_impressao import calcular_folhas_fisicas
    
    query = "SELECT pages_printed, duplex FROM events WHERE date(date) >= date(?) AND date(date) <= date(?)"
    params = [inicio, fim]
    
    if tipo == "user":
        query += " AND user = ?"
        params.append(referencia)
    elif tipo == "setor":
        query += " AND user IN (SELECT user FROM users WHERE sector = ?)"
        params.append(referencia)
    elif tipo == "impressora":
        query += " AND printer_name = ?"
        params.append(referencia)
    
    rows = conn.execute(query, params).fetchall()
    
    total_paginas = 0
    for row in rows:
        pages = row[0] or 0
        duplex = row[1] if len(row) > 1 else None
        total_paginas += calcular_folhas_fisicas(pages, duplex)
    
    return total_paginas


def criar_quota(conn: sqlite3.Connection, tipo: str, referencia: str,
               limite_mensal: Optional[int] = None,
               limite_trimestral: Optional[int] = None,
               limite_anual: Optional[int] = None) -> bool:
    """Cria ou atualiza uma quota"""
    try:
        conn.execute(
            """INSERT OR REPLACE INTO quotas 
               (tipo, referencia, limite_mensal, limite_trimestral, limite_anual, ativo)
               VALUES (?, ?, ?, ?, ?, 1)""",
            (tipo, referencia, limite_mensal, limite_trimestral, limite_anual)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro ao criar quota: {e}")
        return False


def listar_quotas(conn: sqlite3.Connection, tipo: Optional[str] = None) -> List[Dict]:
    """Lista todas as quotas"""
    if tipo:
        rows = conn.execute(
            "SELECT * FROM quotas WHERE tipo = ? AND ativo = 1 ORDER BY referencia",
            (tipo,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM quotas WHERE ativo = 1 ORDER BY tipo, referencia"
        ).fetchall()
    
    quotas = []
    for row in rows:
        quotas.append({
            "id": row[0],
            "tipo": row[1],
            "referencia": row[2],
            "limite_mensal": row[3],
            "limite_trimestral": row[4],
            "limite_anual": row[5],
            "periodo_inicio": row[6],
            "periodo_fim": row[7],
            "ativo": row[8]
        })
    
    return quotas

