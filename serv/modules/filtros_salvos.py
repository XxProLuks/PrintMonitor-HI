"""
Módulo para gerenciar filtros salvos e favoritos
"""
import sqlite3
import json
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


def criar_tabela_filtros(conn: sqlite3.Connection):
    """Cria tabela de filtros salvos se não existir"""
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS filtros_salvos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL,
                nome TEXT NOT NULL,
                tipo TEXT NOT NULL,
                filtros TEXT NOT NULL,
                compartilhado INTEGER DEFAULT 0,
                padrao INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(usuario, nome, tipo)
            )
        """)
        conn.commit()
    except Exception as e:
        logger.error(f"Erro ao criar tabela de filtros: {e}")


def salvar_filtro(conn: sqlite3.Connection, usuario: str, nome: str, 
                  tipo: str, filtros: Dict, compartilhado: bool = False,
                  padrao: bool = False) -> bool:
    """
    Salva um filtro para o usuário
    
    Args:
        conn: Conexão com banco
        usuario: Nome do usuário
        nome: Nome do filtro
        tipo: Tipo de filtro (dashboard, usuarios, setores, etc)
        filtros: Dicionário com os filtros
        compartilhado: Se o filtro pode ser compartilhado
        padrao: Se é o filtro padrão do usuário
    """
    try:
        criar_tabela_filtros(conn)
        
        # Se for padrão, remove padrão anterior do mesmo tipo
        if padrao:
            conn.execute(
                "UPDATE filtros_salvos SET padrao = 0 WHERE usuario = ? AND tipo = ?",
                (usuario, tipo)
            )
        
        # Salva o filtro
        conn.execute(
            """INSERT OR REPLACE INTO filtros_salvos 
            (usuario, nome, tipo, filtros, compartilhado, padrao)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (usuario, nome, tipo, json.dumps(filtros), 1 if compartilhado else 0, 1 if padrao else 0)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar filtro: {e}")
        return False


def listar_filtros(conn: sqlite3.Connection, usuario: str, 
                   tipo: Optional[str] = None) -> List[Dict]:
    """Lista filtros salvos do usuário"""
    try:
        criar_tabela_filtros(conn)
        
        if tipo:
            query = """
                SELECT id, nome, tipo, filtros, compartilhado, padrao, created_at
                FROM filtros_salvos
                WHERE usuario = ? AND tipo = ?
                ORDER BY padrao DESC, created_at DESC
            """
            rows = conn.execute(query, (usuario, tipo)).fetchall()
        else:
            query = """
                SELECT id, nome, tipo, filtros, compartilhado, padrao, created_at
                FROM filtros_salvos
                WHERE usuario = ? OR compartilhado = 1
                ORDER BY padrao DESC, created_at DESC
            """
            rows = conn.execute(query, (usuario,)).fetchall()
        
        filtros = []
        for row in rows:
            filtros.append({
                'id': row[0],
                'nome': row[1],
                'tipo': row[2],
                'filtros': json.loads(row[3]),
                'compartilhado': bool(row[4]),
                'padrao': bool(row[5]),
                'created_at': row[6]
            })
        
        return filtros
    except Exception as e:
        logger.error(f"Erro ao listar filtros: {e}")
        return []


def obter_filtro_padrao(conn: sqlite3.Connection, usuario: str, tipo: str) -> Optional[Dict]:
    """Obtém o filtro padrão do usuário para um tipo"""
    try:
        criar_tabela_filtros(conn)
        
        row = conn.execute(
            """SELECT filtros FROM filtros_salvos
            WHERE usuario = ? AND tipo = ? AND padrao = 1
            LIMIT 1""",
            (usuario, tipo)
        ).fetchone()
        
        if row:
            return json.loads(row[0])
        return None
    except Exception as e:
        logger.error(f"Erro ao obter filtro padrão: {e}")
        return None


def deletar_filtro(conn: sqlite3.Connection, filtro_id: int, usuario: str) -> bool:
    """Deleta um filtro (apenas se for do usuário)"""
    try:
        criar_tabela_filtros(conn)
        
        conn.execute(
            "DELETE FROM filtros_salvos WHERE id = ? AND usuario = ?",
            (filtro_id, usuario)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro ao deletar filtro: {e}")
        return False

