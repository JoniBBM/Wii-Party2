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
    
    # NEUE FELDER FÜR FELDAKTIONEN
    is_blocked = db.Column(db.Boolean, default=False, nullable=False)  # Spieler blockiert
    blocked_turns_remaining = db.Column(db.Integer, default=0)  # Runden blockiert
    extra_moves_remaining = db.Column(db.Integer, default=0)  # Extra-Bewegungen
    has_shield = db.Column(db.Boolean, default=False, nullable=False)  # Schutz vor Fallen
    last_field_action_id = db.Column(db.Integer, db.ForeignKey('field_action_result.id'), nullable=True)

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
    
    # NEUE FELDER FÜR VULKAN-SYSTEM
    volcano_countdown = db.Column(db.Integer, default=0)  # Countdown bis Vulkanausbruch
    volcano_active = db.Column(db.Boolean, default=False, nullable=False)  # Vulkan bereit für Ausbruch
    volcano_last_triggered = db.Column(db.DateTime, nullable=True)  # Letzter Ausbruch
    
    # FELDAKTIONS-STATUS
    pending_field_action = db.Column(db.Text, nullable=True)  # JSON für wartende Aktion
    current_field_action_team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)

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

    def set_pending_field_action(self, action_data):
        """Setzt eine wartende Feldaktion"""
        self.pending_field_action = json.dumps(action_data)

    def get_pending_field_action(self):
        """Gibt wartende Feldaktion zurück"""
        if self.pending_field_action:
            try:
                return json.loads(self.pending_field_action)
            except:
                return None
        return None

    def clear_pending_field_action(self):
        """Löscht wartende Feldaktion"""
        self.pending_field_action = None
        self.current_field_action_team_id = None

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

# NEUE MODELLE FÜR FELDAKTIONEN

