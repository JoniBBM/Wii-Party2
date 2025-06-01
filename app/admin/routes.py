import sys
import os
import random
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, g
from flask_login import login_user, logout_user, login_required, current_user
from app.models import Admin, Team, Minigame, Character, GameSession, GameEvent, db
from app.forms import AdminLoginForm, TeamForm, MinigameForm, SetNextMinigameForm

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Hilfsfunktion, um die aktive oder eine neue GameSession zu bekommen
def get_or_create_active_session():
    active_session = GameSession.query.filter_by(is_active=True).first()
    if not active_session:
        active_session = GameSession(is_active=True, current_phase='SETUP_MINIGAME')
        db.session.add(active_session)
        db.session.flush() # Wichtig: ID für active_session generieren lassen VOR dem Commit des Events

        # Event für neue Session erstellen
        event = GameEvent(
            game_session_id=active_session.id, # Jetzt hat active_session eine ID
            event_type="game_session_started",
            description="Neue Spielsitzung gestartet."
        )
        db.session.add(event)
        db.session.commit() 
    return active_session

@admin_bp.route('/')
@login_required
def admin_dashboard():
    if not isinstance(current_user, Admin):
        flash('Zugriff verweigert. Nur Admins können das Admin Dashboard sehen.', 'danger')
        return redirect(url_for('main.index'))

    active_session = get_or_create_active_session()
    teams = Team.query.order_by(Team.name).all()
    minigames_db = Minigame.query.all()

    set_minigame_form = SetNextMinigameForm()
    # Choices für das SelectField im Formular setzen
    set_minigame_form.selected_minigame_id.choices = [(0, '-- Manuelle Eingabe verwenden --')] + \
                                                     [(mg.id, mg.name) for mg in minigames_db]

    template_data = {
        "teams": teams,
        "minigames_db": minigames_db,
        "active_session": active_session,
        "current_minigame_name": active_session.current_minigame_name,
        "current_minigame_description": active_session.current_minigame_description,
        "current_phase": active_session.current_phase,
        "set_minigame_form": set_minigame_form # Formular an das Template übergeben
    }
    
    print(f"DEBUG: Admin Dashboard - Session ID: {active_session.id}, Phase: {active_session.current_phase}")
    print(f"DEBUG: Aktuelles Minispiel: Name='{active_session.current_minigame_name}', Beschreibung='{active_session.current_minigame_description}'")
    sys.stdout.flush()

    return render_template('admin.html', **template_data)

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated and isinstance(current_user, Admin):
        return redirect(url_for('admin.admin_dashboard'))
    
    form = AdminLoginForm()
    if form.validate_on_submit():
        admin = Admin.query.filter_by(username=form.username.data).first()
        if admin and admin.check_password(form.password.data):
            login_user(admin)
            flash('Admin erfolgreich eingeloggt.', 'success')
            return redirect(url_for('admin.admin_dashboard'))
        else:
            flash('Ungültiger Benutzername oder Passwort.', 'danger')
    return render_template('admin_login.html', title='Admin Login', form=form)

@admin_bp.route('/logout')
@login_required
def logout():
    if not isinstance(current_user, Admin):
        flash('Nur Admins können sich hier ausloggen.', 'warning')
        return redirect(url_for('main.index'))
    logout_user()
    flash('Admin erfolgreich ausgeloggt.', 'info')
    return redirect(url_for('main.index'))

