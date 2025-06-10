# app/admin/routes.py
import sys
import os
import random
import json
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, g, jsonify, make_response
from flask_login import login_user, logout_user, login_required, current_user
from ..models import (Admin, Team, Character, GameSession, GameEvent, MinigameFolder, GameRound, 
                     QuestionResponse, FieldConfiguration, db)
from ..forms import (AdminLoginForm, CreateTeamForm, EditTeamForm, SetNextMinigameForm, 
                     AdminConfirmPasswordForm, CreateMinigameFolderForm, EditMinigameFolderForm,
                     CreateGameRoundForm, EditGameRoundForm, FolderMinigameForm, EditFolderMinigameForm,
                     DeleteConfirmationForm, CreateQuestionForm, EditQuestionForm,
                     FieldConfigurationForm, FieldPreviewForm, FieldImportExportForm, FieldBulkEditForm)
from .init_characters import initialize_characters
from .minigame_utils import (ensure_minigame_folders_exist, create_minigame_folder_if_not_exists,
                            delete_minigame_folder, get_minigames_from_folder, add_minigame_to_folder,
                            update_minigame_in_folder, delete_minigame_from_folder, get_minigame_from_folder,
                            get_random_minigame_from_folder, list_available_folders, update_folder_info,
                            get_questions_from_folder, add_question_to_folder, get_question_from_folder,
                            get_all_content_from_folder, get_random_content_from_folder, get_played_count_for_folder,
                            get_available_content_from_folder, mark_content_as_played, reset_played_content_for_session)

# NEU: FELD-MANAGEMENT IMPORTS
from .field_config import (
    get_field_type_color_mapping, get_field_preview_data, create_default_field_config,
    update_field_config, get_frequency_type_options, get_field_type_templates,
    export_field_configurations, import_field_configurations, reset_to_default_configurations,
    validate_field_conflicts, get_field_usage_statistics
)

# SONDERFELD-LOGIK IMPORT
from app.game_logic.special_fields import (
    handle_special_field_action, 
    check_barrier_release, 
    get_field_type_at_position,
    get_all_special_field_positions,
    get_field_statistics
)

admin_bp = Blueprint('admin', __name__, template_folder='../templates/admin', url_prefix='/admin')

