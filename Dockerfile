FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para compilación si procede
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Exponer puerto de la API REST
EXPOSE 8000

# Comando por defecto para iniciar el servidor FastAPI
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--ws", "none"]
