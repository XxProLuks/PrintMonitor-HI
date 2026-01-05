"""
Módulo para sistema de aprovação de impressões
"""
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def criar_tabela_aprovacoes(conn: sqlite3.Connection):
    """Cria tabelas de aprovação se não existirem"""
    try:
        # Tabela de regras de aprovação
        conn.execute("""
            CREATE TABLE IF NOT EXISTS regras_aprovacao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                condicao TEXT NOT NULL,
                valor_limite REAL,
                ativo INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabela de aprovações pendentes
        conn.execute("""
            CREATE TABLE IF NOT EXISTS aprovacoes_pendentes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evento_id INTEGER,
                usuario TEXT NOT NULL,
                motivo TEXT,
                valor REAL,
                status TEXT DEFAULT 'pendente',
                aprovador TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                aprovado_em TEXT,
                FOREIGN KEY (evento_id) REFERENCES events(id)
            )
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_aprovacoes_status 
            ON aprovacoes_pendentes(status)
        """)
        
        conn.commit()
    except Exception as e:
        logger.error(f"Erro ao criar tabelas de aprovação: {e}")


def criar_regra_aprovacao(conn: sqlite3.Connection, nome: str, 
                          condicao: str, valor_limite: Optional[float] = None) -> bool:
    """Cria uma regra de aprovação"""
    try:
        criar_tabela_aprovacoes(conn)
        
        conn.execute(
            """INSERT INTO regras_aprovacao (nome, condicao, valor_limite)
            VALUES (?, ?, ?)""",
            (nome, condicao, valor_limite)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro ao criar regra de aprovação: {e}")
        return False


def verificar_necessita_aprovacao(conn: sqlite3.Connection, evento: Dict) -> bool:
    """Verifica se um evento precisa de aprovação"""
    try:
        criar_tabela_aprovacoes(conn)
        
        regras = conn.execute(
            "SELECT condicao, valor_limite FROM regras_aprovacao WHERE ativo = 1"
        ).fetchall()
        
        for condicao, valor_limite in regras:
            if condicao == 'valor_maior_que' and evento.get('valor_estimado', 0) > (valor_limite or 0):
                return True
            elif condicao == 'paginas_maior_que' and evento.get('pages_printed', 0) > (valor_limite or 0):
                return True
            elif condicao == 'color' and evento.get('color_mode') == 'color':
                return True
        
        return False
    except Exception as e:
        logger.error(f"Erro ao verificar aprovação: {e}")
        return False


def criar_solicitacao_aprovacao(conn: sqlite3.Connection, evento_id: int,
                                usuario: str, motivo: str, valor: float) -> bool:
    """Cria solicitação de aprovação"""
    try:
        criar_tabela_aprovacoes(conn)
        
        conn.execute(
            """INSERT INTO aprovacoes_pendentes 
            (evento_id, usuario, motivo, valor, status)
            VALUES (?, ?, ?, ?, 'pendente')""",
            (evento_id, usuario, motivo, valor)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro ao criar solicitação de aprovação: {e}")
        return False


def listar_aprovacoes_pendentes(conn: sqlite3.Connection) -> List[Dict]:
    """Lista aprovações pendentes"""
    try:
        criar_tabela_aprovacoes(conn)
        
        rows = conn.execute("""
            SELECT a.id, a.evento_id, a.usuario, a.motivo, a.valor, a.created_at,
                   e.date, e.printer_name, e.pages_printed
            FROM aprovacoes_pendentes a
            LEFT JOIN events e ON a.evento_id = e.id
            WHERE a.status = 'pendente'
            ORDER BY a.created_at DESC
        """).fetchall()
        
        aprovacoes = []
        for row in rows:
            aprovacoes.append({
                'id': row[0],
                'evento_id': row[1],
                'usuario': row[2],
                'motivo': row[3],
                'valor': row[4],
                'created_at': row[5],
                'evento': {
                    'date': row[6],
                    'printer': row[7],
                    'pages': row[8]
                } if row[6] else None
            })
        
        return aprovacoes
    except Exception as e:
        logger.error(f"Erro ao listar aprovações: {e}")
        return []


def aprovar_impressao(conn: sqlite3.Connection, aprovacao_id: int, 
                     aprovador: str) -> bool:
    """Aprova uma impressão"""
    try:
        criar_tabela_aprovacoes(conn)
        
        conn.execute(
            """UPDATE aprovacoes_pendentes 
            SET status = 'aprovado', aprovador = ?, aprovado_em = ?
            WHERE id = ?""",
            (aprovador, datetime.now().isoformat(), aprovacao_id)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro ao aprovar impressão: {e}")
        return False


def rejeitar_impressao(conn: sqlite3.Connection, aprovacao_id: int,
                      aprovador: str, motivo: str) -> bool:
    """Rejeita uma impressão"""
    try:
        criar_tabela_aprovacoes(conn)
        
        conn.execute(
            """UPDATE aprovacoes_pendentes 
            SET status = 'rejeitado', aprovador = ?, aprovado_em = ?, motivo = ?
            WHERE id = ?""",
            (aprovador, datetime.now().isoformat(), motivo, aprovacao_id)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro ao rejeitar impressão: {e}")
        return False

