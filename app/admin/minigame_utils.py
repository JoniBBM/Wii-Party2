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
    """Gibt den Pfad zum saved_rounds Verzeichnis zurück"""
    import os
    # Finde das Basedir (ein Verzeichnis über dem app Ordner)
    current_dir = os.path.dirname(os.path.abspath(__file__))  # .../app/admin/
    app_dir = os.path.dirname(current_dir)  # .../app/
    base_dir = os.path.dirname(app_dir)  # .../
    return os.path.join(base_dir, 'app', 'static', 'saved_rounds')

def save_round_to_filesystem(round_obj) -> bool:
    """
    Speichert eine GameRound in das Dateisystem als JSON-Backup.
    
    Args:
        round_obj: GameRound Objekt
        
    Returns:
        bool: True wenn erfolgreich gespeichert
    """
    import json
    from datetime import datetime
    
    try:
        rounds_path = get_saved_rounds_path()
        os.makedirs(rounds_path, exist_ok=True)
        
        # Erstelle JSON-Datei mit Runden-Daten
        round_data = {
            'name': round_obj.name,
            'description': round_obj.description,
            'minigame_folder_name': round_obj.minigame_folder.name if round_obj.minigame_folder else None,
            'is_active': round_obj.is_active,
            'created_at': round_obj.created_at.isoformat() if round_obj.created_at else datetime.utcnow().isoformat(),
            'saved_at': datetime.utcnow().isoformat()
        }
        
        # Sanitize filename (entferne gefährliche Zeichen)
        safe_filename = "".join(c for c in round_obj.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        json_filename = f"{safe_filename}.json"
        json_path = os.path.join(rounds_path, json_filename)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(round_data, f, indent=2, ensure_ascii=False)
        
        return True
        
    except Exception as e:
        print(f"Fehler beim Speichern der Runde '{round_obj.name}': {e}")
        return False

def load_rounds_from_filesystem() -> List[dict]:
    """
    Lädt alle gespeicherten Runden aus dem Dateisystem.
    
    Returns:
        List[dict]: Liste der Runden-Daten
    """
    import json
    
    rounds_path = get_saved_rounds_path()
    
    if not os.path.exists(rounds_path):
        return []
    
    rounds = []
    
    try:
        for filename in os.listdir(rounds_path):
            if filename.endswith('.json'):
                json_path = os.path.join(rounds_path, filename)
                
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        round_data = json.load(f)
                        rounds.append(round_data)
                except Exception as e:
                    print(f"Fehler beim Laden der Runde aus {filename}: {e}")
                    continue
    
    except Exception as e:
        print(f"Fehler beim Durchsuchen der saved_rounds: {e}")
    
    return rounds

def restore_rounds_to_database() -> int:
    """
    Stellt alle gespeicherten Runden aus dem Dateisystem in die Datenbank wieder her.
    
    Returns:
        int: Anzahl der wiederhergestellten Runden
    """
    from app.models import GameRound, MinigameFolder
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

def delete_round_from_filesystem(round_name: str) -> bool:
    """
    Löscht eine gespeicherte Runde aus dem Dateisystem.
    
    Args:
        round_name: Name der zu löschenden Runde
        
    Returns:
        bool: True wenn erfolgreich gelöscht
    """
    import os
    
    try:
        rounds_path = get_saved_rounds_path()
        
        # Finde die JSON-Datei für diese Runde
        for filename in os.listdir(rounds_path):
            if filename.endswith('.json'):
                json_path = os.path.join(rounds_path, filename)
                
                try:
                    import json
                    with open(json_path, 'r', encoding='utf-8') as f:
                        round_data = json.load(f)
                        
                    if round_data.get('name') == round_name:
                        os.remove(json_path)
                        return True
                        
                except Exception:
                    continue
        
        return False
        
    except Exception as e:
        print(f"Fehler beim Löschen der Runde '{round_name}' aus Dateisystem: {e}")
        return False

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