"""
Interface Gráfica Melhorada para Instalação do Agente de Monitoramento
Versão 2.0 - Design Moderno com Ferramentas Avançadas
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import subprocess
import os
import sys
from pathlib import Path
import json
from datetime import datetime
import csv
from collections import defaultdict

class AgentInstallerGUIMelhorado:
    def __init__(self, root):
        self.root = root
        self.root.title("Instalador do Agente de Monitoramento - v2.0 Pro")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)
        
        # Configura tema moderno
        self.setup_modern_theme()
        
        # Variáveis
        self.computers = []
        self.network_computers = {}
        self.computer_groups = {}  # Grupos de computadores
        self.operation_history = []  # Histórico de operações
        self.is_installing = False
        self.is_scanning = False
        self.agent_path = Path(__file__).parent.absolute()
        self.stats = {
            'total': 0,
            'online': 0,
            'offline': 0,
            'installed': 0,
            'not_installed': 0
        }
        
        # Configurações
        self.scan_config = {
            'use_ad': True,
            'use_netview': True,
            'use_wmi': True,
            'use_ping_scan': True,
            'ping_scan_range': '0.1-1.254',
            'ping_scan_subnet': None,
            'server_ip': '192.168.0.13',
            'subnet_mask': '255.255.254.0'
        }
        
        # Cria interface
        self.create_widgets()
        self.load_settings()
        
        # Atalhos de teclado
        self.setup_keyboard_shortcuts()
    
    def setup_modern_theme(self):
        """Configura tema moderno"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Cores modernas
        self.colors = {
            'primary': '#0078d4',
            'success': '#107c10',
            'error': '#d13438',
            'warning': '#ffaa44',
            'info': '#0078d4',
            'bg': '#f3f3f3',
            'fg': '#323130',
            'border': '#e1dfdd'
        }
        
        # Configura estilos
        style.configure('Title.TLabel', font=('Segoe UI', 16, 'bold'), foreground=self.colors['primary'])
        style.configure('Heading.TLabel', font=('Segoe UI', 11, 'bold'))
        style.configure('Accent.TButton', font=('Segoe UI', 9, 'bold'))
        style.configure('Success.TLabel', foreground=self.colors['success'])
        style.configure('Error.TLabel', foreground=self.colors['error'])
        style.configure('Warning.TLabel', foreground=self.colors['warning'])
    
    def setup_keyboard_shortcuts(self):
        """Configura atalhos de teclado"""
        self.root.bind('<Control-s>', lambda e: self.save_list())
        self.root.bind('<Control-o>', lambda e: self.load_from_file())
        self.root.bind('<Control-f>', lambda e: self.search_entry.focus())
        self.root.bind('<F5>', lambda e: self.scan_network())
        self.root.bind('<F6>', lambda e: self.check_status())
        self.root.bind('<Escape>', lambda e: self.clear_search())
    
    def create_widgets(self):
        """Cria widgets da interface"""
        # Container principal com notebook (abas)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Aba 1: Instalação (principal)
        self.tab_install = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_install, text="📦 Instalação")
        self.create_installation_tab()
        
        # Aba 2: Dashboard
        self.tab_dashboard = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_dashboard, text="📊 Dashboard")
        self.create_dashboard_tab()
        
        # Aba 3: Grupos
        self.tab_groups = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_groups, text="👥 Grupos")
        self.create_groups_tab()
        
        # Aba 4: Histórico
        self.tab_history = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_history, text="📜 Histórico")
        self.create_history_tab()
        
        # Barra de status global
        self.create_status_bar()
    
    def create_installation_tab(self):
        """Cria aba de instalação"""
        main_frame = ttk.Frame(self.tab_install)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # ===== SEÇÃO 1: CONFIGURAÇÕES =====
        config_frame = ttk.LabelFrame(main_frame, text="⚙️ Configurações", padding="10")
        config_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        config_frame.columnconfigure(1, weight=1)
        
        # Domínio
        ttk.Label(config_frame, text="Domínio:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5), pady=5)
        self.domain_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.domain_var, width=30).grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Usuário
        ttk.Label(config_frame, text="Usuário Admin:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=5)
        self.username_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.username_var, width=30).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Senha
        ttk.Label(config_frame, text="Senha:").grid(row=2, column=0, sticky=tk.W, padx=(0, 5), pady=5)
        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(config_frame, textvariable=self.password_var, width=30, show="*")
        password_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Botões de credenciais
        cred_buttons = ttk.Frame(config_frame)
        cred_buttons.grid(row=2, column=2, padx=(10, 0), pady=5)
        ttk.Button(cred_buttons, text="💾 Salvar", command=self.save_credentials).pack(side=tk.LEFT, padx=2)
        ttk.Button(cred_buttons, text="👁️ Mostrar", command=lambda: self.toggle_password(password_entry)).pack(side=tk.LEFT, padx=2)
        
        # ===== SEÇÃO 2: BUSCA E FILTROS =====
        filter_frame = ttk.LabelFrame(main_frame, text="🔍 Busca e Filtros", padding="10")
        filter_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        filter_frame.columnconfigure(1, weight=1)
        
        # Busca
        ttk.Label(filter_frame, text="Buscar:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.filter_computers())
        self.search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=30)
        self.search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(filter_frame, text="❌ Limpar", command=self.clear_search).grid(row=0, column=2, padx=5)
        
        # Filtros
        filter_buttons = ttk.Frame(filter_frame)
        filter_buttons.grid(row=1, column=0, columnspan=3, pady=(10, 0), sticky=tk.W)
        
        self.filter_online_var = tk.BooleanVar(value=True)
        self.filter_offline_var = tk.BooleanVar(value=True)
        self.filter_installed_var = tk.BooleanVar(value=True)
        self.filter_not_installed_var = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(filter_buttons, text="🟢 Online", variable=self.filter_online_var, 
                       command=self.filter_computers).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(filter_buttons, text="🔴 Offline", variable=self.filter_offline_var,
                       command=self.filter_computers).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(filter_buttons, text="✅ Instalado", variable=self.filter_installed_var,
                       command=self.filter_computers).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(filter_buttons, text="❌ Não Instalado", variable=self.filter_not_installed_var,
                       command=self.filter_computers).pack(side=tk.LEFT, padx=5)
        
        # ===== SEÇÃO 3: COMPUTADORES =====
        computers_frame = ttk.LabelFrame(main_frame, text="💻 Computadores", padding="10")
        computers_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        computers_frame.columnconfigure(0, weight=1)
        computers_frame.rowconfigure(1, weight=1)
        
        # Botões de ação rápida
        action_frame = ttk.Frame(computers_frame)
        action_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(action_frame, text="🔍 Escanear Rede", command=self.scan_network,
                  style="Accent.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="⚙️ Configurar", command=self.configure_scan).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="✅ Selecionar Todos", command=self.select_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="❌ Desmarcar Todos", command=self.deselect_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="🔄 Atualizar", command=self.update_computer_list).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="🧪 Testar Conectividade", command=self.test_connectivity).pack(side=tk.LEFT, padx=2)
        
        self.scan_status_var = tk.StringVar(value="Pronto para escanear")
        ttk.Label(action_frame, textvariable=self.scan_status_var, foreground="gray").pack(side=tk.LEFT, padx=(20, 0))
        
        # Lista de computadores com Treeview (mais moderno)
        list_container = ttk.Frame(computers_frame)
        list_container.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_container.columnconfigure(0, weight=1)
        list_container.rowconfigure(0, weight=1)
        
        # Treeview com colunas
        columns = ('Computador', 'Status', 'Usuário', 'Instalado')
        self.computers_tree = ttk.Treeview(list_container, columns=columns, show='tree headings', height=15)
        self.computers_tree.heading('#0', text='☑', anchor=tk.W)
        self.computers_tree.heading('Computador', text='Computador')
        self.computers_tree.heading('Status', text='Status')
        self.computers_tree.heading('Usuário', text='Usuário Logado')
        self.computers_tree.heading('Instalado', text='Agente')
        
        self.computers_tree.column('#0', width=30, anchor=tk.W)
        self.computers_tree.column('Computador', width=200, anchor=tk.W)
        self.computers_tree.column('Status', width=100, anchor=tk.CENTER)
        self.computers_tree.column('Usuário', width=150, anchor=tk.W)
        self.computers_tree.column('Instalado', width=100, anchor=tk.CENTER)
        
        scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.computers_tree.yview)
        self.computers_tree.configure(yscrollcommand=scrollbar.set)
        
        self.computers_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Bind para seleção
        self.computers_tree.bind('<Button-1>', self.on_tree_click)
        
        # Botões de gerenciamento
        mgmt_frame = ttk.Frame(computers_frame)
        mgmt_frame.grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
        
        ttk.Label(mgmt_frame, text="Adicionar:").pack(side=tk.LEFT, padx=(0, 5))
        self.computer_entry = ttk.Entry(mgmt_frame, width=20)
        self.computer_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.computer_entry.bind('<Return>', lambda e: self.add_computer())
        
        ttk.Button(mgmt_frame, text="➕ Adicionar", command=self.add_computer).pack(side=tk.LEFT, padx=2)
        ttk.Button(mgmt_frame, text="➖ Remover", command=self.remove_computer).pack(side=tk.LEFT, padx=2)
        ttk.Button(mgmt_frame, text="🗑️ Limpar", command=self.clear_computers).pack(side=tk.LEFT, padx=2)
        ttk.Button(mgmt_frame, text="📂 Carregar", command=self.load_from_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(mgmt_frame, text="💾 Salvar", command=self.save_list).pack(side=tk.LEFT, padx=2)
        ttk.Button(mgmt_frame, text="📊 Exportar", command=self.export_report).pack(side=tk.LEFT, padx=2)
        
        # ===== SEÇÃO 4: AÇÕES =====
        actions_frame = ttk.LabelFrame(main_frame, text="⚡ Ações", padding="10")
        actions_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        ttk.Button(actions_frame, text="🔧 Instalar Agente", command=self.install_agents,
                  style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="🗑️ Desinstalar", command=self.uninstall_agents).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="📊 Verificar Status", command=self.check_status).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="🔄 Reiniciar Agente", command=self.restart_agents).pack(side=tk.LEFT, padx=5)
        
        # ===== SEÇÃO 5: LOG =====
        log_frame = ttk.LabelFrame(main_frame, text="📝 Log de Operações", padding="10")
        log_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Frame para controles do log
        log_controls = ttk.Frame(log_frame)
        log_controls.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Button(log_controls, text="🗑️ Limpar Log", command=self.clear_log).pack(side=tk.LEFT, padx=2)
        ttk.Button(log_controls, text="💾 Salvar Log", command=self.save_log).pack(side=tk.LEFT, padx=2)
        ttk.Button(log_controls, text="🔍 Filtrar", command=self.filter_log).pack(side=tk.LEFT, padx=2)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, wrap=tk.WORD, 
                                                   font=("Consolas", 9))
        self.log_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Barra de progresso
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        self.progress_label = ttk.Label(progress_frame, text="")
        self.progress_label.grid(row=0, column=1)
    
    def create_dashboard_tab(self):
        """Cria aba de dashboard"""
        main_frame = ttk.Frame(self.tab_dashboard)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        title = ttk.Label(main_frame, text="📊 Dashboard de Estatísticas", style="Title.TLabel")
        title.pack(pady=(0, 20))
        
        # Cards de estatísticas
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.stats_cards = {}
        stats = [
            ('Total', 'total', '💻'),
            ('Online', 'online', '🟢'),
            ('Offline', 'offline', '🔴'),
            ('Instalado', 'installed', '✅'),
            ('Não Instalado', 'not_installed', '❌')
        ]
        
        for i, (label, key, icon) in enumerate(stats):
            card = ttk.LabelFrame(stats_frame, text=f"{icon} {label}", padding="15")
            card.grid(row=0, column=i, padx=5, sticky=(tk.W, tk.E))
            stats_frame.columnconfigure(i, weight=1)
            
            value_label = ttk.Label(card, text="0", font=('Segoe UI', 24, 'bold'))
            value_label.pack()
            self.stats_cards[key] = value_label
        
        # Gráfico de distribuição (simulado com labels)
        chart_frame = ttk.LabelFrame(main_frame, text="📈 Distribuição", padding="15")
        chart_frame.pack(fill=tk.BOTH, expand=True)
        
        self.chart_canvas = tk.Canvas(chart_frame, height=200, bg='white')
        self.chart_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Botão de atualizar
        ttk.Button(main_frame, text="🔄 Atualizar Estatísticas", 
                  command=self.update_dashboard).pack(pady=10)
    
    def create_groups_tab(self):
        """Cria aba de grupos"""
        main_frame = ttk.Frame(self.tab_groups)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Controles
        controls = ttk.Frame(main_frame)
        controls.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(controls, text="Nome do Grupo:").pack(side=tk.LEFT, padx=5)
        self.group_name_var = tk.StringVar()
        ttk.Entry(controls, textvariable=self.group_name_var, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="➕ Criar Grupo", command=self.create_group).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="💾 Salvar Grupos", command=self.save_groups).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="📂 Carregar Grupos", command=self.load_groups).pack(side=tk.LEFT, padx=5)
        
        # Lista de grupos
        groups_frame = ttk.LabelFrame(main_frame, text="Grupos de Computadores", padding="10")
        groups_frame.pack(fill=tk.BOTH, expand=True)
        groups_frame.columnconfigure(0, weight=1)
        groups_frame.rowconfigure(0, weight=1)
        
        self.groups_tree = ttk.Treeview(groups_frame, columns=('Computadores',), show='tree')
        self.groups_tree.heading('#0', text='Grupo')
        self.groups_tree.heading('Computadores', text='Quantidade')
        self.groups_tree.column('Computadores', width=100)
        
        scrollbar = ttk.Scrollbar(groups_frame, orient=tk.VERTICAL, command=self.groups_tree.yview)
        self.groups_tree.configure(yscrollcommand=scrollbar.set)
        
        self.groups_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
    
    def create_history_tab(self):
        """Cria aba de histórico"""
        main_frame = ttk.Frame(self.tab_history)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Controles
        controls = ttk.Frame(main_frame)
        controls.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(controls, text="🗑️ Limpar Histórico", command=self.clear_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="💾 Exportar", command=self.export_history).pack(side=tk.LEFT, padx=5)
        
        # Lista de histórico
        history_frame = ttk.LabelFrame(main_frame, text="Histórico de Operações", padding="10")
        history_frame.pack(fill=tk.BOTH, expand=True)
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)
        
        columns = ('Data', 'Operação', 'Computador', 'Status', 'Mensagem')
        self.history_tree = ttk.Treeview(history_frame, columns=columns, show='headings', height=20)
        
        for col in columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=150)
        
        scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        
        self.history_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
    
    def create_status_bar(self):
        """Cria barra de status"""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_var = tk.StringVar(value="Pronto")
        status_label = ttk.Label(self.status_bar, textvariable=self.status_var, relief=tk.SUNKEN)
        status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Contador de computadores
        self.computer_count_var = tk.StringVar(value="0 computadores")
        count_label = ttk.Label(self.status_bar, textvariable=self.computer_count_var, relief=tk.SUNKEN, width=20)
        count_label.pack(side=tk.RIGHT)
    
    # Métodos auxiliares (implementações básicas - serão expandidas)
    def toggle_password(self, entry):
        """Alterna visibilidade da senha"""
        if entry.cget('show') == '*':
            entry.config(show='')
        else:
            entry.config(show='*')
    
    def filter_computers(self):
        """Filtra lista de computadores"""
        search_term = self.search_var.get().lower()
        # Implementar filtro
        self.update_computer_list()
    
    def clear_search(self):
        """Limpa busca"""
        self.search_var.set('')
        self.filter_computers()
    
    def on_tree_click(self, event):
        """Handle click no treeview"""
        item = self.computers_tree.selection()[0] if self.computers_tree.selection() else None
        if item:
            # Toggle seleção
            pass
    
    def test_connectivity(self):
        """Testa conectividade dos computadores selecionados"""
        self.log("Iniciando teste de conectividade...", "INFO")
        # Implementar teste
        pass
    
    def restart_agents(self):
        """Reinicia agentes"""
        if messagebox.askyesno("Confirmar", "Reiniciar agentes nos computadores selecionados?"):
            self.log("Reiniciando agentes...", "INFO")
            # Implementar reinício
            pass
    
    def clear_log(self):
        """Limpa log"""
        self.log_text.delete(1.0, tk.END)
    
    def save_log(self):
        """Salva log em arquivo"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.log_text.get(1.0, tk.END))
            self.log(f"Log salvo em {filename}", "SUCCESS")
    
    def filter_log(self):
        """Filtra log"""
        # Implementar filtro de log
        pass
    
    def export_report(self):
        """Exporta relatório"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if filename:
            self.save_report_csv(filename)
            self.log(f"Relatório exportado: {filename}", "SUCCESS")
    
    def save_report_csv(self, filename):
        """Salva relatório em CSV"""
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Computador', 'Status', 'Usuário', 'Agente Instalado', 'Última Verificação'])
            for computer, info in self.network_computers.items():
                writer.writerow([
                    computer,
                    'Online' if info.get('online') else 'Offline',
                    info.get('logged_user', 'N/A'),
                    'Sim' if info.get('installed') else 'Não',
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ])
    
    def update_dashboard(self):
        """Atualiza dashboard"""
        # Atualiza estatísticas
        self.stats['total'] = len(self.network_computers)
        self.stats['online'] = sum(1 for c in self.network_computers.values() if c.get('online'))
        self.stats['offline'] = self.stats['total'] - self.stats['online']
        self.stats['installed'] = sum(1 for c in self.network_computers.values() if c.get('installed'))
        self.stats['not_installed'] = self.stats['total'] - self.stats['installed']
        
        # Atualiza cards
        for key, label in self.stats_cards.items():
            label.config(text=str(self.stats.get(key, 0)))
        
        # Atualiza gráfico
        self.draw_chart()
    
    def draw_chart(self):
        """Desenha gráfico simples"""
        self.chart_canvas.delete('all')
        # Implementar gráfico simples
        pass
    
    def create_group(self):
        """Cria grupo de computadores"""
        group_name = self.group_name_var.get().strip()
        if not group_name:
            messagebox.showwarning("Aviso", "Digite um nome para o grupo")
            return
        
        selected = [c for c, info in self.network_computers.items() if info.get('selected')]
        if not selected:
            messagebox.showwarning("Aviso", "Selecione computadores primeiro")
            return
        
        self.computer_groups[group_name] = selected
        self.update_groups_tree()
        self.log(f"Grupo '{group_name}' criado com {len(selected)} computadores", "SUCCESS")
    
    def update_groups_tree(self):
        """Atualiza árvore de grupos"""
        for item in self.groups_tree.get_children():
            self.groups_tree.delete(item)
        
        for group_name, computers in self.computer_groups.items():
            item = self.groups_tree.insert('', tk.END, text=group_name, values=(len(computers),))
            for computer in computers:
                self.groups_tree.insert(item, tk.END, text=computer, values=('',))
    
    def save_groups(self):
        """Salva grupos"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.computer_groups, f, indent=2)
            self.log(f"Grupos salvos: {filename}", "SUCCESS")
    
    def load_groups(self):
        """Carrega grupos"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, 'r', encoding='utf-8') as f:
                self.computer_groups = json.load(f)
            self.update_groups_tree()
            self.log(f"Grupos carregados: {filename}", "SUCCESS")
    
    def clear_history(self):
        """Limpa histórico"""
        if messagebox.askyesno("Confirmar", "Limpar todo o histórico?"):
            self.operation_history = []
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)
            self.log("Histórico limpo", "INFO")
    
    def export_history(self):
        """Exporta histórico"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Data', 'Operação', 'Computador', 'Status', 'Mensagem'])
                for item in self.history_tree.get_children():
                    values = self.history_tree.item(item, 'values')
                    writer.writerow(values)
            self.log(f"Histórico exportado: {filename}", "SUCCESS")
    
    def add_history_entry(self, operation, computer, status, message):
        """Adiciona entrada ao histórico"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.operation_history.append({
            'timestamp': timestamp,
            'operation': operation,
            'computer': computer,
            'status': status,
            'message': message
        })
        self.history_tree.insert('', tk.END, values=(timestamp, operation, computer, status, message))
    
    # Métodos que precisam ser implementados (compatibilidade com código original)
    def log(self, message, level="INFO"):
        """Adiciona mensagem ao log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "ERROR": "❌",
            "WARNING": "⚠️"
        }.get(level, "ℹ️")
        
        log_message = f"[{timestamp}] {prefix} {message}\n"
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
    
    def update_status(self, message):
        """Atualiza barra de status"""
        self.status_var.set(message)
        self.computer_count_var.set(f"{len(self.computers)} computadores")
    
    def add_computer(self):
        """Adiciona computador"""
        computer = self.computer_entry.get().strip()
        if computer:
            if computer not in self.network_computers:
                self.network_computers[computer] = {
                    'selected': True,
                    'online': False,
                    'logged_user': 'Verificando...',
                    'installed': False
                }
            if computer not in self.computers:
                self.computers.append(computer)
            self.update_computer_list()
            self.computer_entry.delete(0, tk.END)
            self.log(f"Computador '{computer}' adicionado", "SUCCESS")
    
    def remove_computer(self):
        """Remove computador"""
        selected = self.computers_tree.selection()
        if selected:
            item = selected[0]
            computer = self.computers_tree.item(item, 'text')
            if computer in self.computers:
                self.computers.remove(computer)
            if computer in self.network_computers:
                del self.network_computers[computer]
            self.update_computer_list()
            self.log(f"Computador '{computer}' removido", "INFO")
    
    def clear_computers(self):
        """Limpa lista"""
        if messagebox.askyesno("Confirmar", "Limpar toda a lista?"):
            self.computers = []
            self.network_computers = {}
            self.update_computer_list()
            self.log("Lista limpa", "INFO")
    
    def update_computer_list(self):
        """Atualiza lista de computadores"""
        # Limpa treeview
        for item in self.computers_tree.get_children():
            self.computers_tree.delete(item)
        
        # Adiciona computadores
        for computer, info in self.network_computers.items():
            status = "🟢 Online" if info.get('online') else "🔴 Offline"
            installed = "✅ Sim" if info.get('installed') else "❌ Não"
            user = info.get('logged_user', 'N/A')
            
            item = self.computers_tree.insert('', tk.END, 
                text="☑" if info.get('selected') else "☐",
                values=(computer, status, user, installed))
        
        self.update_status("Lista atualizada")
        self.update_dashboard()
    
    def select_all(self):
        """Seleciona todos"""
        for computer in self.network_computers:
            self.network_computers[computer]['selected'] = True
            if computer not in self.computers:
                self.computers.append(computer)
        self.update_computer_list()
    
    def deselect_all(self):
        """Deseleciona todos"""
        for computer in self.network_computers:
            self.network_computers[computer]['selected'] = False
        self.computers = []
        self.update_computer_list()
    
    def scan_network(self):
        """Escaneia rede"""
        self.log("Iniciando varredura de rede...", "INFO")
        # Implementar varredura (usar código original)
        pass
    
    def configure_scan(self):
        """Configura varredura"""
        # Implementar diálogo de configuração
        pass
    
    def install_agents(self):
        """Instala agentes"""
        if not self.computers:
            messagebox.showwarning("Aviso", "Selecione computadores primeiro")
            return
        self.log(f"Iniciando instalação em {len(self.computers)} computadores...", "INFO")
        # Implementar instalação
        pass
    
    def uninstall_agents(self):
        """Desinstala agentes"""
        if not self.computers:
            messagebox.showwarning("Aviso", "Selecione computadores primeiro")
            return
        self.log(f"Iniciando desinstalação em {len(self.computers)} computadores...", "INFO")
        # Implementar desinstalação
        pass
    
    def check_status(self):
        """Verifica status"""
        if not self.computers:
            messagebox.showwarning("Aviso", "Selecione computadores primeiro")
            return
        self.log("Verificando status dos agentes...", "INFO")
        # Implementar verificação
        pass
    
    def load_from_file(self):
        """Carrega de arquivo"""
        filename = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    computer = line.strip()
                    if computer and not computer.startswith('#'):
                        if computer not in self.network_computers:
                            self.network_computers[computer] = {
                                'selected': True,
                                'online': False,
                                'logged_user': 'N/A',
                                'installed': False
                            }
                        if computer not in self.computers:
                            self.computers.append(computer)
            self.update_computer_list()
            self.log(f"Lista carregada de {filename}", "SUCCESS")
    
    def save_list(self):
        """Salva lista"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                for computer in self.computers:
                    f.write(f"{computer}\n")
            self.log(f"Lista salva em {filename}", "SUCCESS")
    
    def save_credentials(self):
        """Salva credenciais"""
        settings = {
            'domain': self.domain_var.get(),
            'username': self.username_var.get(),
            'password': self.password_var.get()  # Em produção, criptografar
        }
        settings_file = self.agent_path / 'installer_settings.json'
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
        self.log("Credenciais salvas", "SUCCESS")
    
    def load_settings(self):
        """Carrega configurações"""
        settings_file = self.agent_path / 'installer_settings.json'
        if settings_file.exists():
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.domain_var.set(settings.get('domain', ''))
                    self.username_var.set(settings.get('username', ''))
                    # Não carrega senha por segurança
                    # self.password_var.set(settings.get('password', ''))
                    self.password_var.set('')
            except:
                pass


def main():
    """Função principal"""
    if sys.platform != "win32":
        print("Este aplicativo é apenas para Windows")
        return
    
    root = tk.Tk()
    app = AgentInstallerGUIMelhorado(root)
    
    # Centraliza janela
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    root.mainloop()


if __name__ == "__main__":
    main()

