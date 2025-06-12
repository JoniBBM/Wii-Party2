from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models import Team, db, Admin, GameSession, GameRound, QuestionResponse, GameEvent
from flask import current_app
from app.forms import TeamLoginForm, QuestionAnswerForm
from app.admin.minigame_utils import get_question_from_folder
import json
from datetime import datetime, timedelta

teams_bp = Blueprint('teams', __name__, url_prefix='/teams')

@teams_bp.route('/login', methods=['GET', 'POST'])
def team_login():
    # Teams müssen immer das Passwort eingeben - automatische Auslogung
    if current_user.is_authenticated:
        if isinstance(current_user, Team):
            # Team ist eingeloggt -> automatisch ausloggen für neue Anmeldung
            logout_user()
            flash('Bitte melde dich erneut an.', 'info')
        elif isinstance(current_user, Admin):
             flash('Du bist bereits als Admin eingeloggt.', 'info')
             return redirect(url_for('admin.admin_dashboard'))

    form = TeamLoginForm()
    if form.validate_on_submit():
        team = Team.query.filter_by(name=form.team_name.data).first()
        if team and team.check_password(form.password.data):
            login_user(team)
            flash(f'Team "{team.name}" erfolgreich eingeloggt.', 'success')
            return redirect(url_for('teams.team_dashboard'))
        else:
            flash('Ungültiger Teamname oder Passwort.', 'danger')
    return render_template('team_login.html', title='Team Login', form=form)

@teams_bp.route('/logout')
@login_required
def team_logout():
    if not isinstance(current_user, Team):
        flash('Nur Teams können sich hier ausloggen.', 'warning')
        if isinstance(current_user, Admin):
            return redirect(url_for('admin.admin_dashboard'))
        return redirect(url_for('main.index'))

    logout_user()
    flash('Team erfolgreich ausgeloggt.', 'info')
    return redirect(url_for('main.index'))

def _get_team_game_progress(team_user):
    """Sammelt die Spielverlauf-Daten für ein Team"""
    active_session = GameSession.query.filter_by(is_active=True).first()
    if not active_session:
        return []
    
    # Hole alle Bewegungs-Events für dieses Team in der aktuellen Session
    move_events = GameEvent.query.filter_by(
        game_session_id=active_session.id,
        related_team_id=team_user.id
    ).filter(
        GameEvent.event_type.in_(['dice_roll', 'admin_dice_roll', 'admin_dice_roll_legacy'])
    ).order_by(GameEvent.timestamp).all()
    
    progress_data = []
    move_number = 0
    
    # Startposition
    progress_data.append({
        'move': 0,
        'position': 0,
        'timestamp': active_session.start_time.strftime('%H:%M:%S') if active_session.start_time else '00:00:00',
        'description': 'Spielstart'
    })
    
    for event in move_events:
        move_number += 1
        
        # Parse data_json für neue und alte Position
        old_position = 0
        new_position = team_user.current_position  # Fallback zur aktuellen Position
        dice_total = 0
        
        if event.data_json:
            try:
                # Versuche JSON parsing zuerst
                if isinstance(event.data_json, str):
                    try:
                        event_data = json.loads(event.data_json)
                    except json.JSONDecodeError:
                        # Fallback zu eval für Legacy-Daten
                        try:
                            event_data = eval(event.data_json)
                        except:
                            event_data = {}
                else:
                    event_data = event.data_json
                
                old_position = event_data.get('old_position', 0)
                new_position = event_data.get('new_position', team_user.current_position)
                dice_total = event_data.get('total_roll', 0)
                standard_roll = event_data.get('standard_roll', 0)
                bonus_roll = event_data.get('bonus_roll', 0)
                
            except Exception as e:
                # Falls Parsing fehlschlägt, verwende Fallback-Werte
                pass
        
        progress_data.append({
            'move': move_number,
            'position': new_position,
            'timestamp': event.timestamp.strftime('%H:%M:%S'),
            'description': f'Würfelwurf: {dice_total}' if dice_total > 0 else 'Bewegung',
            'dice_roll': dice_total
        })
    
    return progress_data

