from flask import (
    Flask,
    request,
    render_template,
    jsonify,
    redirect,
    url_for,
    session,
    flash,
    send_file,
)
import sqlite3
import os
import sys
from datetime import datetime, timedelta
import ctypes
import ctypes.wintypes
from functools import wraps
from contextlib import contextmanager
import pandas as pd  # type: ignore
import io
import logging
import threading
from typing import Optional, List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from werkzeug.security import generate_password_hash, check_password_hash

# Configurar logging primeiro (antes de usar logger)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# WebSocket para atualizações em tempo real
try:
    from flask_socketio import SocketIO, emit, join_room, leave_room
    SOCKETIO_AVAILABLE = True
    logger.info("✅ WebSocket habilitado (flask-socketio)")
except ImportError:
    SOCKETIO_AVAILABLE = False
    SocketIO = None
    emit = None
    join_room = None
    leave_room = None
    # Logger ainda não está definido aqui, então vamos criar um temporário
    if 'logger' not in globals():
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
    logger.warning(
        "⚠️  flask-socketio não instalado. WebSocket desabilitado.\n"
        "   💡 Para habilitar: pip install flask-socketio\n"
        "   ⚠️  Sem WebSocket, atualizações em tempo real não funcionarão."
    )

# Importa módulo centralizado de cálculos de impressão
from modules.calculo_impressao import (
    calcular_folhas,
    calcular_folhas_fisicas,
    normalizar_duplex,
    normalizar_paginas,
    normalizar_copias,
    calcular_economia_duplex,
    validar_evento,
    get_sql_folhas_expression,
)

# Importa funções auxiliares do banco de dados
from modules.helper_db import (
    obter_duplex_da_impressora,
    obter_tipo_impressora,
)

# Importa connection pooling
from modules.db_pool import init_db_pool, get_db_connection

# Carrega variáveis de ambiente (opcional)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv não instalado - usa variáveis de ambiente do sistema
    pass

app = Flask(__name__)

# ============================================================================
# CONFIGURAÇÃO DE SEGURANÇA - SECRET_KEY
# ============================================================================
def get_secret_key():
    """
    Obtém a SECRET_KEY de forma segura.
    
    Em produção, a SECRET_KEY DEVE ser definida em variáveis de ambiente.
    Em desenvolvimento, gera uma chave temporária se não estiver definida.
    """
    secret_key = os.getenv('SECRET_KEY')
    
    if secret_key:
        return secret_key
    
    # Verifica se está em produção
    is_production = os.getenv('FLASK_ENV') == 'production' or os.getenv('ENVIRONMENT') == 'production'
    
    if is_production:
        # Em produção, falha se SECRET_KEY não estiver definida
        raise ValueError(
            "❌ ERRO CRÍTICO: SECRET_KEY não está definida em produção!\n"
            "   Defina a variável de ambiente SECRET_KEY antes de iniciar o servidor.\n"
            "   Para gerar uma chave segura, execute:\n"
            "   python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    
    # Em desenvolvimento, gera uma chave temporária
    import secrets
    temp_key = secrets.token_hex(32)
    logger.warning(
        "⚠️  SECRET_KEY não definida - usando chave temporária gerada.\n"
        "   ⚠️  Esta chave será diferente a cada reinício em desenvolvimento.\n"
        "   💡 Para produção, defina SECRET_KEY em variáveis de ambiente."
    )
    return temp_key

app.secret_key = get_secret_key()

# Inicializa WebSocket (SocketIO)
socketio = None
if SOCKETIO_AVAILABLE:
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    logging.getLogger(__name__).info("🔌 WebSocket (SocketIO) habilitado!")
else:
    logging.getLogger(__name__).warning("⚠️ flask-socketio não instalado. WebSocket desabilitado.")

# Usa caminho relativo ao diretório do servidor (deve vir antes de usar BASE_DIR)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, os.getenv('DB_NAME', 'print_events.db'))

# Configurações de segurança
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = int(os.getenv('SESSION_LIFETIME', 3600))  # 1 hora padrão

# Configurar logging (após definir BASE_DIR)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, 'servidor.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Rate Limiting (opcional - requer flask-limiter)
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=os.getenv('RATELIMIT_STORAGE_URL', 'memory://')
    )
    RATE_LIMIT_ENABLED = True
    logger.info("✅ Rate limiting habilitado (flask-limiter)")
except ImportError:
    logger.warning(
        "⚠️  flask-limiter não instalado. Rate limiting desabilitado.\n"
        "   💡 Para habilitar: pip install flask-limiter\n"
        "   ⚠️  Sem rate limiting, o servidor pode ser vulnerável a ataques de força bruta."
    )
    RATE_LIMIT_ENABLED = False
    limiter = None

# CSRF Protection (opcional - requer flask-wtf)
try:
    from flask_wtf.csrf import CSRFProtect
    csrf = CSRFProtect(app)
    CSRF_ENABLED = True
    # Flask-WTF automaticamente disponibiliza csrf_token() nos templates
    logger.info("✅ CSRF protection habilitado (flask-wtf)")
except ImportError:
    logger.warning(
        "⚠️  flask-wtf não instalado. CSRF protection desabilitado.\n"
        "   💡 Para habilitar: pip install flask-wtf\n"
        "   ⚠️  Sem CSRF protection, o servidor pode ser vulnerável a ataques CSRF."
    )
    CSRF_ENABLED = False
    csrf = None

# Helper para desabilitar CSRF em endpoints específicos
def csrf_exempt_if_enabled(f):
    """Decorator que desabilita CSRF se estiver habilitado"""
    if CSRF_ENABLED and csrf:
        return csrf.exempt(f)
    return f

# Compressão HTTP (opcional)
try:
    from flask_compress import Compress
    Compress(app)
    COMPRESS_ENABLED = True
except ImportError:
    logger.warning("flask-compress não instalado. Compressão desabilitada.")
    COMPRESS_ENABLED = False

# BASE_DIR e DB já foram definidos acima

# =============================================================================
# HELPER PARA CONEXÃO COM BANCO (Connection Pooling com Fallback)
# =============================================================================
@contextmanager
def get_db():
    """
    Helper para obter conexão do banco de dados.
    Tenta usar connection pool, faz fallback para conexão direta se necessário.
    
    Usage:
        with get_db() as conn:
            cursor = conn.execute("SELECT ...")
    """
    conn = None
    pool_context = None
    
    try:
        # Tenta usar connection pool
        try:
            pool_context = get_db_connection()
            conn = pool_context.__enter__()
            try:
                yield conn
            except GeneratorExit:
                # Generator está sendo fechado (normal em returns)
                raise
            except:
                # Se houver exceção, garante que o context manager seja fechado corretamente
                exc_type, exc_val, exc_tb = sys.exc_info()
                try:
                    pool_context.__exit__(exc_type, exc_val, exc_tb)
                except:
                    pass
                raise
            finally:
                # Sempre fecha o pool, mesmo em caso de return
                if pool_context:
                    try:
                        pool_context.__exit__(None, None, None)
                    except:
                        pass
                    pool_context = None
        except (RuntimeError, AttributeError, NameError, ImportError, TypeError):
            # Fallback para conexão direta se pool não estiver disponível
            if pool_context:
                try:
                    pool_context.__exit__(None, None, None)
                except:
                    pass
                pool_context = None
            
            conn = sqlite3.connect(DB)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
                    conn = None
    except GeneratorExit:
        # Generator está sendo fechado, garante limpeza
        if pool_context:
            try:
                pool_context.__exit__(None, None, None)
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass
        raise
    except Exception:
        # Garante que conexão seja fechada em caso de erro
        if pool_context:
            try:
                exc_type, exc_val, exc_tb = sys.exc_info()
                pool_context.__exit__(exc_type, exc_val, exc_tb)
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass
        raise


def get_job_group_by_clause(has_job_id: bool = True) -> str:
    """
    Retorna a cláusula GROUP BY correta para agrupar eventos por job único.
    
    Args:
        has_job_id: Se True, usa job_id quando disponível, senão usa combinação de campos
    
    Returns:
        String com a cláusula GROUP BY
    """
    if has_job_id:
        return """CASE 
            WHEN job_id IS NOT NULL AND job_id != '' THEN 
                job_id || '|' || COALESCE(printer_name, '') || '|' || date
            ELSE 
                user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
        END"""
    else:
        return """user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date"""


# --- SID para nome de usuário ---
# NOTA: calcular_folhas_fisicas() foi movida para modules/calculo_impressao.py
# Usar: from modules.calculo_impressao import calcular_folhas_fisicas


# Função obter_duplex_da_impressora movida para modules.helper_db
# Mantida aqui apenas para compatibilidade (delegando para o módulo)
def obter_duplex_da_impressora(conn: sqlite3.Connection, printer_name: str, duplex_evento: Optional[int] = None) -> int:
    """
    DEPRECATED: Use modules.helper_db.obter_duplex_da_impressora diretamente.
    Mantida para compatibilidade com código existente.
    """
    from modules.helper_db import obter_duplex_da_impressora as _obter_duplex
    return _obter_duplex(conn, printer_name, duplex_evento)


def recalcular_eventos_impressora(conn: sqlite3.Connection, printer_name: str, tipo: str) -> int:
    """
    Recalcula o campo duplex de todos os eventos de uma impressora
    baseado no tipo cadastrado (duplex/simplex)
    
    Args:
        conn: Conexão com banco de dados
        printer_name: Nome da impressora
        tipo: Tipo da impressora ('duplex' ou 'simplex')
    
    Returns:
        Número de eventos atualizados
    """
    try:
        # Converte tipo para valor duplex (1 = duplex, 0 = simplex)
        duplex_value = 1 if tipo.lower() == 'duplex' else 0
        
        # Atualiza todos os eventos dessa impressora
        cursor = conn.execute(
            "UPDATE events SET duplex = ? WHERE printer_name = ?",
            (duplex_value, printer_name)
        )
        conn.commit()
        
        eventos_atualizados = cursor.rowcount
        logger.info(f"Recalculados {eventos_atualizados} eventos da impressora '{printer_name}' (tipo: {tipo})")
        
        return eventos_atualizados
    except Exception as e:
        logger.error(f"Erro ao recalcular eventos da impressora '{printer_name}': {e}")
        return 0


