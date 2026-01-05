"""
Módulo Unificado de Relatórios e Dashboard
Centraliza e otimiza todas as consultas de relatórios
"""
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

# Usa módulo centralizado de cálculos
from modules.calculo_impressao import calcular_folhas_fisicas

logger = logging.getLogger(__name__)


def obter_estatisticas_gerais(conn: sqlite3.Connection, 
                              start_date: Optional[str] = None,
                              end_date: Optional[str] = None) -> Dict:
    """
    Obtém estatísticas gerais otimizadas
    
    Returns:
        Dict com todas as estatísticas principais
    """
    
    # Query base com filtros de data
    where_clause = "WHERE 1=1"
    params = []
    
    if start_date:
        where_clause += " AND date(date) >= date(?)"
        params.append(start_date)
    if end_date:
        where_clause += " AND date(date) <= date(?)"
        params.append(end_date)
    
    # Verifica se job_id existe na tabela
    existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(events)").fetchall()]
    has_job_id = 'job_id' in existing_columns
    
    # Total de impressões (jobs únicos, não eventos)
    if has_job_id:
        total_impressos = conn.execute(
            f"""SELECT COUNT(DISTINCT CASE 
                WHEN job_id IS NOT NULL AND job_id != '' THEN 
                    job_id || '|' || COALESCE(printer_name, '') || '|' || date
                ELSE 
                    user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
            END) FROM events {where_clause}""",
            params
        ).fetchone()[0]
    else:
        total_impressos = conn.execute(
            f"""SELECT COUNT(DISTINCT user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date) 
            FROM events {where_clause}""",
            params
        ).fetchone()[0]
    
    # Total de páginas (folhas físicas) - AGRUPA POR JOB PRIMEIRO
    # IMPORTANTE: Usa tipo da impressora cadastrada, não o campo duplex do evento
    if has_job_id:
        rows = conn.execute(
            f"""SELECT 
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex,
                MAX(COALESCE(copies, 1)) as copies,
                MAX(printer_name) as printer_name
            FROM events {where_clause}
            GROUP BY CASE 
                WHEN job_id IS NOT NULL AND job_id != '' THEN 
                    job_id || '|' || COALESCE(printer_name, '') || '|' || date
                ELSE 
                    user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
            END""",
            params
        ).fetchall()
    else:
        rows = conn.execute(
            f"""SELECT 
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex,
                MAX(COALESCE(copies, 1)) as copies,
                MAX(printer_name) as printer_name
            FROM events {where_clause}
            GROUP BY user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date""",
            params
        ).fetchall()
    
    # OTIMIZAÇÃO: Cache tipos de impressoras para evitar queries N+1
    printer_types_cache = {}
    printer_names_in_rows = {row[3] for row in rows if len(row) > 3 and row[3]}
    if printer_names_in_rows:
        printer_types = conn.execute(
            "SELECT printer_name, tipo FROM printers WHERE printer_name IN ({})".format(
                ','.join(['?'] * len(printer_names_in_rows))
            ),
            list(printer_names_in_rows)
        ).fetchall()
        printer_types_cache = {p[0]: p[1] for p in printer_types if p[0] and p[1]}
    
    total_paginas = 0
    for row in rows:
        pages = row[0] or 0
        duplex_evento = row[1] if len(row) > 1 else None
        copies = row[2] if len(row) > 2 else 1
        printer_name = row[3] if len(row) > 3 else None
        
        # Obtém duplex baseado no tipo da impressora cadastrada (usando cache)
        if printer_name and printer_name in printer_types_cache:
            tipo_impressora = printer_types_cache[printer_name].lower()
            duplex = 1 if tipo_impressora == 'duplex' else 0
        else:
            # Fallback para valor do evento
            duplex = duplex_evento if duplex_evento is not None else 0
        
        total_paginas += calcular_folhas_fisicas(pages, duplex, copies)
    
    # Total de usuários
    total_usuarios = conn.execute(
        f"SELECT COUNT(DISTINCT user) FROM events {where_clause}",
        params
    ).fetchone()[0]
    
    # Total de setores
    if start_date or end_date:
        total_setores = conn.execute(
            f"""SELECT COUNT(DISTINCT u.sector) 
                FROM events e
                LEFT JOIN users u ON e.user = u.user
                {where_clause.replace('WHERE', 'WHERE')}""",
            params
        ).fetchone()[0]
    else:
        total_setores = conn.execute(
            "SELECT COUNT(DISTINCT sector) FROM users WHERE sector IS NOT NULL"
        ).fetchone()[0]
    
    # Total de impressoras
    total_impressoras = conn.execute(
        f"""SELECT COUNT(DISTINCT printer_name) 
            FROM events 
            {where_clause} AND printer_name IS NOT NULL AND printer_name != ''""",
        params
    ).fetchone()[0]
    
    return {
        "total_impressos": total_impressos,
        "total_paginas": total_paginas,
        "total_usuarios": total_usuarios,
        "total_setores": total_setores,
        "total_impressoras": total_impressoras
    }


