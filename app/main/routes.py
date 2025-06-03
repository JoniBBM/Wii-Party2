from flask import render_template, jsonify, request, session, current_app
from app.main import main_bp
from app.models import Team, Character, GameSession, GameEvent, Admin # Admin importiert für Check
from app import db
import random # Für Würfellogik
import traceback # Für detaillierte Fehlermeldungen
from flask_login import current_user

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/board')
def game_board():
    teams = Team.query.order_by(Team.name).all()
    active_session = GameSession.query.filter_by(is_active=True).first()
    is_admin = session.get('is_admin', False)
    team_colors = ["#FF5252", "#448AFF", "#4CAF50", "#FFC107", "#9C27B0", "#FF9800"]
    
    return render_template('game_board.html', 
                           teams=teams, 
                           is_admin=is_admin,
                           team_colors=team_colors,
                           active_session=active_session)

@main_bp.route('/api/board-status')
def board_status():
    """API für Spielstatus-Updates via AJAX mit verbesserter Fehlerbehandlung"""
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
                "minigame_placement": team_obj.minigame_placement # Kann None sein
            })

        game_session_data = None
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

            game_session_data = {
                "current_minigame_name": active_session_query.current_minigame_name,
                "current_minigame_description": active_session_query.current_minigame_description,
                "current_phase": active_session_query.current_phase,
                "current_team_turn_id": current_team_id,
                "dice_roll_order": dice_order_ids
            }
        
        return jsonify({
            "teams": team_data,
            "game_session": game_session_data
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

        standard_dice_roll = random.randint(1, 6)
        bonus_dice_roll = 0
        if team.bonus_dice_sides and team.bonus_dice_sides > 0:
            bonus_dice_roll = random.randint(1, team.bonus_dice_sides)
        
        total_roll = standard_dice_roll + bonus_dice_roll
        old_position = team.current_position
        
        # Annahme: Maximale Feldanzahl (z.B. 72 für 73 Felder 0-72)
        max_field_index = 72 
        new_position = min(team.current_position + total_roll, max_field_index)
        team.current_position = new_position

        event_description = f"Admin würfelte für Team {team.name}: {standard_dice_roll}"
        if bonus_dice_roll > 0:
            event_description += f" (Bonus: {bonus_dice_roll}, Gesamt: {total_roll})"
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
                "rolled_by": "admin_legacy_route"
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

        return jsonify({
            "success": True,
            "team_id": team.id,
            "team_name": team.name,
            "standard_roll": standard_dice_roll,
            "bonus_roll": bonus_dice_roll,
            "total_roll": total_roll,
            "new_position": new_position,
            "next_team_id": active_session.current_team_turn_id,
            "new_phase": active_session.current_phase
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Schwerer Fehler in /api/roll_dice_action_admin_only: {e}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": "Ein interner Serverfehler beim Würfeln ist aufgetreten.", "details": str(e)}), 500