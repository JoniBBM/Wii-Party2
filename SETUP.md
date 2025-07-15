# Wii Party U Deluxe - Setup Guide

## Schnellstart

### 1. Admin-Passwort setzen
```bash
# .env Datei bearbeiten
nano .env

# Diese Zeile ändern:
ADMIN_PASSWORD=DeinNeuesPasswort123!
```

### 2. Lokal ohne Docker starten
```bash
# Abhängigkeiten installieren
pip install -r requirements.txt

# Anwendung starten
python -m flask run

# Verfügbar unter: http://localhost:5000
```

### 3. Mit Docker starten (empfohlen)
```bash
# Container starten
docker-compose up -d

# Verfügbar unter: http://localhost:5001
```

## Erster Admin-Login

1. Gehe zu: `http://localhost:5001` (oder `:5000` ohne Docker)
2. Klicke auf "Admin Login"  
3. Benutzername: `admin`
4. Passwort: Was du in der `.env` Datei gesetzt hast

## Datenbank-Setup

### Erste Einrichtung (Docker)
```bash
# Container-Shell öffnen
docker-compose exec web bash

# Datenbank initialisieren
flask db upgrade

# Admin-User erstellen (falls nötig)
python create_admin.py
```

### Lokale Entwicklung
```bash
# Datenbank initialisieren
flask db upgrade

# Admin-User erstellen
python create_admin.py
```

## Wichtige Befehle

### Docker
```bash
# Container starten
docker-compose up -d

# Container stoppen
docker-compose down

# Logs anzeigen
docker-compose logs -f web

# Container neu bauen
docker-compose build --no-cache
```

### Datenbank
```bash
# Migration erstellen
flask db migrate -m "Beschreibung"

# Migration anwenden
flask db upgrade

# Datenbank zurücksetzen (VORSICHT!)
rm app.db  # oder Docker Volume löschen
flask db upgrade
```

## Konfiguration

### .env Datei
```bash
# Wichtige Einstellungen:
ADMIN_USERNAME=admin
ADMIN_PASSWORD=DeinSicheresPasswort123!
SECRET_KEY=dein-sehr-geheimer-schluessel
DATABASE_URL=sqlite:///app.db
```

### Docker vs. Lokal
- **Lokal**: Verwendet SQLite (`app.db`)
- **Docker**: Verwendet PostgreSQL in separatem Container

## Troubleshooting

### Container startet nicht
```bash
# Logs prüfen
docker-compose logs

# Container neu bauen
docker-compose build --no-cache
```

### Admin-Login funktioniert nicht
1. Prüfe `.env` Datei
2. Stelle sicher, dass `create_admin.py` ausgeführt wurde
3. Prüfe die Datenbank mit `flask shell`

### Datenbank-Probleme
```bash
# Datenbank-Status prüfen
docker-compose exec web flask db current

# Datenbank zurücksetzen
docker-compose down
docker volume rm wii-party2_postgres_data
docker-compose up -d
```

Das war's! Jetzt ist es viel einfacher zu verwenden.