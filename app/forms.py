# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, BooleanField, SelectField, HiddenField, TextAreaField, RadioField
from wtforms.validators import DataRequired, Length, EqualTo, NumberRange, Optional, ValidationError
from app.models import Character, MinigameFolder, GameRound # Importiere die Models

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
        # Befülle die Auswahlmöglichkeiten für Charaktere aus der Datenbank
        # Stellt sicher, dass dies innerhalb eines App-Kontexts mit Zugriff auf die DB geschieht
        from app.models import Character 
        self.character_id.choices = [(c.id, c.name) for c in Character.query.filter_by(is_selected=False).all()]

class EditTeamForm(FlaskForm):
    team_name = StringField('Teamname', validators=[DataRequired(), Length(min=2, max=50)])
    password = PasswordField('Neues Passwort (leer lassen, um nicht zu ändern)', validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField('Neues Passwort bestätigen', validators=[EqualTo('password', message='Passwörter müssen übereinstimmen.')])
    # current_password = PasswordField('Aktuelles Passwort (erforderlich für Änderungen)') # Vorerst auskommentiert, falls nicht sofort benötigt
    character_id = SelectField('Charakter ändern', coerce=int, validators=[Optional()])
    submit = SubmitField('Änderungen speichern')

    def __init__(self, original_team_name, current_character_id, *args, **kwargs):
        super(EditTeamForm, self).__init__(*args, **kwargs)
        self.original_team_name = original_team_name
        # Charakterauswahl befüllen
        available_characters = Character.query.filter(
            (Character.is_selected == False) | (Character.id == current_character_id)
        ).all()
        self.character_id.choices = [(0, '-- Keinen Charakter --')] + [(c.id, c.name) for c in available_characters]
        # Setze den aktuellen Charakter als vorausgewählt, falls vorhanden, sonst 0
        self.character_id.data = current_character_id if current_character_id else 0

class MinigameForm(FlaskForm):
    name = StringField('Name des Minispiels', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Beschreibung', validators=[Optional(), Length(max=300)])
    type = SelectField('Typ', choices=[('game', 'Spiel'), ('video', 'Video')], validators=[DataRequired()])
    submit = SubmitField('Minispiel erstellen/aktualisieren')

class SetNextMinigameForm(FlaskForm):
    # Erweiterte Minigame-Auswahl
    minigame_source = RadioField('Minigame-Quelle', 
                                choices=[
                                    ('manual', 'Manuell eingeben'),
                                    ('database', 'Aus Datenbank-Bibliothek auswählen'),
                                    ('folder_random', 'Zufällig aus aktuellem Ordner'),
                                    ('folder_selected', 'Aus aktuellem Ordner auswählen')
                                ], 
                                default='manual',
                                validators=[DataRequired()])
    
    # Manuelle Eingabe (wie bisher)
    minigame_name = StringField('Manueller Name Minispiel', validators=[Optional(), Length(max=100)])
    minigame_description = TextAreaField('Manuelle Beschreibung', validators=[Optional(), Length(max=300)])
    
    # Auswahl aus Datenbank-Bibliothek (wie bisher)
    selected_minigame_id = SelectField('Aus Datenbank-Bibliothek auswählen', coerce=int, validators=[Optional()])
    
    # Auswahl aus Ordner
    selected_folder_minigame_id = SelectField('Aus Ordner auswählen', validators=[Optional()])
    
    submit = SubmitField('Minispiel festlegen')

    def __init__(self, *args, **kwargs):
        super(SetNextMinigameForm, self).__init__(*args, **kwargs)
        # Befülle DB-Minigames
        from app.models import Minigame
        minigames_db = Minigame.query.all()
        self.selected_minigame_id.choices = [(0, '-- Manuelle Eingabe verwenden --')] + \
                                             [(mg.id, mg.name) for mg in minigames_db]
        
        # Befülle Ordner-Minigames (wird in der Route dynamisch gesetzt)
        self.selected_folder_minigame_id.choices = [('', '-- Wähle aus Ordner --')]

class EnterVideoScoresForm(FlaskForm):
    # Dieses Formular wird dynamisch in der Route basierend auf den Teams erstellt.
    submit = SubmitField('Punkte eintragen')

class AdminConfirmPasswordForm(FlaskForm):
    password = PasswordField('Admin-Passwort zur Bestätigung', validators=[DataRequired()])
    submit = SubmitField('Bestätigen und Zurücksetzen')

# NEUE FORMS FÜR MINIGAME-ORDNER & SPIELRUNDEN

class CreateMinigameFolderForm(FlaskForm):
    name = StringField('Ordner-Name', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Beschreibung', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Ordner erstellen')

    def validate_name(self, name):
        # Prüfe auf ungültige Zeichen für Ordnernamen
        import re
        if not re.match(r'^[a-zA-Z0-9_\-\s]+$', name.data):
            raise ValidationError('Ordnername darf nur Buchstaben, Zahlen, Leerzeichen, Bindestriche und Unterstriche enthalten.')
        
        # Prüfe auf existierenden Ordner
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
        # Prüfe auf ungültige Zeichen
        import re
        if not re.match(r'^[a-zA-Z0-9_\-\s]+$', name.data):
            raise ValidationError('Ordnername darf nur Buchstaben, Zahlen, Leerzeichen, Bindestriche und Unterstriche enthalten.')
        
        # Prüfe auf existierenden Ordner (außer dem aktuellen)
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
        # Befülle die Ordner-Auswahl
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
        # Befülle die Ordner-Auswahl
        folders = MinigameFolder.query.order_by(MinigameFolder.name).all()
        self.minigame_folder_id.choices = [(f.id, f"{f.name} ({f.get_minigames_count()} Spiele)") for f in folders]

    def validate_name(self, name):
        if name.data != self.original_round_name:
            existing_round = GameRound.query.filter_by(name=name.data).first()
            if existing_round:
                raise ValidationError('Eine Runde mit diesem Namen existiert bereits.')

class FolderMinigameForm(FlaskForm):
    """Form für Minispiele in Ordnern (JSON-basiert)"""
    name = StringField('Name des Minispiels', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Beschreibung', validators=[Optional(), Length(max=300)])
    type = SelectField('Typ', choices=[('game', 'Spiel'), ('video', 'Video'), ('challenge', 'Challenge')], validators=[DataRequired()])
    submit = SubmitField('Minispiel speichern')

class EditFolderMinigameForm(FlaskForm):
    """Form für das Bearbeiten von Minispielen in Ordnern"""
    name = StringField('Name des Minispiels', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Beschreibung', validators=[Optional(), Length(max=300)])
    type = SelectField('Typ', choices=[('game', 'Spiel'), ('video', 'Video'), ('challenge', 'Challenge')], validators=[DataRequired()])
    submit = SubmitField('Änderungen speichern')

class DeleteConfirmationForm(FlaskForm):
    """Allgemeines Bestätigungsformular für Löschvorgänge"""
    confirm = BooleanField('Ja, ich möchte dies wirklich löschen', validators=[DataRequired()])
    submit = SubmitField('Endgültig löschen')