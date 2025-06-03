# app/admin/routes.py
import sys
import os
import random
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, g, jsonify
from flask_login import login_user, logout_user, login_required, current_user
# Korrigierte Importe basierend auf der Nutzung und der ursprünglichen Datei des Benutzers:
from ..models import Admin, Team, Minigame, Character, GameSession, GameEvent, MinigameFolder, GameRound, db
from ..forms import (AdminLoginForm, CreateTeamForm, EditTeamForm, MinigameForm, SetNextMinigameForm, 
                     AdminConfirmPasswordForm, CreateMinigameFolderForm, EditMinigameFolderForm,
                     CreateGameRoundForm, EditGameRoundForm, FolderMinigameForm, EditFolderMinigameForm,
                     DeleteConfirmationForm)
# Importiere init_characters, wenn es verwendet wird (z.B. in init_chars Route)
from .init_characters import initialize_characters
from .minigame_utils import (ensure_minigame_folders_exist, create_minigame_folder_if_not_exists,
                            delete_minigame_folder, get_minigames_from_folder, add_minigame_to_folder,
                            update_minigame_in_folder, delete_minigame_from_folder, get_minigame_from_folder,
                            get_random_minigame_from_folder, list_available_folders, update_folder_info)

admin_bp = Blueprint('admin', __name__, template_folder='../templates/admin', url_prefix='/admin')

# Hilfsfunktion, um die aktive oder eine neue GameSession zu bekommen
def get_or_create_active_session():
    active_session = GameSession.query.filter_by(is_active=True).first()
    if not active_session:
        # Hole die aktive GameRound
        active_round = GameRound.get_active_round()
        
        active_session = GameSession(
            is_active=True, 
            current_phase='SETUP_MINIGAME',
            game_round_id=active_round.id if active_round else None
        )
        db.session.add(active_session)
        db.session.flush() 

        event = GameEvent(
            game_session_id=active_session.id,
            event_type="game_session_started",
            description=f"Neue Spielsitzung gestartet{f' für Runde {active_round.name}' if active_round else ''}."
        )
        db.session.add(event)
        db.session.commit() 
    return active_session

