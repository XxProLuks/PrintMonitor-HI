"""
Módulo de Integração com Active Directory
==========================================

Sincroniza usuários e setores do AD via LDAP.

Configuração (via variáveis de ambiente ou .env):
- AD_SERVER: ldap://seu-dc.dominio.local
- AD_DOMAIN: DOMINIO
- AD_USER: usuario_servico
- AD_PASSWORD: senha
- AD_BASE_DN: DC=dominio,DC=local
- AD_USERS_OU: OU=Usuarios,DC=dominio,DC=local (opcional)
"""

import logging
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Flag de disponibilidade do LDAP
LDAP_AVAILABLE = False

try:
    from ldap3 import Server, Connection, ALL, NTLM, SUBTREE
    LDAP_AVAILABLE = True
    logger.info("✅ ldap3 disponível para integração AD")
except ImportError:
    logger.warning(
        "⚠️ ldap3 não instalado. Integração AD desabilitada.\n"
        "   💡 Para habilitar: pip install ldap3"
    )


def get_ad_config() -> Dict[str, str]:
    """
    Obtém configuração do AD das variáveis de ambiente.
    
    Returns:
        Dict com configurações do AD
    """
    return {
        'server': os.getenv('AD_SERVER', ''),
        'domain': os.getenv('AD_DOMAIN', ''),
        'user': os.getenv('AD_USER', ''),
        'password': os.getenv('AD_PASSWORD', ''),
        'base_dn': os.getenv('AD_BASE_DN', ''),
        'users_ou': os.getenv('AD_USERS_OU', ''),
    }


def is_ad_configured() -> bool:
    """Verifica se AD está configurado."""
    config = get_ad_config()
    return bool(config['server'] and config['domain'] and config['user'])


def test_ad_connection() -> Tuple[bool, str]:
    """
    Testa conexão com o AD.
    
    Returns:
        Tuple (sucesso, mensagem)
    """
    if not LDAP_AVAILABLE:
        return False, "ldap3 não está instalado. Execute: pip install ldap3"
    
    config = get_ad_config()
    
    if not config['server']:
        return False, "AD_SERVER não configurado"
    if not config['domain']:
        return False, "AD_DOMAIN não configurado"
    if not config['user']:
        return False, "AD_USER não configurado"
    
    try:
        server = Server(config['server'], get_info=ALL)
        
        # Monta usuário no formato DOMAIN\user
        ad_user = f"{config['domain']}\\{config['user']}"
        
        conn = Connection(
            server,
            user=ad_user,
            password=config['password'],
            authentication=NTLM,
            auto_bind=True
        )
        
        # Testa busca simples
        base_dn = config['base_dn'] or config['users_ou']
        if base_dn:
            conn.search(base_dn, '(objectClass=*)', search_scope=SUBTREE, size_limit=1)
        
        conn.unbind()
        
        return True, f"Conexão com AD bem-sucedida ({config['server']})"
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Erro ao conectar ao AD: {error_msg}")
        return False, f"Erro de conexão: {error_msg}"


def sync_users_from_ad(conn_db=None) -> Dict[str, any]:
    """
    Sincroniza usuários do AD para o banco de dados local.
    
    Args:
        conn_db: Conexão com banco SQLite (opcional)
    
    Returns:
        Dict com resultado {success, users_synced, users_created, users_updated, errors}
    """
    if not LDAP_AVAILABLE:
        return {
            'success': False,
            'message': 'ldap3 não instalado',
            'users_synced': 0,
            'errors': ['ldap3 não está disponível']
        }
    
    config = get_ad_config()
    
    if not is_ad_configured():
        return {
            'success': False,
            'message': 'AD não configurado',
            'users_synced': 0,
            'errors': ['Configuração do AD incompleta']
        }
    
    result = {
        'success': False,
        'users_synced': 0,
        'users_created': 0,
        'users_updated': 0,
        'errors': [],
        'users': []
    }
    
    try:
        server = Server(config['server'], get_info=ALL)
        ad_user = f"{config['domain']}\\{config['user']}"
        
        conn = Connection(
            server,
            user=ad_user,
            password=config['password'],
            authentication=NTLM,
            auto_bind=True
        )
        
        # Base DN para busca
        base_dn = config['users_ou'] or config['base_dn']
        
        if not base_dn:
            result['errors'].append('AD_BASE_DN ou AD_USERS_OU não configurado')
            return result
        
        # Busca usuários ativos
        search_filter = '(&(objectClass=user)(objectCategory=person)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))'
        
        conn.search(
            base_dn,
            search_filter,
            search_scope=SUBTREE,
            attributes=['sAMAccountName', 'displayName', 'department', 'mail', 'distinguishedName']
        )
        
        users_found = []
        for entry in conn.entries:
            user_data = {
                'username': str(entry.sAMAccountName) if hasattr(entry, 'sAMAccountName') else None,
                'display_name': str(entry.displayName) if hasattr(entry, 'displayName') else None,
                'department': str(entry.department) if hasattr(entry, 'department') else None,
                'email': str(entry.mail) if hasattr(entry, 'mail') else None,
                'dn': str(entry.distinguishedName) if hasattr(entry, 'distinguishedName') else None,
            }
            
            if user_data['username']:
                users_found.append(user_data)
        
        logger.info(f"AD: Encontrados {len(users_found)} usuários")
        
        # Sincroniza com banco local se conexão fornecida
        if conn_db and users_found:
            for user in users_found:
                try:
                    # Verifica se usuário existe
                    existing = conn_db.execute(
                        "SELECT user, sector FROM users WHERE user = ?",
                        (user['username'],)
                    ).fetchone()
                    
                    sector = user['department'] or 'Sem Setor'
                    
                    if existing:
                        # Atualiza setor se diferente
                        if existing[1] != sector:
                            conn_db.execute(
                                "UPDATE users SET sector = ? WHERE user = ?",
                                (sector, user['username'])
                            )
                            result['users_updated'] += 1
                    else:
                        # Cria novo usuário
                        conn_db.execute(
                            "INSERT INTO users (user, sector) VALUES (?, ?)",
                            (user['username'], sector)
                        )
                        result['users_created'] += 1
                    
                    result['users_synced'] += 1
                    
                except Exception as e:
                    result['errors'].append(f"Erro ao sincronizar {user['username']}: {e}")
            
            conn_db.commit()
        
        result['users'] = users_found
        result['success'] = True
        result['message'] = f"Sincronizados {result['users_synced']} usuários do AD"
        
        conn.unbind()
        
    except Exception as e:
        logger.error(f"Erro na sincronização AD: {e}", exc_info=True)
        result['errors'].append(str(e))
        result['message'] = f"Erro: {e}"
    
    return result


