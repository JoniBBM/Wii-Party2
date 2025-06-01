import sys # Importiere sys für stdout.flush()
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app.models import Admin, Team, Minigame, TeamMinigameScore, Character, GameSession, GameEvent, db
from app.forms import AdminLoginForm, TeamForm, MinigameForm, ScoreForm
import os
import random

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

current_video_minigame_data = None

def get_video_minigames():
    video_folder = current_app.config.get('MINIGAME_VIDEO_FOLDER')
    videos = []
    if not video_folder or not os.path.exists(video_folder):
        print(f"DEBUG: Video-Ordner '{video_folder}' nicht gefunden oder nicht konfiguriert."); sys.stdout.flush()
        return videos
    try:
        for f in os.listdir(video_folder):
            if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                title = os.path.splitext(f)[0].replace('_', ' ').replace('-', ' ').title()
                videos.append({'filename': f, 'title': title, 'type': 'video'})
    except Exception as e:
        print(f"DEBUG: Fehler beim Lesen des Video-Ordners: {e}"); sys.stdout.flush()
    return videos

@admin_bp.route('/')
@login_required
def admin_dashboard():
    print("DEBUG: admin_dashboard aufgerufen"); sys.stdout.flush()
    if not isinstance(current_user, Admin):
        print("DEBUG: admin_dashboard - Zugriff verweigert, kein Admin."); sys.stdout.flush()
        flash('Zugriff verweigert. Nur Admins können das Admin Dashboard sehen.', 'danger')
        return redirect(url_for('main.index'))
    
    print("DEBUG: admin_dashboard - Lade Daten..."); sys.stdout.flush()
    try:
        teams = Team.query.all()
        minigames_db = Minigame.query.filter_by(is_video_game=False).all()
        video_minigames_list = get_video_minigames()
        print(f"DEBUG: admin_dashboard - Teams: {len(teams)}, DB-Minispiele: {len(minigames_db)}, Video-Minispiele: {len(video_minigames_list)}"); sys.stdout.flush()
    except Exception as e:
        print(f"DEBUG: admin_dashboard - FEHLER beim Laden von Daten: {e}"); sys.stdout.flush()
        flash(f"Fehler beim Laden der Dashboard-Daten: {e}", "danger")
        teams = []
        minigames_db = []
        video_minigames_list = []

    current_game_session = GameSession.query.filter_by(is_active=True).first()
    current_minigame_title = "Kein Minispiel aktiv"
    current_minigame_id = None
    current_minigame_is_video = False
    active_video_filename = None

    if current_video_minigame_data:
        current_minigame_title = current_video_minigame_data['title']
        current_minigame_is_video = True
        active_video_filename = current_video_minigame_data['filename']
    elif current_game_session and current_game_session.current_minigame_id:
        mg = Minigame.query.get(current_game_session.current_minigame_id)
        if mg:
            current_minigame_title = mg.name
            current_minigame_id = mg.id
    
    print("DEBUG: admin_dashboard - Rendere Template."); sys.stdout.flush()
    return render_template('admin.html', 
                           teams=teams, 
                           minigames_db=minigames_db,
                           video_minigames=video_minigames_list,
                           current_minigame_title=current_minigame_title,
                           current_minigame_id=current_minigame_id,
                           current_minigame_is_video=current_minigame_is_video,
                           current_video_filename=active_video_filename)

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    print(f"--- DEBUG: Admin Login Route AUFGERUFEN, Methode: {request.method} ---"); sys.stdout.flush()
    if current_user.is_authenticated and isinstance(current_user, Admin):
        print("DEBUG: Admin bereits eingeloggt, redirect zum Dashboard."); sys.stdout.flush()
        flash('Du bist bereits als Admin eingeloggt.', 'info')
        return redirect(url_for('admin.admin_dashboard'))
    
    form = AdminLoginForm()
    print(f"DEBUG: AdminLoginForm Instanz erstellt."); sys.stdout.flush()
    
    if request.method == 'POST':
        print(f"DEBUG: Admin Login POST Request erhalten."); sys.stdout.flush()
        print(f"DEBUG: Formular Daten: username='{form.username.data}', password_present={'yes' if form.password.data else 'no'}"); sys.stdout.flush()
        if form.validate_on_submit():
            print(f"DEBUG: Admin Login Form VALIDIERT. Username: {form.username.data}"); sys.stdout.flush()
            try:
                admin = Admin.query.filter_by(username=form.username.data).first()
                if admin:
                    print(f"DEBUG: Admin-Objekt GEFUNDEN: {admin.username}"); sys.stdout.flush()
                    if admin.check_password(form.password.data):
                        print("DEBUG: Admin Passwort KORREKT."); sys.stdout.flush()
                        login_user(admin)
                        flash('Admin erfolgreich eingeloggt.', 'success')
                        next_page = request.args.get('next')
                        print(f"DEBUG: Admin Login ERFOLGREICH. Redirect zu: {next_page or url_for('admin.admin_dashboard')}"); sys.stdout.flush()
                        return redirect(next_page or url_for('admin.admin_dashboard'))
                    else:
                        print("DEBUG: Admin Passwort FALSCH."); sys.stdout.flush()
                        flash('Ungültiger Benutzername oder Passwort.', 'danger')
                else:
                    print(f"DEBUG: Admin-Benutzer '{form.username.data}' NICHT gefunden."); sys.stdout.flush()
                    flash('Ungültiger Benutzername oder Passwort.', 'danger')
            except Exception as e:
                print(f"DEBUG: FEHLER während Admin Login Datenbankabfrage: {e}"); sys.stdout.flush()
                flash("Ein Datenbankfehler ist beim Login aufgetreten.", "danger")
        else: 
            print(f"DEBUG: Admin Login Form NICHT validiert bei POST. Fehler: {form.errors}"); sys.stdout.flush()
            flash('Fehler bei der Formularvalidierung. Bitte überprüfe deine Eingaben.', 'warning')
            
    return render_template('admin_login.html', title='Admin Login', form=form)

