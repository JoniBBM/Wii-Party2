"""
Utility-Funktionen für das Management von Minigame-Ordnern und JSON-Dateien
Erweitert um Quiz-Support
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
    create_minigame_folder_if_not_exists(default_folder, "Standard-Minispiele")

def create_minigame_folder_if_not_exists(folder_name: str, description: str = "") -> bool:
    """Erstellt einen neuen Minigame-Ordner falls er nicht existiert"""
    folders_path = get_minigame_folders_path()
    folder_path = os.path.join(folders_path, folder_name)
    
    if os.path.exists(folder_path):
        return False  # Ordner existiert bereits
    
    try:
        os.makedirs(folder_path, exist_ok=True)
        
        # Erstelle initiale JSON-Datei mit Quiz-Support
        initial_data = {
            "folder_info": {
                "name": folder_name,
                "description": description,
                "created_at": datetime.utcnow().isoformat()
            },
            "minigames": [],
            "quizzes": []
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
    """Lädt alle Minispiele aus einem Ordner"""
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
    """Fügt ein neues Minispiel zu einem Ordner hinzu"""
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
        
        # Füge Minispiel hinzu
        if 'minigames' not in data:
            data['minigames'] = []
        data['minigames'].append(minigame_data)
        
        # Stelle sicher, dass quizzes Array existiert (für Abwärtskompatibilität)
        if 'quizzes' not in data:
            data['quizzes'] = []
        
        # Speichere zurück
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        return True
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Hinzufügen des Minispiels zu {folder_name}: {e}")
        return False

def update_minigame_in_folder(folder_name: str, minigame_id: str, updated_data: Dict[str, Any]) -> bool:
    """Aktualisiert ein existierendes Minispiel in einem Ordner"""
    json_path = get_folder_json_path(folder_name)
    
    if not os.path.exists(json_path):
        return False
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        minigames = data.get('minigames', [])
        
        # Finde das zu aktualisierende Minispiel
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
            return False  # Minispiel nicht gefunden
        
        # Speichere zurück
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        return True
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Aktualisieren des Minispiels {minigame_id} in {folder_name}: {e}")
        return False

def delete_minigame_from_folder(folder_name: str, minigame_id: str) -> bool:
    """Löscht ein Minispiel aus einem Ordner"""
    json_path = get_folder_json_path(folder_name)
    
    if not os.path.exists(json_path):
        return False
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        minigames = data.get('minigames', [])
        original_count = len(minigames)
        
        # Filtere das zu löschende Minispiel heraus
        data['minigames'] = [mg for mg in minigames if mg.get('id') != minigame_id]
        
        if len(data['minigames']) == original_count:
            return False  # Nichts wurde gelöscht
        
        # Speichere zurück
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        return True
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Löschen des Minispiels {minigame_id} aus {folder_name}: {e}")
        return False

def get_minigame_from_folder(folder_name: str, minigame_id: str) -> Optional[Dict[str, Any]]:
    """Lädt ein spezifisches Minispiel aus einem Ordner"""
    minigames = get_minigames_from_folder(folder_name)
    
    for minigame in minigames:
        if minigame.get('id') == minigame_id:
            return minigame
    
    return None

def get_random_minigame_from_folder(folder_name: str) -> Optional[Dict[str, Any]]:
    """Gibt ein zufälliges Minispiel aus einem Ordner zurück"""
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

# NEUE QUIZ-FUNKTIONEN

def get_quizzes_from_folder(folder_name: str) -> List[Dict[str, Any]]:
    """Lädt alle Quizzes aus einem Ordner"""
    json_path = get_folder_json_path(folder_name)
    
    if not os.path.exists(json_path):
        return []
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('quizzes', [])
    except Exception as e:
        current_app.logger.error(f"Fehler beim Laden der Quizzes aus {folder_name}: {e}")
        return []

def add_quiz_to_folder(folder_name: str, quiz_data: Dict[str, Any]) -> bool:
    """Fügt ein neues Quiz zu einem Ordner hinzu"""
    json_path = get_folder_json_path(folder_name)
    
    if not os.path.exists(json_path):
        current_app.logger.error(f"Ordner {folder_name} existiert nicht")
        return False
    
    try:
        # Lade existierende Daten
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Generiere eindeutige ID falls nicht vorhanden
        if 'id' not in quiz_data or not quiz_data['id']:
            quiz_data['id'] = str(uuid.uuid4())[:8]
        
        # Füge Timestamp hinzu
        quiz_data['created_at'] = datetime.utcnow().isoformat()
        
        # Prüfe auf doppelte IDs
        existing_ids = [quiz.get('id') for quiz in data.get('quizzes', [])]
        if quiz_data['id'] in existing_ids:
            quiz_data['id'] = str(uuid.uuid4())[:8]  # Neue ID generieren
        
        # Füge Quiz hinzu
        if 'quizzes' not in data:
            data['quizzes'] = []
        data['quizzes'].append(quiz_data)
        
        # Speichere zurück
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        return True
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Hinzufügen des Quiz zu {folder_name}: {e}")
        return False

def update_quiz_in_folder(folder_name: str, quiz_id: str, updated_data: Dict[str, Any]) -> bool:
    """Aktualisiert ein existierendes Quiz in einem Ordner"""
    json_path = get_folder_json_path(folder_name)
    
    if not os.path.exists(json_path):
        return False
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        quizzes = data.get('quizzes', [])
        
        # Finde das zu aktualisierende Quiz
        for i, quiz in enumerate(quizzes):
            if quiz.get('id') == quiz_id:
                # Behalte original ID und created_at
                updated_data['id'] = quiz_id
                if 'created_at' in quiz:
                    updated_data['created_at'] = quiz['created_at']
                updated_data['updated_at'] = datetime.utcnow().isoformat()
                
                quizzes[i] = updated_data
                break
        else:
            return False  # Quiz nicht gefunden
        
        # Speichere zurück
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        return True
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Aktualisieren des Quiz {quiz_id} in {folder_name}: {e}")
        return False

def delete_quiz_from_folder(folder_name: str, quiz_id: str) -> bool:
    """Löscht ein Quiz aus einem Ordner"""
    json_path = get_folder_json_path(folder_name)
    
    if not os.path.exists(json_path):
        return False
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        quizzes = data.get('quizzes', [])
        original_count = len(quizzes)
        
        # Filtere das zu löschende Quiz heraus
        data['quizzes'] = [quiz for quiz in quizzes if quiz.get('id') != quiz_id]
        
        if len(data['quizzes']) == original_count:
            return False  # Nichts wurde gelöscht
        
        # Speichere zurück
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        return True
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Löschen des Quiz {quiz_id} aus {folder_name}: {e}")
        return False

def get_quiz_from_folder(folder_name: str, quiz_id: str) -> Optional[Dict[str, Any]]:
    """Lädt ein spezifisches Quiz aus einem Ordner"""
    quizzes = get_quizzes_from_folder(folder_name)
    
    for quiz in quizzes:
        if quiz.get('id') == quiz_id:
            return quiz
    
    return None

def get_random_quiz_from_folder(folder_name: str) -> Optional[Dict[str, Any]]:
    """Gibt ein zufälliges Quiz aus einem Ordner zurück"""
    quizzes = get_quizzes_from_folder(folder_name)
    
    if not quizzes:
        return None
    
    import random
    return random.choice(quizzes)

def get_all_content_from_folder(folder_name: str) -> Dict[str, List[Dict[str, Any]]]:
    """Gibt alle Inhalte (Minispiele + Quizzes) aus einem Ordner zurück"""
    return {
        'minigames': get_minigames_from_folder(folder_name),
        'quizzes': get_quizzes_from_folder(folder_name)
    }

def get_random_content_from_folder(folder_name: str) -> Optional[Dict[str, Any]]:
    """Gibt zufälligen Inhalt (Minispiel oder Quiz) aus einem Ordner zurück"""
    content = get_all_content_from_folder(folder_name)
    all_items = content['minigames'] + content['quizzes']
    
    if not all_items:
        return None
    
    import random
    selected = random.choice(all_items)
    
    # Füge Typ-Info hinzu falls nicht vorhanden
    if 'content_type' not in selected:
        if selected in content['quizzes']:
            selected['content_type'] = 'quiz'
        else:
            selected['content_type'] = 'minigame'
    
    return selected