class FieldType(db.Model):
    """Definiert verschiedene Feldtypen und ihre Eigenschaften"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # z.B. 'volcano', 'teleport', 'bonus'
    display_name = db.Column(db.String(100), nullable=False)  # z.B. 'Vulkan-Feld'
    description = db.Column(db.Text, nullable=True)
    color = db.Column(db.String(7), default='#FF0000')  # Hex-Farbe
    icon = db.Column(db.String(20), nullable=True)  # Unicode-Icon oder CSS-Klasse
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    probability = db.Column(db.Float, default=1.0)  # Wahrscheinlichkeit für zufällige Platzierung
    
    # Konfiguration als JSON
    config_json = db.Column(db.Text, nullable=True)  # Parameter für das Feld
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_config(self):
        """Gibt Konfiguration als Dictionary zurück"""
        if self.config_json:
            try:
                return json.loads(self.config_json)
            except:
                return {}
        return {}

    def set_config(self, config_dict):
        """Setzt Konfiguration als JSON"""
        self.config_json = json.dumps(config_dict)

    def __repr__(self):
        return f'<FieldType {self.name}: {self.display_name}>'

class BoardField(db.Model):
    """Definiert spezielle Felder auf dem Spielbrett"""
    id = db.Column(db.Integer, primary_key=True)
    position = db.Column(db.Integer, nullable=False)  # Feldposition (0-72)
    field_type_id = db.Column(db.Integer, db.ForeignKey('field_type.id'), nullable=True)
    field_type = db.relationship('FieldType', backref='board_fields')
    
    # Optionale Überschreibung der Feldtyp-Konfiguration
    custom_config_json = db.Column(db.Text, nullable=True)
    
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_effective_config(self):
        """Gibt die effektive Konfiguration zurück (custom oder vom Typ)"""
        if self.custom_config_json:
            try:
                return json.loads(self.custom_config_json)
            except:
                pass
        
        if self.field_type:
            return self.field_type.get_config()
        
        return {}

    def set_custom_config(self, config_dict):
        """Setzt benutzerdefinierte Konfiguration"""
        self.custom_config_json = json.dumps(config_dict)

    def __repr__(self):
        return f'<BoardField {self.position}: {self.field_type.name if self.field_type else "Normal"}>'

class FieldActionResult(db.Model):
    """Protokolliert ausgeführte Feldaktionen"""
    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.Integer, db.ForeignKey('game_session.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    field_position = db.Column(db.Integer, nullable=False)
    field_type_id = db.Column(db.Integer, db.ForeignKey('field_type.id'), nullable=True)
    
    action_type = db.Column(db.String(50), nullable=False)  # z.B. 'move_backward', 'extra_dice', 'volcano_eruption'
    action_data_json = db.Column(db.Text, nullable=True)  # Parameter der Aktion
    result_data_json = db.Column(db.Text, nullable=True)  # Ergebnis der Aktion
    
    executed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Beziehungen
    game_session = db.relationship('GameSession', backref='field_action_results')
    team = db.relationship('Team', backref='field_action_results')
    field_type = db.relationship('FieldType', backref='action_results')

    def get_action_data(self):
        """Gibt Aktionsdaten als Dictionary zurück"""
        if self.action_data_json:
            try:
                return json.loads(self.action_data_json)
            except:
                return {}
        return {}

    def set_action_data(self, data_dict):
        """Setzt Aktionsdaten als JSON"""
        self.action_data_json = json.dumps(data_dict)

    def get_result_data(self):
        """Gibt Ergebnisdaten als Dictionary zurück"""
        if self.result_data_json:
            try:
                return json.loads(self.result_data_json)
            except:
                return {}
        return {}

    def set_result_data(self, data_dict):
        """Setzt Ergebnisdaten als JSON"""
        self.result_data_json = json.dumps(data_dict)

    def __repr__(self):
        return f'<FieldActionResult {self.action_type} Team:{self.team_id} Field:{self.field_position}>'

class VolcanoState(db.Model):
    """Verwaltet den globalen Vulkan-Zustand"""
    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.Integer, db.ForeignKey('game_session.id'), nullable=False, unique=True)
    
    # Vulkan-Status
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    countdown = db.Column(db.Integer, default=0)
    pressure_level = db.Column(db.Integer, default=0)  # 0-100, beeinflusst Ausbruchswahrscheinlichkeit
    
    # Ausbruch-Konfiguration
    min_countdown = db.Column(db.Integer, default=3)
    max_countdown = db.Column(db.Integer, default=8)
    trigger_probability = db.Column(db.Float, default=0.15)  # Wahrscheinlichkeit pro Vulkanfeld-Besuch
    
    # Statistiken
    total_eruptions = db.Column(db.Integer, default=0)
    last_eruption_at = db.Column(db.DateTime, nullable=True)
    
    # Beziehungen
    game_session = db.relationship('GameSession', backref=db.backref('volcano_state', uselist=False))

    def increase_pressure(self, amount=10):
        """Erhöht Vulkandruck"""
        self.pressure_level = min(100, self.pressure_level + amount)

    def can_trigger_eruption(self):
        """Prüft ob Vulkanausbruch möglich ist"""
        base_probability = self.trigger_probability
        pressure_bonus = self.pressure_level / 100 * 0.3  # Bis zu 30% Bonus durch Druck
        total_probability = min(0.8, base_probability + pressure_bonus)
        
        import random
        return random.random() < total_probability

    def trigger_eruption(self):
        """Startet Vulkanausbruch-Countdown"""
        if not self.is_active:
            import random
            self.countdown = random.randint(self.min_countdown, self.max_countdown)
            self.is_active = True
            self.pressure_level = 0  # Reset Druck

    def tick_countdown(self):
        """Reduziert Countdown um 1"""
        if self.is_active and self.countdown > 0:
            self.countdown -= 1
            return self.countdown <= 0  # True wenn Ausbruch jetzt stattfindet

    def execute_eruption(self):
        """Führt Vulkanausbruch aus"""
        self.is_active = False
        self.countdown = 0
        self.total_eruptions += 1
        self.last_eruption_at = datetime.utcnow()
        self.pressure_level = 0

    def __repr__(self):
        return f'<VolcanoState Session:{self.game_session_id} Active:{self.is_active} Countdown:{self.countdown}>'