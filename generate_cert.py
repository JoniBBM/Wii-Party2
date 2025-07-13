#!/usr/bin/env python3
"""
SSL-Zertifikat Generator für Wii-Party lokale HTTPS-Entwicklung
Erstellt selbstsignierte Zertifikate für lokale IP-Adressen und localhost
"""

import os
import sys
import subprocess
import socket
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timedelta
import ipaddress

def get_local_ip():
    """Ermittelt die lokale IP-Adresse"""
    try:
        # Verbinde zu einem externen Server um lokale IP zu ermitteln
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        return local_ip
    except Exception:
        return "192.168.1.100"  # Fallback

def check_mkcert():
    """Prüft ob mkcert verfügbar ist und bietet Installation an"""
    try:
        result = subprocess.run(['mkcert', '-version'], 
                              capture_output=True, text=True, check=True)
        print(f"✅ mkcert gefunden: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ mkcert nicht gefunden")
        print("\n📖 mkcert Installation:")
        print("macOS: brew install mkcert")
        print("Linux: curl -JLO \"https://dl.filippo.io/mkcert/latest?for=linux/amd64\" && chmod +x mkcert-v*-linux-amd64 && sudo mv mkcert-v*-linux-amd64 /usr/local/bin/mkcert")
        print("Windows: scoop install mkcert oder choco install mkcert")
        print("\nDanach: mkcert -install")
        return False

def generate_with_mkcert(domains):
    """Generiert Zertifikat mit mkcert (empfohlen)"""
    print(f"\n🔧 Erstelle Zertifikat mit mkcert für: {', '.join(domains)}")
    
    # Erstelle certs Verzeichnis
    os.makedirs('certs', exist_ok=True)
    
    try:
        # mkcert installieren falls noch nicht geschehen
        subprocess.run(['mkcert', '-install'], check=True, capture_output=True)
        
        # Zertifikat erstellen
        cmd = ['mkcert', '-key-file', 'certs/key.pem', '-cert-file', 'certs/cert.pem'] + domains
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        print("✅ Zertifikat erfolgreich erstellt!")
        print(f"   Zertifikat: certs/cert.pem")
        print(f"   Privater Schlüssel: certs/key.pem")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Fehler bei mkcert: {e}")
        print(f"   Stdout: {e.stdout}")
        print(f"   Stderr: {e.stderr}")
        return False

def generate_with_openssl(domains):
    """Generiert selbstsigniertes Zertifikat mit Python cryptography"""
    print(f"\n🔧 Erstelle selbstsigniertes Zertifikat für: {', '.join(domains)}")
    
    # Erstelle certs Verzeichnis
    os.makedirs('certs', exist_ok=True)
    
    # Generiere privaten Schlüssel
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    # Erstelle Subject für Zertifikat
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "DE"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Local"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Development"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Wii-Party Local Dev"),
        x509.NameAttribute(NameOID.COMMON_NAME, domains[0]),
    ])
    
    # Alternative Namen (SAN) für alle Domains/IPs
    san_list = []
    for domain in domains:
        try:
            # Prüfe ob es eine IP-Adresse ist
            ip = ipaddress.ip_address(domain)
            san_list.append(x509.IPAddress(ip))
        except ValueError:
            # Es ist ein Domain-Name
            san_list.append(x509.DNSName(domain))
    
    # Erstelle Zertifikat
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName(san_list),
        critical=False,
    ).sign(private_key, hashes.SHA256())
    
    # Speichere Zertifikat
    with open("certs/cert.pem", "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    # Speichere privaten Schlüssel
    with open("certs/key.pem", "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    print("✅ Selbstsigniertes Zertifikat erstellt!")
    print(f"   Zertifikat: certs/cert.pem")
    print(f"   Privater Schlüssel: certs/key.pem")
    print("\n⚠️  WICHTIG: Browser werden eine Warnung anzeigen!")
    print("   Klicke auf 'Erweitert' → 'Trotzdem fortfahren'")
    return True

def main():
    print("🎮 Wii-Party HTTPS-Zertifikat Generator")
    print("=" * 50)
    
    # Ermittle lokale IP
    local_ip = get_local_ip()
    print(f"📍 Lokale IP-Adresse: {local_ip}")
    
    # Standarddomains
    domains = ["localhost", "127.0.0.1", local_ip]
    
    # Benutzer nach zusätzlichen IPs/Domains fragen
    print(f"\n📝 Standard-Domains: {', '.join(domains)}")
    additional = input("Zusätzliche IP-Adressen/Domains (komma-separiert, Enter für keine): ").strip()
    
    if additional:
        additional_domains = [d.strip() for d in additional.split(',') if d.strip()]
        domains.extend(additional_domains)
        print(f"📝 Alle Domains: {', '.join(domains)}")
    
    # Prüfe mkcert Verfügbarkeit
    if check_mkcert():
        choice = input("\n❓ Verwende mkcert (empfohlen) oder OpenSSL? [m/o] (Standard: m): ").lower().strip()
        use_mkcert = choice != 'o'
    else:
        print("\n🔄 Verwende Python cryptography für selbstsigniertes Zertifikat...")
        use_mkcert = False
    
    # Generiere Zertifikat
    if use_mkcert:
        success = generate_with_mkcert(domains)
    else:
        success = generate_with_openssl(domains)
    
    if success:
        print("\n🎉 Setup abgeschlossen!")
        print("\n📋 Nächste Schritte:")
        print("1. Starte die App: python -m flask run --host=0.0.0.0 --port=5000 --cert=certs/cert.pem --key=certs/key.pem")
        print("2. Oder mit Docker: docker-compose up")
        print(f"3. Öffne: https://{local_ip}:5000")
        print("4. Bei Zertifikat-Warnung: 'Erweitert' → 'Trotzdem fortfahren'")
        
        if not use_mkcert:
            print("\n⚠️  Browser-Setup für selbstsignierte Zertifikate:")
            print("   Chrome: chrome://flags → 'Allow invalid certificates for resources loaded from localhost'")
            print("   Firefox: about:config → security.tls.insecure_fallback_hosts → localhost,127.0.0.1")
    else:
        print("\n❌ Zertifikat-Erstellung fehlgeschlagen!")
        sys.exit(1)

if __name__ == "__main__":
    main()