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
    # Neues Feld für Welcome-System (nur 6-stellige Passwörter, temporär gespeichert)
    welcome_password = db.Column(db.String(10), nullable=True)
    members = db.Column(db.String(255), nullable=True)
    # Erweiterte Spieler-Konfiguration (JSON mit Spieler-Details)
    player_config = db.Column(db.Text, nullable=True)  # JSON mit Spieler-Einstellungen

    character_name = db.Column(db.String(100), nullable=True)
    character_id = db.Column(db.Integer, db.ForeignKey('character.id'), nullable=True)
    character = db.relationship('Character', backref='teams')

    current_position = db.Column(db.Integer, default=0)
    minigame_placement = db.Column(db.Integer, nullable=True)
    bonus_dice_sides = db.Column(db.Integer, default=0)
    last_dice_result = db.Column(db.Integer, nullable=True)  # Letztes Würfelergebnis
    is_admin_flag = db.Column(db.Boolean, default=False, nullable=False)
    
    # SONDERFELD-FELDER (vereinfacht)
    is_blocked = db.Column(db.Boolean, default=False, nullable=False)  # Spieler blockiert
    blocked_target_number = db.Column(db.Integer, nullable=True)  # Zahl die gewürfelt werden muss (backward compatibility)
    blocked_config = db.Column(db.Text, nullable=True)  # JSON config for barrier conditions
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

    def get_player_config(self):
        """Gibt die Spieler-Konfiguration als Dictionary zurück"""
        if not self.player_config:
            return {}
        try:
            return json.loads(self.player_config)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_player_config(self, config_dict):
        """Setzt die Spieler-Konfiguration aus Dictionary"""
        if config_dict is None:
            self.player_config = None
        else:
            self.player_config = json.dumps(config_dict)

    def get_selectable_players(self):
        """Gibt eine Liste der Spieler zurück, die für Auslosung verfügbar sind"""
        if not self.members:
            return []
        
        all_players = [m.strip() for m in self.members.split(',') if m.strip()]
        player_config = self.get_player_config()
        
        # Filtere Spieler, die nicht ausgelost werden sollen
        selectable = []
        for player in all_players:
            player_settings = player_config.get(player, {})
            if player_settings.get('can_be_selected', True):  # Default: kann ausgelost werden
                selectable.append(player)
        
        return selectable

    def update_player_selection_status(self, player_name, can_be_selected=True):
        """Aktualisiert den Auslosungs-Status eines Spielers"""
        config = self.get_player_config()
        if player_name not in config:
            config[player_name] = {}
        config[player_name]['can_be_selected'] = can_be_selected
        self.set_player_config(config)

    def __repr__(self):
        return f'<Team {self.name}>'

