import win32evtlog
import requests
import re
import time
import logging
import json
import os
import subprocess
import math
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple

# ============================================================================
# CONFIGURAÇÃO E LOGGING - Deve vir ANTES das classes
# ============================================================================

# Configuração temporária de logging (será reconfigurado depois)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CLASSES DE INTERCEPTAÇÃO E VALIDAÇÃO (unificadas no agente.py)
# ============================================================================

# Tentar importar pysnmp para SNMP (opcional)
try:
    from pysnmp.hlapi import (  # type: ignore
        getCmd,
        SnmpEngine,
        CommunityData,
        UdpTransportTarget,
        ContextData,
        ObjectType,
        ObjectIdentity
    )
    SNMP_AVAILABLE = True
except ImportError:
    SNMP_AVAILABLE = False
    # Define stubs vazios para evitar erros de linter
    getCmd = None  # type: ignore
    SnmpEngine = None  # type: ignore
    CommunityData = None  # type: ignore
    UdpTransportTarget = None  # type: ignore
    ContextData = None  # type: ignore
    ObjectType = None  # type: ignore
    ObjectIdentity = None  # type: ignore
    logging.debug("Biblioteca pysnmp não instalada. Validação SNMP desabilitada.")

# Tentar importar win32print para interceptação de spool (opcional)
try:
    import win32print
    import win32api
    import win32con
    import threading
    SPOOL_INTERCEPTOR_AVAILABLE = True
    WIN32PRINT_AVAILABLE = True
except ImportError:
    SPOOL_INTERCEPTOR_AVAILABLE = False
    WIN32PRINT_AVAILABLE = False
    logging.debug("win32print não disponível. Interceptação de spool desabilitada.")

# Tentar importar WMI para backup (opcional)
try:
    import wmi
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False
    logging.debug("Biblioteca WMI não instalada. Backup WMI desabilitado.")

# ============================================================================
# CONSTANTES DO SISTEMA
# ============================================================================

# Event Log do Windows
EVENT_LOG_OPERATIONAL = 'Microsoft-Windows-PrintService/Operational'  # Event 307/805
EVENT_ID_PRINT = 307       # ID do evento de impressão concluída
EVENT_ID_JOB_CONFIG = 805  # ID do evento de configuração do job (RenderJobDiag)

# Campos do Event 805 (RenderJobDiag):
# - JobId: ID do job (para correlacionar com Event 307)
# - Copies: Número real de cópias configuradas
# - Color: 1 = Monocromático, 2 = Colorido
# - XRes/YRes: Resolução
# - Quality: Qualidade de impressão

# Cache de configurações de jobs do Event 805
# Armazena dados do Event 805 para correlacionar com Event 307
_JOB_CONFIG_CACHE: Dict[int, Dict] = {}
_JOB_CONFIG_CACHE_MAX_SIZE = 100  # Limite de jobs em cache

# Servidor e timeouts
DEFAULT_SERVER_URL = "http://192.168.1.27:5002/api/print_events"
DEFAULT_CHECK_INTERVAL = 5  # segundos
DEFAULT_RETRY_INTERVAL = 30  # segundos
DEFAULT_BATCH_SIZE = 50  # eventos por lote

# ============================================================================
# CLASSES DE INTERCEPTAÇÃO
# ============================================================================


# ============================================================================
# IDENTIFICAÇÃO DA MÁQUINA
# ============================================================================
# NOTA: Obtém o nome da máquina de forma consistente e cacheada
# ============================================================================

# Cache global do nome da máquina
_MACHINE_NAME_CACHE: Optional[str] = None


def obter_nome_maquina() -> str:
    """
    Obtém o nome da máquina de forma consistente.
    
    Usa cache para evitar múltiplas consultas.
    Ordem de prioridade:
    1. Cache (se já obtido)
    2. Variável de ambiente COMPUTERNAME
    3. Hostname via socket
    4. Fallback: "UNKNOWN"
    
    Returns:
        Nome da máquina em MAIÚSCULAS
    """
    global _MACHINE_NAME_CACHE
    
    if _MACHINE_NAME_CACHE is not None:
        return _MACHINE_NAME_CACHE
    
    # Tenta COMPUTERNAME (mais confiável no Windows)
    machine = os.environ.get('COMPUTERNAME', '')
    
    # Se não encontrou, tenta socket
    if not machine:
        try:
            import socket
            machine = socket.gethostname()
        except Exception:
            pass
    
    # Fallback
    if not machine:
        machine = "UNKNOWN"
    
    # Normaliza e cacheia
    _MACHINE_NAME_CACHE = machine.upper().strip()
    
    logger.info(f"🖥️ Nome da máquina identificado: {_MACHINE_NAME_CACHE}")
    
    return _MACHINE_NAME_CACHE


# ============================================================================
# FUNÇÕES AUXILIARES PARA CÁLCULO DE FOLHAS
# ============================================================================
# NOTA: Esta função replica a lógica de serv/modules/calculo_impressao.py
#       Manter sincronizada se houver mudanças!
# ============================================================================

def extrair_valor_property(prop) -> str:
    """
    Extrai o valor de uma Property do PowerShell.
    
    O PowerShell pode retornar Properties em diferentes formatos:
    - String simples: "valor"
    - Objeto com Value: {'Value': 'valor'}
    - Objeto complexo: {'Value': 'valor', 'Type': 'System.String'}
    
    Esta função extrai o valor correto em todos os casos.
    
    Args:
        prop: Propriedade do PowerShell (pode ser str, dict, ou None)
    
    Returns:
        String com o valor extraído, ou string vazia se não encontrar
    """
    if prop is None:
        return ""
    
    # Se já é string, retorna diretamente
    if isinstance(prop, str):
        return prop.strip()
    
    # Se é um dicionário com 'Value', extrai o valor
    if isinstance(prop, dict):
        value = prop.get('Value') or prop.get('value') or prop.get('#text', '')
        if value is not None:
            return str(value).strip()
        # Tenta pegar o primeiro valor encontrado
        for v in prop.values():
            if v is not None:
                return str(v).strip()
        return ""
    
    # Para outros tipos, converte para string
    return str(prop).strip()


def calcular_folhas_fisicas(paginas: int, tipo_impressora: str, copias: int = 1) -> int:
    """
    Calcula folhas físicas baseado em páginas e tipo da impressora.
    
    LÓGICA PADRONIZADA (igual ao módulo centralizado):
    - Faces impressas = páginas × cópias
    - Simplex: folhas = faces
    - Duplex:  folhas = ceil(faces / 2)
    
    Args:
        paginas: Param8 do Event 307 (número de páginas impressas)
        tipo_impressora: Tipo da impressora ("duplex" ou "simplex")
        copias: Número de cópias (default: 1)
    
    Returns:
        Número de folhas físicas
    
    Examples:
        >>> calcular_folhas_fisicas(5, "simplex")
        5
        >>> calcular_folhas_fisicas(5, "duplex")
        3
        >>> calcular_folhas_fisicas(2, "duplex", copias=3)
        3
    """
    if paginas is None or paginas <= 0:
        return 0
    
    # Calcula faces totais impressas
    faces_totais = paginas * copias
    
    if tipo_impressora and tipo_impressora.lower() == "duplex":
        # Duplex: 2 faces por folha, arredonda para cima
        return math.ceil(faces_totais / 2)
    else:
        # Simplex ou tipo não informado: 1 face = 1 folha
        return faces_totais


# ============================================================================
# FUNÇÕES DE CAPTURA DO EVENT 805 (Configuração do Job)
# ============================================================================