# ... (Rest der Admin-Routen bleiben unverändert, aber du könntest dort auch sys.stdout.flush() hinzufügen, wenn nötig) ...
@admin_bp.route('/logout')
@login_required
def logout():
    print("DEBUG: Admin Logout aufgerufen"); sys.stdout.flush()
    if not isinstance(current_user, Admin):
        flash('Nur Admins können sich hier ausloggen.', 'warning')
        return redirect(url_for('main.index'))
    logout_user()
    flash('Admin erfolgreich ausgeloggt.', 'info')
    return redirect(url_for('main.index'))

@admin_bp.route('/create_team', methods=['GET', 'POST'])
@login_required
def create_team():
    if not isinstance(current_user, Admin): return redirect(url_for('main.index'))
    form = TeamForm()
    if form.validate_on_submit():
        existing_team = Team.query.filter_by(name=form.name.data).first()
        if existing_team:
            flash('Ein Team mit diesem Namen existiert bereits.', 'warning')
        else:
            team = Team(name=form.name.data, character_name=form.character.data)
            db.session.add(team)
            db.session.commit()
            flash('Team erfolgreich erstellt.', 'success')
            return redirect(url_for('admin.admin_dashboard'))
    return render_template('create_team.html', title='Team erstellen', form=form)

@admin_bp.route('/edit_team/<int:team_id>', methods=['GET', 'POST'])
@login_required
def edit_team(team_id):
    if not isinstance(current_user, Admin): return redirect(url_for('main.index'))
    team = Team.query.get_or_404(team_id)
    form = TeamForm(obj=team)
    if form.validate_on_submit():
        existing_team = Team.query.filter(Team.id != team_id, Team.name == form.name.data).first()
        if existing_team:
            flash('Ein anderes Team mit diesem Namen existiert bereits.', 'warning')
        else:
            team.name = form.name.data
            team.character_name = form.character.data
            db.session.commit()
            flash('Team erfolgreich aktualisiert.', 'success')
            return redirect(url_for('admin.admin_dashboard'))
    return render_template('edit_team.html', title='Team bearbeiten', form=form, team=team)