def obter_dados_setores(conn: sqlite3.Connection,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        limite: int = 10) -> List[Dict]:
    """Obtém dados de impressões por setor"""
    # Importa função de custo (não causa circular)
    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from modules.helper_db import custo_unitario_por_data
    except ImportError:
        def custo_unitario_por_data(data, color_mode):
            return 0.05  # Fallback
    
    where_clause = "WHERE 1=1"
    params = []
    
    if start_date:
        where_clause += " AND date(e.date) >= date(?)"
        params.append(start_date)
    if end_date:
        where_clause += " AND date(e.date) <= date(?)"
        params.append(end_date)
    
    # Verifica se job_id existe
    existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(events)").fetchall()]
    has_job_id = 'job_id' in existing_columns
    
    # OTIMIZAÇÃO: Prepara cache de tipos de impressoras (será preenchido após buscar rows)
    
    # Busca jobs únicos agrupados por job_id + impressora + data (evita duplicação)
    if has_job_id:
        rows = conn.execute(
            f"""SELECT 
                COALESCE(u.sector, 'Sem Setor') as sector,
                MAX(e.pages_printed) as pages,
                MAX(e.duplex) as duplex,
                MAX(COALESCE(e.copies, 1)) as copies,
                MAX(e.color_mode) as color_mode,
                MAX(e.date) as date,
                MAX(e.printer_name) as printer_name
            FROM events e
            LEFT JOIN users u ON e.user = u.user
            {where_clause}
            GROUP BY CASE 
                WHEN e.job_id IS NOT NULL AND e.job_id != '' THEN 
                    e.job_id || '|' || COALESCE(e.printer_name, '') || '|' || e.date
                ELSE 
                    e.user || '|' || e.machine || '|' || COALESCE(e.document, '') || '|' || COALESCE(e.printer_name, '') || '|' || e.date
            END, COALESCE(u.sector, 'Sem Setor')""",
            params
        ).fetchall()
    else:
        rows = conn.execute(
            f"""SELECT 
                COALESCE(u.sector, 'Sem Setor') as sector,
                MAX(e.pages_printed) as pages,
                MAX(e.duplex) as duplex,
                MAX(COALESCE(e.copies, 1)) as copies,
                MAX(e.color_mode) as color_mode,
                MAX(e.date) as date,
                MAX(e.printer_name) as printer_name
            FROM events e
            LEFT JOIN users u ON e.user = u.user
            {where_clause}
            GROUP BY e.user || '|' || e.machine || '|' || COALESCE(e.document, '') || '|' || COALESCE(e.printer_name, '') || '|' || e.date,
                     COALESCE(u.sector, 'Sem Setor')""",
            params
        ).fetchall()
    
    # OTIMIZAÇÃO: Cache tipos de impressoras para evitar queries N+1
    printer_types_cache = {}
    printer_names_in_rows = {row[6] for row in rows if len(row) > 6 and row[6]}
    if printer_names_in_rows:
        printer_types = conn.execute(
            "SELECT printer_name, tipo FROM printers WHERE printer_name IN ({})".format(
                ','.join(['?'] * len(printer_names_in_rows))
            ),
            list(printer_names_in_rows)
        ).fetchall()
        printer_types_cache = {p[0]: p[1] for p in printer_types if p[0] and p[1]}
    
    # Agrupa por setor
    setores_dict = {}
    for row in rows:
        sector = row[0]
        pages = row[1] or 0
        duplex_evento = row[2] if len(row) > 2 else None
        copies = row[3] if len(row) > 3 else 1
        color_mode = row[4] if len(row) > 4 else None
        date_str = row[5] if len(row) > 5 else None
        printer_name = row[6] if len(row) > 6 else None
        
        if sector not in setores_dict:
            setores_dict[sector] = {
                "total_impressos": 0,
                "total_paginas": 0,
                "paginas_color": 0,
                "paginas_bw": 0,
                "custo_total": 0.0
            }
        
        # Obtém duplex baseado no tipo da impressora cadastrada (usando cache)
        if printer_name and printer_name in printer_types_cache:
            tipo_impressora = printer_types_cache[printer_name].lower()
            duplex = 1 if tipo_impressora == 'duplex' else 0
        else:
            # Fallback para valor do evento
            duplex = duplex_evento if duplex_evento is not None else 0
        
        folhas_fisicas = calcular_folhas_fisicas(pages, duplex, copies)
        setores_dict[sector]["total_impressos"] += 1
        setores_dict[sector]["total_paginas"] += folhas_fisicas
        
        # Calcula custo
        if date_str:
            data_evento = date_str.split()[0] if " " in date_str else date_str
            # Importa get_config se necessário
            try:
                import sys
                import os
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from servidor import get_config
            except ImportError:
                def get_config(key, default):
                    return default
            
            if color_mode == 'Color':
                custo = custo_unitario_por_data(conn, data_evento, 'Color', get_config)
                setores_dict[sector]["paginas_color"] += folhas_fisicas
            elif color_mode == 'Black & White':
                custo = custo_unitario_por_data(conn, data_evento, 'Black & White', get_config)
                setores_dict[sector]["paginas_bw"] += folhas_fisicas
            else:
                custo = custo_unitario_por_data(conn, data_evento, None, get_config)
            
            setores_dict[sector]["custo_total"] += folhas_fisicas * custo
    
    # Converte para lista e ordena
    setores_list = [
        {
            "sector": k,
            "total_impressos": v["total_impressos"],
            "total_paginas": v["total_paginas"],
            "paginas_color": v["paginas_color"],
            "paginas_bw": v["paginas_bw"],
            "custo_total": round(v["custo_total"], 2)
        }
        for k, v in setores_dict.items()
    ]
    
    setores_list.sort(key=lambda x: x['total_impressos'], reverse=True)
    return setores_list[:limite]


