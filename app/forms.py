# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, BooleanField, SelectField, HiddenField, TextAreaField, RadioField, FloatField, SelectMultipleField
from wtforms.validators import DataRequired, Length, EqualTo, NumberRange, Optional, ValidationError
from app.models import Character, MinigameFolder, GameRound, FieldType, Team

class AdminLoginForm(FlaskForm):
    username = StringField('Benutzername', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Passwort', validators=[DataRequired()])
    submit = SubmitField('Anmelden')

class TeamLoginForm(FlaskForm):
    team_name = StringField('Teamname', validators=[DataRequired(), Length(min=2, max=50)])
    password = PasswordField('Passwort', validators=[DataRequired()])
    submit = SubmitField('Anmelden')

class CreateTeamForm(FlaskForm):
    team_name = StringField('Teamname', validators=[DataRequired(), Length(min=2, max=50)])
    password = PasswordField('Passwort', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Passwort bestätigen', validators=[DataRequired(), EqualTo('password')])
    character_id = SelectField('Charakter auswählen', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Team erstellen')

    def __init__(self, *args, **kwargs):
        super(CreateTeamForm, self).__init__(*args, **kwargs)
        from app.models import Character 
        self.character_id.choices = [(c.id, c.name) for c in Character.query.filter_by(is_selected=False).all()]

class EditTeamForm(FlaskForm):
    team_name = StringField('Teamname', validators=[DataRequired(), Length(min=2, max=50)])
    password = PasswordField('Neues Passwort (leer lassen, um nicht zu ändern)', validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField('Neues Passwort bestätigen', validators=[EqualTo('password', message='Passwörter müssen übereinstimmen.')])
    character_id = SelectField('Charakter ändern', coerce=int, validators=[Optional()])
    submit = SubmitField('Änderungen speichern')

    def __init__(self, original_team_name, current_character_id, *args, **kwargs):
        super(EditTeamForm, self).__init__(*args, **kwargs)
        self.original_team_name = original_team_name
        available_characters = Character.query.filter(
            (Character.is_selected == False) | (Character.id == current_character_id)
        ).all()
        self.character_id.choices = [(0, '-- Keinen Charakter --')] + [(c.id, c.name) for c in available_characters]
        self.character_id.data = current_character_id if current_character_id else 0

class SetNextMinigameForm(FlaskForm):
    # Erweiterte Minigame-Auswahl mit direkter Fragen-Erstellung
    minigame_source = RadioField('Inhalts-Quelle', 
                                choices=[
                                    ('manual', 'Manuell eingeben'),
                                    ('direct_question', 'Direkte Frage erstellen'),
                                    ('folder_random', 'Zufällig aus aktuellem Ordner'),
                                    ('folder_selected', 'Aus aktuellem Ordner auswählen')
                                ], 
                                default='manual',
                                validators=[DataRequired()])
    
    # Manuelle Eingabe
    minigame_name = StringField('Name', validators=[Optional(), Length(max=100)])
    minigame_description = TextAreaField('Beschreibung', validators=[Optional(), Length(max=300)])
    
    # Direkte Fragen-Erstellung
    question_text = TextAreaField('Frage', validators=[Optional(), Length(max=500)])
    question_type = SelectField('Fragetyp', choices=[
        ('multiple_choice', 'Multiple Choice'),
        ('text_input', 'Freitext-Eingabe')
    ], validators=[Optional()])
    
    # Multiple Choice Optionen
    option_1 = StringField('Option 1', validators=[Optional(), Length(max=200)])
    option_2 = StringField('Option 2', validators=[Optional(), Length(max=200)])
    option_3 = StringField('Option 3', validators=[Optional(), Length(max=200)])
    option_4 = StringField('Option 4', validators=[Optional(), Length(max=200)])
    correct_option = SelectField('Korrekte Option', choices=[
        (0, 'Option 1'), (1, 'Option 2'), (2, 'Option 3'), (3, 'Option 4')
    ], coerce=int, validators=[Optional()])
    
    # Freitext-Antwort
    correct_text = StringField('Korrekte Antwort', validators=[Optional(), Length(max=200)])
    
    # Auswahl aus Ordner
    selected_folder_minigame_id = SelectField('Aus Ordner auswählen', validators=[Optional()])
    
    submit = SubmitField('Inhalt festlegen')

    def __init__(self, *args, **kwargs):
        super(SetNextMinigameForm, self).__init__(*args, **kwargs)
        self.selected_folder_minigame_id.choices = [('', '-- Wähle aus Ordner --')]

class AdminConfirmPasswordForm(FlaskForm):
    password = PasswordField('Admin-Passwort zur Bestätigung', validators=[DataRequired()])
    submit = SubmitField('Bestätigen und Zurücksetzen')

# FORMS FÜR MINIGAME-ORDNER & SPIELRUNDEN

class CreateMinigameFolderForm(FlaskForm):
    name = StringField('Ordner-Name', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Beschreibung', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Ordner erstellen')

    def validate_name(self, name):
        import re
        if not re.match(r'^[a-zA-Z0-9_\-\s]+$', name.data):
            raise ValidationError('Ordnername darf nur Buchstaben, Zahlen, Leerzeichen, Bindestriche und Unterstriche enthalten.')
        
        existing_folder = MinigameFolder.query.filter_by(name=name.data).first()
        if existing_folder:
            raise ValidationError('Ein Ordner mit diesem Namen existiert bereits.')

class EditMinigameFolderForm(FlaskForm):
    name = StringField('Ordner-Name', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Beschreibung', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Änderungen speichern')

    def __init__(self, original_folder_name, *args, **kwargs):
        super(EditMinigameFolderForm, self).__init__(*args, **kwargs)
        self.original_folder_name = original_folder_name

    def validate_name(self, name):
        import re
        if not re.match(r'^[a-zA-Z0-9_\-\s]+$', name.data):
            raise ValidationError('Ordnername darf nur Buchstaben, Zahlen, Leerzeichen, Bindestriche und Unterstriche enthalten.')
        
        if name.data != self.original_folder_name:
            existing_folder = MinigameFolder.query.filter_by(name=name.data).first()
            if existing_folder:
                raise ValidationError('Ein Ordner mit diesem Namen existiert bereits.')

class CreateGameRoundForm(FlaskForm):
    name = StringField('Runden-Name', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Beschreibung', validators=[Optional(), Length(max=500)])
    minigame_folder_id = SelectField('Minigame-Ordner', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Runde erstellen')

    def __init__(self, *args, **kwargs):
        super(CreateGameRoundForm, self).__init__(*args, **kwargs)
        folders = MinigameFolder.query.order_by(MinigameFolder.name).all()
        self.minigame_folder_id.choices = [(f.id, f"{f.name} ({f.get_minigames_count()} Spiele)") for f in folders]

    def validate_name(self, name):
        existing_round = GameRound.query.filter_by(name=name.data).first()
        if existing_round:
            raise ValidationError('Eine Runde mit diesem Namen existiert bereits.')

class EditGameRoundForm(FlaskForm):
    name = StringField('Runden-Name', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Beschreibung', validators=[Optional(), Length(max=500)])
    minigame_folder_id = SelectField('Minigame-Ordner', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Änderungen speichern')

    def __init__(self, original_round_name, *args, **kwargs):
        super(EditGameRoundForm, self).__init__(*args, **kwargs)
        self.original_round_name = original_round_name
        folders = MinigameFolder.query.order_by(MinigameFolder.name).all()
        self.minigame_folder_id.choices = [(f.id, f"{f.name} ({f.get_minigames_count()} Spiele)") for f in folders]

    def validate_name(self, name):
        if name.data != self.original_round_name:
            existing_round = GameRound.query.filter_by(name=name.data).first()
            if existing_round:
                raise ValidationError('Eine Runde mit diesem Namen existiert bereits.')

class FolderMinigameForm(FlaskForm):
    """Form für Minispiele in Ordnern (JSON-basiert)"""
    name = StringField('Name des Inhalts', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Beschreibung', validators=[Optional(), Length(max=300)])
    type = SelectField('Typ', choices=[
        ('game', 'Spiel'), 
        ('video', 'Video'), 
        ('challenge', 'Challenge'),
        ('question', 'Einzelfrage')
    ], validators=[DataRequired()])
    submit = SubmitField('Inhalt speichern')

class EditFolderMinigameForm(FlaskForm):
    """Form für das Bearbeiten von Minispielen in Ordnern"""
    name = StringField('Name des Inhalts', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Beschreibung', validators=[Optional(), Length(max=300)])
    type = SelectField('Typ', choices=[
        ('game', 'Spiel'), 
        ('video', 'Video'), 
        ('challenge', 'Challenge'),
        ('question', 'Einzelfrage')
    ], validators=[DataRequired()])
    submit = SubmitField('Änderungen speichern')

# FRAGEN-FORMS (ohne Punkte)

class CreateQuestionForm(FlaskForm):
    """Form für das Erstellen einer Einzelfrage"""
    name = StringField('Frage-Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Beschreibung', validators=[Optional(), Length(max=500)])
    question_text = TextAreaField('Frage', validators=[DataRequired(), Length(max=500)])
    
    question_type = SelectField('Fragetyp', choices=[
        ('multiple_choice', 'Multiple Choice'),
        ('text_input', 'Freitext-Eingabe')
    ], validators=[DataRequired()])
    
    # Multiple Choice Optionen
    option_1 = StringField('Option 1', validators=[Optional(), Length(max=200)])
    option_2 = StringField('Option 2', validators=[Optional(), Length(max=200)])
    option_3 = StringField('Option 3', validators=[Optional(), Length(max=200)])
    option_4 = StringField('Option 4', validators=[Optional(), Length(max=200)])
    
    correct_option = SelectField('Korrekte Option', choices=[
        (0, 'Option 1'), (1, 'Option 2'), (2, 'Option 3'), (3, 'Option 4')
    ], coerce=int, validators=[Optional()])
    
    correct_text = StringField('Korrekte Antwort (Freitext)', validators=[Optional(), Length(max=200)])
    
    submit = SubmitField('Frage erstellen')

class EditQuestionForm(FlaskForm):
    """Form für das Bearbeiten einer Einzelfrage"""
    name = StringField('Frage-Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Beschreibung', validators=[Optional(), Length(max=500)])
    question_text = TextAreaField('Frage', validators=[DataRequired(), Length(max=500)])
    
    question_type = SelectField('Fragetyp', choices=[
        ('multiple_choice', 'Multiple Choice'),
        ('text_input', 'Freitext-Eingabe')
    ], validators=[DataRequired()])
    
    # Multiple Choice Optionen
    option_1 = StringField('Option 1', validators=[Optional(), Length(max=200)])
    option_2 = StringField('Option 2', validators=[Optional(), Length(max=200)])
    option_3 = StringField('Option 3', validators=[Optional(), Length(max=200)])
    option_4 = StringField('Option 4', validators=[Optional(), Length(max=200)])
    
    correct_option = SelectField('Korrekte Option', choices=[
        (0, 'Option 1'), (1, 'Option 2'), (2, 'Option 3'), (3, 'Option 4')
    ], coerce=int, validators=[Optional()])
    
    correct_text = StringField('Korrekte Antwort (Freitext)', validators=[Optional(), Length(max=200)])
    
    submit = SubmitField('Frage aktualisieren')

class QuestionAnswerForm(FlaskForm):
    """Form für Team-Antworten auf Einzelfragen - ohne Punkte"""
    question_id = HiddenField()
    
    # Für Multiple Choice
    selected_option = RadioField('Antwort auswählen', coerce=int, validators=[Optional()])
    
    # Für Freitext
    answer_text = TextAreaField('Antwort eingeben', validators=[Optional(), Length(max=500)])
    
    submit = SubmitField('Antwort abschicken')

class DeleteConfirmationForm(FlaskForm):
    """Allgemeines Bestätigungsformular für Löschvorgänge"""
    confirm = BooleanField('Ja, ich möchte dies wirklich löschen', validators=[DataRequired()])
    submit = SubmitField('Endgültig löschen')

# NEUE FORMS FÜR FELDAKTIONEN

class CreateFieldTypeForm(FlaskForm):
    """Form für das Erstellen eines neuen Feldtyps"""
    name = StringField('Interner Name', validators=[DataRequired(), Length(min=2, max=50)])
    display_name = StringField('Anzeigename', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Beschreibung', validators=[Optional(), Length(max=500)])
    color = StringField('Farbe (Hex)', validators=[DataRequired(), Length(min=7, max=7)], default='#FF0000')
    icon = StringField('Icon (Unicode/CSS)', validators=[Optional(), Length(max=20)], default='⭐')
    probability = FloatField('Wahrscheinlichkeit', validators=[NumberRange(min=0.0, max=1.0)], default=1.0)
    
    # Basis-Konfiguration
    action_type = SelectField('Hauptaktion', choices=[
        ('move_backward', 'Rückwärts bewegen'),
        ('move_forward', 'Vorwärts bewegen'),
        ('teleport', 'Teleportation'),
        ('swap_positions', 'Positionen tauschen'),
        ('extra_dice', 'Extra-Würfel'),
        ('bonus_move', 'Bonus-Bewegung'),
        ('block_player', 'Spieler blockieren'),
        ('shield', 'Schutzschild'),
        ('volcano_trigger', 'Vulkan auslösen'),
        ('lucky_field', 'Glücksfeld'),
        ('choice_field', 'Wahlfeld'),
        ('minigame_field', 'Mini-Minispiel'),
        ('mystery_box', 'Mysterium-Box'),
        ('time_warp', 'Zeitverzerrung')
    ], validators=[DataRequired()])
    
    submit = SubmitField('Feldtyp erstellen')

    def validate_name(self, name):
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', name.data):
            raise ValidationError('Name darf nur Buchstaben, Zahlen und Unterstriche enthalten.')
        
        existing_type = FieldType.query.filter_by(name=name.data).first()
        if existing_type:
            raise ValidationError('Ein Feldtyp mit diesem Namen existiert bereits.')

    def validate_color(self, color):
        import re
        if not re.match(r'^#[0-9A-Fa-f]{6}$', color.data):
            raise ValidationError('Farbe muss im Format #RRGGBB angegeben werden (z.B. #FF0000).')

class EditFieldTypeForm(FlaskForm):
    """Form für das Bearbeiten eines Feldtyps"""
    name = StringField('Interner Name', validators=[DataRequired(), Length(min=2, max=50)])
    display_name = StringField('Anzeigename', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Beschreibung', validators=[Optional(), Length(max=500)])
    color = StringField('Farbe (Hex)', validators=[DataRequired(), Length(min=7, max=7)])
    icon = StringField('Icon (Unicode/CSS)', validators=[Optional(), Length(max=20)])
    probability = FloatField('Wahrscheinlichkeit', validators=[NumberRange(min=0.0, max=1.0)])
    is_active = BooleanField('Aktiv')
    
    action_type = SelectField('Hauptaktion', choices=[
        ('move_backward', 'Rückwärts bewegen'),
        ('move_forward', 'Vorwärts bewegen'),
        ('teleport', 'Teleportation'),
        ('swap_positions', 'Positionen tauschen'),
        ('extra_dice', 'Extra-Würfel'),
        ('bonus_move', 'Bonus-Bewegung'),
        ('block_player', 'Spieler blockieren'),
        ('shield', 'Schutzschild'),
        ('volcano_trigger', 'Vulkan auslösen'),
        ('lucky_field', 'Glücksfeld'),
        ('choice_field', 'Wahlfeld'),
        ('minigame_field', 'Mini-Minispiel'),
        ('mystery_box', 'Mysterium-Box'),
        ('time_warp', 'Zeitverzerrung')
    ], validators=[DataRequired()])
    
    submit = SubmitField('Änderungen speichern')

    def __init__(self, original_name, *args, **kwargs):
        super(EditFieldTypeForm, self).__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, name):
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', name.data):
            raise ValidationError('Name darf nur Buchstaben, Zahlen und Unterstriche enthalten.')
        
        if name.data != self.original_name:
            existing_type = FieldType.query.filter_by(name=name.data).first()
            if existing_type:
                raise ValidationError('Ein Feldtyp mit diesem Namen existiert bereits.')

    def validate_color(self, color):
        import re
        if not re.match(r'^#[0-9A-Fa-f]{6}$', color.data):
            raise ValidationError('Farbe muss im Format #RRGGBB angegeben werden (z.B. #FF0000).')

class BoardFieldConfigForm(FlaskForm):
    """Form für die Konfiguration von Spielbrett-Feldern"""
    position = IntegerField('Feld-Position', validators=[DataRequired(), NumberRange(min=0, max=72)])
    field_type_id = SelectField('Feldtyp', coerce=int, validators=[Optional()])
    is_active = BooleanField('Aktiv', default=True)
    
    # Erweiterte Konfiguration (JSON)
    custom_config = TextAreaField('Benutzerdefinierte Konfiguration (JSON)', validators=[Optional()])
    
    submit = SubmitField('Feld konfigurieren')

    def __init__(self, *args, **kwargs):
        super(BoardFieldConfigForm, self).__init__(*args, **kwargs)
        field_types = FieldType.query.filter_by(is_active=True).order_by(FieldType.display_name).all()
        self.field_type_id.choices = [(0, '-- Normal (kein spezieller Typ) --')] + [(ft.id, f"{ft.display_name} ({ft.name})") for ft in field_types]

    def validate_custom_config(self, custom_config):
        if custom_config.data and custom_config.data.strip():
            try:
                import json
                json.loads(custom_config.data)
            except json.JSONDecodeError:
                raise ValidationError('Benutzerdefinierte Konfiguration muss gültiges JSON sein.')

class VolcanoControlForm(FlaskForm):
    """Form für die Vulkan-Steuerung"""
    action = SelectField('Vulkan-Aktion', choices=[
        ('trigger', 'Vulkan-Countdown starten'),
        ('eruption', 'Sofortiger Ausbruch'),
        ('calm', 'Vulkan beruhigen'),
        ('reset', 'Vulkan zurücksetzen')
    ], validators=[DataRequired()])
    
    countdown = IntegerField('Countdown (nur bei Trigger)', validators=[Optional(), NumberRange(min=1, max=10)], default=5)
    eruption_type = SelectField('Ausbruchstyp', choices=[
        ('scatter', 'Alle Teams verstreuen'),
        ('reset', 'Alle Teams zum Start'),
        ('selective', 'Positions-abhängige Effekte')
    ], default='scatter')
    
    submit = SubmitField('Vulkan-Aktion ausführen')

class FieldActionConfigForm(FlaskForm):
    """Form für die Konfiguration spezifischer Feldaktionen"""
    action_type = SelectField('Aktionstyp', validators=[DataRequired()])
    
    # Allgemeine Parameter
    min_value = IntegerField('Minimum-Wert', validators=[Optional()])
    max_value = IntegerField('Maximum-Wert', validators=[Optional()])
    fixed_value = IntegerField('Fester Wert', validators=[Optional()])
    probability = FloatField('Wahrscheinlichkeit', validators=[Optional(), NumberRange(min=0.0, max=1.0)])
    
    # Spezifische Parameter
    duration = IntegerField('Dauer (Züge)', validators=[Optional(), NumberRange(min=1, max=10)])
    target_type = SelectField('Ziel', choices=[
        ('self', 'Nur eigenes Team'),
        ('choice', 'Team auswählen'),
        ('random', 'Zufälliges Team'),
        ('all', 'Alle Teams'),
        ('others', 'Alle anderen Teams')
    ], default='self')
    
    effect_strength = SelectField('Stärke', choices=[
        ('weak', 'Schwach'),
        ('normal', 'Normal'),
        ('strong', 'Stark')
    ], default='normal')
    
    submit = SubmitField('Konfiguration speichern')

    def __init__(self, *args, **kwargs):
        super(FieldActionConfigForm, self).__init__(*args, **kwargs)
        # Aktionstypen aus dem Feldaktions-System laden
        from app.field_actions import get_available_actions, get_action_info
        
        action_choices = []
        for action_type in get_available_actions():
            info = get_action_info(action_type)
            action_choices.append((action_type, f"{info.get('name', action_type)} ({info.get('category', 'unknown')})"))
        
        self.action_type.choices = action_choices

class QuickFieldSetupForm(FlaskForm):
    """Form für schnelle Feld-Konfiguration"""
    setup_type = SelectField('Setup-Typ', choices=[
        ('random', 'Zufällige Verteilung'),
        ('balanced', 'Ausgewogene Verteilung'),
        ('chaotic', 'Chaotische Verteilung'),
        ('volcano_heavy', 'Vulkan-lastig'),
        ('safe', 'Sicher (wenig Fallen)'),
        ('clear_all', 'Alle Spezialfelder entfernen')
    ], validators=[DataRequired()])
    
    special_field_density = SelectField('Dichte der Spezialfelder', choices=[
        ('low', 'Niedrig (10%)'),
        ('medium', 'Mittel (20%)'),
        ('high', 'Hoch (30%)'),
        ('extreme', 'Extrem (40%)')
    ], default='medium')
    
    include_volcano = BooleanField('Vulkan-Felder einschließen', default=True)
    include_teleport = BooleanField('Teleport-Felder einschließen', default=True)
    include_bonus = BooleanField('Bonus-Felder einschließen', default=True)
    include_traps = BooleanField('Fallen einschließen', default=True)
    
    submit = SubmitField('Spielbrett konfigurieren')

class TeamFieldActionForm(FlaskForm):
    """Form für Team-Interaktionen mit Feldaktionen"""
    action_id = HiddenField()
    choice_value = StringField('Auswahl')
    target_team_id = SelectField('Ziel-Team', coerce=int, validators=[Optional()])
    
    submit = SubmitField('Aktion ausführen')

    def __init__(self, *args, **kwargs):
        super(TeamFieldActionForm, self).__init__(*args, **kwargs)
        teams = Team.query.order_by(Team.name).all()
        self.target_team_id.choices = [(0, '-- Kein Team --')] + [(t.id, t.name) for t in teams]