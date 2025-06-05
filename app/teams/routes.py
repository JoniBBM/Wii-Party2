from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import Team, db, Admin, GameSession, GameRound, Minigame # Admin importieren für Typ-Check
from app.forms import TeamLoginForm # Importiere das neue Formular

teams_bp = Blueprint('teams', __name__, url_prefix='/teams')

@teams_bp.route('/login', methods=['GET', 'POST'])
def team_login():
    if current_user.is_authenticated:
        if isinstance(current_user, Team):
            return redirect(url_for('teams.team_dashboard'))
        elif isinstance(current_user, Admin): # Admin ist bereits eingeloggt
             flash('Du bist bereits als Admin eingeloggt.', 'info')
             return redirect(url_for('admin.admin_dashboard'))
        # Andere User-Typen könnten hier auch behandelt werden

    form = TeamLoginForm() # Formularinstanz erstellen
    if form.validate_on_submit():
        team = Team.query.filter_by(name=form.team_name.data).first()
        if team and team.check_password(form.password.data):
            login_user(team)
            flash(f'Team "{team.name}" erfolgreich eingeloggt.', 'success')
            # next_page = request.args.get('next') # Für Redirect nach Login, falls benötigt
            # return redirect(next_page or url_for('teams.team_dashboard'))
            return redirect(url_for('teams.team_dashboard'))
        else:
            flash('Ungültiger Teamname oder Passwort.', 'danger')
    return render_template('team_login.html', title='Team Login', form=form)

@teams_bp.route('/logout')
@login_required
def team_logout():
    if not isinstance(current_user, Team):
        flash('Nur Teams können sich hier ausloggen.', 'warning')
        # Je nach Logik, wohin ein nicht-Team-User hier geleitet werden soll
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
    
    # Spielbrett-Informationen
    max_board_fields = 73  # Kann aus Config geholt werden falls konfigurierbar
    
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
        'title': f'Dashboard Team {team_user.name}'
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