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

COPY scraper/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything from the project root
COPY . .

# Cambiamos al directorio del scraper para que los imports relativos funcionen
WORKDIR /app/scraper

CMD ["python", "linkedin_public_mvp.py"]
