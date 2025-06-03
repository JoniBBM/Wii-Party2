# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, BooleanField, SelectField, HiddenField, TextAreaField
from wtforms.validators import DataRequired, Length, EqualTo, NumberRange, Optional
from app.models import Character # Importiere das Character-Modell

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
    minigame_name = StringField('Manueller Name Minispiel', validators=[Optional(), Length(max=100)])
    minigame_description = TextAreaField('Manuelle Beschreibung', validators=[Optional(), Length(max=300)])
    selected_minigame_id = SelectField('Aus Bibliothek auswählen', coerce=int, validators=[Optional()])
    submit = SubmitField('Minispiel festlegen')

class EnterVideoScoresForm(FlaskForm):
    # Dieses Formular wird dynamisch in der Route basierend auf den Teams erstellt.
    submit = SubmitField('Punkte eintragen')

class AdminConfirmPasswordForm(FlaskForm):
    password = PasswordField('Admin-Passwort zur Bestätigung', validators=[DataRequired()])
    submit = SubmitField('Bestätigen und Zurücksetzen')