@admin_bp.route('/delete_team/<int:team_id>', methods=['POST'])
@login_required
def delete_team(team_id):
    if not isinstance(current_user, Admin): return redirect(url_for('main.index'))
    team = Team.query.get_or_404(team_id)
    TeamMinigameScore.query.filter_by(team_id=team.id).delete()
    db.session.delete(team)
    db.session.commit()
    flash('Team und zugehörige Scores erfolgreich gelöscht.', 'success')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/create_minigame', methods=['GET', 'POST'])
@login_required
def create_minigame():
    if not isinstance(current_user, Admin): return redirect(url_for('main.index'))
    form = MinigameForm()
    if form.validate_on_submit():
        minigame = Minigame(name=form.name.data, description=form.description.data, is_video_game=False)
        db.session.add(minigame)
        db.session.commit()
        flash('Minispiel erfolgreich erstellt.', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    return render_template('create_minigame.html', title='Minispiel erstellen', form=form)

@admin_bp.route('/edit_minigame/<int:minigame_id>', methods=['GET', 'POST'])
@login_required
def edit_minigame(minigame_id):
    if not isinstance(current_user, Admin): return redirect(url_for('main.index'))
    minigame = Minigame.query.get_or_404(minigame_id)
    if minigame.is_video_game:
        flash("Video-Minispiele können hier nicht bearbeitet werden.", "warning")
        return redirect(url_for('admin.admin_dashboard'))
    form = MinigameForm(obj=minigame)
    if form.validate_on_submit():
        minigame.name = form.name.data
        minigame.description = form.description.data
        db.session.commit()
        flash('Minispiel erfolgreich aktualisiert.', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    return render_template('edit_minigame.html', title='Minispiel bearbeiten', form=form, minigame=minigame)

@admin_bp.route('/delete_minigame/<int:minigame_id>', methods=['POST'])
@login_required
def delete_minigame(minigame_id):
    if not isinstance(current_user, Admin): return redirect(url_for('main.index'))
    minigame = Minigame.query.get_or_404(minigame_id)
    TeamMinigameScore.query.filter_by(minigame_id=minigame.id).delete()
    db.session.delete(minigame)
    db.session.commit()
    flash('Minispiel und zugehörige Scores erfolgreich gelöscht.', 'success')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/start_random_minigame', methods=['POST'])
@login_required
def start_random_minigame():
    global current_video_minigame_data
    if not isinstance(current_user, Admin): return redirect(url_for('main.index'))

    current_game_session = GameSession.query.filter_by(is_active=True).first()
    if not current_game_session:
        current_game_session = GameSession(is_active=True)
        db.session.add(current_game_session)
    
    db_minigames = Minigame.query.filter_by(is_video_game=False).all()
    video_minigames_list = get_video_minigames()

    all_games = []
    for mg in db_minigames:
        all_games.append({'id': mg.id, 'name': mg.name, 'type': 'db'})
    for vid_mg in video_minigames_list:
        all_games.append({'id': vid_mg['filename'], 'name': vid_mg['title'], 'type': 'video'})

    if not all_games:
        flash('Keine Minispiele verfügbar, um ein zufälliges Spiel zu starten.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))

    selected_game = random.choice(all_games)
    current_video_minigame_data = None 
    current_game_session.current_minigame_id = None

    if selected_game['type'] == 'db':
        current_game_session.current_minigame_id = selected_game['id']
        flash(f"Zufälliges DB-Minispiel gestartet: {selected_game['name']}", 'info')
        event = GameEvent(game_session_id=current_game_session.id, event_type="minigame_started", description=f"Minigame '{selected_game['name']}' (ID: {selected_game['id']}) gestartet.")
        db.session.add(event)
    elif selected_game['type'] == 'video':
        video_obj = next((v for v in video_minigames_list if v['filename'] == selected_game['id']), None)
        if video_obj:
            current_video_minigame_data = video_obj
            flash(f"Zufälliges Video-Minispiel ausgewählt: {video_obj['title']}", 'info')
            event = GameEvent(game_session_id=current_game_session.id, event_type="video_minigame_selected", description=f"Video-Minigame '{video_obj['title']}' (Datei: {video_obj['filename']}) ausgewählt.")
            db.session.add(event)
        else:
            flash("Fehler bei der Auswahl des Video-Minispiels.", "danger")
    
    db.session.commit()
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/enter_scores/<int:minigame_id>', methods=['GET', 'POST'])
@login_required
def enter_scores(minigame_id):
    if not isinstance(current_user, Admin): return redirect(url_for('main.index'))
    minigame = Minigame.query.get_or_404(minigame_id)
    if minigame.is_video_game: 
        flash("Scores für Video-Minispiele bitte über die entsprechende Seite eingeben.", "warning")
        try:
            parts = minigame.name.split("Datei: ")
            video_filename_from_name = parts[1] if len(parts) > 1 else None
            if video_filename_from_name:
                 return redirect(url_for('admin.enter_video_scores', video_filename=video_filename_from_name))
            else:
                flash("Konnte Video-Dateinamen nicht aus Minigame-Namen extrahieren (Format erwartet: 'Video: ..., Datei: ...').", "danger")
                return redirect(url_for('admin.admin_dashboard'))
        except IndexError:
             flash("Konnte Video-Dateinamen nicht aus Minigame-Namen extrahieren.", "danger")
             return redirect(url_for('admin.admin_dashboard'))

    teams = Team.query.all()
    form = ScoreForm() 

    current_game_session = GameSession.query.filter_by(is_active=True).first()
    if not current_game_session:
        flash("Keine aktive Spielsitzung. Bitte starte zuerst ein Spiel.", "warning")
        return redirect(url_for('admin.admin_dashboard'))

    if request.method == 'POST':
        if current_game_session.current_minigame_id != minigame_id:
            flash("Die eingegebenen Ergebnisse sind nicht für das aktuell aktive Minispiel.", "warning")
            return redirect(url_for('admin.admin_dashboard'))

        for team in teams:
            score_value_str = request.form.get(f'score_team_{team.id}')
            if score_value_str is not None and score_value_str.strip().isdigit():
                score_value = int(score_value_str)
                team_score = TeamMinigameScore.query.filter_by(
                    team_id=team.id,
                    minigame_id=minigame.id,
                    game_session_id=current_game_session.id
                ).first()

                if team_score:
                    team_score.score = score_value
                else:
                    team_score = TeamMinigameScore(
                        team_id=team.id,
                        minigame_id=minigame.id,
                        score=score_value,
                        game_session_id=current_game_session.id
                    )
                    db.session.add(team_score)
                
                event_desc = f"Score für Team '{team.name}' im Minigame '{minigame.name}' auf {score_value} gesetzt."
                event = GameEvent(game_session_id=current_game_session.id, event_type="score_updated", description=event_desc)
                db.session.add(event)
            elif score_value_str is not None and score_value_str.strip() != "": 
                flash(f"Ungültige Eingabe für Team {team.name}. Bitte eine Zahl eingeben.", "warning")

        db.session.commit()
        flash(f'Scores für Minispiel "{minigame.name}" erfolgreich gespeichert.', 'success')
        return redirect(url_for('admin.admin_dashboard'))

    scores_data = {}
    if current_game_session:
        for team in teams:
            team_score = TeamMinigameScore.query.filter_by(
                team_id=team.id, 
                minigame_id=minigame.id,
                game_session_id=current_game_session.id
            ).first()
            scores_data[team.id] = team_score.score if team_score else 0
    
    return render_template('enter_scores.html', title=f"Scores für {minigame.name}", minigame=minigame, teams=teams, form=form, scores_data=scores_data)

@admin_bp.route('/enter_video_scores/<string:video_filename>', methods=['GET', 'POST'])
@login_required
def enter_video_scores(video_filename):
    global current_video_minigame_data
    if not isinstance(current_user, Admin): return redirect(url_for('main.index'))

    video_title = "Unbekanntes Video-Minispiel"
    all_video_games = get_video_minigames()
    found_video = next((vid for vid in all_video_games if vid['filename'] == video_filename), None)
    
    if found_video:
        video_title = found_video['title']
        if not current_video_minigame_data or current_video_minigame_data['filename'] != video_filename:
            current_video_minigame_data = found_video
    else:
        flash(f"Video-Minispiel mit Dateinamen '{video_filename}' nicht gefunden.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    teams = Team.query.all()
    current_game_session = GameSession.query.filter_by(is_active=True).first()
    if not current_game_session:
        flash("Keine aktive Spielsitzung. Bitte starte zuerst ein Spiel.", "warning")
        return redirect(url_for('admin.admin_dashboard'))

    minigame_entry_name = f"Video: {video_title}, Datei: {video_filename}"
    minigame_db_entry = Minigame.query.filter_by(name=minigame_entry_name).first()
    
    if not minigame_db_entry:
        minigame_db_entry = Minigame(name=minigame_entry_name, description=f"Video-Minispiel", is_video_game=True)
        db.session.add(minigame_db_entry)
        db.session.flush() 

    minigame_id_for_scores = minigame_db_entry.id

    if request.method == 'POST':
        for team in teams:
            score_value_str = request.form.get(f'score_team_{team.id}')
            if score_value_str is not None and score_value_str.strip().isdigit():
                score_value = int(score_value_str)
                team_score = TeamMinigameScore.query.filter_by(
                    team_id=team.id,
                    minigame_id=minigame_id_for_scores,
                    game_session_id=current_game_session.id
                ).first()

                if team_score:
                    team_score.score = score_value
                else:
                    team_score = TeamMinigameScore(
                        team_id=team.id,
                        minigame_id=minigame_id_for_scores,
                        score=score_value,
                        game_session_id=current_game_session.id
                    )
                    db.session.add(team_score)
                
                event_desc = f"Score für Team '{team.name}' im Video-Minigame '{video_title}' auf {score_value} gesetzt."
                event = GameEvent(game_session_id=current_game_session.id, event_type="score_updated", description=event_desc)
                db.session.add(event)
            elif score_value_str is not None and score_value_str.strip() != "":
                flash(f"Ungültige Eingabe für Team {team.name}. Bitte eine Zahl eingeben.", "warning")
        
        db.session.commit()
        flash(f'Scores für Video-Minispiel "{video_title}" erfolgreich gespeichert.', 'success')
        return redirect(url_for('admin.admin_dashboard'))

    scores_data = {}
    if current_game_session and minigame_db_entry:
        for team in teams:
            team_score = TeamMinigameScore.query.filter_by(
                team_id=team.id,
                minigame_id=minigame_db_entry.id,
                game_session_id=current_game_session.id
            ).first()
            scores_data[team.id] = team_score.score if team_score else 0
    
    return render_template('enter_video_scores.html', title=f"Scores für {video_title}", video_title=video_title, video_filename=video_filename, teams=teams, scores_data=scores_data)

@admin_bp.route('/reset_game_state', methods=['POST'])
@login_required
def reset_game_state():
    global current_video_minigame_data
    if not isinstance(current_user, Admin): return redirect(url_for('main.index'))

    try:
        active_session = GameSession.query.filter_by(is_active=True).first()
        if active_session:
            active_session.is_active = False
            active_session.current_minigame_id = None
            event = GameEvent(game_session_id=active_session.id, event_type="game_session_ended", description="Spielsitzung durch Admin zurückgesetzt.")
            db.session.add(event)
            print(f"Spielsitzung ID {active_session.id} als inaktiv markiert."); sys.stdout.flush()
        else:
            print("Keine aktive Spielsitzung zum Zurücksetzen gefunden."); sys.stdout.flush()

        current_video_minigame_data = None
        
        db.session.commit()
        flash('Spielstatus erfolgreich zurückgesetzt. Aktive Sitzung beendet.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Zurücksetzen des Spielstatus: {e}', 'danger')
        print(f"FEHLER beim reset_game_state: {e}"); sys.stdout.flush()
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/init_chars')
@login_required
def init_chars():
    if not isinstance(current_user, Admin):
        flash('Nur Admins können auf diese Seite zugreifen.', 'warning')
        return redirect(url_for('main.index'))
    from .init_characters import initialize_characters 
    initialize_characters() 
    flash("Charaktere initialisiert/überprüft.", "info")
    return redirect(url_for('admin.admin_dashboard'))
