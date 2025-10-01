# --- Dockerfile para el frontend (visor) ---
FROM python:3.12-slim

# Evitar prompts de apt
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema necesarias para matplotlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6 \
    libpng16-16 \
    libjpeg62-turbo \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de la app
WORKDIR /app

# Copiar requirements del visor
COPY requirements-visor.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements-visor.txt

# Copiar código del visor
COPY . .

# Exponer puerto de Streamlit
EXPOSE 8501
CMD ["streamlit", "run", "run_visor.py", "--server.port=8501", "--server.address=0.0.0.0"]