def sid_to_username(sid_str):
    """
    Converte SID para nome de usuário.
    Se já for um nome de usuário (não SID), retorna o próprio valor.
    Se falhar, retorna o valor original para não perder o evento.
    """
    if not sid_str:
        return None
    
    # Se já parece ser um nome de usuário (contém \ ou não começa com S-), retorna direto
    sid_str_clean = str(sid_str).strip()
    if '\\' in sid_str_clean or not sid_str_clean.startswith('S-'):
        # Já é um nome de usuário, não precisa converter
        return sid_str_clean
    
    # Tenta converter SID para nome de usuário
    try:
        ConvertStringSidToSid = ctypes.windll.advapi32.ConvertStringSidToSidW
        ConvertStringSidToSid.argtypes = [
            ctypes.wintypes.LPCWSTR,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        ConvertStringSidToSid.restype = ctypes.wintypes.BOOL

        LookupAccountSid = ctypes.windll.advapi32.LookupAccountSidW
        LookupAccountSid.argtypes = [
            ctypes.wintypes.LPCWSTR,
            ctypes.c_void_p,
            ctypes.wintypes.LPWSTR,
            ctypes.POINTER(ctypes.wintypes.DWORD),
            ctypes.wintypes.LPWSTR,
            ctypes.POINTER(ctypes.wintypes.DWORD),
            ctypes.POINTER(ctypes.wintypes.DWORD),
        ]
        LookupAccountSid.restype = ctypes.wintypes.BOOL

        pSid = ctypes.c_void_p()
        if not ConvertStringSidToSid(sid_str_clean, ctypes.byref(pSid)):
            # Se não conseguiu converter, pode ser que já seja um nome de usuário
            logger.debug(f"Não foi possível converter '{sid_str_clean}' como SID, usando valor original")
            return sid_str_clean

        name_len = ctypes.wintypes.DWORD(0)
        domain_len = ctypes.wintypes.DWORD(0)
        peUse = ctypes.wintypes.DWORD()

        LookupAccountSid(
            None,
            pSid,
            None,
            ctypes.byref(name_len),
            None,
            ctypes.byref(domain_len),
            ctypes.byref(peUse),
        )
        name = ctypes.create_unicode_buffer(name_len.value)
        domain = ctypes.create_unicode_buffer(domain_len.value)

        success = LookupAccountSid(
            None,
            pSid,
            name,
            ctypes.byref(name_len),
            domain,
            ctypes.byref(domain_len),
            ctypes.byref(peUse),
        )
        if not success:
            # Se falhou, retorna o valor original para não perder o evento
            logger.debug(f"Não foi possível fazer lookup do SID '{sid_str_clean}', usando valor original")
            ctypes.windll.kernel32.LocalFree(pSid)
            return sid_str_clean

        ctypes.windll.kernel32.LocalFree(pSid)
        return f"{domain.value}\\{name.value}"
    except Exception as e:
        # Se der qualquer erro, retorna o valor original para não perder o evento
        logger.debug(f"Erro ao converter SID '{sid_str_clean}': {e}, usando valor original")
        return sid_str_clean


# --- Inicializa DB ---
def init_db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    
    # Inicializa connection pool
    try:
        init_db_pool(DB)
        logger.info("✅ Connection pool inicializado")
    except Exception as e:
        logger.warning(f"⚠️ Erro ao inicializar connection pool: {e}. Usando conexões diretas.")
    
    with sqlite3.connect(DB) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            user TEXT,
            machine TEXT,
            pages_printed INTEGER DEFAULT 1,
            copies INTEGER DEFAULT 1,
            document TEXT,
            printer_name TEXT,
            printer_port TEXT,
            color_mode TEXT,
            paper_size TEXT,
            duplex INTEGER,
            job_id TEXT,
            job_status TEXT,
            record_number INTEGER,
            file_size INTEGER,
            processing_time REAL,
            source_ip TEXT,
            application TEXT,
            cost REAL,
            account TEXT,
            archived_path TEXT,
            snmp_validated INTEGER DEFAULT 0,
            snmp_total_before INTEGER,
            snmp_total_after INTEGER,
            snmp_difference INTEGER,
            validation_message TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
        )
        # Adiciona coluna sheets_used se não existir (folhas físicas calculadas)
        try:
            conn.execute("ALTER TABLE events ADD COLUMN sheets_used INTEGER")
            logger.info("✅ Coluna sheets_used adicionada à tabela events")
        except sqlite3.OperationalError:
            pass  # Coluna já existe
        
        # Adiciona novas colunas se a tabela já existir
        try:
            existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(events)").fetchall()]
            new_columns = [
                ('printer_name', 'TEXT'),
                ('printer_port', 'TEXT'),
                ('color_mode', 'TEXT'),
                ('paper_size', 'TEXT'),
                ('duplex', 'INTEGER'),
                ('job_id', 'TEXT'),
                ('job_status', 'TEXT'),
                ('record_number', 'INTEGER'),
                ('file_size', 'INTEGER'),
                ('processing_time', 'REAL'),
                ('source_ip', 'TEXT'),
                ('application', 'TEXT'),
                ('cost', 'REAL'),
                ('account', 'TEXT'),
                ('archived_path', 'TEXT'),
                ('snmp_validated', 'INTEGER'),
                ('snmp_total_before', 'INTEGER'),
                ('snmp_total_after', 'INTEGER'),
                ('snmp_difference', 'INTEGER'),
                ('copies', 'INTEGER'),
                ('validation_message', 'TEXT'),
                ('created_at', 'TEXT DEFAULT CURRENT_TIMESTAMP')
            ]
            for col_name, col_type in new_columns:
                if col_name not in existing_columns:
                    conn.execute(f"ALTER TABLE events ADD COLUMN {col_name} {col_type}")
                    logger.info(f"Coluna {col_name} adicionada à tabela events")
        except Exception as e:
            logger.warning(f"Erro ao adicionar colunas: {e}")
        # Adiciona índice para melhorar performance de consultas
        # Nota: Não usamos UNIQUE aqui porque eventos legítimos podem ter os mesmos valores
        # A prevenção de duplicatas é feita pela lógica de inserção
        # Criar índices para melhorar performance
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_events_date ON events(date)",
            "CREATE INDEX IF NOT EXISTS idx_events_user ON events(user)",
            "CREATE INDEX IF NOT EXISTS idx_events_printer ON events(printer_name)",
            "CREATE INDEX IF NOT EXISTS idx_events_sector ON events(sector)",
            "CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_events_record_number ON events(record_number)",
            "CREATE INDEX IF NOT EXISTS idx_events_job_id ON events(job_id)",
            "CREATE INDEX IF NOT EXISTS idx_events_date_user ON events(date, user)",
            "CREATE INDEX IF NOT EXISTS idx_events_color_mode ON events(color_mode)",
            "CREATE INDEX IF NOT EXISTS idx_events_duplex ON events(duplex)"
        ]
        for index_sql in indices:
            try:
                conn.execute(index_sql)
            except sqlite3.OperationalError:
                # Índices podem já existir - ignora
                pass
        conn.execute(
            """CREATE TABLE IF NOT EXISTS users (
            user TEXT PRIMARY KEY,
            sector TEXT)"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS precos (
            data_inicio TEXT PRIMARY KEY,
            valor REAL)"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS materiais (
            nome TEXT,
            preco REAL,
            rendimento INTEGER,
            valor REAL,
            data_inicio TEXT)"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS login (
            username TEXT PRIMARY KEY,
            password TEXT,
            is_admin INTEGER DEFAULT 0)"""
        )
        # Migração de senhas desabilitada - migração acontece apenas no login
        # Isso evita re-hash de senhas já hasheadas a cada reinício do servidor
        # A migração no login é mais segura e acontece apenas quando necessário
        # Tabela de configurações do sistema
        conn.execute(
            """CREATE TABLE IF NOT EXISTS config (
            chave TEXT PRIMARY KEY,
            valor TEXT)"""
        )
        # Tabela para vincular impressoras a setores
        conn.execute(
            """CREATE TABLE IF NOT EXISTS printers (
            printer_name TEXT PRIMARY KEY,
            sector TEXT,
            tipo TEXT DEFAULT 'simplex')"""
        )
        # Migração: adiciona coluna tipo se não existir
        try:
            conn.execute("ALTER TABLE printers ADD COLUMN tipo TEXT DEFAULT 'simplex'")
        except sqlite3.OperationalError:
            pass  # Coluna já existe
        # Migração: adiciona coluna ip se não existir
        try:
            conn.execute("ALTER TABLE printers ADD COLUMN ip TEXT")
        except sqlite3.OperationalError:
            pass  # Coluna já existe
        # Migração: adiciona colunas de comodato se não existirem
        comodato_columns = [
            ('comodato', 'INTEGER DEFAULT 0'),
            ('insumos_inclusos', 'INTEGER DEFAULT 0'),
            ('custo_fixo_mensal', 'REAL'),
            ('limite_paginas_mensal', 'INTEGER'),
            ('custo_excedente', 'REAL'),
            ('fornecedor', 'TEXT'),
            ('data_inicio_comodato', 'TEXT')
        ]
        for col_name, col_def in comodato_columns:
            try:
                conn.execute(f"ALTER TABLE printers ADD COLUMN {col_name} {col_def}")
                logger.info(f"✅ Coluna {col_name} adicionada à tabela printers")
            except sqlite3.OperationalError:
                pass  # Coluna já existe
        # Tabela de comodatos (histórico e gestão de contratos)
        conn.execute(
            """CREATE TABLE IF NOT EXISTS comodatos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            printer_name TEXT NOT NULL,
            fornecedor TEXT,
            custo_mensal REAL NOT NULL,
            limite_paginas INTEGER,
            custo_excedente REAL,
            insumos_inclusos INTEGER DEFAULT 1,
            data_inicio TEXT NOT NULL,
            data_fim TEXT,
            ativo INTEGER DEFAULT 1,
            observacoes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (printer_name) REFERENCES printers(printer_name))"""
        )
        # Índices para comodatos
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_comodatos_printer ON comodatos(printer_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_comodatos_ativo ON comodatos(ativo)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_comodatos_data ON comodatos(data_inicio, data_fim)")
        except sqlite3.OperationalError:
            pass
        # Tabela para tokens de recuperação de senha
        conn.execute(
            """CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            token TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES login(username))"""
        )
        # Índice para busca rápida por token
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_reset_token ON password_reset_tokens(token)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_reset_username ON password_reset_tokens(username)")
        except sqlite3.OperationalError:
            pass
        # Tabelas para novas funcionalidades
        # Quotas e limites
        conn.execute(
            """CREATE TABLE IF NOT EXISTS quotas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            referencia TEXT NOT NULL,
            limite_mensal INTEGER,
            limite_trimestral INTEGER,
            limite_anual INTEGER,
            periodo_inicio TEXT,
            periodo_fim TEXT,
            ativo INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(tipo, referencia))"""
        )
        # Metas
        conn.execute(
            """CREATE TABLE IF NOT EXISTS metas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            referencia TEXT NOT NULL,
            meta_paginas INTEGER,
            meta_custo REAL,
            periodo TEXT,
            ano INTEGER,
            mes INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
        )
        # Tabela orcamentos removida: sistema de orçamento removido
        # Alertas e notificações
        conn.execute(
            """CREATE TABLE IF NOT EXISTS alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            nivel TEXT NOT NULL,
            titulo TEXT NOT NULL,
            mensagem TEXT,
            referencia TEXT,
            valor_atual REAL,
            valor_limite REAL,
            lido INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
        )
        # Configurações de alertas
        conn.execute(
            """CREATE TABLE IF NOT EXISTS alerta_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            referencia TEXT,
            condicao TEXT NOT NULL,
            valor_limite REAL,
            email_habilitado INTEGER DEFAULT 0,
            email_destinatarios TEXT,
            ativo INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
        )
        # Auditoria
        conn.execute(
            """CREATE TABLE IF NOT EXISTS auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            acao TEXT NOT NULL,
            tabela TEXT,
            registro_id TEXT,
            dados_anteriores TEXT,
            dados_novos TEXT,
            ip_address TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
        )
        # Relatórios agendados
        conn.execute(
            """CREATE TABLE IF NOT EXISTS relatorios_agendados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL,
            frequencia TEXT NOT NULL,
            dia_semana INTEGER,
            dia_mes INTEGER,
            hora TEXT,
            destinatarios TEXT,
            filtros TEXT,
            ativo INTEGER DEFAULT 1,
            ultimo_envio TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
        )
        # Sugestões de economia
        conn.execute(
            """CREATE TABLE IF NOT EXISTS sugestoes_economia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evento_id INTEGER,
            tipo TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            economia_estimada REAL,
            aplicada INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
        )
        # Cache de consultas
        conn.execute(
            """CREATE TABLE IF NOT EXISTS cache_consultas (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL,
            expiracao TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
        )
        # Dashboard widgets personalizados
        conn.execute(
            """CREATE TABLE IF NOT EXISTS dashboard_widgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            tipo TEXT NOT NULL,
            posicao INTEGER,
            configuracao TEXT,
            ativo INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
        )
        # Análise de padrões
        conn.execute(
            """CREATE TABLE IF NOT EXISTS padroes_analise (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            referencia TEXT,
            periodo TEXT,
            valor REAL,
            desvio_padrao REAL,
            anomalia INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
        )
        # Backup points
        conn.execute(
            """CREATE TABLE IF NOT EXISTS backup_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT,
            arquivo_path TEXT,
            tamanho INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
        )
        # Inicializa configurações padrão
        default_configs = [
            ('color_multiplier', '2.0'),
            ('color_alert_threshold', '50'),
            ('color_alert_enabled', '1')
        ]
        for chave, valor in default_configs:
            conn.execute(
                "INSERT OR IGNORE INTO config (chave, valor) VALUES (?, ?)",
                (chave, valor)
            )
        colunas = conn.execute("PRAGMA table_info(login)").fetchall()
        if "is_admin" not in [col[1] for col in colunas]:
            conn.execute(
                "ALTER TABLE login ADD COLUMN is_admin INTEGER DEFAULT 0")
        if not conn.execute(
                "SELECT 1 FROM login WHERE username = 'admin'").fetchone():
            # Cria usuário admin com senha aleatória segura
            import secrets
            import string
            # Gera senha aleatória de 16 caracteres
            alphabet = string.ascii_letters + string.digits + "!@#$%&*"
            random_password = ''.join(secrets.choice(alphabet) for _ in range(16))
            admin_password_hash = generate_password_hash(random_password)
            conn.execute(
                "INSERT INTO login (username, password, is_admin) VALUES ('admin', ?, 1)",
                (admin_password_hash,)
            )
            # Log da senha gerada (apenas na primeira criação)
            logger.warning(
                f"⚠️  USUÁRIO ADMIN CRIADO!\n"
                f"   Username: admin\n"
                f"   Senha gerada: {random_password}\n"
                f"   ⚠️  ANOTE ESTA SENHA E ALTERE-A APÓS O PRIMEIRO LOGIN!\n"
                f"   💡 Use: python alterar_senha_admin.py"
            )
            print(f"\n{'='*70}")
            print(f"⚠️  USUÁRIO ADMIN CRIADO!")
            print(f"   Username: admin")
            print(f"   Senha gerada: {random_password}")
            print(f"   ⚠️  ANOTE ESTA SENHA E ALTERE-A APÓS O PRIMEIRO LOGIN!")
            print(f"   💡 Use: python alterar_senha_admin.py")
            print(f"{'='*70}\n")


# --- Decorators de login ---
def is_api_request():
    """Detecta se a requisição é de uma API (não navegador)"""
    # Verifica múltiplos indicadores de requisição de API
    return (request.is_json or
            request.path.startswith('/api/') or
            request.headers.get('Content-Type', '').startswith('application/json') or
            request.headers.get('Accept', '').startswith('application/json') or
            request.args.get('api') == 'true' or  # Parâmetro explícito
            'application/json' in request.headers.get('Accept', '') or
            # User-Agent que não seja navegador comum
            (request.headers.get('User-Agent', '') and 
             not any(browser in request.headers.get('User-Agent', '').lower() 
                    for browser in ['mozilla', 'chrome', 'safari', 'edge', 'firefox', 'opera'])))

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            # Se for requisição de API, retorna JSON
            if is_api_request():
                return jsonify({"error": "Não autenticado", "message": "Login necessário"}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return "Acesso negado: apenas administradores", 403
        return f(*args, **kwargs)

    return wrapper

def get_config(key: str, default: str = "") -> str:
    """Obtém valor de configuração do banco de dados"""
    try:
        with get_db() as conn:
            result = conn.execute(
                "SELECT valor FROM config WHERE chave = ?", (key,)
            ).fetchone()
            return result[0] if result else default
    except Exception as e:
        logger.warning(f"Erro ao ler configuração {key}: {e}")
        return default

def set_config(key: str, value: str):
    """Define valor de configuração no banco de dados"""
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO config (chave, valor) VALUES (?, ?)",
                (key, str(value))
            )
            conn.commit()
            logger.info(f"Configuração {key} atualizada para {value}")
    except Exception as e:
        logger.error(f"Erro ao salvar configuração {key}: {e}")

# =============================================================================
# FUNÇÕES DE VALIDAÇÃO E SEGURANÇA
# =============================================================================

# Whitelist de tabelas permitidas para queries dinâmicas
TABELAS_PERMITIDAS = {
    'events', 'users', 'printers', 'materiais', 'comodatos', 
    'login', 'config', 'quotas', 'metas', 'orcamentos', 
    'alertas', 'password_reset_tokens'
}

# Operadores SQL permitidos (whitelist)
OPERADORES_PERMITIDOS = {'=', '!=', '<>', '<', '>', '<=', '>=', 'LIKE', 'IN', 'NOT IN'}

# Direções de ordenação permitidas
DIRECOES_ORDENACAO = {'ASC', 'DESC'}


def validar_nome_tabela(tabela: str) -> bool:
    """
    Valida se o nome da tabela está na whitelist de tabelas permitidas.
    
    Args:
        tabela: Nome da tabela a validar
    
    Returns:
        True se válido, False caso contrário
    """
    if not tabela or not isinstance(tabela, str):
        return False
    # Remove espaços e converte para minúsculas para comparação
    tabela_clean = tabela.strip().lower()
    return tabela_clean in {t.lower() for t in TABELAS_PERMITIDAS}


def validar_nome_coluna(coluna: str, tabela: str, conn: sqlite3.Connection) -> bool:
    """
    Valida se o nome da coluna existe na tabela especificada.
    
    Args:
        coluna: Nome da coluna a validar
        tabela: Nome da tabela
        conn: Conexão com banco de dados
    
    Returns:
        True se válido, False caso contrário
    """
    if not coluna or not isinstance(coluna, str):
        return False
    
    # Remove espaços
    coluna_clean = coluna.strip()
    
    # Se for *, permite (SELECT *)
    if coluna_clean == '*':
        return True
    
    try:
        # Busca colunas da tabela usando PRAGMA (seguro)
        cursor = conn.execute(f"PRAGMA table_info({tabela})")
        colunas_existentes = {row[1].lower() for row in cursor.fetchall()}
        
        # Valida se a coluna existe (case-insensitive)
        return coluna_clean.lower() in colunas_existentes
    except sqlite3.OperationalError:
        # Tabela não existe ou erro ao buscar colunas
        return False


def validar_lista_colunas(colunas: list, tabela: str, conn: sqlite3.Connection) -> tuple[bool, list]:
    """
    Valida uma lista de nomes de colunas.
    
    Args:
        colunas: Lista de nomes de colunas
        tabela: Nome da tabela
        conn: Conexão com banco de dados
    
    Returns:
        Tuple (valido, colunas_validas)
    """
    if not colunas:
        return True, ['*']
    
    colunas_validas = []
    for coluna in colunas:
        if not isinstance(coluna, str):
            return False, []
        
        # Valida cada coluna
        if validar_nome_coluna(coluna, tabela, conn):
            colunas_validas.append(coluna.strip())
        else:
            logger.warning(f"⚠️ Coluna inválida rejeitada: {coluna} na tabela {tabela}")
            return False, []
    
    return True, colunas_validas


def validar_operador_sql(operador: str) -> bool:
    """
    Valida se o operador SQL está na whitelist.
    
    Args:
        operador: Operador SQL a validar
    
    Returns:
        True se válido, False caso contrário
    """
    if not operador or not isinstance(operador, str):
        return False
    return operador.upper() in OPERADORES_PERMITIDOS


def sanitizar_nome_campo(campo: str) -> str:
    """
    Sanitiza nome de campo removendo caracteres perigosos.
    Apenas permite letras, números e underscore.
    
    Args:
        campo: Nome do campo a sanitizar
    
    Returns:
        Nome sanitizado ou string vazia se inválido
    """
    if not campo or not isinstance(campo, str):
        return ""
    
    # Remove caracteres perigosos, mantém apenas alfanuméricos e underscore
    import re
    campo_clean = re.sub(r'[^a-zA-Z0-9_]', '', campo.strip())
    
    # Não pode começar com número
    if campo_clean and campo_clean[0].isdigit():
        return ""
    
    return campo_clean


def validar_direcao_ordenacao(direcao: str) -> str:
    """
    Valida e retorna direção de ordenação válida.
    
    Args:
        direcao: Direção a validar
    
    Returns:
        Direção válida (ASC ou DESC) ou DESC como padrão
    """
    if not direcao or not isinstance(direcao, str):
        return 'DESC'
    
    direcao_upper = direcao.strip().upper()
    return direcao_upper if direcao_upper in DIRECOES_ORDENACAO else 'DESC'


# =============================================================================
# FUNÇÕES DE CÁLCULO DE CUSTO
# =============================================================================

def custo_unitario_por_data(data_evento: str, color_mode: Optional[str] = None) -> float:
    """
    DEPRECATED: Sistema de custos foi removido.
    Retorna 0 para manter compatibilidade com código existente.
    
    Args:
        data_evento: Data do evento (não usado)
        color_mode: 'Color' ou 'Black & White' (não usado)
    
    Returns:
        0 (sistema de custos removido)
    """
    return 0.0

def check_color_alerts() -> List[Dict]:
    """Verifica alertas de uso de cor e retorna lista de alertas"""
    alerts = []
    try:
        alert_enabled = get_config('color_alert_enabled', '1') == '1'
        if not alert_enabled:
            return alerts
        
        threshold = float(get_config('color_alert_threshold', '50'))
        
        with get_db() as conn:
            # Verifica se job_id existe
            existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(events)").fetchall()]
            has_job_id = 'job_id' in existing_columns
            
            # Busca eventos agrupados por job primeiro
            if has_job_id:
                rows = conn.execute("""
                    SELECT 
                        date(date) as dia,
                        MAX(pages_printed) as pages,
                        MAX(COALESCE(duplex, 0)) as duplex,
                        MAX(COALESCE(copies, 1)) as copies,
                        MAX(color_mode) as color_mode
                    FROM events
                    WHERE date(date) >= date('now', '-7 days')
                    GROUP BY CASE 
                        WHEN job_id IS NOT NULL AND job_id != '' THEN 
                            job_id || '|' || COALESCE(printer_name, '') || '|' || date
                        ELSE 
                            user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
                    END, date(date)
                """).fetchall()
            else:
                rows = conn.execute("""
                    SELECT 
                        date(date) as dia,
                        MAX(pages_printed) as pages,
                        MAX(COALESCE(duplex, 0)) as duplex,
                        MAX(COALESCE(copies, 1)) as copies,
                        MAX(color_mode) as color_mode
                    FROM events
                    WHERE date(date) >= date('now', '-7 days')
                    GROUP BY user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date, date(date)
                """).fetchall()
            
            # Agrupa por dia e calcula folhas físicas
            dias_dict = {}
            for row in rows:
                dia = row[0]
                pages = row[1] or 0
                duplex = row[2]
                copies = row[3] or 1
                color_mode = row[4]
                
                folhas_fisicas = calcular_folhas_fisicas(pages, duplex, copies)
                
                if dia not in dias_dict:
                    dias_dict[dia] = {"total_paginas": 0, "paginas_color": 0}
                
                dias_dict[dia]["total_paginas"] += folhas_fisicas
                if color_mode == 'Color':
                    dias_dict[dia]["paginas_color"] += folhas_fisicas
            
            # Filtra dias com percentual de cor acima do threshold
            for dia, data in dias_dict.items():
                pct_color = (data["paginas_color"] * 100.0 / data["total_paginas"]) if data["total_paginas"] > 0 else 0
                if pct_color > threshold:
                    alerts.append({
                        'date': dia,
                        'pct_color': round(pct_color, 2),
                        'pages_color': data["paginas_color"],
                        'total_pages': data["total_paginas"]
                    })
            
            # Ordena por data descendente
            alerts.sort(key=lambda x: x['date'], reverse=True)
    except Exception as e:
        logger.error(f"Erro ao verificar alertas: {e}")
    
    return alerts


@app.route("/login", methods=["GET", "POST"])
@csrf_exempt_if_enabled
def login():
    if request.method == "POST":
        # Suporta tanto form-data quanto JSON
        if request.is_json:
            data = request.get_json()
            user = data.get("username", "").strip() if data else ""
            pwd = data.get("password", "").strip() if data else ""
        else:
            user = request.form.get("username", "").strip()
            pwd = request.form.get("password", "").strip()
        
        if not user or not pwd:
            # Se for requisição de API, retorna JSON com 400
            if is_api_request():
                return jsonify({"error": "Por favor, informe usuário e senha"}), 400
            flash("Por favor, informe usuário e senha", "danger")
            return render_template("login.html")
        
        with get_db() as conn:
            result = conn.execute(
                "SELECT username, password, is_admin FROM login WHERE username = ?",
                (user,)
            ).fetchone()
            
            if result:
                stored_password = result[1]
                
                # Debug: log do tipo de senha (sem mostrar a senha)
                if stored_password:
                    # Verifica se está hasheada (pode começar com $ ou scrypt: ou pbkdf2:)
                    is_hashed = (stored_password.startswith('$') or 
                                stored_password.startswith('scrypt:') or 
                                stored_password.startswith('pbkdf2:'))
                    logger.debug(f"Tentativa de login: {user}, senha hasheada: {is_hashed}, tamanho: {len(stored_password) if stored_password else 0}")
                
                # Verifica se a senha está hasheada (pode começar com $, scrypt: ou pbkdf2:)
                if stored_password and (stored_password.startswith('$') or 
                                       stored_password.startswith('scrypt:') or 
                                       stored_password.startswith('pbkdf2:')):
                    # Senha está hasheada, usa check_password_hash
                    try:
                        if check_password_hash(stored_password, pwd):
                            # Senha correta - autentica usuário
                            session["logged_in"] = True
                            session["user"] = user
                            session.permanent = True
                            # Verifica is_admin de forma segura
                            try:
                                session["is_admin"] = len(result) > 2 and result[2] == 1
                            except (IndexError, TypeError):
                                session["is_admin"] = False
                            logger.info(f"Login bem-sucedido: {user}")
                            # Se for requisição de API, retorna JSON
                            if is_api_request():
                                return jsonify({"status": "success", "message": "Login bem-sucedido", "user": user, "is_admin": session.get("is_admin", False)}), 200
                            return redirect(url_for("home"))
                        else:
                            logger.warning(f"Senha incorreta para usuário: {user} (senha hasheada)")
                            # Se for requisição de API, retorna JSON com 401
                            if is_api_request():
                                return jsonify({"error": "Usuário ou senha inválidos"}), 401
                            flash("Usuário ou senha inválidos", "danger")
                    except Exception as e:
                        logger.error(f"Erro ao verificar senha hasheada: {e}", exc_info=True)
                        # Se for requisição de API, retorna JSON com 401
                        if is_api_request():
                            return jsonify({"error": "Erro ao verificar credenciais"}), 401
                        flash("Erro ao verificar credenciais", "danger")
                elif stored_password:
                    # Senha em texto plano (legado) - compara diretamente e depois hasheia
                    if stored_password == pwd:
                        # Migra para hash
                        hashed = generate_password_hash(pwd)
                        conn.execute(
                            "UPDATE login SET password = ? WHERE username = ?",
                            (hashed, user)
                        )
                        conn.commit()
                        logger.info(f"Senha do usuário {user} migrada para hash")
                        
                        # Autentica usuário
                        session["logged_in"] = True
                        session["user"] = user
                        session.permanent = True
                        try:
                            session["is_admin"] = len(result) > 2 and result[2] == 1
                        except (IndexError, TypeError):
                            session["is_admin"] = False
                        logger.info(f"Login bem-sucedido: {user} (após migração)")
                        # Se for requisição de API, retorna JSON
                        if is_api_request():
                            return jsonify({"status": "success", "message": "Login bem-sucedido", "user": user, "is_admin": session.get("is_admin", False)}), 200
                        return redirect(url_for("home"))
                    else:
                        logger.warning(f"Senha incorreta para usuário: {user} (senha em texto plano)")
                        # Se for requisição de API, retorna JSON com 401
                        if is_api_request():
                            return jsonify({"error": "Usuário ou senha inválidos"}), 401
                        flash("Usuário ou senha inválidos", "danger")
                else:
                    # Senha vazia ou None
                    logger.error(f"Senha vazia para usuário: {user}")
                    # Se for requisição de API, retorna JSON com 401
                    if is_api_request():
                        return jsonify({"error": "Senha não configurada para este usuário"}), 401
                    flash("Erro: senha não configurada para este usuário", "danger")
            else:
                logger.warning(f"Usuário não encontrado: {user}")
                # Se for requisição de API, retorna JSON com 401
                if is_api_request():
                    return jsonify({"error": "Usuário ou senha inválidos"}), 401
                flash("Usuário ou senha inválidos", "danger")
        
        # Se for requisição POST e chegou aqui sem retornar (credenciais inválidas)
        # Verifica novamente se é API (pode ter sido form-data sem headers)
        if request.method == "POST":
            # Tenta detectar API de forma mais agressiva para POST
            # Se não tem flash messages ou se tem headers específicos
            if (is_api_request() or 
                request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
                request.headers.get('X-API-Request') == 'true'):
                return jsonify({"error": "Usuário ou senha inválidos"}), 401
    
    # Se GET ou se não foi detectado como API, retorna página de login
    return render_template("login.html")


@app.route("/recuperar-senha", methods=["GET", "POST"])
@csrf_exempt_if_enabled
def recuperar_senha():
    """Endpoint para solicitar recuperação de senha (valida token)"""
    if request.method == "POST":
        # Limpa o código: remove hífens, espaços e converte para maiúsculo
        codigo_raw = request.form.get("codigo", "").strip()
        codigo = ''.join(c for c in codigo_raw if c.isalnum()).upper()
        username = request.form.get("username", "").strip()
        
        if not codigo or not username:
            flash("Por favor, informe o nome de usuário e o código de recuperação", "danger")
            return render_template("recuperar_senha.html")
        
        # Valida se o código tem 12 caracteres
        if len(codigo) != 12:
            flash(f"Código inválido. O código deve ter 12 caracteres. Recebido: {len(codigo)} caracteres.", "danger")
            logger.warning(f"Tentativa de validação com código de tamanho incorreto: {len(codigo)} caracteres")
            return render_template("recuperar_senha.html")
        
        with get_db() as conn:
            from datetime import datetime
            
            # Busca token válido
            token_data = conn.execute(
                """SELECT username, expires_at, used 
                FROM password_reset_tokens 
                WHERE token = ? AND username = ?""",
                (codigo, username)
            ).fetchone()
            
            if not token_data:
                # Log para debug
                logger.warning(f"Tentativa de validação falhou - Usuario: {username}, Codigo: {codigo[:4]}...")
                # Verifica se o código existe para outro usuário
                token_outro_user = conn.execute(
                    "SELECT username FROM password_reset_tokens WHERE token = ?",
                    (codigo,)
                ).fetchone()
                
                if token_outro_user:
                    flash("Código de recuperação inválido para este usuário. Verifique se o código corresponde ao usuário informado.", "danger")
                else:
                    flash("Código de recuperação inválido ou não encontrado. Verifique se copiou o código completo.", "danger")
                return render_template("recuperar_senha.html")
            
            token_username, expires_at_str, used = token_data
            
            # Verifica se já foi usado
            if used == 1:
                flash("Este código de recuperação já foi utilizado", "danger")
                return render_template("recuperar_senha.html")
            
            # Verifica expiração
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.now() > expires_at:
                    flash("Este código de recuperação expirou. Solicite um novo código ao administrador.", "danger")
                    # Marca como usado
                    conn.execute(
                        "UPDATE password_reset_tokens SET used = 1 WHERE token = ?",
                        (codigo,)
                    )
                    conn.commit()
                    return render_template("recuperar_senha.html")
                
                # Redireciona para página de reset com o token
                return redirect(url_for("resetar_senha_com_token", token=codigo))
                
            except (ValueError, TypeError):
                flash("Erro ao validar código. Tente novamente.", "danger")
                return render_template("recuperar_senha.html")
    
    return render_template("recuperar_senha.html")


@app.route("/resetar-senha/<token>", methods=["GET", "POST"])
@csrf_exempt_if_enabled
def resetar_senha_com_token(token):
    """Endpoint para resetar senha usando token"""
    if request.method == "POST":
        nova_senha = request.form.get("nova_senha", "").strip()
        confirmar_senha = request.form.get("confirmar_senha", "").strip()
        
        if not nova_senha or not confirmar_senha:
            flash("Por favor, preencha todos os campos", "danger")
            return render_template("resetar_senha.html", token=token)
        
        if nova_senha != confirmar_senha:
            flash("As senhas não coincidem", "danger")
            return render_template("resetar_senha.html", token=token)
        
        if len(nova_senha) < 6:
            flash("A senha deve ter no mínimo 6 caracteres", "danger")
            return render_template("resetar_senha.html", token=token)
        
        with get_db() as conn:
            # Busca token válido
            from datetime import datetime
            token_data = conn.execute(
                """SELECT username, expires_at, used 
                FROM password_reset_tokens 
                WHERE token = ?""",
                (token,)
            ).fetchone()
            
            if not token_data:
                flash("Código de recuperação inválido ou não encontrado", "danger")
                return redirect(url_for("recuperar_senha"))
            
            username, expires_at_str, used = token_data
            
            # Verifica se já foi usado
            if used == 1:
                flash("Este código de recuperação já foi utilizado", "danger")
                return redirect(url_for("recuperar_senha"))
            
            # Verifica expiração
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.now() > expires_at:
                    flash("Este código de recuperação expirou. Solicite um novo código.", "danger")
                    # Marca como usado
                    conn.execute(
                        "UPDATE password_reset_tokens SET used = 1 WHERE token = ?",
                        (token,)
                    )
                    conn.commit()
                    return redirect(url_for("recuperar_senha"))
            except (ValueError, TypeError):
                flash("Erro ao validar código. Tente novamente.", "danger")
                return redirect(url_for("recuperar_senha"))
            
            # Reseta a senha
            password_hash = generate_password_hash(nova_senha)
            conn.execute(
                "UPDATE login SET password = ? WHERE username = ?",
                (password_hash, username)
            )
            
            # Marca token como usado
            conn.execute(
                "UPDATE password_reset_tokens SET used = 1 WHERE token = ?",
                (token,)
            )
            
            conn.commit()
            
            logger.info(f"Senha resetada para usuário: {username} via token")
            flash("Senha alterada com sucesso! Faça login com sua nova senha.", "success")
            return redirect(url_for("login"))
    
    # GET - mostra formulário de reset
    with get_db() as conn:
        from datetime import datetime
        
        token_data = conn.execute(
            """SELECT username, expires_at, used 
            FROM password_reset_tokens 
            WHERE token = ?""",
            (token,)
        ).fetchone()
        
        if not token_data:
            flash("Código de recuperação inválido", "danger")
            return redirect(url_for("recuperar_senha"))
        
        username, expires_at_str, used = token_data
        
        # Verifica se já foi usado
        if used == 1:
            flash("Este código já foi utilizado", "danger")
            return redirect(url_for("recuperar_senha"))
        
        # Verifica expiração
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if datetime.now() > expires_at:
                flash("Este código expirou. Solicite um novo código.", "danger")
                return redirect(url_for("recuperar_senha"))
            
            # Calcula tempo restante
            tempo_restante = expires_at - datetime.now()
            minutos_restantes = int(tempo_restante.total_seconds() / 60)
        except (ValueError, TypeError):
            flash("Erro ao validar código", "danger")
            return redirect(url_for("recuperar_senha"))
        
        return render_template("resetar_senha.html", 
                             token=token, 
                             username=username,
                             minutos_restantes=minutos_restantes)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def home():
    return redirect(url_for("all_users"))


@app.route("/usuarios")
@login_required
def all_users():
    try:
        start_date = request.args.get("start_date", "")
        end_date = request.args.get("end_date", "")
        filtro_usuario = request.args.get("filtro_usuario", "")
        # Paginação
        try:
            page = int(request.args.get("page", 1))
            per_page = int(request.args.get("per_page", 50))
        except (ValueError, TypeError):
            page = 1
            per_page = 50
        offset = (page - 1) * per_page

        # Impressão = Folha lógica (job) | Páginas = Folha física (papel)
        # IMPORTANTE: Agrupa por job_id para contar jobs únicos, não eventos individuais
        with get_db() as conn:
            # Verifica se job_id existe na tabela
            existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(events)").fetchall()]
            has_job_id = 'job_id' in existing_columns
            
            if has_job_id:
                # Agrupa por job_id quando disponível (mais preciso)
                # IMPORTANTE: Usa MAX(pages_printed) porque cada evento do mesmo job tem o total de páginas
                query = """SELECT 
                    user, 
                    machine,
                    job_id,
                    document,
                    printer_name,
                    date,
                    MAX(pages_printed) as total_pages,
                    MAX(COALESCE(duplex, 0)) as duplex,
                    MAX(COALESCE(copies, 1)) as copies
                FROM events 
                WHERE 1=1"""
                params = []
                if start_date:
                    query += " AND date(date) >= date(?)"
                    params.append(start_date)
                if end_date:
                    query += " AND date(date) <= date(?)"
                    params.append(end_date)
                if filtro_usuario:
                    query += " AND user LIKE ?"
                    params.append(f"%{filtro_usuario}%")
                
                # Agrupa por job_id + impressora + data para evitar agrupar jobs diferentes com mesmo job_id
                # IMPORTANTE: job_id pode ser reutilizado pelo Windows, então precisamos considerar também impressora e data
                query += """ GROUP BY 
                    CASE 
                        WHEN job_id IS NOT NULL AND job_id != '' THEN 
                            job_id || '|' || COALESCE(printer_name, '') || '|' || date
                        ELSE 
                            user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
                    END,
                    user,
                    machine"""
                query += " ORDER BY user, machine"
                
                rows = conn.execute(query, params).fetchall()
            else:
                # Fallback: agrupa por combinação de campos quando job_id não existe
                # IMPORTANTE: Usa MAX(pages_printed) porque cada evento do mesmo job tem o total de páginas
                query = """SELECT 
                    user, 
                    machine,
                    document,
                    printer_name,
                    date,
                    MAX(pages_printed) as total_pages,
                    MAX(COALESCE(duplex, 0)) as duplex,
                    MAX(COALESCE(copies, 1)) as copies
                FROM events 
                WHERE 1=1"""
                params = []
                if start_date:
                    query += " AND date(date) >= date(?)"
                    params.append(start_date)
                if end_date:
                    query += " AND date(date) <= date(?)"
                    params.append(end_date)
                if filtro_usuario:
                    query += " AND user LIKE ?"
                    params.append(f"%{filtro_usuario}%")
                
                # Agrupa por combinação de campos para identificar jobs únicos
                # Inclui impressora e data para garantir unicidade
                query += """ GROUP BY 
                    user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date,
                    user,
                    machine"""
                query += " ORDER BY user, machine"
                
                rows = conn.execute(query, params).fetchall()
        
        # Agrupa por user/machine e calcula totais
        # O template espera tuplas: (user, machine, total_impressos, total_paginas)
        user_data = {}
        for row in rows:
            user = row[0]
            machine = row[1]
            # total_pages está na posição 6 (ou 5 se não tem job_id)
            pages = row[6] if has_job_id else row[5]
            # duplex está na posição 7 (ou 6 se não tem job_id)
            duplex_evento = row[7] if has_job_id else (row[6] if len(row) > 6 else None)
            # copies pode estar na posição 8 (ou 7 se não tem job_id), mas pode não estar na query
            copies = row[8] if has_job_id and len(row) > 8 else (row[7] if len(row) > 7 else 1)
            # printer_name está na posição 4 (ou 3 se não tem job_id)
            printer_name = row[4] if has_job_id else (row[3] if len(row) > 3 else None)
            key = (user, machine)
            
            if key not in user_data:
                user_data[key] = {"user": user, "machine": machine, "total_impressos": 0, "total_paginas": 0}
            
            # Obtém duplex baseado no tipo da impressora cadastrada
            with sqlite3.connect(DB) as conn_dup:
                duplex = obter_duplex_da_impressora(conn_dup, printer_name, duplex_evento)
            
            # Cada linha já representa um job único (devido ao GROUP BY)
            user_data[key]["total_impressos"] += 1
            # Soma as páginas físicas do job (usa copies se disponível)
            user_data[key]["total_paginas"] += calcular_folhas_fisicas(pages or 0, duplex, copies if copies else 1)
        
        # Converte para formato de tupla que o template espera
        all_data = [(item["user"], item["machine"], item["total_impressos"], item["total_paginas"]) 
                    for item in user_data.values()]
        
        # Paginação
        total_items = len(all_data)
        total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 1
        paginated_data = all_data[offset:offset + per_page]
        
        return render_template(
            "usuarios.html",
            data=paginated_data,
            start_date=start_date,
            end_date=end_date,
            filtro_usuario=filtro_usuario,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            total_items=total_items,
        )
    except Exception as e:
        logger.error(f"Erro em all_users: {e}", exc_info=True)
        flash(f"Erro ao carregar usuários: {str(e)}", "danger")
        return render_template(
            "usuarios.html",
            data=[],
            start_date="",
            end_date="",
            filtro_usuario="",
            page=1,
            per_page=50,
            total_pages=1,
            total_items=0,
        )


@app.route("/usuarios/export")
@login_required
def export_usuarios_excel():
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    filtro_usuario = request.args.get("filtro_usuario", "")

    with sqlite3.connect(DB) as conn:
        # Verifica se job_id existe na tabela
        existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(events)").fetchall()]
        has_job_id = 'job_id' in existing_columns
        
        # Busca eventos agrupados por job primeiro e calcula folhas físicas
        where_clause = "WHERE 1=1"
        params = []
        if start_date:
            where_clause += " AND date(date) >= date(?)"
            params.append(start_date)
        if end_date:
            where_clause += " AND date(date) <= date(?)"
            params.append(end_date)
        if filtro_usuario:
            where_clause += " AND user LIKE ?"
            params.append(f"%{filtro_usuario}%")
        
        if has_job_id:
            query = f"""
                SELECT 
                    user,
                    machine,
                    MAX(pages_printed) as pages,
                    MAX(COALESCE(duplex, 0)) as duplex,
                    MAX(COALESCE(copies, 1)) as copies
                FROM events
                {where_clause}
                GROUP BY CASE 
                    WHEN job_id IS NOT NULL AND job_id != '' THEN 
                        job_id || '|' || COALESCE(printer_name, '') || '|' || date
                    ELSE 
                        user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
                END, user, machine
            """
        else:
            query = f"""
                SELECT 
                    user,
                    machine,
                    MAX(pages_printed) as pages,
                    MAX(COALESCE(duplex, 0)) as duplex,
                    MAX(COALESCE(copies, 1)) as copies
                FROM events
                {where_clause}
                GROUP BY user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date, user, machine
            """
        
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()
        
        # Agrupa por user/machine e calcula folhas físicas
        usuarios_dict = {}
        for row in rows:
            user = row["user"]
            machine = row["machine"]
            pages = row["pages"] or 0
            duplex = row["duplex"]
            copies = row["copies"] or 1
            
            key = f"{user}|{machine}"
            if key not in usuarios_dict:
                usuarios_dict[key] = {
                    "user": user,
                    "machine": machine,
                    "total_impressos": 0,
                    "total_paginas": 0
                }
            
            folhas_fisicas = calcular_folhas_fisicas(pages, duplex, copies)
            usuarios_dict[key]["total_impressos"] += 1
            usuarios_dict[key]["total_paginas"] += folhas_fisicas
        
        # Prepara dados para Excel
        excel_data = []
        for key, dados in sorted(usuarios_dict.items(), key=lambda x: x[1]["total_paginas"], reverse=True):
            excel_data.append({
                'Usuário': dados["user"],
                'Computador': dados["machine"],
                'Total Impressões': dados["total_impressos"],
                'Total Páginas': dados["total_paginas"]
            })
        
        df = pd.DataFrame(excel_data)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Usuários")
    output.seek(0)

    return send_file(
        output,
        download_name="usuarios.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/admin/usuarios", methods=["GET", "POST"])
@csrf_exempt_if_enabled
@admin_required
def admin_usuarios():
    message = ""
    try:
        conn = sqlite3.connect(DB)
        cursor = conn.cursor()

        if request.method == "POST":
            # Suporta tanto form-data quanto JSON
            if request.is_json:
                data = request.get_json()
                action = data.get("action")
                usuario = data.get("usuario")
                setor = data.get("setor")
            else:
                action = request.form.get("action")
                usuario = request.form.get("usuario")
                setor = request.form.get("setor")

            if action == "edit":
                if not usuario or not setor:
                    message = "Usuário e setor são obrigatórios."
                    if request.is_json:
                        return jsonify({"error": message}), 400
                else:
                    cursor.execute("SELECT 1 FROM users WHERE user = ?", (usuario,))
                    exists = cursor.fetchone()
                    if exists:
                        cursor.execute(
                            "UPDATE users SET sector = ? WHERE user = ?", (setor, usuario)
                        )
                    else:
                        cursor.execute(
                            "INSERT INTO users (user, sector) VALUES (?, ?)", (usuario, setor)
                        )
                    conn.commit()
                    message = f"Setor do usuário '{usuario}' atualizado para '{setor}'."
                    if request.is_json:
                        return jsonify({"status": "success", "message": message}), 200
            elif action == "delete":
                if not usuario:
                    message = "Usuário é obrigatório para exclusão."
                    if request.is_json:
                        return jsonify({"error": message}), 400
                else:
                    cursor.execute("DELETE FROM users WHERE user = ?", (usuario,))
                    conn.commit()
                    message = f"Usuário '{usuario}' excluído com sucesso."
                    if request.is_json:
                        return jsonify({"status": "success", "message": message}), 200

        cursor.execute("""
            SELECT DISTINCT e.user, u.sector
            FROM events e
            LEFT JOIN users u ON e.user = u.user
            ORDER BY e.user
        """)
        usuarios = cursor.fetchall()
        conn.close()
    except Exception as e:
        logger.error(f"Erro em admin_usuarios: {e}", exc_info=True)
        message = f"Erro ao processar: {str(e)}"
        usuarios = []

    return render_template("admin_usuarios.html", usuarios=usuarios, message=message)


# Rota removida: sistema de preços e comodatos removido
# @app.route("/admin/precos", methods=["GET", "POST"])
# @admin_required
# def admin_precos():
#     # Função removida - sistema de preços e comodatos desativado
#     pass


# Função removida: sistema de preços e comodatos removido

@app.route("/admin/configuracoes", methods=["GET", "POST"])
@login_required
@admin_required
def admin_configuracoes():
    """Página de configurações do sistema"""
    message = ""
    
    if request.method == "POST":
        color_multiplier = request.form.get("color_multiplier", "2.0")
        color_alert_threshold = request.form.get("color_alert_threshold", "50")
        color_alert_enabled = request.form.get("color_alert_enabled", "0")
        
        try:
            set_config('color_multiplier', color_multiplier)
            set_config('color_alert_threshold', color_alert_threshold)
            set_config('color_alert_enabled', '1' if color_alert_enabled else '0')
            message = "Configurações salvas com sucesso!"
            flash(message, "success")
            return redirect(url_for("admin_configuracoes"))
        except Exception as e:
            message = f"Erro ao salvar configurações: {str(e)}"
            flash(message, "danger")
    
    # Carrega configurações atuais
    configs = {
        'color_multiplier': get_config('color_multiplier', '2.0'),
        'color_alert_threshold': get_config('color_alert_threshold', '50'),
        'color_alert_enabled': get_config('color_alert_enabled', '1') == '1'
    }
    
    return render_template("admin_configuracoes.html", configs=configs, message=message)


@app.route("/admin/logins", methods=["GET", "POST"])
@login_required
@admin_required
@csrf_exempt_if_enabled
def admin_logins():
    message = ""
    if request.method == "POST":
        action = request.form.get("action")
        username = request.form.get("username")
        password = request.form.get("password")
        is_admin = int(bool(request.form.get("is_admin")))

        with get_db() as conn:
            if action == "add":
                try:
                    # Hash da senha antes de inserir
                    password_hash = generate_password_hash(password)
                    conn.execute(
                        "INSERT INTO login (username, password, is_admin) VALUES (?, ?, ?)",
                        (username, password_hash, is_admin),
                    )
                    message = "Usuário adicionado."
                except sqlite3.IntegrityError:
                    message = "Usuário já existe."
            elif action == "edit":
                # Hash da senha antes de atualizar (apenas se uma nova senha foi fornecida)
                if password and password.strip():
                    password_hash = generate_password_hash(password)
                    conn.execute(
                        "UPDATE login SET password = ?, is_admin = ? WHERE username = ?",
                        (password_hash, is_admin, username),
                    )
                    message = "Usuário atualizado."
                else:
                    # Se não forneceu senha, atualiza apenas is_admin
                    conn.execute(
                        "UPDATE login SET is_admin = ? WHERE username = ?",
                        (is_admin, username),
                    )
                    message = "Permissões do usuário atualizadas."
                conn.commit()
            elif action == "delete":
                if username != "admin":
                    conn.execute(
                        "DELETE FROM login WHERE username = ?", (username,))
                    message = "Usuário removido."
                else:
                    message = "Não é possível remover o admin."
            elif action == "gerar_codigo":
                # Gera código de recuperação para o usuário
                import secrets
                import string
                from datetime import datetime, timedelta
                
                # Verifica se o usuário existe
                user = conn.execute(
                    "SELECT username FROM login WHERE username = ?",
                    (username,)
                ).fetchone()
                
                if user:
                    # Invalida tokens anteriores do usuário
                    conn.execute(
                        "UPDATE password_reset_tokens SET used = 1 WHERE username = ?",
                        (username,)
                    )
                    
                    # Gera token aleatório único
                    token = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(12))
                    
                    # Define expiração (1 hora por padrão, configurável)
                    tempo_expiracao_horas = int(os.getenv('RESET_TOKEN_EXPIRES_HOURS', '1'))
                    expires_at = (datetime.now() + timedelta(hours=tempo_expiracao_horas)).isoformat()
                    
                    # Insere token no banco
                    try:
                        conn.execute(
                            """INSERT INTO password_reset_tokens (username, token, expires_at)
                            VALUES (?, ?, ?)""",
                            (username, token, expires_at)
                        )
                        conn.commit()
                        message = f"Código gerado para {username}: {token[:4]}-{token[4:8]}-{token[8:]}"
                        logger.info(f"Token de recuperação gerado pelo admin para usuário: {username}")
                    except sqlite3.IntegrityError:
                        message = "Erro ao gerar código. Tente novamente."
                else:
                    message = "Usuário não encontrado."
            conn.commit()

    with get_db() as conn:
        # Busca usuários e seus tokens ativos
        usuarios_data = []
        usuarios = conn.execute(
            "SELECT username, is_admin FROM login ORDER BY username"
        ).fetchall()
        
        for usuario, is_admin in usuarios:
            # Busca token ativo mais recente para este usuário
            from datetime import datetime
            token_data = conn.execute(
                """SELECT token, expires_at, used 
                FROM password_reset_tokens 
                WHERE username = ? AND used = 0
                ORDER BY created_at DESC 
                LIMIT 1""",
                (usuario,)
            ).fetchone()
            
            token_ativo = None
            if token_data:
                token, expires_at_str, used = token_data
                try:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if datetime.now() < expires_at:
                        token_ativo = token
                except (ValueError, TypeError):
                    pass
            
            usuarios_data.append({
                'username': usuario,
                'is_admin': is_admin,
                'token_ativo': token_ativo
            })
    
    return render_template("admin_logins.html",
                           usuarios=usuarios_data, message=message)


