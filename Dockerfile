# Dockerfile para o Servidor
FROM python:3.11-slim

WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copia requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código do servidor
COPY serv/ ./serv/
COPY config.json ./

# Cria diretório para banco de dados
RUN mkdir -p /app/data

# Variáveis de ambiente
ENV FLASK_APP=servidor.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Porta
EXPOSE 5002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5002/health')"

# Comando para iniciar
WORKDIR /app/serv
CMD ["python", "servidor.py"]