def obter_dados_usuarios(conn: sqlite3.Connection,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        limite: int = 10) -> List[Dict]:
    """Obtém dados de impressões por usuário"""
    
    where_clause = "WHERE 1=1"
    params = []
    
    if start_date:
        where_clause += " AND date(date) >= date(?)"
        params.append(start_date)
    if end_date:
        where_clause += " AND date(date) <= date(?)"
        params.append(end_date)
    
    # Verifica se job_id existe
    existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(events)").fetchall()]
    has_job_id = 'job_id' in existing_columns
    
    # Busca jobs únicos agrupados por job_id + impressora + data
    if has_job_id:
        rows = conn.execute(
            f"""SELECT 
                user,
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex,
                MAX(COALESCE(copies, 1)) as copies,
                MAX(printer_name) as printer_name
            FROM events
            {where_clause}
            GROUP BY CASE 
                WHEN job_id IS NOT NULL AND job_id != '' THEN 
                    job_id || '|' || COALESCE(printer_name, '') || '|' || date
                ELSE 
                    user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
            END, user""",
            params
        ).fetchall()
    else:
        rows = conn.execute(
            f"""SELECT 
                user,
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex,
                MAX(COALESCE(copies, 1)) as copies,
                MAX(printer_name) as printer_name
            FROM events
            {where_clause}
            GROUP BY user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date,
                     user""",
            params
        ).fetchall()
    
    # OTIMIZAÇÃO: Cache tipos de impressoras para evitar queries N+1
    printer_types_cache = {}
    printer_names_in_rows = {row[4] for row in rows if len(row) > 4 and row[4]}
    if printer_names_in_rows:
        printer_types = conn.execute(
            "SELECT printer_name, tipo FROM printers WHERE printer_name IN ({})".format(
                ','.join(['?'] * len(printer_names_in_rows))
            ),
            list(printer_names_in_rows)
        ).fetchall()
        printer_types_cache = {p[0]: p[1] for p in printer_types if p[0] and p[1]}
    
    usuarios_dict = {}
    for row in rows:
        user = row[0]
        pages = row[1] or 0
        duplex_evento = row[2] if len(row) > 2 else None
        copies = row[3] if len(row) > 3 else 1
        printer_name = row[4] if len(row) > 4 else None
        
        if user not in usuarios_dict:
            usuarios_dict[user] = {
                "total_impressos": 0,
                "total_paginas": 0
            }
        
        # Obtém duplex baseado no tipo da impressora cadastrada (usando cache)
        if printer_name and printer_name in printer_types_cache:
            tipo_impressora = printer_types_cache[printer_name].lower()
            duplex = 1 if tipo_impressora == 'duplex' else 0
        else:
            # Fallback para valor do evento
            duplex = duplex_evento if duplex_evento is not None else 0
        
        usuarios_dict[user]["total_impressos"] += 1
        usuarios_dict[user]["total_paginas"] += calcular_folhas_fisicas(pages, duplex, copies)
    
    usuarios_list = [
        {
            "user": k,
            "total_impressos": v["total_impressos"],
            "total_paginas": v["total_paginas"]
        }
        for k, v in usuarios_dict.items()
    ]
    
    usuarios_list.sort(key=lambda x: x['total_impressos'], reverse=True)
    return usuarios_list[:limite]


