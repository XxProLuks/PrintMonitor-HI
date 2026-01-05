#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de Descoberta Automática de Impressoras de Rede
Escaneia a rede hospitalar e identifica impressoras via Ping, SNMP e WS-Discovery
"""

import asyncio
import socket
import sqlite3
import subprocess
import sys
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Set
from ipaddress import ip_address
import platform

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Tentar importar pysnmp
try:
    from pysnmp.hlapi import (
        getCmd, SnmpEngine, CommunityData, UdpTransportTarget,
        ContextData, ObjectType, ObjectIdentity
    )
    SNMP_AVAILABLE = True
except ImportError:
    SNMP_AVAILABLE = False

# Configurações
# Tenta usar o banco do servidor se existir, senão usa o padrão
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERV_DB = os.path.join(BASE_DIR, "serv", "print_events.db")
DEFAULT_DB = r"C:\Monitoramento\print_events.db"

# Usa o banco do servidor se existir, senão usa o padrão
# Verifica também se existe na estrutura do projeto
PROJECT_DB = os.path.join(BASE_DIR, "serv", "print_events.db")
if os.path.exists(PROJECT_DB):
    DB_PATH = PROJECT_DB
elif os.path.exists(SERV_DB):
    DB_PATH = SERV_DB
else:
    DB_PATH = DEFAULT_DB

LOG_DIR = r"C:\Monitoramento\logs"
LOG_FILE = os.path.join(LOG_DIR, "scan_impressoras.log")
NETWORK_RANGE_START = "192.168.0.1"
NETWORK_RANGE_END = "192.168.0.254"  # Range padrão /24
SNMP_COMMUNITY = "public"
SNMP_TIMEOUT = 2
PING_TIMEOUT = 1
MAX_CONCURRENT = 100  # Máximo de tarefas assíncronas simultâneas

# OIDs SNMP úteis
SNMP_OID_SYS_NAME = "1.3.6.1.2.1.1.5.0"  # sysName
SNMP_OID_SYS_DESC = "1.3.6.1.2.1.1.1.0"  # sysDescr
SNMP_OID_PRINTER_MIB = "1.3.6.1.2.1.25.3.2.1.3"  # hrDeviceDescr (impressoras)

# Configurar logging
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def check_permissions():
    """
    Verifica permissões necessárias antes de iniciar o scan
    
    Returns:
        Tuple (bool, List[str]): (sucesso, lista de avisos)
    """
    warnings = []
    
    # Verifica permissão de escrita no diretório do banco
    try:
        db_dir = os.path.dirname(DB_PATH)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        test_file = os.path.join(db_dir, ".test_write")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
    except Exception as e:
        warnings.append(f"Sem permissao de escrita no diretorio do banco ({db_dir}): {e}")
        return False, warnings
    
    # Verifica permissão de escrita no diretório de logs
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        test_file = os.path.join(LOG_DIR, ".test_write")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
    except Exception as e:
        warnings.append(f"Sem permissao de escrita no diretorio de logs ({LOG_DIR}): {e}")
        return False, warnings
    
    # Verifica se está rodando como administrador (não necessário, mas avisa)
    if platform.system() == 'Windows':
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            if not is_admin:
                warnings.append("Executando sem privilegios de administrador (normal para scan TCP simples)")
        except Exception:
            pass
    
    return True, warnings


def init_database():
    """Inicializa a tabela de impressoras no banco de dados"""
    try:
        db_dir = os.path.dirname(DB_PATH)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS impressoras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT,
                ip TEXT UNIQUE,
                modelo TEXT,
                status TEXT,
                data_detectada DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Índice para melhor performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_impressoras_ip 
            ON impressoras(ip)
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"Banco de dados inicializado: {DB_PATH}")
        
    except PermissionError as e:
        logger.error(f"ERRO DE PERMISSAO: Sem permissao de escrita no banco de dados: {e}")
        logger.error(f"Verifique se o usuario tem permissao de escrita em: {os.path.dirname(DB_PATH)}")
        raise
    except Exception as e:
        logger.error(f"Erro ao inicializar banco de dados: {e}")
        raise


def save_printer(printer_info: Dict) -> bool:
    """
    Salva ou atualiza informações da impressora no banco de dados
    
    Args:
        printer_info: Dicionário com informações da impressora
        
    Returns:
        True se salvou com sucesso, False caso contrário
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO impressoras 
            (nome, ip, modelo, status, data_detectada)
            VALUES (?, ?, ?, ?, ?)
        """, (
            printer_info.get('nome', ''),
            printer_info.get('ip', ''),
            printer_info.get('modelo', ''),
            printer_info.get('status', 'Online'),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Erro ao salvar impressora {printer_info.get('ip')}: {e}")
        return False


def ping_host(ip: str) -> bool:
    """
    Verifica se um host está ativo usando ping
    
    Args:
        ip: Endereço IP
        
    Returns:
        True se o host respondeu ao ping, False caso contrário
    """
    try:
        if platform.system() == 'Windows':
            # Windows ping
            result = subprocess.run(
                ['ping', '-n', '1', '-w', str(PING_TIMEOUT * 1000), ip],
                capture_output=True,
                timeout=PING_TIMEOUT + 1,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            return result.returncode == 0
        else:
            # Linux/Unix ping
            result = subprocess.run(
                ['ping', '-c', '1', '-W', str(PING_TIMEOUT), ip],
                capture_output=True,
                timeout=PING_TIMEOUT + 1
            )
            return result.returncode == 0
    except Exception:
        return False


async def ping_host_async(ip: str) -> bool:
    """
    Versão assíncrona do ping
    
    Args:
        ip: Endereço IP
        
    Returns:
        True se o host respondeu ao ping, False caso contrário
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, ping_host, ip)


