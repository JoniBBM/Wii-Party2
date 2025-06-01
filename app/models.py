from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime

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
        return f"admin_{self.id}" # Präfix für Admin IDs

    @property
    def is_admin(self):
        return True

    @property
    def is_team_user(self):
        return False

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
    is_admin_flag = db.Column(db.Boolean, default=False, nullable=False) # UserMixin Kompatibilität

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return f"team_{self.id}" # Präfix für Team IDs

    @property
    def is_admin(self):
        return False

    @property
    def is_team_user(self):
        return True

    def get_total_score(self, game_session_id=None):
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

    def __repr__(self):
        return f'<Minigame {self.name}>'

class TeamMinigameScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    minigame_id = db.Column(db.Integer, db.ForeignKey('minigame.id'), nullable=True) # Kann auch ein Ad-hoc Minispiel sein
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
    js_file = db.Column(db.String(120), nullable=True)
    color = db.Column(db.String(7), default="#FFFFFF")
    description = db.Column(db.Text, nullable=True)

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

    current_phase = db.Column(db.String(50), default='SETUP_MINIGAME')
    dice_roll_order = db.Column(db.String(255), nullable=True)
    current_team_turn_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    current_team_turn = db.relationship('Team', foreign_keys=[current_team_turn_id])

    events = db.relationship('GameEvent', backref='game_session', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<GameSession {self.id} Active: {self.is_active} Phase: {self.current_phase}>'

class GameEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.Integer, db.ForeignKey('game_session.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    event_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    related_team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    related_minigame_id = db.Column(db.Integer, db.ForeignKey('minigame.id'), nullable=True)
    data_json = db.Column(db.Text, nullable=True)

    related_team = db.relationship('Team', foreign_keys=[related_team_id])
    related_minigame = db.relationship('Minigame', foreign_keys=[related_minigame_id])

    def __repr__(self):
        return f'<GameEvent {self.id} Type: {self.event_type} Session: {self.game_session_id}>'
