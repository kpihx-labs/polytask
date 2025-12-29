# Image Debian-based (compatible avec les libs Python lourdes comme Pandas/Psycopg2)
FROM python:3.11-slim

WORKDIR /app

# Désactive le buffering Python pour que stdout/stderr remonte immédiatement
ENV PYTHONUNBUFFERED=1

# Installation des dépendances système nécessaires pour compiler psycopg2
# On utilise apt-get (Debian) et pas apk (Alpine)
RUN apt-get update && \
    apt-get install -y libpq-dev gcc git && \
    rm -rf /var/lib/apt/lists/*

# Installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY . .

# Port Streamlit
EXPOSE 8501

# Lancement
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]