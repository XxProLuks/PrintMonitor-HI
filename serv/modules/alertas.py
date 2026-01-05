"""
Módulo de Alertas e Notificações
Sistema completo de alertas por email, dashboard, etc.
"""
import sqlite3
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List, Optional
import logging
import json

logger = logging.getLogger(__name__)


def criar_alerta(conn: sqlite3.Connection, tipo: str, nivel: str, titulo: str,
                mensagem: str, referencia: Optional[str] = None,
                valor_atual: Optional[float] = None,
                valor_limite: Optional[float] = None) -> bool:
    """Cria um novo alerta"""
    try:
        conn.execute(
            """INSERT INTO alertas 
               (tipo, nivel, titulo, mensagem, referencia, valor_atual, valor_limite)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (tipo, nivel, titulo, mensagem, referencia, valor_atual, valor_limite)
        )
        conn.commit()
        
        # Verifica se deve enviar email
        config = buscar_config_alerta(conn, tipo, referencia)
        if config and config.get("email_habilitado"):
            enviar_email_alerta(titulo, mensagem, config.get("email_destinatarios", ""))
        
        return True
    except Exception as e:
        logger.error(f"Erro ao criar alerta: {e}")
        return False


def buscar_alertas(conn: sqlite3.Connection, lido: Optional[bool] = None,
                  nivel: Optional[str] = None, limite: int = 50) -> List[Dict]:
    """Busca alertas"""
    query = "SELECT * FROM alertas WHERE 1=1"
    params = []
    
    if lido is not None:
        query += " AND lido = ?"
        params.append(1 if lido else 0)
    
    if nivel:
        query += " AND nivel = ?"
        params.append(nivel)
    
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limite)
    
    rows = conn.execute(query, params).fetchall()
    
    alertas = []
    for row in rows:
        alertas.append({
            "id": row[0],
            "tipo": row[1],
            "nivel": row[2],
            "titulo": row[3],
            "mensagem": row[4],
            "referencia": row[5],
            "valor_atual": row[6],
            "valor_limite": row[7],
            "lido": bool(row[8]),
            "created_at": row[9]
        })
    
    return alertas


def marcar_lido(conn: sqlite3.Connection, alerta_id: int) -> bool:
    """Marca alerta como lido"""
    try:
        conn.execute(
            "UPDATE alertas SET lido = 1 WHERE id = ?",
            (alerta_id,)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro ao marcar alerta como lido: {e}")
        return False


def buscar_config_alerta(conn: sqlite3.Connection, tipo: str,
                        referencia: Optional[str] = None) -> Optional[Dict]:
    """Busca configuração de alerta"""
    if referencia:
        row = conn.execute(
            "SELECT * FROM alerta_config WHERE tipo = ? AND referencia = ? AND ativo = 1",
            (tipo, referencia)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM alerta_config WHERE tipo = ? AND referencia IS NULL AND ativo = 1",
            (tipo,)
        ).fetchone()
    
    if not row:
        return None
    
    return {
        "id": row[0],
        "tipo": row[1],
        "referencia": row[2],
        "condicao": row[3],
        "valor_limite": row[4],
        "email_habilitado": bool(row[5]),
        "email_destinatarios": row[6],
        "ativo": bool(row[7])
    }


def verificar_alertas_automaticos(conn: sqlite3.Connection):
    """Verifica e cria alertas automaticamente baseado em configurações"""
    configs = conn.execute(
        "SELECT * FROM alerta_config WHERE ativo = 1"
    ).fetchall()
    
    for config in configs:
        tipo = config[1]
        referencia = config[2]
        condicao = config[3]
        valor_limite = config[4]
        
        # Calcula valor atual baseado no tipo
        valor_atual = _calcular_valor_atual(conn, tipo, referencia)
        
        # Verifica condição
        if _verificar_condicao(valor_atual, condicao, valor_limite):
            criar_alerta(
                conn, tipo, "warning",
                f"Alerta de {tipo}",
                f"Valor atual ({valor_atual}) {condicao} limite ({valor_limite})",
                referencia, valor_atual, valor_limite
            )


def _calcular_valor_atual(conn: sqlite3.Connection, tipo: str,
                          referencia: Optional[str]) -> float:
    """Calcula valor atual para verificação de alertas"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from modules.calculo_impressao import calcular_folhas_fisicas
    from modules.helper_db import custo_unitario_por_data
    
    hoje = datetime.now()
    inicio_mes = hoje.replace(day=1).strftime("%Y-%m-%d")
    fim_mes = hoje.strftime("%Y-%m-%d")
    
    query = "SELECT pages_printed, duplex, color_mode, date FROM events WHERE date(date) >= date(?) AND date(date) <= date(?)"
    params = [inicio_mes, fim_mes]
    
    if tipo == "custo_setor" and referencia:
        query += " AND user IN (SELECT user FROM users WHERE sector = ?)"
        params.append(referencia)
    elif tipo == "custo_user" and referencia:
        query += " AND user = ?"
        params.append(referencia)
    elif tipo == "paginas_setor" and referencia:
        query += " AND user IN (SELECT user FROM users WHERE sector = ?)"
        params.append(referencia)
    elif tipo == "paginas_user" and referencia:
        query += " AND user = ?"
        params.append(referencia)
    
    rows = conn.execute(query, params).fetchall()
    
    if "custo" in tipo:
        total = 0.0
        for row in rows:
            pages = row[0] or 0
            duplex = row[1] if len(row) > 1 else None
            color_mode = row[2] if len(row) > 2 else None
            date_str = row[3] if len(row) > 3 else None
            
            folhas = calcular_folhas_fisicas(pages, duplex)
            if date_str:
                data_evento = date_str.split()[0] if " " in date_str else date_str
                if color_mode == 'Color':
                    custo = custo_unitario_por_data(data_evento, 'Color')
                elif color_mode == 'Black & White':
                    custo = custo_unitario_por_data(data_evento, 'Black & White')
                else:
                    custo = custo_unitario_por_data(data_evento, None)
                total += folhas * custo
        return total
    else:
        total = 0
        for row in rows:
            pages = row[0] or 0
            duplex = row[1] if len(row) > 1 else None
            total += calcular_folhas_fisicas(pages, duplex)
        return float(total)


def _verificar_condicao(valor_atual: float, condicao: str, valor_limite: float) -> bool:
    """Verifica se condição foi atendida"""
    if condicao == ">=":
        return valor_atual >= valor_limite
    elif condicao == ">":
        return valor_atual > valor_limite
    elif condicao == "<=":
        return valor_atual <= valor_limite
    elif condicao == "<":
        return valor_atual < valor_limite
    elif condicao == "==":
        return valor_atual == valor_limite
    return False


def enviar_email_alerta(titulo: str, mensagem: str, destinatarios: str):
    """Envia email de alerta"""
    try:
        # Configuração de email (pode ser movida para config)
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        
        if not smtp_user or not smtp_password:
            logger.warning("Configuração de email não encontrada. Alerta não enviado.")
            return False
        
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = destinatarios
        msg['Subject'] = f"[Print Monitor] {titulo}"
        msg.attach(MIMEText(mensagem, 'plain', 'utf-8'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email de alerta enviado para {destinatarios}")
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar email: {e}")
        return False

