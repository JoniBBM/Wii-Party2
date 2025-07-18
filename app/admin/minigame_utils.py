"""
Utility-Funktionen für das Management von Minigame-Ordnern und JSON-Dateien
Vereinfacht ohne komplexes Quiz-System - unterstützt nur Einzelfragen
Erweitert um Tracking von bereits gespielten Inhalten
"""
import os
import json
import shutil
from datetime import datetime
from flask import current_app
from typing import List, Dict, Optional, Any
import uuid

def get_minigame_folders_path() -> str:
    """Gibt den vollständigen Pfad zum Minigame-Ordner zurück"""
    return current_app.config.get('MINIGAME_FOLDERS_PATH', 
                                os.path.join(current_app.root_path, 'static', 'minigame_folders'))

def get_folder_json_path(folder_name: str) -> str:
    """Gibt den Pfad zur JSON-Datei eines bestimmten Ordners zurück"""
    base_path = get_minigame_folders_path()
    return os.path.join(base_path, folder_name, 'minigames.json')

def ensure_minigame_folders_exist():
    """Stellt sicher, dass das Minigame-Ordner-Verzeichnis existiert"""
    folders_path = get_minigame_folders_path()
    os.makedirs(folders_path, exist_ok=True)
    
    # Erstelle Default-Ordner falls nicht vorhanden
    default_folder = current_app.config.get('DEFAULT_MINIGAME_FOLDER', 'Default')
    create_minigame_folder_if_not_exists(default_folder, "Standard-Minispiele und Fragen")

