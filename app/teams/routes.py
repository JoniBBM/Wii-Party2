from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import Team, db, Admin # Admin importieren für Typ-Check
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

@teams_bp.route('/dashboard')
@login_required
def team_dashboard():
    if not isinstance(current_user, Team):
        flash('Nur eingeloggte Teams können ihr Dashboard sehen.', 'warning')
        return redirect(url_for('teams.team_login')) # Oder main.index
    
    # Hier könnten spezifische Daten für das Team-Dashboard geladen werden
    # z.B. active_session = GameSession.query.filter_by(is_active=True).first()
    #      team_score = current_user.get_total_score(game_session_id=active_session.id if active_session else None)
    
    return render_template('team_dashboard.html', title=f'Dashboard Team {current_user.name}')
