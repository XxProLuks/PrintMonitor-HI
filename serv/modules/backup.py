"""
Módulo de Backup Automático
Gerencia backups e restore points
"""
import sqlite3
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional
import logging
import threading
import time

logger = logging.getLogger(__name__)


def criar_backup(db_path: str, nome: Optional[str] = None,
                descricao: Optional[str] = None) -> Optional[str]:
    """Cria um backup do banco de dados"""
    try:
        if not nome:
            nome = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Cria diretório de backups se não existir
        backup_dir = os.path.join(os.path.dirname(db_path), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        backup_path = os.path.join(backup_dir, f"{nome}.db")
        
        # Copia arquivo
        shutil.copy2(db_path, backup_path)
        
        tamanho = os.path.getsize(backup_path)
        
        # Registra no banco
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """INSERT INTO backup_points (nome, descricao, arquivo_path, tamanho)
                   VALUES (?, ?, ?, ?)""",
                (nome, descricao, backup_path, tamanho)
            )
            conn.commit()
        
        logger.info(f"Backup criado: {backup_path} ({tamanho} bytes)")
        return backup_path
    except Exception as e:
        logger.error(f"Erro ao criar backup: {e}")
        return None


def restaurar_backup(db_path: str, backup_id: int) -> bool:
    """Restaura um backup"""
    try:
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT arquivo_path FROM backup_points WHERE id = ?",
                (backup_id,)
            ).fetchone()
        
        if not row:
            logger.error(f"Backup {backup_id} não encontrado")
            return False
        
        backup_path = row[0]
        
        if not os.path.exists(backup_path):
            logger.error(f"Arquivo de backup não encontrado: {backup_path}")
            return False
        
        # Cria backup do banco atual antes de restaurar
        backup_atual = criar_backup(db_path, f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # Restaura
        shutil.copy2(backup_path, db_path)
        
        logger.info(f"Backup restaurado: {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Erro ao restaurar backup: {e}")
        return False


def listar_backups(conn: sqlite3.Connection) -> List[Dict]:
    """Lista todos os backups"""
    rows = conn.execute(
        "SELECT * FROM backup_points ORDER BY created_at DESC"
    ).fetchall()
    
    backups = []
    for row in rows:
        backups.append({
            "id": row[0],
            "nome": row[1],
            "descricao": row[2],
            "arquivo_path": row[3],
            "tamanho": row[4],
            "created_at": row[5],
            "existe": os.path.exists(row[3]) if row[3] else False
        })
    
    return backups


def limpar_backups_antigos(db_path: str, dias_manter: int = 30):
    """Remove backups mais antigos que X dias"""
    try:
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                "SELECT id, arquivo_path, created_at FROM backup_points"
            ).fetchall()
        
        hoje = datetime.now()
        removidos = 0
        
        for row in rows:
            backup_id, arquivo_path, created_str = row
            
            try:
                created = datetime.fromisoformat(created_str)
                dias_diferenca = (hoje - created).days
                
                if dias_diferenca > dias_manter:
                    if arquivo_path and os.path.exists(arquivo_path):
                        os.remove(arquivo_path)
                    
                    with sqlite3.connect(db_path) as conn:
                        conn.execute("DELETE FROM backup_points WHERE id = ?", (backup_id,))
                        conn.commit()
                    
                    removidos += 1
            except:
                pass
        
        logger.info(f"Removidos {removidos} backups antigos")
        return removidos
    except Exception as e:
        logger.error(f"Erro ao limpar backups: {e}")
        return 0


def iniciar_backup_automatico(db_path: str, intervalo_horas: int = 24):
    """Inicia thread para backup automático"""
    def backup_loop():
        while True:
            try:
                criar_backup(db_path, None, "Backup automático")
                limpar_backups_antigos(db_path)
            except Exception as e:
                logger.error(f"Erro no backup automático: {e}")
            
            time.sleep(intervalo_horas * 3600)
    
    thread = threading.Thread(target=backup_loop, daemon=True)
    thread.start()
    return thread

