#!/bin/bash
# Script de deploy automatizado para produção
# Configura e inicia o servidor em produção

set -e  # Para em caso de erro

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "======================================================================"
echo "🚀 DEPLOY AUTOMATIZADO - PRINT MONITOR"
echo "======================================================================"
echo ""

# Diretório base
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

# 1. Verificar Python
echo -e "${BLUE}📋 Passo 1: Verificando Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 não encontrado!${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✅ $PYTHON_VERSION${NC}"
echo ""

# 2. Verificar/Criar ambiente virtual
echo -e "${BLUE}📋 Passo 2: Configurando ambiente virtual...${NC}"
if [ ! -d "venv" ]; then
    echo "   Criando ambiente virtual..."
    python3 -m venv venv
fi
source venv/bin/activate
echo -e "${GREEN}✅ Ambiente virtual ativado${NC}"
echo ""

# 3. Instalar dependências
echo -e "${BLUE}📋 Passo 3: Instalando dependências...${NC}"
pip install --upgrade pip
pip install -r requirements.txt
pip install waitress gunicorn  # Servidores WSGI
echo -e "${GREEN}✅ Dependências instaladas${NC}"
echo ""

# 4. Verificar/Criar arquivo .env
echo -e "${BLUE}📋 Passo 4: Configurando variáveis de ambiente...${NC}"
if [ ! -f .env ]; then
    if [ -f .env.production ]; then
        echo "   Copiando .env.production para .env..."
        cp .env.production .env
        echo -e "${YELLOW}⚠️  IMPORTANTE: Revise o arquivo .env e ajuste as configurações!${NC}"
    else
        echo -e "${RED}❌ Arquivo .env não encontrado e .env.production não existe!${NC}"
        echo "   Crie um arquivo .env baseado em env.example"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Arquivo .env já existe${NC}"
fi

# Verifica SECRET_KEY
source .env 2>/dev/null || true
if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "sua-chave-secreta-aqui" ]; then
    echo -e "${YELLOW}⚠️  SECRET_KEY não configurada ou usando valor padrão${NC}"
    echo "   Gerando nova SECRET_KEY..."
    python3 gerar_secret_key.py
    echo -e "${YELLOW}   Adicione a SECRET_KEY gerada ao arquivo .env${NC}"
    read -p "   Pressione Enter após adicionar a SECRET_KEY ao .env..."
fi
echo ""

# 5. Criar diretórios necessários
echo -e "${BLUE}📋 Passo 5: Criando diretórios...${NC}"
mkdir -p serv/backups
mkdir -p serv/logs
mkdir -p /var/log/print-monitor 2>/dev/null || true
echo -e "${GREEN}✅ Diretórios criados${NC}"
echo ""

# 6. Inicializar banco de dados
echo -e "${BLUE}📋 Passo 6: Verificando banco de dados...${NC}"
if [ ! -f "serv/print_events.db" ]; then
    echo "   Criando banco de dados..."
    cd serv
    python3 -c "from servidor import init_db; init_db()" || python3 recreate_database.py
    cd ..
    echo -e "${GREEN}✅ Banco de dados criado${NC}"
else
    echo -e "${GREEN}✅ Banco de dados já existe${NC}"
fi
echo ""

# 7. Verificar permissões
echo -e "${BLUE}📋 Passo 7: Verificando permissões...${NC}"
chmod +x start_production_gunicorn.sh
chmod +x start_production_waitress.py
echo -e "${GREEN}✅ Permissões configuradas${NC}"
echo ""

# 8. Resumo
echo "======================================================================"
echo -e "${GREEN}✅ DEPLOY CONCLUÍDO COM SUCESSO!${NC}"
echo "======================================================================"
echo ""
echo "📋 Próximos passos:"
echo ""
echo "1. Revise o arquivo .env e ajuste as configurações:"
echo "   - SECRET_KEY (já configurada)"
echo "   - FLASK_ENV=production"
echo "   - DEBUG=False"
echo "   - SESSION_COOKIE_SECURE=True (se usar HTTPS)"
echo ""
echo "2. Para iniciar o servidor:"
echo "   - Linux/Mac: ./start_production_gunicorn.sh"
echo "   - Windows: start_production_waitress.bat"
echo "   - Ou: python start_production_waitress.py"
echo ""
echo "3. Para usar systemd (Linux):"
echo "   sudo cp print-monitor.service /etc/systemd/system/"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable print-monitor"
echo "   sudo systemctl start print-monitor"
echo ""
echo "4. Configure firewall:"
echo "   sudo ufw allow 5002/tcp"
echo ""
echo "======================================================================"

