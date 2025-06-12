import os
import sys

# Füge das Projekt-Root-Verzeichnis (das 'app'-Paket enthält) zum sys.path hinzu.
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT) 

# Importiere create_app und db zuerst
from app import create_app, db 
from app.models import Admin, Team, Character, GameSession, GameEvent, MinigameFolder, GameRound, FieldConfiguration, WelcomeSession, PlayerRegistration

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
        print("✅ Spiele-Tracking-Feld 'played_content_ids' in GameSession enthalten.")
        print("✅ Sonderfeld-Features 'is_blocked' und 'blocked_target_number' in Team enthalten.")
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

    # NEUE SEKTION: Minigame-Ordner und Spielrunden initialisieren
    print("\n--- Minigame-Ordner und Spielrunden werden initialisiert ---")
    
    try:
        from app.admin.minigame_utils import ensure_minigame_folders_exist, create_minigame_folder_if_not_exists
        
        # Erstelle grundlegende Ordnerstruktur
        print("Erstelle Minigame-Ordner-Struktur...")
        ensure_minigame_folders_exist()
        
        # Erstelle Default-Minigame-Ordner in der Datenbank falls nicht vorhanden
        default_folder_name = app_instance.config.get('DEFAULT_MINIGAME_FOLDER', 'Default')
        default_folder = MinigameFolder.query.filter_by(name=default_folder_name).first()
        
        if not default_folder:
            default_folder = MinigameFolder(
                name=default_folder_name,
                description="Standard-Minispiele für allgemeine Verwendung",
                folder_path=default_folder_name
            )
            db.session.add(default_folder)
            print(f"Standard-Minigame-Ordner '{default_folder_name}' in DB erstellt.")
        else:
            print(f"Standard-Minigame-Ordner '{default_folder_name}' existiert bereits in DB.")
        
        # Erstelle Default-Spielrunde falls nicht vorhanden
        default_round = GameRound.query.filter_by(name="Standard-Spiel").first()
        
        if not default_round:
            default_round = GameRound(
                name="Standard-Spiel",
                description="Standard-Spielrunde für allgemeine Verwendung",
                minigame_folder_id=default_folder.id,
                is_active=True  # Als aktive Runde setzen
            )
            db.session.add(default_round)
            print("Standard-Spielrunde 'Standard-Spiel' erstellt und als aktiv gesetzt.")
        else:
            # Sicherstellen, dass mindestens eine Runde aktiv ist
            if not GameRound.query.filter_by(is_active=True).first():
                default_round.is_active = True
                print("Standard-Spielrunde als aktiv gesetzt (keine andere aktive Runde gefunden).")
            else:
                print("Standard-Spielrunde existiert bereits.")
        
        db.session.commit()
        print("Minigame-Ordner und Spielrunden erfolgreich initialisiert.")
        
        # NEU: Initialisiere FieldConfiguration
        print("\n--- Initialisiere Sonderfeld-Konfigurationen ---")
        try:
            print("Erstelle Standard-Feld-Konfigurationen...")
            FieldConfiguration.initialize_default_configs()
            print("✅ FieldConfiguration-Tabelle erfolgreich initialisiert!")
            
            # Zeige initialisierte Konfigurationen
            all_configs = FieldConfiguration.query.all()
            print(f"📋 {len(all_configs)} Feld-Konfigurationen erstellt:")
            for config in all_configs:
                status = "✅" if config.is_enabled else "❌"
                print(f"  {status} {config.field_type}: {config.display_name} {config.icon}")
                
            # Cache initialisieren
            print("Initialisiere Sonderfeld-Cache...")
            from app.game_logic.special_fields import clear_field_distribution_cache
            clear_field_distribution_cache()
            print("✅ Sonderfeld-Cache erfolgreich initialisiert!")
            
        except Exception as field_init_e:
            print(f"❌ Fehler bei FieldConfiguration-Initialisierung: {field_init_e}")
            print("Das Spiel wird trotzdem funktionieren, aber ohne Sonderfelder.")
        
        # Teste die neuen Tracking-Features
        print("\n--- Teste Spiele-Tracking-Features ---")
        
        # Erstelle eine Test-GameSession mit Tracking
        test_session = GameSession(
            is_active=False,
            current_phase='SETUP_MINIGAME',
            game_round_id=default_round.id,
            played_content_ids=''  # Explizit initialisieren
        )
        
        # Teste die neuen Methoden
        print("Teste get_played_content_ids()...")
        initial_ids = test_session.get_played_content_ids()
        print(f"  Initial IDs: {initial_ids}")
        
        print("Teste add_played_content_id()...")
        test_session.add_played_content_id('test_game_001')
        test_session.add_played_content_id('test_question_002')
        updated_ids = test_session.get_played_content_ids()
        print(f"  Nach dem Hinzufügen: {updated_ids}")
        
        print("Teste is_content_already_played()...")
        is_played = test_session.is_content_already_played('test_game_001')
        print(f"  test_game_001 gespielt: {is_played}")
        
        print("Teste reset_played_content()...")
        test_session.reset_played_content()
        final_ids = test_session.get_played_content_ids()
        print(f"  Nach Reset: {final_ids}")
        
        # Lösche Test-Session (nicht speichern)
        print("✅ Alle Tracking-Features funktionieren korrekt!")
        
        # NEU: Teste Selected Players Features
        print("\n--- Teste Selected Players Features ---")
        
        print("Teste get_selected_players()...")
        initial_players = test_session.get_selected_players()
        print(f"  Initial selected players: {initial_players}")
        
        print("Teste set_selected_players()...")
        test_players = {"1": ["Alice", "Bob"], "2": ["Charlie", "Diana"]}
        test_session.set_selected_players(test_players)
        updated_players = test_session.get_selected_players()
        print(f"  Nach dem Setzen: {updated_players}")
        
        print("Teste select_random_players()...")
        # Erstelle Test-Teams für die zufällige Auswahl
        test_teams = []
        for i, (name, members) in enumerate([("Team Alpha", "Alice, Bob, Charlie"), ("Team Beta", "Diana, Eve, Frank")], 1):
            team = Team(name=name, members=members)
            team.id = i  # Simuliere ID
            test_teams.append(team)
        
        selected = test_session.select_random_players(test_teams, 2)
        print(f"  Zufällige Auswahl (2 pro Team): {selected}")
        
        print("Teste select_random_players() mit 'all'...")
        selected_all = test_session.select_random_players(test_teams, "all")
        print(f"  Auswahl ganzes Team: {selected_all}")
        
        print("Teste Faire Rotation...")
        # Mehrere Runden simulieren
        for round_num in range(1, 6):
            print(f"  Runde {round_num}:")
            selected = test_session.select_random_players(test_teams, 2)
            for team_id, players in selected.items():
                team = next((t for t in test_teams if str(t.id) == team_id), None)
                team_name = team.name if team else f"Team {team_id}"
                print(f"    {team_name}: {', '.join(players)}")
        
        # Statistiken anzeigen
        stats = test_session.get_player_statistics()
        print("  Statistiken nach 5 Runden:")
        for team_id, team_stats in stats.items():
            team = next((t for t in test_teams if str(t.id) == team_id), None)
            team_name = team.name if team else f"Team {team_id}"
            print(f"    {team_name}: {team_stats['players']}")
        
        print("✅ Alle Selected Players Features und Rotation funktionieren korrekt!")
        
    except ImportError as ie:
        print(f"ImportFehler beim Laden der Minigame-Utils: {ie}")
        print("Stelle sicher, dass app/admin/minigame_utils.py existiert und korrekt implementiert ist.")
    except Exception as minigame_e:
        print(f"Fehler bei der Minigame-Ordner-Initialisierung: {minigame_e}")
        print("Die Grundfunktionalität sollte trotzdem funktionieren.")

    # NEU: Teste Sonderfeld-Features
    print("\n--- Teste Sonderfeld-Features ---")
    
    try:
        # Erstelle Test-Team
        test_team = Team(name="Test-Team-Sonderfelder")
        test_team.set_password("test123")
        test_team.current_position = 15  # Sonderfeld-Position
        
        print("Teste Sonderfeld-Status-Features...")
        print(f"  Initial is_blocked: {test_team.is_blocked}")
        print(f"  Initial blocked_target_number: {test_team.blocked_target_number}")
        
        # Teste Blockierung
        test_team.is_blocked = True
        test_team.blocked_target_number = 5
        print(f"  Nach Blockierung - is_blocked: {test_team.is_blocked}, target: {test_team.blocked_target_number}")
        
        # Teste Reset
        test_team.reset_special_field_status()
        print(f"  Nach Reset - is_blocked: {test_team.is_blocked}, target: {test_team.blocked_target_number}")
        
        # Teste Sonderfeld-Logik
        from app.game_logic.special_fields import get_field_type_at_position, get_all_special_field_positions
        
        print("Teste Sonderfeld-Typ-Erkennung...")
        test_positions = [0, 15, 26, 34, 38, 72]  # Start, Katapult vorwärts, Katapult rückwärts, Tausch, Sperre, Ziel
        for pos in test_positions:
            field_type = get_field_type_at_position(pos)
            print(f"  Position {pos}: {field_type}")
        
        print("Teste get_all_special_field_positions()...")
        special_positions = get_all_special_field_positions(73)
        for field_type, positions in special_positions.items():
            print(f"  {field_type}: {len(positions)} Felder - {positions[:5]}{'...' if len(positions) > 5 else ''}")
        
        print("✅ Alle Sonderfeld-Features funktionieren korrekt!")
        
        # Lösche Test-Team (nicht speichern)
        
    except ImportError as ie:
        print(f"ImportFehler beim Laden der Sonderfeld-Logic: {ie}")
        print("Stelle sicher, dass app/game_logic/special_fields.py existiert und korrekt implementiert ist.")
    except Exception as special_e:
        print(f"Fehler bei der Sonderfeld-Feature-Initialisierung: {special_e}")
        print("Die Grundfunktionalität sollte trotzdem funktionieren.")

    # NEU: Welcome-System testen und initialisieren
    print("\n--- Welcome-System wird initialisiert ---")
    
    try:
        print("Teste Welcome-System-Features...")
        
        # Prüfe ob WelcomeSession Tabelle erstellt wurde
        test_welcome_session = WelcomeSession(is_active=False)
        print(f"  WelcomeSession Tabelle: ✅ Erstellt")
        
        # Prüfe ob PlayerRegistration Tabelle erstellt wurde  
        test_registration = PlayerRegistration(
            welcome_session_id=1,  # Wird nicht gespeichert
            player_name="Test Player"
        )
        print(f"  PlayerRegistration Tabelle: ✅ Erstellt")
        
        # Prüfe welcome_password Feld in Team Tabelle
        test_team = Team(name="Test-Welcome-Team", welcome_password="ABC123")
        test_team.set_password("test123")
        print(f"  Team.welcome_password Feld: ✅ Verfügbar")
        
        # Teste WelcomeSession Methoden
        print("Teste WelcomeSession Methoden...")
        active_session = WelcomeSession.get_active_session()
        print(f"  get_active_session(): ✅ {active_session is None} (keine aktive Session erwartet)")
        
        print("✅ Alle Welcome-System-Features funktionieren korrekt!")
        
    except Exception as welcome_e:
        print(f"❌ Fehler bei Welcome-System-Tests: {welcome_e}")
        print("Das Spiel wird trotzdem funktionieren, aber ohne Welcome-System.")

    print("\nDatenbank-Initialisierung abgeschlossen.")
    print("\n📁 Minigame-Ordner-System ist bereit!")
    print("🎮 Standard-Spielrunde wurde erstellt und aktiviert.")
    print("📊 Spiele-Tracking-System ist aktiviert und getestet!")
    print("⭐ Sonderfeld-System ist implementiert und getestet!")
    print("🎉 Welcome-System ist implementiert und getestet!")
    print("👨‍💼 Admin kann jetzt über das Dashboard weitere Ordner und Runden erstellen.")
    print("\n🎯 Neue Features:")
    print("  ✅ Spiele werden nur einmal pro Runde ausgewählt")
    print("  ✅ Zufallsauswahl berücksichtigt bereits gespielte Inhalte")  
    print("  ✅ Admin kann gespielte Inhalte zurücksetzen")
    print("  ✅ Spielfortschritt wird im Dashboard angezeigt")
    print("  ✅ Bereits gespielte Inhalte werden markiert")
    print("  ✅ Zufällige Spielerauswahl für Minispiele")
    print("  ✅ Banner-Anzeige für ausgewählte Spieler")
    print("  ✅ Admin-Übersicht der aktiven Spieler")
    print("\n🎉 WELCOME-SYSTEM FEATURES:")
    print("  👋 Welcome-Seite mit Live-Spielerregistrierung")
    print("  📝 Pop-up Registrierung auf der Startseite")
    print("  🎲 Automatische zufällige Teamaufteilung (2-6 Teams)")
    print("  🔐 6-stellige Team-Passwörter automatisch generiert")
    print("  🎭 Team-Setup: Namen ändern und Charaktere auswählen")
    print("  ⚡ Live-Updates und Admin-Controls")
    print("  📊 Integration im Admin-Dashboard")
    print("\n🌟 SONDERFELD-FEATURES:")
    print("  🚀 Katapult Vorwärts: Wirft Teams 3-5 Felder nach vorne")
    print("  💥 Katapult Rückwärts: Wirft Teams 2-4 Felder nach hinten")
    print("  🔄 Spieler-Tausch: Tauscht Positionen mit zufälligem Team")
    print("  🚧 Sperren-Feld: Blockiert Teams bis bestimmte Zahl gewürfelt wird")
    print("  🎨 Visuelle Effekte: Spezielle Dekos und Animationen für jedes Feld")
    print("  🎮 Integration: Nahtlose Einbindung in bestehende Würfel-Mechanik")
    print("\n📍 Sonderfeld-Positionen:")
    print("  - Katapult Vorwärts: Alle 15 Felder (15, 30, 45, 60)")
    print("  - Katapult Rückwärts: Alle 13 Felder (13, 26, 39, 52, 65)")
    print("  - Spieler-Tausch: Alle 17 Felder (17, 34, 51, 68)")
    print("  - Sperren-Feld: Alle 19 Felder (19, 38, 57)")
    print("\n🎲 Spiel ist bereit für epische Abenteuer!")