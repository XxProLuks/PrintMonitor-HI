"""
Módulo para sistema de gamificação e recompensas
"""
import sqlite3
from typing import List, Dict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def criar_tabela_gamificacao(conn: sqlite3.Connection):
    """Cria tabelas de gamificação se não existirem"""
    try:
        # Tabela de pontos e badges
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gamificacao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL,
                setor TEXT,
                pontos INTEGER DEFAULT 0,
                badges TEXT,
                nivel INTEGER DEFAULT 1,
                economia_total REAL DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(usuario)
            )
        """)
        
        # Tabela de conquistas
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conquistas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL,
                badge TEXT NOT NULL,
                descricao TEXT,
                pontos INTEGER DEFAULT 0,
                data_conquista TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_gamificacao_pontos 
            ON gamificacao(pontos DESC)
        """)
        
        conn.commit()
    except Exception as e:
        logger.error(f"Erro ao criar tabelas de gamificação: {e}")


def calcular_pontos_economia(conn: sqlite3.Connection, usuario: str, 
                            economia: float) -> int:
    """Calcula pontos baseado em economia (1 real = 10 pontos)"""
    return int(economia * 10)


def atualizar_pontos(conn: sqlite3.Connection, usuario: str, 
                    pontos: int, economia: float, setor: Optional[str] = None):
    """Atualiza pontos do usuário"""
    try:
        criar_tabela_gamificacao(conn)
        
        # Verifica se usuário existe
        user_data = conn.execute(
            "SELECT pontos, economia_total FROM gamificacao WHERE usuario = ?",
            (usuario,)
        ).fetchone()
        
        if user_data:
            pontos_atual = user_data[0] + pontos
            economia_total = user_data[1] + economia
            nivel = min(10, (pontos_atual // 1000) + 1)  # Nível baseado em pontos
            
            conn.execute(
                """UPDATE gamificacao 
                SET pontos = ?, economia_total = ?, nivel = ?, updated_at = ?
                WHERE usuario = ?""",
                (pontos_atual, economia_total, nivel, datetime.now().isoformat(), usuario)
            )
        else:
            nivel = min(10, (pontos // 1000) + 1)
            conn.execute(
                """INSERT INTO gamificacao (usuario, setor, pontos, economia_total, nivel)
                VALUES (?, ?, ?, ?, ?)""",
                (usuario, setor, pontos, economia, nivel)
            )
        
        conn.commit()
    except Exception as e:
        logger.error(f"Erro ao atualizar pontos: {e}")


def adicionar_badge(conn: sqlite3.Connection, usuario: str, badge: str, 
                   descricao: str, pontos: int = 0):
    """Adiciona badge ao usuário"""
    try:
        criar_tabela_gamificacao(conn)
        
        # Adiciona conquista
        conn.execute(
            """INSERT INTO conquistas (usuario, badge, descricao, pontos)
            VALUES (?, ?, ?, ?)""",
            (usuario, badge, descricao, pontos)
        )
        
        # Atualiza badges do usuário
        user_data = conn.execute(
            "SELECT badges FROM gamificacao WHERE usuario = ?",
            (usuario,)
        ).fetchone()
        
        badges_existentes = user_data[0].split(',') if user_data and user_data[0] else []
        if badge not in badges_existentes:
            badges_existentes.append(badge)
            badges_str = ','.join(badges_existentes)
            
            conn.execute(
                "UPDATE gamificacao SET badges = ? WHERE usuario = ?",
                (badges_str, usuario)
            )
        
        # Adiciona pontos
        if pontos > 0:
            atualizar_pontos(conn, usuario, pontos, 0)
        
        conn.commit()
    except Exception as e:
        logger.error(f"Erro ao adicionar badge: {e}")


def obter_ranking(conn: sqlite3.Connection, tipo: str = 'geral', 
                 limite: int = 10) -> List[Dict]:
    """Obtém ranking de usuários ou setores"""
    try:
        criar_tabela_gamificacao(conn)
        
        if tipo == 'usuarios':
            query = """
                SELECT usuario, pontos, nivel, economia_total, badges
                FROM gamificacao
                ORDER BY pontos DESC
                LIMIT ?
            """
            rows = conn.execute(query, (limite,)).fetchall()
        else:  # setores
            query = """
                SELECT setor, SUM(pontos) as total_pontos, SUM(economia_total) as total_economia
                FROM gamificacao
                WHERE setor IS NOT NULL
                GROUP BY setor
                ORDER BY total_pontos DESC
                LIMIT ?
            """
            rows = conn.execute(query, (limite,)).fetchall()
        
        ranking = []
        posicao = 1
        for row in rows:
            if tipo == 'usuarios':
                ranking.append({
                    'posicao': posicao,
                    'usuario': row[0],
                    'pontos': row[1],
                    'nivel': row[2],
                    'economia': row[3],
                    'badges': row[4].split(',') if row[4] else []
                })
            else:
                ranking.append({
                    'posicao': posicao,
                    'setor': row[0],
                    'pontos': row[1],
                    'economia': row[2]
                })
            posicao += 1
        
        return ranking
    except Exception as e:
        logger.error(f"Erro ao obter ranking: {e}")
        return []


def verificar_conquistas(conn: sqlite3.Connection, usuario: str):
    """Verifica e atribui conquistas automáticas"""
    try:
        criar_tabela_gamificacao(conn)
        
        # Busca dados do usuário
        user_data = conn.execute(
            "SELECT pontos, economia_total FROM gamificacao WHERE usuario = ?",
            (usuario,)
        ).fetchone()
        
        if not user_data:
            return
        
        pontos, economia = user_data
        
        # Conquistas baseadas em pontos
        if pontos >= 1000 and not conn.execute(
            "SELECT 1 FROM conquistas WHERE usuario = ? AND badge = 'bronze'",
            (usuario,)
        ).fetchone():
            adicionar_badge(conn, usuario, 'bronze', 'Primeiros 1000 pontos!', 50)
        
        if pontos >= 5000 and not conn.execute(
            "SELECT 1 FROM conquistas WHERE usuario = ? AND badge = 'prata'",
            (usuario,)
        ).fetchone():
            adicionar_badge(conn, usuario, 'prata', '5000 pontos alcançados!', 100)
        
        if pontos >= 10000 and not conn.execute(
            "SELECT 1 FROM conquistas WHERE usuario = ? AND badge = 'ouro'",
            (usuario,)
        ).fetchone():
            adicionar_badge(conn, usuario, 'ouro', 'Mestre em economia!', 200)
        
        # Conquistas baseadas em economia
        if economia >= 100 and not conn.execute(
            "SELECT 1 FROM conquistas WHERE usuario = ? AND badge = 'economizador'",
            (usuario,)
        ).fetchone():
            adicionar_badge(conn, usuario, 'economizador', 'Economizou R$ 100!', 100)
        
    except Exception as e:
        logger.error(f"Erro ao verificar conquistas: {e}")