def capturar_event_805(minutos_busca: int = 30) -> Dict[int, Dict]:
    """
    Captura eventos 805 (RenderJobDiag) e retorna cache por JobID.
    
    Event 805 contém configurações reais do job:
    - Copies: Número real de cópias
    - Color: 1=Mono, 2=Colorido
    - XRes/YRes: Resolução
    
    Args:
        minutos_busca: Quantos minutos para trás buscar
        
    Returns:
        Dict com JobID como chave e configurações como valor
    """
    global _JOB_CONFIG_CACHE
    
    try:
        # Script PowerShell para buscar Event 805
        ps_script = f"""
        $events = Get-WinEvent -FilterHashtable @{{
            LogName='Microsoft-Windows-PrintService/Operational'
            ID=805
            StartTime=(Get-Date).AddMinutes(-{minutos_busca})
        }} -MaxEvents 50 -ErrorAction SilentlyContinue
        
        foreach ($event in $events) {{
            $xml = [xml]$event.ToXml()
            $userData = $xml.Event.UserData.RenderJobDiag
            if ($userData) {{
                Write-Output "JOB805|$($userData.JobId)|$($userData.Copies)|$($userData.Color)|$($userData.XRes)|$($userData.YRes)"
            }}
        }}
        """
        
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if line.startswith('JOB805|'):
                    parts = line.split('|')
                    if len(parts) >= 5:
                        try:
                            job_id = int(parts[1])
                            copies = int(parts[2]) if parts[2] else 1
                            color = int(parts[3]) if parts[3] else 1
                            x_res = int(parts[4]) if parts[4] else 0
                            y_res = int(parts[5]) if len(parts) > 5 and parts[5] else 0
                            
                            _JOB_CONFIG_CACHE[job_id] = {
                                'copies': copies,
                                'color': color,  # 1=Mono, 2=Colorido
                                'color_mode': 'color' if color > 1 else 'mono',
                                'x_res': x_res,
                                'y_res': y_res
                            }
                            logger.debug(f"[Event 805] JobID={job_id}: copies={copies}, color={color}")
                        except (ValueError, IndexError) as e:
                            logger.debug(f"[Event 805] Erro ao parsear linha: {line} - {e}")
            
            # Limpa cache se muito grande
            if len(_JOB_CONFIG_CACHE) > _JOB_CONFIG_CACHE_MAX_SIZE:
                # Remove os mais antigos (metade do cache)
                oldest_keys = list(_JOB_CONFIG_CACHE.keys())[:_JOB_CONFIG_CACHE_MAX_SIZE // 2]
                for key in oldest_keys:
                    del _JOB_CONFIG_CACHE[key]
            
            logger.info(f"[Event 805] Cache atualizado: {len(_JOB_CONFIG_CACHE)} jobs")
            
    except subprocess.TimeoutExpired:
        logger.warning("[Event 805] Timeout ao buscar eventos")
    except Exception as e:
        logger.debug(f"[Event 805] Erro ao capturar: {e}")
    
    return _JOB_CONFIG_CACHE


def obter_config_job(job_id: int) -> Optional[Dict]:
    """
    Obtém configuração do job do cache do Event 805.
    
    Args:
        job_id: ID do job de impressão
        
    Returns:
        Dict com configurações ou None se não encontrado
    """
    return _JOB_CONFIG_CACHE.get(job_id)


# ============================================================================
# FILA PERSISTENTE DE EVENTOS
# ============================================================================
# Armazena eventos localmente quando o servidor está offline
# Reenvia automaticamente quando a conexão é restaurada
# ============================================================================

class EventQueue:
    """
    Fila persistente de eventos usando SQLite.
    
    Garante que nenhum evento seja perdido quando o servidor está offline.
    Os eventos são armazenados localmente e reenviados quando a conexão é restaurada.
    """
    
    def __init__(self, db_path: str = "event_queue.db"):
        """
        Inicializa a fila de eventos.
        
        Args:
            db_path: Caminho para o banco de dados SQLite
        """
        # Coloca o banco no mesmo diretório do agente
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(script_dir, db_path)
        self.conn = None
        self._init_db()
        
    def _init_db(self):
        """Inicializa o banco de dados e cria a tabela se não existir."""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS pending_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    retry_count INTEGER DEFAULT 0,
                    last_retry TEXT,
                    error_message TEXT
                )
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_pending_created 
                ON pending_events(created_at)
            """)
            self.conn.commit()
            logger.info(f"📦 Fila de eventos inicializada: {self.db_path}")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar fila de eventos: {e}")
    
    def add_event(self, event: Dict) -> bool:
        """
        Adiciona um evento à fila.
        
        Args:
            event: Dicionário com dados do evento
            
        Returns:
            True se adicionado com sucesso
        """
        try:
            event_json = json.dumps(event, ensure_ascii=False)
            self.conn.execute(
                "INSERT INTO pending_events (event_json) VALUES (?)",
                (event_json,)
            )
            self.conn.commit()
            logger.debug(f"📥 Evento adicionado à fila: {event.get('record_number', '?')}")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao adicionar evento à fila: {e}")
            return False
    
    def add_events(self, events: List[Dict]) -> int:
        """
        Adiciona múltiplos eventos à fila.
        
        Args:
            events: Lista de eventos
            
        Returns:
            Número de eventos adicionados
        """
        added = 0
        try:
            for event in events:
                event_json = json.dumps(event, ensure_ascii=False)
                self.conn.execute(
                    "INSERT INTO pending_events (event_json) VALUES (?)",
                    (event_json,)
                )
                added += 1
            self.conn.commit()
            logger.info(f"📥 {added} eventos adicionados à fila")
        except Exception as e:
            logger.error(f"❌ Erro ao adicionar eventos à fila: {e}")
        return added
    
    def get_pending_events(self, limit: int = 50) -> List[Tuple[int, Dict]]:
        """
        Obtém eventos pendentes para envio.
        
        Args:
            limit: Número máximo de eventos a retornar
            
        Returns:
            Lista de tuplas (id, evento)
        """
        events = []
        try:
            cursor = self.conn.execute(
                """SELECT id, event_json FROM pending_events 
                   ORDER BY created_at ASC LIMIT ?""",
                (limit,)
            )
            for row in cursor.fetchall():
                try:
                    event = json.loads(row[1])
                    events.append((row[0], event))
                except json.JSONDecodeError:
                    logger.warning(f"Evento corrompido na fila: ID={row[0]}")
        except Exception as e:
            logger.error(f"❌ Erro ao ler fila de eventos: {e}")
        return events
    
    def remove_event(self, event_id: int) -> bool:
        """
        Remove um evento da fila após envio bem-sucedido.
        
        Args:
            event_id: ID do evento na fila
            
        Returns:
            True se removido com sucesso
        """
        try:
            self.conn.execute(
                "DELETE FROM pending_events WHERE id = ?",
                (event_id,)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao remover evento da fila: {e}")
            return False
    
    def remove_events(self, event_ids: List[int]) -> int:
        """
        Remove múltiplos eventos da fila.
        
        Args:
            event_ids: Lista de IDs dos eventos
            
        Returns:
            Número de eventos removidos
        """
        removed = 0
        try:
            for event_id in event_ids:
                self.conn.execute(
                    "DELETE FROM pending_events WHERE id = ?",
                    (event_id,)
                )
                removed += 1
            self.conn.commit()
        except Exception as e:
            logger.error(f"❌ Erro ao remover eventos da fila: {e}")
        return removed
    
    def update_retry(self, event_id: int, error_message: str = None):
        """
        Atualiza contagem de retry e mensagem de erro.
        
        Args:
            event_id: ID do evento
            error_message: Mensagem de erro opcional
        """
        try:
            self.conn.execute(
                """UPDATE pending_events 
                   SET retry_count = retry_count + 1,
                       last_retry = datetime('now'),
                       error_message = ?
                   WHERE id = ?""",
                (error_message, event_id)
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar retry: {e}")
    
    def get_queue_stats(self) -> Dict:
        """
        Retorna estatísticas da fila.
        
        Returns:
            Dict com estatísticas
        """
        try:
            cursor = self.conn.execute(
                """SELECT 
                    COUNT(*) as total,
                    MIN(created_at) as oldest,
                    MAX(retry_count) as max_retries
                   FROM pending_events"""
            )
            row = cursor.fetchone()
            return {
                "pending_count": row[0] or 0,
                "oldest_event": row[1],
                "max_retries": row[2] or 0
            }
        except Exception as e:
            logger.error(f"❌ Erro ao obter estatísticas da fila: {e}")
            return {"pending_count": 0, "oldest_event": None, "max_retries": 0}
    
    def cleanup_old_events(self, days: int = 7):
        """
        Remove eventos muito antigos da fila.
        
        Args:
            days: Eventos mais antigos que N dias serão removidos
        """
        try:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            cursor = self.conn.execute(
                "DELETE FROM pending_events WHERE created_at < ?",
                (cutoff,)
            )
            removed = cursor.rowcount
            self.conn.commit()
            if removed > 0:
                logger.info(f"🗑️ Removidos {removed} eventos antigos da fila")
        except Exception as e:
            logger.error(f"❌ Erro ao limpar fila: {e}")
    
    def close(self):
        """Fecha a conexão com o banco."""
        if self.conn:
            self.conn.close()


# Instância global da fila de eventos
_event_queue: Optional[EventQueue] = None


def get_event_queue() -> EventQueue:
    """Obtém instância singleton da fila de eventos."""
    global _event_queue
    if _event_queue is None:
        _event_queue = EventQueue()
    return _event_queue


class SpoolInterceptor:
    """Intercepta e analisa jobs na fila de impressão"""
    
    def __init__(self, callback=None):
        """
        Args:
            callback: Função chamada quando um job é interceptado
                     Recebe (printer_name, job_data) como parâmetros
        """
        if not SPOOL_INTERCEPTOR_AVAILABLE:
            raise ImportError("win32print não está disponível")
        
        self.callback = callback
        self.monitoring = False
        self.monitor_thread = None
        self.processed_jobs = set()  # IDs de jobs já processados
        self.monitored_printers = []
        
    def get_all_printers(self) -> List[str]:
        """Lista todas as impressoras disponíveis"""
        printers = []
        try:
            printer_info = win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )
            for printer in printer_info:
                printers.append(printer[2])
        except Exception as e:
            logger.error(f"Erro ao listar impressoras: {e}")
        return printers
    
    def get_printer_jobs(self, printer_name: str) -> List[Dict]:
        """Lista todos os jobs na fila de uma impressora"""
        jobs = []
        handle = None
        
        try:
            handle = win32print.OpenPrinter(printer_name)
            job_info = win32print.EnumJobs(handle, 0, -1, 1)
            
            for job in job_info:
                job_data = {
                    'JobId': job['JobId'],
                    'PrinterName': job['pPrinterName'],
                    'UserName': job['pUserName'],
                    'Document': job['pDocument'],
                    'Status': job['Status'],
                    'TotalPages': job.get('TotalPages', 0),
                    'PagesPrinted': job.get('PagesPrinted', 0),
                    'Submitted': job['Submitted'],
                    'Size': job.get('Size', 0),
                    'Datatype': job.get('pDatatype', ''),
                    'Parameters': job.get('pParameters', ''),
                    'NotifyName': job.get('pNotifyName', ''),
                    'Priority': job.get('Priority', 0),
                    'Position': job.get('Position', 0)
                }
                
                # Converter data para string
                if job_data['Submitted']:
                    try:
                        job_data['Submitted'] = job_data['Submitted'].Format('%Y-%m-%d %H:%M:%S')
                    except:
                        job_data['Submitted'] = str(job_data['Submitted'])
                
                jobs.append(job_data)
                
        except Exception as e:
            logger.error(f"Erro ao listar jobs da impressora {printer_name}: {e}")
        finally:
            if handle:
                win32print.ClosePrinter(handle)
        
        return jobs
    
    def extract_metadata_from_job(self, job: Dict, printer_name: str) -> Dict:
        """Extrai metadados completos de um job"""
        metadata = {
            'job_id': job['JobId'],
            'printer_name': printer_name,
            'user': job['UserName'],
            'document': job['Document'],
            'pages': job['TotalPages'] if job['TotalPages'] > 0 else 1,
            'pages_printed': job['PagesPrinted'],
            'size': job['Size'],
            'submitted': job['Submitted'],
            'status': self._get_status_string(job['Status']),
            'datatype': job['Datatype'],
            'priority': job['Priority'],
            'position': job['Position']
        }
        
        # Extrai informações adicionais dos parâmetros
        if job.get('Parameters'):
            params = job['Parameters'].lower()
            
            # Modo de cor
            if 'color' in params or 'colorido' in params:
                metadata['color_mode'] = 'Color'
            elif 'monochrome' in params or 'monocrom' in params or 'black' in params:
                metadata['color_mode'] = 'Black & White'
            
            # Duplex
            if 'duplex' in params or 'two-sided' in params:
                metadata['duplex'] = 1
            elif 'simplex' in params or 'one-sided' in params:
                metadata['duplex'] = 0
            
            # Tamanho de papel (busca comum)
            paper_sizes = ['a4', 'a3', 'letter', 'legal', 'a5', 'b4', 'b5']
            for size in paper_sizes:
                if size in params:
                    metadata['paper_size'] = size.upper()
                    break
        
        return metadata
    
    def _get_status_string(self, status: int) -> str:
        """Converte código de status para string"""
        status_map = {
            win32print.JOB_STATUS_PAUSED: 'paused',
            win32print.JOB_STATUS_ERROR: 'error',
            win32print.JOB_STATUS_DELETING: 'deleting',
            win32print.JOB_STATUS_SPOOLING: 'spooling',
            win32print.JOB_STATUS_PRINTING: 'printing',
            win32print.JOB_STATUS_OFFLINE: 'offline',
            win32print.JOB_STATUS_PAPEROUT: 'paperout',
            win32print.JOB_STATUS_PRINTED: 'printed',
            win32print.JOB_STATUS_DELETED: 'deleted',
            win32print.JOB_STATUS_BLOCKED_DEVQ: 'blocked',
            win32print.JOB_STATUS_USER_INTERVENTION: 'user_intervention',
            win32print.JOB_STATUS_RESTART: 'restart',
        }
        
        for code, name in status_map.items():
            if status & code:
                return name
        return 'unknown'
    
    def pause_job(self, printer_name: str, job_id: int) -> bool:
        """Pausa um job na fila"""
        handle = None
        try:
            handle = win32print.OpenPrinter(printer_name)
            win32print.SetJob(handle, job_id, 0, None, win32print.JOB_CONTROL_PAUSE)
            logger.info(f"Job {job_id} pausado na impressora {printer_name}")
            return True
        except Exception as e:
            logger.error(f"Erro ao pausar job {job_id}: {e}")
            return False
        finally:
            if handle:
                win32print.ClosePrinter(handle)
    
    def resume_job(self, printer_name: str, job_id: int) -> bool:
        """Retoma um job pausado"""
        handle = None
        try:
            handle = win32print.OpenPrinter(printer_name)
            win32print.SetJob(handle, job_id, 0, None, win32print.JOB_CONTROL_RESUME)
            logger.info(f"Job {job_id} retomado na impressora {printer_name}")
            return True
        except Exception as e:
            logger.error(f"Erro ao retomar job {job_id}: {e}")
            return False
        finally:
            if handle:
                win32print.ClosePrinter(handle)
    
    def cancel_job(self, printer_name: str, job_id: int) -> bool:
        """Cancela um job"""
        handle = None
        try:
            handle = win32print.OpenPrinter(printer_name)
            win32print.SetJob(handle, job_id, 0, None, win32print.JOB_CONTROL_CANCEL)
            logger.info(f"Job {job_id} cancelado na impressora {printer_name}")
            return True
        except Exception as e:
            logger.error(f"Erro ao cancelar job {job_id}: {e}")
            return False
        finally:
            if handle:
                win32print.ClosePrinter(handle)
    
    def monitor_spooler(self, interval: float = 2.0):
        """Monitora o spooler continuamente (deve rodar em thread separada)"""
        self.monitoring = True
        logger.info("Iniciando monitoramento do spooler de impressão")
        
        # Lista todas as impressoras se não especificadas
        if not self.monitored_printers:
            self.monitored_printers = self.get_all_printers()
            logger.info(f"Monitorando {len(self.monitored_printers)} impressoras")
        
        while self.monitoring:
            try:
                for printer_name in self.monitored_printers:
                    jobs = self.get_printer_jobs(printer_name)
                    
                    for job in jobs:
                        job_id = job['JobId']
                        job_key = f"{printer_name}:{job_id}"
                        
                        # Processa apenas jobs novos em spooling
                        if (job_key not in self.processed_jobs and 
                            job['Status'] & win32print.JOB_STATUS_SPOOLING):
                            
                            # Marca como processado
                            self.processed_jobs.add(job_key)
                            
                            # Extrai metadados
                            metadata = self.extract_metadata_from_job(job, printer_name)
                            
                            # Chama callback se fornecido
                            if self.callback:
                                try:
                                    self.callback(printer_name, metadata)
                                except Exception as e:
                                    logger.error(f"Erro no callback: {e}")
                            
                            logger.debug(f"Job interceptado: {printer_name} - {job['Document']} - {metadata['pages']} páginas")
                
            except Exception as e:
                logger.error(f"Erro no monitoramento do spooler: {e}")
            
            time.sleep(interval)
    
    def start_monitoring(self, interval: float = 2.0, daemon: bool = True):
        """Inicia monitoramento em thread separada"""
        if self.monitoring:
            logger.warning("Monitoramento já está ativo")
            return
        
        self.monitor_thread = threading.Thread(
            target=self.monitor_spooler,
            args=(interval,),
            daemon=daemon
        )
        self.monitor_thread.start()
        logger.info("Thread de monitoramento do spooler iniciada")
    
    def stop_monitoring(self):
        """Para o monitoramento"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Monitoramento do spooler parado")


