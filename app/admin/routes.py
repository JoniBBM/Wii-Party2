# app/admin/routes.py
import sys
import os
import random
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, g, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models import Admin, Team, Minigame, Character, GameSession, GameEvent, db # TeamMinigameScore ggf. importieren
from app.forms import AdminLoginForm, CreateTeamForm, EditTeamForm, MinigameForm, SetNextMinigameForm, AdminConfirmPasswordForm # TeamForm wurde zu CreateTeamForm/EditTeamForm

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Hilfsfunktion, um die aktive oder eine neue GameSession zu bekommen
def get_or_create_active_session():
    active_session = GameSession.query.filter_by(is_active=True).first()
    if not active_session:
        active_session = GameSession(is_active=True, current_phase='SETUP_MINIGAME')
        db.session.add(active_session)
        db.session.flush() 

        event = GameEvent(
            game_session_id=active_session.id,
            event_type="game_session_started",
            description="Neue Spielsitzung gestartet."
        )
        db.session.add(event)
        db.session.commit() 
    return active_session

@admin_bp.route('/', methods=['GET', 'POST']) # POST für das Reset-Formular
@login_required
def admin_dashboard():
    if not isinstance(current_user, Admin):
        flash('Zugriff verweigert. Nur Admins können das Admin Dashboard sehen.', 'danger')
        return redirect(url_for('main.index'))

    active_session = get_or_create_active_session()
    teams = Team.query.order_by(Team.name).all()
    minigames_db = Minigame.query.all()

    set_minigame_form = SetNextMinigameForm()
    set_minigame_form.selected_minigame_id.choices = [(0, '-- Manuelle Eingabe verwenden --')] + \
                                                     [(mg.id, mg.name) for mg in minigames_db]
    
    confirm_reset_form = AdminConfirmPasswordForm() # Formular für Passwortbestätigung

    # Das reset_game_state Formular wird jetzt hier gehandhabt, wenn es per POST kommt
    # Aber die Logik ist in einer eigenen Route, um es sauber zu halten.
    # Hier wird es nur für die Anzeige im Template benötigt.

    template_data = {
        "teams": teams,
        "minigames_db": minigames_db,
        "active_session": active_session,
        "current_minigame_name": active_session.current_minigame_name,
        "current_minigame_description": active_session.current_minigame_description,
        "current_phase": active_session.current_phase,
        "set_minigame_form": set_minigame_form,
        "confirm_reset_form": confirm_reset_form # Passwortbestätigungsformular an Template übergeben
    }
    
    # current_app.logger.debug(f"Admin Dashboard - Session ID: {active_session.id}, Phase: {active_session.current_phase}")
    # current_app.logger.debug(f"Aktuelles Minispiel: Name='{active_session.current_minigame_name}', Beschreibung='{active_session.current_minigame_description}'")

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

