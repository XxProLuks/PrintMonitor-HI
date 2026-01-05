"""
Módulo de Análise de Padrões
Identifica padrões de uso, horários de pico, anomalias
"""
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


def analisar_horarios_pico(conn: sqlite3.Connection, dias: int = 30) -> Dict:
    """Analisa horários de pico de impressão"""
    inicio = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
    
    rows = conn.execute(
        """SELECT date, pages_printed, duplex 
           FROM events 
           WHERE date(date) >= date(?)
           ORDER BY date""",
        (inicio,)
    ).fetchall()
    
    # Agrupa por hora
    por_hora = defaultdict(lambda: {"total": 0, "quantidade": 0})
    
    from modules.calculo_impressao import calcular_folhas_fisicas
    
    for row in rows:
        date_str = row[0]
        pages = row[1] or 0
        duplex = row[2] if len(row) > 2 else None
        
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            hora = dt.hour
            folhas = calcular_folhas_fisicas(pages, duplex)
            por_hora[hora]["total"] += folhas
            por_hora[hora]["quantidade"] += 1
        except:
            pass
    
    # Encontra picos
    horas_ordenadas = sorted(por_hora.items(), key=lambda x: x[1]["total"], reverse=True)
    
    return {
        "por_hora": {h: d for h, d in por_hora.items()},
        "horarios_pico": [h for h, d in horas_ordenadas[:5]],
        "horarios_baixo": [h for h, d in horas_ordenadas[-5:]]
    }


def analisar_dias_semana(conn: sqlite3.Connection, dias: int = 30) -> Dict:
    """Analisa padrão de uso por dia da semana"""
    inicio = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
    
    rows = conn.execute(
        """SELECT date, pages_printed, duplex 
           FROM events 
           WHERE date(date) >= date(?)
           ORDER BY date""",
        (inicio,)
    ).fetchall()
    
    # Agrupa por dia da semana (0=segunda, 6=domingo)
    por_dia = defaultdict(lambda: {"total": 0, "quantidade": 0})
    
    from modules.calculo_impressao import calcular_folhas_fisicas
    
    dias_nomes = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    
    for row in rows:
        date_str = row[0]
        pages = row[1] or 0
        duplex = row[2] if len(row) > 2 else None
        
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            dia_semana = dt.weekday()
            folhas = calcular_folhas_fisicas(pages, duplex)
            por_dia[dia_semana]["total"] += folhas
            por_dia[dia_semana]["quantidade"] += 1
        except:
            pass
    
    return {
        "por_dia": {dias_nomes[d]: d["total"] for d, d in por_dia.items()},
        "dia_mais_usado": dias_nomes[max(por_dia.items(), key=lambda x: x[1]["total"])[0]] if por_dia else None,
        "dia_menos_usado": dias_nomes[min(por_dia.items(), key=lambda x: x[1]["total"])[0]] if por_dia else None
    }


def detectar_anomalias(conn: sqlite3.Connection, referencia: Optional[str] = None,
                       tipo: str = "user") -> List[Dict]:
    """Detecta impressões anômalas (fora do padrão)"""
    # Calcula média e desvio padrão
    inicio = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    query = """SELECT pages_printed, duplex, date 
               FROM events 
               WHERE date(date) >= date(?)"""
    params = [inicio]
    
    if referencia:
        if tipo == "user":
            query += " AND user = ?"
            params.append(referencia)
        elif tipo == "setor":
            query += " AND user IN (SELECT user FROM users WHERE sector = ?)"
            params.append(referencia)
    
    rows = conn.execute(query, params).fetchall()
    
    from modules.calculo_impressao import calcular_folhas_fisicas
    
    valores = []
    for row in rows:
        pages = row[0] or 0
        duplex = row[1] if len(row) > 1 else None
        valores.append(calcular_folhas_fisicas(pages, duplex))
    
    if len(valores) < 2:
        return []
    
    media = statistics.mean(valores)
    desvio = statistics.stdev(valores) if len(valores) > 1 else 0
    
    # Identifica anomalias (mais de 2 desvios padrão)
    limite_superior = media + (2 * desvio)
    anomalias = []
    
    for idx, row in enumerate(rows):
        pages = row[0] or 0
        duplex = row[1] if len(row) > 1 else None
        date_str = row[2] if len(row) > 2 else None
        valor = calcular_folhas_fisicas(pages, duplex)
        
        if valor > limite_superior:
            anomalias.append({
                "data": date_str,
                "valor": valor,
                "media": round(media, 2),
                "desvio": round(desvio, 2),
                "tipo": "alto"
            })
    
    return anomalias


def analisar_tendencia(conn: sqlite3.Connection, referencia: Optional[str] = None,
                      tipo: str = "user", dias: int = 30) -> Dict:
    """Analisa tendência de uso"""
    inicio = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
    
    query = """SELECT date(date) as dia, pages_printed, duplex 
               FROM events 
               WHERE date(date) >= date(?)"""
    params = [inicio]
    
    if referencia:
        if tipo == "user":
            query += " AND user = ?"
            params.append(referencia)
        elif tipo == "setor":
            query += " AND user IN (SELECT user FROM users WHERE sector = ?)"
            params.append(referencia)
    
    query += " GROUP BY dia ORDER BY dia"
    
    rows = conn.execute(query, params).fetchall()
    
    from modules.calculo_impressao import calcular_folhas_fisicas
    
    valores_diarios = []
    for row in rows:
        pages = row[1] or 0
        duplex = row[2] if len(row) > 2 else None
        valores_diarios.append(calcular_folhas_fisicas(pages, duplex))
    
    if len(valores_diarios) < 2:
        return {"tendencia": "insuficiente", "variacao": 0}
    
    # Calcula tendência simples (primeira metade vs segunda metade)
    meio = len(valores_diarios) // 2
    primeira_metade = statistics.mean(valores_diarios[:meio])
    segunda_metade = statistics.mean(valores_diarios[meio:])
    
    variacao = ((segunda_metade - primeira_metade) / primeira_metade * 100) if primeira_metade > 0 else 0
    
    if variacao > 10:
        tendencia = "crescimento"
    elif variacao < -10:
        tendencia = "declinio"
    else:
        tendencia = "estavel"
    
    return {
        "tendencia": tendencia,
        "variacao": round(variacao, 2),
        "primeira_metade": round(primeira_metade, 2),
        "segunda_metade": round(segunda_metade, 2)
    }

