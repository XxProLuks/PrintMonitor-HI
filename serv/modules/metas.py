"""
Módulo de Metas
Gerencia metas de páginas e custos
"""
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def criar_meta(conn: sqlite3.Connection, tipo: str, referencia: str,
              meta_paginas: Optional[int] = None,
              meta_custo: Optional[float] = None,
              periodo: str = "mensal", ano: Optional[int] = None,
              mes: Optional[int] = None) -> bool:
    """Cria uma meta"""
    try:
        if not ano:
            ano = datetime.now().year
        if not mes and periodo == "mensal":
            mes = datetime.now().month
        
        conn.execute(
            """INSERT INTO metas 
               (tipo, referencia, meta_paginas, meta_custo, periodo, ano, mes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (tipo, referencia, meta_paginas, meta_custo, periodo, ano, mes)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro ao criar meta: {e}")
        return False


def verificar_meta(conn: sqlite3.Connection, tipo: str, referencia: str,
                  periodo: str = "mensal") -> Dict:
    """Verifica status de uma meta"""
    hoje = datetime.now()
    ano = hoje.year
    mes = hoje.month
    
    # Busca meta
    if periodo == "mensal":
        row = conn.execute(
            """SELECT * FROM metas 
               WHERE tipo = ? AND referencia = ? AND periodo = ? AND ano = ? AND mes = ?
               ORDER BY created_at DESC LIMIT 1""",
            (tipo, referencia, periodo, ano, mes)
        ).fetchone()
    else:
        row = conn.execute(
            """SELECT * FROM metas 
               WHERE tipo = ? AND referencia = ? AND periodo = ? AND ano = ?
               ORDER BY created_at DESC LIMIT 1""",
            (tipo, referencia, periodo, ano)
        ).fetchone()
    
    if not row:
        return {
            "tem_meta": False,
            "atingida": False,
            "progresso_paginas": 0,
            "progresso_custo": 0
        }
    
    meta_paginas = row[3]
    meta_custo = row[4]
    
    # Calcula uso atual
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from modules.calculo_impressao import calcular_folhas_fisicas
    from modules.helper_db import custo_unitario_por_data
    
    if periodo == "mensal":
        inicio = hoje.replace(day=1).strftime("%Y-%m-%d")
        fim = hoje.strftime("%Y-%m-%d")
    elif periodo == "trimestral":
        trimestre = (hoje.month - 1) // 3 + 1
        mes_inicio = (trimestre - 1) * 3 + 1
        inicio = hoje.replace(month=mes_inicio, day=1).strftime("%Y-%m-%d")
        fim = hoje.strftime("%Y-%m-%d")
    else:  # anual
        inicio = hoje.replace(month=1, day=1).strftime("%Y-%m-%d")
        fim = hoje.strftime("%Y-%m-%d")
    
    # Calcula uso de páginas diretamente
    query_uso = "SELECT pages_printed, duplex FROM events WHERE date(date) >= date(?) AND date(date) <= date(?)"
    params_uso = [inicio, fim]
    
    if tipo == "user":
        query_uso += " AND user = ?"
        params_uso.append(referencia)
    elif tipo == "setor":
        query_uso += " AND user IN (SELECT user FROM users WHERE sector = ?)"
        params_uso.append(referencia)
    
    rows_uso = conn.execute(query_uso, params_uso).fetchall()
    uso_paginas = 0
    for row in rows_uso:
        pages = row[0] or 0
        duplex = row[1] if len(row) > 1 else None
        uso_paginas += calcular_folhas_fisicas(pages, duplex)
    
    # Calcula custo atual
    query = """SELECT pages_printed, duplex, color_mode, date 
               FROM events 
               WHERE date(date) >= date(?) AND date(date) <= date(?)"""
    params = [inicio, fim]
    
    if tipo == "user":
        query += " AND user = ?"
        params.append(referencia)
    elif tipo == "setor":
        query += " AND user IN (SELECT user FROM users WHERE sector = ?)"
        params.append(referencia)
    
    rows = conn.execute(query, params).fetchall()
    uso_custo = 0.0
    
    for row in rows:
        pages = row[0] or 0
        duplex = row[1] if len(row) > 1 else None
        color_mode = row[2] if len(row) > 2 else None
        date_str = row[3] if len(row) > 3 else None
        
        folhas = calcular_folhas_fisicas(pages, duplex)
        if date_str:
            data_evento = date_str.split()[0] if " " in date_str else date_str
            if color_mode == 'Color':
                custo = custo_unitario_por_data(data_evento, 'Color')
            elif color_mode == 'Black & White':
                custo = custo_unitario_por_data(data_evento, 'Black & White')
            else:
                custo = custo_unitario_por_data(data_evento, None)
            uso_custo += folhas * custo
    
    progresso_paginas = (uso_paginas / meta_paginas * 100) if meta_paginas and meta_paginas > 0 else 0
    progresso_custo = (uso_custo / meta_custo * 100) if meta_custo and meta_custo > 0 else 0
    
    return {
        "tem_meta": True,
        "meta_paginas": meta_paginas,
        "meta_custo": meta_custo,
        "uso_paginas": uso_paginas,
        "uso_custo": round(uso_custo, 2),
        "progresso_paginas": round(progresso_paginas, 2),
        "progresso_custo": round(progresso_custo, 2),
        "atingida_paginas": uso_paginas >= meta_paginas if meta_paginas else False,
        "atingida_custo": uso_custo >= meta_custo if meta_custo else False,
        "atingida": (uso_paginas >= meta_paginas if meta_paginas else True) and \
                   (uso_custo >= meta_custo if meta_custo else True)
    }


def listar_metas(conn: sqlite3.Connection, tipo: Optional[str] = None) -> List[Dict]:
    """Lista todas as metas"""
    try:
        if tipo:
            rows = conn.execute(
                "SELECT * FROM metas WHERE tipo = ? ORDER BY ano DESC, mes DESC",
                (tipo,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM metas ORDER BY tipo, ano DESC, mes DESC"
            ).fetchall()
        
        metas = []
        if rows:
            for row in rows:
                if row and len(row) >= 9:
                    metas.append({
                        "id": row[0],
                        "tipo": row[1],
                        "referencia": row[2],
                        "meta_paginas": row[3],
                        "meta_custo": row[4],
                        "periodo": row[5],
                        "ano": row[6],
                        "mes": row[7],
                        "created_at": row[8]
                    })
        
        return metas
    except Exception as e:
        logger.error(f"Erro ao listar metas: {e}")
        return []

