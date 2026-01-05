"""
Módulo para sistema de comentários e anotações
"""
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def criar_tabela_comentarios(conn: sqlite3.Connection):
    """Cria tabela de comentários se não existir"""
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS comentarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evento_id INTEGER,
                usuario TEXT NOT NULL,
                comentario TEXT NOT NULL,
                tags TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (evento_id) REFERENCES events(id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_comentarios_evento 
            ON comentarios(evento_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_comentarios_usuario 
            ON comentarios(usuario)
        """)
        conn.commit()
    except Exception as e:
        logger.error(f"Erro ao criar tabela de comentários: {e}")


def adicionar_comentario(conn: sqlite3.Connection, evento_id: int, 
                        usuario: str, comentario: str, 
                        tags: Optional[List[str]] = None) -> bool:
    """Adiciona comentário a um evento"""
    try:
        criar_tabela_comentarios(conn)
        
        tags_str = ','.join(tags) if tags else None
        
        conn.execute(
            """INSERT INTO comentarios (evento_id, usuario, comentario, tags)
            VALUES (?, ?, ?, ?)""",
            (evento_id, usuario, comentario, tags_str)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro ao adicionar comentário: {e}")
        return False


def listar_comentarios(conn: sqlite3.Connection, evento_id: Optional[int] = None,
                       usuario: Optional[str] = None) -> List[Dict]:
    """Lista comentários"""
    try:
        criar_tabela_comentarios(conn)
        
        if evento_id:
            query = """
                SELECT id, evento_id, usuario, comentario, tags, created_at
                FROM comentarios
                WHERE evento_id = ?
                ORDER BY created_at DESC
            """
            rows = conn.execute(query, (evento_id,)).fetchall()
        elif usuario:
            query = """
                SELECT id, evento_id, usuario, comentario, tags, created_at
                FROM comentarios
                WHERE usuario = ?
                ORDER BY created_at DESC
            """
            rows = conn.execute(query, (usuario,)).fetchall()
        else:
            query = """
                SELECT id, evento_id, usuario, comentario, tags, created_at
                FROM comentarios
                ORDER BY created_at DESC
                LIMIT 100
            """
            rows = conn.execute(query).fetchall()
        
        comentarios = []
        for row in rows:
            comentarios.append({
                'id': row[0],
                'evento_id': row[1],
                'usuario': row[2],
                'comentario': row[3],
                'tags': row[4].split(',') if row[4] else [],
                'created_at': row[5]
            })
        
        return comentarios
    except Exception as e:
        logger.error(f"Erro ao listar comentários: {e}")
        return []


def deletar_comentario(conn: sqlite3.Connection, comentario_id: int, 
                      usuario: str) -> bool:
    """Deleta comentário (apenas se for do usuário)"""
    try:
        criar_tabela_comentarios(conn)
        
        conn.execute(
            "DELETE FROM comentarios WHERE id = ? AND usuario = ?",
            (comentario_id, usuario)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro ao deletar comentário: {e}")
        return False

