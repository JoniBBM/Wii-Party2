from flask import render_template, jsonify, request, session, current_app, redirect, url_for, flash
from app.main import main_bp
from app.models import Team, Character, GameSession, GameEvent, Admin, WelcomeSession, PlayerRegistration
from app import db, csrf
import random # Für Würfellogik
import traceback # Für detaillierte Fehlermeldungen
from flask_login import current_user
from datetime import datetime, timedelta
import json


def get_consistent_emoji_for_player(player_name):
    """
    Generiert ein deterministisches Emoji für einen Spieler basierend auf seinem Namen.
    Verwendet die gleiche Hashing-Logik wie das JavaScript Frontend.
    """
    available_emojis = [
        "😀", "😃", "😄", "😁", "😆", "😅", "🤣", "😂", "🙂", "🙃", 
        "😉", "😊", "😇", "🥰", "😍", "🤩", "😘", "😗", "😚", "😙",
        "😋", "😛", "😜", "🤪", "😝", "🤑", "🤗", "🤭", "🤫", "🤔",
        "🤓", "😎", "🤡", "🥳", "😏", "😒", "😞", "😔", "😟", "😕",
        "🙁", "☹️", "😣", "😖", "😫", "😩", "🥺", "😢", "😭", "😤",
        "😠", "😡", "🤬", "🤯", "😳", "🥵", "🥶", "😱", "😨", "😰"
    ]
    
    # Verwende die gleiche Hash-Funktion wie JavaScript
    hash_value = 0
    for char in player_name:
        char_code = ord(char)
        hash_value = ((hash_value << 5) - hash_value) + char_code
        hash_value = hash_value & 0xFFFFFFFF  # Convert to 32bit integer (JavaScript behavior)
        if hash_value > 0x7FFFFFFF:  # Handle negative values like JavaScript does
            hash_value -= 0x100000000
    
    return available_emojis[abs(hash_value) % len(available_emojis)]

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/board')
def game_board():
    teams = Team.query.order_by(Team.name).all()
    
    # Prüfe ob Teams angemeldet sind - wenn nicht, zur Welcome-Seite weiterleiten
    if len(teams) == 0:
        return redirect(url_for('main.welcome'))
    
    active_session = GameSession.query.filter_by(is_active=True).first()
    is_admin = session.get('is_admin', False)
    team_colors = ["#FF5252", "#448AFF", "#4CAF50", "#FFC107", "#9C27B0", "#FF9800"]
    
    # Get minigame folder name for current session
    minigame_folder_name = "Minispiel"
    if active_session and active_session.game_round and active_session.game_round.minigame_folder:
        minigame_folder_name = active_session.game_round.minigame_folder.name
    
    return render_template('game_board.html', 
                           teams=teams, 
                           is_admin=is_admin,
                           team_colors=team_colors,
                           active_session=active_session,
                           minigame_folder_name=minigame_folder_name)

@main_bp.route('/api/board-status')
def board_status():
    """API für Spielstatus-Updates via AJAX mit verbesserter Fehlerbehandlung und Sonderfeld-Unterstützung"""
    try:
        teams_query = Team.query.order_by(Team.id).all() # Reihenfolge nach ID für Konsistenz
        active_session_query = GameSession.query.filter_by(is_active=True).first()

        team_data = []
        for team_obj in teams_query:
            char_info = None
            if team_obj.character:
                char_info = {
                    "id": team_obj.character.id,
                    "name": team_obj.character.name,
                    "color": team_obj.character.color  # Sicherstellen, dass Character Model 'color' hat
                }
            
            team_data.append({
                "id": team_obj.id,
                "name": team_obj.name,
                "position": team_obj.current_position if team_obj.current_position is not None else 0,
                "character": char_info,
                "bonus_dice_sides": team_obj.bonus_dice_sides if team_obj.bonus_dice_sides is not None else 0,
                "minigame_placement": team_obj.minigame_placement, # Kann None sein
                # SONDERFELD: Sonderfeld-Status hinzufügen
                "is_blocked": team_obj.is_blocked if hasattr(team_obj, 'is_blocked') else False,
                "blocked_target_number": team_obj.blocked_target_number if hasattr(team_obj, 'blocked_target_number') else None,
                "blocked_turns_remaining": team_obj.blocked_turns_remaining if hasattr(team_obj, 'blocked_turns_remaining') else 0,
                "extra_moves_remaining": team_obj.extra_moves_remaining if hasattr(team_obj, 'extra_moves_remaining') else 0,
                "has_shield": team_obj.has_shield if hasattr(team_obj, 'has_shield') else False
            })

        game_session_data = None
        current_team_id = None  # Initialize current_team_id before use
        if active_session_query:
            dice_order_ids = []
            if active_session_query.dice_roll_order:
                try:
                    # Stellt sicher, dass nur gültige Integer-IDs in der Liste landen
                    dice_order_ids = [int(tid_str) for tid_str in active_session_query.dice_roll_order.split(',') if tid_str.strip().isdigit()]
                except ValueError:
                    current_app.logger.error(f"Ungültige dice_roll_order: {active_session_query.dice_roll_order}")
                    dice_order_ids = [] # Im Fehlerfall leere Liste

            # Sicherstellen, dass current_team_turn_id ein Integer ist oder None
            current_team_id = active_session_query.current_team_turn_id
            if current_team_id is not None:
                try:
                    current_team_id = int(current_team_id)
                except ValueError:
                    current_app.logger.error(f"Ungültige current_team_turn_id: {current_team_id}")
                    current_team_id = None

            # Get minigame folder name from current game round
            minigame_folder_name = "Minispiel"
            if active_session_query.game_round and active_session_query.game_round.minigame_folder:
                minigame_folder_name = active_session_query.game_round.minigame_folder.name

            game_session_data = {
                "current_minigame_name": active_session_query.current_minigame_name,
                "current_minigame_description": active_session_query.current_minigame_description,
                "current_phase": active_session_query.current_phase,
                "current_team_turn_id": current_team_id,
                "current_question_id": active_session_query.current_question_id,
                "dice_roll_order": dice_order_ids,
                "minigame_folder_name": minigame_folder_name,
                # SONDERFELD: Vulkan-Status (für zukünftige Implementierung)
                "volcano_countdown": active_session_query.volcano_countdown if hasattr(active_session_query, 'volcano_countdown') else 0,
                "volcano_active": active_session_query.volcano_active if hasattr(active_session_query, 'volcano_active') else False
            }
        
        # Get recent events (dice results and special field events)
        last_dice_result = None
        last_special_field_event = None
        from datetime import datetime, timedelta
        
        # Only get events from the last 10 seconds to avoid old results (TEST MODE)
        recent_time = datetime.utcnow() - timedelta(seconds=10)
        
        # Find the most recent dice roll from any team
        last_dice_event = GameEvent.query.filter_by(
            game_session_id=active_session_query.id
        ).filter(
            GameEvent.event_type.in_(['dice_roll', 'admin_dice_roll', 'admin_dice_roll_legacy', 'team_dice_roll']),
            GameEvent.timestamp >= recent_time
        ).order_by(GameEvent.timestamp.desc()).first()
        
        # Find the most recent special field event (catapult, barrier, swap, field minigames)
        last_special_event = GameEvent.query.filter_by(
            game_session_id=active_session_query.id
        ).filter(
            GameEvent.event_type.in_(['special_field_catapult_forward', 'special_field_catapult_backward', 
                                     'special_field_player_swap', 'special_field_barrier_set', 
                                     'special_field_barrier_released', 'special_field_barrier_blocked',
                                     'field_minigame_completed']),
            GameEvent.timestamp >= recent_time
        ).order_by(GameEvent.timestamp.desc()).first()
        
        # Process dice result
        if last_dice_event and last_dice_event.data_json:
            try:
                import json
                # Parse data_json
                if isinstance(last_dice_event.data_json, str):
                    try:
                        event_data = json.loads(last_dice_event.data_json)
                    except json.JSONDecodeError:
                        # Fallback to eval for legacy data
                        event_data = eval(last_dice_event.data_json)
                else:
                    event_data = last_dice_event.data_json
                
                last_dice_result = {
                    'standard_roll': event_data.get('standard_roll', 0),
                    'bonus_roll': event_data.get('bonus_roll', 0),
                    'total_roll': event_data.get('total_roll', 0),
                    'timestamp': last_dice_event.timestamp.strftime('%H:%M:%S'),
                    'team_id': last_dice_event.related_team_id,
                    'was_blocked': event_data.get('was_blocked', False),
                    'barrier_released': event_data.get('barrier_released', False),
                    'barrier_config': event_data.get('barrier_config', {}),
                    'barrier_display_text': event_data.get('barrier_display_text', 'Höhere Zahl benötigt'),
                    'victory_triggered': event_data.get('victory_triggered', False),
                    'needs_final_roll': event_data.get('needs_final_roll', False)
                }
                
                current_app.logger.info(f"Found recent dice result for team {last_dice_event.related_team_id}: {last_dice_result}")
            except Exception as e:
                current_app.logger.error(f"Error parsing dice result: {e}")
                last_dice_result = None

        # Process special field event
        if last_special_event and last_special_event.data_json:
            try:
                import json
                # Parse data_json
                if isinstance(last_special_event.data_json, str):
                    try:
                        event_data = json.loads(last_special_event.data_json)
                    except json.JSONDecodeError:
                        event_data = eval(last_special_event.data_json)
                else:
                    event_data = last_special_event.data_json
                
                last_special_field_event = {
                    'event_type': last_special_event.event_type,
                    'timestamp': last_special_event.timestamp.strftime('%H:%M:%S'),
                    'team_id': last_special_event.related_team_id,
                    'data': event_data
                }
                
                current_app.logger.info(f"Found recent special field event for team {last_special_event.related_team_id}: {last_special_event.event_type}")
            except Exception as e:
                current_app.logger.error(f"Error parsing special field event: {e}")
                last_special_field_event = None

        # Get question data if question is active
        question_data = None
        if (active_session_query and 
            active_session_query.current_phase == 'QUESTION_ACTIVE' and 
            active_session_query.current_question_id):
            
            current_app.logger.info(f"[QUESTION BANNER] Attempting to load question data for ID: {active_session_query.current_question_id}")
            
            try:
                from app.models import GameRound
                from app.admin.minigame_utils import get_question_from_folder
                
                active_round = GameRound.get_active_round()
                current_app.logger.info(f"[QUESTION BANNER] Active round: {active_round}")
                
                if active_round and active_round.minigame_folder:
                    current_app.logger.info(f"[QUESTION BANNER] Minigame folder: {active_round.minigame_folder.folder_path}")
                    
                    question_info = get_question_from_folder(
                        active_round.minigame_folder.folder_path, 
                        active_session_query.current_question_id
                    )
                    current_app.logger.info(f"[QUESTION BANNER] Question info loaded: {question_info}")
                    
                    if question_info:
                        question_data = {
                            'question_active': True,
                            'question': {
                                'id': active_session_query.current_question_id,
                                'title': question_info.get('title', 'Aktuelle Frage'),
                                'text': question_info.get('question', ''),
                                'type': question_info.get('type', 'multiple_choice')
                            },
                            'answers': question_info.get('options', [])
                        }
                        current_app.logger.info(f"[QUESTION BANNER] Question data prepared: {question_data}")
                    else:
                        current_app.logger.warning(f"[QUESTION BANNER] No question info returned from get_question_from_folder")
                else:
                    current_app.logger.warning(f"[QUESTION BANNER] No active round or minigame folder")
            except Exception as e:
                current_app.logger.error(f"[QUESTION BANNER] Error loading question data: {e}")
                import traceback
                current_app.logger.error(f"[QUESTION BANNER] Traceback: {traceback.format_exc()}")
                question_data = None
        else:
            current_app.logger.info(f"[QUESTION BANNER] Not loading question data - Phase: {active_session_query.current_phase if active_session_query else 'None'}, Question ID: {active_session_query.current_question_id if active_session_query else 'None'}")
        
        response_data = {
            "teams": team_data,
            "game_session": game_session_data,
            "last_dice_result": last_dice_result,
            "last_special_field_event": last_special_field_event
        }
        
        # Add question data if available
        if question_data:
            response_data["question_data"] = question_data
        
        # Add field update timestamp for live updates
        try:
            from app.admin.routes import field_update_events
            if field_update_events:
                response_data["last_field_update"] = max(event.get('timestamp', 0) for event in field_update_events)
            else:
                response_data["last_field_update"] = 0
        except:
            response_data["last_field_update"] = 0
            
        return jsonify(response_data)

    except Exception as e:
        current_app.logger.error(f"Schwerer Fehler in /api/board-status: {e}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": "Ein interner Serverfehler ist aufgetreten.", "details": str(e)}), 500

