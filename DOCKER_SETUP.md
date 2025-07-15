# Docker Setup für Wii Party U Deluxe

## Überblick

Das Projekt unterstützt sowohl SQLite (für Development) als auch PostgreSQL (für Production) in Docker-Containern.

## Development Setup (SQLite)

Für lokale Entwicklung mit SQLite:

```bash
# .env Datei erstellen
cp .env.example .env

# Normale Flask-Entwicklung
python -m flask run
```

## Docker Setup (PostgreSQL)

### 1. Entwicklung mit Docker Compose

```bash
# Container starten
docker-compose up -d

# Logs anzeigen
docker-compose logs -f

# Container stoppen
docker-compose down
```

Die Anwendung ist verfügbar unter: `http://localhost:5001`

### 2. Produktion mit Docker Compose

```bash
# Production Setup
docker-compose -f docker-compose.prod.yml up -d

# Mit SSL/HTTPS
docker-compose -f docker-compose.prod.yml up -d
```

## Datenbankmigrationen

### Erste Einrichtung

```bash
# In den Web-Container einsteigen
docker-compose exec web bash

# Migrations-Ordner initialisieren (falls nicht vorhanden)
flask db init

# Migration erstellen
flask db migrate -m "Initial migration"

# Migration ausführen
flask db upgrade
```

### Neue Migrationen

```bash
# Container-Bash
docker-compose exec web bash

# Neue Migration erstellen
flask db migrate -m "Beschreibung der Änderung"

# Migration anwenden
flask db upgrade
```

## Datenbank-Management

### Datenbank zurücksetzen

```bash
# Container stoppen
docker-compose down

# Volumes löschen (ACHTUNG: Alle Daten gehen verloren!)
docker volume rm wii-party2_postgres_data

# Container neu starten
docker-compose up -d
```

### Datenbank-Backup

```bash
# Backup erstellen
docker-compose exec db pg_dump -U wii_party_user wii_party > backup.sql

# Backup wiederherstellen
docker-compose exec -T db psql -U wii_party_user wii_party < backup.sql
```

## Konfiguration

### Umgebungsvariablen

- `DATABASE_URL`: Datenbankverbindung
- `SECRET_KEY`: Flask Secret Key
- `ADMIN_USERNAME`: Admin-Benutzername
- `ADMIN_PASSWORD`: Admin-Passwort
- `SESSION_COOKIE_SECURE`: HTTPS-Cookie-Sicherheit
- `LOG_TO_STDOUT`: Logging-Konfiguration

### Volumes

- `postgres_data`: PostgreSQL-Daten
- `web_uploads`: Hochgeladene Dateien
- `web_saved_rounds`: Gespeicherte Spielrunden

## Troubleshooting

### Container startet nicht

```bash
# Logs prüfen
docker-compose logs db
docker-compose logs web

# Container neu bauen
docker-compose build --no-cache
```

### Datenbankverbindung fehlgeschlagen

```bash
# Datenbankcontainer-Status prüfen
docker-compose ps db

# Datenbankcontainer-Logs prüfen
docker-compose logs db

# Verbindung testen
docker-compose exec db pg_isready -U wii_party_user -d wii_party
```

### Migration-Fehler

```bash
# Migrations-Status prüfen
docker-compose exec web flask db current

# Migration-History anzeigen
docker-compose exec web flask db history

# Migration zurücksetzen
docker-compose exec web flask db downgrade
```

## Sicherheitshinweise

1. **Passwörter ändern**: Alle Standard-Passwörter in der Produktion ändern
2. **SSL/TLS**: HTTPS in der Produktion aktivieren
3. **Firewall**: Nur notwendige Ports öffnen
4. **Backups**: Regelmäßige Datenbank-Backups erstellen
5. **Updates**: Container-Images regelmäßig aktualisieren

## Monitoring

```bash
# Container-Status
docker-compose ps

# Ressourcenverbrauch
docker stats

# Logs live verfolgen
docker-compose logs -f web db
```