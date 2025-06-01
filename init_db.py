import os
import sys

# Füge das Projekt-Root-Verzeichnis (das 'app'-Paket enthält) zum sys.path hinzu.
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT) 

# Importiere create_app und db zuerst
from app import create_app, db 
from app.models import Admin, Team, Minigame, TeamMinigameScore, Character, GameSession, GameEvent

app_instance = create_app()

with app_instance.app_context():
    print("Datenbank-Tabellen werden gelöscht und neu erstellt...")
    try:
        db.drop_all()
        print("Vorhandene Tabellen gelöscht.")
    except Exception as e:
        print(f"Fehler beim Löschen der Tabellen (möglicherweise waren keine vorhanden): {e}")
    
    try:
        db.create_all()
        print("Datenbank-Tabellen erfolgreich erstellt.")
    except Exception as e:
        print(f"Fehler beim Erstellen der Tabellen: {e}")
        sys.exit(1)

    # Admin-Benutzer erstellen
    admin_username = app_instance.config.get('ADMIN_USERNAME', 'admin')
    admin_password = app_instance.config.get('ADMIN_PASSWORD', 'password')
    if not Admin.query.filter_by(username=admin_username).first():
        admin = Admin(username=admin_username)
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        print(f"Admin-Benutzer '{admin_username}' erstellt.")
    else:
        print(f"Admin-Benutzer '{admin_username}' existiert bereits.")

    # Charaktere initialisieren
    # Importiere initialize_characters erst HIER, direkt vor dem Aufruf.
    try:
        from app.admin.init_characters import initialize_characters
        print("Charaktere werden initialisiert/überprüft...")
        initialize_characters() 
        print("Charaktere initialisiert.")
    except ImportError as ie:
        print(f"ImportFehler beim Laden von initialize_characters: {ie}")
        print("Stelle sicher, dass app/admin/init_characters.py existiert und die Funktion 'initialize_characters' enthält.")
    except Exception as char_e:
        print(f"Ein anderer Fehler ist bei der Charakter-Initialisierung aufgetreten: {char_e}")


    print("Datenbank-Initialisierung abgeschlossen.")
