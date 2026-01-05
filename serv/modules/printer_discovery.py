"""
Módulo de Descoberta de Impressoras
====================================

Melhora a detecção automática de impressoras usando SNMP e outros métodos.

Funcionalidades:
- Scan SNMP na rede local
- Detecção de capacidade duplex
- Auto-cadastro de impressoras descobertas
- Obtenção de informações detalhadas via SNMP
"""

import logging
import re
import socket
import subprocess
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# SNMP OIDs comuns para impressoras
SNMP_OIDS = {
    # Informações gerais
    'sysDescr': '1.3.6.1.2.1.1.1.0',
    'sysName': '1.3.6.1.2.1.1.5.0',
    'sysLocation': '1.3.6.1.2.1.1.6.0',
    
    # Impressora
    'prtGeneralPrinterName': '1.3.6.1.2.1.43.5.1.1.16.1',
    'prtGeneralSerialNumber': '1.3.6.1.2.1.43.5.1.1.17.1',
    
    # Contadores de páginas
    'prtMarkerLifeCount': '1.3.6.1.2.1.43.10.2.1.4.1.1',
    'hrPrinterStatus': '1.3.6.1.2.1.25.3.5.1.1.1',
    
    # Capacidades (duplex)
    'prtOutputDefaultIndex': '1.3.6.1.2.1.43.9.2.1.2',
    'prtInputDefaultIndex': '1.3.6.1.2.1.43.8.2.1.2',
}

# Portas comuns de impressoras
PRINTER_PORTS = [9100, 515, 631, 161]

# Flag de disponibilidade SNMP
SNMP_AVAILABLE = False

try:
    from pysnmp.hlapi import (
        getCmd, SnmpEngine, CommunityData, UdpTransportTarget,
        ContextData, ObjectType, ObjectIdentity
    )
    SNMP_AVAILABLE = True
    logger.info("✅ pysnmp disponível para descoberta SNMP")
except ImportError:
    logger.warning(
        "⚠️ pysnmp não instalado. Descoberta SNMP desabilitada.\n"
        "   💡 Para habilitar: pip install pysnmp"
    )


def is_snmp_available() -> bool:
    """Verifica se SNMP está disponível."""
    return SNMP_AVAILABLE


def get_snmp_value(ip: str, oid: str, community: str = 'public', 
                   timeout: float = 2.0) -> Optional[str]:
    """
    Obtém valor SNMP de um dispositivo.
    
    Args:
        ip: Endereço IP do dispositivo
        oid: OID SNMP a consultar
        community: Community string (padrão: public)
        timeout: Timeout em segundos
    
    Returns:
        Valor ou None se falhar
    """
    if not SNMP_AVAILABLE:
        return None
    
    try:
        errorIndication, errorStatus, errorIndex, varBinds = next(
            getCmd(
                SnmpEngine(),
                CommunityData(community),
                UdpTransportTarget((ip, 161), timeout=timeout, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            )
        )
        
        if errorIndication or errorStatus:
            return None
        
        for varBind in varBinds:
            return str(varBind[1])
        
        return None
        
    except Exception as e:
        logger.debug(f"SNMP erro para {ip}: {e}")
        return None


def get_printer_info_snmp(ip: str, community: str = 'public') -> Optional[Dict]:
    """
    Obtém informações completas da impressora via SNMP.
    
    Args:
        ip: Endereço IP da impressora
        community: Community string
    
    Returns:
        Dict com informações ou None
    """
    if not SNMP_AVAILABLE:
        return None
    
    try:
        # Busca informações básicas
        sys_descr = get_snmp_value(ip, SNMP_OIDS['sysDescr'], community)
        
        if not sys_descr:
            return None
        
        info = {
            'ip': ip,
            'description': sys_descr,
            'name': get_snmp_value(ip, SNMP_OIDS['sysName'], community) or ip,
            'location': get_snmp_value(ip, SNMP_OIDS['sysLocation'], community) or '',
            'serial': get_snmp_value(ip, SNMP_OIDS['prtGeneralSerialNumber'], community) or '',
            'page_count': None,
            'is_printer': False,
            'duplex_capable': False,
        }
        
        # Verifica se é impressora
        printer_keywords = ['printer', 'print', 'mfp', 'laserjet', 'officejet', 
                          'deskjet', 'phaser', 'imagerunner', 'bizhub', 'ecosys',
                          'lexmark', 'brother', 'epson', 'canon', 'ricoh', 'xerox',
                          'kyocera', 'samsung', 'dell', 'konica']
        
        descr_lower = sys_descr.lower()
        info['is_printer'] = any(kw in descr_lower for kw in printer_keywords)
        
        if info['is_printer']:
            # Tenta obter contador de páginas
            page_count = get_snmp_value(ip, SNMP_OIDS['prtMarkerLifeCount'], community)
            if page_count:
                try:
                    info['page_count'] = int(page_count)
                except ValueError:
                    pass
            
            # Detecta capacidade duplex (heurística baseada no modelo)
            duplex_keywords = ['duplex', 'dn', 'dtn', 'mfp', 'laserjet pro', 
                             'm4', 'm553', 'm402', 'm477', 'm605', 'm506']
            info['duplex_capable'] = any(kw in descr_lower for kw in duplex_keywords)
        
        return info
        
    except Exception as e:
        logger.debug(f"Erro ao obter info SNMP de {ip}: {e}")
        return None


def detect_duplex_capability(ip: str, community: str = 'public') -> Optional[bool]:
    """
    Detecta se impressora suporta duplex via SNMP.
    
    Args:
        ip: Endereço IP
        community: Community string
    
    Returns:
        True/False ou None se não detectável
    """
    info = get_printer_info_snmp(ip, community)
    if info:
        return info.get('duplex_capable')
    return None


def scan_ip_range(network: str, port: int = 9100, 
                  timeout: float = 0.5) -> List[str]:
    """
    Scan de uma faixa de IPs para encontrar dispositivos com porta aberta.
    
    Args:
        network: Rede no formato 192.168.1.0/24 ou 192.168.1
        port: Porta a verificar
        timeout: Timeout por conexão
    
    Returns:
        Lista de IPs com porta aberta
    """
    # Extrai base da rede
    if '/' in network:
        base = network.split('/')[0].rsplit('.', 1)[0]
    else:
        base = network.rsplit('.', 1)[0] if '.' in network else network
    
    found_ips = []
    
    def check_ip(ip: str) -> Optional[str]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            if result == 0:
                return ip
        except:
            pass
        return None
    
    # Gera lista de IPs
    ips_to_scan = [f"{base}.{i}" for i in range(1, 255)]
    
    # Scan paralelo
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(check_ip, ip): ip for ip in ips_to_scan}
        for future in as_completed(futures, timeout=30):
            try:
                result = future.result()
                if result:
                    found_ips.append(result)
            except:
                pass
    
    return found_ips