def create_minigame_folder_if_not_exists(folder_name: str, description: str = "") -> bool:
    """Erstellt einen neuen Minigame-Ordner falls er nicht existiert"""
    folders_path = get_minigame_folders_path()
    folder_path = os.path.join(folders_path, folder_name)
    
    if os.path.exists(folder_path):
        return False  # Ordner existiert bereits
    
    try:
        os.makedirs(folder_path, exist_ok=True)
        
        # Erstelle initiale JSON-Datei
        initial_data = {
            "folder_info": {
                "name": folder_name,
                "description": description,
                "created_at": datetime.utcnow().isoformat()
            },
            "minigames": []
        }
        
        json_path = os.path.join(folder_path, 'minigames.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, indent=2, ensure_ascii=False)
            
        return True
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Erstellen des Ordners {folder_name}: {e}")
        return False

def delete_minigame_folder(folder_name: str) -> bool:
    """Löscht einen Minigame-Ordner komplett"""
    if folder_name == current_app.config.get('DEFAULT_MINIGAME_FOLDER', 'Default'):
        current_app.logger.warning(f"Versuch, Default-Ordner {folder_name} zu löschen - nicht erlaubt")
        return False
        
    folders_path = get_minigame_folders_path()
    folder_path = os.path.join(folders_path, folder_name)
    
    if not os.path.exists(folder_path):
        return False  # Ordner existiert nicht
    
    try:
        shutil.rmtree(folder_path)
        return True
    except Exception as e:
        current_app.logger.error(f"Fehler beim Löschen des Ordners {folder_name}: {e}")
        return False

def get_folder_info(folder_name: str) -> Optional[Dict[str, Any]]:
    """Lädt die Folder-Info aus der JSON-Datei"""
    json_path = get_folder_json_path(folder_name)
    
    if not os.path.exists(json_path):
        return None
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('folder_info', {})
    except Exception as e:
        current_app.logger.error(f"Fehler beim Laden der Folder-Info für {folder_name}: {e}")
        return None

def get_minigames_from_folder(folder_name: str) -> List[Dict[str, Any]]:
    """Lädt alle Minispiele und Fragen aus einem Ordner"""
    json_path = get_folder_json_path(folder_name)
    
    if not os.path.exists(json_path):
        return []
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            minigames = data.get('minigames', [])
            
            # Füge Default player_count für ältere Minispiele hinzu, die es nicht haben
            for minigame in minigames:
                if 'player_count' not in minigame:
                    minigame['player_count'] = '1'  # Default: 1 Spieler pro Team
            
            return minigames
    except Exception as e:
        current_app.logger.error(f"Fehler beim Laden der Minispiele aus {folder_name}: {e}")
        return []

def add_minigame_to_folder(folder_name: str, minigame_data: Dict[str, Any]) -> bool:
    """Fügt ein neues Minispiel oder eine Frage zu einem Ordner hinzu"""
    json_path = get_folder_json_path(folder_name)
    
    if not os.path.exists(json_path):
        current_app.logger.error(f"Ordner {folder_name} existiert nicht")
        return False
    
    try:
        # Lade existierende Daten
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Generiere eindeutige ID falls nicht vorhanden
        if 'id' not in minigame_data or not minigame_data['id']:
            minigame_data['id'] = str(uuid.uuid4())[:8]
        
        # Setze Default player_count falls nicht vorhanden
        if 'player_count' not in minigame_data:
            minigame_data['player_count'] = '1'  # Default: 1 Spieler pro Team
        
        # Füge Timestamp hinzu
        minigame_data['created_at'] = datetime.utcnow().isoformat()
        
        # Prüfe auf doppelte IDs
        existing_ids = [mg.get('id') for mg in data.get('minigames', [])]
        if minigame_data['id'] in existing_ids:
            minigame_data['id'] = str(uuid.uuid4())[:8]  # Neue ID generieren
        
        # Füge Minispiel/Frage hinzu
        if 'minigames' not in data:
            data['minigames'] = []
        data['minigames'].append(minigame_data)
        
        # Speichere zurück
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        return True
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Hinzufügen des Inhalts zu {folder_name}: {e}")
        return False

def update_minigame_in_folder(folder_name: str, minigame_id: str, updated_data: Dict[str, Any]) -> bool:
    """Aktualisiert ein existierendes Minispiel oder eine Frage in einem Ordner"""
    json_path = get_folder_json_path(folder_name)
    
    if not os.path.exists(json_path):
        return False
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        minigames = data.get('minigames', [])
        
        # Finde das zu aktualisierende Item
        for i, minigame in enumerate(minigames):
            if minigame.get('id') == minigame_id:
                # Behalte original ID und created_at
                updated_data['id'] = minigame_id
                if 'created_at' in minigame:
                    updated_data['created_at'] = minigame['created_at']
                updated_data['updated_at'] = datetime.utcnow().isoformat()
                
                minigames[i] = updated_data
                break
        else:
            return False  # Item nicht gefunden
        
        # Speichere zurück
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        return True
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Aktualisieren des Inhalts {minigame_id} in {folder_name}: {e}")
        return False

def delete_minigame_from_folder(folder_name: str, minigame_id: str) -> bool:
    """Löscht ein Minispiel oder eine Frage aus einem Ordner"""
    json_path = get_folder_json_path(folder_name)
    
    if not os.path.exists(json_path):
        return False
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        minigames = data.get('minigames', [])
        original_count = len(minigames)
        
        # Filtere das zu löschende Item heraus
        data['minigames'] = [mg for mg in minigames if mg.get('id') != minigame_id]
        
        if len(data['minigames']) == original_count:
            return False  # Nichts wurde gelöscht
        
        # Speichere zurück
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        return True
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Löschen des Inhalts {minigame_id} aus {folder_name}: {e}")
        return False

def get_minigame_from_folder(folder_name: str, minigame_id: str) -> Optional[Dict[str, Any]]:
    """Lädt ein spezifisches Minispiel oder eine Frage aus einem Ordner"""
    minigames = get_minigames_from_folder(folder_name)
    
    for minigame in minigames:
        if minigame.get('id') == minigame_id:
            return minigame
    
    return None

def get_random_minigame_from_folder(folder_name: str, exclude_played_ids: List[str] = None) -> Optional[Dict[str, Any]]:
    """
    Gibt ein zufälliges Minispiel oder eine Frage aus einem Ordner zurück.
    
    Args:
        folder_name: Name des Ordners
        exclude_played_ids: Liste von IDs, die ausgeschlossen werden sollen
        
    Returns:
        Zufälliges Minispiel/Frage oder None wenn keines verfügbar
    """
    all_minigames = get_minigames_from_folder(folder_name)
    
    if not all_minigames:
        return None
    
    # Filtere bereits gespielte Inhalte heraus
    if exclude_played_ids:
        available_minigames = [mg for mg in all_minigames if mg.get('id') not in exclude_played_ids]
    else:
        available_minigames = all_minigames
    
    # Wenn alle gespielt wurden, gib trotzdem einen zufälligen zurück (oder leere Liste)
    if not available_minigames:
        current_app.logger.warning(f"Alle Minispiele aus Ordner '{folder_name}' wurden bereits gespielt")
        # Optional: Alle wieder verfügbar machen oder None zurückgeben
        available_minigames = all_minigames  # Alle wieder verfügbar machen
    
    import random
    return random.choice(available_minigames)

def list_available_folders() -> List[str]:
    """Gibt eine Liste aller verfügbaren Minigame-Ordner zurück"""
    folders_path = get_minigame_folders_path()
    
    if not os.path.exists(folders_path):
        return []
    
    folders = []
    for item in os.listdir(folders_path):
        folder_path = os.path.join(folders_path, item)
        json_path = os.path.join(folder_path, 'minigames.json')
        
        # Nur Ordner mit gültiger JSON-Datei
        if os.path.isdir(folder_path) and os.path.exists(json_path):
            folders.append(item)
    
    return sorted(folders)

def sync_folders_to_database() -> int:
    """
    Synchronisiert Minigame-Ordner zwischen Dateisystem und Datenbank.
    Fügt fehlende Ordner zur Datenbank hinzu.
    
    Returns:
        int: Anzahl der hinzugefügten Ordner
    """
    from app.models import MinigameFolder
    from app import db
    import json
    from datetime import datetime
    
    folders_path = get_minigame_folders_path()
    
    if not os.path.exists(folders_path):
        return 0
    
    # Bereits vorhandene Ordner in der Datenbank
    existing_folders = {folder.folder_path: folder for folder in MinigameFolder.query.all()}
    
    added_count = 0
    
    # Durchsuche alle Ordner im Dateisystem
    for item in os.listdir(folders_path):
        folder_path = os.path.join(folders_path, item)
        json_path = os.path.join(folder_path, 'minigames.json')
        
        # Nur Ordner mit gültiger JSON-Datei
        if os.path.isdir(folder_path) and os.path.exists(json_path):
            # Prüfe ob bereits in Datenbank
            if item in existing_folders:
                continue
            
            # Lade Beschreibung aus JSON
            description = "Minigame-Sammlung"
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'description' in data:
                        description = data['description']
            except Exception:
                pass  # Verwende Standard-Beschreibung bei Fehlern
            
            # Erstelle Datenbankeintrag
            try:
                folder = MinigameFolder(
                    name=item,
                    description=description,
                    folder_path=item,
                    created_at=datetime.utcnow()
                )
                
                db.session.add(folder)
                db.session.commit()
                added_count += 1
                
            except Exception:
                db.session.rollback()
    
    return added_count

def get_saved_rounds_path() -> str:
    """Gibt den Pfad zum spielstaende/runden Verzeichnis zurück"""
    import os
    # Finde das Basedir (ein Verzeichnis über dem app Ordner)
    current_dir = os.path.dirname(os.path.abspath(__file__))  # .../app/admin/
    app_dir = os.path.dirname(current_dir)  # .../app/
    base_dir = os.path.dirname(app_dir)  # .../
    return os.path.join(base_dir, 'spielstaende', 'runden')

def get_spielstaende_base_path() -> str:
    """Gibt den Pfad zum spielstaende Basis-Verzeichnis zurück"""
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))  # .../app/admin/
    app_dir = os.path.dirname(current_dir)  # .../app/
    base_dir = os.path.dirname(app_dir)  # .../
    return os.path.join(base_dir, 'spielstaende')

