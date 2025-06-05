from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models import Team, db, Admin, GameSession, GameRound, QuizResponse
from app.forms import TeamLoginForm, QuizAnswerForm
from app.admin.minigame_utils import get_quiz_from_folder
import json
from datetime import datetime

teams_bp = Blueprint('teams', __name__, url_prefix='/teams')

@teams_bp.route('/login', methods=['GET', 'POST'])
def team_login():
    if current_user.is_authenticated:
        if isinstance(current_user, Team):
            return redirect(url_for('teams.team_dashboard'))
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

def _get_dashboard_data(team_user):
    """Hilfsfunktion um Dashboard-Daten zu sammeln"""
    # Alle Teams für Vergleich/Rangliste
    all_teams = Team.query.order_by(Team.current_position.desc(), Team.name).all()
    
    # Aktive Spielsitzung
    active_session = GameSession.query.filter_by(is_active=True).first()
    
    # Aktive Spielrunde
    active_round = GameRound.get_active_round()
    
    # Quiz-Daten falls aktiv
    current_quiz_data = None
    quiz_responses = []
    quiz_progress = None
    
    if active_session and active_session.current_quiz_id and active_round and active_round.minigame_folder:
        current_quiz_data = get_quiz_from_folder(active_round.minigame_folder.folder_path, active_session.current_quiz_id)
        if current_quiz_data:
            # Hole bereits gegebene Antworten dieses Teams
            quiz_responses = QuizResponse.query.filter_by(
                team_id=team_user.id,
                game_session_id=active_session.id,
                quiz_id=active_session.current_quiz_id
            ).all()
            
            # Berechne Quiz-Fortschritt
            total_questions = len(current_quiz_data.get('questions', []))
            answered_questions = len(quiz_responses)
            quiz_progress = {
                'total': total_questions,
                'answered': answered_questions,
                'percentage': (answered_questions / total_questions * 100) if total_questions > 0 else 0,
                'completed': answered_questions >= total_questions
            }
    
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
            game_status = "Admin wählt nächstes Minispiel aus"
            game_status_class = "warning"
        elif active_session.current_phase == 'MINIGAME_ANNOUNCED':
            game_status = "Minispiel wurde angekündigt - Warte auf Platzierungen"
            game_status_class = "info"
        elif active_session.current_phase == 'QUIZ_ACTIVE':
            if current_quiz_data:
                if quiz_progress and quiz_progress['completed']:
                    game_status = f"Quiz '{current_quiz_data['name']}' abgeschlossen - Warte auf andere Teams"
                    game_status_class = "success"
                else:
                    game_status = f"Quiz '{current_quiz_data['name']}' läuft - Beantworte die Fragen!"
                    game_status_class = "primary"
            else:
                game_status = "Quiz läuft"
                game_status_class = "primary"
        elif active_session.current_phase == 'QUIZ_COMPLETED':
            game_status = "Quiz beendet - Warte auf Platzierungen"
            game_status_class = "info"
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
            game_status = "Runde beendet - Nächstes Minispiel wird vorbereitet"
            game_status_class = "secondary"
        else:
            game_status = f"Spielphase: {active_session.current_phase}"
            game_status_class = "info"
    else:
        game_status = "Kein aktives Spiel"
        game_status_class = "danger"
    
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
        # Quiz-Daten
        'current_quiz_data': current_quiz_data,
        'quiz_responses': quiz_responses,
        'quiz_progress': quiz_progress
    }