@admin_bp.route('/set_minigame', methods=['POST'])
@login_required
def set_minigame():
    if not isinstance(current_user, Admin):
        flash('Aktion nicht erlaubt.', 'danger')
        return redirect(url_for('main.index'))

    active_session = get_or_create_active_session()
    form = SetNextMinigameForm(request.form) # Formular mit POST-Daten instanziieren
    
    # Choices für das SelectField im Formular erneut setzen, falls Validierung fehlschlägt und neu gerendert wird
    # (obwohl wir hier bei Erfolg redirecten)
    minigames_db = Minigame.query.all()
    form.selected_minigame_id.choices = [(0, '-- Manuelle Eingabe verwenden --')] + \
                                         [(mg.id, mg.name) for mg in minigames_db]

    # Manuelle Validierung der Pflichtfelder, wenn kein Spiel aus der DB gewählt wurde
    manual_name = form.minigame_name.data
    manual_description = form.minigame_description.data
    selected_id = form.selected_minigame_id.data
    
    # Logik: Wenn eine ID ausgewählt ist, hat diese Vorrang. Sonst müssen Name und Beschreibung da sein.
    minigame_chosen_from_db = False
    if selected_id and selected_id != 0: # 0 ist der Platzhalterwert
        minigame_from_db = Minigame.query.get(selected_id)
        if minigame_from_db:
            active_session.current_minigame_name = minigame_from_db.name
            active_session.current_minigame_description = minigame_from_db.description
            active_session.selected_minigame_id = minigame_from_db.id
            flash(f"Minispiel '{minigame_from_db.name}' aus Bibliothek ausgewählt.", 'info')
            minigame_chosen_from_db = True
        else:
            flash('Ausgewähltes Minispiel nicht gefunden. Bitte manuell eingeben oder erneut auswählen.', 'warning')
            # Hier könnte man das Formular erneut anzeigen, aber wir redirecten erstmal
            return redirect(url_for('admin.admin_dashboard'))
    
    if not minigame_chosen_from_db: # Wenn kein Spiel aus DB, dann manuelle Eingabe prüfen
        if manual_name and manual_description:
            active_session.current_minigame_name = manual_name
            active_session.current_minigame_description = manual_description
            active_session.selected_minigame_id = None 
            flash(f"Minispiel '{manual_name}' manuell gesetzt.", 'info')
        else:
            flash('Bitte Name und Beschreibung für das Minispiel angeben ODER ein Spiel aus der Bibliothek auswählen.', 'warning')
            return redirect(url_for('admin.admin_dashboard'))

    active_session.current_phase = 'MINIGAME_ANNOUNCED'
    event = GameEvent(
        game_session_id=active_session.id,
        event_type="minigame_set",
        description=f"Minispiel '{active_session.current_minigame_name}' wurde festgelegt.",
        related_minigame_id=active_session.selected_minigame_id,
        data_json=f'{{"name": "{active_session.current_minigame_name}", "description": "{active_session.current_minigame_description}"}}'
    )
    db.session.add(event)
    db.session.commit()
    print(f"DEBUG: Minispiel gesetzt - Name: {active_session.current_minigame_name}, Phase: {active_session.current_phase}")
    sys.stdout.flush()
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/record_placements', methods=['POST'])
@login_required
def record_placements():
    if not isinstance(current_user, Admin):
        flash('Aktion nicht erlaubt.', 'danger')
        return redirect(url_for('main.index'))

    active_session = GameSession.query.filter_by(is_active=True).first()
    if not active_session or active_session.current_phase != 'MINIGAME_ANNOUNCED':
        flash('Platzierungen können nur nach Ankündigung eines Minispiels eingegeben werden.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))

    teams = Team.query.all()
    placements = {} 
    
    valid_placements = True
    for team in teams:
        placement_str = request.form.get(f'placement_team_{team.id}')
        if placement_str and placement_str.isdigit():
            placements[team.id] = int(placement_str)
        else:
            flash(f"Ungültige oder fehlende Platzierung für Team {team.name}.", 'danger')
            valid_placements = False
            break 
    
    if not valid_placements:
        return redirect(url_for('admin.admin_dashboard'))

    num_teams = len(teams)
    if len(set(placements.values())) != num_teams or not all(1 <= p <= num_teams for p in placements.values()):
        flash('Ungültige Platzierungen. Jede Platzierung von 1 bis zur Anzahl der Teams muss genau einmal vergeben werden.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    sorted_teams_by_placement = sorted(teams, key=lambda t: placements[t.id])
    
    dice_roll_order_ids = []
    for team_obj in sorted_teams_by_placement: # team_obj statt team um Verwechslung zu vermeiden
        placement = placements[team_obj.id]
        team_obj.minigame_placement = placement
        dice_roll_order_ids.append(str(team_obj.id))

        if placement == 1:
            team_obj.bonus_dice_sides = 6
        elif placement == 2:
            team_obj.bonus_dice_sides = 4
        elif placement == 3:
            team_obj.bonus_dice_sides = 2
        else:
            team_obj.bonus_dice_sides = 0
        
        print(f"DEBUG: Team {team_obj.name} - Platz: {placement}, Bonus: {team_obj.bonus_dice_sides}")

    active_session.dice_roll_order = ",".join(dice_roll_order_ids)
    active_session.current_team_turn_id = int(dice_roll_order_ids[0]) if dice_roll_order_ids else None
    active_session.current_phase = 'DICE_ROLLING'
    
    event_desc = f"Platzierungen für Minigame '{active_session.current_minigame_name}' festgelegt. Würfelreihenfolge: {active_session.dice_roll_order}"
    event_data = {f"team_{t.id}_placement": placements[t.id] for t in teams}
    event = GameEvent(
        game_session_id=active_session.id,
        event_type="placements_recorded",
        description=event_desc,
        data_json=str(event_data)
    )
    db.session.add(event)
    db.session.commit()
    
    flash('Platzierungen erfolgreich gespeichert. Würfelrunde beginnt.', 'success')
    print(f"DEBUG: Platzierungen gespeichert. Phase: {active_session.current_phase}, Nächstes Team: {active_session.current_team_turn_id}")
    sys.stdout.flush()
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/reset_game_state', methods=['POST'])
@login_required
def reset_game_state():
    if not isinstance(current_user, Admin):
        flash('Aktion nicht erlaubt.', 'danger')
        return redirect(url_for('main.index'))

    active_session = GameSession.query.filter_by(is_active=True).first()
    if active_session:
        teams = Team.query.all()
        for team in teams:
            team.minigame_placement = None
            team.bonus_dice_sides = 0
            # team.current_position = 0 # Position zurücksetzen? Hier nicht, wie im Template-Kommentar.

        # Lösche die alte Session und ihre Events.
        # Es ist wichtig, abhängige Objekte zuerst zu behandeln, wenn keine Kaskaden definiert sind,
        # oder sicherzustellen, dass Kaskaden korrekt funktionieren.
        GameEvent.query.filter_by(game_session_id=active_session.id).delete()
        db.session.delete(active_session)
        db.session.commit()
        flash('Aktive Spielsitzung und Team-Platzierungen/Boni zurückgesetzt. Eine neue Session wird beim nächsten Admin-Dashboard-Aufruf gestartet.', 'success')
        print("DEBUG: Spielstatus zurückgesetzt, alte Session und zugehörige Events gelöscht.")
    else:
        flash('Keine aktive Spielsitzung zum Zurücksetzen gefunden.', 'info')
        print("DEBUG: Keine aktive Session zum Zurücksetzen.")
    
    sys.stdout.flush()
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/create_team', methods=['GET', 'POST'])
@login_required
def create_team():
    if not isinstance(current_user, Admin): return redirect(url_for('main.index'))
    form = TeamForm()
    form.character_id.choices = [(0, 'Kein Charakter')] + [(c.id, c.name) for c in Character.query.order_by('name').all()]

    if form.validate_on_submit():
        existing_team = Team.query.filter_by(name=form.name.data).first()
        if existing_team:
            flash('Ein Team mit diesem Namen existiert bereits.', 'warning')
        else:
            team = Team(name=form.name.data, members=form.members.data)
            if form.password.data:
                team.set_password(form.password.data)
            
            selected_character_id = form.character_id.data
            if selected_character_id and selected_character_id != 0: # Sicherstellen, dass 0 nicht als gültige ID interpretiert wird
                char = Character.query.get(selected_character_id)
                if char:
                    team.character_id = char.id
                    team.character_name = char.name
            else:
                team.character_id = None
                team.character_name = None # Explizit auf None setzen

            db.session.add(team)
            db.session.commit()
            flash('Team erfolgreich erstellt.', 'success')
            return redirect(url_for('admin.admin_dashboard'))
    return render_template('create_team.html', title='Team erstellen', form=form)

@admin_bp.route('/edit_team/<int:team_id>', methods=['GET', 'POST'])
@login_required
def edit_team(team_id):
    if not isinstance(current_user, Admin): return redirect(url_for('main.index'))
    team = Team.query.get_or_404(team_id)
    form = TeamForm(obj=team)
    form.character_id.choices = [(0, 'Kein Charakter')] + [(c.id, c.name) for c in Character.query.order_by('name').all()]
    
    if request.method == 'GET':
        form.character_id.data = team.character_id if team.character_id else 0

    if form.validate_on_submit():
        existing_team = Team.query.filter(Team.id != team_id, Team.name == form.name.data).first()
        if existing_team:
            flash('Ein anderes Team mit diesem Namen existiert bereits.', 'warning')
        else:
            team.name = form.name.data
            team.members = form.members.data
            if form.password.data:
                team.set_password(form.password.data)
            
            selected_character_id = form.character_id.data
            if selected_character_id and selected_character_id != 0:
                char = Character.query.get(selected_character_id)
                if char:
                    team.character_id = char.id
                    team.character_name = char.name
            else:
                team.character_id = None
                team.character_name = None

            db.session.commit()
            flash('Team erfolgreich aktualisiert.', 'success')
            return redirect(url_for('admin.admin_dashboard'))
    return render_template('edit_team.html', title='Team bearbeiten', form=form, team=team)

@admin_bp.route('/delete_team/<int:team_id>', methods=['POST'])
@login_required
def delete_team(team_id):
    if not isinstance(current_user, Admin): return redirect(url_for('main.index'))
    team = Team.query.get_or_404(team_id)
    
    # Sessions aktualisieren, wo dieses Team am Zug war
    GameSession.query.filter_by(current_team_turn_id=team.id).update({"current_team_turn_id": None})
    
    # GameEvents anonymisieren
    GameEvent.query.filter_by(related_team_id=team.id).update({"related_team_id": None})
    
    # TeamMinigameScore löschen
    TeamMinigameScore.query.filter_by(team_id=team.id).delete()
    
    db.session.delete(team)
    db.session.commit()
    flash('Team und zugehörige Referenzen erfolgreich gelöscht/anonymisiert.', 'success')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/create_minigame_db', methods=['GET', 'POST'])
@login_required
def create_minigame_db():
    if not isinstance(current_user, Admin): return redirect(url_for('main.index'))
    form = MinigameForm()
    if form.validate_on_submit():
        minigame = Minigame(name=form.name.data, description=form.description.data)
        db.session.add(minigame)
        db.session.commit()
        flash('Datenbank-Minispiel erfolgreich erstellt.', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    return render_template('create_minigame.html', title='DB-Minispiel erstellen', form=form)

@admin_bp.route('/edit_minigame_db/<int:minigame_id>', methods=['GET', 'POST'])
@login_required
def edit_minigame_db(minigame_id):
    if not isinstance(current_user, Admin): return redirect(url_for('main.index'))
    minigame = Minigame.query.get_or_404(minigame_id)
    form = MinigameForm(obj=minigame)
    if form.validate_on_submit():
        minigame.name = form.name.data
        minigame.description = form.description.data
        db.session.commit()
        flash('Datenbank-Minispiel erfolgreich aktualisiert.', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    return render_template('edit_minigame.html', title='DB-Minispiel bearbeiten', form=form, minigame=minigame)

@admin_bp.route('/delete_minigame_db/<int:minigame_id>', methods=['POST'])
@login_required
def delete_minigame_db(minigame_id):
    if not isinstance(current_user, Admin): return redirect(url_for('main.index'))
    minigame = Minigame.query.get_or_404(minigame_id)
    
    GameEvent.query.filter_by(related_minigame_id=minigame.id).update({"related_minigame_id": None})
    TeamMinigameScore.query.filter_by(minigame_id=minigame.id).delete()
    
    active_sessions_with_this_minigame = GameSession.query.filter_by(selected_minigame_id=minigame.id, is_active=True).all()
    for sess in active_sessions_with_this_minigame:
        sess.selected_minigame_id = None
        if sess.current_minigame_name == minigame.name : # Nur wenn es das aktuell manuell gesetzte war
             sess.current_minigame_name = "Gelöschtes Minispiel"
             sess.current_minigame_description = "Dieses Minispiel wurde aus der Bibliothek gelöscht."

    db.session.delete(minigame)
    db.session.commit()
    flash('Datenbank-Minispiel und zugehörige Referenzen erfolgreich gelöscht/anonymisiert.', 'success')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/init_chars')
@login_required
def init_chars():
    if not isinstance(current_user, Admin):
        flash('Nur Admins können auf diese Seite zugreifen.', 'warning')
        return redirect(url_for('main.index'))
    from .init_characters import initialize_characters 
    initialize_characters() 
    flash("Charaktere initialisiert/überprüft.", "info")
    return redirect(url_for('admin.admin_dashboard'))
