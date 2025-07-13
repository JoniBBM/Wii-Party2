# 🔐 HTTPS-Setup für Wii-Party Kamera-Funktionalität

## Problem
Moderne Browser erlauben `getUserMedia()` (Kamera/Mikrofon-Zugriff) nur über HTTPS oder localhost. Bei HTTP-Zugriff über lokale IP-Adressen funktioniert die Kamera-Funktion nicht.

## 🚀 Schnell-Setup

### 1. SSL-Zertifikat generieren
```bash
# Zertifikat für lokale IP und localhost erstellen
python generate_cert.py
```

### 2. Server starten

#### Option A: Direkt mit Python
```bash
# HTTPS-Server starten
python run_https.py
```

#### Option B: Mit Docker
```bash
# Nur HTTPS-Service starten
docker-compose up web-https

# Oder beide Services (HTTP + HTTPS)
docker-compose up
```

### 3. Zugriff
- **HTTPS (mit Kamera)**: https://192.168.1.XXX:5000
- **HTTP (ohne Kamera)**: http://192.168.1.XXX:8080

## 📋 Detaillierte Anleitung

### SSL-Zertifikat erstellen

#### mkcert (Empfohlen)
```bash
# Installation (macOS)
brew install mkcert

# Installation (Linux)
curl -JLO "https://dl.filippo.io/mkcert/latest?for=linux/amd64"
chmod +x mkcert-v*-linux-amd64
sudo mv mkcert-v*-linux-amd64 /usr/local/bin/mkcert

# Root CA installieren
mkcert -install

# Zertifikat generieren
python generate_cert.py
# -> Wähle 'm' für mkcert
```

#### OpenSSL (Fallback)
```bash
# Ohne mkcert (selbstsigniert)
python generate_cert.py
# -> Automatisch OpenSSL wenn mkcert nicht verfügbar
```

### Browser-Setup

#### Chrome
1. Zertifikat-Warnung: **"Erweitert"** → **"Trotzdem fortfahren"**
2. Optional für localhost: `chrome://flags` → `Allow invalid certificates for resources loaded from localhost`

#### Firefox  
1. Zertifikat-Warnung: **"Erweitert"** → **"Risiko akzeptieren"**
2. Optional: `about:config` → `security.tls.insecure_fallback_hosts` → `localhost,127.0.0.1`

#### Safari
1. Zertifikat-Warnung: **"Details anzeigen"** → **"Website besuchen"**

## 🐳 Docker-Setup

### Struktur
```
docker-compose.yml
├── web (HTTP:8080)     # Standard-Zugriff ohne Kamera
└── web-https (HTTPS:5000) # Kamera-Zugriff über HTTPS
```

### Commands
```bash
# Beide Services starten
docker-compose up

# Nur HTTPS (für Kamera)
docker-compose up web-https

# Nur HTTP (ohne Kamera)  
docker-compose up web

# Im Hintergrund
docker-compose up -d web-https
```

## 🛠️ Umgebungsvariablen

### .env Datei (Optional)
```bash
# HTTPS-Konfiguration
USE_HTTPS=true
HTTPS_PORT=5000
HTTP_PORT=8080
SSL_CERT_PATH=./certs/cert.pem
SSL_KEY_PATH=./certs/key.pem
SESSION_COOKIE_SECURE=true
FORCE_HTTPS_REDIRECT=false

# Flask-Standard
FLASK_DEBUG=true
FLASK_HOST=0.0.0.0
```

## 🔧 Troubleshooting

### Zertifikat-Fehler
```bash
# Zertifikat-Info anzeigen
openssl x509 -in certs/cert.pem -text -noout

# Neue Zertifikate generieren
rm -rf certs/
python generate_cert.py
```

### Browser zeigt "Unsicher"
- **Chrome**: `chrome://flags` → `Treat risky downloads as active mixed content`
- **Firefox**: `about:config` → `security.mixed_content.block_active_content = false`

### Port-Konflikte
```bash
# Verwendete Ports prüfen
lsof -i :5000
lsof -i :8080

# Ports in docker-compose.yml ändern
ports:
  - "5001:5000"  # Host:Container
```

### Docker-Probleme
```bash
# Container neu bauen
docker-compose build --no-cache

# Logs anzeigen
docker-compose logs web-https

# Container zurücksetzen
docker-compose down
docker-compose up --build
```

## 📱 Gerätespezifische Hinweise

### Smartphone/Tablet
- **iOS Safari**: Zertifikat-Warnung akzeptieren → Funktioniert
- **Android Chrome**: Zertifikat-Warnung akzeptieren → Funktioniert
- **Android Firefox**: Möglicherweise zusätzliche Einstellungen nötig

### Notebook ohne Kamera
- HTTPS ist trotzdem empfohlen für einheitliche Entwicklung
- Kamera-Features werden automatisch deaktiviert/versteckt

### LAN-Party Setup
1. Ein Gerät hostet (mit HTTPS)
2. Alle anderen verbinden sich über IP
3. Jeder akzeptiert Zertifikat-Warnung einmalig

## ⚡ Performance-Tipps

### Produktions-Setup
```bash
# Flask ohne Debug-Modus
export FLASK_DEBUG=false

# SSL-Terminierung mit nginx (optional)
# nginx → Flask HTTP (intern)
```

### Entwicklung
```bash
# Auto-Reload bei Code-Änderungen
export FLASK_DEBUG=true

# Logs für Debugging
export LOG_TO_STDOUT=true
```

## 🎯 Alternative Lösungen

### Browser-Flags (nur für Entwicklung)
```bash
# Chrome mit unsicheren Origins
google-chrome --unsafely-treat-insecure-origin-as-secure="http://192.168.1.100:8080"

# Firefox Entwickler-Edition
firefox --profile /tmp/dev-profile
```

### Localhost-Tunneling
```bash
# ngrok (öffentlicher Tunnel)
ngrok http 5000

# localtunnel
npx localtunnel --port 5000
```

---

## 📞 Support

Bei Problemen:
1. Logs prüfen: `docker-compose logs web-https`
2. Browser-Console öffnen (F12)
3. Zertifikat neu generieren: `python generate_cert.py`
4. Port-Konflikte prüfen: `lsof -i :5000`

**Wichtig**: HTTPS ist nur für lokale Entwicklung! Für Produktion echte Zertifikate verwenden.