def sync_sectors_from_ad(conn_db=None) -> Dict[str, any]:
    """
    Sincroniza setores (OUs/departamentos) do AD.
    
    Args:
        conn_db: Conexão com banco SQLite (opcional)
    
    Returns:
        Dict com resultado
    """
    if not LDAP_AVAILABLE:
        return {
            'success': False,
            'message': 'ldap3 não instalado',
            'sectors': []
        }
    
    config = get_ad_config()
    
    if not is_ad_configured():
        return {
            'success': False,
            'message': 'AD não configurado',
            'sectors': []
        }
    
    result = {
        'success': False,
        'sectors': [],
        'errors': []
    }
    
    try:
        server = Server(config['server'], get_info=ALL)
        ad_user = f"{config['domain']}\\{config['user']}"
        
        conn = Connection(
            server,
            user=ad_user,
            password=config['password'],
            authentication=NTLM,
            auto_bind=True
        )
        
        base_dn = config['base_dn']
        
        if not base_dn:
            result['errors'].append('AD_BASE_DN não configurado')
            return result
        
        # Busca departamentos únicos dos usuários
        search_filter = '(&(objectClass=user)(objectCategory=person)(department=*))'
        
        conn.search(
            base_dn,
            search_filter,
            search_scope=SUBTREE,
            attributes=['department']
        )
        
        sectors_set = set()
        for entry in conn.entries:
            if hasattr(entry, 'department') and entry.department:
                sectors_set.add(str(entry.department))
        
        result['sectors'] = sorted(list(sectors_set))
        result['success'] = True
        result['message'] = f"Encontrados {len(result['sectors'])} setores no AD"
        
        conn.unbind()
        
        logger.info(f"AD: Encontrados {len(result['sectors'])} setores")
        
    except Exception as e:
        logger.error(f"Erro ao buscar setores do AD: {e}", exc_info=True)
        result['errors'].append(str(e))
        result['message'] = f"Erro: {e}"
    
    return result


def authenticate_with_ad(username: str, password: str) -> Tuple[bool, Optional[Dict]]:
    """
    Autentica usuário via AD.
    
    Args:
        username: Nome de usuário (sem domínio)
        password: Senha do usuário
    
    Returns:
        Tuple (sucesso, dados_usuario ou None)
    """
    if not LDAP_AVAILABLE:
        return False, None
    
    config = get_ad_config()
    
    if not is_ad_configured():
        return False, None
    
    try:
        server = Server(config['server'], get_info=ALL)
        ad_user = f"{config['domain']}\\{username}"
        
        conn = Connection(
            server,
            user=ad_user,
            password=password,
            authentication=NTLM,
            auto_bind=True
        )
        
        # Busca informações do usuário
        base_dn = config['base_dn']
        search_filter = f'(sAMAccountName={username})'
        
        conn.search(
            base_dn,
            search_filter,
            search_scope=SUBTREE,
            attributes=['sAMAccountName', 'displayName', 'department', 'mail', 'memberOf']
        )
        
        if conn.entries:
            entry = conn.entries[0]
            user_info = {
                'username': str(entry.sAMAccountName) if hasattr(entry, 'sAMAccountName') else username,
                'display_name': str(entry.displayName) if hasattr(entry, 'displayName') else username,
                'department': str(entry.department) if hasattr(entry, 'department') else None,
                'email': str(entry.mail) if hasattr(entry, 'mail') else None,
                'groups': [str(g) for g in entry.memberOf] if hasattr(entry, 'memberOf') else [],
            }
            conn.unbind()
            logger.info(f"AD: Autenticação bem-sucedida para {username}")
            return True, user_info
        
        conn.unbind()
        return True, {'username': username}
        
    except Exception as e:
        logger.warning(f"AD: Falha na autenticação de {username}: {e}")
        return False, None


# Exporta funções públicas
__all__ = [
    'LDAP_AVAILABLE',
    'is_ad_configured',
    'test_ad_connection',
    'sync_users_from_ad',
    'sync_sectors_from_ad',
    'authenticate_with_ad',
    'get_ad_config',
]
