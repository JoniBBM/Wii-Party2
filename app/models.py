from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime
import json

from . import db

class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_admin_flag = db.Column(db.Boolean, default=True, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return f"admin_{self.id}"

    @property
    def is_admin(self):
        return self.is_admin_flag

    @property
    def is_team_user(self):
        return not self.is_admin_flag

    def __repr__(self):
        return f'<Admin {self.username}>'

class Team(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)
    members = db.Column(db.String(255), nullable=True)

    character_name = db.Column(db.String(100), nullable=True)
    character_id = db.Column(db.Integer, db.ForeignKey('character.id'), nullable=True)
    character = db.relationship('Character', backref='teams')

    current_position = db.Column(db.Integer, default=0)
    minigame_placement = db.Column(db.Integer, nullable=True)
    bonus_dice_sides = db.Column(db.Integer, default=0)
    is_admin_flag = db.Column(db.Boolean, default=False, nullable=False)
    
    # SONDERFELD-FELDER (vereinfacht)
    is_blocked = db.Column(db.Boolean, default=False, nullable=False)  # Spieler blockiert
    blocked_target_number = db.Column(db.Integer, nullable=True)  # Zahl die gewürfelt werden muss
    blocked_turns_remaining = db.Column(db.Integer, default=0)  # Runden blockiert
    extra_moves_remaining = db.Column(db.Integer, default=0)  # Extra-Bewegungen
    has_shield = db.Column(db.Boolean, default=False, nullable=False)  # Schutz vor Fallen

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return f"team_{self.id}"

    @property
    def is_admin(self):
        return self.is_admin_flag

    @property
    def is_team_user(self):
        return not self.is_admin_flag

    def apply_block(self, turns=1):
        """Blockiert das Team für eine bestimmte Anzahl von Zügen"""
        self.is_blocked = True
        self.blocked_turns_remaining = turns

    def reduce_block(self):
        """Reduziert die Blockierung um einen Zug"""
        if self.blocked_turns_remaining > 0:
            self.blocked_turns_remaining -= 1
            if self.blocked_turns_remaining <= 0:
                self.is_blocked = False

    def add_extra_moves(self, moves=1):
        """Fügt Extra-Bewegungen hinzu"""
        self.extra_moves_remaining += moves

    def use_extra_move(self):
        """Verwendet eine Extra-Bewegung"""
        if self.extra_moves_remaining > 0:
            self.extra_moves_remaining -= 1
            return True
        return False

    def reset_special_field_status(self):
        """Setzt alle Sonderfeld-Stati zurück"""
        self.is_blocked = False
        self.blocked_target_number = None
        self.blocked_turns_remaining = 0
        self.extra_moves_remaining = 0
        self.has_shield = False

    def __repr__(self):
        return f'<Team {self.name}>'

class MinigameFolder(db.Model):
    """Verwaltet persistente Minigame-Ordner im Static-Verzeichnis"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(500), nullable=True)
    folder_path = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    game_rounds = db.relationship('GameRound', backref='minigame_folder', lazy='dynamic')

    def get_minigames_count(self):
        """Gibt die Anzahl der Minispiele und Fragen in diesem Ordner zurück"""
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
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(500), nullable=True)
    minigame_folder_id = db.Column(db.Integer, db.ForeignKey('minigame_folder.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    game_sessions = db.relationship('GameSession', backref='game_round', lazy='dynamic')

    def activate(self):
        """Aktiviert diese Runde und deaktiviert alle anderen"""
        GameRound.query.update({'is_active': False})
        self.is_active = True
        db.session.commit()

    @classmethod
    def get_active_round(cls):
        """Gibt die aktuell aktive Runde zurück"""
        return cls.query.filter_by(is_active=True).first()

    def __repr__(self):
        return f'<GameRound {self.name} (Active: {self.is_active})>'

class QuestionResponse(db.Model):
    """Speichert Team-Antworten auf Einzelfragen - ohne Punkte-System"""
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    game_session_id = db.Column(db.Integer, db.ForeignKey('game_session.id'), nullable=False)
    
    # Frage-Identifikation (aus JSON-Datei)
    question_id = db.Column(db.String(100), nullable=False)
    
    # Antwort-Daten
    answer_text = db.Column(db.Text, nullable=True)  # Freitext-Antwort
    selected_option = db.Column(db.Integer, nullable=True)  # Multiple Choice (Index)
    is_correct = db.Column(db.Boolean, nullable=True)
    
    # Zeitstempel für automatische Platzierung
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)
    time_taken_seconds = db.Column(db.Integer, nullable=True)
    
    # Beziehungen
    team = db.relationship('Team', backref=db.backref('question_responses', lazy='dynamic'))
    game_session = db.relationship('GameSession', backref=db.backref('question_responses', lazy='dynamic'))

    def __repr__(self):
        return f'<QuestionResponse Team {self.team_id} Question {self.question_id}>'

class Character(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    image_file = db.Column(db.String(120), nullable=True)
    js_file = db.Column(db.String(120), nullable=True)
    color = db.Column(db.String(7), default="#FFFFFF")
    description = db.Column(db.Text, nullable=True)
    is_selected = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f'<Character {self.name}>'

class GameSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Verknüpfung zu GameRound
    game_round_id = db.Column(db.Integer, db.ForeignKey('game_round.id'), nullable=True)

    current_minigame_name = db.Column(db.String(200), nullable=True)
    current_minigame_description = db.Column(db.Text, nullable=True)
    
    # Für Einzelfragen
    current_question_id = db.Column(db.String(100), nullable=True)  # UUID aus JSON-Datei
    
    # Zusätzliche Felder für Minigame-Auswahl
    selected_folder_minigame_id = db.Column(db.String(100), nullable=True)  # ID aus JSON-Datei
    minigame_source = db.Column(db.String(50), default='manual')  # 'manual', 'folder_random', 'folder_selected', 'direct_question'

    # Tracking für bereits gespielte Inhalte
    played_content_ids = db.Column(db.Text, nullable=True, default='')  # Komma-separierte Liste von gespielten IDs

    current_phase = db.Column(db.String(50), default='SETUP_MINIGAME') 
    # Mögliche Phasen: SETUP_MINIGAME, MINIGAME_ANNOUNCED, QUESTION_ACTIVE, QUESTION_COMPLETED, DICE_ROLLING, ROUND_OVER, FIELD_ACTION
    
    dice_roll_order = db.Column(db.String(255), nullable=True)
    current_team_turn_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    current_team_turn = db.relationship('Team', foreign_keys=[current_team_turn_id])
    
    # VULKAN-SYSTEM (vereinfacht, für zukünftige Erweiterung)
    volcano_countdown = db.Column(db.Integer, default=0)  # Countdown bis Vulkanausbruch
    volcano_active = db.Column(db.Boolean, default=False, nullable=False)  # Vulkan bereit für Ausbruch
    volcano_last_triggered = db.Column(db.DateTime, nullable=True)  # Letzter Ausbruch

    events = db.relationship('GameEvent', backref='game_session', lazy='dynamic', cascade="all, delete-orphan")

    def get_played_content_ids(self):
        """Gibt eine Liste der bereits gespielten Content-IDs zurück"""
        if not self.played_content_ids:
            return []
        return [content_id.strip() for content_id in self.played_content_ids.split(',') if content_id.strip()]

    def add_played_content_id(self, content_id):
        """Fügt eine Content-ID zur Liste der gespielten Inhalte hinzu"""
        played_ids = self.get_played_content_ids()
        if content_id not in played_ids:
            played_ids.append(content_id)
            self.played_content_ids = ','.join(played_ids)

    def reset_played_content(self):
        """Setzt die Liste der gespielten Inhalte zurück"""
        self.played_content_ids = ''

    def is_content_already_played(self, content_id):
        """Prüft, ob ein Inhalt bereits gespielt wurde"""
        return content_id in self.get_played_content_ids()

    def trigger_volcano_countdown(self, countdown=5):
        """Startet den Vulkan-Countdown"""
        self.volcano_countdown = countdown
        self.volcano_active = False

    def tick_volcano_countdown(self):
        """Reduziert Vulkan-Countdown und aktiviert bei 0"""
        if self.volcano_countdown > 0:
            self.volcano_countdown -= 1
            if self.volcano_countdown <= 0:
                self.volcano_active = True
                return True  # Vulkan ist bereit
        return False

    def trigger_volcano_eruption(self):
        """Triggert Vulkanausbruch"""
        self.volcano_active = False
        self.volcano_countdown = 0
        self.volcano_last_triggered = datetime.utcnow()

    def __repr__(self):
        return f'<GameSession {self.id} Round: {self.game_round_id} Active: {self.is_active} Phase: {self.current_phase}>'

class GameEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.Integer, db.ForeignKey('game_session.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    event_type = db.Column(db.String(50), nullable=False) 
    # z.B. 'game_session_started', 'minigame_set', 'question_started', 'question_completed', 'placements_recorded', 'dice_roll', 'team_login', 'field_action', 'volcano_eruption'
    description = db.Column(db.String(500), nullable=True)
    related_team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    data_json = db.Column(db.Text, nullable=True)

    related_team = db.relationship('Team', foreign_keys=[related_team_id])

    def __repr__(self):
        return f'<GameEvent {self.id} Type: {self.event_type} Session: {self.game_session_id}>'