def get_hostname(ip: str) -> Optional[str]:
    """
    Obtém o hostname de um IP usando reverse DNS
    
    Args:
        ip: Endereço IP
        
    Returns:
        Hostname ou None
    """
    try:
        hostname, _, _ = socket.gethostbyaddr(ip)
        return hostname
    except Exception:
        return None


async def get_hostname_async(ip: str) -> Optional[str]:
    """
    Versão assíncrona do get_hostname
    
    Args:
        ip: Endereço IP
        
    Returns:
        Hostname ou None
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_hostname, ip)


def get_snmp_info(ip: str) -> Optional[Dict]:
    """
    Obtém informações da impressora via SNMP
    
    Args:
        ip: Endereço IP
        
    Returns:
        Dicionário com informações SNMP ou None
    """
    if not SNMP_AVAILABLE:
        return None
    
    try:
        info = {}
        
        # Tenta obter sysName
        try:
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(SNMP_COMMUNITY),
                UdpTransportTarget((ip, 161), timeout=SNMP_TIMEOUT, retries=0),
                ContextData(),
                ObjectType(ObjectIdentity(SNMP_OID_SYS_NAME))
            )
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            if not errorIndication and not errorStatus:
                for oid, val in varBinds:
                    info['nome'] = str(val).strip()
        except Exception:
            pass
        
        # Tenta obter sysDescr (modelo)
        try:
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(SNMP_COMMUNITY),
                UdpTransportTarget((ip, 161), timeout=SNMP_TIMEOUT, retries=0),
                ContextData(),
                ObjectType(ObjectIdentity(SNMP_OID_SYS_DESC))
            )
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            if not errorIndication and not errorStatus:
                for oid, val in varBinds:
                    desc = str(val).strip()
                    # Extrai modelo da descrição (geralmente contém o modelo)
                    info['modelo'] = desc
        except Exception:
            pass
        
        return info if info else None
        
    except Exception as e:
        logger.debug(f"Erro SNMP em {ip}: {e}")
        return None


async def get_snmp_info_async(ip: str) -> Optional[Dict]:
    """
    Versão assíncrona do get_snmp_info
    
    Args:
        ip: Endereço IP
        
    Returns:
        Dicionário com informações SNMP ou None
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_snmp_info, ip)


