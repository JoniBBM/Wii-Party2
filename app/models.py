from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime

# Es ist üblich, db direkt zu importieren, wenn es in __init__.py definiert ist.
# Wenn db hier initialisiert wird, ist das auch okay.
# Annahme: db wird von irgendwo importiert (z.B. from . import db oder from yourapp import db)
# Basierend auf deinem Code-Snippet, scheint es from . import db zu sein.
from . import db

class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_admin_flag = db.Column(db.Boolean, default=True, nullable=False) # Für UserMixin is_admin Logik

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return f"admin_{self.id}"

    @property
    def is_admin(self): # Explizit für Admin-Rollenprüfung
        return self.is_admin_flag

    @property
    def is_team_user(self):
        return not self.is_admin_flag

    def __repr__(self):
        return f'<Admin {self.username}>'

class Team(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True) # Erlaube leere Passwörter für Teams
    members = db.Column(db.String(255), nullable=True)

    character_name = db.Column(db.String(100), nullable=True) # Wird in Routen gesetzt
    character_id = db.Column(db.Integer, db.ForeignKey('character.id'), nullable=True)
    character = db.relationship('Character', backref='teams') # backref war 'teams', nicht 'team'

    current_position = db.Column(db.Integer, default=0)
    minigame_placement = db.Column(db.Integer, nullable=True)
    bonus_dice_sides = db.Column(db.Integer, default=0)
    is_admin_flag = db.Column(db.Boolean, default=False, nullable=False) # Für UserMixin is_admin Logik

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash: # Wenn kein Passwort gesetzt ist
            return False
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return f"team_{self.id}"

    @property
    def is_admin(self): # Explizit für Admin-Rollenprüfung
        return self.is_admin_flag

    @property
    def is_team_user(self):
        return not self.is_admin_flag

    def __repr__(self):
        return f'<Team {self.name}>'

# NEUE MODELS FÜR MINIGAME-ORDNER & SPIELRUNDEN