@app.route("/admin/impressoras", methods=["GET", "POST"])
@login_required
@admin_required
@csrf_exempt_if_enabled
def admin_impressoras():
    """Página de administração de impressoras - cadastro de tipo (duplex/simplex)"""
    message = ""
    impressoras_list = []
    total_cadastradas = 0
    total_rede = 0
    total_eventos = 0
    
    try:
        with get_db() as conn:
            if request.method == "POST":
                # Suporta tanto form-data quanto JSON
                if request.is_json:
                    data = request.get_json()
                    action = data.get("action")
                    printer_name = data.get("printer_name", "").strip()
                    sector = data.get("sector", "").strip()
                    tipo = data.get("tipo", "simplex").strip().lower()
                else:
                    action = request.form.get("action")
                    printer_name = request.form.get("printer_name", "").strip()
                    sector = request.form.get("sector", "").strip()
                    tipo = request.form.get("tipo", "simplex").strip().lower()
                
                # Validação
                if not printer_name:
                    message = "Nome da impressora é obrigatório."
                    if request.is_json:
                        # Retorna antes de fechar o context manager
                        response = jsonify({"error": message})
                        return response, 400
                elif tipo not in ["duplex", "simplex"]:
                    message = "Tipo deve ser 'duplex' ou 'simplex'."
                    if request.is_json:
                        # Retorna antes de fechar o context manager
                        response = jsonify({"error": message})
                        return response, 400
                else:
                    if action == "add" or action == "edit":
                        # Insere ou atualiza impressora
                        # Verifica se já existe e busca tipo anterior
                        cursor_old = conn.execute(
                            "SELECT tipo FROM printers WHERE printer_name = ?",
                            (printer_name,)
                        )
                        old_row = cursor_old.fetchone()
                        existing = old_row is not None
                        tipo_anterior = old_row[0] if old_row else None
                        
                        if existing:
                            # Atualiza
                            # Verifica se coluna ip existe
                            existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(printers)").fetchall()]
                            has_ip = 'ip' in existing_columns
                            
                            if has_ip:
                                ip = request.form.get("ip", "").strip() if not request.is_json else (request.json.get("ip", "").strip() if request.is_json else "")
                                conn.execute(
                                    "UPDATE printers SET sector = ?, tipo = ?, ip = ? WHERE printer_name = ?",
                                    (sector, tipo, ip if ip else None, printer_name)
                                )
                            else:
                                conn.execute(
                                    "UPDATE printers SET sector = ?, tipo = ? WHERE printer_name = ?",
                                    (sector, tipo, printer_name)
                                )
                        else:
                            # Insere
                            # Verifica se coluna ip existe
                            existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(printers)").fetchall()]
                            has_ip = 'ip' in existing_columns
                            
                            if has_ip:
                                ip = request.form.get("ip", "").strip() if not request.is_json else (request.json.get("ip", "").strip() if request.is_json else "")
                                conn.execute(
                                    "INSERT INTO printers (printer_name, sector, tipo, ip) VALUES (?, ?, ?, ?)",
                                    (printer_name, sector, tipo, ip if ip else None)
                                )
                            else:
                                conn.execute(
                                    "INSERT INTO printers (printer_name, sector, tipo) VALUES (?, ?, ?)",
                                    (printer_name, sector, tipo)
                                )
                        conn.commit()
                        action_done = "atualizada" if existing else "cadastrada"
                        
                        # Recalcula eventos se tipo mudou ou é novo cadastro
                        eventos_atualizados = 0
                        if not existing or tipo_anterior != tipo:
                            eventos_atualizados = recalcular_eventos_impressora(conn, printer_name, tipo)
                        
                        if eventos_atualizados > 0:
                            message = f"Impressora '{printer_name}' {action_done} com sucesso (tipo: {tipo}). {eventos_atualizados} eventos recalculados."
                        else:
                            message = f"Impressora '{printer_name}' {action_done} com sucesso (tipo: {tipo})."
                        
                        if request.is_json:
                            # Retorna antes de fechar o context manager
                            response = jsonify({
                                "status": "success", 
                                "message": message,
                                "eventos_atualizados": eventos_atualizados
                            })
                            return response, 200
                    elif action == "delete":
                        conn.execute("DELETE FROM printers WHERE printer_name = ?", (printer_name,))
                        conn.commit()
                        message = f"Impressora '{printer_name}' excluída com sucesso."
                        if request.is_json:
                            # Retorna antes de fechar o context manager
                            response = jsonify({"status": "success", "message": message})
                            return response, 200
            
            # Verifica se a tabela printers existe, se não, cria
            try:
                conn.execute("SELECT 1 FROM printers LIMIT 1")
            except sqlite3.OperationalError:
                # Tabela não existe, cria
                logger.info("Tabela 'printers' não existe, criando...")
                conn.execute(
                    """CREATE TABLE IF NOT EXISTS printers (
                    printer_name TEXT PRIMARY KEY,
                    sector TEXT,
                    tipo TEXT DEFAULT 'simplex',
                    ip TEXT)"""
                )
                conn.commit()
                logger.info("Tabela 'printers' criada com sucesso")
            
            # Verifica se coluna ip existe na tabela printers
            existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(printers)").fetchall()]
            has_ip_column = 'ip' in existing_columns
            
            # Adiciona coluna ip se não existir
            if not has_ip_column:
                try:
                    conn.execute("ALTER TABLE printers ADD COLUMN ip TEXT")
                    conn.commit()
                    has_ip_column = True
                    logger.info("Coluna 'ip' adicionada à tabela 'printers'")
                except sqlite3.OperationalError:
                    pass  # Coluna já existe ou erro ao adicionar
            
            # Busca todas as impressoras cadastradas
            try:
                if has_ip_column:
                    impressoras_cadastradas = conn.execute(
                        "SELECT printer_name, sector, tipo, ip FROM printers ORDER BY printer_name"
                    ).fetchall()
                else:
                    impressoras_cadastradas = conn.execute(
                        "SELECT printer_name, sector, tipo FROM printers ORDER BY printer_name"
                    ).fetchall()
                logger.info(f"✅ Encontradas {len(impressoras_cadastradas)} impressoras cadastradas no banco")
            except sqlite3.OperationalError as e:
                logger.error(f"Erro ao buscar impressoras cadastradas: {e}")
                impressoras_cadastradas = []
            
            # Busca todas as impressoras que aparecem nos eventos (para sugerir cadastro)
            impressoras_eventos = conn.execute(
                """SELECT DISTINCT printer_name 
                   FROM events 
                   WHERE printer_name IS NOT NULL AND printer_name != ''
                   ORDER BY printer_name"""
            ).fetchall()
            
            # Busca impressoras da rede (se solicitado)
            discover_network = request.args.get('discover', 'false').lower() == 'true'
            impressoras_rede = []
            
            if discover_network:
                try:
                    import subprocess
                    import platform
                    import re
                    
                    if platform.system() == 'Windows':
                        logger.info("Iniciando descoberta de impressoras da rede...")
                        
                        # Método 1: WMI Win32_Printer (mais completo, inclui IP)
                        try:
                            ps_command = """
                            $ErrorActionPreference = 'Stop'
                            try {
                                Get-WmiObject -Class Win32_Printer | 
                                Select-Object Name, PrinterStatus, DriverName, PortName, Location, Network, Shared, ShareName | 
                                ConvertTo-Json -Depth 2 -Compress
                            } catch {
                                Write-Output "ERROR: $_"
                                exit 1
                            }
                            """
                            
                            result = subprocess.run(
                                ['powershell', '-ExecutionPolicy', 'Bypass', '-NoProfile', '-Command', ps_command],
                                capture_output=True,
                                text=True,
                                timeout=30,
                                encoding='utf-8',
                                errors='replace',
                                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                            )
                            
                            if result.returncode == 0 and result.stdout.strip():
                                # Remove possíveis mensagens de erro do PowerShell
                                stdout_clean = result.stdout.strip()
                                if stdout_clean.startswith('ERROR:'):
                                    logger.warning(f"PowerShell retornou erro: {stdout_clean}")
                                else:
                                    try:
                                        import json as json_lib
                                        printers_wmi = json_lib.loads(stdout_clean)
                                        
                                        if isinstance(printers_wmi, dict):
                                            printers_wmi = [printers_wmi]
                                        
                                        logger.info(f"WMI encontrou {len(printers_wmi)} impressoras instaladas localmente")
                                        
                                        for printer in printers_wmi:
                                            printer_name = printer.get('Name', '').strip()
                                            port_name = printer.get('PortName', '').strip()
                                            is_network = printer.get('Network', False)
                                            
                                            if printer_name:
                                                # Extrai IP da porta
                                                ip_address = ''
                                                if port_name:
                                                    ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', port_name)
                                                    if ip_match:
                                                        ip_address = ip_match.group(1)
                                                    elif port_name.startswith('IP_') or port_name.startswith('TCPIP_'):
                                                        parts = port_name.split('_')
                                                        for part in parts:
                                                            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', part):
                                                                ip_address = part
                                                                break
                                                
                                                # Só adiciona se for impressora de rede (não local)
                                                # Impressoras locais têm portas como "USB001", "LPT1", etc.
                                                if is_network or ip_address or port_name.startswith(('IP_', 'TCPIP_', '192.', '10.', '172.')):
                                                    impressoras_rede.append({
                                                        'name': printer_name,
                                                        'ip': ip_address,
                                                        'port': port_name,
                                                        'location': printer.get('Location', ''),
                                                        'shared': printer.get('Shared', False),
                                                        'network': is_network or bool(ip_address)
                                                    })
                                    except json_lib.JSONDecodeError as e:
                                        logger.error(f"Erro ao parsear JSON do WMI: {e}")
                                        logger.debug(f"Output recebido: {result.stdout[:500]}")
                                    except Exception as e:
                                        logger.error(f"Erro ao processar impressoras WMI: {e}", exc_info=True)
                            else:
                                if result.stderr:
                                    logger.warning(f"PowerShell retornou erro: {result.stderr}")
                                if result.returncode != 0:
                                    logger.warning(f"PowerShell retornou código {result.returncode}")
                        except subprocess.TimeoutExpired:
                            logger.error("Timeout ao executar comando WMI (30s)")
                        except Exception as e:
                            logger.error(f"Erro ao usar WMI Win32_Printer: {e}", exc_info=True)
                        
                        # Método 2: Busca portas TCP/IP configuradas (pode ter impressoras não instaladas)
                        try:
                            ps_command_ports = """
                            $ErrorActionPreference = 'Stop'
                            try {
                                Get-WmiObject -Class Win32_TCPIPPrinterPort | 
                                Select-Object Name, HostAddress | 
                                ConvertTo-Json -Depth 2 -Compress
                            } catch {
                                Write-Output "ERROR: $_"
                                exit 1
                            }
                            """
                            
                            result_ports = subprocess.run(
                                ['powershell', '-ExecutionPolicy', 'Bypass', '-NoProfile', '-Command', ps_command_ports],
                                capture_output=True,
                                text=True,
                                timeout=20,
                                encoding='utf-8',
                                errors='replace',
                                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                            )
                            
                            if result_ports.returncode == 0 and result_ports.stdout.strip():
                                stdout_clean = result_ports.stdout.strip()
                                if not stdout_clean.startswith('ERROR:'):
                                    try:
                                        import json as json_lib
                                        ports = json_lib.loads(stdout_clean)
                                        
                                        if isinstance(ports, dict):
                                            ports = [ports]
                                        
                                        logger.info(f"Encontradas {len(ports)} portas TCP/IP")
                                        
                                        for port in ports:
                                            port_name = port.get('Name', '').strip()
                                            ip_address = port.get('HostAddress', '').strip()
                                            
                                            if ip_address and port_name:
                                                # Verifica se já não está na lista
                                                if not any(p.get('ip') == ip_address for p in impressoras_rede if p.get('ip')):
                                                    impressoras_rede.append({
                                                        'name': f"Impressora {ip_address}",
                                                        'ip': ip_address,
                                                        'port': port_name,
                                                        'location': '',
                                                        'shared': False,
                                                        'network': True
                                                    })
                                    except json_lib.JSONDecodeError as e:
                                        logger.error(f"Erro ao parsear JSON das portas TCP/IP: {e}")
                                    except Exception as e:
                                        logger.error(f"Erro ao processar portas TCP/IP: {e}", exc_info=True)
                        except subprocess.TimeoutExpired:
                            logger.warning("Timeout ao buscar portas TCP/IP")
                        except Exception as e:
                            logger.error(f"Erro ao buscar portas TCP/IP: {e}", exc_info=True)
                        
                        # Método 3: Find-Printer (descobre impressoras na rede sem instalar) ⭐ NOVO
                        try:
                            logger.info("Buscando impressoras na rede via Find-Printer...")
                            ps_command_find = """
                            $ErrorActionPreference = 'Stop'
                            try {
                                # Find-Printer descobre impressoras na rede sem instalar
                                $printers = Find-Printer -ErrorAction SilentlyContinue | 
                                    Select-Object Name, PrinterStatus, DriverName, PortName, Location, Network, Shared, ComputerName |
                                    ConvertTo-Json -Depth 2 -Compress
                                if ($printers) {
                                    Write-Output $printers
                                } else {
                                    Write-Output "[]"
                                }
                            } catch {
                                # Se Find-Printer não funcionar, tenta método alternativo
                                Write-Output "[]"
                            }
                            """
                            
                            result_find = subprocess.run(
                                ['powershell', '-ExecutionPolicy', 'Bypass', '-NoProfile', '-Command', ps_command_find],
                                capture_output=True,
                                text=True,
                                timeout=15,
                                encoding='utf-8',
                                errors='replace',
                                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                            )
                            
                            if result_find.returncode == 0 and result_find.stdout.strip():
                                stdout_clean = result_find.stdout.strip()
                                if stdout_clean and stdout_clean != "[]" and not stdout_clean.startswith('ERROR:'):
                                    try:
                                        import json as json_lib
                                        find_printers = json_lib.loads(stdout_clean)
                                        
                                        if isinstance(find_printers, dict):
                                            find_printers = [find_printers]
                                        
                                        logger.info(f"Find-Printer encontrou {len(find_printers)} impressoras na rede")
                                        
                                        for printer in find_printers:
                                            printer_name = printer.get('Name', '').strip()
                                            port_name = printer.get('PortName', '').strip()
                                            computer_name = printer.get('ComputerName', '').strip()
                                            
                                            if printer_name:
                                                # Extrai IP da porta ou do computador
                                                ip_address = ''
                                                if port_name:
                                                    ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', port_name)
                                                    if ip_match:
                                                        ip_address = ip_match.group(1)
                                                elif computer_name:
                                                    try:
                                                        import socket
                                                        ip_address = socket.gethostbyname(computer_name)
                                                    except:
                                                        pass
                                                
                                                # Verifica se já não está na lista
                                                if not any(p.get('name') == printer_name for p in impressoras_rede if p.get('name')):
                                                    impressoras_rede.append({
                                                        'name': printer_name,
                                                        'ip': ip_address,
                                                        'port': port_name,
                                                        'location': printer.get('Location', ''),
                                                        'shared': printer.get('Shared', False),
                                                        'network': printer.get('Network', True)
                                                    })
                                    except json_lib.JSONDecodeError as e:
                                        logger.debug(f"Find-Printer não retornou JSON válido (pode não ter encontrado impressoras): {e}")
                                    except Exception as e:
                                        logger.error(f"Erro ao processar Find-Printer: {e}", exc_info=True)
                        except subprocess.TimeoutExpired:
                            logger.warning("Timeout ao buscar via Find-Printer")
                        except Exception as e:
                            logger.error(f"Erro ao buscar via Find-Printer: {e}", exc_info=True)
                        
                        # Método 3.1: WS-Discovery via Get-PrinterPort (portas descobertas)
                        try:
                            logger.info("Buscando portas de rede descobertas via WS-Discovery...")
                            ps_command_wsd = """
                            $ErrorActionPreference = 'Stop'
                            try {
                                # Busca portas de rede descobertas (WSD, IP, etc.)
                                $ports = Get-PrinterPort | Where-Object { 
                                    $_.Name -like 'WSD*' -or 
                                    $_.Name -like 'IP_*' -or 
                                    $_.Name -like 'TCPIP_*' -or
                                    $_.Name -match '\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}' 
                                }
                                
                                $printers = @()
                                foreach ($port in $ports) {
                                    $ip = if ($port.Name -match '\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}') { 
                                        $matches[0] 
                                    } elseif ($port.Description -match '\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}') {
                                        $matches[0]
                                    } else { 
                                        $null 
                                    }
                                    if ($ip) {
                                        $printers += @{
                                            Name = "Impressora $ip"
                                            PortName = $port.Name
                                            HostAddress = $ip
                                        }
                                    }
                                }
                                $printers | ConvertTo-Json -Depth 2 -Compress
                            } catch {
                                Write-Output "ERROR: $_"
                                exit 1
                            }
                            """
                            
                            result_wsd = subprocess.run(
                                ['powershell', '-ExecutionPolicy', 'Bypass', '-NoProfile', '-Command', ps_command_wsd],
                                capture_output=True,
                                text=True,
                                timeout=10,
                                encoding='utf-8',
                                errors='replace',
                                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                            )
                            
                            if result_wsd.returncode == 0 and result_wsd.stdout.strip():
                                stdout_clean = result_wsd.stdout.strip()
                                if not stdout_clean.startswith('ERROR:'):
                                    try:
                                        import json as json_lib
                                        wsd_printers = json_lib.loads(stdout_clean)
                                        
                                        if isinstance(wsd_printers, dict):
                                            wsd_printers = [wsd_printers]
                                        
                                        logger.info(f"WS-Discovery encontrou {len(wsd_printers)} portas de rede")
                                        
                                        for printer in wsd_printers:
                                            ip_address = printer.get('HostAddress', '').strip() or printer.get('ip', '').strip()
                                            port_name = printer.get('PortName', '').strip() or printer.get('Name', '').strip()
                                            printer_name = printer.get('Name', '').strip()
                                            
                                            if ip_address:
                                                # Verifica se já não está na lista
                                                if not any(p.get('ip') == ip_address for p in impressoras_rede if p.get('ip')):
                                                    impressoras_rede.append({
                                                        'name': printer_name if printer_name and printer_name != f"Impressora {ip_address}" else f"Impressora {ip_address}",
                                                        'ip': ip_address,
                                                        'port': port_name,
                                                        'location': '',
                                                        'shared': False,
                                                        'network': True
                                                    })
                                    except json_lib.JSONDecodeError as e:
                                        logger.error(f"Erro ao parsear JSON do WS-Discovery: {e}")
                                    except Exception as e:
                                        logger.error(f"Erro ao processar WS-Discovery: {e}", exc_info=True)
                        except subprocess.TimeoutExpired:
                            logger.warning("Timeout ao buscar via WS-Discovery")
                        except Exception as e:
                            logger.error(f"Erro ao buscar via WS-Discovery: {e}", exc_info=True)
                        
                        # Método 4: Get-Printer (PowerShell moderno - mais rápido e completo)
                        try:
                            logger.info("Buscando impressoras via Get-Printer (PowerShell moderno)...")
                            ps_command_getprinter = """
                            $ErrorActionPreference = 'Stop'
                            try {
                                # Get-Printer é mais rápido e completo que WMI
                                Get-Printer | Where-Object { 
                                    $_.Network -eq $true -or 
                                    $_.PortName -like '*.*' -or
                                    $_.PortName -like 'IP_*' -or
                                    $_.PortName -like 'WSD*' -or
                                    $_.PortName -like 'TCPIP_*'
                                } | 
                                Select-Object Name, PortName, DriverName, Location, Network, Shared, PrinterStatus | 
                                ConvertTo-Json -Depth 2 -Compress
                            } catch {
                                Write-Output "ERROR: $_"
                                exit 1
                            }
                            """
                            
                            result_getprinter = subprocess.run(
                                ['powershell', '-ExecutionPolicy', 'Bypass', '-NoProfile', '-Command', ps_command_getprinter],
                                capture_output=True,
                                text=True,
                                timeout=10,
                                encoding='utf-8',
                                errors='replace',
                                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                            )
                            
                            if result_getprinter.returncode == 0 and result_getprinter.stdout.strip():
                                stdout_clean = result_getprinter.stdout.strip()
                                if not stdout_clean.startswith('ERROR:'):
                                    try:
                                        import json as json_lib
                                        getprinter_printers = json_lib.loads(stdout_clean)
                                        
                                        if isinstance(getprinter_printers, dict):
                                            getprinter_printers = [getprinter_printers]
                                        
                                        logger.info(f"Get-Printer encontrou {len(getprinter_printers)} impressoras")
                                        
                                        for printer in getprinter_printers:
                                            printer_name = printer.get('Name', '').strip()
                                            port_name = printer.get('PortName', '').strip()
                                            
                                            if printer_name:
                                                # Extrai IP da porta
                                                ip_address = ''
                                                if port_name:
                                                    ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', port_name)
                                                    if ip_match:
                                                        ip_address = ip_match.group(1)
                                                    elif port_name.startswith('IP_') or port_name.startswith('TCPIP_'):
                                                        parts = port_name.split('_')
                                                        for part in parts:
                                                            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', part):
                                                                ip_address = part
                                                                break
                                                
                                                # Verifica se já não está na lista
                                                if not any(p.get('ip') == ip_address for p in impressoras_rede if ip_address and p.get('ip')):
                                                    impressoras_rede.append({
                                                        'name': printer_name,
                                                        'ip': ip_address,
                                                        'port': port_name,
                                                        'location': printer.get('Location', ''),
                                                        'shared': printer.get('Shared', False),
                                                        'network': printer.get('Network', False)
                                                    })
                                    except json_lib.JSONDecodeError as e:
                                        logger.error(f"Erro ao parsear JSON do Get-Printer: {e}")
                                    except Exception as e:
                                        logger.error(f"Erro ao processar Get-Printer: {e}", exc_info=True)
                        except subprocess.TimeoutExpired:
                            logger.warning("Timeout ao buscar via Get-Printer")
                        except Exception as e:
                            logger.error(f"Erro ao buscar via Get-Printer: {e}", exc_info=True)
                        
                        # Método 5: Scan ativo de rede (testa portas de impressora em vários IPs)
                        try:
                            logger.info("Escaneando rede ativamente procurando impressoras...")
                            import socket
                            import threading
                            from concurrent.futures import ThreadPoolExecutor, as_completed
                            
                            # Obtém IP local e sub-rede
                            hostname = socket.gethostname()
                            local_ip = socket.gethostbyname(hostname)
                            ip_parts = local_ip.split('.')
                            network_base = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"
                            
                            # Portas comuns de impressoras
                            printer_ports = [9100, 631, 515]  # JetDirect, IPP, LPR
                            found_ips = set()
                            lock = threading.Lock()
                            
                            def scan_ip_port(ip, port):
                                """Testa se uma porta está aberta em um IP"""
                                try:
                                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                    sock.settimeout(0.3)
                                    result = sock.connect_ex((ip, port))
                                    sock.close()
                                    return result == 0
                                except:
                                    return False
                            
                            def is_computer_hostname(hostname):
                                """Verifica se o hostname indica que é um computador, não impressora"""
                                if not hostname:
                                    return False
                                hostname_lower = hostname.lower()
                                # Palavras que indicam computador
                                computer_keywords = ['pc', 'computer', 'desktop', 'laptop', 'notebook', 
                                                    'workstation', 'server', 'host', 'client', 'win-', 
                                                    'win10', 'win11', 'desktop-', 'laptop-']
                                return any(kw in hostname_lower for kw in computer_keywords)
                            
                            def check_if_printer(ip, port):
                                """Verifica se realmente é uma impressora (não um PC)"""
                                try:
                                    # Se porta 80 ou 443 está aberta, tenta verificar HTTP
                                    if port in [80, 443, 8080]:
                                        try:
                                            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                            sock.settimeout(1)
                                            sock.connect((ip, port))
                                            # Envia requisição HTTP simples
                                            request = f"GET / HTTP/1.1\r\nHost: {ip}\r\n\r\n"
                                            sock.send(request.encode())
                                            response = sock.recv(4096).decode('utf-8', errors='ignore').lower()
                                            sock.close()
                                            
                                            # Palavras-chave que indicam impressora
                                            printer_keywords = ['printer', 'print', 'hp', 'canon', 'epson', 
                                                              'brother', 'kyocera', 'xerox', 'lexmark', 'ricoh',
                                                              'samsung', 'konica', 'minolta', 'sharp', 'toshiba',
                                                              'jetdirect', 'ipp', 'cups', 'printing']
                                            
                                            # Se contém palavras de impressora, é impressora
                                            if any(kw in response for kw in printer_keywords):
                                                return True
                                            
                                            # Se não contém palavras de impressora, provavelmente é PC
                                            return False
                                        except:
                                            pass
                                    
                                    # Para porta 9100 (JetDirect), geralmente é impressora
                                    if port == 9100:
                                        return True
                                    
                                    # Para porta 631 (IPP), geralmente é impressora
                                    if port == 631:
                                        return True
                                    
                                    # Para porta 515 (LPR), geralmente é impressora
                                    if port == 515:
                                        return True
                                    
                                    return True  # Por padrão, assume que é impressora se tem porta aberta
                                except:
                                    return True  # Em caso de erro, assume que é impressora
                            
                            def scan_ip(ip):
                                """Escaneia um IP procurando portas de impressora"""
                                if ip == local_ip:
                                    return None
                                
                                for port in printer_ports:
                                    if scan_ip_port(ip, port):
                                        # Verifica se realmente é uma impressora
                                        if not check_if_printer(ip, port):
                                            continue  # Pula se não for impressora
                                        
                                        with lock:
                                            if ip not in found_ips:
                                                found_ips.add(ip)
                                                try:
                                                    hostname_resolved = socket.gethostbyaddr(ip)[0]
                                                    
                                                    # Filtra hostnames que indicam PC/computador
                                                    if is_computer_hostname(hostname_resolved):
                                                        logger.debug(f"Filtrando {ip} - hostname indica PC: {hostname_resolved}")
                                                        found_ips.remove(ip)
                                                        continue
                                                    
                                                    printer_name = hostname_resolved
                                                except:
                                                    printer_name = f"Impressora {ip}"
                                                
                                                # Verifica se já não está na lista
                                                if not any(p.get('ip') == ip for p in impressoras_rede if p.get('ip')):
                                                    impressoras_rede.append({
                                                        'name': printer_name,
                                                        'ip': ip,
                                                        'port': f"TCP/{port}",
                                                        'location': '',
                                                        'shared': False,
                                                        'network': True
                                                    })
                                                return ip
                                return None
                            
                            # Escaneia IPs da rede em paralelo (mais rápido)
                            # Escaneia TODA a sub-rede (1-254) para encontrar todas as impressoras
                            scan_ips = list(range(1, 255))  # Escaneia toda a faixa de IPs
                            
                            logger.info(f"Escaneando {len(scan_ips)} IPs na rede {network_base}.x procurando impressoras...")
                            
                            # Usa ThreadPoolExecutor para escanear em paralelo
                            # Aumenta workers para escanear mais rápido
                            with ThreadPoolExecutor(max_workers=100) as executor:
                                futures = {executor.submit(scan_ip, f"{network_base}.{i}"): i for i in scan_ips}
                                
                                # Aguarda resultados com timeout maior para rede completa
                                completed = 0
                                for future in as_completed(futures, timeout=60):
                                    try:
                                        future.result(timeout=1)
                                        completed += 1
                                        # Mostra progresso a cada 50 IPs escaneados
                                        if completed % 50 == 0:
                                            logger.info(f"Progresso: {completed}/{len(scan_ips)} IPs escaneados, {len(found_ips)} impressoras encontradas")
                                    except:
                                        pass
                                    
                                    # Aumenta limite de impressoras encontradas
                                    if len(found_ips) >= 100:
                                        logger.info(f"Limite de 100 impressoras atingido, parando scan...")
                                        break
                            
                            logger.info(f"✅ Scan ativo concluído: {len(found_ips)} dispositivos com portas de impressora encontrados")
                        except Exception as e:
                            logger.error(f"Erro ao escanear rede: {e}", exc_info=True)
                        
                        logger.info(f"Descoberta concluída: {len(impressoras_rede)} impressoras encontradas")
                    else:
                        logger.warning("Descoberta de impressoras só está disponível no Windows")
                            
                except Exception as e:
                    logger.error(f"Erro ao descobrir impressoras da rede: {e}", exc_info=True)
                    message = f"Erro ao descobrir impressoras: {str(e)}"
            
            # Cria lista de impressoras com status (cadastrada ou não)
            # Garante que has_ip_column está definido
            try:
                _ = has_ip_column  # Verifica se está definido
            except NameError:
                # Se não estiver definido, define agora
                existing_columns_check = [col[1] for col in conn.execute("PRAGMA table_info(printers)").fetchall()]
                has_ip_column = 'ip' in existing_columns_check
                logger.info(f"has_ip_column definido como: {has_ip_column}")
            
            # Inicializa lista de impressoras (se ainda não foi inicializada)
            if not impressoras_list:
                impressoras_list = []
            
            # Converte rows para dicionários se necessário
            cadastradas_nomes = set()
            if impressoras_cadastradas:
                logger.info(f"Processando {len(impressoras_cadastradas)} impressoras cadastradas...")
                for row in impressoras_cadastradas:
                    if isinstance(row, sqlite3.Row):
                        cadastradas_nomes.add(row['printer_name'])
                    elif isinstance(row, (list, tuple)) and len(row) > 0:
                        cadastradas_nomes.add(row[0])
                    else:
                        cadastradas_nomes.add(str(row))
            else:
                logger.warning("⚠️ Nenhuma impressora cadastrada encontrada no banco de dados")
            
            todas_impressoras = set()
            
            # Adiciona impressoras cadastradas
            for row in impressoras_cadastradas:
                try:
                    # Extrai dados do row (pode ser Row object ou tupla)
                    if isinstance(row, sqlite3.Row):
                        # sqlite3.Row não tem .get(), usa acesso direto
                        printer_name = row['printer_name'] if 'printer_name' in row.keys() else ''
                        sector = row['sector'] if 'sector' in row.keys() and row['sector'] else ''
                        tipo = row['tipo'] if 'tipo' in row.keys() and row['tipo'] else 'simplex'
                        ip = row['ip'] if has_ip_column and 'ip' in row.keys() and row['ip'] else ''
                    elif isinstance(row, (list, tuple)):
                        printer_name = row[0] if len(row) > 0 else ''
                        sector = row[1] if len(row) > 1 and row[1] else ''
                        tipo = row[2] if len(row) > 2 and row[2] else 'simplex'
                        ip = row[3] if has_ip_column and len(row) > 3 and row[3] else ''
                    else:
                        continue
                    
                    if not printer_name:
                        continue
                    
                    printer_data = {
                        'printer_name': printer_name,
                        'sector': sector or '',
                        'tipo': tipo or 'simplex',
                        'cadastrada': True,
                        'source': 'cadastrada'
                    }
                    # Adiciona IP se disponível
                    if has_ip_column and ip:
                        printer_data['ip'] = ip
                    impressoras_list.append(printer_data)
                    todas_impressoras.add(printer_name)
                    logger.debug(f"✅ Impressora adicionada à lista: {printer_name} (tipo: {tipo}, cadastrada: True)")
                except Exception as e:
                    logger.error(f"❌ Erro ao processar impressora cadastrada: {e}, row: {row}", exc_info=True)
                    continue
            
            # Adiciona impressoras dos eventos
            for row in impressoras_eventos:
                try:
                    # Extrai nome da impressora
                    if isinstance(row, sqlite3.Row):
                        printer_name = row['printer_name']
                    elif isinstance(row, (list, tuple)) and len(row) > 0:
                        printer_name = row[0]
                    else:
                        continue
                    
                    if printer_name and printer_name not in cadastradas_nomes:
                        impressoras_list.append({
                            'printer_name': printer_name,
                            'sector': '',
                            'tipo': 'simplex',
                            'cadastrada': False,
                            'source': 'eventos'
                        })
                        todas_impressoras.add(printer_name)
                except Exception as e:
                    logger.error(f"Erro ao processar impressora dos eventos: {e}, row: {row}")
                    continue
            
            # Adiciona impressoras descobertas da rede (que não estão cadastradas)
            for printer_info in impressoras_rede:
                printer_name = printer_info.get('name', '') if isinstance(printer_info, dict) else str(printer_info)
                
                if printer_name and printer_name not in todas_impressoras:
                    impressoras_list.append({
                        'printer_name': printer_name,
                        'sector': '',
                        'tipo': 'simplex',
                        'cadastrada': False,
                        'source': 'rede',
                        'ip': printer_info.get('ip', '') if isinstance(printer_info, dict) else '',
                        'port': printer_info.get('port', '') if isinstance(printer_info, dict) else '',
                        'location': printer_info.get('location', '') if isinstance(printer_info, dict) else ''
                    })
                    todas_impressoras.add(printer_name)
            
            # Ordena por nome
            impressoras_list.sort(key=lambda x: x['printer_name'])
            
            # Conta impressoras por fonte
            total_cadastradas = sum(1 for i in impressoras_list if i.get('cadastrada'))
            total_rede = sum(1 for i in impressoras_list if i.get('source') == 'rede')
            total_eventos = sum(1 for i in impressoras_list if i.get('source') == 'eventos')
            
            logger.info(f"📊 Resumo: {total_cadastradas} cadastradas, {total_rede} da rede, {total_eventos} dos eventos, Total: {len(impressoras_list)}")
            
    except Exception as e:
        logger.error(f"Erro em admin_impressoras: {e}", exc_info=True)
        message = f"Erro ao processar: {str(e)}"
        impressoras_list = []
        total_cadastradas = 0
        total_rede = 0
        total_eventos = 0
        if request.is_json:
            return jsonify({"error": message}), 500
    
    if request.is_json:
        return jsonify({
            "status": "success",
            "impressoras": impressoras_list,
            "message": message,
            "total_cadastradas": total_cadastradas,
            "total_rede": total_rede,
            "total_eventos": total_eventos
        }), 200
    
    return render_template("admin_impressoras.html", 
                          impressoras=impressoras_list, 
                          message=message,
                          total_cadastradas=total_cadastradas,
                          total_rede=total_rede,
                          total_eventos=total_eventos)


