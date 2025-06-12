# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, BooleanField, SelectField, HiddenField, TextAreaField, RadioField, FloatField, SelectMultipleField
from wtforms.validators import DataRequired, Length, EqualTo, NumberRange, Optional, ValidationError
from app.models import Character, MinigameFolder, GameRound, Team, FieldConfiguration

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
    
    # Spieler-Management
    members = TextAreaField('Teammitglieder', 
                           validators=[Optional(), Length(max=500)],
                           render_kw={"placeholder": "Spielername 1, Spielername 2, Spielername 3...\n(Ein Name pro Zeile oder kommagetrennt)"})
    
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
    current_position = IntegerField('Aktuelle Position', validators=[NumberRange(min=0, max=72)], default=0)
    last_dice_result = IntegerField('Letztes Würfelergebnis', validators=[Optional(), NumberRange(min=1, max=6)])
    
    # Erweiterte Spieler-Verwaltung
    members = TextAreaField('Teammitglieder', 
                           validators=[Optional(), Length(max=500)],
                           render_kw={"placeholder": "Spielername 1, Spielername 2, Spielername 3...\n(Ein Name pro Zeile oder kommagetrennt)"})
    
    submit = SubmitField('Änderungen speichern')

    def __init__(self, original_team_name, current_character_id, *args, **kwargs):
        super(EditTeamForm, self).__init__(*args, **kwargs)
        self.original_team_name = original_team_name
        available_characters = Character.query.filter(
            (Character.is_selected == False) | (Character.id == current_character_id)
        ).all()
        self.character_id.choices = [(0, '-- Keinen Charakter --')] + [(c.id, c.name) for c in available_characters]
        self.character_id.data = current_character_id if current_character_id else 0

class EditPlayerForm(FlaskForm):
    player_name = StringField('Spielername', validators=[DataRequired(), Length(min=2, max=100)])
    assigned_team_id = SelectField('Team zuweisen', coerce=int, validators=[Optional()])
    submit = SubmitField('Spieler aktualisieren')

    def __init__(self, *args, **kwargs):
        super(EditPlayerForm, self).__init__(*args, **kwargs)
        teams = Team.query.order_by(Team.name).all()
        self.assigned_team_id.choices = [(0, '-- Kein Team --')] + [(t.id, t.name) for t in teams]

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
    
    # Spieleranzahl für alle Arten von Inhalten
    player_count = SelectField('Spieleranzahl', choices=[
        ('1', 'Pro Team 1 Spieler'),
        ('2', 'Pro Team 2 Spieler'),
        ('3', 'Pro Team 3 Spieler'),
        ('4', 'Pro Team 4 Spieler'),
        ('all', 'Ganzes Team')
    ], validators=[Optional()], default='all')
    
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
    player_count = SelectField('Spieleranzahl', choices=[
        ('1', 'Pro Team 1 Spieler'),
        ('2', 'Pro Team 2 Spieler'),
        ('3', 'Pro Team 3 Spieler'),
        ('4', 'Pro Team 4 Spieler'),
        ('all', 'Ganzes Team')
    ], validators=[DataRequired()], default='all')
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
    player_count = SelectField('Spieleranzahl', choices=[
        ('1', 'Pro Team 1 Spieler'),
        ('2', 'Pro Team 2 Spieler'),
        ('3', 'Pro Team 3 Spieler'),
        ('4', 'Pro Team 4 Spieler'),
        ('all', 'Ganzes Team')
    ], validators=[DataRequired()], default='all')
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

# NEU: FELD-MANAGEMENT FORMS