class SNMPValidator:
    """Valida dados de impressão consultando contadores físicos via SNMP"""
    
    # OIDs comuns para impressoras
    OIDS = {
        'total_pages': {
            'hp': '1.3.6.1.2.1.43.10.2.1.4.1.1',  # HP Standard
            'canon': '1.3.6.1.4.1.1602.1.11.1.3.1.4.1',
            'epson': '1.3.6.1.4.1.1248.1.2.2.1.1.1.1.1',
            'generic': '1.3.6.1.2.1.43.10.2.1.4.1.1'  # MIB-II Standard
        },
        'color_pages': {
            'hp': '1.3.6.1.2.1.43.10.2.1.4.1.2',
            'generic': '1.3.6.1.2.1.43.10.2.1.4.1.2'
        },
        'bw_pages': {
            'hp': '1.3.6.1.2.1.43.10.2.1.4.1.3',
            'generic': '1.3.6.1.2.1.43.10.2.1.4.1.3'
        },
        'serial_number': '1.3.6.1.2.1.43.5.1.1.17.1',
        'model': '1.3.6.1.2.1.43.25.3.2.1.3.1',
        'toner_level': '1.3.6.1.2.1.43.11.1.1.9.1.1',
        'status': '1.3.6.1.2.1.43.16.5.1.2.1.1'
    }
    
    def __init__(self, community: str = 'public', timeout: int = 3):
        """
        Args:
            community: SNMP community string (geralmente 'public' ou 'private')
            timeout: Timeout em segundos para consultas SNMP
        """
        self.community = community
        self.timeout = timeout
        self.cache = {}  # Cache de consultas (printer_ip -> dados)
        self.cache_timeout = 300  # 5 minutos
        
        if not SNMP_AVAILABLE:
            logger.warning("SNMP não disponível. Funcionalidades de validação serão limitadas.")
    
    def get_printer_counters(self, printer_ip: str, printer_type: str = 'generic') -> Optional[Dict]:
        """
        Consulta contadores de uma impressora via SNMP
        
        Args:
            printer_ip: IP ou hostname da impressora
            printer_type: Tipo da impressora ('hp', 'canon', 'epson', 'generic')
        
        Returns:
            Dicionário com contadores ou None se não conseguir consultar
        """
        if not SNMP_AVAILABLE:
            return None
        
        # Verifica cache
        cache_key = f"{printer_ip}:{printer_type}"
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if (datetime.now() - cached_time).total_seconds() < self.cache_timeout:
                return cached_data
        
        counters = {
            'printer_ip': printer_ip,
            'timestamp': datetime.now().isoformat(),
            'total_pages': None,
            'color_pages': None,
            'bw_pages': None,
            'serial_number': None,
            'model': None,
            'toner_level': None,
            'status': None
        }
        
        try:
            # Consulta contador total
            total_oid = self.OIDS['total_pages'].get(printer_type, self.OIDS['total_pages']['generic'])
            total = self._snmp_get(printer_ip, total_oid)
            if total is not None:
                counters['total_pages'] = int(total)
            
            # Consulta páginas coloridas
            try:
                color_oid = self.OIDS['color_pages'].get(printer_type, self.OIDS['color_pages'].get('generic'))
                color = self._snmp_get(printer_ip, color_oid)
                if color is not None:
                    counters['color_pages'] = int(color)
            except:
                pass
            
            # Consulta páginas P&B
            try:
                bw_oid = self.OIDS['bw_pages'].get(printer_type, self.OIDS['bw_pages'].get('generic'))
                bw = self._snmp_get(printer_ip, bw_oid)
                if bw is not None:
                    counters['bw_pages'] = int(bw)
            except:
                pass
            
            # Consulta serial number
            try:
                serial = self._snmp_get(printer_ip, self.OIDS['serial_number'])
                if serial:
                    counters['serial_number'] = str(serial)
            except:
                pass
            
            # Consulta modelo
            try:
                model = self._snmp_get(printer_ip, self.OIDS['model'])
                if model:
                    counters['model'] = str(model)
            except:
                pass
            
            # Atualiza cache
            self.cache[cache_key] = (counters, datetime.now())
            
            return counters
            
        except Exception as e:
            logger.error(f"Erro ao consultar SNMP da impressora {printer_ip}: {e}")
            return None
    
    def _snmp_get(self, host: str, oid: str) -> Optional[str]:
        """Executa consulta SNMP GET"""
        if not SNMP_AVAILABLE:
            return None
        
        try:
            for (errorIndication, errorStatus, errorIndex, varBinds) in getCmd(
                SnmpEngine(),
                CommunityData(self.community),
                UdpTransportTarget((host, 161), timeout=self.timeout),
                ContextData(),
                ObjectType(ObjectIdentity(oid)),
                lexicographicMode=False):
                
                if errorIndication:
                    logger.debug(f"SNMP Error Indication: {errorIndication}")
                    return None
                elif errorStatus:
                    logger.debug(f"SNMP Error Status: {errorStatus.prettyPrint()}")
                    return None
                else:
                    for varBind in varBinds:
                        return str(varBind[1])
        except Exception as e:
            logger.debug(f"Erro na consulta SNMP {oid} para {host}: {e}")
        
        return None
    
    def validate_job(self, job_data: Dict, printer_ip: Optional[str] = None) -> Dict:
        """
        Valida um job comparando com contadores SNMP
        
        Args:
            job_data: Dados do job coletados do spool
            printer_ip: IP da impressora (se conhecido)
        
        Returns:
            Dicionário com resultado da validação
        """
        validation_result = {
            'validated': False,
            'discrepancy': False,
            'spool_pages': job_data.get('pages', 0),
            'snmp_total_before': None,
            'snmp_total_after': None,
            'difference': None,
            'message': ''
        }
        
        if not SNMP_AVAILABLE:
            validation_result['message'] = 'SNMP não disponível'
            return validation_result
        
        if not printer_ip:
            # Tenta extrair IP do nome da impressora ou porta
            printer_name = job_data.get('printer_name', '')
            printer_port = job_data.get('printer_port', '')
            
            # Tenta extrair IP de porta de rede (ex: "IP_192.168.1.100")
            if 'IP_' in printer_port:
                printer_ip = printer_port.replace('IP_', '').split(':')[0]
            elif printer_port.startswith('\\\\'):
                # Formato UNC
                printer_ip = printer_port.split('\\')[2] if '\\' in printer_port else None
            else:
                validation_result['message'] = 'IP da impressora não identificado'
                return validation_result
        
        try:
            # Consulta contadores ANTES (se possível)
            counters_before = self.get_printer_counters(printer_ip)
            if counters_before:
                validation_result['snmp_total_before'] = counters_before.get('total_pages')
            
            # Aguarda um pouco para o job processar
            time.sleep(2)
            
            # Consulta contadores DEPOIS
            counters_after = self.get_printer_counters(printer_ip)
            if counters_after:
                validation_result['snmp_total_after'] = counters_after.get('total_pages')
                validation_result['validated'] = True
                
                # Calcula diferença
                if validation_result['snmp_total_before'] and validation_result['snmp_total_after']:
                    snmp_diff = validation_result['snmp_total_after'] - validation_result['snmp_total_before']
                    spool_pages = validation_result['spool_pages']
                    
                    validation_result['difference'] = abs(snmp_diff - spool_pages)
                    
                    # Considera discrepância se diferença > 2 páginas
                    if validation_result['difference'] > 2:
                        validation_result['discrepancy'] = True
                        validation_result['message'] = f'Discrepância detectada: Spool={spool_pages}, SNMP={snmp_diff}, Diferença={validation_result["difference"]}'
                    else:
                        validation_result['message'] = 'Validação OK'
            
        except Exception as e:
            logger.error(f"Erro ao validar job: {e}")
            validation_result['message'] = f'Erro na validação: {str(e)}'
        
        return validation_result
    
    def get_printer_info(self, printer_ip: str) -> Optional[Dict]:
        """Obtém informações gerais da impressora via SNMP"""
        return self.get_printer_counters(printer_ip)
    
    def clear_cache(self):
        """Limpa o cache de consultas SNMP"""
        self.cache.clear()

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "server_url": DEFAULT_SERVER_URL,
    "retry_interval": DEFAULT_RETRY_INTERVAL,
    "check_interval": DEFAULT_CHECK_INTERVAL,
    "max_retries": 3,
    "log_level": "INFO",
    "batch_size": DEFAULT_BATCH_SIZE,
    "process_all_on_start": True,
    "use_wmi_backup": True,
    "use_spool_interceptor": False,
    "use_snmp_validation": False,
    "snmp_community": "public"
}