@app.route("/api/admin/discover_printers", methods=["GET"])
@login_required
@admin_required
@csrf_exempt_if_enabled
def api_discover_printers():
    """
    API para descobrir impressoras da rede/local usando PowerShell/WMI
    
    Returns:
        JSON com lista de impressoras encontradas
    """
    try:
        import subprocess
        import platform
        
        # Só funciona no Windows
        if platform.system() != 'Windows':
            return jsonify({
                "status": "error",
                "message": "Descoberta de impressoras só está disponível no Windows",
                "printers": []
            }), 400
        
        printers_found = []
        
        import re
        
        # Método 1: WMI Win32_Printer (mais completo, inclui IP)
        try:
            logger.info("Iniciando descoberta de impressoras via API...")
            ps_command = """
            $ErrorActionPreference = 'Stop'
            try {
                Get-WmiObject -Class Win32_Printer | 
                Select-Object Name, PrinterStatus, DriverName, PortName, Location, Network, Shared, ShareName | 
                ConvertTo-Json -Depth 2 -Compress
            } catch {
                Write-Output "ERROR: $_"
                exit 1
            }
            """
            
            result = subprocess.run(
                ['powershell', '-ExecutionPolicy', 'Bypass', '-NoProfile', '-Command', ps_command],
                capture_output=True,
                text=True,
                timeout=10,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0 and result.stdout.strip():
                stdout_clean = result.stdout.strip()
                if stdout_clean.startswith('ERROR:'):
                    logger.warning(f"PowerShell retornou erro: {stdout_clean}")
                else:
                    try:
                        import json as json_lib
                        printers_wmi = json_lib.loads(stdout_clean)
                        
                        if isinstance(printers_wmi, dict):
                            printers_wmi = [printers_wmi]
                        
                        logger.info(f"WMI encontrou {len(printers_wmi)} impressoras")
                        
                        for printer in printers_wmi:
                            printer_name = printer.get('Name', '').strip()
                            port_name = printer.get('PortName', '').strip()
                            
                            if printer_name:
                                # Extrai IP da porta
                                ip_address = ''
                                if port_name:
                                    ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', port_name)
                                    if ip_match:
                                        ip_address = ip_match.group(1)
                                    elif port_name.startswith('IP_') or port_name.startswith('TCPIP_'):
                                        parts = port_name.split('_')
                                        for part in parts:
                                            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', part):
                                                ip_address = part
                                                break
                                
                                printers_found.append({
                                    'name': printer_name,
                                    'status': printer.get('PrinterStatus', 'Unknown'),
                                    'driver': printer.get('DriverName', ''),
                                    'port': port_name,
                                    'ip': ip_address,
                                    'location': printer.get('Location', ''),
                                    'network': printer.get('Network', False),
                                    'shared': printer.get('Shared', False),
                                    'source': 'WMI'
                                })
                    except json_lib.JSONDecodeError as e:
                        logger.error(f"Erro ao parsear JSON do WMI: {e}")
                        logger.debug(f"Output recebido: {result.stdout[:500]}")
                    except Exception as e:
                        logger.error(f"Erro ao processar impressoras WMI: {e}", exc_info=True)
            else:
                if result.stderr:
                    logger.warning(f"PowerShell retornou erro: {result.stderr}")
                if result.returncode != 0:
                    logger.warning(f"PowerShell retornou código {result.returncode}")
        except subprocess.TimeoutExpired:
            logger.error("Timeout ao executar comando WMI (10s)")
        except Exception as e:
            logger.error(f"Erro ao usar WMI Win32_Printer: {e}", exc_info=True)
        
        # Método 2: Busca portas TCP/IP configuradas
        try:
            ps_command_ports = """
            $ErrorActionPreference = 'Stop'
            try {
                Get-WmiObject -Class Win32_TCPIPPrinterPort | 
                Select-Object Name, HostAddress | 
                ConvertTo-Json -Depth 2 -Compress
            } catch {
                Write-Output "ERROR: $_"
                exit 1
            }
            """
            
            result_ports = subprocess.run(
                ['powershell', '-ExecutionPolicy', 'Bypass', '-NoProfile', '-Command', ps_command_ports],
                capture_output=True,
                text=True,
                timeout=10,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result_ports.returncode == 0 and result_ports.stdout.strip():
                stdout_clean = result_ports.stdout.strip()
                if not stdout_clean.startswith('ERROR:'):
                    try:
                        import json as json_lib
                        ports = json_lib.loads(stdout_clean)
                        
                        if isinstance(ports, dict):
                            ports = [ports]
                        
                        logger.info(f"Encontradas {len(ports)} portas TCP/IP")
                        
                        for port in ports:
                            port_name = port.get('Name', '').strip()
                            ip_address = port.get('HostAddress', '').strip()
                            
                            if ip_address:
                                # Verifica se já não está na lista
                                if not any(p.get('ip') == ip_address for p in printers_found):
                                    printers_found.append({
                                        'name': f"Impressora {ip_address}",
                                        'status': 'Unknown',
                                        'driver': '',
                                        'port': port_name,
                                        'ip': ip_address,
                                        'location': '',
                                        'network': True,
                                        'shared': False,
                                        'source': 'TCP/IP Port'
                                    })
                    except json_lib.JSONDecodeError as e:
                        logger.error(f"Erro ao parsear JSON das portas TCP/IP: {e}")
                    except Exception as e:
                        logger.error(f"Erro ao processar portas TCP/IP: {e}", exc_info=True)
        except subprocess.TimeoutExpired:
            logger.warning("Timeout ao buscar portas TCP/IP")
        except Exception as e:
            logger.error(f"Erro ao buscar portas TCP/IP: {e}", exc_info=True)
        
        # Método 3: Get-Printer (PowerShell moderno - mais rápido)
        try:
            ps_command_getprinter = """
            $ErrorActionPreference = 'Stop'
            try {
                Get-Printer | Where-Object { 
                    $_.Network -eq $true -or 
                    $_.PortName -like '*.*' -or
                    $_.PortName -like 'IP_*' -or
                    $_.PortName -like 'WSD*' -or
                    $_.PortName -like 'TCPIP_*'
                } | 
                Select-Object Name, PortName, DriverName, Location, Network, Shared, PrinterStatus | 
                ConvertTo-Json -Depth 2 -Compress
            } catch {
                Write-Output "ERROR: $_"
                exit 1
            }
            """
            
            result_getprinter = subprocess.run(
                ['powershell', '-ExecutionPolicy', 'Bypass', '-NoProfile', '-Command', ps_command_getprinter],
                capture_output=True,
                text=True,
                timeout=10,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result_getprinter.returncode == 0 and result_getprinter.stdout.strip():
                stdout_clean = result_getprinter.stdout.strip()
                if not stdout_clean.startswith('ERROR:'):
                    try:
                        import json as json_lib
                        getprinter_printers = json_lib.loads(stdout_clean)
                        
                        if isinstance(getprinter_printers, dict):
                            getprinter_printers = [getprinter_printers]
                        
                        logger.info(f"Get-Printer encontrou {len(getprinter_printers)} impressoras")
                        
                        for printer in getprinter_printers:
                            printer_name = printer.get('Name', '').strip()
                            port_name = printer.get('PortName', '').strip()
                            
                            if printer_name:
                                # Extrai IP da porta
                                ip_address = ''
                                if port_name:
                                    ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', port_name)
                                    if ip_match:
                                        ip_address = ip_match.group(1)
                                    elif port_name.startswith('IP_') or port_name.startswith('TCPIP_'):
                                        parts = port_name.split('_')
                                        for part in parts:
                                            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', part):
                                                ip_address = part
                                                break
                                
                                # Verifica se já não está na lista
                                if not any(p.get('ip') == ip_address for p in printers_found if ip_address and p.get('ip')):
                                    printers_found.append({
                                        'name': printer_name,
                                        'status': printer.get('PrinterStatus', 'Unknown'),
                                        'driver': printer.get('DriverName', ''),
                                        'port': port_name,
                                        'ip': ip_address,
                                        'location': printer.get('Location', ''),
                                        'network': printer.get('Network', False),
                                        'shared': printer.get('Shared', False),
                                        'source': 'Get-Printer'
                                    })
                    except json_lib.JSONDecodeError as e:
                        logger.error(f"Erro ao parsear JSON do Get-Printer: {e}")
                    except Exception as e:
                        logger.error(f"Erro ao processar Get-Printer: {e}", exc_info=True)
        except subprocess.TimeoutExpired:
            logger.warning("Timeout ao buscar via Get-Printer")
        except Exception as e:
            logger.error(f"Erro ao buscar via Get-Printer: {e}", exc_info=True)
        
        # Remove duplicatas (por IP, priorizando por nome)
        seen_ips = set()
        seen_names = set()
        unique_printers = []
        for printer in printers_found:
            ip = printer.get('ip', '')
            name = printer.get('name', '')
            
            # Prioriza por IP se disponível, senão por nome
            if ip and ip not in seen_ips:
                seen_ips.add(ip)
                unique_printers.append(printer)
            elif name and name not in seen_names:
                seen_names.add(name)
                unique_printers.append(printer)
        
        logger.info(f"Descoberta concluída: {len(unique_printers)} impressoras únicas encontradas")
        
        return jsonify({
            "status": "success",
            "printers": unique_printers,
            "total": len(unique_printers),
            "message": f"{len(unique_printers)} impressoras encontradas"
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao descobrir impressoras: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Erro ao descobrir impressoras: {str(e)}",
            "printers": [],
            "total": 0
        }), 500


@app.route("/api/admin/printers", methods=["GET", "POST", "PUT", "DELETE"])
@login_required
@admin_required
@csrf_exempt_if_enabled
def api_admin_printers():
    """
    API REST para gerenciar impressoras
    
    GET: Lista todas as impressoras
    POST: Cadastra nova impressora
    PUT: Atualiza impressora existente
    DELETE: Remove impressora
    """
    try:
        with get_db() as conn:
            if request.method == "GET":
                # Lista todas as impressoras
                rows = conn.execute(
                    "SELECT printer_name, sector, tipo FROM printers ORDER BY printer_name"
                ).fetchall()
                
                impressoras = [{
                    'printer_name': row['printer_name'],
                    'sector': row['sector'] or '',
                    'tipo': row['tipo'] or 'simplex'
                } for row in rows]
                
                return jsonify({
                    "status": "success",
                    "impressoras": impressoras,
                    "total": len(impressoras)
                }), 200
            
            elif request.method == "POST":
                # Cadastra nova impressora
                data = request.get_json() if request.is_json else request.form.to_dict()
                printer_name = data.get("printer_name", "").strip()
                sector = data.get("sector", "").strip()
                tipo = data.get("tipo", "simplex").strip().lower()
                
                if not printer_name:
                    return jsonify({"error": "printer_name é obrigatório"}), 400
                
                if tipo not in ["duplex", "simplex"]:
                    return jsonify({"error": "tipo deve ser 'duplex' ou 'simplex'"}), 400
                
                conn.execute(
                    "INSERT INTO printers (printer_name, sector, tipo) VALUES (?, ?, ?)",
                    (printer_name, sector, tipo)
                )
                conn.commit()
                
                # Recalcula eventos da impressora
                eventos_atualizados = recalcular_eventos_impressora(conn, printer_name, tipo)
                
                return jsonify({
                    "status": "success",
                    "message": f"Impressora '{printer_name}' cadastrada com sucesso. {eventos_atualizados} eventos recalculados.",
                    "printer": {
                        "printer_name": printer_name,
                        "sector": sector,
                        "tipo": tipo
                    },
                    "eventos_atualizados": eventos_atualizados
                }), 201
            
            elif request.method == "PUT":
                # Atualiza impressora existente
                data = request.get_json() if request.is_json else request.form.to_dict()
                printer_name = data.get("printer_name", "").strip()
                sector = data.get("sector", "").strip()
                tipo = data.get("tipo", "simplex").strip().lower()
                
                if not printer_name:
                    return jsonify({"error": "printer_name é obrigatório"}), 400
                
                if tipo not in ["duplex", "simplex"]:
                    return jsonify({"error": "tipo deve ser 'duplex' ou 'simplex'"}), 400
                
                # Busca tipo anterior
                cursor_old = conn.execute(
                    "SELECT tipo FROM printers WHERE printer_name = ?",
                    (printer_name,)
                )
                old_row = cursor_old.fetchone()
                tipo_anterior = old_row[0] if old_row else None
                
                cursor = conn.execute(
                    "UPDATE printers SET sector = ?, tipo = ? WHERE printer_name = ?",
                    (sector, tipo, printer_name)
                )
                conn.commit()
                
                if cursor.rowcount == 0:
                    return jsonify({"error": f"Impressora '{printer_name}' não encontrada"}), 404
                
                # Recalcula eventos se tipo mudou
                eventos_atualizados = 0
                if tipo_anterior != tipo:
                    eventos_atualizados = recalcular_eventos_impressora(conn, printer_name, tipo)
                
                return jsonify({
                    "status": "success",
                    "message": f"Impressora '{printer_name}' atualizada com sucesso. {eventos_atualizados} eventos recalculados." if eventos_atualizados > 0 else f"Impressora '{printer_name}' atualizada com sucesso",
                    "printer": {
                        "printer_name": printer_name,
                        "sector": sector,
                        "tipo": tipo
                    },
                    "eventos_atualizados": eventos_atualizados
                }), 200
            
            elif request.method == "DELETE":
                # Remove impressora
                printer_name = request.args.get("printer_name", "").strip()
                
                if not printer_name:
                    return jsonify({"error": "printer_name é obrigatório"}), 400
                
                cursor = conn.execute(
                    "DELETE FROM printers WHERE printer_name = ?",
                    (printer_name,)
                )
                conn.commit()
                
                if cursor.rowcount == 0:
                    return jsonify({"error": f"Impressora '{printer_name}' não encontrada"}), 404
                
                return jsonify({
                    "status": "success",
                    "message": f"Impressora '{printer_name}' removida com sucesso"
                }), 200
    
    except sqlite3.IntegrityError:
        return jsonify({"error": "Impressora já cadastrada"}), 409
    except Exception as e:
        logger.error(f"Erro em api_admin_printers: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/custo-historico")
@login_required
def api_custo_historico():
    """API para histórico de custos ao longo do tempo"""
    days = int(request.args.get("days", 30))
    
    with get_db() as conn:
        # Impressão = Folha lógica (job) | Páginas = Folha física (papel)
        # Calcula custo diário considerando folhas físicas
        rows = conn.execute("""
            SELECT 
                date(date) as dia,
                pages_printed,
                duplex,
                color_mode,
                COALESCE(copies, 1) as copies
            FROM events
            WHERE date(date) >= date('now', '-' || ? || ' days')
            ORDER BY dia
        """, (days,)).fetchall()
        
        # Agrupa por dia e calcula folhas físicas
        historico_dict = {}
        for row in rows:
            dia = row[0]
            pages = row[1] or 0
            duplex_val = row[2] if len(row) > 2 else None
            color_mode = row[3] if len(row) > 3 else None
            copies_val = row[4] if len(row) > 4 else 1
            
            folhas_fisicas = calcular_folhas_fisicas(pages, duplex_val, copies_val)
            
            if dia not in historico_dict:
                historico_dict[dia] = {
                    'paginas_total': 0,
                    'paginas_color': 0,
                    'paginas_bw': 0
                }
            
            historico_dict[dia]['paginas_total'] += folhas_fisicas
            
            if color_mode == 'Color':
                historico_dict[dia]['paginas_color'] += folhas_fisicas
            elif color_mode == 'Black & White':
                historico_dict[dia]['paginas_bw'] += folhas_fisicas
        
        # Prepara histórico (sem custos - sistema removido)
        historico = []
        for dia, dados in sorted(historico_dict.items()):
            historico.append({
                'dia': dia,
                'paginas_total': dados['paginas_total'],
                'paginas_color': dados['paginas_color'],
                'paginas_bw': dados['paginas_bw']
            })
    
    return jsonify(historico)


@app.route("/api/alertas")
@login_required
def api_alertas():
    """API para alertas de uso de cor"""
    alerts = check_color_alerts()
    return jsonify(alerts)


@app.route("/dashboard")
@login_required
def dashboard():
    """Dashboard unificado e otimizado com relatórios detalhados"""
    from datetime import datetime, timedelta
    
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    
    # Calcula datas para filtros rápidos
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    with get_db() as conn:
        if MODULOS_DISPONIVEIS:
            try:
                from modules.relatorios_unificado import obter_relatorio_completo
                relatorio = obter_relatorio_completo(conn, start_date, end_date, usar_cache=False)
                
                # Prepara dados para o template
                stats = relatorio["stats"]
                setores_top = relatorio["setores"][:5]
                usuarios_top = relatorio["usuarios"][:5]
                impressoras_top = relatorio["impressoras"][:5]
                
                setores_labels = [s["sector"] for s in setores_top]
                setores_values = [s["total_impressos"] for s in setores_top]
                
                usuarios_labels = [u["user"] for u in usuarios_top]
                usuarios_values = [u["total_impressos"] for u in usuarios_top]
                
                impressoras_labels = [i["printer_name"] for i in impressoras_top]
                impressoras_values = [i["total_impressos"] for i in impressoras_top]
                
                dias_labels = relatorio["tendencia"]["labels"][-7:]  # Últimos 7 dias
                dias_values = relatorio["tendencia"]["values"][-7:]
                
                color_modes = [c["color_mode"] for c in relatorio["cor"]]
                color_pages = [c["total_paginas"] for c in relatorio["cor"]]
                
                # Dados detalhados de relatórios
                color_report = relatorio["cor"]
                paper_report = relatorio["papel"]
                duplex_report = [
                    {
                        "duplex_mode": "Sim",
                        "total_impressos": relatorio["duplex"]["duplex"]["impressoes"],
                        "total_paginas": relatorio["duplex"]["duplex"]["paginas"]
                    },
                    {
                        "duplex_mode": "Não",
                        "total_impressos": relatorio["duplex"]["simplex"]["impressoes"],
                        "total_paginas": relatorio["duplex"]["simplex"]["paginas"]
                    }
                ]
                
                # Calcula métricas de eficiência
                total_duplex = relatorio["duplex"]["duplex"]["paginas"]
                total_simplex = relatorio["duplex"]["simplex"]["paginas"]
                total_paginas_duplex = total_duplex + total_simplex
                taxa_duplex = (total_duplex / total_paginas_duplex * 100) if total_paginas_duplex > 0 else 0
                
                # Calcula economia de papel (estimativa: duplex economiza ~50% das folhas)
                economia_duplex = total_duplex // 2 if total_duplex > 0 else 0
                
                # Calcula comparação com período anterior
                if start_date and end_date:
                    try:
                        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
                        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
                        periodo_dias = (end_dt - start_dt).days + 1
                        periodo_anterior_start = start_dt - timedelta(days=periodo_dias)
                        periodo_anterior_end = start_dt - timedelta(days=1)
                        
                        relatorio_anterior = obter_relatorio_completo(
                            conn, 
                            periodo_anterior_start.isoformat(), 
                            periodo_anterior_end.isoformat(), 
                            usar_cache=False
                        )
                        stats_anterior = relatorio_anterior["stats"]
                        
                        # Calcula variações percentuais
                        total_impressos_ant = stats_anterior.get("total_impressos", 0)
                        total_paginas_ant = stats_anterior.get("total_paginas", 0)
                        total_usuarios_ant = stats_anterior.get("total_usuarios", 0)
                        
                        variacao_impressos = ((stats.get("total_impressos", 0) - total_impressos_ant) / total_impressos_ant * 100) if total_impressos_ant > 0 else 0
                        variacao_paginas = ((stats.get("total_paginas", 0) - total_paginas_ant) / total_paginas_ant * 100) if total_paginas_ant > 0 else 0
                        variacao_usuarios = ((stats.get("total_usuarios", 0) - total_usuarios_ant) / total_usuarios_ant * 100) if total_usuarios_ant > 0 else 0
                        
                        periodo_anterior_impressos = total_impressos_ant
                    except:
                        variacao_impressos = None
                        variacao_paginas = None
                        variacao_usuarios = None
                        periodo_anterior_impressos = None
                else:
                    variacao_impressos = None
                    variacao_paginas = None
                    variacao_usuarios = None
                    periodo_anterior_impressos = None
                
                # Média por usuário
                media_por_usuario = (stats.get("total_paginas", 0) / stats.get("total_usuarios", 1)) if stats.get("total_usuarios", 0) > 0 else 0
                
            except ImportError:
                # Fallback se módulo não disponível
                stats = obter_estatisticas_gerais_fallback(conn, start_date, end_date)
                setores_labels, setores_values = [], []
                usuarios_labels, usuarios_values = [], []
                impressoras_labels, impressoras_values = [], []
                dias_labels, dias_values = [], []
                color_modes, color_pages = [], []
                color_report = []
                paper_report = []
                duplex_report = []
                taxa_duplex = None
                economia_duplex = None
                variacao_impressos = None
                variacao_paginas = None
                variacao_usuarios = None
                periodo_anterior_impressos = None
                media_por_usuario = None
        else:
            # Fallback se módulos não disponíveis
            stats = obter_estatisticas_gerais_fallback(conn, start_date, end_date)
            setores_labels, setores_values = [], []
            usuarios_labels, usuarios_values = [], []
            impressoras_labels, impressoras_values = [], []
            dias_labels, dias_values = [], []
            color_modes, color_pages = [], []
            color_report = []
            paper_report = []
            duplex_report = []
            taxa_duplex = None
            economia_duplex = None
            variacao_impressos = None
            variacao_paginas = None
            variacao_usuarios = None
            periodo_anterior_impressos = None
            media_por_usuario = None
    
    # Busca alertas de cor
    alerts = check_color_alerts()
    
    # Busca último evento para exibir no dashboard
    ultimo_evento = None
    with get_db() as conn:
        ultimo_evento_row = conn.execute(
            "SELECT date, user, printer_name, duplex FROM events ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        
        if ultimo_evento_row:
            duplex_evento = ultimo_evento_row[3] if len(ultimo_evento_row) > 3 else None
            duplex_ultimo = obter_duplex_da_impressora(conn, ultimo_evento_row[2], duplex_evento)
            ultimo_evento = {
                "date": ultimo_evento_row[0],
                "user": ultimo_evento_row[1],
                "printer": ultimo_evento_row[2],
                "duplex": duplex_ultimo
            }
    
    return render_template(
        "dashboard.html",
        total_impressos=stats.get("total_impressos", 0),
        total_paginas=stats.get("total_paginas", 0),
        total_usuarios=stats.get("total_usuarios", 0),
        total_setores=stats.get("total_setores", 0),
        setores_labels=setores_labels,
        setores_values=setores_values,
        usuarios_labels=usuarios_labels,
        usuarios_values=usuarios_values,
        dias_labels=dias_labels,
        dias_values=dias_values,
        impressoras_labels=impressoras_labels,
        impressoras_values=impressoras_values,
        color_modes=color_modes,
        color_pages=color_pages,
        color_report=color_report,
        paper_report=paper_report,
        duplex_report=duplex_report,
        alerts=alerts,
        ultimo_evento=ultimo_evento,
        start_date=start_date,
        end_date=end_date,
        today=today,
        week_ago=week_ago,
        month_ago=month_ago,
        taxa_duplex=taxa_duplex,
        economia_duplex=economia_duplex,
        variacao_impressos=variacao_impressos,
        variacao_paginas=variacao_paginas,
        variacao_usuarios=variacao_usuarios,
        periodo_anterior_impressos=periodo_anterior_impressos,
        media_por_usuario=media_por_usuario,
    )


# Rotas removidas: sistema de comodatos removido


def contar_jobs_unicos(conn: sqlite3.Connection, where_clause: str = "WHERE 1=1", params: list = None) -> int:
    """
    Conta jobs únicos (não eventos individuais) na tabela events.
    Agrupa por job_id quando disponível, ou por combinação de campos.
    
    Args:
        conn: Conexão com banco de dados
        where_clause: Cláusula WHERE (ex: "WHERE date(date) = date('now')")
        params: Parâmetros para a query
    
    Returns:
        Número de jobs únicos
    """
    if params is None:
        params = []
    
    # Verifica se job_id existe na tabela
    existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(events)").fetchall()]
    has_job_id = 'job_id' in existing_columns
    
    if has_job_id:
        # Agrupa por job_id quando disponível (mais preciso)
        total = conn.execute(
            f"""SELECT COUNT(DISTINCT CASE 
                WHEN job_id IS NOT NULL AND job_id != '' THEN 
                    job_id || '|' || COALESCE(printer_name, '') || '|' || date
                ELSE 
                    user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
            END) FROM events {where_clause}""",
            params
        ).fetchone()[0]
    else:
        # Fallback: agrupa por combinação de campos quando job_id não existe
        total = conn.execute(
            f"""SELECT COUNT(DISTINCT user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date) 
            FROM events {where_clause}""",
            params
        ).fetchone()[0]
    
    return total


def obter_estatisticas_gerais_fallback(conn: sqlite3.Connection,
                                     start_date: Optional[str] = None,
                                     end_date: Optional[str] = None) -> Dict:
    """Fallback caso módulo não esteja disponível"""
    where_clause = "WHERE 1=1"
    params = []
    
    if start_date:
        where_clause += " AND date(date) >= date(?)"
        params.append(start_date)
    if end_date:
        where_clause += " AND date(date) <= date(?)"
        params.append(end_date)
    
    # Conta jobs únicos usando função auxiliar
    total_impressos = contar_jobs_unicos(conn, where_clause, params)
    
    # Verifica se job_id existe na tabela
    existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(events)").fetchall()]
    has_job_id = 'job_id' in existing_columns
    
    # Calcula páginas físicas agrupando por job primeiro (evita duplicação)
    # Cada evento do mesmo job tem o total de páginas, então usamos MAX
    if has_job_id:
        rows = conn.execute(
            f"""SELECT 
                MAX(pages_printed) as pages,
                MAX(duplex) as duplex,
                MAX(COALESCE(copies, 1)) as copies,
                MAX(printer_name) as printer_name
            FROM events {where_clause}
            GROUP BY CASE 
                WHEN job_id IS NOT NULL AND job_id != '' THEN 
                    job_id || '|' || COALESCE(printer_name, '') || '|' || date
                ELSE 
                    user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
            END""",
            params
        ).fetchall()
    else:
        rows = conn.execute(
            f"""SELECT 
                MAX(pages_printed) as pages,
                MAX(COALESCE(duplex, 0)) as duplex,
                MAX(COALESCE(copies, 1)) as copies,
                MAX(printer_name) as printer_name
            FROM events {where_clause}
            GROUP BY user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date""",
            params
        ).fetchall()
    
    total_paginas = 0
    for row in rows:
        pages = row[0] or 0
        duplex_evento = row[1] if len(row) > 1 else None
        copies = row[2] if len(row) > 2 else 1
        printer_name = row[3] if len(row) > 3 else None
        
        # Obtém duplex baseado no tipo da impressora cadastrada
        duplex = obter_duplex_da_impressora(conn, printer_name, duplex_evento)
        
        total_paginas += calcular_folhas_fisicas(pages, duplex, copies)
    
    total_usuarios = conn.execute(
        f"SELECT COUNT(DISTINCT user) FROM events {where_clause}",
        params
    ).fetchone()[0]
    
    total_setores = conn.execute(
        "SELECT COUNT(DISTINCT sector) FROM users WHERE sector IS NOT NULL"
    ).fetchone()[0]
    
    return {
        "total_impressos": total_impressos,
        "total_paginas": total_paginas,
        "total_usuarios": total_usuarios,
        "total_setores": total_setores
    }


@app.route("/setores")
@login_required
def painel_setores():
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    filtro_setor = request.args.get("filtro_setor", "")

    # Impressão = Folha lógica (job) | Páginas = Folha física (papel)
    # Busca todos os eventos para calcular corretamente
    query = """SELECT COALESCE(u.sector, 'Sem Setor') as sector,
                      e.date,
                      e.pages_printed,
                      e.duplex,
                      e.color_mode
               FROM events e
               LEFT JOIN users u ON e.user = u.user
               WHERE 1=1"""
    params = []
    if start_date:
        query += " AND date(e.date) >= date(?)"
        params.append(start_date)
    if end_date:
        query += " AND date(e.date) <= date(?)"
        params.append(end_date)
    if filtro_setor:
        query += " AND u.sector LIKE ?"
        params.append(f"%{filtro_setor}%")

    query += " ORDER BY u.sector, e.date"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()

    # Agrupa por setor e calcula corretamente
    setores_agrupados = {}
    for row in rows:
        setor = row["sector"] or "Sem Setor"
        data_evento = row["date"]
        pages = row["pages_printed"] or 0
        duplex = row["duplex"] if "duplex" in row.keys() else None
        color_mode = row["color_mode"] if "color_mode" in row.keys() else None
        
        # Calcula folhas físicas
        copies_val = row.get("copies", 1) if isinstance(row, dict) else (row[5] if len(row) > 5 else 1)
        folhas_fisicas = calcular_folhas_fisicas(pages, duplex, copies_val)
        
        # Sistema de custos removido

        if setor not in setores_agrupados:
            setores_agrupados[setor] = {
                "total_paginas": 0,
                "total_impressos": 0,
            }

        setores_agrupados[setor]["total_paginas"] += folhas_fisicas
        setores_agrupados[setor]["total_impressos"] += 1

    # Ordena setores por valor estimado (maior primeiro)
    setores_final = []
    for setor, dados in setores_agrupados.items():
        setores_final.append({
            "sector": setor,
            "total_paginas": dados["total_paginas"],
            "total_impressos": dados["total_impressos"],
        })
    
    # Ordena por total de páginas (decrescente)
    setores_final.sort(key=lambda x: x['total_paginas'], reverse=True)

    # Consulta usuários por setor (aplica os mesmos filtros)
    usuarios_dict = {}
    with get_db() as conn:
        usuarios_query = """
            SELECT COALESCE(u.sector, 'Sem Setor') as sector, e.user
            FROM events e
            LEFT JOIN users u ON e.user = u.user
            WHERE 1=1
        """
        usuarios_params = []
        
        if start_date:
            usuarios_query += " AND date(e.date) >= date(?)"
            usuarios_params.append(start_date)
        if end_date:
            usuarios_query += " AND date(e.date) <= date(?)"
            usuarios_params.append(end_date)
        if filtro_setor:
            usuarios_query += " AND u.sector LIKE ?"
            usuarios_params.append(f"%{filtro_setor}%")
        
        usuarios_query += " GROUP BY sector, e.user ORDER BY sector, e.user"
        
        usuarios_por_setor = conn.execute(usuarios_query, usuarios_params).fetchall()

        for row in usuarios_por_setor:
            setor = row["sector"] or "Sem Setor"
            user = row["user"]
            if setor not in usuarios_dict:
                usuarios_dict[setor] = []
            if user not in usuarios_dict[setor]:  # Evita duplicatas
                usuarios_dict[setor].append(user)
        
        # Ordena usuários dentro de cada setor
        for setor in usuarios_dict:
            usuarios_dict[setor].sort()

    return render_template(
        "setores.html",
        setores=setores_final,
        usuarios_por_setor=usuarios_dict,
        start_date=start_date,
        end_date=end_date,
        filtro_setor=filtro_setor,
    )

@app.route("/setores/export")
@login_required
def export_setores_excel():
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    filtro_setor = request.args.get("filtro_setor", "")

    # Constrói WHERE clause
    where_clause = "WHERE 1=1"
    params = []
    if start_date:
        where_clause += " AND date(e.date) >= date(?)"
        params.append(start_date)
    if end_date:
        where_clause += " AND date(e.date) <= date(?)"
        params.append(end_date)
    if filtro_setor:
        where_clause += " AND u.sector LIKE ?"
        params.append(f"%{filtro_setor}%")

    with get_db() as conn:
        # Verifica se job_id existe
        existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(events)").fetchall()]
        has_job_id = 'job_id' in existing_columns
        
        # Busca eventos agrupados por job primeiro
        if has_job_id:
            query = f"""
                SELECT 
                    COALESCE(u.sector, 'Sem Setor') as sector,
                    MAX(e.pages_printed) as pages,
                    MAX(COALESCE(e.duplex, 0)) as duplex,
                    MAX(COALESCE(e.copies, 1)) as copies,
                    MAX(e.date) as date
                FROM events e
                LEFT JOIN users u ON e.user = u.user
                {where_clause}
                GROUP BY CASE 
                    WHEN e.job_id IS NOT NULL AND e.job_id != '' THEN 
                        e.job_id || '|' || COALESCE(e.printer_name, '') || '|' || e.date
                    ELSE 
                        e.user || '|' || e.machine || '|' || COALESCE(e.document, '') || '|' || COALESCE(e.printer_name, '') || '|' || e.date
                END, COALESCE(u.sector, 'Sem Setor')
            """
        else:
            query = f"""
                SELECT 
                    COALESCE(u.sector, 'Sem Setor') as sector,
                    MAX(e.pages_printed) as pages,
                    MAX(COALESCE(e.duplex, 0)) as duplex,
                    MAX(COALESCE(e.copies, 1)) as copies,
                    MAX(e.date) as date
                FROM events e
                LEFT JOIN users u ON e.user = u.user
                {where_clause}
                GROUP BY e.user || '|' || e.machine || '|' || COALESCE(e.document, '') || '|' || COALESCE(e.printer_name, '') || '|' || e.date, COALESCE(u.sector, 'Sem Setor')
            """
        
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()
        
        # Agrupa por setor e calcula folhas físicas
        setores_dict = {}
        for row in rows:
            sector = row["sector"]
            pages = row["pages"] or 0
            duplex = row["duplex"]
            copies = row["copies"] or 1
            date_val = row["date"]
            
            if sector not in setores_dict:
                setores_dict[sector] = {
                    "total_impressos": 0,
                    "total_paginas": 0
                }
            
            folhas_fisicas = calcular_folhas_fisicas(pages, duplex, copies)
            setores_dict[sector]["total_impressos"] += 1
            setores_dict[sector]["total_paginas"] += folhas_fisicas
        
        # Prepara dados para Excel (sem custos - sistema removido)
        excel_data = []
        for sector, dados in sorted(setores_dict.items()):
            excel_data.append({
                'Setor': sector,
                'Total Impressões': dados["total_impressos"],
                'Total Páginas': dados["total_paginas"]
            })
        
        df = pd.DataFrame(excel_data)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Setores")
    output.seek(0)

    return send_file(
        output,
        download_name="setores.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/api/impressao-tendencia")
@login_required
def api_impressao_tendencia():
    """API para tendência de impressões - conta jobs únicos por dia"""
    with get_db() as conn:
        # Verifica se job_id existe na tabela
        existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(events)").fetchall()]
        has_job_id = 'job_id' in existing_columns
        
        if has_job_id:
            # Conta jobs únicos agrupados por dia
            data = conn.execute(
                """
                SELECT 
                    date(date) as dia,
                    COUNT(DISTINCT CASE 
                        WHEN job_id IS NOT NULL AND job_id != '' THEN 
                            job_id || '|' || COALESCE(printer_name, '') || '|' || date
                        ELSE 
                            user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
                    END) as total_impressos
                FROM events
                WHERE date >= date('now', '-30 days')
                GROUP BY dia
                ORDER BY dia
            """
            ).fetchall()
        else:
            # Fallback: agrupa por combinação de campos
            data = conn.execute(
                """
                SELECT 
                    date(date) as dia,
                    COUNT(DISTINCT user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date) as total_impressos
                FROM events
                WHERE date >= date('now', '-30 days')
                GROUP BY dia
                ORDER BY dia
            """
            ).fetchall()

    resultados = []
    prev = None
    for row in data:
        dia, total = row
        crescimento = None
        if prev is not None and prev[1] > 0:
            crescimento = round((total - prev[1]) / prev[1] * 100, 2)
        resultados.append(
            {"dia": dia, "total_impressos": total, "crescimento_pct": crescimento}
        )
        prev = row

    return jsonify(resultados)


@app.route("/api/impressao-dia")
@login_required
def api_impressao_dia():
    """API para impressões do dia - conta jobs únicos por usuário"""
    hoje = datetime.now().date()
    with get_db() as conn:
        # Verifica se job_id existe na tabela
        existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(events)").fetchall()]
        has_job_id = 'job_id' in existing_columns
        
        if has_job_id:
            # Conta jobs únicos agrupados por usuário
            data = conn.execute(
                """
                SELECT 
                    user,
                    COUNT(DISTINCT CASE 
                        WHEN job_id IS NOT NULL AND job_id != '' THEN 
                            job_id || '|' || COALESCE(printer_name, '') || '|' || date
                        ELSE 
                            user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
                    END) as total_impressos
                FROM events
                WHERE date(date) = ?
                GROUP BY user
                ORDER BY total_impressos DESC
                LIMIT 10
            """,
                (hoje,),
            ).fetchall()
        else:
            # Fallback: agrupa por combinação de campos
            data = conn.execute(
                """
                SELECT 
                    user,
                    COUNT(DISTINCT user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date) as total_impressos
                FROM events
                WHERE date(date) = ?
                GROUP BY user
                ORDER BY total_impressos DESC
                LIMIT 10
            """,
                (hoje,),
            ).fetchall()

    resultados = [{"user": row[0], "total_impressos": row[1]} for row in data]
    return jsonify(resultados)


@app.route("/impressoras")
@login_required
def impressoras():
    """Página de relatórios por impressora"""
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    filtro_impressora = request.args.get("filtro_impressora", "")

    # Impressão = Folha lógica (job) | Páginas = Folha física (papel)
    # Verifica se a coluna copies existe antes de incluí-la na query
    with get_db() as conn_check:
        existing_columns = [col[1] for col in conn_check.execute("PRAGMA table_info(events)").fetchall()]
        has_copies = 'copies' in existing_columns
    
    if has_copies:
        query = """SELECT 
                          COALESCE(printer_name, 'Sem Nome') as printer_name,
                          pages_printed,
                          duplex,
                          color_mode,
                          COALESCE(copies, 1) as copies
                   FROM events
                   WHERE 1=1"""
    else:
        query = """SELECT 
                          COALESCE(printer_name, 'Sem Nome') as printer_name,
                          pages_printed,
                          duplex,
                          color_mode,
                          1 as copies
                   FROM events
                   WHERE 1=1"""
    params = []
    if start_date:
        query += " AND date(date) >= date(?)"
        params.append(start_date)
    if end_date:
        query += " AND date(date) <= date(?)"
        params.append(end_date)
    if filtro_impressora:
        query += " AND printer_name LIKE ?"
        params.append(f"%{filtro_impressora}%")
    
    query += " ORDER BY printer_name"

    with get_db() as conn:
        conn.row_factory = sqlite3.Row  # Garante que retorna Row objects
        rows = conn.execute(query, params).fetchall()
        
        # Busca setores vinculados às impressoras
        printers_sectors = {}
        sectors_query = conn.execute("SELECT printer_name, sector FROM printers").fetchall()
        for row in sectors_query:
            if isinstance(row, sqlite3.Row):
                printers_sectors[row["printer_name"]] = row["sector"]
            else:
                printers_sectors[row[0]] = row[1] if len(row) > 1 else ""
        
        # Busca lista de setores disponíveis
        setores_disponiveis = [row[0] for row in conn.execute(
            "SELECT DISTINCT sector FROM users WHERE sector IS NOT NULL AND sector != '' ORDER BY sector"
        ).fetchall()]
        
        # OTIMIZAÇÃO: Cache tipos de impressoras para evitar queries N+1
        printer_types_cache = {}
        printer_names_in_rows = set()
        for row in rows:
            if isinstance(row, sqlite3.Row):
                printer_name = row["printer_name"]
            else:
                printer_name = row[0] if len(row) > 0 else None
            if printer_name:
                printer_names_in_rows.add(printer_name)
        
        if printer_names_in_rows:
            printer_types = conn.execute(
                "SELECT printer_name, tipo FROM printers WHERE printer_name IN ({})".format(
                    ','.join(['?'] * len(printer_names_in_rows))
                ),
                list(printer_names_in_rows)
            ).fetchall()
            for p in printer_types:
                if isinstance(p, sqlite3.Row):
                    printer_types_cache[p["printer_name"]] = p["tipo"]
                else:
                    if len(p) >= 2 and p[0] and p[1]:
                        printer_types_cache[p[0]] = p[1]

    # Agrupa e calcula folhas físicas por impressora
    impressoras_dict = {}
    for row in rows:
        # Extrai dados do row (pode ser Row object ou tupla)
        try:
            if isinstance(row, sqlite3.Row):
                printer_name = row["printer_name"]
                pages = row["pages_printed"] or 0
                duplex_evento = row["duplex"] if "duplex" in row.keys() else None
                color_mode = row["color_mode"] if "color_mode" in row.keys() else None
                copies_val = row["copies"] if "copies" in row.keys() else 1
            else:
                # Fallback para tupla
                printer_name = row[0] if len(row) > 0 else None
                pages = row[1] if len(row) > 1 else 0
                duplex_evento = row[2] if len(row) > 2 else None
                color_mode = row[3] if len(row) > 3 else None
                copies_val = row[4] if len(row) > 4 else 1
        except (KeyError, IndexError, TypeError, AttributeError) as e:
            logger.error(f"Erro ao extrair dados do row: {e}, row type: {type(row)}")
            continue
        
        if not printer_name:
            continue
        
        if printer_name not in impressoras_dict:
            impressoras_dict[printer_name] = {
                "total_impressos": 0,
                "total_paginas": 0,
                "paginas_color": 0,
                "paginas_bw": 0,
                "impressoes_color": 0,
                "impressoes_bw": 0,
                "impressoes_duplex": 0,
                "impressoes_simplex": 0,
            }
        
        # Obtém duplex baseado no tipo da impressora cadastrada (usando cache)
        if printer_name and printer_name in printer_types_cache:
            tipo_impressora = printer_types_cache[printer_name].lower()
            duplex = 1 if tipo_impressora == 'duplex' else 0
        else:
            # Fallback para valor do evento
            duplex = duplex_evento if duplex_evento is not None else 0
        
        # Calcula folhas físicas
        try:
            folhas_fisicas = calcular_folhas_fisicas(pages, duplex, copies_val)
        except Exception as e:
            logger.error(f"Erro ao calcular folhas físicas: {e}, pages={pages}, duplex={duplex}, copies={copies_val}")
            folhas_fisicas = pages or 0  # Fallback simples
        
        impressoras_dict[printer_name]["total_impressos"] += 1
        impressoras_dict[printer_name]["total_paginas"] += folhas_fisicas
        
        if color_mode == 'Color':
            impressoras_dict[printer_name]["paginas_color"] += folhas_fisicas
            impressoras_dict[printer_name]["impressoes_color"] += 1
        elif color_mode == 'Black & White':
            impressoras_dict[printer_name]["paginas_bw"] += folhas_fisicas
            impressoras_dict[printer_name]["impressoes_bw"] += 1
        
        if duplex == 1:
            impressoras_dict[printer_name]["impressoes_duplex"] += 1
        elif duplex == 0:
            impressoras_dict[printer_name]["impressoes_simplex"] += 1

    # Prepara lista de impressoras (sem cálculo de custo - sistema removido)
    impressoras_list = []
    for printer_name, dados in impressoras_dict.items():
        sector_vinculado = printers_sectors.get(printer_name, "")
        
        impressoras_list.append({
            "printer_name": printer_name,
            "total_impressos": dados["total_impressos"],
            "total_paginas": dados["total_paginas"],
            "paginas_color": dados["paginas_color"],
            "paginas_bw": dados["paginas_bw"],
            "impressoes_color": dados["impressoes_color"],
            "impressoes_bw": dados["impressoes_bw"],
            "impressoes_duplex": dados["impressoes_duplex"],
            "impressoes_simplex": dados["impressoes_simplex"],
            "sector": sector_vinculado
        })
    
    # Ordena por total de impressões
    impressoras_list.sort(key=lambda x: x['total_impressos'], reverse=True)

    return render_template(
        "impressoras.html",
        impressoras=impressoras_list,
        setores_disponiveis=setores_disponiveis,
        start_date=start_date,
        end_date=end_date,
        filtro_impressora=filtro_impressora,
    )


@app.route("/impressoras/update_sector", methods=["POST"])
@csrf_exempt_if_enabled
@login_required
def update_printer_sector():
    """Atualiza o setor vinculado a uma impressora"""
    if not request.is_json:
        return jsonify({"status": "error", "message": "Content-Type deve ser application/json"}), 400
    
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "JSON inválido ou vazio"}), 400
    
    printer_name = data.get("printer_name")
    sector = data.get("sector", "").strip()
    
    if not printer_name:
        return jsonify({
            "status": "error", 
            "message": "Nome da impressora é obrigatório",
            "expected_format": {
                "printer_name": "string (obrigatório)",
                "sector": "string (opcional)"
            }
        }), 400
    
    try:
        with get_db() as conn:
            if sector:
                # Verifica se impressora já existe
                cursor = conn.execute(
                    "SELECT tipo FROM printers WHERE printer_name = ?",
                    (printer_name,)
                )
                existing_row = cursor.fetchone()
                existing = existing_row is not None
                tipo_existente = existing_row[0] if existing_row else None
                
                if existing:
                    # Atualiza apenas o setor, preservando o tipo
                    conn.execute(
                        "UPDATE printers SET sector = ? WHERE printer_name = ?",
                        (sector, printer_name)
                    )
                    message = f"Setor '{sector}' vinculado à impressora '{printer_name}'"
                else:
                    # Insere nova impressora com tipo padrão 'simplex'
                    conn.execute(
                        "INSERT INTO printers (printer_name, sector, tipo) VALUES (?, ?, ?)",
                        (printer_name, sector, 'simplex')
                    )
                    # Recalcula eventos da nova impressora
                    eventos_atualizados = recalcular_eventos_impressora(conn, printer_name, 'simplex')
                    if eventos_atualizados > 0:
                        message = f"Setor '{sector}' vinculado à impressora '{printer_name}'. {eventos_atualizados} eventos recalculados."
                    else:
                        message = f"Setor '{sector}' vinculado à impressora '{printer_name}'"
            else:
                # Remove o vínculo se setor estiver vazio
                # Mas preserva o tipo se a impressora existir
                cursor = conn.execute(
                    "SELECT tipo FROM printers WHERE printer_name = ?",
                    (printer_name,)
                )
                existing_row = cursor.fetchone()
                
                if existing_row:
                    # Atualiza setor para NULL, mas mantém tipo
                    conn.execute(
                        "UPDATE printers SET sector = NULL WHERE printer_name = ?",
                        (printer_name,)
                    )
                    message = f"Vínculo de setor removido da impressora '{printer_name}'"
                else:
                    # Se não existe, não faz nada
                    message = f"Impressora '{printer_name}' não encontrada"
            
            conn.commit()
        
        return jsonify({"status": "success", "message": message}), 200
    except Exception as e:
        logger.error(f"Erro ao atualizar setor da impressora: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/impressoras/export")
@login_required
def export_impressoras_excel():
    """Exporta relatório de impressoras para Excel"""
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    filtro_impressora = request.args.get("filtro_impressora", "")

    # Constrói WHERE clause
    where_clause = "WHERE 1=1"
    params = []
    if start_date:
        where_clause += " AND date(date) >= date(?)"
        params.append(start_date)
    if end_date:
        where_clause += " AND date(date) <= date(?)"
        params.append(end_date)
    if filtro_impressora:
        where_clause += " AND printer_name LIKE ?"
        params.append(f"%{filtro_impressora}%")
    
    # Verifica se job_id existe
    with get_db() as conn:
        existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(events)").fetchall()]
        has_job_id = 'job_id' in existing_columns
        
        # Busca eventos agrupados por job primeiro
        if has_job_id:
            query = f"""
                SELECT 
                    COALESCE(printer_name, 'Sem Nome') as printer_name,
                    MAX(pages_printed) as pages,
                    MAX(COALESCE(duplex, 0)) as duplex,
                    MAX(COALESCE(copies, 1)) as copies,
                    MAX(color_mode) as color_mode
                FROM events
                {where_clause} AND printer_name IS NOT NULL
                GROUP BY CASE 
                    WHEN job_id IS NOT NULL AND job_id != '' THEN 
                        job_id || '|' || COALESCE(printer_name, '') || '|' || date
                    ELSE 
                        user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
                END, printer_name
            """
        else:
            query = f"""
                SELECT 
                    COALESCE(printer_name, 'Sem Nome') as printer_name,
                    MAX(pages_printed) as pages,
                    MAX(COALESCE(duplex, 0)) as duplex,
                    MAX(COALESCE(copies, 1)) as copies,
                    MAX(color_mode) as color_mode
                FROM events
                {where_clause} AND printer_name IS NOT NULL
                GROUP BY user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date, printer_name
            """
        
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()
        
        # Agrupa por impressora e calcula folhas físicas
        impressoras_dict = {}
        for row in rows:
            printer_name = row["printer_name"]
            pages = row["pages"] or 0
            duplex = row["duplex"]
            copies = row["copies"] or 1
            color_mode = row["color_mode"]
            
            if printer_name not in impressoras_dict:
                impressoras_dict[printer_name] = {
                    "total_impressos": 0,
                    "total_paginas": 0,
                    "paginas_color": 0,
                    "paginas_bw": 0,
                    "impressoes_color": 0,
                    "impressoes_bw": 0
                }
            
            folhas_fisicas = calcular_folhas_fisicas(pages, duplex, copies)
            impressoras_dict[printer_name]["total_impressos"] += 1
            impressoras_dict[printer_name]["total_paginas"] += folhas_fisicas
            
            if color_mode == 'Color':
                impressoras_dict[printer_name]["paginas_color"] += folhas_fisicas
                impressoras_dict[printer_name]["impressoes_color"] += 1
            elif color_mode == 'Black & White':
                impressoras_dict[printer_name]["paginas_bw"] += folhas_fisicas
                impressoras_dict[printer_name]["impressoes_bw"] += 1
        
        # Prepara dados para Excel (sem cálculo de custo - sistema removido)
        excel_data = []
        for printer_name, dados in sorted(impressoras_dict.items(), key=lambda x: x[1]["total_impressos"], reverse=True):
            excel_data.append({
                'Impressora': printer_name,
                'Total Impressões': dados["total_impressos"],
                'Total Páginas': dados["total_paginas"],
                'Páginas Color': dados["paginas_color"],
                'Páginas P&B': dados["paginas_bw"],
                'Impressões Color': dados["impressoes_color"],
                'Impressões P&B': dados["impressoes_bw"]
            })
        
        df = pd.DataFrame(excel_data)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Impressoras")
    output.seek(0)

    return send_file(
        output,
        download_name="impressoras.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/dashboard/export/pdf")
@login_required
def export_dashboard_pdf():
    """Exporta dashboard em PDF - Relatório Profissional Hospitalar"""
    if not PDF_EXPORT_AVAILABLE:
        flash("Exportação PDF não disponível. Instale reportlab.", "warning")
        return redirect(url_for('dashboard'))
    
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        hospital_nome = request.args.get("hospital_nome", "Hospital")
        
        # Gera PDF profissional usando a nova função
        with get_db() as conn:
            pdf_buffer = pdf_export.gerar_relatorio_hospitalar_completo(
                conn=conn,
                hospital_nome=hospital_nome,
                start_date=start_date,
                end_date=end_date,
                incluir_graficos=False
            )
        
        # Nome do arquivo
        filename = f"relatorio_impressoes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return send_file(
            pdf_buffer,
            download_name=filename,
            as_attachment=True,
            mimetype="application/pdf"
        )
    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {e}", exc_info=True)
        flash(f"Erro ao gerar PDF: {str(e)}", "danger")
        return redirect(url_for('dashboard'))


@app.route("/dashboard/export")
@login_required
def export_dashboard_excel():
    """Exporta dados do dashboard para Excel - Relatório Profissional Hospitalar"""
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    hospital_nome = request.args.get("hospital_nome", "Hospital")
    
    try:
        # Usa a nova função de exportação profissional
        with get_db() as conn:
            if NOVOS_MODULOS_DISPONIVEIS:
                try:
                    output = exportacao_avancada.exportar_relatorio_excel_hospitalar(
                        conn=conn,
                        hospital_nome=hospital_nome,
                        start_date=start_date if start_date else None,
                        end_date=end_date if end_date else None
                    )
                except Exception as e:
                    logger.error(f"Erro ao gerar Excel profissional: {e}")
                    # Fallback para método antigo
                    output = exportar_dashboard_excel_fallback(conn, start_date, end_date)
            else:
                output = exportar_dashboard_excel_fallback(conn, start_date, end_date)
        
        filename = f"relatorio_impressoes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return send_file(
            output,
            download_name=filename,
            as_attachment=True,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        logger.error(f"Erro ao exportar Excel: {e}", exc_info=True)
        flash(f"Erro ao exportar Excel: {str(e)}", "danger")
        return redirect(url_for('dashboard'))


def exportar_dashboard_excel_fallback(conn, start_date: str = "", end_date: str = ""):
    """Método fallback para exportação Excel (compatibilidade)"""
    params = []
    where_clause = ""
    if start_date:
        where_clause += " AND date(date) >= date(?)"
        params.append(start_date)
    if end_date:
        where_clause += " AND date(date) <= date(?)"
        params.append(end_date)
    
    params_tuple = tuple(params) if params else ()
    
    # Verifica se job_id existe
    existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(events)").fetchall()]
    has_job_id = 'job_id' in existing_columns
    
    # Busca eventos agrupados por job primeiro
    if has_job_id:
        query_jobs = f"""
            SELECT 
                MAX(color_mode) as color_mode,
                MAX(paper_size) as paper_size,
                MAX(COALESCE(duplex, 0)) as duplex,
                MAX(pages_printed) as pages,
                MAX(COALESCE(copies, 1)) as copies
            FROM events
            WHERE 1=1 {where_clause}
            GROUP BY CASE 
                WHEN job_id IS NOT NULL AND job_id != '' THEN 
                    job_id || '|' || COALESCE(printer_name, '') || '|' || date
                ELSE 
                    user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
            END
        """
    else:
        query_jobs = f"""
            SELECT 
                MAX(color_mode) as color_mode,
                MAX(paper_size) as paper_size,
                MAX(COALESCE(duplex, 0)) as duplex,
                MAX(pages_printed) as pages,
                MAX(COALESCE(copies, 1)) as copies
            FROM events
            WHERE 1=1 {where_clause}
            GROUP BY user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
        """
    
    conn.row_factory = sqlite3.Row
    rows = conn.execute(query_jobs, params_tuple).fetchall()
    
    # Agrupa e calcula folhas físicas
    color_dict = {}
    paper_dict = {}
    duplex_dict = {"Sim": {"impressoes": 0, "paginas": 0}, "Não": {"impressoes": 0, "paginas": 0}, "Desconhecido": {"impressoes": 0, "paginas": 0}}
    
    for row in rows:
        color_mode = row["color_mode"]
        paper_size = row["paper_size"]
        duplex = row["duplex"]
        pages = row["pages"] or 0
        copies = row["copies"] or 1
        
        folhas_fisicas = calcular_folhas_fisicas(pages, duplex, copies)
        
        # Agrupa por cor
        if color_mode:
            if color_mode not in color_dict:
                color_dict[color_mode] = {"impressoes": 0, "paginas": 0}
            color_dict[color_mode]["impressoes"] += 1
            color_dict[color_mode]["paginas"] += folhas_fisicas
        
        # Agrupa por papel
        if paper_size:
            if paper_size not in paper_dict:
                paper_dict[paper_size] = {"impressoes": 0, "paginas": 0}
            paper_dict[paper_size]["impressoes"] += 1
            paper_dict[paper_size]["paginas"] += folhas_fisicas
        
        # Agrupa por duplex
        if duplex == 1:
            tipo = "Sim"
        elif duplex == 0:
            tipo = "Não"
        else:
            tipo = "Desconhecido"
        duplex_dict[tipo]["impressoes"] += 1
        duplex_dict[tipo]["paginas"] += folhas_fisicas
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Planilha 1: Modo de Cor
        color_data = [
            {"Modo de Cor": mode, "Total Impressões": data["impressoes"], "Total Páginas": data["paginas"]}
            for mode, data in sorted(color_dict.items(), key=lambda x: x[1]["paginas"], reverse=True)
        ]
        if color_data:
            color_df = pd.DataFrame(color_data)
            color_df.to_excel(writer, index=False, sheet_name="Modo de Cor")
        
        # Planilha 2: Tamanho de Papel
        paper_data = [
            {"Tamanho": size, "Total Impressões": data["impressoes"], "Total Páginas": data["paginas"]}
            for size, data in sorted(paper_dict.items(), key=lambda x: x[1]["paginas"], reverse=True)
        ]
        if paper_data:
            paper_df = pd.DataFrame(paper_data)
            paper_df.to_excel(writer, index=False, sheet_name="Tamanho de Papel")
        
        # Planilha 3: Duplex
        duplex_data = [
            {"Modo Duplex": tipo, "Total Impressões": data["impressoes"], "Total Páginas": data["paginas"]}
            for tipo, data in duplex_dict.items() if data["impressoes"] > 0
        ]
        if duplex_data:
            duplex_df = pd.DataFrame(duplex_data)
            duplex_df.to_excel(writer, index=False, sheet_name="Duplex")
    
    output.seek(0)
    return output


@app.route("/api/printer_type", methods=["GET"])
@csrf_exempt_if_enabled
def get_printer_type():
    """
    API para buscar o tipo da impressora (duplex/simplex)
    
    Query params:
        printer_name: Nome da impressora
    
    Returns:
        JSON com {"tipo": "duplex" ou "simplex"}
    """
    printer_name = request.args.get('printer_name', '').strip()
    
    if not printer_name:
        return jsonify({"status": "error", "message": "printer_name é obrigatório"}), 400
    
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT tipo FROM printers WHERE printer_name = ?",
                (printer_name,)
            ).fetchone()
            
            if row:
                tipo = row['tipo'] or 'simplex'
                return jsonify({"tipo": tipo})
            else:
                # Se não encontrou, retorna simplex como padrão
                return jsonify({"tipo": "simplex"})
    
    except Exception as e:
        logger.error(f"Erro ao buscar tipo da impressora: {e}")
        return jsonify({"status": "error", "message": str(e), "tipo": "simplex"}), 500


