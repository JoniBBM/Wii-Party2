#!/usr/bin/env python3
"""
Migration Script: Fügt FieldConfiguration Tabelle hinzu

Führe dieses Script aus, um die bestehende Datenbank zu aktualisieren:
python add_field_configuration_migration.py
"""

import os
import sys
import sqlite3

# Füge das Projekt-Root-Verzeichnis zum sys.path hinzu
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

from app import create_app, db
from app.models import FieldConfiguration

def add_field_configuration_table():
    """Fügt die FieldConfiguration Tabelle hinzu"""
    
    app = create_app()
    
    with app.app_context():
        print("🔄 Überprüfe Datenbank-Schema für FieldConfiguration...")
        
        # Prüfe ob die Tabelle bereits existiert
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        
        if 'field_configuration' in tables:
            print("✅ FieldConfiguration Tabelle existiert bereits!")
        else:
            print("➕ Erstelle FieldConfiguration Tabelle...")
            try:
                # Erstelle die Tabelle
                db.create_all()
                print("✅ FieldConfiguration Tabelle erfolgreich erstellt!")
            except Exception as e:
                print(f"❌ Fehler beim Erstellen der Tabelle: {e}")
                return False
        
        # Initialisiere Standard-Konfigurationen
        try:
            print("🔧 Initialisiere Standard-Feld-Konfigurationen...")
            FieldConfiguration.initialize_default_configs()
            print("✅ Standard-Feld-Konfigurationen initialisiert!")
            
            # Zeige erstellte Konfigurationen
            configs = FieldConfiguration.query.all()
            print(f"\n📊 {len(configs)} Feld-Konfigurationen verfügbar:")
            for config in configs:
                status = "🟢 Aktiv" if config.is_enabled else "🔴 Deaktiviert"
                print(f"   {config.icon} {config.display_name} - {status} (alle {config.frequency_value} Felder)")
            
            return True
            
        except Exception as e:
            print(f"❌ Fehler beim Initialisieren der Konfigurationen: {e}")
            return False

def verify_migration():
    """Überprüft ob die Migration erfolgreich war"""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Teste ob die neue Tabelle funktioniert
            test_config = FieldConfiguration.get_config_for_field('start')
            
            if test_config:
                print("🧪 Teste FieldConfiguration-Features...")
                print(f"   ✅ Start-Feld Konfiguration: {test_config.display_name}")
                print(f"   ✅ Farbe: {test_config.color_hex}")
                print(f"   ✅ Icon: {test_config.icon}")
                print(f"   ✅ Aktiviert: {test_config.is_enabled}")
                
                # Teste config_dict Property
                config_dict = test_config.config_dict
                print(f"   ✅ Zusatz-Konfiguration: {config_dict}")
                
                # Teste get_all_enabled
                enabled_configs = FieldConfiguration.get_all_enabled()
                print(f"   ✅ {len(enabled_configs)} aktivierte Feld-Typen gefunden")
                
                print("✅ Migration erfolgreich! FieldConfiguration funktioniert.")
                return True
            else:
                print("❌ Verifikation fehlgeschlagen: Keine Start-Feld Konfiguration gefunden.")
                return False
                
        except Exception as e:
            print(f"❌ Verifikation fehlgeschlagen: {e}")
            return False

def main():
    """Hauptfunktion für die Migration"""
    
    print("🎯 Starte Migration für FieldConfiguration-System...")
    print("=" * 60)
    
    # Prüfe ob die Datenbank existiert
    db_path = os.path.join(PROJECT_ROOT, 'app.db')
    if not os.path.exists(db_path):
        print("❌ Datenbank app.db nicht gefunden!")
        print("💡 Führe zuerst 'python init_db.py' aus, um die Datenbank zu erstellen.")
        return False
    
    # Führe Migration aus
    success = add_field_configuration_table()
    
    if success:
        print("\n🔍 Verifiziere Migration...")
        verify_success = verify_migration()
        
        if verify_success:
            print("\n🎉 Migration erfolgreich abgeschlossen!")
            print("\nNEUE FELD-MANAGEMENT-FEATURES:")
            print("=" * 60)
            print("✅ Konfigurierbare Feld-Häufigkeiten")
            print("✅ Aktivierung/Deaktivierung von Feld-Typen")
            print("✅ Anpassbare Farben und Icons")
            print("✅ Erweiterte Feld-Konfigurationen")
            print("✅ Admin-Interface für Feld-Verwaltung")
            
            print("\n🎮 VERFÜGBARE FELD-TYPEN:")
            with create_app().app_context():
                configs = FieldConfiguration.query.all()
                for config in sorted(configs, key=lambda x: x.frequency_value):
                    freq_text = f"alle {config.frequency_value}" if config.frequency_value > 0 else "spezielle Position"
                    print(f"  {config.icon} {config.display_name} - {freq_text} Felder")
            
            print("\n🔧 KONFIGURATIONSOPTIONEN:")
            print("  - Häufigkeit: Modulo-basiert, feste Positionen oder Wahrscheinlichkeit")
            print("  - Aktivierung: Ein-/Ausschalten einzelner Feld-Typen")
            print("  - Farben: Hex-Codes für Frontend-Darstellung")
            print("  - Icons: Emoji/Unicode-Symbole für bessere Erkennbarkeit")
            print("  - Zusatz-Config: JSON-basierte erweiterte Einstellungen")
            
            print("\n🎲 Das Feld-System ist bereit für individuelle Anpassungen!")
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