def _get_last_dice_result(team_user, active_session):
    """Holt das letzte Würfelergebnis für ein Team"""
    if not active_session:
        return None
    
    # Hole letztes Würfel-Event für dieses Team
    last_dice_event = GameEvent.query.filter_by(
        game_session_id=active_session.id,
        related_team_id=team_user.id
    ).filter(
        GameEvent.event_type.in_(['dice_roll', 'admin_dice_roll', 'admin_dice_roll_legacy'])
    ).order_by(GameEvent.timestamp.desc()).first()
    
    if last_dice_event and last_dice_event.data_json:
        try:
            # Parse data_json
            if isinstance(last_dice_event.data_json, str):
                # Versuche JSON parsing
                try:
                    event_data = json.loads(last_dice_event.data_json)
                except json.JSONDecodeError:
                    # Fallback zu eval für alte Daten
                    event_data = eval(last_dice_event.data_json)
            else:
                event_data = last_dice_event.data_json
            
            return {
                'standard_roll': event_data.get('standard_roll', 0),
                'bonus_roll': event_data.get('bonus_roll', 0),
                'total_roll': event_data.get('total_roll', 0),
                'timestamp': last_dice_event.timestamp.strftime('%H:%M:%S'),
                'was_blocked': event_data.get('was_blocked', False),
                'barrier_released': event_data.get('barrier_released', False)
            }
        except Exception as e:
            current_app.logger.error(f"Error parsing dice result: {e}")
            return None
    
    return None

def _get_dashboard_data(team_user):
    """Hilfsfunktion um Dashboard-Daten zu sammeln"""
    # Alle Teams für Vergleich/Rangliste
    all_teams = Team.query.order_by(Team.current_position.desc(), Team.name).all()
    
    # Aktive Spielsitzung
    active_session = GameSession.query.filter_by(is_active=True).first()
    
    # Aktive Spielrunde
    active_round = GameRound.get_active_round()
    
    # Fragen-Daten falls aktiv
    current_question_data = None
    question_response = None
    question_answered = False
    
    if active_session and active_session.current_question_id and active_round and active_round.minigame_folder:
        current_question_data = get_question_from_folder(active_round.minigame_folder.folder_path, active_session.current_question_id)
        if current_question_data:
            # Hole bereits gegebene Antwort dieses Teams für diese Frage
            question_response = QuestionResponse.query.filter_by(
                team_id=team_user.id,
                game_session_id=active_session.id,
                question_id=active_session.current_question_id
            ).first()
            
            question_answered = question_response is not None
    
    # Spielbrett-Informationen
    max_board_fields = 73
    
    # Aktuelles Team beim Würfeln (falls Würfelphase aktiv)
    current_team_turn = None
    current_team_turn_name = None
    dice_roll_order = []
    dice_roll_order_names = []
    
    if active_session:
        if active_session.current_team_turn_id:
            current_team_turn = Team.query.get(active_session.current_team_turn_id)
            current_team_turn_name = current_team_turn.name if current_team_turn else "Unbekannt"
        
        # Würfelreihenfolge verarbeiten
        if active_session.dice_roll_order:
            try:
                dice_roll_order = [int(tid) for tid in active_session.dice_roll_order.split(',') if tid.strip().isdigit()]
                dice_roll_order_names = []
                for team_id in dice_roll_order:
                    team = Team.query.get(team_id)
                    if team:
                        dice_roll_order_names.append(team.name)
            except ValueError:
                dice_roll_order = []
                dice_roll_order_names = []
    
    # Statistiken berechnen
    teams_count = len(all_teams)
    
    # Position des aktuellen Teams in der Rangliste ermitteln
    current_team_rank = 1
    for i, team in enumerate(all_teams):
        if team.id == team_user.id:
            current_team_rank = i + 1
            break
    
    # Führendes Team
    leading_team = all_teams[0] if all_teams else None
    
    # Teams die vor dem aktuellen Team sind
    teams_ahead = sum(1 for team in all_teams if team.current_position > team_user.current_position)
    
    # Verbleibendes Feld bis zum Ziel
    fields_to_goal = max_board_fields - 1 - team_user.current_position
    
    # Spielstatus-Text generieren
    if active_session:
        if active_session.current_phase == 'SETUP_MINIGAME':
            game_status = "Admin wählt nächsten Inhalt aus"
            game_status_class = "warning"
        elif active_session.current_phase == 'MINIGAME_ANNOUNCED':
            game_status = "Minispiel wurde angekündigt - Warte auf Platzierungen"
            game_status_class = "info"
        elif active_session.current_phase == 'QUESTION_ACTIVE':
            if current_question_data:
                if question_answered:
                    game_status = f"Frage '{current_question_data['name']}' beantwortet - Warte auf andere Teams"
                    game_status_class = "success"
                else:
                    game_status = f"Frage '{current_question_data['name']}' läuft - Beantworte die Frage!"
                    game_status_class = "primary"
            else:
                game_status = "Frage läuft"
                game_status_class = "primary"
        elif active_session.current_phase == 'DICE_ROLLING':
            if current_team_turn_name:
                if current_team_turn_name == team_user.name:
                    game_status = f"Du bist am Zug! Warte auf Admin's Würfelwurf"
                    game_status_class = "success"
                else:
                    game_status = f"{current_team_turn_name} ist am Zug"
                    game_status_class = "primary"
            else:
                game_status = "Würfelrunde läuft"
                game_status_class = "primary"
        elif active_session.current_phase == 'ROUND_OVER':
            game_status = "Runde beendet - Nächster Inhalt wird vorbereitet"
            game_status_class = "secondary"
        else:
            game_status = f"Spielphase: {active_session.current_phase}"
            game_status_class = "info"
    else:
        game_status = "Kein aktives Spiel"
        game_status_class = "danger"
    
    # NEU: Spielverlauf-Daten
    game_progress = _get_team_game_progress(team_user)
    
    return {
        'all_teams': all_teams,
        'active_session': active_session,
        'active_round': active_round,
        'max_board_fields': max_board_fields,
        'current_team_turn': current_team_turn,
        'current_team_turn_name': current_team_turn_name,
        'dice_roll_order': dice_roll_order,
        'dice_roll_order_names': dice_roll_order_names,
        'teams_count': teams_count,
        'current_team_rank': current_team_rank,
        'leading_team': leading_team,
        'teams_ahead': teams_ahead,
        'fields_to_goal': fields_to_goal,
        'game_status': game_status,
        'game_status_class': game_status_class,
        'title': f'Dashboard Team {team_user.name}',
        # Fragen-Daten
        'current_question_data': current_question_data,
        'question_response': question_response,
        'question_answered': question_answered,
        # NEU: Spielverlauf
        'game_progress': game_progress,
        # NEU: Letztes Würfelergebnis
        'last_dice_result': _get_last_dice_result(team_user, active_session)
    }