def get_round_save_path(round_name: str) -> str:
    """Gibt den Pfad für eine spezifische Runde zurück"""
    import os
    # Sanitize round name für Dateisystem
    safe_name = "".join(c for c in round_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    return os.path.join(get_saved_rounds_path(), safe_name)

def save_round_to_filesystem(round_obj) -> bool:
    """
    Speichert eine GameRound mit kompletten Spielzustand in saubere Ordnerstruktur.
    
    Erstellt:
    spielstaende/runden/[RundenName]/
    ├── rundeninfo.json      # Runden-Metadaten
    ├── teams.json           # Alle Teams mit Positionen
    ├── spielsitzung.json    # GameSession Daten
    ├── konfiguration.json   # Feld-Konfigurationen
    └── minigames/           # Kopie der Minigame-Ordner
        └── [Ordnername]/
            └── minigames.json
    
    Args:
        round_obj: GameRound Objekt
        
    Returns:
        bool: True wenn erfolgreich gespeichert
    """
    import json
    import shutil
    from datetime import datetime
    
    try:
        # Erstelle Ordner für diese Runde
        round_path = get_round_save_path(round_obj.name)
        os.makedirs(round_path, exist_ok=True)
        
        # 1. RUNDENINFO.JSON - Basis-Informationen
        rundeninfo = {
            'name': round_obj.name,
            'description': round_obj.description,
            'minigame_folder_name': round_obj.minigame_folder.name if round_obj.minigame_folder else None,
            'is_active': round_obj.is_active,
            'created_at': round_obj.created_at.isoformat() if round_obj.created_at else datetime.utcnow().isoformat(),
            'saved_at': datetime.utcnow().isoformat(),
            'version': '2.0'  # Neue Struktur-Version
        }
        
        with open(os.path.join(round_path, 'rundeninfo.json'), 'w', encoding='utf-8') as f:
            json.dump(rundeninfo, f, indent=2, ensure_ascii=False)
        
        # 2. TEAMS.JSON - Alle Teams mit kompletten Daten
        teams_data = []
        from app.models import Team
        teams = Team.query.all()
        
        for team in teams:
            team_data = {
                'name': team.name,
                'password_hash': team.password_hash,
                'welcome_password': team.welcome_password,
                'members': team.members,
                'player_config': team.player_config,
                'profile_images': team.profile_images,
                'character_name': team.character_name,
                'character_id': team.character_id,
                'character_customization': team.character_customization,
                'current_position': team.current_position,
                'minigame_placement': team.minigame_placement,
                'bonus_dice_sides': team.bonus_dice_sides,
                'last_dice_result': team.last_dice_result,
                'is_blocked': team.is_blocked,
                'blocked_target_number': team.blocked_target_number,
                'blocked_config': team.blocked_config,
                'blocked_turns_remaining': team.blocked_turns_remaining,
                'extra_moves_remaining': team.extra_moves_remaining
            }
            teams_data.append(team_data)
        
        with open(os.path.join(round_path, 'teams.json'), 'w', encoding='utf-8') as f:
            json.dump(teams_data, f, indent=2, ensure_ascii=False)
        
        # 3. SPIELSITZUNG.JSON - GameSession Daten
        from app.models import GameSession
        active_session = GameSession.query.filter_by(is_active=True).first()
        
        if active_session:
            game_session_data = {
                'start_time': active_session.start_time.isoformat() if active_session.start_time else None,
                'end_time': active_session.end_time.isoformat() if active_session.end_time else None,
                'current_minigame_name': active_session.current_minigame_name,
                'current_minigame_description': active_session.current_minigame_description,
                'current_player_count': active_session.current_player_count,
                'selected_players': active_session.selected_players,
                'current_question_id': active_session.current_question_id,
                'selected_folder_minigame_id': active_session.selected_folder_minigame_id,
                'minigame_source': active_session.minigame_source,
                'played_content_ids': active_session.played_content_ids,
                'player_rotation_data': active_session.player_rotation_data,
                'current_phase': active_session.current_phase,
                'dice_roll_order': active_session.dice_roll_order,
                'current_team_turn_id': active_session.current_team_turn_id,
                'volcano_countdown': active_session.volcano_countdown,
                'volcano_active': active_session.volcano_active,
                'volcano_last_triggered': active_session.volcano_last_triggered.isoformat() if active_session.volcano_last_triggered else None,
                'field_minigame_mode': active_session.field_minigame_mode,
                'field_minigame_landing_team_id': active_session.field_minigame_landing_team_id,
                'field_minigame_opponent_team_id': active_session.field_minigame_opponent_team_id,
                'field_minigame_content_id': active_session.field_minigame_content_id,
                'field_minigame_content_type': active_session.field_minigame_content_type,
                'field_minigame_result': active_session.field_minigame_result
            }
            
            with open(os.path.join(round_path, 'spielsitzung.json'), 'w', encoding='utf-8') as f:
                json.dump(game_session_data, f, indent=2, ensure_ascii=False)
        
        # 4. KONFIGURATION.JSON - Rundenspezifische FieldConfiguration Daten
        field_configs_data = []
        from app.models import RoundFieldConfiguration
        round_configs = RoundFieldConfiguration.query.filter_by(game_round_id=round_obj.id).all()
        
        for config in round_configs:
            config_data = {
                'field_type': config.field_type,
                'display_name': config.display_name,
                'description': config.description,
                'is_enabled': config.is_enabled,
                'frequency_type': config.frequency_type,
                'frequency_value': config.frequency_value,
                'color_hex': config.color_hex,
                'emission_hex': config.emission_hex,
                'icon': config.icon,
                'config_data': config.config_data
            }
            field_configs_data.append(config_data)
        
        with open(os.path.join(round_path, 'konfiguration.json'), 'w', encoding='utf-8') as f:
            json.dump(field_configs_data, f, indent=2, ensure_ascii=False)
        
        # 5. MINIGAMES/ - Kopie der Minigame-Ordner
        minigames_path = os.path.join(round_path, 'minigames')
        os.makedirs(minigames_path, exist_ok=True)
        
        # Sammle MinigameFolder Daten und kopiere Inhalte
        from app.models import MinigameFolder
        folders = MinigameFolder.query.all()
        
        for folder in folders:
            try:
                # Erstelle Ordner für jede Minigame-Sammlung
                folder_target_path = os.path.join(minigames_path, folder.folder_path)
                os.makedirs(folder_target_path, exist_ok=True)
                
                # Kopiere minigames.json
                source_json = get_folder_json_path(folder.folder_path)
                target_json = os.path.join(folder_target_path, 'minigames.json')
                
                if os.path.exists(source_json):
                    shutil.copy2(source_json, target_json)
                else:
                    # Fallback: Erstelle leere JSON-Datei
                    with open(target_json, 'w', encoding='utf-8') as f:
                        json.dump({'minigames': []}, f, indent=2, ensure_ascii=False)
                
                print(f"✅ Minigame-Ordner '{folder.folder_path}' gesichert")
                
            except Exception as folder_e:
                print(f"⚠️ Fehler beim Sichern des Ordners '{folder.folder_path}': {folder_e}")
        
        # 6. ORDNER-METADATEN - Informationen über Minigame-Ordner
        folders_data = []
        for folder in folders:
            folder_data = {
                'name': folder.name,
                'description': folder.description,
                'folder_path': folder.folder_path,
                'created_at': folder.created_at.isoformat() if folder.created_at else None
            }
            folders_data.append(folder_data)
        
        with open(os.path.join(round_path, 'ordner.json'), 'w', encoding='utf-8') as f:
            json.dump(folders_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Spielstand '{round_obj.name}' erfolgreich in '{round_path}' gespeichert")
        return True
        
    except Exception as e:
        print(f"❌ Fehler beim Speichern der Runde '{round_obj.name}': {e}")
        return False

def load_rounds_from_filesystem() -> List[dict]:
    """
    Lädt alle gespeicherten Runden aus dem neuen Dateisystem.
    
    Unterstützt sowohl die alte Struktur (*.json) als auch die neue Ordnerstruktur.
    
    Returns:
        List[dict]: Liste der Runden-Daten
    """
    import json
    
    rounds_path = get_saved_rounds_path()
    
    if not os.path.exists(rounds_path):
        return []
    
    rounds = []
    
    try:
        for item in os.listdir(rounds_path):
            item_path = os.path.join(rounds_path, item)
            
            if os.path.isdir(item_path):
                # Neue Ordnerstruktur
                try:
                    round_data = load_round_from_new_structure(item_path)
                    if round_data:
                        rounds.append(round_data)
                except Exception as e:
                    print(f"Fehler beim Laden der Runde aus Ordner {item}: {e}")
                    continue
            
            elif item.endswith('.json'):
                # Alte Struktur (Backward Compatibility)
                json_path = os.path.join(rounds_path, item)
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        round_data = json.load(f)
                        rounds.append(round_data)
                except Exception as e:
                    print(f"Fehler beim Laden der Runde aus {item}: {e}")
                    continue
    
    except Exception as e:
        print(f"Fehler beim Durchsuchen der spielstaende/runden: {e}")
    
    return rounds

def load_round_from_new_structure(round_path: str) -> dict:
    """
    Lädt eine Runde aus der neuen Ordnerstruktur.
    
    Args:
        round_path: Pfad zum Runden-Ordner
        
    Returns:
        dict: Runden-Daten im alten Format für Kompatibilität
    """
    import json
    
    try:
        # 1. Rundeninfo laden
        rundeninfo_path = os.path.join(round_path, 'rundeninfo.json')
        if not os.path.exists(rundeninfo_path):
            return None
        
        with open(rundeninfo_path, 'r', encoding='utf-8') as f:
            rundeninfo = json.load(f)
        
        # 2. Teams laden
        teams_data = []
        teams_path = os.path.join(round_path, 'teams.json')
        if os.path.exists(teams_path):
            with open(teams_path, 'r', encoding='utf-8') as f:
                teams_data = json.load(f)
        
        # 3. Spielsitzung laden
        game_session_data = None
        session_path = os.path.join(round_path, 'spielsitzung.json')
        if os.path.exists(session_path):
            with open(session_path, 'r', encoding='utf-8') as f:
                game_session_data = json.load(f)
        
        # 4. Konfiguration laden
        field_configs_data = []
        config_path = os.path.join(round_path, 'konfiguration.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                field_configs_data = json.load(f)
        
        # 5. Ordner-Metadaten laden
        folders_data = []
        ordner_path = os.path.join(round_path, 'ordner.json')
        if os.path.exists(ordner_path):
            with open(ordner_path, 'r', encoding='utf-8') as f:
                folders_data = json.load(f)
        
        # 6. Minigame-Inhalte laden
        minigame_contents = {}
        minigames_path = os.path.join(round_path, 'minigames')
        if os.path.exists(minigames_path):
            for folder_name in os.listdir(minigames_path):
                folder_path = os.path.join(minigames_path, folder_name)
                if os.path.isdir(folder_path):
                    json_path = os.path.join(folder_path, 'minigames.json')
                    if os.path.exists(json_path):
                        with open(json_path, 'r', encoding='utf-8') as f:
                            folder_data = json.load(f)
                            minigame_contents[folder_name] = folder_data.get('minigames', [])
        
        # Kombiniere alle Daten im alten Format für Kompatibilität
        combined_data = {
            'name': rundeninfo.get('name', 'Unbekannt'),
            'description': rundeninfo.get('description', ''),
            'minigame_folder_name': rundeninfo.get('minigame_folder_name'),
            'is_active': rundeninfo.get('is_active', False),
            'created_at': rundeninfo.get('created_at'),
            'saved_at': rundeninfo.get('saved_at'),
            'version': rundeninfo.get('version', '2.0'),
            
            # Neue Struktur
            'teams': teams_data,
            'game_session': game_session_data,
            'field_configurations': field_configs_data,
            'minigame_folders': folders_data,
            'minigame_contents': minigame_contents,
            
            # Zusätzliche Metadaten
            'structure_type': 'new_folder',
            'round_path': round_path
        }
        
        return combined_data
        
    except Exception as e:
        print(f"Fehler beim Laden der Runde aus {round_path}: {e}")
        return None

def restore_rounds_to_database() -> int:
    """
    Stellt alle gespeicherten Runden mit kompletten Spielzustand aus dem Dateisystem wieder her.
    
    Returns:
        int: Anzahl der wiederhergestellten Runden
    """
    from app.models import GameRound, MinigameFolder, Team, GameSession, FieldConfiguration
    from app import db
    from datetime import datetime
    
    saved_rounds = load_rounds_from_filesystem()
    
    if not saved_rounds:
        return 0
    
    restored_count = 0
    
    for round_data in saved_rounds:
        try:
            # Prüfe ob Runde bereits existiert
            existing_round = GameRound.query.filter_by(name=round_data['name']).first()
            if existing_round:
                continue
            
            # Finde den zugehörigen MinigameFolder
            folder = None
            if round_data.get('minigame_folder_name'):
                folder = MinigameFolder.query.filter_by(name=round_data['minigame_folder_name']).first()
            
            if not folder:
                print(f"⚠️  Ordner '{round_data.get('minigame_folder_name')}' für Runde '{round_data['name']}' nicht gefunden. Überspringe.")
                continue
            
            # Erstelle neue GameRound
            new_round = GameRound(
                name=round_data['name'],
                description=round_data.get('description', ''),
                minigame_folder_id=folder.id,
                is_active=False,  # Setze nicht automatisch als aktiv
                created_at=datetime.fromisoformat(round_data['created_at']) if round_data.get('created_at') else datetime.utcnow()
            )
            
            db.session.add(new_round)
            db.session.flush()  # Um die ID zu bekommen
            
            # Wiederherstellung der Teams falls vorhanden
            if round_data.get('teams'):
                _restore_teams_from_data(round_data['teams'])
            
            # Wiederherstellung der rundenspezifischen FieldConfigurations falls vorhanden
            if round_data.get('field_configurations'):
                _restore_field_configurations_from_data(round_data['field_configurations'], new_round.id)
            
            # Wiederherstellung der MinigameFolders falls vorhanden
            if round_data.get('minigame_folders'):
                _restore_minigame_folders_from_data(round_data['minigame_folders'])
            
            # Wiederherstellung der Minigame-Inhalte falls vorhanden
            _restore_minigame_contents_from_new_structure(round_data)
            
            # Wiederherstellung der GameSession falls vorhanden
            if round_data.get('game_session'):
                _restore_game_session_from_data(round_data['game_session'], new_round.id)
            
            restored_count += 1
            
        except Exception as e:
            print(f"Fehler beim Wiederherstellen der Runde '{round_data.get('name', 'Unbekannt')}': {e}")
            continue
    
    try:
        db.session.commit()
        return restored_count
    except Exception as e:
        db.session.rollback()
        print(f"Fehler beim Speichern der wiederhergestellten Runden: {e}")
        return 0

def _restore_teams_from_data(teams_data):
    """Hilfsfunktion zur Wiederherstellung der Teams aus den Backup-Daten"""
    from app.models import Team
    from app import db
    
    for team_data in teams_data:
        try:
            # Prüfe ob Team bereits existiert
            existing_team = Team.query.filter_by(name=team_data['name']).first()
            if existing_team:
                continue
            
            # Erstelle neues Team
            team = Team(
                name=team_data['name'],
                password_hash=team_data.get('password_hash'),
                welcome_password=team_data.get('welcome_password'),
                members=team_data.get('members'),
                player_config=team_data.get('player_config'),
                profile_images=team_data.get('profile_images'),
                character_name=team_data.get('character_name'),
                character_id=team_data.get('character_id'),
                character_customization=team_data.get('character_customization'),
                current_position=team_data.get('current_position', 0),
                minigame_placement=team_data.get('minigame_placement'),
                bonus_dice_sides=team_data.get('bonus_dice_sides', 0),
                last_dice_result=team_data.get('last_dice_result'),
                is_blocked=team_data.get('is_blocked', False),
                blocked_target_number=team_data.get('blocked_target_number'),
                blocked_config=team_data.get('blocked_config'),
                blocked_turns_remaining=team_data.get('blocked_turns_remaining', 0),
                extra_moves_remaining=team_data.get('extra_moves_remaining', 0)
            )
            
            db.session.add(team)
            
        except Exception as e:
            print(f"Fehler beim Wiederherstellen des Teams '{team_data.get('name', 'Unbekannt')}': {e}")
            continue

def _restore_field_configurations_from_data(field_configs_data, round_id):
    """Hilfsfunktion zur Wiederherstellung der rundenspezifischen FieldConfigurations aus den Backup-Daten"""
    from app.models import RoundFieldConfiguration
    from app import db
    
    for config_data in field_configs_data:
        try:
            # Prüfe ob rundenspezifische Konfiguration bereits existiert
            existing_config = RoundFieldConfiguration.query.filter_by(
                game_round_id=round_id,
                field_type=config_data['field_type']
            ).first()
            
            if existing_config:
                # Aktualisiere existierende Konfiguration
                existing_config.display_name = config_data.get('display_name', existing_config.display_name)
                existing_config.description = config_data.get('description', existing_config.description)
                existing_config.is_enabled = config_data.get('is_enabled', existing_config.is_enabled)
                existing_config.frequency_type = config_data.get('frequency_type', existing_config.frequency_type)
                existing_config.frequency_value = config_data.get('frequency_value', existing_config.frequency_value)
                existing_config.color_hex = config_data.get('color_hex', existing_config.color_hex)
                existing_config.emission_hex = config_data.get('emission_hex', existing_config.emission_hex)
                existing_config.icon = config_data.get('icon', existing_config.icon)
                existing_config.config_data = config_data.get('config_data', existing_config.config_data)
                continue
            
            # Erstelle neue rundenspezifische FieldConfiguration
            round_config = RoundFieldConfiguration(
                game_round_id=round_id,
                field_type=config_data['field_type'],
                display_name=config_data.get('display_name', ''),
                description=config_data.get('description', ''),
                is_enabled=config_data.get('is_enabled', True),
                frequency_type=config_data.get('frequency_type', 'modulo'),
                frequency_value=config_data.get('frequency_value', 10),
                color_hex=config_data.get('color_hex', '#00FF00'),
                emission_hex=config_data.get('emission_hex', '#00CC00'),
                icon=config_data.get('icon', '⬜'),
                config_data=config_data.get('config_data')
            )
            
            db.session.add(round_config)
            
        except Exception as e:
            print(f"Fehler beim Wiederherstellen der rundenspezifischen FieldConfiguration '{config_data.get('field_type', 'Unbekannt')}': {e}")
            continue

def _restore_minigame_folders_from_data(folders_data):
    """Hilfsfunktion zur Wiederherstellung der MinigameFolders aus den Backup-Daten"""
    from app.models import MinigameFolder
    from app import db
    from datetime import datetime
    
    for folder_data in folders_data:
        try:
            # Prüfe ob MinigameFolder bereits existiert
            existing_folder = MinigameFolder.query.filter_by(name=folder_data['name']).first()
            if existing_folder:
                continue
            
            # Erstelle neuen MinigameFolder
            folder = MinigameFolder(
                name=folder_data['name'],
                description=folder_data.get('description', ''),
                folder_path=folder_data.get('folder_path', folder_data['name']),
                created_at=datetime.fromisoformat(folder_data['created_at']) if folder_data.get('created_at') else datetime.utcnow()
            )
            
            db.session.add(folder)
            
        except Exception as e:
            print(f"Fehler beim Wiederherstellen des MinigameFolder '{folder_data.get('name', 'Unbekannt')}': {e}")
            continue

def _restore_minigame_contents_from_data(contents_data):
    """Hilfsfunktion zur Wiederherstellung der Minigame-Inhalte aus den Backup-Daten"""
    import json
    
    for folder_path, folder_content in contents_data.items():
        try:
            # Erstelle Ordner falls nicht vorhanden
            create_minigame_folder_if_not_exists(folder_path, f"Wiederhergestellter Ordner: {folder_path}")
            
            # Lade aktuelle Inhalte
            json_path = get_folder_json_path(folder_path)
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    current_data = json.load(f)
            else:
                current_data = {'minigames': []}
            
            # Prüfe welche Inhalte bereits vorhanden sind
            existing_ids = {item.get('id') for item in current_data.get('minigames', [])}
            
            # Füge neue Inhalte hinzu
            for item in folder_content:
                if item.get('id') not in existing_ids:
                    current_data['minigames'].append(item)
            
            # Speichere aktualisierte Daten
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(current_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Minigame-Inhalte für Ordner '{folder_path}' wiederhergestellt")
            
        except Exception as e:
            print(f"Fehler beim Wiederherstellen der Inhalte für Ordner '{folder_path}': {e}")
            continue

def _restore_minigame_contents_from_new_structure(round_data):
    """Hilfsfunktion zur Wiederherstellung der Minigame-Inhalte aus der neuen Ordnerstruktur"""
    import json
    import shutil
    
    # Prüfe ob es sich um die neue Ordnerstruktur handelt
    if round_data.get('structure_type') != 'new_folder':
        # Fallback zur alten Methode
        if 'minigame_contents' in round_data:
            _restore_minigame_contents_from_data(round_data['minigame_contents'])
        return
    
    # Neue Ordnerstruktur - kopiere Minigame-Ordner direkt
    round_path = round_data.get('round_path')
    if not round_path:
        return
    
    minigames_backup_path = os.path.join(round_path, 'minigames')
    if not os.path.exists(minigames_backup_path):
        return
    
    # Durchsuche alle gesicherten Minigame-Ordner
    for folder_name in os.listdir(minigames_backup_path):
        folder_backup_path = os.path.join(minigames_backup_path, folder_name)
        
        if not os.path.isdir(folder_backup_path):
            continue
        
        try:
            # Erstelle Ziel-Ordner
            create_minigame_folder_if_not_exists(folder_name, f"Wiederhergestellter Ordner: {folder_name}")
            
            # Kopiere minigames.json
            source_json = os.path.join(folder_backup_path, 'minigames.json')
            target_json = get_folder_json_path(folder_name)
            
            if os.path.exists(source_json):
                # Merge mit existierendem Inhalt
                existing_data = {'minigames': []}
                if os.path.exists(target_json):
                    with open(target_json, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                
                # Lade Backup-Daten
                with open(source_json, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
                
                # Merge Inhalte
                existing_ids = {item.get('id') for item in existing_data.get('minigames', [])}
                for item in backup_data.get('minigames', []):
                    if item.get('id') not in existing_ids:
                        existing_data['minigames'].append(item)
                
                # Speichere gemergten Inhalt
                with open(target_json, 'w', encoding='utf-8') as f:
                    json.dump(existing_data, f, indent=2, ensure_ascii=False)
                
                print(f"✅ Minigame-Ordner '{folder_name}' aus neuer Struktur wiederhergestellt")
            
        except Exception as e:
            print(f"Fehler beim Wiederherstellen des Ordners '{folder_name}': {e}")
            continue

def _restore_game_session_from_data(session_data, round_id):
    """Hilfsfunktion zur Wiederherstellung der GameSession aus den Backup-Daten"""
    from app.models import GameSession
    from app import db
    from datetime import datetime
    
    try:
        # Prüfe ob bereits eine aktive GameSession existiert
        existing_session = GameSession.query.filter_by(is_active=True).first()
        if existing_session:
            # Deaktiviere existierende Session
            existing_session.is_active = False
        
        # Erstelle neue GameSession
        session = GameSession(
            game_round_id=round_id,
            start_time=datetime.fromisoformat(session_data['start_time']) if session_data.get('start_time') else datetime.utcnow(),
            end_time=datetime.fromisoformat(session_data['end_time']) if session_data.get('end_time') else None,
            is_active=False,  # Nicht automatisch aktivieren
            current_minigame_name=session_data.get('current_minigame_name'),
            current_minigame_description=session_data.get('current_minigame_description'),
            current_player_count=session_data.get('current_player_count', '1'),
            selected_players=session_data.get('selected_players'),
            current_question_id=session_data.get('current_question_id'),
            selected_folder_minigame_id=session_data.get('selected_folder_minigame_id'),
            minigame_source=session_data.get('minigame_source', 'manual'),
            played_content_ids=session_data.get('played_content_ids', ''),
            player_rotation_data=session_data.get('player_rotation_data'),
            current_phase=session_data.get('current_phase', 'SETUP_MINIGAME'),
            dice_roll_order=session_data.get('dice_roll_order'),
            current_team_turn_id=session_data.get('current_team_turn_id'),
            volcano_countdown=session_data.get('volcano_countdown', 0),
            volcano_active=session_data.get('volcano_active', False),
            volcano_last_triggered=datetime.fromisoformat(session_data['volcano_last_triggered']) if session_data.get('volcano_last_triggered') else None,
            field_minigame_mode=session_data.get('field_minigame_mode'),
            field_minigame_landing_team_id=session_data.get('field_minigame_landing_team_id'),
            field_minigame_opponent_team_id=session_data.get('field_minigame_opponent_team_id'),
            field_minigame_content_id=session_data.get('field_minigame_content_id'),
            field_minigame_content_type=session_data.get('field_minigame_content_type'),
            field_minigame_result=session_data.get('field_minigame_result')
        )
        
        db.session.add(session)
        
    except Exception as e:
        print(f"Fehler beim Wiederherstellen der GameSession: {e}")

def delete_round_from_filesystem(round_name: str) -> bool:
    """
    Löscht eine gespeicherte Runde aus dem Dateisystem.
    
    Unterstützt sowohl die alte Struktur (*.json) als auch die neue Ordnerstruktur.
    
    Args:
        round_name: Name der zu löschenden Runde
        
    Returns:
        bool: True wenn erfolgreich gelöscht
    """
    import os
    import shutil
    
    try:
        rounds_path = get_saved_rounds_path()
        
        if not os.path.exists(rounds_path):
            return False
        
        # 1. Neue Ordnerstruktur - Suche nach Ordner
        round_folder_path = get_round_save_path(round_name)
        if os.path.exists(round_folder_path) and os.path.isdir(round_folder_path):
            shutil.rmtree(round_folder_path)
            print(f"✅ Runden-Ordner '{round_name}' erfolgreich gelöscht")
            return True
        
        # 2. Alte Struktur - Suche nach JSON-Datei
        for filename in os.listdir(rounds_path):
            if filename.endswith('.json'):
                json_path = os.path.join(rounds_path, filename)
                
                try:
                    import json
                    with open(json_path, 'r', encoding='utf-8') as f:
                        round_data = json.load(f)
                        
                    if round_data.get('name') == round_name:
                        os.remove(json_path)
                        print(f"✅ Runden-Datei '{filename}' erfolgreich gelöscht")
                        return True
                        
                except Exception:
                    continue
        
        return False
        
    except Exception as e:
        print(f"Fehler beim Löschen der Runde '{round_name}' aus Dateisystem: {e}")
        return False

def backup_all_rounds_before_db_reset() -> int:
    """
    Sichert alle existierenden Runden vor einem Datenbank-Reset.
    
    Returns:
        int: Anzahl der gesicherten Runden
    """
    from app.models import GameRound
    
    try:
        rounds = GameRound.query.all()
        if not rounds:
            return 0
        
        backed_up_count = 0
        
        for round_obj in rounds:
            try:
                if save_round_to_filesystem(round_obj):
                    backed_up_count += 1
                    print(f"✅ Runde '{round_obj.name}' gesichert")
                else:
                    print(f"⚠️  Runde '{round_obj.name}' konnte nicht gesichert werden")
            except Exception as e:
                print(f"❌ Fehler beim Sichern der Runde '{round_obj.name}': {e}")
                continue
        
        return backed_up_count
        
    except Exception as e:
        print(f"❌ Fehler beim Sichern aller Runden: {e}")
        return 0

def update_folder_info(folder_name: str, new_description: str) -> bool:
    """Aktualisiert die Beschreibung eines Ordners"""
    json_path = get_folder_json_path(folder_name)
    
    if not os.path.exists(json_path):
        return False
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'folder_info' not in data:
            data['folder_info'] = {}
        
        data['folder_info']['description'] = new_description
        data['folder_info']['updated_at'] = datetime.utcnow().isoformat()
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        return True
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Aktualisieren der Folder-Info für {folder_name}: {e}")
        return False

# FRAGEN-SPEZIFISCHE HILFSFUNKTIONEN

def add_question_to_folder(folder_name: str, question_data: Dict[str, Any]) -> bool:
    """Fügt eine neue Frage zu einem Ordner hinzu"""
    # Setze den Typ auf 'question'
    question_data['type'] = 'question'
    return add_minigame_to_folder(folder_name, question_data)

def get_question_from_folder(folder_name: str, question_id: str) -> Optional[Dict[str, Any]]:
    """Lädt eine spezifische Frage aus einem Ordner"""
    question = get_minigame_from_folder(folder_name, question_id)
    
    # Prüfe ob es wirklich eine Frage ist
    if question and question.get('type') == 'question':
        return question
    
    return None

def get_questions_from_folder(folder_name: str) -> List[Dict[str, Any]]:
    """Lädt alle Fragen aus einem Ordner"""
    all_content = get_minigames_from_folder(folder_name)
    
    # Filtere nur Fragen heraus
    questions = [item for item in all_content if item.get('type') == 'question']
    
    return questions

def get_games_from_folder(folder_name: str) -> List[Dict[str, Any]]:
    """Lädt alle Nicht-Fragen (normale Minispiele) aus einem Ordner"""
    all_content = get_minigames_from_folder(folder_name)
    
    # Filtere Fragen heraus
    games = [item for item in all_content if item.get('type') != 'question']
    
    return games

def get_all_content_from_folder(folder_name: str) -> Dict[str, List[Dict[str, Any]]]:
    """Gibt alle Inhalte getrennt nach Typ zurück"""
    all_content = get_minigames_from_folder(folder_name)
    
    games = []
    questions = []
    
    for item in all_content:
        if item.get('type') == 'question':
            questions.append(item)
        else:
            games.append(item)
    
    return {
        'games': games,
        'questions': questions
    }

def get_random_content_from_folder(folder_name: str, exclude_played_ids: List[str] = None) -> Optional[Dict[str, Any]]:
    """
    Gibt zufälligen Inhalt (Minispiel oder Frage) aus einem Ordner zurück.
    
    Args:
        folder_name: Name des Ordners
        exclude_played_ids: Liste von IDs, die ausgeschlossen werden sollen
        
    Returns:
        Zufälliges Minispiel/Frage oder None wenn keines verfügbar
    """
    all_items = get_minigames_from_folder(folder_name)
    
    if not all_items:
        return None
    
    # Filtere bereits gespielte Inhalte heraus
    if exclude_played_ids:
        available_items = [item for item in all_items if item.get('id') not in exclude_played_ids]
    else:
        available_items = all_items
    
    # Wenn alle gespielt wurden, gib trotzdem einen zufälligen zurück
    if not available_items:
        current_app.logger.warning(f"Alle Inhalte aus Ordner '{folder_name}' wurden bereits gespielt. Alle werden wieder verfügbar gemacht.")
        available_items = all_items  # Alle wieder verfügbar machen
    
    import random
    selected = random.choice(available_items)
    
    # Füge Typ-Info hinzu falls nicht vorhanden
    if 'type' not in selected:
        selected['type'] = 'game'  # Default zu game
    
    return selected

# NEUE TRACKING-FUNKTIONEN

def get_played_count_for_folder(folder_name: str, played_ids: List[str]) -> Dict[str, int]:
    """
    Gibt Statistiken über gespielte Inhalte in einem Ordner zurück.
    
    Args:
        folder_name: Name des Ordners
        played_ids: Liste der bereits gespielten IDs
        
    Returns:
        Dict mit 'total', 'played', 'remaining'
    """
    all_items = get_minigames_from_folder(folder_name)
    total_count = len(all_items)
    
    played_count = 0
    for item in all_items:
        if item.get('id') in played_ids:
            played_count += 1
    
    return {
        'total': total_count,
        'played': played_count,
        'remaining': total_count - played_count
    }

def get_available_content_from_folder(folder_name: str, exclude_played_ids: List[str] = None) -> List[Dict[str, Any]]:
    """
    Gibt alle noch nicht gespielten Inhalte aus einem Ordner zurück.
    
    Args:
        folder_name: Name des Ordners
        exclude_played_ids: Liste von IDs, die ausgeschlossen werden sollen
        
    Returns:
        Liste der verfügbaren Inhalte
    """
    all_items = get_minigames_from_folder(folder_name)
    
    if not exclude_played_ids:
        return all_items
    
    available_items = [item for item in all_items if item.get('id') not in exclude_played_ids]
    return available_items

def reset_played_content_for_session(game_session):
    """
    Setzt die gespielten Inhalte für eine GameSession zurück.
    
    Args:
        game_session: GameSession-Objekt
    """
    if hasattr(game_session, 'reset_played_content'):
        game_session.reset_played_content()
        current_app.logger.info(f"Gespielte Inhalte für Session {game_session.id} zurückgesetzt")

def mark_content_as_played(game_session, content_id: str):
    """
    Markiert einen Inhalt als gespielt für eine GameSession.
    
    Args:
        game_session: GameSession-Objekt
        content_id: ID des gespielten Inhalts
    """
    if hasattr(game_session, 'add_played_content_id'):
        game_session.add_played_content_id(content_id)
        current_app.logger.info(f"Inhalt {content_id} als gespielt markiert für Session {game_session.id}")