@app.route("/api/sheets_stats", methods=["GET"])
@login_required
def api_sheets_stats():
    """
    API para estatísticas de folhas físicas vs páginas lógicas.
    
    Retorna:
        - total_pages: Total de páginas lógicas impressas
        - total_sheets: Total de folhas físicas consumidas
        - sheets_saved: Folhas economizadas com duplex
        - savings_percent: Percentual de economia
        - by_printer: Estatísticas por impressora
    """
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    
    try:
        with sqlite3.connect(DB) as conn:
            conn.row_factory = sqlite3.Row
            
            # Query base
            where_clause = ""
            params = []
            if start_date:
                where_clause = "WHERE date >= ?"
                params.append(start_date)
            if end_date:
                if where_clause:
                    where_clause += " AND date <= ?"
                else:
                    where_clause = "WHERE date <= ?"
                params.append(end_date)
            
            # Estatísticas gerais
            query = f"""
                SELECT 
                    COALESCE(SUM(pages_printed), 0) as total_pages,
                    COALESCE(SUM(sheets_used), 0) as total_sheets,
                    COALESCE(SUM(CASE WHEN sheets_used IS NULL THEN pages_printed ELSE 0 END), 0) as sem_calculo,
                    COUNT(*) as total_eventos,
                    SUM(CASE WHEN duplex = 1 THEN 1 ELSE 0 END) as eventos_duplex,
                    SUM(CASE WHEN duplex = 0 OR duplex IS NULL THEN 1 ELSE 0 END) as eventos_simplex
                FROM events
                {where_clause}
            """
            stats = conn.execute(query, params).fetchone()
            
            total_pages = stats['total_pages'] or 0
            total_sheets = stats['total_sheets'] or 0
            
            # Se há eventos sem cálculo, recalcula na hora
            sem_calculo = stats['sem_calculo'] or 0
            if sem_calculo > 0:
                # Recalcula eventos sem sheets_used
                eventos_sem_calc = conn.execute(f"""
                    SELECT pages_printed, duplex, copies
                    FROM events
                    WHERE sheets_used IS NULL
                    {where_clause.replace('WHERE', 'AND') if where_clause else ''}
                """, params).fetchall()
                
                for ev in eventos_sem_calc:
                    pages = ev['pages_printed'] or 1
                    duplex = ev['duplex']
                    copies = ev['copies'] or 1
                    total_sheets += calcular_folhas_fisicas(pages, duplex, copies)
            
            sheets_saved = total_pages - total_sheets if total_pages > total_sheets else 0
            savings_percent = (sheets_saved / total_pages * 100) if total_pages > 0 else 0
            
            # Estatísticas por impressora
            query_printer = f"""
                SELECT 
                    printer_name,
                    COALESCE(SUM(pages_printed), 0) as pages,
                    COALESCE(SUM(sheets_used), 0) as sheets,
                    COUNT(*) as jobs,
                    MAX(duplex) as is_duplex
                FROM events
                {where_clause}
                GROUP BY printer_name
                ORDER BY sheets DESC
                LIMIT 10
            """
            by_printer = []
            for row in conn.execute(query_printer, params).fetchall():
                pages = row['pages'] or 0
                sheets = row['sheets'] or pages  # Fallback se sheets_used não calculado
                saved = pages - sheets if pages > sheets else 0
                by_printer.append({
                    "printer_name": row['printer_name'] or "Desconhecida",
                    "pages": pages,
                    "sheets": sheets,
                    "jobs": row['jobs'],
                    "is_duplex": row['is_duplex'] == 1,
                    "saved": saved
                })
            
            return jsonify({
                "status": "ok",
                "total_pages": total_pages,
                "total_sheets": total_sheets,
                "sheets_saved": sheets_saved,
                "savings_percent": round(savings_percent, 1),
                "total_jobs": stats['total_eventos'] or 0,
                "jobs_duplex": stats['eventos_duplex'] or 0,
                "jobs_simplex": stats['eventos_simplex'] or 0,
                "by_printer": by_printer,
                "period": {
                    "start": start_date,
                    "end": end_date
                }
            })
    
    except Exception as e:
        logger.error(f"Erro ao calcular estatísticas de folhas: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/print_events", methods=["POST"])
@csrf_exempt_if_enabled
def receive_events():
    """Recebe eventos de impressão dos agentes"""
    logger.info(f"Recebida requisição de {request.remote_addr}")
    
    if not request.is_json:
        logger.warning("Requisição sem Content-Type application/json")
        return jsonify({"status": "error", "message": "Content-Type deve ser application/json"}), 400
    
    try:
        data = request.json
        if not data or "events" not in data:
            return jsonify({
                "status": "error", 
                "message": "Formato inválido: esperado 'events' no JSON",
                "expected_format": {
                    "events": [
                        {
                            "date": "YYYY-MM-DD HH:MM:SS (obrigatório)",
                            "user": "string (obrigatório)",
                            "machine": "string (obrigatório)",
                            "pages": "integer (opcional, default: 1)",
                            "printer_name": "string (opcional)",
                            "color": "boolean (opcional)",
                            "duplex": "boolean (opcional)"
                        }
                    ]
                }
            }), 400
        
        events = data.get("events", [])
        if not isinstance(events, list):
            return jsonify({
                "status": "error", 
                "message": "Events deve ser uma lista",
                "expected_format": {
                    "events": "array de objetos"
                }
            }), 400
        
        inserted = 0
        skipped = 0
        errors = []
        
        with get_db() as conn:
            for idx, e in enumerate(events):
                try:
                    # Validação de campos obrigatórios
                    if not isinstance(e, dict):
                        errors.append(f"Evento {idx}: não é um objeto válido")
                        continue
                    
                    if "date" not in e or "user" not in e or "machine" not in e:
                        errors.append(f"Evento {idx}: campos obrigatórios faltando (date, user, machine)")
                        continue
                    
                    # Parse da data
                    try:
                        dt = datetime.strptime(e["date"], "%Y-%m-%d %H:%M:%S")
                        date_iso = dt.strftime("%Y-%m-%d")
                    except (ValueError, TypeError):
                        date_iso = e.get("date", datetime.now().strftime("%Y-%m-%d"))
                    
                    # Converte SID para nome de usuário (ou usa o valor original se já for nome)
                    user_name = sid_to_username(e["user"])
                    if not user_name:
                        # Se ainda assim não tiver nome, usa o valor original do evento
                        user_name = str(e["user"])[:100] if e.get("user") else "Desconhecido"
                        logger.warning(f"⚠️ Não foi possível obter nome de usuário do evento {idx}, usando '{user_name}'")
                    
                    # Validação de páginas
                    try:
                        pages = int(e.get("pages", 1))
                        if pages < 1:
                            pages = 1
                        elif pages > 10000:  # Limite razoável
                            pages = 10000
                    except (ValueError, TypeError):
                        pages = 1
                    
                    # Extrai cópias (se disponível)
                    copies = 1  # Default 1 cópia
                    if "copies" in e:
                        try:
                            copies = int(e.get("copies", 1))
                            if copies < 1:
                                copies = 1
                            elif copies > 100:  # Limite razoável
                                copies = 100
                        except (ValueError, TypeError):
                            copies = 1
                    
                    # IMPORTANTE: O Windows Event Log reporta páginas lógicas (faces)
                    # - Simplex: 1 página lógica = 1 folha física
                    # - Duplex: 2 páginas lógicas = 1 folha física
                    # O cálculo de folhas físicas será feito usando calcular_folhas_fisicas(pages, duplex, copies)
                    
                    machine = str(e["machine"])[:100]  # Limita tamanho
                    document = str(e.get("document", ""))[:255] if "document" in e else None
                    
                    # Extrai informações adicionais da impressora
                    printer_name = str(e.get("printer_name", ""))[:100] if e.get("printer_name") else None
                    printer_port = str(e.get("printer_port", ""))[:100] if e.get("printer_port") else None
                    color_mode = str(e.get("color_mode", ""))[:50] if e.get("color_mode") else None
                    paper_size = str(e.get("paper_size", ""))[:50] if e.get("paper_size") else None
                    
                    # IMPORTANTE: O campo duplex deve ser baseado no tipo da impressora cadastrada,
                    # não no campo duplex/tipo do evento. Busca o tipo da impressora no banco.
                    duplex = None
                    if printer_name:
                        cursor_tipo = conn.execute(
                            "SELECT tipo FROM printers WHERE printer_name = ?",
                            (printer_name,)
                        )
                        tipo_row = cursor_tipo.fetchone()
                        if tipo_row:
                            tipo_impressora = tipo_row[0]
                            # Converte tipo para duplex (1 = duplex, 0 = simplex)
                            duplex = 1 if tipo_impressora and tipo_impressora.lower() == 'duplex' else 0
                            logger.debug(f"Tipo da impressora '{printer_name}' encontrado: {tipo_impressora} -> duplex={duplex}")
                    
                    # Se não encontrou no banco, tenta usar o campo do evento (fallback)
                    if duplex is None:
                        # Aceita tanto "duplex" quanto "tipo" do agente
                        tipo_raw = e.get("tipo") or e.get("duplex")
                        if tipo_raw:
                            if isinstance(tipo_raw, str):
                                tipo_lower = tipo_raw.lower()
                                if tipo_lower == 'duplex':
                                    duplex = 1
                                elif tipo_lower == 'simplex':
                                    duplex = 0
                            elif tipo_raw is True or tipo_raw == 1 or str(tipo_raw).lower() == 'true':
                                duplex = 1
                            elif tipo_raw is False or tipo_raw == 0 or str(tipo_raw).lower() == 'false':
                                duplex = 0
                    
                    # Se ainda não tem, assume None (desconhecido)
                    if duplex is None:
                        logger.debug(f"Tipo duplex não determinado para impressora '{printer_name}', usando None")
                    
                    # Extrai record_number e job_id para prevenção de duplicatas
                    record_number = e.get("record_number")
                    job_id = e.get("job_id")
                    
                    # Log detalhado para diagnóstico de problemas
                    if idx == 0:
                        logger.info(f"🔍 [DIAGNÓSTICO] Evento recebido:")
                        logger.info(f"   - Pages (lógicas): {pages}")
                        logger.info(f"   - Duplex recebido: {e.get('duplex')} (convertido: {duplex})")
                        logger.info(f"   - Record Number: {record_number}")
                        logger.info(f"   - Job ID: {job_id}")
                        logger.info(f"   - Document: {document}")
                        folhas_fisicas_esperadas = calcular_folhas_fisicas(pages, duplex, copies)
                        logger.info(f"   - Folhas fisicas esperadas: {folhas_fisicas_esperadas} (pages={pages}, copies={copies}, duplex={duplex})")
                    
                    # Log detalhado do primeiro evento para debug
                    if idx == 0:
                        logger.info(f"🔍 ===== PRIMEIRO EVENTO RECEBIDO =====")
                        logger.info(f"🔍 record_number: {record_number} (tipo: {type(record_number)})")
                        logger.info(f"🔍 job_id: {job_id} (tipo: {type(job_id)})")
                        logger.info(f"🔍 user original: {e.get('user')} (tipo: {type(e.get('user'))})")
                        logger.info(f"🔍 date: {e.get('date')}")
                        logger.info(f"🔍 document: {e.get('document')}")
                        logger.info(f"🔍 pages: {e.get('pages')}")
                        logger.info(f"🔍 Todos os campos: {list(e.keys())}")
                        logger.info(f"🔍 =====================================")
                    
                    # Verifica se deve forçar inserção (ignorar duplicatas)
                    force_insert = e.get('force_insert', False) is True
                    
                    # Prevenção de duplicatas: usa record_number (mais confiável) ou fallback para dados
                    existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(events)").fetchall()]
                    has_record_number = 'record_number' in existing_columns
                    
                    if idx == 0:
                        logger.info(f"🔍 Coluna record_number existe no banco: {has_record_number}")
                        logger.info(f"🔍 Evento tem record_number: {record_number is not None} (valor: {record_number})")
                        logger.info(f"🔍 Force insert: {force_insert}")
                    
                    # Inicializa existing como None
                    existing = None
                    
                    # Se force_insert=True, ignora verificação de duplicatas
                    if not force_insert:
                        if has_record_number and record_number is not None:
                            # Usa record_number como identificador único (mais preciso)
                            # IMPORTANTE: Aceita record_number = 0 também (pode ser válido)
                            existing = conn.execute(
                                "SELECT 1 FROM events WHERE record_number = ? LIMIT 1",
                                (record_number,)
                            ).fetchone()
                            if existing:
                                logger.warning(f"⚠️ Duplicata encontrada por record_number={record_number} (já existe no banco)")
                            elif idx == 0:
                                logger.info(f"✅ Record_number {record_number} não encontrado no banco - será inserido")
                        elif job_id and 'job_id' in existing_columns and job_id:
                            # Fallback: usa job_id se disponível
                            existing = conn.execute(
                                "SELECT 1 FROM events WHERE job_id = ? LIMIT 1",
                                (job_id,)
                            ).fetchone()
                            if existing and idx == 0:
                                logger.warning(f"⚠️ Duplicata encontrada por job_id={job_id}")
                            elif idx == 0:
                                logger.info(f"✅ Job_id {job_id} não encontrado no banco - será inserido")
                        else:
                            # Fallback final: usa dados do evento (menos preciso)
                            # Só verifica se não tem record_number nem job_id
                            # IMPORTANTE: Este fallback é muito restritivo e pode causar falsos positivos
                            # Por isso, só verifica se o evento foi criado nos últimos 2 minutos
                            has_created_at = 'created_at' in existing_columns
                            if has_created_at:
                                # Verifica duplicata apenas nos últimos 2 minutos (janela muito curta)
                                existing = conn.execute(
                                    """SELECT 1 FROM events 
                                       WHERE date = ? AND user = ? AND machine = ? AND pages_printed = ?
                                       AND COALESCE(document, '') = COALESCE(?, '')
                                       AND created_at >= datetime('now', '-2 minutes')
                                       LIMIT 1""",
                                    (date_iso, user_name, machine, pages, document)
                                ).fetchone()
                            else:
                                # Sem created_at, não verifica duplicata por dados (muito arriscado)
                                # Permite inserir para não perder eventos
                                existing = None
                                if idx == 0:
                                    logger.info(f"⚠️ Sem record_number/job_id e sem created_at - inserindo sem verificar duplicata por dados")
                            
                            if existing and idx == 0:
                                logger.warning(f"⚠️ Duplicata encontrada por dados do evento (date={date_iso}, user={user_name}, pages={pages}) nos últimos 2 minutos")
                            elif idx == 0 and not existing:
                                logger.info(f"✅ Evento não encontrado no banco por dados - será inserido")
                    else:
                        # force_insert=True: ignora duplicatas, sempre insere
                        existing = None
                        if idx == 0:
                            logger.info(f"🔧 FORCE_INSERT ativado: evento será inserido mesmo se já existir")
                    
                    # Se existing foi definido e encontrou duplicata, ignora
                    if existing:
                        skipped += 1
                        motivo = "desconhecido"
                        if has_record_number and record_number is not None:
                            motivo = f"record_number={record_number} já existe"
                        elif job_id:
                            motivo = f"job_id={job_id} já existe"
                        else:
                            motivo = "dados idênticos nos últimos 2 minutos"
                        
                        logger.warning(f"⏭️ Evento {idx} IGNORADO: {motivo} | User: {user_name} | Doc: {document} | Pages: {pages}")
                        continue
                    
                    # Tenta inserir com todas as informações
                    try:
                        # Monta query dinâmica baseada nas colunas disponíveis
                        existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(events)").fetchall()]
                        
                        insert_cols = ['date', 'user', 'machine', 'pages_printed']
                        insert_vals = [date_iso, user_name, machine, pages]
                        
                        if 'document' in existing_columns:
                            insert_cols.append('document')
                            insert_vals.append(document)
                        if 'printer_name' in existing_columns:
                            insert_cols.append('printer_name')
                            insert_vals.append(printer_name)
                        if 'printer_port' in existing_columns:
                            insert_cols.append('printer_port')
                            insert_vals.append(printer_port)
                        if 'color_mode' in existing_columns:
                            insert_cols.append('color_mode')
                            insert_vals.append(color_mode)
                        if 'paper_size' in existing_columns:
                            insert_cols.append('paper_size')
                            insert_vals.append(paper_size)
                        if 'duplex' in existing_columns:
                            insert_cols.append('duplex')
                            insert_vals.append(duplex)
                        if 'copies' in existing_columns:
                            insert_cols.append('copies')
                            insert_vals.append(copies)
                        if 'job_id' in existing_columns:
                            insert_cols.append('job_id')
                            insert_vals.append(job_id)
                        if 'record_number' in existing_columns and record_number is not None:
                            insert_cols.append('record_number')
                            insert_vals.append(record_number)
                        
                        # MELHORIA: Calcula e salva folhas físicas no momento do insert
                        sheets_used = calcular_folhas_fisicas(pages, duplex, copies)
                        if 'sheets_used' in existing_columns:
                            insert_cols.append('sheets_used')
                            insert_vals.append(sheets_used)
                            logger.debug(f"📄 Evento {idx}: {pages} páginas, duplex={duplex}, copies={copies} -> {sheets_used} folhas")
                        
                        # MELHORIA: Calcula custo considerando comodatos
                        if 'cost' in existing_columns:
                            # Busca informações da impressora (comodato)
                            comodato_info = None
                            if printer_name:
                                cursor_printer = conn.execute(
                                    """SELECT comodato, insumos_inclusos, limite_paginas_mensal, custo_excedente 
                                       FROM printers WHERE printer_name = ?""",
                                    (printer_name,)
                                )
                                printer_row = cursor_printer.fetchone()
                                if printer_row:
                                    comodato_info = {
                                        'comodato': bool(printer_row[0]) if printer_row[0] is not None else False,
                                        'insumos_inclusos': bool(printer_row[1]) if printer_row[1] is not None else False,
                                        'limite_mensal': printer_row[2],
                                        'custo_excedente': printer_row[3]
                                    }
                            
                            # Calcula uso mensal atual (para verificar excedente)
                            uso_mensal_atual = 0
                            if comodato_info and comodato_info['comodato'] and comodato_info['limite_mensal']:
                                mes_atual = datetime.now().strftime("%Y-%m")
                                cursor_uso = conn.execute(
                                    """SELECT COALESCE(SUM(sheets_used), 0) as total 
                                       FROM events 
                                       WHERE printer_name = ? AND strftime('%Y-%m', date) = ?""",
                                    (printer_name, mes_atual)
                                )
                                uso_row = cursor_uso.fetchone()
                                uso_mensal_atual = uso_row[0] if uso_row else 0
                            
                            # Sistema de custos removido - não calcula mais custos
                            # insert_cols.append('cost')
                            # insert_vals.append(0.0)
                        
                        placeholders = ','.join(['?'] * len(insert_vals))
                        columns_str = ','.join(insert_cols)
                        
                        cursor = conn.execute(
                            f"INSERT INTO events ({columns_str}) VALUES ({placeholders})",
                            insert_vals
                        )
                        if cursor.rowcount > 0:
                            inserted += 1
                            if idx == 0 or inserted <= 3:
                                logger.info(f"✅ Evento {idx} INSERIDO com sucesso! ID: {cursor.lastrowid}, RecordNumber: {record_number}")
                            
                            # MELHORIA: Emite evento via WebSocket para tempo real
                            try:
                                broadcast_new_event({
                                    'id': cursor.lastrowid,
                                    'user': user_name,
                                    'printer_name': printer_name,
                                    'pages': pages,
                                    'copies': copies,
                                    'date': date_iso,
                                    'document': document,
                                    'machine': machine
                                })
                            except Exception as ws_error:
                                logger.debug(f"WebSocket broadcast error: {ws_error}")
                        else:
                            skipped += 1
                            logger.warning(f"⚠️ Evento {idx} não foi inserido (rowcount=0)")
                    except sqlite3.IntegrityError as db_error:
                        skipped += 1
                        logger.warning(f"IntegrityError ao inserir evento: {db_error}")
                    except Exception as db_error:
                        errors.append(f"Evento {idx}: erro no banco - {str(db_error)}")
                        logger.error(f"Erro ao inserir evento {idx}: {db_error}")
                
                except Exception as ex:
                    error_msg = f"Evento {idx}: {str(ex)}"
                    errors.append(error_msg)
                    # Log detalhado do erro para diagnóstico
                    logger.error(f"❌ {error_msg}")
                    if isinstance(e, dict):
                        logger.error(f"   Dados do evento: user={e.get('user', '?')}, date={e.get('date', '?')}, pages={e.get('pages', '?')}, machine={e.get('machine', '?')}")
            
            conn.commit()
        
        response = {
            "status": "ok",
            "received": len(events),
            "inserted": inserted,
            "skipped": skipped,
        }
        
        if errors:
            response["errors"] = errors[:10]  # Limita a 10 erros para não sobrecarregar
            if len(errors) > 10:
                response["errors_count"] = len(errors)
        
        logger.info(f"📊 Processados {len(events)} eventos: {inserted} inseridos, {skipped} ignorados")
        if skipped > 0 and inserted == 0:
            logger.error(f"❌ ATENÇÃO CRÍTICA: Todos os {skipped} eventos foram ignorados!")
            logger.error(f"   Possíveis causas:")
            logger.error(f"   1. Os record_numbers já existem no banco (eventos já foram processados)")
            logger.error(f"   2. Os eventos não têm record_number e estão sendo marcados como duplicados")
            logger.error(f"   3. Problema na conversão de SID para nome de usuário")
            logger.error(f"   4. Lógica de verificação de duplicatas muito restritiva")
            logger.error(f"   💡 SOLUÇÃO: Verifique os logs acima para ver por que cada evento foi ignorado")
        elif skipped > 0:
            logger.warning(f"⚠️ {skipped} eventos foram ignorados (provavelmente duplicatas legítimas)")
        if errors:
            logger.warning(f"⚠️ Encontrados {len(errors)} erros ao processar eventos")
        
        return jsonify(response)
    
    except sqlite3.OperationalError as e:
        logger.error(f"❌ Erro operacional do banco ao processar eventos: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Erro ao processar eventos no banco de dados",
            "error_type": "database_operational"
        }), 500
    except sqlite3.DatabaseError as e:
        logger.error(f"❌ Erro de banco de dados ao processar eventos: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Erro de integridade do banco de dados",
            "error_type": "database_error"
        }), 500
    except ValueError as e:
        logger.warning(f"⚠️ Erro de validação ao processar eventos: {e}")
        return jsonify({
            "status": "error",
            "message": f"Erro de validação: {str(e)}",
            "error_type": "validation_error"
        }), 400
    except Exception as e:
        logger.error(f"❌ Erro inesperado ao processar requisição: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Erro interno ao processar requisição",
            "error_type": "internal_error"
        }), 500


# ============================================================================
# NOVAS FUNCIONALIDADES - ENDPOINTS
# ============================================================================

# Inicializa variáveis de módulos
NOVOS_MODULOS_DISPONIVEIS = False
MODULOS_DISPONIVEIS = False
IA_GRATUITA_DISPONIVEL = False

# Importa módulos
try:
    from modules import comparativo, quotas, alertas, auditoria, sugestoes
    from modules import cache, relatorios_agendados, analise_padroes, metas
    from modules import backup, dashboard_widgets, relatorios_unificado
    # Novos módulos
    try:
        from modules import filtros_salvos, exportacao_avancada, comentarios
        from modules import aprovacao_impressoes, heatmap, gamificacao
        NOVOS_MODULOS_DISPONIVEIS = True
    except ImportError as e:
        logger.warning(f"Novos módulos não disponíveis: {e}")
        NOVOS_MODULOS_DISPONIVEIS = False
    # Módulos de IA
    from modules import ia_deteccao_anomalias, ia_otimizacao
    from modules import ia_alertas_inteligentes, ia_chatbot, ia_analise_preditiva
    from modules import ia_recomendacoes, ia_tendencias, ia_score_eficiencia, ia_relatorios_narrativos
    # Módulo de IA Gratuita
    try:
        from modules import ia_chatbot_gratuito
        IA_GRATUITA_DISPONIVEL = True
    except ImportError:
        IA_GRATUITA_DISPONIVEL = False
    MODULOS_DISPONIVEIS = True
except ImportError as e:
    logger.warning(f"Módulos não disponíveis: {e}")
    MODULOS_DISPONIVEIS = False
    NOVOS_MODULOS_DISPONIVEIS = False

# Importa módulo de PDF (opcional)
try:
    from modules import pdf_export
    PDF_EXPORT_AVAILABLE = True
except ImportError:
    logger.warning("Módulo pdf_export não disponível. Exportação PDF desabilitada.")
    PDF_EXPORT_AVAILABLE = False


# ============================================================================
# COMPARATIVO DE PERÍODOS
# ============================================================================

@app.route("/api/comparativo")
@login_required
def api_comparativo():
    """API para comparativo de períodos"""
    if not MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulos não disponíveis"}), 500
    
    periodo_tipo = request.args.get("periodo", "mes")
    referencia = request.args.get("referencia")
    tipo_ref = request.args.get("tipo_ref", "geral")
    
    with sqlite3.connect(DB) as conn:
        resultado = comparativo.comparar_periodos(conn, periodo_tipo, 
                                                  f"{tipo_ref}:{referencia}" if referencia else None)
    
    return jsonify(resultado)


@app.route("/comparativo")
@login_required
def pagina_comparativo():
    """Página de comparativo"""
    periodo = request.args.get("periodo", "mes")
    referencia = request.args.get("referencia")
    tipo_ref = request.args.get("tipo_ref", "geral")
    
    with sqlite3.connect(DB) as conn:
        if MODULOS_DISPONIVEIS:
            dados = comparativo.comparar_periodos(conn, periodo,
                                                 f"{tipo_ref}:{referencia}" if referencia else None)
        else:
            dados = None
    
    return render_template("comparativo.html", dados=dados, periodo=periodo,
                          referencia=referencia, tipo_ref=tipo_ref)


# ============================================================================
# QUOTAS E LIMITES
# ============================================================================