def get_or_create_active_session():
    active_session = GameSession.query.filter_by(is_active=True).first()
    if not active_session:
        active_round = GameRound.get_active_round()
        
        active_session = GameSession(
            is_active=True, 
            current_phase='SETUP_MINIGAME',
            game_round_id=active_round.id if active_round else None,
            played_content_ids=''  # Initialisiere mit leerem String
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

def calculate_automatic_placements():
    """Berechnet automatische Platzierungen basierend auf Antwort-Reihenfolge und Korrektheit"""
    active_session = GameSession.query.filter_by(is_active=True).first()
    if not active_session or not active_session.current_question_id:
        return

    # Alle Antworten für die aktuelle Frage
    responses = QuestionResponse.query.filter_by(
        game_session_id=active_session.id,
        question_id=active_session.current_question_id
    ).order_by(QuestionResponse.answered_at).all()

    if not responses:
        return

    # Sortiere nach Korrektheit (richtig zuerst) und dann nach Antwortzeit
    correct_responses = [r for r in responses if r.is_correct]
    incorrect_responses = [r for r in responses if not r.is_correct]

    # Setze Platzierungen
    placement = 1
    
    # Erst die richtigen Antworten in zeitlicher Reihenfolge
    for response in correct_responses:
        response.team.minigame_placement = placement
        current_app.logger.info(f"Team {response.team.name} erhält Platzierung {placement} (richtige Antwort)")
        placement += 1

    # Dann die falschen Antworten (bekommen keinen Bonus-Würfel)
    for response in incorrect_responses:
        response.team.minigame_placement = placement
        current_app.logger.info(f"Team {response.team.name} erhält Platzierung {placement} (falsche Antwort)")
        placement += 1

    # Teams die nicht geantwortet haben bekommen letzte Plätze
    all_teams = Team.query.all()
    answered_team_ids = {r.team_id for r in responses}
    
    for team in all_teams:
        if team.id not in answered_team_ids:
            team.minigame_placement = placement
            current_app.logger.info(f"Team {team.name} erhält Platzierung {placement} (keine Antwort)")
            placement += 1

    # VERBESSERT: Setze Bonus-Würfel für Teams mit richtigen Antworten
    bonus_config = current_app.config.get('PLACEMENT_BONUS_DICE', {1: 6, 2: 4, 3: 2})
    
    # Erst alle Bonus-Würfel zurücksetzen
    for team in all_teams:
        team.bonus_dice_sides = 0
    
    # Dann nur für Teams mit richtigen Antworten setzen
    correct_team_ids = {r.team_id for r in correct_responses}
    
    for team in all_teams:
        if team.minigame_placement and team.minigame_placement in bonus_config:
            # Nur wenn das Team eine richtige Antwort gegeben hat
            if team.id in correct_team_ids:
                team.bonus_dice_sides = bonus_config[team.minigame_placement]
                current_app.logger.info(f"Team {team.name} (Platz {team.minigame_placement}) erhält Bonus-Würfel: 1-{team.bonus_dice_sides}")
            else:
                team.bonus_dice_sides = 0
                current_app.logger.info(f"Team {team.name} (Platz {team.minigame_placement}) erhält keinen Bonus-Würfel (falsche/keine Antwort)")
        else:
            team.bonus_dice_sides = 0

    db.session.commit()

@admin_bp.route('/', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if not isinstance(current_user, Admin):
        flash('Zugriff verweigert. Nur Admins können das Admin Dashboard sehen.', 'danger')
        return redirect(url_for('main.index'))

    active_session = get_or_create_active_session()
    teams = Team.query.order_by(Team.name).all()

    active_round = GameRound.get_active_round()
    available_folders = MinigameFolder.query.order_by(MinigameFolder.name).all()
    available_rounds = GameRound.query.order_by(GameRound.name).all()

    set_minigame_form = SetNextMinigameForm()
    
    # Befülle Ordner-Inhalte falls aktive Runde vorhanden
    if active_round and active_round.minigame_folder:
        content = get_all_content_from_folder(active_round.minigame_folder.folder_path)
        choices = [('', '-- Wähle aus Ordner --')]
        
        # Markiere bereits gespielte Inhalte
        played_ids = active_session.get_played_content_ids()
        
        for mg in content['games']:
            label = f"🎮 {mg['name']}"
            if mg['id'] in played_ids:
                label += " (bereits gespielt)"
            choices.append((mg['id'], label))
        
        for question in content['questions']:
            label = f"❓ {question['name']}"
            if question['id'] in played_ids:
                label += " (bereits gespielt)"
            choices.append((question['id'], label))
            
        set_minigame_form.selected_folder_minigame_id.choices = choices
    
    confirm_reset_form = AdminConfirmPasswordForm()

    # Zusätzliche Informationen für das Dashboard
    played_stats = None
    if active_round and active_round.minigame_folder:
        played_stats = get_played_count_for_folder(
            active_round.minigame_folder.folder_path, 
            active_session.get_played_content_ids()
        )

    # NEU: Feld-Konfiguration Statistiken für Dashboard
    field_stats = get_field_statistics()
    field_color_mapping = get_field_type_color_mapping()

    template_data = {
        "teams": teams,
        "active_session": active_session,
        "active_round": active_round,
        "available_folders": available_folders,
        "available_rounds": available_rounds,
        "current_minigame_name": active_session.current_minigame_name,
        "current_minigame_description": active_session.current_minigame_description,
        "current_phase": active_session.current_phase,
        "set_minigame_form": set_minigame_form,
        "confirm_reset_form": confirm_reset_form,
        "played_stats": played_stats,
        # NEU: Feld-Management Daten
        "field_stats": field_stats,
        "field_color_mapping": field_color_mapping
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

        # SONDERFELD: Prüfe ob Team blockiert ist (Sperren-Feld)
        standard_dice_roll = random.randint(1, 6)
        bonus_dice_roll = 0
        
        current_app.logger.info(f"Team {team.name} würfelt - Bonus-Würfel-Seiten: {team.bonus_dice_sides}")
        
        if team.bonus_dice_sides and team.bonus_dice_sides > 0:
            bonus_dice_roll = random.randint(1, team.bonus_dice_sides)
            current_app.logger.info(f"Team {team.name} erhält Bonus-Würfel: {bonus_dice_roll} (von 1-{team.bonus_dice_sides})")
        else:
            current_app.logger.info(f"Team {team.name} erhält keinen Bonus-Würfel")
        
        total_roll = standard_dice_roll + bonus_dice_roll
        old_position = team.current_position
        new_position = old_position  # Default: keine Bewegung
        special_field_result = None
        barrier_check_result = None

        # SONDERFELD: Prüfe Sperren-Status
        if team.is_blocked:
            # Team ist blockiert - prüfe ob es freikommt
            barrier_check_result = check_barrier_release(team, standard_dice_roll, active_session)
            
            if barrier_check_result['released']:
                # Team ist befreit und kann sich normal bewegen
                max_field_index = current_app.config.get('MAX_BOARD_FIELDS', 72)
                new_position = min(team.current_position + total_roll, max_field_index)
                team.current_position = new_position
                
                # Prüfe Sonderfeld-Aktion nach Bewegung
                all_teams = Team.query.all()
                special_field_result = handle_special_field_action(team, all_teams, active_session)
            else:
                # Team bleibt blockiert, keine Bewegung
                new_position = old_position
        else:
            # Team ist nicht blockiert - normale Bewegung
            max_field_index = current_app.config.get('MAX_BOARD_FIELDS', 72)
            new_position = min(team.current_position + total_roll, max_field_index)
            team.current_position = new_position
            
            # SONDERFELD: Prüfe Sonderfeld-Aktion nach Bewegung
            all_teams = Team.query.all()
            special_field_result = handle_special_field_action(team, all_teams, active_session)

        # Event für den Würfelwurf erstellen
        event_description = f"Admin würfelte für Team {team.name}: {standard_dice_roll}"
        if bonus_dice_roll > 0:
            event_description += f" (Bonus: {bonus_dice_roll}, Gesamt: {total_roll})"
        
        if team.is_blocked and not barrier_check_result.get('released', False):
            event_description += f" - BLOCKIERT: Konnte sich nicht befreien."
        else:
            event_description += f" und bewegte sich von Feld {old_position} zu Feld {new_position}."
        
        dice_event = GameEvent(
            game_session_id=active_session.id,
            event_type="admin_dice_roll",
            description=event_description,
            related_team_id=team.id,
            data_json=json.dumps({
                "standard_roll": standard_dice_roll,
                "bonus_roll": bonus_dice_roll,
                "total_roll": total_roll,
                "old_position": old_position,
                "new_position": new_position,
                "rolled_by": "admin",
                "was_blocked": team.is_blocked if barrier_check_result else False,
                "barrier_released": barrier_check_result.get('released', False) if barrier_check_result else False
            })
        )
        db.session.add(dice_event)

        # Nächstes Team ermitteln
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
            
            # VERBESSERT: Nur Bonus-Würfel zurücksetzen, Platzierungen beibehalten für Statistiken
            all_teams_in_db = Team.query.all()
            for t_obj in all_teams_in_db:
                current_app.logger.info(f"Runde beendet - Bonus-Würfel für Team {t_obj.name} zurückgesetzt (war: {t_obj.bonus_dice_sides})")
                t_obj.bonus_dice_sides = 0
                # Platzierungen NICHT zurücksetzen - die bleiben für Statistiken
            
            round_over_event = GameEvent(
                game_session_id=active_session.id,
                event_type="dice_round_finished",
                description="Admin beendete die Würfelrunde. Alle Teams haben gewürfelt."
            )
            db.session.add(round_over_event)

        db.session.commit()

        # Response zusammenstellen
        response_data = {
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
        }

        # SONDERFELD: Füge Sonderfeld-Informationen hinzu
        if barrier_check_result:
            response_data["barrier_check"] = barrier_check_result
            
        if special_field_result and special_field_result.get("success"):
            response_data["special_field"] = special_field_result

        return jsonify(response_data)

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
    active_round = GameRound.get_active_round()
    if active_round and active_round.minigame_folder:
        content = get_all_content_from_folder(active_round.minigame_folder.folder_path)
        choices = [('', '-- Wähle aus Ordner --')]
        
        # Markiere bereits gespielte Inhalte
        played_ids = active_session.get_played_content_ids()
        
        for mg in content['games']:
            label = f"🎮 {mg['name']}"
            if mg['id'] in played_ids:
                label += " (bereits gespielt)"
            choices.append((mg['id'], label))
        
        for question in content['questions']:
            label = f"❓ {question['name']}"
            if question['id'] in played_ids:
                label += " (bereits gespielt)"
            choices.append((question['id'], label))
            
        form.selected_folder_minigame_id.choices = choices

    if not form.validate_on_submit():
        flash('Formular-Validierung fehlgeschlagen.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    minigame_source = form.minigame_source.data
    minigame_set = False

    try:
        if minigame_source == 'manual':
            # Manuelle Eingabe - kein Tracking nötig
            manual_name = form.minigame_name.data
            manual_description = form.minigame_description.data
            
            if manual_name and manual_description:
                active_session.current_minigame_name = manual_name
                active_session.current_minigame_description = manual_description
                active_session.selected_folder_minigame_id = None
                active_session.current_question_id = None
                active_session.minigame_source = 'manual'
                flash(f"Inhalt '{manual_name}' manuell gesetzt.", 'info')
                minigame_set = True
            else:
                flash('Bitte Name und Beschreibung für den manuellen Inhalt angeben.', 'warning')

        elif minigame_source == 'direct_question':
            # Direkte Fragen-Erstellung
            question_name = form.minigame_name.data or "Spontane Frage"
            question_text = form.question_text.data
            question_type = form.question_type.data
            
            if question_text:
                # Erstelle temporäre Frage (ohne in Ordner zu speichern)
                question_id = str(uuid.uuid4())[:8]
                
                question_data = {
                    'id': question_id,
                    'name': question_name,
                    'description': form.minigame_description.data or '',
                    'type': 'question',
                    'question_text': question_text,
                    'question_type': question_type,
                    'created_at': datetime.utcnow().isoformat()
                }
                
                if question_type == 'multiple_choice':
                    options = []
                    if form.option_1.data: options.append(form.option_1.data)
                    if form.option_2.data: options.append(form.option_2.data)
                    if form.option_3.data: options.append(form.option_3.data)
                    if form.option_4.data: options.append(form.option_4.data)
                    
                    if len(options) < 2:
                        flash('Mindestens 2 Antwortoptionen sind erforderlich.', 'warning')
                        return redirect(url_for('admin.admin_dashboard'))
                    
                    question_data['options'] = options
                    question_data['correct_option'] = form.correct_option.data
                    
                elif question_type == 'text_input':
                    if not form.correct_text.data:
                        flash('Korrekte Antwort ist bei Freitext-Fragen erforderlich.', 'warning')
                        return redirect(url_for('admin.admin_dashboard'))
                    
                    question_data['correct_text'] = form.correct_text.data
                
                # Speichere temporär in Session-Daten
                if active_round and active_round.minigame_folder:
                    add_question_to_folder(active_round.minigame_folder.folder_path, question_data)
                
                # Markiere als gespielt
                mark_content_as_played(active_session, question_id)
                
                active_session.current_minigame_name = question_name
                active_session.current_minigame_description = question_data['description']
                active_session.selected_folder_minigame_id = question_id
                active_session.current_question_id = question_id
                active_session.minigame_source = 'direct_question'
                flash(f"Direkte Frage '{question_name}' erstellt und aktiviert.", 'success')
                minigame_set = True
            else:
                flash('Bitte Fragetext eingeben.', 'warning')

        elif minigame_source == 'folder_random':
            # Zufällig aus Ordner - mit Tracking
            if active_round and active_round.minigame_folder:
                played_ids = active_session.get_played_content_ids()
                random_content = get_random_content_from_folder(
                    active_round.minigame_folder.folder_path, 
                    played_ids
                )
                
                if random_content:
                    # Markiere als gespielt
                    mark_content_as_played(active_session, random_content['id'])
                    
                    active_session.current_minigame_name = random_content['name']
                    active_session.current_minigame_description = random_content.get('description', '')
                    active_session.selected_folder_minigame_id = random_content['id']
                    active_session.minigame_source = 'folder_random'
                    
                    # Check if all content has been played
                    stats = get_played_count_for_folder(
                        active_round.minigame_folder.folder_path, 
                        active_session.get_played_content_ids()
                    )
                    
                    if random_content.get('type') == 'question':
                        active_session.current_question_id = random_content['id']
                        flash_msg = f"Zufällige Frage '{random_content['name']}' aus Ordner '{active_round.minigame_folder.name}' ausgewählt."
                    else:
                        active_session.current_question_id = None
                        flash_msg = f"Zufälliges Minispiel '{random_content['name']}' aus Ordner '{active_round.minigame_folder.name}' ausgewählt."
                    
                    if stats['remaining'] == 0:
                        flash_msg += f" Alle {stats['total']} Inhalte wurden gespielt!"
                    else:
                        flash_msg += f" ({stats['remaining']} von {stats['total']} noch verfügbar)"
                    
                    flash(flash_msg, 'info')
                    minigame_set = True
                else:
                    flash(f"Keine Inhalte im Ordner '{active_round.minigame_folder.name}' gefunden.", 'warning')
            else:
                flash('Keine aktive Runde oder Minigame-Ordner zugewiesen.', 'warning')

        elif minigame_source == 'folder_selected':
            # Aus Ordner auswählen - mit Tracking
            selected_id = form.selected_folder_minigame_id.data
            if selected_id and active_round and active_round.minigame_folder:
                selected_content = get_minigame_from_folder(active_round.minigame_folder.folder_path, selected_id)
                
                if selected_content:
                    # Markiere als gespielt
                    mark_content_as_played(active_session, selected_content['id'])
                    
                    active_session.current_minigame_name = selected_content['name']
                    active_session.current_minigame_description = selected_content.get('description', '')
                    active_session.selected_folder_minigame_id = selected_content['id']
                    active_session.minigame_source = 'folder_selected'
                    
                    if selected_content.get('type') == 'question':
                        active_session.current_question_id = selected_content['id']
                        flash(f"Frage '{selected_content['name']}' aus Ordner ausgewählt.", 'info')
                    else:
                        active_session.current_question_id = None
                        flash(f"Minispiel '{selected_content['name']}' aus Ordner ausgewählt.", 'info')
                    
                    minigame_set = True
                else:
                    flash('Ausgewählter Inhalt nicht im Ordner gefunden.', 'warning')
            else:
                flash('Bitte einen Inhalt aus dem Ordner auswählen.', 'warning')

        if minigame_set:
            # Setze Spielphase und reset Team-Platzierungen NUR bei Phasenwechsel
            if active_session.current_question_id:
                active_session.current_phase = 'QUESTION_ACTIVE'
            else:
                active_session.current_phase = 'MINIGAME_ANNOUNCED'
            
            # VERBESSERT: Nur Platzierungen zurücksetzen, nicht Bonus-Würfel (die werden erst beim Würfeln zurückgesetzt)
            teams_to_reset = Team.query.all()
            for t in teams_to_reset:
                t.minigame_placement = None
                # t.bonus_dice_sides NICHT hier zurücksetzen - das passiert erst nach dem Würfeln

            event = GameEvent(
                game_session_id=active_session.id,
                event_type="content_set",
                description=f"{'Frage' if active_session.current_question_id else 'Minispiel'} '{active_session.current_minigame_name}' wurde festgelegt (Quelle: {minigame_source}). Platzierungen zurückgesetzt.",
                data_json=f'{{"name": "{active_session.current_minigame_name}", "description": "{active_session.current_minigame_description}", "source": "{minigame_source}", "is_question": {bool(active_session.current_question_id)}}}'
            )
            db.session.add(event)
            db.session.commit()

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Setzen des Inhalts: {e}", exc_info=True)
        flash('Ein Fehler ist beim Setzen des Inhalts aufgetreten.', 'danger')

    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/end_question', methods=['POST'])
@login_required
def end_question():
    """Beendet die aktive Frage und berechnet automatische Platzierungen"""
    if not isinstance(current_user, Admin):
        flash('Aktion nicht erlaubt.', 'danger')
        return redirect(url_for('main.index'))
    
    active_session = GameSession.query.filter_by(is_active=True).first()
    if not active_session:
        flash('Keine aktive Spielsitzung gefunden.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))
    
    if active_session.current_phase != 'QUESTION_ACTIVE':
        flash('Keine aktive Frage zum Beenden gefunden.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))
    
    try:
        # Berechne automatische Platzierungen
        calculate_automatic_placements()
        
        # Wechsle zur Würfelphase
        active_session.current_phase = 'DICE_ROLLING'
        
        # Erstelle Würfelreihenfolge basierend auf Platzierungen
        teams_by_placement = Team.query.filter(Team.minigame_placement.isnot(None)).order_by(Team.minigame_placement).all()
        if teams_by_placement:
            dice_order_ids = [str(team.id) for team in teams_by_placement]
            active_session.dice_roll_order = ",".join(dice_order_ids)
            active_session.current_team_turn_id = teams_by_placement[0].id
        
        # Reset Fragen-Daten
        active_session.current_question_id = None
        
        event = GameEvent(
            game_session_id=active_session.id,
            event_type="question_auto_completed",
            description=f"Frage '{active_session.current_minigame_name}' automatisch beendet und Platzierungen berechnet. Würfelrunde beginnt."
        )
        db.session.add(event)
        db.session.commit()
        
        flash(f"Frage '{active_session.current_minigame_name}' beendet. Platzierungen automatisch berechnet.", 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Beenden der Frage: {e}", exc_info=True)
        flash('Fehler beim Beenden der Frage.', 'danger')
    
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/api/question-responses')
@login_required
def question_responses_api():
    """API zum Abrufen der aktuellen Fragen-Antworten"""
    if not isinstance(current_user, Admin):
        return jsonify({"success": False, "error": "Nur Admins können Antworten einsehen."}), 403
    
    try:
        active_session = GameSession.query.filter_by(is_active=True).first()
        if not active_session or not active_session.current_question_id:
            return jsonify({
                "success": True,
                "responses": [],
                "message": "Keine aktive Frage"
            })
        
        responses = QuestionResponse.query.filter_by(
            game_session_id=active_session.id,
            question_id=active_session.current_question_id
        ).join(Team).all()
        
        formatted_responses = []
        for response in responses:
            answer_preview = ""
            if response.selected_option is not None:
                active_round = GameRound.get_active_round()
                if active_round and active_round.minigame_folder:
                    question_data = get_question_from_folder(active_round.minigame_folder.folder_path, response.question_id)
                    if question_data and question_data.get('options'):
                        options = question_data['options']
                        if 0 <= response.selected_option < len(options):
                            answer_preview = f"Option {response.selected_option + 1}: {options[response.selected_option][:30]}..."
                        else:
                            answer_preview = f"Option {response.selected_option + 1}"
                    else:
                        answer_preview = f"Option {response.selected_option + 1}"
            elif response.answer_text:
                answer_preview = response.answer_text[:50]
                if len(response.answer_text) > 50:
                    answer_preview += "..."
            else:
                answer_preview = "Keine Antwort"
            
            formatted_responses.append({
                "team_id": response.team_id,
                "team_name": response.team.name,
                "answer_preview": answer_preview,
                "is_correct": response.is_correct,
                "answered_at": response.answered_at.strftime('%H:%M:%S') if response.answered_at else None
            })
        
        formatted_responses.sort(key=lambda x: x['answered_at'] or '99:99:99')
        
        return jsonify({
            "success": True,
            "responses": formatted_responses,
            "total_responses": len(formatted_responses),
            "total_teams": Team.query.count(),
            "question_name": active_session.current_minigame_name
        })
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Laden der Fragen-Antworten: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Fehler beim Laden der Antworten"
        }), 500

@admin_bp.route('/record_placements', methods=['POST'])
@login_required
def record_placements():
    if not isinstance(current_user, Admin):
        flash('Aktion nicht erlaubt.', 'danger')
        return redirect(url_for('main.index')) 

    active_session = GameSession.query.filter_by(is_active=True).first()
    if not active_session or active_session.current_phase not in ['MINIGAME_ANNOUNCED']:
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

        # VERBESSERT: Bonus-Würfel Logik mit Logging
        bonus_config = current_app.config.get('PLACEMENT_BONUS_DICE', {1: 6, 2: 4, 3: 2})
        bonus_dice = bonus_config.get(placement, 0)
        team_obj.bonus_dice_sides = bonus_dice
        
        current_app.logger.info(f"Manuelle Platzierung - Team {team_obj.name} (Platz {placement}) erhält Bonus-Würfel: 1-{bonus_dice}")
        
    active_session.dice_roll_order = ",".join(dice_roll_order_ids)
    active_session.current_team_turn_id = int(dice_roll_order_ids[0]) if dice_roll_order_ids else None
    active_session.current_phase = 'DICE_ROLLING'
    
    active_session.current_question_id = None
    
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
                QuestionResponse.query.delete()
                GameSession.query.delete() 

                teams = Team.query.all()
                for team in teams:
                    team.minigame_placement = None
                    team.bonus_dice_sides = 0
                    team.current_position = 0
                    # SONDERFELD: Sonderfeld-Status zurücksetzen
                    team.reset_special_field_status()

                db.session.commit()
                flash('Spiel komplett zurückgesetzt (inkl. Positionen, Events, Fragen-Antworten, Session, Sonderfeld-Status). Eine neue Session wird beim nächsten Aufruf gestartet.', 'success')
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

# Route zum Zurücksetzen der gespielten Inhalte
@admin_bp.route('/reset_played_content', methods=['POST'])
@login_required
def reset_played_content():
    if not isinstance(current_user, Admin):
        flash('Aktion nicht erlaubt.', 'danger')
        return redirect(url_for('main.index'))
    
    try:
        active_session = GameSession.query.filter_by(is_active=True).first()
        if active_session:
            reset_played_content_for_session(active_session)
            db.session.commit()
            
            event = GameEvent(
                game_session_id=active_session.id,
                event_type="played_content_reset",
                description="Admin hat die Liste der gespielten Inhalte zurückgesetzt. Alle Spiele sind wieder verfügbar."
            )
            db.session.add(event)
            db.session.commit()
            
            flash('Liste der gespielten Inhalte wurde zurückgesetzt. Alle Spiele sind wieder verfügbar.', 'success')
        else:
            flash('Keine aktive Spielsitzung gefunden.', 'warning')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Zurücksetzen der gespielten Inhalte: {e}", exc_info=True)
        flash('Fehler beim Zurücksetzen der gespielten Inhalte.', 'danger')
    
    return redirect(url_for('admin.admin_dashboard'))

# SONDERFELD: Route zum manuellen Freigeben von blockierten Teams
@admin_bp.route('/unblock_team/<int:team_id>', methods=['POST'])
@login_required
def unblock_team(team_id):
    if not isinstance(current_user, Admin):
        flash('Aktion nicht erlaubt.', 'danger')
        return redirect(url_for('main.index'))
    
    try:
        team = Team.query.get_or_404(team_id)
        active_session = GameSession.query.filter_by(is_active=True).first()
        
        if team.is_blocked:
            team.reset_special_field_status()
            
            if active_session:
                event = GameEvent(
                    game_session_id=active_session.id,
                    event_type="admin_team_unblocked",
                    description=f"Admin hat Team {team.name} manuell von der Sperre befreit.",
                    related_team_id=team.id
                )
                db.session.add(event)
            
            db.session.commit()
            flash(f'Team {team.name} wurde manuell von der Sperre befreit.', 'success')
        else:
            flash(f'Team {team.name} ist nicht blockiert.', 'info')
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Freigeben von Team {team_id}: {e}", exc_info=True)
        flash('Fehler beim Freigeben des Teams.', 'danger')
    
    return redirect(url_for('admin.admin_dashboard'))

# =============================================================================
# NEU: FELD-MANAGEMENT ROUTES
# =============================================================================

@admin_bp.route('/manage_fields')
@login_required
def manage_fields():
    """Hauptseite für Feld-Management"""
    if not isinstance(current_user, Admin):
        flash('Zugriff verweigert. Nur Admins können Felder verwalten.', 'danger')
        return redirect(url_for('main.index'))
    
    try:
        # Lade alle Feld-Konfigurationen
        field_configs = FieldConfiguration.query.order_by(FieldConfiguration.field_type).all()
        
        # Feld-Statistiken
        field_stats = get_field_statistics()
        
        # Farb-Mapping
        color_mapping = get_field_type_color_mapping()
        
        # Feld-Verteilungs-Vorschau
        preview_data = get_field_preview_data(73)
        
        # Nutzungsstatistiken
        usage_stats = get_field_usage_statistics()
        
        # Konflikte prüfen
        conflicts = validate_field_conflicts()
        
        return render_template('admin/manage_fields.html',
                             field_configs=field_configs,
                             field_stats=field_stats,
                             color_mapping=color_mapping,
                             preview_data=preview_data,
                             usage_stats=usage_stats,
                             conflicts=conflicts,
                             frequency_options=get_frequency_type_options())
                             
    except Exception as e:
        current_app.logger.error(f"Fehler beim Laden der Feld-Verwaltung: {e}", exc_info=True)
        flash('Fehler beim Laden der Feld-Verwaltung.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/edit_field/<string:field_type>', methods=['GET', 'POST'])
@login_required
def edit_field(field_type):
    """Einzelfeld-Konfiguration bearbeiten"""
    if not isinstance(current_user, Admin):
        flash('Zugriff verweigert. Nur Admins können Felder bearbeiten.', 'danger')
        return redirect(url_for('main.index'))
    
    try:
        # Lade existierende Konfiguration oder erstelle neue
        config = FieldConfiguration.get_config_for_field(field_type)
        
        if not config:
            # Erstelle neue Konfiguration mit Standard-Werten
            templates = get_field_type_templates()
            if field_type in templates:
                template = templates[field_type]
                config = create_default_field_config(field_type, template['display_name'], **template)
            else:
                config = create_default_field_config(field_type, field_type.replace('_', ' ').title())
            
            db.session.add(config)
            db.session.commit()
            flash(f"Neue Konfiguration für '{field_type}' erstellt.", 'info')
        
        form = FieldConfigurationForm(field_type=field_type, obj=config)
        
        if form.validate_on_submit():
            # Aktualisiere Konfiguration
            updated_config = update_field_config(config.id, form.data)
            
            # Cache invalidieren
            from app.game_logic.special_fields import clear_field_distribution_cache
            clear_field_distribution_cache()
            
            db.session.commit()
            flash(f"Feld-Konfiguration für '{updated_config.display_name}' erfolgreich aktualisiert.", 'success')
            return redirect(url_for('admin.manage_fields'))
        
        # Lade Template-Informationen für Frontend
        templates = get_field_type_templates()
        template_info = templates.get(field_type, {})
        
        return render_template('admin/edit_field.html',
                             form=form,
                             config=config,
                             field_type=field_type,
                             template_info=template_info,
                             frequency_options=get_frequency_type_options())
                             
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Bearbeiten von Feld '{field_type}': {e}", exc_info=True)
        flash('Fehler beim Bearbeiten der Feld-Konfiguration.', 'danger')
        return redirect(url_for('admin.manage_fields'))

@admin_bp.route('/toggle_field/<string:field_type>', methods=['POST'])
@login_required
def toggle_field(field_type):
    """Toggle einzelne Feld-Konfiguration (AJAX-Endpunkt)"""
    print(f"[DEBUG] toggle_field called with field_type: {field_type}")
    if not isinstance(current_user, Admin):
        print(f"[DEBUG] Access denied - current_user is not Admin: {current_user}")
        return jsonify({"success": False, "error": "Zugriff verweigert"}), 403
    
    try:
        current_app.logger.info(f"Toggle field request for: {field_type}")
        
        # System-Felder vor Deaktivierung schützen
        system_fields = ['start', 'goal', 'normal']
        if field_type in system_fields:
            current_app.logger.warning(f"Attempt to toggle system field: {field_type}")
            return jsonify({
                "success": False, 
                "error": f"System-Feld '{field_type}' kann nicht deaktiviert werden."
            }), 400
        
        # Feld-Konfiguration laden oder erstellen
        current_app.logger.info(f"Looking for config for field: {field_type}")
        config = FieldConfiguration.get_config_for_field(field_type)
        
        if not config:
            current_app.logger.info(f"No config found for {field_type}, creating new one")
            # Erstelle neue Konfiguration falls nicht vorhanden
            from .field_config import create_default_field_config
            
            # Generiere lesbaren Display-Namen aus field_type
            display_name = field_type.replace('_', ' ').title()
            
            config = create_default_field_config(field_type, display_name)
            if not config:
                current_app.logger.error(f"Failed to create default config for {field_type}")
                return jsonify({
                    "success": False, 
                    "error": f"Konnte Konfiguration für '{field_type}' nicht erstellen."
                }), 500
            
            # Füge neue Konfiguration zur Datenbank-Session hinzu
            db.session.add(config)
            current_app.logger.info(f"Neue Feld-Konfiguration für '{field_type}' erstellt und zur Session hinzugefügt.")
        else:
            current_app.logger.info(f"Found existing config for {field_type}: enabled={config.is_enabled}")
        
        # Status umschalten
        old_status = config.is_enabled
        config.is_enabled = not old_status
        current_app.logger.info(f"Toggling {field_type} from {old_status} to {config.is_enabled}")
        
        # Cache invalidieren
        from app.game_logic.special_fields import clear_field_distribution_cache
        clear_field_distribution_cache()
        
        # Änderungen speichern
        current_app.logger.info(f"Committing changes for {field_type}")
        db.session.commit()
        current_app.logger.info(f"Successfully committed changes for {field_type}")
        
        action = "aktiviert" if config.is_enabled else "deaktiviert"
        return jsonify({
            "success": True,
            "message": f"Feld-Konfiguration '{config.display_name}' wurde {action}.",
            "field_type": field_type,
            "is_enabled": config.is_enabled,
            "display_name": config.display_name
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Umschalten von Feld '{field_type}': {e}", exc_info=True)
        return jsonify({
            "success": False, 
            "error": f"Fehler beim Umschalten der Feld-Konfiguration: {str(e)}"
        }), 500

@admin_bp.route('/field_preview')
@login_required
def field_preview():
    """Spielfeld-Vorschau mit aktuellen Konfigurationen"""
    if not isinstance(current_user, Admin):
        return jsonify({"success": False, "error": "Zugriff verweigert"}), 403
    
    try:
        form = FieldPreviewForm()
        max_fields = int(request.args.get('max_fields', 73))
        
        # Generiere Vorschau-Daten
        preview_data = get_field_preview_data(max_fields)
        
        # Feld-Statistiken
        field_stats = get_field_statistics()
        
        # Spezielle Feld-Positionen
        special_positions = get_all_special_field_positions(max_fields)
        
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({
                "success": True,
                "preview_data": preview_data,
                "field_stats": field_stats,
                "special_positions": special_positions
            })
        
        return render_template('admin/field_preview.html',
                             form=form,
                             preview_data=preview_data,
                             field_stats=field_stats,
                             special_positions=special_positions,
                             max_fields=max_fields)
                             
    except Exception as e:
        current_app.logger.error(f"Fehler bei der Feld-Vorschau: {e}", exc_info=True)
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({"success": False, "error": str(e)}), 500
        
        flash('Fehler bei der Feld-Vorschau.', 'danger')
        return redirect(url_for('admin.manage_fields'))

@admin_bp.route('/api/field_data')
def api_field_data():
    """Öffentliche API für Feld-Daten (für Game-Board)"""
    try:
        max_fields = int(request.args.get('max_fields', 73))
        
        # Generiere Vorschau-Daten
        from .field_config import get_field_preview_data
        from app.game_logic.special_fields import get_all_special_field_positions
        preview_data = get_field_preview_data(max_fields)
        
        # Spezielle Feld-Positionen
        special_positions = get_all_special_field_positions(max_fields)
        
        return jsonify({
            "success": True,
            "preview_data": preview_data,
            "special_positions": special_positions,
            "max_fields": max_fields
        })
        
    except Exception as e:
        current_app.logger.error(f"Fehler bei der öffentlichen Feld-API: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/import_export_fields', methods=['GET', 'POST'])
@login_required
def import_export_fields():
    """Import/Export von Feld-Konfigurationen"""
    if not isinstance(current_user, Admin):
        flash('Zugriff verweigert. Nur Admins können Konfigurationen importieren/exportieren.', 'danger')
        return redirect(url_for('main.index'))
    
    form = FieldImportExportForm()
    
    if request.method == 'POST':
        if form.import_submit.data and form.validate_on_submit():
            # Import-Funktionalität
            try:
                import_data = json.loads(form.import_data.data)
                result = import_field_configurations(import_data)
                
                if result['imported_count'] > 0:
                    flash(f"Erfolgreich {result['imported_count']} Konfigurationen importiert.", 'success')
                
                if result['errors']:
                    for error in result['errors']:
                        flash(f"Import-Fehler: {error}", 'warning')
                
                return redirect(url_for('admin.manage_fields'))
                
            except json.JSONDecodeError:
                flash('Ungültiges JSON-Format.', 'danger')
            except Exception as e:
                current_app.logger.error(f"Fehler beim Import: {e}", exc_info=True)
                flash('Fehler beim Importieren der Konfigurationen.', 'danger')
        
        elif form.export_submit.data:
            # Export-Funktionalität
            try:
                export_data = export_field_configurations()
                
                if form.export_format.data == 'json':
                    response = make_response(json.dumps(export_data, indent=2))
                    response.headers['Content-Type'] = 'application/json'
                    response.headers['Content-Disposition'] = 'attachment; filename=field_configurations.json'
                    return response
                
                elif form.export_format.data == 'csv':
                    # CSV-Export implementieren
                    import csv
                    from io import StringIO
                    
                    output = StringIO()
                    writer = csv.DictWriter(output, fieldnames=export_data[0].keys() if export_data else [])
                    writer.writeheader()
                    writer.writerows(export_data)
                    
                    response = make_response(output.getvalue())
                    response.headers['Content-Type'] = 'text/csv'
                    response.headers['Content-Disposition'] = 'attachment; filename=field_configurations.csv'
                    return response
                
                else:
                    flash('Unbekanntes Export-Format.', 'warning')
                    
            except Exception as e:
                current_app.logger.error(f"Fehler beim Export: {e}", exc_info=True)
                flash('Fehler beim Exportieren der Konfigurationen.', 'danger')
        
        elif form.reset_submit.data:
            # Reset auf Standard-Konfigurationen
            try:
                if reset_to_default_configurations():
                    flash('Alle Feld-Konfigurationen wurden auf Standard-Werte zurückgesetzt.', 'success')
                else:
                    flash('Fehler beim Zurücksetzen der Konfigurationen.', 'danger')
                
                return redirect(url_for('admin.manage_fields'))
                
            except Exception as e:
                current_app.logger.error(f"Fehler beim Reset: {e}", exc_info=True)
                flash('Fehler beim Zurücksetzen der Konfigurationen.', 'danger')
    
    # Bereite Export-Daten für Vorschau vor
    export_preview = None
    try:
        export_data = export_field_configurations()
        if export_data:
            export_preview = json.dumps(export_data[:3], indent=2)  # Zeige nur ersten 3 Einträge
            if len(export_data) > 3:
                export_preview += f"\n... und {len(export_data) - 3} weitere Konfigurationen"
    except Exception:
        pass
    
    return render_template('admin/import_export_fields.html',
                         form=form,
                         export_preview=export_preview,
                         total_configs=FieldConfiguration.query.count())

@admin_bp.route('/bulk_edit_fields', methods=['GET', 'POST'])
@login_required
def bulk_edit_fields():
    """Massen-Bearbeitung von Feld-Konfigurationen"""
    if not isinstance(current_user, Admin):
        flash('Zugriff verweigert. Nur Admins können Massen-Bearbeitungen durchführen.', 'danger')
        return redirect(url_for('main.index'))
    
    form = FieldBulkEditForm()
    
    if form.validate_on_submit():
        try:
            # Frontend sendet Feld-Typen (Strings), nicht IDs
            selected_field_types = form.selected_fields.data
            selected_configs = FieldConfiguration.query.filter(FieldConfiguration.field_type.in_(selected_field_types)).all()
            
            if not selected_configs:
                flash('Keine Felder für Bearbeitung ausgewählt.', 'warning')
                return redirect(url_for('admin.bulk_edit_fields'))
            
            action = form.action.data
            modified_count = 0
            
            if action == 'enable':
                for config in selected_configs:
                    config.is_enabled = True
                    modified_count += 1
                flash(f"{modified_count} Feld-Konfigurationen wurden aktiviert.", 'success')
                
            elif action == 'disable':
                for config in selected_configs:
                    config.is_enabled = False
                    modified_count += 1
                flash(f"{modified_count} Feld-Konfigurationen wurden deaktiviert.", 'success')
                
            elif action == 'change_frequency':
                if form.new_frequency_type.data and form.new_frequency_value.data:
                    for config in selected_configs:
                        config.frequency_type = form.new_frequency_type.data
                        config.frequency_value = form.new_frequency_value.data
                        modified_count += 1
                    flash(f"Häufigkeit für {modified_count} Feld-Konfigurationen geändert.", 'success')
                else:
                    flash('Neue Häufigkeits-Werte sind erforderlich.', 'warning')
                    
            elif action == 'change_colors':
                if form.new_color_hex.data:
                    for config in selected_configs:
                        config.color_hex = form.new_color_hex.data
                        if form.new_emission_hex.data:
                            config.emission_hex = form.new_emission_hex.data
                        modified_count += 1
                    flash(f"Farben für {modified_count} Feld-Konfigurationen geändert.", 'success')
                else:
                    flash('Neue Hauptfarbe ist erforderlich.', 'warning')
                    
            elif action == 'delete':
                for config in selected_configs:
                    # Prüfe ob Feld in aktiver Nutzung
                    if config.field_type in ['start', 'goal', 'normal']:
                        flash(f"Basis-Feld '{config.field_type}' kann nicht gelöscht werden.", 'warning')
                        continue
                    db.session.delete(config)
                    modified_count += 1
                
                if modified_count > 0:
                    flash(f"{modified_count} Feld-Konfigurationen wurden gelöscht.", 'success')
            
            # Cache invalidieren wenn Änderungen gemacht wurden
            if modified_count > 0:
                from app.game_logic.special_fields import clear_field_distribution_cache
                clear_field_distribution_cache()
            
            db.session.commit()
            return redirect(url_for('admin.manage_fields'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Fehler bei Massen-Bearbeitung: {e}", exc_info=True)
            flash('Fehler bei der Massen-Bearbeitung.', 'danger')
    
    return render_template('admin/bulk_edit_fields.html', form=form)

@admin_bp.route('/api/field_colors')
@login_required
def api_field_colors():
    """API-Endpunkt für Feld-Farb-Mapping (für Frontend-Integration)"""
    if not isinstance(current_user, Admin):
        return jsonify({"success": False, "error": "Zugriff verweigert"}), 403
    
    try:
        color_mapping = get_field_type_color_mapping()
        return jsonify({
            "success": True,
            "color_mapping": color_mapping
        })
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Laden der Feld-Farben: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

# =============================================================================
# TEAM MANAGEMENT ROUTES (Bestehend)
# =============================================================================

@admin_bp.route('/create_team', methods=['GET', 'POST'])
@login_required
def create_team():
    if not isinstance(current_user, Admin): return redirect(url_for('main.index')) 
    form = CreateTeamForm()

    if form.validate_on_submit():
        existing_team = Team.query.filter_by(name=form.team_name.data).first()
        if existing_team:
            flash('Ein Team mit diesem Namen existiert bereits.', 'warning')
        else:
            team = Team(name=form.team_name.data)
            team.set_password(form.password.data) 
            
            selected_character_id = form.character_id.data
            char = Character.query.get(selected_character_id) 
            if char:
                if char.is_selected:
                    flash(f'Charakter {char.name} ist bereits ausgewählt. Bitte einen anderen wählen.', 'warning')
                    return render_template('create_team.html', title='Team erstellen', form=form)
                
                team.character_id = char.id
                team.character_name = char.name 
                char.is_selected = True 
                db.session.add(char)
            
            db.session.add(team)
            db.session.commit()
            flash('Team erfolgreich erstellt.', 'success')
            return redirect(url_for('admin.admin_dashboard'))
    else:
        if request.method == 'POST':
            for fieldName, errorMessages in form.errors.items():
                for err in errorMessages:
                    field_label = fieldName
                    try:
                        field_label = getattr(form, fieldName).label.text
                    except AttributeError:
                        pass
                    flash(f"Fehler im Feld '{field_label}': {err}", 'danger')

    return render_template('create_team.html', title='Team erstellen', form=form)

@admin_bp.route('/edit_team/<int:team_id>', methods=['GET', 'POST'])
@login_required
def edit_team(team_id):
    if not isinstance(current_user, Admin): return redirect(url_for('main.index')) 
    team = Team.query.get_or_404(team_id)
    
    current_char_id_for_form = team.character_id if team.character_id else 0 
    
    form = EditTeamForm(original_team_name=team.name, current_character_id=current_char_id_for_form, obj=team if request.method == 'GET' else None)

    if form.validate_on_submit():
        if form.team_name.data != team.name: 
            existing_team_check = Team.query.filter(Team.id != team_id, Team.name == form.team_name.data).first()
            if existing_team_check:
                flash('Ein anderes Team mit diesem Namen existiert bereits.', 'warning')
                return render_template('edit_team.html', title='Team bearbeiten', form=form, team=team)
        
        team.name = form.team_name.data
        
        if form.password.data:
            team.set_password(form.password.data)

        new_character_id = form.character_id.data
        old_character_id = team.character_id

        if new_character_id != old_character_id:
            if old_character_id:
                old_char = Character.query.get(old_character_id)
                if old_char:
                    old_char.is_selected = False
                    db.session.add(old_char)
            
            if new_character_id: 
                new_char = Character.query.get(new_character_id)
                if new_char:
                    if new_char.is_selected and new_char.id != old_character_id:
                        flash(f"Charakter {new_char.name} ist bereits von einem anderen Team ausgewählt. Dies sollte nicht passieren.", "danger")
                        return render_template('edit_team.html', title='Team bearbeiten', form=form, team=team)
                    
                    team.character_id = new_char.id
                    team.character_name = new_char.name
                    new_char.is_selected = True
                    db.session.add(new_char)
                else:
                    team.character_id = None
                    team.character_name = None
            else:
                team.character_id = None
                team.character_name = None
        
        db.session.commit()
        flash('Team erfolgreich aktualisiert.', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    else:
        if request.method == 'POST':
            for fieldName, errorMessages in form.errors.items():
                for err in errorMessages:
                    field_label = fieldName
                    try:
                        field_label = getattr(form, fieldName).label.text
                    except AttributeError:
                        pass
                    flash(f"Fehler im Feld '{field_label}': {err}", 'danger')
        elif request.method == 'GET':
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
    QuestionResponse.query.filter_by(team_id=team.id).delete()
    
    active_sessions = GameSession.query.filter(GameSession.dice_roll_order.like(f"%{str(team.id)}%")).all()
    for sess in active_sessions:
        order_list = sess.dice_roll_order.split(',')
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

# =============================================================================
# FOLDER & ROUND MANAGEMENT ROUTES (Bestehend)
# =============================================================================

@admin_bp.route('/manage_folders')
@login_required
def manage_folders():
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folders = MinigameFolder.query.order_by(MinigameFolder.name).all()
    return render_template('manage_folders.html', folders=folders)

@admin_bp.route('/create_folder', methods=['GET', 'POST'])
@login_required
def create_folder():
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    form = CreateMinigameFolderForm()
    
    if form.validate_on_submit():
        try:
            # Erstelle Ordner im Dateisystem
            if create_minigame_folder_if_not_exists(form.name.data, form.description.data):
                # Erstelle Eintrag in der Datenbank
                folder = MinigameFolder(
                    name=form.name.data,
                    description=form.description.data,
                    folder_path=form.name.data
                )
                db.session.add(folder)
                db.session.commit()
                
                flash(f"Minigame-Ordner '{form.name.data}' erfolgreich erstellt.", 'success')
                return redirect(url_for('admin.manage_folders'))
            else:
                flash('Fehler beim Erstellen des Ordners im Dateisystem.', 'danger')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Fehler beim Erstellen des Ordners: {e}", exc_info=True)
            flash('Ein Fehler ist beim Erstellen des Ordners aufgetreten.', 'danger')
    
    return render_template('create_folder.html', form=form)

@admin_bp.route('/edit_folder/<int:folder_id>')
@login_required
def edit_folder(folder_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folder = MinigameFolder.query.get_or_404(folder_id)
    
    # Lade Inhalte aus dem Ordner
    content = get_all_content_from_folder(folder.folder_path)
    games = content['games']
    questions = content['questions']
    
    form = EditMinigameFolderForm(original_folder_name=folder.name, obj=folder)
    
    if request.method == 'POST' and form.validate_on_submit():
        try:
            # Aktualisiere nur die Beschreibung (Name kann nicht geändert werden)
            folder.description = form.description.data
            
            # Aktualisiere auch die JSON-Datei
            update_folder_info(folder.folder_path, form.description.data)
            
            db.session.commit()
            flash(f"Ordner '{folder.name}' erfolgreich aktualisiert.", 'success')
            return redirect(url_for('admin.manage_folders'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Fehler beim Aktualisieren des Ordners: {e}", exc_info=True)
            flash('Ein Fehler ist beim Aktualisieren des Ordners aufgetreten.', 'danger')
    
    return render_template('edit_folder.html', form=form, folder=folder, games=games, questions=questions)

@admin_bp.route('/delete_folder/<int:folder_id>', methods=['GET', 'POST'])
@login_required
def delete_folder(folder_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folder = MinigameFolder.query.get_or_404(folder_id)
    
    # Prüfe ob Ordner von Spielrunden verwendet wird
    using_rounds = GameRound.query.filter_by(minigame_folder_id=folder.id).all()
    
    form = DeleteConfirmationForm()
    
    if using_rounds:
        # Ordner kann nicht gelöscht werden
        minigames = get_minigames_from_folder(folder.folder_path)
        return render_template('delete_folder.html', 
                             folder=folder, 
                             using_rounds=using_rounds,
                             minigames=minigames,
                             form=form)
    
    if request.method == 'POST' and form.validate_on_submit():
        try:
            # Lösche aus Dateisystem
            if delete_minigame_folder(folder.folder_path):
                # Lösche aus Datenbank
                db.session.delete(folder)
                db.session.commit()
                
                flash(f"Ordner '{folder.name}' erfolgreich gelöscht.", 'success')
                return redirect(url_for('admin.manage_folders'))
            else:
                flash('Fehler beim Löschen des Ordners aus dem Dateisystem.', 'danger')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Fehler beim Löschen des Ordners: {e}", exc_info=True)
            flash('Ein Fehler ist beim Löschen des Ordners aufgetreten.', 'danger')
    
    # Lade Minispiele für die Anzeige
    minigames = get_minigames_from_folder(folder.folder_path)
    
    return render_template('delete_folder.html', 
                         folder=folder, 
                         using_rounds=using_rounds,
                         minigames=minigames,
                         form=form)

@admin_bp.route('/create_folder_minigame/<int:folder_id>', methods=['GET', 'POST'])
@login_required
def create_folder_minigame(folder_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folder = MinigameFolder.query.get_or_404(folder_id)
    form = FolderMinigameForm()
    
    if form.validate_on_submit():
        try:
            minigame_data = {
                'name': form.name.data,
                'description': form.description.data,
                'type': form.type.data
            }
            
            if add_minigame_to_folder(folder.folder_path, minigame_data):
                flash(f"Minispiel '{form.name.data}' erfolgreich zu Ordner '{folder.name}' hinzugefügt.", 'success')
                return redirect(url_for('admin.edit_folder', folder_id=folder.id))
            else:
                flash('Fehler beim Hinzufügen des Minispiels.', 'danger')
        except Exception as e:
            current_app.logger.error(f"Fehler beim Erstellen des Minispiels: {e}", exc_info=True)
            flash('Ein Fehler ist beim Erstellen des Minispiels aufgetreten.', 'danger')
    
    return render_template('create_folder_minigame.html', form=form, folder=folder)

@admin_bp.route('/edit_folder_minigame/<int:folder_id>/<string:minigame_id>', methods=['GET', 'POST'])
@login_required
def edit_folder_minigame(folder_id, minigame_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folder = MinigameFolder.query.get_or_404(folder_id)
    minigame = get_minigame_from_folder(folder.folder_path, minigame_id)
    
    if not minigame:
        flash('Minispiel nicht gefunden.', 'danger')
        return redirect(url_for('admin.edit_folder', folder_id=folder.id))
    
    form = EditFolderMinigameForm(obj=type('obj', (object,), minigame)())
    
    if form.validate_on_submit():
        try:
            updated_data = {
                'name': form.name.data,
                'description': form.description.data,
                'type': form.type.data
            }
            
            if update_minigame_in_folder(folder.folder_path, minigame_id, updated_data):
                flash(f"Minispiel '{form.name.data}' erfolgreich aktualisiert.", 'success')
                return redirect(url_for('admin.edit_folder', folder_id=folder.id))
            else:
                flash('Fehler beim Aktualisieren des Minispiels.', 'danger')
        except Exception as e:
            current_app.logger.error(f"Fehler beim Aktualisieren des Minispiels: {e}", exc_info=True)
            flash('Ein Fehler ist beim Aktualisieren des Minispiels aufgetreten.', 'danger')
    
    return render_template('edit_folder_minigame.html', form=form, folder=folder, minigame=minigame)

@admin_bp.route('/delete_folder_minigame/<int:folder_id>/<string:minigame_id>', methods=['POST'])
@login_required
def delete_folder_minigame(folder_id, minigame_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folder = MinigameFolder.query.get_or_404(folder_id)
    
    try:
        if delete_minigame_from_folder(folder.folder_path, minigame_id):
            flash('Minispiel erfolgreich gelöscht.', 'success')
        else:
            flash('Fehler beim Löschen des Minispiels.', 'danger')
    except Exception as e:
        current_app.logger.error(f"Fehler beim Löschen des Minispiels: {e}", exc_info=True)
        flash('Ein Fehler ist beim Löschen des Minispiels aufgetreten.', 'danger')
    
    return redirect(url_for('admin.edit_folder', folder_id=folder.id))

# QUESTION MANAGEMENT ROUTES
@admin_bp.route('/create_question/<int:folder_id>', methods=['GET', 'POST'])
@login_required
def create_question(folder_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folder = MinigameFolder.query.get_or_404(folder_id)
    form = CreateQuestionForm()
    
    if form.validate_on_submit():
        try:
            question_data = {
                'name': form.name.data,
                'description': form.description.data,
                'question_text': form.question_text.data,
                'question_type': form.question_type.data,
                'type': 'question'
            }
            
            if form.question_type.data == 'multiple_choice':
                options = []
                if form.option_1.data: options.append(form.option_1.data)
                if form.option_2.data: options.append(form.option_2.data)
                if form.option_3.data: options.append(form.option_3.data)
                if form.option_4.data: options.append(form.option_4.data)
                
                if len(options) < 2:
                    flash('Mindestens 2 Antwortoptionen sind erforderlich.', 'warning')
                    return render_template('create_question.html', form=form, folder=folder)
                
                question_data['options'] = options
                question_data['correct_option'] = form.correct_option.data
                
            elif form.question_type.data == 'text_input':
                if not form.correct_text.data:
                    flash('Korrekte Antwort ist bei Freitext-Fragen erforderlich.', 'warning')
                    return render_template('create_question.html', form=form, folder=folder)
                
                question_data['correct_text'] = form.correct_text.data
            
            if add_question_to_folder(folder.folder_path, question_data):
                flash(f"Frage '{form.name.data}' erfolgreich zu Ordner '{folder.name}' hinzugefügt.", 'success')
                return redirect(url_for('admin.edit_folder', folder_id=folder.id))
            else:
                flash('Fehler beim Hinzufügen der Frage.', 'danger')
        except Exception as e:
            current_app.logger.error(f"Fehler beim Erstellen der Frage: {e}", exc_info=True)
            flash('Ein Fehler ist beim Erstellen der Frage aufgetreten.', 'danger')
    
    return render_template('create_question.html', form=form, folder=folder)

@admin_bp.route('/edit_question/<int:folder_id>/<string:question_id>', methods=['GET', 'POST'])
@login_required
def edit_question(folder_id, question_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folder = MinigameFolder.query.get_or_404(folder_id)
    question = get_question_from_folder(folder.folder_path, question_id)
    
    if not question:
        flash('Frage nicht gefunden.', 'danger')
        return redirect(url_for('admin.edit_folder', folder_id=folder.id))
    
    # Erstelle ein temporäres Objekt für das Form
    question_obj = type('obj', (object,), question)()
    form = EditQuestionForm(obj=question_obj)
    
    if form.validate_on_submit():
        try:
            updated_data = {
                'name': form.name.data,
                'description': form.description.data,
                'question_text': form.question_text.data,
                'question_type': form.question_type.data,
                'type': 'question'
            }
            
            if form.question_type.data == 'multiple_choice':
                options = []
                if form.option_1.data: options.append(form.option_1.data)
                if form.option_2.data: options.append(form.option_2.data)
                if form.option_3.data: options.append(form.option_3.data)
                if form.option_4.data: options.append(form.option_4.data)
                
                if len(options) < 2:
                    flash('Mindestens 2 Antwortoptionen sind erforderlich.', 'warning')
                    return render_template('edit_question.html', form=form, folder=folder, question=question)
                
                updated_data['options'] = options
                updated_data['correct_option'] = form.correct_option.data
                
            elif form.question_type.data == 'text_input':
                if not form.correct_text.data:
                    flash('Korrekte Antwort ist bei Freitext-Fragen erforderlich.', 'warning')
                    return render_template('edit_question.html', form=form, folder=folder, question=question)
                
                updated_data['correct_text'] = form.correct_text.data
            
            if update_minigame_in_folder(folder.folder_path, question_id, updated_data):
                flash(f"Frage '{form.name.data}' erfolgreich aktualisiert.", 'success')
                return redirect(url_for('admin.edit_folder', folder_id=folder.id))
            else:
                flash('Fehler beim Aktualisieren der Frage.', 'danger')
        except Exception as e:
            current_app.logger.error(f"Fehler beim Aktualisieren der Frage: {e}", exc_info=True)
            flash('Ein Fehler ist beim Aktualisieren der Frage aufgetreten.', 'danger')
    
    return render_template('edit_question.html', form=form, folder=folder, question=question)

@admin_bp.route('/delete_question/<int:folder_id>/<string:question_id>', methods=['POST'])
@login_required
def delete_question(folder_id, question_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folder = MinigameFolder.query.get_or_404(folder_id)
    
    try:
        if delete_minigame_from_folder(folder.folder_path, question_id):
            flash('Frage erfolgreich gelöscht.', 'success')
        else:
            flash('Fehler beim Löschen der Frage.', 'danger')
    except Exception as e:
        current_app.logger.error(f"Fehler beim Löschen der Frage: {e}", exc_info=True)
        flash('Ein Fehler ist beim Löschen der Frage aufgetreten.', 'danger')
    
    return redirect(url_for('admin.edit_folder', folder_id=folder.id))

# ROUND MANAGEMENT ROUTES
@admin_bp.route('/manage_rounds')
@login_required
def manage_rounds():
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    rounds = GameRound.query.order_by(GameRound.name).all()
    active_round = GameRound.get_active_round()
    
    return render_template('manage_rounds.html', rounds=rounds, active_round=active_round)

@admin_bp.route('/create_round', methods=['GET', 'POST'])
@login_required
def create_round():
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    form = CreateGameRoundForm()
    
    if form.validate_on_submit():
        try:
            round_obj = GameRound(
                name=form.name.data,
                description=form.description.data,
                minigame_folder_id=form.minigame_folder_id.data,
                is_active=False  # Wird nicht automatisch aktiviert
            )
            
            db.session.add(round_obj)
            db.session.commit()
            
            flash(f"Spielrunde '{form.name.data}' erfolgreich erstellt.", 'success')
            return redirect(url_for('admin.manage_rounds'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Fehler beim Erstellen der Spielrunde: {e}", exc_info=True)
            flash('Ein Fehler ist beim Erstellen der Spielrunde aufgetreten.', 'danger')
    
    return render_template('create_round.html', form=form)

@admin_bp.route('/edit_round/<int:round_id>', methods=['GET', 'POST'])
@login_required
def edit_round(round_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    round_obj = GameRound.query.get_or_404(round_id)
    form = EditGameRoundForm(original_round_name=round_obj.name, obj=round_obj)
    
    if form.validate_on_submit():
        try:
            round_obj.name = form.name.data
            round_obj.description = form.description.data
            round_obj.minigame_folder_id = form.minigame_folder_id.data
            
            db.session.commit()
            flash(f"Spielrunde '{form.name.data}' erfolgreich aktualisiert.", 'success')
            return redirect(url_for('admin.manage_rounds'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Fehler beim Aktualisieren der Spielrunde: {e}", exc_info=True)
            flash('Ein Fehler ist beim Aktualisieren der Spielrunde aufgetreten.', 'danger')
    
    return render_template('edit_round.html', form=form, round=round_obj)

@admin_bp.route('/delete_round/<int:round_id>', methods=['GET', 'POST'])
@login_required
def delete_round(round_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    round_obj = GameRound.query.get_or_404(round_id)
    form = DeleteConfirmationForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        try:
            was_active = round_obj.is_active
            
            # Aktualisiere GameSessions
            GameSession.query.filter_by(game_round_id=round_obj.id).update({'game_round_id': None})
            
            # Lösche die Runde
            db.session.delete(round_obj)
            
            # Falls es die aktive Runde war, aktiviere eine andere
            if was_active:
                other_round = GameRound.query.first()
                if other_round:
                    other_round.is_active = True
                    flash(f"Runde '{other_round.name}' wurde automatisch aktiviert.", 'info')
            
            db.session.commit()
            flash(f"Spielrunde '{round_obj.name}' erfolgreich gelöscht.", 'success')
            return redirect(url_for('admin.manage_rounds'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Fehler beim Löschen der Spielrunde: {e}", exc_info=True)
            flash('Ein Fehler ist beim Löschen der Spielrunde aufgetreten.', 'danger')
    
    return render_template('delete_round.html', form=form, round=round_obj)

@admin_bp.route('/activate_round/<int:round_id>', methods=['POST'])
@login_required
def activate_round(round_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    try:
        round_obj = GameRound.query.get_or_404(round_id)
        round_obj.activate()  # Verwendet die Model-Methode
        
        # Beim Wechseln der Runde: Gespielte Inhalte zurücksetzen
        active_session = GameSession.query.filter_by(is_active=True).first()
        if active_session:
            reset_played_content_for_session(active_session)
            
            event = GameEvent(
                game_session_id=active_session.id,
                event_type="round_activated",
                description=f"Spielrunde '{round_obj.name}' wurde aktiviert. Gespielte Inhalte wurden zurückgesetzt."
            )
            db.session.add(event)
            db.session.commit()
        
        flash(f"Spielrunde '{round_obj.name}' wurde aktiviert. Gespielte Inhalte wurden zurückgesetzt.", 'success')
    except Exception as e:
        current_app.logger.error(f"Fehler beim Aktivieren der Spielrunde: {e}", exc_info=True)
        flash('Ein Fehler ist beim Aktivieren der Spielrunde aufgetreten.', 'danger')
    
    return redirect(url_for('admin.manage_rounds'))