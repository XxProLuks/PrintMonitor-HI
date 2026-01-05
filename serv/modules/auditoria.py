"""
Módulo de Auditoria
Registra todas as ações dos usuários
"""
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
import logging
from flask import request

logger = logging.getLogger(__name__)


def registrar_acao(conn: sqlite3.Connection, usuario: str, acao: str,
                   tabela: Optional[str] = None, registro_id: Optional[str] = None,
                   dados_anteriores: Optional[Dict] = None,
                   dados_novos: Optional[Dict] = None):
    """Registra uma ação na auditoria"""
    try:
        ip_address = request.remote_addr if request else None
        
        dados_ant_str = None
        if dados_anteriores:
            import json
            dados_ant_str = json.dumps(dados_anteriores, ensure_ascii=False)
        
        dados_novos_str = None
        if dados_novos:
            import json
            dados_novos_str = json.dumps(dados_novos, ensure_ascii=False)
        
        conn.execute(
            """INSERT INTO auditoria 
               (usuario, acao, tabela, registro_id, dados_anteriores, dados_novos, ip_address)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (usuario, acao, tabela, registro_id, dados_ant_str, dados_novos_str, ip_address)
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Erro ao registrar ação na auditoria: {e}")


def buscar_auditoria(conn: sqlite3.Connection, usuario: Optional[str] = None,
                    acao: Optional[str] = None, tabela: Optional[str] = None,
                    limite: int = 100) -> List[Dict]:
    """Busca registros de auditoria"""
    query = "SELECT * FROM auditoria WHERE 1=1"
    params = []
    
    if usuario:
        query += " AND usuario = ?"
        params.append(usuario)
    
    if acao:
        query += " AND acao = ?"
        params.append(acao)
    
    if tabela:
        query += " AND tabela = ?"
        params.append(tabela)
    
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limite)
    
    rows = conn.execute(query, params).fetchall()
    
    registros = []
    for row in rows:
        import json
        dados_ant = None
        dados_nov = None
        
        if row[5]:
            try:
                dados_ant = json.loads(row[5])
            except:
                dados_ant = row[5]
        
        if row[6]:
            try:
                dados_nov = json.loads(row[6])
            except:
                dados_nov = row[6]
        
        registros.append({
            "id": row[0],
            "usuario": row[1],
            "acao": row[2],
            "tabela": row[3],
            "registro_id": row[4],
            "dados_anteriores": dados_ant,
            "dados_novos": dados_nov,
            "ip_address": row[7],
            "created_at": row[8]
        })
    
    return registros

