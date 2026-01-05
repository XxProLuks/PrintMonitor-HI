"""
Módulo de Cache
Sistema de cache para melhorar performance
"""
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Any
import json
import logging

logger = logging.getLogger(__name__)


def obter_cache(conn: sqlite3.Connection, chave: str) -> Optional[Any]:
    """Obtém valor do cache se ainda válido"""
    row = conn.execute(
        "SELECT valor, expiracao FROM cache_consultas WHERE chave = ?",
        (chave,)
    ).fetchone()
    
    if not row:
        return None
    
    valor_str, expiracao_str = row
    
    # Verifica se expirou
    try:
        expiracao = datetime.fromisoformat(expiracao_str)
        if datetime.now() > expiracao:
            # Remove cache expirado
            conn.execute("DELETE FROM cache_consultas WHERE chave = ?", (chave,))
            conn.commit()
            return None
    except:
        return None
    
    # Deserializa valor
    try:
        return json.loads(valor_str)
    except:
        return valor_str


def definir_cache(conn: sqlite3.Connection, chave: str, valor: Any, 
                 minutos_expiracao: int = 5):
    """Define valor no cache"""
    try:
        expiracao = (datetime.now() + timedelta(minutes=minutos_expiracao)).isoformat()
        valor_str = json.dumps(valor, ensure_ascii=False) if not isinstance(valor, str) else valor
        
        conn.execute(
            """INSERT OR REPLACE INTO cache_consultas (chave, valor, expiracao)
               VALUES (?, ?, ?)""",
            (chave, valor_str, expiracao)
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Erro ao definir cache: {e}")


def limpar_cache_expirado(conn: sqlite3.Connection):
    """Remove caches expirados"""
    try:
        agora = datetime.now().isoformat()
        conn.execute(
            "DELETE FROM cache_consultas WHERE expiracao < ?",
            (agora,)
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Erro ao limpar cache: {e}")


def limpar_cache(conn: sqlite3.Connection, chave: Optional[str] = None):
    """Limpa cache específico ou todo"""
    try:
        if chave:
            conn.execute("DELETE FROM cache_consultas WHERE chave = ?", (chave,))
        else:
            conn.execute("DELETE FROM cache_consultas")
        conn.commit()
    except Exception as e:
        logger.error(f"Erro ao limpar cache: {e}")

