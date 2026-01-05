#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Teste para Descoberta de Impressoras
Verifica se o ambiente está configurado corretamente para encontrar impressoras na rede
"""

import socket
import subprocess
import platform
import sys
import re
from typing import List, Dict, Tuple

# Cores para output (Windows)
try:
    import colorama
    colorama.init()
    GREEN = colorama.Fore.GREEN
    RED = colorama.Fore.RED
    YELLOW = colorama.Fore.YELLOW
    BLUE = colorama.Fore.BLUE
    RESET = colorama.Fore.RESET
    BOLD = colorama.Style.BRIGHT
    NORMAL = colorama.Style.NORMAL
except ImportError:
    GREEN = RED = YELLOW = BLUE = RESET = BOLD = NORMAL = ""

def print_header(text: str):
    """Imprime cabeçalho formatado"""
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}{text:^70}{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")

def print_success(text: str):
    """Imprime mensagem de sucesso"""
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text: str):
    """Imprime mensagem de erro"""
    print(f"{RED}❌ {text}{RESET}")

def print_warning(text: str):
    """Imprime mensagem de aviso"""
    print(f"{YELLOW}⚠️  {text}{RESET}")

def print_info(text: str):
    """Imprime mensagem informativa"""
    print(f"{BLUE}ℹ️  {text}{RESET}")

def test_1_network_info() -> Tuple[str, str]:
    """Teste 1: Informações de Rede"""
    print_header("TESTE 1: Informações de Rede")
    
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        ip_parts = local_ip.split('.')
        network_base = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"
        
        print_success(f"Hostname: {hostname}")
        print_success(f"IP Local: {local_ip}")
        print_success(f"Sub-rede: {network_base}.x")
        
        return local_ip, network_base
    except Exception as e:
        print_error(f"Erro ao obter informações de rede: {e}")
        return None, None

def test_2_firewall_check() -> bool:
    """Teste 2: Verificação de Firewall"""
    print_header("TESTE 2: Verificação de Firewall")
    
    if platform.system() != 'Windows':
        print_warning("Teste de firewall só disponível no Windows")
        return True
    
    try:
        # Tenta executar comando PowerShell para verificar firewall
        ps_command = """
        $profiles = Get-NetFirewallProfile
        $blocked = $false
        foreach ($profile in $profiles) {
            if ($profile.Enabled -and $profile.DefaultOutboundAction -eq 'Block') {
                $blocked = $true
                Write-Output "Perfil $($profile.Name): Bloqueando conexões de saída"
            }
        }
        if (-not $blocked) {
            Write-Output "OK"
        }
        """
        
        result = subprocess.run(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-NoProfile', '-Command', ps_command],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        
        if "OK" in result.stdout:
            print_success("Firewall não está bloqueando conexões de saída por padrão")
            return True
        else:
            print_warning("Firewall pode estar bloqueando conexões")
            print_info("Recomendação: Adicione Python às exceções do firewall")
            return False
    except Exception as e:
        print_warning(f"Não foi possível verificar firewall: {e}")
        print_info("Recomendação: Verifique manualmente as configurações de firewall")
        return True  # Assume OK se não conseguir verificar

def test_3_socket_permissions() -> bool:
    """Teste 3: Permissões de Socket"""
    print_header("TESTE 3: Permissões de Socket (Conexões de Rede)")
    
    try:
        # Tenta criar um socket e conectar em um IP externo
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.settimeout(2)
        
        # Tenta conectar em um servidor público (Google DNS)
        result = test_socket.connect_ex(('8.8.8.8', 53))
        test_socket.close()
        
        if result == 0:
            print_success("Consegue criar conexões de rede (socket)")
            return True
        else:
            print_error("Não consegue criar conexões de rede")
            print_info("Possível causa: Firewall bloqueando ou sem permissões")
            return False
    except socket.error as e:
        print_error(f"Erro ao testar socket: {e}")
        return False
    except Exception as e:
        print_error(f"Erro inesperado: {e}")
        return False

def test_4_powershell_access() -> bool:
    """Teste 4: Acesso ao PowerShell"""
    print_header("TESTE 4: Acesso ao PowerShell")
    
    if platform.system() != 'Windows':
        print_warning("PowerShell só disponível no Windows")
        return True
    
    try:
        result = subprocess.run(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-NoProfile', '-Command', 'Write-Output "OK"'],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        
        if result.returncode == 0 and "OK" in result.stdout:
            print_success("Consegue executar comandos PowerShell")
            return True
        else:
            print_error("Não consegue executar PowerShell")
            return False
    except Exception as e:
        print_error(f"Erro ao testar PowerShell: {e}")
        return False

def test_5_wmi_access() -> bool:
    """Teste 5: Acesso ao WMI"""
    print_header("TESTE 5: Acesso ao WMI (Windows Management Instrumentation)")
    
    if platform.system() != 'Windows':
        print_warning("WMI só disponível no Windows")
        return True
    
    try:
        ps_command = """
        try {
            Get-WmiObject -Class Win32_Printer -ErrorAction Stop | Select-Object -First 1 | Out-Null
            Write-Output "OK"
        } catch {
            Write-Output "ERROR: $_"
        }
        """
        
        result = subprocess.run(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-NoProfile', '-Command', ps_command],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        
        if result.returncode == 0 and "OK" in result.stdout:
            print_success("Consegue acessar WMI")
            return True
        else:
            print_warning("Não consegue acessar WMI completamente")
            print_info("Pode funcionar mesmo assim, mas algumas funcionalidades podem estar limitadas")
            return False
    except Exception as e:
        print_warning(f"Erro ao testar WMI: {e}")
        return False

def test_6_scan_single_ip(ip: str, port: int = 9100) -> bool:
    """Teste 6: Scan de IP Único"""
    print_header(f"TESTE 6: Scan de IP Único ({ip}:{port})")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((ip, port))
        sock.close()
        
        if result == 0:
            print_success(f"Porta {port} está aberta no IP {ip}")
            return True
        else:
            print_warning(f"Porta {port} não está acessível no IP {ip}")
            print_info("Isso é normal se não houver impressora nesse IP")
            return False
    except Exception as e:
        print_warning(f"Erro ao testar {ip}:{port}: {e}")
        return False

def test_7_network_scan(network_base: str, sample_size: int = 10) -> List[str]:
    """Teste 7: Scan de Amostra da Rede"""
    print_header(f"TESTE 7: Scan de Amostra da Rede ({sample_size} IPs)")
    
    if not network_base:
        print_error("Não foi possível determinar a sub-rede")
        return []
    
    printer_ports = [9100, 631, 515]
    found_ips = []
    
    # Escaneia uma amostra pequena
    test_ips = list(range(1, sample_size + 1))
    
    print_info(f"Escaneando {len(test_ips)} IPs na rede {network_base}.x...")
    print_info("Portas testadas: 9100 (JetDirect), 631 (IPP), 515 (LPR)")
    print()
    
    for i in test_ips:
        ip = f"{network_base}.{i}"
        found_any = False
        
        for port in printer_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.3)
                result = sock.connect_ex((ip, port))
                sock.close()
                
                if result == 0:
                    if not found_any:
                        print_success(f"{ip}: Porta {port} aberta")
                        found_ips.append(ip)
                        found_any = True
            except:
                pass
    
    if found_ips:
        print()
        print_success(f"Encontrados {len(found_ips)} dispositivos com portas de impressora:")
        for ip in found_ips:
            print(f"  - {ip}")
    else:
        print()
        print_warning(f"Nenhum dispositivo com portas de impressora encontrado nos {sample_size} primeiros IPs")
        print_info("Isso pode ser normal se:")
        print_info("  - Não houver impressoras nessa faixa de IPs")
        print_info("  - Firewall bloqueando")
        print_info("  - Impressoras em outra faixa de IPs")
    
    return found_ips

def test_8_installed_printers() -> List[Dict]:
    """Teste 8: Impressoras Instaladas"""
    print_header("TESTE 8: Impressoras Instaladas no Windows")
    
    if platform.system() != 'Windows':
        print_warning("Só disponível no Windows")
        return []
    
    try:
        ps_command = """
        Get-WmiObject -Class Win32_Printer | 
        Select-Object Name, PortName, Network, Shared | 
        ConvertTo-Json -Depth 2 -Compress
        """
        
        result = subprocess.run(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-NoProfile', '-Command', ps_command],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        
        if result.returncode == 0 and result.stdout.strip():
            try:
                import json
                printers = json.loads(result.stdout.strip())
                if isinstance(printers, dict):
                    printers = [printers]
                
                print_success(f"Encontradas {len(printers)} impressoras instaladas:")
                print()
                
                network_printers = []
                for printer in printers:
                    name = printer.get('Name', 'N/A')
                    port = printer.get('PortName', 'N/A')
                    network = printer.get('Network', False)
                    shared = printer.get('Shared', False)
                    
                    status = []
                    if network:
                        status.append("Rede")
                    if shared:
                        status.append("Compartilhada")
                    
                    status_str = f" ({', '.join(status)})" if status else ""
                    
                    print(f"  printer {name}")
                    print(f"     Porta: {port}{status_str}")
                    
                    # Extrai IP se houver
                    ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', port)
                    if ip_match:
                        ip = ip_match.group(1)
                        network_printers.append({'name': name, 'ip': ip, 'port': port})
                        print(f"     IP: {ip}")
                    print()
                
                if network_printers:
                    print_success(f"{len(network_printers)} impressoras de rede encontradas")
                    return network_printers
                else:
                    print_warning("Nenhuma impressora de rede encontrada (apenas locais)")
                    return []
            except json.JSONDecodeError:
                print_warning("Erro ao processar resultado do WMI")
                return []
        else:
            print_warning("Nenhuma impressora instalada encontrada")
            return []
    except Exception as e:
        print_warning(f"Erro ao buscar impressoras: {e}")
        return []

def generate_report(results: Dict) -> None:
    """Gera relatório final"""
    print_header("RELATÓRIO FINAL")
    
    total_tests = len([k for k in results.keys() if k.startswith('test_')])
    passed_tests = sum(1 for v in results.values() if isinstance(v, bool) and v)
    
    print(f"{BOLD}Testes Executados: {total_tests}{RESET}")
    print(f"{GREEN}Testes Aprovados: {passed_tests}{RESET}")
    print(f"{RED}Testes com Problemas: {total_tests - passed_tests}{RESET}")
    print()
    
    if passed_tests == total_tests:
        print_success("🎉 Todos os testes passaram! O ambiente está configurado corretamente.")
        print()
        print_info("Você pode usar a descoberta de impressoras sem problemas.")
    else:
        print_warning("⚠️  Alguns testes falharam. Verifique as recomendações abaixo:")
        print()
        
        if not results.get('test_2_firewall', True):
            print_error("FIREWALL: Configure exceções para Python no Windows Defender Firewall")
            print()
        
        if not results.get('test_3_socket', False):
            print_error("REDE: Não consegue criar conexões de rede")
            print_info("  - Verifique firewall")
            print_info("  - Verifique permissões de administrador")
            print()
        
        if not results.get('test_4_powershell', False):
            print_error("POWERSHELL: Não consegue executar comandos PowerShell")
            print_info("  - Verifique se PowerShell está instalado")
            print_info("  - Execute como administrador")
            print()
        
        if not results.get('test_5_wmi', False):
            print_warning("WMI: Acesso limitado ao WMI")
            print_info("  - Execute como administrador para melhor acesso")
            print_info("  - Pode funcionar mesmo assim")
            print()
    
    # Informações adicionais
    if results.get('network_base'):
        print()
        print_info(f"Sub-rede detectada: {results['network_base']}.x")
        print_info("O sistema escaneará IPs de 1 a 254 nessa sub-rede")
    
    if results.get('found_ips'):
        print()
        print_success(f"Dispositivos encontrados no teste: {len(results['found_ips'])}")
    
    if results.get('installed_printers'):
        print()
        print_success(f"Impressoras instaladas: {len(results['installed_printers'])}")

def main():
    """Função principal"""
    print_header("TESTE DE CONFIGURAÇÃO - DESCOBERTA DE IMPRESSORAS")
    print()
    print("Este script verifica se o ambiente está configurado corretamente")
    print("para descobrir impressoras na rede.")
    print()
    
    results = {}
    
    # Teste 1: Informações de rede
    local_ip, network_base = test_1_network_info()
    results['local_ip'] = local_ip
    results['network_base'] = network_base
    
    # Teste 2: Firewall
    results['test_2_firewall'] = test_2_firewall_check()
    
    # Teste 3: Permissões de socket
    results['test_3_socket'] = test_3_socket_permissions()
    
    # Teste 4: PowerShell
    results['test_4_powershell'] = test_4_powershell_access()
    
    # Teste 5: WMI
    results['test_5_wmi'] = test_5_wmi_access()
    
    # Teste 6: Scan de IP único (se tiver network_base)
    if network_base:
        # Testa o próprio IP + alguns próximos
        test_ip = f"{network_base}.1"
        results['test_6_scan'] = test_6_scan_single_ip(test_ip)
    
    # Teste 7: Scan de amostra
    if network_base:
        found_ips = test_7_network_scan(network_base, sample_size=20)
        results['found_ips'] = found_ips
    
    # Teste 8: Impressoras instaladas
    installed_printers = test_8_installed_printers()
    results['installed_printers'] = installed_printers
    
    # Gera relatório
    generate_report(results)
    
    print()
    print_header("TESTE CONCLUÍDO")
    print()
    print("Pressione Enter para sair...")
    try:
        input()
    except:
        pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTeste interrompido pelo usuário.")
        sys.exit(0)
    except Exception as e:
        print_error(f"Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

