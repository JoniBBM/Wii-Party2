# app/admin/routes.py
import sys
import os
import random
import json
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, g, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from ..models import Admin, Team, Character, GameSession, GameEvent, MinigameFolder, GameRound, QuestionResponse, db
from ..forms import (AdminLoginForm, CreateTeamForm, EditTeamForm, SetNextMinigameForm, 
                     AdminConfirmPasswordForm, CreateMinigameFolderForm, EditMinigameFolderForm,
                     CreateGameRoundForm, EditGameRoundForm, FolderMinigameForm, EditFolderMinigameForm,
                     DeleteConfirmationForm, CreateQuestionForm, EditQuestionForm)
from .init_characters import initialize_characters
from .minigame_utils import (ensure_minigame_folders_exist, create_minigame_folder_if_not_exists,
                            delete_minigame_folder, get_minigames_from_folder, add_minigame_to_folder,
                            update_minigame_in_folder, delete_minigame_from_folder, get_minigame_from_folder,
                            get_random_minigame_from_folder, list_available_folders, update_folder_info,
                            get_questions_from_folder, add_question_to_folder, get_question_from_folder,
                            get_all_content_from_folder, get_random_content_from_folder)

admin_bp = Blueprint('admin', __name__, template_folder='../templates/admin', url_prefix='/admin')

def get_or_create_active_session():
    active_session = GameSession.query.filter_by(is_active=True).first()
    if not active_session:
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
        placement += 1

    # Dann die falschen Antworten (bekommen keinen Bonus-Würfel)
    for response in incorrect_responses:
        response.team.minigame_placement = placement
        placement += 1

    # Teams die nicht geantwortet haben bekommen letzte Plätze
    all_teams = Team.query.all()
    answered_team_ids = {r.team_id for r in responses}
    
    for team in all_teams:
        if team.id not in answered_team_ids:
            team.minigame_placement = placement
            placement += 1

    # Setze Bonus-Würfel für Teams mit richtigen Antworten
    bonus_config = current_app.config.get('PLACEMENT_BONUS_DICE', {1: 6, 2: 4, 3: 2})
    for team in all_teams:
        if team.minigame_placement and team.minigame_placement in bonus_config:
            # Nur wenn die Antwort richtig war
            team_response = next((r for r in correct_responses if r.team_id == team.id), None)
            if team_response:
                team.bonus_dice_sides = bonus_config[team.minigame_placement]
            else:
                team.bonus_dice_sides = 0
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
        
        for mg in content['games']:
            choices.append((mg['id'], f"🎮 {mg['name']}"))
        
        for question in content['questions']:
            choices.append((question['id'], f"❓ {question['name']}"))
            
        set_minigame_form.selected_folder_minigame_id.choices = choices
    
    confirm_reset_form = AdminConfirmPasswordForm()

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
    active_round = GameRound.get_active_round()
    if active_round and active_round.minigame_folder:
        content = get_all_content_from_folder(active_round.minigame_folder.folder_path)
        choices = [('', '-- Wähle aus Ordner --')]
        
        for mg in content['games']:
            choices.append((mg['id'], f"🎮 {mg['name']}"))
        
        for question in content['questions']:
            choices.append((question['id'], f"❓ {question['name']}"))
            
        form.selected_folder_minigame_id.choices = choices

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
            # Zufällig aus Ordner
            if active_round and active_round.minigame_folder:
                random_content = get_random_content_from_folder(active_round.minigame_folder.folder_path)
                if random_content:
                    active_session.current_minigame_name = random_content['name']
                    active_session.current_minigame_description = random_content.get('description', '')
                    active_session.selected_folder_minigame_id = random_content['id']
                    active_session.minigame_source = 'folder_random'
                    
                    if random_content.get('type') == 'question':
                        active_session.current_question_id = random_content['id']
                        flash(f"Zufällige Frage '{random_content['name']}' aus Ordner '{active_round.minigame_folder.name}' ausgewählt.", 'info')
                    else:
                        active_session.current_question_id = None
                        flash(f"Zufälliges Minispiel '{random_content['name']}' aus Ordner '{active_round.minigame_folder.name}' ausgewählt.", 'info')
                    
                    minigame_set = True
                else:
                    flash(f"Keine Inhalte im Ordner '{active_round.minigame_folder.name}' gefunden.", 'warning')
            else:
                flash('Keine aktive Runde oder Minigame-Ordner zugewiesen.', 'warning')

        elif minigame_source == 'folder_selected':
            # Aus Ordner auswählen
            selected_id = form.selected_folder_minigame_id.data
            if selected_id and active_round and active_round.minigame_folder:
                selected_content = get_minigame_from_folder(active_round.minigame_folder.folder_path, selected_id)
                
                if selected_content:
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
            # Setze Spielphase und reset Team-Platzierungen
            if active_session.current_question_id:
                active_session.current_phase = 'QUESTION_ACTIVE'
            else:
                active_session.current_phase = 'MINIGAME_ANNOUNCED'
            
            teams_to_reset = Team.query.all()
            for t in teams_to_reset:
                t.minigame_placement = None

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

        bonus_config = current_app.config.get('PLACEMENT_BONUS_DICE', {1: 6, 2: 4, 3: 2})
        team_obj.bonus_dice_sides = bonus_config.get(placement, 0)
        
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

                db.session.commit()
                flash('Spiel komplett zurückgesetzt (inkl. Positionen, Events, Fragen-Antworten, Session). Eine neue Session wird beim nächsten Aufruf gestartet.', 'success')
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

# REST OF THE ROUTES (Folder and Round management) - keeping them as they are for brevity
# [Include all other routes from the original file - create_team, edit_team, delete_team, manage_folders, etc.]

# EXISTING TEAM MANAGEMENT ROUTES
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

# Include all other folder and round management routes here (keeping them unchanged for brevity)
# manage_folders, create_folder, edit_folder, delete_folder, etc.
# manage_rounds, create_round, edit_round, delete_round, etc.