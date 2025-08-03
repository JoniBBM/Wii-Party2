# app/admin/routes.py
import sys
import os
import random
import json
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, g, jsonify, make_response, Response
from flask_login import login_user, logout_user, login_required, current_user
import json
import time
from ..models import (Admin, Team, Character, GameSession, GameEvent, MinigameFolder, GameRound, 
                     QuestionResponse, FieldConfiguration, WelcomeSession, PlayerRegistration, 
                     MinigameSequence, db)
from ..forms import (AdminLoginForm, CreateTeamForm, EditTeamForm, SetNextMinigameForm, 
                     AdminConfirmPasswordForm, CreateMinigameFolderForm, EditMinigameFolderForm,
                     CreateGameRoundForm, EditGameRoundForm, FolderMinigameForm, EditFolderMinigameForm,
                     DeleteConfirmationForm, CreateQuestionForm, EditQuestionForm,
                     FieldConfigurationForm, FieldPreviewForm, FieldImportExportForm, FieldBulkEditForm,
                     SequenceUpdateForm)
from .init_characters import initialize_characters
from .minigame_utils import (ensure_minigame_folders_exist, create_minigame_folder_if_not_exists,
                            delete_minigame_folder, get_minigames_from_folder, add_minigame_to_folder,
                            update_minigame_in_folder, delete_minigame_from_folder, get_minigame_from_folder,
                            get_random_minigame_from_folder, list_available_folders, update_folder_info,
                            get_questions_from_folder, add_question_to_folder, get_question_from_folder,
                            get_all_content_from_folder, get_random_content_from_folder, get_played_count_for_folder,
                            get_available_content_from_folder, mark_content_as_played, reset_played_content_for_session,
                            save_round_to_filesystem, backup_all_rounds_before_db_reset, restore_rounds_to_database,
                            load_rounds_from_filesystem, delete_round_from_filesystem)

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
    get_field_statistics,
    start_selected_field_minigame,  # NEU: Für Admin-Auswahl
    handle_field_minigame_result  # NEU: Für Ergebnis-Verarbeitung
)

admin_bp = Blueprint('admin', __name__, template_folder='../templates/admin', url_prefix='/admin')

# Simple in-memory store for field update events
field_update_events = []
MAX_EVENTS = 100  # Keep only last 100 events

def add_field_update_event(event_data):
    """Add a field update event to the queue."""
    global field_update_events
    event_data['timestamp'] = time.time()
    event_data['id'] = len(field_update_events) + 1
    field_update_events.append(event_data)
    
    # Keep only recent events
    if len(field_update_events) > MAX_EVENTS:
        field_update_events = field_update_events[-MAX_EVENTS:]

@admin_bp.route('/api/field_updates/stream')
def field_updates_stream():
    """SSE endpoint for real-time field updates."""
    def event_stream():
        last_sent_id = 0
        keepalive_counter = 0
        
        # Send initial connection confirmation
        yield f"data: {json.dumps({'type': 'connected', 'message': 'SSE verbunden', 'timestamp': time.time()})}\n\n"
        
        while True:
            # Send any new events
            new_events_sent = 0
            for event in field_update_events:
                if event['id'] > last_sent_id:
                    yield f"data: {json.dumps(event)}\n\n"
                    last_sent_id = event['id']
                    new_events_sent += 1
            
            # Send keepalive every 10 seconds (shorter for testing)
            keepalive_counter += 1
            if keepalive_counter >= 10:  # 10 * 1 second = 10 seconds
                yield f"data: {json.dumps({'type': 'keepalive', 'timestamp': time.time()})}\n\n"
                keepalive_counter = 0
            
            time.sleep(1)  # Check every second
    
    return Response(event_stream(), mimetype='text/event-stream',
                   headers={'Cache-Control': 'no-cache',
                           'Connection': 'keep-alive',
                           'Access-Control-Allow-Origin': '*'})

@admin_bp.route('/api/field_updates/poll')
def field_updates_poll():
    """Polling endpoint for field updates (fallback for SSE)."""
    last_id = request.args.get('last_id', 0, type=int)
    new_events = [event for event in field_update_events if event['id'] > last_id]
    return jsonify({
        'events': new_events,
        'last_id': field_update_events[-1]['id'] if field_update_events else 0
    })

@admin_bp.route('/api/test_field_update', methods=['POST'])
@login_required
def test_field_update():
    """Test endpoint to manually trigger a field update event."""
    if not isinstance(current_user, Admin):
        return jsonify({"success": False, "error": "Zugriff verweigert"}), 403
    
    add_field_update_event({
        'type': 'test_update',
        'field_type': 'test',
        'display_name': 'Test Update',
        'message': 'Test-Event für Live-Updates'
    })
    
    return jsonify({
        "success": True,
        "message": "Test-Event gesendet",
        "events_count": len(field_update_events)
    })

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

@admin_bp.route('/moderation_mode')
@login_required
def moderation_mode():
    """Moderationsmodus - Nur-Lese-Ansicht für Live-Überwachung"""
    if not isinstance(current_user, Admin):
        flash('Zugriff verweigert. Nur Admins können den Moderationsmodus nutzen.', 'danger')
        return redirect(url_for('main.index'))
    
    # Aktuellen Spielstatus ermitteln
    active_session = GameSession.query.filter_by(is_active=True).first()
    game_status = None
    
    if active_session:
        current_phase = active_session.current_phase
        
        if current_phase == 'DICE_ROLLING':
            current_team = None
            if active_session.current_team_turn_id:
                team = Team.query.get(active_session.current_team_turn_id)
                current_team = team.name if team else "Unbekannt"
            
            # Lade letztes Würfelergebnis für Moderationsmodus
            dice_result = _get_latest_dice_result(active_session)
            
            # TEMP: Test-Daten falls keine echten Daten vorhanden
            if not dice_result:
                current_app.logger.info("DEBUG: No real dice result found, checking for test data")
                # Teste mit aktueller Team-Info
                if active_session.current_team_turn_id:
                    from datetime import datetime
                    team = Team.query.get(active_session.current_team_turn_id)
                    current_app.logger.info(f"DEBUG: Current team: {team.name if team else 'None'}, last_dice_result: {team.last_dice_result if team else 'No team'}")
                    
                    if team and team.last_dice_result:
                        dice_result = {
                            'team_name': team.name,
                            'standard_roll': team.last_dice_result if team.last_dice_result <= 6 else 6,
                            'bonus_roll': max(0, team.last_dice_result - 6),
                            'total_roll': team.last_dice_result,
                            'timestamp': datetime.utcnow().strftime('%H:%M:%S'),
                            'has_bonus': team.last_dice_result > 6,
                            'is_recent': True
                        }
                        current_app.logger.info(f"DEBUG: Using team last_dice_result: {dice_result}")
                    else:
                        # FORCE TEST: Erstelle einfach Test-Daten
                        dice_result = {
                            'team_name': team.name if team else 'Test Team',
                            'standard_roll': 4,
                            'bonus_roll': 2,
                            'total_roll': 6,
                            'timestamp': datetime.utcnow().strftime('%H:%M:%S'),
                            'has_bonus': True,
                            'is_recent': True
                        }
                        current_app.logger.info(f"DEBUG: Using FORCE TEST dice result: {dice_result}")
            
            current_app.logger.info(f"DEBUG: DICE_ROLLING phase - final dice result: {dice_result}")
            
            game_status = {
                'current_status': 'Würfelrunde',
                'status_color': 'primary',
                'current_team': current_team,
                'additional_info': f'Team {current_team} ist an der Reihe' if current_team else 'Würfelrunde läuft',
                'dice_result': dice_result  # NEU: Würfelergebnis für Auto-Display
            }
        
        elif current_phase == 'MINIGAME_ANNOUNCED':
            # Lade Content-Daten aus verfügbaren Session-Feldern
            current_content = _get_current_content_from_session(active_session)
            content_name = current_content.get('name', 'Unbekannt') if current_content else 'Unbekannt'
            content_type = current_content.get('type', 'unknown') if current_content else 'unknown'
            
            status_text = 'Minispiel' if content_type == 'game' else 'Frage'
            
            game_status = {
                'current_status': status_text,
                'status_color': 'warning' if content_type == 'game' else 'info',
                'current_team': None,
                'additional_info': f'{status_text}: {content_name}',
                'content_details': _get_content_details(current_content, content_type, active_session)
            }
        
        elif current_phase == 'QUESTION_ACTIVE':
            # Lade Content-Daten aus verfügbaren Session-Feldern  
            current_content = _get_current_content_from_session(active_session)
            content_name = current_content.get('name', 'Unbekannt') if current_content else 'Unbekannt'
            
            game_status = {
                'current_status': 'Frage läuft',
                'status_color': 'success',
                'current_team': None,
                'additional_info': f'Aktive Frage: {content_name}',
                'content_details': _get_content_details(current_content, 'question', active_session)
            }
        
        elif current_phase == 'MINIGAME_RESULTS':
            # Lade Content-Daten und Ergebnisse
            current_content = _get_current_content_from_session(active_session)
            content_name = current_content.get('name', 'Unbekannt') if current_content else 'Unbekannt'
            content_type = current_content.get('type', 'game') if current_content else 'game'
            
            results = _get_game_results(active_session)
            current_app.logger.info(f"DEBUG: MINIGAME_RESULTS phase - results: {results}")
            
            game_status = {
                'current_status': 'Ergebnisse',
                'status_color': 'warning',
                'current_team': None,
                'additional_info': f'Ergebnisse: {content_name}',
                'content_details': _get_content_details(current_content, content_type, active_session),
                'results': results
            }
        
        elif current_phase == 'SETUP_MINIGAME':
            game_status = {
                'current_status': 'Vorbereitung',
                'status_color': 'info',
                'current_team': None,
                'additional_info': 'Admin wählt nächsten Inhalt aus'
            }
        
        elif current_phase == 'ROUND_OVER':
            # Zeige letzte Ergebnisse falls vorhanden
            results = _get_game_results(active_session)
            game_status = {
                'current_status': 'Runde beendet',
                'status_color': 'success',
                'current_team': None,
                'additional_info': 'Runde ist beendet',
                'results': results if results and results.get('has_results') else None
            }
        
        else:
            game_status = {
                'current_status': 'Unbekannt',
                'status_color': 'secondary',
                'current_team': None,
                'additional_info': f'Phase: {current_phase}'
            }
        
    
    return render_template('admin/moderation_mode.html', 
                         title='Moderationsmodus',
                         game_status=game_status)