@admin_bp.route('/admin_roll_dice', methods=['POST'])
@login_required
def admin_roll_dice():
    if not isinstance(current_user, Admin):
        return jsonify({"success": False, "error": "Nur Admins können würfeln."}), 403

    try:
        active_session = GameSession.query.filter_by(is_active=True).first()
        if not active_session:
            return jsonify({"success": False, "error": "Keine aktive Spielsitzung."}), 404

        if active_session.current_phase != 'DICE_ROLLING':
            return jsonify({"success": False, "error": "Es ist nicht die Würfelphase."}), 403
        
        current_team_id = active_session.current_team_turn_id
        if not current_team_id:
            return jsonify({"success": False, "error": "Kein Team für aktuellen Zug festgelegt."}), 404

        team = Team.query.get(current_team_id)
        if not team:
            return jsonify({"success": False, "error": "Aktuelles Team nicht gefunden."}), 404

        standard_dice_roll = random.randint(1, 6)
        bonus_dice_roll = 0
        if team.bonus_dice_sides and team.bonus_dice_sides > 0:
            bonus_dice_roll = random.randint(1, team.bonus_dice_sides)
        
        total_roll = standard_dice_roll + bonus_dice_roll
        old_position = team.current_position
        
        max_field_index = current_app.config.get('MAX_BOARD_FIELDS', 72) # Aus Config laden
        new_position = min(team.current_position + total_roll, max_field_index)
        team.current_position = new_position

        event_description = f"Admin würfelte für Team {team.name}: {standard_dice_roll}"
        if bonus_dice_roll > 0:
            event_description += f" (Bonus: {bonus_dice_roll}, Gesamt: {total_roll})"
        event_description += f" und bewegte sich von Feld {old_position} zu Feld {new_position}."
        
        dice_event = GameEvent(
            game_session_id=active_session.id,
            event_type="admin_dice_roll",
            description=event_description,
            related_team_id=team.id,
            data_json=str({
                "standard_roll": standard_dice_roll,
                "bonus_roll": bonus_dice_roll,
                "total_roll": total_roll,
                "old_position": old_position,
                "new_position": new_position,
                "rolled_by": "admin"
            })
        )
        db.session.add(dice_event)

        dice_order_ids_str = active_session.dice_roll_order
        if not dice_order_ids_str: # Fallback, falls die Reihenfolge leer ist
            db.session.rollback()
            current_app.logger.error("Würfelreihenfolge ist leer in der aktiven Session.")
            return jsonify({"success": False, "error": "Fehler: Würfelreihenfolge nicht gesetzt."}), 500

        dice_order_ids_int = [int(tid) for tid in dice_order_ids_str.split(',') if tid.isdigit()]
        
        current_team_index_in_order = -1
        if team.id in dice_order_ids_int:
            current_team_index_in_order = dice_order_ids_int.index(team.id)
        else:
            db.session.rollback()
            current_app.logger.error(f"Team {team.id} nicht in Würfelreihenfolge {dice_order_ids_int} gefunden.")
            return jsonify({"success": False, "error": "Fehler in der Würfelreihenfolge (Team nicht gefunden)."}), 500

        next_team_name = None # Initialisieren
        if current_team_index_in_order < len(dice_order_ids_int) - 1:
            active_session.current_team_turn_id = dice_order_ids_int[current_team_index_in_order + 1]
            next_team = Team.query.get(active_session.current_team_turn_id)
            next_team_name = next_team.name if next_team else "Unbekannt"
        else:
            active_session.current_phase = 'ROUND_OVER'
            active_session.current_team_turn_id = None 
            
            all_teams_in_db = Team.query.all()
            for t_obj in all_teams_in_db:
                t_obj.bonus_dice_sides = 0
                # t_obj.minigame_placement = None # Platzierung wird erst beim nächsten Minispiel neu gesetzt
            
            round_over_event = GameEvent(
                game_session_id=active_session.id,
                event_type="dice_round_finished",
                description="Admin beendete die Würfelrunde. Alle Teams haben gewürfelt."
            )
            db.session.add(round_over_event)

        db.session.commit()

        # current_app.logger.debug(f"Admin würfelte für {team.name}: {standard_dice_roll}+{bonus_dice_roll}={total_roll}, neue Position: {new_position}")
        # if next_team_name:
        #     current_app.logger.debug(f"Nächstes Team: {next_team_name}")
        # else:
        #     current_app.logger.debug(f"Runde beendet, Phase: {active_session.current_phase}")

        return jsonify({
            "success": True,
            "team_id": team.id,
            "team_name": team.name,
            "standard_roll": standard_dice_roll,
            "bonus_roll": bonus_dice_roll,
            "total_roll": total_roll,
            "old_position": old_position,
            "new_position": new_position,
            "next_team_id": active_session.current_team_turn_id,
            "next_team_name": next_team_name, # Wird gesendet, auch wenn None
            "new_phase": active_session.current_phase
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Schwerer Fehler in admin_roll_dice: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Ein interner Serverfehler beim Würfeln ist aufgetreten.", "details": str(e)}), 500

@admin_bp.route('/set_minigame', methods=['POST'])
@login_required
def set_minigame():
    if not isinstance(current_user, Admin):
        flash('Aktion nicht erlaubt.', 'danger')
        return redirect(url_for('main.index'))

    active_session = get_or_create_active_session()
    form = SetNextMinigameForm(request.form)
    
    minigames_db = Minigame.query.all()
    form.selected_minigame_id.choices = [(0, '-- Manuelle Eingabe verwenden --')] + \
                                         [(mg.id, mg.name) for mg in minigames_db]

    manual_name = form.minigame_name.data
    manual_description = form.minigame_description.data
    selected_id = form.selected_minigame_id.data
    
    minigame_chosen_from_db = False
    if selected_id and selected_id != 0:
        minigame_from_db = Minigame.query.get(selected_id)
        if minigame_from_db:
            active_session.current_minigame_name = minigame_from_db.name
            active_session.current_minigame_description = minigame_from_db.description
            active_session.selected_minigame_id = minigame_from_db.id
            flash(f"Minispiel '{minigame_from_db.name}' aus Bibliothek ausgewählt.", 'info')
            minigame_chosen_from_db = True
        else:
            flash('Ausgewähltes Minispiel nicht gefunden.', 'warning')
            return redirect(url_for('admin.admin_dashboard'))
    
    if not minigame_chosen_from_db:
        if manual_name and manual_description: # Nur wenn Name UND Beschreibung da sind
            active_session.current_minigame_name = manual_name
            active_session.current_minigame_description = manual_description
            active_session.selected_minigame_id = None 
            flash(f"Minispiel '{manual_name}' manuell gesetzt.", 'info')
        elif manual_name and not manual_description: # Nur Name gegeben
             flash('Bitte auch eine Beschreibung für das manuelle Minispiel angeben.', 'warning')
             return redirect(url_for('admin.admin_dashboard'))
        elif not manual_name and manual_description: # Nur Beschreibung gegeben
             flash('Bitte auch einen Namen für das manuelle Minispiel angeben.', 'warning')
             return redirect(url_for('admin.admin_dashboard'))
        else: # Beides leer und nichts ausgewählt
            flash('Bitte Name und Beschreibung für das Minispiel angeben ODER ein Spiel aus der Bibliothek auswählen.', 'warning')
            return redirect(url_for('admin.admin_dashboard'))

    active_session.current_phase = 'MINIGAME_ANNOUNCED'
    # Alte Platzierungen der Teams zurücksetzen, wenn ein neues Minispiel gesetzt wird
    teams_to_reset = Team.query.all()
    for t in teams_to_reset:
        t.minigame_placement = None
        # Bonuswürfel bleiben bis nach der Würfelrunde des vorherigen Minispiels erhalten

    event = GameEvent(
        game_session_id=active_session.id,
        event_type="minigame_set",
        description=f"Minispiel '{active_session.current_minigame_name}' wurde festgelegt. Platzierungen zurückgesetzt.",
        related_minigame_id=active_session.selected_minigame_id,
        data_json=f'{{"name": "{active_session.current_minigame_name}", "description": "{active_session.current_minigame_description}"}}'
    )
    db.session.add(event)
    db.session.commit()
    # current_app.logger.debug(f"Minispiel gesetzt - Name: {active_session.current_minigame_name}, Phase: {active_session.current_phase}")
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
    if not teams:
        flash('Keine Teams vorhanden, um Platzierungen einzutragen.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))
        
    placements = {} 
    
    valid_placements = True
    for team_obj_iter in teams: # Umbenannt, um Konflikt mit team-Variable unten zu vermeiden
        placement_str = request.form.get(f'placement_team_{team_obj_iter.id}')
        if placement_str and placement_str.isdigit():
            placements[team_obj_iter.id] = int(placement_str)
        else:
            flash(f"Ungültige oder fehlende Platzierung für Team {team_obj_iter.name}.", 'danger')
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
    for team_obj in sorted_teams_by_placement:
        placement = placements[team_obj.id]
        team_obj.minigame_placement = placement
        dice_roll_order_ids.append(str(team_obj.id))

        # Bonuswürfel basierend auf Platzierung
        bonus_config = current_app.config.get('PLACEMENT_BONUS_DICE', {1: 6, 2: 4, 3: 2})
        team_obj.bonus_dice_sides = bonus_config.get(placement, 0)
        
        # current_app.logger.debug(f"Team {team_obj.name} - Platz: {placement}, Bonus: {team_obj.bonus_dice_sides}")

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
    # current_app.logger.debug(f"Platzierungen gespeichert. Phase: {active_session.current_phase}, Nächstes Team: {active_session.current_team_turn_id}")
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/reset_game_state_confirmed', methods=['POST']) # Eigene Route für den bestätigten Reset
@login_required
def reset_game_state_confirmed():
    if not isinstance(current_user, Admin):
        flash('Aktion nicht erlaubt.', 'danger')
        return redirect(url_for('main.index'))

    form = AdminConfirmPasswordForm(request.form)
    admin_user = Admin.query.get(current_user.id) # Admin-Objekt frisch laden

    if form.validate_on_submit():
        if admin_user and admin_user.check_password(form.password.data):
            try:
                # 1. Alle GameEvents löschen (oder zumindest die der aktiven Sessions)
                # Um sicherzugehen, dass wir keine Foreign Key Constraints verletzen,
                # löschen wir Events, bevor wir Sessions löschen.
                # Wenn es viele Sessions gäbe, könnte man das auf aktive beschränken.
                GameEvent.query.delete() # Löscht alle Events

                # 2. Alle GameSessions löschen (oder zumindest die aktive)
                GameSession.query.delete() # Löscht alle Sessions

                # 3. Alle Teams zurücksetzen
                teams = Team.query.all()
                for team in teams:
                    team.minigame_placement = None
                    team.bonus_dice_sides = 0
                    team.current_position = 0  # Position auch zurücksetzen

                # Ggf. TeamMinigameScore löschen, falls diese Tabelle existiert und genutzt wird
                # from app.models import TeamMinigameScore # Sicherstellen, dass Import existiert
                # TeamMinigameScore.query.delete()

                db.session.commit()
                flash('Spiel komplett zurückgesetzt (inkl. Positionen, Events, Session). Eine neue Session wird beim nächsten Aufruf gestartet.', 'success')
                current_app.logger.info("Spiel komplett zurückgesetzt durch Admin.")
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Fehler beim kompletten Zurücksetzen des Spiels: {e}", exc_info=True)
                flash('Fehler beim Zurücksetzen des Spiels.', 'danger')
        else:
            flash('Falsches Admin-Passwort. Spiel nicht zurückgesetzt.', 'danger')
    else:
        flash('Passworteingabe für Reset ungültig.', 'warning')
        # Bei Fehlern im Formular (z.B. leeres Passwort) zurück zum Dashboard, wo das Formular angezeigt wird.
        # Die Fehler werden dann vom Formular selbst angezeigt, wenn es im Template richtig eingebunden ist.

    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/create_team', methods=['GET', 'POST'])
@login_required
def create_team():
    if not isinstance(current_user, Admin): return redirect(url_for('main.index'))
    form = CreateTeamForm() # Verwendet das neue Formular
    # Character choices werden jetzt im Formular __init__ gesetzt

    if form.validate_on_submit():
        existing_team = Team.query.filter_by(name=form.team_name.data).first()
        if existing_team:
            flash('Ein Team mit diesem Namen existiert bereits.', 'warning')
        else:
            team = Team(name=form.team_name.data)
            team.set_password(form.password.data) # Passwort ist jetzt Pflicht
            
            selected_character_id = form.character_id.data
            char = Character.query.get(selected_character_id) # character_id ist jetzt Pflicht
            if char:
                if char.is_selected:
                    flash(f'Charakter {char.name} ist bereits ausgewählt. Bitte einen anderen wählen.', 'warning')
                    # Formular erneut anzeigen mit Fehlermeldung (kein redirect)
                    return render_template('create_team.html', title='Team erstellen', form=form)
                
                team.character_id = char.id
                team.character_name = char.name
                char.is_selected = True # Charakter als ausgewählt markieren
                db.session.add(char)
            # Kein else nötig, da character_id ein Pflichtfeld ist und validiert wird

            db.session.add(team)
            db.session.commit()
            flash('Team erfolgreich erstellt.', 'success')
            return redirect(url_for('admin.admin_dashboard'))
    else:
        # Fehler ausgeben, falls die Formularvalidierung fehlschlägt
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Fehler im Feld '{getattr(form, field).label.text}': {error}", 'danger')

    return render_template('create_team.html', title='Team erstellen', form=form)


@admin_bp.route('/edit_team/<int:team_id>', methods=['GET', 'POST'])
@login_required
def edit_team(team_id):
    if not isinstance(current_user, Admin): return redirect(url_for('main.index'))
    team = Team.query.get_or_404(team_id)
    
    # Holen des aktuellen Charakters, bevor das Formular instanziiert wird
    current_char_id_for_form = team.character_id if team.character_id else 0

    form = EditTeamForm(original_team_name=team.name, current_character_id=current_char_id_for_form, obj=team)
    # Character choices werden jetzt im Formular __init__ gesetzt,
    # inklusive Logik, um den aktuell ausgewählten Charakter des Teams verfügbar zu machen.

    if request.method == 'GET':
        # Setze den aktuellen Charakter des Teams im Formular vorausgewählt
        form.character_id.data = team.character_id if team.character_id else None


    if form.validate_on_submit():
        # Prüfen, ob das aktuelle Admin-Passwort korrekt ist, falls Änderungen vorgenommen werden sollen
        # die es erfordern (z.B. Passwortänderung des Teams). Hier nicht explizit implementiert,
        # aber `form.current_password.data` wäre der Ort dafür.
        # Fürs Erste gehen wir davon aus, dass der Admin berechtigt ist.

        # Name-Validierung: Sicherstellen, dass der neue Name nicht von einem *anderen* Team verwendet wird
        if form.team_name.data != team.name: # Nur prüfen, wenn der Name geändert wurde
            existing_team = Team.query.filter(Team.id != team_id, Team.name == form.team_name.data).first()
            if existing_team:
                flash('Ein anderes Team mit diesem Namen existiert bereits.', 'warning')
                return render_template('edit_team.html', title='Team bearbeiten', form=form, team=team)
        
        team.name = form.team_name.data
        
        if form.password.data: # Wenn ein neues Passwort eingegeben wurde
            team.set_password(form.password.data)

        new_character_id = form.character_id.data
        old_character_id = team.character_id

        if new_character_id != old_character_id:
            # Alten Charakter als nicht ausgewählt markieren, falls vorhanden
            if old_character_id:
                old_char = Character.query.get(old_character_id)
                if old_char:
                    old_char.is_selected = False
                    db.session.add(old_char)
            
            # Neuen Charakter als ausgewählt markieren und dem Team zuweisen
            if new_character_id: # new_character_id könnte auch None sein, wenn "kein Charakter" gewählt wird
                new_char = Character.query.get(new_character_id)
                if new_char:
                    if new_char.is_selected: # Darf nicht passieren, wenn Formularlogik stimmt
                        flash(f"Charakter {new_char.name} ist bereits von einem anderen Team ausgewählt.", "warning")
                        return render_template('edit_team.html', title='Team bearbeiten', form=form, team=team)
                    team.character_id = new_char.id
                    team.character_name = new_char.name
                    new_char.is_selected = True
                    db.session.add(new_char)
                else: # Sollte nicht passieren, wenn character_id aus gültigen Choices kommt
                    team.character_id = None
                    team.character_name = None
            else: # "Kein Charakter" wurde explizit ausgewählt
                team.character_id = None
                team.character_name = None
        
        db.session.commit()
        flash('Team erfolgreich aktualisiert.', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    else:
        # Fehler ausgeben, falls die Formularvalidierung fehlschlägt (z.B. bei GET oder invalid POST)
        if request.method == 'POST': # Nur bei fehlgeschlagenem POST die Fehler anzeigen
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"Fehler im Feld '{getattr(form, field).label.text}': {error}", 'danger')

    return render_template('edit_team.html', title='Team bearbeiten', form=form, team=team)


@admin_bp.route('/delete_team/<int:team_id>', methods=['POST'])
@login_required
def delete_team(team_id):
    if not isinstance(current_user, Admin): return redirect(url_for('main.index'))
    team = Team.query.get_or_404(team_id)
    
    # Charakter des Teams als nicht mehr ausgewählt markieren
    if team.character_id:
        char = Character.query.get(team.character_id)
        if char:
            char.is_selected = False
            db.session.add(char)

    # Sessions aktualisieren, wo dieses Team am Zug war
    GameSession.query.filter_by(current_team_turn_id=team.id).update({"current_team_turn_id": None})
    
    # GameEvents anonymisieren
    GameEvent.query.filter_by(related_team_id=team.id).update({"related_team_id": None})
    
    # TeamMinigameScore löschen (falls vorhanden)
    # from app.models import TeamMinigameScore # Sicherstellen, dass Import existiert
    # TeamMinigameScore.query.filter_by(team_id=team.id).delete()
    
    # Würfelreihenfolge in aktiven Sessions anpassen
    active_sessions = GameSession.query.filter(GameSession.dice_roll_order.like(f"%{team.id}%")).all()
    for sess in active_sessions:
        order_list = sess.dice_roll_order.split(',')
        if str(team.id) in order_list:
            order_list.remove(str(team.id))
            sess.dice_roll_order = ",".join(order_list)
            if not order_list and sess.current_phase == 'DICE_ROLLING': # Wenn letztes Team gelöscht wurde
                sess.current_phase = 'ROUND_OVER' # Oder eine andere passende Phase
                sess.current_team_turn_id = None


    db.session.delete(team)
    db.session.commit()
    flash('Team und zugehörige Referenzen erfolgreich gelöscht/aktualisiert.', 'success')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/create_minigame_db', methods=['GET', 'POST'])
@login_required
def create_minigame_db():
    if not isinstance(current_user, Admin): return redirect(url_for('main.index'))
    form = MinigameForm()
    if form.validate_on_submit():
        minigame = Minigame(name=form.name.data, description=form.description.data, type=form.type.data)
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
        minigame.type = form.type.data
        db.session.commit()
        flash('Datenbank-Minispiel erfolgreich aktualisiert.', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    return render_template('edit_minigame.html', title='DB-Minispiel bearbeiten', form=form, minigame=minigame)

@admin_bp.route('/delete_minigame_db/<int:minigame_id>', methods=['POST'])
@login_required
def delete_minigame_db(minigame_id):
    if not isinstance(current_user, Admin): return redirect(url_for('main.index'))
    minigame_to_delete = Minigame.query.get_or_404(minigame_id) # Umbenannt, um Konflikt zu vermeiden
    
    # GameEvents anonymisieren, die sich auf dieses Minispiel beziehen
    GameEvent.query.filter_by(related_minigame_id=minigame_to_delete.id).update({"related_minigame_id": None})
    
    # TeamMinigameScore löschen, die sich auf dieses Minispiel beziehen (falls vorhanden)
    # from app.models import TeamMinigameScore # Sicherstellen, dass Import existiert
    # TeamMinigameScore.query.filter_by(minigame_id=minigame_to_delete.id).delete()
    
    # Aktive Sessions aktualisieren, die dieses Minispiel ausgewählt haben
    active_sessions_with_this_minigame = GameSession.query.filter_by(selected_minigame_id=minigame_to_delete.id).all()
    for sess in active_sessions_with_this_minigame:
        sess.selected_minigame_id = None
        # Wenn das gelöschte Minispiel das aktuell im Textfeld stehende ist, neutralen Text setzen
        if sess.current_minigame_name == minigame_to_delete.name:
             sess.current_minigame_name = "N/A" # Oder leer lassen
             sess.current_minigame_description = "Minispiel wurde gelöscht."
             if sess.current_phase == 'MINIGAME_ANNOUNCED': # Wenn das gelöschte Spiel gerade aktiv war
                 sess.current_phase = 'SETUP_MINIGAME' # Zurück zur Minispielauswahl

    db.session.delete(minigame_to_delete)
    db.session.commit()
    flash('Datenbank-Minispiel und zugehörige Referenzen erfolgreich gelöscht/aktualisiert.', 'success')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/init_chars')
@login_required
def init_chars():
    if not isinstance(current_user, Admin):
        flash('Nur Admins können auf diese Seite zugreifen.', 'warning')
        return redirect(url_for('main.index'))
    
    # Pfad zur init_characters.py anpassen, falls es direkt im admin-Ordner liegt
    # from .init_characters import initialize_characters # Wenn es im gleichen Ordner ist
    # Wenn es in app/admin/init_characters.py liegt und admin_bp von app importiert wird:
    from app.admin.init_characters import initialize_characters
    
    try:
        initialize_characters() 
        flash("Charaktere initialisiert/überprüft.", "info")
    except Exception as e:
        current_app.logger.error(f"Fehler bei der Charakterinitialisierung: {e}", exc_info=True)
        flash("Fehler bei der Charakterinitialisierung.", "danger")
    return redirect(url_for('admin.admin_dashboard'))