def load_config() -> dict:
    """Carrega configuração do arquivo JSON ou cria com valores padrão"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # Verifica se todas as chaves necessárias estão presentes
            for key in DEFAULT_CONFIG:
                if key not in config:
                    config[key] = DEFAULT_CONFIG[key]
            return config
        except Exception as e:
            print(f"Erro ao carregar configuração: {e}")
    
    # Cria arquivo de configuração padrão
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
    
    return DEFAULT_CONFIG.copy()

# Carrega configuração
config = load_config()

# Reconfigura logging com as configurações carregadas
log_level = getattr(logging, config.get("log_level", "INFO").upper(), logging.INFO)

# Remove handlers anteriores para reconfigurar
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Configura novamente com o nível correto
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('print_monitor.log', encoding='utf-8'),
        logging.StreamHandler()
    ],
    force=True
)

# Atualiza o logger
logger = logging.getLogger(__name__)
logger.setLevel(log_level)

class PrintMonitor:
    def __init__(self):
        self.server_url = config["server_url"]
        self.retry_interval = config["retry_interval"]
        self.check_interval = config["check_interval"]
        self.max_retries = config["max_retries"]
        self.batch_size = config.get("batch_size", 50)
        self.process_all_on_start = config.get("process_all_on_start", True)
        self.event_handle = None
        # Arquivo para persistir estado (na pasta do agente)
        agent_dir = os.path.dirname(os.path.abspath(__file__))
        self.state_file = os.path.join(agent_dir, "agent_state.json")
        self.highest_record_processed = self.load_last_record()
        
        # Cache para tipos de impressoras (evita consultas repetidas ao servidor)
        # Estrutura: {printer_name: 'duplex' ou 'simplex'}
        self.printer_type_cache = {}
        self.printer_type_cache_max_age = 3600  # 1 hora em segundos
        
        # Sistema híbrido: PowerShell + WMI backup
        self.use_powershell = config.get("use_powershell", True)
        self.use_wmi_backup = config.get("use_wmi_backup", True) and WMI_AVAILABLE
        self.wmi_connection = None
        self.wmi_jobs_seen = set()
        self.event_log_failures = 0
        # Prioridade: PowerShell > WMI > win32evtlog
        self.using_powershell_mode = self.use_powershell
        self.using_wmi_mode = False
        
        # Inicializar interceptador de spool (opcional)
        self.use_spool_interceptor = config.get("use_spool_interceptor", False)
        self.spool_interceptor = None
        if self.use_spool_interceptor and SPOOL_INTERCEPTOR_AVAILABLE:
            try:
                self.spool_interceptor = SpoolInterceptor(callback=self.on_spool_job_intercepted)
                logger.info("SpoolInterceptor inicializado")
            except Exception as e:
                logger.warning(f"Não foi possível inicializar SpoolInterceptor: {e}")
        
        # Inicializar validador SNMP (opcional)
        self.use_snmp_validation = config.get("use_snmp_validation", False)
        self.snmp_validator = None
        if self.use_snmp_validation and SNMP_AVAILABLE:
            try:
                snmp_community = config.get("snmp_community", "public")
                self.snmp_validator = SNMPValidator(community=snmp_community)
                logger.info("SNMPValidator inicializado")
            except Exception as e:
                logger.warning(f"Não foi possível inicializar SNMPValidator: {e}")
    
    def load_last_record(self) -> int:
        """Carrega o último record processado de arquivo"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    last_record = state.get('highest_record_processed', 0)
                    logger.info(f"Estado carregado: último record processado = {last_record}")
                    return last_record
            except Exception as e:
                logger.warning(f"Erro ao carregar estado: {e}")
                # Se houve erro ao carregar, considera como sem estado
                return -1
        # Arquivo não existe = sem estado
        return -1
    
    def has_state(self) -> bool:
        """Verifica se existe estado salvo válido"""
        return self.highest_record_processed >= 0
    
    def save_last_record(self):
        """Salva o último record processado em arquivo"""
        try:
            state = {
                'highest_record_processed': self.highest_record_processed,
                'last_update': datetime.now().isoformat()
            }
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            logger.debug(f"Estado salvo: último record = {self.highest_record_processed}")
        except Exception as e:
            logger.warning(f"Erro ao salvar estado: {e}")
        
    def connect_to_event_log(self) -> bool:
        """Conecta ao log de eventos do Windows"""
        try:
            server = 'localhost'
            self.event_handle = win32evtlog.OpenEventLog(server, EVENT_LOG_OPERATIONAL)
            logger.info("Conectado ao log de eventos do Windows")
            self.event_log_failures = 0  # Reset contador de falhas
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar ao log de eventos: {e}")
            self.event_log_failures += 1
            
            # Se falhar muito, tenta WMI
            if self.event_log_failures >= 3 and self.use_wmi_backup:
                logger.warning("⚠️ Event Log com problemas. Ativando modo WMI backup...")
                self.using_wmi_mode = True
            
            return False
    
    def disconnect_from_event_log(self):
        """Desconecta do log de eventos"""
        if self.event_handle:
            try:
                win32evtlog.CloseEventLog(self.event_handle)
                self.event_handle = None
                logger.info("Desconectado do log de eventos")
            except Exception as e:
                logger.error(f"Erro ao desconectar do log de eventos: {e}")
    
    def parse_event_xml(self, event) -> Optional[Dict]:
        """Tenta parsear os dados do evento para extrair informações estruturadas"""
        try:
            if hasattr(event, 'StringInserts') and event.StringInserts:
                # Estrutura típica do Event 307 do PrintService:
                # StringInserts[0] = Nome da impressora
                # StringInserts[1] = Nome do documento
                # StringInserts[2] = Usuário (pode ser SID ou nome)
                # StringInserts[3] = Número de páginas impressas (pode ser string ou número)
                # StringInserts[4+] = Outras informações (porta, configurações, etc.)
                inserts = [str(s) if s else "" for s in event.StringInserts]
                
                result = {
                    'printer_name': inserts[0].strip() if len(inserts) > 0 and inserts[0] else None,
                    'document_name': inserts[1].strip() if len(inserts) > 1 and inserts[1] else None,
                    'user': inserts[2].strip() if len(inserts) > 2 and inserts[2] else None,
                    'pages': inserts[3] if len(inserts) > 3 and inserts[3] else None,
                    'raw_inserts': inserts
                }
                
                # Tenta converter páginas para número
                if result['pages']:
                    try:
                        # Remove espaços e caracteres não numéricos
                        pages_str = re.sub(r'[^\d]', '', str(result['pages']))
                        if pages_str:
                            result['pages'] = int(pages_str)
                    except (ValueError, TypeError):
                        pass
                
                return result
        except Exception as e:
            logger.debug(f"Erro ao parsear dados do evento: {e}")
        return None
    
    def extract_user_info(self, event) -> str:
        """Extrai informações do usuário do evento com método melhorado"""
        try:
            # Primeiro tenta do XML parseado
            xml_data = self.parse_event_xml(event)
            if xml_data and xml_data.get('user'):
                user = xml_data['user']
                if user and user.strip() and user != "Desconhecido":
                    return user.strip()
            
            # Tenta extrair o nome do usuário das StringInserts
            if hasattr(event, 'StringInserts') and event.StringInserts:
                inserts = [str(s) for s in event.StringInserts if s]
                # Procura por padrões de usuário
                for insert in inserts:
                    if insert and '\\' in str(insert):  # Formato DOMAIN\username
                        return str(insert).strip()
                    # Verifica se parece um nome de usuário (não é caminho, não é número, etc)
                    if insert and '@' not in str(insert) and len(str(insert)) > 2:
                        if '\\' not in str(insert) and not str(insert).isdigit():
                            # Pode ser apenas o nome do usuário
                            potential_user = str(insert).strip()
                            if potential_user and potential_user != "Desconhecido":
                                return potential_user
            
            # Se não encontrar, tenta usar o SID
            if hasattr(event, 'Sid') and event.Sid:
                return str(event.Sid)
                
        except Exception as e:
            logger.debug(f"Erro ao extrair usuário: {e}")
        
        return "Desconhecido"
    
    def extract_document_info(self, event) -> tuple:
        """Extrai nome do documento e número de páginas com método melhorado"""
        document_name = "Documento sem nome"
        pages = 1
        
        try:
            # Primeiro tenta do XML parseado
            xml_data = self.parse_event_xml(event)
            if xml_data:
                if xml_data.get('document_name'):
                    doc = xml_data['document_name'].strip()
                    if doc and doc != "Desconhecido":
                        document_name = doc
                
                if xml_data.get('pages'):
                    try:
                        pages = int(xml_data['pages'])
                    except (ValueError, TypeError):
                        pass
            
            if hasattr(event, 'StringInserts') and event.StringInserts:
                inserts = [str(s) for s in event.StringInserts if s]
                
                # Concatena todas as strings para buscar informações
                full_message = " ".join(inserts)
                
                # Análise mais inteligente dos StringInserts
                # Estrutura típica: [Impressora, Documento, Usuário, Páginas, ...]
                for idx, insert in enumerate(inserts):
                    if not insert or len(str(insert).strip()) < 2:
                        continue
                    
                    insert_str = str(insert).strip()
                    
                    # Tenta identificar nome do documento
                    # Geralmente é o segundo StringInsert (índice 1) e não contém caminhos
                    if idx == 1 and '\\' not in insert_str and not insert_str.isdigit():
                        if len(insert_str) > 1 and insert_str not in ["Desconhecido", "Unknown"]:
                            document_name = insert_str
                    
                    # Tenta identificar número de páginas
                    # Pode estar em formato "X páginas" ou apenas o número
                    if insert_str.isdigit() and int(insert_str) > 0 and int(insert_str) < 10000:
                        # Se for um número razoável, pode ser páginas
                        if idx >= 2:  # Geralmente após impressora e documento
                            pages = int(insert_str)
                
                # Busca número de páginas com padrões regex (fallback)
                if pages == 1:  # Se ainda não encontrou
                    patterns = [
                        r"Pages printed:\s*(\d+)",
                        r"Páginas impressas:\s*(\d+)",
                        r"(\d+)\s+pages?",
                        r"(\d+)\s+página",
                        r"página[ns]?[:\s]+(\d+)",
                        r"page[ns]?[:\s]+(\d+)"
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, full_message, re.IGNORECASE)
                        if match:
                            try:
                                pages = int(match.group(1))
                                if pages > 0 and pages < 10000:
                                    break
                            except (ValueError, IndexError):
                                continue
                        
        except Exception as e:
            logger.debug(f"Erro ao extrair informações do documento: {e}")
        
        return document_name, pages
    
    def extract_printer_info(self, event) -> Dict:
        """Extrai informações detalhadas da impressora"""
        printer_info = {
            'printer_name': None,
            'printer_port': None,
            'printer_driver': None,
            'paper_type': None,
            'paper_size': None,
            'color_mode': None,
            'duplex': None
        }
        
        try:
            # Tenta do XML parseado
            xml_data = self.parse_event_xml(event)
            if xml_data and xml_data.get('printer_name'):
                printer_info['printer_name'] = xml_data['printer_name'].strip()
            
            if hasattr(event, 'StringInserts') and event.StringInserts:
                inserts = [str(s) for s in event.StringInserts if s]
                full_message = " ".join(inserts).lower()
                
                # Primeiro StringInsert geralmente é o nome da impressora
                if len(inserts) > 0:
                    printer_name = str(inserts[0]).strip()
                    if printer_name and printer_name != "Desconhecido":
                        printer_info['printer_name'] = printer_name
                
                # Tenta extrair informações adicionais da mensagem
                # Porta da impressora (geralmente contém "on", "via", "port")
                port_patterns = [
                    r"on\s+([A-Z0-9_\\]+)",
                    r"via\s+([A-Z0-9_\\]+)",
                    r"port[:\s]+([A-Z0-9_\\]+)",
                    r"porta[:\s]+([A-Z0-9_\\]+)"
                ]
                for pattern in port_patterns:
                    match = re.search(pattern, full_message, re.IGNORECASE)
                    if match:
                        printer_info['printer_port'] = match.group(1).strip()
                        break
                
                # Modo de cor
                if re.search(r'color|colorido|colour', full_message, re.IGNORECASE):
                    printer_info['color_mode'] = 'Color'
                elif re.search(r'black|preto|monochrome|monocromático|grayscale|escala', full_message, re.IGNORECASE):
                    printer_info['color_mode'] = 'Black & White'
                
                # Duplex
                if re.search(r'duplex|frente e verso|two.sided', full_message, re.IGNORECASE):
                    printer_info['duplex'] = True
                elif re.search(r'simplex|one.sided|frente', full_message, re.IGNORECASE):
                    printer_info['duplex'] = False
                
                # Tipo de papel
                paper_types = ['A4', 'A3', 'Letter', 'Legal', 'A5', 'B4', 'B5']
                for paper_type in paper_types:
                    if re.search(rf'\b{paper_type}\b', full_message, re.IGNORECASE):
                        printer_info['paper_size'] = paper_type
                        break
                
        except Exception as e:
            logger.debug(f"Erro ao extrair informações da impressora: {e}")
        
        return printer_info
    
    def process_event(self, event) -> Optional[Dict]:
        """Processa um evento individual de impressão com extração melhorada"""
        try:
            record_number = getattr(event, 'RecordNumber', 0)
            
            # Formatar data no padrão ISO
            date_str = event.TimeGenerated.Format('%Y-%m-%d %H:%M:%S')
            
            # Extrai informações básicas do evento
            user = self.extract_user_info(event)
            machine = event.ComputerName if hasattr(event, 'ComputerName') and event.ComputerName else obter_nome_maquina()
            document_name, pages = self.extract_document_info(event)
            
            # Extrai informações detalhadas da impressora
            printer_info = self.extract_printer_info(event)
            
            # Validação de páginas
            if pages < 1 or pages > 10000:
                pages = 1
            
            # Normaliza duplex para int (0/1)
            duplex_raw = printer_info.get('duplex')
            if duplex_raw is None:
                duplex = 0  # Default: simplex
            elif isinstance(duplex_raw, bool):
                duplex = 1 if duplex_raw else 0
            elif isinstance(duplex_raw, int):
                duplex = 1 if duplex_raw else 0
            elif isinstance(duplex_raw, str):
                duplex = 1 if duplex_raw.lower() in ('duplex', 'true', '1', 'yes') else 0
            else:
                duplex = 0
            
            # Normaliza color_mode para formato do servidor
            color_mode_raw = printer_info.get('color_mode')
            if color_mode_raw:
                if isinstance(color_mode_raw, str):
                    if color_mode_raw.lower() in ('color', 'colorido', 'colour'):
                        color_mode = 'Color'
                    else:
                        color_mode = 'Black & White'
                else:
                    color_mode = 'Color' if color_mode_raw else 'Black & White'
            else:
                color_mode = None
            
            # Monta objeto de evento completo
            event_data = {
                "record_number": record_number,
                "date": date_str,
                "user": user,
                "machine": machine,
                "document": document_name,
                "pages": pages,
                "event_id": event.EventID,
                # Informações adicionais da impressora
                "printer_name": printer_info.get('printer_name'),
                "printer_port": printer_info.get('printer_port'),
                "color_mode": color_mode,  # Normalizado: 'Color' ou 'Black & White'
                "paper_size": printer_info.get('paper_size'),
                "duplex": duplex,  # Normalizado: 0 ou 1
                "copies": 1,  # Event Log não fornece cópias, assume 1
                # Campos adicionais (podem ser preenchidos por interceptador)
                "job_id": None,
                "job_status": None,
                "file_size": None,
                "source_ip": None,
                "application": None
            }
            
            logger.debug(f"Evento processado: ID={record_number}, User={user}, Doc={document_name}, Pages={pages}, Printer={printer_info.get('printer_name', 'N/A')}")
            return event_data
            
        except Exception as e:
            logger.error(f"Erro ao processar evento: {e}", exc_info=True)
            return None
    
    def on_spool_job_intercepted(self, printer_name: str, job_metadata: Dict):
        """Callback chamado quando um job é interceptado no spooler"""
        try:
            # Normaliza color_mode para formato do servidor
            color_mode_raw = job_metadata.get('color_mode')
            if color_mode_raw:
                if isinstance(color_mode_raw, str):
                    if color_mode_raw.lower() in ('color', 'colorido', 'colour'):
                        color_mode = 'Color'
                    else:
                        color_mode = 'Black & White'
                else:
                    color_mode = 'Color' if color_mode_raw else 'Black & White'
            else:
                color_mode = None
            
            # Normaliza duplex para int (0/1)
            duplex_raw = job_metadata.get('duplex', 0)
            if isinstance(duplex_raw, bool):
                duplex = 1 if duplex_raw else 0
            elif isinstance(duplex_raw, str):
                duplex = 1 if duplex_raw.lower() in ('duplex', 'true', '1', 'yes') else 0
            else:
                duplex = 1 if duplex_raw else 0
            
            # Calcula folhas físicas
            pages = job_metadata.get('pages', 1)
            copies = job_metadata.get('copies', 1)
            tipo_impressora = "duplex" if duplex == 1 else "simplex"
            folhas = calcular_folhas_fisicas(pages, tipo_impressora, copies)
            
            # Adiciona informações do spool ao evento
            event_data = {
                "date": job_metadata.get('submitted', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                "user": job_metadata.get('user', 'Unknown'),
                "machine": obter_nome_maquina(),
                "document": job_metadata.get('document', 'Unknown'),
                "pages": pages,
                "printer_name": printer_name,
                "printer_port": job_metadata.get('datatype', ''),
                "color_mode": color_mode,  # Normalizado: 'Color' ou 'Black & White'
                "paper_size": job_metadata.get('paper_size'),
                "duplex": duplex,  # Normalizado: 0 ou 1
                "copies": copies,  # Adiciona campo copies
                "job_id": str(job_metadata.get('job_id', '')),
                "job_status": job_metadata.get('status', 'unknown'),
                "file_size": job_metadata.get('size', 0),
                "source_ip": None,
                "application": None,
                "sheets_used": folhas  # Folhas físicas calculadas
            }
            
            # Validação SNMP se habilitada
            if self.snmp_validator:
                validation_result = self.snmp_validator.validate_job(event_data)
                if validation_result.get('validated'):
                    event_data['snmp_validated'] = 1
                    event_data['snmp_total_before'] = validation_result.get('snmp_total_before')
                    event_data['snmp_total_after'] = validation_result.get('snmp_total_after')
                    event_data['snmp_difference'] = validation_result.get('difference')
                    event_data['validation_message'] = validation_result.get('message')
            
            # Envia evento para servidor
            self.send_events([event_data])
            
        except Exception as e:
            logger.error(f"Erro ao processar job interceptado: {e}", exc_info=True)
    
    def send_events(self, events: List[Dict], force_insert: bool = False) -> bool:
        """
        Envia eventos para o servidor com retry automático
        
        Args:
            events: Lista de eventos para enviar
            force_insert: Se True, adiciona flag para forçar inserção no servidor (ignora duplicatas)
        """
        if not events:
            return True
        
        # Remove duplicatas baseado em record_number antes de enviar
        # (o servidor também verifica, mas é melhor evitar enviar duplicatas)
        seen_record_ids = set()
        events_to_send = []
        
        for event in events:
            record_id = event.get('record_number')
            
            # Se não tem record_number, envia mesmo assim (servidor vai gerenciar)
            if record_id is None:
                event_copy = event.copy()
                # Mantém record_number se existir, senão None
                if force_insert:
                    event_copy['force_insert'] = True
                events_to_send.append(event_copy)
            elif record_id not in seen_record_ids:
                seen_record_ids.add(record_id)
                event_copy = event.copy()
                # Mantém record_number para o servidor usar na prevenção de duplicatas
                if force_insert:
                    event_copy['force_insert'] = True
                events_to_send.append(event_copy)
        
        if not events_to_send:
            logger.debug("Todos os eventos eram duplicados, nada para enviar")
            return True
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.server_url, 
                    json={"events": events_to_send},
                    timeout=30,
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    inserted = result.get('inserted', 0)
                    skipped = result.get('skipped', 0)
                    logger.info(f"✅ {len(events_to_send)} eventos enviados: {inserted} inseridos, {skipped} ignorados (duplicatas)")
                    
                    # Atualiza o maior record processado (usa events_to_send que já foi filtrado)
                    for event in events_to_send:
                        record_id = event.get('record_number')
                        if record_id is not None and record_id > self.highest_record_processed:
                            self.highest_record_processed = record_id
                    # Salva estado após envio bem-sucedido
                    if events_to_send:
                        self.save_last_record()
                    
                    return True
                else:
                    logger.error(f"❌ Erro HTTP {response.status_code}: {response.text}")
                    
            except requests.exceptions.ConnectionError:
                logger.warning(f"⚠️ Tentativa {attempt + 1}: Servidor indisponível")
            except requests.exceptions.Timeout:
                logger.warning(f"⚠️ Tentativa {attempt + 1}: Timeout na requisição")
            except Exception as e:
                logger.error(f"❌ Erro na tentativa {attempt + 1}: {e}")
            
            if attempt < self.max_retries - 1:
                # Backoff exponencial: 5s, 10s, 20s...
                wait_time = 5 * (2 ** attempt)
                time.sleep(min(wait_time, 60))  # Máximo 60s
        
        # MELHORIA: Salva na fila local quando servidor offline
        logger.error(f"❌ Falha ao enviar {len(events_to_send)} eventos após {self.max_retries} tentativas")
        logger.info(f"📦 Salvando {len(events_to_send)} eventos na fila local...")
        
        queue = get_event_queue()
        added = queue.add_events(events_to_send)
        if added > 0:
            logger.info(f"✅ {added} eventos salvos na fila local para reenvio posterior")
        
        return False
    
    def read_all_events(self, force_all: bool = False) -> List[Dict]:
        """
        Lê TODOS os eventos 307 do log (independente de já processados)
        
        Args:
            force_all: Se True, ignora highest_record_processed e lê todos os eventos
        """
        if not self.event_handle:
            return []
        
        all_events = []
        
        try:
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            
            # Usa um contador para evitar loops infinitos
            max_iterations = 1000
            iteration = 0
            
            while iteration < max_iterations:
                events = win32evtlog.ReadEventLog(self.event_handle, flags, 0)
                if not events:
                    break
                
                for event in events:
                    if event.EventID == EVENT_ID_PRINT:
                        # Se force_all=False e temos estado válido, pula eventos já processados
                        # IMPORTANTE: highest_record_processed = -1 significa sem estado, então processa tudo
                        if not force_all and self.has_state() and self.highest_record_processed >= 0:
                            record_num = getattr(event, 'RecordNumber', 0)
                            if record_num <= self.highest_record_processed:
                                continue
                        
                        processed_event = self.process_event(event)
                        if processed_event:
                            all_events.append(processed_event)
                
                # Mostra progresso
                if len(all_events) % 100 == 0 and len(all_events) > 0:
                    logger.info(f"📊 Processados {len(all_events)} eventos até agora...")
                
                iteration += 1
            
            # Ordena por record_number para processar na ordem correta
            all_events.sort(key=lambda x: x['record_number'])
            logger.info(f"📊 Total de {len(all_events)} eventos 307 encontrados no log")
            
        except Exception as e:
            logger.error(f"Erro ao ler todos os eventos: {e}")
        
        return all_events
    
    def get_printer_type(self, printer_name: str) -> str:
        """
        Busca o tipo da impressora (duplex/simplex) no servidor.
        Usa cache para evitar consultas repetidas.
        
        Args:
            printer_name: Nome da impressora
        
        Returns:
            "duplex" ou "simplex" (padrão: "simplex" se não encontrado)
        """
        if not printer_name or printer_name == "Unknown":
            return "simplex"
        
        # Verifica cache primeiro
        if printer_name in self.printer_type_cache:
            return self.printer_type_cache[printer_name]
        
        # Busca no servidor
        try:
            # Monta URL da API do servidor
            api_url = self.server_url.replace("/api/print_events", "/api/printer_type")
            api_url = f"{api_url}?printer_name={requests.utils.quote(printer_name)}"
            
            response = requests.get(api_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                tipo = data.get('tipo', 'simplex')
                # Armazena no cache
                self.printer_type_cache[printer_name] = tipo
                logger.debug(f"[API] Tipo da impressora '{printer_name}': {tipo}")
                return tipo
            else:
                logger.debug(f"[API] Impressora '{printer_name}' não encontrada no servidor, assumindo 'simplex'")
                # Armazena no cache como simplex (evita consultas repetidas)
                self.printer_type_cache[printer_name] = "simplex"
                return "simplex"
                
        except Exception as e:
            logger.warning(f"[API] Erro ao buscar tipo da impressora '{printer_name}': {e}. Assumindo 'simplex'")
            # Armazena no cache como simplex
            self.printer_type_cache[printer_name] = "simplex"
            return "simplex"
    
    def read_new_events_powershell(self) -> List[Dict]:
        """Lê eventos usando Get-WinEvent via PowerShell (método mais confiável)"""
        new_events = []
        
        try:
            # Busca eventos ID 307 recentes (impressão concluída)
            minutos_busca = 60 if self.highest_record_processed == 0 else 10
            
            ps_command = f"""
            Get-WinEvent -FilterHashtable @{{
                LogName='{EVENT_LOG_OPERATIONAL}'
                ID={EVENT_ID_PRINT}
                StartTime=(Get-Date).AddMinutes(-{minutos_busca})
            }} -MaxEvents 100 -ErrorAction SilentlyContinue | 
            Select-Object RecordId, TimeCreated, Message, Properties | 
            ConvertTo-Json -Depth 5
            """
            
            # Executa PowerShell
            result = subprocess.run(
                ['powershell', '-Command', ps_command],
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW  # Não mostra janela
            )
            
            if result.returncode != 0:
                logger.debug(f"PowerShell retornou código {result.returncode}")
                return []
            
            if not result.stdout or result.stdout.strip() == '':
                logger.debug("PowerShell não retornou eventos")
                return []
            
            # Parse JSON
            try:
                import json as json_lib
                eventos_ps = json_lib.loads(result.stdout)
                
                # Se retornou apenas 1 evento, PowerShell retorna objeto, não array
                if isinstance(eventos_ps, dict):
                    eventos_ps = [eventos_ps]
                elif not isinstance(eventos_ps, list):
                    logger.warning(f"[PowerShell] Formato inesperado retornado: {type(eventos_ps)}")
                    eventos_ps = []
            except json.JSONDecodeError as e:
                logger.error(f"[PowerShell] Erro ao parsear JSON: {e}")
                logger.debug(f"[PowerShell] Saída recebida: {result.stdout[:200]}...")
                return []
            except Exception as e:
                logger.error(f"[PowerShell] Erro inesperado ao processar resposta: {e}")
                return []
            
            logger.debug(f"[PowerShell] Get-WinEvent retornou {len(eventos_ps)} eventos")
            logger.debug(f"[PowerShell] highest_record_processed atual: {self.highest_record_processed}")
            
            # MELHORIA: Captura Event 805 para obter configurações reais do job
            capturar_event_805(minutos_busca)
            
            # Processa cada evento
            for evento_ps in eventos_ps:
                record_id = evento_ps.get('RecordId', 0)
                
                logger.debug(f"[PowerShell] Verificando RecordID {record_id} vs {self.highest_record_processed}")
                
                # Só processa se for novo
                if record_id > self.highest_record_processed:
                    # Parse do Event 307 conforme especificação
                    # Event 307 Properties:
                    # Properties[0] = Param1 = JobID/DocumentID
                    # Properties[1] = Param2 = Nome do documento
                    # Properties[2] = Param3 = Usuário
                    # Properties[3] = Param4 = Computador
                    # Properties[4] = Param5 = Nome da impressora
                    # Properties[5] = Param6 = Porta/Caminho
                    # Properties[6] = Param7 = Tamanho em bytes
                    # Properties[7] = Param8 = Número total de páginas impressas
                    
                    message = evento_ps.get('Message', '')
                    time_created = evento_ps.get('TimeCreated', '')
                    properties = evento_ps.get('Properties', [])
                    
                    # Extrai Params das Properties (usa função auxiliar para tratar objetos {'Value': '...'})
                    props_list = [extrair_valor_property(p) for p in properties] if properties else []
                    
                    # Param1 = JobID (DocumentID)
                    job_id = props_list[0] if len(props_list) > 0 and props_list[0].isdigit() else None
                    if not job_id:
                        # Fallback: tenta extrair da mensagem
                        job_match = re.search(r'O documento (\d+)', message, re.IGNORECASE)
                        if job_match:
                            job_id = job_match.group(1)
                    
                    # Param2 = Nome do documento
                    document = props_list[1].strip() if len(props_list) > 1 and props_list[1] else "Unknown"
                    
                    # Param3 = Usuário
                    user = props_list[2].strip() if len(props_list) > 2 and props_list[2] else "Unknown"
                    
                    # Param4 = Computador
                    machine = props_list[3].replace('\\', '').replace('\\\\', '').strip() if len(props_list) > 3 and props_list[3] else obter_nome_maquina()
                    
                    # Param5 = Nome da impressora
                    printer_name = props_list[4].strip() if len(props_list) > 4 and props_list[4] else "Unknown"
                    
                    # Param6 = Porta/Caminho
                    printer_port = props_list[5].strip() if len(props_list) > 5 and props_list[5] else None
                    
                    # Param7 = Tamanho em bytes
                    file_size = None
                    if len(props_list) > 6 and props_list[6]:
                        try:
                            file_size = int(re.sub(r'[^\d]', '', props_list[6]))
                        except (ValueError, TypeError):
                            pass
                    
                    # Param8 = Número total de páginas impressas (IMPORTANTE!)
                    pages = None
                    if len(props_list) > 7 and props_list[7]:
                        try:
                            pages = int(re.sub(r'[^\d]', '', props_list[7]))
                        except (ValueError, TypeError):
                            pass
                    
                    # Fallback: tenta extrair páginas da mensagem se não encontrou em Properties[7]
                    if pages is None or pages < 1:
                        pages_match = re.search(r'P[áa]ginas impressas:\s*(\d+)|Pages printed:\s*(\d+)', message, re.IGNORECASE)
                        if pages_match:
                            try:
                                pages = int(pages_match.group(1) or pages_match.group(2))
                            except (ValueError, IndexError):
                                pass
                    
                    # Validação de páginas
                    if pages is None or pages < 1:
                        pages = 1
                    elif pages > 10000:
                        logger.warning(f"[Event 307] Número de páginas inválido ({pages}) para RecordID={record_id}, usando 1")
                        pages = 1
                    
                    # MELHORIA: Busca configuração real do job via Event 805
                    job_config = None
                    copies = 1
                    color_mode = None
                    if job_id:
                        try:
                            job_config = obter_config_job(int(job_id))
                        except (ValueError, TypeError):
                            pass
                    
                    if job_config:
                        # Usa dados reais do Event 805
                        copies = job_config.get('copies', 1)
                        color_mode_raw = job_config.get('color_mode')  # 'mono' ou 'color'
                        # Normaliza color_mode para formato do servidor: 'Color' ou 'Black & White'
                        if color_mode_raw:
                            if color_mode_raw.lower() in ('color', 'colorido', 'colour'):
                                color_mode = 'Color'
                            else:
                                color_mode = 'Black & White'
                        else:
                            color_mode = None
                        logger.debug(f"[Event 805] Configuração do Job {job_id}: copies={copies}, color={color_mode}")
                    
                    # Busca tipo da impressora no servidor (duplex/simplex)
                    tipo_impressora = self.get_printer_type(printer_name)
                    # Garante que tipo_impressora é uma string válida
                    if not tipo_impressora or not isinstance(tipo_impressora, str):
                        tipo_impressora = "simplex"
                    
                    # Calcula folhas físicas usando função auxiliar
                    # NOTA: pages do Event 307 = páginas por cópia
                    # copies do Event 805 = número real de cópias configuradas
                    # Cálculo: folhas = calcular_folhas_fisicas(pages, tipo_impressora, copies)
                    folhas = calcular_folhas_fisicas(pages, tipo_impressora, copies)
                    
                    logger.info(f"[CALCULO] Job {job_id}: {pages} páginas, copies={copies}, tipo={tipo_impressora} -> {folhas} folhas físicas")
                    
                    # Converte data
                    try:
                        if '/Date(' in time_created:
                            timestamp_match = re.search(r'/Date\((\d+)\)/', time_created)
                            if timestamp_match:
                                timestamp_ms = int(timestamp_match.group(1))
                                date_str = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')
                            else:
                                date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            date_str = datetime.fromisoformat(time_created.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
                    except Exception as e:
                        logger.debug(f"Erro ao converter data {time_created}: {e}")
                        date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Formata conforme esperado pelo servidor (campos em inglês)
                    event_data = {
                        "record_number": record_id,
                        "user": user,                    # Nome do usuário
                        "machine": machine,              # Nome do computador
                        "date": date_str,                # Data/hora do evento
                        "pages": pages,                  # Número de páginas (lógicas)
                        "printer_name": printer_name,    # Nome da impressora
                        "document": document,            # Nome do documento
                        "printer_port": printer_port,    # Porta/caminho da impressora
                        "job_id": job_id,                # ID do job
                        "duplex": 1 if tipo_impressora.lower() == "duplex" else 0,  # 1=duplex, 0=simplex
                        "file_size": file_size,          # Tamanho em bytes
                        "event_id": EVENT_ID_PRINT,      # ID do evento (307)
                        # NOVOS CAMPOS do Event 805 (se disponível)
                        "copies": copies,                # Cópias reais do Event 805
                        "color_mode": color_mode,        # Modo de cor ('Color' ou 'Black & White')
                        "sheets_used": folhas            # Folhas físicas calculadas (enviado para o servidor)
                    }
                    
                    new_events.append(event_data)
                    color_info = f", Color={color_mode}" if color_mode else ""
                    logger.info(f"[Event 307] Capturado: JobID={job_id}, User={user}, Pages={pages}, Copies={copies}, Folhas={folhas}, Tipo={tipo_impressora}{color_info}")
                else:
                    logger.debug(f"[PowerShell] Evento RecordID={record_id} JÁ PROCESSADO (highest={self.highest_record_processed})")
            
            # Atualiza highest_record_processed se houver novos eventos
            if new_events:
                max_record = max(e.get('record_number', 0) for e in new_events)
                if max_record > self.highest_record_processed:
                    self.highest_record_processed = max_record
                    self.save_last_record()
                logger.info(f"[PowerShell] Capturados {len(new_events)} eventos via Get-WinEvent")
            else:
                logger.debug(f"[PowerShell] Nenhum evento novo (highest_record_processed={self.highest_record_processed})")
        
        except subprocess.TimeoutExpired:
            logger.error("Timeout ao executar PowerShell")
        except Exception as e:
            logger.error(f"Erro ao ler eventos via PowerShell: {e}", exc_info=True)
        
        return new_events
    
    def read_new_events_wmi(self) -> List[Dict]:
        """Lê eventos usando WMI (método backup)"""
        if not WMI_AVAILABLE:
            return []
        
        new_events = []
        
        try:
            # Conecta ao WMI se necessário
            if not self.wmi_connection:
                self.wmi_connection = wmi.WMI()
                logger.info("🔄 Conectado ao WMI para monitoramento backup")
            
            # Lista jobs na fila
            for job in self.wmi_connection.Win32_PrintJob():
                job_key = f"{job.JobId}_{job.Document}"
                
                # Se é um job novo
                if job_key not in self.wmi_jobs_seen:
                    self.wmi_jobs_seen.add(job_key)
                    
                    # Extrai informações do job
                    # WMI não fornece todas as informações, então usa valores default
                    event_data = {
                        "record_number": 0,  # WMI não tem RecordNumber
                        "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "user": job.Owner if hasattr(job, 'Owner') and job.Owner else "Unknown",
                        "machine": obter_nome_maquina(),
                        "document": job.Document if hasattr(job, 'Document') else "Unknown",
                        "pages": job.TotalPages if hasattr(job, 'TotalPages') and job.TotalPages else 1,
                        "event_id": EVENT_ID_PRINT,
                        "printer_name": job.Name.split(',')[0] if hasattr(job, 'Name') and ',' in job.Name else "Unknown",
                        "printer_port": None,
                        "color_mode": None,  # WMI não fornece modo de cor
                        "paper_size": None,
                        "duplex": 0,  # WMI não fornece duplex, assume simplex (0)
                        "copies": 1,  # WMI não fornece cópias, assume 1
                        "job_id": str(job.JobId) if hasattr(job, 'JobId') else None,
                        "job_status": job.Status if hasattr(job, 'Status') else None,
                        "file_size": None,
                        "source_ip": None,
                        "application": None
                    }
                    
                    new_events.append(event_data)
                    logger.debug(f"[WMI] Job capturado: {job.Document} - {job.TotalPages} páginas")
            
            # Limpa jobs antigos do set (mantém últimos 1000)
            if len(self.wmi_jobs_seen) > 1000:
                self.wmi_jobs_seen = set(list(self.wmi_jobs_seen)[-500:])
        
        except Exception as e:
            logger.error(f"Erro ao ler eventos via WMI: {e}")
        
        return new_events
    
    def read_new_events(self) -> List[Dict]:
        """Lê apenas eventos novos (após o último processado)"""
        # PRIORIDADE 1: PowerShell Get-WinEvent (mais confiável)
        if self.using_powershell_mode:
            eventos = self.read_new_events_powershell()
            if eventos:
                return eventos
            # Se PowerShell falhar, tenta WMI
            logger.warning("PowerShell não retornou eventos, tentando WMI...")
            if self.use_wmi_backup:
                return self.read_new_events_wmi()
        
        # PRIORIDADE 2: WMI (se PowerShell desabilitado)
        if self.using_wmi_mode:
            return self.read_new_events_wmi()
        
        # PRIORIDADE 3: win32evtlog (fallback - conhecido por não funcionar bem)
        if not self.event_handle:
            # Tenta WMI como fallback
            if self.use_wmi_backup:
                logger.warning("Event Log não disponível, usando WMI backup")
                return self.read_new_events_wmi()
            return []
        
        new_events = []
        
        try:
            # CORREÇÃO: Lê eventos BACKWARDS (do mais recente para o mais antigo)
            # Isso garante que encontramos os eventos mais novos primeiro
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            
            # Lê um lote de eventos recentes
            max_events_per_read = 200  # Aumentado para capturar mais eventos
            events_read = 0
            found_new = False
            max_new_record = self.highest_record_processed  # Inicializa com o valor atual
            
            while True:
                events = win32evtlog.ReadEventLog(self.event_handle, flags, max_events_per_read)
                if not events:
                    break
                
                events_read += len(events)
                
                # Processa eventos na ordem (do mais recente para o mais antigo)
                for event in events:
                    if event.EventID == EVENT_ID_PRINT:
                        # Verifica se é um evento novo
                        is_new = event.RecordNumber > self.highest_record_processed
                        if is_new:
                            found_new = True
                            processed_event = self.process_event(event)
                            if processed_event:
                                new_events.append(processed_event)
                                # Atualiza o maior record encontrado
                                if event.RecordNumber > max_new_record:
                                    max_new_record = event.RecordNumber
                                logger.debug(f"Novo evento capturado: RecordNumber={event.RecordNumber}, User={processed_event.get('user', 'N/A')}")
                        else:
                            # Se encontrou um evento já processado, pode parar
                            # (já que está lendo BACKWARDS, os próximos serão ainda mais antigos)
                            if found_new:
                                break
                
                # Se já encontrou eventos novos e passou do highest_record, pode parar
                if found_new and max_new_record > self.highest_record_processed:
                    # Continua lendo um pouco mais para garantir que não perde nada
                    # Mas para se já leu muitos eventos
                    if events_read >= max_events_per_read:
                        break
                
                # Limita leitura total para não travar
                if events_read >= 1000:
                    logger.debug(f"Lidos {events_read} eventos, parando para evitar sobrecarga")
                    break
                
                # Se não encontrou nenhum evento novo e já leu muitos, para
                if not found_new and events_read >= max_events_per_read:
                    break
            
            # Atualiza highest_record_processed com o maior encontrado
            if new_events:
                self.highest_record_processed = max_new_record
                self.save_last_record()  # Salva estado
                logger.info(f"Capturados {len(new_events)} novos eventos (RecordNumbers: {min(e.get('record_number', 0) for e in new_events)}-{max(e.get('record_number', 0) for e in new_events)})")
                logger.debug(f"Ultimo record processado atualizado para: {self.highest_record_processed}")
            else:
                logger.debug(f"Nenhum evento novo encontrado (ultimo processado: {self.highest_record_processed})")
            
        except Exception as e:
            logger.error(f"Erro ao ler novos eventos: {e}", exc_info=True)
            self.event_log_failures += 1
            
            # Se falhou muito, tenta WMI
            if self.event_log_failures >= 5 and self.use_wmi_backup and not self.using_wmi_mode:
                logger.warning("⚠️ Muitas falhas no Event Log. Mudando para modo WMI...")
                self.using_wmi_mode = True
                # Tenta ler via WMI
                return self.read_new_events_wmi()
        
        return new_events
    
    def process_events_batch(self, events: List[Dict], force_insert: bool = False):
        """
        Processa eventos em lotes
        
        Args:
            events: Lista de eventos para processar
            force_insert: Se True, força inserção mesmo que sejam duplicatas (útil para sincronização completa)
        """
        total_events = len(events)
        
        if total_events == 0:
            logger.info("Nenhum evento para processar")
            return
        
        logger.info(f"🚀 Iniciando processamento de {total_events} eventos em lotes de {self.batch_size}")
        if force_insert:
            logger.info("⚠️ Modo FORCE_INSERT ativado: eventos serão inseridos mesmo se já existirem")
        
        total_inserted = 0
        total_skipped = 0
        
        # Processa em lotes
        for i in range(0, total_events, self.batch_size):
            batch = events[i:i + self.batch_size]
            lote_num = i//self.batch_size + 1
            total_lotes = ((total_events-1)//self.batch_size)+1
            logger.info(f"📦 Processando lote {lote_num}/{total_lotes} ({len(batch)} eventos)")
            
            success = self.send_events(batch, force_insert=force_insert)
            if not success:
                logger.warning(f"⚠️ Falha ao enviar lote {lote_num}")
                # Continua tentando os próximos lotes
            else:
                # Tenta obter estatísticas do último envio (se disponível)
                logger.debug(f"✅ Lote {lote_num} enviado com sucesso")
            
            # Pequena pausa entre lotes para não sobrecarregar
            if i + self.batch_size < total_events:
                time.sleep(1)
        
        logger.info(f"✅ Processamento em lote concluído")
    
    def read_all_events_powershell(self, force_all: bool = False) -> List[Dict]:
        """
        Lê TODOS os eventos ID 307 de todas as datas via PowerShell (sincronização inicial)
        
        Args:
            force_all: Se True, ignora highest_record_processed e lê todos os eventos
        """
        all_events = []
        seen_record_ids = set()  # Para evitar duplicatas
        
        try:
            logger.info("📊 Buscando TODOS os eventos ID 307 de todas as datas...")
            logger.info("⏳ Isso pode levar alguns minutos dependendo da quantidade de eventos...")
            
            # Busca TODOS os eventos sem limite de data
            # Usa MaxEvents alto e faz múltiplas consultas se necessário
            max_events_per_query = 5000
            offset = 0
            total_found = 0
            
            while True:
                ps_command = f"""
                $events = Get-WinEvent -FilterHashtable @{{
                    LogName='{EVENT_LOG_OPERATIONAL}'
                    ID={EVENT_ID_PRINT}
                }} -MaxEvents {max_events_per_query} -ErrorAction SilentlyContinue | 
                Select-Object RecordId, TimeCreated, Message | 
                Sort-Object RecordId
                
                if ($events) {{
                    $events | ConvertTo-Json
                }}
                """
                
                result = subprocess.run(
                    ['powershell', '-Command', ps_command],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                if result.returncode != 0 or not result.stdout.strip():
                    break
                
                try:
                    import json as json_lib
                    eventos_ps = json_lib.loads(result.stdout)
                    
                    if isinstance(eventos_ps, dict):
                        eventos_ps = [eventos_ps]
                    
                    if not eventos_ps:
                        break
                    
                    logger.info(f"📊 Lote {offset//max_events_per_query + 1}: {len(eventos_ps)} eventos encontrados")
                    
                    # Processa cada evento, evitando duplicatas
                    batch_added = 0
                    for evento_ps in eventos_ps:
                        record_id = evento_ps.get('RecordId', 0)
                        
                        # Verifica se já foi processado (evita duplicatas no mesmo batch)
                        if record_id in seen_record_ids:
                            continue
                        
                        seen_record_ids.add(record_id)
                        
                        # Se force_all=False e temos estado válido, pula eventos já processados
                        # IMPORTANTE: highest_record_processed = -1 significa sem estado, então processa tudo
                        if not force_all and self.has_state() and self.highest_record_processed >= 0 and record_id <= self.highest_record_processed:
                            logger.debug(f"[PowerShell] Evento RecordID={record_id} pulado (já processado: {self.highest_record_processed})")
                            continue
                        
                        event_data = self.parse_powershell_event(evento_ps)
                        if event_data:
                            all_events.append(event_data)
                            batch_added += 1
                        else:
                            logger.warning(f"[PowerShell] Falha ao parsear evento RecordID={record_id}")
                    
                    total_found += len(eventos_ps)
                    skipped_in_batch = len(eventos_ps) - batch_added
                    if skipped_in_batch > 0:
                        logger.warning(f"⚠️ {skipped_in_batch} eventos foram pulados neste lote (já processados ou falha no parse)")
                    logger.info(f"✅ {batch_added} eventos novos adicionados (total acumulado: {len(all_events)})")
                    
                    # Se retornou menos que o máximo, chegou ao fim
                    if len(eventos_ps) < max_events_per_query:
                        break
                    
                    offset += max_events_per_query
                    
                    # Pequena pausa entre consultas para não sobrecarregar
                    time.sleep(0.5)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Erro ao parsear JSON: {e}")
                    break
                except Exception as e:
                    logger.error(f"Erro ao processar lote: {e}")
                    break
            
            # Ordena por record_number para garantir ordem cronológica
            all_events.sort(key=lambda x: x.get('record_number', 0))
            
            total_skipped = total_found - len(all_events)
            logger.info(f"📊 Sincronização completa: {len(all_events)} eventos únicos processados de {total_found} encontrados")
            if total_skipped > 0:
                logger.warning(f"⚠️ {total_skipped} eventos foram pulados (já processados ou falha no parse)")
            
            if all_events:
                min_record = min(e.get('record_number', 0) for e in all_events if e.get('record_number') is not None)
                max_record = max(e.get('record_number', 0) for e in all_events if e.get('record_number') is not None)
                logger.info(f"📌 RecordIDs: {min_record} até {max_record}")
                logger.info(f"📊 Resumo: {len(all_events)} eventos prontos para envio ao servidor")
            else:
                logger.error(f"❌ PROBLEMA CRÍTICO: Nenhum evento foi processado! Total encontrado: {total_found}")
                logger.error(f"   - force_all: {force_all}")
                logger.error(f"   - has_state: {self.has_state()}")
                logger.error(f"   - highest_record_processed: {self.highest_record_processed}")
                if not force_all and self.has_state():
                    logger.error(f"   ⚠️ Possível causa: force_all=False e highest_record={self.highest_record_processed}")
                    logger.error(f"   💡 SOLUÇÃO: Delete agent_state.json para forçar sincronização completa")
                else:
                    logger.error(f"   ⚠️ Possível causa: Falha no parse dos eventos ou filtro muito restritivo")
                    logger.error(f"   💡 Verifique os logs acima para ver quantos eventos falharam no parse")
        
        except Exception as e:
            logger.error(f"Erro ao ler eventos históricos via PowerShell: {e}", exc_info=True)
        
        return all_events
    
    def parse_powershell_event(self, evento_ps: Dict) -> Optional[Dict]:
        """
        Parse de evento retornado pelo PowerShell (usado em sincronização inicial)
        Conforme especificação: extrai Params do Event 307
        """
        try:
            record_id = evento_ps.get('RecordId', 0)
            message = evento_ps.get('Message', '')
            time_created = evento_ps.get('TimeCreated', '')
            properties = evento_ps.get('Properties', [])
            
            # Extrai Params das Properties (usa função auxiliar para tratar objetos {'Value': '...'})
            props_list = [extrair_valor_property(p) for p in properties] if properties else []
            
            # Param1 = JobID
            job_id = props_list[0] if len(props_list) > 0 and props_list[0].isdigit() else None
            if not job_id:
                job_match = re.search(r'O documento (\d+)', message, re.IGNORECASE)
                if job_match:
                    job_id = job_match.group(1)
            
            # Param2 = Documento
            document = props_list[1].strip() if len(props_list) > 1 and props_list[1] else "Unknown"
            
            # Param3 = Usuário
            user = props_list[2].strip() if len(props_list) > 2 and props_list[2] else "Unknown"
            
            # Param4 = Computador
            machine = props_list[3].replace('\\', '').replace('\\\\', '').strip() if len(props_list) > 3 and props_list[3] else obter_nome_maquina()
            
            # Param5 = Impressora
            printer_name = props_list[4].strip() if len(props_list) > 4 and props_list[4] else "Unknown"
            
            # Param6 = Porta
            printer_port = props_list[5].strip() if len(props_list) > 5 and props_list[5] else None
            
            # Param7 = Tamanho em bytes
            file_size = None
            if len(props_list) > 6 and props_list[6]:
                try:
                    file_size = int(re.sub(r'[^\d]', '', props_list[6]))
                except (ValueError, TypeError):
                    pass
            
            # Param8 = Páginas impressas
            pages = None
            if len(props_list) > 7 and props_list[7]:
                try:
                    pages = int(re.sub(r'[^\d]', '', props_list[7]))
                except (ValueError, TypeError):
                    pass
            
            # Fallback: tenta extrair da mensagem
            if pages is None or pages < 1:
                pages_match = re.search(r'P[áa]ginas impressas:\s*(\d+)|Pages printed:\s*(\d+)', message, re.IGNORECASE)
                if pages_match:
                    try:
                        pages = int(pages_match.group(1) or pages_match.group(2))
                    except (ValueError, IndexError):
                        pages = 1
                else:
                    pages = 1
            
            if pages > 10000:
                pages = 1
            
            # Busca tipo da impressora no servidor (duplex/simplex)
            tipo_impressora = self.get_printer_type(printer_name)
            # Garante que tipo_impressora é uma string válida
            if not tipo_impressora or not isinstance(tipo_impressora, str):
                tipo_impressora = "simplex"
            
            # Calcula folhas físicas usando função auxiliar
            # NOTA: Em sincronização inicial, não temos Event 805, então usa copies=1 como default
            copies = 1  # Default se não tiver Event 805
            folhas = calcular_folhas_fisicas(pages, tipo_impressora, copies)
            
            # Converte data
            try:
                if '/Date(' in time_created:
                    timestamp_match = re.search(r'/Date\((\d+)\)/', time_created)
                    if timestamp_match:
                        timestamp_ms = int(timestamp_match.group(1))
                        date_str = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                else:
                    date_str = datetime.fromisoformat(time_created.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
            except Exception as e:
                logger.debug(f"Erro ao converter data {time_created}: {e}")
                date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Formata conforme esperado pelo servidor (campos em inglês)
            # NOTA: Em sincronização inicial, não temos Event 805, então usa valores default
            return {
                "record_number": record_id,
                "user": user,                    # Nome do usuário
                "machine": machine,              # Nome do computador
                "date": date_str,                # Data/hora do evento
                "pages": pages,                  # Número de páginas (lógicas)
                "printer_name": printer_name,    # Nome da impressora
                "document": document,            # Nome do documento
                "printer_port": printer_port,    # Porta/caminho da impressora
                "job_id": job_id,                # ID do job
                "duplex": 1 if tipo_impressora.lower() == "duplex" else 0,  # 1=duplex, 0=simplex
                "file_size": file_size,          # Tamanho em bytes
                "event_id": EVENT_ID_PRINT,      # ID do evento (307)
                "copies": copies,                # Cópias (default=1 em sincronização inicial)
                "color_mode": None,              # Modo de cor (não disponível em sincronização inicial)
                "sheets_used": folhas            # Folhas físicas calculadas
            }
        
        except Exception as e:
            logger.error(f"Erro ao parsear evento PowerShell: {e}", exc_info=True)
            return None
    
    def initial_sync(self, force_all: bool = False):
        """
        Sincronização inicial - processa todos os eventos existentes
        
        Args:
            force_all: Se True, força leitura de todos os eventos mesmo que já existam no servidor
        """
        # Determina se deve forçar leitura de todos os eventos
        should_force_all = force_all or not self.has_state()
        
        if should_force_all:
            logger.info("🔄 Iniciando sincronização COMPLETA de TODOS os eventos históricos...")
            logger.info("ℹ️ Isso pode levar alguns minutos dependendo da quantidade de eventos...")
            logger.info(f"ℹ️ Modo: force_all={should_force_all}, has_state={self.has_state()}, highest_record={self.highest_record_processed}")
        else:
            logger.info("🔄 Iniciando sincronização inicial de eventos...")
            logger.info(f"ℹ️ Modo: force_all={should_force_all}, has_state={self.has_state()}, highest_record={self.highest_record_processed}")
        
        # Se usando PowerShell, não precisa conectar ao Event Log
        if self.using_powershell_mode:
            try:
                all_events = self.read_all_events_powershell(force_all=should_force_all)
                
                if all_events:
                    logger.info(f"📊 Enviando {len(all_events)} eventos para o servidor...")
                    if should_force_all:
                        logger.info("⚠️ Modo FORCE_INSERT: eventos serão inseridos mesmo se já existirem no banco")
                    else:
                        logger.info("ℹ️ O servidor irá gerenciar duplicatas automaticamente")
                    
                    # Processa em lotes (force_insert=True quando é sincronização completa)
                    self.process_events_batch(all_events, force_insert=should_force_all)
                    
                    # Atualiza o último record processado
                    if all_events:
                        max_record = max(event['record_number'] for event in all_events if event.get('record_number') is not None)
                        if max_record > 0:  # Só atualiza se houver record válido
                            self.highest_record_processed = max_record
                            self.save_last_record()
                            logger.info(f"📌 Último record processado atualizado: {self.highest_record_processed}")
                        else:
                            logger.warning("⚠️ Nenhum record_number válido encontrado nos eventos")
                else:
                    logger.info("ℹ️ Nenhum evento de impressão encontrado")
                
                return True
            except Exception as e:
                logger.error(f"❌ Erro na sincronização via PowerShell: {e}")
                return False
        
        # Fallback para método antigo (win32evtlog)
        if not self.connect_to_event_log():
            logger.error("❌ Falha ao conectar ao log de eventos")
            return False
        
        try:
            # Lê todos os eventos (force_all se não tiver estado)
            all_events = self.read_all_events(force_all=should_force_all)
            
            if all_events:
                # O servidor deve lidar com duplicatas, mas vamos enviar todos
                logger.info(f"📊 Enviando {len(all_events)} eventos para o servidor...")
                if should_force_all:
                    logger.info("⚠️ Modo FORCE_INSERT: eventos serão inseridos mesmo se já existirem no banco")
                else:
                    logger.info("ℹ️ O servidor irá gerenciar duplicatas automaticamente")
                
                # Processa em lotes (force_insert=True quando é sincronização completa)
                self.process_events_batch(all_events, force_insert=should_force_all)
                
                # Atualiza o último record processado
                if all_events:
                    max_record = max(event['record_number'] for event in all_events if event.get('record_number') is not None)
                    if max_record > 0:  # Só atualiza se houver record válido
                        self.highest_record_processed = max_record
                        self.save_last_record()  # Salva estado
                        logger.info(f"📌 Último record processado atualizado: {self.highest_record_processed}")
                    else:
                        logger.warning("⚠️ Nenhum record_number válido encontrado nos eventos")
            else:
                logger.info("ℹ️ Nenhum evento de impressão encontrado no log")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro na sincronização inicial: {e}")
            return False
        finally:
            self.disconnect_from_event_log()
    
    def process_pending_queue(self) -> int:
        """
        Processa eventos pendentes da fila local.
        
        Chamado periodicamente para tentar reenviar eventos que falharam.
        
        Returns:
            Número de eventos enviados com sucesso
        """
        queue = get_event_queue()
        stats = queue.get_queue_stats()
        
        if stats["pending_count"] == 0:
            return 0
        
        logger.info(f"📦 Fila local: {stats['pending_count']} eventos pendentes")
        
        # Obtém eventos pendentes (em lotes menores para não sobrecarregar)
        pending = queue.get_pending_events(limit=20)
        
        if not pending:
            return 0
        
        # Tenta enviar diretamente ao servidor (sem usar send_events que pode re-enfileirar)
        events_to_send = [event for _, event in pending]
        ids_to_remove = []
        
        try:
            response = requests.post(
                self.server_url,
                json={"events": events_to_send},
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                inserted = result.get('inserted', 0)
                skipped = result.get('skipped', 0)
                
                # Remove eventos enviados da fila
                ids_to_remove = [id_ for id_, _ in pending]
                removed = queue.remove_events(ids_to_remove)
                
                logger.info(f"✅ Fila processada: {inserted} inseridos, {skipped} duplicatas, {removed} removidos da fila")
                
                # Atualiza highest_record para eventos reenviados
                for _, event in pending:
                    record_id = event.get('record_number')
                    if record_id is not None and record_id > self.highest_record_processed:
                        self.highest_record_processed = record_id
                
                self.save_last_record()
                return len(ids_to_remove)
            else:
                logger.warning(f"⚠️ Erro ao processar fila: HTTP {response.status_code}")
                # Atualiza retry count
                for id_, _ in pending:
                    queue.update_retry(id_, f"HTTP {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            logger.debug("📦 Servidor ainda offline, fila mantida")
        except requests.exceptions.Timeout:
            logger.warning("⚠️ Timeout ao processar fila")
        except Exception as e:
            logger.error(f"❌ Erro ao processar fila: {e}")
        
        return 0
    
    def monitor_events(self):
        """Loop principal de monitoramento"""
        logger.info("🖨️ Iniciando monitoramento de eventos de impressão...")
        logger.info(f"📡 Servidor: {self.server_url}")
        logger.info(f"⏱️ Intervalo de verificação: {self.check_interval}s")
        
        # Informa sobre modo híbrido
        if self.using_powershell_mode:
            logger.info("⚡ Modo PowerShell ativo: Get-WinEvent (mais confiável)")
        elif self.use_wmi_backup:
            logger.info("🔄 Modo híbrido ativo: Event Log + WMI backup")
        else:
            logger.info("📋 Modo Event Log apenas")
        
        # Sincronização inicial automática se não houver estado OU se configurado
        needs_sync = not self.has_state() or self.process_all_on_start
        
        if needs_sync:
            if not self.has_state():
                logger.warning("⚠️ Estado do agente não encontrado ou inválido!")
                logger.info("🔄 Executando sincronização completa automática para recuperar dados históricos...")
            else:
                logger.info("📋 Sincronização inicial habilitada pela configuração")
            
            if not self.initial_sync():
                logger.warning("⚠️ Falha na sincronização inicial, continuando com monitoramento...")
        else:
            logger.info("⏭️ Estado encontrado, monitorando apenas novos eventos")
        
        # Loop de monitoramento contínuo
        logger.info("👀 Monitorando novos eventos...")
        
        # Contador para processar fila periodicamente
        queue_check_counter = 0
        QUEUE_CHECK_INTERVAL = 12  # Verifica fila a cada 12 ciclos (60s se check_interval=5s)
        
        # Mostra estatísticas da fila no início
        queue = get_event_queue()
        stats = queue.get_queue_stats()
        if stats["pending_count"] > 0:
            logger.warning(f"📦 Fila local tem {stats['pending_count']} eventos pendentes do período offline")
        
        try:
            while True:
                try:
                    if not self.event_handle:
                        if not self.connect_to_event_log():
                            logger.error(f"❌ Falha na conexão. Tentando novamente em {self.retry_interval}s...")
                            time.sleep(self.retry_interval)
                            continue
                    
                    # Lê apenas eventos novos
                    new_events = self.read_new_events()
                    
                    if new_events:
                        if self.using_powershell_mode:
                            modo = "[PowerShell]"
                        elif self.using_wmi_mode:
                            modo = "[WMI]"
                        else:
                            modo = "[EventLog]"
                        logger.info(f"🆕 {modo} Encontrados {len(new_events)} novos eventos")
                        self.process_events_batch(new_events)
                        
                        # Atualiza o maior record processado (já foi atualizado em read_new_events)
                        # Mas garante que está salvo
                        if new_events:
                            self.save_last_record()
                    
                    # MELHORIA: Processa fila de eventos pendentes periodicamente
                    queue_check_counter += 1
                    if queue_check_counter >= QUEUE_CHECK_INTERVAL:
                        queue_check_counter = 0
                        self.process_pending_queue()
                        
                        # Limpa eventos muito antigos (mais de 7 dias)
                        queue.cleanup_old_events(days=7)
                    
                    time.sleep(self.check_interval)
                    
                except KeyboardInterrupt:
                    logger.info("⏹️ Interrupção solicitada pelo usuário")
                    break
                except Exception as e:
                    logger.error(f"❌ Erro no loop de monitoramento: {e}")
                    self.disconnect_from_event_log()
                    logger.info(f"⏳ Aguardando {self.retry_interval} segundos antes de reconectar...")
                    time.sleep(self.retry_interval)
        finally:
            # Cleanup
            if self.spool_interceptor:
                self.spool_interceptor.stop_monitoring()
            self.disconnect_from_event_log()
            logger.info("👋 Monitoramento finalizado")

def test_connection():
    """Testa conexão com o servidor"""
    try:
        response = requests.get(config["server_url"].replace("/api/print_events", "/"), timeout=5)
        if response.status_code == 200:
            logger.info("✅ Conexão com servidor OK")
            return True
        else:
            logger.warning(f"⚠️ Servidor retornou status {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Falha na conexão com servidor: {e}")
        return False

def test_event_log_access():
    """Testa acesso ao log de eventos"""
    try:
        server = 'localhost'
        handle = win32evtlog.OpenEventLog(server, EVENT_LOG_OPERATIONAL)
        win32evtlog.CloseEventLog(handle)
        logger.info("✅ Acesso ao log de eventos OK")
        return True
    except Exception as e:
        logger.error(f"❌ Falha no acesso ao log de eventos: {e}")
        logger.info("💡 Dica: Execute como administrador")
        return False

def reset_state():
    """Reseta o estado do agente (remove agent_state.json)"""
    agent_dir = os.path.dirname(os.path.abspath(__file__))
    state_file = os.path.join(agent_dir, "agent_state.json")
    
    if os.path.exists(state_file):
        try:
            os.remove(state_file)
            print("✅ Estado do agente resetado com sucesso!")
            print("   O arquivo agent_state.json foi removido.")
            print("   Na próxima execução, o agente processará todos os eventos.")
            return True
        except Exception as e:
            print(f"❌ Erro ao resetar estado: {e}")
            return False
    else:
        print("ℹ️  Arquivo agent_state.json não encontrado.")
        print("   O agente já está sem estado.")
        return True

def main():
    """Função principal"""
    import sys
    
    # Verifica se foi passado argumento --reset
    if len(sys.argv) > 1 and sys.argv[1] in ['--reset', '-r', 'reset']:
        reset_state()
        return
    
    # Banner de inicialização
    machine_name = obter_nome_maquina()
    print("=" * 60)
    print("   AGENTE DE MONITORAMENTO DE IMPRESSÃO v3.2")
    print("=" * 60)
    print(f"   🖥️  Máquina: {machine_name}")
    print(f"   📅 Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   🌐 Servidor: {config.get('server_url', DEFAULT_SERVER_URL)}")
    print("=" * 60)
    
    logger.info(f"🚀 Agente iniciado na máquina: {machine_name}")
    logger.info(f"📁 Configuração carregada de: {CONFIG_FILE}")
    
    # Testes iniciais
    logger.info("🧪 Executando testes iniciais...")
    test_event_log_access()
    test_connection()
    
    # Inicializa e executa monitor
    monitor = PrintMonitor()
    try:
        monitor.monitor_events()
    except Exception as e:
        logger.critical(f"💥 Erro crítico: {e}")
        raise

if __name__ == "__main__":
    main()