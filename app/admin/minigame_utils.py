"""
Utility-Funktionen für das Management von Minigame-Ordnern und JSON-Dateien
Vereinfacht ohne komplexes Quiz-System - unterstützt nur Einzelfragen
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
            return data.get('minigames', [])
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

def get_random_minigame_from_folder(folder_name: str) -> Optional[Dict[str, Any]]:
    """Gibt ein zufälliges Minispiel oder eine Frage aus einem Ordner zurück"""
    minigames = get_minigames_from_folder(folder_name)
    
    if not minigames:
        return None
    
    import random
    return random.choice(minigames)

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

def get_random_content_from_folder(folder_name: str) -> Optional[Dict[str, Any]]:
    """Gibt zufälligen Inhalt (Minispiel oder Frage) aus einem Ordner zurück"""
    all_items = get_minigames_from_folder(folder_name)
    
    if not all_items:
        return None
    
    import random
    selected = random.choice(all_items)
    
    # Füge Typ-Info hinzu falls nicht vorhanden
    if 'type' not in selected:
        selected['type'] = 'game'  # Default zu game
    
    return selected