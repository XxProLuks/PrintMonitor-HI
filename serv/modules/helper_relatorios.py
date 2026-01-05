"""
Funções auxiliares para relatórios - agrupamento por job
"""
import sqlite3
from typing import List, Tuple, Dict, Optional

# Usa módulo centralizado de cálculos
from modules.calculo_impressao import calcular_folhas_fisicas

def get_job_group_by_clause(has_job_id: bool) -> str:
    """Retorna cláusula GROUP BY para agrupar por job"""
    if has_job_id:
        return """CASE 
            WHEN job_id IS NOT NULL AND job_id != '' THEN 
                job_id || '|' || COALESCE(printer_name, '') || '|' || date
            ELSE 
                user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
        END"""
    else:
        return """user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date"""

def obter_dados_agrupados_por_job(
    conn: sqlite3.Connection,
    where_clause: str,
    params: tuple,
    group_by_field: str,
    has_job_id: bool = True
) -> List[Tuple]:
    """
    Obtém dados agrupados por job primeiro, depois por campo específico
    
    Args:
        conn: Conexão com banco
        where_clause: Cláusula WHERE
        params: Parâmetros da query
        group_by_field: Campo para agrupar (ex: 'user', 'printer_name', 'account')
        has_job_id: Se job_id existe na tabela
    
    Returns:
        Lista de tuplas: (campo, total_impressoes, total_paginas, ...)
    """
    job_group_by = get_job_group_by_clause(has_job_id)
    
    # Primeiro agrupa por job
    if has_job_id:
        rows = conn.execute(
            f"""SELECT 
                MAX({group_by_field}) as campo,
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex,
                MAX(COALESCE(copies, 1)) as copies
            FROM events
            {where_clause}
            GROUP BY {job_group_by}
            """, params
        ).fetchall()
    else:
        rows = conn.execute(
            f"""SELECT 
                MAX({group_by_field}) as campo,
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex,
                MAX(COALESCE(copies, 1)) as copies
            FROM events
            {where_clause}
            GROUP BY {job_group_by}
            """, params
        ).fetchall()
    
    # Agrupa por campo e calcula totais
    result_dict = {}
    for row in rows:
        campo = row[0]
        pages = row[1] or 0
        duplex = row[2] if len(row) > 2 else None
        copies = row[3] if len(row) > 3 else 1
        folhas = calcular_folhas_fisicas(pages, duplex, copies)
        
        if campo not in result_dict:
            result_dict[campo] = {"impressoes": 0, "paginas": 0}
        result_dict[campo]["impressoes"] += 1
        result_dict[campo]["paginas"] += folhas
    
    return [(campo, data["impressoes"], data["paginas"]) for campo, data in result_dict.items()]

