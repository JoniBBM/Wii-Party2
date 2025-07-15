FROM python:3.13-slim

# Setzt das Arbeitsverzeichnis im Container
WORKDIR /app

# Systemabhängigkeiten installieren
RUN apt-get update && apt-get install -y \
    sqlite3 libsqlite3-dev \
    postgresql-client libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python Output Buffering deaktivieren, damit print() Anweisungen sofort in den Logs erscheinen
ENV PYTHONUNBUFFERED=1

# requirements.txt kopieren und Pakete installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Den gesamten Inhalt des aktuellen Verzeichnisses (Build-Kontext) in das Arbeitsverzeichnis im Container kopieren
COPY . .

# Umgebungsvariablen setzen
ENV FLASK_APP=app:create_app
ENV FLASK_DEBUG=1
# Stellt sicher, dass Python Module im /app Verzeichnis findet
ENV PYTHONPATH=/app

# Standardbefehl zum Starten der Anwendung
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
