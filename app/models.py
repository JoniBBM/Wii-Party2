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

    def get_total_score(self, game_session_id=None):
        # Stelle sicher, dass TeamMinigameScore hier bekannt ist.
        # Falls es zu Import-Zyklen kommt, könnte man den Import in die Methode verschieben.
        query = TeamMinigameScore.query.filter_by(team_id=self.id)
        if game_session_id:
            query = query.filter_by(game_session_id=game_session_id)
        total_score = sum(score.score for score in query.all() if score.score is not None)
        return total_score

    def __repr__(self):
        return f'<Team {self.name}>'

class Minigame(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(500))
    # HINZUGEFÜGT: type-Feld, basierend auf deiner MinigameForm und Routen-Logik
    type = db.Column(db.String(50), nullable=False, default='score') # default='score' oder was immer sinnvoll ist

    def __repr__(self):
        return f'<Minigame {self.name}>'

class TeamMinigameScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    minigame_id = db.Column(db.Integer, db.ForeignKey('minigame.id'), nullable=True) 
    score = db.Column(db.Integer, nullable=True)
    game_session_id = db.Column(db.Integer, db.ForeignKey('game_session.id'), nullable=False)

    team = db.relationship('Team', backref=db.backref('minigame_scores_history', lazy='dynamic'))
    minigame = db.relationship('Minigame', backref=db.backref('scores_history', lazy='dynamic'))
    game_session = db.relationship('GameSession', backref=db.backref('scores_in_session_history', lazy='dynamic'))

    def __repr__(self):
        return f'<TeamMinigameScore Team {self.team_id} Minigame {self.minigame_id} Score {self.score} Session {self.game_session_id}>'

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

    current_minigame_name = db.Column(db.String(200), nullable=True)
    current_minigame_description = db.Column(db.Text, nullable=True)
    selected_minigame_id = db.Column(db.Integer, db.ForeignKey('minigame.id'), nullable=True)
    selected_minigame = db.relationship('Minigame', foreign_keys=[selected_minigame_id])

    current_phase = db.Column(db.String(50), default='SETUP_MINIGAME') # z.B. SETUP_MINIGAME, MINIGAME_ANNOUNCED, DICE_ROLLING, ROUND_OVER
    dice_roll_order = db.Column(db.String(255), nullable=True) # Komma-separierte Team-IDs
    current_team_turn_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    current_team_turn = db.relationship('Team', foreign_keys=[current_team_turn_id])

    events = db.relationship('GameEvent', backref='game_session', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<GameSession {self.id} Active: {self.is_active} Phase: {self.current_phase}>'

class GameEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.Integer, db.ForeignKey('game_session.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    event_type = db.Column(db.String(50), nullable=False) # z.B. 'game_session_started', 'minigame_set', 'placements_recorded', 'dice_roll', 'team_login'
    description = db.Column(db.String(500), nullable=True)
    related_team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    related_minigame_id = db.Column(db.Integer, db.ForeignKey('minigame.id'), nullable=True)
    data_json = db.Column(db.Text, nullable=True) # Für zusätzliche strukturierte Daten als JSON-String

    # Beziehungen, um einfach auf zugehörige Objekte zugreifen zu können
    related_team = db.relationship('Team', foreign_keys=[related_team_id])
    related_minigame = db.relationship('Minigame', foreign_keys=[related_minigame_id])
    # game_session ist bereits über backref definiert

    def __repr__(self):
        return f'<GameEvent {self.id} Type: {self.event_type} Session: {self.game_session_id}>'