@admin_bp.route('/', methods=['GET', 'POST']) # POST für das Reset-Formular
@login_required
def admin_dashboard():
    if not isinstance(current_user, Admin):
        flash('Zugriff verweigert. Nur Admins können das Admin Dashboard sehen.', 'danger')
        return redirect(url_for('main.index')) # Annahme: 'main.index' ist die Hauptseite

    active_session = get_or_create_active_session()
    teams = Team.query.order_by(Team.name).all()
    minigames_db = Minigame.query.all()

    # Hole aktuelle Runde und verfügbare Ordner
    active_round = GameRound.get_active_round()
    available_folders = MinigameFolder.query.order_by(MinigameFolder.name).all()
    available_rounds = GameRound.query.order_by(GameRound.name).all()

    set_minigame_form = SetNextMinigameForm()
    set_minigame_form.selected_minigame_id.choices = [(0, '-- Manuelle Eingabe verwenden --')] + \
                                                     [(mg.id, mg.name) for mg in minigames_db]
    
    # Befülle Ordner-Minigames falls aktive Runde vorhanden
    if active_round and active_round.minigame_folder:
        folder_minigames = get_minigames_from_folder(active_round.minigame_folder.folder_path)
        set_minigame_form.selected_folder_minigame_id.choices = [('', '-- Wähle aus Ordner --')] + \
                                                                [(mg['id'], mg['name']) for mg in folder_minigames]
    
    confirm_reset_form = AdminConfirmPasswordForm() # Formular für Passwortbestätigung

    template_data = {
        "teams": teams,
        "minigames_db": minigames_db,
        "active_session": active_session,
        "active_round": active_round,
        "available_folders": available_folders,
        "available_rounds": available_rounds,
        "current_minigame_name": active_session.current_minigame_name,
        "current_minigame_description": active_session.current_minigame_description,
        "current_phase": active_session.current_phase,
        "set_minigame_form": set_minigame_form,
        "confirm_reset_form": confirm_reset_form 
    }
    
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
        
        max_field_index = current_app.config.get('MAX_BOARD_FIELDS', 72) 
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
        if not dice_order_ids_str: 
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

        next_team_name = None 
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
            
            round_over_event = GameEvent(
                game_session_id=active_session.id,
                event_type="dice_round_finished",
                description="Admin beendete die Würfelrunde. Alle Teams haben gewürfelt."
            )
            db.session.add(round_over_event)

        db.session.commit()

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
            "next_team_name": next_team_name, 
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
    
    # Dynamische Befüllung der Form-Choices
    minigames_db = Minigame.query.all()
    form.selected_minigame_id.choices = [(0, '-- Manuelle Eingabe verwenden --')] + \
                                         [(mg.id, mg.name) for mg in minigames_db]

    # Befülle Ordner-Minigames
    active_round = GameRound.get_active_round()
    if active_round and active_round.minigame_folder:
        folder_minigames = get_minigames_from_folder(active_round.minigame_folder.folder_path)
        form.selected_folder_minigame_id.choices = [('', '-- Wähle aus Ordner --')] + \
                                                    [(mg['id'], mg['name']) for mg in folder_minigames]

    if not form.validate_on_submit():
        flash('Formular-Validierung fehlgeschlagen.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    minigame_source = form.minigame_source.data
    minigame_set = False

    try:
        if minigame_source == 'manual':
            # Manuelle Eingabe
            manual_name = form.minigame_name.data
            manual_description = form.minigame_description.data
            
            if manual_name and manual_description:
                active_session.current_minigame_name = manual_name
                active_session.current_minigame_description = manual_description
                active_session.selected_minigame_id = None
                active_session.selected_folder_minigame_id = None
                active_session.minigame_source = 'manual'
                flash(f"Minispiel '{manual_name}' manuell gesetzt.", 'info')
                minigame_set = True
            else:
                flash('Bitte Name und Beschreibung für das manuelle Minispiel angeben.', 'warning')

        elif minigame_source == 'database':
            # Aus Datenbank-Bibliothek
            selected_id = form.selected_minigame_id.data
            if selected_id and selected_id != 0:
                minigame_from_db = Minigame.query.get(selected_id)
                if minigame_from_db:
                    active_session.current_minigame_name = minigame_from_db.name
                    active_session.current_minigame_description = minigame_from_db.description
                    active_session.selected_minigame_id = minigame_from_db.id
                    active_session.selected_folder_minigame_id = None
                    active_session.minigame_source = 'database'
                    flash(f"Minispiel '{minigame_from_db.name}' aus Datenbank-Bibliothek ausgewählt.", 'info')
                    minigame_set = True
                else:
                    flash('Ausgewähltes Minispiel nicht gefunden.', 'warning')
            else:
                flash('Bitte ein Minispiel aus der Datenbank-Bibliothek auswählen.', 'warning')

        elif minigame_source == 'folder_random':
            # Zufällig aus Ordner
            if active_round and active_round.minigame_folder:
                random_minigame = get_random_minigame_from_folder(active_round.minigame_folder.folder_path)
                if random_minigame:
                    active_session.current_minigame_name = random_minigame['name']
                    active_session.current_minigame_description = random_minigame.get('description', '')
                    active_session.selected_minigame_id = None
                    active_session.selected_folder_minigame_id = random_minigame['id']
                    active_session.minigame_source = 'folder_random'
                    flash(f"Zufälliges Minispiel '{random_minigame['name']}' aus Ordner '{active_round.minigame_folder.name}' ausgewählt.", 'info')
                    minigame_set = True
                else:
                    flash(f"Keine Minispiele im Ordner '{active_round.minigame_folder.name}' gefunden.", 'warning')
            else:
                flash('Keine aktive Runde oder Minigame-Ordner zugewiesen.', 'warning')

        elif minigame_source == 'folder_selected':
            # Aus Ordner auswählen
            selected_folder_id = form.selected_folder_minigame_id.data
            if selected_folder_id and active_round and active_round.minigame_folder:
                selected_minigame = get_minigame_from_folder(active_round.minigame_folder.folder_path, selected_folder_id)
                if selected_minigame:
                    active_session.current_minigame_name = selected_minigame['name']
                    active_session.current_minigame_description = selected_minigame.get('description', '')
                    active_session.selected_minigame_id = None
                    active_session.selected_folder_minigame_id = selected_minigame['id']
                    active_session.minigame_source = 'folder_selected'
                    flash(f"Minispiel '{selected_minigame['name']}' aus Ordner ausgewählt.", 'info')
                    minigame_set = True
                else:
                    flash('Ausgewähltes Minispiel nicht im Ordner gefunden.', 'warning')
            else:
                flash('Bitte ein Minispiel aus dem Ordner auswählen.', 'warning')

        if minigame_set:
            # Setze Spielphase und reset Team-Platzierungen
            active_session.current_phase = 'MINIGAME_ANNOUNCED'
            teams_to_reset = Team.query.all()
            for t in teams_to_reset:
                t.minigame_placement = None

            event = GameEvent(
                game_session_id=active_session.id,
                event_type="minigame_set",
                description=f"Minispiel '{active_session.current_minigame_name}' wurde festgelegt (Quelle: {minigame_source}). Platzierungen zurückgesetzt.",
                related_minigame_id=active_session.selected_minigame_id,
                data_json=f'{{"name": "{active_session.current_minigame_name}", "description": "{active_session.current_minigame_description}", "source": "{minigame_source}"}}'
            )
            db.session.add(event)
            db.session.commit()

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Setzen des Minispiels: {e}", exc_info=True)
        flash('Ein Fehler ist beim Setzen des Minispiels aufgetreten.', 'danger')

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
    for team_obj_iter in teams: 
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

        bonus_config = current_app.config.get('PLACEMENT_BONUS_DICE', {1: 6, 2: 4, 3: 2})
        team_obj.bonus_dice_sides = bonus_config.get(placement, 0)
        
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
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/reset_game_state_confirmed', methods=['POST']) 
@login_required
def reset_game_state_confirmed():
    if not isinstance(current_user, Admin):
        flash('Aktion nicht erlaubt.', 'danger')
        return redirect(url_for('main.index')) 

    form = AdminConfirmPasswordForm(request.form)
    admin_user = Admin.query.get(current_user.id) 

    if form.validate_on_submit():
        if admin_user and admin_user.check_password(form.password.data):
            try:
                GameEvent.query.delete() 
                GameSession.query.delete() 

                teams = Team.query.all()
                for team in teams:
                    team.minigame_placement = None
                    team.bonus_dice_sides = 0
                    team.current_position = 0  

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
        flash('Passworteingabe für Reset ungültig oder fehlend.', 'warning')

    return redirect(url_for('admin.admin_dashboard'))

# NEUE ROUTEN FÜR MINIGAME-ORDNER MANAGEMENT

@admin_bp.route('/folders')
@login_required
def manage_folders():
    """Übersichtsseite für alle Minigame-Ordner"""
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    ensure_minigame_folders_exist()  # Stelle sicher, dass Struktur existiert
    folders = MinigameFolder.query.order_by(MinigameFolder.name).all()
    
    return render_template('admin/manage_folders.html', folders=folders)

@admin_bp.route('/folders/create', methods=['GET', 'POST'])
@login_required
def create_folder():
    """Erstelle einen neuen Minigame-Ordner"""
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    form = CreateMinigameFolderForm()
    
    if form.validate_on_submit():
        folder_name = form.name.data.strip()
        description = form.description.data.strip() if form.description.data else ""
        
        # Erstelle Ordner-Struktur
        if create_minigame_folder_if_not_exists(folder_name, description):
            # Erstelle DB-Eintrag
            new_folder = MinigameFolder(
                name=folder_name,
                description=description,
                folder_path=folder_name
            )
            db.session.add(new_folder)
            db.session.commit()
            
            flash(f'Minigame-Ordner "{folder_name}" erfolgreich erstellt.', 'success')
            return redirect(url_for('admin.manage_folders'))
        else:
            flash('Fehler beim Erstellen des Ordners. Möglicherweise existiert er bereits.', 'danger')
    
    return render_template('admin/create_folder.html', form=form)

@admin_bp.route('/folders/<int:folder_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_folder(folder_id):
    """Bearbeite einen Minigame-Ordner"""
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folder = MinigameFolder.query.get_or_404(folder_id)
    form = EditMinigameFolderForm(original_folder_name=folder.name, obj=folder)
    
    if form.validate_on_submit():
        # Aktualisiere nur Beschreibung (Name-Änderung ist komplizierter wegen File-System)
        if form.description.data != folder.description:
            folder.description = form.description.data
            update_folder_info(folder.folder_path, form.description.data)
            db.session.commit()
            flash(f'Ordner "{folder.name}" erfolgreich aktualisiert.', 'success')
            return redirect(url_for('admin.manage_folders'))
    
    # Lade Minispiele für Anzeige
    minigames = get_minigames_from_folder(folder.folder_path)
    
    return render_template('admin/edit_folder.html', form=form, folder=folder, minigames=minigames)

@admin_bp.route('/folders/<int:folder_id>/delete', methods=['GET', 'POST'])
@login_required
def delete_folder(folder_id):
    """Lösche einen Minigame-Ordner"""
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folder = MinigameFolder.query.get_or_404(folder_id)
    
    # Verhindere Löschen des Default-Ordners
    default_folder_name = current_app.config.get('DEFAULT_MINIGAME_FOLDER', 'Default')
    if folder.name == default_folder_name:
        flash(f'Der Standard-Ordner "{default_folder_name}" kann nicht gelöscht werden.', 'warning')
        return redirect(url_for('admin.manage_folders'))
    
    form = DeleteConfirmationForm()
    
    if form.validate_on_submit() and form.confirm.data:
        try:
            # Prüfe ob Ordner von aktiven Runden verwendet wird
            using_rounds = GameRound.query.filter_by(minigame_folder_id=folder.id).all()
            if using_rounds:
                round_names = ', '.join([r.name for r in using_rounds])
                flash(f'Ordner kann nicht gelöscht werden. Wird von folgenden Runden verwendet: {round_names}', 'warning')
                return redirect(url_for('admin.manage_folders'))
            
            # Lösche Dateisystem-Ordner
            if delete_minigame_folder(folder.folder_path):
                # Lösche DB-Eintrag
                db.session.delete(folder)
                db.session.commit()
                flash(f'Ordner "{folder.name}" erfolgreich gelöscht.', 'success')
            else:
                flash('Fehler beim Löschen des Ordners.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Löschen: {str(e)}', 'danger')
        
        return redirect(url_for('admin.manage_folders'))
    
    minigames = get_minigames_from_folder(folder.folder_path)
    using_rounds = GameRound.query.filter_by(minigame_folder_id=folder.id).all()
    
    return render_template('admin/delete_folder.html', form=form, folder=folder, 
                         minigames=minigames, using_rounds=using_rounds)

@admin_bp.route('/folders/<int:folder_id>/minigames/create', methods=['GET', 'POST'])
@login_required
def create_folder_minigame(folder_id):
    """Erstelle ein neues Minispiel in einem Ordner"""
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folder = MinigameFolder.query.get_or_404(folder_id)
    form = FolderMinigameForm()
    
    if form.validate_on_submit():
        minigame_data = {
            'name': form.name.data,
            'description': form.description.data,
            'type': form.type.data
        }
        
        if add_minigame_to_folder(folder.folder_path, minigame_data):
            flash(f'Minispiel "{form.name.data}" erfolgreich erstellt.', 'success')
            return redirect(url_for('admin.edit_folder', folder_id=folder.id))
        else:
            flash('Fehler beim Erstellen des Minispiels.', 'danger')
    
    return render_template('admin/create_folder_minigame.html', form=form, folder=folder)

@admin_bp.route('/folders/<int:folder_id>/minigames/<minigame_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_folder_minigame(folder_id, minigame_id):
    """Bearbeite ein Minispiel in einem Ordner"""
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folder = MinigameFolder.query.get_or_404(folder_id)
    minigame = get_minigame_from_folder(folder.folder_path, minigame_id)
    
    if not minigame:
        flash('Minispiel nicht gefunden.', 'danger')
        return redirect(url_for('admin.edit_folder', folder_id=folder.id))
    
    form = EditFolderMinigameForm(obj=type('obj', (object,), minigame)())
    
    if form.validate_on_submit():
        updated_data = {
            'name': form.name.data,
            'description': form.description.data,
            'type': form.type.data
        }
        
        if update_minigame_in_folder(folder.folder_path, minigame_id, updated_data):
            flash(f'Minispiel "{form.name.data}" erfolgreich aktualisiert.', 'success')
            return redirect(url_for('admin.edit_folder', folder_id=folder.id))
        else:
            flash('Fehler beim Aktualisieren des Minispiels.', 'danger')
    
    return render_template('admin/edit_folder_minigame.html', form=form, folder=folder, minigame=minigame)

@admin_bp.route('/folders/<int:folder_id>/minigames/<minigame_id>/delete', methods=['POST'])
@login_required
def delete_folder_minigame(folder_id, minigame_id):
    """Lösche ein Minispiel aus einem Ordner"""
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folder = MinigameFolder.query.get_or_404(folder_id)
    
    if delete_minigame_from_folder(folder.folder_path, minigame_id):
        flash('Minispiel erfolgreich gelöscht.', 'success')
    else:
        flash('Fehler beim Löschen des Minispiels.', 'danger')
    
    return redirect(url_for('admin.edit_folder', folder_id=folder.id))

# NEUE ROUTEN FÜR SPIELRUNDEN MANAGEMENT

@admin_bp.route('/rounds')
@login_required
def manage_rounds():
    """Übersichtsseite für alle Spielrunden"""
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    rounds = GameRound.query.order_by(GameRound.name).all()
    active_round = GameRound.get_active_round()
    
    return render_template('admin/manage_rounds.html', rounds=rounds, active_round=active_round)

@admin_bp.route('/rounds/create', methods=['GET', 'POST'])
@login_required
def create_round():
    """Erstelle eine neue Spielrunde"""
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    form = CreateGameRoundForm()
    
    if form.validate_on_submit():
        new_round = GameRound(
            name=form.name.data,
            description=form.description.data,
            minigame_folder_id=form.minigame_folder_id.data,
            is_active=False  # Wird später aktiviert
        )
        db.session.add(new_round)
        db.session.commit()
        
        flash(f'Spielrunde "{form.name.data}" erfolgreich erstellt.', 'success')
        return redirect(url_for('admin.manage_rounds'))
    
    return render_template('admin/create_round.html', form=form)

@admin_bp.route('/rounds/<int:round_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_round(round_id):
    """Bearbeite eine Spielrunde"""
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    round_obj = GameRound.query.get_or_404(round_id)
    form = EditGameRoundForm(original_round_name=round_obj.name, obj=round_obj)
    
    if form.validate_on_submit():
        round_obj.name = form.name.data
        round_obj.description = form.description.data
        round_obj.minigame_folder_id = form.minigame_folder_id.data
        db.session.commit()
        
        flash(f'Spielrunde "{form.name.data}" erfolgreich aktualisiert.', 'success')
        return redirect(url_for('admin.manage_rounds'))
    
    return render_template('admin/edit_round.html', form=form, round=round_obj)

@admin_bp.route('/rounds/<int:round_id>/activate', methods=['POST'])
@login_required
def activate_round(round_id):
    """Aktiviere eine Spielrunde"""
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    round_obj = GameRound.query.get_or_404(round_id)
    round_obj.activate()  # Verwendet die Model-Methode
    
    flash(f'Spielrunde "{round_obj.name}" ist jetzt aktiv.', 'success')
    return redirect(url_for('admin.manage_rounds'))

@admin_bp.route('/rounds/<int:round_id>/delete', methods=['GET', 'POST'])
@login_required
def delete_round(round_id):
    """Lösche eine Spielrunde"""
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    round_obj = GameRound.query.get_or_404(round_id)
    
    # Verhindere Löschen der aktiven Runde falls es die einzige ist
    if round_obj.is_active and GameRound.query.count() == 1:
        flash('Die letzte Spielrunde kann nicht gelöscht werden.', 'warning')
        return redirect(url_for('admin.manage_rounds'))
    
    form = DeleteConfirmationForm()
    
    if form.validate_on_submit() and form.confirm.data:
        try:
            # Wenn aktive Runde gelöscht wird, aktiviere eine andere
            if round_obj.is_active:
                other_round = GameRound.query.filter(GameRound.id != round_obj.id).first()
                if other_round:
                    other_round.is_active = True
            
            # Aktualisiere GameSessions die diese Runde referenzieren
            GameSession.query.filter_by(game_round_id=round_obj.id).update({'game_round_id': None})
            
            db.session.delete(round_obj)
            db.session.commit()
            
            flash(f'Spielrunde "{round_obj.name}" erfolgreich gelöscht.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Löschen: {str(e)}', 'danger')
        
        return redirect(url_for('admin.manage_rounds'))
    
    return render_template('admin/delete_round.html', form=form, round=round_obj)

# BESTEHENDE ROUTEN (Team & Minigame Management) - Unverändert

@admin_bp.route('/create_team', methods=['GET', 'POST'])
@login_required
def create_team():
    if not isinstance(current_user, Admin): return redirect(url_for('main.index')) 
    form = CreateTeamForm() # Nutzt Character Choices aus Form __init__

    if form.validate_on_submit():
        existing_team = Team.query.filter_by(name=form.team_name.data).first()
        if existing_team:
            flash('Ein Team mit diesem Namen existiert bereits.', 'warning')
        else:
            team = Team(name=form.team_name.data)
            team.set_password(form.password.data) 
            
            selected_character_id = form.character_id.data
            # Da character_id ein Pflichtfeld im Formular ist (Required()),
            # können wir davon ausgehen, dass es hier einen Wert hat.
            char = Character.query.get(selected_character_id) 
            if char:
                if char.is_selected: # Diese Prüfung ist wichtig
                    flash(f'Charakter {char.name} ist bereits ausgewählt. Bitte einen anderen wählen.', 'warning')
                    # Formular erneut anzeigen, damit der Benutzer korrigieren kann
                    return render_template('create_team.html', title='Team erstellen', form=form)
                
                team.character_id = char.id
                # Stelle sicher, dass das Team-Modell ein Feld 'character_name' hat, wenn du es hier setzt.
                # Alternativ kann der Name über die Beziehung team.character.name abgerufen werden.
                team.character_name = char.name 
                char.is_selected = True 
                db.session.add(char)
            # Kein else für "char nicht gefunden", da SelectField normalerweise gültige IDs liefert.
            
            db.session.add(team)
            db.session.commit()
            flash('Team erfolgreich erstellt.', 'success')
            return redirect(url_for('admin.admin_dashboard'))
    else:
        # Fehler ausgeben, falls die Formularvalidierung fehlschlägt (z.B. Passwort zu kurz)
        if request.method == 'POST': # Nur bei fehlgeschlagenem POST die Fehler anzeigen
            for fieldName, errorMessages in form.errors.items():
                for err in errorMessages:
                    # Versuch, das Label des Feldes zu bekommen, falls vorhanden
                    field_label = fieldName
                    try:
                        field_label = getattr(form, fieldName).label.text
                    except AttributeError:
                        pass # Feld hat kein Label-Attribut oder .text
                    flash(f"Fehler im Feld '{field_label}': {err}", 'danger')

    return render_template('create_team.html', title='Team erstellen', form=form)

@admin_bp.route('/edit_team/<int:team_id>', methods=['GET', 'POST'])
@login_required
def edit_team(team_id):
    if not isinstance(current_user, Admin): return redirect(url_for('main.index')) 
    team = Team.query.get_or_404(team_id)
    
    # current_char_id_for_form wird an EditTeamForm übergeben, um die Logik
    # für die Charakterauswahl im Formular zu unterstützen.
    current_char_id_for_form = team.character_id if team.character_id else 0 
                                                                          # (oder None, je nachdem was das Formular erwartet)
    
    # Bei POST-Request werden die Daten aus request.form genommen,
    # bei GET aus dem obj=team (falls vorhanden und gewünscht)
    form = EditTeamForm(original_team_name=team.name, current_character_id=current_char_id_for_form, obj=team if request.method == 'GET' else None)

    if form.validate_on_submit():
        # Name-Validierung: Sicherstellen, dass der neue Name nicht von einem *anderen* Team verwendet wird
        if form.team_name.data != team.name: 
            existing_team_check = Team.query.filter(Team.id != team_id, Team.name == form.team_name.data).first()
            if existing_team_check:
                flash('Ein anderes Team mit diesem Namen existiert bereits.', 'warning')
                # Wichtig: Formular erneut mit den aktuellen (fehlerhaften) Eingaben rendern,
                # nicht das leere Formular oder die alten Daten.
                return render_template('edit_team.html', title='Team bearbeiten', form=form, team=team) # team wird für Template-Infos benötigt
        
        team.name = form.team_name.data
        
        if form.password.data: # Wenn ein neues Passwort eingegeben wurde
            team.set_password(form.password.data)

        new_character_id = form.character_id.data # Dies ist die ID des neu ausgewählten Charakters
        old_character_id = team.character_id    # Dies ist die ID des alten Charakters des Teams

        if new_character_id != old_character_id:
            # Alten Charakter als nicht ausgewählt markieren, falls vorhanden
            if old_character_id:
                old_char = Character.query.get(old_character_id)
                if old_char:
                    old_char.is_selected = False
                    db.session.add(old_char)
            
            # Neuen Charakter als ausgewählt markieren und dem Team zuweisen
            if new_character_id: 
                new_char = Character.query.get(new_character_id)
                if new_char:
                    # Zusätzliche Prüfung, falls die Formularlogik umgangen wurde oder Race Condition:
                    # Der Charakter darf nicht bereits von einem *anderen* Team ausgewählt sein.
                    # Die Formularlogik sollte dies bereits handhaben, indem nur verfügbare Chars + der eigene alte Char zur Auswahl stehen.
                    if new_char.is_selected and new_char.id != old_character_id : # Diese Bedingung sollte eigentlich nie eintreten, wenn Formularlogik stimmt
                        flash(f"Charakter {new_char.name} ist bereits von einem anderen Team ausgewählt. Dies sollte nicht passieren.", "danger")
                        return render_template('edit_team.html', title='Team bearbeiten', form=form, team=team)
                    
                    team.character_id = new_char.id
                    team.character_name = new_char.name # Siehe Kommentar in create_team
                    new_char.is_selected = True
                    db.session.add(new_char)
                else: # Sollte nicht passieren, wenn character_id aus gültigen Choices kommt
                    team.character_id = None
                    team.character_name = None
            else: # "Kein Charakter" wurde explizit ausgewählt (falls das Formular das erlaubt)
                team.character_id = None
                team.character_name = None
        
        db.session.commit()
        flash('Team erfolgreich aktualisiert.', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    else:
        # Fehler ausgeben, falls die Formularvalidierung fehlschlägt (z.B. bei initialem GET oder invalid POST)
        if request.method == 'POST': # Nur bei fehlgeschlagenem POST die Fehler anzeigen
            for fieldName, errorMessages in form.errors.items():
                for err in errorMessages:
                    field_label = fieldName
                    try:
                        field_label = getattr(form, fieldName).label.text
                    except AttributeError:
                        pass
                    flash(f"Fehler im Feld '{field_label}': {err}", 'danger')
        elif request.method == 'GET':
            # Formular mit den aktuellen Daten des Teams vorbefüllen
            form.team_name.data = team.name
            form.character_id.data = team.character_id

    return render_template('edit_team.html', title='Team bearbeiten', form=form, team=team)

@admin_bp.route('/delete_team/<int:team_id>', methods=['POST'])
@login_required
def delete_team(team_id):
    if not isinstance(current_user, Admin): return redirect(url_for('main.index')) 
    team = Team.query.get_or_404(team_id)
    
    if team.character_id:
        char = Character.query.get(team.character_id)
        if char:
            char.is_selected = False
            db.session.add(char)

    GameSession.query.filter_by(current_team_turn_id=team.id).update({"current_team_turn_id": None})
    GameEvent.query.filter_by(related_team_id=team.id).update({"related_team_id": None})
    
    active_sessions = GameSession.query.filter(GameSession.dice_roll_order.like(f"%{str(team.id)}%")).all() # Wichtig: team.id zu str konvertieren für LIKE
    for sess in active_sessions:
        order_list = sess.dice_roll_order.split(',')
        # Sicherstellen, dass wir Strings vergleichen
        team_id_str = str(team.id)
        if team_id_str in order_list:
            order_list.remove(team_id_str)
            sess.dice_roll_order = ",".join(order_list)
            if not order_list and sess.current_phase == 'DICE_ROLLING': 
                sess.current_phase = 'ROUND_OVER' 
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
    minigame_to_delete = Minigame.query.get_or_404(minigame_id) 
    
    GameEvent.query.filter_by(related_minigame_id=minigame_to_delete.id).update({"related_minigame_id": None})
    
    active_sessions_with_this_minigame = GameSession.query.filter_by(selected_minigame_id=minigame_to_delete.id).all()
    for sess in active_sessions_with_this_minigame:
        sess.selected_minigame_id = None
        if sess.current_minigame_name == minigame_to_delete.name:
             sess.current_minigame_name = "N/A" 
             sess.current_minigame_description = "Minispiel wurde gelöscht."
             if sess.current_phase == 'MINIGAME_ANNOUNCED': 
                 sess.current_phase = 'SETUP_MINIGAME' 

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
    
    try:
        initialize_characters() 
        flash("Charaktere initialisiert/überprüft.", "info")
    except Exception as e:
        current_app.logger.error(f"Fehler bei der Charakterinitialisierung: {e}", exc_info=True)
        flash(f"Fehler bei der Charakterinitialisierung: {str(e)}", "danger")
    return redirect(url_for('admin.admin_dashboard'))