#!/bin/bash
# Script para configurar HTTPS com Let's Encrypt e Nginx

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "======================================================================"
echo "CONFIGURACAO HTTPS - PRINT MONITOR"
echo "======================================================================"
echo ""

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}ERRO: Execute como root (sudo)${NC}"
    exit 1
fi

# Solicitar domínio
read -p "Digite o dominio (ex: monitor.empresa.com): " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo -e "${RED}ERRO: Dominio nao pode ser vazio${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}Configurando HTTPS para: ${DOMAIN}${NC}"
echo ""

# 1. Instalar Nginx
echo -e "${BLUE}Passo 1: Instalando Nginx...${NC}"
apt-get update
apt-get install -y nginx
echo -e "${GREEN}OK: Nginx instalado${NC}"
echo ""

# 2. Instalar Certbot
echo -e "${BLUE}Passo 2: Instalando Certbot...${NC}"
apt-get install -y certbot python3-certbot-nginx
echo -e "${GREEN}OK: Certbot instalado${NC}"
echo ""

# 3. Configurar Nginx
echo -e "${BLUE}Passo 3: Configurando Nginx...${NC}"
cp nginx_print_monitor.conf /etc/nginx/sites-available/print-monitor
sed -i "s/seu-dominio.com/${DOMAIN}/g" /etc/nginx/sites-available/print-monitor

# Criar link simbólico
ln -sf /etc/nginx/sites-available/print-monitor /etc/nginx/sites-enabled/

# Remover configuração padrão
rm -f /etc/nginx/sites-enabled/default

# Testar configuração
nginx -t
echo -e "${GREEN}OK: Nginx configurado${NC}"
echo ""

# 4. Obter certificado SSL
echo -e "${BLUE}Passo 4: Obtendo certificado SSL (Let's Encrypt)...${NC}"
echo -e "${YELLOW}IMPORTANTE: Certifique-se de que o dominio aponta para este servidor!${NC}"
read -p "Pressione Enter para continuar..."

certbot --nginx -d ${DOMAIN} -d www.${DOMAIN} --non-interactive --agree-tos --email admin@${DOMAIN} --redirect

echo -e "${GREEN}OK: Certificado SSL obtido${NC}"
echo ""

# 5. Configurar renovação automática
echo -e "${BLUE}Passo 5: Configurando renovacao automatica...${NC}"
systemctl enable certbot.timer
systemctl start certbot.timer
echo -e "${GREEN}OK: Renovacao automatica configurada${NC}"
echo ""

# 6. Reiniciar Nginx
echo -e "${BLUE}Passo 6: Reiniciando Nginx...${NC}"
systemctl restart nginx
systemctl enable nginx
echo -e "${GREEN}OK: Nginx reiniciado${NC}"
echo ""

# 7. Configurar firewall
echo -e "${BLUE}Passo 7: Configurando firewall...${NC}"
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp
echo -e "${GREEN}OK: Firewall configurado${NC}"
echo ""

# 8. Atualizar .env
echo -e "${BLUE}Passo 8: Atualizando configuracoes...${NC}"
if [ -f /app/.env ]; then
    sed -i 's/SESSION_COOKIE_SECURE=False/SESSION_COOKIE_SECURE=True/' /app/.env
    echo -e "${GREEN}OK: SESSION_COOKIE_SECURE atualizado${NC}"
fi
echo ""

echo "======================================================================"
echo -e "${GREEN}HTTPS CONFIGURADO COM SUCESSO!${NC}"
echo "======================================================================"
echo ""
echo "Acesse o sistema em: https://${DOMAIN}"
echo ""
echo "Certificado SSL renovado automaticamente a cada 90 dias"
echo ""
echo "======================================================================"

