from flask import render_template, jsonify, request, session, current_app, redirect, url_for, flash
from app.main import main_bp
from app.models import Team, Character, GameSession, GameEvent, Admin, WelcomeSession, PlayerRegistration
from app import db, csrf
import random # Für Würfellogik
import traceback # Für detaillierte Fehlermeldungen
from flask_login import current_user
from datetime import datetime, timedelta
import json

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
                "dice_roll_order": dice_order_ids,
                "minigame_folder_name": minigame_folder_name,
                # SONDERFELD: Vulkan-Status (für zukünftige Implementierung)
                "volcano_countdown": active_session_query.volcano_countdown if hasattr(active_session_query, 'volcano_countdown') else 0,
                "volcano_active": active_session_query.volcano_active if hasattr(active_session_query, 'volcano_active') else False
            }
        
        # Get last dice result for current team turn (only recent results from last 5 minutes)
        last_dice_result = None
        if current_team_id:
            from datetime import datetime, timedelta
            
            # Only get dice results from the last 5 minutes to avoid old results
            recent_time = datetime.utcnow() - timedelta(minutes=5)
            
            last_dice_event = GameEvent.query.filter_by(
                game_session_id=active_session_query.id,
                related_team_id=current_team_id
            ).filter(
                GameEvent.event_type.in_(['dice_roll', 'admin_dice_roll', 'admin_dice_roll_legacy']),
                GameEvent.timestamp >= recent_time
            ).order_by(GameEvent.timestamp.desc()).first()
            
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
                        'was_blocked': event_data.get('was_blocked', False),
                        'barrier_released': event_data.get('barrier_released', False)
                    }
                    
                    current_app.logger.info(f"Found recent dice result for team {current_team_id}: {last_dice_result}")
                except Exception as e:
                    current_app.logger.error(f"Error parsing dice result: {e}")
                    last_dice_result = None

        return jsonify({
            "teams": team_data,
            "game_session": game_session_data,
            "last_dice_result": last_dice_result
            })

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
        
        event_description = f"Admin würfelte für Team {team.name}: {standard_dice_roll}"
        if bonus_dice_roll > 0:
            event_description += f" (Bonus: {bonus_dice_roll}, Gesamt: {total_roll})"
        
        if (special_fields_available and hasattr(team, 'is_blocked') and 
            team.is_blocked and not barrier_check_result.get('released', False)):
            event_description += f" - BLOCKIERT: Konnte sich nicht befreien."
        else:
            event_description += f" und bewegte sich von Feld {old_position} zu Feld {new_position}."
        
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
                "barrier_released": barrier_check_result.get('released', False) if barrier_check_result else False
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

        if current_team_index_in_order < len(dice_order_ids_int) - 1:
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
            "new_phase": active_session.current_phase
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
def register_player():
    """Spieler registrieren"""
    try:
        
        data = request.get_json()
        player_name = data.get('player_name', '').strip()
        
        if not player_name:
            return jsonify({"success": False, "error": "Name ist erforderlich"}), 400
        
        if len(player_name) > 50:
            return jsonify({"success": False, "error": "Name ist zu lang (max. 50 Zeichen)"}), 400
        
        # Prüfe ob Registrierung aktiv ist
        welcome_session = WelcomeSession.get_active_session()
        if not welcome_session:
            return jsonify({"success": False, "error": "Keine aktive Registrierung"}), 400
        
        if welcome_session.teams_created:
            return jsonify({"success": False, "error": "Registrierung ist bereits abgeschlossen"}), 400
        
        # Prüfe ob Name bereits existiert
        existing = PlayerRegistration.query.filter_by(
            welcome_session_id=welcome_session.id,
            player_name=player_name
        ).first()
        
        if existing:
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
            players.append({
                "id": registration.id,
                "name": registration.player_name,
                "registration_time": registration.registration_time.isoformat()
            })
        
        # Hole Team-Informationen falls bereits erstellt
        teams = []
        if welcome_session.teams_created:
            # Hole alle Teams die in dieser Welcome-Session erstellt wurden
            team_objects = Team.query.join(PlayerRegistration).filter(
                PlayerRegistration.welcome_session_id == welcome_session.id,
                PlayerRegistration.assigned_team_id.isnot(None)
            ).distinct().all()
            
            for team in team_objects:
                # Hole Mitglieder dieses Teams
                team_players = PlayerRegistration.query.filter_by(
                    welcome_session_id=welcome_session.id,
                    assigned_team_id=team.id
                ).all()
                
                teams.append({
                    "id": team.id,
                    "name": team.name,
                    "password": team.welcome_password or "Passwort nicht verfügbar",
                    "members": [p.player_name for p in team_players]
                })
        
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
            for team_id_tuple in team_ids:
                team = Team.query.get(team_id_tuple[0])
                if team:
                    # Hole Teammitglieder aus der Session
                    members = PlayerRegistration.query.filter_by(
                        welcome_session_id=welcome_session.id,
                        assigned_team_id=team.id
                    ).all()
                    
                    teams_data.append({
                        "id": team.id,
                        "name": team.name,
                        "password": team.welcome_password or "Kein Passwort",
                        "members": [member.player_name for member in members]
                    })
        
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
        # Hole Victory-Daten aus Session
        victory_data = session.get('victory_data')
        
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
                
                # Zähle Minispiel-Events
                minigame_events = GameEvent.query.filter_by(
                    game_session_id=game_session.id,
                    event_type='minigame_started'
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
    """Berechnet detaillierte Minispiel-Statistiken für alle Teams"""
    if not game_session_id:
        return {}
    
    try:
        # Hole alle Minispiel-Events für diese Session
        minigame_events = GameEvent.query.filter_by(
            game_session_id=game_session_id,
            event_type='minigame_placements'
        ).all()
        
        team_stats = {}
        
        for event in minigame_events:
            if event.data_json:
                try:
                    # Parse Minispiel-Placement-Daten
                    if isinstance(event.data_json, str):
                        data = json.loads(event.data_json)
                    else:
                        data = event.data_json
                    
                    placements = data.get('placements', {})
                    
                    for team_id_str, placement in placements.items():
                        if team_id_str not in team_stats:
                            team_stats[team_id_str] = {
                                'wins': 0,
                                'participations': 0,
                                'placements': [],
                                'average_placement': 0.0
                            }
                        
                        team_stats[team_id_str]['participations'] += 1
                        team_stats[team_id_str]['placements'].append(placement)
                        
                        # Zähle Siege (1. Platz)
                        if placement == 1:
                            team_stats[team_id_str]['wins'] += 1
                
                except (json.JSONDecodeError, KeyError) as e:
                    current_app.logger.warning(f"Fehler beim Parsen von Minispiel-Daten: {e}")
        
        # Berechne Durchschnittsplatzierungen
        for team_id, stats in team_stats.items():
            if stats['placements']:
                stats['average_placement'] = sum(stats['placements']) / len(stats['placements'])
        
        return team_stats
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Berechnen der Minispiel-Statistiken: {e}")
        return {}
    
def calculate_position_history(game_session_id):
    """Berechnet Positionsverlauf für alle Teams"""
    if not game_session_id:
        return {}
    
    try:
        # Hole alle Bewegungs-Events
        movement_events = GameEvent.query.filter_by(
            game_session_id=game_session_id
        ).filter(
            GameEvent.event_type.in_(['dice_roll', 'admin_dice_roll', 'admin_dice_roll_legacy'])
        ).order_by(GameEvent.timestamp.asc()).all()
        
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
        
        # Prüfe ob Minispiel läuft und nicht alle Teams spielen
        if active_session.current_phase != 'SETUP_MINIGAME':
            return jsonify({
                "success": True,
                "show_faces": False,
                "message": "Kein Minispiel in Vorbereitung"
            })
        
        # Hole ausgewählte Spieler aus der Session
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
            
            for player_name in player_names:
                # Hole Profilbild aus Team-Daten
                profile_image = team.get_profile_image(player_name)
                
                if profile_image:
                    player_faces.append({
                        "player_name": player_name,
                        "team_name": team_name,
                        "team_id": team.id,
                        "team_color": team_color,
                        "image_path": profile_image
                    })
        
        # Nur anzeigen wenn mindestens ein Profilbild vorhanden ist
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