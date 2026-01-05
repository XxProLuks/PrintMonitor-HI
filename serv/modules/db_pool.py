"""
Módulo de Connection Pooling para SQLite
=========================================

Implementa um pool de conexões para melhorar performance e gerenciar
múltiplas conexões simultâneas ao banco de dados SQLite.

Features:
- Pool de conexões reutilizáveis
- Retry logic para falhas de conexão
- Timeout configurável
- Monitoramento de conexões
- Thread-safe
"""

import sqlite3
import threading
import time
import logging
from typing import Optional, ContextManager
from contextlib import contextmanager
from queue import Queue, Empty

logger = logging.getLogger(__name__)

class SQLiteConnectionPool:
    """
    Pool de conexões SQLite com retry logic e timeout.
    """
    
    def __init__(
        self,
        db_path: str,
        max_connections: int = 10,
        timeout: float = 5.0,
        max_retries: int = 3,
        retry_delay: float = 0.5
    ):
        """
        Inicializa o pool de conexões.
        
        Args:
            db_path: Caminho para o banco de dados SQLite
            max_connections: Número máximo de conexões no pool
            timeout: Timeout para operações (segundos)
            max_retries: Número máximo de tentativas em caso de falha
            retry_delay: Delay entre tentativas (segundos)
        """
        self.db_path = db_path
        self.max_connections = max_connections
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Pool de conexões (fila thread-safe)
        self._pool = Queue(maxsize=max_connections)
        self._lock = threading.Lock()
        self._active_connections = 0
        self._total_connections_created = 0
        
        # Inicializa algumas conexões
        self._initialize_pool()
        
        logger.info(f"📦 Pool de conexões SQLite inicializado: max={max_connections}, timeout={timeout}s")
    
    def _initialize_pool(self):
        """Inicializa conexões iniciais no pool."""
        for _ in range(min(3, self.max_connections)):
            try:
                conn = self._create_connection()
                self._pool.put(conn)
                self._total_connections_created += 1
            except Exception as e:
                logger.warning(f"⚠️ Erro ao criar conexão inicial: {e}")
    
    def _create_connection(self) -> sqlite3.Connection:
        """
        Cria uma nova conexão SQLite.
        
        Returns:
            Conexão SQLite configurada
        """
        conn = sqlite3.connect(
            self.db_path,
            timeout=self.timeout,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row  # Retorna rows como dicionários
        return conn
    
    @contextmanager
    def get_connection(self) -> ContextManager[sqlite3.Connection]:
        """
        Obtém uma conexão do pool (context manager).
        
        Usage:
            with pool.get_connection() as conn:
                cursor = conn.execute("SELECT ...")
        
        Yields:
            Conexão SQLite
        """
        conn = None
        try:
            # Tenta obter conexão do pool
            try:
                conn = self._pool.get(timeout=self.timeout)
            except Empty:
                # Pool vazio, cria nova conexão se possível
                with self._lock:
                    if self._active_connections < self.max_connections:
                        conn = self._create_connection()
                        self._total_connections_created += 1
                        self._active_connections += 1
                    else:
                        # Espera por uma conexão disponível
                        conn = self._pool.get(timeout=self.timeout)
            
            if conn is None:
                raise RuntimeError("Não foi possível obter conexão do pool")
            
            # Verifica se conexão ainda está válida
            try:
                conn.execute("SELECT 1").fetchone()
            except (sqlite3.ProgrammingError, sqlite3.OperationalError):
                # Conexão inválida, cria nova
                try:
                    conn.close()
                except:
                    pass
                conn = self._create_connection()
            
            yield conn
            
            # Retorna conexão ao pool
            try:
                self._pool.put(conn, timeout=1.0)
            except:
                # Pool cheio ou timeout, fecha conexão
                try:
                    conn.close()
                    with self._lock:
                        self._active_connections -= 1
                except:
                    pass
                    
        except Exception as e:
            # Em caso de erro, fecha conexão se necessário
            if conn:
                try:
                    conn.close()
                    with self._lock:
                        self._active_connections -= 1
                except:
                    pass
            raise
    
    def execute_with_retry(self, query: str, params: tuple = (), commit: bool = False):
        """
        Executa uma query com retry logic.
        
        Args:
            query: Query SQL
            params: Parâmetros da query
            commit: Se deve fazer commit após execução
            
        Returns:
            Resultado da query
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                with self.get_connection() as conn:
                    cursor = conn.execute(query, params)
                    result = cursor.fetchall()
                    
                    if commit:
                        conn.commit()
                    
                    return result
                    
            except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # Backoff exponencial
                    logger.warning(f"⚠️ Tentativa {attempt + 1}/{self.max_retries} falhou: {e}")
                else:
                    logger.error(f"❌ Todas as tentativas falharam: {e}")
        
        raise last_error
    
    def get_stats(self) -> dict:
        """
        Retorna estatísticas do pool.
        
        Returns:
            Dict com estatísticas do pool
        """
        with self._lock:
            return {
                'pool_size': self._pool.qsize(),
                'active_connections': self._active_connections,
                'total_created': self._total_connections_created,
                'max_connections': self.max_connections
            }
    
    def close_all(self):
        """Fecha todas as conexões do pool."""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except:
                pass
        
        with self._lock:
            self._active_connections = 0


# Instância global do pool (será inicializada em servidor.py)
_db_pool: Optional[SQLiteConnectionPool] = None


def init_db_pool(db_path: str, **kwargs) -> SQLiteConnectionPool:
    """
    Inicializa o pool de conexões global.
    
    Args:
        db_path: Caminho para o banco de dados
        **kwargs: Argumentos adicionais para SQLiteConnectionPool
        
    Returns:
        Instância do pool
    """
    global _db_pool
    _db_pool = SQLiteConnectionPool(db_path, **kwargs)
    return _db_pool


def get_db_pool() -> Optional[SQLiteConnectionPool]:
    """
    Retorna a instância global do pool.
    
    Returns:
        Instância do pool ou None se não inicializado
    """
    return _db_pool


@contextmanager
def get_db_connection():
    """
    Helper para obter conexão do pool global.
    
    Usage:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT ...")
    """
    if _db_pool is None:
        raise RuntimeError("Pool de conexões não inicializado. Chame init_db_pool() primeiro.")
    
    with _db_pool.get_connection() as conn:
        yield conn