@app.route("/api/quotas")
@login_required
def api_quotas():
    """API para gerenciar quotas"""
    if not MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulos não disponíveis"}), 500
    
    tipo = request.args.get("tipo")
    referencia = request.args.get("referencia")
    periodo = request.args.get("periodo", "mensal")
    
    with sqlite3.connect(DB) as conn:
        if tipo and referencia:
            status = quotas.verificar_quota(conn, tipo, referencia, periodo)
            return jsonify(status)
        else:
            lista = quotas.listar_quotas(conn, tipo)
            return jsonify(lista)


@app.route("/admin/quotas", methods=["GET", "POST"])
@login_required
@admin_required
def admin_quotas():
    """Página de administração de quotas"""
    message = ""
    
    if request.method == "POST":
        action = request.form.get("action")
        tipo = request.form.get("tipo")
        referencia = request.form.get("referencia")
        
        with sqlite3.connect(DB) as conn:
            if action == "create":
                limite_mensal = request.form.get("limite_mensal")
                limite_trimestral = request.form.get("limite_trimestral")
                limite_anual = request.form.get("limite_anual")
                
                if quotas.criar_quota(conn, tipo, referencia,
                                     int(limite_mensal) if limite_mensal else None,
                                     int(limite_trimestral) if limite_trimestral else None,
                                     int(limite_anual) if limite_anual else None):
                    message = "Quota criada com sucesso!"
                    if MODULOS_DISPONIVEIS:
                        auditoria.registrar_acao(conn, session.get("username", "admin"),
                                                "criar_quota", "quotas", referencia)
            elif action == "delete":
                conn.execute("UPDATE quotas SET ativo = 0 WHERE tipo = ? AND referencia = ?",
                           (tipo, referencia))
                conn.commit()
                message = "Quota removida!"
    
    with sqlite3.connect(DB) as conn:
        if MODULOS_DISPONIVEIS:
            quotas_list = quotas.listar_quotas(conn)
        else:
            quotas_list = []
    
    return render_template("admin_quotas.html", quotas=quotas_list, message=message)


# ============================================================================
# ALERTAS
# ============================================================================

@app.route("/api/alertas")
@login_required
def api_alertas_lista():
    """API para listar alertas"""
    if not MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulos não disponíveis"}), 500
    
    lido = request.args.get("lido")
    nivel = request.args.get("nivel")
    
    with sqlite3.connect(DB) as conn:
        lido_bool = None if lido is None else (lido.lower() == "true")
        alertas_list = alertas.buscar_alertas(conn, lido_bool, nivel)
    
    return jsonify(alertas_list)


@app.route("/api/alertas/<int:alerta_id>/ler", methods=["POST"])
@login_required
def api_alertas_ler(alerta_id):
    """Marca alerta como lido"""
    if not MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulos não disponíveis"}), 500
    
    with sqlite3.connect(DB) as conn:
        if alertas.marcar_lido(conn, alerta_id):
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error"}), 500


@app.route("/alertas")
@login_required
def pagina_alertas():
    """Página de alertas"""
    with sqlite3.connect(DB) as conn:
        if MODULOS_DISPONIVEIS:
            alertas_list = alertas.buscar_alertas(conn, lido=False, limite=100)
            nao_lidos = len([a for a in alertas_list if not a["lido"]])
        else:
            alertas_list = []
            nao_lidos = 0
    
    return render_template("alertas.html", alertas=alertas_list, nao_lidos=nao_lidos)


# ============================================================================
# SUGESTÕES DE ECONOMIA
# ============================================================================

@app.route("/api/sugestoes")
@login_required
def api_sugestoes():
    """API para sugestões de economia"""
    if not MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulos não disponíveis"}), 500
    
    aplicadas = request.args.get("aplicadas")
    
    with sqlite3.connect(DB) as conn:
        aplicadas_bool = None if aplicadas is None else (aplicadas.lower() == "true")
        sugestoes_list = sugestoes.buscar_sugestoes(conn, aplicadas_bool)
        economia_total = sugestoes.calcular_economia_total(conn)
    
    return jsonify({
        "sugestoes": sugestoes_list,
        "economia_total": economia_total
    })


@app.route("/sugestoes")
@login_required
def pagina_sugestoes():
    """Página de sugestões de economia"""
    with sqlite3.connect(DB) as conn:
        if MODULOS_DISPONIVEIS:
            sugestoes_list = sugestoes.buscar_sugestoes(conn, aplicadas=False, limite=100)
            economia_total = sugestoes.calcular_economia_total(conn)
        else:
            sugestoes_list = []
            economia_total = {"economia_total_estimada": 0, "quantidade_sugestoes": 0}
    
    return render_template("sugestoes.html", sugestoes=sugestoes_list, 
                         economia_total=economia_total)


# ============================================================================
# ANÁLISE DE PADRÕES
# ============================================================================

@app.route("/api/analise/horarios")
@login_required
def api_analise_horarios():
    """API para análise de horários de pico"""
    dias = int(request.args.get("dias", 30))
    
    try:
        with get_db() as conn:
            if MODULOS_DISPONIVEIS:
                try:
                    from modules import analise_padroes
                    resultado = analise_padroes.analisar_horarios_pico(conn, dias)
                    return jsonify(resultado)
                except ImportError:
                    pass
            
            # Fallback simples se módulo não disponível
            horarios = []
            for hora in range(24):
                count = conn.execute(
                    """SELECT COUNT(*) FROM events 
                       WHERE CAST(strftime('%H', datetime(date || ' ' || COALESCE(time, '00:00:00'))) AS INTEGER) = ?
                       AND date >= date('now', '-' || ? || ' days')""",
                    (hora, dias)
                ).fetchone()[0]
                horarios.append({"hora": f"{hora:02d}", "total": count})
            return jsonify({"horarios": horarios})
    except Exception as e:
        logger.error(f"Erro ao analisar horários: {e}")
        return jsonify({"error": str(e), "horarios": []}), 500


@app.route("/api/dashboard/atividade-recente")
@login_required
def api_atividade_recente():
    """API para retornar atividade recente de impressões"""
    limit = int(request.args.get("limit", 10))
    
    try:
        with get_db() as conn:
            eventos = conn.execute(
                """SELECT date, user, printer_name, sheets_used, color_mode, duplex 
                   FROM events 
                   ORDER BY created_at DESC 
                   LIMIT ?""",
                (limit,)
            ).fetchall()
            
            resultado = []
            for evento in eventos:
                resultado.append({
                    "date": evento[0] if evento[0] else "N/A",
                    "user": evento[1] if evento[1] else "N/A",
                    "printer_name": evento[2] if evento[2] else "N/A",
                    "sheets_used": evento[3] if evento[3] else 0,
                    "color_mode": evento[4] if evento[4] else "N/A",
                    "duplex": evento[5] if evento[5] is not None else None
                })
            
            return jsonify(resultado)
    except Exception as e:
        logger.error(f"Erro ao buscar atividade recente: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/analise/dias")
@login_required
def api_analise_dias():
    """API para análise de dias da semana"""
    if not MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulos não disponíveis"}), 500
    
    dias = int(request.args.get("dias", 30))
    
    with sqlite3.connect(DB) as conn:
        resultado = analise_padroes.analisar_dias_semana(conn, dias)
    
    return jsonify(resultado)


@app.route("/api/analise/anomalias")
@login_required
def api_analise_anomalias():
    """API para detecção de anomalias"""
    if not MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulos não disponíveis"}), 500
    
    referencia = request.args.get("referencia")
    tipo = request.args.get("tipo", "user")
    
    with sqlite3.connect(DB) as conn:
        anomalias_list = analise_padroes.detectar_anomalias(conn, referencia, tipo)
    
    return jsonify(anomalias_list)


@app.route("/api/analise/tendencia")
@login_required
def api_analise_tendencia():
    """API para análise de tendência"""
    if not MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulos não disponíveis"}), 500
    
    referencia = request.args.get("referencia")
    tipo = request.args.get("tipo", "user")
    dias = int(request.args.get("dias", 30))
    
    with sqlite3.connect(DB) as conn:
        resultado = analise_padroes.analisar_tendencia(conn, referencia, tipo, dias)
    
    return jsonify(resultado)


# ============================================================================
# METAS
# ============================================================================

@app.route("/api/metas")
@login_required
def api_metas():
    """API para gerenciar metas"""
    if not MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulos não disponíveis"}), 500
    
    tipo = request.args.get("tipo")
    referencia = request.args.get("referencia")
    periodo = request.args.get("periodo", "mensal")
    
    with sqlite3.connect(DB) as conn:
        if tipo and referencia:
            status = metas.verificar_meta(conn, tipo, referencia, periodo)
            return jsonify(status)
        else:
            lista = metas.listar_metas(conn, tipo)
            return jsonify(lista)


@app.route("/admin/metas", methods=["GET", "POST"])
@login_required
@admin_required
def admin_metas():
    """Página de administração de metas"""
    message = ""
    ano_atual = datetime.now().year
    
    if request.method == "POST":
        action = request.form.get("action")
        tipo = request.form.get("tipo")
        referencia = request.form.get("referencia")
        periodo = request.form.get("periodo", "mensal")
        
        with sqlite3.connect(DB) as conn:
            if action == "create":
                meta_paginas = request.form.get("meta_paginas")
                meta_custo = request.form.get("meta_custo")
                ano = request.form.get("ano")
                mes = request.form.get("mes")
                
                if metas.criar_meta(conn, tipo, referencia,
                                  int(meta_paginas) if meta_paginas else None,
                                  float(meta_custo) if meta_custo else None,
                                  periodo,
                                  int(ano) if ano else None,
                                  int(mes) if mes else None):
                    message = "Meta criada com sucesso!"
                    if MODULOS_DISPONIVEIS:
                        auditoria.registrar_acao(conn, session.get("username", "admin"),
                                                "criar_meta", "metas", referencia)
    
    with sqlite3.connect(DB) as conn:
        if MODULOS_DISPONIVEIS:
            metas_list = metas.listar_metas(conn)
        else:
            metas_list = []
    
    return render_template("admin_metas.html", metas=metas_list, message=message, ano_atual=ano_atual)


# ============================================================================
# ORÇAMENTO
# ============================================================================

# Rotas removidas: sistema de orçamento removido
# @app.route("/api/orcamento")
# @app.route("/admin/orcamento")


# ============================================================================
# AUDITORIA
# ============================================================================

@app.route("/admin/auditoria")
@login_required
@admin_required
def admin_auditoria():
    """Página de auditoria"""
    usuario = request.args.get("usuario")
    acao = request.args.get("acao")
    tabela = request.args.get("tabela")
    
    with sqlite3.connect(DB) as conn:
        if MODULOS_DISPONIVEIS:
            registros = auditoria.buscar_auditoria(conn, usuario, acao, tabela, limite=200)
        else:
            registros = []
    
    return render_template("admin_auditoria.html", registros=registros)


# ============================================================================
# RELATÓRIOS AGENDADOS
# ============================================================================

@app.route("/admin/relatorios_agendados", methods=["GET", "POST"])
@login_required
@admin_required
def admin_relatorios_agendados():
    """Página de administração de relatórios agendados"""
    message = ""
    
    with get_db() as conn:
        if request.method == "POST":
            action = request.form.get("action")
            
            if action == "create":
                nome = request.form.get("nome")
                tipo = request.form.get("tipo")
                frequencia = request.form.get("frequencia")
                hora = request.form.get("hora")
                dia_semana = request.form.get("dia_semana")
                dia_mes = request.form.get("dia_mes")
                destinatarios = request.form.get("destinatarios")
                
                if relatorios_agendados.criar_relatorio_agendado(conn, nome, tipo, frequencia,
                                                                 hora,
                                                                 int(dia_semana) if dia_semana else None,
                                                                 int(dia_mes) if dia_mes else None,
                                                                 destinatarios):
                    message = "Relatório agendado criado com sucesso!"
        
        if MODULOS_DISPONIVEIS:
            rows = conn.execute("SELECT * FROM relatorios_agendados WHERE ativo = 1").fetchall()
            relatorios = [{"id": r[0], "nome": r[1], "tipo": r[2], "frequencia": r[3],
                          "hora": r[6], "destinatarios": r[7], "ultimo_envio": r[10]}
                         for r in rows]
        else:
            relatorios = []
    
    return render_template("admin_relatorios_agendados.html", relatorios=relatorios, message=message)


# ============================================================================
# DASHBOARD WIDGETS
# ============================================================================

@app.route("/api/dashboard/widgets", methods=["GET", "POST", "PUT", "DELETE"])
@login_required
def api_dashboard_widgets():
    """API para gerenciar widgets do dashboard"""
    if not MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulos não disponíveis"}), 500
    
    usuario = session.get("username", "admin")
    
    with sqlite3.connect(DB) as conn:
        if request.method == "GET":
            widgets = dashboard_widgets.buscar_widgets(conn, usuario)
            return jsonify(widgets)
        
        elif request.method == "POST":
            data = request.get_json()
            if dashboard_widgets.criar_widget(conn, usuario, data["tipo"],
                                            data.get("posicao", 0), data.get("configuracao", {})):
                return jsonify({"status": "success"})
            return jsonify({"status": "error"}), 500
        
        elif request.method == "PUT":
            data = request.get_json()
            widget_id = data.get("id")
            if dashboard_widgets.atualizar_widget(conn, widget_id,
                                                 data.get("posicao"),
                                                 data.get("configuracao")):
                return jsonify({"status": "success"})
            return jsonify({"status": "error"}), 500
        
        elif request.method == "DELETE":
            widget_id = request.args.get("id")
            if dashboard_widgets.remover_widget(conn, int(widget_id)):
                return jsonify({"status": "success"})
            return jsonify({"status": "error"}), 500


# ============================================================================
# BACKUP
# ============================================================================

@app.route("/admin/backup", methods=["GET", "POST"])
@login_required
@admin_required
def admin_backup():
    """Página de administração de backups"""
    message = ""
    
    if request.method == "POST":
        action = request.form.get("action")
        
        with sqlite3.connect(DB) as conn:
            if action == "create":
                nome = request.form.get("nome")
                descricao = request.form.get("descricao")
                if backup.criar_backup(DB, nome, descricao):
                    message = "Backup criado com sucesso!"
                    if MODULOS_DISPONIVEIS:
                        auditoria.registrar_acao(conn, session.get("username", "admin"),
                                                "criar_backup", "backup", nome)
            elif action == "restore":
                backup_id = request.form.get("backup_id")
                if backup.restaurar_backup(DB, int(backup_id)):
                    message = "Backup restaurado com sucesso!"
                    if MODULOS_DISPONIVEIS:
                        auditoria.registrar_acao(conn, session.get("username", "admin"),
                                                "restaurar_backup", "backup", backup_id)
    
    with sqlite3.connect(DB) as conn:
        if MODULOS_DISPONIVEIS:
            backups_list = backup.listar_backups(conn)
        else:
            backups_list = []
    
    return render_template("admin_backup.html", backups=backups_list, message=message)


# ============================================================================
# API REST COMPLETA
# ============================================================================

@app.route("/api/v1/events", methods=["GET"])
@login_required
def api_v1_events():
    """API REST para eventos"""
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    user = request.args.get("user")
    printer = request.args.get("printer")
    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))
    
    query = "SELECT * FROM events WHERE 1=1"
    params = []
    
    if start_date:
        query += " AND date(date) >= date(?)"
        params.append(start_date)
    if end_date:
        query += " AND date(date) <= date(?)"
        params.append(end_date)
    if user:
        query += " AND user = ?"
        params.append(user)
    if printer:
        query += " AND printer_name = ?"
        params.append(printer)
    
    query += " ORDER BY date DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()
        
        events = []
        for row in rows:
            events.append(dict(row))
    
    return jsonify({
        "events": events,
        "total": len(events),
        "limit": limit,
        "offset": offset
    })