@teams_bp.route('/dashboard')
@login_required
def team_dashboard():
    if not isinstance(current_user, Team):
        flash('Nur eingeloggte Teams können ihr Dashboard sehen.', 'warning')
        return redirect(url_for('teams.team_login'))
    
    # Prüfe ob Team-Setup erforderlich ist (aus Welcome-System kommend)
    if current_user.welcome_password and not current_user.character_id:
        # Team ist aus Welcome-System und muss noch Setup durchführen
        return redirect(url_for('teams.team_setup'))
    
    template_data = _get_dashboard_data(current_user)
    return render_template('team_dashboard.html', **template_data)

@teams_bp.route('/setup', methods=['GET', 'POST'])
@login_required
def team_setup():
    """Team-Setup für Teams aus dem Welcome-System"""
    if not isinstance(current_user, Team):
        flash('Nur eingeloggte Teams können das Setup durchführen.', 'warning')
        return redirect(url_for('teams.team_login'))
    
    # Nur für Teams aus Welcome-System (haben welcome_password)
    if not current_user.welcome_password:
        flash('Team-Setup ist nicht erforderlich.', 'info')
        return redirect(url_for('teams.team_dashboard'))
    
    # Hole verfügbare Charaktere
    from app.models import Character
    available_characters = Character.query.filter_by(is_selected=False).all()
    
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            new_team_name = data.get('team_name', '').strip()
            character_id = data.get('character_id')
            
            # Validierung
            if not new_team_name:
                if request.is_json:
                    return jsonify({"success": False, "error": "Team-Name ist erforderlich"}), 400
                flash('Team-Name ist erforderlich.', 'danger')
                return redirect(url_for('teams.team_setup'))
            
            if len(new_team_name) > 50:
                if request.is_json:
                    return jsonify({"success": False, "error": "Team-Name ist zu lang (max. 50 Zeichen)"}), 400
                flash('Team-Name ist zu lang (max. 50 Zeichen).', 'danger')
                return redirect(url_for('teams.team_setup'))
            
            # Prüfe ob Name bereits existiert (außer dem aktuellen Team)
            existing_team = Team.query.filter(Team.name == new_team_name, Team.id != current_user.id).first()
            if existing_team:
                if request.is_json:
                    return jsonify({"success": False, "error": "Team-Name ist bereits vergeben"}), 400
                flash('Team-Name ist bereits vergeben.', 'danger')
                return redirect(url_for('teams.team_setup'))
            
            # Charakter-Validierung falls angegeben
            character = None
            if character_id:
                try:
                    character_id = int(character_id)
                    character = Character.query.filter_by(id=character_id, is_selected=False).first()
                    if not character:
                        if request.is_json:
                            return jsonify({"success": False, "error": "Charakter ist nicht verfügbar"}), 400
                        flash('Charakter ist nicht verfügbar.', 'danger')
                        return redirect(url_for('teams.team_setup'))
                except ValueError:
                    if request.is_json:
                        return jsonify({"success": False, "error": "Ungültige Charakter-ID"}), 400
                    flash('Ungültige Charakter-ID.', 'danger')
                    return redirect(url_for('teams.team_setup'))
            
            # Markiere alten Charakter als verfügbar falls vorhanden
            if current_user.character_id:
                old_character = Character.query.get(current_user.character_id)
                if old_character:
                    old_character.is_selected = False
            
            # Aktualisiere Team
            current_user.name = new_team_name
            if character:
                current_user.character_id = character.id
                current_user.character_name = character.name
                character.is_selected = True
            
            db.session.commit()
            
            current_app.logger.info(f"Team-Setup abgeschlossen: {current_user.id} -> {new_team_name}, Charakter: {character.name if character else 'None'}")
            
            if request.is_json:
                return jsonify({
                    "success": True,
                    "message": "Team-Setup erfolgreich abgeschlossen",
                    "team_name": new_team_name,
                    "character_name": character.name if character else None
                })
            
            flash(f'Team-Setup erfolgreich abgeschlossen! Willkommen {new_team_name}!', 'success')
            return redirect(url_for('teams.team_dashboard'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Fehler beim Team-Setup: {e}", exc_info=True)
            if request.is_json:
                return jsonify({"success": False, "error": "Ein Fehler ist aufgetreten"}), 500
            flash('Ein Fehler ist aufgetreten. Versuche es nochmal.', 'danger')
    
    return render_template('team_setup.html', 
                         team=current_user, 
                         available_characters=available_characters)

@teams_bp.route('/api/dashboard-status')
@login_required
def dashboard_status_api():
    """API für Live-Updates des Team Dashboards"""
    if not isinstance(current_user, Team):
        return {'error': 'Unauthorized'}, 403
    
    try:
        # Hole aktuelle Daten
        data = _get_dashboard_data(current_user)
        
        # Konvertiere Teams zu JSON-freundlichem Format
        teams_data = []
        for team in data['all_teams']:
            teams_data.append({
                'id': team.id,
                'name': team.name,
                'position': team.current_position,
                'minigame_placement': team.minigame_placement,
                'bonus_dice_sides': team.bonus_dice_sides,
                'character_name': team.character.name if team.character else None,
                'is_current_user': team.id == current_user.id
            })
        
        # Würfelreihenfolge für JSON
        dice_order_data = []
        if data['dice_roll_order_names']:
            for i, team_name in enumerate(data['dice_roll_order_names']):
                dice_order_data.append({
                    'position': i + 1,
                    'name': team_name,
                    'is_current_turn': team_name == data['current_team_turn_name'],
                    'is_current_user': team_name == current_user.name
                })
        
        # Fragen-Daten für JSON
        question_data = None
        if data['current_question_data']:
            question_data = {
                'id': data['current_question_data']['id'],
                'name': data['current_question_data']['name'],
                'description': data['current_question_data'].get('description', ''),
                'question_text': data['current_question_data'].get('question_text', ''),
                'question_type': data['current_question_data'].get('question_type', 'multiple_choice'),
                'options': data['current_question_data'].get('options', []),
                'answered': data['question_answered']
            }
        
        return {
            'success': True,
            'data': {
                'teams': teams_data,
                'game_status': data['game_status'],
                'game_status_class': data['game_status_class'],
                'current_phase': data['active_session'].current_phase if data['active_session'] else None,
                'current_team_turn_name': data['current_team_turn_name'],
                'current_minigame_name': data['active_session'].current_minigame_name if data['active_session'] else None,
                'current_minigame_description': data['active_session'].current_minigame_description if data['active_session'] else None,
                'dice_roll_order': dice_order_data,
                'question_data': question_data,
                'current_user': {
                    'id': current_user.id,
                    'name': current_user.name,
                    'position': current_user.current_position,
                    'rank': data['current_team_rank'],
                    'fields_to_goal': data['fields_to_goal'],
                    'teams_ahead': data['teams_ahead'],
                    'bonus_dice_sides': current_user.bonus_dice_sides,
                    'minigame_placement': current_user.minigame_placement,
                    'is_current_turn': data['current_team_turn_name'] == current_user.name,
                    'is_blocked': current_user.is_blocked,
                    'blocked_target_number': current_user.blocked_target_number,
                    'blocked_config': current_user.blocked_config if hasattr(current_user, 'blocked_config') else None
                },
                'stats': {
                    'max_board_fields': data['max_board_fields'],
                    'teams_count': data['teams_count']
                },
                # NEU: Spielverlauf für Updates
                'game_progress': data['game_progress'],
                # NEU: Letztes Würfelergebnis
                'last_dice_result': data['last_dice_result'],
                # Special field event (für Barrier-Felder)
                'special_field_event': _get_recent_special_field_event(current_user, data['active_session'])
            }
        }
        
    except Exception as e:
        return {'error': str(e)}, 500

@teams_bp.route('/submit_question_answer', methods=['POST'])
@login_required
def submit_question_answer():
    """Verarbeite Fragen-Antwort eines Teams - ohne Punkte, mit automatischer Platzierung"""
    if not isinstance(current_user, Team):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'Keine Daten empfangen'}), 400
        
        question_id = data.get('question_id')
        answer_type = data.get('answer_type')
        
        if not all([question_id, answer_type]):
            return jsonify({'success': False, 'error': 'Fehlende erforderliche Daten'}), 400
        
        # Hole aktive Session
        active_session = GameSession.query.filter_by(is_active=True).first()
        if not active_session or active_session.current_question_id != question_id:
            return jsonify({'success': False, 'error': 'Keine aktive Frage gefunden'}), 404
        
        if active_session.current_phase != 'QUESTION_ACTIVE':
            return jsonify({'success': False, 'error': 'Frage ist nicht aktiv'}), 403
        
        # Prüfe ob bereits beantwortet
        existing_response = QuestionResponse.query.filter_by(
            team_id=current_user.id,
            game_session_id=active_session.id,
            question_id=question_id
        ).first()
        
        if existing_response:
            return jsonify({'success': False, 'error': 'Frage bereits beantwortet'}), 409
        
        # Hole Fragen-Daten
        active_round = GameRound.get_active_round()
        if not active_round or not active_round.minigame_folder:
            return jsonify({'success': False, 'error': 'Keine aktive Spielrunde'}), 404
        
        question_data = get_question_from_folder(active_round.minigame_folder.folder_path, question_id)
        if not question_data:
            return jsonify({'success': False, 'error': 'Fragen-Daten nicht gefunden'}), 404
        
        # Erstelle Antwort-Objekt
        response = QuestionResponse(
            team_id=current_user.id,
            game_session_id=active_session.id,
            question_id=question_id
        )
        
        # Verarbeite Antwort basierend auf Typ
        is_correct = False
        
        if answer_type == 'multiple_choice':
            selected_option = data.get('selected_option')
            if selected_option is not None:
                response.selected_option = int(selected_option)
                
                # Prüfe Korrektheit
                correct_option = question_data.get('correct_option', 0)
                if selected_option == correct_option:
                    is_correct = True
        
        elif answer_type == 'text_input':
            answer_text = data.get('answer_text', '').strip()
            response.answer_text = answer_text
            
            # Prüfe Korrektheit (case-insensitive)
            correct_text = question_data.get('correct_text', '').strip().lower()
            if answer_text.lower() == correct_text:
                is_correct = True
        
        else:
            return jsonify({'success': False, 'error': 'Ungültiger Antworttyp'}), 400
        
        response.is_correct = is_correct
        
        # Speichere in Datenbank
        db.session.add(response)
        db.session.commit()
        
        # Prüfe ob alle Teams geantwortet haben
        total_teams = Team.query.count()
        total_responses = QuestionResponse.query.filter_by(
            game_session_id=active_session.id,
            question_id=question_id
        ).count()
        
        all_teams_answered = total_responses >= total_teams
        
        return jsonify({
            'success': True,
            'is_correct': is_correct,
            'all_teams_answered': all_teams_answered,
            'feedback': {
                'message': 'Richtig!' if is_correct else 'Leider falsch.',
                'correct_answer': question_data.get('correct_text') if answer_type == 'text_input' else question_data.get('options', [])[question_data.get('correct_option', 0)] if answer_type == 'multiple_choice' else None
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Serverfehler: {str(e)}'}), 500

@teams_bp.route('/question/status')
@login_required
def question_status():
    """API für Fragen-Status Updates"""
    if not isinstance(current_user, Team):
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        active_session = GameSession.query.filter_by(is_active=True).first()
        if not active_session or not active_session.current_question_id:
            return jsonify({
                'question_active': False,
                'message': 'Keine aktive Frage'
            })
        
        if active_session.current_phase != 'QUESTION_ACTIVE':
            return jsonify({
                'question_active': False,
                'message': 'Frage nicht in aktiver Phase'
            })
        
        # Hole Fragen-Daten
        active_round = GameRound.get_active_round()
        if not active_round or not active_round.minigame_folder:
            return jsonify({
                'question_active': False,
                'message': 'Keine aktive Spielrunde'
            })
        
        question_data = get_question_from_folder(active_round.minigame_folder.folder_path, active_session.current_question_id)
        if not question_data:
            return jsonify({
                'question_active': False,
                'message': 'Fragen-Daten nicht gefunden'
            })
        
        # Hole Team-Antwort
        team_response = QuestionResponse.query.filter_by(
            team_id=current_user.id,
            game_session_id=active_session.id,
            question_id=active_session.current_question_id
        ).first()
        
        team_answered = team_response is not None
        
        return jsonify({
            'question_active': True,
            'question_data': {
                'id': question_data['id'],
                'name': question_data['name'],
                'description': question_data.get('description', ''),
                'question_text': question_data.get('question_text', ''),
                'question_type': question_data.get('question_type', 'multiple_choice'),
                'options': question_data.get('options', [])
            },
            'team_answered': team_answered,
            'team_response': {
                'is_correct': team_response.is_correct if team_response else None
            } if team_response else None
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def _get_recent_special_field_event(team, session):
    """Holt das letzte relevante Special Field Event für das Team"""
    if not session:
        return None
        
    try:
        # Hole Events der letzten 10 Sekunden für dieses Team
        recent_time = datetime.utcnow() - timedelta(seconds=10)
        recent_event = GameEvent.query.filter_by(
            game_session_id=session.id,
            related_team_id=team.id,
            event_type='field_action'
        ).filter(
            GameEvent.timestamp >= recent_time
        ).order_by(GameEvent.timestamp.desc()).first()
        
        if recent_event and recent_event.data:
            event_data = recent_event.data
            # Check if it's a barrier-related event
            if event_data.get('action') == 'barrier' and event_data.get('barrier_set'):
                return {
                    'type': 'barrier_set',
                    'target_config': event_data.get('target_config')
                }
            elif event_data.get('action') == 'check_barrier_release':
                # Build dice roll data with all components
                dice_roll_data = {
                    'dice_roll': event_data.get('dice_roll'),
                    'bonus_roll': event_data.get('bonus_roll', 0),
                    'total_roll': event_data.get('total_roll', event_data.get('dice_roll'))
                }
                
                if event_data.get('released'):
                    return {
                        'type': 'barrier_released',
                        'dice_roll': dice_roll_data,
                        'barrier_config': event_data.get('barrier_config'),
                        'release_method': event_data.get('release_method')
                    }
                else:
                    return {
                        'type': 'barrier_failed',
                        'dice_roll': dice_roll_data,
                        'barrier_config': event_data.get('barrier_config')
                    }
        
        return None
        
    except Exception as e:
        print(f"Error getting special field event: {e}")
        return None