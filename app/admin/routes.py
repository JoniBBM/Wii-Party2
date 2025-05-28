from flask import render_template, redirect, url_for, flash, request, session
from app.admin import admin_bp
from app import db
from app.models import Team, Admin, Character
from config import Config

@admin_bp.route('/')
def admin_index():
    return redirect(url_for('admin.admin_login'))

@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('is_admin'):
        return redirect(url_for('admin.admin_panel'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        
        admin = Admin.query.filter_by(username="admin").first()
        if admin and admin.check_password(password):
            session['is_admin'] = True
            flash('Erfolgreich als Admin eingeloggt', 'success')
            return redirect(url_for('admin.admin_panel'))
        else:
            flash('Ungültiges Admin-Passwort', 'danger')
    
    return render_template('admin_login.html')

@admin_bp.route('/panel', methods=['GET', 'POST'])
def admin_panel():
    if not session.get('is_admin'):
        flash('Bitte zuerst als Admin einloggen', 'warning')
        return redirect(url_for('admin.admin_login'))
    
    if request.method == 'POST':
        # Team anlegen
        name = request.form['name']
        members = request.form['members']
        password = request.form['password']
        character_id = request.form.get('character_id')
        
        if not name or not members or not password:
            flash('Bitte alle Felder ausfüllen!', 'danger')
        else:
            team = Team(
                name=name, 
                members=members,
                character_id=character_id if character_id else None
            )
            team.set_password(password)
            db.session.add(team)
            db.session.commit()
            flash(f'Team "{name}" erfolgreich erstellt!', 'success')
    
    teams = Team.query.order_by(Team.position.desc()).all()
    characters = Character.query.all()
    return render_template('admin.html', teams=teams, characters=characters)

@admin_bp.route('/logout')
def admin_logout():
    session.pop('is_admin', None)
    flash('Admin erfolgreich ausgeloggt', 'success')
    return redirect(url_for('main.index'))

@admin_bp.route('/delete_team/<int:team_id>', methods=['POST'])
def delete_team(team_id):
    if not session.get('is_admin'):
        flash('Bitte zuerst als Admin einloggen', 'warning')
        return redirect(url_for('admin.admin_login'))
    
    team = Team.query.get(team_id)
    if team:
        db.session.delete(team)
        db.session.commit()
        flash('Team gelöscht!', 'success')
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/move_team/<int:team_id>', methods=['POST'])
def move_team(team_id):
    if not session.get('is_admin'):
        flash('Bitte zuerst als Admin einloggen', 'warning')
        return redirect(url_for('admin.admin_login'))
    
    team = Team.query.get(team_id)
    if team:
        steps = int(request.form.get('steps', 1))
        team.position += steps
        db.session.commit()
        flash(f'Team {team.name} um {steps} Felder bewegt!', 'success')
    
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/reset_positions', methods=['POST'])
def reset_positions():
    if not session.get('is_admin'):
        flash('Bitte zuerst als Admin einloggen', 'warning')
        return redirect(url_for('admin.admin_login'))
    
    teams = Team.query.all()
    for team in teams:
        team.position = 0
    
    db.session.commit()
    flash('Alle Team-Positionen zurückgesetzt!', 'success')
    return redirect(url_for('admin.admin_panel'))

@admin_bp.route('/assign_character/<int:team_id>', methods=['POST'])
def assign_character(team_id):
    if not session.get('is_admin'):
        flash('Bitte zuerst als Admin einloggen', 'warning')
        return redirect(url_for('admin.admin_login'))
    
    team = Team.query.get(team_id)
    character_id = request.form.get('character_id')
    
    if team and character_id:
        team.character_id = character_id
        db.session.commit()
        flash(f'Charakter für Team {team.name} zugewiesen!', 'success')
    
    return redirect(url_for('admin.admin_panel'))