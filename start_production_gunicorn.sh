#!/bin/bash
# Script para iniciar o servidor em produção usando Gunicorn (Linux/Mac)
# Gunicorn é um servidor WSGI adequado para produção

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Diretório base
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

# Carrega variáveis de ambiente do .env
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo -e "${GREEN}✅ Arquivo .env carregado${NC}"
else
    echo -e "${YELLOW}⚠️  Arquivo .env não encontrado${NC}"
    echo "   Usando variáveis de ambiente do sistema"
fi

# Verifica se Gunicorn está instalado
if ! command -v gunicorn &> /dev/null; then
    echo -e "${RED}❌ ERRO: Gunicorn não está instalado!${NC}"
    echo "   Instale com: pip install gunicorn"
    exit 1
fi

# Verifica ambiente
if [ "$FLASK_ENV" != "production" ]; then
    echo -e "${YELLOW}⚠️  AVISO: FLASK_ENV não está definido como 'production'${NC}"
    echo "   Valor atual: $FLASK_ENV"
    read -p "   Continuar mesmo assim? (s/N): " resposta
    if [ "$resposta" != "s" ]; then
        echo -e "${RED}❌ Cancelado. Configure FLASK_ENV=production antes de continuar.${NC}"
        exit 1
    fi
fi

# Verifica SECRET_KEY
if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "sua-chave-secreta-aqui" ]; then
    echo -e "${RED}❌ ERRO: SECRET_KEY não está configurada!${NC}"
    echo "   Configure SECRET_KEY no arquivo .env ou variáveis de ambiente"
    exit 1
fi

# Configurações
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-5002}
WORKERS=${WORKERS:-4}
THREADS=${THREADS:-2}
TIMEOUT=${TIMEOUT:-120}

echo "======================================================================"
echo "🚀 INICIANDO SERVIDOR EM PRODUÇÃO (Gunicorn)"
echo "======================================================================"
echo "📍 Host: $HOST"
echo "🔌 Porta: $PORT"
echo "👷 Workers: $WORKERS"
echo "🧵 Threads por worker: $THREADS"
echo "⏱️  Timeout: $TIMEOUT segundos"
echo "🌍 Ambiente: ${FLASK_ENV:-development}"
echo "🔐 SECRET_KEY: ${GREEN}✅ Configurada${NC}"
echo "======================================================================"
echo ""
echo -e "${GREEN}✅ Servidor iniciado com sucesso!${NC}"
echo "🌐 Acesse: http://${HOST:-localhost}:$PORT"
echo ""
echo "⚠️  Para parar o servidor, pressione Ctrl+C"
echo "======================================================================"
echo ""

# Inicia servidor Gunicorn
cd serv
gunicorn \
    --bind "$HOST:$PORT" \
    --workers $WORKERS \
    --threads $THREADS \
    --timeout $TIMEOUT \
    --worker-class gthread \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --preload \
    servidor:app

