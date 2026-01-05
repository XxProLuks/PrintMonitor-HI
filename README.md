# 🖨️ Print Monitor - Sistema de Monitoramento de Impressões

Sistema completo e avançado de monitoramento de impressões corporativas com análise em tempo real, alertas inteligentes, gestão de quotas, metas, orçamentos e muito mais.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)
![License](https://img.shields.io/badge/License-Internal-red.svg)

---

## 📋 Índice

- [Visão Geral](#-visão-geral)
- [Funcionalidades](#-funcionalidades)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Instalação](#️-instalação)
- [Configuração](#-configuração)
- [Uso](#-uso)
- [API REST](#-api-rest)
- [Troubleshooting](#-troubleshooting)
- [Documentação Adicional](#-documentação-adicional)
- [Contribuição](#-contribuição)
- [Licença](#-licença)

---

## 🎯 Visão Geral

O **Print Monitor** é uma solução corporativa completa para monitoramento e gestão de impressões em ambientes Windows. O sistema captura eventos de impressão em tempo real, analisa padrões de uso, calcula custos, gerencia quotas e fornece insights valiosos para otimização de recursos.

### Características Principais

- ✅ **Monitoramento em Tempo Real** - Captura eventos via PowerShell, WMI e Event Log
- ✅ **Dashboard Web Interativo** - Interface moderna e responsiva
- ✅ **Análise Avançada** - Comparativos, tendências e padrões
- ✅ **Gestão Inteligente** - Quotas, metas, orçamentos e alertas
- ✅ **IA Integrada** - 10 módulos de inteligência artificial
- ✅ **API REST Completa** - Integração com outros sistemas
- ✅ **Segurança** - Autenticação, auditoria e backups automáticos

---

## 🚀 Funcionalidades

### Core (Funcionalidades Básicas)

| Funcionalidade | Descrição |
|---------------|-----------|
| 📊 **Captura de Eventos** | Monitoramento em tempo real via PowerShell, WMI e Event Log |
| 🖥️ **Dashboard Web** | Interface web completa com gráficos e estatísticas |
| 📈 **Relatórios** | Relatórios detalhados por usuário, setor e impressora |
| 👥 **Gestão de Usuários** | Cadastro e gestão de usuários e setores |
| 💰 **Cálculo de Custos** | Cálculo automático de custos por impressão |
| 🗄️ **Banco de Dados** | SQLite com histórico completo de impressões |

### Funcionalidades Avançadas

#### 📊 Análise e Comparativos
- **Comparativo de Períodos** - Compare mês atual vs anterior, trimestres, anos
- **Análise de Padrões** - Identifique horários de pico, anomalias e tendências
- **Heatmaps de Uso** - Visualização de padrões de uso por horário, setor e dia da semana
- **Exportação Avançada** - Exporte dados em CSV, Excel, PNG e PDF

#### 🎯 Gestão e Controle
- **Quotas e Limites** - Defina limites por usuário, setor ou impressora
- **Metas e Acompanhamento** - Defina e acompanhe metas de páginas e custos
- **Orçamento e Projeções** - Gerencie orçamentos por setor com projeções
- **Sistema de Aprovação** - Aprove ou rejeite impressões antes da execução

#### 🔔 Alertas e Notificações
- **Sistema de Alertas** - Alertas automáticos por email e dashboard
- **Alertas Inteligentes** - Alertas que aprendem padrões (IA)
- **Sugestões de Economia** - Sugestões automáticas de duplex e P&B

#### 💬 Colaboração
- **Sistema de Comentários** - Adicione comentários e tags aos eventos
- **Filtros Salvos** - Salve e compartilhe filtros de busca
- **Gamificação** - Sistema de pontos, badges e ranking

#### 📝 Administração
- **Auditoria Completa** - Log de todas as ações dos usuários
- **Relatórios Agendados** - Envio automático de relatórios por email
- **Backup Automático** - Backups diários automáticos com restore points
- **Dashboard Personalizado** - Widgets customizáveis por usuário

#### ⚡ Performance
- **Cache Inteligente** - Sistema de cache para melhor performance
- **API REST** - API completa para integrações
- **Compressão HTTP** - Otimização de transferência de dados

### 🤖 Funcionalidades de IA

O sistema inclui **10 módulos de IA** para análise inteligente:

| Módulo | Descrição | Requer API Key |
|--------|-----------|----------------|
| 🔮 **Previsão de Custos** | Previsão de custos futuros usando Machine Learning | ❌ |
| 🔍 **Detecção de Anomalias** | Identifica padrões suspeitos automaticamente | ❌ |
| ⚡ **Otimização Automática** | Sugestões de otimização de recursos | ❌ |
| 🔔 **Alertas Inteligentes** | Alertas que aprendem padrões | ❌ |
| 💬 **Chatbot Inteligente** | Assistente virtual | ✅ OpenAI/Groq |
| 📦 **Análise Preditiva** | Previsão de reposição de materiais | ❌ |
| 🎯 **Recomendações** | Sugestões baseadas em histórico | ❌ |
| 📈 **Análise de Tendências** | Identifica padrões e tendências | ❌ |
| 🏆 **Score de Eficiência** | Pontuação de eficiência por usuário/setor | ❌ |
| 📝 **Relatórios Narrativos** | Geração automática de relatórios | ✅ OpenAI |

> 📚 **Documentação completa de IA:** Veja `CONFIGURACAO_OPENAI.md` e `CONFIGURAR_GROQ.md`

---

## 📁 Estrutura do Projeto

```
Monitoramento1/
├── agent/                          # Agente de monitoramento
│   ├── agente.py                   # Agente principal (executa como admin)
│   ├── config.json                 # Configuração do agente
│   ├── requirements.txt            # Dependências do agente
│   └── *.log                       # Logs do agente
│
├── serv/                           # Servidor web Flask
│   ├── servidor.py                 # Servidor Flask principal (4096 linhas)
│   ├── print_events.db             # Banco de dados SQLite
│   ├── servidor.log                # Logs do servidor
│   │
│   ├── modules/                    # Módulos de funcionalidades
│   │   ├── alertas.py              # Sistema de alertas
│   │   ├── analise_padroes.py      # Análise de padrões
│   │   ├── aprovacao_impressoes.py # Sistema de aprovação
│   │   ├── auditoria.py            # Auditoria de ações
│   │   ├── backup.py               # Backup automático
│   │   ├── cache.py                # Sistema de cache
│   │   ├── comentarios.py          # Sistema de comentários
│   │   ├── comparativo.py          # Comparativo de períodos
│   │   ├── dashboard_widgets.py    # Widgets do dashboard
│   │   ├── exportacao_avancada.py  # Exportação avançada
│   │   ├── filtros_salvos.py       # Filtros salvos
│   │   ├── gamificacao.py          # Sistema de gamificação
│   │   ├── heatmap.py              # Heatmaps de uso
│   │   ├── metas.py                # Gestão de metas
│   │   ├── orcamento.py            # Gestão de orçamentos
│   │   ├── pdf_export.py           # Exportação PDF
│   │   ├── quotas.py                # Gestão de quotas
│   │   ├── relatorios_agendados.py  # Relatórios agendados
│   │   ├── relatorios_unificado.py  # Relatórios unificados
│   │   ├── sugestoes.py            # Sugestões de economia
│   │   │
│   │   └── ia_*.py                 # Módulos de IA (10 módulos)
│   │       ├── ia_previsao_custos.py
│   │       ├── ia_deteccao_anomalias.py
│   │       ├── ia_otimizacao.py
│   │       ├── ia_alertas_inteligentes.py
│   │       ├── ia_chatbot.py
│   │       ├── ia_chatbot_gratuito.py
│   │       ├── ia_analise_preditiva.py
│   │       ├── ia_recomendacoes.py
│   │       ├── ia_tendencias.py
│   │       ├── ia_score_eficiencia.py
│   │       └── ia_relatorios_narrativos.py
│   │
│   ├── templates/                  # Templates HTML (Jinja2)
│   │   ├── base.html               # Template base (com sidebar)
│   │   ├── login.html              # Página de login
│   │   ├── dashboard.html          # Dashboard principal
│   │   ├── usuarios.html           # Lista de usuários
│   │   ├── setores.html            # Estatísticas por setor
│   │   ├── impressoras.html        # Estatísticas por impressora
│   │   ├── comparativo.html        # Comparativo de períodos
│   │   ├── alertas.html            # Central de alertas
│   │   ├── sugestoes.html          # Sugestões de economia
│   │   ├── filtros_salvos.html     # Filtros salvos
│   │   ├── heatmaps.html           # Heatmaps de uso
│   │   ├── gamificacao.html        # Gamificação
│   │   ├── comentarios.html        # Sistema de comentários
│   │   ├── aprovacoes.html         # Sistema de aprovação
│   │   ├── status_sistema.html     # Status do sistema
│   │   └── admin_*.html            # Páginas administrativas
│   │
│   ├── static/                     # Arquivos estáticos
│   │   ├── css/                    # Estilos CSS
│   │   │   ├── style.css
│   │   │   ├── theme.css
│   │   │   └── github-dark.css
│   │   └── js/                     # Scripts JavaScript
│   │       └── script.js
│   │
│   └── backups/                    # Backups automáticos
│       └── backup_*.db
│
├── config.json                     # Configuração principal
├── requirements.txt                 # Dependências do servidor
├── README.md                       # Este arquivo
│
└── Documentação/                   # Documentação adicional
    ├── CONFIGURACAO_OPENAI.md      # Configuração OpenAI
    ├── CONFIGURAR_GROQ.md          # Configuração Groq
    ├── STATUS_IMPLEMENTACAO_FINAL.md
    ├── RESUMO_IMPLEMENTACAO.md
    └── ...
```

---

## 🛠️ Instalação

### Pré-requisitos

- **Python 3.8+** (recomendado 3.10+)
- **Windows** (para o agente de monitoramento)
- **Privilégios de Administrador** (para executar o agente)
- **PowerShell 5.1+**

### Passo 1: Clonar/Baixar o Projeto

```bash
# Se usar Git
git clone <repository-url>
cd Monitoramento1

# Ou extraia o ZIP do projeto
```

### Passo 2: Instalar Dependências

#### Servidor Web

```bash
# Na raiz do projeto
pip install -r requirements.txt
```

#### Agente de Monitoramento

```bash
cd agent
pip install -r requirements.txt
```

### Passo 3: Configurar Banco de Dados

O banco de dados será criado automaticamente na primeira execução. Se necessário, você pode recriar:

```bash
cd serv
python recreate_database.py
```

### Passo 4: Configurar Variáveis de Ambiente (Opcional)

Crie um arquivo `.env` na raiz do projeto:

```env
# Segurança
SECRET_KEY=sua-chave-secreta-aqui
SESSION_LIFETIME=3600

# Banco de Dados
DB_NAME=print_events.db

# Email (para alertas)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu_email@gmail.com
SMTP_PASSWORD=sua_senha_app

# OpenAI (opcional - para IA)
OPENAI_API_KEY=sk-sua-chave-aqui

# Groq (opcional - alternativa gratuita)
GROQ_API_KEY=gsk_sua-chave-aqui
```

---

## ⚙️ Configuração

### Configuração do Agente

Edite `agent/config.json`:

```json
{
  "server_url": "http://localhost:5002",
  "check_interval": 5,
  "methods": ["powershell", "wmi", "eventlog"],
  "printers": ["*"]
}
```

### Configuração do Servidor

Edite `config.json` na raiz:

```json
{
  "port": 5002,
  "host": "0.0.0.0",
  "debug": false,
  "preco_por_pagina": 0.10,
  "preco_por_pagina_colorida": 0.50
}
```

### Configuração de Email (Opcional)

Para alertas por email, configure no `.env` ou variáveis de ambiente:

```bash
# Windows PowerShell
$env:SMTP_SERVER="smtp.gmail.com"
$env:SMTP_PORT="587"
$env:SMTP_USER="seu_email@gmail.com"
$env:SMTP_PASSWORD="sua_senha_app"

# Linux/Mac
export SMTP_SERVER=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=seu_email@gmail.com
export SMTP_PASSWORD=sua_senha_app
```

### Configuração de IA (Opcional)

#### OpenAI

1. Obtenha uma chave de API em https://platform.openai.com/api-keys
2. Adicione ao `.env`:
   ```env
   OPENAI_API_KEY=sk-sua-chave-aqui
   ```

#### Groq (Alternativa Gratuita)

1. Obtenha uma chave em https://console.groq.com/keys
2. Adicione ao `.env`:
   ```env
   GROQ_API_KEY=gsk_sua-chave-aqui
   ```

> 📚 **Documentação completa:** Veja `CONFIGURACAO_OPENAI.md` e `CONFIGURAR_GROQ.md`

---

## 🚀 Uso

### Iniciar o Sistema

#### Terminal 1 - Servidor Web

```bash
cd serv
python servidor.py
```

O servidor estará disponível em: **http://localhost:5002**

#### Terminal 2 - Agente de Monitoramento (como Administrador)

```bash
# Windows PowerShell (como Administrador)
cd agent
python agente.py
```

> ⚠️ **Importante:** O agente deve ser executado como **Administrador** para acessar o Event Log.

### Acessar o Sistema

1. Abra o navegador em: **http://localhost:5002**
2. Faça login com:
   - **Usuário padrão:** `admin`
   - **Senha padrão:** `123` (altere após primeiro login)

### Primeiros Passos

1. **Configurar Preços** - Vá em `Administração > Preços` e configure os custos
2. **Cadastrar Usuários** - Vá em `Administração > Usuários` e cadastre os usuários
3. **Configurar Quotas** - Vá em `Administração > Quotas` e defina limites
4. **Configurar Metas** - Vá em `Administração > Metas` e defina metas
5. **Visualizar Dashboard** - Acesse o Dashboard para ver estatísticas em tempo real

### Navegação no Sistema

O sidebar possui menus expansíveis organizados em:

- **Dashboard** - Visão geral do sistema
- **Relatórios** - Usuários, Setores, Impressoras
- **Análises** - Comparativo, Alertas, Sugestões, Filtros, Heatmaps, Gamificação, Comentários
- **Administração** (apenas admin):
  - **Configurações** - Usuários, Logins, Preços, Configurações
  - **Planejamento** - Quotas, Metas, Orçamento
  - **Sistema** - Status, Auditoria, Relatórios Agendados, Backup, Aprovações

---

## 🔌 API REST

O sistema fornece uma API REST completa para integrações:

### Autenticação

```bash
# Login (obter token)
POST /api/login
{
  "username": "admin",
  "password": "123"
}
```

### Endpoints Principais

#### Eventos
```bash
GET  /api/v1/events              # Lista eventos
GET  /api/v1/events/{id}          # Detalhes do evento
POST /api/v1/events               # Criar evento (agente)
```

#### Estatísticas
```bash
GET  /api/v1/stats                # Estatísticas gerais
GET  /api/v1/stats/users          # Estatísticas por usuário
GET  /api/v1/stats/printers       # Estatísticas por impressora
```

#### Comparativo
```bash
GET  /api/comparativo             # Comparativo de períodos
POST /api/comparativo             # Comparativo customizado
```

#### Quotas
```bash
GET  /api/quotas                  # Lista quotas
POST /api/quotas                  # Criar quota
PUT  /api/quotas/{id}             # Atualizar quota
DELETE /api/quotas/{id}           # Deletar quota
```

#### Alertas
```bash
GET  /api/alertas                 # Lista alertas
POST /api/alertas                  # Criar alerta
PUT  /api/alertas/{id}/resolver   # Resolver alerta
```

#### Sugestões
```bash
GET  /api/sugestoes               # Lista sugestões
POST /api/sugestoes               # Criar sugestão
```

#### Metas
```bash
GET  /api/metas                   # Lista metas
POST /api/metas                   # Criar meta
PUT  /api/metas/{id}              # Atualizar meta
```

#### Orçamento
```bash
GET  /api/orcamento               # Lista orçamentos
POST /api/orcamento               # Criar orçamento
PUT  /api/orcamento/{id}          # Atualizar orçamento
```

#### Filtros Salvos
```bash
GET  /api/filtros/listar          # Lista filtros salvos
POST /api/filtros/salvar          # Salvar filtro
DELETE /api/filtros/deletar/{id}  # Deletar filtro
```

#### Comentários
```bash
GET  /api/comentarios/listar      # Lista comentários
POST /api/comentarios/adicionar   # Adicionar comentário
DELETE /api/comentarios/deletar/{id} # Deletar comentário
```

#### Aprovações
```bash
GET  /api/aprovacoes/pendentes    # Lista aprovações pendentes
POST /api/aprovacoes/aprovar      # Aprovar impressão
POST /api/aprovacoes/rejeitar     # Rejeitar impressão
```

#### Heatmaps
```bash
GET  /api/heatmap/horarios        # Heatmap de horários
GET  /api/heatmap/setores         # Heatmap de setores
GET  /api/heatmap/semanal         # Heatmap semanal
```

#### Gamificação
```bash
GET  /api/gamificacao/ranking     # Ranking de usuários
GET  /api/gamificacao/pontos      # Pontos do usuário
GET  /api/gamificacao/badges      # Badges do usuário
```

#### IA
```bash
GET  /api/ia/previsao             # Previsão de custos
GET  /api/ia/anomalias            # Detecção de anomalias
GET  /api/ia/recomendacoes        # Recomendações
POST /api/ia/chatbot              # Chatbot (requer OpenAI)
```

### Exemplo de Uso da API

```python
import requests

# Login
response = requests.post('http://localhost:5002/api/login', json={
    'username': 'admin',
    'password': '123'
})
token = response.json()['token']

# Obter eventos
headers = {'Authorization': f'Bearer {token}'}
events = requests.get('http://localhost:5002/api/v1/events', headers=headers)
print(events.json())
```

---

## 🔧 Troubleshooting

### Problema: Agente não captura eventos

**Solução:**
1. Verifique se está executando como **Administrador**
2. Verifique se o Event Log está habilitado:
   ```powershell
   # Execute como Administrador
   .\habilitar_event_log_307.ps1
   ```
3. Verifique os logs em `agent/agente_log.txt`

### Problema: Erro de conexão com banco de dados

**Solução:**
1. Verifique se o arquivo `serv/print_events.db` existe
2. Se não existir, execute:
   ```bash
   cd serv
   python recreate_database.py
   ```

### Problema: Não consigo fazer login

**Solução:**
1. Verifique se o usuário existe no banco
2. Execute o script de reset de senhas:
   ```bash
   python resetar_senhas_automatico.py
   ```
3. Ou crie um novo usuário admin:
   ```bash
   python criar_usuario_admin.py
   ```

### Problema: Servidor não inicia

**Solução:**
1. Verifique se a porta 5002 está livre:
   ```bash
   # Windows
   netstat -ano | findstr :5002
   
   # Linux/Mac
   lsof -i :5002
   ```
2. Altere a porta em `config.json` se necessário
3. Verifique os logs em `serv/servidor.log`

### Problema: IA não funciona

**Solução:**
1. Verifique se as dependências de IA estão instaladas:
   ```bash
   pip install numpy scikit-learn prophet openai
   ```
2. Para chatbot, verifique se a chave de API está configurada:
   ```bash
   # Verificar
   python -c "import os; print(os.getenv('OPENAI_API_KEY'))"
   ```
3. Veja `CONFIGURACAO_OPENAI.md` para mais detalhes

### Problema: Email não envia alertas

**Solução:**
1. Verifique as variáveis de ambiente de email
2. Para Gmail, use uma "Senha de App" (não a senha normal)
3. Teste a conexão SMTP:
   ```python
   import smtplib
   server = smtplib.SMTP('smtp.gmail.com', 587)
   server.starttls()
   server.login('seu_email@gmail.com', 'senha_app')
   ```

---

## 📚 Documentação Adicional

- **`CONFIGURACAO_OPENAI.md`** - Guia completo de configuração OpenAI
- **`CONFIGURAR_GROQ.md`** - Guia de configuração Groq (alternativa gratuita)
- **`STATUS_IMPLEMENTACAO_FINAL.md`** - Status das implementações
- **`RESUMO_IMPLEMENTACAO.md`** - Resumo das funcionalidades
- **`VALIDACAO_COMPLETA.md`** - Validação do projeto
- **`RELATORIO_VALIDACAO.md`** - Relatório de validação

---

## 🤝 Contribuição

Este é um projeto interno. Para sugestões ou melhorias:

1. Documente a funcionalidade proposta
2. Teste localmente antes de sugerir
3. Mantenha compatibilidade com o código existente
4. Siga os padrões de código do projeto

### Padrões de Código

- **Python:** PEP 8
- **HTML:** Indentação de 2 espaços
- **CSS:** BEM naming convention
- **JavaScript:** ES6+

---

## 📝 Licença

Este projeto é de **uso interno** e não possui licença pública.

---

## 🎯 Conceitos Importantes

### Impressão vs Páginas

- **Impressão** = Folha lógica (job/documento) = `COUNT(*)`
- **Páginas** = Folha física (folha de papel real, considerando duplex)

### Estrutura de Dados

O banco de dados armazena:
- **Eventos de impressão** - Cada job de impressão
- **Usuários** - Usuários do sistema e do Windows
- **Setores** - Organização por departamentos
- **Impressoras** - Impressoras monitoradas
- **Configurações** - Preços, quotas, metas, etc.

---

## 📞 Suporte

Para dúvidas ou problemas:

1. Consulte a documentação adicional
2. Verifique os logs (`serv/servidor.log` e `agent/agente_log.txt`)
3. Revise a seção de Troubleshooting
4. Verifique o status do sistema em `Administração > Status`

---

**Desenvolvido com ❤️ para melhorar o monitoramento de impressões corporativas!**

---

## 📊 Estatísticas do Projeto

- **Linhas de Código:** ~15.000+
- **Módulos Python:** 26+
- **Templates HTML:** 23+
- **Endpoints API:** 50+
- **Funcionalidades de IA:** 10
- **Funcionalidades Principais:** 30+

---

**Última atualização:** 2025-01-07
