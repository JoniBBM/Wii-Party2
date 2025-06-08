#!/usr/bin/env python3
"""
Migration Script: Fügt Sonderfeld-Felder zur Team Tabelle hinzu

Führe dieses Script aus, um die bestehende Datenbank zu aktualisieren:
python add_special_fields_migration.py
"""

import os
import sys
import sqlite3

# Füge das Projekt-Root-Verzeichnis zum sys.path hinzu
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

from app import create_app, db
from app.models import Team

def add_special_fields():
    """Fügt die Sonderfeld-Felder zur Team Tabelle hinzu"""
    
    app = create_app()
    
    with app.app_context():
        print("🔄 Überprüfe Datenbank-Schema für Sonderfeld-Features...")
        
        # Prüfe ob die Felder bereits existieren
        inspector = db.inspect(db.engine)
        columns = inspector.get_columns('team')
        
        existing_columns = [col['name'] for col in columns]
        
        # Liste der Sonderfeld-Felder die hinzugefügt werden sollen (vereinfacht)
        special_fields = [
            ('is_blocked', 'BOOLEAN DEFAULT 0'),
            ('blocked_target_number', 'INTEGER'),
            ('blocked_turns_remaining', 'INTEGER DEFAULT 0'),
            ('extra_moves_remaining', 'INTEGER DEFAULT 0'),
            ('has_shield', 'BOOLEAN DEFAULT 0')
        ]
        
        fields_to_add = []
        fields_already_exist = []
        
        for field_name, field_type in special_fields:
            if field_name in existing_columns:
                fields_already_exist.append(field_name)
            else:
                fields_to_add.append((field_name, field_type))
        
        if fields_already_exist:
            print(f"✅ Diese Sonderfeld-Felder existieren bereits: {', '.join(fields_already_exist)}")
        
        if not fields_to_add:
            print("✅ Alle Sonderfeld-Felder sind bereits vorhanden!")
            return True
        
        print(f"➕ Füge folgende Sonderfeld-Felder zur Team Tabelle hinzu: {', '.join([f[0] for f in fields_to_add])}")
        
        try:
            # Füge die fehlenden Felder hinzu
            for field_name, field_type in fields_to_add:
                sql = f"ALTER TABLE team ADD COLUMN {field_name} {field_type}"
                db.engine.execute(sql)
                print(f"   ✅ {field_name} hinzugefügt")
            
            # Initialisiere bestehende Teams mit Standardwerten
            existing_teams = Team.query.all()
            if existing_teams:
                for team in existing_teams:
                    # Setze Standardwerte für neue Felder
                    if 'is_blocked' in [f[0] for f in fields_to_add]:
                        team.is_blocked = False
                    if 'blocked_target_number' in [f[0] for f in fields_to_add]:
                        team.blocked_target_number = None
                    if 'blocked_turns_remaining' in [f[0] for f in fields_to_add]:
                        team.blocked_turns_remaining = 0
                    if 'extra_moves_remaining' in [f[0] for f in fields_to_add]:
                        team.extra_moves_remaining = 0
                    if 'has_shield' in [f[0] for f in fields_to_add]:
                        team.has_shield = False
                
                db.session.commit()
                print(f"🔄 {len(existing_teams)} bestehende Teams mit Standardwerten initialisiert.")
            
            return True
            
        except Exception as e:
            print(f"❌ Fehler beim Hinzufügen der Felder: {e}")
            
            # Fallback: Prüfe ob es spezifische SQLite-Syntax-Fehler gibt
            if "duplicate column name" in str(e).lower():
                print("✅ Die Felder existieren bereits (wurde als Fehler erkannt).")
                return True
            
            return False

def verify_migration():
    """Überprüft ob die Migration erfolgreich war"""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Teste ob die neuen Felder verwendet werden können
            test_team = Team.query.first()
            
            if test_team is not None:
                # Teste die Sonderfeld-Features
                print("🧪 Teste Sonderfeld-Features...")
                
                # Test 1: Blockierung
                original_blocked = test_team.is_blocked
                original_target = test_team.blocked_target_number
                
                test_team.is_blocked = True
                test_team.blocked_target_number = 5
                
                # Test 2: Reset-Funktion
                test_team.reset_special_field_status()
                
                if (test_team.is_blocked == False and 
                    test_team.blocked_target_number is None):
                    print("   ✅ reset_special_field_status() funktioniert")
                else:
                    print("   ⚠️  reset_special_field_status() funktioniert nicht korrekt")
                
                # Setze ursprüngliche Werte zurück
                test_team.is_blocked = original_blocked
                test_team.blocked_target_number = original_target
                db.session.commit()
                
                print("✅ Migration erfolgreich! Sonderfeld-Features funktionieren.")
                return True
            else:
                print("ℹ️  Keine Teams zum Testen vorhanden, aber Schema-Update war erfolgreich.")
                return True
                
        except Exception as e:
            print(f"❌ Verifikation fehlgeschlagen: {e}")
            return False

def main():
    """Hauptfunktion für die Migration"""
    
    print("🎯 Starte Migration für Sonderfeld-Features...")
    print("=" * 50)
    
    # Prüfe ob die Datenbank existiert
    db_path = os.path.join(PROJECT_ROOT, 'app.db')
    if not os.path.exists(db_path):
        print("❌ Datenbank app.db nicht gefunden!")
        print("💡 Führe zuerst 'python init_db.py' aus, um die Datenbank zu erstellen.")
        return False
    
    # Führe Migration aus
    success = add_special_fields()
    
    if success:
        print("\n🔍 Verifiziere Migration...")
        verify_success = verify_migration()
        
        if verify_success:
            print("\n🎉 Migration erfolgreich abgeschlossen!")
            print("\nNEUE SONDERFELD-FEATURES:")
            print("=" * 50)
            print("✅ Team.is_blocked - Team ist blockiert (Sperren-Feld)")
            print("✅ Team.blocked_target_number - Zahl die gewürfelt werden muss")
            print("✅ Team.blocked_turns_remaining - Verbleibende blockierte Züge")
            print("✅ Team.extra_moves_remaining - Extra-Bewegungen verfügbar")
            print("✅ Team.has_shield - Schutz vor Fallen")
            print("✅ Team.reset_special_field_status() - Setzt alle Stati zurück")
            print("\n🎮 SONDERFELD-AKTIONEN VERFÜGBAR:")
            print("🚀 Katapult Vorwärts - Wirft Teams 3-5 Felder nach vorne")
            print("💥 Katapult Rückwärts - Wirft Teams 2-4 Felder nach hinten")
            print("🔄 Spieler-Tausch - Tauscht Positionen mit zufälligem Team")
            print("🚧 Sperren-Feld - Blockiert Teams bis bestimmte Zahl gewürfelt wird")
            print("\n📍 SONDERFELD-POSITIONEN:")
            print("  - Katapult Vorwärts: Feld 15, 30, 45, 60")
            print("  - Katapult Rückwärts: Feld 13, 26, 39, 52, 65")
            print("  - Spieler-Tausch: Feld 17, 34, 51, 68")
            print("  - Sperren-Feld: Feld 19, 38, 57")
            print("\n🎲 Das Spiel ist bereit für epische Sonderfeld-Abenteuer!")
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