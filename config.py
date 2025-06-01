import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env')) # Lädt .env, falls vorhanden

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'eine-sehr-geheime-zeichenkette'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db') # Stellt sicher, dass app.db im Root-Verzeichnis des Projekts landet
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'admin'
    # Geändertes Standard-Admin-Passwort
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or '1234qwer!' 
    MINIGAME_VIDEO_FOLDER = os.path.join(basedir, 'app', 'static', 'minigame_videos')

    # Logging Konfiguration (optional, aber hilfreich für Debugging)
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