def obter_dados_impressoras(conn: sqlite3.Connection,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None,
                           limite: int = 10) -> List[Dict]:
    """Obtém dados de impressões por impressora"""
    # Importa função de custo (não causa circular)
    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from modules.helper_db import custo_unitario_por_data
    except ImportError:
        def custo_unitario_por_data(data, color_mode):
            return 0.05  # Fallback
    
    where_clause = "WHERE printer_name IS NOT NULL AND printer_name != ''"
    params = []
    
    if start_date:
        where_clause += " AND date(date) >= date(?)"
        params.append(start_date)
    if end_date:
        where_clause += " AND date(date) <= date(?)"
        params.append(end_date)
    
    # Verifica se job_id existe
    existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(events)").fetchall()]
    has_job_id = 'job_id' in existing_columns
    
    # Busca jobs únicos agrupados por job_id + impressora + data
    if has_job_id:
        rows = conn.execute(
            f"""SELECT 
                printer_name,
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex,
                MAX(COALESCE(copies, 1)) as copies,
                MAX(color_mode) as color_mode,
                MAX(date) as date
            FROM events
            {where_clause}
            GROUP BY CASE 
                WHEN job_id IS NOT NULL AND job_id != '' THEN 
                    job_id || '|' || COALESCE(printer_name, '') || '|' || date
                ELSE 
                    user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
            END, printer_name""",
            params
        ).fetchall()
    else:
        rows = conn.execute(
            f"""SELECT 
                printer_name,
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex,
                MAX(COALESCE(copies, 1)) as copies,
                MAX(color_mode) as color_mode,
                MAX(date) as date
            FROM events
            {where_clause}
            GROUP BY user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date,
                     printer_name""",
            params
        ).fetchall()
    
    impressoras_dict = {}
    for row in rows:
        printer_name = row[0]
        pages = row[1] or 0
        duplex = row[2] if len(row) > 2 else None
        copies = row[3] if len(row) > 3 else 1
        color_mode = row[4] if len(row) > 4 else None
        date_str = row[5] if len(row) > 5 else None
        
        if printer_name not in impressoras_dict:
            impressoras_dict[printer_name] = {
                "total_impressos": 0,
                "total_paginas": 0,
                "paginas_color": 0,
                "paginas_bw": 0,
                "impressoes_duplex": 0,
                "impressoes_simplex": 0,
                "custo_total": 0.0
            }
        
        folhas_fisicas = calcular_folhas_fisicas(pages, duplex, copies)
        impressoras_dict[printer_name]["total_impressos"] += 1
        impressoras_dict[printer_name]["total_paginas"] += folhas_fisicas
        
        if color_mode == 'Color':
            impressoras_dict[printer_name]["paginas_color"] += folhas_fisicas
        elif color_mode == 'Black & White':
            impressoras_dict[printer_name]["paginas_bw"] += folhas_fisicas
        
        if duplex == 1:
            impressoras_dict[printer_name]["impressoes_duplex"] += 1
        elif duplex == 0:
            impressoras_dict[printer_name]["impressoes_simplex"] += 1
        
        # Calcula custo
        if date_str:
            data_evento = date_str.split()[0] if " " in date_str else date_str
            if color_mode == 'Color':
                custo = custo_unitario_por_data(data_evento, 'Color')
            elif color_mode == 'Black & White':
                custo = custo_unitario_por_data(data_evento, 'Black & White')
            else:
                custo = custo_unitario_por_data(data_evento, None)
            impressoras_dict[printer_name]["custo_total"] += folhas_fisicas * custo
    
    impressoras_list = [
        {
            "printer_name": k,
            **v,
            "custo_total": round(v["custo_total"], 2)
        }
        for k, v in impressoras_dict.items()
    ]
    
    impressoras_list.sort(key=lambda x: x['total_impressos'], reverse=True)
    return impressoras_list[:limite]