@teams_bp.route('/dashboard')
@login_required
def team_dashboard():
    if not isinstance(current_user, Team):
        flash('Nur eingeloggte Teams können ihr Dashboard sehen.', 'warning')
        return redirect(url_for('teams.team_login'))
    
    template_data = _get_dashboard_data(current_user)
    return render_template('team_dashboard.html', **template_data)

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
        
        # Quiz-Daten für JSON
        quiz_data = None
        if data['current_quiz_data']:
            quiz_data = {
                'id': data['current_quiz_data']['id'],
                'name': data['current_quiz_data']['name'],
                'description': data['current_quiz_data'].get('description', ''),
                'time_limit': data['current_quiz_data'].get('time_limit', 0),
                'questions_count': len(data['current_quiz_data'].get('questions', [])),
                'progress': data['quiz_progress']
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
                'quiz_data': quiz_data,
                'current_user': {
                    'id': current_user.id,
                    'name': current_user.name,
                    'position': current_user.current_position,
                    'rank': data['current_team_rank'],
                    'fields_to_goal': data['fields_to_goal'],
                    'teams_ahead': data['teams_ahead'],
                    'bonus_dice_sides': current_user.bonus_dice_sides,
                    'minigame_placement': current_user.minigame_placement,
                    'is_current_turn': data['current_team_turn_name'] == current_user.name
                },
                'stats': {
                    'max_board_fields': data['max_board_fields'],
                    'teams_count': data['teams_count']
                }
            }
        }
        
    except Exception as e:
        return {'error': str(e)}, 500

# NEUE QUIZ-ROUTEN

@teams_bp.route('/quiz')
@login_required
def quiz_interface():
    """Quiz-Interface für Teams"""
    if not isinstance(current_user, Team):
        flash('Nur eingeloggte Teams können Quizzes bearbeiten.', 'warning')
        return redirect(url_for('teams.team_login'))
    
    # Hole aktive Session und Quiz-Daten
    active_session = GameSession.query.filter_by(is_active=True).first()
    if not active_session or not active_session.current_quiz_id:
        flash('Derzeit ist kein Quiz aktiv.', 'info')
        return redirect(url_for('teams.team_dashboard'))
    
    if active_session.current_phase != 'QUIZ_ACTIVE':
        flash('Das Quiz ist derzeit nicht aktiv.', 'warning')
        return redirect(url_for('teams.team_dashboard'))
    
    # Hole Quiz-Daten
    active_round = GameRound.get_active_round()
    if not active_round or not active_round.minigame_folder:
        flash('Keine aktive Spielrunde gefunden.', 'danger')
        return redirect(url_for('teams.team_dashboard'))
    
    quiz_data = get_quiz_from_folder(active_round.minigame_folder.folder_path, active_session.current_quiz_id)
    if not quiz_data:
        flash('Quiz-Daten konnten nicht geladen werden.', 'danger')
        return redirect(url_for('teams.team_dashboard'))
    
    # Prüfe ob Team bereits alle Fragen beantwortet hat
    existing_responses = QuizResponse.query.filter_by(
        team_id=current_user.id,
        game_session_id=active_session.id,
        quiz_id=active_session.current_quiz_id
    ).all()
    
    answered_question_ids = [r.question_id for r in existing_responses]
    questions = quiz_data.get('questions', [])
    
    # Finde die nächste unbeantwortete Frage
    current_question = None
    question_index = 0
    
    for i, question in enumerate(questions):
        if question['id'] not in answered_question_ids:
            current_question = question
            question_index = i
            break
    
    if not current_question:
        flash('Du hast bereits alle Fragen beantwortet!', 'success')
        return redirect(url_for('teams.team_dashboard'))
    
    # Quiz-Zeitlimit prüfen
    quiz_time_expired = False
    time_remaining = None
    
    if quiz_data.get('time_limit', 0) > 0 and active_session.quiz_started_at:
        from datetime import timedelta
        elapsed_time = datetime.utcnow() - active_session.quiz_started_at
        time_remaining = quiz_data['time_limit'] - elapsed_time.total_seconds()
        
        if time_remaining <= 0:
            quiz_time_expired = True
            flash('Das Zeitlimit für dieses Quiz ist abgelaufen.', 'warning')
            return redirect(url_for('teams.team_dashboard'))
    
    return render_template('quiz_interface.html',
                         quiz_data=quiz_data,
                         current_question=current_question,
                         question_index=question_index,
                         total_questions=len(questions),
                         answered_questions=len(existing_responses),
                         time_remaining=time_remaining,
                         active_session=active_session)