def check_printer_port(ip: str, port: int, timeout: float = 1.0) -> bool:
    """
    Verifica se uma porta de impressora está aberta
    
    Args:
        ip: Endereço IP
        port: Porta a verificar
        timeout: Timeout em segundos
        
    Returns:
        True se a porta estiver aberta, False caso contrário
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except Exception:
        return False


async def check_printer_port_async(ip: str, port: int) -> bool:
    """
    Versão assíncrona do check_printer_port
    
    Args:
        ip: Endereço IP
        port: Porta a verificar
        
    Returns:
        True se a porta estiver aberta, False caso contrário
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, check_printer_port, ip, port, 1.0)


async def check_http_printer(ip: str, port: int = 80) -> Optional[Dict]:
    """
    Verifica se um IP tem interface web de impressora
    
    Args:
        ip: Endereço IP
        port: Porta HTTP (80, 443, 8080)
        
    Returns:
        Informações da impressora se encontrada, None caso contrário
    """
    try:
        # Tenta método simples primeiro (socket)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((ip, port))
        if result != 0:
            sock.close()
            return None
        
        # Porta aberta, tenta ler banner/resposta
        try:
            sock.settimeout(1)
            # Envia requisição HTTP simples
            request = f"GET / HTTP/1.1\r\nHost: {ip}\r\n\r\n"
            sock.send(request.encode())
            response = sock.recv(4096).decode('utf-8', errors='ignore')
            sock.close()
            
            # Indicadores de impressora
            printer_keywords = [
                'printer', 'print', 'hp', 'canon', 'epson', 'brother',
                'kyocera', 'xerox', 'lexmark', 'ricoh', 'samsung',
                'konica', 'minolta', 'sharp', 'toshiba', 'oki',
                'jetdirect', 'ipp', 'cups', 'printing'
            ]
            
            # Verifica no conteúdo
            text_to_check = response.lower()
            
            for keyword in printer_keywords:
                if keyword in text_to_check:
                    # Tenta extrair nome/modelo
                    nome = f"Impressora {ip}"
                    modelo = ''
                    
                    # Tenta pegar do título
                    import re
                    title_match = re.search(r'<title[^>]*>(.*?)</title>', response, re.IGNORECASE)
                    if title_match:
                        title = title_match.group(1).strip()
                        if any(kw in title.lower() for kw in printer_keywords):
                            nome = title
                            modelo = title
                    
                    return {
                        'ip': ip,
                        'nome': nome,
                        'modelo': modelo,
                        'status': 'Online',
                        'source': f'HTTP-{port}',
                        'web_port': port
                    }
        except Exception:
            sock.close()
            # Mesmo sem ler resposta, se porta está aberta pode ser impressora
            return {
                'ip': ip,
                'nome': f"Impressora {ip}",
                'modelo': '',
                'status': 'Online',
                'source': f'HTTP-{port}',
                'web_port': port
            }
            
    except Exception:
        pass
    
    return None