@app.route("/api/v1/stats", methods=["GET"])
@login_required
def api_v1_stats():
    """API REST para estatísticas"""
    with sqlite3.connect(DB) as conn:
        # Calcula estatísticas básicas - conta jobs únicos, não eventos
        total_impressos = contar_jobs_unicos(conn)
        
        # Calcula páginas físicas agrupando por job primeiro (evita duplicação)
        existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(events)").fetchall()]
        has_job_id = 'job_id' in existing_columns
        
        if has_job_id:
            rows = conn.execute(
                """SELECT 
                    MAX(pages_printed) as pages,
                    MAX(duplex) as duplex,
                    MAX(COALESCE(copies, 1)) as copies,
                    MAX(printer_name) as printer_name
                FROM events
                GROUP BY CASE 
                    WHEN job_id IS NOT NULL AND job_id != '' THEN 
                        job_id || '|' || COALESCE(printer_name, '') || '|' || date
                    ELSE 
                        user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
                END"""
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT 
                    MAX(pages_printed) as pages,
                    MAX(duplex) as duplex,
                    MAX(COALESCE(copies, 1)) as copies,
                    MAX(printer_name) as printer_name
                FROM events
                GROUP BY user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date"""
            ).fetchall()
        
        total_paginas = 0
        for row in rows:
            pages = row[0] or 0
            duplex_evento = row[1] if len(row) > 1 else None
            copies = row[2] if len(row) > 2 else 1
            printer_name = row[3] if len(row) > 3 else None
            
            # Obtém duplex baseado no tipo da impressora cadastrada
            duplex = obter_duplex_da_impressora(conn, printer_name, duplex_evento)
            
            total_paginas += calcular_folhas_fisicas(pages, duplex, copies)
        
        total_usuarios = conn.execute("SELECT COUNT(DISTINCT user) FROM events").fetchone()[0]
        total_impressoras = conn.execute("SELECT COUNT(DISTINCT printer_name) FROM events WHERE printer_name IS NOT NULL").fetchone()[0]
    
    return jsonify({
        "total_impressos": total_impressos,
        "total_paginas": total_paginas,
        "total_usuarios": total_usuarios,
        "total_impressoras": total_impressoras
    })


@app.route("/api/search", methods=["GET"])
@login_required
def api_search():
    """API de busca global melhorada - busca inteligente e abrangente"""
    query = request.args.get("q", "").strip()
    
    if len(query) < 1:
        return jsonify({"results": []})
    
    query_lower = query.lower()
    query_words = query_lower.split()
    results = []
    seen = set()
    
    def add_result(title, description, url, result_type, icon, score=0):
        """Adiciona resultado evitando duplicatas"""
        if not title:
            return
        key = (str(title).lower(), result_type)
        if key not in seen:
            seen.add(key)
            results.append({
                "title": str(title),
                "description": description,
                "url": url,
                "type": result_type,
                "icon": icon,
                "score": score  # Para ordenação por relevância
            })
    
    def calculate_relevance(text, query):
        """Calcula relevância: match exato = 100, início = 50, contém = 25, palavras = 10"""
        if not text:
            return 1  # Mínimo para sempre incluir
            
        text_lower = str(text).lower()
        query_lower = query.lower()
        
        # Match exato
        if text_lower == query_lower:
            return 100
        
        # Começa com a query
        if text_lower.startswith(query_lower):
            return 50
        
        # Contém a query completa
        if query_lower in text_lower:
            return 25
        
        # Busca por palavras individuais
        words_found = 0
        for word in query_words:
            if word and word in text_lower:
                words_found += 1
        
        if words_found == len(query_words) and len(query_words) > 1:
            return 15
        elif words_found > 0:
            return 10
        
        # Se contém qualquer parte da query, retorna score mínimo
        if len(query) >= 2:
            for i in range(len(query_lower) - 1):
                if query_lower[i:i+2] in text_lower:
                    return 5
        
        return 1  # Score mínimo para sempre incluir
    
    try:
        with sqlite3.connect(DB) as conn:
            # ================================================================
            # BUSCA USUÁRIOS (mais abrangente e inteligente)
            # ================================================================
            try:
                # Busca exata primeiro (maior relevância)
                users_exact = conn.execute(
                    """SELECT DISTINCT user, COUNT(*) as count 
                       FROM events 
                       WHERE LOWER(user) = ? 
                       GROUP BY user 
                       ORDER BY count DESC 
                       LIMIT 10""",
                    (query_lower,)
                ).fetchall()
                
                for user_row in users_exact:
                    user = user_row[0]
                    add_result(
                        user,
                        f"Ver impressões do usuário {user}",
                        url_for("all_users", filtro_usuario=user),
                        "Usuário",
                        "bi-person",
                        score=100
                    )
                
                # Busca que começa com a query
                if len([r for r in results if r["type"] == "Usuário"]) < 20:
                    users_starts = conn.execute(
                        """SELECT DISTINCT user, COUNT(*) as count 
                           FROM events 
                           WHERE LOWER(user) LIKE ? 
                           AND LOWER(user) != ?
                           GROUP BY user 
                           ORDER BY 
                             CASE WHEN LOWER(user) LIKE ? THEN 1 ELSE 2 END,
                             LENGTH(user),
                             count DESC
                           LIMIT 20""",
                        (f"{query_lower}%", query_lower, f"{query_lower}%")
                    ).fetchall()
                    
                    for user_row in users_starts:
                        user = user_row[0] if user_row[0] else ""
                        if user:
                            score = calculate_relevance(user, query)
                            add_result(
                                user,
                                f"Ver impressões do usuário {user}",
                                url_for("all_users", filtro_usuario=user),
                                "Usuário",
                                "bi-person",
                                score=score
                            )
                
                # Busca contém (mais ampla) - SEMPRE executa
                users_contains = conn.execute(
                    """SELECT DISTINCT user, COUNT(*) as count 
                       FROM events 
                       WHERE user IS NOT NULL 
                       AND user != ''
                       AND LOWER(user) LIKE ?
                       AND LOWER(user) NOT LIKE ?
                       GROUP BY user 
                       ORDER BY 
                         CASE 
                           WHEN LOWER(user) LIKE ? THEN 1
                           WHEN LOWER(user) LIKE ? THEN 2
                           ELSE 3
                         END,
                         count DESC,
                         LENGTH(user)
                       LIMIT 30""",
                    (f"%{query_lower}%", f"{query_lower}%", f"%{query_lower}%", f"{query_lower}%")
                ).fetchall()
                
                for user_row in users_contains:
                    user = user_row[0] if user_row[0] else ""
                    if user:
                        score = calculate_relevance(user, query)
                        add_result(
                            user,
                            f"Ver impressões do usuário {user}",
                            url_for("all_users", filtro_usuario=user),
                            "Usuário",
                            "bi-person",
                            score=score
                        )
            except Exception as e:
                logger.warning(f"Erro ao buscar usuários: {e}")
            
            # ================================================================
            # BUSCA SETORES (tabela users e campo account)
            # ================================================================
            try:
                # Da tabela users
                sectors = conn.execute(
                    """SELECT DISTINCT sector, COUNT(*) as count
                       FROM users 
                       WHERE sector IS NOT NULL AND sector != '' 
                       AND LOWER(sector) LIKE ?
                       GROUP BY sector
                       ORDER BY 
                         CASE WHEN LOWER(sector) = ? THEN 1 
                              WHEN LOWER(sector) LIKE ? THEN 2 
                              ELSE 3 END,
                         LENGTH(sector),
                         count DESC
                       LIMIT 20""",
                    (f"%{query_lower}%", query_lower, f"{query_lower}%")
                ).fetchall()
                
                for sector_row in sectors:
                    sector = sector_row[0] if sector_row[0] else ""
                    if sector:
                        score = calculate_relevance(sector, query)
                        add_result(
                            sector,
                            f"Ver estatísticas do setor {sector}",
                            url_for("painel_setores", filtro_setor=sector),
                            "Setor",
                            "bi-building",
                            score=score
                        )
                
                # Do campo account dos events
                account_sectors = conn.execute(
                    """SELECT DISTINCT account, COUNT(*) as count
                       FROM events 
                       WHERE account IS NOT NULL AND account != '' 
                       AND LOWER(account) LIKE ?
                       GROUP BY account
                       ORDER BY 
                         CASE WHEN LOWER(account) = ? THEN 1 
                              WHEN LOWER(account) LIKE ? THEN 2 
                              ELSE 3 END,
                         LENGTH(account),
                         count DESC
                       LIMIT 30""",
                    (f"%{query_lower}%", query_lower, f"{query_lower}%")
                ).fetchall()
                
                for account_row in account_sectors:
                    account = account_row[0] if account_row[0] else ""
                    if account:
                        score = calculate_relevance(account, query)
                        add_result(
                            account,
                            f"Ver estatísticas do setor/departamento {account}",
                            url_for("painel_setores", filtro_setor=account),
                            "Setor",
                            "bi-building",
                            score=score
                        )
            except Exception as e:
                logger.warning(f"Erro ao buscar setores: {e}")
            
            # ================================================================
            # BUSCA IMPRESSORAS
            # ================================================================
            try:
                printers = conn.execute(
                    """SELECT DISTINCT printer_name, COUNT(*) as count
                       FROM events 
                       WHERE printer_name IS NOT NULL AND printer_name != '' 
                       AND LOWER(printer_name) LIKE ?
                       GROUP BY printer_name
                       ORDER BY 
                         CASE WHEN LOWER(printer_name) = ? THEN 1 
                              WHEN LOWER(printer_name) LIKE ? THEN 2 
                              ELSE 3 END,
                         LENGTH(printer_name),
                         count DESC
                       LIMIT 20""",
                    (f"%{query_lower}%", query_lower, f"{query_lower}%")
                ).fetchall()
                
                for printer_row in printers:
                    printer = printer_row[0] if printer_row[0] else ""
                    if printer:
                        score = calculate_relevance(printer, query)
                        add_result(
                            printer,
                            f"Ver estatísticas da impressora {printer}",
                            url_for("impressoras", filtro_impressora=printer),
                            "Impressora",
                            "bi-printer",
                            score=score
                        )
            except Exception as e:
                logger.warning(f"Erro ao buscar impressoras: {e}")
            
            # ================================================================
            # BUSCA MÁQUINAS/COMPUTADORES
            # ================================================================
            try:
                machines = conn.execute(
                    """SELECT DISTINCT machine, COUNT(*) as count
                       FROM events 
                       WHERE machine IS NOT NULL AND machine != '' 
                       AND LOWER(machine) LIKE ?
                       GROUP BY machine
                       ORDER BY 
                         CASE WHEN LOWER(machine) = ? THEN 1 
                              WHEN LOWER(machine) LIKE ? THEN 2 
                              ELSE 3 END,
                         count DESC
                       LIMIT 10""",
                    (f"%{query_lower}%", query_lower, f"{query_lower}%")
                ).fetchall()
                
                for machine_row in machines:
                    machine = machine_row[0] if machine_row[0] else ""
                    if machine:
                        score = calculate_relevance(machine, query)
                        add_result(
                            machine,
                            f"Ver impressões da máquina {machine}",
                            url_for("all_users"),  # Pode criar endpoint específico depois
                            "Máquina",
                            "bi-pc-display",
                            score=score
                        )
            except Exception as e:
                logger.warning(f"Erro ao buscar máquinas: {e}")
            
            # ================================================================
            # BUSCA APLICAÇÕES
            # ================================================================
            try:
                applications = conn.execute(
                    """SELECT DISTINCT application, COUNT(*) as count
                       FROM events 
                       WHERE application IS NOT NULL AND application != '' 
                       AND LOWER(application) LIKE ?
                       GROUP BY application
                       ORDER BY 
                         CASE WHEN LOWER(application) = ? THEN 1 
                              WHEN LOWER(application) LIKE ? THEN 2 
                              ELSE 3 END,
                         count DESC
                       LIMIT 10""",
                    (f"%{query_lower}%", query_lower, f"{query_lower}%")
                ).fetchall()
                
                for app_row in applications:
                    app = app_row[0] if app_row[0] else ""
                    if app:
                        if len(app) > 40:
                            app_display = app[:37] + "..."
                        else:
                            app_display = app
                        score = calculate_relevance(app, query)
                        add_result(
                            app_display,
                            f"Aplicação: {app}",
                            url_for("all_users"),
                            "Aplicação",
                            "bi-app",
                            score=score
                        )
            except Exception as e:
                logger.warning(f"Erro ao buscar aplicações: {e}")
            
            # ================================================================
            # BUSCA DOCUMENTOS (apenas se query maior)
            # ================================================================
            if len(query) >= 3:
                try:
                    documents = conn.execute(
                        """SELECT DISTINCT document, COUNT(*) as count
                           FROM events 
                           WHERE document IS NOT NULL AND document != '' 
                           AND LOWER(document) LIKE ?
                           GROUP BY document
                           ORDER BY 
                             CASE WHEN LOWER(document) LIKE ? THEN 1 ELSE 2 END,
                             count DESC
                           LIMIT 10""",
                        (f"%{query_lower}%", f"{query_lower}%")
                    ).fetchall()
                    
                    for doc_row in documents:
                        doc = doc_row[0] if doc_row[0] else ""
                        if doc:
                            doc_display = doc if len(doc) <= 60 else doc[:57] + "..."
                            score = calculate_relevance(doc, query)
                            add_result(
                                doc_display,
                                f"Documento: {doc[:80] if len(doc) > 80 else doc}",
                                url_for("all_users"),
                                "Documento",
                                "bi-file-text",
                                score=score
                            )
                except Exception as e:
                    logger.warning(f"Erro ao buscar documentos: {e}")
                    
    except Exception as e:
        logger.error(f"Erro na busca: {e}", exc_info=True)
        return jsonify({"error": "Erro ao realizar busca", "results": []}), 500
    
    # Se não encontrou nada, tenta busca mais ampla (qualquer coisa que contenha qualquer caractere)
    if len(results) == 0 and len(query) >= 1:
        try:
            with sqlite3.connect(DB) as conn:
                # Busca qualquer usuário que contenha pelo menos o primeiro caractere
                fallback_users = conn.execute(
                    """SELECT DISTINCT user, COUNT(*) as count 
                       FROM events 
                       WHERE user IS NOT NULL 
                       AND user != ''
                       AND LOWER(user) LIKE ?
                       GROUP BY user 
                       ORDER BY count DESC 
                       LIMIT 10""",
                    (f"%{query_lower[0]}%",)
                ).fetchall()
                
                for user_row in fallback_users:
                    user = user_row[0] if user_row[0] else ""
                    if user:
                        add_result(
                            user,
                            f"Ver impressões do usuário {user}",
                            url_for("all_users", filtro_usuario=user),
                            "Usuário",
                            "bi-person",
                            score=1
                        )
        except Exception as e:
            logger.warning(f"Erro na busca fallback: {e}")
    
    # Ordena por relevância (score) e depois por tipo
    type_priority = {"Usuário": 1, "Setor": 2, "Impressora": 3, "Máquina": 4, "Aplicação": 5, "Documento": 6}
    results.sort(key=lambda x: (-x.get("score", 0), type_priority.get(x["type"], 99)))
    
    # Remove score antes de retornar (não é necessário no frontend)
    for result in results:
        result.pop("score", None)
    
    # Log para debug
    logger.info(f"Busca '{query}' retornou {len(results)} resultados")
    
    # Se ainda não encontrou nada, verifica se há dados no banco
    if len(results) == 0:
        try:
            with sqlite3.connect(DB) as conn:
                total_users = conn.execute("SELECT COUNT(DISTINCT user) FROM events WHERE user IS NOT NULL AND user != ''").fetchone()[0]
                total_printers = conn.execute("SELECT COUNT(DISTINCT printer_name) FROM events WHERE printer_name IS NOT NULL AND printer_name != ''").fetchone()[0]
                logger.warning(f"Busca '{query}' não encontrou resultados. Total de usuários no banco: {total_users}, impressoras: {total_printers}")
        except Exception as e:
            logger.error(f"Erro ao verificar dados do banco: {e}")
    
    # Limita a 50 resultados (aumentado ainda mais)
    return jsonify({"results": results[:50]})


# ============================================================================
# ENDPOINTS DE IA
# ============================================================================

# Rota removida: /ia/previsao-custos
# Sistema de custos foi removido do projeto


@app.route("/ia/anomalias")
@login_required
def ia_anomalias():
    """Endpoint para detecção de anomalias"""
    try:
        dias = request.args.get('dias', 30, type=int)
        
        with sqlite3.connect(DB) as conn:
            anomalias = ia_deteccao_anomalias.detectar_padroes_suspeitos(conn, dias)
        
        return jsonify(anomalias)
    except Exception as e:
        logger.error(f"Erro na detecção de anomalias: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route("/ia/otimizacoes")
@login_required
def ia_otimizacoes():
    """Endpoint para sugestões de otimização"""
    try:
        dias = request.args.get('dias', 30, type=int)
        
        with sqlite3.connect(DB) as conn:
            otimizacoes = ia_otimizacao.obter_otimizacoes_completas(conn, dias)
        
        return jsonify(otimizacoes)
    except Exception as e:
        logger.error(f"Erro ao obter otimizações: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route("/ia/alertas-inteligentes")
@login_required
def ia_alertas_inteligentes():
    """Endpoint para alertas inteligentes"""
    try:
        dias = request.args.get('dias', 7, type=int)
        
        with sqlite3.connect(DB) as conn:
            alertas = ia_alertas_inteligentes.gerar_alertas_inteligentes(conn, dias)
            alertas_priorizados = ia_alertas_inteligentes.priorizar_alertas(alertas)
        
        return jsonify({
            'alertas': alertas_priorizados,
            'total': len(alertas_priorizados)
        })
    except Exception as e:
        logger.error(f"Erro ao gerar alertas: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route("/ia/chatbot", methods=['POST'])
@login_required
def ia_chatbot():
    """Endpoint para chatbot inteligente (tenta APIs gratuitas primeiro)"""
    try:
        data = request.get_json()
        pergunta = data.get('pergunta', '')
        metodo = data.get('metodo', 'auto')  # 'auto', 'gratuito', 'openai'
        
        if not pergunta:
            return jsonify({'erro': 'Pergunta não fornecida'}), 400
        
        with sqlite3.connect(DB) as conn:
            # Tenta APIs gratuitas primeiro (se disponível)
            if IA_GRATUITA_DISPONIVEL and metodo != 'openai':
                try:
                    resposta = ia_chatbot_gratuito.processar_pergunta_gratuita(
                        conn, pergunta, metodo='auto'
                    )
                    if resposta.get('resposta'):
                        return jsonify(resposta)
                except Exception as e:
                    logger.warning(f"Erro ao usar API gratuita: {e}, tentando OpenAI...")
            
            # Fallback para OpenAI (se configurado)
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key and metodo != 'gratuito':
                resposta = ia_chatbot.processar_pergunta(conn, pergunta, api_key)
                return jsonify(resposta)
            
            # Fallback para processamento local simples
            if IA_GRATUITA_DISPONIVEL:
                resposta = ia_chatbot_gratuito.processar_pergunta_gratuita(
                    conn, pergunta, metodo='local'
                )
                return jsonify(resposta)
            
            return jsonify({
                'resposta': 'Nenhuma API de IA configurada. Configure Groq, Ollama ou OpenAI.',
                'metodo': 'Nenhum',
                'erro': 'Nenhuma API disponível'
            }), 503
            
    except Exception as e:
        logger.error(f"Erro no chatbot: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route("/ia/apis-disponiveis")
@login_required
def ia_apis_disponiveis():
    """Lista APIs de IA disponíveis e seu status"""
    try:
        apis = []
        
        # OpenAI
        if os.getenv('OPENAI_API_KEY'):
            apis.append({
                'id': 'openai',
                'nome': 'OpenAI GPT',
                'status': 'configurado',
                'limite': 'Pay-as-you-go'
            })
        else:
            apis.append({
                'id': 'openai',
                'nome': 'OpenAI GPT',
                'status': 'nao_configurado',
                'limite': 'Requer créditos'
            })
        
        # APIs Gratuitas
        if IA_GRATUITA_DISPONIVEL:
            apis_gratuitas = ia_chatbot_gratuito.listar_apis_disponiveis()
            apis.extend(apis_gratuitas)
        
        return jsonify({'apis': apis})
    except Exception as e:
        logger.error(f"Erro ao listar APIs: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route("/ia/previsao-materiais")
@login_required
def ia_previsao_materiais():
    """Endpoint para previsão de reposição de materiais"""
    try:
        with sqlite3.connect(DB) as conn:
            previsao = ia_analise_preditiva.prever_reposicao_materiais(conn)
            sugestoes = ia_analise_preditiva.sugerir_compra_materiais(conn)
        
        return jsonify({
            'previsao': previsao,
            'sugestoes_compra': sugestoes
        })
    except Exception as e:
        logger.error(f"Erro na previsão de materiais: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route("/ia/recomendacoes")
@login_required
def ia_recomendacoes():
    """Endpoint para recomendações de configuração"""
    try:
        usuario = request.args.get('usuario', '')
        documento = request.args.get('documento', '')
        paginas = request.args.get('paginas', 0, type=int)
        
        if not usuario:
            return jsonify({'erro': 'Usuário não fornecido'}), 400
        
        with sqlite3.connect(DB) as conn:
            recomendacao = ia_recomendacoes.recomendar_configuracao(
                conn, usuario, documento, paginas
            )
        
        return jsonify(recomendacao)
    except Exception as e:
        logger.error(f"Erro nas recomendações: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route("/ia/tendencias")
@login_required
def ia_tendencias():
    """Endpoint para análise de tendências"""
    try:
        with sqlite3.connect(DB) as conn:
            insights = ia_tendencias.obter_insights_tendencias(conn)
        
        return jsonify(insights)
    except Exception as e:
        logger.error(f"Erro na análise de tendências: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route("/ia/score-eficiencia")
@login_required
def ia_score_eficiencia():
    """Endpoint para scores de eficiência"""
    try:
        tipo = request.args.get('tipo', 'usuario')  # 'usuario' ou 'setor'
        item = request.args.get('item', '')  # Nome do usuário ou setor
        dias = request.args.get('dias', 30, type=int)
        
        with sqlite3.connect(DB) as conn:
            if item:
                if tipo == 'usuario':
                    score = ia_score_eficiencia.calcular_score_eficiencia_usuario(conn, item, dias)
                else:
                    score = ia_score_eficiencia.calcular_score_eficiencia_setor(conn, item, dias)
                return jsonify(score)
            else:
                ranking = ia_score_eficiencia.obter_ranking_eficiencia(conn, tipo, dias)
                return jsonify({'ranking': ranking})
    except Exception as e:
        logger.error(f"Erro no score de eficiência: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route("/ia/relatorio-narrativo")
@login_required
def ia_relatorio_narrativo():
    """Endpoint para geração de relatório narrativo"""
    try:
        dias = request.args.get('dias', 30, type=int)
        api_key = os.getenv('OPENAI_API_KEY')
        
        with get_db() as conn:
            relatorio = ia_relatorios_narrativos.gerar_relatorio_narrativo(conn, dias, api_key)
        
        return jsonify(relatorio)
    except Exception as e:
        logger.error(f"Erro ao gerar relatório narrativo: {e}")
        return jsonify({'erro': str(e)}), 500


@app.route("/health")
def health():
    """Endpoint de health check para monitoramento"""
    try:
        # Verifica conexão com banco
        with get_db() as conn:
            conn.execute("SELECT 1").fetchone()
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return jsonify({
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "features": {
            "rate_limiting": RATE_LIMIT_ENABLED,
            "csrf": CSRF_ENABLED,
            "compression": COMPRESS_ENABLED,
            "pdf_export": PDF_EXPORT_AVAILABLE,
            "modules": MODULOS_DISPONIVEIS
        }
    }), 200 if db_status == "healthy" else 503


# ============================================================================
# FILTROS SALVOS
# ============================================================================

@app.route("/api/filtros/salvar", methods=["POST"])
@login_required
def api_filtros_salvar():
    """API para salvar um filtro"""
    if not NOVOS_MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulo não disponível"}), 500
    
    try:
        data = request.get_json()
        usuario = session.get("user", "admin")
        nome = data.get("nome", "")
        tipo = data.get("tipo", "dashboard")
        filtros = data.get("filtros", {})
        compartilhado = data.get("compartilhado", False)
        padrao = data.get("padrao", False)
        
        if not nome:
            return jsonify({"error": "Nome do filtro é obrigatório"}), 400
        
        with sqlite3.connect(DB) as conn:
            if filtros_salvos.salvar_filtro(conn, usuario, nome, tipo, filtros, compartilhado, padrao):
                return jsonify({"status": "success", "message": "Filtro salvo com sucesso"})
            else:
                return jsonify({"error": "Erro ao salvar filtro"}), 500
    except Exception as e:
        logger.error(f"Erro ao salvar filtro: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/filtros/listar", methods=["GET"])
@login_required
def api_filtros_listar():
    """API para listar filtros salvos"""
    if not NOVOS_MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulo não disponível"}), 500
    
    try:
        usuario = session.get("user", "admin")
        tipo = request.args.get("tipo")
        
        with sqlite3.connect(DB) as conn:
            filtros = filtros_salvos.listar_filtros(conn, usuario, tipo)
            return jsonify({"filtros": filtros})
    except Exception as e:
        logger.error(f"Erro ao listar filtros: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/filtros/deletar", methods=["DELETE"])
@login_required
def api_filtros_deletar():
    """API para deletar um filtro"""
    if not NOVOS_MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulo não disponível"}), 500
    
    try:
        filtro_id = request.args.get("id")
        usuario = session.get("user", "admin")
        
        if not filtro_id:
            return jsonify({"error": "ID do filtro é obrigatório"}), 400
        
        with sqlite3.connect(DB) as conn:
            if filtros_salvos.deletar_filtro(conn, int(filtro_id), usuario):
                return jsonify({"status": "success", "message": "Filtro deletado com sucesso"})
            else:
                return jsonify({"error": "Erro ao deletar filtro"}), 500
    except Exception as e:
        logger.error(f"Erro ao deletar filtro: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/filtros")
@login_required
def pagina_filtros():
    """Página de gerenciamento de filtros salvos"""
    if not NOVOS_MODULOS_DISPONIVEIS:
        flash("Funcionalidade não disponível", "warning")
        return redirect(url_for("dashboard"))
    
    try:
        usuario = session.get("user", "admin")
        with sqlite3.connect(DB) as conn:
            # Cria tabelas se não existirem
            filtros_salvos.criar_tabela_filtros(conn)
            filtros = filtros_salvos.listar_filtros(conn, usuario)
        
        return render_template("filtros_salvos.html", filtros=filtros)
    except Exception as e:
        logger.error(f"Erro ao carregar página de filtros: {e}", exc_info=True)
        flash(f"Erro ao carregar filtros: {str(e)}", "danger")
        return redirect(url_for("dashboard"))


# ============================================================================
# EXPORTAÇÃO AVANÇADA
# ============================================================================

@app.route("/api/export/csv", methods=["POST"])
@login_required
def api_export_csv():
    """API para exportar dados em CSV"""
    if not NOVOS_MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulo não disponível"}), 500
    
    try:
        data = request.get_json()
        query = data.get("query", "")
        params = tuple(data.get("params", []))
        
        if not query:
            return jsonify({"error": "Query é obrigatória"}), 400
        
        with get_db() as conn:
            output = exportacao_avancada.exportar_csv(conn, query, params)
            return send_file(
                output,
                download_name="exportacao.csv",
                as_attachment=True,
                mimetype="text/csv"
            )
    except Exception as e:
        logger.error(f"Erro ao exportar CSV: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/export/png", methods=["POST"])
@login_required
def api_export_png():
    """API para exportar gráfico como PNG"""
    if not NOVOS_MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulo não disponível"}), 500
    
    try:
        data = request.get_json()
        chart_data = data.get("chart_data", {})
        
        png_data = exportacao_avancada.exportar_grafico_png(chart_data)
        if png_data:
            return send_file(
                io.BytesIO(png_data),
                download_name="grafico.png",
                as_attachment=True,
                mimetype="image/png"
            )
        else:
            return jsonify({"error": "Erro ao gerar PNG"}), 500
    except Exception as e:
        logger.error(f"Erro ao exportar PNG: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# COMENTÁRIOS
# ============================================================================

@app.route("/api/comentarios/adicionar", methods=["POST"])
@login_required
def api_comentarios_adicionar():
    """API para adicionar comentário"""
    if not NOVOS_MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulo não disponível"}), 500
    
    try:
        data = request.get_json()
        evento_id = data.get("evento_id")
        usuario = session.get("user", "admin")
        comentario = data.get("comentario", "")
        tags = data.get("tags", [])
        
        if not evento_id or not comentario:
            return jsonify({"error": "Evento ID e comentário são obrigatórios"}), 400
        
        with sqlite3.connect(DB) as conn:
            if comentarios.adicionar_comentario(conn, evento_id, usuario, comentario, tags):
                return jsonify({"status": "success", "message": "Comentário adicionado"})
            else:
                return jsonify({"error": "Erro ao adicionar comentário"}), 500
    except Exception as e:
        logger.error(f"Erro ao adicionar comentário: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/comentarios/listar", methods=["GET"])
@login_required
def api_comentarios_listar():
    """API para listar comentários"""
    if not NOVOS_MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulo não disponível"}), 500
    
    try:
        evento_id = request.args.get("evento_id")
        usuario = request.args.get("usuario")
        
        with sqlite3.connect(DB) as conn:
            comentarios_list = comentarios.listar_comentarios(
                conn, 
                int(evento_id) if evento_id else None,
                usuario
            )
            return jsonify({"comentarios": comentarios_list})
    except Exception as e:
        logger.error(f"Erro ao listar comentários: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/comentarios/deletar", methods=["DELETE"])
@login_required
def api_comentarios_deletar():
    """API para deletar comentário"""
    if not NOVOS_MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulo não disponível"}), 500
    
    try:
        comentario_id = request.args.get("id")
        usuario = session.get("user", "admin")
        
        if not comentario_id:
            return jsonify({"error": "ID do comentário é obrigatório"}), 400
        
        with sqlite3.connect(DB) as conn:
            if comentarios.deletar_comentario(conn, int(comentario_id), usuario):
                return jsonify({"status": "success", "message": "Comentário deletado"})
            else:
                return jsonify({"error": "Erro ao deletar comentário"}), 500
    except Exception as e:
        logger.error(f"Erro ao deletar comentário: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/comentarios")
@login_required
def pagina_comentarios():
    """Página de gerenciamento de comentários"""
    if not NOVOS_MODULOS_DISPONIVEIS:
        flash("Funcionalidade não disponível", "warning")
        return redirect(url_for("dashboard"))
    
    try:
        with sqlite3.connect(DB) as conn:
            # Cria tabelas se não existirem
            comentarios.criar_tabela_comentarios(conn)
        
        return render_template("comentarios.html")
    except Exception as e:
        logger.error(f"Erro ao carregar página de comentários: {e}", exc_info=True)
        flash(f"Erro ao carregar comentários: {str(e)}", "danger")
        return redirect(url_for("dashboard"))


# ============================================================================
# APROVAÇÕES
# ============================================================================

@app.route("/api/aprovacoes/pendentes", methods=["GET"])
@login_required
@admin_required
def api_aprovacoes_pendentes():
    """API para listar aprovações pendentes"""
    if not NOVOS_MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulo não disponível"}), 500
    
    try:
        with sqlite3.connect(DB) as conn:
            aprovacoes = aprovacao_impressoes.listar_aprovacoes_pendentes(conn)
            return jsonify({"aprovacoes": aprovacoes})
    except Exception as e:
        logger.error(f"Erro ao listar aprovações: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/aprovacoes/aprovar", methods=["POST"])
@login_required
@admin_required
def api_aprovacoes_aprovar():
    """API para aprovar impressão"""
    if not NOVOS_MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulo não disponível"}), 500
    
    try:
        data = request.get_json()
        aprovacao_id = data.get("id")
        aprovador = session.get("user", "admin")
        
        if not aprovacao_id:
            return jsonify({"error": "ID da aprovação é obrigatório"}), 400
        
        with sqlite3.connect(DB) as conn:
            if aprovacao_impressoes.aprovar_impressao(conn, aprovacao_id, aprovador):
                return jsonify({"status": "success", "message": "Impressão aprovada"})
            else:
                return jsonify({"error": "Erro ao aprovar impressão"}), 500
    except Exception as e:
        logger.error(f"Erro ao aprovar impressão: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/aprovacoes/rejeitar", methods=["POST"])
@login_required
@admin_required
def api_aprovacoes_rejeitar():
    """API para rejeitar impressão"""
    if not NOVOS_MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulo não disponível"}), 500
    
    try:
        data = request.get_json()
        aprovacao_id = data.get("id")
        motivo = data.get("motivo", "")
        aprovador = session.get("user", "admin")
        
        if not aprovacao_id:
            return jsonify({"error": "ID da aprovação é obrigatório"}), 400
        
        with sqlite3.connect(DB) as conn:
            if aprovacao_impressoes.rejeitar_impressao(conn, aprovacao_id, aprovador, motivo):
                return jsonify({"status": "success", "message": "Impressão rejeitada"})
            else:
                return jsonify({"error": "Erro ao rejeitar impressão"}), 500
    except Exception as e:
        logger.error(f"Erro ao rejeitar impressão: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/aprovacoes")
@login_required
@admin_required
def pagina_aprovacoes():
    """Página de aprovações pendentes"""
    if not NOVOS_MODULOS_DISPONIVEIS:
        flash("Funcionalidade não disponível", "warning")
        return redirect(url_for("dashboard"))
    
    try:
        with sqlite3.connect(DB) as conn:
            # Cria tabelas se não existirem
            aprovacao_impressoes.criar_tabela_aprovacoes(conn)
            aprovacoes_list = aprovacao_impressoes.listar_aprovacoes_pendentes(conn)
        
        return render_template("aprovacoes.html", aprovacoes=aprovacoes_list)
    except Exception as e:
        logger.error(f"Erro ao carregar página de aprovações: {e}", exc_info=True)
        flash(f"Erro ao carregar aprovações: {str(e)}", "danger")
        return redirect(url_for("dashboard"))


# ============================================================================
# HEATMAPS
# ============================================================================

@app.route("/api/heatmap/horarios", methods=["GET"])
@login_required
def api_heatmap_horarios():
    """API para heatmap de horários"""
    if not NOVOS_MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulo não disponível"}), 500
    
    try:
        dias = int(request.args.get("dias", 30))
        with sqlite3.connect(DB) as conn:
            data = heatmap.gerar_heatmap_horarios(conn, dias)
            return jsonify(data)
    except Exception as e:
        logger.error(f"Erro ao gerar heatmap de horários: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/heatmap/setores", methods=["GET"])
@login_required
def api_heatmap_setores():
    """API para heatmap de setores"""
    if not NOVOS_MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulo não disponível"}), 500
    
    try:
        dias = int(request.args.get("dias", 30))
        with sqlite3.connect(DB) as conn:
            data = heatmap.gerar_heatmap_setores(conn, dias)
            return jsonify(data)
    except Exception as e:
        logger.error(f"Erro ao gerar heatmap de setores: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/heatmap/semanal", methods=["GET"])
@login_required
def api_heatmap_semanal():
    """API para heatmap semanal"""
    if not NOVOS_MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulo não disponível"}), 500
    
    try:
        semanas = int(request.args.get("semanas", 8))
        with sqlite3.connect(DB) as conn:
            data = heatmap.gerar_heatmap_semanal(conn, semanas)
            return jsonify(data)
    except Exception as e:
        logger.error(f"Erro ao gerar heatmap semanal: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/heatmaps")
@login_required
def pagina_heatmaps():
    """Página de heatmaps"""
    if not NOVOS_MODULOS_DISPONIVEIS:
        flash("Funcionalidade não disponível", "warning")
        return redirect(url_for("dashboard"))
    
    try:
        return render_template("heatmaps.html")
    except Exception as e:
        logger.error(f"Erro ao carregar página de heatmaps: {e}", exc_info=True)
        flash(f"Erro ao carregar heatmaps: {str(e)}", "danger")
        return redirect(url_for("dashboard"))


# ============================================================================
# GAMIFICAÇÃO
# ============================================================================

@app.route("/api/gamificacao/ranking", methods=["GET"])
@login_required
def api_gamificacao_ranking():
    """API para ranking de gamificação"""
    if not NOVOS_MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulo não disponível"}), 500
    
    try:
        tipo = request.args.get("tipo", "usuarios")
        limite = int(request.args.get("limite", 10))
        
        with sqlite3.connect(DB) as conn:
            ranking = gamificacao.obter_ranking(conn, tipo, limite)
            return jsonify({"ranking": ranking})
    except Exception as e:
        logger.error(f"Erro ao obter ranking: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/gamificacao/pontos", methods=["GET"])
@login_required
def api_gamificacao_pontos():
    """API para obter pontos do usuário"""
    if not NOVOS_MODULOS_DISPONIVEIS:
        return jsonify({"error": "Módulo não disponível"}), 500
    
    try:
        usuario = session.get("user", "admin")
        with sqlite3.connect(DB) as conn:
            user_data = conn.execute(
                "SELECT pontos, nivel, economia_total, badges FROM gamificacao WHERE usuario = ?",
                (usuario,)
            ).fetchone()
            
            if user_data:
                return jsonify({
                    "pontos": user_data[0],
                    "nivel": user_data[1],
                    "economia": user_data[2],
                    "badges": user_data[3].split(',') if user_data[3] else []
                })
            else:
                return jsonify({"pontos": 0, "nivel": 1, "economia": 0, "badges": []})
    except Exception as e:
        logger.error(f"Erro ao obter pontos: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/gamificacao")
@login_required
def pagina_gamificacao():
    """Página de gamificação e ranking"""
    if not NOVOS_MODULOS_DISPONIVEIS:
        flash("Funcionalidade não disponível", "warning")
        return redirect(url_for("dashboard"))
    
    usuario = session.get("user", "admin")
    try:
        with sqlite3.connect(DB) as conn:
            # Cria tabelas se não existirem
            gamificacao.criar_tabela_gamificacao(conn)
            
            ranking_usuarios = gamificacao.obter_ranking(conn, "usuarios", 10)
            ranking_setores = gamificacao.obter_ranking(conn, "setores", 10)
            
            try:
                user_data = conn.execute(
                    "SELECT pontos, nivel, economia_total, badges FROM gamificacao WHERE usuario = ?",
                    (usuario,)
                ).fetchone()
            except sqlite3.OperationalError:
                # Tabela não existe ainda, cria e retorna valores padrão
                gamificacao.criar_tabela_gamificacao(conn)
                user_data = None
            
            pontos_usuario = {
                "pontos": user_data[0] if user_data else 0,
                "nivel": user_data[1] if user_data else 1,
                "economia": user_data[2] if user_data else 0,
                "badges": user_data[3].split(',') if user_data and user_data[3] else []
            }
        
        return render_template("gamificacao.html", 
                             ranking_usuarios=ranking_usuarios,
                             ranking_setores=ranking_setores,
                             pontos_usuario=pontos_usuario)
    except Exception as e:
        logger.error(f"Erro ao carregar página de gamificação: {e}", exc_info=True)
        flash(f"Erro ao carregar gamificação: {str(e)}", "danger")
        return redirect(url_for("dashboard"))


# ============================================================================
# WIDGETS PERSONALIZADOS
# ============================================================================

@app.route("/widgets")
@login_required
def pagina_widgets():
    """Página para gerenciar widgets personalizados"""
    return render_template("widgets_personalizados.html")


# ============================================================================
# PAINEL ADMINISTRATIVO AVANÇADO
# ============================================================================

@app.route("/admin/limpar-eventos", methods=["GET", "POST"])
@login_required
@admin_required
@csrf_exempt_if_enabled
def admin_limpar_eventos():
    """Página administrativa para limpar eventos do banco"""
    message = ""
    message_type = "info"
    
    if request.method == "POST":
        try:
            # Tenta obter action de diferentes formas
            action = None
            if request.is_json:
                action = request.json.get("action")
            else:
                action = request.form.get("action")
            
            # Log para debug
            logger.info(f"POST recebido - action: {action}, form: {dict(request.form)}, is_json: {request.is_json}, content_type: {request.content_type}")
            
            if not action:
                # Tenta obter de outras formas
                action = request.form.get("action") or request.args.get("action")
                if not action:
                    # Lista todos os campos recebidos para debug
                    form_keys = list(request.form.keys()) if request.form else []
                    args_keys = list(request.args.keys()) if request.args else []
                    message = f"Ação não especificada. Campos recebidos - Form: {form_keys}, Args: {args_keys}, Form data: {dict(request.form)}"
                    message_type = "danger"
                    logger.warning(f"Ação não encontrada no request. Form keys: {form_keys}, Args keys: {args_keys}, Form data: {dict(request.form)}")
                else:
                    logger.info(f"Action encontrado via fallback: {action}")
            else:
                with sqlite3.connect(DB) as conn:
                    eventos_antes = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
                    
                    if action == "todos":
                        # Limpa todos os eventos
                        conn.execute("DELETE FROM events")
                        conn.commit()
                        eventos_depois = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
                        eventos_removidos = eventos_antes - eventos_depois
                        message = f"✅ Todos os eventos foram removidos. {eventos_removidos} eventos deletados."
                        message_type = "success"
                        logger.info(f"Admin {session.get('username', 'unknown')} removeu TODOS os eventos ({eventos_removidos} eventos)")
                    
                    elif action == "periodo":
                        # Limpa eventos de um período específico
                        start_date = request.form.get("start_date") or (request.json.get("start_date") if request.is_json else None)
                        end_date = request.form.get("end_date") or (request.json.get("end_date") if request.is_json else None)
                        
                        if not start_date or not end_date:
                            message = "Data início e data fim são obrigatórias para limpeza por período."
                            message_type = "danger"
                        else:
                            # Conta antes
                            eventos_antes = conn.execute(
                                "SELECT COUNT(*) FROM events WHERE date(date) >= date(?) AND date(date) <= date(?)",
                                (start_date, end_date)
                            ).fetchone()[0]
                            
                            # Remove
                            conn.execute(
                                "DELETE FROM events WHERE date(date) >= date(?) AND date(date) <= date(?)",
                                (start_date, end_date)
                            )
                            conn.commit()
                            
                            # Conta depois
                            eventos_depois = conn.execute(
                                "SELECT COUNT(*) FROM events WHERE date(date) >= date(?) AND date(date) <= date(?)",
                                (start_date, end_date)
                            ).fetchone()[0]
                            
                            eventos_removidos = eventos_antes - eventos_depois
                            message = f"✅ Eventos do período {start_date} a {end_date} foram removidos. {eventos_removidos} eventos deletados."
                            message_type = "success"
                            logger.info(f"Admin {session.get('username', 'unknown')} removeu eventos do período {start_date} a {end_date} ({eventos_removidos} eventos)")
                    
                    elif action == "antigos":
                        # Limpa eventos mais antigos que X dias
                        dias = int(request.form.get("dias", 90) or (request.json.get("dias", 90) if request.is_json else 90))
                        
                        # Conta antes
                        eventos_antes = conn.execute(
                            "SELECT COUNT(*) FROM events WHERE date(date) < date('now', '-' || ? || ' days')",
                            (dias,)
                        ).fetchone()[0]
                        
                        # Remove
                        conn.execute(
                            "DELETE FROM events WHERE date(date) < date('now', '-' || ? || ' days')",
                            (dias,)
                        )
                        conn.commit()
                        
                        # Conta depois
                        eventos_depois = conn.execute(
                            "SELECT COUNT(*) FROM events WHERE date(date) < date('now', '-' || ? || ' days')",
                            (dias,)
                        ).fetchone()[0]
                        
                        eventos_removidos = eventos_antes - eventos_depois
                        message = f"✅ Eventos mais antigos que {dias} dias foram removidos. {eventos_removidos} eventos deletados."
                        message_type = "success"
                        logger.info(f"Admin {session.get('username', 'unknown')} removeu eventos mais antigos que {dias} dias ({eventos_removidos} eventos)")
                    
                    else:
                        message = "Ação inválida."
                        message_type = "danger"
            
            if request.is_json:
                return jsonify({"status": "success" if message_type == "success" else "error", "message": message}), 200 if message_type == "success" else 400
            
        except Exception as e:
            logger.error(f"Erro ao limpar eventos: {e}", exc_info=True)
            message = f"Erro ao limpar eventos: {str(e)}"
            message_type = "danger"
            if request.is_json:
                return jsonify({"status": "error", "message": message}), 500
    
    # Estatísticas para exibir na página
    try:
        with sqlite3.connect(DB) as conn:
            total_eventos = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            total_jobs = contar_jobs_unicos(conn)
            
            # Eventos por mês (últimos 6 meses)
            eventos_por_mes = conn.execute("""
                SELECT 
                    strftime('%Y-%m', date) as mes,
                    COUNT(*) as total
                FROM events
                WHERE date >= date('now', '-6 months')
                GROUP BY mes
                ORDER BY mes DESC
            """).fetchall()
            
            # Evento mais antigo
            evento_mais_antigo = conn.execute("SELECT MIN(date) FROM events").fetchone()[0]
            
            # Evento mais recente
            evento_mais_recente = conn.execute("SELECT MAX(date) FROM events").fetchone()[0]
            
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        total_eventos = 0
        total_jobs = 0
        eventos_por_mes = []
        evento_mais_antigo = None
        evento_mais_recente = None
    
    return render_template("admin_limpar_eventos.html",
                         total_eventos=total_eventos,
                         total_jobs=total_jobs,
                         eventos_por_mes=eventos_por_mes,
                         evento_mais_antigo=evento_mais_antigo,
                         evento_mais_recente=evento_mais_recente,
                         message=message,
                         message_type=message_type,
                         CSRF_ENABLED=CSRF_ENABLED)


@app.route("/admin/painel")
@login_required
@admin_required
def admin_painel():
    """Painel administrativo avançado com todas as ferramentas"""
    try:
        with sqlite3.connect(DB) as conn:
            # Estatísticas gerais
            total_usuarios = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            # IMPORTANTE: Conta jobs únicos, não eventos individuais
            total_eventos = contar_jobs_unicos(conn)
            total_impressoras = conn.execute("SELECT COUNT(DISTINCT printer_name) FROM events WHERE printer_name IS NOT NULL").fetchone()[0]
            
            # Eventos hoje - conta jobs únicos
            hoje = datetime.now().date().isoformat()
            eventos_hoje = contar_jobs_unicos(conn, "WHERE date(date) = date(?)", [hoje])
            
            # Últimos eventos
            ultimos_eventos = conn.execute(
                "SELECT user, printer_name, pages_printed, date, created_at FROM events ORDER BY created_at DESC LIMIT 10"
            ).fetchall()
            
            # Alertas não lidos
            alertas_nao_lidos = conn.execute(
                "SELECT COUNT(*) FROM alertas WHERE lido = 0"
            ).fetchone()[0]
            
            # Usuários ativos (últimos 30 dias)
            trinta_dias_atras = (datetime.now() - timedelta(days=30)).date().isoformat()
            usuarios_ativos = conn.execute(
                "SELECT COUNT(DISTINCT user) FROM events WHERE date(date) >= date(?)",
                (trinta_dias_atras,)
            ).fetchone()[0]
            
            # Tamanho do banco de dados
            db_size = os.path.getsize(DB) if os.path.exists(DB) else 0
            db_size_mb = db_size / (1024 * 1024)
            
            # Configurações do sistema
            configs = {}
            try:
                config_rows = conn.execute("SELECT chave, valor FROM config").fetchall()
                for row in config_rows:
                    configs[row[0]] = row[1]
            except sqlite3.OperationalError:
                pass
            
        return render_template("admin_painel.html",
                             total_usuarios=total_usuarios,
                             total_eventos=total_eventos,
                             total_impressoras=total_impressoras,
                             eventos_hoje=eventos_hoje,
                             usuarios_ativos=usuarios_ativos,
                             alertas_nao_lidos=alertas_nao_lidos,
                             db_size_mb=round(db_size_mb, 2),
                             ultimos_eventos=ultimos_eventos,
                             configs=configs)
    except Exception as e:
        logger.error(f"Erro ao carregar painel administrativo: {e}", exc_info=True)
        flash(f"Erro ao carregar painel: {str(e)}", "danger")
        return redirect(url_for("dashboard"))


# ============================================================================
# NOVAS FERRAMENTAS E APIs AVANÇADAS
# ============================================================================

@app.route("/api/metrics/realtime", methods=["GET"])
@login_required
def api_metrics_realtime():
    """API para métricas em tempo real"""
    try:
        with sqlite3.connect(DB) as conn:
            # Últimas 24 horas
            hoje = datetime.now().date().isoformat()
            
            # Impressões hoje
            impressoes_hoje = conn.execute(
                "SELECT COUNT(*) FROM events WHERE date(date) = date(?)",
                (hoje,)
            ).fetchone()[0]
            
            # Impressões última hora
            impressoes_ultima_hora = conn.execute(
                """SELECT COUNT(*) FROM events 
                   WHERE datetime(date || ' ' || substr(created_at, 12, 8)) >= datetime('now', '-1 hour')""",
            ).fetchone()[0]
            
            # Páginas hoje
            rows = conn.execute(
                "SELECT pages_printed, duplex, COALESCE(copies, 1) as copies FROM events WHERE date(date) = date(?)",
                (hoje,)
            ).fetchall()
            paginas_hoje = sum(calcular_folhas_fisicas(r[0] or 0, r[1] if len(r) > 1 else None, r[2] if len(r) > 2 else 1) for r in rows)
            
            # Top usuários hoje
            top_usuarios = conn.execute(
                """SELECT user, COUNT(*) as total 
                   FROM events 
                   WHERE date(date) = date(?)
                   GROUP BY user 
                   ORDER BY total DESC 
                   LIMIT 5""",
                (hoje,)
            ).fetchall()
            
            # Top impressoras hoje
            top_impressoras = conn.execute(
                """SELECT printer_name, COUNT(*) as total 
                   FROM events 
                   WHERE date(date) = date(?) AND printer_name IS NOT NULL
                   GROUP BY printer_name 
                   ORDER BY total DESC 
                   LIMIT 5""",
                (hoje,)
            ).fetchall()
            
            # Tendência (últimas 6 horas)
            tendencia = []
            for i in range(6):
                hora = datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(hours=i)
                hora_anterior = hora - timedelta(hours=1)
                count = conn.execute(
                    """SELECT COUNT(*) FROM events 
                       WHERE datetime(date || ' ' || substr(created_at, 12, 8)) >= ? 
                       AND datetime(date || ' ' || substr(created_at, 12, 8)) < ?""",
                    (hora_anterior.isoformat(), hora.isoformat())
                ).fetchone()[0]
                tendencia.insert(0, {
                    'hora': hora.strftime('%H:00'),
                    'total': count
                })
            
            return jsonify({
                'impressoes_hoje': impressoes_hoje,
                'impressoes_ultima_hora': impressoes_ultima_hora,
                'paginas_hoje': paginas_hoje,
                'top_usuarios': [{'user': u[0], 'total': u[1]} for u in top_usuarios],
                'top_impressoras': [{'printer': p[0], 'total': p[1]} for p in top_impressoras],
                'tendencia': tendencia,
                'timestamp': datetime.now().isoformat()
            })
    except Exception as e:
        logger.error(f"Erro ao obter métricas em tempo real: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/notifications", methods=["GET", "POST"])
@login_required
def api_notifications():
    """API para notificações em tempo real"""
    if request.method == "GET":
        try:
            usuario = session.get("user", "admin")
            nao_lidas = request.args.get("nao_lidas", "false").lower() == "true"
            
            with sqlite3.connect(DB) as conn:
                query = """SELECT id, tipo, titulo, mensagem, nivel, lido, created_at 
                          FROM alertas WHERE 1=1"""
                params = []
                
                if nao_lidas:
                    query += " AND lido = 0"
                
                query += " ORDER BY created_at DESC LIMIT 50"
                
                alertas_list = conn.execute(query, params).fetchall()
                
                notifications = []
                for alerta in alertas_list:
                    notifications.append({
                        'id': alerta[0],
                        'type': alerta[1],
                        'title': alerta[2],
                        'message': alerta[3],
                        'level': alerta[4],
                        'read': bool(alerta[5]),
                        'created_at': alerta[6]
                    })
                
                return jsonify({"notifications": notifications})
        except Exception as e:
            logger.error(f"Erro ao buscar notificações: {e}")
            return jsonify({"error": str(e)}), 500
    
    elif request.method == "POST":
        try:
            data = request.get_json()
            action = data.get("action")
            notification_id = data.get("id")
            
            with sqlite3.connect(DB) as conn:
                if action == "mark_read":
                    conn.execute(
                        "UPDATE alertas SET lido = 1 WHERE id = ?",
                        (notification_id,)
                    )
                    conn.commit()
                    return jsonify({"status": "success"})
                elif action == "mark_all_read":
                    conn.execute("UPDATE alertas SET lido = 1")
                    conn.commit()
                    return jsonify({"status": "success"})
                elif action == "delete":
                    conn.execute("DELETE FROM alertas WHERE id = ?", (notification_id,))
                    conn.commit()
                    return jsonify({"status": "success"})
        except Exception as e:
            logger.error(f"Erro ao processar notificação: {e}")
            return jsonify({"error": str(e)}), 500


@app.route("/api/compare/periods", methods=["POST"])
@login_required
def api_compare_periods():
    """API para comparação avançada de períodos"""
    try:
        data = request.get_json()
        periodo1_inicio = data.get("periodo1_inicio")
        periodo1_fim = data.get("periodo1_fim")
        periodo2_inicio = data.get("periodo2_inicio")
        periodo2_fim = data.get("periodo2_fim")
        tipo = data.get("tipo", "geral")  # geral, usuario, setor, impressora
        
        if not all([periodo1_inicio, periodo1_fim, periodo2_inicio, periodo2_fim]):
            return jsonify({"error": "Todos os períodos são obrigatórios"}), 400
        
        with sqlite3.connect(DB) as conn:
            # Verifica se job_id existe
            existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(events)").fetchall()]
            has_job_id = 'job_id' in existing_columns
            
            # Função auxiliar para calcular estatísticas de um período
            def calcular_estatisticas_periodo(inicio, fim, tipo_ref=None, referencia=None):
                where_clause = "WHERE date(date) >= date(?) AND date(date) <= date(?)"
                params = [inicio, fim]
                
                if tipo_ref == "usuario" and referencia:
                    where_clause += " AND user = ?"
                    params.append(referencia)
                elif tipo_ref == "setor" and referencia:
                    where_clause += " AND user IN (SELECT user FROM users WHERE sector = ?)"
                    params.append(referencia)
                elif tipo_ref == "impressora" and referencia:
                    where_clause += " AND printer_name = ?"
                    params.append(referencia)
                
                # Busca eventos agrupados por job
                if has_job_id:
                    query = f"""
                        SELECT 
                            MAX(pages_printed) as pages,
                            MAX(COALESCE(duplex, 0)) as duplex,
                            MAX(COALESCE(copies, 1)) as copies,
                            MAX(user) as user
                        FROM events
                        {where_clause}
                        GROUP BY CASE 
                            WHEN job_id IS NOT NULL AND job_id != '' THEN 
                                job_id || '|' || COALESCE(printer_name, '') || '|' || date
                            ELSE 
                                user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
                        END
                    """
                else:
                    query = f"""
                        SELECT 
                            MAX(pages_printed) as pages,
                            MAX(COALESCE(duplex, 0)) as duplex,
                            MAX(COALESCE(copies, 1)) as copies,
                            MAX(user) as user
                        FROM events
                        {where_clause}
                        GROUP BY user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
                    """
                
                rows = conn.execute(query, params).fetchall()
                
                total_impressos = len(rows)
                total_paginas = 0
                usuarios = set()
                
                for row in rows:
                    pages = row[0] or 0
                    duplex = row[1]
                    copies = row[2] or 1
                    user = row[3]
                    
                    total_paginas += calcular_folhas_fisicas(pages, duplex, copies)
                    if user:
                        usuarios.add(user)
                
                return total_impressos, total_paginas, len(usuarios)
            
            # Calcula estatísticas para ambos os períodos
            periodo1_stats = calcular_estatisticas_periodo(
                periodo1_inicio, periodo1_fim, 
                tipo if tipo != "geral" else None, 
                data.get("referencia") if tipo != "geral" else None
            )
            periodo2_stats = calcular_estatisticas_periodo(
                periodo2_inicio, periodo2_fim,
                tipo if tipo != "geral" else None,
                data.get("referencia") if tipo != "geral" else None
            )
            
            # Calcula diferenças
            diff_impressos = periodo2_stats[0] - periodo1_stats[0]
            diff_paginas = periodo2_stats[1] - periodo1_stats[1]
            diff_usuarios = periodo2_stats[2] - periodo1_stats[2]
            
            # Percentuais
            pct_impressos = ((diff_impressos / periodo1_stats[0] * 100) if periodo1_stats[0] > 0 else 0)
            pct_paginas = ((diff_paginas / periodo1_stats[1] * 100) if periodo1_stats[1] > 0 else 0)
            pct_usuarios = ((diff_usuarios / periodo1_stats[2] * 100) if periodo1_stats[2] > 0 else 0)
            
            return jsonify({
                "periodo1": {
                    "inicio": periodo1_inicio,
                    "fim": periodo1_fim,
                    "total_impressos": periodo1_stats[0],
                    "total_paginas": periodo1_stats[1],
                    "total_usuarios": periodo1_stats[2]
                },
                "periodo2": {
                    "inicio": periodo2_inicio,
                    "fim": periodo2_fim,
                    "total_impressos": periodo2_stats[0],
                    "total_paginas": periodo2_stats[1],
                    "total_usuarios": periodo2_stats[2]
                },
                "diferenca": {
                    "impressos": diff_impressos,
                    "paginas": diff_paginas,
                    "usuarios": diff_usuarios,
                    "pct_impressos": round(pct_impressos, 2),
                    "pct_paginas": round(pct_paginas, 2),
                    "pct_usuarios": round(pct_usuarios, 2)
                }
            })
    except Exception as e:
        logger.error(f"Erro ao comparar períodos: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/export/custom", methods=["POST"])
@login_required
def api_export_custom():
    """API para exportação customizada de dados - COM VALIDAÇÃO DE SEGURANÇA"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Dados JSON não fornecidos"}), 400
        
        formato = data.get("formato", "csv")  # csv, excel, json
        if formato not in ["csv", "excel", "json"]:
            return jsonify({"error": "Formato inválido. Use: csv, excel ou json"}), 400
        
        tabela = data.get("tabela", "events")
        colunas = data.get("colunas", [])
        filtros = data.get("filtros", {})
        ordenacao = data.get("ordenacao", {})
        
        with get_db() as conn:
            # 🔒 VALIDAÇÃO 1: Nome da tabela (whitelist)
            if not validar_nome_tabela(tabela):
                logger.warning(f"⚠️ Tentativa de acesso a tabela não permitida: {tabela}")
                return jsonify({
                    "error": "Tabela não permitida",
                    "tabelas_permitidas": list(TABELAS_PERMITIDAS)
                }), 400
            
            # 🔒 VALIDAÇÃO 2: Lista de colunas
            if colunas:
                if not isinstance(colunas, list):
                    return jsonify({"error": "Colunas deve ser uma lista"}), 400
                valido, colunas_validas = validar_lista_colunas(colunas, tabela, conn)
                if not valido:
                    logger.warning(f"⚠️ Tentativa de acesso a colunas inválidas na tabela {tabela}")
                    return jsonify({"error": "Uma ou mais colunas são inválidas"}), 400
                colunas_str = ", ".join(colunas_validas)
            else:
                colunas_str = "*"
            
            # Monta query base (SEGURA)
            query = f"SELECT {colunas_str} FROM {tabela} WHERE 1=1"
            params = []
            
            # 🔒 VALIDAÇÃO 3: Filtros (valida campos e operadores)
            if filtros:
                if not isinstance(filtros, dict):
                    return jsonify({"error": "Filtros deve ser um objeto"}), 400
                
                for campo, valor in filtros.items():
                    # Sanitiza nome do campo
                    campo_sanitizado = sanitizar_nome_campo(campo)
                    if not campo_sanitizado:
                        logger.warning(f"⚠️ Nome de campo inválido rejeitado: {campo}")
                        continue
                    
                    # Valida se o campo existe na tabela
                    if not validar_nome_coluna(campo_sanitizado, tabela, conn):
                        logger.warning(f"⚠️ Campo não existe na tabela {tabela}: {campo_sanitizado}")
                        continue
                    
                    if isinstance(valor, dict):
                        operador = valor.get("operador", "=")
                        valor_filtro = valor.get("valor")
                        
                        # 🔒 VALIDAÇÃO 4: Operador SQL (whitelist)
                        if not validar_operador_sql(operador):
                            logger.warning(f"⚠️ Operador SQL não permitido rejeitado: {operador}")
                            continue
                        
                        operador_upper = operador.upper()
                        if operador_upper == "LIKE":
                            query += f" AND {campo_sanitizado} LIKE ?"
                            params.append(f"%{valor_filtro}%")
                        elif operador_upper in [">=", "<=", ">", "<", "=", "!=", "<>"]:
                            query += f" AND {campo_sanitizado} {operador_upper} ?"
                            params.append(valor_filtro)
                        else:
                            # Operador válido mas não suportado nesta implementação
                            logger.warning(f"⚠️ Operador não suportado: {operador_upper}")
                            continue
                    else:
                        # Valor simples, usa operador =
                        query += f" AND {campo_sanitizado} = ?"
                        params.append(valor)
            
            # 🔒 VALIDAÇÃO 5: Ordenação
            if ordenacao:
                if not isinstance(ordenacao, dict):
                    return jsonify({"error": "Ordenação deve ser um objeto"}), 400
                
                campo_ordem = ordenacao.get("campo", "id")
                campo_ordem_sanitizado = sanitizar_nome_campo(campo_ordem)
                
                if campo_ordem_sanitizado and validar_nome_coluna(campo_ordem_sanitizado, tabela, conn):
                    direcao = validar_direcao_ordenacao(ordenacao.get("direcao", "DESC"))
                    query += f" ORDER BY {campo_ordem_sanitizado} {direcao}"
                else:
                    logger.warning(f"⚠️ Campo de ordenação inválido: {campo_ordem}")
                    # Usa ordenação padrão segura
                    query += " ORDER BY id DESC"
            
            # Executa query (AGORA SEGURA)
            try:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(query, params).fetchall()
            except sqlite3.OperationalError as e:
                logger.error(f"❌ Erro ao executar query: {e}")
                return jsonify({"error": "Erro ao executar consulta", "details": str(e)}), 500
            except sqlite3.DatabaseError as e:
                logger.error(f"❌ Erro de banco de dados: {e}")
                return jsonify({"error": "Erro de banco de dados"}), 500
            
            if formato == "json":
                result = [dict(row) for row in rows]
                return jsonify({"data": result})
            
            elif formato == "csv":
                output = io.StringIO()
                import csv
                writer = csv.writer(output)
                
                if rows:
                    # Header
                    writer.writerow([col for col in rows[0].keys()])
                    # Data
                    for row in rows:
                        writer.writerow([row[col] for col in row.keys()])
                
                output.seek(0)
                return send_file(
                    io.BytesIO(output.getvalue().encode('utf-8')),
                    download_name="exportacao_custom.csv",
                    as_attachment=True,
                    mimetype="text/csv"
                )
            
            elif formato == "excel":
                df = pd.DataFrame([dict(row) for row in rows])
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    df.to_excel(writer, index=False, sheet_name="Dados")
                output.seek(0)
                return send_file(
                    output,
                    download_name="exportacao_custom.xlsx",
                    as_attachment=True,
                    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    except Exception as e:
        logger.error(f"Erro ao exportar dados customizados: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/favorites", methods=["GET", "POST", "DELETE"])
@login_required
def api_favorites():
    """API para gerenciar favoritos/atalhos rápidos"""
    usuario = session.get("user", "admin")
    
    if request.method == "GET":
        try:
            with sqlite3.connect(DB) as conn:
                # Cria tabela se não existir
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS favorites (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        usuario TEXT NOT NULL,
                        nome TEXT NOT NULL,
                        url TEXT NOT NULL,
                        icone TEXT,
                        categoria TEXT,
                        ordem INTEGER DEFAULT 0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(usuario, url)
                    )
                """)
                
                favorites = conn.execute(
                    "SELECT id, nome, url, icone, categoria, ordem FROM favorites WHERE usuario = ? ORDER BY ordem, nome",
                    (usuario,)
                ).fetchall()
                
                return jsonify({
                    "favorites": [
                        {
                            "id": f[0],
                            "nome": f[1],
                            "url": f[2],
                            "icone": f[3] or "bi-star",
                            "categoria": f[4] or "Geral",
                            "ordem": f[5]
                        }
                        for f in favorites
                    ]
                })
        except Exception as e:
            logger.error(f"Erro ao buscar favoritos: {e}")
            return jsonify({"error": str(e)}), 500
    
    elif request.method == "POST":
        try:
            data = request.get_json()
            nome = data.get("nome")
            url = data.get("url")
            icone = data.get("icone", "bi-star")
            categoria = data.get("categoria", "Geral")
            
            if not nome or not url:
                return jsonify({"error": "Nome e URL são obrigatórios"}), 400
            
            with sqlite3.connect(DB) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS favorites (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        usuario TEXT NOT NULL,
                        nome TEXT NOT NULL,
                        url TEXT NOT NULL,
                        icone TEXT,
                        categoria TEXT,
                        ordem INTEGER DEFAULT 0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(usuario, url)
                    )
                """)
                
                try:
                    conn.execute(
                        """INSERT INTO favorites (usuario, nome, url, icone, categoria) 
                           VALUES (?, ?, ?, ?, ?)""",
                        (usuario, nome, url, icone, categoria)
                    )
                    conn.commit()
                    return jsonify({"status": "success", "message": "Favorito adicionado"})
                except sqlite3.IntegrityError:
                    return jsonify({"error": "Este favorito já existe"}), 400
        except Exception as e:
            logger.error(f"Erro ao adicionar favorito: {e}")
            return jsonify({"error": str(e)}), 500
    
    elif request.method == "DELETE":
        try:
            favorite_id = request.args.get("id")
            if not favorite_id:
                return jsonify({"error": "ID é obrigatório"}), 400
            
            with sqlite3.connect(DB) as conn:
                conn.execute(
                    "DELETE FROM favorites WHERE id = ? AND usuario = ?",
                    (favorite_id, usuario)
                )
                conn.commit()
                return jsonify({"status": "success", "message": "Favorito removido"})
        except Exception as e:
            logger.error(f"Erro ao remover favorito: {e}")
            return jsonify({"error": str(e)}), 500


