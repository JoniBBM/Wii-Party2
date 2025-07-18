#!/usr/bin/env python
"""
Schnelle Migration für RoundFieldConfiguration Tabelle
Führe dies in deiner App-Umgebung aus: python migrate_roundconfig.py
"""

import sys
import os

# Füge das Projekt-Root-Verzeichnis zum sys.path hinzu
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

from app import create_app, db
from app.models import GameRound, FieldConfiguration, RoundFieldConfiguration

def migrate_round_configurations():
    """Erstelle RoundFieldConfiguration Tabelle und initialisiere Daten"""
    
    app = create_app()
    
    with app.app_context():
        print("🔄 Erstelle RoundFieldConfiguration Tabelle...")
        
        try:
            # Erstelle nur die neue Tabelle
            db.engine.execute("""
                CREATE TABLE IF NOT EXISTS round_field_configuration (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_round_id INTEGER NOT NULL,
                    field_type VARCHAR(50) NOT NULL,
                    display_name VARCHAR(100) NOT NULL,
                    description VARCHAR(500),
                    is_enabled BOOLEAN DEFAULT 1,
                    frequency_type VARCHAR(20) DEFAULT 'modulo',
                    frequency_value INTEGER DEFAULT 10,
                    color_hex VARCHAR(7) NOT NULL,
                    emission_hex VARCHAR(7),
                    icon VARCHAR(10),
                    config_data TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(game_round_id, field_type),
                    FOREIGN KEY(game_round_id) REFERENCES game_round(id)
                );
            """)
            
            print("✅ RoundFieldConfiguration Tabelle erstellt")
            
            # Initialisiere rundenspezifische Konfigurationen
            print("🔄 Initialisiere rundenspezifische Konfigurationen...")
            
            rounds = GameRound.query.all()
            global_configs = FieldConfiguration.query.all()
            
            for round_obj in rounds:
                print(f"  📋 Erstelle Konfigurationen für Runde '{round_obj.name}'...")
                
                for global_config in global_configs:
                    # Prüfe ob bereits existiert
                    existing = RoundFieldConfiguration.query.filter_by(
                        game_round_id=round_obj.id,
                        field_type=global_config.field_type
                    ).first()
                    
                    if not existing:
                        # Erstelle neue rundenspezifische Konfiguration
                        round_config = RoundFieldConfiguration(
                            game_round_id=round_obj.id,
                            field_type=global_config.field_type,
                            display_name=global_config.display_name,
                            description=global_config.description,
                            is_enabled=global_config.is_enabled,
                            frequency_type=global_config.frequency_type,
                            frequency_value=global_config.frequency_value,
                            color_hex=global_config.color_hex,
                            emission_hex=global_config.emission_hex,
                            icon=global_config.icon,
                            config_data=global_config.config_data
                        )
                        db.session.add(round_config)
                
                print(f"  ✅ Konfigurationen für '{round_obj.name}' erstellt")
            
            db.session.commit()
            
            print("✅ Migration erfolgreich abgeschlossen!")
            print("🎯 Jetzt kannst du Runden aktivieren und jede hat ihre eigenen Konfigurationen!")
            
        except Exception as e:
            print(f"❌ Fehler bei der Migration: {e}")
            db.session.rollback()
            return False
    
    return True

if __name__ == "__main__":
    print("🚀 Starte Migration für rundenspezifische Konfigurationen...")
    if migrate_round_configurations():
        print("\n🎉 Migration erfolgreich!")
        print("Du kannst jetzt Test1 aktivieren und es wird funktionieren!")
    else:
        print("\n❌ Migration fehlgeschlagen!")