class FieldConfigurationForm(FlaskForm):
    """Form für das Bearbeiten von Feld-Konfigurationen"""
    display_name = StringField('Anzeige-Name', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Beschreibung', validators=[Optional(), Length(max=500)])
    is_enabled = BooleanField('Aktiviert', default=True)
    
    # Häufigkeits-Konfiguration
    frequency_type = SelectField('Häufigkeits-Typ', choices=[
        ('modulo', 'Modulo-basiert (alle X Felder)'),
        ('fixed_positions', 'Feste Positionen'),
        ('probability', 'Wahrscheinlichkeitsbasiert (%)'),
        ('default', 'Standard (für normale Felder)')
    ], validators=[DataRequired()])
    
    frequency_value = IntegerField('Häufigkeits-Wert', validators=[NumberRange(min=0, max=100)], default=10)
    
    # Feste Positionen (nur bei frequency_type = 'fixed_positions')
    fixed_positions = StringField('Feste Positionen (komma-getrennt)', validators=[Optional()],
                                 render_kw={"placeholder": "z.B. 15,30,45,60"})
    
    # Farb-Konfiguration
    color_hex = StringField('Hauptfarbe (Hex)', validators=[DataRequired(), Length(min=7, max=7)], 
                           default='#81C784', render_kw={"type": "color"})
    emission_hex = StringField('Effektfarbe (Hex)', validators=[Optional(), Length(min=7, max=7)], 
                              default='#4CAF50', render_kw={"type": "color"})
    
    # Icon/Symbol
    icon = StringField('Icon/Symbol', validators=[Optional(), Length(max=10)], 
                      render_kw={"placeholder": "z.B. 🚀, ⭐, 🎮"})
    
    # Feldspezifische Konfigurationen
    # Katapult Felder
    min_distance = IntegerField('Min. Distanz', validators=[Optional(), NumberRange(min=1, max=20)], default=3)
    max_distance = IntegerField('Max. Distanz', validators=[Optional(), NumberRange(min=1, max=20)], default=5)
    
    # Sperren-Feld
    target_numbers = StringField('Ziel-Zahlen (komma-getrennt)', validators=[Optional()],
                                default='4,5,6', render_kw={"placeholder": "z.B. 4,5,6"})
    
    # Bonus-Feld
    bonus_type = SelectField('Bonus-Typ', choices=[
        ('extra_dice', 'Extra-Würfel'),
        ('extra_move', 'Extra-Bewegung'),
        ('shield', 'Schutzschild')
    ], validators=[Optional()], default='extra_dice')
    
    # Fallen-Feld
    trap_effects = SelectMultipleField('Fallen-Effekte', choices=[
        ('move_back', 'Zurück bewegen'),
        ('skip_turn', 'Zug überspringen'),
        ('remove_bonus', 'Bonus entfernen'),
        ('lose_dice', 'Würfel verlieren')
    ], validators=[Optional()])
    
    # Ereignis-Feld
    chance_events = SelectMultipleField('Mögliche Ereignisse', choices=[
        ('bonus_move', 'Bonus-Bewegung'),
        ('lose_turn', 'Zug verlieren'),
        ('extra_roll', 'Extra-Wurf'),
        ('teleport', 'Teleportation'),
        ('swap_random', 'Zufälliger Tausch')
    ], validators=[Optional()])
    
    submit = SubmitField('Konfiguration speichern')

    def __init__(self, field_type=None, *args, **kwargs):
        super(FieldConfigurationForm, self).__init__(*args, **kwargs)
        self.field_type = field_type
        
        # Setze Standard-Werte basierend auf Feld-Typ
        if field_type and not kwargs.get('obj'):
            from app.admin.field_config import get_field_type_templates
            templates = get_field_type_templates()
            if field_type in templates:
                template = templates[field_type]
                self.display_name.data = template['display_name']
                self.description.data = template['description']
                self.color_hex.data = template['color_hex']
                self.emission_hex.data = template['emission_hex']
                self.icon.data = template['icon']
                self.frequency_type.data = template['frequency_type']
                self.frequency_value.data = template['frequency_value']

    def validate_frequency_value(self, frequency_value):
        if self.frequency_type.data == 'modulo' and frequency_value.data <= 0:
            raise ValidationError('Modulo-Wert muss größer als 0 sein.')
        if self.frequency_type.data == 'probability' and (frequency_value.data < 0 or frequency_value.data > 100):
            raise ValidationError('Wahrscheinlichkeit muss zwischen 0 und 100 liegen.')

    def validate_color_hex(self, color_hex):
        import re
        if not re.match(r'^#[0-9A-Fa-f]{6}$', color_hex.data):
            raise ValidationError('Farbe muss ein gültiger Hex-Code sein (z.B. #FF0000).')

    def validate_emission_hex(self, emission_hex):
        if emission_hex.data:
            import re
            if not re.match(r'^#[0-9A-Fa-f]{6}$', emission_hex.data):
                raise ValidationError('Effektfarbe muss ein gültiger Hex-Code sein (z.B. #FF0000).')

    def validate_fixed_positions(self, fixed_positions):
        if self.frequency_type.data == 'fixed_positions' and fixed_positions.data:
            try:
                positions = [int(x.strip()) for x in fixed_positions.data.split(',') if x.strip()]
                if not positions:
                    raise ValidationError('Mindestens eine Position muss angegeben werden.')
                for pos in positions:
                    if pos < 0 or pos > 72:
                        raise ValidationError('Positionen müssen zwischen 0 und 72 liegen.')
            except ValueError:
                raise ValidationError('Positionen müssen Zahlen sein, getrennt durch Kommas.')

    def validate_target_numbers(self, target_numbers):
        if self.field_type == 'barrier' and target_numbers.data:
            data = target_numbers.data.strip()
            
            # Check for special syntaxes
            if data.startswith('-'):
                # Maximum mode: -4 means "4 or less"
                try:
                    num = int(data[1:])
                    if num < 1 or num > 6:
                        raise ValidationError('Bei negativen Zahlen muss der Wert zwischen 1 und 6 liegen.')
                except ValueError:
                    raise ValidationError('Nach dem Minus muss eine Zahl zwischen 1 und 6 stehen.')
            elif data.endswith('+'):
                # Minimum mode: 5+ means "5 or more"
                try:
                    num = int(data[:-1])
                    if num < 1 or num > 6:
                        raise ValidationError('Bei Plus-Notation muss der Wert zwischen 1 und 6 liegen.')
                except ValueError:
                    raise ValidationError('Vor dem Plus muss eine Zahl zwischen 1 und 6 stehen.')
            else:
                # Exact numbers mode
                try:
                    numbers = [int(x.strip()) for x in data.split(',') if x.strip()]
                    if not numbers:
                        raise ValidationError('Mindestens eine Ziel-Zahl muss angegeben werden.')
                    for num in numbers:
                        if num < 1 or num > 6:
                            raise ValidationError('Ziel-Zahlen müssen zwischen 1 und 6 liegen.')
                except ValueError:
                    raise ValidationError('Ziel-Zahlen müssen Zahlen sein (z.B. "4,5,6"), oder spezielle Syntax verwenden (z.B. "-3" oder "5+").')

class FieldPreviewForm(FlaskForm):
    """Form für Spielfeld-Vorschau-Einstellungen"""
    max_fields = IntegerField('Anzahl Felder', validators=[NumberRange(min=10, max=100)], default=73)
    show_field_numbers = BooleanField('Feld-Nummern anzeigen', default=True)
    show_field_types = BooleanField('Feld-Typen anzeigen', default=True)
    show_statistics = BooleanField('Statistiken anzeigen', default=True)
    highlight_conflicts = BooleanField('Konflikte hervorheben', default=True)
    
    submit = SubmitField('Vorschau aktualisieren')

class FieldImportExportForm(FlaskForm):
    """Form für Import/Export von Feld-Konfigurationen"""
    import_data = TextAreaField('JSON-Daten importieren', validators=[Optional()],
                               render_kw={"rows": "10", "placeholder": "JSON-Konfiguration hier einfügen..."})
    export_format = SelectField('Export-Format', choices=[
        ('json', 'JSON'),
        ('csv', 'CSV'),
        ('backup', 'Backup-Datei')
    ], default='json')
    
    include_disabled = BooleanField('Deaktivierte Felder einschließen', default=False)
    
    import_submit = SubmitField('Konfigurationen importieren')
    export_submit = SubmitField('Konfigurationen exportieren')
    reset_submit = SubmitField('Auf Standard zurücksetzen')

    def validate_import_data(self, import_data):
        if import_data.data:
            try:
                import json
                data = json.loads(import_data.data)
                if not isinstance(data, list):
                    raise ValidationError('Import-Daten müssen eine JSON-Liste sein.')
                
                required_fields = ['field_type', 'display_name', 'color_hex']
                for item in data:
                    if not isinstance(item, dict):
                        raise ValidationError('Jedes Element muss ein JSON-Objekt sein.')
                    for field in required_fields:
                        if field not in item:
                            raise ValidationError(f'Erforderliches Feld "{field}" fehlt in einem der Elemente.')
            except json.JSONDecodeError:
                raise ValidationError('Ungültiges JSON-Format.')
            except Exception as e:
                raise ValidationError(f'Fehler beim Validieren der Import-Daten: {str(e)}')

class FieldBulkEditForm(FlaskForm):
    """Form für Massen-Bearbeitung von Feld-Konfigurationen"""
    selected_fields = SelectMultipleField('Felder auswählen', choices=[], validators=[DataRequired()])
    
    action = SelectField('Aktion', choices=[
        ('enable', 'Aktivieren'),
        ('disable', 'Deaktivieren'),
        ('change_frequency', 'Häufigkeit ändern'),
        ('change_colors', 'Farben ändern'),
        ('delete', 'Löschen')
    ], validators=[DataRequired()])
    
    # Für Häufigkeits-Änderung
    new_frequency_type = SelectField('Neuer Häufigkeits-Typ', choices=[
        ('modulo', 'Modulo-basiert'),
        ('fixed_positions', 'Feste Positionen'),
        ('probability', 'Wahrscheinlichkeitsbasiert')
    ], validators=[Optional()])
    
    new_frequency_value = IntegerField('Neuer Häufigkeits-Wert', validators=[Optional(), NumberRange(min=0, max=100)])
    
    # Für Farb-Änderung
    new_color_hex = StringField('Neue Hauptfarbe', validators=[Optional(), Length(min=7, max=7)],
                               render_kw={"type": "color"})
    new_emission_hex = StringField('Neue Effektfarbe', validators=[Optional(), Length(min=7, max=7)],
                                  render_kw={"type": "color"})
    
    submit = SubmitField('Massen-Bearbeitung ausführen')

    def __init__(self, *args, **kwargs):
        super(FieldBulkEditForm, self).__init__(*args, **kwargs)
        # Lade verfügbare Felder - verwende field_type als Value (nicht ID)
        field_configs = FieldConfiguration.query.all()
        self.selected_fields.choices = [(config.field_type, f"{config.display_name} ({config.field_type})") 
                                       for config in field_configs]