@app.route("/api/dashboard/widgets/custom", methods=["GET", "POST", "PUT", "DELETE"])
@login_required
def api_dashboard_widgets_custom():
    """API para widgets personalizáveis do dashboard"""
    usuario = session.get("user", "admin")
    
    if request.method == "GET":
        try:
            with sqlite3.connect(DB) as conn:
                # Cria tabela se não existir
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS dashboard_widgets_custom (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        usuario TEXT NOT NULL,
                        tipo TEXT NOT NULL,
                        titulo TEXT NOT NULL,
                        configuracao TEXT,
                        posicao_x INTEGER DEFAULT 0,
                        posicao_y INTEGER DEFAULT 0,
                        largura INTEGER DEFAULT 4,
                        altura INTEGER DEFAULT 3,
                        ativo INTEGER DEFAULT 1,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                widgets = conn.execute(
                    """SELECT id, tipo, titulo, configuracao, posicao_x, posicao_y, largura, altura, ativo
                       FROM dashboard_widgets_custom 
                       WHERE usuario = ? AND ativo = 1
                       ORDER BY posicao_y, posicao_x""",
                    (usuario,)
                ).fetchall()
                
                result = []
                for w in widgets:
                    import json
                    config = json.loads(w[3]) if w[3] else {}
                    result.append({
                        "id": w[0],
                        "tipo": w[1],
                        "titulo": w[2],
                        "configuracao": config,
                        "posicao": {"x": w[4], "y": w[5]},
                        "tamanho": {"largura": w[6], "altura": w[7]},
                        "ativo": bool(w[8])
                    })
                
                return jsonify({"widgets": result})
        except Exception as e:
            logger.error(f"Erro ao buscar widgets: {e}")
            return jsonify({"error": str(e)}), 500
    
    elif request.method == "POST":
        try:
            data = request.get_json()
            tipo = data.get("tipo")
            titulo = data.get("titulo")
            configuracao = data.get("configuracao", {})
            
            if not tipo or not titulo:
                return jsonify({"error": "Tipo e título são obrigatórios"}), 400
            
            with sqlite3.connect(DB) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS dashboard_widgets_custom (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        usuario TEXT NOT NULL,
                        tipo TEXT NOT NULL,
                        titulo TEXT NOT NULL,
                        configuracao TEXT,
                        posicao_x INTEGER DEFAULT 0,
                        posicao_y INTEGER DEFAULT 0,
                        largura INTEGER DEFAULT 4,
                        altura INTEGER DEFAULT 3,
                        ativo INTEGER DEFAULT 1,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                import json
                conn.execute(
                    """INSERT INTO dashboard_widgets_custom 
                       (usuario, tipo, titulo, configuracao, posicao_x, posicao_y, largura, altura)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (usuario, tipo, titulo, json.dumps(configuracao), 
                     data.get("posicao_x", 0), data.get("posicao_y", 0),
                     data.get("largura", 4), data.get("altura", 3))
                )
                conn.commit()
                return jsonify({"status": "success", "message": "Widget criado"})
        except Exception as e:
            logger.error(f"Erro ao criar widget: {e}")
            return jsonify({"error": str(e)}), 500
    
    elif request.method == "PUT":
        try:
            data = request.get_json()
            widget_id = data.get("id")
            
            if not widget_id:
                return jsonify({"error": "ID é obrigatório"}), 400
            
            with sqlite3.connect(DB) as conn:
                updates = []
                params = []
                
                if "configuracao" in data:
                    import json
                    updates.append("configuracao = ?")
                    params.append(json.dumps(data["configuracao"]))
                if "posicao_x" in data:
                    updates.append("posicao_x = ?")
                    params.append(data["posicao_x"])
                if "posicao_y" in data:
                    updates.append("posicao_y = ?")
                    params.append(data["posicao_y"])
                if "largura" in data:
                    updates.append("largura = ?")
                    params.append(data["largura"])
                if "altura" in data:
                    updates.append("altura = ?")
                    params.append(data["altura"])
                if "titulo" in data:
                    updates.append("titulo = ?")
                    params.append(data["titulo"])
                if "ativo" in data:
                    updates.append("ativo = ?")
                    params.append(1 if data["ativo"] else 0)
                
                if updates:
                    params.append(widget_id)
                    params.append(usuario)
                    conn.execute(
                        f"UPDATE dashboard_widgets_custom SET {', '.join(updates)} WHERE id = ? AND usuario = ?",
                        params
                    )
                    conn.commit()
                    return jsonify({"status": "success", "message": "Widget atualizado"})
                else:
                    return jsonify({"error": "Nenhum campo para atualizar"}), 400
        except Exception as e:
            logger.error(f"Erro ao atualizar widget: {e}")
            return jsonify({"error": str(e)}), 500
    
    elif request.method == "DELETE":
        try:
            widget_id = request.args.get("id")
            if not widget_id:
                return jsonify({"error": "ID é obrigatório"}), 400
            
            with sqlite3.connect(DB) as conn:
                conn.execute(
                    "UPDATE dashboard_widgets_custom SET ativo = 0 WHERE id = ? AND usuario = ?",
                    (widget_id, usuario)
                )
                conn.commit()
                return jsonify({"status": "success", "message": "Widget removido"})
        except Exception as e:
            logger.error(f"Erro ao remover widget: {e}")
            return jsonify({"error": str(e)}), 500


@app.route("/api/admin/acoes", methods=["POST"])
@login_required
@admin_required
def api_admin_acoes():
    """API para ações administrativas rápidas"""
    try:
        data = request.get_json()
        acao = data.get("acao")
        
        if acao == "limpar_cache":
            # Limpar cache (se houver sistema de cache)
            return jsonify({"status": "success", "message": "Cache limpo"})
        
        elif acao == "otimizar_db":
            with sqlite3.connect(DB) as conn:
                conn.execute("VACUUM")
                conn.execute("ANALYZE")
                conn.commit()
            return jsonify({"status": "success", "message": "Banco de dados otimizado"})
        
        else:
            return jsonify({"error": "Ação não reconhecida"}), 400
            
    except Exception as e:
        logger.error(f"Erro ao executar ação administrativa: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/analytics/insights", methods=["GET"])
@login_required
def api_analytics_insights():
    """API para insights e análises avançadas"""
    try:
        dias = int(request.args.get("dias", 30))
        
        with sqlite3.connect(DB) as conn:
            # Padrões de uso
            horario_pico = conn.execute("""
                SELECT strftime('%H', date || ' ' || substr(created_at, 12, 8)) as hora,
                       COUNT(*) as total
                FROM events
                WHERE date(date) >= date('now', '-' || ? || ' days')
                GROUP BY hora
                ORDER BY total DESC
                LIMIT 1
            """, (dias,)).fetchone()
            
            # Dia da semana mais usado
            dia_semana_pico = conn.execute("""
                SELECT strftime('%w', date) as dia_semana,
                       COUNT(*) as total
                FROM events
                WHERE date(date) >= date('now', '-' || ? || ' days')
                GROUP BY dia_semana
                ORDER BY total DESC
                LIMIT 1
            """, (dias,)).fetchone()
            
            # Usuário mais ativo
            usuario_mais_ativo = conn.execute("""
                SELECT user, COUNT(*) as total
                FROM events
                WHERE date(date) >= date('now', '-' || ? || ' days')
                GROUP BY user
                ORDER BY total DESC
                LIMIT 1
            """, (dias,)).fetchone()
            
            # Impressora mais usada
            impressora_mais_usada = conn.execute("""
                SELECT printer_name, COUNT(*) as total
                FROM events
                WHERE date(date) >= date('now', '-' || ? || ' days')
                AND printer_name IS NOT NULL
                GROUP BY printer_name
                ORDER BY total DESC
                LIMIT 1
            """, (dias,)).fetchone()
            
            # Tendência (últimos 7 dias)
            tendencia_7dias = []
            for i in range(7):
                dia = (datetime.now() - timedelta(days=i)).date()
                count = conn.execute(
                    "SELECT COUNT(*) FROM events WHERE date(date) = date(?)",
                    (dia.isoformat(),)
                ).fetchone()[0]
                tendencia_7dias.insert(0, {
                    'dia': dia.strftime('%Y-%m-%d'),
                    'total': count
                })
            
            # Economia potencial (duplex) - calcula folhas físicas corretamente
            existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(events)").fetchall()]
            has_job_id = 'job_id' in existing_columns
            
            if has_job_id:
                rows = conn.execute("""
                    SELECT 
                        MAX(pages_printed) as pages,
                        MAX(COALESCE(duplex, 0)) as duplex,
                        MAX(COALESCE(copies, 1)) as copies
                    FROM events
                    WHERE date(date) >= date('now', '-' || ? || ' days')
                    AND (duplex = 0 OR duplex IS NULL)
                    GROUP BY CASE 
                        WHEN job_id IS NOT NULL AND job_id != '' THEN 
                            job_id || '|' || COALESCE(printer_name, '') || '|' || date
                        ELSE 
                            user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
                    END
                """, (dias,)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT 
                        MAX(pages_printed) as pages,
                        MAX(COALESCE(duplex, 0)) as duplex,
                        MAX(COALESCE(copies, 1)) as copies
                    FROM events
                    WHERE date(date) >= date('now', '-' || ? || ' days')
                    AND (duplex = 0 OR duplex IS NULL)
                    GROUP BY user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
                """, (dias,)).fetchall()
            
            economia_potencial = 0
            for row in rows:
                pages = row[0] or 0
                duplex = row[1]
                copies = row[2] or 1
                economia_potencial += calcular_folhas_fisicas(pages, duplex, copies)
            
            economia_estimada = economia_potencial * 0.5  # 50% de economia com duplex
            
            return jsonify({
                "horario_pico": {
                    "hora": horario_pico[0] if horario_pico else None,
                    "total": horario_pico[1] if horario_pico else 0
                },
                "dia_semana_pico": {
                    "dia": dia_semana_pico[0] if dia_semana_pico else None,
                    "total": dia_semana_pico[1] if dia_semana_pico else 0
                },
                "usuario_mais_ativo": {
                    "user": usuario_mais_ativo[0] if usuario_mais_ativo else None,
                    "total": usuario_mais_ativo[1] if usuario_mais_ativo else 0
                },
                "impressora_mais_usada": {
                    "printer": impressora_mais_usada[0] if impressora_mais_usada else None,
                    "total": impressora_mais_usada[1] if impressora_mais_usada else 0
                },
                "tendencia_7dias": tendencia_7dias,
                "economia_potencial": {
                    "paginas_simplex": economia_potencial,
                    "economia_estimada_paginas": round(economia_estimada, 0)
                }
            })
    except Exception as e:
        logger.error(f"Erro ao obter insights: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/quick-stats", methods=["GET"])
@login_required
def api_quick_stats():
    """API para estatísticas rápidas (otimizada)"""
    try:
        periodo = request.args.get("periodo", "hoje")  # hoje, semana, mes, ano
        
        with sqlite3.connect(DB) as conn:
            if periodo == "hoje":
                date_filter = "date(date) = date('now')"
            elif periodo == "semana":
                date_filter = "date(date) >= date('now', '-7 days')"
            elif periodo == "mes":
                date_filter = "date(date) >= date('now', '-30 days')"
            else:  # ano
                date_filter = "date(date) >= date('now', '-365 days')"
            
            # Estatísticas básicas - conta jobs únicos, não eventos
            total_impressos = contar_jobs_unicos(conn, f"WHERE {date_filter}")
            total_usuarios = conn.execute(f"SELECT COUNT(DISTINCT user) FROM events WHERE {date_filter}").fetchone()[0]
            total_impressoras = conn.execute(f"SELECT COUNT(DISTINCT printer_name) FROM events WHERE {date_filter} AND printer_name IS NOT NULL").fetchone()[0]
            
            # Calcula páginas físicas agrupando por job primeiro (evita duplicação)
            existing_columns = [col[1] for col in conn.execute("PRAGMA table_info(events)").fetchall()]
            has_job_id = 'job_id' in existing_columns
            
            if has_job_id:
                rows = conn.execute(f"""
                    SELECT 
                        MAX(pages_printed) as pages,
                        MAX(duplex) as duplex,
                        MAX(COALESCE(copies, 1)) as copies,
                        MAX(printer_name) as printer_name
                    FROM events
                    WHERE {date_filter}
                    GROUP BY CASE 
                        WHEN job_id IS NOT NULL AND job_id != '' THEN 
                            job_id || '|' || COALESCE(printer_name, '') || '|' || date
                        ELSE 
                            user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date
                    END"""
                ).fetchall()
            else:
                rows = conn.execute(f"""
                    SELECT 
                        MAX(pages_printed) as pages,
                        MAX(duplex) as duplex,
                        MAX(COALESCE(copies, 1)) as copies,
                        MAX(printer_name) as printer_name
                    FROM events
                    WHERE {date_filter}
                    GROUP BY user || '|' || machine || '|' || COALESCE(document, '') || '|' || COALESCE(printer_name, '') || '|' || date"""
                ).fetchall()
            
            total_paginas = 0
            for row in rows:
                pages = row[0] or 0
                duplex_evento = row[1] if len(row) > 1 else None
                copies = row[2] if len(row) > 2 else 1
                printer_name = row[3] if len(row) > 3 else None
                
                # Obtém duplex baseado no tipo da impressora cadastrada
                duplex = obter_duplex_da_impressora(conn, printer_name, duplex_evento)
                
                total_paginas += calcular_folhas_fisicas(pages, duplex, copies)
            
            # Modo de cor
            color_stats = conn.execute(f"""
                SELECT 
                    color_mode,
                    COUNT(*) as total
                FROM events
                WHERE {date_filter} AND color_mode IS NOT NULL
                GROUP BY color_mode
            """).fetchall()
            
            return jsonify({
                "periodo": periodo,
                "total_impressos": total_impressos,
                "total_usuarios": total_usuarios,
                "total_impressoras": total_impressoras,
                "total_paginas": total_paginas,
                "color_mode": {
                    c[0]: c[1] for c in color_stats
                },
                "timestamp": datetime.now().isoformat()
            })
    except Exception as e:
        logger.error(f"Erro ao obter quick stats: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/status")
@login_required
def status_sistema():
    """Página de status do sistema com informações detalhadas"""
    try:
        import psutil
        PSUTIL_AVAILABLE = True
    except ImportError:
        PSUTIL_AVAILABLE = False
        logger.warning("psutil não instalado. Algumas métricas de sistema não estarão disponíveis.")
    
    import platform
    
    # Informações do sistema
    if PSUTIL_AVAILABLE:
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            uptime_seconds = (datetime.now() - datetime.fromtimestamp(psutil.boot_time())).total_seconds()
            uptime_days = int(uptime_seconds // 86400)
            uptime_hours = int((uptime_seconds % 86400) // 3600)
        except Exception as e:
            logger.warning(f"Erro ao obter métricas do sistema: {e}")
            cpu_percent = 0
            memory = type('obj', (object,), {'percent': 0, 'total': 0, 'available': 0})()
            disk = type('obj', (object,), {'percent': 0, 'total': 0, 'free': 0})()
            uptime_days = 0
            uptime_hours = 0
    else:
        cpu_percent = 0
        memory = type('obj', (object,), {'percent': 0, 'total': 0, 'available': 0})()
        disk = type('obj', (object,), {'percent': 0, 'total': 0, 'free': 0})()
        uptime_days = 0
        uptime_hours = 0
    
    # Status do banco
    db_info = {}
    try:
        with sqlite3.connect(DB) as conn:
            # Tamanho do banco
            db_size = os.path.getsize(DB) / (1024 * 1024)  # MB
            
            # Contagem de registros
            total_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            total_users = conn.execute("SELECT COUNT(DISTINCT user) FROM events").fetchone()[0]
            total_printers = conn.execute("SELECT COUNT(DISTINCT printer_name) FROM events").fetchone()[0]
            
            # Último evento (inclui duplex)
            ultimo_evento = conn.execute(
                "SELECT date, user, printer_name, duplex FROM events ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            
            # Obtém duplex baseado no tipo da impressora cadastrada
            duplex_ultimo = None
            if ultimo_evento and ultimo_evento[2]:  # Se tem printer_name
                duplex_evento = ultimo_evento[3] if len(ultimo_evento) > 3 else None
                duplex_ultimo = obter_duplex_da_impressora(conn, ultimo_evento[2], duplex_evento)
            
            db_info = {
                "size_mb": round(db_size, 2),
                "total_events": total_events,
                "total_users": total_users,
                "total_printers": total_printers,
                "ultimo_evento": {
                    "date": ultimo_evento[0] if ultimo_evento else None,
                    "user": ultimo_evento[1] if ultimo_evento else None,
                    "printer": ultimo_evento[2] if ultimo_evento else None,
                    "duplex": duplex_ultimo
                } if ultimo_evento else None
            }
    except Exception as e:
        db_info = {"error": str(e)}
    
    # Estatísticas de uso
    stats = {
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "memory_total_gb": round(memory.total / (1024**3), 2),
        "memory_available_gb": round(memory.available / (1024**3), 2),
        "disk_percent": disk.percent,
        "disk_total_gb": round(disk.total / (1024**3), 2),
        "disk_free_gb": round(disk.free / (1024**3), 2),
        "uptime": f"{uptime_days} dias, {uptime_hours} horas",
        "platform": platform.system(),
        "python_version": platform.python_version()
    }
    
    return render_template("status_sistema.html", 
                         db_info=db_info, 
                         stats=stats,
                         features={
                             "rate_limiting": RATE_LIMIT_ENABLED,
                             "csrf": CSRF_ENABLED,
                             "compression": COMPRESS_ENABLED,
                             "pdf_export": PDF_EXPORT_AVAILABLE,
                             "modules": MODULOS_DISPONIVEIS
                         })


# ============================================================================
# WEBSOCKET - EVENTOS EM TEMPO REAL
# ============================================================================

# Contador de clientes conectados
_websocket_clients = 0

if SOCKETIO_AVAILABLE and socketio:
    
    @socketio.on('connect')
    def handle_connect():
        """Cliente conectou via WebSocket"""
        global _websocket_clients
        _websocket_clients += 1
        logger.info(f"🔌 WebSocket: Cliente conectado (total: {_websocket_clients})")
        emit('connected', {
            'status': 'ok',
            'message': 'Conectado ao servidor em tempo real',
            'clients': _websocket_clients
        })
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Cliente desconectou"""
        global _websocket_clients
        _websocket_clients = max(0, _websocket_clients - 1)
        logger.info(f"🔌 WebSocket: Cliente desconectou (restam: {_websocket_clients})")
    
    @socketio.on('subscribe_dashboard')
    def handle_subscribe_dashboard():
        """Cliente se inscreve para receber atualizações do dashboard"""
        join_room('dashboard')
        logger.debug("Cliente inscrito no room 'dashboard'")
        emit('subscribed', {'room': 'dashboard'})
    
    @socketio.on('unsubscribe_dashboard')
    def handle_unsubscribe_dashboard():
        """Cliente cancela inscrição do dashboard"""
        leave_room('dashboard')
        logger.debug("Cliente saiu do room 'dashboard'")
    
    @socketio.on('ping')
    def handle_ping():
        """Responde a ping do cliente (keep-alive)"""
        emit('pong', {'time': datetime.now().isoformat()})


def broadcast_new_event(event_data: dict):
    """
    Emite um novo evento de impressão para todos os clientes conectados.
    
    Args:
        event_data: Dados do evento de impressão
    """
    if SOCKETIO_AVAILABLE and socketio:
        try:
            # Emite para o room 'dashboard'
            socketio.emit('new_print_event', {
                'event': event_data,
                'timestamp': datetime.now().isoformat()
            }, room='dashboard')
            
            # Também emite estatísticas atualizadas
            with sqlite3.connect(DB) as conn:
                # Total de impressões hoje
                hoje = datetime.now().strftime('%Y-%m-%d')
                stats = conn.execute("""
                    SELECT 
                        COUNT(*) as total_hoje,
                        COALESCE(SUM(pages_printed), 0) as paginas_hoje,
                        COALESCE(SUM(sheets_used), SUM(pages_printed)) as folhas_hoje
                    FROM events
                    WHERE date(date) = date(?)
                """, (hoje,)).fetchone()
                
                socketio.emit('stats_update', {
                    'total_hoje': stats[0] or 0,
                    'paginas_hoje': stats[1] or 0,
                    'folhas_hoje': stats[2] or 0,
                    'timestamp': datetime.now().isoformat()
                }, room='dashboard')
                
        except Exception as e:
            logger.error(f"Erro ao emitir evento WebSocket: {e}")


def broadcast_stats_update():
    """Emite estatísticas atualizadas para todos os clientes."""
    if SOCKETIO_AVAILABLE and socketio:
        try:
            with sqlite3.connect(DB) as conn:
                hoje = datetime.now().strftime('%Y-%m-%d')
                stats = conn.execute("""
                    SELECT 
                        COUNT(*) as total_hoje,
                        COALESCE(SUM(pages_printed), 0) as paginas_hoje,
                        COALESCE(SUM(sheets_used), SUM(pages_printed)) as folhas_hoje,
                        COUNT(DISTINCT user) as usuarios_ativos
                    FROM events
                    WHERE date(date) = date(?)
                """, (hoje,)).fetchone()
                
                socketio.emit('stats_update', {
                    'total_hoje': stats[0] or 0,
                    'paginas_hoje': stats[1] or 0,
                    'folhas_hoje': stats[2] or 0,
                    'usuarios_ativos': stats[3] or 0,
                    'timestamp': datetime.now().isoformat()
                }, room='dashboard')
                
        except Exception as e:
            logger.error(f"Erro ao emitir stats WebSocket: {e}")


# ============================================================================
# INICIALIZAÇÃO
# ============================================================================

if __name__ == "__main__":
    try:
        init_db()
        logger.info("Banco de dados inicializado")
        
        # Inicializa connection pool se disponível
        # Verifica se connection pool está disponível
        try:
            from modules.db_pool import get_db_pool
            pool = get_db_pool()
            DB_POOL_AVAILABLE = pool is not None
        except (ImportError, AttributeError):
            DB_POOL_AVAILABLE = False
        
        if DB_POOL_AVAILABLE:
            try:
                init_db_pool(
                    DB,
                    max_connections=int(os.getenv('DB_POOL_MAX_CONNECTIONS', 10)),
                    timeout=float(os.getenv('DB_POOL_TIMEOUT', 5.0)),
                    max_retries=int(os.getenv('DB_POOL_MAX_RETRIES', 3)),
                    retry_delay=float(os.getenv('DB_POOL_RETRY_DELAY', 0.5))
                )
                logger.info("✅ Connection pool inicializado")
            except Exception as e:
                logger.error(f"❌ Erro ao inicializar connection pool: {e}")
                DB_POOL_AVAILABLE = False
        
        # Inicia threads de background
        if MODULOS_DISPONIVEIS:
            # Thread de relatórios agendados
            relatorios_agendados.iniciar_thread_relatorios(DB)
            
            # Thread de backup automático
            backup.iniciar_backup_automatico(DB, intervalo_horas=24)
            
            # Thread de verificação de alertas
            def verificar_alertas_loop():
                import time
                while True:
                    try:
                        with sqlite3.connect(DB) as conn:
                            alertas.verificar_alertas_automaticos(conn)
                            # Sistema de comodatos removido
                    except Exception as e:
                        logger.error(f"Erro ao verificar alertas: {e}")
                    time.sleep(300)  # A cada 5 minutos
            
            threading.Thread(target=verificar_alertas_loop, daemon=True).start()
            
            # Limpa cache expirado periodicamente
            def limpar_cache_loop():
                import time
                while True:
                    try:
                        with sqlite3.connect(DB) as conn:
                            cache.limpar_cache_expirado(conn)
                    except Exception as e:
                        logger.error(f"Erro ao limpar cache: {e}")
                    time.sleep(3600)  # A cada hora
            
            threading.Thread(target=limpar_cache_loop, daemon=True).start()
            
            # Limpa tokens de reset expirados periodicamente
            def limpar_tokens_expirados_loop():
                import time
                from datetime import datetime
                while True:
                    try:
                        with sqlite3.connect(DB) as conn:
                            agora = datetime.now().isoformat()
                            # Remove tokens expirados e já usados (mais de 7 dias)
                            conn.execute(
                                """DELETE FROM password_reset_tokens 
                                WHERE (expires_at < ? AND used = 1) 
                                OR (expires_at < ? AND used = 0)""",
                                (agora, agora)
                            )
                            deleted = conn.rowcount
                            if deleted > 0:
                                logger.info(f"Limpeza: {deleted} token(s) de reset expirado(s) removido(s)")
                            conn.commit()
                    except Exception as e:
                        logger.error(f"Erro ao limpar tokens expirados: {e}")
                    time.sleep(3600)  # A cada hora
            
            threading.Thread(target=limpar_tokens_expirados_loop, daemon=True).start()
        
        logger.info("Servidor iniciado")
        logger.info(f"Rate Limiting: {'Habilitado' if RATE_LIMIT_ENABLED else 'Desabilitado'}")
        logger.info(f"CSRF Protection: {'Habilitado' if CSRF_ENABLED else 'Desabilitado'}")
        logger.info(f"Compressão HTTP: {'Habilitada' if COMPRESS_ENABLED else 'Desabilitada'}")
        logger.info(f"PDF Export: {'Disponível' if PDF_EXPORT_AVAILABLE else 'Indisponível'}")
        logger.info(f"WebSocket: {'Habilitado' if SOCKETIO_AVAILABLE else 'Desabilitado'}")
        logger.info(f"Sessões seguras: HTTPOnly={app.config['SESSION_COOKIE_HTTPONLY']}, SameSite={app.config['SESSION_COOKIE_SAMESITE']}")
        
        host = os.getenv('HOST', '0.0.0.0')
        port = int(os.getenv('PORT', 5002))
        debug = os.getenv('DEBUG', 'False').lower() == 'true'
        logger.info(f"Iniciando servidor na porta {port}")
        
        # Usa SocketIO se disponível para WebSocket
        if SOCKETIO_AVAILABLE and socketio:
            logger.info("🔌 Iniciando com suporte a WebSocket...")
            socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
        else:
            app.run(host=host, port=port, debug=debug)
    except Exception as e:
        logger.critical(f"Erro ao iniciar servidor: {e}", exc_info=True)
        raise
