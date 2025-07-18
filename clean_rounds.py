#!/usr/bin/env python
"""
Löscht alle existierenden Runden und Konfigurationen für einen sauberen Neustart
Führe dies in deiner App-Umgebung aus: python clean_rounds.py
"""

import sys
import os

# Füge das Projekt-Root-Verzeichnis zum sys.path hinzu
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

from app import create_app, db
from app.models import GameRound, RoundFieldConfiguration, GameSession, FieldConfiguration

def clean_all_rounds():
    """Löscht alle existierenden Runden für einen sauberen Neustart"""
    
    app = create_app()
    
    with app.app_context():
        print("🧹 Bereite System für manuelle Runden-Erstellung vor...")
        
        try:
            # 1. Alle GameSessions deaktivieren
            print("🔄 Deaktiviere alle GameSessions...")
            GameSession.query.update({'is_active': False})
            
            # 2. Alle rundenspezifischen Konfigurationen löschen
            print("🗑️  Lösche alle rundenspezifischen Konfigurationen...")
            deleted_configs = RoundFieldConfiguration.query.delete()
            print(f"  ✅ {deleted_configs} rundenspezifische Konfigurationen gelöscht")
            
            # 3. Alle GameRounds löschen
            print("🗑️  Lösche alle GameRounds...")
            rounds = GameRound.query.all()
            for round_obj in rounds:
                print(f"  🗑️  Lösche Runde: {round_obj.name}")
            
            deleted_rounds = GameRound.query.delete()
            print(f"  ✅ {deleted_rounds} Runden gelöscht")
            
            # 4. Stelle globale FieldConfigurations auf Standard zurück
            print("🔄 Setze globale FieldConfigurations auf Standard zurück...")
            FieldConfiguration.initialize_default_configs()
            print("  ✅ Standard-Konfigurationen wiederhergestellt")
            
            db.session.commit()
            
            print("\n✅ System erfolgreich bereinigt!")
            print("\n🎯 Jetzt kannst du manuell neue Runden erstellen:")
            print("   1. Gehe zu Admin → Runden verwalten")
            print("   2. Erstelle 'Test1' → wird automatisch rundenspezifische Configs bekommen")
            print("   3. Erstelle 'Standard-Spiel' → wird eigene Configs bekommen")
            print("   4. Jede Runde hat dann ihre eigenen Konfigurationen!")
            
        except Exception as e:
            print(f"❌ Fehler bei der Bereinigung: {e}")
            db.session.rollback()
            return False
    
    return True

def show_current_state():
    """Zeigt den aktuellen Zustand der Datenbank"""
    
    app = create_app()
    
    with app.app_context():
        print("\n📊 Aktueller Zustand der Datenbank:")
        
        rounds = GameRound.query.all()
        print(f"  🎮 GameRounds: {len(rounds)}")
        for round_obj in rounds:
            print(f"    - {round_obj.name} (aktiv: {round_obj.is_active})")
        
        round_configs = RoundFieldConfiguration.query.all()
        print(f"  ⚙️  RoundFieldConfigurations: {len(round_configs)}")
        
        global_configs = FieldConfiguration.query.all()
        print(f"  🌐 Globale FieldConfigurations: {len(global_configs)}")
        
        sessions = GameSession.query.all()
        print(f"  🎲 GameSessions: {len(sessions)}")
        active_sessions = GameSession.query.filter_by(is_active=True).all()
        print(f"    - Aktive Sessions: {len(active_sessions)}")

if __name__ == "__main__":
    print("🚀 Bereinige System für manuelle Runden-Erstellung...")
    
    # Zeige aktuellen Zustand
    show_current_state()
    
    # Bestätigung
    print("\n⚠️  WARNUNG: Dies wird ALLE existierenden Runden löschen!")
    print("   Du kannst sie danach manuell neu erstellen.")
    
    confirm = input("\nMöchtest du fortfahren? (ja/nein): ")
    
    if confirm.lower() in ['ja', 'j', 'yes', 'y']:
        if clean_all_rounds():
            print("\n🎉 Bereinigung erfolgreich!")
            print("Das System ist bereit für manuelle Runden-Erstellung!")
        else:
            print("\n❌ Bereinigung fehlgeschlagen!")
    else:
        print("\n❌ Bereinigung abgebrochen.")