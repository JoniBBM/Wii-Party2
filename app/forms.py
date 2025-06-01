from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, IntegerField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, NumberRange # Email und EqualTo sind Beispiele, falls benötigt

class AdminLoginForm(FlaskForm):
    username = StringField('Benutzername', validators=[DataRequired()])
    password = PasswordField('Passwort', validators=[DataRequired()])
    submit = SubmitField('Login')

class TeamForm(FlaskForm):
    name = StringField('Team Name', validators=[DataRequired(), Length(min=2, max=100)])
    # Beispiel für Charakterauswahl, dies muss an deine Character-Logik angepasst werden
    # Du könntest die Choices dynamisch im Route-Handler setzen.
    character = StringField('Charakter Name', validators=[DataRequired(), Length(min=2, max=100)])
    # Alternativ, wenn du eine feste Liste hast:
    # character = SelectField('Charakter', choices=[('Mario', 'Mario'), ('Luigi', 'Luigi')], validators=[DataRequired()])
    submit = SubmitField('Team erstellen/aktualisieren')

class MinigameForm(FlaskForm):
    name = StringField('Minispiel Name', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Beschreibung')
    submit = SubmitField('Minispiel erstellen/aktualisieren')

class ScoreForm(FlaskForm):
    # Dieses Formular wird in deiner enter_scores Route nicht direkt zum Rendern verwendet,
    # aber es ist gut, es für die Konsistenz und mögliche zukünftige Validierungen zu definieren.
    # Die eigentlichen Score-Eingabefelder werden dynamisch im Template erstellt.
    # Hier könnten Validatoren für einzelne Scores stehen, falls benötigt.
    # Beispielhaft ein Feld, das aber so nicht direkt genutzt wird:
    score = IntegerField('Score', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Scores speichern') # Wird im Template ggf. anders gehandhabt
