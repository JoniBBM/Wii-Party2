from flask import render_template, redirect, url_for, flash, request
from app.teams import teams_bp
from app import db
from app.models import Team
from flask_login import login_user, logout_user, login_required, current_user

@teams_bp.route('/login', methods=['GET', 'POST'])
def team_login():
    if current_user.is_authenticated:
        return redirect(url_for('teams.dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')
        
        team = Team.query.filter_by(name=name).first()
        
        if team and team.check_password(password):
            login_user(team)
            flash('Erfolgreich eingeloggt!', 'success')
            return redirect(url_for('teams.dashboard'))
        else:
            flash('Ungültiger Teamname oder Passwort', 'danger')
    
    return render_template('team_login.html', action='login')

@teams_bp.route('/register', methods=['GET', 'POST'])
def team_register():
    if current_user.is_authenticated:
        return redirect(url_for('teams.dashboard'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        members = request.form.get('members')
        password = request.form.get('password')
        
        if not name or not members or not password:
            flash('Bitte alle Felder ausfüllen!', 'danger')
            return render_template('team_login.html', action='register')
            
        if Team.query.filter_by(name=name).first():
            flash('Teamname bereits vergeben!', 'danger')
            return render_template('team_login.html', action='register')
        
        team = Team(
            name=name,
            members=members,
            is_admin=False
        )
        team.set_password(password)
        
        db.session.add(team)
        db.session.commit()
        flash('Team erfolgreich registriert!', 'success')
        return redirect(url_for('teams.team_login'))
    
    return render_template('team_login.html', action='register')

@teams_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('team_dashboard.html', team=current_user)

@teams_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Erfolgreich ausgeloggt', 'success')
    return redirect(url_for('main.index'))