@admin_bp.route('/moderation_mode_api')
@login_required
def moderation_mode_api():
    """API Endpoint für AJAX Updates im Moderationsmodus"""
    try:
        if not isinstance(current_user, Admin):
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Gleiche Logik wie moderation_mode, aber als JSON
        active_session = GameSession.query.filter_by(is_active=True).first()
        game_status = None
        
        if active_session:
            current_phase = active_session.current_phase
            current_app.logger.info(f"DEBUG API: Current phase is {current_phase}")
            
            if current_phase == 'DICE_ROLLING':
                current_team = None
                if active_session.current_team_turn_id:
                    team = Team.query.get(active_session.current_team_turn_id)
                    current_team = team.name if team else "Unbekannt"
                
                # Lade letztes Würfelergebnis für Moderationsmodus  
                dice_result = _get_latest_dice_result(active_session)
                
                # TEMP: Test-Daten falls keine echten Daten vorhanden
                if not dice_result:
                    current_app.logger.info("DEBUG API: No real dice result found, checking for test data")
                    # Teste mit aktueller Team-Info
                    if active_session.current_team_turn_id:
                        from datetime import datetime
                        team = Team.query.get(active_session.current_team_turn_id)
                        current_app.logger.info(f"DEBUG API: Current team: {team.name if team else 'None'}, last_dice_result: {team.last_dice_result if team else 'No team'}")
                        
                        if team and team.last_dice_result:
                            dice_result = {
                                'team_name': team.name,
                                'standard_roll': team.last_dice_result if team.last_dice_result <= 6 else 6,
                                'bonus_roll': max(0, team.last_dice_result - 6),
                                'total_roll': team.last_dice_result,
                                'timestamp': datetime.utcnow().strftime('%H:%M:%S'),
                                'has_bonus': team.last_dice_result > 6,
                                'is_recent': True
                            }
                            current_app.logger.info(f"DEBUG API: Using team last_dice_result: {dice_result}")
                        else:
                            # FORCE TEST: Erstelle einfach Test-Daten
                            dice_result = {
                                'team_name': team.name if team else 'Test Team',
                                'standard_roll': 4,
                                'bonus_roll': 2,
                                'total_roll': 6,
                                'timestamp': datetime.utcnow().strftime('%H:%M:%S'),
                                'has_bonus': True,
                                'is_recent': True
                            }
                            current_app.logger.info(f"DEBUG API: Using FORCE TEST dice result: {dice_result}")
                
                current_app.logger.info(f"DEBUG API: DICE_ROLLING phase - final dice result: {dice_result}")
                
                game_status = {
                    'current_status': 'Würfelrunde',
                    'status_color': 'primary',
                    'current_team': current_team,
                    'additional_info': f'Team {current_team} ist an der Reihe' if current_team else 'Würfelrunde läuft',
                    'dice_result': dice_result  # NEU: Würfelergebnis für Auto-Display
                }
            
            elif current_phase == 'MINIGAME_ANNOUNCED':
                current_content = _get_current_content_from_session(active_session)
                content_name = current_content.get('name', 'Unbekannt') if current_content else 'Unbekannt'
                content_type = current_content.get('type', 'unknown') if current_content else 'unknown'
                
                status_text = 'Minispiel' if content_type == 'game' else 'Frage'
                
                game_status = {
                    'current_status': status_text,
                    'status_color': 'warning' if content_type == 'game' else 'info',
                    'current_team': None,
                    'additional_info': f'{status_text}: {content_name}',
                    'content_details': _get_content_details(current_content, content_type, active_session)
                }
            
            elif current_phase == 'QUESTION_ACTIVE':
                current_content = _get_current_content_from_session(active_session)
                content_name = current_content.get('name', 'Unbekannt') if current_content else 'Unbekannt'
                
                game_status = {
                    'current_status': 'Frage läuft',
                    'status_color': 'success',
                    'current_team': None,
                    'additional_info': f'Aktive Frage: {content_name}',
                    'content_details': _get_content_details(current_content, 'question', active_session)
                }
            
            elif current_phase == 'MINIGAME_RESULTS':
                current_content = _get_current_content_from_session(active_session)
                content_name = current_content.get('name', 'Unbekannt') if current_content else 'Unbekannt'
                content_type = current_content.get('type', 'game') if current_content else 'game'
                
                results = _get_game_results(active_session)
                current_app.logger.info(f"DEBUG API: MINIGAME_RESULTS phase - results: {results}")
                
                game_status = {
                    'current_status': 'Ergebnisse',
                    'status_color': 'warning',
                    'current_team': None,
                    'additional_info': f'Ergebnisse: {content_name}',
                    'content_details': _get_content_details(current_content, content_type, active_session),
                    'results': results
                }
            
            elif current_phase == 'SETUP_MINIGAME':
                game_status = {
                    'current_status': 'Vorbereitung',
                    'status_color': 'info',
                    'current_team': None,
                    'additional_info': 'Admin wählt nächsten Inhalt aus'
                }
            
            elif current_phase == 'ROUND_OVER':
                # Zeige letzte Ergebnisse falls vorhanden
                results = _get_game_results(active_session)
                game_status = {
                    'current_status': 'Runde beendet',
                    'status_color': 'success',
                    'current_team': None,
                    'additional_info': 'Runde ist beendet',
                    'results': results if results and results.get('has_results') else None
                }
            
            else:
                game_status = {
                    'current_status': 'Unbekannt',
                    'status_color': 'secondary',
                    'current_team': None,
                    'additional_info': f'Phase: {current_phase}'
                }
    
        return jsonify({'game_status': game_status})
        
    except Exception as e:
        current_app.logger.error(f"ERROR in moderation_mode_api: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

def _get_content_details(current_content, content_type, active_session=None):
    """Hilfsfunktion um Details für Fragen/Minigames zu extrahieren"""
    if not current_content:
        return None
    
    details = {
        'name': current_content.get('name', 'Unbekannt'),
        'description': current_content.get('description', ''),
        'type_name': 'Minispiel' if content_type == 'game' else 'Frage',
        'type_color': 'warning' if content_type == 'game' else 'info',
        'icon': 'gamepad' if content_type == 'game' else 'question-circle'
    }
    
    # Für Fragen: spezifische Daten und Team-Antworten
    if content_type == 'question':
        # Try different field names for question text (same logic as main/routes.py)
        details['question_text'] = (current_content.get('question_text') or 
                                   current_content.get('question') or 
                                   current_content.get('text') or 
                                   current_content.get('content') or 
                                   current_content.get('description') or '')
        
        # Get question type
        question_type = current_content.get('question_type', current_content.get('type', 'multiple_choice'))
        
        # Multiple Choice Optionen
        if question_type == 'multiple_choice':
            details['options'] = current_content.get('options', [])
            correct_idx = current_content.get('correct_option')
            if correct_idx is not None and details['options'] and 0 <= correct_idx < len(details['options']):
                details['correct_answer'] = f"Option {correct_idx + 1}: {details['options'][correct_idx]}"
        
        # Text Input
        elif question_type == 'text_input':
            details['correct_answer'] = current_content.get('correct_text', '')
        
        # Team-Antworten Status
        if active_session:
            details['team_responses'] = _get_team_response_status(active_session)
    
    # Für Minigames: spezifische Daten und ausgeloste Spieler
    elif content_type == 'game':
        details['duration'] = current_content.get('duration', '')
        details['instructions'] = current_content.get('instructions', '')
        
        # Ausgeloste Spieler
        if active_session:
            details['selected_players'] = _get_selected_players(active_session)
    
    return details

def _get_team_response_status(active_session):
    """DETAILLIERTE TEAM-ANTWORTEN MIT RICHTIG/FALSCH STATUS - GLEICHE LOGIK WIE /api/question-responses"""
    from ..models import QuestionResponse, Team
    
    # Nur laden wenn Frage aktiv ist
    if not active_session.current_question_id:
        return {
            'answered': [],
            'pending': [],
            'detailed_responses': []
        }
    
    try:
        all_teams = Team.query.all()
        
        # Lade Antworten für aktuelle Frage mit Details
        responses = QuestionResponse.query.filter_by(
            game_session_id=active_session.id,
            question_id=active_session.current_question_id
        ).join(Team).all()
        
        answered_team_ids = [r.team_id for r in responses]
        detailed_responses = []
        
        # Erstelle detaillierte Antwort-Liste (wie im Admin Dashboard)
        for response in responses:
            answer_preview = ""
            if response.selected_option is not None:
                active_round = GameRound.get_active_round()
                if active_round and active_round.minigame_folder:
                    from .minigame_utils import get_question_from_folder
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
            
            detailed_responses.append({
                "team_name": response.team.name,
                "answer_preview": answer_preview,
                "is_correct": response.is_correct,
                "answered_at": response.answered_at.strftime('%H:%M:%S') if response.answered_at else None
            })
        
        # Sortiere nach Antwortzeit
        detailed_responses.sort(key=lambda x: x['answered_at'] or '99:99:99')
        
        answered_teams = [team.name for team in all_teams if team.id in answered_team_ids]
        pending_teams = [team.name for team in all_teams if team.id not in answered_team_ids]
        
        return {
            'answered': answered_teams,
            'pending': pending_teams,
            'detailed_responses': detailed_responses,
            'total_responses': len(detailed_responses),
            'total_teams': len(all_teams)
        }
        
    except Exception as e:
        current_app.logger.error(f"Error getting team response status: {e}", exc_info=True)
        return {
            'answered': [],
            'pending': [],
            'detailed_responses': []
        }

def _get_latest_dice_result(active_session):
    """Ermittelt das neueste Würfelergebnis für den Moderationsmodus"""
    from ..models import GameEvent
    from datetime import datetime, timedelta
    import json
    
    if not active_session:
        current_app.logger.info("DEBUG _get_latest_dice_result: No active session")
        return None
        
    try:
        # Suche nach dem neuesten Würfel-Event in den letzten 60 Sekunden (erweitert)
        recent_time = datetime.utcnow() - timedelta(seconds=60)
        
        # Debug: Alle dice_roll Events anzeigen
        all_dice_events = GameEvent.query.filter(
            GameEvent.event_type == 'dice_roll',
            GameEvent.game_session_id == active_session.id
        ).order_by(GameEvent.timestamp.desc()).limit(5).all()
        
        current_app.logger.info(f"DEBUG: Found {len(all_dice_events)} dice events total for session {active_session.id}")
        for event in all_dice_events:
            current_app.logger.info(f"  - Event {event.id}: {event.timestamp}, team={event.related_team_id}")
        
        last_dice_event = GameEvent.query.filter(
            GameEvent.event_type == 'dice_roll',
            GameEvent.game_session_id == active_session.id,
            GameEvent.timestamp >= recent_time
        ).order_by(GameEvent.timestamp.desc()).first()
        
        current_app.logger.info(f"DEBUG: Recent dice event (last 60s): {last_dice_event}")
        
        if last_dice_event and last_dice_event.data_json:
            current_app.logger.info(f"DEBUG: Processing dice event data: {last_dice_event.data_json}")
            
            # Versuche JSON zu parsen
            if isinstance(last_dice_event.data_json, str):
                event_data = json.loads(last_dice_event.data_json)
            else:
                event_data = last_dice_event.data_json
            
            # Hole Team-Name
            team_name = "Unbekannt"
            if last_dice_event.related_team_id:
                from ..models import Team
                team = Team.query.get(last_dice_event.related_team_id)
                if team:
                    team_name = team.name
            
            result = {
                'team_name': team_name,
                'standard_roll': event_data.get('standard_roll', 0),
                'bonus_roll': event_data.get('bonus_roll', 0),
                'total_roll': event_data.get('total_roll', 0),
                'timestamp': last_dice_event.timestamp.strftime('%H:%M:%S'),
                'has_bonus': event_data.get('bonus_roll', 0) > 0,
                'is_recent': True  # Marker für Auto-Display
            }
            
            current_app.logger.info(f"DEBUG: Returning dice result: {result}")
            return result
        else:
            current_app.logger.info("DEBUG: No recent dice event found or no data_json")
            
    except Exception as e:
        current_app.logger.error(f"Error getting latest dice result: {e}", exc_info=True)
    
    return None

def _get_selected_players(active_session):
    """Ermittelt ausgeloste Spieler für Minigames"""
    selected_players = {}
    
    # Aus selected_players Feld laden (JSON in session)
    if hasattr(active_session, 'selected_players') and active_session.selected_players:
        try:
            selections = json.loads(active_session.selected_players) if isinstance(active_session.selected_players, str) else active_session.selected_players
            
            for team_id, player_name in selections.items():
                from ..models import Team
                team = Team.query.get(int(team_id))
                if team:
                    selected_players[team.name] = player_name
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
    
    return selected_players

def _get_current_content_from_session(active_session):
    """Extrahiert aktuelle Content-Daten aus GameSession Feldern - MEHR DETAILS ALS ADMIN DASHBOARD"""
    content = {}
    
    # Prüfe zuerst ob eine Frage aktiv ist
    if active_session.current_question_id:
        # Lade Frage mit allen Details aus Datei
        active_round = GameRound.get_active_round()
        if active_round and active_round.minigame_folder:
            try:
                from .minigame_utils import get_question_from_folder
                question_data = get_question_from_folder(
                    active_round.minigame_folder.folder_path, 
                    active_session.current_question_id
                )
                current_app.logger.info(f"DEBUG: Question data loaded: {question_data}")
                
                if question_data:
                    content = {
                        'name': active_session.current_minigame_name or question_data.get('name', 'Frage'),
                        'description': active_session.current_minigame_description or question_data.get('description', ''),
                        'type': 'question',
                        'question_text': question_data.get('question_text', ''),
                        'question_type': question_data.get('question_type', ''),
                    }
                    
                    # Für Multiple Choice Fragen: Optionen hinzufügen
                    if question_data.get('question_type') == 'multiple_choice' and question_data.get('options'):
                        content['options'] = question_data['options']
                        # Korrekte Antwort basierend auf Index
                        if 'correct_option' in question_data and isinstance(question_data['correct_option'], int):
                            try:
                                correct_idx = question_data['correct_option']
                                if 0 <= correct_idx < len(question_data['options']):
                                    content['correct_answer'] = question_data['options'][correct_idx]
                            except (IndexError, TypeError):
                                pass
                    
                    # Für Text Input Fragen: Korrekte Antwort direkt
                    elif question_data.get('question_type') == 'text_input' and question_data.get('correct_text'):
                        content['correct_answer'] = question_data['correct_text']
                    
                    current_app.logger.info(f"DEBUG: Final question content: {content}")
                    return content
                    
            except Exception as e:
                current_app.logger.error(f"Error loading question: {e}", exc_info=True)
    
    # Falls kein Question-Daten gefunden, verwende Minigame-Info
    if not content and active_session.current_minigame_name:
        content = {
            'name': active_session.current_minigame_name,
            'description': active_session.current_minigame_description or '',
            'type': 'game'
        }
    
    # Fallback-Werte
    if not content.get('name'):
        content['name'] = 'Unbekannt'
    if not content.get('type'):
        content['type'] = 'unknown'
        
    return content

def _get_game_results(active_session):
    """Ermittelt Spiel-Ergebnisse und Platzierungen"""
    from ..models import Team
    
    results = {
        'placements': [],
        'has_results': False
    }
    
    try:
        # Hole alle Teams mit ihren Platzierungen
        teams = Team.query.all()
        team_placements = []
        
        current_app.logger.info(f"DEBUG: Checking results for {len(teams)} teams")
        
        for team in teams:
            # Prüfe auf verschiedene Platzierungs-Felder
            placement = None
            if hasattr(team, 'minigame_placement') and team.minigame_placement is not None:
                placement = team.minigame_placement
                current_app.logger.info(f"DEBUG: Team {team.name} has minigame_placement: {placement}")
            elif hasattr(team, 'question_placement') and team.question_placement is not None:
                placement = team.question_placement
                current_app.logger.info(f"DEBUG: Team {team.name} has question_placement: {placement}")
            
            if placement is not None:
                team_placements.append({
                    'team_name': team.name,
                    'placement': placement
                })
                current_app.logger.info(f"DEBUG: Added team {team.name} with placement {placement}")
        
        current_app.logger.info(f"DEBUG: Found {len(team_placements)} teams with placements")
        
        if team_placements:
            # Sortiere nach Platzierung
            team_placements.sort(key=lambda x: x['placement'])
            results['placements'] = team_placements
            results['has_results'] = True
        
        # DEBUG: Immer Beispiel-Ergebnisse für Tests
        if not results['has_results'] and len(teams) > 0:
            current_app.logger.info("DEBUG: No real results found, creating test results")
            for i, team in enumerate(teams[:3]):
                team_placements.append({
                    'team_name': team.name,
                    'placement': i + 1
                })
            results['placements'] = team_placements
            results['has_results'] = True
    
    except Exception as e:
        current_app.logger.error(f"Fehler beim Laden der Ergebnisse: {e}")
    
    return results

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

    # Sequenz-Info direkt aus DB laden (wegen Beziehungsproblem)
    active_sequence = None
    if active_round and active_round.minigame_folder:
        active_sequence = MinigameSequence.query.filter_by(
            minigame_folder_id=active_round.minigame_folder.id
        ).first()

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
        "active_sequence": active_sequence,
        # NEU: Feld-Management Daten
        "field_stats": field_stats,
        "field_color_mapping": field_color_mapping
    }
    
    return render_template('admin.html', **template_data)

