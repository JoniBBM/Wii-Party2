#!/usr/bin/env python3
"""
Migration Script: Fügt das played_content_ids Feld zur GameSession Tabelle hinzu

Führe dieses Script aus, um die bestehende Datenbank zu aktualisieren:
python add_tracking_field_migration.py
"""

import os
import sys
import sqlite3

# Füge das Projekt-Root-Verzeichnis zum sys.path hinzu
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

from app import create_app, db
from app.models import GameSession

def add_played_content_ids_field():
    """Fügt das played_content_ids Feld zur GameSession Tabelle hinzu"""
    
    app = create_app()
    
    with app.app_context():
        print("🔄 Überprüfe Datenbank-Schema...")
        
        # Prüfe ob das Feld bereits existiert
        inspector = db.inspect(db.engine)
        columns = inspector.get_columns('game_session')
        
        # Schaue nach ob played_content_ids schon existiert
        field_exists = any(col['name'] == 'played_content_ids' for col in columns)
        
        if field_exists:
            print("✅ Das played_content_ids Feld existiert bereits in der GameSession Tabelle.")
            return True
        
        print("➕ Füge played_content_ids Feld zur GameSession Tabelle hinzu...")
        
        try:
            # Für SQLite: ALTER TABLE ADD COLUMN
            db.engine.execute(
                "ALTER TABLE game_session ADD COLUMN played_content_ids TEXT DEFAULT ''"
            )
            
            print("✅ played_content_ids Feld erfolgreich hinzugefügt!")
            
            # Initialisiere bestehende Sessions mit leerem String
            existing_sessions = GameSession.query.all()
            if existing_sessions:
                for session in existing_sessions:
                    if session.played_content_ids is None:
                        session.played_content_ids = ''
                
                db.session.commit()
                print(f"🔄 {len(existing_sessions)} bestehende GameSession(s) initialisiert.")
            
            return True
            
        except Exception as e:
            print(f"❌ Fehler beim Hinzufügen des Feldes: {e}")
            
            # Fallback: Prüfe ob es eine spezifische SQLite-Syntax gibt
            if "duplicate column name" in str(e).lower():
                print("✅ Das Feld existiert bereits (wurde als Fehler erkannt).")
                return True
            
            return False

def verify_migration():
    """Überprüft ob die Migration erfolgreich war"""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Teste ob das neue Feld verwendet werden kann
            test_session = GameSession.query.first()
            
            if test_session is not None:
                # Teste die neuen Methoden
                original_ids = test_session.get_played_content_ids()
                test_session.add_played_content_id('test_id_123')
                updated_ids = test_session.get_played_content_ids()
                
                # Setze zurück
                test_session.played_content_ids = ','.join(original_ids) if original_ids else ''
                db.session.commit()
                
                print("✅ Migration erfolgreich! Neue Methoden funktionieren.")
                return True
            else:
                print("ℹ️  Keine GameSession zum Testen vorhanden, aber Schema-Update war erfolgreich.")
                return True
                
        except Exception as e:
            print(f"❌ Verifikation fehlgeschlagen: {e}")
            return False

def main():
    """Hauptfunktion für die Migration"""
    
    print("🎯 Starte Migration für Spiele-Tracking...")
    print("=" * 50)
    
    # Prüfe ob die Datenbank existiert
    db_path = os.path.join(PROJECT_ROOT, 'app.db')
    if not os.path.exists(db_path):
        print("❌ Datenbank app.db nicht gefunden!")
        print("💡 Führe zuerst 'python init_db.py' aus, um die Datenbank zu erstellen.")
        return False
    
    # Führe Migration aus
    success = add_played_content_ids_field()
    
    if success:
        print("\n🔍 Verifiziere Migration...")
        verify_success = verify_migration()
        
        if verify_success:
            print("\n🎉 Migration erfolgreich abgeschlossen!")
            print("\nÄnderungen:")
            print("  ✅ played_content_ids Feld zur GameSession Tabelle hinzugefügt")
            print("  ✅ Neue Methoden für Tracking verfügbar:")
            print("     - get_played_content_ids()")
            print("     - add_played_content_id(content_id)")
            print("     - reset_played_content()")
            print("     - is_content_already_played(content_id)")
            print("\n🚀 Die Anwendung kann jetzt gespielten Inhalt verfolgen!")
            return True
        else:
            print("\n⚠️  Migration wurde ausgeführt, aber Verifikation fehlgeschlagen.")
            return False
    else:
        print("\n❌ Migration fehlgeschlagen!")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)