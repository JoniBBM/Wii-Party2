FROM python:3.11-slim

# Setzt das Arbeitsverzeichnis im Container
WORKDIR /app

# Systemabhängigkeiten installieren
RUN apt-get update && apt-get install -y sqlite3 libsqlite3-dev build-essential && rm -rf /var/lib/apt/lists/*

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

# SSL/HTTPS Umgebungsvariablen
ENV USE_HTTPS=false
ENV HTTPS_PORT=5000
ENV HTTP_PORT=8080
ENV SSL_CERT_PATH=/app/certs/cert.pem
ENV SSL_KEY_PATH=/app/certs/key.pem

# Ports für HTTP und HTTPS exponieren
EXPOSE 5000 8080

# Erstelle certs Verzeichnis
RUN mkdir -p /app/certs

# Standardbefehl zum Starten der Anwendung (HTTP)
# Für HTTPS: docker run mit "python run_https.py" überschreiben
CMD ["flask", "run", "--host=0.0.0.0", "--port=8080"]
