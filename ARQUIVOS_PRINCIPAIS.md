# 📁 ARQUIVOS PRINCIPAIS DO PROJETO

**Guia de Referência Rápida dos Arquivos Essenciais**

---

## 🎯 ARQUIVOS CORE (CRÍTICOS)

### **Servidor Web (Flask)**

| Arquivo | Descrição | Importância |
|---------|-----------|-------------|
| `serv/servidor.py` | **Servidor Flask principal** - Todas as rotas, endpoints e lógica principal (8.890 linhas) | ⭐⭐⭐⭐⭐ |
| `serv/print_events.db` | **Banco de dados SQLite** - Armazena todos os eventos de impressão | ⭐⭐⭐⭐⭐ |
| `serv/modules/calculo_impressao.py` | **Módulo de cálculos** - Centraliza toda lógica de cálculo de folhas e custos | ⭐⭐⭐⭐⭐ |
| `serv/modules/db_pool.py` | **Connection Pooling** - Gerencia conexões do banco de dados | ⭐⭐⭐⭐ |
| `serv/modules/helper_db.py` | **Funções auxiliares DB** - Funções comuns de banco de dados | ⭐⭐⭐⭐ |
| `serv/modules/validacao.py` | **Validação de dados** - Sanitização e validação de inputs | ⭐⭐⭐⭐ |
| `serv/modules/error_handler.py` | **Tratamento de erros** - Exceções customizadas e handlers | ⭐⭐⭐ |

### **Agente de Monitoramento**

| Arquivo | Descrição | Importância |
|---------|-----------|-------------|
| `agent/agente.py` | **Agente principal** - Captura eventos de impressão do Windows | ⭐⭐⭐⭐⭐ |
| `agent/config.json` | **Configuração do agente** - URL do servidor e configurações | ⭐⭐⭐⭐⭐ |

---

## 📦 MÓDULOS DE FUNCIONALIDADES

### **Módulos Core**

| Módulo | Descrição |
|--------|-----------|
| `serv/modules/relatorios_unificado.py` | Relatórios e dashboard unificados |
| `serv/modules/analise_comodatos.py` | Análise de comodatos (contratos de impressão) |
| `serv/modules/analise_padroes.py` | Análise de padrões de impressão |
| `serv/modules/alertas.py` | Sistema de alertas e notificações |
| `serv/modules/quotas.py` | Gestão de quotas de impressão |
| `serv/modules/metas.py` | Gestão de metas |
| `serv/modules/orcamento.py` | Gestão de orçamentos |
| `serv/modules/comparativo.py` | Comparativo entre períodos |
| `serv/modules/sugestoes.py` | Sugestões de economia |
| `serv/modules/exportacao_avancada.py` | Exportação avançada de dados |
| `serv/modules/pdf_export.py` | Exportação para PDF |
| `serv/modules/backup.py` | Sistema de backup automático |
| `serv/modules/auditoria.py` | Auditoria de ações do sistema |
| `serv/modules/cache.py` | Sistema de cache |

### **Módulos de IA (10 módulos)**

| Módulo | Descrição | Requer API Key |
|--------|-----------|---------------|
| `serv/modules/ia_previsao_custos.py` | Previsão de custos futuros | ❌ |
| `serv/modules/ia_deteccao_anomalias.py` | Detecção de anomalias | ❌ |
| `serv/modules/ia_otimizacao.py` | Otimização automática | ❌ |
| `serv/modules/ia_alertas_inteligentes.py` | Alertas inteligentes | ❌ |
| `serv/modules/ia_chatbot.py` | Chatbot com OpenAI | ✅ |
| `serv/modules/ia_chatbot_gratuito.py` | Chatbot gratuito (local) | ❌ |
| `serv/modules/ia_analise_preditiva.py` | Análise preditiva | ❌ |
| `serv/modules/ia_recomendacoes.py` | Recomendações inteligentes | ❌ |
| `serv/modules/ia_tendencias.py` | Análise de tendências | ❌ |
| `serv/modules/ia_score_eficiencia.py` | Score de eficiência | ❌ |
| `serv/modules/ia_relatorios_narrativos.py` | Relatórios narrativos | ✅ |

### **Módulos Adicionais**

| Módulo | Descrição |
|--------|-----------|
| `serv/modules/gamificacao.py` | Sistema de gamificação |
| `serv/modules/heatmap.py` | Heatmaps de uso |
| `serv/modules/comentarios.py` | Sistema de comentários |
| `serv/modules/aprovacao_impressoes.py` | Sistema de aprovação |
| `serv/modules/filtros_salvos.py` | Filtros salvos |
| `serv/modules/dashboard_widgets.py` | Widgets do dashboard |
| `serv/modules/helper_relatorios.py` | Funções auxiliares de relatórios |

---

## 🎨 INTERFACE (Templates e Estáticos)

### **Templates HTML (Jinja2)**

| Template | Descrição |
|----------|-----------|
| `serv/templates/base.html` | **Template base** - Layout principal com sidebar |
| `serv/templates/login.html` | Página de login |
| `serv/templates/dashboard.html` | Dashboard principal |
| `serv/templates/usuarios.html` | Lista de usuários |
| `serv/templates/setores.html` | Estatísticas por setor |
| `serv/templates/impressoras.html` | Estatísticas por impressora |
| `serv/templates/admin_*.html` | Páginas administrativas (11 arquivos) |

### **Arquivos Estáticos**

| Arquivo | Descrição |
|---------|-----------|
| `serv/static/css/style.css` | Estilos principais |
| `serv/static/css/theme.css` | Tema do sistema |
| `serv/static/js/script.js` | JavaScript principal |
| `serv/static/js/websocket.js` | WebSocket para atualizações em tempo real |