@admin_bp.route('/open-board')
@login_required
def open_board():
    """Route für 'Spielbrett öffnen' - prüft ob Teams existieren"""
    if not isinstance(current_user, Admin):
        flash('Zugriff verweigert. Nur Admins können das Spielbrett öffnen.', 'danger')
        return redirect(url_for('main.index'))
    
    # Prüfe ob Teams registriert sind
    teams_count = Team.query.count()
    if teams_count == 0:
        # Keine Teams -> zur Welcome-Seite umleiten
        flash('Noch keine Teams registriert. Nutze das Welcome-System, um Teams zu erstellen.', 'info')
        return redirect(url_for('main.welcome'))
    
    # Teams vorhanden -> zum Spielbrett weiterleiten
    return redirect(url_for('main.game_board'))

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated and isinstance(current_user, Admin):
        return redirect(url_for('admin.admin_dashboard'))
    
    form = AdminLoginForm()
    if form.validate_on_submit():
        admin = Admin.query.filter_by(username=form.username.data).first()
        if admin and admin.check_password(form.password.data):
            login_user(admin, remember=True)  # Remember session für längere Laufzeit
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

        # EINFACHE ABER ROBUSTE LÖSUNG: Zähle aktuelle Würfel-Events in der Runde  
        if active_session.dice_roll_order:
            try:
                # Parse die Würfelreihenfolge
                dice_order_team_ids = [int(tid) for tid in active_session.dice_roll_order.split(',') if tid.strip().isdigit()]
                total_teams = len(dice_order_team_ids)
                
                # Zähle ALLE Würfel-Events in dieser Session
                all_dice_events_in_session = GameEvent.query.filter_by(
                    game_session_id=active_session.id
                ).filter(
                    GameEvent.event_type.in_(['team_dice_roll', 'admin_dice_roll'])
                ).count()
                
                # Zähle Würfel-Events für dieses spezifische Team
                team_dice_events = GameEvent.query.filter_by(
                    game_session_id=active_session.id,
                    related_team_id=team.id
                ).filter(
                    GameEvent.event_type.in_(['team_dice_roll', 'admin_dice_roll'])
                ).count()
                
                # Ermittle welche "Runde" wir sind (wie oft jedes Team gewürfelt haben sollte)
                expected_round = (all_dice_events_in_session // total_teams) + 1
                
                # Wenn das Team bereits in dieser Runde gewürfelt hat, verweigern
                if team_dice_events >= expected_round:
                    if team.id != active_session.current_team_turn_id:
                        return jsonify({"success": False, "error": f"Team {team.name} hat bereits in dieser Runde gewürfelt."}), 403
                        
            except (ValueError, ZeroDivisionError) as e:
                current_app.logger.warning(f"Fehler bei Würfel-Validierung: {e}")
                pass  # Bei Fehlern in der Logik, erlaube Würfeln

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
            barrier_check_result = check_barrier_release(team, standard_dice_roll, active_session, bonus_dice_roll)
            
            if barrier_check_result['released']:
                # Team ist befreit und kann sich normal bewegen
                max_field_index = current_app.config.get('MAX_BOARD_FIELDS', 72)
                new_position = min(team.current_position + total_roll, max_field_index)
                team.current_position = new_position
                
                # Prüfe Sonderfeld-Aktion nach Bewegung
                all_teams = Team.query.all()
                dice_info = {
                    "old_position": old_position,
                    "new_position": new_position,
                    "dice_roll": standard_dice_roll,
                    "bonus_roll": bonus_dice_roll,
                    "total_roll": total_roll
                }
                special_field_result = handle_special_field_action(team, all_teams, active_session, dice_info)
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
            dice_info = {
                "old_position": old_position,
                "new_position": new_position,
                "dice_roll": standard_dice_roll,
                "bonus_roll": bonus_dice_roll,
                "total_roll": total_roll
            }
            special_field_result = handle_special_field_action(team, all_teams, active_session, dice_info)

        # ZIELFELD: Prüfe Gewinn-Bedingung
        # WICHTIG: Team muss BEREITS auf Position 72 gewesen sein (old_position), nicht erst durch den Wurf dorthin gekommen
        victory_triggered = False
        current_app.logger.info(f"🔍 ADMIN DICE DEBUG: Team {team.name} - old_position: {old_position}, new_position: {new_position}, total_roll: {total_roll}")
        
        if old_position == 72 and total_roll >= 6:
            # Team war bereits auf Zielfeld und hat 6+ gewürfelt - hat gewonnen!
            victory_triggered = True
            current_app.logger.info(f"🏆 VICTORY: Team {team.name} war auf Position 72 und würfelte {total_roll} (>= 6) - SIEG!")
        elif old_position == 72 and total_roll < 6:
            # Team war auf Zielfeld, hat aber weniger als 6 gewürfelt
            current_app.logger.info(f"🎯 FINAL FIELD: Team {team.name} war auf Position 72, würfelte {total_roll} - braucht mindestens 6 zum Gewinnen")
        elif new_position == 72:
            # Team ist gerade erst auf Position 72 angekommen - muss nächste Runde 6+ würfeln
            current_app.logger.info(f"🎯 REACHED FINAL FIELD: Team {team.name} erreichte Position 72 - muss nächste Runde mindestens 6 würfeln")
            
        current_app.logger.info(f"🔍 ADMIN DICE DEBUG: victory_triggered = {victory_triggered}")

        # Event für den Würfelwurf erstellen
        event_description = f"Admin würfelte für Team {team.name}: {standard_dice_roll}"
        if bonus_dice_roll > 0:
            event_description += f" (Bonus: {bonus_dice_roll}, Gesamt: {total_roll})"
        
        if team.is_blocked and (not barrier_check_result or not barrier_check_result.get('released', False)):
            event_description += f" - BLOCKIERT: Konnte sich nicht befreien."
        else:
            event_description += f" und bewegte sich von Feld {old_position} zu Feld {new_position}."
            
        if victory_triggered:
            event_description += f" 🏆 SIEG! Team war auf Zielfeld und würfelte {total_roll}!"
        elif old_position == 72 and total_roll < 6:
            event_description += f" 🎯 War auf Zielfeld - braucht mindestens 6 zum Gewinnen (gewürfelt: {total_roll})"
        elif new_position == 72:
            event_description += f" 🎯 Erreichte Zielfeld - braucht nächste Runde mindestens 6 zum Gewinnen"
        
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
                "barrier_released": barrier_check_result.get('released', False) if barrier_check_result else False,
                "victory_triggered": victory_triggered,
                "needs_final_roll": old_position == 72 and total_roll < 6
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
            # Prüfe ob ein Feld-Minigame gestartet wurde (Phase geändert von special_field_action)
            if active_session.current_phase == 'FIELD_MINIGAME_SELECTION_PENDING':
                # Feld-Minigame wurde ausgelöst - nicht ROUND_OVER setzen
                current_app.logger.info(f"Letztes Team {team.name} landete auf Minigame-Feld - Runde wartet auf Feld-Minigame")
                active_session.current_team_turn_id = None  # Kein nächstes Team, aber Phase bleibt
            else:
                # Kein Feld-Minigame - normale Rundenvervollständigung
                active_session.current_phase = 'ROUND_OVER'
                active_session.current_team_turn_id = None 
                
                # WICHTIG: Erstelle Event für Rundenende nur wenn Runde wirklich beendet
                round_end_event = GameEvent(
                    game_session_id=active_session.id,
                    event_type="dice_round_ended",
                    description="Würfelrunde beendet (Admin) - alle Teams haben gewürfelt"
                )
                db.session.add(round_end_event)
                
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

        # ZIELFELD: Victory automatisch auslösen wenn gewonnen
        if victory_triggered:
            try:
                # Speichere Victory Event
                victory_event = GameEvent(
                    game_session_id=active_session.id,
                    event_type="game_victory",
                    description=f"Team {team.name} hat das Spiel gewonnen!",
                    related_team_id=team.id,
                    data_json=json.dumps({
                        "winning_team_id": team.id,
                        "winning_team_name": team.name,
                        "victory_timestamp": datetime.utcnow().isoformat(),
                        "final_position": team.current_position,
                        "final_dice_roll": total_roll
                    })
                )
                db.session.add(victory_event)
                
                # Setze Spiel auf beendet
                active_session.current_phase = 'GAME_FINISHED'
                
                current_app.logger.info(f"🏆 Victory automatisch ausgelöst für Team {team.name}")
                
            except Exception as ve:
                current_app.logger.error(f"Fehler beim Victory-Handling: {ve}")
                db.session.rollback()
                return jsonify({"success": False, "error": f"Victory-Fehler: {str(ve)}"}), 500

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
            "new_position": team.current_position,  # Aktuelle finale Position (nach Special Field)
            "next_team_id": active_session.current_team_turn_id,
            "next_team_name": next_team_name, 
            "new_phase": active_session.current_phase,
            "victory_triggered": victory_triggered,
            "needs_final_roll": old_position == 72 and total_roll < 6
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

@admin_bp.route('/abort-minigame', methods=['POST'])
@login_required
def abort_current_minigame():
    """Aktuelles Minigame/Frage abbrechen - zurück zur Admin-Auswahl"""
    if not isinstance(current_user, Admin):
        return jsonify({"success": False, "error": "Nur Admins können Minigames abbrechen."}), 403
    
    try:
        # Aktive Sitzung finden
        active_session = GameSession.query.filter_by(is_active=True).first()
        if not active_session:
            return jsonify({"success": False, "error": "Keine aktive Spielsitzung gefunden."}), 404
        
        current_app.logger.info(f"Admin {current_user.username} bricht aktuelles Minigame ab (Session ID: {active_session.id})")
        
        # Nur die aktuelle Phase zurücksetzen, NICHT die Spielerpositionen
        old_phase = active_session.current_phase
        
        # Je nach aktueller Phase unterschiedlich reagieren
        if active_session.current_phase in ['QUESTION_ACTIVE', 'MINIGAME_RESULTS']:
            # Zurück zu SETUP_MINIGAME für Admin-Auswahl ("Inhalt festlegen")
            active_session.current_phase = 'SETUP_MINIGAME'
            # Team-Turn zurücksetzen damit Admin neues Minigame starten kann
            active_session.current_team_turn_id = None
            current_app.logger.info(f"Phase geändert von {old_phase} zu SETUP_MINIGAME - Admin kann neues Minigame auswählen")
            
        elif active_session.current_phase == 'DICE_ROLLING':
            # Bereits in Würfelphase - nichts zu tun
            current_app.logger.info("Bereits in DICE_ROLLING Phase - kein Minigame aktiv")
            return jsonify({"success": False, "error": "Kein aktives Minigame zum Abbrechen gefunden."})
            
        else:
            # Andere Phasen - zurück zu SETUP_MINIGAME
            active_session.current_phase = 'SETUP_MINIGAME'
            active_session.current_team_turn_id = None
            current_app.logger.info(f"Phase geändert von {old_phase} zu SETUP_MINIGAME")
            
        # WICHTIG: Alle Fragen-Antworten für die aktuelle Session löschen
        # damit das Board aufhört auf Antworten zu warten
        QuestionResponse.query.filter_by(game_session_id=active_session.id).delete()
        current_app.logger.info("Alle Fragen-Antworten für Session gelöscht - Board stoppt Minigame")
        
        # Aktuelles Minigame KOMPLETT aus der Session entfernen
        active_session.current_minigame_content = None
        active_session.current_minigame_type = None
        active_session.current_minigame_name = None
        active_session.current_minigame_description = None
        active_session.current_question_id = None
        active_session.selected_folder_minigame_id = None
        current_app.logger.info("Aktuelles Minigame komplett aus Session entfernt")
        
        # Event für Minigame-Abbruch erstellen
        abort_event = GameEvent(
            game_session_id=active_session.id,
            event_type="minigame_aborted",
            description=f"Minigame/Frage wurde von Admin {current_user.username} abgebrochen (vorherige Phase: {old_phase})"
        )
        db.session.add(abort_event)
        
        # Änderungen speichern
        db.session.commit()
        
        current_app.logger.info("Minigame erfolgreich abgebrochen - zurück zur Admin-Auswahl")
        
        return jsonify({
            "success": True, 
            "message": "Minigame wurde abgebrochen. Admin kann neues Minigame auswählen.",
            "new_phase": active_session.current_phase
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Minigame-Abbruch: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Interner Serverfehler beim Minigame-Abbruch.", "details": str(e)}), 500

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
    current_app.logger.info(f"DEBUG set_minigame: minigame_source='{minigame_source}'")
    minigame_set = False

    try:
        if minigame_source == 'manual':
            # Manuelle Eingabe - kein Tracking nötig
            manual_name = form.minigame_name.data
            manual_description = form.minigame_description.data
            player_count = form.player_count.data or 'all'
            
            if manual_name and manual_description:
                current_app.logger.info(f"DEBUG set_minigame: Setting minigame name='{manual_name}', description='{manual_description}'")
                active_session.current_minigame_name = manual_name
                active_session.current_minigame_description = manual_description
                current_app.logger.info(f"DEBUG set_minigame: After setting - session.current_minigame_name='{active_session.current_minigame_name}'")
                active_session.current_player_count = player_count
                active_session.selected_folder_minigame_id = None
                active_session.current_question_id = None
                active_session.minigame_source = 'manual'
                
                # Zufällige Spielerauswahl bei numerischen Werten oder "ganzes Team"
                if player_count.isdigit() or player_count == "all":
                    # Stelle sicher, dass die Teams mit aktuellen Daten geladen werden
                    # BUGFIX: Commit session changes before expire_all() to prevent data loss
                    db.session.commit()
                    db.session.expire_all()
                    teams = Team.query.all()
                    selected_players = active_session.select_random_players(teams, player_count)
                    
                    # Flash-Nachricht mit ausgewählten Spielern
                    player_info = []
                    for team_id, players in selected_players.items():
                        team = Team.query.get(int(team_id))
                        if team and players:
                            player_info.append(f"{team.name}: {', '.join(players)}")
                    
                    selection_type = "Ganze Teams" if player_count == "all" else f"{player_count} Spieler pro Team"
                    flash_msg = f"Inhalt '{manual_name}' gesetzt ({selection_type}). Ausgewählte Spieler: " + " | ".join(player_info)
                    flash(flash_msg, 'info')
                else:
                    # Spieleranzahl für Flash-Nachricht
                    player_display = dict(form.player_count.choices).get(player_count, player_count)
                    flash(f"Inhalt '{manual_name}' manuell gesetzt. Spieleranzahl: {player_display}", 'info')
                
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
                active_session.current_player_count = None  # Keine Spieleranzahl bei Fragen
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
                    
                    current_app.logger.info(f"DEBUG set_minigame folder_random: Setting minigame name='{random_content['name']}', description='{random_content.get('description', '')}'")
                    active_session.current_minigame_name = random_content['name']
                    active_session.current_minigame_description = random_content.get('description', '')
                    current_app.logger.info(f"DEBUG set_minigame folder_random: After setting - session.current_minigame_name='{active_session.current_minigame_name}'")
                    active_session.selected_folder_minigame_id = random_content['id']
                    active_session.minigame_source = 'folder_random'
                    
                    # Setze Spieleranzahl nur bei Minispielen, nicht bei Fragen
                    if random_content.get('type') != 'question':
                        # Verwende Spieleranzahl aus Minigame-Konfiguration, falls verfügbar
                        minigame_player_count = random_content.get('player_count')
                        form_player_count = form.player_count.data
                        
                        # Priorisiere Minigame-Konfiguration über Formular-Eingabe
                        # Gültige Werte: '1', '2', '3', '4', 'all'
                        valid_counts = ['1', '2', '3', '4', 'all']
                        if minigame_player_count and minigame_player_count in valid_counts:
                            player_count = minigame_player_count
                            current_app.logger.info(f"Random minigame - using player_count from config: {player_count}")
                        else:
                            player_count = form_player_count or 'all'
                            current_app.logger.info(f"Random minigame - using player_count from form: {player_count} (minigame config was: {minigame_player_count})")
                        
                        active_session.current_player_count = player_count
                    
                    # Check if all content has been played
                    stats = get_played_count_for_folder(
                        active_round.minigame_folder.folder_path, 
                        active_session.get_played_content_ids()
                    )
                    
                    if random_content.get('type') == 'question':
                        active_session.current_question_id = random_content['id']
                        active_session.current_player_count = None  # Keine Spieleranzahl bei Fragen
                        flash_msg = f"Zufällige Frage '{random_content['name']}' aus Ordner '{active_round.minigame_folder.name}' ausgewählt."
                    else:
                        active_session.current_question_id = None
                        # Spielerauswahl für Minispiele
                        if player_count.isdigit() or player_count == "all":
                            # Stelle sicher, dass die Teams mit aktuellen Daten geladen werden
                            # BUGFIX: Commit session changes before expire_all() to prevent data loss
                            db.session.commit()
                            db.session.expire_all()
                            teams = Team.query.all()
                            selected_players = active_session.select_random_players(teams, player_count)
                            selection_type = "Ganze Teams" if player_count == "all" else f"{player_count} Spieler pro Team"
                            config_source = " (aus Minigame-Konfiguration)" if minigame_player_count else " (aus Formular)"
                            flash_msg = f"Zufälliges Minispiel '{random_content['name']}' aus Ordner '{active_round.minigame_folder.name}' ausgewählt ({selection_type}{config_source})."
                        else:
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
                    
                    current_app.logger.info(f"DEBUG set_minigame folder_selected: Setting minigame name='{selected_content['name']}', description='{selected_content.get('description', '')}'")
                    active_session.current_minigame_name = selected_content['name']
                    active_session.current_minigame_description = selected_content.get('description', '')
                    current_app.logger.info(f"DEBUG set_minigame folder_selected: After setting - session.current_minigame_name='{active_session.current_minigame_name}'")
                    active_session.selected_folder_minigame_id = selected_content['id']
                    active_session.minigame_source = 'folder_selected'
                    
                    if selected_content.get('type') == 'question':
                        active_session.current_question_id = selected_content['id']
                        active_session.current_player_count = None  # Keine Spieleranzahl bei Fragen
                        flash(f"Frage '{selected_content['name']}' aus Ordner ausgewählt.", 'info')
                    else:
                        active_session.current_question_id = None
                        # Verwende Spieleranzahl aus Minigame-Konfiguration, falls verfügbar
                        minigame_player_count = selected_content.get('player_count')
                        form_player_count = form.player_count.data
                        
                        # Priorisiere Minigame-Konfiguration über Formular-Eingabe
                        # Gültige Werte: '1', '2', '3', '4', 'all'
                        valid_counts = ['1', '2', '3', '4', 'all']
                        if minigame_player_count and minigame_player_count in valid_counts:
                            player_count = minigame_player_count
                            current_app.logger.info(f"Using player_count from minigame config: {player_count}")
                        else:
                            player_count = form_player_count or 'all'
                            current_app.logger.info(f"Using player_count from form: {player_count} (minigame config was: {minigame_player_count})")
                        
                        active_session.current_player_count = player_count
                        
                        if player_count.isdigit() or player_count == "all":
                            # Stelle sicher, dass die Teams mit aktuellen Daten geladen werden
                            # BUGFIX: Commit session changes before expire_all() to prevent data loss
                            db.session.commit()
                            db.session.expire_all()
                            teams = Team.query.all()
                            selected_players = active_session.select_random_players(teams, player_count)
                            selection_type = "Ganze Teams" if player_count == "all" else f"{player_count} Spieler pro Team"
                            config_source = " (aus Minigame-Konfiguration)" if minigame_player_count else " (aus Formular)"
                            flash(f"Minispiel '{selected_content['name']}' aus Ordner ausgewählt ({selection_type}{config_source}).", 'info')
                        else:
                            flash(f"Minispiel '{selected_content['name']}' aus Ordner ausgewählt.", 'info')
                    
                    minigame_set = True
                else:
                    flash('Ausgewählter Inhalt nicht im Ordner gefunden.', 'warning')
            else:
                flash('Bitte einen Inhalt aus dem Ordner auswählen.', 'warning')

        elif minigame_source == 'folder_planned':
            # Geplanter Ablauf - aus aktiver Sequenz
            if active_round and active_round.minigame_folder:
                active_sequence = MinigameSequence.query.filter_by(
                    minigame_folder_id=active_round.minigame_folder.id,
                    is_active=True
                ).first()
                
                if active_sequence:
                    current_item = active_sequence.get_current_item()
                    
                    if current_item:
                        # Lade vollständige Item-Daten aus dem Ordner
                        full_item_data = get_minigame_from_folder(
                            active_round.minigame_folder.folder_path, 
                            current_item['id']
                        )
                        
                        if full_item_data:
                            # Verwende direkte Item-Daten (keine Custom-Namen im vereinfachten System)
                            display_name = full_item_data['name']
                            display_description = full_item_data.get('description', '')
                            
                            current_app.logger.info(f"DEBUG set_minigame folder_planned: Setting minigame name='{display_name}', description='{display_description}'")
                            active_session.current_minigame_name = display_name
                            active_session.current_minigame_description = display_description
                            active_session.selected_folder_minigame_id = current_item['id']
                            active_session.minigame_source = 'folder_planned'
                            
                            # Markiere als gespielt (optional für Tracking)
                            mark_content_as_played(active_session, current_item['id'])
                            
                            # Setze Frage-ID falls es eine Frage ist
                            if current_item.get('type') == 'question':
                                active_session.current_question_id = current_item['id']
                                active_session.current_player_count = None
                                flash(f"Frage '{display_name}' aus Ablaufplan geladen (Position {active_sequence.current_position + 1}/{len(active_sequence.sequence_list)}).", 'info')
                            else:
                                active_session.current_question_id = None
                                
                                # Verwende Spieleranzahl aus Minigame-Konfiguration
                                minigame_player_count = full_item_data.get('player_count')
                                form_player_count = form.player_count.data
                                
                                valid_counts = ['1', '2', '3', '4', 'all']
                                if minigame_player_count and minigame_player_count in valid_counts:
                                    player_count = minigame_player_count
                                elif form_player_count and form_player_count in valid_counts:
                                    player_count = form_player_count
                                else:
                                    player_count = 'all'
                                
                                active_session.current_player_count = player_count
                                
                                selection_type = "Ganze Teams" if player_count == "all" else f"{player_count} Spieler pro Team"
                                config_source = " (aus Minigame-Konfiguration)" if minigame_player_count else " (aus Formular)"
                                flash(f"Minispiel '{display_name}' aus Ablaufplan geladen (Position {active_sequence.current_position + 1}/{len(active_sequence.sequence_list)}, {selection_type}{config_source}).", 'info')
                            
                            # Erweitere Sequenz zum nächsten Item
                            if active_sequence.advance():
                                current_app.logger.info(f"Sequenz für Ordner '{active_round.minigame_folder.name}' erweitert zu Position {active_sequence.current_position}")
                            else:
                                current_app.logger.info(f"Sequenz für Ordner '{active_round.minigame_folder.name}' am Ende angelangt")
                                flash(f"Alle Items des Ablaufplans für '{active_round.minigame_folder.name}' wurden abgeschlossen!", 'success')
                            
                            minigame_set = True
                        else:
                            flash(f"Item '{current_item['id']}' aus Ablaufplan nicht im Ordner gefunden.", 'danger')
                    else:
                        flash(f"Ablaufplan für '{active_round.minigame_folder.name}' ist abgeschlossen.", 'warning')
                else:
                    flash(f"Kein aktiver Ablaufplan für Ordner '{active_round.minigame_folder.name}' gefunden.", 'warning')
            else:
                flash('Keine aktive Runde oder Minigame-Ordner zugewiesen.', 'warning')

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
            current_app.logger.info(f"DEBUG set_minigame: Before commit - session.current_minigame_name='{active_session.current_minigame_name}'")
            db.session.commit()
            current_app.logger.info(f"DEBUG set_minigame: After commit - session.current_minigame_name='{active_session.current_minigame_name}'")

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
        
        # WICHTIG: Markiere den Beginn einer neuen Würfelrunde
        new_round_event = GameEvent(
            game_session_id=active_session.id,
            event_type="dice_round_started",
            description="Neue Würfelrunde gestartet - alle Teams dürfen wieder würfeln"
        )
        db.session.add(new_round_event)
        
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
    
    # WICHTIG: Markiere den Beginn einer neuen Würfelrunde
    new_round_event = GameEvent(
        game_session_id=active_session.id,
        event_type="dice_round_started",
        description="Neue Würfelrunde gestartet (manuelle Platzierungen) - alle Teams dürfen wieder würfeln"
    )
    db.session.add(new_round_event)
    
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
        
        # Aktive Runde für Kontext
        active_round = GameRound.get_active_round()
        
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
                             active_round=active_round,
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
            # Debug logging
            current_app.logger.info(f"[EDIT_FIELD] Form validated for {field_type}")
            current_app.logger.info(f"[EDIT_FIELD] Form data: {form.data}")
            current_app.logger.info(f"[EDIT_FIELD] Request form data: {request.form}")
            
            # Aktualisiere Konfiguration
            updated_config = update_field_config(config.id, form.data)
            
            # Cache invalidieren
            from app.game_logic.special_fields import clear_field_distribution_cache
            clear_field_distribution_cache()
            
            db.session.commit()
            
            # Live-Update Event hinzufügen
            add_field_update_event({
                'type': 'field_updated',
                'field_type': field_type,
                'display_name': updated_config.display_name,
                'message': f"Feld '{updated_config.display_name}' wurde aktualisiert"
            })
            
            flash(f"Feld-Konfiguration für '{updated_config.display_name}' erfolgreich aktualisiert.", 'success')
            return redirect(url_for('admin.manage_fields'))
        
        # Log form errors if validation failed
        if form.errors:
            current_app.logger.warning(f"[EDIT_FIELD] Form validation failed for {field_type}")
            current_app.logger.warning(f"[EDIT_FIELD] Form errors: {form.errors}")
        
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
        
        # Live-Update Event hinzufügen
        add_field_update_event({
            'type': 'field_toggled',
            'field_type': field_type,
            'display_name': config.display_name,
            'is_enabled': config.is_enabled,
            'message': f"Feld '{config.display_name}' wurde {action}"
        })
        
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
        
        # Farb-Mapping für Template
        color_mapping = get_field_type_color_mapping()
        
        # Konflikte prüfen
        conflicts = validate_field_conflicts()
        
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({
                "success": True,
                "preview_data": preview_data,
                "field_stats": field_stats,
                "special_positions": special_positions,
                "color_mapping": color_mapping
            })
        
        return render_template('admin/field_preview.html',
                             form=form,
                             preview_data=preview_data,
                             field_stats=field_stats,
                             special_positions=special_positions,
                             color_mapping=color_mapping,
                             conflicts=conflicts,
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
            
            # Live-Update Event hinzufügen wenn Änderungen gemacht wurden
            if modified_count > 0:
                add_field_update_event({
                    'type': 'bulk_update',
                    'field_type': 'bulk_update',
                    'display_name': 'Mehrere Felder',
                    'modified_count': modified_count,
                    'action': action,
                    'message': f"{modified_count} Felder wurden per Massen-Bearbeitung geändert"
                })
            
            return redirect(url_for('admin.manage_fields'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Fehler bei Massen-Bearbeitung: {e}", exc_info=True)
            flash('Fehler bei der Massen-Bearbeitung.', 'danger')
    
    return render_template('admin/bulk_edit_fields.html', form=form)

@admin_bp.route('/api/field_colors')
def api_field_colors():
    """API-Endpunkt für Feld-Farb-Mapping (für Frontend-Integration) - Öffentlich zugänglich"""
    
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
            
            # Teammitglieder verarbeiten
            if form.members.data:
                # Normalisiere Spielernamen (unterstützt sowohl Komma- als auch Zeilenumbruch-getrennt)
                raw_members = form.members.data.replace('\n', ',')
                members_list = [m.strip() for m in raw_members.split(',') if m.strip()]
                team.members = ', '.join(members_list)
                
                # Erstelle PlayerRegistration Einträge für die Spieler
                welcome_session = WelcomeSession.get_active_session()
                if not welcome_session:
                    # Erstelle eine neue Session falls keine aktiv
                    welcome_session = WelcomeSession()
                    welcome_session.is_active = True
                    db.session.add(welcome_session)
                    db.session.flush()  # Um ID zu bekommen
                
                # Erstelle Registrierungen für alle Spieler
                for member_name in members_list:
                    # Prüfe ob Spieler bereits registriert ist
                    existing_player = PlayerRegistration.query.filter_by(player_name=member_name).first()
                    if not existing_player:
                        player_registration = PlayerRegistration(
                            welcome_session_id=welcome_session.id,
                            player_name=member_name,
                            assigned_team_id=None  # Wird nach Team-Erstellung gesetzt
                        )
                        db.session.add(player_registration)
            
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
            db.session.flush()  # Um Team-ID zu bekommen
            
            # Aktualisiere PlayerRegistration Einträge mit Team-ID
            if form.members.data:
                raw_members = form.members.data.replace('\n', ',')
                members_list = [m.strip() for m in raw_members.split(',') if m.strip()]
                
                for member_name in members_list:
                    player_registration = PlayerRegistration.query.filter_by(
                        player_name=member_name,
                        assigned_team_id=None
                    ).first()
                    if player_registration:
                        player_registration.assigned_team_id = team.id
                        
                        # Kopiere Profilbild ins Team falls vorhanden
                        if player_registration.profile_image_path:
                            team.set_profile_image(member_name, player_registration.profile_image_path)
            
            # Setze welcome_password für die Klartext-Anzeige
            team.welcome_password = form.password.data
            
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
            team.welcome_password = form.password.data
        
        # Update Position und Dice Result
        team.current_position = form.current_position.data
        if form.last_dice_result.data is not None:
            team.last_dice_result = form.last_dice_result.data

        # Teammitglieder aktualisieren
        if form.members.data is not None:  # Auch leere Strings erlauben (zum Leeren)
            # Normalisiere Spielernamen (unterstützt sowohl Komma- als auch Zeilenumbruch-getrennt)
            raw_members = form.members.data.replace('\n', ',')
            members_list = [m.strip() for m in raw_members.split(',') if m.strip()]
            team.members = ', '.join(members_list) if members_list else None
            
            # Wenn sich die Spielerliste geändert hat, player_config aktualisieren
            # Entferne Einstellungen für Spieler, die nicht mehr im Team sind
            if team.player_config:
                current_config = team.get_player_config()
                updated_config = {}
                for player in members_list:
                    if player in current_config:
                        updated_config[player] = current_config[player]
                    # Neue Spieler erhalten Standardeinstellungen (können ausgelost werden)
                team.set_player_config(updated_config)

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

    # Alle Teams für Dropdown in Spieler-Zuordnung laden
    all_teams = Team.query.order_by(Team.name).all()
    return render_template('edit_team.html', title='Team bearbeiten', form=form, team=team, all_teams=all_teams)

@admin_bp.route('/add_player', methods=['GET', 'POST'])
@login_required
def add_player():
    if not isinstance(current_user, Admin): 
        return redirect(url_for('main.index'))
    
    from app.forms import AddPlayerForm
    form = AddPlayerForm()
    
    if form.validate_on_submit():
        team = Team.query.get_or_404(form.team_id.data)
        player_name = form.player_name.data.strip()
        
        # Prüfe ob Spieler bereits in einem Team ist
        existing_player = PlayerRegistration.query.filter_by(player_name=player_name).first()
        if existing_player:
            flash(f'Spieler "{player_name}" ist bereits registriert.', 'warning')
            return render_template('add_player.html', title='Spieler hinzufügen', form=form)
        
        # Erstelle neue Spielerregistrierung
        welcome_session = WelcomeSession.get_active_session()
        if not welcome_session:
            # Erstelle eine neue Session falls keine aktiv
            welcome_session = WelcomeSession()
            welcome_session.is_active = True
            db.session.add(welcome_session)
            db.session.commit()
        
        player_registration = PlayerRegistration(
            welcome_session_id=welcome_session.id,
            player_name=player_name,
            assigned_team_id=team.id
        )
        db.session.add(player_registration)
        
        # Füge Spieler auch zur Team-Mitgliederliste hinzu
        if team.members:
            current_members = [m.strip() for m in team.members.split(',') if m.strip()]
            if player_name not in current_members:
                current_members.append(player_name)
                team.members = ', '.join(current_members)
        else:
            team.members = player_name
        
        db.session.commit()
        flash(f'Spieler "{player_name}" wurde erfolgreich zu Team "{team.name}" hinzugefügt.', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    
    return render_template('add_player.html', title='Spieler hinzufügen', form=form)

@admin_bp.route('/api/update_player_selection_status/<int:team_id>', methods=['POST'])
@login_required
def update_player_selection_status(team_id):
    """AJAX-Route zum Aktualisieren des Auslosungs-Status eines Spielers"""
    if not isinstance(current_user, Admin):
        return jsonify({'success': False, 'message': 'Keine Berechtigung'}), 403
    
    try:
        team = Team.query.get_or_404(team_id)
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Keine Daten erhalten'}), 400
        
        player_name = data.get('player_name')
        can_be_selected = data.get('can_be_selected', True)
        
        if not player_name:
            return jsonify({'success': False, 'message': 'Spielername fehlt'}), 400
        
        # Prüfe ob Spieler wirklich im Team ist
        if team.members:
            members_list = [m.strip() for m in team.members.split(',') if m.strip()]
            if player_name not in members_list:
                return jsonify({'success': False, 'message': 'Spieler nicht im Team gefunden'}), 400
        else:
            return jsonify({'success': False, 'message': 'Team hat keine Mitglieder'}), 400
        
        # Status aktualisieren
        team.update_player_selection_status(player_name, can_be_selected)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Auslosungs-Status für {player_name} aktualisiert',
            'player_name': player_name,
            'can_be_selected': can_be_selected
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Aktualisieren des Spieler-Status: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Ein Fehler ist aufgetreten'}), 500

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

# =============================================================================
# PLAYER MANAGEMENT AJAX ROUTES
# =============================================================================

@admin_bp.route('/update_player_name', methods=['POST'])
@login_required
def update_player_name():
    if not isinstance(current_user, Admin):
        return jsonify({'success': False, 'error': 'Nicht autorisiert'})
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Keine Daten erhalten'})
            
        player_id = data.get('player_id')
        new_name = data.get('new_name', '').strip()
        
        if not player_id or not new_name:
            return jsonify({'success': False, 'error': 'Ungültige Parameter'})
        
        if len(new_name) < 2:
            return jsonify({'success': False, 'error': 'Spielername muss mindestens 2 Zeichen lang sein'})
        
        player = PlayerRegistration.query.get(player_id)
        if not player:
            return jsonify({'success': False, 'error': 'Spieler nicht gefunden'})
        player.player_name = new_name
        db.session.commit()
        
        return jsonify({'success': True})
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Update des Spielernamens: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Serverfehler beim Speichern'})

def _update_team_members_from_registrations():
    """Aktualisiert die Team-Member-Listen basierend auf PlayerRegistration-Zuweisungen"""
    try:
        # Alle Teams holen
        teams = Team.query.all()
        
        # Für jedes Team die Members-Liste aktualisieren
        for team in teams:
            # Hole alle Spieler die diesem Team zugewiesen sind
            assigned_players = PlayerRegistration.query.filter_by(assigned_team_id=team.id).all()
            
            # Erstelle neue Members-Liste
            member_names = [player.player_name for player in assigned_players if player.player_name]
            
            # Aktualisiere das Team
            team.members = ', '.join(member_names) if member_names else None
            
        current_app.logger.info("Team-Member-Listen wurden aktualisiert")
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Aktualisieren der Team-Member-Listen: {e}", exc_info=True)
        raise

@admin_bp.route('/reassign_player', methods=['POST'])
@login_required
def reassign_player():
    if not isinstance(current_user, Admin):
        return jsonify({'success': False, 'error': 'Nicht autorisiert'})
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Keine Daten erhalten'})
            
        player_id = data.get('player_id')
        new_team_id = data.get('new_team_id')
        
        if not player_id:
            return jsonify({'success': False, 'error': 'Ungültige Spieler-ID'})
        
        player = PlayerRegistration.query.get(player_id)
        if not player:
            return jsonify({'success': False, 'error': 'Spieler nicht gefunden'})
        
        # Validiere neues Team (falls angegeben)
        if new_team_id and new_team_id != 0:
            new_team = Team.query.get(new_team_id)
            if not new_team:
                return jsonify({'success': False, 'error': 'Team nicht gefunden'})
            player.assigned_team_id = new_team_id
        else:
            # Kein Team zuweisen
            player.assigned_team_id = None
        
        # Aktualisiere die Team-Member-Listen nach der Zuweisung
        _update_team_members_from_registrations()
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Spieler erfolgreich zugewiesen'})
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler bei der Team-Zuweisung: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Serverfehler bei der Team-Zuweisung'})

@admin_bp.route('/add_player_to_team', methods=['POST'])
@login_required
def add_player_to_team():
    """Fügt einen neuen Spieler zu einem bestehenden Team hinzu"""
    current_app.logger.info("=== ADD PLAYER TO TEAM ROUTE REACHED ===")
    
    if not isinstance(current_user, Admin):
        current_app.logger.error("Not authorized - not admin user")
        return jsonify({'success': False, 'error': 'Nicht autorisiert'})
    
    try:
        data = request.get_json()
        current_app.logger.info(f"Request data: {data}")
        
        if not data:
            current_app.logger.error("No JSON data received")
            return jsonify({'success': False, 'error': 'Keine Daten erhalten'})
        
        team_id = data.get('team_id')
        player_name = data.get('player_name', '').strip()
        
        current_app.logger.info(f"Adding player '{player_name}' to team {team_id}")
        
        if not team_id or not player_name:
            return jsonify({'success': False, 'error': 'Team-ID und Spielername sind erforderlich'})
        
        if len(player_name) < 2:
            return jsonify({'success': False, 'error': 'Spielername muss mindestens 2 Zeichen lang sein'})
        
        if len(player_name) > 50:
            return jsonify({'success': False, 'error': 'Spielername ist zu lang (max. 50 Zeichen)'})
        
        # Team finden
        team = Team.query.get(team_id)
        if not team:
            return jsonify({'success': False, 'error': 'Team nicht gefunden'})
        
        # Prüfe ob Name bereits in diesem Team existiert
        if team.members:
            existing_members = [m.strip() for m in team.members.split(',') if m.strip()]
            if player_name in existing_members:
                return jsonify({'success': False, 'error': 'Spieler ist bereits im Team'})
        
        # Prüfe ob Name bereits in PlayerRegistration existiert
        existing_player = PlayerRegistration.query.filter_by(player_name=player_name).first()
        if existing_player:
            return jsonify({'success': False, 'error': 'Spielername ist bereits vergeben'})
        
        # Prüfe ob bereits ein aktives Spiel läuft
        active_game_session = GameSession.query.filter_by(is_active=True).first()
        
        # Finde oder erstelle aktive WelcomeSession NUR wenn kein aktives Spiel läuft
        welcome_session = WelcomeSession.get_active_session()
        if not welcome_session and not active_game_session:
            # Erstelle neue WelcomeSession nur falls keine aktiv ist UND kein Spiel läuft
            # Erst alle anderen deaktivieren
            WelcomeSession.query.update({'is_active': False})
            # Dann neue Session erstellen
            welcome_session = WelcomeSession(is_active=True)
            db.session.add(welcome_session)
            db.session.commit()  # Commit um ID zu bekommen
            current_app.logger.info("Neue WelcomeSession erstellt für Spieler-Hinzufügung")
        elif active_game_session:
            # Spiel läuft bereits - keine WelcomeSession erstellen/aktivieren
            current_app.logger.info("Aktives Spiel erkannt - keine WelcomeSession für Spieler-Hinzufügung erstellt")
        
        # Erstelle neue PlayerRegistration nur wenn WelcomeSession existiert
        new_player = None  # Initialisiere Variable
        if welcome_session:
            new_player = PlayerRegistration(
                welcome_session_id=welcome_session.id,
                player_name=player_name,
                assigned_team_id=team_id,
                registration_time=datetime.utcnow()
            )
            db.session.add(new_player)
        
        # Aktualisiere Team-Members-Liste
        if team.members:
            existing_members = [m.strip() for m in team.members.split(',') if m.strip()]
        else:
            existing_members = []
        
        existing_members.append(player_name)
        team.members = ', '.join(existing_members)
        
        # Aktualisiere player_config für neuen Spieler (kann ausgelost werden)
        player_config = team.get_player_config() or {}
        player_config[player_name] = {'can_be_selected': True}
        team.set_player_config(player_config)
        
        db.session.commit()
        
        response_data = {
            'success': True, 
            'message': f'Spieler {player_name} erfolgreich zum Team hinzugefügt',
            'player_name': player_name
        }
        
        # Füge player_id nur hinzu wenn PlayerRegistration erstellt wurde
        if new_player:
            response_data['player_id'] = new_player.id
        
        return jsonify(response_data)
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Hinzufügen des Spielers: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Serverfehler: {str(e)}'})

@admin_bp.route('/remove_team_member', methods=['POST'])
@login_required
def remove_team_member():
    """Entfernt einen Spieler aus der team.members Liste (für nachträglich hinzugefügte Spieler)"""
    if not isinstance(current_user, Admin):
        return jsonify({'success': False, 'error': 'Nicht autorisiert'})
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Keine Daten erhalten'})
        
        team_id = data.get('team_id')
        player_name = data.get('player_name', '').strip()
        
        if not team_id or not player_name:
            return jsonify({'success': False, 'error': 'Team-ID und Spielername sind erforderlich'})
        
        # Team finden
        team = Team.query.get(team_id)
        if not team:
            return jsonify({'success': False, 'error': 'Team nicht gefunden'})
        
        # Entferne Spieler aus team.members
        if not team.members:
            return jsonify({'success': False, 'error': 'Keine Team-Mitglieder vorhanden'})
        
        current_members = [m.strip() for m in team.members.split(',') if m.strip()]
        if player_name not in current_members:
            return jsonify({'success': False, 'error': 'Spieler ist nicht in der Team-Mitgliederliste'})
        
        # Entferne Spieler aus der Liste
        current_members.remove(player_name)
        team.members = ', '.join(current_members) if current_members else None
        
        # Entferne auch aus player_config falls vorhanden
        player_config = team.get_player_config() or {}
        if player_name in player_config:
            del player_config[player_name]
            team.set_player_config(player_config)
        
        db.session.commit()
        
        current_app.logger.info(f"Spieler '{player_name}' aus Team '{team.name}' entfernt (team.members)")
        
        return jsonify({
            'success': True,
            'message': f'Spieler "{player_name}" erfolgreich aus Team entfernt'
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Entfernen des Team-Mitglieds: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Serverfehler: {str(e)}'})

@admin_bp.route('/move_team_member', methods=['POST'])
@login_required
def move_team_member():
    """Verschiebt einen Team-Mitglied zwischen Teams (für nachträglich hinzugefügte Spieler)"""
    if not isinstance(current_user, Admin):
        return jsonify({'success': False, 'error': 'Nicht autorisiert'})
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Keine Daten erhalten'})
        
        current_team_id = data.get('current_team_id')
        player_name = data.get('player_name', '').strip()
        new_team_id = data.get('new_team_id')
        
        if not current_team_id or not player_name:
            return jsonify({'success': False, 'error': 'Team-ID und Spielername sind erforderlich'})
        
        # Aktuelles Team finden
        current_team = Team.query.get(current_team_id)
        if not current_team:
            return jsonify({'success': False, 'error': 'Aktuelles Team nicht gefunden'})
        
        # Entferne Spieler aus aktuellem Team
        if not current_team.members:
            return jsonify({'success': False, 'error': 'Keine Team-Mitglieder im aktuellen Team'})
        
        current_members = [m.strip() for m in current_team.members.split(',') if m.strip()]
        if player_name not in current_members:
            return jsonify({'success': False, 'error': 'Spieler ist nicht im aktuellen Team'})
        
        # Entferne aus aktuellem Team
        current_members.remove(player_name)
        current_team.members = ', '.join(current_members) if current_members else None
        
        # Entferne auch aus player_config des aktuellen Teams
        current_config = current_team.get_player_config() or {}
        if player_name in current_config:
            del current_config[player_name]
            current_team.set_player_config(current_config)
        
        # Füge zu neuem Team hinzu (falls nicht 0 = kein Team)
        if new_team_id and new_team_id != 0:
            new_team = Team.query.get(new_team_id)
            if not new_team:
                return jsonify({'success': False, 'error': 'Neues Team nicht gefunden'})
            
            # Prüfe ob Spieler bereits im neuen Team ist
            if new_team.members:
                new_team_members = [m.strip() for m in new_team.members.split(',') if m.strip()]
                if player_name in new_team_members:
                    return jsonify({'success': False, 'error': 'Spieler ist bereits im Ziel-Team'})
                new_team_members.append(player_name)
            else:
                new_team_members = [player_name]
            
            new_team.members = ', '.join(new_team_members)
            
            # Füge auch zu player_config des neuen Teams hinzu
            new_config = new_team.get_player_config() or {}
            new_config[player_name] = {'can_be_selected': True}
            new_team.set_player_config(new_config)
        
        db.session.commit()
        
        if new_team_id and new_team_id != 0:
            current_app.logger.info(f"Spieler '{player_name}' von Team '{current_team.name}' zu Team '{new_team.name}' verschoben")
            message = f'Spieler "{player_name}" erfolgreich zu neuem Team verschoben'
        else:
            current_app.logger.info(f"Spieler '{player_name}' aus Team '{current_team.name}' entfernt (kein neues Team)")
            message = f'Spieler "{player_name}" erfolgreich aus Team entfernt'
        
        return jsonify({
            'success': True,
            'message': message
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Verschieben des Team-Mitglieds: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Serverfehler: {str(e)}'})

@admin_bp.route('/update_team_member_name', methods=['POST'])
@login_required
def update_team_member_name():
    """Ändert den Namen eines Team-Mitglieds (für nachträglich hinzugefügte Spieler)"""
    if not isinstance(current_user, Admin):
        return jsonify({'success': False, 'error': 'Nicht autorisiert'})
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Keine Daten erhalten'})
        
        team_id = data.get('team_id')
        old_player_name = data.get('old_player_name', '').strip()
        new_player_name = data.get('new_player_name', '').strip()
        
        if not team_id or not old_player_name or not new_player_name:
            return jsonify({'success': False, 'error': 'Team-ID, alter und neuer Spielername sind erforderlich'})
        
        if len(new_player_name) < 2:
            return jsonify({'success': False, 'error': 'Neuer Spielername muss mindestens 2 Zeichen lang sein'})
        
        if len(new_player_name) > 50:
            return jsonify({'success': False, 'error': 'Neuer Spielername ist zu lang (max. 50 Zeichen)'})
        
        # Team finden
        team = Team.query.get(team_id)
        if not team:
            return jsonify({'success': False, 'error': 'Team nicht gefunden'})
        
        # Prüfe ob alter Name in team.members existiert
        if not team.members:
            return jsonify({'success': False, 'error': 'Keine Team-Mitglieder vorhanden'})
        
        current_members = [m.strip() for m in team.members.split(',') if m.strip()]
        if old_player_name not in current_members:
            return jsonify({'success': False, 'error': 'Alter Spielername nicht in Team-Mitgliederliste gefunden'})
        
        # Prüfe ob neuer Name bereits existiert (in diesem Team oder als PlayerRegistration)
        if new_player_name in current_members:
            return jsonify({'success': False, 'error': 'Neuer Spielername existiert bereits in diesem Team'})
        
        existing_registration = PlayerRegistration.query.filter_by(player_name=new_player_name).first()
        if existing_registration:
            return jsonify({'success': False, 'error': 'Neuer Spielername ist bereits als registrierter Spieler vergeben'})
        
        # Ändere Namen in team.members
        updated_members = []
        for member in current_members:
            if member == old_player_name:
                updated_members.append(new_player_name)
            else:
                updated_members.append(member)
        
        team.members = ', '.join(updated_members)
        
        # Ändere auch Namen in player_config falls vorhanden
        player_config = team.get_player_config() or {}
        if old_player_name in player_config:
            player_config[new_player_name] = player_config[old_player_name]
            del player_config[old_player_name]
            team.set_player_config(player_config)
        
        db.session.commit()
        
        current_app.logger.info(f"Team-Mitglied '{old_player_name}' in Team '{team.name}' zu '{new_player_name}' umbenannt")
        
        return jsonify({
            'success': True,
            'message': f'Spielername erfolgreich von "{old_player_name}" zu "{new_player_name}" geändert'
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Ändern des Team-Mitglied-Namens: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Serverfehler: {str(e)}'})

@admin_bp.route('/delete_player', methods=['POST'])
@login_required
def delete_player():
    """Löscht einen Spieler aus der PlayerRegistration Tabelle"""
    if not isinstance(current_user, Admin):
        return jsonify({'success': False, 'error': 'Nicht autorisiert'})
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Keine Daten erhalten'})
        
        player_id = data.get('player_id')
        if not player_id:
            return jsonify({'success': False, 'error': 'Spieler-ID ist erforderlich'})
        
        # Spieler finden
        player = PlayerRegistration.query.get(player_id)
        if not player:
            return jsonify({'success': False, 'error': 'Spieler nicht gefunden'})
        
        # Spieler aus Team-Members entfernen falls vorhanden
        if player.assigned_team_id:
            team = Team.query.get(player.assigned_team_id)
            if team and team.members:
                existing_members = [m.strip() for m in team.members.split(',') if m.strip()]
                if player.player_name in existing_members:
                    existing_members.remove(player.player_name)
                    team.members = ', '.join(existing_members) if existing_members else None
                    
                    # Auch aus player_config entfernen
                    player_config = team.get_player_config() or {}
                    if player.player_name in player_config:
                        del player_config[player.player_name]
                        team.set_player_config(player_config)
        
        # Profilbild löschen falls vorhanden
        if player.profile_image_path:
            import os
            image_path = os.path.join(current_app.root_path, 'static', player.profile_image_path.lstrip('/static/'))
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)
                    current_app.logger.info(f"Profilbild gelöscht: {image_path}")
                except Exception as e:
                    current_app.logger.warning(f"Fehler beim Löschen des Profilbildes: {e}")
        
        # Spieler aus Datenbank löschen
        db.session.delete(player)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Spieler {player.player_name} erfolgreich gelöscht'
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Löschen des Spielers: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Serverfehler: {str(e)}'})

@admin_bp.route('/upload_team_player_image', methods=['POST'])
@login_required
def upload_team_player_image():
    """Upload eines Profilbildes für einen Team-Spieler"""
    if not isinstance(current_user, Admin):
        return jsonify({'success': False, 'error': 'Nicht autorisiert'})
    
    try:
        import base64
        import binascii
        import os
        from PIL import Image
        import io
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Keine Daten erhalten'})
        
        team_id = data.get('team_id')
        player_name = data.get('player_name', '').strip()
        image_data = data.get('image_data', '')
        
        if not team_id or not player_name:
            return jsonify({'success': False, 'error': 'Team-ID und Spielername sind erforderlich'})
        
        if not image_data:
            return jsonify({'success': False, 'error': 'Bilddaten fehlen'})
        
        # Team finden
        team = Team.query.get(team_id)
        if not team:
            return jsonify({'success': False, 'error': 'Team nicht gefunden'})
        
        # Spieler finden
        player = PlayerRegistration.query.filter_by(
            player_name=player_name,
            assigned_team_id=team_id
        ).first()
        
        if not player:
            return jsonify({'success': False, 'error': 'Spieler nicht gefunden'})
        
        # Entferne data:image/...;base64, prefix falls vorhanden
        if 'base64,' in image_data:
            image_data = image_data.split('base64,')[1]
        elif image_data.startswith('data:'):
            parts = image_data.split(',', 1)
            if len(parts) > 1:
                image_data = parts[1]
        
        # Dekodiere Base64
        try:
            image_bytes = base64.b64decode(image_data)
        except (binascii.Error, ValueError) as e:
            current_app.logger.error(f"Base64 decode error: {e}")
            return jsonify({'success': False, 'error': 'Ungültige Bilddaten'})
        
        # Erstelle PIL Image
        try:
            image = Image.open(io.BytesIO(image_bytes))
            image = image.convert('RGB')  # Konvertiere zu RGB falls nötig
        except Exception as e:
            current_app.logger.error(f"Image processing error: {e}")
            return jsonify({'success': False, 'error': 'Bild konnte nicht verarbeitet werden'})
        
        # Resize auf 150x150
        image = image.resize((150, 150), Image.Resampling.LANCZOS)
        
        # Stelle sicher, dass das profile_images Verzeichnis existiert
        profile_dir = os.path.join(current_app.static_folder, 'profile_images')
        if not os.path.exists(profile_dir):
            os.makedirs(profile_dir, exist_ok=True)
        
        # Erstelle Dateinamen
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{team_id}_{player_name}_{timestamp}.jpg"
        filepath = os.path.join(profile_dir, filename)
        
        # Speichere Bild
        try:
            image.save(filepath, 'JPEG', quality=85, optimize=True)
            current_app.logger.info(f"Profile image saved: {filepath}")
        except Exception as e:
            current_app.logger.error(f"Error saving image: {e}")
            return jsonify({'success': False, 'error': 'Bild konnte nicht gespeichert werden'})
        
        # Aktualisiere PlayerRegistration
        player.profile_image_path = f"profile_images/{filename}"
        
        # Aktualisiere auch Team profile_images
        team.set_profile_image(player_name, f"profile_images/{filename}")
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Profilbild erfolgreich hochgeladen',
            'image_path': f"profile_images/{filename}"
        })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Upload des Profilbildes: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Serverfehler beim Upload'})

@admin_bp.route('/api/update_player_emoji', methods=['POST'])
@login_required
def update_player_emoji():
    """API-Route zum Ändern des Spieler-Emojis"""
    if not isinstance(current_user, Admin):
        return jsonify({'success': False, 'error': 'Nicht autorisiert'})
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Keine Daten erhalten'})
        
        team_id = data.get('team_id')
        player_name = data.get('player_name', '').strip()
        new_emoji = data.get('emoji', '').strip()
        player_type = data.get('player_type', 'registration')  # 'registration' oder 'member'
        
        if not team_id or not player_name:
            return jsonify({'success': False, 'error': 'Team-ID und Spielername sind erforderlich'})
        
        if not new_emoji:
            return jsonify({'success': False, 'error': 'Emoji ist erforderlich'})
        
        # Team finden
        team = Team.query.get(team_id)
        if not team:
            return jsonify({'success': False, 'error': 'Team nicht gefunden'})
        
        if player_type == 'registration':
            # Spieler in PlayerRegistration finden
            player = PlayerRegistration.query.filter_by(
                player_name=player_name,
                assigned_team_id=team_id
            ).first()
            
            if not player:
                return jsonify({'success': False, 'error': 'Registrierter Spieler nicht gefunden'})
            
            # CLEANUP: Entferne vorhandenes Profilbild falls vorhanden (Wechsel von Bild zu Emoji)
            if player.profile_image_path:
                old_file_path = os.path.join(current_app.static_folder, player.profile_image_path)
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
                    current_app.logger.info(f"Removed old profile image: {old_file_path}")
                player.profile_image_path = None
            
            # Emoji in player_config speichern
            player_config = team.get_player_config()
            if player_name not in player_config:
                player_config[player_name] = {}
            player_config[player_name]['emoji'] = new_emoji
            
            # Speichere in Team player_config
            team.set_player_config(player_config)
            
        else:  # player_type == 'member'
            # Spieler in team.members (nachträglich hinzugefügter Spieler)
            members = team.members.split(',') if team.members else []
            clean_members = [m.strip() for m in members]
            
            if player_name not in clean_members:
                return jsonify({'success': False, 'error': 'Team-Mitglied nicht gefunden'})
            
            # CLEANUP: Entferne vorhandenes Profilbild falls vorhanden (Wechsel von Bild zu Emoji)
            profile_images = team.get_profile_images() or {}
            if player_name in profile_images:
                old_file_path = os.path.join(current_app.static_folder, profile_images[player_name])
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
                    current_app.logger.info(f"Removed old profile image: {old_file_path}")
                
                del profile_images[player_name]
                team.profile_images = json.dumps(profile_images)
            
            # Emoji in player_config speichern
            player_config = team.get_player_config()
            if player_name not in player_config:
                player_config[player_name] = {}
            player_config[player_name]['emoji'] = new_emoji
            
            # Speichere in Team player_config
            team.set_player_config(player_config)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Emoji für {player_name} erfolgreich geändert',
            'new_emoji': new_emoji
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Ändern des Player-Emojis: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Serverfehler beim Ändern des Emojis'})

@admin_bp.route('/api/update_player_image', methods=['POST'])
@login_required
def update_player_image():
    """API-Route zum Ändern/Hochladen eines neuen Spieler-Profilbildes"""
    if not isinstance(current_user, Admin):
        return jsonify({'success': False, 'error': 'Nicht autorisiert'})
    
    try:
        import base64
        import binascii
        import os
        from PIL import Image
        import io
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Keine Daten erhalten'})
        
        team_id = data.get('team_id')
        player_name = data.get('player_name', '').strip()
        image_data = data.get('image_data', '')
        player_type = data.get('player_type', 'registration')  # 'registration' oder 'member'
        action = data.get('action', 'upload')  # 'upload' oder 'remove'
        
        if not team_id or not player_name:
            return jsonify({'success': False, 'error': 'Team-ID und Spielername sind erforderlich'})
        
        # Team finden
        team = Team.query.get(team_id)
        if not team:
            return jsonify({'success': False, 'error': 'Team nicht gefunden'})
        
        if action == 'remove':
            # Profilbild entfernen
            if player_type == 'registration':
                player = PlayerRegistration.query.filter_by(
                    player_name=player_name,
                    assigned_team_id=team_id
                ).first()
                
                if not player:
                    return jsonify({'success': False, 'error': 'Registrierter Spieler nicht gefunden'})
                
                # Entferne Profilbild-Datei falls vorhanden
                if player.profile_image_path:
                    old_file_path = os.path.join(current_app.static_folder, player.profile_image_path)
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)
                    player.profile_image_path = None
            
            else:  # member
                # Prüfe ob Spieler in team.members existiert
                members = team.members.split(',') if team.members else []
                clean_members = [m.strip() for m in members]
                
                if player_name not in clean_members:
                    return jsonify({'success': False, 'error': 'Team-Mitglied nicht gefunden'})
                
                # Team-Mitglied Profilbild entfernen
                profile_images = team.get_profile_images() or {}
                if player_name in profile_images:
                    # Entferne Datei falls vorhanden
                    old_file_path = os.path.join(current_app.static_folder, profile_images[player_name])
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)
                    
                    del profile_images[player_name]
                    team.profile_images = json.dumps(profile_images)
            
            db.session.commit()
            return jsonify({
                'success': True, 
                'message': f'Profilbild für {player_name} erfolgreich entfernt'
            })
        
        elif action == 'upload':
            # Neues Profilbild hochladen
            if not image_data:
                return jsonify({'success': False, 'error': 'Bilddaten fehlen'})
            
            # Entferne data:image/...;base64, prefix falls vorhanden
            if 'base64,' in image_data:
                image_data = image_data.split('base64,')[1]
            elif image_data.startswith('data:'):
                parts = image_data.split(',', 1)
                if len(parts) > 1:
                    image_data = parts[1]
            
            # Dekodiere Base64
            try:
                image_binary = base64.b64decode(image_data)
            except (binascii.Error, ValueError) as e:
                return jsonify({'success': False, 'error': 'Ungültige Base64-Daten'})
            
            # Validiere und verarbeite Bild
            try:
                img = Image.open(io.BytesIO(image_binary))
                
                # Konvertiere zu RGB falls nötig
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize auf 150x150 und schneide zu Kreis
                img = img.resize((150, 150), Image.Resampling.LANCZOS)
                
                # Erstelle Upload-Verzeichnis
                upload_dir = os.path.join(current_app.static_folder, 'team_images')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Generiere Dateinamen
                import time
                filename = f"player_{team_id}_{player_name}_{int(time.time())}.jpg"
                file_path = os.path.join(upload_dir, filename)
                relative_path = f"team_images/{filename}"
                
                # Speichere Bild
                img.save(file_path, 'JPEG', quality=85, optimize=True)
                
                # Aktualisiere Datenbankrecord
                if player_type == 'registration':
                    player = PlayerRegistration.query.filter_by(
                        player_name=player_name,
                        assigned_team_id=team_id
                    ).first()
                    
                    if not player:
                        return jsonify({'success': False, 'error': 'Registrierter Spieler nicht gefunden'})
                    
                    # Entferne altes Profilbild
                    if player.profile_image_path:
                        old_file_path = os.path.join(current_app.static_folder, player.profile_image_path)
                        if os.path.exists(old_file_path):
                            os.remove(old_file_path)
                    
                    # CLEANUP: Entferne Emoji-Config falls vorhanden (Wechsel von Emoji zu Bild)
                    player_config = team.get_player_config()
                    if player_name in player_config and 'emoji' in player_config[player_name]:
                        del player_config[player_name]['emoji']
                        # Entferne den ganzen Player-Eintrag wenn er leer ist
                        if not player_config[player_name]:
                            del player_config[player_name]
                        team.set_player_config(player_config)
                        current_app.logger.info(f"Removed emoji config for player: {player_name}")
                    
                    player.profile_image_path = relative_path
                
                else:  # member
                    # Prüfe ob Spieler in team.members existiert
                    members = team.members.split(',') if team.members else []
                    clean_members = [m.strip() for m in members]
                    
                    if player_name not in clean_members:
                        return jsonify({'success': False, 'error': 'Team-Mitglied nicht gefunden'})
                    
                    # Team-Mitglied Profilbild aktualisieren
                    profile_images = team.get_profile_images() or {}
                    
                    # Entferne altes Bild falls vorhanden
                    if player_name in profile_images:
                        old_file_path = os.path.join(current_app.static_folder, profile_images[player_name])
                        if os.path.exists(old_file_path):
                            os.remove(old_file_path)
                    
                    # CLEANUP: Entferne Emoji-Config falls vorhanden (Wechsel von Emoji zu Bild)
                    player_config = team.get_player_config()
                    if player_name in player_config and 'emoji' in player_config[player_name]:
                        del player_config[player_name]['emoji']
                        # Entferne den ganzen Player-Eintrag wenn er leer ist
                        if not player_config[player_name]:
                            del player_config[player_name]
                        team.set_player_config(player_config)
                        current_app.logger.info(f"Removed emoji config for player: {player_name}")
                    
                    profile_images[player_name] = relative_path
                    team.profile_images = json.dumps(profile_images)
                
                db.session.commit()
                
                return jsonify({
                    'success': True, 
                    'message': f'Profilbild für {player_name} erfolgreich aktualisiert',
                    'image_path': relative_path
                })
                
            except Exception as img_error:
                return jsonify({'success': False, 'error': f'Fehler bei der Bildverarbeitung: {str(img_error)}'})
        
        else:
            return jsonify({'success': False, 'error': 'Ungültige Aktion'})
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Aktualisieren des Player-Bildes: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Serverfehler beim Aktualisieren des Bildes'})

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

@admin_bp.route('/sync_folders')
@login_required
def sync_folders():
    """Synchronisiert Minigame-Ordner zwischen Dateisystem und Datenbank"""
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    try:
        from app.admin.minigame_utils import sync_folders_to_database
        added_count = sync_folders_to_database()
        
        if added_count > 0:
            flash(f'Erfolgreich {added_count} neue Ordner zur Datenbank hinzugefügt.', 'success')
        else:
            flash('Alle Ordner sind bereits synchronisiert.', 'info')
            
    except Exception as e:
        current_app.logger.error(f"Fehler beim Synchronisieren der Ordner: {e}", exc_info=True)
        flash('Fehler beim Synchronisieren der Ordner.', 'danger')
    
    return redirect(url_for('admin.manage_folders'))

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
                'type': form.type.data,
                'player_count': form.player_count.data
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
                'type': form.type.data,
                'player_count': form.player_count.data
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
    
    # Erstelle ein temporäres Objekt für das Form mit korrekter Mapping der Multiple-Choice-Optionen
    form_data = dict(question)  # Kopiere die Frage-Daten
    
    # Mappe Multiple-Choice-Optionen zu einzelnen Feldern
    if question.get('question_type') == 'multiple_choice' and 'options' in question:
        options = question['options']
        form_data['option_1'] = options[0] if len(options) > 0 else ''
        form_data['option_2'] = options[1] if len(options) > 1 else ''
        form_data['option_3'] = options[2] if len(options) > 2 else ''
        form_data['option_4'] = options[3] if len(options) > 3 else ''
    
    question_obj = type('obj', (object,), form_data)()
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
            
            # Automatisches Backup der neuen Runde
            try:
                from app.admin.minigame_utils import save_round_to_filesystem
                save_round_to_filesystem(round_obj)
            except Exception as backup_e:
                current_app.logger.warning(f"Backup der Runde '{round_obj.name}' fehlgeschlagen: {backup_e}")
            
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
            
            # Automatisches Backup der aktualisierten Runde
            try:
                from app.admin.minigame_utils import save_round_to_filesystem
                save_round_to_filesystem(round_obj)
            except Exception as backup_e:
                current_app.logger.warning(f"Backup der aktualisierten Runde '{round_obj.name}' fehlgeschlagen: {backup_e}")
            
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
            round_name = round_obj.name  # Namen vor dem Löschen speichern
            
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
            
            # Lösche auch das Backup aus dem Dateisystem
            try:
                from app.admin.minigame_utils import delete_round_from_filesystem
                delete_round_from_filesystem(round_name)
            except Exception as backup_e:
                current_app.logger.warning(f"Löschen des Backups für Runde '{round_name}' fehlgeschlagen: {backup_e}")
            
            flash(f"Spielrunde '{round_name}' erfolgreich gelöscht.", 'success')
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
        
        # Stelle sicher, dass die Runde rundenspezifische Konfigurationen hat
        round_obj.ensure_round_configurations()
        
        # Aktiviere die Runde (lädt automatisch die Konfigurationen)
        round_obj.activate()
        
        # Beim Wechseln der Runde: Gespielte Inhalte zurücksetzen
        active_session = GameSession.query.filter_by(is_active=True).first()
        if active_session:
            reset_played_content_for_session(active_session)
            
            event = GameEvent(
                game_session_id=active_session.id,
                event_type="round_activated",
                description=f"Spielrunde '{round_obj.name}' wurde aktiviert. Gespielte Inhalte und Konfigurationen wurden geladen."
            )
            db.session.add(event)
            db.session.commit()
        
        flash(f"Spielrunde '{round_obj.name}' wurde aktiviert. Rundenspezifische Konfigurationen wurden geladen.", 'success')
    except Exception as e:
        current_app.logger.error(f"Fehler beim Aktivieren der Spielrunde: {e}", exc_info=True)
        flash('Ein Fehler ist beim Aktivieren der Spielrunde aufgetreten.', 'danger')
    
    return redirect(url_for('admin.manage_rounds'))

@admin_bp.route('/backup_rounds', methods=['GET', 'POST'])
@login_required
def backup_rounds():
    """Manuelle Sicherung und Wiederherstellung von Spielrunden"""
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'backup_all':
            try:
                backed_up_count = backup_all_rounds_before_db_reset()
                if backed_up_count > 0:
                    flash(f"✅ {backed_up_count} Runden erfolgreich gesichert!", 'success')
                else:
                    flash("ℹ️ Keine Runden zum Sichern gefunden.", 'info')
            except Exception as e:
                current_app.logger.error(f"Fehler beim Sichern aller Runden: {e}", exc_info=True)
                flash("❌ Fehler beim Sichern der Runden.", 'danger')
        
        elif action == 'restore_all':
            try:
                restored_count = restore_rounds_to_database()
                if restored_count > 0:
                    flash(f"✅ {restored_count} Runden erfolgreich wiederhergestellt!", 'success')
                else:
                    flash("ℹ️ Keine Runden zum Wiederherstellen gefunden.", 'info')
            except Exception as e:
                current_app.logger.error(f"Fehler beim Wiederherstellen der Runden: {e}", exc_info=True)
                flash("❌ Fehler beim Wiederherstellen der Runden.", 'danger')
        
        elif action == 'backup_single':
            round_id = request.form.get('round_id')
            try:
                round_obj = GameRound.query.get_or_404(round_id)
                if save_round_to_filesystem(round_obj):
                    flash(f"✅ Runde '{round_obj.name}' erfolgreich gesichert!", 'success')
                else:
                    flash(f"❌ Fehler beim Sichern der Runde '{round_obj.name}'.", 'danger')
            except Exception as e:
                current_app.logger.error(f"Fehler beim Sichern der Runde: {e}", exc_info=True)
                flash("❌ Fehler beim Sichern der Runde.", 'danger')
        
        elif action == 'delete_backup':
            round_name = request.form.get('round_name')
            try:
                if delete_round_from_filesystem(round_name):
                    flash(f"✅ Backup der Runde '{round_name}' erfolgreich gelöscht!", 'success')
                else:
                    flash(f"❌ Backup der Runde '{round_name}' nicht gefunden.", 'warning')
            except Exception as e:
                current_app.logger.error(f"Fehler beim Löschen des Backups: {e}", exc_info=True)
                flash("❌ Fehler beim Löschen des Backups.", 'danger')
        
        return redirect(url_for('admin.backup_rounds'))
    
    # GET request - zeige die Backup-Seite
    try:
        # Aktuelle Runden in der Datenbank
        db_rounds = GameRound.query.order_by(GameRound.name).all()
        
        # Gesicherte Runden im Dateisystem
        saved_rounds = load_rounds_from_filesystem()
        
        # Statistiken
        stats = {
            'db_rounds_count': len(db_rounds),
            'saved_rounds_count': len(saved_rounds),
            'total_storage_used': sum(len(json.dumps(r, ensure_ascii=False)) for r in saved_rounds)
        }
        
        return render_template('backup_rounds.html', 
                             db_rounds=db_rounds, 
                             saved_rounds=saved_rounds, 
                             stats=stats)
    except Exception as e:
        current_app.logger.error(f"Fehler beim Laden der Backup-Seite: {e}", exc_info=True)
        flash("❌ Fehler beim Laden der Backup-Informationen.", 'danger')
        return redirect(url_for('admin.manage_rounds'))

# WELCOME-SYSTEM ADMIN API-ENDPUNKTE

@admin_bp.route('/api/start-welcome', methods=['POST'])
@login_required
def start_welcome():
    """Startet das Welcome-System"""
    if not isinstance(current_user, Admin):
        current_app.logger.error(f"Unauthorized access attempt to start-welcome by: {current_user}")
        return jsonify({"success": False, "error": "Nur Admins können das Welcome-System starten"}), 403
    
    try:
        current_app.logger.info(f"Starting welcome system - requested by: {current_user.username}")
        
        # Prüfe ob bereits eine Session aktiv ist
        existing_session = WelcomeSession.get_active_session()
        if existing_session:
            return jsonify({"success": False, "error": "Welcome-System ist bereits aktiv"}), 400
        
        # Erstelle neue Welcome-Session
        welcome_session = WelcomeSession()
        welcome_session.activate()
        
        db.session.add(welcome_session)
        db.session.commit()
        
        current_app.logger.info(f"Welcome-System gestartet von Admin: {current_user.username}")
        
        return jsonify({
            "success": True,
            "message": "Welcome-System erfolgreich gestartet"
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Starten des Welcome-Systems: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Ein Fehler ist aufgetreten"}), 500

@admin_bp.route('/api/create-teams', methods=['POST'])
@login_required
def create_teams():
    """Erstellt Teams und verteilt Spieler zufällig"""
    if not isinstance(current_user, Admin):
        return jsonify({"success": False, "error": "Nur Admins können Teams erstellen"}), 403
    
    try:
        import random
        import string
        
        data = request.get_json()
        team_count = data.get('team_count')
        
        if not team_count or not isinstance(team_count, int) or team_count < 2 or team_count > 6:
            return jsonify({"success": False, "error": "Ungültige Team-Anzahl (2-6 erlaubt)"}), 400
        
        # Prüfe aktive Welcome-Session
        welcome_session = WelcomeSession.get_active_session()
        if not welcome_session:
            return jsonify({"success": False, "error": "Keine aktive Welcome-Session"}), 400
        
        if welcome_session.teams_created:
            return jsonify({"success": False, "error": "Teams wurden bereits erstellt"}), 400
        
        # Hole alle registrierten Spieler
        players = welcome_session.get_registered_players()
        if len(players) < team_count:
            return jsonify({"success": False, "error": f"Nicht genügend Spieler (mindestens {team_count} erforderlich)"}), 400
        
        # Mische Spieler zufällig mit verschiedenen Methoden für maximale Zufälligkeit
        players_list = list(players)
        current_app.logger.info(f"Spieler vor Mischen: {[p.player_name for p in players_list]}")
        
        # Mehrfaches Mischen für bessere Zufälligkeit
        import time
        random.seed(int(time.time() * 1000000) % 1000000)  # Microsekunden-basierter Seed
        for _ in range(3):
            random.shuffle(players_list)
        
        current_app.logger.info(f"Spieler nach Mischen: {[p.player_name for p in players_list]}")
        
        # Erstelle Teams mit zufälligen 6-stelligen Passwörtern
        created_teams = []
        
        for i in range(team_count):
            # Generiere 6-stelliges Passwort
            password = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            
            # Erstelle Team
            team = Team(
                name=f"Team {i+1}",
                members="",  # Wird später mit Spielernamen gefüllt
                welcome_password=password  # Speichere Klartext-Passwort für Welcome-System
            )
            team.set_password(password)
            
            db.session.add(team)
            db.session.flush()  # Damit wir die Team-ID bekommen
            
            created_teams.append({
                "team": team,
                "password": password,
                "members": []
            })
        
        # Verteile Spieler gleichmäßig auf Teams
        for i, player in enumerate(players_list):
            team_index = i % team_count
            selected_team = created_teams[team_index]
            
            # Setze Team-Zuordnung für Spieler
            player.assigned_team_id = selected_team["team"].id
            selected_team["members"].append(player.player_name)
            
            # Kopiere Profilbild ins Team falls vorhanden
            if player.profile_image_path:
                selected_team["team"].set_profile_image(player.player_name, player.profile_image_path)
        
        # Aktualisiere Team-Members String
        for team_data in created_teams:
            team_data["team"].members = ", ".join(team_data["members"])
        
        # Markiere Welcome-Session als teams_created
        welcome_session.teams_created = True
        welcome_session.team_count = team_count
        
        db.session.commit()
        
        current_app.logger.info(f"Teams erstellt von Admin {current_user.username}: {team_count} Teams mit {len(players_list)} Spielern")
        
        # Erstelle Response mit Team-Informationen (inkl. Passwörter für Admin)
        teams_info = []
        for team_data in created_teams:
            teams_info.append({
                "id": team_data["team"].id,
                "name": team_data["team"].name,
                "password": team_data["password"],
                "members": team_data["members"]
            })
        
        return jsonify({
            "success": True,
            "message": f"{team_count} Teams erfolgreich erstellt",
            "teams": teams_info
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Erstellen der Teams: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Ein Fehler ist aufgetreten"}), 500

@admin_bp.route('/api/end-welcome', methods=['POST'])
@login_required
def end_welcome():
    """Beendet Welcome-Modus und wechselt zum Spielbrett"""
    if not isinstance(current_user, Admin):
        return jsonify({"success": False, "error": "Nur Admins können das Welcome-System beenden"}), 403
    
    try:
        
        welcome_session = WelcomeSession.get_active_session()
        if not welcome_session:
            return jsonify({"success": False, "error": "Keine aktive Welcome-Session"}), 400
        
        if not welcome_session.teams_created:
            return jsonify({"success": False, "error": "Teams müssen erst erstellt werden"}), 400
        
        # Beende Welcome-Session
        welcome_session.deactivate()
        
        current_app.logger.info(f"Welcome-System beendet von Admin: {current_user.username}")
        
        return jsonify({
            "success": True,
            "message": "Welcome-System beendet, Spiel kann beginnen"
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Beenden des Welcome-Systems: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Ein Fehler ist aufgetreten"}), 500

@admin_bp.route('/api/end-registration', methods=['POST'])
@login_required
def end_registration():
    """Beendet die Registrierung komplett (ohne Teams zu erstellen)"""
    current_app.logger.info(f"end-registration aufgerufen von User: {current_user}")
    
    # CSRF Token Validierung mit JSON-Response bei Fehlern
    try:
        from flask_wtf.csrf import validate_csrf
        validate_csrf(request.headers.get('X-CSRFToken'))
    except Exception as csrf_error:
        current_app.logger.error(f"CSRF validation failed: {csrf_error}")
        return jsonify({"success": False, "error": "CSRF token validation failed"}), 400
    
    if not isinstance(current_user, Admin):
        current_app.logger.warning(f"Unauthorized access attempt by: {current_user}")
        return jsonify({"success": False, "error": "Nur Admins können die Registrierung beenden"}), 403
    
    try:
        current_app.logger.info("Suche nach aktiver Welcome-Session")
        welcome_session = WelcomeSession.get_active_session()
        if not welcome_session:
            current_app.logger.warning("Keine aktive Welcome-Session gefunden")
            return jsonify({"success": False, "error": "Keine aktive Welcome-Session"}), 400
        
        current_app.logger.info(f"Deaktiviere Welcome-Session {welcome_session.id}")
        # Beende Welcome-Session
        welcome_session.deactivate()
        
        current_app.logger.info(f"Registrierung erfolgreich beendet von Admin: {current_user.username}")
        
        return jsonify({
            "success": True,
            "message": "Registrierung erfolgreich beendet"
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Beenden der Registrierung: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Ein Fehler ist aufgetreten"
        }), 500

@admin_bp.route('/player_rotation_stats')
@login_required
def player_rotation_stats():
    """Zeigt Statistiken zur Spieler-Rotation"""
    if not isinstance(current_user, Admin):
        flash('Zugriff verweigert. Nur Admins können Rotations-Statistiken sehen.', 'danger')
        return redirect(url_for('main.index'))
    
    try:
        active_session = GameSession.query.filter_by(is_active=True).first()
        if not active_session:
            flash('Keine aktive Spielsitzung gefunden.', 'warning')
            return redirect(url_for('admin.admin_dashboard'))
        
        # Hole Statistiken
        rotation_stats = active_session.get_player_statistics()
        
        # Hole Team-Informationen
        teams = Team.query.all()
        team_lookup = {str(team.id): team for team in teams}
        
        # Format für Template
        formatted_stats = {}
        for team_id, stats in rotation_stats.items():
            team = team_lookup.get(team_id)
            if team:
                formatted_stats[team.name] = {
                    'total_games': stats['total_games'],
                    'players': stats['players'],
                    'most_played': stats['most_played'],
                    'least_played': stats['least_played'],
                    'team_members': team.members.split(', ') if team.members else []
                }
        
        return jsonify({
            'success': True,
            'stats': formatted_stats,
            'session_id': active_session.id
        })
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Laden der Rotations-Statistiken: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Fehler beim Laden der Statistiken'
        }), 500

@admin_bp.route('/reset_player_rotation', methods=['POST'])
@login_required
def reset_player_rotation():
    """Setzt die Spieler-Rotation zurück"""
    if not isinstance(current_user, Admin):
        return jsonify({'success': False, 'error': 'Zugriff verweigert'}), 403
    
    try:
        active_session = GameSession.query.filter_by(is_active=True).first()
        if not active_session:
            return jsonify({'success': False, 'error': 'Keine aktive Spielsitzung'}), 400
        
        # Reset der Rotation
        active_session.reset_player_rotation()
        db.session.commit()
        
        # Event loggen
        event = GameEvent(
            game_session_id=active_session.id,
            event_type="player_rotation_reset",
            description="Spieler-Rotation wurde zurückgesetzt.",
            related_team_id=None
        )
        db.session.add(event)
        db.session.commit()
        
        flash('Spieler-Rotation wurde zurückgesetzt. Alle Spieler starten wieder mit 0 Einsätzen.', 'success')
        
        return jsonify({
            'success': True,
            'message': 'Spieler-Rotation zurückgesetzt'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Zurücksetzen der Rotation: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Fehler beim Zurücksetzen'
        }), 500


# =============================================================================
# FELD-MINIGAME API ENDPUNKTE
# =============================================================================

@admin_bp.route('/api/field_minigame_counts')
@login_required
def api_field_minigame_counts():
    """API-Endpunkt für Feld-Minigame Anzahl"""
    if not isinstance(current_user, Admin):
        return jsonify({'error': 'Zugriff verweigert'}), 403
    
    try:
        import os
        
        team_vs_all_path = os.path.join(current_app.static_folder, 'field_minigames', 'team_vs_all')
        team_vs_team_path = os.path.join(current_app.static_folder, 'field_minigames', 'team_vs_team')
        
        team_vs_all_count = 0
        team_vs_team_count = 0
        
        # Zähle JSON-Dateien in team_vs_all
        if os.path.exists(team_vs_all_path):
            team_vs_all_count = len([f for f in os.listdir(team_vs_all_path) if f.endswith('.json')])
        
        # Zähle JSON-Dateien in team_vs_team
        if os.path.exists(team_vs_team_path):
            team_vs_team_count = len([f for f in os.listdir(team_vs_team_path) if f.endswith('.json')])
        
        return jsonify({
            'team_vs_all': team_vs_all_count,
            'team_vs_team': team_vs_team_count
        })
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Laden der Minigame-Anzahl: {e}")
        return jsonify({'error': 'Fehler beim Laden'}), 500


@admin_bp.route('/api/field_minigame_config', methods=['GET', 'POST'])
@login_required
def api_field_minigame_config():
    """API-Endpunkt für Feld-Minigame Konfiguration"""
    if not isinstance(current_user, Admin):
        return jsonify({'error': 'Zugriff verweigert'}), 403
    
    config_path = os.path.join(current_app.static_folder, 'field_minigames', 'config.json')
    
    if request.method == 'GET':
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                return jsonify(config)
            else:
                return jsonify({'field_minigames': {'enabled': True}})
        except Exception as e:
            current_app.logger.error(f"Fehler beim Laden der Konfiguration: {e}")
            return jsonify({'error': 'Fehler beim Laden'}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            key = data.get('key')
            value = data.get('value')
            
            # Lade aktuelle Konfiguration
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {'field_minigames': {'enabled': True, 'modes': {}}}
            
            # Aktualisiere Konfiguration basierend auf dem Key
            field_config = config.get('field_minigames', {})
            
            if key == 'reward_forward':
                # Aktualisiere Belohnung für beide Modi
                modes = field_config.get('modes', {})
                if 'team_vs_all' in modes:
                    modes['team_vs_all']['reward_forward'] = int(value)
                if 'team_vs_team' in modes:
                    modes['team_vs_team']['reward_forward'] = int(value)
                field_config['modes'] = modes
            elif key == 'default_mode':
                field_config['default_mode'] = value
            elif key == 'auto_start_timer':
                if 'game_flow' not in field_config:
                    field_config['game_flow'] = {}
                field_config['game_flow']['auto_start_timer'] = int(value)
            
            config['field_minigames'] = field_config
            
            # Speichere Konfiguration
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            return jsonify({'success': True, 'message': 'Konfiguration gespeichert'})
            
        except Exception as e:
            current_app.logger.error(f"Fehler beim Speichern der Konfiguration: {e}")
            return jsonify({'success': False, 'error': 'Fehler beim Speichern'}), 500


@admin_bp.route('/api/field_minigames/<mode>', methods=['GET', 'POST'])
@login_required
def api_field_minigames(mode):
    """API-Endpunkt für Feld-Minigame Verwaltung"""
    if not isinstance(current_user, Admin):
        return jsonify({'error': 'Zugriff verweigert'}), 403
    
    if mode not in ['team_vs_all', 'team_vs_team']:
        return jsonify({'error': 'Ungültiger Modus'}), 400
    
    folder_path = os.path.join(current_app.static_folder, 'field_minigames', mode)
    
    if request.method == 'GET':
        try:
            minigames = []
            
            if os.path.exists(folder_path):
                for filename in os.listdir(folder_path):
                    if filename.endswith('.json'):
                        file_path = os.path.join(folder_path, filename)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = json.load(f)
                            content['id'] = filename  # Verwende Dateiname als ID
                            minigames.append(content)
            
            return jsonify({'minigames': minigames})
            
        except Exception as e:
            current_app.logger.error(f"Fehler beim Laden der Minigames: {e}")
            return jsonify({'error': 'Fehler beim Laden'}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            
            # Validierung - nur Spiele erlaubt
            if not data.get('type') or data['type'] != 'game':
                return jsonify({'success': False, 'error': 'Nur Spiele sind erlaubt'}), 400
            
            if not data.get('title') or not data.get('instructions'):
                return jsonify({'success': False, 'error': 'Fehlende Pflichtfelder für Spiel'}), 400
            
            if not data.get('player_count') or not isinstance(data['player_count'], int) or data['player_count'] < 1:
                return jsonify({'success': False, 'error': 'Ungültige Spieleranzahl'}), 400
            
            # Erstelle Ordner falls nicht vorhanden
            os.makedirs(folder_path, exist_ok=True)
            
            # Generiere eindeutigen Dateinamen
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"game_{timestamp}_{str(uuid.uuid4())[:8]}.json"
            file_path = os.path.join(folder_path, filename)
            
            # Speichere Minigame
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return jsonify({'success': True, 'message': 'Minigame gespeichert', 'id': filename})
            
        except Exception as e:
            current_app.logger.error(f"Fehler beim Speichern des Minigames: {e}")
            return jsonify({'success': False, 'error': 'Fehler beim Speichern'}), 500


@admin_bp.route('/api/field_minigames/<mode>/<minigame_id>', methods=['PUT'])
@login_required
def api_update_field_minigame(mode, minigame_id):
    """API-Endpunkt zum Aktualisieren von Feld-Minigames"""
    if not isinstance(current_user, Admin):
        return jsonify({'error': 'Zugriff verweigert'}), 403
    
    if mode not in ['team_vs_all', 'team_vs_team']:
        return jsonify({'error': 'Ungültiger Modus'}), 400
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Keine Daten empfangen'}), 400
        
        folder_path = os.path.join(current_app.static_folder, 'field_minigames', mode)
        file_path = os.path.join(folder_path, minigame_id)
        
        if not os.path.exists(file_path) or not file_path.endswith('.json'):
            return jsonify({'success': False, 'error': 'Minigame nicht gefunden'}), 404
        
        # Erstelle das Update-Objekt
        update_data = {
            'type': data.get('type', 'game'),
            'title': data.get('title', ''),
            'instructions': data.get('instructions', ''),
            'player_count': data.get('player_count', 1),
            'materials': data.get('materials', 'Keine')
        }
        
        # Aktualisiere die JSON-Datei
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(update_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({'success': True, 'message': 'Minigame aktualisiert'})
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Aktualisieren des Minigames: {e}")
        return jsonify({'success': False, 'error': 'Fehler beim Aktualisieren'}), 500


@admin_bp.route('/api/field_minigames/<mode>/<minigame_id>', methods=['DELETE'])
@login_required
def api_delete_field_minigame(mode, minigame_id):
    """API-Endpunkt zum Löschen von Feld-Minigames"""
    if not isinstance(current_user, Admin):
        return jsonify({'error': 'Zugriff verweigert'}), 403
    
    if mode not in ['team_vs_all', 'team_vs_team']:
        return jsonify({'error': 'Ungültiger Modus'}), 400
    
    try:
        folder_path = os.path.join(current_app.static_folder, 'field_minigames', mode)
        file_path = os.path.join(folder_path, minigame_id)
        
        if os.path.exists(file_path) and file_path.endswith('.json'):
            os.remove(file_path)
            return jsonify({'success': True, 'message': 'Minigame gelöscht'})
        else:
            return jsonify({'success': False, 'error': 'Minigame nicht gefunden'}), 404
            
    except Exception as e:
        current_app.logger.error(f"Fehler beim Löschen des Minigames: {e}")
        return jsonify({'success': False, 'error': 'Fehler beim Löschen'}), 500

# =============================================================================
# SEQUENCE MANAGEMENT ROUTES (Vereinfacht)
# =============================================================================

@admin_bp.route('/manage_sequence/<int:folder_id>', methods=['GET'])
@login_required
def manage_sequence(folder_id):
    """Verwaltet die Ablaufsequenz für einen Ordner"""
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folder = MinigameFolder.query.get_or_404(folder_id)
    
    # Hole oder erstelle die Sequenz für diesen Ordner
    sequence = MinigameSequence.query.filter_by(minigame_folder_id=folder.id).first()
    
    # Lade verfügbare Items
    available_minigames = get_minigames_from_folder(folder.folder_path) or []
    available_questions = [item for item in available_minigames if item.get('type') == 'question']
    available_minigames = [item for item in available_minigames if item.get('type') != 'question']
    
    return render_template('admin/manage_sequence.html',
                         folder=folder,
                         sequence=sequence,
                         available_minigames=available_minigames,
                         available_questions=available_questions)

@admin_bp.route('/update_sequence/<int:folder_id>', methods=['POST'])
@login_required
def update_sequence(folder_id):
    """Aktualisiert die Sequenz per JSON (Drag & Drop)"""
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folder = MinigameFolder.query.get_or_404(folder_id)
    
    try:
        # Lade JSON-Daten aus dem Form
        sequence_data = request.form.get('sequence_data')
        if not sequence_data:
            flash('Keine Sequenz-Daten erhalten.', 'danger')
            return redirect(url_for('admin.manage_sequence', folder_id=folder.id))
        
        sequence_list = json.loads(sequence_data)
        
        # Hole oder erstelle Sequenz
        sequence = MinigameSequence.query.filter_by(minigame_folder_id=folder.id).first()
        
        if not sequence:
            sequence = MinigameSequence(
                minigame_folder_id=folder.id,
                sequence_data='[]',
                current_position=0,
                is_active=False
            )
            db.session.add(sequence)
        
        # Aktualisiere Sequenz
        sequence.sequence_list = sequence_list
        sequence.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Ablaufplan erfolgreich gespeichert.', 'success')
        
    except json.JSONDecodeError:
        flash('Ungültige Sequenz-Daten.', 'danger')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Speichern der Sequenz: {e}", exc_info=True)
        flash('Ein Fehler ist beim Speichern aufgetreten.', 'danger')
    
    return redirect(url_for('admin.manage_sequence', folder_id=folder.id))

@admin_bp.route('/activate_sequence/<int:folder_id>', methods=['POST'])
@login_required  
def activate_sequence(folder_id):
    """Aktiviert die Sequenz für einen Ordner"""  
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folder = MinigameFolder.query.get_or_404(folder_id)
    
    try:
        sequence = MinigameSequence.query.filter_by(minigame_folder_id=folder.id).first()
        
        if sequence:
            sequence.is_active = True
            sequence.updated_at = datetime.utcnow()
            db.session.commit()
            flash('Ablaufplan wurde aktiviert.', 'success')
        else:
            flash('Kein Ablaufplan für diesen Ordner gefunden.', 'warning')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Aktivieren der Sequenz: {e}", exc_info=True)
        flash('Ein Fehler ist beim Aktivieren aufgetreten.', 'danger')
    
    return redirect(url_for('admin.manage_sequence', folder_id=folder.id))

@admin_bp.route('/deactivate_sequence/<int:folder_id>', methods=['POST'])
@login_required
def deactivate_sequence(folder_id):
    """Deaktiviert die Sequenz für einen Ordner"""
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folder = MinigameFolder.query.get_or_404(folder_id)
    
    try:
        sequence = MinigameSequence.query.filter_by(minigame_folder_id=folder.id).first()
        
        if sequence:
            sequence.is_active = False
            sequence.updated_at = datetime.utcnow()
            db.session.commit()
            flash('Ablaufplan wurde deaktiviert.', 'success')
        else:
            flash('Kein Ablaufplan für diesen Ordner gefunden.', 'warning')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Deaktivieren der Sequenz: {e}", exc_info=True)
        flash('Ein Fehler ist beim Deaktivieren aufgetreten.', 'danger')
    
    return redirect(url_for('admin.manage_sequence', folder_id=folder.id))

@admin_bp.route('/api/sequence_status')
@login_required
def api_sequence_status():
    """API-Route für Live-Updates der Sequence-Status im Admin Dashboard"""
    if not isinstance(current_user, Admin):
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        active_round = GameRound.get_active_round()
        if not active_round or not active_round.minigame_folder:
            return jsonify({'has_sequence': False})
        
        # Lade Sequenz direkt aus DB (gleiche Logik wie im admin_dashboard)
        active_sequence = MinigameSequence.query.filter_by(
            minigame_folder_id=active_round.minigame_folder.id
        ).first()
        
        if not active_sequence:
            return jsonify({'has_sequence': False})
        
        # Sequenz-Daten für Frontend aufbereiten
        sequence_data = {
            'has_sequence': True,
            'is_active': active_sequence.is_active,
            'has_items': len(active_sequence.sequence_list) > 0,
            'folder_name': active_round.minigame_folder.name,
            'current_position': active_sequence.current_position,
            'total_items': len(active_sequence.sequence_list),
            'progress_percentage': active_sequence.get_progress_percentage(),
            'sequence_list': active_sequence.sequence_list
        }
        
        # Aktuelles und nächstes Item
        current_item = active_sequence.get_current_item()
        if current_item:
            sequence_data['current_item'] = current_item
        
        next_item = active_sequence.get_next_item()
        if next_item:
            sequence_data['next_item'] = next_item
            
        return jsonify(sequence_data)
        
    except Exception as e:
        current_app.logger.error(f"Fehler bei API sequence_status: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# NEU: Minigame-Feld Admin Auswahl Routes
def handle_minigame_result_phase(active_session):
    """Helper function to handle the minigame result input phase"""
    from app.models import Team
    
    # Hole Team-Informationen
    landing_team = None
    opponent_team = None
    
    if active_session.field_minigame_landing_team_id:
        landing_team = Team.query.get(active_session.field_minigame_landing_team_id)
    
    if active_session.field_minigame_opponent_team_id:
        opponent_team = Team.query.get(active_session.field_minigame_opponent_team_id)
    
    # Hole Minigame-Informationen aus der Session
    minigame_name = "Unbekanntes Minigame"
    minigame_mode = "team_vs_all"  # Default
    
    if active_session.field_minigame_content_id:
        try:
            import os
            import json
            
            # Parse die Content-ID (format: "mode:filename")
            if ':' in active_session.field_minigame_content_id:
                mode, filename = active_session.field_minigame_content_id.split(':', 1)
                minigame_mode = mode
                
                # Lade Minigame-Daten
                field_minigames_path = os.path.join(current_app.static_folder, 'field_minigames', mode)
                filepath = os.path.join(field_minigames_path, f"{filename}.json")
                
                if os.path.exists(filepath):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        minigame_data = json.load(f)
                    minigame_name = minigame_data.get('title', filename)
        except Exception as e:
            current_app.logger.warning(f"Fehler beim Laden der Minigame-Daten: {e}")
    
    return jsonify({
        'selection_pending': False,
        'result_pending': True,
        'mode': minigame_mode,
        'landing_team': landing_team.name if landing_team else 'Unbekannt',
        'opponent_team': opponent_team.name if opponent_team else None,
        'minigame_name': minigame_name
    })

@admin_bp.route('/check_minigame_field_status')
@login_required
def check_minigame_field_status():
    """API-Route zum Prüfen ob Minigame-Feld Auswahl erforderlich ist"""
    if not isinstance(current_user, Admin):
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        active_session = GameSession.query.filter_by(is_active=True).first()
        if not active_session:
            return jsonify({'selection_pending': False})
        
        # Prüfe ob in FIELD_MINIGAME_SELECTION_PENDING oder FIELD_MINIGAME_TRIGGERED Phase
        if active_session.current_phase == 'FIELD_MINIGAME_SELECTION_PENDING':
            # Phase 1: Admin muss Minigame auswählen
            pass  # Continue with selection logic below
        elif active_session.current_phase == 'FIELD_MINIGAME_TRIGGERED':
            # Phase 2: Admin muss Ergebnis eingeben
            return handle_minigame_result_phase(active_session)
        else:
            return jsonify({'selection_pending': False, 'result_pending': False})
        
        # Hole Team-Informationen
        landing_team = None
        opponent_team = None
        
        if active_session.field_minigame_landing_team_id:
            landing_team = Team.query.get(active_session.field_minigame_landing_team_id)
        
        if active_session.field_minigame_opponent_team_id:
            opponent_team = Team.query.get(active_session.field_minigame_opponent_team_id)
        
        # Hole verfügbare Feld-Minispiele aus BEIDEN Modi - Admin soll wählen
        import os
        import json
        
        available_minigames = {
            'team_vs_all': [],
            'team_vs_team': []
        }
        
        for mode in ['team_vs_all', 'team_vs_team']:
            field_minigames_path = os.path.join(current_app.static_folder, 'field_minigames', mode)
            
            if os.path.exists(field_minigames_path):
                for filename in os.listdir(field_minigames_path):
                    if filename.endswith('.json'):
                        try:
                            filepath = os.path.join(field_minigames_path, filename)
                            with open(filepath, 'r', encoding='utf-8') as f:
                                minigame_data = json.load(f)
                            
                            # ID ist der Dateiname ohne .json Extension plus Modus
                            minigame_id = f"{mode}:{filename[:-5]}"  # z.B. "team_vs_all:game123"
                            
                            available_minigames[mode].append({
                                'id': minigame_id,
                                'title': minigame_data.get('title', filename[:-5]),
                                'instructions': minigame_data.get('instructions', ''),
                                'player_count': minigame_data.get('player_count', 1),
                                'mode': mode
                            })
                        except Exception as e:
                            current_app.logger.warning(f"Fehler beim Laden von Feld-Minispiel {filename}: {e}")
                            continue
        
        # Bestimme Modi-Namen
        mode_names = {
            'team_vs_team': 'Ein Team gegen ein anderes',
            'team_vs_all': 'Ein Team gegen alle anderen'
        }
        
        return jsonify({
            'selection_pending': True,
            'mode': 'pending',  # Admin soll wählen
            'landing_team': landing_team.name if landing_team else 'Unbekannt',
            'available_minigames': available_minigames,
            'mode_selection': True  # Zeigt an, dass Admin den Modus wählen soll
        })
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Prüfen des Minigame-Feld Status: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@admin_bp.route('/start_field_minigame', methods=['POST'])
@login_required
def start_field_minigame():
    """API-Route zum Starten des ausgewählten Feld-Minigames"""
    if not isinstance(current_user, Admin):
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        current_app.logger.info(f"Field minigame start request data: {data}")
        
        if not data or 'minigame_id' not in data:
            current_app.logger.warning("Missing minigame_id in request data")
            return jsonify({'success': False, 'message': 'Minigame-ID fehlt'}), 400
        
        full_minigame_id = data['minigame_id']
        current_app.logger.info(f"Received minigame ID: {full_minigame_id}")
        
        # Parse die ID um Modus und echte ID zu extrahieren
        if ':' not in full_minigame_id:
            current_app.logger.warning(f"Invalid minigame ID format: {full_minigame_id}")
            return jsonify({'success': False, 'message': 'Ungültiges Minigame-ID Format'}), 400
        
        selected_mode, minigame_id = full_minigame_id.split(':', 1)
        current_app.logger.info(f"Parsed mode: {selected_mode}, minigame_id: {minigame_id}")
        
        # Hole aktive Session
        active_session = GameSession.query.filter_by(is_active=True).first()
        if not active_session:
            return jsonify({'success': False, 'message': 'Keine aktive Spielsitzung'}), 400
        
        # Setze den gewählten Modus und bestimme Gegner-Team
        active_session.field_minigame_mode = selected_mode
        
        if selected_mode == 'team_vs_team':
            # Wähle zufälliges anderes Team als Gegner
            from app.models import Team
            landing_team_id = active_session.field_minigame_landing_team_id
            other_teams = Team.query.filter(Team.id != landing_team_id).all()
            
            if other_teams:
                import random
                opponent_team = random.choice(other_teams)
                active_session.field_minigame_opponent_team_id = opponent_team.id
            else:
                # Fallback zu team_vs_all wenn nur ein Team vorhanden
                active_session.field_minigame_mode = 'team_vs_all'
                active_session.field_minigame_opponent_team_id = None
        else:
            # team_vs_all - kein spezifisches Gegner-Team
            active_session.field_minigame_opponent_team_id = None
        
        # Starte das ausgewählte Minigame mit dem gewählten Modus
        result = start_selected_field_minigame(active_session, minigame_id, selected_mode)
        
        if result['success']:
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': result['message'],
                'minigame_name': result['selected_minigame'].get('title', minigame_id)
            })
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Fehler beim Starten des Feld-Minigames: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@admin_bp.route('/submit_field_minigame_result', methods=['POST'])
@login_required
def submit_field_minigame_result():
    """API-Route zum Eingeben des Feld-Minigame Ergebnisses"""
    if not isinstance(current_user, Admin):
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        if not data or 'result' not in data:
            return jsonify({'success': False, 'message': 'Ergebnis fehlt'}), 400
        
        result_outcome = data['result']  # 'won' oder 'lost'
        
        if result_outcome not in ['won', 'lost']:
            return jsonify({'success': False, 'message': 'Ungültiges Ergebnis'}), 400
        
        # Hole aktive Session
        active_session = GameSession.query.filter_by(is_active=True).first()
        if not active_session:
            return jsonify({'success': False, 'message': 'Keine aktive Spielsitzung'}), 400
        
        # Prüfe ob Session in richtigem Status
        if active_session.current_phase != 'FIELD_MINIGAME_TRIGGERED':
            return jsonify({'success': False, 'message': 'Kein aktives Feld-Minigame'}), 400
        
        # Bestimme Gewinner-Team basierend auf Ergebnis
        winning_team_id = None
        if result_outcome == 'won':
            # Herausforderer (landing team) hat gewonnen
            winning_team_id = active_session.field_minigame_landing_team_id
        # Bei 'lost' bleibt winning_team_id None (kein Bonus)
        
        # Verarbeite Ergebnis mit Katapult-Belohnung
        result = handle_field_minigame_result(active_session, winning_team_id)
        
        if result['success']:
            # Setze Session zurück zur Würfelphase falls Runde noch nicht fertig
            # Prüfe ob noch Teams in der Würfelreihenfolge dran sind
            if active_session.dice_roll_order and active_session.current_team_turn_id:
                # Es ist noch ein Team dran - zurück zur Würfelphase
                active_session.current_phase = 'DICE_ROLLING'  # Würfelrunde fortsetzen
            else:
                # Keine Teams mehr oder Runde schon beendet
                active_session.current_phase = 'ROUND_OVER'  # Runde beendet
            
            # Reset Field-Minigame Daten
            active_session.field_minigame_landing_team_id = None
            active_session.field_minigame_opponent_team_id = None
            active_session.field_minigame_mode = None
            active_session.field_minigame_result = None
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': result['message'],
                'team_name': result.get('team_name', ''),
                'reward_forward': result.get('reward_forward', 0),
                'continue_rolling': active_session.current_phase == 'DICE_ROLLING'
            })
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Fehler beim Verarbeiten des Feld-Minigame Ergebnisses: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