def discover_via_windows_event_logs() -> List[Dict]:
    """
    Descobre impressoras analisando logs de eventos do Windows
    
    Returns:
        Lista de IPs de impressoras encontradas nos logs
    """
    printers = []
    
    if platform.system() != 'Windows':
        return printers
    
    try:
        import subprocess
        import re
        
        # Busca eventos de impressão (Event ID 307)
        ps_command = """
        Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-PrintService/Operational'; ID=307} -MaxEvents 1000 -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty Message |
        ForEach-Object {
            if ($_ -match 'Param5.*?\\\\?([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)') {
                $matches[1]
            }
        } |
        Select-Object -Unique
        """
        
        result = subprocess.run(
            ['powershell', '-Command', ps_command],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        
        if result.returncode == 0 and result.stdout.strip():
            ips = result.stdout.strip().split('\n')
            for ip in ips:
                ip = ip.strip()
                if ip and re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
                    printers.append({
                        'ip': ip,
                        'nome': f"Impressora {ip}",
                        'modelo': '',
                        'status': 'Online',
                        'source': 'Event Log'
                    })
        
    except Exception as e:
        logger.debug(f"Erro ao buscar impressoras nos logs: {e}")
    
    return printers


def discover_via_windows_network() -> List[Dict]:
    """
    Descobre impressoras usando métodos nativos do Windows (WS-Discovery, WMI)
    
    Returns:
        Lista de impressoras encontradas
    """
    printers = []
    
    if platform.system() != 'Windows':
        return printers
    
    try:
        import subprocess
        import re
        
        # Método 1: WMI Win32_Printer
        ps_command = """
        Get-WmiObject -Class Win32_Printer | 
        Where-Object { $_.Network -eq $true -or $_.PortName -like '*.*' } |
        Select-Object Name, PortName, DriverName, Location | 
        ConvertTo-Json -Depth 2
        """
        
        result = subprocess.run(
            ['powershell', '-Command', ps_command],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        
        if result.returncode == 0 and result.stdout.strip():
            import json
            printers_wmi = json.loads(result.stdout)
            
            if isinstance(printers_wmi, dict):
                printers_wmi = [printers_wmi]
            
            for printer in printers_wmi:
                port_name = printer.get('PortName', '').strip()
                printer_name = printer.get('Name', '').strip()
                
                if printer_name and port_name:
                    # Extrai IP da porta
                    ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', port_name)
                    if ip_match:
                        ip_address = ip_match.group(1)
                        printers.append({
                            'ip': ip_address,
                            'nome': printer_name,
                            'modelo': printer.get('DriverName', ''),
                            'status': 'Online',
                            'source': 'WMI'
                        })
                    else:
                        # Tenta resolver hostname
                        try:
                            resolved_ip = socket.gethostbyname(port_name)
                            printers.append({
                                'ip': resolved_ip,
                                'nome': printer_name,
                                'modelo': printer.get('DriverName', ''),
                                'status': 'Online',
                                'source': 'WMI-Hostname'
                            })
                        except Exception:
                            pass
        
        # Método 2: Get-Printer (PowerShell moderno)
        ps_command2 = """
        Get-Printer | Where-Object { $_.Network -eq $true } |
        Select-Object Name, PortName, DriverName | 
        ConvertTo-Json -Depth 2
        """
        
        result2 = subprocess.run(
            ['powershell', '-Command', ps_command2],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        
        if result2.returncode == 0 and result2.stdout.strip():
            import json
            printers_ps = json.loads(result2.stdout)
            
            if isinstance(printers_ps, dict):
                printers_ps = [printers_ps]
            
            for printer in printers_ps:
                port_name = printer.get('PortName', '').strip()
                printer_name = printer.get('Name', '').strip()
                
                if printer_name and port_name:
                    ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', port_name)
                    if ip_match:
                        ip_address = ip_match.group(1)
                        # Verifica se já não está na lista
                        if not any(p.get('ip') == ip_address for p in printers):
                            printers.append({
                                'ip': ip_address,
                                'nome': printer_name,
                                'modelo': printer.get('DriverName', ''),
                                'status': 'Online',
                                'source': 'Get-Printer'
                            })
        
    except Exception as e:
        logger.debug(f"Erro ao descobrir impressoras via Windows: {e}")
    
    return printers


async def scan_single_ip(ip: str) -> Optional[Dict]:
    """
    Escaneia um único IP procurando por impressoras (múltiplos métodos)
    
    Args:
        ip: Endereço IP a escanear
        
    Returns:
        Dicionário com informações da impressora encontrada ou None
    """
    try:
        # 1. Verifica se o host está ativo (ping) - mas não desiste se falhar
        # (ICMP pode estar bloqueado, mas portas podem estar abertas)
        is_alive = await ping_host_async(ip)
        
        # 2. Verifica portas de impressora comuns
        printer_ports = [9100, 631, 515, 161]  # JetDirect, IPP, LPR, SNMP
        open_ports = []
        
        for port in printer_ports:
            if await check_printer_port_async(ip, port):
                open_ports.append(port)
        
        # 3. Se não encontrou portas tradicionais, tenta interfaces web
        if not open_ports:
            # Tenta portas HTTP/HTTPS comuns
            web_ports = [80, 443, 8080, 8443]
            for web_port in web_ports:
                http_result = await check_http_printer(ip, web_port)
                if http_result:
                    # Encontrou interface web de impressora
                    return http_result
        
        # Se encontrou pelo menos uma porta de impressão, é provável que seja uma impressora
        if not open_ports:
            # Mesmo sem portas abertas, se ping funcionou, pode ser impressora
            # (pode estar com firewall bloqueando portas específicas)
            if is_alive:
                # Tenta obter hostname - se tiver nome relacionado a impressora, considera
                hostname = await get_hostname_async(ip)
                if hostname:
                    printer_keywords = ['print', 'printer', 'hp', 'canon', 'kyocera', 'epson', 'brother']
                    if any(kw in hostname.lower() for kw in printer_keywords):
                        return {
                            'ip': ip,
                            'nome': hostname,
                            'modelo': '',
                            'status': 'Online',
                            'source': 'Hostname'
                        }
            return None
        
        # 4. Tenta obter informações via SNMP
        snmp_info = await get_snmp_info_async(ip)
        
        # 5. Tenta obter hostname
        hostname = await get_hostname_async(ip)
        
        # 6. Tenta interface web também (mesmo tendo portas abertas)
        web_info = None
        if 80 in open_ports or 443 in open_ports:
            web_port = 443 if 443 in open_ports else 80
            web_info = await check_http_printer(ip, web_port)
        
        # Monta informações da impressora
        printer_info = {
            'ip': ip,
            'nome': (snmp_info.get('nome') if snmp_info else None) or 
                   (web_info.get('nome') if web_info else None) or
                   (hostname or f"Impressora {ip}"),
            'modelo': (snmp_info.get('modelo') if snmp_info else '') or
                     (web_info.get('modelo') if web_info else ''),
            'status': 'Online',
            'source': 'Scan'
        }
        
        return printer_info
        
    except Exception as e:
        logger.debug(f"Erro ao escanear {ip}: {e}")
        return None


def generate_ip_range(start: str, end: str) -> List[str]:
    """
    Gera lista de IPs no range especificado
    
    Args:
        start: IP inicial (ex: "192.168.0.1")
        end: IP final (ex: "192.168.0.999")
        
    Returns:
        Lista de IPs
    """
    ip_list = []
    
    try:
        start_ip = ip_address(start)
        end_ip = ip_address(end)
        
        # Se end tem mais de 255, assume que é um range de rede
        if int(end.split('.')[-1]) > 255:
            # Extrai a rede base (ex: 192.168.0)
            base = '.'.join(end.split('.')[:-1])
            # Gera todos os IPs possíveis na última octeto
            for i in range(1, 255):
                ip_list.append(f"{base}.{i}")
        else:
            # Range normal
            current = int(start_ip)
            end_int = int(end_ip)
            while current <= end_int:
                ip_list.append(str(ip_address(current)))
                current += 1
        
    except Exception as e:
        logger.error(f"Erro ao gerar range de IPs: {e}")
        # Fallback: gera range padrão 192.168.0.1-254
        base = "192.168.0"
        for i in range(1, 255):
            ip_list.append(f"{base}.{i}")
    
    return ip_list


async def scan_rede_impressoras() -> int:
    """
    Função principal: escaneia a rede e identifica impressoras
    
    Returns:
        Número total de impressoras detectadas
    """
    logger.info("="*80)
    logger.info("INICIANDO SCAN DE IMPRESSORAS DE REDE")
    logger.info("="*80)
    
    # Verifica permissões antes de iniciar
    logger.info("[VERIFICACAO] Verificando permissoes...")
    has_perms, warnings = check_permissions()
    if not has_perms:
        logger.error("ERRO: Permissoes insuficientes!")
        for warning in warnings:
            logger.error(f"  - {warning}")
        raise PermissionError("Permissoes insuficientes para executar o scan")
    
    if warnings:
        for warning in warnings:
            logger.warning(f"  [AVISO] {warning}")
    
    # Inicializa banco de dados
    init_database()
    
    start_time = datetime.now()
    found_printers = []
    
    # 1. Descobre impressoras via Windows (WS-Discovery, WMI)
    logger.info("[ETAPA 1] Descobrindo impressoras via Windows...")
    windows_printers = discover_via_windows_network()
    logger.info(f"        Encontradas {len(windows_printers)} impressoras via Windows")
    
    # 1.1. Descobre impressoras via logs de eventos
    logger.info("[ETAPA 1.1] Analisando logs de eventos do Windows...")
    event_printers = discover_via_windows_event_logs()
    logger.info(f"        Encontradas {len(event_printers)} impressoras nos logs")
    
    # Combina resultados
    all_windows_printers = windows_printers + event_printers
    # Remove duplicatas por IP
    seen_ips = set()
    unique_windows_printers = []
    for printer in all_windows_printers:
        ip = printer.get('ip')
        if ip and ip not in seen_ips:
            seen_ips.add(ip)
            unique_windows_printers.append(printer)
    
    logger.info(f"        Total unico: {len(unique_windows_printers)} impressoras")
    
    for printer in unique_windows_printers:
        found_printers.append(printer)
        save_printer(printer)
    
    # 2. Gera lista de IPs para escanear
    logger.info(f"[ETAPA 2] Gerando range de IPs: {NETWORK_RANGE_START} - {NETWORK_RANGE_END}")
    ip_list = generate_ip_range(NETWORK_RANGE_START, NETWORK_RANGE_END)
    logger.info(f"        Total de IPs a escanear: {len(ip_list)}")
    
    # Remove IPs já encontrados via Windows
    known_ips = {p.get('ip') for p in windows_printers}
    ip_list = [ip for ip in ip_list if ip not in known_ips]
    logger.info(f"        IPs restantes após descoberta Windows: {len(ip_list)}")
    
    # 3. Escaneia IPs de forma assíncrona
    logger.info("[ETAPA 3] Escaneando IPs da rede (assíncrono)...")
    logger.info(f"        Maximo de tarefas simultaneas: {MAX_CONCURRENT}")
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    
    async def scan_with_semaphore(ip: str):
        async with semaphore:
            return await scan_single_ip(ip)
    
    tasks = [scan_with_semaphore(ip) for ip in ip_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Processa resultados
    scanned_count = 0
    for result in results:
        if isinstance(result, Exception):
            continue
        if result:
            found_printers.append(result)
            save_printer(result)
            scanned_count += 1
            if scanned_count % 10 == 0:
                logger.info(f"        Progresso: {scanned_count} impressoras encontradas...")
    
    # 4. Resumo final
    elapsed_time = (datetime.now() - start_time).total_seconds()
    
    logger.info("="*80)
    logger.info("SCAN CONCLUIDO")
    logger.info("="*80)
    logger.info(f"Total de impressoras detectadas: {len(found_printers)}")
    logger.info(f"Tempo total: {elapsed_time:.2f} segundos")
    logger.info(f"Velocidade: {len(ip_list)/elapsed_time:.2f} IPs/segundo")
    logger.info("="*80)
    
    # Lista impressoras encontradas
    if found_printers:
        logger.info("\nImpressoras encontradas:")
        for printer in found_printers:
            logger.info(f"  - {printer['ip']:15s} | {printer['nome']:30s} | "
                       f"Modelo: {printer.get('modelo', 'N/A'):20s} | "
                       f"Fonte: {printer.get('source', 'Scan')}")
    
    return len(found_printers)


def main():
    """Função principal para execução standalone"""
    try:
        # Executa o scan
        total = asyncio.run(scan_rede_impressoras())
        print(f"\n[OK] Scan concluido! Total de impressoras: {total}")
        return total
    except KeyboardInterrupt:
        logger.warning("Scan interrompido pelo usuario")
        return 0
    except Exception as e:
        logger.error(f"Erro fatal: {e}", exc_info=True)
        return 0


if __name__ == "__main__":
    sys.exit(main())

