"""
Módulo de Dashboard Widgets Personalizados
Gerencia widgets customizáveis do dashboard
"""
import sqlite3
import json
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def criar_widget(conn: sqlite3.Connection, usuario: str, tipo: str,
                posicao: int, configuracao: Dict) -> bool:
    """Cria um widget personalizado"""
    try:
        config_str = json.dumps(configuracao, ensure_ascii=False)
        
        conn.execute(
            """INSERT INTO dashboard_widgets 
               (usuario, tipo, posicao, configuracao, ativo)
               VALUES (?, ?, ?, ?, 1)""",
            (usuario, tipo, posicao, config_str)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro ao criar widget: {e}")
        return False


def buscar_widgets(conn: sqlite3.Connection, usuario: str) -> List[Dict]:
    """Busca widgets de um usuário"""
    rows = conn.execute(
        """SELECT * FROM dashboard_widgets 
           WHERE usuario = ? AND ativo = 1 
           ORDER BY posicao""",
        (usuario,)
    ).fetchall()
    
    widgets = []
    for row in rows:
        try:
            config = json.loads(row[4])
        except:
            config = {}
        
        widgets.append({
            "id": row[0],
            "usuario": row[1],
            "tipo": row[2],
            "posicao": row[3],
            "configuracao": config,
            "ativo": bool(row[5])
        })
    
    return widgets


def atualizar_widget(conn: sqlite3.Connection, widget_id: int,
                    posicao: Optional[int] = None,
                    configuracao: Optional[Dict] = None) -> bool:
    """Atualiza um widget"""
    try:
        if posicao is not None:
            conn.execute(
                "UPDATE dashboard_widgets SET posicao = ? WHERE id = ?",
                (posicao, widget_id)
            )
        
        if configuracao is not None:
            config_str = json.dumps(configuracao, ensure_ascii=False)
            conn.execute(
                "UPDATE dashboard_widgets SET configuracao = ? WHERE id = ?",
                (config_str, widget_id)
            )
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar widget: {e}")
        return False


def remover_widget(conn: sqlite3.Connection, widget_id: int) -> bool:
    """Remove um widget (desativa)"""
    try:
        conn.execute(
            "UPDATE dashboard_widgets SET ativo = 0 WHERE id = ?",
            (widget_id,)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro ao remover widget: {e}")
        return False


TIPOS_WIDGETS_DISPONIVEIS = [
    {"tipo": "total_impressoes", "nome": "Total de Impressões", "icone": "bi-printer"},
    {"tipo": "total_paginas", "nome": "Total de Páginas", "icone": "bi-file-text"},
    {"tipo": "custo_mensal", "nome": "Custo Mensal", "icone": "bi-currency-dollar"},
    {"tipo": "grafico_setores", "nome": "Gráfico por Setores", "icone": "bi-bar-chart"},
    {"tipo": "grafico_usuarios", "nome": "Gráfico por Usuários", "icone": "bi-people"},
    {"tipo": "grafico_tendencia", "nome": "Tendência 7 Dias", "icone": "bi-graph-up"},
    {"tipo": "alertas", "nome": "Alertas Recentes", "icone": "bi-bell"},
    {"tipo": "quota_status", "nome": "Status de Quotas", "icone": "bi-clipboard-check"},
    {"tipo": "economia", "nome": "Economia Estimada", "icone": "bi-piggy-bank"},
    {"tipo": "comparativo", "nome": "Comparativo Períodos", "icone": "bi-arrow-left-right"}
]

