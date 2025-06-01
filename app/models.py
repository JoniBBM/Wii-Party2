from flask_sqlalchemy import SQLAlchemy # Nur für den Fall, dass es woanders gebraucht wird, aber db kommt von app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime

# Importiere die 'db'-Instanz, die in app/__init__.py definiert wurde.
# Dies stellt sicher, dass alle Teile deiner Anwendung dieselbe SQLAlchemy-Instanz verwenden.
from . import db  # Der Punkt . importiert aus dem aktuellen Paket (__init__.py)

class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Admin {self.username}>'

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    character_name = db.Column(db.String(100), nullable=True)
    
    def __repr__(self):
        return f'<Team {self.name}>'

    def get_total_score(self, game_session_id=None):
        query = TeamMinigameScore.query.filter_by(team_id=self.id)
        if game_session_id:
            query = query.filter_by(game_session_id=game_session_id)
        
        total_score = sum(score.score for score in query.all() if score.score is not None)
        return total_score

class Minigame(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(200))
    is_video_game = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f'<Minigame {self.name}>'

class TeamMinigameScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    minigame_id = db.Column(db.Integer, db.ForeignKey('minigame.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    game_session_id = db.Column(db.Integer, db.ForeignKey('game_session.id'), nullable=False)

    team = db.relationship('Team', backref=db.backref('scores', lazy='dynamic'))
    minigame = db.relationship('Minigame', backref=db.backref('scores', lazy='dynamic'))
    game_session = db.relationship('GameSession', backref=db.backref('scores_in_session', lazy='dynamic'))

    def __repr__(self):
        return f'<TeamMinigameScore Team {self.team_id} Minigame {self.minigame_id} Score {self.score} Session {self.game_session_id}>'

class Character(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    image_file = db.Column(db.String(120), nullable=True)
    js_file = db.Column(db.String(120), nullable=True)

    def __repr__(self):
        return f'<Character {self.name}>'

class GameSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    current_minigame_id = db.Column(db.Integer, db.ForeignKey('minigame.id'), nullable=True)

    current_minigame = db.relationship('Minigame', foreign_keys=[current_minigame_id])
    events = db.relationship('GameEvent', backref='game_session', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<GameSession {self.id} Active: {self.is_active}>'

class GameEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.Integer, db.ForeignKey('game_session.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    event_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<GameEvent {self.id} Type: {self.event_type} Session: {self.game_session_id}>'
