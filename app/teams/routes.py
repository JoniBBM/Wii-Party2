from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models import Team, db, Admin, GameSession, GameRound, QuestionResponse, GameEvent, Character, CharacterPart
from flask import current_app
from app.forms import TeamLoginForm, QuestionAnswerForm
from app.admin.minigame_utils import get_question_from_folder
from app import csrf
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
            login_user(team, remember=True)  # Remember session für längere Laufzeit
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
        GameEvent.event_type.in_([
            'dice_roll', 'admin_dice_roll', 'admin_dice_roll_legacy', 'team_dice_roll',
            'special_field_catapult_forward', 'special_field_catapult_backward',
            'special_field_player_swap'
        ])
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
        # Parse data_json für Event-Daten
        event_data = {}
        if event.data_json:
            try:
                if isinstance(event.data_json, str):
                    try:
                        event_data = json.loads(event.data_json)
                    except json.JSONDecodeError:
                        try:
                            event_data = eval(event.data_json)
                        except:
                            event_data = {}
                else:
                    event_data = event.data_json
            except Exception as e:
                event_data = {}
        
        # Behandle verschiedene Event-Typen
        if event.event_type in ['dice_roll', 'admin_dice_roll', 'admin_dice_roll_legacy', 'team_dice_roll']:
            # Standard Würfel-Event
            move_number += 1
            old_position = event_data.get('old_position', 0)
            new_position = event_data.get('new_position', team_user.current_position)
            dice_total = event_data.get('total_roll', 0)
            
            progress_data.append({
                'move': move_number,
                'position': new_position,
                'timestamp': event.timestamp.strftime('%H:%M:%S'),
                'description': f'Würfelwurf: {dice_total}' if dice_total > 0 else 'Bewegung',
                'dice_roll': dice_total,
                'event_type': event.event_type
            })
            
        elif event.event_type in ['special_field_catapult_forward', 'special_field_catapult_backward']:
            # Katapult-Event
            move_number += 1
            old_position = event_data.get('old_position', 0)
            new_position = event_data.get('new_position', team_user.current_position)
            catapult_distance = event_data.get('catapult_distance', 0)
            direction = 'vorwärts' if event.event_type == 'special_field_catapult_forward' else 'rückwärts'
            
            progress_data.append({
                'move': move_number,
                'position': new_position,
                'timestamp': event.timestamp.strftime('%H:%M:%S'),
                'description': f'Katapult {direction}: {catapult_distance} Felder',
                'catapult_distance': catapult_distance,
                'catapult_direction': direction,
                'event_type': event.event_type
            })
            
        elif event.event_type == 'special_field_player_swap':
            # Spieler-Tausch Event
            move_number += 1
            is_initiating = event_data.get('is_initiating_team', False)
            
            if is_initiating:
                # Team das gewürfelt hat
                old_position = event_data.get('current_team_old_position', 0)
                new_position = event_data.get('current_team_new_position', team_user.current_position)
                swap_team_name = event_data.get('swap_team_name', 'Unbekannt')
            else:
                # Team das getauscht wurde
                old_position = event_data.get('swap_team_old_position', 0)
                new_position = event_data.get('swap_team_new_position', team_user.current_position)
                swap_team_name = event_data.get('current_team_name', 'Unbekannt')
            
            progress_data.append({
                'move': move_number,
                'position': new_position,
                'timestamp': event.timestamp.strftime('%H:%M:%S'),
                'description': f'Tausch mit {swap_team_name}',
                'swap_team_name': swap_team_name,
                'is_initiating_team': is_initiating,
                'event_type': event.event_type
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
        GameEvent.event_type.in_(['dice_roll', 'admin_dice_roll', 'admin_dice_roll_legacy', 'team_dice_roll'])
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
                    game_status = f"Du bist am Zug! Klicke auf 'Würfeln' um zu würfeln"
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
@csrf.exempt
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
            
            # Erweiterte Charakter-Anpassung Daten
            customization_data = data.get('customization', {})
            
            # Rückwärtskompatibilität mit alten Farbdaten
            if not customization_data:
                character_customization = {
                    'shirtColor': data.get('shirt_color', '#4169E1'),
                    'pantsColor': data.get('pants_color', '#8B4513'),
                    'hairColor': data.get('hair_color', '#2C1810'),
                    'shoeColor': data.get('shoe_color', '#8B4513')
                }
            else:
                # Neue umfassende Anpassungsdaten
                character_customization = {
                    # Basis-Farben
                    'shirtColor': customization_data.get('shirtColor', '#4169E1'),
                    'pantsColor': customization_data.get('pantsColor', '#8B4513'),
                    'hairColor': customization_data.get('hairColor', '#2C1810'),
                    'shoeColor': customization_data.get('shoeColor', '#8B4513'),
                    'skinColor': customization_data.get('skinColor', '#FFDE97'),
                    'eyeColor': customization_data.get('eyeColor', '#4169E1'),
                    
                    # Aussehen
                    'faceShape': customization_data.get('faceShape', 'oval'),
                    'bodyType': customization_data.get('bodyType', 'normal'),
                    'height': customization_data.get('height', 'normal'),
                    'hairStyle': customization_data.get('hairStyle', 'short'),
                    'eyeShape': customization_data.get('eyeShape', 'normal'),
                    'beardStyle': customization_data.get('beardStyle', 'none'),
                    
                    # Kleidung
                    'shirtType': customization_data.get('shirtType', 'tshirt'),
                    'pantsType': customization_data.get('pantsType', 'jeans'),
                    'shoeType': customization_data.get('shoeType', 'sneakers'),
                    
                    # Accessoires
                    'hat': customization_data.get('hat', 'none'),
                    'glasses': customization_data.get('glasses', 'none'),
                    'jewelry': customization_data.get('jewelry', 'none'),
                    'backpack': customization_data.get('backpack', 'none'),
                    
                    # Animationen
                    'animationStyle': customization_data.get('animationStyle', 'normal'),
                    'walkStyle': customization_data.get('walkStyle', 'normal'),
                    'idleStyle': customization_data.get('idleStyle', 'normal'),
                    'voiceType': customization_data.get('voiceType', 'normal'),
                    
                    # Zusätzliche Eigenschaften
                    'voicePitch': customization_data.get('voicePitch', 1.0),
                    'defaultPose': customization_data.get('defaultPose', 'normal'),
                    'defaultExpression': customization_data.get('defaultExpression', 'happy'),
                    'aura': customization_data.get('aura', 'none'),
                    'trail': customization_data.get('trail', 'none')
                }
            
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
            
            # Erstelle oder finde Default-Charakter für alle Teams
            character = None
            if not character_id:
                character_id = 1  # Default auf Default-Charakter setzen
                
            if character_id:
                try:
                    character_id = int(character_id)
                    # Für Default-Charakter (ID 1) keine Verfügbarkeitsprüfung
                    if character_id == 1:
                        character = Character.query.get(character_id)
                        if not character:
                            # Erstelle Default-Charakter falls nicht vorhanden
                            character = Character(
                                id=1,
                                name="Default Character",
                                js_file="js/characters/defaultCharacter.js",
                                image_file="default.png",
                                color="#FF6B6B",
                                is_selected=False
                            )
                            db.session.add(character)
                            db.session.flush()  # Um ID zu bekommen
                    else:
                        # Für andere Charaktere normale Verfügbarkeitsprüfung
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
            
            # Für Default-Charakter (ID 1) keine Exklusivität - alle Teams können ihn verwenden
            if current_user.character_id and current_user.character_id != 1:
                old_character = Character.query.get(current_user.character_id)
                if old_character:
                    old_character.is_selected = False
            
            # Aktualisiere Team
            current_user.name = new_team_name
            if character:
                current_user.character_id = character.id
                current_user.character_name = character.name
                # Default-Charakter wird nicht als "selected" markiert, da alle ihn verwenden können
                if character.id != 1:
                    character.is_selected = True
            
            # Speichere Charakter-Anpassung
            current_user.set_character_customization(character_customization)
            
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

@teams_bp.route('/api/characters')
def api_characters():
    """API endpoint für Charakterdaten"""
    try:
        # Hole alle verfügbaren Charaktere
        characters = Character.query.all()
        
        character_data = []
        for char in characters:
            # Prüfe ob Charakter für aktuelles Team verfügbar ist
            is_available = True
            current_team = current_user if isinstance(current_user, Team) else None
            
            if not char.is_available_for_team(current_team):
                is_available = False
            
            char_info = {
                'id': char.id,
                'name': char.name,
                'description': char.description,
                'category': char.category,
                'rarity': char.rarity,
                'color': char.color,
                'is_unlocked': char.is_unlocked,
                'is_available': is_available,
                'stats': char.get_stats(),
                'customization_options': char.get_customization_options(),
                'preview_image': char.preview_image,
                'thumbnail': char.thumbnail
            }
            
            character_data.append(char_info)
        
        return jsonify(character_data)
    
    except Exception as e:
        current_app.logger.error(f"Fehler beim Laden der Charakterdaten: {e}")
        return jsonify({'error': 'Fehler beim Laden der Charakterdaten'}), 500

@teams_bp.route('/api/character-parts')
def api_character_parts():
    """API endpoint für Charakter-Teile"""
    try:
        category = request.args.get('category')
        subcategory = request.args.get('subcategory')
        
        if category:
            parts = CharacterPart.get_parts_by_category(category, subcategory)
        else:
            parts = CharacterPart.query.all()
        
        parts_data = []
        for part in parts:
            # Prüfe ob Teil für aktuelles Team verfügbar ist
            is_available = True
            current_team = current_user if isinstance(current_user, Team) else None
            
            if not part.is_available_for_team(current_team):
                is_available = False
            
            part_info = {
                'id': part.id,
                'name': part.name,
                'category': part.category,
                'subcategory': part.subcategory,
                'rarity': part.rarity,
                'is_unlocked': part.is_unlocked,
                'is_available': is_available,
                'asset_path': part.asset_path,
                'icon_path': part.icon_path,
                'color_customizable': part.color_customizable,
                'default_color': part.default_color,
                'description': part.description,
                'compatible_body_types': part.get_compatible_body_types(),
                'compatible_face_shapes': part.get_compatible_face_shapes(),
                'stats_modifier': part.get_stats_modifier(),
                'special_effects': part.get_special_effects()
            }
            
            parts_data.append(part_info)
        
        return jsonify(parts_data)
    
    except Exception as e:
        current_app.logger.error(f"Fehler beim Laden der Charakter-Teile: {e}")
        return jsonify({'error': 'Fehler beim Laden der Charakter-Teile'}), 500

@teams_bp.route('/api/dashboard-status')
@login_required
def dashboard_status_api():
    """API für Live-Updates des Team Dashboards"""
    if not isinstance(current_user, Team):
        return {'error': 'Unauthorized'}, 403
    
    try:
        # Hole aktuelle Daten
        data = _get_dashboard_data(current_user)
        
        # DEBUG: Minigame-Daten aus Session prüfen
        if data['active_session']:
            current_app.logger.info(f"DEBUG dashboard_status_api: session.current_minigame_name='{data['active_session'].current_minigame_name}', session.current_minigame_description='{data['active_session'].current_minigame_description}', session.current_phase='{data['active_session'].current_phase}'")
        
        # Konvertiere Teams zu JSON-freundlichem Format
        teams_data = []
        for team in data['all_teams']:
            team_data = {
                'id': team.id,
                'name': team.name,
                'position': team.current_position,
                'minigame_placement': team.minigame_placement,
                'bonus_dice_sides': team.bonus_dice_sides,
                'character_name': team.character.name if team.character else None,
                'is_current_user': team.id == current_user.id
            }
            
            # Füge vollständige Charakter-Daten hinzu wenn verfügbar
            if team.character:
                team_data['character'] = {
                    'id': team.character.id,
                    'name': team.character.name,
                    'color': team.character.color,
                    'js_file': team.character.js_file,
                    'image_file': team.character.image_file,
                    'preview_image': team.character.preview_image,
                    'thumbnail': team.character.thumbnail
                }
            else:
                team_data['character'] = None
            
            # Füge Charakter-Anpassungen hinzu wenn verfügbar
            if hasattr(team, 'get_character_customization'):
                team_data['character_customization'] = team.get_character_customization()
            else:
                team_data['character_customization'] = None
                
            teams_data.append(team_data)
        
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
            # Hole die Antwort des Teams für diese Frage
            question_response = data.get('question_response')
            is_correct = question_response.is_correct if question_response else None
            
            question_data = {
                'id': data['current_question_data']['id'],
                'name': data['current_question_data']['name'],
                'description': data['current_question_data'].get('description', ''),
                'question_text': data['current_question_data'].get('question_text', ''),
                'question_type': data['current_question_data'].get('question_type', 'multiple_choice'),
                'options': data['current_question_data'].get('options', []),
                'answered': data['question_answered'],
                'is_correct': is_correct
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
                'special_field_event': _get_recent_special_field_event(current_user, data['active_session']),
                # NEU: Ausgewählte Spieler für Minispiele
                'selected_players': data['active_session'].get_selected_players() if data['active_session'] else None,
                'current_player_count': data['active_session'].current_player_count if data['active_session'] else None
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
        
        # Suche nach verschiedenen Event-Typen
        special_field_event_types = [
            'field_action',  # Barrier events
            'special_field_catapult_forward',
            'special_field_catapult_backward', 
            'special_field_player_swap'
        ]
        
        recent_event = GameEvent.query.filter(
            GameEvent.game_session_id == session.id,
            GameEvent.related_team_id == team.id,
            GameEvent.event_type.in_(special_field_event_types),
            GameEvent.timestamp >= recent_time
        ).order_by(GameEvent.timestamp.desc()).first()
        
        if recent_event and recent_event.data:
            event_data = recent_event.data
            event_type = recent_event.event_type
            
            # Handle different event types
            if event_type == 'field_action':
                # Check if it's a barrier-related event
                if event_data.get('action') == 'barrier' and event_data.get('barrier_set'):
                    return {
                        'type': 'barrier_set',
                        'event_id': recent_event.id,
                        'timestamp': recent_event.timestamp.isoformat(),
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
                            'event_id': recent_event.id,
                            'timestamp': recent_event.timestamp.isoformat(),
                            'dice_roll': dice_roll_data,
                            'barrier_config': event_data.get('barrier_config'),
                            'release_method': event_data.get('release_method')
                        }
                    else:
                        return {
                            'type': 'barrier_failed',
                            'event_id': recent_event.id,
                            'timestamp': recent_event.timestamp.isoformat(),
                            'dice_roll': dice_roll_data,
                            'barrier_config': event_data.get('barrier_config')
                        }
            
            elif event_type == 'special_field_catapult_forward':
                return {
                    'type': 'catapult_forward',
                    'event_id': recent_event.id,
                    'timestamp': recent_event.timestamp.isoformat(),
                    'catapult_distance': event_data.get('catapult_distance'),
                    'old_position': event_data.get('old_position'),
                    'new_position': event_data.get('new_position'),
                    # Original Würfel-Bewegung
                    'dice_old_position': event_data.get('dice_old_position'),
                    'dice_new_position': event_data.get('dice_new_position'),
                    'dice_roll': event_data.get('dice_roll'),
                    'bonus_roll': event_data.get('bonus_roll'),
                    'total_roll': event_data.get('total_roll')
                }
            
            elif event_type == 'special_field_catapult_backward':
                return {
                    'type': 'catapult_backward',
                    'event_id': recent_event.id,
                    'timestamp': recent_event.timestamp.isoformat(),
                    'catapult_distance': event_data.get('catapult_distance'),
                    'old_position': event_data.get('old_position'),
                    'new_position': event_data.get('new_position'),
                    # Original Würfel-Bewegung
                    'dice_old_position': event_data.get('dice_old_position'),
                    'dice_new_position': event_data.get('dice_new_position'),
                    'dice_roll': event_data.get('dice_roll'),
                    'bonus_roll': event_data.get('bonus_roll'),
                    'total_roll': event_data.get('total_roll')
                }
            
            elif event_type == 'special_field_player_swap':
                return {
                    'type': 'player_swap',
                    'event_id': recent_event.id,
                    'timestamp': recent_event.timestamp.isoformat(),
                    'swap_team_name': event_data.get('swap_team_name'),
                    'current_team_name': event_data.get('current_team_name'),
                    'current_team_old_position': event_data.get('current_team_old_position'),
                    'current_team_new_position': event_data.get('current_team_new_position'),
                    'swap_team_old_position': event_data.get('swap_team_old_position'),
                    'swap_team_new_position': event_data.get('swap_team_new_position'),
                    'is_initiating_team': event_data.get('is_initiating_team', False)
                }
        
        return None
        
    except Exception as e:
        print(f"Error getting special field event: {e}")
        return None

@teams_bp.route('/api/team_roll_dice_test', methods=['POST'])
@login_required
def team_roll_dice_test():
    """Test-Route für Team-Würfeln"""
    if not isinstance(current_user, Team):
        return jsonify({"success": False, "error": "Nur Teams können würfeln."}), 403
    
    try:
        return jsonify({
            "success": True,
            "message": "Test erfolgreich",
            "team_name": current_user.name,
            "team_id": current_user.id,
            "is_authenticated": True
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@teams_bp.route('/api/team_roll_dice', methods=['POST'])
@login_required
def team_roll_dice():
    """Team würfelt für sich selbst, wenn es am Zug ist"""
    if not isinstance(current_user, Team):
        return jsonify({"success": False, "error": "Nur Teams können würfeln."}), 403
    
    try:
        # Importiere die notwendigen Funktionen
        import random
        import json
        from app.models import GameEvent
        
        current_app.logger.info(f"Team {current_user.name} (ID: {current_user.id}) versucht zu würfeln")
        
        # Prüfe Spielsitzung
        active_session = GameSession.query.filter_by(is_active=True).first()
        if not active_session:
            return jsonify({"success": False, "error": "Keine aktive Spielsitzung."}), 404
        
        if active_session.current_phase != 'DICE_ROLLING':
            return jsonify({"success": False, "error": "Es ist nicht die Würfelphase."}), 403
        
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
                    related_team_id=current_user.id
                ).filter(
                    GameEvent.event_type.in_(['team_dice_roll', 'admin_dice_roll'])
                ).count()
                
                # Ermittle welche "Runde" wir sind (wie oft jedes Team gewürfelt haben sollte)
                expected_round = (all_dice_events_in_session // total_teams) + 1
                
                # Wenn das Team bereits in dieser Runde gewürfelt hat, verweigern
                if team_dice_events >= expected_round:
                    if current_user.id != active_session.current_team_turn_id:
                        return jsonify({"success": False, "error": "Du hast bereits in dieser Runde gewürfelt."}), 403
                        
            except (ValueError, ZeroDivisionError) as e:
                current_app.logger.warning(f"Fehler bei Würfel-Validierung: {e}")
                pass  # Bei Fehlern in der Logik, erlaube Würfeln

        # Prüfe ob das Team am Zug ist
        if active_session.current_team_turn_id != current_user.id:
            current_team = Team.query.get(active_session.current_team_turn_id) if active_session.current_team_turn_id else None
            current_team_name = current_team.name if current_team else "Unbekannt"
            return jsonify({"success": False, "error": f"Du bist nicht am Zug. Aktuell ist {current_team_name} am Zug."}), 403
        
        team = current_user
        
        # Würfeln
        standard_dice_roll = random.randint(1, 6)
        bonus_dice_roll = 0
        
        current_app.logger.info(f"Team {team.name} würfelt selbst - Bonus-Würfel-Seiten: {team.bonus_dice_sides}")
        
        if team.bonus_dice_sides and team.bonus_dice_sides > 0:
            bonus_dice_roll = random.randint(1, team.bonus_dice_sides)
            current_app.logger.info(f"Team {team.name} erhält Bonus-Würfel: {bonus_dice_roll} (von 1-{team.bonus_dice_sides})")
        else:
            current_app.logger.info(f"Team {team.name} erhält keinen Bonus-Würfel")
        
        total_roll = standard_dice_roll + bonus_dice_roll
        old_position = team.current_position
        
        # Einfache Bewegung (ohne Sonderfelder erstmal)
        max_field_index = current_app.config.get('MAX_BOARD_FIELDS', 72)
        new_position = min(team.current_position + total_roll, max_field_index)
        team.current_position = new_position
        
        # Sonderfeld-Behandlung (falls Module verfügbar)
        special_field_result = None
        barrier_check_result = None
        
        try:
            from app.game_logic.special_fields import handle_special_field_action, check_barrier_release
            
            # SONDERFELD: Prüfe Sperren-Status
            if team.is_blocked:
                # Team ist blockiert - prüfe ob es freikommt
                barrier_check_result = check_barrier_release(team, standard_dice_roll, active_session, bonus_dice_roll)
                
                if barrier_check_result['released']:
                    # Team ist befreit und kann sich normal bewegen
                    team.current_position = new_position
                else:
                    # Team bleibt blockiert, keine Bewegung
                    new_position = old_position
                    team.current_position = old_position
            
            # Prüfe Sonderfeld-Aktion nach Bewegung (nur wenn nicht blockiert)
            if not team.is_blocked or (barrier_check_result and barrier_check_result.get('released', False)):
                all_teams = Team.query.all()
                dice_info = {
                    "old_position": old_position,
                    "new_position": new_position,
                    "dice_roll": standard_dice_roll,
                    "bonus_roll": bonus_dice_roll,
                    "total_roll": total_roll
                }
                special_field_result = handle_special_field_action(team, all_teams, active_session, dice_info)
        except ImportError as e:
            current_app.logger.warning(f"Sonderfeld-Module nicht verfügbar: {e}")
        except Exception as e:
            current_app.logger.error(f"Fehler bei Sonderfeld-Behandlung: {e}")
            # Fehler bei Sonderfeldern sollen das Würfeln nicht stoppen
        
        # Event für den Würfelwurf erstellen
        event_description = f"Team {team.name} würfelte selbst: {standard_dice_roll}"
        if bonus_dice_roll > 0:
            event_description += f" (Bonus: {bonus_dice_roll}, Gesamt: {total_roll})"
        
        if team.is_blocked and (not barrier_check_result or not barrier_check_result.get('released', False)):
            event_description += f" - BLOCKIERT: Konnte sich nicht befreien."
        else:
            event_description += f" und bewegte sich von Feld {old_position} zu Feld {new_position}."
        
        # Prepare dice event data
        dice_event_data = {
            "standard_roll": standard_dice_roll,
            "bonus_roll": bonus_dice_roll,
            "total_roll": total_roll,
            "old_position": old_position,
            "new_position": new_position,
            "rolled_by": "team",
            "was_blocked": team.is_blocked and (not barrier_check_result or not barrier_check_result.get('released', False)),
            "barrier_released": barrier_check_result.get('released', False) if barrier_check_result else False
        }
        
        # Add barrier config if team was blocked
        if team.is_blocked:
            barrier_config = None
            display_text = 'Höhere Zahl benötigt'
            
            # Try to get config from barrier_check_result first
            if barrier_check_result and barrier_check_result.get('barrier_config'):
                barrier_config = barrier_check_result.get('barrier_config', {})
                display_text = barrier_config.get('display_text', 'Höhere Zahl benötigt')
                current_app.logger.info(f"[BARRIER DEBUG] Got barrier config from check result: {barrier_config}")
            else:
                # Fallback: Get config from team's stored blocked_config
                try:
                    if hasattr(team, 'blocked_config') and team.blocked_config:
                        import json
                        barrier_config = json.loads(team.blocked_config)
                        display_text = barrier_config.get('display_text', 'Höhere Zahl benötigt')
                        current_app.logger.info(f"[BARRIER DEBUG] Got barrier config from team storage: {barrier_config}")
                    else:
                        # Fallback 2: Get current barrier field configuration
                        try:
                            from app.models import FieldConfiguration
                            barrier_field_config = FieldConfiguration.get_config_for_field('barrier')
                            if barrier_field_config and barrier_field_config.is_enabled:
                                config_data = barrier_field_config.config_dict
                                target_numbers = config_data.get('target_numbers', [4, 5, 6])
                                
                                # Parse the target numbers using the same logic as handle_barrier_field
                                from app.game_logic.special_fields import _parse_barrier_config
                                barrier_config = _parse_barrier_config(target_numbers)
                                display_text = barrier_config.get('display_text', 'Höhere Zahl benötigt')
                                current_app.logger.info(f"[BARRIER DEBUG] Got barrier config from FieldConfiguration: {barrier_config}")
                            else:
                                raise Exception("No barrier field configuration found")
                        except Exception as fe:
                            current_app.logger.warning(f"[BARRIER DEBUG] Could not load barrier field config: {fe}")
                            # Ultimate fallback: create basic config from blocked_target_number
                            target_number = team.blocked_target_number or 4
                            barrier_config = {
                                'mode': 'minimum', 
                                'min_number': target_number,
                                'display_text': f'Würfle mindestens eine {target_number}!'
                            }
                            display_text = barrier_config['display_text']
                            current_app.logger.info(f"[BARRIER DEBUG] Created ultimate fallback barrier config: {barrier_config}")
                except Exception as e:
                    current_app.logger.error(f"[BARRIER DEBUG] Error getting barrier config: {e}")
                    barrier_config = {'mode': 'minimum', 'min_number': 4, 'display_text': 'Würfle mindestens eine 4!'}
                    display_text = barrier_config['display_text']
            
            dice_event_data["barrier_config"] = barrier_config or {}
            dice_event_data["barrier_display_text"] = display_text
            current_app.logger.info(f"[BARRIER DEBUG] Final barrier data - config: {barrier_config}, text: {display_text}")
        else:
            current_app.logger.info(f"[BARRIER DEBUG] Team {team.name} is not blocked")
        
        dice_event = GameEvent(
            game_session_id=active_session.id,
            event_type="team_dice_roll",
            description=event_description,
            related_team_id=team.id,
            data_json=json.dumps(dice_event_data)
        )
        db.session.add(dice_event)
        
        # Setze Bonuswürfel zurück (wird nach jedem Wurf verbraucht)
        team.bonus_dice_sides = 0
        
        # FIX: Verbesserte Logik für Rundenerkennung - prüfe wieviele Teams bereits gewürfelt haben
        next_team = None
        round_complete = False
        
        if active_session.dice_roll_order:
            try:
                team_ids = [int(tid) for tid in active_session.dice_roll_order.split(',') if tid.strip().isdigit()]
                total_teams = len(team_ids)
                
                # Zähle ALLE Würfel-Events in dieser Session
                all_dice_events_in_session = GameEvent.query.filter_by(
                    game_session_id=active_session.id
                ).filter(
                    GameEvent.event_type.in_(['team_dice_roll', 'admin_dice_roll'])
                ).count()
                
                # Nach diesem Wurf haben wir einen weiteren Event
                total_events_after_this_roll = all_dice_events_in_session + 1
                
                current_app.logger.info(f"Würfel-Events: {total_events_after_this_roll}, Teams: {total_teams}")
                
                # FIX: Ermittle das nächste Team in der Reihenfolge  
                current_index = team_ids.index(team.id)
                next_index = (current_index + 1) % len(team_ids)
                next_team = Team.query.get(team_ids[next_index])
                
                # FIX: Runde ist beendet wenn wir beim letzten Team sind UND es gerade gewürfelt hat
                # Das bedeutet: wir sind bei Team an letzter Position in dice_roll_order
                is_last_team_in_order = current_index == (total_teams - 1)
                
                if is_last_team_in_order:
                    # Letztes Team hat gewürfelt - Runde beenden
                    round_complete = True
                    current_app.logger.info(f"Letztes Team ({team.name}) hat gewürfelt - Runde beendet")
                else:
                    current_app.logger.info(f"Team {team.name} (Position {current_index + 1}/{total_teams}) hat gewürfelt. Nächstes Team: {next_team.name if next_team else 'None'}")
                    
            except (ValueError, IndexError) as e:
                current_app.logger.warning(f"Fehler beim Ermitteln des nächsten Teams: {e}. Reihenfolge: {active_session.dice_roll_order}")
                # Fallback: Runde beenden
                round_complete = True
        
        # FIX: Verwende round_complete statt nächstes Team Vergleich
        if round_complete:
            active_session.current_phase = 'ROUND_OVER'
            active_session.current_team_turn_id = None
            
            # WICHTIG: Erstelle Event für Rundenende
            round_end_event = GameEvent(
                game_session_id=active_session.id,
                event_type="dice_round_ended",
                description="Würfelrunde beendet - alle Teams haben gewürfelt"
            )
            db.session.add(round_end_event)
            
            current_app.logger.info(f"Alle Teams haben gewürfelt. Runde beendet.")
        elif next_team:
            # Runde geht weiter - nächstes Team ist dran
            active_session.current_team_turn_id = next_team.id
            current_app.logger.info(f"Nächstes Team am Zug: {next_team.name}")
        else:
            # Fallback: Keine Teams gefunden oder Fehler - beende Runde
            active_session.current_phase = 'ROUND_OVER'
            active_session.current_team_turn_id = None
            
            # WICHTIG: Erstelle Event für Rundenende
            round_end_event = GameEvent(
                game_session_id=active_session.id,
                event_type="dice_round_ended",
                description="Würfelrunde beendet - keine weiteren Teams"
            )
            db.session.add(round_end_event)
            
            current_app.logger.info(f"Keine weiteren Teams. Runde beendet.")
        
        db.session.commit()
        
        # Bereite Response vor
        response_data = {
            "success": True,
            "standard_roll": standard_dice_roll,
            "bonus_roll": bonus_dice_roll,
            "total_roll": total_roll,
            "old_position": old_position,
            "new_position": new_position,
            "team_name": team.name,
            "next_team_name": next_team.name if next_team else None,
            "phase": active_session.current_phase,
            "was_blocked": team.is_blocked and (not barrier_check_result or not barrier_check_result.get('released', False)),
            "barrier_released": barrier_check_result.get('released', False) if barrier_check_result else False
        }
        
        # Füge Barrier-Check-Informationen hinzu
        if barrier_check_result:
            response_data['barrier_check'] = barrier_check_result
        
        # Füge Sonderfeld-Informationen hinzu, aber überschreibe nicht success=True
        if special_field_result:
            # Entferne success aus special_field_result falls vorhanden
            special_field_result_copy = special_field_result.copy()
            special_field_result_copy.pop('success', None)
            response_data.update(special_field_result_copy)
        
        # Stelle sicher, dass success=True gesetzt ist
        response_data['success'] = True
        
        return jsonify(response_data)
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Schwerer Fehler in team_roll_dice: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"Ein interner Serverfehler beim Würfeln ist aufgetreten: {str(e)}"}), 500

@teams_bp.route('/api/active-fields')
@login_required
def get_active_fields():
    """Gibt eine Übersicht aller aktiven Spezialfelder zurück"""
    try:
        from app.models import FieldConfiguration
        
        # Hole alle aktivierten Feld-Konfigurationen
        active_configs = FieldConfiguration.get_all_enabled()
        
        field_details = []
        
        # Füge Standard-Felder hinzu die immer aktiv sind
        standard_fields = [
            {
                'field_type': 'normal',
                'display_name': 'Normale Felder',
                'description': 'Standard-Spielfelder ohne besondere Effekte',
                'icon': '⬜',
                'color_hex': '#6c757d',
                'emission_hex': '#495057',
                'frequency_type': 'default',
                'frequency_value': 0
            },
            {
                'field_type': 'start',
                'display_name': 'Startfeld',
                'description': 'Das Startfeld des Spielbretts',
                'icon': '🏁',
                'color_hex': '#28a745',
                'emission_hex': '#1e7e34',
                'frequency_type': 'fixed_positions',
                'frequency_value': 1
            },
            {
                'field_type': 'goal',
                'display_name': 'Zielfeld',
                'description': 'Das Zielfeld des Spielbretts',
                'icon': '🎯',
                'color_hex': '#dc3545',
                'emission_hex': '#c82333',
                'frequency_type': 'fixed_positions',
                'frequency_value': 1
            }
        ]
        
        # Sammle alle Feld-Typen aus der Datenbank
        db_field_types = {config.field_type for config in active_configs}
        
        # Verarbeite nur Standard-Felder, die nicht bereits in der DB konfiguriert sind
        for std_field in standard_fields:
            if std_field['field_type'] not in db_field_types:
                frequency_desc = ""
                if std_field['field_type'] == 'normal':
                    frequency_desc = "Alle übrigen Felder"
                elif std_field['field_type'] in ['start', 'goal']:
                    frequency_desc = "Einmalig (Position 0)" if std_field['field_type'] == 'start' else "Einmalig (Position 72)"
                
                field_detail = {
                    'id': f"std_{std_field['field_type']}",
                    'type': std_field['field_type'],
                    'name': std_field['display_name'],
                    'description': std_field['description'],
                    'icon': std_field['icon'],
                    'color': std_field['color_hex'],
                    'emission_color': std_field['emission_hex'],
                    'frequency': frequency_desc,
                    'frequency_value': std_field['frequency_value'],
                    'config': {}
                }
                field_details.append(field_detail)
        
        # Verarbeite Datenbank-Konfigurationen
        for config in active_configs:
            config_dict = config.config_dict
            
            # Erstelle benutzerfreundliche Häufigkeits-Beschreibung
            frequency_desc = ""
            if config.frequency_type == 'modulo':
                frequency_desc = f"Alle {config.frequency_value} Felder"
            elif config.frequency_type == 'fixed_positions':
                positions = config_dict.get('positions', [])
                if positions:
                    frequency_desc = f"Positionen: {', '.join(map(str, positions))}"
                else:
                    frequency_desc = "Feste Positionen"
            elif config.frequency_type == 'probability':
                frequency_desc = f"{config.frequency_value}% Wahrscheinlichkeit"
            else:
                frequency_desc = "Standard"
            
            # Erstelle erweiterte Beschreibung basierend auf Konfiguration
            extended_desc = config.description
            if config.field_type == 'catapult_forward':
                min_dist = config_dict.get('min_distance', 3)
                max_dist = config_dict.get('max_distance', 5)
                extended_desc += f" ({min_dist}-{max_dist} Felder)"
            elif config.field_type == 'catapult_backward':
                min_dist = config_dict.get('min_distance', 4)
                max_dist = config_dict.get('max_distance', 10)
                extended_desc += f" ({min_dist}-{max_dist} Felder zurück)"
            elif config.field_type == 'barrier':
                targets = config_dict.get('target_numbers', '4,5,6')
                extended_desc += f" (Befreiung: {targets})"
            elif config.field_type == 'player_swap':
                min_dist = config_dict.get('min_distance', 3)
                extended_desc += f" (Min. Abstand: {min_dist})"
            
            field_detail = {
                'id': config.id,
                'type': config.field_type,
                'name': config.display_name,
                'description': extended_desc,
                'icon': config.icon or '⬜',
                'color': config.color_hex or '#6c757d',
                'emission_color': config.emission_hex or config.color_hex,
                'frequency': frequency_desc,
                'frequency_value': config.frequency_value,
                'config': config_dict
            }
            field_details.append(field_detail)
        
        # Sortiere nach Feldtyp für bessere Übersicht
        field_details.sort(key=lambda x: x['name'])
        
        return jsonify({
            'success': True,
            'fields': field_details,
            'total_count': len(field_details)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Fehler beim Laden der Felder: {str(e)}'
        }), 500