---

## 🛠️ SCRIPTS ÚTEIS

### **Scripts de Configuração**

| Script | Descrição |
|-------|-----------|
| `gerar_secret_key.py` | Gera SECRET_KEY segura para produção |
| `criar_usuario_admin.py` | Cria usuário administrador |
| `criar_usuario_ti.py` | Cria usuário TI |
| `listar_usuarios.py` | Lista todos os usuários |
| `instalar_ia.py` | Instala dependências de IA |

### **Scripts de Cadastro**

| Script | Descrição |
|-------|-----------|
| `cadastrar_impressoras_manual.py` | Cadastra impressoras manualmente no banco |
| `importar_impressoras_csv.py` | Importa impressoras via CSV |
| `listar_impressoras_rede.ps1` | Lista impressoras da rede (PowerShell) |

### **Scripts de Teste**

| Script | Descrição |
|-------|-----------|
| `test_project.py` | Testes gerais do projeto |
| `test_endpoints.py` | Testes de endpoints da API |
| `test_admin_impressoras.py` | Testes da rota admin_impressoras |
| `simular_impressoes.py` | Simula impressões para validar cálculos |
| `check_db.py` | Verifica integridade do banco de dados |

### **Scripts de Scanner**

| Script | Descrição |
|-------|-----------|
| `scanner_impressoras.py` | Scanner principal de impressoras de rede |
| `agent/scanner_rede_impressoras.py` | Scanner de rede do agente |
| `agent/executar_scan_impressoras.py` | Executa scan de impressoras |

### **Scripts do Agente**

| Script | Descrição |
|-------|-----------|
| `agent/installer_gui_melhorado.py` | Instalador GUI melhorado |
| `agent/DEPLOY_REDE_COMPLETO.ps1` | Deploy completo em rede (PowerShell) |
| `agent/install_agent.ps1` | Instalação do agente (PowerShell) |
| `agent/reset_estado.py` | Reseta estado do agente |
| `agent/build_exe.py` | Compila agente em executável |

---

## 📄 CONFIGURAÇÃO

| Arquivo | Descrição |
|---------|-----------|
| `requirements.txt` | **Dependências do servidor** (Python) |
| `agent/requirements.txt` | Dependências do agente |
| `config.json` | Configuração principal (raiz) |
| `agent/config.json` | Configuração do agente |
| `env.example` | Exemplo de variáveis de ambiente |
| `Dockerfile` | Container Docker |
| `docker-compose.yml` | Orquestração Docker |

---

## 📚 DOCUMENTAÇÃO

### **Documentação Principal**

| Arquivo | Descrição |
|---------|-----------|
| `README.md` | **Documentação principal** do projeto |
| `AUDITORIA_PROJETO.md` | Auditoria completa do projeto |
| `MELHORIAS_IMPLEMENTADAS.md` | Melhorias implementadas |
| `RELATORIO_TESTES.md` | Relatório de testes |
| `RELATORIO_LIMPEZA_PROJETO.md` | Relatório de limpeza |

### **Guias de Configuração**

| Arquivo | Descrição |
|---------|-----------|
| `GUIA_CONFIGURACAO_COMODATOS.md` | Como configurar comodatos |
| `GUIA_CONFIGURAR_SECRET_KEY.md` | Como configurar SECRET_KEY |
| `CONFIGURACAO_OPENAI.md` | Configuração de IA (OpenAI) |
| `CONFIGURAR_GROQ.md` | Configuração de IA (Groq) |

### **Documentação do Agente**

| Arquivo | Descrição |
|---------|-----------|
| `agent/INSTALACAO_AGENTE.md` | Guia de instalação do agente |
| `agent/GUIA_DEPLOY_REDE.md` | Guia de deploy em rede |
| `agent/EXEMPLOS_DEPLOY.md` | Exemplos práticos de deploy |

---

## 🗄️ BANCO DE DADOS

| Arquivo | Descrição |
|---------|-----------|
| `serv/print_events.db` | **Banco principal** - Eventos de impressão |
| `agent/event_queue.db` | Fila de eventos do agente (local) |
| `serv/backups/backup_*.db` | Backups automáticos (5 mais recentes) |

---

## 🚀 PONTOS DE ENTRADA

### **Servidor**
```bash
python serv/servidor.py
```

### **Agente**
```bash
python agent/agente.py
```

### **Scanner de Impressoras**
```bash
python scanner_impressoras.py
```

---

## 📊 RESUMO POR CATEGORIA

| Categoria | Quantidade | Arquivos Principais |
|-----------|------------|---------------------|
| **Core** | 6 | `servidor.py`, `agente.py`, `calculo_impressao.py`, `db_pool.py`, `helper_db.py`, `validacao.py` |
| **Módulos** | 39 | Todos em `serv/modules/` |
| **Templates** | 34 | Todos em `serv/templates/` |
| **Scripts** | 15+ | Scripts de configuração, teste e cadastro |
| **Documentação** | 12 | Guias e relatórios |
| **Configuração** | 7 | `requirements.txt`, `config.json`, etc. |

---

## ⚠️ ARQUIVOS QUE NÃO DEVEM SER MODIFICADOS

- `serv/print_events.db` - Banco de dados principal (fazer backup antes)
- `serv/modules/calculo_impressao.py` - Lógica crítica de cálculos
- `serv/modules/db_pool.py` - Connection pooling (pode afetar performance)
- `agent/agente.py` - Agente principal (pode afetar captura de eventos)

---

**Última atualização:** 2024-12-04

