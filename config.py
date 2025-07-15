import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env')) # Lädt .env, falls vorhanden

class Config:
    # Security Configuration - No default values for production secrets
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable is required")
    
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session-Konfiguration für Teams
    PERMANENT_SESSION_LIFETIME = 86400  # 24 Stunden
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1', 'on')
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Admin Configuration - No default passwords
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
    
    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        raise ValueError("ADMIN_USERNAME and ADMIN_PASSWORD environment variables are required") 
    MINIGAME_VIDEO_FOLDER = os.path.join(basedir, 'app', 'static', 'minigame_videos')

    # KONFIGURATION FÜR MINIGAME-ORDNER
    MINIGAME_FOLDERS_PATH = os.path.join(basedir, 'app', 'static', 'minigame_folders')
    
    # Konfiguration für Standardordner
    DEFAULT_MINIGAME_FOLDER = 'Default'
    
    # Maximale Anzahl an Minispielen pro Ordner (optional)
    MAX_MINIGAMES_PER_FOLDER = 100

    # SPIELBRETT-KONFIGURATION
    MAX_BOARD_FIELDS = 72  # Maximale Anzahl Felder auf dem Spielbrett (0-72 = 73 Felder)
    
    # BONUS-WÜRFEL-KONFIGURATION
    PLACEMENT_BONUS_DICE = {
        1: 6,  # 1. Platz erhält 1-6 Bonus-Würfel
        2: 4,  # 2. Platz erhält 1-4 Bonus-Würfel  
        3: 2   # 3. Platz erhält 1-2 Bonus-Würfel
    }
    
    # SONDERFELD-KONFIGURATIONEN
    # Katapult-Felder
    CATAPULT_FORWARD_DISTANCE = (3, 5)  # Min, Max Felder nach vorne
    CATAPULT_BACKWARD_DISTANCE = (2, 4)  # Min, Max Felder nach hinten
    
    # Sperren-Feld
    BARRIER_TARGET_NUMBERS = [4, 5, 6]  # Mögliche Zahlen die gewürfelt werden müssen
    BARRIER_RELEASE_PROBABILITY = 1.0  # Wahrscheinlichkeit pro Würfelwurf (1.0 = immer aktiv)
    
    # Spieler-Tausch
    PLAYER_SWAP_ENABLED = True
    PLAYER_SWAP_MIN_DISTANCE = 3  # Minimaler Abstand zwischen Tausch-Partnern
    
    # Feld-Verteilung (welche Positionen haben welche Sonderfelder)
    SPECIAL_FIELD_POSITIONS = {
        'catapult_forward': 15,   # Jedes 15. Feld (15, 30, 45, 60)
        'catapult_backward': 13,  # Jedes 13. Feld (13, 26, 39, 52, 65)
        'player_swap': 17,        # Jedes 17. Feld (17, 34, 51, 68)
        'barrier': 19             # Jedes 19. Feld (19, 38, 57)
    }
    
    # VULKAN-KONFIGURATION (für zukünftige Implementierung)
    VOLCANO_ENABLED = False  # Noch nicht implementiert
    VOLCANO_TRIGGER_PROBABILITY = 0.15  # 15% Chance pro Vulkanfeld-Besuch
    VOLCANO_MIN_COUNTDOWN = 3
    VOLCANO_MAX_COUNTDOWN = 8
    VOLCANO_PRESSURE_INCREASE = 10  # Druckerhöhung pro Trigger
    
    # FELDAKTIONS-KONFIGURATION
    FIELD_ACTION_ANIMATION_DURATION = 2000  # Millisekunden für Sonderfeld-Animationen
    FIELD_ACTION_PARTICLE_COUNT = 30  # Anzahl Partikel für Effekte
    
    # EVENT-LOGGING
    LOG_SPECIAL_FIELD_ACTIONS = True  # Sonderfeld-Aktionen in GameEvents protokollieren
    LOG_DICE_DETAILS = True  # Detaillierte Würfel-Logs
    
    # PERFORMANCE-EINSTELLUNGEN
    ANIMATION_QUALITY = 'high'  # 'low', 'medium', 'high'
    PARTICLE_EFFECTS = True
    SOUND_EFFECTS = True  # Für zukünftige Audio-Implementation
    
    # DEBUGGING
    DEBUG_SPECIAL_FIELDS = os.environ.get('DEBUG_SPECIAL_FIELDS', 'False').lower() in ('true', '1', 'on')
    FORCE_SPECIAL_FIELD_TRIGGERS = os.environ.get('FORCE_SPECIAL_FIELD_TRIGGERS', 'False').lower() in ('true', '1', 'on')

    # Logging Konfiguration (optional, aber hilfreich für Debugging)
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')