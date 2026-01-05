"""
Módulo de Relatórios Agendados
Gerencia envio automático de relatórios
"""
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import threading
import time

logger = logging.getLogger(__name__)


def criar_relatorio_agendado(conn: sqlite3.Connection, nome: str, tipo: str,
                            frequencia: str, hora: str,
                            dia_semana: Optional[int] = None,
                            dia_mes: Optional[int] = None,
                            destinatarios: str = "",
                            filtros: Optional[Dict] = None) -> bool:
    """Cria um relatório agendado"""
    try:
        filtros_str = None
        if filtros:
            import json
            filtros_str = json.dumps(filtros, ensure_ascii=False)
        
        conn.execute(
            """INSERT INTO relatorios_agendados 
               (nome, tipo, frequencia, dia_semana, dia_mes, hora, destinatarios, filtros)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (nome, tipo, frequencia, dia_semana, dia_mes, hora, destinatarios, filtros_str)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro ao criar relatório agendado: {e}")
        return False


def verificar_relatorios_pendentes(conn: sqlite3.Connection) -> List[Dict]:
    """Verifica quais relatórios devem ser enviados agora"""
    agora = datetime.now()
    dia_semana_atual = agora.weekday()  # 0 = segunda, 6 = domingo
    dia_mes_atual = agora.day
    hora_atual = agora.strftime("%H:%M")
    
    rows = conn.execute(
        "SELECT * FROM relatorios_agendados WHERE ativo = 1"
    ).fetchall()
    
    pendentes = []
    
    for row in rows:
        id_rel, nome, tipo, frequencia, dia_semana, dia_mes, hora, dest, filtros, ativo, ultimo_envio, created = row
        
        # Verifica se deve executar agora
        deve_executar = False
        
        if frequencia == "diario":
            deve_executar = hora == hora_atual
        elif frequencia == "semanal":
            deve_executar = (dia_semana == dia_semana_atual and hora == hora_atual)
        elif frequencia == "mensal":
            deve_executar = (dia_mes == dia_mes_atual and hora == hora_atual)
        
        # Verifica se já foi enviado hoje
        if ultimo_envio:
            try:
                ultimo = datetime.fromisoformat(ultimo_envio)
                if ultimo.date() == agora.date() and frequencia != "diario":
                    deve_executar = False
            except:
                pass
        
        if deve_executar:
            filtros_dict = None
            if filtros:
                try:
                    import json
                    filtros_dict = json.loads(filtros)
                except:
                    pass
            
            pendentes.append({
                "id": id_rel,
                "nome": nome,
                "tipo": tipo,
                "frequencia": frequencia,
                "destinatarios": dest,
                "filtros": filtros_dict
            })
    
    return pendentes


def executar_relatorio(conn: sqlite3.Connection, relatorio: Dict) -> bool:
    """Executa e envia um relatório agendado"""
    try:
        tipo = relatorio["tipo"]
        filtros = relatorio.get("filtros", {})
        destinatarios = relatorio.get("destinatarios", "")
        
        # Gera relatório baseado no tipo
        if tipo == "dashboard":
            conteudo = gerar_relatorio_dashboard(conn, filtros)
        elif tipo == "setores":
            conteudo = gerar_relatorio_setores(conn, filtros)
        elif tipo == "usuarios":
            conteudo = gerar_relatorio_usuarios(conn, filtros)
        elif tipo == "impressoras":
            conteudo = gerar_relatorio_impressoras(conn, filtros)
        else:
            conteudo = gerar_relatorio_geral(conn, filtros)
        
        # Envia email
        if destinatarios:
            from modules.alertas import enviar_email_alerta
            enviar_email_alerta(
                f"Relatório: {relatorio['nome']}",
                conteudo,
                destinatarios
            )
        
        # Atualiza último envio
        conn.execute(
            "UPDATE relatorios_agendados SET ultimo_envio = ? WHERE id = ?",
            (datetime.now().isoformat(), relatorio["id"])
        )
        conn.commit()
        
        return True
    except Exception as e:
        logger.error(f"Erro ao executar relatório: {e}")
        return False


def gerar_relatorio_dashboard(conn: sqlite3.Connection, filtros: Dict) -> str:
    """Gera relatório de dashboard"""
    # Implementação simplificada
    return "Relatório de Dashboard - Em desenvolvimento"


def gerar_relatorio_setores(conn: sqlite3.Connection, filtros: Dict) -> str:
    """Gera relatório de setores"""
    return "Relatório de Setores - Em desenvolvimento"


def gerar_relatorio_usuarios(conn: sqlite3.Connection, filtros: Dict) -> str:
    """Gera relatório de usuários"""
    return "Relatório de Usuários - Em desenvolvimento"


def gerar_relatorio_impressoras(conn: sqlite3.Connection, filtros: Dict) -> str:
    """Gera relatório de impressoras"""
    return "Relatório de Impressoras - Em desenvolvimento"


def gerar_relatorio_geral(conn: sqlite3.Connection, filtros: Dict) -> str:
    """Gera relatório geral"""
    return "Relatório Geral - Em desenvolvimento"


def iniciar_thread_relatorios(db_path):
    """Inicia thread para verificar relatórios agendados"""
    def verificar_loop():
        while True:
            try:
                with sqlite3.connect(db_path) as conn:
                    pendentes = verificar_relatorios_pendentes(conn)
                    for relatorio in pendentes:
                        executar_relatorio(conn, relatorio)
            except Exception as e:
                logger.error(f"Erro na thread de relatórios: {e}")
            
            time.sleep(60)  # Verifica a cada minuto
    
    thread = threading.Thread(target=verificar_loop, daemon=True)
    thread.start()
    return thread