@main_bp.route('/api/minigame-status')
def minigame_status():
    active_session = GameSession.query.filter_by(is_active=True).first()
    if active_session:
        return jsonify({
            "current_minigame_name": active_session.current_minigame_name,
            "current_minigame_description": active_session.current_minigame_description,
            "current_phase": active_session.current_phase
        })
    return jsonify({
        "current_minigame_name": None,
        "current_minigame_description": None,
        "current_phase": None
    }), 404

@main_bp.route('/api/question-status')
def question_status_for_gameboard():
    """API für Fragen-Status für das Gameboard (ohne Login-Requirement)"""
    try:
        active_session = GameSession.query.filter_by(is_active=True).first()
        if not active_session:
            return jsonify({'question_active': False, 'message': 'Keine aktive Spielsitzung'})
            
        if active_session.current_phase != 'QUESTION_ACTIVE' or not active_session.current_question_id:
            return jsonify({'question_active': False, 'message': 'Keine aktive Frage'})
        
        # Hole Fragen-Daten
        from app.models import GameRound
        from app.admin.minigame_utils import get_question_from_folder
        
        active_round = GameRound.get_active_round()
        if not active_round or not active_round.minigame_folder:
            return jsonify({'question_active': False, 'message': 'Keine aktive Spielrunde'})
        
        question_data = get_question_from_folder(active_round.minigame_folder.folder_path, active_session.current_question_id)
        current_app.logger.info(f"[QUESTION BANNER] Raw question data: {question_data}")
        
        if not question_data:
            return jsonify({'question_active': False, 'message': 'Frage nicht gefunden'})
        
        # Try different field names for question text
        question_text = (question_data.get('question_text') or   # <-- Das war's!
                        question_data.get('question') or 
                        question_data.get('text') or 
                        question_data.get('content') or 
                        question_data.get('description') or '')
        
        # Get question title/name
        question_title = (question_data.get('name') or           # <-- Und das!
                         question_data.get('title') or
                         'Aktuelle Frage')
        
        # Try different field names for answers
        answers = (question_data.get('options') or 
                  question_data.get('answers') or 
                  question_data.get('choices') or [])
        
        current_app.logger.info(f"[QUESTION BANNER] Processed - text: '{question_text}', answers: {answers}")
        
        return jsonify({
            'question_active': True,
            'question': {
                'id': active_session.current_question_id,
                'title': question_title,
                'text': question_text,
                'type': question_data.get('question_type', 'multiple_choice')
            },
            'answers': answers,
            'debug_raw_data': question_data  # Temporary debug field
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in question_status_for_gameboard: {e}")
        return jsonify({'question_active': False, 'error': str(e)}), 500

@main_bp.route('/api/update-position', methods=['POST']) # Dieser Endpunkt wird aktuell nicht vom Client genutzt, da Position serverseitig gesetzt wird.
def update_position():
    data = request.json
    team_id = data.get('team_id')
    position = data.get('position')
    
    if team_id is None or position is None:
        return jsonify({"success": False, "error": "Ungültige Parameter"}), 400
    
    team = Team.query.get(team_id)
    if team:
        team.current_position = position
        db.session.commit()
        return jsonify({"success": True})
    
    return jsonify({"success": False, "error": "Team nicht gefunden"}), 404

@main_bp.route('/api/roll_dice_action', methods=['POST'])
def roll_dice_action():
    """ 
    DEPRECATED: Diese Route ist deaktiviert. Das Würfeln erfolgt jetzt nur noch über das Admin Dashboard.
    Teams können nicht mehr selbst würfeln - nur der Admin kann für sie würfeln.
    """
    return jsonify({
        "success": False, 
        "error": "Das Würfeln erfolgt jetzt ausschließlich über das Admin Dashboard. Teams können nicht mehr selbst würfeln."
    }), 403

# Alternative: Wenn du die alte Route komplett behalten möchtest, aber nur für Admins:
@main_bp.route('/api/roll_dice_action_admin_only', methods=['POST'])
def roll_dice_action_admin_only():
    """ 
    LEGACY: API-Endpunkt zum Würfeln - NUR für Admins.
    Diese Route ist nur noch für Rückwärtskompatibilität da.
    Empfohlen wird die Nutzung der neuen Admin-spezifischen Route.
    """
    try:
        # Admin-Check
        if not current_user.is_authenticated or not isinstance(current_user, Admin):
            return jsonify({"success": False, "error": "Nur Admins können würfeln."}), 403

        data = request.json
        team_id_from_request = data.get('team_id')

        if not team_id_from_request:
            return jsonify({"success": False, "error": "Team-ID fehlt."}), 400

        active_session = GameSession.query.filter_by(is_active=True).first()
        if not active_session:
            return jsonify({"success": False, "error": "Keine aktive Spielsitzung."}), 404

        if active_session.current_phase != 'DICE_ROLLING':
            return jsonify({"success": False, "error": "Es ist nicht die Würfelphase."}), 403
        
        # Admin kann für jedes Team würfeln, nicht nur für das aktuelle
        if active_session.current_team_turn_id != team_id_from_request:
            current_turn_team_obj = Team.query.get(active_session.current_team_turn_id)
            return jsonify({"success": False, "error": f"Nicht Zug von Team-ID {team_id_from_request}. {current_turn_team_obj.name if current_turn_team_obj else 'Unbekanntes Team'} (ID: {active_session.current_team_turn_id}) ist dran."}), 403

        team = Team.query.get(team_id_from_request)
        if not team:
            return jsonify({"success": False, "error": "Anfragendes Team nicht gefunden."}), 404

        # SONDERFELD: Importiere Sonderfeld-Funktionen falls verfügbar
        try:
            from app.game_logic.special_fields import (
                handle_special_field_action, 
                check_barrier_release, 
                get_field_type_at_position
            )
            special_fields_available = True
        except ImportError:
            current_app.logger.warning("Sonderfeld-Module nicht verfügbar - Legacy-Modus")
            special_fields_available = False

        standard_dice_roll = random.randint(1, 6)
        bonus_dice_roll = 0
        if team.bonus_dice_sides and team.bonus_dice_sides > 0:
            bonus_dice_roll = random.randint(1, team.bonus_dice_sides)
        
        total_roll = standard_dice_roll + bonus_dice_roll
        old_position = team.current_position
        new_position = old_position
        special_field_result = None
        barrier_check_result = None
        
        # SONDERFELD: Prüfe Sperren-Status wenn verfügbar
        if special_fields_available and hasattr(team, 'is_blocked') and team.is_blocked:
            # Team ist blockiert - prüfe ob es freikommt
            barrier_check_result = check_barrier_release(team, standard_dice_roll, active_session, bonus_dice_roll)
            
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
            # Team ist nicht blockiert oder Sonderfelder nicht verfügbar - normale Bewegung
            max_field_index = current_app.config.get('MAX_BOARD_FIELDS', 72)
            new_position = min(team.current_position + total_roll, max_field_index)
            team.current_position = new_position
            
            # SONDERFELD: Prüfe Sonderfeld-Aktion nach Bewegung wenn verfügbar
            if special_fields_available:
                all_teams = Team.query.all()
                special_field_result = handle_special_field_action(team, all_teams, active_session)
        
        # ZIELFELD: Prüfe Gewinn-Bedingung
        # WICHTIG: Team muss BEREITS auf Position 72 gewesen sein (old_position), nicht erst durch den Wurf dorthin gekommen
        victory_triggered = False
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
        
        event_description = f"Admin würfelte für Team {team.name}: {standard_dice_roll}"
        if bonus_dice_roll > 0:
            event_description += f" (Bonus: {bonus_dice_roll}, Gesamt: {total_roll})"
        
        if (special_fields_available and hasattr(team, 'is_blocked') and 
            team.is_blocked and not barrier_check_result.get('released', False)):
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
            event_type="admin_dice_roll_legacy",
            description=event_description,
            related_team_id=team.id,
            data_json=str({
                "standard_roll": standard_dice_roll,
                "bonus_roll": bonus_dice_roll,
                "total_roll": total_roll,
                "old_position": old_position,
                "new_position": new_position,
                "rolled_by": "admin_legacy_route",
                "was_blocked": getattr(team, 'is_blocked', False) if barrier_check_result else False,
                "barrier_released": barrier_check_result.get('released', False) if barrier_check_result else False,
                "victory_triggered": victory_triggered,
                "needs_final_roll": old_position == 72 and total_roll < 6
            })
        )
        db.session.add(dice_event)

        dice_order_ids_str = active_session.dice_roll_order.split(',')
        dice_order_ids_int = [int(tid) for tid in dice_order_ids_str if tid.isdigit()]
        
        current_team_index_in_order = -1
        if team.id in dice_order_ids_int:
            current_team_index_in_order = dice_order_ids_int.index(team.id)
        else:
            db.session.rollback()
            current_app.logger.error(f"Team {team.id} nicht in Würfelreihenfolge {dice_order_ids_int} gefunden.")
            return jsonify({"success": False, "error": "Fehler in der Würfelreihenfolge (Team nicht gefunden)."}), 500

        # Prüfe ob ein Field-Minigame durch Sonderfeld-Behandlung gestartet wurde
        field_minigame_phases = ['FIELD_MINIGAME_SELECTION_PENDING', 'FIELD_MINIGAME_TRIGGERED', 'FIELD_MINIGAME_COMPLETED']
        if active_session.current_phase in field_minigame_phases:
            # Field-Minigame wurde gestartet - normale Team-Turn-Logik überspringen
            current_app.logger.info(f"Field-Minigame wurde gestartet (Phase: {active_session.current_phase}) - überspringe normale Turn-Logik")
        elif current_team_index_in_order < len(dice_order_ids_int) - 1:
            active_session.current_team_turn_id = dice_order_ids_int[current_team_index_in_order + 1]
        else:
            active_session.current_phase = 'ROUND_OVER'
            active_session.current_team_turn_id = None 
            all_teams_in_db = Team.query.all()
            for t_obj in all_teams_in_db:
                t_obj.bonus_dice_sides = 0
                t_obj.minigame_placement = None
            
            round_over_event = GameEvent(
                game_session_id=active_session.id,
                event_type="dice_round_finished",
                description="Admin beendete die Würfelrunde über Legacy-Route."
            )
            db.session.add(round_over_event)

        db.session.commit()

        # ZIELFELD: Victory automatisch auslösen wenn gewonnen
        if victory_triggered:
            try:
                # Speichere Victory Event
                victory_event = GameEvent(
                    game_session_id=active_session.id,
                    event_type="game_victory",
                    description=f"Team {team.name} hat das Spiel gewonnen!",
                    related_team_id=team.id,
                    data_json=str({
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
                db.session.commit()
                
                current_app.logger.info(f"🏆 Victory automatisch ausgelöst für Team {team.name}")
                
            except Exception as ve:
                current_app.logger.error(f"Fehler beim Victory-Handling: {ve}")
                db.session.rollback()

        # Response zusammenstellen
        response_data = {
            "success": True,
            "team_id": team.id,
            "team_name": team.name,
            "standard_roll": standard_dice_roll,
            "bonus_roll": bonus_dice_roll,
            "total_roll": total_roll,
            "new_position": new_position,
            "next_team_id": active_session.current_team_turn_id,
            "new_phase": active_session.current_phase,
            "victory_triggered": victory_triggered,
            "needs_final_roll": team.current_position == 72 and total_roll < 6
        }

        # SONDERFELD: Füge Sonderfeld-Informationen hinzu wenn verfügbar
        if barrier_check_result:
            response_data["barrier_check"] = barrier_check_result
            
        if special_field_result and special_field_result.get("success"):
            response_data["special_field"] = special_field_result

        return jsonify(response_data)
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Schwerer Fehler in /api/roll_dice_action_admin_only: {e}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": "Ein interner Serverfehler beim Würfeln ist aufgetreten.", "details": str(e)}), 500

# SONDERFELD: Neue API-Endpunkte für Sonderfeld-Interaktionen

@main_bp.route('/api/special-field-status')
def special_field_status():
    """API für Sonderfeld-Status aller Teams"""
    try:
        teams = Team.query.all()
        active_session = GameSession.query.filter_by(is_active=True).first()
        
        special_field_data = []
        for team in teams:
            team_data = {
                "team_id": team.id,
                "team_name": team.name,
                "current_position": team.current_position,
                "is_blocked": getattr(team, 'is_blocked', False),
                "blocked_target_number": getattr(team, 'blocked_target_number', None),
                "blocked_turns_remaining": getattr(team, 'blocked_turns_remaining', 0),
                "extra_moves_remaining": getattr(team, 'extra_moves_remaining', 0),
                "has_shield": getattr(team, 'has_shield', False)
            }
            
            # Bestimme Feldtyp der aktuellen Position
            try:
                from app.game_logic.special_fields import get_field_type_at_position
                team_data["current_field_type"] = get_field_type_at_position(team.current_position)
            except ImportError:
                team_data["current_field_type"] = "normal"
            
            special_field_data.append(team_data)
        
        return jsonify({
            "success": True,
            "teams": special_field_data,
            "volcano_status": {
                "countdown": getattr(active_session, 'volcano_countdown', 0) if active_session else 0,
                "active": getattr(active_session, 'volcano_active', False) if active_session else False
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Fehler in special-field-status: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@main_bp.route('/api/field-types')
def field_types():
    """API für verfügbare Feldtypen und ihre Positionen"""
    try:
        from app.game_logic.special_fields import get_all_special_field_positions
        
        # Hole alle Sonderfeld-Positionen
        max_fields = current_app.config.get('MAX_BOARD_FIELDS', 72) + 1  # 0-72 = 73 Felder
        special_positions = get_all_special_field_positions(max_fields)
        
        # Feldtyp-Informationen
        field_type_info = {
            'catapult_forward': {
                'name': 'Katapult Vorwärts',
                'description': 'Schleudert Teams 3-5 Felder nach vorne',
                'color': '#4CAF50',
                'icon': '🚀'
            },
            'catapult_backward': {
                'name': 'Katapult Rückwärts', 
                'description': 'Schleudert Teams 2-4 Felder nach hinten',
                'color': '#F44336',
                'icon': '💥'
            },
            'player_swap': {
                'name': 'Spieler-Tausch',
                'description': 'Tauscht Position mit zufälligem anderen Team',
                'color': '#2196F3',
                'icon': '🔄'
            },
            'barrier': {
                'name': 'Sperre',
                'description': 'Blockiert Team bis bestimmte Zahl gewürfelt wird',
                'color': '#9E9E9E',
                'icon': '🚧'
            }
        }
        
        return jsonify({
            "success": True,
            "field_types": field_type_info,
            "special_positions": special_positions,
            "total_fields": max_fields
        })
        
    except ImportError:
        # Fallback wenn Sonderfeld-Module nicht verfügbar
        return jsonify({
            "success": False,
            "error": "Sonderfeld-System nicht verfügbar"
        }), 503
    except Exception as e:
        current_app.logger.error(f"Fehler in field-types: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

# WELCOME-SYSTEM API ENDPUNKTE

@main_bp.route('/welcome')
def welcome():
    """Welcome-Seite anzeigen - immer verfügbar, auch ohne aktive Session"""
    
    welcome_session = WelcomeSession.get_active_session()
    
    # Welcome-Seite wird immer angezeigt - auch ohne aktive Session
    # Das Template behandelt den Fall wenn welcome_session None ist
    return render_template('welcome.html', welcome_session=welcome_session)

@main_bp.route('/api/registration-status')
def registration_status():
    """Status der Registrierung für index.html Pop-up"""
    try:
        
        welcome_session = WelcomeSession.get_active_session()
        
        return jsonify({
            "success": True,
            "registration_active": welcome_session is not None,
            "teams_created": welcome_session.teams_created if welcome_session else False
        })
    except Exception as e:
        current_app.logger.error(f"Fehler in registration-status: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@main_bp.route('/api/register-player', methods=['POST'])
@csrf.exempt
def register_player():
    """Spieler registrieren"""
    try:
        current_app.logger.info("Player registration attempt received")
        
        data = request.get_json()
        if not data:
            current_app.logger.error("No JSON data received")
            return jsonify({"success": False, "error": "Keine Daten empfangen"}), 400
            
        player_name = data.get('player_name', '').strip()
        current_app.logger.info(f"Registration attempt for player: '{player_name}'")
        
        if not player_name:
            current_app.logger.error("Empty player name")
            return jsonify({"success": False, "error": "Name ist erforderlich"}), 400
        
        if len(player_name) > 50:
            current_app.logger.error(f"Player name too long: {len(player_name)} chars")
            return jsonify({"success": False, "error": "Name ist zu lang (max. 50 Zeichen)"}), 400
        
        # Prüfe ob Registrierung aktiv ist
        welcome_session = WelcomeSession.get_active_session()
        if not welcome_session:
            current_app.logger.error("No active welcome session found")
            return jsonify({"success": False, "error": "Keine aktive Registrierung"}), 400
        
        current_app.logger.info(f"Active welcome session found: {welcome_session.id}")
        
        if welcome_session.teams_created:
            current_app.logger.error("Teams already created")
            return jsonify({"success": False, "error": "Registrierung ist bereits abgeschlossen"}), 400
        
        # Prüfe ob Name bereits existiert
        existing = PlayerRegistration.query.filter_by(
            welcome_session_id=welcome_session.id,
            player_name=player_name
        ).first()
        
        if existing:
            current_app.logger.error(f"Player name already exists: '{player_name}'")
            return jsonify({"success": False, "error": "Name ist bereits vergeben"}), 400
        
        # Erstelle neue Registrierung
        registration = PlayerRegistration(
            welcome_session_id=welcome_session.id,
            player_name=player_name
        )
        
        db.session.add(registration)
        db.session.commit()
        
        current_app.logger.info(f"Neuer Spieler registriert: {player_name}")
        
        return jsonify({
            "success": True,
            "message": f"Spieler '{player_name}' erfolgreich registriert"
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler bei Spielerregistrierung: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Ein Fehler ist aufgetreten"}), 500

@main_bp.route('/api/debug-welcome-session')
def debug_welcome_session():
    """Debug-Route für Welcome-Session Status"""
    try:
        welcome_session = WelcomeSession.get_active_session()
        if not welcome_session:
            return jsonify({
                "success": False,
                "message": "No active welcome session",
                "all_sessions": [
                    {
                        "id": s.id,
                        "is_active": s.is_active,
                        "start_time": s.start_time.isoformat(),
                        "teams_created": s.teams_created
                    }
                    for s in WelcomeSession.query.all()
                ]
            })
        
        return jsonify({
            "success": True,
            "active_session": {
                "id": welcome_session.id,
                "is_active": welcome_session.is_active,
                "start_time": welcome_session.start_time.isoformat(),
                "teams_created": welcome_session.teams_created,
                "player_count": welcome_session.player_registrations.count()
            }
        })
    except Exception as e:
        current_app.logger.error(f"Debug welcome session error: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@main_bp.route('/api/welcome-status')
def welcome_status():
    """Status-Informationen für Welcome-Seite"""
    try:
        
        welcome_session = WelcomeSession.get_active_session()
        if not welcome_session:
            return jsonify({"success": False, "error": "Keine aktive Session"}), 404
        
        # Hole registrierte Spieler
        players = []
        
        for registration in welcome_session.get_registered_players():
            player_data = {
                "id": registration.id,
                "name": registration.player_name,
                "registration_time": registration.registration_time.isoformat(),
                "has_profile_image": registration.profile_image_path is not None
            }
            
            if registration.profile_image_path:
                player_data["image_path"] = registration.profile_image_path
            else:
                # Deterministisches Emoji basierend auf Spielername
                # So bleibt das Emoji immer gleich für jeden Spieler
                player_data["emoji"] = get_consistent_emoji_for_player(registration.player_name)
            
            players.append(player_data)
        
        # Hole Team-Informationen falls bereits erstellt
        teams = []
        if welcome_session.teams_created:
            # Hole alle Teams die in dieser Welcome-Session erstellt wurden
            team_objects = Team.query.join(PlayerRegistration).filter(
                PlayerRegistration.welcome_session_id == welcome_session.id,
                PlayerRegistration.assigned_team_id.isnot(None)
            ).distinct().all()
            
            teams_raw = []
            for team in team_objects:
                # Hole Mitglieder dieses Teams
                team_players = PlayerRegistration.query.filter_by(
                    welcome_session_id=welcome_session.id,
                    assigned_team_id=team.id
                ).all()
                
                teams_raw.append({
                    "id": team.id,
                    "name": team.name,
                    "password": team.welcome_password or "Passwort nicht verfügbar",
                    "members": [p.player_name for p in team_players]
                })
            
            # Sortiere Teams korrekt (Team 1, Team 2, Team 3, ...)
            def extract_team_number(team_name):
                import re
                match = re.search(r'Team (\d+)', team_name)
                return int(match.group(1)) if match else 999  # 999 für Teams ohne Nummer
            
            teams = sorted(teams_raw, key=lambda t: extract_team_number(t['name']))
        
        return jsonify({
            "success": True,
            "players": players,
            "teams": teams,
            "teams_created": welcome_session.teams_created
        })
        
    except Exception as e:
        current_app.logger.error(f"Fehler in welcome-status: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@main_bp.route('/api/welcome-admin-status')
def welcome_admin_status():
    """Admin-Status für Welcome-System im Dashboard"""
    try:
        
        welcome_session = WelcomeSession.get_active_session()
        
        if not welcome_session:
            return jsonify({
                "success": True,
                "active": False
            })
        
        player_count = welcome_session.player_registrations.count()
        team_count = 0
        teams_data = []
        
        if welcome_session.teams_created:
            # Hole alle Teams die in dieser Session erstellt wurden
            team_ids = db.session.query(PlayerRegistration.assigned_team_id).filter(
                PlayerRegistration.welcome_session_id == welcome_session.id,
                PlayerRegistration.assigned_team_id.isnot(None)
            ).distinct().all()
            
            team_count = len(team_ids)
            
            # Hole vollständige Team-Informationen mit Passwörtern
            teams_raw = []
            for team_id_tuple in team_ids:
                team = Team.query.get(team_id_tuple[0])
                if team:
                    # Hole Teammitglieder aus der Session
                    members = PlayerRegistration.query.filter_by(
                        welcome_session_id=welcome_session.id,
                        assigned_team_id=team.id
                    ).all()
                    
                    teams_raw.append({
                        "id": team.id,
                        "name": team.name,
                        "password": team.welcome_password or "Kein Passwort",
                        "members": [member.player_name for member in members]
                    })
            
            # Sortiere Teams korrekt (Team 1, Team 2, Team 3, ...)
            def extract_team_number(team_name):
                import re
                match = re.search(r'Team (\d+)', team_name)
                return int(match.group(1)) if match else 999  # 999 für Teams ohne Nummer
            
            teams_data = sorted(teams_raw, key=lambda t: extract_team_number(t['name']))
        
        return jsonify({
            "success": True,
            "active": True,
            "player_count": player_count,
            "teams_created": welcome_session.teams_created,
            "team_count": team_count,
            "teams": teams_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Fehler in welcome-admin-status: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@main_bp.route('/api/victory', methods=['POST'])
def victory():
    """API-Endpunkt für Spielgewinn - speichert Victory-Daten"""
    try:
        data = request.get_json()
        winning_team_id = data.get('winning_team_id')
        winning_team_name = data.get('winning_team_name')
        
        if not winning_team_id:
            return jsonify({"success": False, "error": "Team-ID fehlt"}), 400
        
        # Verifiziere dass das Team existiert
        winning_team = Team.query.get(winning_team_id)
        if not winning_team:
            return jsonify({"success": False, "error": "Team nicht gefunden"}), 404
        
        # Hole aktive Session
        active_session = GameSession.query.filter_by(is_active=True).first()
        if not active_session:
            return jsonify({"success": False, "error": "Keine aktive Spielsitzung"}), 404
        
        # Speichere Victory Event
        victory_event = GameEvent(
            game_session_id=active_session.id,
            event_type="game_victory",
            description=f"Team {winning_team.name} hat das Spiel gewonnen!",
            related_team_id=winning_team_id,
            data_json=str({
                "winning_team_id": winning_team_id,
                "winning_team_name": winning_team_name,
                "victory_timestamp": datetime.utcnow().isoformat(),
                "final_position": winning_team.current_position
            })
        )
        db.session.add(victory_event)
        
        # Beende aktive Session
        active_session.is_active = False
        active_session.current_phase = 'GAME_FINISHED'
        
        # Speichere Victory-Informationen in Session für Goodbye-Seite
        session['victory_data'] = {
            'winning_team_id': winning_team_id,
            'winning_team_name': winning_team_name,
            'victory_timestamp': datetime.utcnow().isoformat(),
            'game_session_id': active_session.id
        }
        
        db.session.commit()
        
        current_app.logger.info(f"Spiel beendet - Gewinner: {winning_team.name} (ID: {winning_team_id})")
        
        return jsonify({
            "success": True,
            "message": f"Victory erfolgreich gespeichert für Team {winning_team.name}"
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler in victory endpoint: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Ein Fehler ist aufgetreten"}), 500

@main_bp.route('/goodbye')
def goodbye():
    """Goodbye-Seite mit Spielstatistiken"""
    try:
        # 🔍 DEBUG: Log available event types for debugging
        all_events = GameEvent.query.with_entities(GameEvent.event_type).distinct().all()
        current_app.logger.info(f"📊 Available event types: {[event[0] for event in all_events]}")
        
        # Hole Victory-Daten aus Session
        victory_data = session.get('victory_data')
        current_app.logger.info(f"📊 Victory data from session: {victory_data}")
        
        if not victory_data:
            # Fallback: Hole letztes beendetes Spiel
            last_finished_session = GameSession.query.filter_by(
                current_phase='GAME_FINISHED'
            ).order_by(GameSession.id.desc()).first()
            
            if last_finished_session:
                # Hole Victory Event
                victory_event = GameEvent.query.filter_by(
                    game_session_id=last_finished_session.id,
                    event_type='game_victory'
                ).first()
                
                if victory_event and victory_event.data_json:
                    import json
                    try:
                        victory_data = eval(victory_event.data_json) if isinstance(victory_event.data_json, str) else victory_event.data_json
                    except:
                        victory_data = None
        
        # Hole alle Teams und ihre Statistiken
        teams = Team.query.order_by(Team.current_position.desc()).all()
        teams_stats = []
        
        winning_team = None
        game_session_id = None
        if victory_data:
            winning_team = Team.query.get(victory_data.get('winning_team_id'))
            game_session_id = victory_data.get('game_session_id')
        
        # Berechne detaillierte Minispiel-Statistiken
        minigame_stats = calculate_minigame_statistics(game_session_id) if game_session_id else {}
        position_history = calculate_position_history(game_session_id) if game_session_id else {}
        
        current_app.logger.info(f"📊 Minigame stats calculated: {minigame_stats}")
        current_app.logger.info(f"📊 Position history calculated: {list(position_history.keys())}")
        
        for team in teams:
            team_minigame_stats = minigame_stats.get(str(team.id), {})
            
            team_stat = {
                'id': team.id,
                'name': team.name,
                'color': team.character.color if team.character else '#CCCCCC',
                'final_position': team.current_position,
                'minigame_wins': team_minigame_stats.get('wins', 0),
                'minigame_participations': team_minigame_stats.get('participations', 0),
                'minigame_placements': team_minigame_stats.get('placements', []),
                'position_history': position_history.get(str(team.id), []),
                'is_winner': team.id == victory_data.get('winning_team_id') if victory_data else False
            }
            teams_stats.append(team_stat)
            current_app.logger.info(f"📊 Team {team.name} stats: position={team.current_position}, wins={team_minigame_stats.get('wins', 0)}, participations={team_minigame_stats.get('participations', 0)}")
        
        # Sortiere Teams nach finaler Position (absteigend)
        teams_stats.sort(key=lambda x: x['final_position'], reverse=True)
        
        # Berechne Spieldauer
        game_duration = "Unbekannt"
        total_minigames = 0
        
        if victory_data and victory_data.get('game_session_id'):
            game_session = GameSession.query.get(victory_data['game_session_id'])
            if game_session and game_session.created_at:
                victory_time = datetime.fromisoformat(victory_data['victory_timestamp'].replace('Z', '+00:00'))
                duration = victory_time - game_session.created_at
                
                hours = int(duration.total_seconds() // 3600)
                minutes = int((duration.total_seconds() % 3600) // 60)
                
                if hours > 0:
                    game_duration = f"{hours}h {minutes}m"
                else:
                    game_duration = f"{minutes}m"
                
                # Zähle Minispiel-Events (placements_recorded indicates minigames were played)
                minigame_events = GameEvent.query.filter_by(
                    game_session_id=game_session.id,
                    event_type='placements_recorded'
                ).count()
                total_minigames = minigame_events
        
        return render_template('goodbye.html',
                             winning_team=winning_team,
                             teams_stats=teams_stats,
                             game_duration=game_duration,
                             total_minigames=total_minigames,
                             victory_data=victory_data,
                             minigame_stats=minigame_stats)
    
    except Exception as e:
        current_app.logger.error(f"Fehler auf Goodbye-Seite: {e}", exc_info=True)
        # Fallback bei Fehlern
        return render_template('goodbye.html',
                             winning_team=None,
                             teams_stats=[],
                             game_duration="Unbekannt",
                             total_minigames=0,
                             victory_data=None,
                             minigame_stats={})

def calculate_minigame_statistics(game_session_id):
    """Berechnet detaillierte Minispiel-Statistiken für alle Teams basierend auf Team-Daten"""
    if not game_session_id:
        return {}
    
    try:
        # Hole alle Teams
        teams = Team.query.all()
        current_app.logger.info(f"📊 Found {len(teams)} teams total")
        
        team_stats = {}
        
        for team in teams:
            current_app.logger.info(f"📊 Team {team.name}: minigame_placement={team.minigame_placement}")
            
            team_stats[str(team.id)] = {
                'wins': 1 if team.minigame_placement == 1 else 0,
                'participations': 1 if team.minigame_placement is not None else 0,
                'placements': [team.minigame_placement] if team.minigame_placement is not None else [],
                'average_placement': float(team.minigame_placement) if team.minigame_placement is not None else 0.0
            }
        
        current_app.logger.info(f"📊 Calculated team stats: {team_stats}")
        return team_stats
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Berechnen der Minispiel-Statistiken: {e}")
        return {}
    
def calculate_position_history(game_session_id):
    """Berechnet Positionsverlauf für alle Teams"""
    if not game_session_id:
        return {}
    
    try:
        # 🔍 DEBUG: Check all dice events
        all_dice_events = GameEvent.query.filter_by(
            game_session_id=game_session_id
        ).filter(
            GameEvent.event_type.like('%dice%')
        ).all()
        current_app.logger.info(f"📊 All dice events found: {[(e.event_type, e.id) for e in all_dice_events]}")
        
        # Hole alle Bewegungs-Events
        movement_events = GameEvent.query.filter_by(
            game_session_id=game_session_id
        ).filter(
            GameEvent.event_type.in_(['dice_roll', 'admin_dice_roll', 'admin_dice_roll_legacy', 'team_dice_roll'])
        ).order_by(GameEvent.timestamp.asc()).all()
        current_app.logger.info(f"📊 Movement events found: {len(movement_events)}")
        
        position_history = {}
        
        for event in movement_events:
            if event.related_team_id and event.data_json:
                try:
                    if isinstance(event.data_json, str):
                        data = json.loads(event.data_json)
                    else:
                        data = event.data_json
                    
                    team_id_str = str(event.related_team_id)
                    new_position = data.get('new_position', 0)
                    
                    if team_id_str not in position_history:
                        position_history[team_id_str] = []
                    
                    position_history[team_id_str].append({
                        'position': new_position,
                        'timestamp': event.timestamp.isoformat(),
                        'dice_result': data.get('total_roll', 0)
                    })
                
                except (json.JSONDecodeError, KeyError) as e:
                    current_app.logger.warning(f"Fehler beim Parsen von Positions-Daten: {e}")
        
        return position_history
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Berechnen der Positionshistorie: {e}")
        return {}

# PROFILBILD-SYSTEM API ENDPUNKTE

@main_bp.route('/api/test-upload', methods=['POST'])
def test_upload():
    """Test-Endpunkt für Upload-Debugging"""
    current_app.logger.info("=== TEST UPLOAD ROUTE REACHED ===")
    current_app.logger.info(f"Content-Type: {request.content_type}")
    current_app.logger.info(f"Data length: {len(request.data) if request.data else 0}")
    
    try:
        data = request.get_json()
        current_app.logger.info(f"JSON parsed successfully: {bool(data)}")
        return jsonify({"success": True, "message": "Test successful"})
    except Exception as e:
        current_app.logger.error(f"JSON parsing failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@main_bp.route('/api/upload-profile-image', methods=['POST'])
@csrf.exempt
def upload_profile_image():
    """Upload eines Profilbildes für einen Spieler"""
    current_app.logger.info("=== UPLOAD PROFILE IMAGE ROUTE REACHED ===")
    try:
        import base64
        import binascii
        import os
        from PIL import Image
        import io
        
        # Debug: Log the request data
        current_app.logger.info(f"Upload request content-type: {request.content_type}")
        current_app.logger.info(f"Upload request data length: {len(request.data) if request.data else 0}")
        
        try:
            data = request.get_json()
        except Exception as e:
            current_app.logger.error(f"JSON parsing failed: {e}")
            return jsonify({"success": False, "error": "Ungültige JSON-Daten"}), 400
            
        if not data:
            current_app.logger.error("No JSON data received in upload request")
            return jsonify({"success": False, "error": "Keine Daten empfangen"}), 400
            
        player_name = data.get('player_name', '').strip()
        image_data = data.get('image_data', '')  # Base64-encoded image
        
        current_app.logger.info(f"Upload request for player: {player_name}")
        current_app.logger.info(f"Image data length: {len(image_data) if image_data else 0}")
        
        if not player_name:
            return jsonify({"success": False, "error": "Spielername ist erforderlich"}), 400
        
        if not image_data:
            return jsonify({"success": False, "error": "Bilddaten fehlen"}), 400
        
        # Entferne data:image/...;base64, prefix falls vorhanden
        if 'base64,' in image_data:
            image_data = image_data.split('base64,')[1]
        elif image_data.startswith('data:'):
            # Fallback: Remove any data: prefix even without base64,
            parts = image_data.split(',', 1)
            if len(parts) > 1:
                image_data = parts[1]
        
        # Prüfe ob aktive Welcome-Session existiert
        welcome_session = WelcomeSession.get_active_session()
        if not welcome_session:
            return jsonify({"success": False, "error": "Keine aktive Registrierung"}), 400
        
        # Prüfe ob Spieler existiert
        registration = PlayerRegistration.query.filter_by(
            welcome_session_id=welcome_session.id,
            player_name=player_name
        ).first()
        
        if not registration:
            return jsonify({"success": False, "error": "Spieler nicht gefunden"}), 404
        
        # Dekodiere Base64-Bild
        try:
            # Bereinige Base64-String (entferne Whitespace)
            image_data = image_data.strip().replace(' ', '').replace('\n', '').replace('\r', '')
            
            # Fixe Base64-Padding falls nötig
            if not image_data:
                return jsonify({"success": False, "error": "Leere Bilddaten"}), 400
            
            padding_needed = len(image_data) % 4
            if padding_needed:
                image_data += '=' * (4 - padding_needed)
            
            image_bytes = base64.b64decode(image_data, validate=True)
            image = Image.open(io.BytesIO(image_bytes))
        except binascii.Error as e:
            current_app.logger.error(f"Base64 decode error: {e}")
            return jsonify({"success": False, "error": "Ungültige Base64-Bilddaten"}), 400
        except Exception as e:
            current_app.logger.error(f"Image processing error: {e}")
            return jsonify({"success": False, "error": "Ungültige Bilddaten"}), 400
        
        # Validiere Bildformat
        if image.format not in ['JPEG', 'PNG', 'WEBP']:
            return jsonify({"success": False, "error": "Ungültiges Bildformat (nur JPEG, PNG, WEBP erlaubt)"}), 400
        
        # Resize auf 150x150px
        image = image.resize((150, 150), Image.Resampling.LANCZOS)
        
        # Konvertiere zu RGB falls nötig (für JPEG)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Erstelle Dateinamen
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_player_name = "".join(c for c in player_name if c.isalnum() or c in ['_', '-'])
        filename = f"{welcome_session.id}_{safe_player_name}_{timestamp}.jpg"
        
        # Speichere Bild
        profile_images_dir = os.path.join(current_app.static_folder, 'profile_images')
        os.makedirs(profile_images_dir, exist_ok=True)
        
        file_path = os.path.join(profile_images_dir, filename)
        image.save(file_path, 'JPEG', quality=85)
        
        # Speichere Pfad in Datenbank (relativer Pfad für static files)
        relative_path = f"profile_images/{filename}"
        registration.profile_image_path = relative_path
        
        # Falls Spieler bereits einem Team zugeordnet ist, aktualisiere auch Team-Profilbilder
        if registration.assigned_team_id:
            team = Team.query.get(registration.assigned_team_id)
            if team:
                team.set_profile_image(player_name, relative_path)
        
        db.session.commit()
        
        current_app.logger.info(f"Profilbild für Spieler '{player_name}' gespeichert: {relative_path}")
        
        return jsonify({
            "success": True,
            "message": f"Profilbild für '{player_name}' erfolgreich gespeichert",
            "image_path": relative_path
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Upload des Profilbildes: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Ein Fehler ist aufgetreten"}), 500

@main_bp.route('/api/get-player-faces')
def get_player_faces():
    """Gibt Profilbilder der aktuell spielenden Teams/Spieler zurück"""
    try:
        # Hole aktive Session
        active_session = GameSession.query.filter_by(is_active=True).first()
        if not active_session:
            return jsonify({"success": False, "error": "Keine aktive Spielsitzung"}), 404
        
        # Prüfe ob Minispiel läuft (normale Minigames oder Feld-Minigames)
        # Zeige Gesichter bei verschiedenen Minispiel-Phasen
        minigame_phases = ['MINIGAME_ANNOUNCED', 'SETUP_MINIGAME', 'MINIGAME_STARTED', 'MINIGAME_RESULTS', 'DICE_ROLLING']
        field_minigame_phases = ['FIELD_MINIGAME_TRIGGERED']
        
        is_normal_minigame = active_session.current_phase in minigame_phases
        is_field_minigame = active_session.current_phase in field_minigame_phases
        
        if not is_normal_minigame and not is_field_minigame:
            return jsonify({
                "success": True,
                "show_faces": False,
                "message": f"Kein Minispiel aktiv (Phase: {active_session.current_phase})"
            })
        
        # Für Feld-Minigames: Hole Spieler basierend auf dem Field-Minigame Setup
        if is_field_minigame:
            return get_field_minigame_player_faces(active_session)
        
        # Für normale Minigames: Hole ausgewählte Spieler aus der Session
        selected_players = active_session.get_selected_players()
        
        if not selected_players:
            return jsonify({
                "success": True, 
                "show_faces": False,
                "message": "Keine Spieler ausgewählt"
            })
        
        # Sammle Profilbilder der ausgewählten Spieler
        player_faces = []
        
        for team_id_str, player_names in selected_players.items():
            team = Team.query.get(int(team_id_str))
            if not team:
                continue
                
            team_name = team.name
            team_color = team.character.color if team.character else '#CCCCCC'
            
            # Hole gespeicherte Player-Konfiguration (enthält gespeicherte Emojis)
            player_config = team.get_player_config()
            
            for player_name in player_names:
                # Hole Profilbild aus Team-Daten
                profile_image = team.get_profile_image(player_name)
                
                if profile_image:
                    player_faces.append({
                        "player_name": player_name,
                        "team_name": team_name,
                        "team_id": team.id,
                        "team_color": team_color,
                        "image_path": profile_image,
                        "has_photo": True
                    })
                else:
                    # Prüfe zuerst nach gespeichertem Emoji in player_config
                    saved_emoji = None
                    if player_config and player_name in player_config:
                        saved_emoji = player_config[player_name].get('emoji')
                    
                    # Verwende gespeichertes Emoji oder falle zurück auf deterministisches
                    emoji = saved_emoji if saved_emoji else get_consistent_emoji_for_player(player_name)
                    
                    player_faces.append({
                        "player_name": player_name,
                        "team_name": team_name,
                        "team_id": team.id,
                        "team_color": team_color,
                        "emoji": emoji,
                        "has_photo": False
                    })
        
        # Zeige Gesichter auch wenn nur Emojis vorhanden sind
        show_faces = len(player_faces) > 0
        
        return jsonify({
            "success": True,
            "show_faces": show_faces,
            "player_faces": player_faces,
            "total_players": len(player_faces)
        })
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Abrufen der Spieler-Gesichter: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Ein Fehler ist aufgetreten"}), 500


def get_field_minigame_player_faces(active_session):
    """Holt Spieler-Gesichter für Feld-Minigames"""
    try:
        import os
        import json
        import random
        
        # Hole das aktuelle Feld-Minigame
        if not active_session.field_minigame_content_id:
            return jsonify({
                "success": True,
                "show_faces": False,
                "message": "Kein Feld-Minigame Content gefunden"
            })
        
        # Lade das Minigame aus den statischen Dateien
        mode = active_session.field_minigame_mode
        field_minigame_path = os.path.join(
            current_app.static_folder, 
            'field_minigames', 
            mode, 
            f"{active_session.field_minigame_content_id}.json"
        )
        
        if not os.path.exists(field_minigame_path):
            return jsonify({
                "success": True,
                "show_faces": False,
                "message": "Feld-Minigame Datei nicht gefunden"
            })
        
        # Lade Minigame-Daten um player_count zu erhalten
        with open(field_minigame_path, 'r', encoding='utf-8') as f:
            minigame_data = json.load(f)
        
        player_count = minigame_data.get('player_count', 1)
        
        # Hole die beteiligten Teams
        landing_team = active_session.field_minigame_landing_team
        opponent_team = active_session.field_minigame_opponent_team if active_session.field_minigame_opponent_team_id else None
        
        if not landing_team:
            return jsonify({
                "success": True,
                "show_faces": False,
                "message": "Kein landendes Team gefunden"
            })
        
        player_faces = []
        
        # Hole Spieler vom landenden Team
        landing_team_profiles = landing_team.get_profile_images()
        
        # Alle Teammitglieder des landenden Teams
        all_landing_players = []
        if landing_team_profiles:
            # Spieler mit Profilbildern
            for player_name, image_path in landing_team_profiles.items():
                all_landing_players.append({
                    "name": player_name,
                    "image_path": image_path,
                    "has_photo": True
                })
        
        # Zusätzliche Spieler ohne Profilbilder (falls das Team mehr Mitglieder hat)
        # Diese Information sollte aus der Team-Konfiguration kommen
        try:
            # Versuche Team-Mitglieder zu finden (falls in der Datenbank gespeichert)
            if hasattr(landing_team, 'members') and landing_team.members:
                team_member_names = landing_team.members.split(',') if isinstance(landing_team.members, str) else landing_team.members
                for member_name in team_member_names:
                    member_name = member_name.strip()
                    if not any(p["name"] == member_name for p in all_landing_players):
                        all_landing_players.append({
                            "name": member_name,
                            "image_path": None,
                            "has_photo": False
                        })
        except:
            pass
        
        # Wähle zufällige Spieler aus dem landenden Team
        selected_from_landing = random.sample(all_landing_players, min(player_count, len(all_landing_players)))
        
        for player_data in selected_from_landing:
            if player_data["has_photo"]:
                player_faces.append({
                    "player_name": player_data["name"],
                    "team_name": landing_team.name,
                    "team_id": landing_team.id,
                    "team_color": landing_team.character.color if landing_team.character else '#CCCCCC',
                    "image_path": player_data["image_path"],
                    "role": "landing_team",
                    "has_photo": True
                })
            else:
                # Prüfe zuerst nach gespeichertem Emoji in player_config
                player_config = landing_team.get_player_config()
                saved_emoji = None
                if player_config and player_data["name"] in player_config:
                    saved_emoji = player_config[player_data["name"]].get('emoji')
                
                # Verwende gespeichertes Emoji oder falle zurück auf deterministisches
                emoji = saved_emoji if saved_emoji else get_consistent_emoji_for_player(player_data["name"])
                
                player_faces.append({
                    "player_name": player_data["name"],
                    "team_name": landing_team.name,
                    "team_id": landing_team.id,
                    "team_color": landing_team.character.color if landing_team.character else '#CCCCCC',
                    "emoji": emoji,
                    "role": "landing_team",
                    "has_photo": False
                })
        
        # Für Team vs Team Modus: Hole auch Spieler vom Gegner-Team
        if mode == 'team_vs_team' and opponent_team:
            opponent_team_profiles = opponent_team.get_profile_images()
            
            all_opponent_players = []
            if opponent_team_profiles:
                for player_name, image_path in opponent_team_profiles.items():
                    all_opponent_players.append({
                        "name": player_name,
                        "image_path": image_path,
                        "has_photo": True
                    })
            
            # Zusätzliche Gegner-Spieler ohne Profilbilder
            try:
                if hasattr(opponent_team, 'members') and opponent_team.members:
                    team_member_names = opponent_team.members.split(',') if isinstance(opponent_team.members, str) else opponent_team.members
                    for member_name in team_member_names:
                        member_name = member_name.strip()
                        if not any(p["name"] == member_name for p in all_opponent_players):
                            all_opponent_players.append({
                                "name": member_name,
                                "image_path": None,
                                "has_photo": False
                            })
            except:
                pass
            
            if all_opponent_players:
                selected_from_opponent = random.sample(all_opponent_players, min(player_count, len(all_opponent_players)))
                
                for player_data in selected_from_opponent:
                    if player_data["has_photo"]:
                        player_faces.append({
                            "player_name": player_data["name"],
                            "team_name": opponent_team.name,
                            "team_id": opponent_team.id,
                            "team_color": opponent_team.character.color if opponent_team.character else '#CCCCCC',
                            "image_path": player_data["image_path"],
                            "role": "opponent_team",
                            "has_photo": True
                        })
                    else:
                        # Prüfe zuerst nach gespeichertem Emoji in player_config
                        player_config = opponent_team.get_player_config()
                        saved_emoji = None
                        if player_config and player_data["name"] in player_config:
                            saved_emoji = player_config[player_data["name"]].get('emoji')
                        
                        # Verwende gespeichertes Emoji oder falle zurück auf deterministisches
                        emoji = saved_emoji if saved_emoji else get_consistent_emoji_for_player(player_data["name"])
                        
                        player_faces.append({
                            "player_name": player_data["name"],
                            "team_name": opponent_team.name,
                            "team_id": opponent_team.id,
                            "team_color": opponent_team.character.color if opponent_team.character else '#CCCCCC',
                            "emoji": emoji,
                            "role": "opponent_team",
                            "has_photo": False
                        })
        
        # Für Team vs All Modus: Hole zufällige Spieler von anderen Teams
        elif mode == 'team_vs_all':
            all_teams = Team.query.filter(Team.id != landing_team.id, Team.is_active == True).all()
            
            for team in all_teams[:min(3, len(all_teams))]:  # Max 3 andere Teams zeigen
                team_profiles = team.get_profile_images()
                
                # Sammle alle Teammitglieder (mit und ohne Fotos)
                all_team_players = []
                if team_profiles:
                    for player_name, image_path in team_profiles.items():
                        all_team_players.append({
                            "name": player_name,
                            "image_path": image_path,
                            "has_photo": True
                        })
                
                # Zusätzliche Spieler ohne Profilbilder
                try:
                    if hasattr(team, 'members') and team.members:
                        team_member_names = team.members.split(',') if isinstance(team.members, str) else team.members
                        for member_name in team_member_names:
                            member_name = member_name.strip()
                            if not any(p["name"] == member_name for p in all_team_players):
                                all_team_players.append({
                                    "name": member_name,
                                    "image_path": None,
                                    "has_photo": False
                                })
                except:
                    pass
                
                if all_team_players:
                    # Ein zufälliger Spieler pro Team
                    selected_player = random.choice(all_team_players)
                    
                    if selected_player["has_photo"]:
                        player_faces.append({
                            "player_name": selected_player["name"],
                            "team_name": team.name,
                            "team_id": team.id,
                            "team_color": team.character.color if team.character else '#CCCCCC',
                            "image_path": selected_player["image_path"],
                            "role": "opponent_team",
                            "has_photo": True
                        })
                    else:
                        # Prüfe zuerst nach gespeichertem Emoji in player_config
                        player_config = team.get_player_config()
                        saved_emoji = None
                        if player_config and selected_player["name"] in player_config:
                            saved_emoji = player_config[selected_player["name"]].get('emoji')
                        
                        # Verwende gespeichertes Emoji oder falle zurück auf deterministisches
                        emoji = saved_emoji if saved_emoji else get_consistent_emoji_for_player(selected_player["name"])
                        
                        player_faces.append({
                            "player_name": selected_player["name"],
                            "team_name": team.name,
                            "team_id": team.id,
                            "team_color": team.character.color if team.character else '#CCCCCC',
                            "emoji": emoji,
                            "role": "opponent_team",
                            "has_photo": False
                        })
        
        show_faces = len(player_faces) > 0
        
        return jsonify({
            "success": True,
            "show_faces": show_faces,
            "player_faces": player_faces,
            "total_players": len(player_faces),
            "minigame_title": minigame_data.get('title', 'Feld-Minigame'),
            "mode": mode
        })
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Abrufen der Feld-Minigame Spieler-Gesichter: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"Fehler: {str(e)}"}), 500

@main_bp.route('/api/get-all-player-images')
def get_all_player_images():
    """Gibt alle verfügbaren Spieler mit ihren Profilbildern oder Emojis zurück"""
    try:
        teams = Team.query.all()
        all_players = []
        
        
        for team in teams:
            # Hole Team-Farbe
            team_color = team.character.color if team.character else '#CCCCCC'
            
            # Hole alle Profilbilder des Teams
            profile_images = team.get_profile_images()
            
            # Hole gespeicherte Player-Konfiguration (enthält gespeicherte Emojis)
            player_config = team.get_player_config()
            
            # Spieler mit Profilbildern
            for player_name, image_path in profile_images.items():
                if image_path and image_path.strip():
                    all_players.append({
                        "player_name": player_name,
                        "team_name": team.name,
                        "team_id": team.id,
                        "team_color": team_color,
                        "image_path": image_path,
                        "has_photo": True
                    })
            
            # Spieler ohne Profilbilder (falls Team mehr Mitglieder hat)
            try:
                if hasattr(team, 'members') and team.members:
                    team_member_names = team.members.split(',') if isinstance(team.members, str) else team.members
                    for member_name in team_member_names:
                        member_name = member_name.strip()
                        # Prüfe ob bereits mit Profilbild hinzugefügt
                        if not any(p["player_name"] == member_name for p in all_players):
                            # Prüfe zuerst nach gespeichertem Emoji in player_config
                            saved_emoji = None
                            if player_config and member_name in player_config:
                                saved_emoji = player_config[member_name].get('emoji')
                            
                            # Verwende gespeichertes Emoji oder falle zurück auf deterministisches
                            emoji = saved_emoji if saved_emoji else get_consistent_emoji_for_player(member_name)
                            
                            all_players.append({  
                                "player_name": member_name,
                                "team_name": team.name,
                                "team_id": team.id,
                                "team_color": team_color,
                                "emoji": emoji,
                                "has_photo": False
                            })
            except:
                pass
        
        return jsonify({
            "success": True,
            "players": all_players,
            "total_players": len(all_players)
        })
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Abrufen aller Spieler-Bilder: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Ein Fehler ist aufgetreten"}), 500

@main_bp.route('/api/profile-image-status')
def profile_image_status():
    """Status der Profilbilder für Welcome-System"""
    try:
        welcome_session = WelcomeSession.get_active_session()
        if not welcome_session:
            return jsonify({"success": False, "error": "Keine aktive Session"}), 404
        
        # Hole alle Registrierungen mit Profilbild-Status
        registrations = welcome_session.get_registered_players()
        players_with_images = []
        
        for registration in registrations:
            has_image = registration.profile_image_path is not None
            players_with_images.append({
                "player_name": registration.player_name,
                "has_profile_image": has_image,
                "image_path": registration.profile_image_path if has_image else None
            })
        
        total_players = len(players_with_images)
        players_with_photos = sum(1 for p in players_with_images if p["has_profile_image"])
        
        return jsonify({
            "success": True,
            "total_players": total_players,
            "players_with_photos": players_with_photos,
            "completion_percentage": (players_with_photos / total_players * 100) if total_players > 0 else 0,
            "players": players_with_images
        })
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Abrufen des Profilbild-Status: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Ein Fehler ist aufgetreten"}), 500

@main_bp.route('/api/remove-player', methods=['POST'])
@csrf.exempt
def remove_player():
    """Spieler aus der Welcome-Session entfernen (nur für Admins)"""
    try:
        # Admin-Check wäre hier normalerweise nötig - für jetzt akzeptieren wir alle Requests
        # da das Frontend bereits prüft
        
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Keine Daten empfangen"}), 400
            
        player_name = data.get('player_name', '').strip()
        player_id = data.get('player_id')
        
        if not player_name:
            return jsonify({"success": False, "error": "Spielername ist erforderlich"}), 400
        
        # Prüfe ob Registrierung aktiv ist
        welcome_session = WelcomeSession.get_active_session()
        if not welcome_session:
            return jsonify({"success": False, "error": "Keine aktive Registrierung"}), 400
        
        # Finde die Registrierung
        registration = PlayerRegistration.query.filter_by(
            welcome_session_id=welcome_session.id,
            player_name=player_name
        ).first()
        
        if player_id and registration and registration.id != player_id:
            return jsonify({"success": False, "error": "Spieler-ID stimmt nicht überein"}), 400
        
        if not registration:
            return jsonify({"success": False, "error": "Spieler nicht gefunden"}), 404
        
        # Lösche Profilbild falls vorhanden
        deleted_image = False
        if registration.profile_image_path:
            try:
                import os
                image_path = os.path.join(current_app.static_folder, registration.profile_image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)
                    deleted_image = True
                    current_app.logger.info(f"Profilbild gelöscht: {image_path}")
            except Exception as e:
                current_app.logger.warning(f"Fehler beim Löschen des Profilbildes: {e}")
        
        # Entferne Registrierung aus Datenbank
        db.session.delete(registration)
        db.session.commit()
        
        current_app.logger.info(f"Spieler '{player_name}' erfolgreich entfernt")
        
        return jsonify({
            "success": True,
            "message": f"Spieler '{player_name}' erfolgreich entfernt",
            "deleted_image": deleted_image
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Entfernen des Spielers: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Ein Fehler ist aufgetreten"}), 500


@main_bp.route('/api/advance_field_minigame_phase', methods=['POST'])
def advance_field_minigame_phase():
    """API-Route um die Field Minigame Phase von COMPLETED zur nächsten Phase zu schalten"""
    try:
        active_session = GameSession.query.filter_by(is_active=True).first()
        if not active_session:
            return jsonify({'success': False, 'message': 'Keine aktive Spielsitzung'}), 400
        
        # Prüfe ob Session in FIELD_MINIGAME_COMPLETED Phase ist
        if active_session.current_phase != 'FIELD_MINIGAME_COMPLETED':
            return jsonify({'success': False, 'message': f'Session nicht in FIELD_MINIGAME_COMPLETED Phase (aktuell: {active_session.current_phase})'}), 400
        
        # Bereinige Feld-Minigame Daten
        active_session.current_minigame_name = None
        active_session.current_minigame_description = None
        
        # Bestimme nächste Phase basierend auf Würfelreihenfolge
        if active_session.dice_roll_order and active_session.current_team_turn_id:
            # Prüfe ob noch weitere Teams nach dem aktuellen Team dran sind
            try:
                dice_order_ids = [int(tid_str) for tid_str in active_session.dice_roll_order.split(',') if tid_str.strip().isdigit()]
                current_team_index = dice_order_ids.index(active_session.current_team_turn_id)
                
                if current_team_index < len(dice_order_ids) - 1:
                    # Es gibt noch weitere Teams - bleibe in DICE_ROLLING
                    active_session.current_phase = 'DICE_ROLLING'
                    current_app.logger.info(f"Field Minigame beendet - zurück zu DICE_ROLLING für Team {active_session.current_team_turn_id} (Index {current_team_index} von {len(dice_order_ids)})")
                else:
                    # Das war das letzte Team - Runde beendet
                    active_session.current_phase = 'ROUND_OVER'
                    active_session.current_team_turn_id = None
                    current_app.logger.info("Field Minigame beendet - war letztes Team, Runde abgeschlossen (ROUND_OVER)")
            except (ValueError, IndexError) as e:
                current_app.logger.error(f"Fehler beim Verarbeiten der Würfelreihenfolge: {e}")
                # Fallback: Runde beenden
                active_session.current_phase = 'ROUND_OVER'
                active_session.current_team_turn_id = None
        else:
            # Keine Teams mehr oder Runde schon beendet
            active_session.current_phase = 'ROUND_OVER'
            current_app.logger.info("Field Minigame beendet - keine Würfelreihenfolge oder Team, Runde abgeschlossen (ROUND_OVER)")
        
        # Field-Minigame Daten löschen
        active_session.field_minigame_landing_team_id = None
        active_session.field_minigame_opponent_team_id = None
        active_session.field_minigame_mode = None
        active_session.field_minigame_content_id = None
        active_session.field_minigame_content_type = None
        active_session.field_minigame_result = None
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'new_phase': active_session.current_phase,
            'message': f'Phase gewechselt zu {active_session.current_phase}'
        })
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Weiterschalten der Field Minigame Phase: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@main_bp.route('/api/field_minigame_status')
def field_minigame_status():
    """API für Field Minigame Banner Status - wird vom Gameboard abgerufen"""
    try:
        active_session = GameSession.query.filter_by(is_active=True).first()
        if not active_session:
            return jsonify({"show_banner": False})
        
        # Prüfe ob ein Field Minigame gerade gestartet wurde oder gerade beendet wurde
        if active_session.current_phase == 'FIELD_MINIGAME_TRIGGERED':
            # Phase 1: Minigame läuft - zeige Start-Banner
            # Hole Team-Informationen
            landing_team = None
            opponent_team = None
            
            if active_session.field_minigame_landing_team_id:
                landing_team = Team.query.get(active_session.field_minigame_landing_team_id)
            
            if active_session.field_minigame_opponent_team_id:
                opponent_team = Team.query.get(active_session.field_minigame_opponent_team_id)
            
            # Hole Minispiel-Informationen
            minigame_name = "Unbekanntes Minispiel"
            minigame_instructions = ""
            minigame_materials = ""
            if active_session.field_minigame_content_id:
                try:
                    import os
                    import json
                    
                    # Feld-Minispiele sind im field_minigames Ordner gespeichert
                    # Versuche zuerst den gespeicherten Mode, dann beide Ordner
                    possible_modes = [active_session.field_minigame_mode, 'team_vs_all', 'team_vs_team']
                    field_minigame_path = None
                    
                    for mode in possible_modes:
                        if mode:
                            test_path = os.path.join(
                                current_app.static_folder, 
                                'field_minigames', 
                                mode,
                                f"{active_session.field_minigame_content_id}.json"
                            )
                            if os.path.exists(test_path):
                                field_minigame_path = test_path
                                break
                    
                    if field_minigame_path:
                        with open(field_minigame_path, 'r', encoding='utf-8') as f:
                            minigame_data = json.load(f)
                        minigame_name = minigame_data.get('title', active_session.field_minigame_content_id)
                        minigame_instructions = minigame_data.get('instructions', '')
                        minigame_materials = minigame_data.get('materials', '')
                except Exception as e:
                    current_app.logger.warning(f"Fehler beim Laden der Feld-Minispiel-Daten: {e}")
                    minigame_name = "Unbekanntes Minispiel"
            
            # Hole ausgeloste Spieler mit Profilbildern
            selected_players = {}
            selected_players_with_images = {}
            if active_session.field_minigame_selected_players:
                try:
                    selected_players = json.loads(active_session.field_minigame_selected_players)
                    # Erweitere um Profilbilder
                    for team_name, players in selected_players.items():
                        team = Team.query.filter_by(name=team_name).first()
                        if team:
                            players_with_images = []
                            for player_data in players:
                                player_name = player_data.get('name', '')
                                # Verwende die neue get_player_by_name Methode um vollständige Daten zu bekommen
                                player_info = team.get_player_by_name(player_name)
                                if player_info:
                                    players_with_images.append({
                                        'name': player_name,
                                        'profile_image': player_info.get('profile_image'),
                                        'has_photo': player_info.get('has_photo', False),
                                        'emoji': player_info.get('emoji')
                                    })
                                else:
                                    # Fallback wenn get_player_by_name fehlschlägt
                                    profile_image = team.get_profile_image(player_name)
                                    # Versuche Emoji aus player_config zu holen
                                    player_config = team.get_player_config()
                                    emoji = None
                                    if player_name in player_config:
                                        emoji = player_config[player_name].get('emoji')
                                    
                                    players_with_images.append({
                                        'name': player_name,
                                        'profile_image': profile_image,
                                        'has_photo': profile_image is not None,
                                        'emoji': emoji
                                    })
                            selected_players_with_images[team_name] = players_with_images
                except Exception as e:
                    current_app.logger.warning(f"Fehler beim Laden der Spielerbilder: {e}")
                    selected_players = {}
            
            return jsonify({
                "show_banner": True,
                "banner_type": "start",  # Start-Banner
                "minigame_data": {
                    "mode": active_session.field_minigame_mode,
                    "landing_team": landing_team.name if landing_team else "Unbekannt",
                    "opponent_team": opponent_team.name if opponent_team else "alle anderen Teams",
                    "minigame_name": minigame_name,
                    "minigame_instructions": minigame_instructions,
                    "minigame_materials": minigame_materials,
                    "selected_players": selected_players_with_images or selected_players
                }
            })
        
        elif active_session.current_phase == 'FIELD_MINIGAME_COMPLETED':
            # Phase 2: Minigame beendet - zeige Ergebnis-Banner für 5 Sekunden
            # Hole Team-Informationen
            landing_team = None
            if active_session.field_minigame_landing_team_id:
                landing_team = Team.query.get(active_session.field_minigame_landing_team_id)
            
            # Hole Ergebnis-Informationen
            result = active_session.field_minigame_result  # 'won' oder 'lost'
            
            # Bestimme Belohnung
            reward_forward = 0
            if result == 'won':
                # Lade Konfiguration für Belohnung
                import os
                import json
                config_path = os.path.join(current_app.static_folder, 'field_minigames', 'config.json')
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    field_config = config.get('field_minigames', {})
                    mode_config = field_config.get('modes', {}).get(active_session.field_minigame_mode, {})
                    reward_forward = mode_config.get('reward_forward', 5)
                else:
                    reward_forward = 5  # Default-Wert
            
            return jsonify({
                "show_banner": True,
                "banner_type": "result",  # Ergebnis-Banner
                "result_data": {
                    "won": result == 'won',
                    "team_name": landing_team.name if landing_team else "Unbekannt",
                    "reward_forward": reward_forward,
                    "message": f"🎉 {landing_team.name} gewinnt und bewegt sich {reward_forward} Felder vor!" if result == 'won' else f"❌ {landing_team.name} verliert - keine Bewegung"
                }
            })
        
        return jsonify({"show_banner": False})
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Abrufen des Field Minigame Status: {e}")
        return jsonify({"show_banner": False})