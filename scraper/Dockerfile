FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Node.js and npm for Cloudflare Wrangler
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copiamos primero los requerimientos para usar el cache de Docker
COPY scraper/requirements.txt /app/scraper/requirements.txt
RUN pip install --no-cache-dir -r /app/scraper/requirements.txt

# Copiamos todo el proyecto
COPY . /app

# Forzar permisos de ejecución para el script de entrada
RUN chmod +x /app/scraper/docker_entrypoint_bil.sh

# Por defecto trabajamos en scraper para tu pipeline original
WORKDIR /app/scraper

CMD ["python", "linkedin_public_mvp.py"]
