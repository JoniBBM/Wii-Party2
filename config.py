import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env')) # Lädt .env, falls vorhanden

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'eine-sehr-geheime-zeichenkette'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db') # Stellt sicher, dass app.db im Root-Verzeichnis des Projekts landet
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session-Konfiguration für Teams (kurze Session-Dauer)
    PERMANENT_SESSION_LIFETIME = 1800  # 30 Minuten
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'  # Automatisch True bei HTTPS
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # SSL/HTTPS-Konfiguration
    SSL_DISABLE = os.environ.get('SSL_DISABLE', 'False').lower() == 'true'
    SSL_CERT_PATH = os.environ.get('SSL_CERT_PATH') or os.path.join(basedir, 'certs', 'cert.pem')
    SSL_KEY_PATH = os.environ.get('SSL_KEY_PATH') or os.path.join(basedir, 'certs', 'key.pem')
    USE_HTTPS = os.environ.get('USE_HTTPS', 'False').lower() == 'true'
    HTTPS_PORT = int(os.environ.get('HTTPS_PORT', '5000'))
    HTTP_PORT = int(os.environ.get('HTTP_PORT', '8080'))  # Fallback HTTP Port
    FORCE_HTTPS_REDIRECT = os.environ.get('FORCE_HTTPS_REDIRECT', 'False').lower() == 'true'
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'admin'
    # Geändertes Standard-Admin-Passwort
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or '1234qwer!' 
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
    DEBUG_SPECIAL_FIELDS = False  # Zusätzliche Debug-Logs für Sonderfelder
    FORCE_SPECIAL_FIELD_TRIGGERS = False  # Immer Sonderfeld-Aktionen auslösen (nur für Tests)

    # Logging Konfiguration (optional, aber hilfreich für Debugging)
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')