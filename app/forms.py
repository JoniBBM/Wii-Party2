from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, SelectField, IntegerField
from wtforms.validators import DataRequired, Length, Optional

class AdminLoginForm(FlaskForm):
    username = StringField('Benutzername', validators=[DataRequired()])
    password = PasswordField('Passwort', validators=[DataRequired()])
    submit = SubmitField('Login')

class TeamForm(FlaskForm): # Für Admin zum Erstellen/Bearbeiten von Teams
    name = StringField('Team Name', validators=[DataRequired(), Length(min=2, max=100)])
    members = StringField('Mitglieder (Komma-getrennt)', validators=[Optional(), Length(max=255)])
    password = PasswordField('Passwort (für Team-Login, leer lassen, um nicht zu ändern)', validators=[Optional(), Length(min=4, max=100)])
    character_id = SelectField('Charakter', coerce=int, validators=[Optional()])
    submit = SubmitField('Team erstellen/aktualisieren')

class MinigameForm(FlaskForm): # Für die DB-Minispiel-Bibliothek
    name = StringField('Minispiel Name', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Beschreibung', validators=[Optional(), Length(max=500)])
    submit = SubmitField('DB-Minispiel erstellen/aktualisieren')

class SetNextMinigameForm(FlaskForm): # Für Admin zur Ad-hoc-Minispiel-Eingabe
    minigame_name = StringField('Name des nächsten Minispiels', validators=[DataRequired(), Length(min=3, max=200)])
    minigame_description = TextAreaField('Beschreibung des Minispiels', validators=[DataRequired(), Length(max=1000)])
    selected_minigame_id = SelectField('Oder wähle ein Minispiel aus der Bibliothek:', coerce=int, validators=[Optional()])
    submit = SubmitField('Minispiel festlegen und ankündigen')

# NEUES Formular für den Team-Login
class TeamLoginForm(FlaskForm):
    team_name = StringField('Teamname', validators=[DataRequired(), Length(min=2, max=100)])
    password = PasswordField('Passwort', validators=[DataRequired()])
    submit = SubmitField('Einloggen')