class MinigameFolder(db.Model):
    """Verwaltet persistente Minigame-Ordner im Static-Verzeichnis"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)  # z.B. "Sommer2025"
    description = db.Column(db.String(500), nullable=True)
    folder_path = db.Column(db.String(200), nullable=False)  # Relativer Pfad z.B. "Sommer2025"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Beziehung zu GameRounds die diesen Ordner verwenden
    game_rounds = db.relationship('GameRound', backref='minigame_folder', lazy='dynamic')

    def get_minigames_count(self):
        """Gibt die Anzahl der Minispiele in diesem Ordner zurück"""
        from app.admin.minigame_utils import get_minigames_from_folder
        try:
            minigames = get_minigames_from_folder(self.folder_path)
            return len(minigames)
        except:
            return 0

    def __repr__(self):
        return f'<MinigameFolder {self.name}>'

class GameRound(db.Model):
    """Verwaltet Spielrunden mit zugewiesenem Minigame-Ordner"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)  # z.B. "Sommer2025-Turnier"
    description = db.Column(db.String(500), nullable=True)
    minigame_folder_id = db.Column(db.Integer, db.ForeignKey('minigame_folder.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Beziehung zu GameSessions die zu dieser Runde gehören
    game_sessions = db.relationship('GameSession', backref='game_round', lazy='dynamic')

    def activate(self):
        """Aktiviert diese Runde und deaktiviert alle anderen"""
        # Alle anderen Runden deaktivieren
        GameRound.query.update({'is_active': False})
        # Diese Runde aktivieren
        self.is_active = True
        db.session.commit()

    @classmethod
    def get_active_round(cls):
        """Gibt die aktuell aktive Runde zurück"""
        return cls.query.filter_by(is_active=True).first()

    def __repr__(self):
        return f'<GameRound {self.name} (Active: {self.is_active})>'

# QUIZ-SYSTEM MODELS

class QuizResponse(db.Model):
    """Speichert Team-Antworten auf Quiz-Fragen"""
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    game_session_id = db.Column(db.Integer, db.ForeignKey('game_session.id'), nullable=False)
    
    # Quiz-Identifikation (aus JSON-Datei)
    quiz_id = db.Column(db.String(100), nullable=False)  # UUID aus JSON
    question_id = db.Column(db.String(100), nullable=False)  # UUID aus JSON
    
    # Antwort-Daten
    answer_text = db.Column(db.Text, nullable=True)  # Freitext-Antwort
    selected_option = db.Column(db.Integer, nullable=True)  # Multiple Choice (Index)
    is_correct = db.Column(db.Boolean, nullable=True)  # Wird beim Bewerten gesetzt
    points_earned = db.Column(db.Integer, default=0)
    
    # Zeitstempel
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)
    time_taken_seconds = db.Column(db.Integer, nullable=True)  # Zeit zum Antworten
    
    # Beziehungen
    team = db.relationship('Team', backref=db.backref('quiz_responses', lazy='dynamic'))
    game_session = db.relationship('GameSession', backref=db.backref('quiz_responses', lazy='dynamic'))

    def __repr__(self):
        return f'<QuizResponse Team {self.team_id} Quiz {self.quiz_id} Question {self.question_id}>'

class Character(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    image_file = db.Column(db.String(120), nullable=True)
    js_file = db.Column(db.String(120), nullable=True) # Pfad zur JS-Datei des Charakters
    color = db.Column(db.String(7), default="#FFFFFF") # Hex-Farbcode für den Charakter
    description = db.Column(db.Text, nullable=True)
    # HINZUGEFÜGT: is_selected Feld
    is_selected = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f'<Character {self.name}>'

class GameSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # ERWEITERT: Verknüpfung zu GameRound
    game_round_id = db.Column(db.Integer, db.ForeignKey('game_round.id'), nullable=True)

    current_minigame_name = db.Column(db.String(200), nullable=True)
    current_minigame_description = db.Column(db.Text, nullable=True)
    
    # ERWEITERT: Quiz-Support
    current_quiz_id = db.Column(db.String(100), nullable=True)  # UUID aus JSON-Datei
    quiz_time_limit = db.Column(db.Integer, nullable=True)  # Zeitlimit in Sekunden
    quiz_started_at = db.Column(db.DateTime, nullable=True)
    
    # ERWEITERT: Zusätzliche Felder für Minigame-Auswahl
    selected_folder_minigame_id = db.Column(db.String(100), nullable=True)  # ID aus JSON-Datei
    minigame_source = db.Column(db.String(50), default='manual')  # 'manual', 'folder_random', 'folder_selected'

    current_phase = db.Column(db.String(50), default='SETUP_MINIGAME') 
    # Mögliche Phasen: SETUP_MINIGAME, MINIGAME_ANNOUNCED, QUIZ_ACTIVE, QUIZ_COMPLETED, DICE_ROLLING, ROUND_OVER
    
    dice_roll_order = db.Column(db.String(255), nullable=True) # Komma-separierte Team-IDs
    current_team_turn_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    current_team_turn = db.relationship('Team', foreign_keys=[current_team_turn_id])

    events = db.relationship('GameEvent', backref='game_session', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<GameSession {self.id} Round: {self.game_round_id} Active: {self.is_active} Phase: {self.current_phase}>'

class GameEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.Integer, db.ForeignKey('game_session.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    event_type = db.Column(db.String(50), nullable=False) 
    # z.B. 'game_session_started', 'minigame_set', 'quiz_started', 'quiz_completed', 'placements_recorded', 'dice_roll', 'team_login'
    description = db.Column(db.String(500), nullable=True)
    related_team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    data_json = db.Column(db.Text, nullable=True) # Für zusätzliche strukturierte Daten als JSON-String

    # Beziehungen, um einfach auf zugehörige Objekte zugreifen zu können
    related_team = db.relationship('Team', foreign_keys=[related_team_id])
    # game_session ist bereits über backref definiert

    def __repr__(self):
        return f'<GameEvent {self.id} Type: {self.event_type} Session: {self.game_session_id}>'