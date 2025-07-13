#!/usr/bin/env python3
"""
HTTPS-Server Starter für Wii-Party
Startet die Flask-App mit SSL-Support für lokale Kamera-Nutzung
"""

import os
import sys
from app import create_app
from config import Config

def check_ssl_files():
    """Prüft ob SSL-Zertifikat und Schlüssel vorhanden sind"""
    cert_path = Config.SSL_CERT_PATH
    key_path = Config.SSL_KEY_PATH
    
    if not os.path.exists(cert_path):
        print(f"❌ SSL-Zertifikat nicht gefunden: {cert_path}")
        print("💡 Führe 'python generate_cert.py' aus um ein Zertifikat zu erstellen")
        return False
        
    if not os.path.exists(key_path):
        print(f"❌ SSL-Schlüssel nicht gefunden: {key_path}")
        print("💡 Führe 'python generate_cert.py' aus um einen Schlüssel zu erstellen")
        return False
    
    print(f"✅ SSL-Zertifikat gefunden: {cert_path}")
    print(f"✅ SSL-Schlüssel gefunden: {key_path}")
    return True

def get_ssl_context():
    """Erstellt SSL-Context für Flask"""
    try:
        import ssl
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(Config.SSL_CERT_PATH, Config.SSL_KEY_PATH)
        return context
    except Exception as e:
        print(f"❌ Fehler beim Erstellen des SSL-Context: {e}")
        return None

def main():
    print("🎮 Wii-Party HTTPS Server")
    print("=" * 30)
    
    # Prüfe SSL-Dateien
    if not check_ssl_files():
        sys.exit(1)
    
    # Erstelle SSL-Context
    ssl_context = get_ssl_context()
    if not ssl_context:
        sys.exit(1)
    
    # Setze Umgebungsvariablen für HTTPS
    os.environ['USE_HTTPS'] = 'true'
    os.environ['SESSION_COOKIE_SECURE'] = 'true'
    
    # Erstelle Flask-App
    app = create_app()
    
    # Server-Konfiguration
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', Config.HTTPS_PORT))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 Starte HTTPS-Server auf https://{host}:{port}")
    print(f"🔐 SSL-Zertifikat: {Config.SSL_CERT_PATH}")
    print(f"🔑 SSL-Schlüssel: {Config.SSL_KEY_PATH}")
    print(f"📱 Kamera-Zugriff: Verfügbar über HTTPS")
    print("\n⚠️  Bei selbstsignierten Zertifikaten:")
    print("   Browser zeigt Warnung → 'Erweitert' → 'Trotzdem fortfahren'")
    print("\n" + "=" * 30)
    
    try:
        app.run(
            host=host,
            port=port,
            debug=debug,
            ssl_context=ssl_context,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n👋 Server gestoppt")
    except Exception as e:
        print(f"\n❌ Server-Fehler: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()