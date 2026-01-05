"""
Script para recriar o banco de dados do zero
Deleta o banco antigo e cria todas as tabelas com a estrutura completa
"""
import sqlite3
import os
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_PATH = "print_events.db"

def recreate_database():
    """Recria o banco de dados do zero"""
    
    # 1. Faz backup do banco antigo (se existir)
    backup_path = f"{DB_PATH}.backup"
    if os.path.exists(DB_PATH):
        try:
            import shutil
            shutil.copy2(DB_PATH, backup_path)
            logger.info(f"[OK] Backup criado: {backup_path}")
        except Exception as e:
            logger.warning(f"[AVISO] Nao foi possivel criar backup: {e}")
    
    # 2. Remove o banco antigo
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            logger.info(f"[OK] Banco antigo removido: {DB_PATH}")
        except Exception as e:
            logger.error(f"[ERRO] Erro ao remover banco antigo: {e}")
            return False
    
    # 3. Cria o banco novo
    logger.info("[OK] Criando novo banco de dados...")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # ========================================================================
        # TABELA: events (Eventos de impressao)
        # ========================================================================
        logger.info("[OK] Criando tabela 'events'...")
        cursor.execute("""
            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                user TEXT NOT NULL,
                machine TEXT NOT NULL,
                pages_printed INTEGER DEFAULT 1,
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
                sheets_used INTEGER,
                copies INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Índices para performance
        cursor.execute("""
            CREATE UNIQUE INDEX idx_events_record_number ON events(record_number)
        """)
        cursor.execute("""
            CREATE INDEX idx_events_date_user ON events(date, user)
        """)
        cursor.execute("""
            CREATE INDEX idx_events_date ON events(date)
        """)
        cursor.execute("""
            CREATE INDEX idx_events_user ON events(user)
        """)
        cursor.execute("""
            CREATE INDEX idx_events_printer_name ON events(printer_name)
        """)
        logger.info("[OK] Tabela 'events' criada com sucesso")
        
        # ========================================================================
        # TABELA: users (Usuários e setores)
        # ========================================================================
        logger.info("[OK] Criando tabela 'users'...")
        cursor.execute("""
            CREATE TABLE users (
                user TEXT PRIMARY KEY,
                sector TEXT
            )
        """)
        logger.info("[OK] Tabela 'users' criada com sucesso")
        
        # ========================================================================
        # TABELA: precos (Preços históricos)
        # ========================================================================
        logger.info("[OK] Criando tabela 'precos'...")
        cursor.execute("""
            CREATE TABLE precos (
                data_inicio TEXT PRIMARY KEY,
                valor REAL NOT NULL
            )
        """)
        logger.info("[OK] Tabela 'precos' criada com sucesso")
        
        # ========================================================================
        # TABELA: materiais (Materiais de impressão)
        # ========================================================================
        logger.info("[OK] Criando tabela 'materiais'...")
        cursor.execute("""
            CREATE TABLE materiais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                preco REAL NOT NULL,
                rendimento INTEGER NOT NULL,
                valor REAL,
                data_inicio TEXT NOT NULL
            )
        """)
        logger.info("[OK] Tabela 'materiais' criada com sucesso")
        
        # ========================================================================
        # TABELA: login (Usuários do sistema)
        # ========================================================================
        logger.info("[OK] Criando tabela 'login'...")
        cursor.execute("""
            CREATE TABLE login (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0
            )
        """)
        logger.info("[OK] Tabela 'login' criada com sucesso")
        
        # ========================================================================
        # TABELA: config (Configurações do sistema)
        # ========================================================================
        logger.info("[OK] Criando tabela 'config'...")
        cursor.execute("""
            CREATE TABLE config (
                chave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            )
        """)
        logger.info("[OK] Tabela 'config' criada com sucesso")
        
        # ========================================================================
        # DADOS INICIAIS
        # ========================================================================
        logger.info("[OK] Inserindo dados iniciais...")
        
        # Admin padrão
        cursor.execute("""
            INSERT INTO login (username, password, is_admin) 
            VALUES ('admin', '123', 1)
        """)
        logger.info("[OK] Usuario admin criado (username: admin, password: 123)")
        
        # Configurações padrão
        default_configs = [
            ('color_multiplier', '2.0'),
            ('color_alert_threshold', '50'),
            ('color_alert_enabled', '1')
        ]
        for chave, valor in default_configs:
            cursor.execute("""
                INSERT INTO config (chave, valor) VALUES (?, ?)
            """, (chave, valor))
        logger.info("[OK] Configuracoes padrao inseridas")
        
        # Commit
        conn.commit()
        conn.close()
        
        logger.info("=" * 80)
        logger.info("[OK] BANCO DE DADOS RECRIADO COM SUCESSO!")
        logger.info("=" * 80)
        logger.info("")
        logger.info("[OK] Estrutura criada:")
        logger.info("  [OK] events - Eventos de impressao (com todas as colunas)")
        logger.info("  [OK] users - Usuarios e setores")
        logger.info("  [OK] precos - Precos historicos")
        logger.info("  [OK] materiais - Materiais de impressao")
        logger.info("  [OK] login - Usuarios do sistema")
        logger.info("  [OK] config - Configuracoes do sistema")
        logger.info("")
        logger.info("[OK] Credenciais padrao:")
        logger.info("  Username: admin")
        logger.info("  Password: 123")
        logger.info("")
        logger.info("[OK] Indices criados:")
        logger.info("  [OK] idx_events_record_number (UNIQUE)")
        logger.info("  [OK] idx_events_date_user")
        logger.info("  [OK] idx_events_date")
        logger.info("  [OK] idx_events_user")
        logger.info("  [OK] idx_events_printer_name")
        logger.info("")
        
        return True
        
    except Exception as e:
        logger.error(f"[ERRO] Erro ao criar banco de dados: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("RECRIACAO DO BANCO DE DADOS")
    print("=" * 80)
    print()
    print("[ATENCAO] Este script vai:")
    print("  1. Fazer backup do banco atual (se existir)")
    print("  2. DELETAR o banco atual")
    print("  3. Criar um novo banco do zero")
    print()
    
    resposta = input("Deseja continuar? (sim/nao): ").strip().lower()
    
    if resposta in ['sim', 's', 'yes', 'y']:
        print()
        if recreate_database():
            print()
            print("[OK] Processo concluido com sucesso!")
        else:
            print()
            print("[ERRO] Erro ao recriar banco de dados")
    else:
        print()
        print("[CANCELADO] Operacao cancelada")