def obter_tendencia_dias(conn: sqlite3.Connection,
                        dias: int = 7,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> Tuple[List[str], List[int]]:
    """Obtém tendência de impressões por dia"""
    where_clause = ""
    params = []
    
    if start_date and end_date:
        where_clause = f"WHERE date(date) >= date(?) AND date(date) <= date(?)"
        params = [start_date, end_date]
    elif start_date:
        where_clause = f"WHERE date(date) >= date(?)"
        params = [start_date]
    elif end_date:
        where_clause = f"WHERE date(date) <= date(?)"
        params = [end_date]
    else:
        where_clause = f"WHERE date(date) >= date('now', '-{dias} days')"
    
    # Verifica se job_id existe
    existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(events)").fetchall()]
    has_job_id = 'job_id' in existing_columns
    
    # Conta jobs únicos por dia, não eventos
    if has_job_id:
        rows = conn.execute(
            f"""SELECT 
                date(date) as dia,
                COUNT(DISTINCT CASE 
                    WHEN job_id IS NOT NULL AND job_id != '' THEN 
                        job_id || '|' || COALESCE(printer_name, '') || '|' || date
                    ELSE 
                        user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
                END) as total
            FROM events
            {where_clause}
            GROUP BY dia
            ORDER BY dia""",
            params
        ).fetchall()
    else:
        rows = conn.execute(
            f"""SELECT 
                date(date) as dia,
                COUNT(DISTINCT user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date) as total
            FROM events
            {where_clause}
            GROUP BY dia
            ORDER BY dia""",
            params
        ).fetchall()
    
    dias_labels = [row[0] for row in rows]
    dias_values = [row[1] for row in rows]
    
    return dias_labels, dias_values


def obter_dados_cor(conn: sqlite3.Connection,
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None) -> List[Dict]:
    """Obtém dados de impressões por modo de cor"""
    
    where_clause = "WHERE color_mode IS NOT NULL AND color_mode != ''"
    params = []
    
    if start_date:
        where_clause += " AND date(date) >= date(?)"
        params.append(start_date)
    if end_date:
        where_clause += " AND date(date) <= date(?)"
        params.append(end_date)
    
    # Verifica se job_id existe
    existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(events)").fetchall()]
    has_job_id = 'job_id' in existing_columns
    
    # Busca jobs únicos agrupados por job_id + impressora + data
    if has_job_id:
        rows = conn.execute(
            f"""SELECT 
                MAX(color_mode) as color_mode,
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex,
                MAX(COALESCE(copies, 1)) as copies
            FROM events
            {where_clause}
            GROUP BY CASE 
                WHEN job_id IS NOT NULL AND job_id != '' THEN 
                    job_id || '|' || COALESCE(printer_name, '') || '|' || date
                ELSE 
                    user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
            END""",
            params
        ).fetchall()
    else:
        rows = conn.execute(
            f"""SELECT 
                MAX(color_mode) as color_mode,
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex,
                MAX(COALESCE(copies, 1)) as copies
            FROM events
            {where_clause}
            GROUP BY user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date""",
            params
        ).fetchall()
    
    color_dict = {}
    for row in rows:
        color_mode = row[0]
        pages = row[1] or 0
        duplex = row[2] if len(row) > 2 else None
        copies = row[3] if len(row) > 3 else 1
        
        # Ignora se color_mode for NULL
        if not color_mode:
            continue
        
        if color_mode not in color_dict:
            color_dict[color_mode] = {"total_impressos": 0, "total_paginas": 0}
        
        color_dict[color_mode]["total_impressos"] += 1
        color_dict[color_mode]["total_paginas"] += calcular_folhas_fisicas(pages, duplex, copies)
    
    return [
        {"color_mode": k, "total_impressos": v["total_impressos"], "total_paginas": v["total_paginas"]}
        for k, v in color_dict.items()
    ]


def obter_dados_papel(conn: sqlite3.Connection,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None) -> List[Dict]:
    """Obtém dados de impressões por tamanho de papel"""
    
    where_clause = "WHERE paper_size IS NOT NULL AND paper_size != ''"
    params = []
    
    if start_date:
        where_clause += " AND date(date) >= date(?)"
        params.append(start_date)
    if end_date:
        where_clause += " AND date(date) <= date(?)"
        params.append(end_date)
    
    # Verifica se job_id existe
    existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(events)").fetchall()]
    has_job_id = 'job_id' in existing_columns
    
    # Busca jobs únicos agrupados por job_id + impressora + data
    if has_job_id:
        rows = conn.execute(
            f"""SELECT 
                MAX(paper_size) as paper_size,
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex,
                MAX(COALESCE(copies, 1)) as copies
            FROM events
            {where_clause}
            GROUP BY CASE 
                WHEN job_id IS NOT NULL AND job_id != '' THEN 
                    job_id || '|' || COALESCE(printer_name, '') || '|' || date
                ELSE 
                    user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
            END""",
            params
        ).fetchall()
    else:
        rows = conn.execute(
            f"""SELECT 
                MAX(paper_size) as paper_size,
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex,
                MAX(COALESCE(copies, 1)) as copies
            FROM events
            {where_clause}
            GROUP BY user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date""",
            params
        ).fetchall()
    
    papel_dict = {}
    for row in rows:
        paper_size = row[0]
        pages = row[1] or 0
        duplex = row[2] if len(row) > 2 else None
        copies = row[3] if len(row) > 3 else 1
        
        # Ignora se paper_size for NULL
        if not paper_size:
            continue
        
        if paper_size not in papel_dict:
            papel_dict[paper_size] = {"total_impressos": 0, "total_paginas": 0}
        
        papel_dict[paper_size]["total_impressos"] += 1
        papel_dict[paper_size]["total_paginas"] += calcular_folhas_fisicas(pages, duplex, copies)
    
    return [
        {"paper_size": k, "total_impressos": v["total_impressos"], "total_paginas": v["total_paginas"]}
        for k, v in sorted(papel_dict.items(), key=lambda x: x[1]["total_paginas"], reverse=True)
    ]


def obter_dados_duplex(conn: sqlite3.Connection,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> Dict:
    """Obtém dados de impressões duplex vs simplex"""
    
    where_clause = "WHERE 1=1"
    params = []
    
    if start_date:
        where_clause += " AND date(date) >= date(?)"
        params.append(start_date)
    if end_date:
        where_clause += " AND date(date) <= date(?)"
        params.append(end_date)
    
    # Verifica se job_id existe
    existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(events)").fetchall()]
    has_job_id = 'job_id' in existing_columns
    
    # Busca jobs únicos agrupados por job_id + impressora + data
    if has_job_id:
        rows = conn.execute(
            f"""SELECT 
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex,
                MAX(COALESCE(copies, 1)) as copies
            FROM events
            {where_clause}
            GROUP BY CASE 
                WHEN job_id IS NOT NULL AND job_id != '' THEN 
                    job_id || '|' || COALESCE(printer_name, '') || '|' || date
                ELSE 
                    user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
            END""",
            params
        ).fetchall()
    else:
        rows = conn.execute(
            f"""SELECT 
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex,
                MAX(COALESCE(copies, 1)) as copies
            FROM events
            {where_clause}
            GROUP BY user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date""",
            params
        ).fetchall()
    
    duplex_count = 0
    simplex_count = 0
    duplex_pages = 0
    simplex_pages = 0
    
    for row in rows:
        pages = row[0] or 0
        duplex = row[1] if len(row) > 1 else None
        copies = row[2] if len(row) > 2 else 1
        folhas_fisicas = calcular_folhas_fisicas(pages, duplex, copies)
        
        if duplex == 1:
            duplex_count += 1
            duplex_pages += folhas_fisicas
        else:
            simplex_count += 1
            simplex_pages += folhas_fisicas
    
    return {
        "duplex": {
            "impressoes": duplex_count,
            "paginas": duplex_pages
        },
        "simplex": {
            "impressoes": simplex_count,
            "paginas": simplex_pages
        }
    }


def obter_relatorio_completo(conn: sqlite3.Connection,
                             start_date: Optional[str] = None,
                             end_date: Optional[str] = None,
                             usar_cache: bool = True) -> Dict:
    """
    Obtém relatório completo unificado e otimizado
    
    Returns:
        Dict com todos os dados do relatório
    """
    # Tenta usar cache se disponível
    if usar_cache:
        try:
            from modules.cache import obter_cache, definir_cache
            
            cache_key = f"relatorio_{start_date}_{end_date}"
            cached = obter_cache(conn, cache_key)
            if cached:
                return cached
        except:
            pass
    
    # Obtém todos os dados
    stats = obter_estatisticas_gerais(conn, start_date, end_date)
    setores = obter_dados_setores(conn, start_date, end_date, limite=20)
    usuarios = obter_dados_usuarios(conn, start_date, end_date, limite=20)
    impressoras = obter_dados_impressoras(conn, start_date, end_date, limite=20)
    dias_labels, dias_values = obter_tendencia_dias(conn, dias=30, start_date=start_date, end_date=end_date)
    cor_data = obter_dados_cor(conn, start_date, end_date)
    papel_data = obter_dados_papel(conn, start_date, end_date)
    duplex_data = obter_dados_duplex(conn, start_date, end_date)
    
    relatorio = {
        "stats": stats,
        "setores": setores,
        "usuarios": usuarios,
        "impressoras": impressoras,
        "tendencia": {
            "labels": dias_labels,
            "values": dias_values
        },
        "cor": cor_data,
        "papel": papel_data,
        "duplex": duplex_data,
        "periodo": {
            "start_date": start_date,
            "end_date": end_date
        }
    }
    
    # Salva no cache
    if usar_cache:
        try:
            from modules.cache import definir_cache
            definir_cache(conn, cache_key, relatorio, minutos_expiracao=5)
        except:
            pass
    
    return relatorio