class FieldConfiguration(db.Model):
    """Konfiguration für Spielfeld-Typen und deren Häufigkeiten"""
    id = db.Column(db.Integer, primary_key=True)
    field_type = db.Column(db.String(50), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    
    # Aktivierung
    is_enabled = db.Column(db.Boolean, default=True, nullable=False)
    
    # Häufigkeits-Konfiguration
    frequency_type = db.Column(db.String(20), default='modulo', nullable=False)  # 'modulo', 'fixed_positions', 'probability'
    frequency_value = db.Column(db.Integer, default=10, nullable=False)  # Modulo-Wert oder Häufigkeit
    
    # Farb-Konfiguration für Frontend
    color_hex = db.Column(db.String(7), nullable=False)  # z.B. "#4CAF50"
    emission_hex = db.Column(db.String(7), nullable=True)  # z.B. "#2E7D32"
    
    # Icon/Symbol
    icon = db.Column(db.String(10), nullable=True)  # Emoji oder Unicode-Symbol
    
    # Zusätzliche Konfiguration (JSON)
    config_data = db.Column(db.Text, nullable=True)  # JSON für feldspezifische Einstellungen
    
    # Metadaten
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def config_dict(self):
        """Gibt config_data als Dictionary zurück"""
        if self.config_data:
            try:
                return json.loads(self.config_data)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    @config_dict.setter
    def config_dict(self, value):
        """Setzt config_data aus Dictionary"""
        if value is None:
            self.config_data = None
        else:
            self.config_data = json.dumps(value)

    @staticmethod
    def get_config_for_field(field_type):
        """Gibt die Konfiguration für einen bestimmten Feldtyp zurück"""
        return FieldConfiguration.query.filter_by(field_type=field_type).first()
    
    @staticmethod
    def get_all_enabled():
        """Gibt alle aktivierten Feld-Konfigurationen zurück"""
        return FieldConfiguration.query.filter_by(is_enabled=True).all()
    
    @staticmethod
    def initialize_default_configs():
        """Erstellt Standard-Feld-Konfigurationen falls sie nicht existieren"""
        default_configs = [
            {
                'field_type': 'start',
                'display_name': 'Startfeld',
                'description': 'Das Startfeld, wo alle Teams beginnen',
                'is_enabled': True,
                'frequency_type': 'fixed_positions',
                'frequency_value': 0,  # Nur Position 0
                'color_hex': '#00BFFF',
                'emission_hex': '#0066CC',
                'icon': '🏁',
                'config_data': json.dumps({})
            },
            {
                'field_type': 'goal',
                'display_name': 'Zielfeld',
                'description': 'Das Zielfeld - Hier gewinnt man!',
                'is_enabled': True,
                'frequency_type': 'fixed_positions',
                'frequency_value': 72,  # Nur Position 72
                'color_hex': '#FF6600',
                'emission_hex': '#CC4400',
                'icon': '🎯',
                'config_data': json.dumps({})
            },
            {
                'field_type': 'normal',
                'display_name': 'Normale Felder',
                'description': 'Standard-Spielfelder ohne besondere Effekte',
                'is_enabled': True,
                'frequency_type': 'default',
                'frequency_value': 0,  # Alle anderen Felder
                'color_hex': '#00FF00',
                'emission_hex': '#00CC00',
                'icon': '⬜',
                'config_data': json.dumps({})
            },
            {
                'field_type': 'catapult_forward',
                'display_name': 'Katapult Vorwärts',
                'description': 'Schleudert Teams 3-5 Felder nach vorne',
                'is_enabled': True,
                'frequency_type': 'modulo',
                'frequency_value': 15,  # Alle 15 Felder
                'color_hex': '#32CD32',
                'emission_hex': '#228B22',
                'icon': '🚀',
                'config_data': json.dumps({
                    'min_distance': 3,
                    'max_distance': 5
                })
            },
            {
                'field_type': 'catapult_backward',
                'display_name': 'Katapult Rückwärts',
                'description': 'Schleudert Teams 4-10 Felder nach hinten',
                'is_enabled': True,
                'frequency_type': 'modulo',
                'frequency_value': 13,  # Alle 13 Felder
                'color_hex': '#FF0000',
                'emission_hex': '#CC0000',
                'icon': '💥',
                'config_data': json.dumps({
                    'min_distance': 4,
                    'max_distance': 10
                })
            },
            {
                'field_type': 'player_swap',
                'display_name': 'Spieler-Tausch',
                'description': 'Tauscht Position mit zufälligem anderen Team',
                'is_enabled': True,
                'frequency_type': 'modulo',
                'frequency_value': 17,  # Alle 17 Felder
                'color_hex': '#0080FF',
                'emission_hex': '#0066CC',
                'icon': '🔄',
                'config_data': json.dumps({
                    'min_distance': 3
                })
            },
            {
                'field_type': 'barrier',
                'display_name': 'Sperren-Feld',
                'description': 'Blockiert Team bis bestimmte Zahl gewürfelt wird',
                'is_enabled': True,
                'frequency_type': 'modulo',
                'frequency_value': 19,  # Alle 19 Felder
                'color_hex': '#666666',
                'emission_hex': '#333333',
                'icon': '🚧',
                'config_data': json.dumps({
                    'target_numbers': [4, 5, 6]
                })
            },
            {
                'field_type': 'bonus',
                'display_name': 'Bonusfeld',
                'description': 'Gibt dem Team einen Vorteil',
                'is_enabled': True,
                'frequency_type': 'modulo',
                'frequency_value': 8,  # Alle 8 Felder
                'color_hex': '#FFD700',
                'emission_hex': '#FF8C00',
                'icon': '⭐',
                'config_data': json.dumps({
                    'bonus_type': 'extra_dice'
                })
            },
            {
                'field_type': 'minigame',
                'display_name': 'Minispiel',
                'description': 'Startet ein Minispiel oder eine Frage',
                'is_enabled': True,
                'frequency_type': 'modulo',
                'frequency_value': 12,  # Alle 12 Felder
                'color_hex': '#8A2BE2',
                'emission_hex': '#6A1B9A',
                'icon': '🎮',
                'config_data': json.dumps({})
            },
            {
                'field_type': 'chance',
                'display_name': 'Ereignisfeld',
                'description': 'Zufälliges Ereignis passiert',
                'is_enabled': True,
                'frequency_type': 'modulo',
                'frequency_value': 20,  # Alle 20 Felder
                'color_hex': '#ADFF2F',
                'emission_hex': '#9ACD32',
                'icon': '🎲',
                'config_data': json.dumps({
                    'events': ['bonus_move', 'lose_turn', 'extra_roll']
                })
            },
            {
                'field_type': 'trap',
                'display_name': 'Falle',
                'description': 'Schadet dem Team oder blockiert es',
                'is_enabled': True,
                'frequency_type': 'modulo',
                'frequency_value': 25,  # Alle 25 Felder
                'color_hex': '#FF4500',
                'emission_hex': '#B22222',
                'icon': '⚠️',
                'config_data': json.dumps({
                    'trap_effects': ['move_back', 'skip_turn', 'remove_bonus']
                })
            }
        ]
        
        for config in default_configs:
            existing = FieldConfiguration.query.filter_by(field_type=config['field_type']).first()
            if not existing:
                field_config = FieldConfiguration(
                    field_type=config['field_type'],
                    display_name=config['display_name'],
                    description=config['description'],
                    is_enabled=config['is_enabled'],
                    frequency_type=config['frequency_type'],
                    frequency_value=config['frequency_value'],
                    color_hex=config['color_hex'],
                    emission_hex=config['emission_hex'],
                    icon=config['icon'],
                    config_data=config['config_data']
                )
                db.session.add(field_config)
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    def __repr__(self):
        return f'<FieldConfiguration {self.field_type}: {self.display_name}>'

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
        
        # Automatisches Backup nach Aktivierung
        try:
            from app.admin.minigame_utils import save_round_to_filesystem
            save_round_to_filesystem(self)
        except Exception as backup_e:
            import logging
            logging.warning(f"Backup der aktivierten Runde '{self.name}' fehlgeschlagen: {backup_e}")

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
    current_player_count = db.Column(db.String(20), default='1', nullable=True)  # Spieleranzahl-Konfiguration
    selected_players = db.Column(db.Text, nullable=True)  # JSON mit ausgewählten Spielern pro Team
    
    # Für Einzelfragen
    current_question_id = db.Column(db.String(100), nullable=True)  # UUID aus JSON-Datei
    
    # Zusätzliche Felder für Minigame-Auswahl
    selected_folder_minigame_id = db.Column(db.String(100), nullable=True)  # ID aus JSON-Datei
    minigame_source = db.Column(db.String(50), default='manual')  # 'manual', 'folder_random', 'folder_selected', 'direct_question'

    # Tracking für bereits gespielte Inhalte
    played_content_ids = db.Column(db.Text, nullable=True, default='')  # Komma-separierte Liste von gespielten IDs
    player_rotation_data = db.Column(db.Text, nullable=True)  # JSON mit Spieleinsatz-Tracking pro Team

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

    def get_selected_players(self):
        """Gibt die ausgewählten Spieler als Dictionary zurück"""
        if not self.selected_players:
            return {}
        try:
            return json.loads(self.selected_players)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_selected_players(self, players_dict):
        """Setzt die ausgewählten Spieler aus Dictionary"""
        if players_dict is None:
            self.selected_players = None
        else:
            self.selected_players = json.dumps(players_dict)

    def select_random_players(self, teams, count_per_team):
        """Wählt faire rotierend Spieler aus jedem Team aus"""
        import random
        selected = {}
        
        for team in teams:
            if not team.members:
                # Fallback: Verwende Team-Name wenn keine Mitglieder definiert
                selected[str(team.id)] = [team.name]
                continue
                
            # Verwende die neue get_selectable_players() Methode für bessere Spieler-Verwaltung
            try:
                # Unterscheidung zwischen "ganzes Team" und regulärer Auswahl
                if count_per_team == "all":
                    # Bei "ganzes Team" alle Spieler verwenden (auch nicht-auslosbare)
                    all_members = [m.strip() for m in team.members.split(',') if m.strip()] if team.members else []
                    if not all_members:
                        selected[str(team.id)] = [team.name]
                        continue
                    selected[str(team.id)] = all_members
                    # Tracking für alle Spieler
                    self._update_player_rotation_tracking(str(team.id), all_members)
                else:
                    # Bei normaler Auswahl nur auslosbare Spieler verwenden
                    selectable_members = team.get_selectable_players()
                    if not selectable_members:
                        # Fallback wenn keine auslosbaren Spieler vorhanden
                        selected[str(team.id)] = [team.name]
                        continue
                    
                    # Faire Auswahl basierend auf Rotation aus auslosbaren Spielern
                    selected_count = min(int(count_per_team), len(selectable_members))
                    selected_members = self._select_fair_rotation(str(team.id), selectable_members, selected_count)
                    selected[str(team.id)] = selected_members
                    # Tracking aktualisieren
                    self._update_player_rotation_tracking(str(team.id), selected_members)
                
            except (ValueError, AttributeError):
                # Fallback bei Parsing-Fehlern
                selected[str(team.id)] = [team.name]
        
        self.set_selected_players(selected)
        return selected

    def get_player_rotation_data(self):
        """Gibt die Spieler-Rotations-Daten als Dictionary zurück"""
        if not self.player_rotation_data:
            return {}
        try:
            return json.loads(self.player_rotation_data)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_player_rotation_data(self, rotation_dict):
        """Setzt die Spieler-Rotations-Daten aus Dictionary"""
        if rotation_dict is None:
            self.player_rotation_data = None
        else:
            self.player_rotation_data = json.dumps(rotation_dict)

    def _select_fair_rotation(self, team_id, members, count_needed):
        """Wählt Spieler basierend auf fairer Rotation aus"""
        import random
        
        rotation_data = self.get_player_rotation_data()
        team_data = rotation_data.get(team_id, {})
        
        # Initialisiere Spieler-Zähler falls noch nicht vorhanden
        player_counts = {}
        for member in members:
            player_counts[member] = team_data.get(member, 0)
        
        # Sortiere Spieler nach Anzahl gespielter Spiele (aufsteigend)
        sorted_players = sorted(player_counts.items(), key=lambda x: x[1])
        
        # Bestimme minimale Anzahl gespielter Spiele
        min_games = sorted_players[0][1] if sorted_players else 0
        
        # Finde alle Spieler mit minimaler Anzahl Spiele
        available_players = [player for player, count in sorted_players if count == min_games]
        
        selected_players = []
        
        # Wähle aus Spielern mit wenigsten Spielen
        if len(available_players) >= count_needed:
            # Genug Spieler mit minimalen Spielen verfügbar
            selected_players = random.sample(available_players, count_needed)
        else:
            # Nicht genug Spieler mit minimalen Spielen - fülle mit nächst-besten auf
            selected_players.extend(available_players)
            remaining_needed = count_needed - len(selected_players)
            
            # Finde Spieler mit zweit-wenigsten Spielen
            remaining_players = [player for player, count in sorted_players 
                               if count > min_games and player not in selected_players]
            
            if remaining_players and remaining_needed > 0:
                # Sortiere nach Anzahl Spiele und fülle auf
                remaining_players_sorted = sorted(remaining_players, 
                                                key=lambda p: player_counts[p])
                
                additional_players = remaining_players_sorted[:remaining_needed]
                selected_players.extend(additional_players)
        
        return selected_players

    def _update_player_rotation_tracking(self, team_id, selected_players):
        """Aktualisiert das Tracking für die ausgewählten Spieler"""
        rotation_data = self.get_player_rotation_data()
        
        if team_id not in rotation_data:
            rotation_data[team_id] = {}
        
        # Erhöhe Zähler für ausgewählte Spieler
        for player in selected_players:
            if player not in rotation_data[team_id]:
                rotation_data[team_id][player] = 0
            rotation_data[team_id][player] += 1
        
        self.set_player_rotation_data(rotation_data)

    def reset_player_rotation(self):
        """Setzt die Spieler-Rotation zurück"""
        self.player_rotation_data = None

    def get_player_statistics(self):
        """Gibt Statistiken über Spieleinsätze zurück"""
        rotation_data = self.get_player_rotation_data()
        stats = {}
        
        for team_id, players in rotation_data.items():
            team_stats = {
                'total_games': sum(players.values()),
                'players': dict(players),
                'most_played': max(players.values()) if players else 0,
                'least_played': min(players.values()) if players else 0
            }
            stats[team_id] = team_stats
        
        return stats

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

    @property
    def data(self):
        """Gibt data_json als Dictionary zurück"""
        if self.data_json:
            try:
                # Versuche erst JSON zu parsen
                return json.loads(self.data_json)
            except json.JSONDecodeError:
                # Falls fehlschlägt, versuche eval für alte Daten
                try:
                    return eval(self.data_json)
                except:
                    return {}
        return {}
    
    @data.setter
    def data(self, value):
        """Setzt data_json aus Dictionary"""
        if value is None:
            self.data_json = None
        else:
            self.data_json = json.dumps(value)

    def __repr__(self):
        return f'<GameEvent {self.id} Type: {self.event_type} Session: {self.game_session_id}>'

class WelcomeSession(db.Model):
    """Verwaltet Willkommensmodus und Spielerregistrierung"""
    id = db.Column(db.Integer, primary_key=True)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    
    # Team-Konfiguration
    team_count = db.Column(db.Integer, nullable=True)
    teams_created = db.Column(db.Boolean, default=False, nullable=False)
    
    # Beziehungen
    player_registrations = db.relationship('PlayerRegistration', backref='welcome_session', lazy='dynamic', cascade="all, delete-orphan")
    
    @classmethod
    def get_active_session(cls):
        """Gibt die aktuelle aktive Welcome-Session zurück"""
        return cls.query.filter_by(is_active=True).first()
    
    def activate(self):
        """Aktiviert diese Session und deaktiviert alle anderen"""
        WelcomeSession.query.update({'is_active': False})
        self.is_active = True
        db.session.commit()
    
    def deactivate(self):
        """Deaktiviert diese Session"""
        self.is_active = False
        self.end_time = datetime.utcnow()
        db.session.commit()
    
    def get_registered_players(self):
        """Gibt alle registrierten Spieler zurück"""
        return self.player_registrations.order_by(PlayerRegistration.registration_time).all()
    
    def __repr__(self):
        return f'<WelcomeSession {self.id} Active: {self.is_active}>'

class PlayerRegistration(db.Model):
    """Einzelne Spielerregistrierung für Welcome-Session"""
    id = db.Column(db.Integer, primary_key=True)
    welcome_session_id = db.Column(db.Integer, db.ForeignKey('welcome_session.id'), nullable=False)
    player_name = db.Column(db.String(100), nullable=False)
    registration_time = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Team-Zuordnung (wird nach Teamaufteilung gesetzt)
    assigned_team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    assigned_team = db.relationship('Team', backref='player_registrations')
    
    def __repr__(self):
        return f'<PlayerRegistration {self.player_name} Session: {self.welcome_session_id}>'