def discover_printers_snmp(network: str, community: str = 'public',
                           max_workers: int = 20) -> List[Dict]:
    """
    Descobre impressoras na rede via SNMP.
    
    Args:
        network: Rede a escanear (192.168.1.0/24)
        community: Community string SNMP
        max_workers: Threads paralelas
    
    Returns:
        Lista de impressoras encontradas
    """
    printers = []
    
    # Primeiro, escaneia porta SNMP (161) ou JetDirect (9100)
    logger.info(f"Iniciando descoberta SNMP na rede {network}...")
    
    # Scan de portas para encontrar dispositivos
    devices = scan_ip_range(network, port=9100, timeout=0.3)
    
    logger.info(f"Encontrados {len(devices)} dispositivos com porta 9100 aberta")
    
    # Para cada dispositivo, tenta obter info SNMP
    if SNMP_AVAILABLE:
        def get_info(ip):
            return get_printer_info_snmp(ip, community)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(get_info, ip): ip for ip in devices}
            for future in as_completed(futures, timeout=60):
                try:
                    info = future.result()
                    if info and info.get('is_printer'):
                        printers.append(info)
                except Exception as e:
                    logger.debug(f"Erro ao processar dispositivo: {e}")
    else:
        # Sem SNMP, apenas registra IPs encontrados
        for ip in devices:
            printers.append({
                'ip': ip,
                'name': f"Impressora {ip}",
                'description': 'Detectada via porta 9100',
                'is_printer': True,
                'duplex_capable': None,
            })
    
    logger.info(f"Descoberta concluída: {len(printers)} impressoras encontradas")
    return printers


def auto_register_printer(conn, printer_info: Dict) -> Tuple[bool, str]:
    """
    Cadastra automaticamente uma impressora descoberta.
    
    Args:
        conn: Conexão SQLite
        printer_info: Dict com informações da impressora
    
    Returns:
        Tuple (sucesso, mensagem)
    """
    try:
        name = printer_info.get('name', printer_info.get('ip', 'Unknown'))
        ip = printer_info.get('ip', '')
        
        # Verifica se já existe
        existing = conn.execute(
            "SELECT printer_name FROM printers WHERE printer_name = ? OR ip = ?",
            (name, ip)
        ).fetchone()
        
        if existing:
            return False, f"Impressora {name} já cadastrada"
        
        # Determina tipo (duplex/simplex)
        tipo = 'duplex' if printer_info.get('duplex_capable') else 'simplex'
        
        # Cadastra
        conn.execute(
            """INSERT INTO printers (printer_name, ip, tipo, sector)
               VALUES (?, ?, ?, ?)""",
            (name, ip, tipo, 'Descoberta Automática')
        )
        conn.commit()
        
        logger.info(f"Impressora {name} ({ip}) cadastrada automaticamente como {tipo}")
        return True, f"Impressora {name} cadastrada como {tipo}"
        
    except Exception as e:
        logger.error(f"Erro ao cadastrar impressora: {e}")
        return False, f"Erro: {e}"


def get_local_network() -> Optional[str]:
    """
    Detecta a rede local do servidor.
    
    Returns:
        Rede no formato 192.168.1.0/24 ou None
    """
    try:
        # Obtém IP local
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        
        # Extrai rede (assumindo /24)
        base = '.'.join(local_ip.split('.')[:-1])
        return f"{base}.0/24"
    except:
        return None


# Exporta funções públicas
__all__ = [
    'SNMP_AVAILABLE',
    'is_snmp_available',
    'get_snmp_value',
    'get_printer_info_snmp',
    'detect_duplex_capability',
    'scan_ip_range',
    'discover_printers_snmp',
    'auto_register_printer',
    'get_local_network',
]
