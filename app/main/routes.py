from flask import render_template, jsonify, request
from app.main import main_bp
from app.models import Team, Character
from flask import session
from app import db

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/board')
def game_board():
    # Spieldaten laden
    teams = Team.query.order_by(Team.name).all()
    
    # Admin-Status überprüfen
    is_admin = session.get('is_admin', False)
    
    # Define team colors - adding this line fixes the error
    team_colors = ["#FF5252", "#448AFF", "#4CAF50", "#FFC107", "#9C27B0", "#FF9800"]
    
    return render_template('game_board.html', 
                           teams=teams, 
                           is_admin=is_admin,
                           team_colors=team_colors)  # Pass team_colors to the template

@main_bp.route('/api/board-status')
def board_status():
    """API für Spielstatus-Updates via AJAX"""
    teams = Team.query.order_by(Team.name).all()
    team_data = [
        {
            "id": team.id, 
            "name": team.name, 
            "position": team.position,
            "character": {
                "id": team.character.id,
                "name": team.character.name,
                "color": team.character.color
            } if team.character else None
        } 
        for team in teams
    ]
    return jsonify({"teams": team_data})

@main_bp.route('/api/update-position', methods=['POST'])
def update_position():
    """API zum Aktualisieren der Team-Position"""
    data = request.json
    team_id = data.get('team_id')
    position = data.get('position')
    
    if team_id is None or position is None:
        return jsonify({"success": False, "error": "Ungültige Parameter"}), 400
    
    team = Team.query.get(team_id)
    if team:
        team.position = position
        db.session.commit()
        return jsonify({"success": True})
    
    return jsonify({"success": False, "error": "Team nicht gefunden"}), 404