@teams_bp.route('/quiz/answer', methods=['POST'])
@login_required
def submit_quiz_answer():
    """Verarbeite Quiz-Antwort eines Teams"""
    if not isinstance(current_user, Team):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'Keine Daten empfangen'}), 400
        
        question_id = data.get('question_id')
        quiz_id = data.get('quiz_id')
        answer_type = data.get('answer_type')
        
        if not all([question_id, quiz_id, answer_type]):
            return jsonify({'success': False, 'error': 'Fehlende erforderliche Daten'}), 400
        
        # Hole aktive Session
        active_session = GameSession.query.filter_by(is_active=True).first()
        if not active_session or active_session.current_quiz_id != quiz_id:
            return jsonify({'success': False, 'error': 'Kein aktives Quiz gefunden'}), 404
        
        if active_session.current_phase != 'QUIZ_ACTIVE':
            return jsonify({'success': False, 'error': 'Quiz ist nicht aktiv'}), 403
        
        # Prüfe ob bereits beantwortet
        existing_response = QuizResponse.query.filter_by(
            team_id=current_user.id,
            game_session_id=active_session.id,
            quiz_id=quiz_id,
            question_id=question_id
        ).first()
        
        if existing_response:
            return jsonify({'success': False, 'error': 'Frage bereits beantwortet'}), 409
        
        # Hole Quiz-Daten
        active_round = GameRound.get_active_round()
        if not active_round or not active_round.minigame_folder:
            return jsonify({'success': False, 'error': 'Keine aktive Spielrunde'}), 404
        
        quiz_data = get_quiz_from_folder(active_round.minigame_folder.folder_path, quiz_id)
        if not quiz_data:
            return jsonify({'success': False, 'error': 'Quiz-Daten nicht gefunden'}), 404
        
        # Finde die Frage
        question = None
        for q in quiz_data.get('questions', []):
            if q['id'] == question_id:
                question = q
                break
        
        if not question:
            return jsonify({'success': False, 'error': 'Frage nicht gefunden'}), 404
        
        # Prüfe Zeitlimit
        if quiz_data.get('time_limit', 0) > 0 and active_session.quiz_started_at:
            elapsed_time = datetime.utcnow() - active_session.quiz_started_at
            if elapsed_time.total_seconds() > quiz_data['time_limit']:
                return jsonify({'success': False, 'error': 'Zeitlimit überschritten'}), 403
        
        # Erstelle Antwort-Objekt
        response = QuizResponse(
            team_id=current_user.id,
            game_session_id=active_session.id,
            quiz_id=quiz_id,
            question_id=question_id
        )
        
        # Verarbeite Antwort basierend auf Typ
        is_correct = False
        points_earned = 0
        
        if answer_type == 'multiple_choice':
            selected_option = data.get('selected_option')
            if selected_option is not None:
                response.selected_option = int(selected_option)
                
                # Prüfe Korrektheit
                correct_option = question.get('correct_option', 0)
                if selected_option == correct_option:
                    is_correct = True
                    points_earned = question.get('points', 10)
        
        elif answer_type == 'text_input':
            answer_text = data.get('answer_text', '').strip()
            response.answer_text = answer_text
            
            # Prüfe Korrektheit (case-insensitive)
            correct_text = question.get('correct_text', '').strip().lower()
            if answer_text.lower() == correct_text:
                is_correct = True
                points_earned = question.get('points', 10)
        
        else:
            return jsonify({'success': False, 'error': 'Ungültiger Antworttyp'}), 400
        
        response.is_correct = is_correct
        response.points_earned = points_earned
        
        # Speichere in Datenbank
        db.session.add(response)
        db.session.commit()
        
        # Prüfe ob alle Teams alle Fragen beantwortet haben
        total_teams = Team.query.count()
        total_questions = len(quiz_data.get('questions', []))
        total_expected_responses = total_teams * total_questions
        
        total_actual_responses = QuizResponse.query.filter_by(
            game_session_id=active_session.id,
            quiz_id=quiz_id
        ).count()
        
        quiz_completed = total_actual_responses >= total_expected_responses
        
        # Berechne Fortschritt für dieses Team
        team_responses = QuizResponse.query.filter_by(
            team_id=current_user.id,
            game_session_id=active_session.id,
            quiz_id=quiz_id
        ).count()
        
        team_completed = team_responses >= total_questions
        
        # Bestimme nächste Frage für dieses Team
        answered_question_ids = [r.question_id for r in QuizResponse.query.filter_by(
            team_id=current_user.id,
            game_session_id=active_session.id,
            quiz_id=quiz_id
        ).all()]
        
        next_question = None
        next_question_index = None
        
        for i, q in enumerate(quiz_data.get('questions', [])):
            if q['id'] not in answered_question_ids:
                next_question = q
                next_question_index = i
                break
        
        return jsonify({
            'success': True,
            'is_correct': is_correct,
            'points_earned': points_earned,
            'team_completed': team_completed,
            'quiz_completed': quiz_completed,
            'next_question': next_question,
            'next_question_index': next_question_index,
            'progress': {
                'answered': team_responses,
                'total': total_questions,
                'percentage': (team_responses / total_questions * 100) if total_questions > 0 else 100
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Serverfehler: {str(e)}'}), 500

@teams_bp.route('/quiz/status')
@login_required
def quiz_status():
    """API für Quiz-Status Updates"""
    if not isinstance(current_user, Team):
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        active_session = GameSession.query.filter_by(is_active=True).first()
        if not active_session or not active_session.current_quiz_id:
            return jsonify({
                'quiz_active': False,
                'message': 'Kein aktives Quiz'
            })
        
        if active_session.current_phase != 'QUIZ_ACTIVE':
            return jsonify({
                'quiz_active': False,
                'message': 'Quiz nicht in aktiver Phase'
            })
        
        # Hole Quiz-Daten
        active_round = GameRound.get_active_round()
        if not active_round or not active_round.minigame_folder:
            return jsonify({
                'quiz_active': False,
                'message': 'Keine aktive Spielrunde'
            })
        
        quiz_data = get_quiz_from_folder(active_round.minigame_folder.folder_path, active_session.current_quiz_id)
        if not quiz_data:
            return jsonify({
                'quiz_active': False,
                'message': 'Quiz-Daten nicht gefunden'
            })
        
        # Berechne verbleibende Zeit
        time_remaining = None
        time_expired = False
        
        if quiz_data.get('time_limit', 0) > 0 and active_session.quiz_started_at:
            elapsed_time = datetime.utcnow() - active_session.quiz_started_at
            time_remaining = max(0, quiz_data['time_limit'] - elapsed_time.total_seconds())
            time_expired = time_remaining <= 0
        
        # Hole Team-Fortschritt
        team_responses = QuizResponse.query.filter_by(
            team_id=current_user.id,
            game_session_id=active_session.id,
            quiz_id=active_session.current_quiz_id
        ).count()
        
        total_questions = len(quiz_data.get('questions', []))
        team_completed = team_responses >= total_questions
        
        return jsonify({
            'quiz_active': True,
            'quiz_data': {
                'id': quiz_data['id'],
                'name': quiz_data['name'],
                'description': quiz_data.get('description', ''),
                'time_limit': quiz_data.get('time_limit', 0),
                'questions_count': total_questions
            },
            'time_remaining': time_remaining,
            'time_expired': time_expired,
            'team_progress': {
                'answered': team_responses,
                'total': total_questions,
                'completed': team_completed,
                'percentage': (team_responses / total_questions * 100) if total_questions > 0 else 100
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500