# app/admin/routes.py
import sys
import os
import random
import json
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, g, jsonify, make_response
from flask_login import login_user, logout_user, login_required, current_user
from ..models import (Admin, Team, Character, GameSession, GameEvent, MinigameFolder, GameRound, 
                     QuestionResponse, FieldConfiguration, WelcomeSession, PlayerRegistration, db)
from ..forms import (AdminLoginForm, CreateTeamForm, EditTeamForm, SetNextMinigameForm, 
                     AdminConfirmPasswordForm, CreateMinigameFolderForm, EditMinigameFolderForm,
                     CreateGameRoundForm, EditGameRoundForm, FolderMinigameForm, EditFolderMinigameForm,
                     DeleteConfirmationForm, CreateQuestionForm, EditQuestionForm,
                     FieldConfigurationForm, FieldPreviewForm, FieldImportExportForm, FieldBulkEditForm)
from .init_characters import initialize_characters
from .minigame_utils import (ensure_minigame_folders_exist, create_minigame_folder_if_not_exists,
                            delete_minigame_folder, get_minigames_from_folder, add_minigame_to_folder,
                            update_minigame_in_folder, delete_minigame_from_folder, get_minigame_from_folder,
                            get_random_minigame_from_folder, list_available_folders, update_folder_info,
                            get_questions_from_folder, add_question_to_folder, get_question_from_folder,
                            get_all_content_from_folder, get_random_content_from_folder, get_played_count_for_folder,
                            get_available_content_from_folder, mark_content_as_played, reset_played_content_for_session,
                            save_round_to_filesystem, backup_all_rounds_before_db_reset, restore_rounds_to_database,
                            load_rounds_from_filesystem, delete_round_from_filesystem)

# NEU: FELD-MANAGEMENT IMPORTS
from .field_config import (
    get_field_type_color_mapping, get_field_preview_data, create_default_field_config,
    update_field_config, get_frequency_type_options, get_field_type_templates,
    export_field_configurations, import_field_configurations, reset_to_default_configurations,
    validate_field_conflicts, get_field_usage_statistics
)

# SONDERFELD-LOGIK IMPORT
from app.game_logic.special_fields import (
    handle_special_field_action, 
    check_barrier_release, 
    get_field_type_at_position,
    get_all_special_field_positions,
    get_field_statistics
)

admin_bp = Blueprint('admin', __name__, template_folder='../templates/admin', url_prefix='/admin')

def get_or_create_active_session():
    active_session = GameSession.query.filter_by(is_active=True).first()
    if not active_session:
        active_round = GameRound.get_active_round()
        
        active_session = GameSession(
            is_active=True, 
            current_phase='SETUP_MINIGAME',
            game_round_id=active_round.id if active_round else None,
            played_content_ids=''  # Initialisiere mit leerem String
        )
        db.session.add(active_session)
        db.session.flush() 

        event = GameEvent(
            game_session_id=active_session.id,
            event_type="game_session_started",
            description=f"Neue Spielsitzung gestartet{f' für Runde {active_round.name}' if active_round else ''}."
        )
        db.session.add(event)
        db.session.commit() 
    return active_session

def calculate_automatic_placements():
    """Berechnet automatische Platzierungen basierend auf Antwort-Reihenfolge und Korrektheit"""
    active_session = GameSession.query.filter_by(is_active=True).first()
    if not active_session or not active_session.current_question_id:
        return

    # Alle Antworten für die aktuelle Frage
    responses = QuestionResponse.query.filter_by(
        game_session_id=active_session.id,
        question_id=active_session.current_question_id
    ).order_by(QuestionResponse.answered_at).all()

    if not responses:
        return

    # Sortiere nach Korrektheit (richtig zuerst) und dann nach Antwortzeit
    correct_responses = [r for r in responses if r.is_correct]
    incorrect_responses = [r for r in responses if not r.is_correct]

    # Setze Platzierungen
    placement = 1
    
    # Erst die richtigen Antworten in zeitlicher Reihenfolge
    for response in correct_responses:
        response.team.minigame_placement = placement
        current_app.logger.info(f"Team {response.team.name} erhält Platzierung {placement} (richtige Antwort)")
        placement += 1

    # Dann die falschen Antworten (bekommen keinen Bonus-Würfel)
    for response in incorrect_responses:
        response.team.minigame_placement = placement
        current_app.logger.info(f"Team {response.team.name} erhält Platzierung {placement} (falsche Antwort)")
        placement += 1

    # Teams die nicht geantwortet haben bekommen letzte Plätze
    all_teams = Team.query.all()
    answered_team_ids = {r.team_id for r in responses}
    
    for team in all_teams:
        if team.id not in answered_team_ids:
            team.minigame_placement = placement
            current_app.logger.info(f"Team {team.name} erhält Platzierung {placement} (keine Antwort)")
            placement += 1

    # VERBESSERT: Setze Bonus-Würfel für Teams mit richtigen Antworten
    bonus_config = current_app.config.get('PLACEMENT_BONUS_DICE', {1: 6, 2: 4, 3: 2})
    
    # Erst alle Bonus-Würfel zurücksetzen
    for team in all_teams:
        team.bonus_dice_sides = 0
    
    # Dann nur für Teams mit richtigen Antworten setzen
    correct_team_ids = {r.team_id for r in correct_responses}
    
    for team in all_teams:
        if team.minigame_placement and team.minigame_placement in bonus_config:
            # Nur wenn das Team eine richtige Antwort gegeben hat
            if team.id in correct_team_ids:
                team.bonus_dice_sides = bonus_config[team.minigame_placement]
                current_app.logger.info(f"Team {team.name} (Platz {team.minigame_placement}) erhält Bonus-Würfel: 1-{team.bonus_dice_sides}")
            else:
                team.bonus_dice_sides = 0
                current_app.logger.info(f"Team {team.name} (Platz {team.minigame_placement}) erhält keinen Bonus-Würfel (falsche/keine Antwort)")
        else:
            team.bonus_dice_sides = 0

    db.session.commit()

@admin_bp.route('/', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if not isinstance(current_user, Admin):
        flash('Zugriff verweigert. Nur Admins können das Admin Dashboard sehen.', 'danger')
        return redirect(url_for('main.index'))

    active_session = get_or_create_active_session()
    teams = Team.query.order_by(Team.name).all()

    active_round = GameRound.get_active_round()
    available_folders = MinigameFolder.query.order_by(MinigameFolder.name).all()
    available_rounds = GameRound.query.order_by(GameRound.name).all()

    set_minigame_form = SetNextMinigameForm()
    
    # Befülle Ordner-Inhalte falls aktive Runde vorhanden
    if active_round and active_round.minigame_folder:
        content = get_all_content_from_folder(active_round.minigame_folder.folder_path)
        choices = [('', '-- Wähle aus Ordner --')]
        
        # Markiere bereits gespielte Inhalte
        played_ids = active_session.get_played_content_ids()
        
        for mg in content['games']:
            label = f"🎮 {mg['name']}"
            if mg['id'] in played_ids:
                label += " (bereits gespielt)"
            choices.append((mg['id'], label))
        
        for question in content['questions']:
            label = f"❓ {question['name']}"
            if question['id'] in played_ids:
                label += " (bereits gespielt)"
            choices.append((question['id'], label))
            
        set_minigame_form.selected_folder_minigame_id.choices = choices
    
    confirm_reset_form = AdminConfirmPasswordForm()

    # Zusätzliche Informationen für das Dashboard
    played_stats = None
    if active_round and active_round.minigame_folder:
        played_stats = get_played_count_for_folder(
            active_round.minigame_folder.folder_path, 
            active_session.get_played_content_ids()
        )

    # NEU: Feld-Konfiguration Statistiken für Dashboard
    field_stats = get_field_statistics()
    field_color_mapping = get_field_type_color_mapping()

    template_data = {
        "teams": teams,
        "active_session": active_session,
        "active_round": active_round,
        "available_folders": available_folders,
        "available_rounds": available_rounds,
        "current_minigame_name": active_session.current_minigame_name,
        "current_minigame_description": active_session.current_minigame_description,
        "current_phase": active_session.current_phase,
        "set_minigame_form": set_minigame_form,
        "confirm_reset_form": confirm_reset_form,
        "played_stats": played_stats,
        # NEU: Feld-Management Daten
        "field_stats": field_stats,
        "field_color_mapping": field_color_mapping
    }
    
    return render_template('admin.html', **template_data)

@admin_bp.route('/open-board')
@login_required
def open_board():
    """Route für 'Spielbrett öffnen' - prüft ob Teams existieren"""
    if not isinstance(current_user, Admin):
        flash('Zugriff verweigert. Nur Admins können das Spielbrett öffnen.', 'danger')
        return redirect(url_for('main.index'))
    
    # Prüfe ob Teams registriert sind
    teams_count = Team.query.count()
    if teams_count == 0:
        # Keine Teams -> zur Welcome-Seite umleiten
        flash('Noch keine Teams registriert. Nutze das Welcome-System, um Teams zu erstellen.', 'info')
        return redirect(url_for('main.welcome'))
    
    # Teams vorhanden -> zum Spielbrett weiterleiten
    return redirect(url_for('main.game_board'))

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated and isinstance(current_user, Admin):
        return redirect(url_for('admin.admin_dashboard'))
    
    form = AdminLoginForm()
    if form.validate_on_submit():
        admin = Admin.query.filter_by(username=form.username.data).first()
        if admin and admin.check_password(form.password.data):
            login_user(admin, remember=True)  # Remember session für längere Laufzeit
            flash('Admin erfolgreich eingeloggt.', 'success')
            return redirect(url_for('admin.admin_dashboard'))
        else:
            flash('Ungültiger Benutzername oder Passwort.', 'danger')
    return render_template('admin_login.html', title='Admin Login', form=form)

@admin_bp.route('/logout')
@login_required
def logout():
    if not isinstance(current_user, Admin):
        flash('Nur Admins können sich hier ausloggen.', 'warning')
        return redirect(url_for('main.index')) 
    logout_user()
    flash('Admin erfolgreich ausgeloggt.', 'info')
    return redirect(url_for('main.index')) 

@admin_bp.route('/admin_roll_dice', methods=['POST'])
@login_required
def admin_roll_dice():
    if not isinstance(current_user, Admin):
        return jsonify({"success": False, "error": "Nur Admins können würfeln."}), 403

    try:
        active_session = GameSession.query.filter_by(is_active=True).first()
        if not active_session:
            return jsonify({"success": False, "error": "Keine aktive Spielsitzung."}), 404

        if active_session.current_phase != 'DICE_ROLLING':
            return jsonify({"success": False, "error": "Es ist nicht die Würfelphase."}), 403
        
        current_team_id = active_session.current_team_turn_id
        if not current_team_id:
            return jsonify({"success": False, "error": "Kein Team für aktuellen Zug festgelegt."}), 404

        team = Team.query.get(current_team_id)
        if not team:
            return jsonify({"success": False, "error": "Aktuelles Team nicht gefunden."}), 404

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
                    related_team_id=team.id
                ).filter(
                    GameEvent.event_type.in_(['team_dice_roll', 'admin_dice_roll'])
                ).count()
                
                # Ermittle welche "Runde" wir sind (wie oft jedes Team gewürfelt haben sollte)
                expected_round = (all_dice_events_in_session // total_teams) + 1
                
                # Wenn das Team bereits in dieser Runde gewürfelt hat, verweigern
                if team_dice_events >= expected_round:
                    if team.id != active_session.current_team_turn_id:
                        return jsonify({"success": False, "error": f"Team {team.name} hat bereits in dieser Runde gewürfelt."}), 403
                        
            except (ValueError, ZeroDivisionError) as e:
                current_app.logger.warning(f"Fehler bei Würfel-Validierung: {e}")
                pass  # Bei Fehlern in der Logik, erlaube Würfeln

        # SONDERFELD: Prüfe ob Team blockiert ist (Sperren-Feld)
        standard_dice_roll = random.randint(1, 6)
        bonus_dice_roll = 0
        
        current_app.logger.info(f"Team {team.name} würfelt - Bonus-Würfel-Seiten: {team.bonus_dice_sides}")
        
        if team.bonus_dice_sides and team.bonus_dice_sides > 0:
            bonus_dice_roll = random.randint(1, team.bonus_dice_sides)
            current_app.logger.info(f"Team {team.name} erhält Bonus-Würfel: {bonus_dice_roll} (von 1-{team.bonus_dice_sides})")
        else:
            current_app.logger.info(f"Team {team.name} erhält keinen Bonus-Würfel")
        
        total_roll = standard_dice_roll + bonus_dice_roll
        old_position = team.current_position
        new_position = old_position  # Default: keine Bewegung
        special_field_result = None
        barrier_check_result = None

        # SONDERFELD: Prüfe Sperren-Status
        if team.is_blocked:
            # Team ist blockiert - prüfe ob es freikommt
            barrier_check_result = check_barrier_release(team, standard_dice_roll, active_session, bonus_dice_roll)
            
            if barrier_check_result['released']:
                # Team ist befreit und kann sich normal bewegen
                max_field_index = current_app.config.get('MAX_BOARD_FIELDS', 72)
                new_position = min(team.current_position + total_roll, max_field_index)
                team.current_position = new_position
                
                # Prüfe Sonderfeld-Aktion nach Bewegung
                all_teams = Team.query.all()
                dice_info = {
                    "old_position": old_position,
                    "new_position": new_position,
                    "dice_roll": standard_dice_roll,
                    "bonus_roll": bonus_dice_roll,
                    "total_roll": total_roll
                }
                special_field_result = handle_special_field_action(team, all_teams, active_session, dice_info)
            else:
                # Team bleibt blockiert, keine Bewegung
                new_position = old_position
        else:
            # Team ist nicht blockiert - normale Bewegung
            max_field_index = current_app.config.get('MAX_BOARD_FIELDS', 72)
            new_position = min(team.current_position + total_roll, max_field_index)
            team.current_position = new_position
            
            # SONDERFELD: Prüfe Sonderfeld-Aktion nach Bewegung
            all_teams = Team.query.all()
            dice_info = {
                "old_position": old_position,
                "new_position": new_position,
                "dice_roll": standard_dice_roll,
                "bonus_roll": bonus_dice_roll,
                "total_roll": total_roll
            }
            special_field_result = handle_special_field_action(team, all_teams, active_session, dice_info)

        # Event für den Würfelwurf erstellen
        event_description = f"Admin würfelte für Team {team.name}: {standard_dice_roll}"
        if bonus_dice_roll > 0:
            event_description += f" (Bonus: {bonus_dice_roll}, Gesamt: {total_roll})"
        
        if team.is_blocked and (not barrier_check_result or not barrier_check_result.get('released', False)):
            event_description += f" - BLOCKIERT: Konnte sich nicht befreien."
        else:
            event_description += f" und bewegte sich von Feld {old_position} zu Feld {new_position}."
        
        dice_event = GameEvent(
            game_session_id=active_session.id,
            event_type="admin_dice_roll",
            description=event_description,
            related_team_id=team.id,
            data_json=json.dumps({
                "standard_roll": standard_dice_roll,
                "bonus_roll": bonus_dice_roll,
                "total_roll": total_roll,
                "old_position": old_position,
                "new_position": new_position,
                "rolled_by": "admin",
                "was_blocked": team.is_blocked if barrier_check_result else False,
                "barrier_released": barrier_check_result.get('released', False) if barrier_check_result else False
            })
        )
        db.session.add(dice_event)

        # Nächstes Team ermitteln
        dice_order_ids_str = active_session.dice_roll_order
        if not dice_order_ids_str: 
            db.session.rollback()
            current_app.logger.error("Würfelreihenfolge ist leer in der aktiven Session.")
            return jsonify({"success": False, "error": "Fehler: Würfelreihenfolge nicht gesetzt."}), 500

        dice_order_ids_int = [int(tid) for tid in dice_order_ids_str.split(',') if tid.isdigit()]
        
        current_team_index_in_order = -1
        if team.id in dice_order_ids_int:
            current_team_index_in_order = dice_order_ids_int.index(team.id)
        else:
            db.session.rollback()
            current_app.logger.error(f"Team {team.id} nicht in Würfelreihenfolge {dice_order_ids_int} gefunden.")
            return jsonify({"success": False, "error": "Fehler in der Würfelreihenfolge (Team nicht gefunden)."}), 500

        next_team_name = None 
        if current_team_index_in_order < len(dice_order_ids_int) - 1:
            active_session.current_team_turn_id = dice_order_ids_int[current_team_index_in_order + 1]
            next_team = Team.query.get(active_session.current_team_turn_id)
            next_team_name = next_team.name if next_team else "Unbekannt"
        else:
            active_session.current_phase = 'ROUND_OVER'
            active_session.current_team_turn_id = None 
            
            # WICHTIG: Erstelle Event für Rundenende
            round_end_event = GameEvent(
                game_session_id=active_session.id,
                event_type="dice_round_ended",
                description="Würfelrunde beendet (Admin) - alle Teams haben gewürfelt"
            )
            db.session.add(round_end_event)
            
            # VERBESSERT: Nur Bonus-Würfel zurücksetzen, Platzierungen beibehalten für Statistiken
            all_teams_in_db = Team.query.all()
            for t_obj in all_teams_in_db:
                current_app.logger.info(f"Runde beendet - Bonus-Würfel für Team {t_obj.name} zurückgesetzt (war: {t_obj.bonus_dice_sides})")
                t_obj.bonus_dice_sides = 0
                # Platzierungen NICHT zurücksetzen - die bleiben für Statistiken
            
            round_over_event = GameEvent(
                game_session_id=active_session.id,
                event_type="dice_round_finished",
                description="Admin beendete die Würfelrunde. Alle Teams haben gewürfelt."
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
            "old_position": old_position,
            "new_position": team.current_position,  # Aktuelle finale Position (nach Special Field)
            "next_team_id": active_session.current_team_turn_id,
            "next_team_name": next_team_name, 
            "new_phase": active_session.current_phase
        }

        # SONDERFELD: Füge Sonderfeld-Informationen hinzu
        if barrier_check_result:
            response_data["barrier_check"] = barrier_check_result
            
        if special_field_result and special_field_result.get("success"):
            response_data["special_field"] = special_field_result

        return jsonify(response_data)

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Schwerer Fehler in admin_roll_dice: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Ein interner Serverfehler beim Würfeln ist aufgetreten.", "details": str(e)}), 500

@admin_bp.route('/abort-minigame', methods=['POST'])
@login_required
def abort_current_minigame():
    """Aktuelles Minigame/Frage abbrechen - zurück zur Admin-Auswahl"""
    if not isinstance(current_user, Admin):
        return jsonify({"success": False, "error": "Nur Admins können Minigames abbrechen."}), 403
    
    try:
        # Aktive Sitzung finden
        active_session = GameSession.query.filter_by(is_active=True).first()
        if not active_session:
            return jsonify({"success": False, "error": "Keine aktive Spielsitzung gefunden."}), 404
        
        current_app.logger.info(f"Admin {current_user.username} bricht aktuelles Minigame ab (Session ID: {active_session.id})")
        
        # Nur die aktuelle Phase zurücksetzen, NICHT die Spielerpositionen
        old_phase = active_session.current_phase
        
        # Je nach aktueller Phase unterschiedlich reagieren
        if active_session.current_phase in ['QUESTION_ACTIVE', 'MINIGAME_RESULTS']:
            # Zurück zu SETUP_MINIGAME für Admin-Auswahl ("Inhalt festlegen")
            active_session.current_phase = 'SETUP_MINIGAME'
            # Team-Turn zurücksetzen damit Admin neues Minigame starten kann
            active_session.current_team_turn_id = None
            current_app.logger.info(f"Phase geändert von {old_phase} zu SETUP_MINIGAME - Admin kann neues Minigame auswählen")
            
        elif active_session.current_phase == 'DICE_ROLLING':
            # Bereits in Würfelphase - nichts zu tun
            current_app.logger.info("Bereits in DICE_ROLLING Phase - kein Minigame aktiv")
            return jsonify({"success": False, "error": "Kein aktives Minigame zum Abbrechen gefunden."})
            
        else:
            # Andere Phasen - zurück zu SETUP_MINIGAME
            active_session.current_phase = 'SETUP_MINIGAME'
            active_session.current_team_turn_id = None
            current_app.logger.info(f"Phase geändert von {old_phase} zu SETUP_MINIGAME")
            
        # WICHTIG: Alle Fragen-Antworten für die aktuelle Session löschen
        # damit das Board aufhört auf Antworten zu warten
        QuestionResponse.query.filter_by(game_session_id=active_session.id).delete()
        current_app.logger.info("Alle Fragen-Antworten für Session gelöscht - Board stoppt Minigame")
        
        # Aktuelles Minigame KOMPLETT aus der Session entfernen
        active_session.current_minigame_content = None
        active_session.current_minigame_type = None
        active_session.current_minigame_name = None
        active_session.current_minigame_description = None
        active_session.current_question_id = None
        active_session.selected_folder_minigame_id = None
        current_app.logger.info("Aktuelles Minigame komplett aus Session entfernt")
        
        # Event für Minigame-Abbruch erstellen
        abort_event = GameEvent(
            game_session_id=active_session.id,
            event_type="minigame_aborted",
            description=f"Minigame/Frage wurde von Admin {current_user.username} abgebrochen (vorherige Phase: {old_phase})"
        )
        db.session.add(abort_event)
        
        # Änderungen speichern
        db.session.commit()
        
        current_app.logger.info("Minigame erfolgreich abgebrochen - zurück zur Admin-Auswahl")
        
        return jsonify({
            "success": True, 
            "message": "Minigame wurde abgebrochen. Admin kann neues Minigame auswählen.",
            "new_phase": active_session.current_phase
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Minigame-Abbruch: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Interner Serverfehler beim Minigame-Abbruch.", "details": str(e)}), 500

@admin_bp.route('/set_minigame', methods=['POST'])
@login_required
def set_minigame():
    if not isinstance(current_user, Admin):
        flash('Aktion nicht erlaubt.', 'danger')
        return redirect(url_for('main.index')) 

    active_session = get_or_create_active_session()
    form = SetNextMinigameForm(request.form)
    
    # Dynamische Befüllung der Form-Choices
    active_round = GameRound.get_active_round()
    if active_round and active_round.minigame_folder:
        content = get_all_content_from_folder(active_round.minigame_folder.folder_path)
        choices = [('', '-- Wähle aus Ordner --')]
        
        # Markiere bereits gespielte Inhalte
        played_ids = active_session.get_played_content_ids()
        
        for mg in content['games']:
            label = f"🎮 {mg['name']}"
            if mg['id'] in played_ids:
                label += " (bereits gespielt)"
            choices.append((mg['id'], label))
        
        for question in content['questions']:
            label = f"❓ {question['name']}"
            if question['id'] in played_ids:
                label += " (bereits gespielt)"
            choices.append((question['id'], label))
            
        form.selected_folder_minigame_id.choices = choices

    if not form.validate_on_submit():
        flash('Formular-Validierung fehlgeschlagen.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    minigame_source = form.minigame_source.data
    current_app.logger.info(f"DEBUG set_minigame: minigame_source='{minigame_source}'")
    minigame_set = False

    try:
        if minigame_source == 'manual':
            # Manuelle Eingabe - kein Tracking nötig
            manual_name = form.minigame_name.data
            manual_description = form.minigame_description.data
            player_count = form.player_count.data or 'all'
            
            if manual_name and manual_description:
                current_app.logger.info(f"DEBUG set_minigame: Setting minigame name='{manual_name}', description='{manual_description}'")
                active_session.current_minigame_name = manual_name
                active_session.current_minigame_description = manual_description
                current_app.logger.info(f"DEBUG set_minigame: After setting - session.current_minigame_name='{active_session.current_minigame_name}'")
                active_session.current_player_count = player_count
                active_session.selected_folder_minigame_id = None
                active_session.current_question_id = None
                active_session.minigame_source = 'manual'
                
                # Zufällige Spielerauswahl bei numerischen Werten oder "ganzes Team"
                if player_count.isdigit() or player_count == "all":
                    # Stelle sicher, dass die Teams mit aktuellen Daten geladen werden
                    # BUGFIX: Commit session changes before expire_all() to prevent data loss
                    db.session.commit()
                    db.session.expire_all()
                    teams = Team.query.all()
                    selected_players = active_session.select_random_players(teams, player_count)
                    
                    # Flash-Nachricht mit ausgewählten Spielern
                    player_info = []
                    for team_id, players in selected_players.items():
                        team = Team.query.get(int(team_id))
                        if team and players:
                            player_info.append(f"{team.name}: {', '.join(players)}")
                    
                    selection_type = "Ganze Teams" if player_count == "all" else f"{player_count} Spieler pro Team"
                    flash_msg = f"Inhalt '{manual_name}' gesetzt ({selection_type}). Ausgewählte Spieler: " + " | ".join(player_info)
                    flash(flash_msg, 'info')
                else:
                    # Spieleranzahl für Flash-Nachricht
                    player_display = dict(form.player_count.choices).get(player_count, player_count)
                    flash(f"Inhalt '{manual_name}' manuell gesetzt. Spieleranzahl: {player_display}", 'info')
                
                minigame_set = True
            else:
                flash('Bitte Name und Beschreibung für den manuellen Inhalt angeben.', 'warning')

        elif minigame_source == 'direct_question':
            # Direkte Fragen-Erstellung
            question_name = form.minigame_name.data or "Spontane Frage"
            question_text = form.question_text.data
            question_type = form.question_type.data
            
            if question_text:
                # Erstelle temporäre Frage (ohne in Ordner zu speichern)
                question_id = str(uuid.uuid4())[:8]
                
                question_data = {
                    'id': question_id,
                    'name': question_name,
                    'description': form.minigame_description.data or '',
                    'type': 'question',
                    'question_text': question_text,
                    'question_type': question_type,
                    'created_at': datetime.utcnow().isoformat()
                }
                
                if question_type == 'multiple_choice':
                    options = []
                    if form.option_1.data: options.append(form.option_1.data)
                    if form.option_2.data: options.append(form.option_2.data)
                    if form.option_3.data: options.append(form.option_3.data)
                    if form.option_4.data: options.append(form.option_4.data)
                    
                    if len(options) < 2:
                        flash('Mindestens 2 Antwortoptionen sind erforderlich.', 'warning')
                        return redirect(url_for('admin.admin_dashboard'))
                    
                    question_data['options'] = options
                    question_data['correct_option'] = form.correct_option.data
                    
                elif question_type == 'text_input':
                    if not form.correct_text.data:
                        flash('Korrekte Antwort ist bei Freitext-Fragen erforderlich.', 'warning')
                        return redirect(url_for('admin.admin_dashboard'))
                    
                    question_data['correct_text'] = form.correct_text.data
                
                # Speichere temporär in Session-Daten
                if active_round and active_round.minigame_folder:
                    add_question_to_folder(active_round.minigame_folder.folder_path, question_data)
                
                # Markiere als gespielt
                mark_content_as_played(active_session, question_id)
                
                active_session.current_minigame_name = question_name
                active_session.current_minigame_description = question_data['description']
                active_session.current_player_count = None  # Keine Spieleranzahl bei Fragen
                active_session.selected_folder_minigame_id = question_id
                active_session.current_question_id = question_id
                active_session.minigame_source = 'direct_question'
                
                flash(f"Direkte Frage '{question_name}' erstellt und aktiviert.", 'success')
                minigame_set = True
            else:
                flash('Bitte Fragetext eingeben.', 'warning')

        elif minigame_source == 'folder_random':
            # Zufällig aus Ordner - mit Tracking
            if active_round and active_round.minigame_folder:
                played_ids = active_session.get_played_content_ids()
                random_content = get_random_content_from_folder(
                    active_round.minigame_folder.folder_path, 
                    played_ids
                )
                
                if random_content:
                    # Markiere als gespielt
                    mark_content_as_played(active_session, random_content['id'])
                    
                    current_app.logger.info(f"DEBUG set_minigame folder_random: Setting minigame name='{random_content['name']}', description='{random_content.get('description', '')}'")
                    active_session.current_minigame_name = random_content['name']
                    active_session.current_minigame_description = random_content.get('description', '')
                    current_app.logger.info(f"DEBUG set_minigame folder_random: After setting - session.current_minigame_name='{active_session.current_minigame_name}'")
                    active_session.selected_folder_minigame_id = random_content['id']
                    active_session.minigame_source = 'folder_random'
                    
                    # Setze Spieleranzahl nur bei Minispielen, nicht bei Fragen
                    if random_content.get('type') != 'question':
                        # Verwende Spieleranzahl aus Minigame-Konfiguration, falls verfügbar
                        minigame_player_count = random_content.get('player_count')
                        form_player_count = form.player_count.data
                        
                        # Priorisiere Minigame-Konfiguration über Formular-Eingabe
                        # Gültige Werte: '1', '2', '3', '4', 'all'
                        valid_counts = ['1', '2', '3', '4', 'all']
                        if minigame_player_count and minigame_player_count in valid_counts:
                            player_count = minigame_player_count
                            current_app.logger.info(f"Random minigame - using player_count from config: {player_count}")
                        else:
                            player_count = form_player_count or 'all'
                            current_app.logger.info(f"Random minigame - using player_count from form: {player_count} (minigame config was: {minigame_player_count})")
                        
                        active_session.current_player_count = player_count
                    
                    # Check if all content has been played
                    stats = get_played_count_for_folder(
                        active_round.minigame_folder.folder_path, 
                        active_session.get_played_content_ids()
                    )
                    
                    if random_content.get('type') == 'question':
                        active_session.current_question_id = random_content['id']
                        active_session.current_player_count = None  # Keine Spieleranzahl bei Fragen
                        flash_msg = f"Zufällige Frage '{random_content['name']}' aus Ordner '{active_round.minigame_folder.name}' ausgewählt."
                    else:
                        active_session.current_question_id = None
                        # Spielerauswahl für Minispiele
                        if player_count.isdigit() or player_count == "all":
                            # Stelle sicher, dass die Teams mit aktuellen Daten geladen werden
                            # BUGFIX: Commit session changes before expire_all() to prevent data loss
                            db.session.commit()
                            db.session.expire_all()
                            teams = Team.query.all()
                            selected_players = active_session.select_random_players(teams, player_count)
                            selection_type = "Ganze Teams" if player_count == "all" else f"{player_count} Spieler pro Team"
                            config_source = " (aus Minigame-Konfiguration)" if minigame_player_count else " (aus Formular)"
                            flash_msg = f"Zufälliges Minispiel '{random_content['name']}' aus Ordner '{active_round.minigame_folder.name}' ausgewählt ({selection_type}{config_source})."
                        else:
                            flash_msg = f"Zufälliges Minispiel '{random_content['name']}' aus Ordner '{active_round.minigame_folder.name}' ausgewählt."
                    
                    if stats['remaining'] == 0:
                        flash_msg += f" Alle {stats['total']} Inhalte wurden gespielt!"
                    else:
                        flash_msg += f" ({stats['remaining']} von {stats['total']} noch verfügbar)"
                    
                    flash(flash_msg, 'info')
                    minigame_set = True
                else:
                    flash(f"Keine Inhalte im Ordner '{active_round.minigame_folder.name}' gefunden.", 'warning')
            else:
                flash('Keine aktive Runde oder Minigame-Ordner zugewiesen.', 'warning')

        elif minigame_source == 'folder_selected':
            # Aus Ordner auswählen - mit Tracking
            selected_id = form.selected_folder_minigame_id.data
            if selected_id and active_round and active_round.minigame_folder:
                selected_content = get_minigame_from_folder(active_round.minigame_folder.folder_path, selected_id)
                
                if selected_content:
                    # Markiere als gespielt
                    mark_content_as_played(active_session, selected_content['id'])
                    
                    current_app.logger.info(f"DEBUG set_minigame folder_selected: Setting minigame name='{selected_content['name']}', description='{selected_content.get('description', '')}'")
                    active_session.current_minigame_name = selected_content['name']
                    active_session.current_minigame_description = selected_content.get('description', '')
                    current_app.logger.info(f"DEBUG set_minigame folder_selected: After setting - session.current_minigame_name='{active_session.current_minigame_name}'")
                    active_session.selected_folder_minigame_id = selected_content['id']
                    active_session.minigame_source = 'folder_selected'
                    
                    if selected_content.get('type') == 'question':
                        active_session.current_question_id = selected_content['id']
                        active_session.current_player_count = None  # Keine Spieleranzahl bei Fragen
                        flash(f"Frage '{selected_content['name']}' aus Ordner ausgewählt.", 'info')
                    else:
                        active_session.current_question_id = None
                        # Verwende Spieleranzahl aus Minigame-Konfiguration, falls verfügbar
                        minigame_player_count = selected_content.get('player_count')
                        form_player_count = form.player_count.data
                        
                        # Priorisiere Minigame-Konfiguration über Formular-Eingabe
                        # Gültige Werte: '1', '2', '3', '4', 'all'
                        valid_counts = ['1', '2', '3', '4', 'all']
                        if minigame_player_count and minigame_player_count in valid_counts:
                            player_count = minigame_player_count
                            current_app.logger.info(f"Using player_count from minigame config: {player_count}")
                        else:
                            player_count = form_player_count or 'all'
                            current_app.logger.info(f"Using player_count from form: {player_count} (minigame config was: {minigame_player_count})")
                        
                        active_session.current_player_count = player_count
                        
                        if player_count.isdigit() or player_count == "all":
                            # Stelle sicher, dass die Teams mit aktuellen Daten geladen werden
                            # BUGFIX: Commit session changes before expire_all() to prevent data loss
                            db.session.commit()
                            db.session.expire_all()
                            teams = Team.query.all()
                            selected_players = active_session.select_random_players(teams, player_count)
                            selection_type = "Ganze Teams" if player_count == "all" else f"{player_count} Spieler pro Team"
                            config_source = " (aus Minigame-Konfiguration)" if minigame_player_count else " (aus Formular)"
                            flash(f"Minispiel '{selected_content['name']}' aus Ordner ausgewählt ({selection_type}{config_source}).", 'info')
                        else:
                            flash(f"Minispiel '{selected_content['name']}' aus Ordner ausgewählt.", 'info')
                    
                    minigame_set = True
                else:
                    flash('Ausgewählter Inhalt nicht im Ordner gefunden.', 'warning')
            else:
                flash('Bitte einen Inhalt aus dem Ordner auswählen.', 'warning')

        if minigame_set:
            # Setze Spielphase und reset Team-Platzierungen NUR bei Phasenwechsel
            if active_session.current_question_id:
                active_session.current_phase = 'QUESTION_ACTIVE'
            else:
                active_session.current_phase = 'MINIGAME_ANNOUNCED'
            
            # VERBESSERT: Nur Platzierungen zurücksetzen, nicht Bonus-Würfel (die werden erst beim Würfeln zurückgesetzt)
            teams_to_reset = Team.query.all()
            for t in teams_to_reset:
                t.minigame_placement = None
                # t.bonus_dice_sides NICHT hier zurücksetzen - das passiert erst nach dem Würfeln

            event = GameEvent(
                game_session_id=active_session.id,
                event_type="content_set",
                description=f"{'Frage' if active_session.current_question_id else 'Minispiel'} '{active_session.current_minigame_name}' wurde festgelegt (Quelle: {minigame_source}). Platzierungen zurückgesetzt.",
                data_json=f'{{"name": "{active_session.current_minigame_name}", "description": "{active_session.current_minigame_description}", "source": "{minigame_source}", "is_question": {bool(active_session.current_question_id)}}}'
            )
            db.session.add(event)
            current_app.logger.info(f"DEBUG set_minigame: Before commit - session.current_minigame_name='{active_session.current_minigame_name}'")
            db.session.commit()
            current_app.logger.info(f"DEBUG set_minigame: After commit - session.current_minigame_name='{active_session.current_minigame_name}'")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Setzen des Inhalts: {e}", exc_info=True)
        flash('Ein Fehler ist beim Setzen des Inhalts aufgetreten.', 'danger')

    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/end_question', methods=['POST'])
@login_required
def end_question():
    """Beendet die aktive Frage und berechnet automatische Platzierungen"""
    if not isinstance(current_user, Admin):
        flash('Aktion nicht erlaubt.', 'danger')
        return redirect(url_for('main.index'))
    
    active_session = GameSession.query.filter_by(is_active=True).first()
    if not active_session:
        flash('Keine aktive Spielsitzung gefunden.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))
    
    if active_session.current_phase != 'QUESTION_ACTIVE':
        flash('Keine aktive Frage zum Beenden gefunden.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))
    
    try:
        # Berechne automatische Platzierungen
        calculate_automatic_placements()
        
        # Wechsle zur Würfelphase
        active_session.current_phase = 'DICE_ROLLING'
        
        # WICHTIG: Markiere den Beginn einer neuen Würfelrunde
        new_round_event = GameEvent(
            game_session_id=active_session.id,
            event_type="dice_round_started",
            description="Neue Würfelrunde gestartet - alle Teams dürfen wieder würfeln"
        )
        db.session.add(new_round_event)
        
        # Erstelle Würfelreihenfolge basierend auf Platzierungen
        teams_by_placement = Team.query.filter(Team.minigame_placement.isnot(None)).order_by(Team.minigame_placement).all()
        if teams_by_placement:
            dice_order_ids = [str(team.id) for team in teams_by_placement]
            active_session.dice_roll_order = ",".join(dice_order_ids)
            active_session.current_team_turn_id = teams_by_placement[0].id
        
        # Reset Fragen-Daten
        active_session.current_question_id = None
        
        event = GameEvent(
            game_session_id=active_session.id,
            event_type="question_auto_completed",
            description=f"Frage '{active_session.current_minigame_name}' automatisch beendet und Platzierungen berechnet. Würfelrunde beginnt."
        )
        db.session.add(event)
        db.session.commit()
        
        flash(f"Frage '{active_session.current_minigame_name}' beendet. Platzierungen automatisch berechnet.", 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Beenden der Frage: {e}", exc_info=True)
        flash('Fehler beim Beenden der Frage.', 'danger')
    
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/api/question-responses')
@login_required
def question_responses_api():
    """API zum Abrufen der aktuellen Fragen-Antworten"""
    if not isinstance(current_user, Admin):
        return jsonify({"success": False, "error": "Nur Admins können Antworten einsehen."}), 403
    
    try:
        active_session = GameSession.query.filter_by(is_active=True).first()
        if not active_session or not active_session.current_question_id:
            return jsonify({
                "success": True,
                "responses": [],
                "message": "Keine aktive Frage"
            })
        
        responses = QuestionResponse.query.filter_by(
            game_session_id=active_session.id,
            question_id=active_session.current_question_id
        ).join(Team).all()
        
        formatted_responses = []
        for response in responses:
            answer_preview = ""
            if response.selected_option is not None:
                active_round = GameRound.get_active_round()
                if active_round and active_round.minigame_folder:
                    question_data = get_question_from_folder(active_round.minigame_folder.folder_path, response.question_id)
                    if question_data and question_data.get('options'):
                        options = question_data['options']
                        if 0 <= response.selected_option < len(options):
                            answer_preview = f"Option {response.selected_option + 1}: {options[response.selected_option][:30]}..."
                        else:
                            answer_preview = f"Option {response.selected_option + 1}"
                    else:
                        answer_preview = f"Option {response.selected_option + 1}"
            elif response.answer_text:
                answer_preview = response.answer_text[:50]
                if len(response.answer_text) > 50:
                    answer_preview += "..."
            else:
                answer_preview = "Keine Antwort"
            
            formatted_responses.append({
                "team_id": response.team_id,
                "team_name": response.team.name,
                "answer_preview": answer_preview,
                "is_correct": response.is_correct,
                "answered_at": response.answered_at.strftime('%H:%M:%S') if response.answered_at else None
            })
        
        formatted_responses.sort(key=lambda x: x['answered_at'] or '99:99:99')
        
        return jsonify({
            "success": True,
            "responses": formatted_responses,
            "total_responses": len(formatted_responses),
            "total_teams": Team.query.count(),
            "question_name": active_session.current_minigame_name
        })
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Laden der Fragen-Antworten: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Fehler beim Laden der Antworten"
        }), 500

@admin_bp.route('/record_placements', methods=['POST'])
@login_required
def record_placements():
    if not isinstance(current_user, Admin):
        flash('Aktion nicht erlaubt.', 'danger')
        return redirect(url_for('main.index')) 

    active_session = GameSession.query.filter_by(is_active=True).first()
    if not active_session or active_session.current_phase not in ['MINIGAME_ANNOUNCED']:
        flash('Platzierungen können nur nach Ankündigung eines Minispiels eingegeben werden.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))

    teams = Team.query.all()
    if not teams:
        flash('Keine Teams vorhanden, um Platzierungen einzutragen.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))
        
    placements = {} 
    
    valid_placements = True
    for team_obj_iter in teams: 
        placement_str = request.form.get(f'placement_team_{team_obj_iter.id}')
        if placement_str and placement_str.isdigit():
            placements[team_obj_iter.id] = int(placement_str)
        else:
            flash(f"Ungültige oder fehlende Platzierung für Team {team_obj_iter.name}.", 'danger')
            valid_placements = False
            break 
    
    if not valid_placements:
        return redirect(url_for('admin.admin_dashboard'))

    num_teams = len(teams)
    if len(set(placements.values())) != num_teams or not all(1 <= p <= num_teams for p in placements.values()):
        flash('Ungültige Platzierungen. Jede Platzierung von 1 bis zur Anzahl der Teams muss genau einmal vergeben werden.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    sorted_teams_by_placement = sorted(teams, key=lambda t: placements[t.id])
    
    dice_roll_order_ids = []
    for team_obj in sorted_teams_by_placement:
        placement = placements[team_obj.id]
        team_obj.minigame_placement = placement
        dice_roll_order_ids.append(str(team_obj.id))

        # VERBESSERT: Bonus-Würfel Logik mit Logging
        bonus_config = current_app.config.get('PLACEMENT_BONUS_DICE', {1: 6, 2: 4, 3: 2})
        bonus_dice = bonus_config.get(placement, 0)
        team_obj.bonus_dice_sides = bonus_dice
        
        current_app.logger.info(f"Manuelle Platzierung - Team {team_obj.name} (Platz {placement}) erhält Bonus-Würfel: 1-{bonus_dice}")
        
    active_session.dice_roll_order = ",".join(dice_roll_order_ids)
    active_session.current_team_turn_id = int(dice_roll_order_ids[0]) if dice_roll_order_ids else None
    active_session.current_phase = 'DICE_ROLLING'
    
    # WICHTIG: Markiere den Beginn einer neuen Würfelrunde
    new_round_event = GameEvent(
        game_session_id=active_session.id,
        event_type="dice_round_started",
        description="Neue Würfelrunde gestartet (manuelle Platzierungen) - alle Teams dürfen wieder würfeln"
    )
    db.session.add(new_round_event)
    
    active_session.current_question_id = None
    
    event_desc = f"Platzierungen für Minigame '{active_session.current_minigame_name}' festgelegt. Würfelreihenfolge: {active_session.dice_roll_order}"
    event_data = {f"team_{t.id}_placement": placements[t.id] for t in teams}
    event = GameEvent(
        game_session_id=active_session.id,
        event_type="placements_recorded",
        description=event_desc,
        data_json=str(event_data)
    )
    db.session.add(event)
    db.session.commit()
    
    flash('Platzierungen erfolgreich gespeichert. Würfelrunde beginnt.', 'success')
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/reset_game_state_confirmed', methods=['POST']) 
@login_required
def reset_game_state_confirmed():
    if not isinstance(current_user, Admin):
        flash('Aktion nicht erlaubt.', 'danger')
        return redirect(url_for('main.index')) 

    form = AdminConfirmPasswordForm(request.form)
    admin_user = Admin.query.get(current_user.id) 

    if form.validate_on_submit():
        if admin_user and admin_user.check_password(form.password.data):
            try:
                GameEvent.query.delete() 
                QuestionResponse.query.delete()
                GameSession.query.delete() 

                teams = Team.query.all()
                for team in teams:
                    team.minigame_placement = None
                    team.bonus_dice_sides = 0
                    team.current_position = 0
                    # SONDERFELD: Sonderfeld-Status zurücksetzen
                    team.reset_special_field_status()

                db.session.commit()
                flash('Spiel komplett zurückgesetzt (inkl. Positionen, Events, Fragen-Antworten, Session, Sonderfeld-Status). Eine neue Session wird beim nächsten Aufruf gestartet.', 'success')
                current_app.logger.info("Spiel komplett zurückgesetzt durch Admin.")
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Fehler beim kompletten Zurücksetzen des Spiels: {e}", exc_info=True)
                flash('Fehler beim Zurücksetzen des Spiels.', 'danger')
        else:
            flash('Falsches Admin-Passwort. Spiel nicht zurückgesetzt.', 'danger')
    else:
        flash('Passworteingabe für Reset ungültig oder fehlend.', 'warning')

    return redirect(url_for('admin.admin_dashboard'))

# Route zum Zurücksetzen der gespielten Inhalte
@admin_bp.route('/reset_played_content', methods=['POST'])
@login_required
def reset_played_content():
    if not isinstance(current_user, Admin):
        flash('Aktion nicht erlaubt.', 'danger')
        return redirect(url_for('main.index'))
    
    try:
        active_session = GameSession.query.filter_by(is_active=True).first()
        if active_session:
            reset_played_content_for_session(active_session)
            db.session.commit()
            
            event = GameEvent(
                game_session_id=active_session.id,
                event_type="played_content_reset",
                description="Admin hat die Liste der gespielten Inhalte zurückgesetzt. Alle Spiele sind wieder verfügbar."
            )
            db.session.add(event)
            db.session.commit()
            
            flash('Liste der gespielten Inhalte wurde zurückgesetzt. Alle Spiele sind wieder verfügbar.', 'success')
        else:
            flash('Keine aktive Spielsitzung gefunden.', 'warning')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Zurücksetzen der gespielten Inhalte: {e}", exc_info=True)
        flash('Fehler beim Zurücksetzen der gespielten Inhalte.', 'danger')
    
    return redirect(url_for('admin.admin_dashboard'))

# SONDERFELD: Route zum manuellen Freigeben von blockierten Teams
@admin_bp.route('/unblock_team/<int:team_id>', methods=['POST'])
@login_required
def unblock_team(team_id):
    if not isinstance(current_user, Admin):
        flash('Aktion nicht erlaubt.', 'danger')
        return redirect(url_for('main.index'))
    
    try:
        team = Team.query.get_or_404(team_id)
        active_session = GameSession.query.filter_by(is_active=True).first()
        
        if team.is_blocked:
            team.reset_special_field_status()
            
            if active_session:
                event = GameEvent(
                    game_session_id=active_session.id,
                    event_type="admin_team_unblocked",
                    description=f"Admin hat Team {team.name} manuell von der Sperre befreit.",
                    related_team_id=team.id
                )
                db.session.add(event)
            
            db.session.commit()
            flash(f'Team {team.name} wurde manuell von der Sperre befreit.', 'success')
        else:
            flash(f'Team {team.name} ist nicht blockiert.', 'info')
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Freigeben von Team {team_id}: {e}", exc_info=True)
        flash('Fehler beim Freigeben des Teams.', 'danger')
    
    return redirect(url_for('admin.admin_dashboard'))

# =============================================================================
# NEU: FELD-MANAGEMENT ROUTES
# =============================================================================

@admin_bp.route('/manage_fields')
@login_required
def manage_fields():
    """Hauptseite für Feld-Management"""
    if not isinstance(current_user, Admin):
        flash('Zugriff verweigert. Nur Admins können Felder verwalten.', 'danger')
        return redirect(url_for('main.index'))
    
    try:
        # Lade alle Feld-Konfigurationen
        field_configs = FieldConfiguration.query.order_by(FieldConfiguration.field_type).all()
        
        # Aktive Runde für Kontext
        active_round = GameRound.get_active_round()
        
        # Feld-Statistiken
        field_stats = get_field_statistics()
        
        # Farb-Mapping
        color_mapping = get_field_type_color_mapping()
        
        # Feld-Verteilungs-Vorschau
        preview_data = get_field_preview_data(73)
        
        # Nutzungsstatistiken
        usage_stats = get_field_usage_statistics()
        
        # Konflikte prüfen
        conflicts = validate_field_conflicts()
        
        return render_template('admin/manage_fields.html',
                             field_configs=field_configs,
                             active_round=active_round,
                             field_stats=field_stats,
                             color_mapping=color_mapping,
                             preview_data=preview_data,
                             usage_stats=usage_stats,
                             conflicts=conflicts,
                             frequency_options=get_frequency_type_options())
                             
    except Exception as e:
        current_app.logger.error(f"Fehler beim Laden der Feld-Verwaltung: {e}", exc_info=True)
        flash('Fehler beim Laden der Feld-Verwaltung.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/edit_field/<string:field_type>', methods=['GET', 'POST'])
@login_required
def edit_field(field_type):
    """Einzelfeld-Konfiguration bearbeiten"""
    if not isinstance(current_user, Admin):
        flash('Zugriff verweigert. Nur Admins können Felder bearbeiten.', 'danger')
        return redirect(url_for('main.index'))
    
    try:
        # Lade existierende Konfiguration oder erstelle neue
        config = FieldConfiguration.get_config_for_field(field_type)
        
        if not config:
            # Erstelle neue Konfiguration mit Standard-Werten
            templates = get_field_type_templates()
            if field_type in templates:
                template = templates[field_type]
                config = create_default_field_config(field_type, template['display_name'], **template)
            else:
                config = create_default_field_config(field_type, field_type.replace('_', ' ').title())
            
            db.session.add(config)
            db.session.commit()
            flash(f"Neue Konfiguration für '{field_type}' erstellt.", 'info')
        
        form = FieldConfigurationForm(field_type=field_type, obj=config)
        
        if form.validate_on_submit():
            # Debug logging
            current_app.logger.info(f"[EDIT_FIELD] Form validated for {field_type}")
            current_app.logger.info(f"[EDIT_FIELD] Form data: {form.data}")
            current_app.logger.info(f"[EDIT_FIELD] Request form data: {request.form}")
            
            # Aktualisiere Konfiguration
            updated_config = update_field_config(config.id, form.data)
            
            # Cache invalidieren
            from app.game_logic.special_fields import clear_field_distribution_cache
            clear_field_distribution_cache()
            
            db.session.commit()
            flash(f"Feld-Konfiguration für '{updated_config.display_name}' erfolgreich aktualisiert.", 'success')
            return redirect(url_for('admin.manage_fields'))
        
        # Log form errors if validation failed
        if form.errors:
            current_app.logger.warning(f"[EDIT_FIELD] Form validation failed for {field_type}")
            current_app.logger.warning(f"[EDIT_FIELD] Form errors: {form.errors}")
        
        # Lade Template-Informationen für Frontend
        templates = get_field_type_templates()
        template_info = templates.get(field_type, {})
        
        return render_template('admin/edit_field.html',
                             form=form,
                             config=config,
                             field_type=field_type,
                             template_info=template_info,
                             frequency_options=get_frequency_type_options())
                             
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Bearbeiten von Feld '{field_type}': {e}", exc_info=True)
        flash('Fehler beim Bearbeiten der Feld-Konfiguration.', 'danger')
        return redirect(url_for('admin.manage_fields'))

@admin_bp.route('/toggle_field/<string:field_type>', methods=['POST'])
@login_required
def toggle_field(field_type):
    """Toggle einzelne Feld-Konfiguration (AJAX-Endpunkt)"""
    print(f"[DEBUG] toggle_field called with field_type: {field_type}")
    if not isinstance(current_user, Admin):
        print(f"[DEBUG] Access denied - current_user is not Admin: {current_user}")
        return jsonify({"success": False, "error": "Zugriff verweigert"}), 403
    
    try:
        current_app.logger.info(f"Toggle field request for: {field_type}")
        
        # System-Felder vor Deaktivierung schützen
        system_fields = ['start', 'goal', 'normal']
        if field_type in system_fields:
            current_app.logger.warning(f"Attempt to toggle system field: {field_type}")
            return jsonify({
                "success": False, 
                "error": f"System-Feld '{field_type}' kann nicht deaktiviert werden."
            }), 400
        
        # Feld-Konfiguration laden oder erstellen
        current_app.logger.info(f"Looking for config for field: {field_type}")
        config = FieldConfiguration.get_config_for_field(field_type)
        
        if not config:
            current_app.logger.info(f"No config found for {field_type}, creating new one")
            # Erstelle neue Konfiguration falls nicht vorhanden
            from .field_config import create_default_field_config
            
            # Generiere lesbaren Display-Namen aus field_type
            display_name = field_type.replace('_', ' ').title()
            
            config = create_default_field_config(field_type, display_name)
            if not config:
                current_app.logger.error(f"Failed to create default config for {field_type}")
                return jsonify({
                    "success": False, 
                    "error": f"Konnte Konfiguration für '{field_type}' nicht erstellen."
                }), 500
            
            # Füge neue Konfiguration zur Datenbank-Session hinzu
            db.session.add(config)
            current_app.logger.info(f"Neue Feld-Konfiguration für '{field_type}' erstellt und zur Session hinzugefügt.")
        else:
            current_app.logger.info(f"Found existing config for {field_type}: enabled={config.is_enabled}")
        
        # Status umschalten
        old_status = config.is_enabled
        config.is_enabled = not old_status
        current_app.logger.info(f"Toggling {field_type} from {old_status} to {config.is_enabled}")
        
        # Cache invalidieren
        from app.game_logic.special_fields import clear_field_distribution_cache
        clear_field_distribution_cache()
        
        # Änderungen speichern
        current_app.logger.info(f"Committing changes for {field_type}")
        db.session.commit()
        current_app.logger.info(f"Successfully committed changes for {field_type}")
        
        action = "aktiviert" if config.is_enabled else "deaktiviert"
        return jsonify({
            "success": True,
            "message": f"Feld-Konfiguration '{config.display_name}' wurde {action}.",
            "field_type": field_type,
            "is_enabled": config.is_enabled,
            "display_name": config.display_name
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Umschalten von Feld '{field_type}': {e}", exc_info=True)
        return jsonify({
            "success": False, 
            "error": f"Fehler beim Umschalten der Feld-Konfiguration: {str(e)}"
        }), 500

@admin_bp.route('/field_preview')
@login_required
def field_preview():
    """Spielfeld-Vorschau mit aktuellen Konfigurationen"""
    if not isinstance(current_user, Admin):
        return jsonify({"success": False, "error": "Zugriff verweigert"}), 403
    
    try:
        form = FieldPreviewForm()
        max_fields = int(request.args.get('max_fields', 73))
        
        # Generiere Vorschau-Daten
        preview_data = get_field_preview_data(max_fields)
        
        # Feld-Statistiken
        field_stats = get_field_statistics()
        
        # Spezielle Feld-Positionen
        special_positions = get_all_special_field_positions(max_fields)
        
        # Farb-Mapping für Template
        color_mapping = get_field_type_color_mapping()
        
        # Konflikte prüfen
        conflicts = validate_field_conflicts()
        
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({
                "success": True,
                "preview_data": preview_data,
                "field_stats": field_stats,
                "special_positions": special_positions,
                "color_mapping": color_mapping
            })
        
        return render_template('admin/field_preview.html',
                             form=form,
                             preview_data=preview_data,
                             field_stats=field_stats,
                             special_positions=special_positions,
                             color_mapping=color_mapping,
                             conflicts=conflicts,
                             max_fields=max_fields)
                             
    except Exception as e:
        current_app.logger.error(f"Fehler bei der Feld-Vorschau: {e}", exc_info=True)
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({"success": False, "error": str(e)}), 500
        
        flash('Fehler bei der Feld-Vorschau.', 'danger')
        return redirect(url_for('admin.manage_fields'))

@admin_bp.route('/api/field_data')
def api_field_data():
    """Öffentliche API für Feld-Daten (für Game-Board)"""
    try:
        max_fields = int(request.args.get('max_fields', 73))
        
        # Generiere Vorschau-Daten
        from .field_config import get_field_preview_data
        from app.game_logic.special_fields import get_all_special_field_positions
        preview_data = get_field_preview_data(max_fields)
        
        # Spezielle Feld-Positionen
        special_positions = get_all_special_field_positions(max_fields)
        
        return jsonify({
            "success": True,
            "preview_data": preview_data,
            "special_positions": special_positions,
            "max_fields": max_fields
        })
        
    except Exception as e:
        current_app.logger.error(f"Fehler bei der öffentlichen Feld-API: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/import_export_fields', methods=['GET', 'POST'])
@login_required
def import_export_fields():
    """Import/Export von Feld-Konfigurationen"""
    if not isinstance(current_user, Admin):
        flash('Zugriff verweigert. Nur Admins können Konfigurationen importieren/exportieren.', 'danger')
        return redirect(url_for('main.index'))
    
    form = FieldImportExportForm()
    
    if request.method == 'POST':
        if form.import_submit.data and form.validate_on_submit():
            # Import-Funktionalität
            try:
                import_data = json.loads(form.import_data.data)
                result = import_field_configurations(import_data)
                
                if result['imported_count'] > 0:
                    flash(f"Erfolgreich {result['imported_count']} Konfigurationen importiert.", 'success')
                
                if result['errors']:
                    for error in result['errors']:
                        flash(f"Import-Fehler: {error}", 'warning')
                
                return redirect(url_for('admin.manage_fields'))
                
            except json.JSONDecodeError:
                flash('Ungültiges JSON-Format.', 'danger')
            except Exception as e:
                current_app.logger.error(f"Fehler beim Import: {e}", exc_info=True)
                flash('Fehler beim Importieren der Konfigurationen.', 'danger')
        
        elif form.export_submit.data:
            # Export-Funktionalität
            try:
                export_data = export_field_configurations()
                
                if form.export_format.data == 'json':
                    response = make_response(json.dumps(export_data, indent=2))
                    response.headers['Content-Type'] = 'application/json'
                    response.headers['Content-Disposition'] = 'attachment; filename=field_configurations.json'
                    return response
                
                elif form.export_format.data == 'csv':
                    # CSV-Export implementieren
                    import csv
                    from io import StringIO
                    
                    output = StringIO()
                    writer = csv.DictWriter(output, fieldnames=export_data[0].keys() if export_data else [])
                    writer.writeheader()
                    writer.writerows(export_data)
                    
                    response = make_response(output.getvalue())
                    response.headers['Content-Type'] = 'text/csv'
                    response.headers['Content-Disposition'] = 'attachment; filename=field_configurations.csv'
                    return response
                
                else:
                    flash('Unbekanntes Export-Format.', 'warning')
                    
            except Exception as e:
                current_app.logger.error(f"Fehler beim Export: {e}", exc_info=True)
                flash('Fehler beim Exportieren der Konfigurationen.', 'danger')
        
        elif form.reset_submit.data:
            # Reset auf Standard-Konfigurationen
            try:
                if reset_to_default_configurations():
                    flash('Alle Feld-Konfigurationen wurden auf Standard-Werte zurückgesetzt.', 'success')
                else:
                    flash('Fehler beim Zurücksetzen der Konfigurationen.', 'danger')
                
                return redirect(url_for('admin.manage_fields'))
                
            except Exception as e:
                current_app.logger.error(f"Fehler beim Reset: {e}", exc_info=True)
                flash('Fehler beim Zurücksetzen der Konfigurationen.', 'danger')
    
    # Bereite Export-Daten für Vorschau vor
    export_preview = None
    try:
        export_data = export_field_configurations()
        if export_data:
            export_preview = json.dumps(export_data[:3], indent=2)  # Zeige nur ersten 3 Einträge
            if len(export_data) > 3:
                export_preview += f"\n... und {len(export_data) - 3} weitere Konfigurationen"
    except Exception:
        pass
    
    return render_template('admin/import_export_fields.html',
                         form=form,
                         export_preview=export_preview,
                         total_configs=FieldConfiguration.query.count())

@admin_bp.route('/bulk_edit_fields', methods=['GET', 'POST'])
@login_required
def bulk_edit_fields():
    """Massen-Bearbeitung von Feld-Konfigurationen"""
    if not isinstance(current_user, Admin):
        flash('Zugriff verweigert. Nur Admins können Massen-Bearbeitungen durchführen.', 'danger')
        return redirect(url_for('main.index'))
    
    form = FieldBulkEditForm()
    
    if form.validate_on_submit():
        try:
            # Frontend sendet Feld-Typen (Strings), nicht IDs
            selected_field_types = form.selected_fields.data
            selected_configs = FieldConfiguration.query.filter(FieldConfiguration.field_type.in_(selected_field_types)).all()
            
            if not selected_configs:
                flash('Keine Felder für Bearbeitung ausgewählt.', 'warning')
                return redirect(url_for('admin.bulk_edit_fields'))
            
            action = form.action.data
            modified_count = 0
            
            if action == 'enable':
                for config in selected_configs:
                    config.is_enabled = True
                    modified_count += 1
                flash(f"{modified_count} Feld-Konfigurationen wurden aktiviert.", 'success')
                
            elif action == 'disable':
                for config in selected_configs:
                    config.is_enabled = False
                    modified_count += 1
                flash(f"{modified_count} Feld-Konfigurationen wurden deaktiviert.", 'success')
                
            elif action == 'change_frequency':
                if form.new_frequency_type.data and form.new_frequency_value.data:
                    for config in selected_configs:
                        config.frequency_type = form.new_frequency_type.data
                        config.frequency_value = form.new_frequency_value.data
                        modified_count += 1
                    flash(f"Häufigkeit für {modified_count} Feld-Konfigurationen geändert.", 'success')
                else:
                    flash('Neue Häufigkeits-Werte sind erforderlich.', 'warning')
                    
            elif action == 'change_colors':
                if form.new_color_hex.data:
                    for config in selected_configs:
                        config.color_hex = form.new_color_hex.data
                        if form.new_emission_hex.data:
                            config.emission_hex = form.new_emission_hex.data
                        modified_count += 1
                    flash(f"Farben für {modified_count} Feld-Konfigurationen geändert.", 'success')
                else:
                    flash('Neue Hauptfarbe ist erforderlich.', 'warning')
                    
            elif action == 'delete':
                for config in selected_configs:
                    # Prüfe ob Feld in aktiver Nutzung
                    if config.field_type in ['start', 'goal', 'normal']:
                        flash(f"Basis-Feld '{config.field_type}' kann nicht gelöscht werden.", 'warning')
                        continue
                    db.session.delete(config)
                    modified_count += 1
                
                if modified_count > 0:
                    flash(f"{modified_count} Feld-Konfigurationen wurden gelöscht.", 'success')
            
            # Cache invalidieren wenn Änderungen gemacht wurden
            if modified_count > 0:
                from app.game_logic.special_fields import clear_field_distribution_cache
                clear_field_distribution_cache()
            
            db.session.commit()
            return redirect(url_for('admin.manage_fields'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Fehler bei Massen-Bearbeitung: {e}", exc_info=True)
            flash('Fehler bei der Massen-Bearbeitung.', 'danger')
    
    return render_template('admin/bulk_edit_fields.html', form=form)

@admin_bp.route('/api/field_colors')
def api_field_colors():
    """API-Endpunkt für Feld-Farb-Mapping (für Frontend-Integration) - Öffentlich zugänglich"""
    
    try:
        color_mapping = get_field_type_color_mapping()
        return jsonify({
            "success": True,
            "color_mapping": color_mapping
        })
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Laden der Feld-Farben: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

# =============================================================================
# TEAM MANAGEMENT ROUTES (Bestehend)
# =============================================================================

@admin_bp.route('/create_team', methods=['GET', 'POST'])
@login_required
def create_team():
    if not isinstance(current_user, Admin): return redirect(url_for('main.index')) 
    form = CreateTeamForm()

    if form.validate_on_submit():
        existing_team = Team.query.filter_by(name=form.team_name.data).first()
        if existing_team:
            flash('Ein Team mit diesem Namen existiert bereits.', 'warning')
        else:
            team = Team(name=form.team_name.data)
            team.set_password(form.password.data)
            
            # Teammitglieder verarbeiten
            if form.members.data:
                # Normalisiere Spielernamen (unterstützt sowohl Komma- als auch Zeilenumbruch-getrennt)
                raw_members = form.members.data.replace('\n', ',')
                members_list = [m.strip() for m in raw_members.split(',') if m.strip()]
                team.members = ', '.join(members_list)
                
                # Erstelle PlayerRegistration Einträge für die Spieler
                welcome_session = WelcomeSession.get_active_session()
                if not welcome_session:
                    # Erstelle eine neue Session falls keine aktiv
                    welcome_session = WelcomeSession()
                    welcome_session.is_active = True
                    db.session.add(welcome_session)
                    db.session.flush()  # Um ID zu bekommen
                
                # Erstelle Registrierungen für alle Spieler
                for member_name in members_list:
                    # Prüfe ob Spieler bereits registriert ist
                    existing_player = PlayerRegistration.query.filter_by(player_name=member_name).first()
                    if not existing_player:
                        player_registration = PlayerRegistration(
                            welcome_session_id=welcome_session.id,
                            player_name=member_name,
                            assigned_team_id=None  # Wird nach Team-Erstellung gesetzt
                        )
                        db.session.add(player_registration)
            
            selected_character_id = form.character_id.data
            char = Character.query.get(selected_character_id) 
            if char:
                if char.is_selected:
                    flash(f'Charakter {char.name} ist bereits ausgewählt. Bitte einen anderen wählen.', 'warning')
                    return render_template('create_team.html', title='Team erstellen', form=form)
                
                team.character_id = char.id
                team.character_name = char.name 
                char.is_selected = True 
                db.session.add(char)
            
            db.session.add(team)
            db.session.flush()  # Um Team-ID zu bekommen
            
            # Aktualisiere PlayerRegistration Einträge mit Team-ID
            if form.members.data:
                raw_members = form.members.data.replace('\n', ',')
                members_list = [m.strip() for m in raw_members.split(',') if m.strip()]
                
                for member_name in members_list:
                    player_registration = PlayerRegistration.query.filter_by(
                        player_name=member_name,
                        assigned_team_id=None
                    ).first()
                    if player_registration:
                        player_registration.assigned_team_id = team.id
                        
                        # Kopiere Profilbild ins Team falls vorhanden
                        if player_registration.profile_image_path:
                            team.set_profile_image(member_name, player_registration.profile_image_path)
            
            # Setze welcome_password für die Klartext-Anzeige
            team.welcome_password = form.password.data
            
            db.session.commit()
            flash('Team erfolgreich erstellt.', 'success')
            return redirect(url_for('admin.admin_dashboard'))
    else:
        if request.method == 'POST':
            for fieldName, errorMessages in form.errors.items():
                for err in errorMessages:
                    field_label = fieldName
                    try:
                        field_label = getattr(form, fieldName).label.text
                    except AttributeError:
                        pass
                    flash(f"Fehler im Feld '{field_label}': {err}", 'danger')

    return render_template('create_team.html', title='Team erstellen', form=form)

@admin_bp.route('/edit_team/<int:team_id>', methods=['GET', 'POST'])
@login_required
def edit_team(team_id):
    if not isinstance(current_user, Admin): return redirect(url_for('main.index')) 
    team = Team.query.get_or_404(team_id)
    
    current_char_id_for_form = team.character_id if team.character_id else 0 
    
    form = EditTeamForm(original_team_name=team.name, current_character_id=current_char_id_for_form, obj=team if request.method == 'GET' else None)

    if form.validate_on_submit():
        if form.team_name.data != team.name: 
            existing_team_check = Team.query.filter(Team.id != team_id, Team.name == form.team_name.data).first()
            if existing_team_check:
                flash('Ein anderes Team mit diesem Namen existiert bereits.', 'warning')
                return render_template('edit_team.html', title='Team bearbeiten', form=form, team=team)
        
        team.name = form.team_name.data
        
        if form.password.data:
            team.set_password(form.password.data)
            team.welcome_password = form.password.data
        
        # Update Position und Dice Result
        team.current_position = form.current_position.data
        if form.last_dice_result.data is not None:
            team.last_dice_result = form.last_dice_result.data

        # Teammitglieder aktualisieren
        if form.members.data is not None:  # Auch leere Strings erlauben (zum Leeren)
            # Normalisiere Spielernamen (unterstützt sowohl Komma- als auch Zeilenumbruch-getrennt)
            raw_members = form.members.data.replace('\n', ',')
            members_list = [m.strip() for m in raw_members.split(',') if m.strip()]
            team.members = ', '.join(members_list) if members_list else None
            
            # Wenn sich die Spielerliste geändert hat, player_config aktualisieren
            # Entferne Einstellungen für Spieler, die nicht mehr im Team sind
            if team.player_config:
                current_config = team.get_player_config()
                updated_config = {}
                for player in members_list:
                    if player in current_config:
                        updated_config[player] = current_config[player]
                    # Neue Spieler erhalten Standardeinstellungen (können ausgelost werden)
                team.set_player_config(updated_config)

        new_character_id = form.character_id.data
        old_character_id = team.character_id

        if new_character_id != old_character_id:
            if old_character_id:
                old_char = Character.query.get(old_character_id)
                if old_char:
                    old_char.is_selected = False
                    db.session.add(old_char)
            
            if new_character_id: 
                new_char = Character.query.get(new_character_id)
                if new_char:
                    if new_char.is_selected and new_char.id != old_character_id:
                        flash(f"Charakter {new_char.name} ist bereits von einem anderen Team ausgewählt. Dies sollte nicht passieren.", "danger")
                        return render_template('edit_team.html', title='Team bearbeiten', form=form, team=team)
                    
                    team.character_id = new_char.id
                    team.character_name = new_char.name
                    new_char.is_selected = True
                    db.session.add(new_char)
                else:
                    team.character_id = None
                    team.character_name = None
            else:
                team.character_id = None
                team.character_name = None
        
        db.session.commit()
        flash('Team erfolgreich aktualisiert.', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    else:
        if request.method == 'POST':
            for fieldName, errorMessages in form.errors.items():
                for err in errorMessages:
                    field_label = fieldName
                    try:
                        field_label = getattr(form, fieldName).label.text
                    except AttributeError:
                        pass
                    flash(f"Fehler im Feld '{field_label}': {err}", 'danger')
        elif request.method == 'GET':
            form.team_name.data = team.name
            form.character_id.data = team.character_id

    # Alle Teams für Dropdown in Spieler-Zuordnung laden
    all_teams = Team.query.order_by(Team.name).all()
    return render_template('edit_team.html', title='Team bearbeiten', form=form, team=team, all_teams=all_teams)

@admin_bp.route('/add_player', methods=['GET', 'POST'])
@login_required
def add_player():
    if not isinstance(current_user, Admin): 
        return redirect(url_for('main.index'))
    
    from app.forms import AddPlayerForm
    form = AddPlayerForm()
    
    if form.validate_on_submit():
        team = Team.query.get_or_404(form.team_id.data)
        player_name = form.player_name.data.strip()
        
        # Prüfe ob Spieler bereits in einem Team ist
        existing_player = PlayerRegistration.query.filter_by(player_name=player_name).first()
        if existing_player:
            flash(f'Spieler "{player_name}" ist bereits registriert.', 'warning')
            return render_template('add_player.html', title='Spieler hinzufügen', form=form)
        
        # Erstelle neue Spielerregistrierung
        welcome_session = WelcomeSession.get_active_session()
        if not welcome_session:
            # Erstelle eine neue Session falls keine aktiv
            welcome_session = WelcomeSession()
            welcome_session.is_active = True
            db.session.add(welcome_session)
            db.session.commit()
        
        player_registration = PlayerRegistration(
            welcome_session_id=welcome_session.id,
            player_name=player_name,
            assigned_team_id=team.id
        )
        db.session.add(player_registration)
        
        # Füge Spieler auch zur Team-Mitgliederliste hinzu
        if team.members:
            current_members = [m.strip() for m in team.members.split(',') if m.strip()]
            if player_name not in current_members:
                current_members.append(player_name)
                team.members = ', '.join(current_members)
        else:
            team.members = player_name
        
        db.session.commit()
        flash(f'Spieler "{player_name}" wurde erfolgreich zu Team "{team.name}" hinzugefügt.', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    
    return render_template('add_player.html', title='Spieler hinzufügen', form=form)

@admin_bp.route('/api/update_player_selection_status/<int:team_id>', methods=['POST'])
@login_required
def update_player_selection_status(team_id):
    """AJAX-Route zum Aktualisieren des Auslosungs-Status eines Spielers"""
    if not isinstance(current_user, Admin):
        return jsonify({'success': False, 'message': 'Keine Berechtigung'}), 403
    
    try:
        team = Team.query.get_or_404(team_id)
        data = request.get_json()
        
        player_name = data.get('player_name')
        can_be_selected = data.get('can_be_selected', True)
        
        if not player_name:
            return jsonify({'success': False, 'message': 'Spielername fehlt'}), 400
        
        # Prüfe ob Spieler wirklich im Team ist
        if team.members:
            members_list = [m.strip() for m in team.members.split(',') if m.strip()]
            if player_name not in members_list:
                return jsonify({'success': False, 'message': 'Spieler nicht im Team gefunden'}), 400
        else:
            return jsonify({'success': False, 'message': 'Team hat keine Mitglieder'}), 400
        
        # Status aktualisieren
        team.update_player_selection_status(player_name, can_be_selected)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Auslosungs-Status für {player_name} aktualisiert',
            'player_name': player_name,
            'can_be_selected': can_be_selected
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Aktualisieren des Spieler-Status: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Ein Fehler ist aufgetreten'}), 500

@admin_bp.route('/delete_team/<int:team_id>', methods=['POST'])
@login_required
def delete_team(team_id):
    if not isinstance(current_user, Admin): return redirect(url_for('main.index')) 
    team = Team.query.get_or_404(team_id)
    
    if team.character_id:
        char = Character.query.get(team.character_id)
        if char:
            char.is_selected = False
            db.session.add(char)

    GameSession.query.filter_by(current_team_turn_id=team.id).update({"current_team_turn_id": None})
    GameEvent.query.filter_by(related_team_id=team.id).update({"related_team_id": None})
    QuestionResponse.query.filter_by(team_id=team.id).delete()
    
    active_sessions = GameSession.query.filter(GameSession.dice_roll_order.like(f"%{str(team.id)}%")).all()
    for sess in active_sessions:
        order_list = sess.dice_roll_order.split(',')
        team_id_str = str(team.id)
        if team_id_str in order_list:
            order_list.remove(team_id_str)
            sess.dice_roll_order = ",".join(order_list)
            if not order_list and sess.current_phase == 'DICE_ROLLING': 
                sess.current_phase = 'ROUND_OVER' 
                sess.current_team_turn_id = None

    db.session.delete(team)
    db.session.commit()
    flash('Team und zugehörige Referenzen erfolgreich gelöscht/aktualisiert.', 'success')
    return redirect(url_for('admin.admin_dashboard'))

# =============================================================================
# PLAYER MANAGEMENT AJAX ROUTES
# =============================================================================

@admin_bp.route('/update_player_name', methods=['POST'])
@login_required
def update_player_name():
    if not isinstance(current_user, Admin):
        return jsonify({'success': False, 'error': 'Nicht autorisiert'})
    
    try:
        data = request.get_json()
        player_id = data.get('player_id')
        new_name = data.get('new_name', '').strip()
        
        if not player_id or not new_name:
            return jsonify({'success': False, 'error': 'Ungültige Parameter'})
        
        if len(new_name) < 2:
            return jsonify({'success': False, 'error': 'Spielername muss mindestens 2 Zeichen lang sein'})
        
        player = PlayerRegistration.query.get_or_404(player_id)
        player.player_name = new_name
        db.session.commit()
        
        return jsonify({'success': True})
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Update des Spielernamens: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Serverfehler beim Speichern'})

def _update_team_members_from_registrations():
    """Aktualisiert die Team-Member-Listen basierend auf PlayerRegistration-Zuweisungen"""
    try:
        # Alle Teams holen
        teams = Team.query.all()
        
        # Für jedes Team die Members-Liste aktualisieren
        for team in teams:
            # Hole alle Spieler die diesem Team zugewiesen sind
            assigned_players = PlayerRegistration.query.filter_by(assigned_team_id=team.id).all()
            
            # Erstelle neue Members-Liste
            member_names = [player.name for player in assigned_players if player.name]
            
            # Aktualisiere das Team
            team.members = ', '.join(member_names) if member_names else None
            
        current_app.logger.info("Team-Member-Listen wurden aktualisiert")
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Aktualisieren der Team-Member-Listen: {e}", exc_info=True)
        raise

@admin_bp.route('/reassign_player', methods=['POST'])
@login_required
def reassign_player():
    if not isinstance(current_user, Admin):
        return jsonify({'success': False, 'error': 'Nicht autorisiert'})
    
    try:
        data = request.get_json()
        player_id = data.get('player_id')
        new_team_id = data.get('new_team_id')
        
        if not player_id:
            return jsonify({'success': False, 'error': 'Ungültige Spieler-ID'})
        
        player = PlayerRegistration.query.get_or_404(player_id)
        
        # Validiere neues Team (falls angegeben)
        if new_team_id and new_team_id != 0:
            new_team = Team.query.get(new_team_id)
            if not new_team:
                return jsonify({'success': False, 'error': 'Team nicht gefunden'})
            player.assigned_team_id = new_team_id
        else:
            # Kein Team zuweisen
            player.assigned_team_id = None
        
        # Aktualisiere die Team-Member-Listen nach der Zuweisung
        _update_team_members_from_registrations()
        
        db.session.commit()
        return jsonify({'success': True})
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler bei der Team-Zuweisung: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Serverfehler bei der Team-Zuweisung'})

@admin_bp.route('/init_chars')
@login_required
def init_chars():
    if not isinstance(current_user, Admin):
        flash('Nur Admins können auf diese Seite zugreifen.', 'warning')
        return redirect(url_for('main.index')) 
    
    try:
        initialize_characters() 
        flash("Charaktere initialisiert/überprüft.", "info")
    except Exception as e:
        current_app.logger.error(f"Fehler bei der Charakterinitialisierung: {e}", exc_info=True)
        flash(f"Fehler bei der Charakterinitialisierung: {str(e)}", "danger")
    return redirect(url_for('admin.admin_dashboard'))

# =============================================================================
# FOLDER & ROUND MANAGEMENT ROUTES (Bestehend)
# =============================================================================

@admin_bp.route('/manage_folders')
@login_required
def manage_folders():
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folders = MinigameFolder.query.order_by(MinigameFolder.name).all()
    return render_template('manage_folders.html', folders=folders)

@admin_bp.route('/sync_folders')
@login_required
def sync_folders():
    """Synchronisiert Minigame-Ordner zwischen Dateisystem und Datenbank"""
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    try:
        from app.admin.minigame_utils import sync_folders_to_database
        added_count = sync_folders_to_database()
        
        if added_count > 0:
            flash(f'Erfolgreich {added_count} neue Ordner zur Datenbank hinzugefügt.', 'success')
        else:
            flash('Alle Ordner sind bereits synchronisiert.', 'info')
            
    except Exception as e:
        current_app.logger.error(f"Fehler beim Synchronisieren der Ordner: {e}", exc_info=True)
        flash('Fehler beim Synchronisieren der Ordner.', 'danger')
    
    return redirect(url_for('admin.manage_folders'))

@admin_bp.route('/create_folder', methods=['GET', 'POST'])
@login_required
def create_folder():
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    form = CreateMinigameFolderForm()
    
    if form.validate_on_submit():
        try:
            # Erstelle Ordner im Dateisystem
            if create_minigame_folder_if_not_exists(form.name.data, form.description.data):
                # Erstelle Eintrag in der Datenbank
                folder = MinigameFolder(
                    name=form.name.data,
                    description=form.description.data,
                    folder_path=form.name.data
                )
                db.session.add(folder)
                db.session.commit()
                
                flash(f"Minigame-Ordner '{form.name.data}' erfolgreich erstellt.", 'success')
                return redirect(url_for('admin.manage_folders'))
            else:
                flash('Fehler beim Erstellen des Ordners im Dateisystem.', 'danger')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Fehler beim Erstellen des Ordners: {e}", exc_info=True)
            flash('Ein Fehler ist beim Erstellen des Ordners aufgetreten.', 'danger')
    
    return render_template('create_folder.html', form=form)

@admin_bp.route('/edit_folder/<int:folder_id>')
@login_required
def edit_folder(folder_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folder = MinigameFolder.query.get_or_404(folder_id)
    
    # Lade Inhalte aus dem Ordner
    content = get_all_content_from_folder(folder.folder_path)
    games = content['games']
    questions = content['questions']
    
    form = EditMinigameFolderForm(original_folder_name=folder.name, obj=folder)
    
    if request.method == 'POST' and form.validate_on_submit():
        try:
            # Aktualisiere nur die Beschreibung (Name kann nicht geändert werden)
            folder.description = form.description.data
            
            # Aktualisiere auch die JSON-Datei
            update_folder_info(folder.folder_path, form.description.data)
            
            db.session.commit()
            flash(f"Ordner '{folder.name}' erfolgreich aktualisiert.", 'success')
            return redirect(url_for('admin.manage_folders'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Fehler beim Aktualisieren des Ordners: {e}", exc_info=True)
            flash('Ein Fehler ist beim Aktualisieren des Ordners aufgetreten.', 'danger')
    
    return render_template('edit_folder.html', form=form, folder=folder, games=games, questions=questions)

@admin_bp.route('/delete_folder/<int:folder_id>', methods=['GET', 'POST'])
@login_required
def delete_folder(folder_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folder = MinigameFolder.query.get_or_404(folder_id)
    
    # Prüfe ob Ordner von Spielrunden verwendet wird
    using_rounds = GameRound.query.filter_by(minigame_folder_id=folder.id).all()
    
    form = DeleteConfirmationForm()
    
    if using_rounds:
        # Ordner kann nicht gelöscht werden
        minigames = get_minigames_from_folder(folder.folder_path)
        return render_template('delete_folder.html', 
                             folder=folder, 
                             using_rounds=using_rounds,
                             minigames=minigames,
                             form=form)
    
    if request.method == 'POST' and form.validate_on_submit():
        try:
            # Lösche aus Dateisystem
            if delete_minigame_folder(folder.folder_path):
                # Lösche aus Datenbank
                db.session.delete(folder)
                db.session.commit()
                
                flash(f"Ordner '{folder.name}' erfolgreich gelöscht.", 'success')
                return redirect(url_for('admin.manage_folders'))
            else:
                flash('Fehler beim Löschen des Ordners aus dem Dateisystem.', 'danger')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Fehler beim Löschen des Ordners: {e}", exc_info=True)
            flash('Ein Fehler ist beim Löschen des Ordners aufgetreten.', 'danger')
    
    # Lade Minispiele für die Anzeige
    minigames = get_minigames_from_folder(folder.folder_path)
    
    return render_template('delete_folder.html', 
                         folder=folder, 
                         using_rounds=using_rounds,
                         minigames=minigames,
                         form=form)

@admin_bp.route('/create_folder_minigame/<int:folder_id>', methods=['GET', 'POST'])
@login_required
def create_folder_minigame(folder_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folder = MinigameFolder.query.get_or_404(folder_id)
    form = FolderMinigameForm()
    
    if form.validate_on_submit():
        try:
            minigame_data = {
                'name': form.name.data,
                'description': form.description.data,
                'type': form.type.data,
                'player_count': form.player_count.data
            }
            
            if add_minigame_to_folder(folder.folder_path, minigame_data):
                flash(f"Minispiel '{form.name.data}' erfolgreich zu Ordner '{folder.name}' hinzugefügt.", 'success')
                return redirect(url_for('admin.edit_folder', folder_id=folder.id))
            else:
                flash('Fehler beim Hinzufügen des Minispiels.', 'danger')
        except Exception as e:
            current_app.logger.error(f"Fehler beim Erstellen des Minispiels: {e}", exc_info=True)
            flash('Ein Fehler ist beim Erstellen des Minispiels aufgetreten.', 'danger')
    
    return render_template('create_folder_minigame.html', form=form, folder=folder)

@admin_bp.route('/edit_folder_minigame/<int:folder_id>/<string:minigame_id>', methods=['GET', 'POST'])
@login_required
def edit_folder_minigame(folder_id, minigame_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folder = MinigameFolder.query.get_or_404(folder_id)
    minigame = get_minigame_from_folder(folder.folder_path, minigame_id)
    
    if not minigame:
        flash('Minispiel nicht gefunden.', 'danger')
        return redirect(url_for('admin.edit_folder', folder_id=folder.id))
    
    form = EditFolderMinigameForm(obj=type('obj', (object,), minigame)())
    
    if form.validate_on_submit():
        try:
            updated_data = {
                'name': form.name.data,
                'description': form.description.data,
                'type': form.type.data,
                'player_count': form.player_count.data
            }
            
            if update_minigame_in_folder(folder.folder_path, minigame_id, updated_data):
                flash(f"Minispiel '{form.name.data}' erfolgreich aktualisiert.", 'success')
                return redirect(url_for('admin.edit_folder', folder_id=folder.id))
            else:
                flash('Fehler beim Aktualisieren des Minispiels.', 'danger')
        except Exception as e:
            current_app.logger.error(f"Fehler beim Aktualisieren des Minispiels: {e}", exc_info=True)
            flash('Ein Fehler ist beim Aktualisieren des Minispiels aufgetreten.', 'danger')
    
    return render_template('edit_folder_minigame.html', form=form, folder=folder, minigame=minigame)

@admin_bp.route('/delete_folder_minigame/<int:folder_id>/<string:minigame_id>', methods=['POST'])
@login_required
def delete_folder_minigame(folder_id, minigame_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folder = MinigameFolder.query.get_or_404(folder_id)
    
    try:
        if delete_minigame_from_folder(folder.folder_path, minigame_id):
            flash('Minispiel erfolgreich gelöscht.', 'success')
        else:
            flash('Fehler beim Löschen des Minispiels.', 'danger')
    except Exception as e:
        current_app.logger.error(f"Fehler beim Löschen des Minispiels: {e}", exc_info=True)
        flash('Ein Fehler ist beim Löschen des Minispiels aufgetreten.', 'danger')
    
    return redirect(url_for('admin.edit_folder', folder_id=folder.id))

# QUESTION MANAGEMENT ROUTES
@admin_bp.route('/create_question/<int:folder_id>', methods=['GET', 'POST'])
@login_required
def create_question(folder_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folder = MinigameFolder.query.get_or_404(folder_id)
    form = CreateQuestionForm()
    
    if form.validate_on_submit():
        try:
            question_data = {
                'name': form.name.data,
                'description': form.description.data,
                'question_text': form.question_text.data,
                'question_type': form.question_type.data,
                'type': 'question'
            }
            
            if form.question_type.data == 'multiple_choice':
                options = []
                if form.option_1.data: options.append(form.option_1.data)
                if form.option_2.data: options.append(form.option_2.data)
                if form.option_3.data: options.append(form.option_3.data)
                if form.option_4.data: options.append(form.option_4.data)
                
                if len(options) < 2:
                    flash('Mindestens 2 Antwortoptionen sind erforderlich.', 'warning')
                    return render_template('create_question.html', form=form, folder=folder)
                
                question_data['options'] = options
                question_data['correct_option'] = form.correct_option.data
                
            elif form.question_type.data == 'text_input':
                if not form.correct_text.data:
                    flash('Korrekte Antwort ist bei Freitext-Fragen erforderlich.', 'warning')
                    return render_template('create_question.html', form=form, folder=folder)
                
                question_data['correct_text'] = form.correct_text.data
            
            if add_question_to_folder(folder.folder_path, question_data):
                flash(f"Frage '{form.name.data}' erfolgreich zu Ordner '{folder.name}' hinzugefügt.", 'success')
                return redirect(url_for('admin.edit_folder', folder_id=folder.id))
            else:
                flash('Fehler beim Hinzufügen der Frage.', 'danger')
        except Exception as e:
            current_app.logger.error(f"Fehler beim Erstellen der Frage: {e}", exc_info=True)
            flash('Ein Fehler ist beim Erstellen der Frage aufgetreten.', 'danger')
    
    return render_template('create_question.html', form=form, folder=folder)

@admin_bp.route('/edit_question/<int:folder_id>/<string:question_id>', methods=['GET', 'POST'])
@login_required
def edit_question(folder_id, question_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folder = MinigameFolder.query.get_or_404(folder_id)
    question = get_question_from_folder(folder.folder_path, question_id)
    
    if not question:
        flash('Frage nicht gefunden.', 'danger')
        return redirect(url_for('admin.edit_folder', folder_id=folder.id))
    
    # Erstelle ein temporäres Objekt für das Form mit korrekter Mapping der Multiple-Choice-Optionen
    form_data = dict(question)  # Kopiere die Frage-Daten
    
    # Mappe Multiple-Choice-Optionen zu einzelnen Feldern
    if question.get('question_type') == 'multiple_choice' and 'options' in question:
        options = question['options']
        form_data['option_1'] = options[0] if len(options) > 0 else ''
        form_data['option_2'] = options[1] if len(options) > 1 else ''
        form_data['option_3'] = options[2] if len(options) > 2 else ''
        form_data['option_4'] = options[3] if len(options) > 3 else ''
    
    question_obj = type('obj', (object,), form_data)()
    form = EditQuestionForm(obj=question_obj)
    
    if form.validate_on_submit():
        try:
            updated_data = {
                'name': form.name.data,
                'description': form.description.data,
                'question_text': form.question_text.data,
                'question_type': form.question_type.data,
                'type': 'question'
            }
            
            if form.question_type.data == 'multiple_choice':
                options = []
                if form.option_1.data: options.append(form.option_1.data)
                if form.option_2.data: options.append(form.option_2.data)
                if form.option_3.data: options.append(form.option_3.data)
                if form.option_4.data: options.append(form.option_4.data)
                
                if len(options) < 2:
                    flash('Mindestens 2 Antwortoptionen sind erforderlich.', 'warning')
                    return render_template('edit_question.html', form=form, folder=folder, question=question)
                
                updated_data['options'] = options
                updated_data['correct_option'] = form.correct_option.data
                
            elif form.question_type.data == 'text_input':
                if not form.correct_text.data:
                    flash('Korrekte Antwort ist bei Freitext-Fragen erforderlich.', 'warning')
                    return render_template('edit_question.html', form=form, folder=folder, question=question)
                
                updated_data['correct_text'] = form.correct_text.data
            
            if update_minigame_in_folder(folder.folder_path, question_id, updated_data):
                flash(f"Frage '{form.name.data}' erfolgreich aktualisiert.", 'success')
                return redirect(url_for('admin.edit_folder', folder_id=folder.id))
            else:
                flash('Fehler beim Aktualisieren der Frage.', 'danger')
        except Exception as e:
            current_app.logger.error(f"Fehler beim Aktualisieren der Frage: {e}", exc_info=True)
            flash('Ein Fehler ist beim Aktualisieren der Frage aufgetreten.', 'danger')
    
    return render_template('edit_question.html', form=form, folder=folder, question=question)

@admin_bp.route('/delete_question/<int:folder_id>/<string:question_id>', methods=['POST'])
@login_required
def delete_question(folder_id, question_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    folder = MinigameFolder.query.get_or_404(folder_id)
    
    try:
        if delete_minigame_from_folder(folder.folder_path, question_id):
            flash('Frage erfolgreich gelöscht.', 'success')
        else:
            flash('Fehler beim Löschen der Frage.', 'danger')
    except Exception as e:
        current_app.logger.error(f"Fehler beim Löschen der Frage: {e}", exc_info=True)
        flash('Ein Fehler ist beim Löschen der Frage aufgetreten.', 'danger')
    
    return redirect(url_for('admin.edit_folder', folder_id=folder.id))

# ROUND MANAGEMENT ROUTES
@admin_bp.route('/manage_rounds')
@login_required
def manage_rounds():
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    rounds = GameRound.query.order_by(GameRound.name).all()
    active_round = GameRound.get_active_round()
    
    return render_template('manage_rounds.html', rounds=rounds, active_round=active_round)

@admin_bp.route('/create_round', methods=['GET', 'POST'])
@login_required
def create_round():
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    form = CreateGameRoundForm()
    
    if form.validate_on_submit():
        try:
            round_obj = GameRound(
                name=form.name.data,
                description=form.description.data,
                minigame_folder_id=form.minigame_folder_id.data,
                is_active=False  # Wird nicht automatisch aktiviert
            )
            
            db.session.add(round_obj)
            db.session.commit()
            
            # Automatisches Backup der neuen Runde
            try:
                from app.admin.minigame_utils import save_round_to_filesystem
                save_round_to_filesystem(round_obj)
            except Exception as backup_e:
                current_app.logger.warning(f"Backup der Runde '{round_obj.name}' fehlgeschlagen: {backup_e}")
            
            flash(f"Spielrunde '{form.name.data}' erfolgreich erstellt.", 'success')
            return redirect(url_for('admin.manage_rounds'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Fehler beim Erstellen der Spielrunde: {e}", exc_info=True)
            flash('Ein Fehler ist beim Erstellen der Spielrunde aufgetreten.', 'danger')
    
    return render_template('create_round.html', form=form)

@admin_bp.route('/edit_round/<int:round_id>', methods=['GET', 'POST'])
@login_required
def edit_round(round_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    round_obj = GameRound.query.get_or_404(round_id)
    form = EditGameRoundForm(original_round_name=round_obj.name, obj=round_obj)
    
    if form.validate_on_submit():
        try:
            round_obj.name = form.name.data
            round_obj.description = form.description.data
            round_obj.minigame_folder_id = form.minigame_folder_id.data
            
            db.session.commit()
            
            # Automatisches Backup der aktualisierten Runde
            try:
                from app.admin.minigame_utils import save_round_to_filesystem
                save_round_to_filesystem(round_obj)
            except Exception as backup_e:
                current_app.logger.warning(f"Backup der aktualisierten Runde '{round_obj.name}' fehlgeschlagen: {backup_e}")
            
            flash(f"Spielrunde '{form.name.data}' erfolgreich aktualisiert.", 'success')
            return redirect(url_for('admin.manage_rounds'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Fehler beim Aktualisieren der Spielrunde: {e}", exc_info=True)
            flash('Ein Fehler ist beim Aktualisieren der Spielrunde aufgetreten.', 'danger')
    
    return render_template('edit_round.html', form=form, round=round_obj)

@admin_bp.route('/delete_round/<int:round_id>', methods=['GET', 'POST'])
@login_required
def delete_round(round_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    round_obj = GameRound.query.get_or_404(round_id)
    form = DeleteConfirmationForm()
    
    if request.method == 'POST' and form.validate_on_submit():
        try:
            was_active = round_obj.is_active
            round_name = round_obj.name  # Namen vor dem Löschen speichern
            
            # Aktualisiere GameSessions
            GameSession.query.filter_by(game_round_id=round_obj.id).update({'game_round_id': None})
            
            # Lösche die Runde
            db.session.delete(round_obj)
            
            # Falls es die aktive Runde war, aktiviere eine andere
            if was_active:
                other_round = GameRound.query.first()
                if other_round:
                    other_round.is_active = True
                    flash(f"Runde '{other_round.name}' wurde automatisch aktiviert.", 'info')
            
            db.session.commit()
            
            # Lösche auch das Backup aus dem Dateisystem
            try:
                from app.admin.minigame_utils import delete_round_from_filesystem
                delete_round_from_filesystem(round_name)
            except Exception as backup_e:
                current_app.logger.warning(f"Löschen des Backups für Runde '{round_name}' fehlgeschlagen: {backup_e}")
            
            flash(f"Spielrunde '{round_name}' erfolgreich gelöscht.", 'success')
            return redirect(url_for('admin.manage_rounds'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Fehler beim Löschen der Spielrunde: {e}", exc_info=True)
            flash('Ein Fehler ist beim Löschen der Spielrunde aufgetreten.', 'danger')
    
    return render_template('delete_round.html', form=form, round=round_obj)

@admin_bp.route('/activate_round/<int:round_id>', methods=['POST'])
@login_required
def activate_round(round_id):
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    try:
        round_obj = GameRound.query.get_or_404(round_id)
        
        # Stelle sicher, dass die Runde rundenspezifische Konfigurationen hat
        round_obj.ensure_round_configurations()
        
        # Aktiviere die Runde (lädt automatisch die Konfigurationen)
        round_obj.activate()
        
        # Beim Wechseln der Runde: Gespielte Inhalte zurücksetzen
        active_session = GameSession.query.filter_by(is_active=True).first()
        if active_session:
            reset_played_content_for_session(active_session)
            
            event = GameEvent(
                game_session_id=active_session.id,
                event_type="round_activated",
                description=f"Spielrunde '{round_obj.name}' wurde aktiviert. Gespielte Inhalte und Konfigurationen wurden geladen."
            )
            db.session.add(event)
            db.session.commit()
        
        flash(f"Spielrunde '{round_obj.name}' wurde aktiviert. Rundenspezifische Konfigurationen wurden geladen.", 'success')
    except Exception as e:
        current_app.logger.error(f"Fehler beim Aktivieren der Spielrunde: {e}", exc_info=True)
        flash('Ein Fehler ist beim Aktivieren der Spielrunde aufgetreten.', 'danger')
    
    return redirect(url_for('admin.manage_rounds'))

@admin_bp.route('/backup_rounds', methods=['GET', 'POST'])
@login_required
def backup_rounds():
    """Manuelle Sicherung und Wiederherstellung von Spielrunden"""
    if not isinstance(current_user, Admin):
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'backup_all':
            try:
                backed_up_count = backup_all_rounds_before_db_reset()
                if backed_up_count > 0:
                    flash(f"✅ {backed_up_count} Runden erfolgreich gesichert!", 'success')
                else:
                    flash("ℹ️ Keine Runden zum Sichern gefunden.", 'info')
            except Exception as e:
                current_app.logger.error(f"Fehler beim Sichern aller Runden: {e}", exc_info=True)
                flash("❌ Fehler beim Sichern der Runden.", 'danger')
        
        elif action == 'restore_all':
            try:
                restored_count = restore_rounds_to_database()
                if restored_count > 0:
                    flash(f"✅ {restored_count} Runden erfolgreich wiederhergestellt!", 'success')
                else:
                    flash("ℹ️ Keine Runden zum Wiederherstellen gefunden.", 'info')
            except Exception as e:
                current_app.logger.error(f"Fehler beim Wiederherstellen der Runden: {e}", exc_info=True)
                flash("❌ Fehler beim Wiederherstellen der Runden.", 'danger')
        
        elif action == 'backup_single':
            round_id = request.form.get('round_id')
            try:
                round_obj = GameRound.query.get_or_404(round_id)
                if save_round_to_filesystem(round_obj):
                    flash(f"✅ Runde '{round_obj.name}' erfolgreich gesichert!", 'success')
                else:
                    flash(f"❌ Fehler beim Sichern der Runde '{round_obj.name}'.", 'danger')
            except Exception as e:
                current_app.logger.error(f"Fehler beim Sichern der Runde: {e}", exc_info=True)
                flash("❌ Fehler beim Sichern der Runde.", 'danger')
        
        elif action == 'delete_backup':
            round_name = request.form.get('round_name')
            try:
                if delete_round_from_filesystem(round_name):
                    flash(f"✅ Backup der Runde '{round_name}' erfolgreich gelöscht!", 'success')
                else:
                    flash(f"❌ Backup der Runde '{round_name}' nicht gefunden.", 'warning')
            except Exception as e:
                current_app.logger.error(f"Fehler beim Löschen des Backups: {e}", exc_info=True)
                flash("❌ Fehler beim Löschen des Backups.", 'danger')
        
        return redirect(url_for('admin.backup_rounds'))
    
    # GET request - zeige die Backup-Seite
    try:
        # Aktuelle Runden in der Datenbank
        db_rounds = GameRound.query.order_by(GameRound.name).all()
        
        # Gesicherte Runden im Dateisystem
        saved_rounds = load_rounds_from_filesystem()
        
        # Statistiken
        stats = {
            'db_rounds_count': len(db_rounds),
            'saved_rounds_count': len(saved_rounds),
            'total_storage_used': sum(len(json.dumps(r, ensure_ascii=False)) for r in saved_rounds)
        }
        
        return render_template('backup_rounds.html', 
                             db_rounds=db_rounds, 
                             saved_rounds=saved_rounds, 
                             stats=stats)
    except Exception as e:
        current_app.logger.error(f"Fehler beim Laden der Backup-Seite: {e}", exc_info=True)
        flash("❌ Fehler beim Laden der Backup-Informationen.", 'danger')
        return redirect(url_for('admin.manage_rounds'))

# WELCOME-SYSTEM ADMIN API-ENDPUNKTE

@admin_bp.route('/api/start-welcome', methods=['POST'])
@login_required
def start_welcome():
    """Startet das Welcome-System"""
    if not isinstance(current_user, Admin):
        current_app.logger.error(f"Unauthorized access attempt to start-welcome by: {current_user}")
        return jsonify({"success": False, "error": "Nur Admins können das Welcome-System starten"}), 403
    
    try:
        current_app.logger.info(f"Starting welcome system - requested by: {current_user.username}")
        
        # Prüfe ob bereits eine Session aktiv ist
        existing_session = WelcomeSession.get_active_session()
        if existing_session:
            return jsonify({"success": False, "error": "Welcome-System ist bereits aktiv"}), 400
        
        # Erstelle neue Welcome-Session
        welcome_session = WelcomeSession()
        welcome_session.activate()
        
        db.session.add(welcome_session)
        db.session.commit()
        
        current_app.logger.info(f"Welcome-System gestartet von Admin: {current_user.username}")
        
        return jsonify({
            "success": True,
            "message": "Welcome-System erfolgreich gestartet"
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Starten des Welcome-Systems: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Ein Fehler ist aufgetreten"}), 500

@admin_bp.route('/api/create-teams', methods=['POST'])
@login_required
def create_teams():
    """Erstellt Teams und verteilt Spieler zufällig"""
    if not isinstance(current_user, Admin):
        return jsonify({"success": False, "error": "Nur Admins können Teams erstellen"}), 403
    
    try:
        import random
        import string
        
        data = request.get_json()
        team_count = data.get('team_count')
        
        if not team_count or not isinstance(team_count, int) or team_count < 2 or team_count > 6:
            return jsonify({"success": False, "error": "Ungültige Team-Anzahl (2-6 erlaubt)"}), 400
        
        # Prüfe aktive Welcome-Session
        welcome_session = WelcomeSession.get_active_session()
        if not welcome_session:
            return jsonify({"success": False, "error": "Keine aktive Welcome-Session"}), 400
        
        if welcome_session.teams_created:
            return jsonify({"success": False, "error": "Teams wurden bereits erstellt"}), 400
        
        # Hole alle registrierten Spieler
        players = welcome_session.get_registered_players()
        if len(players) < team_count:
            return jsonify({"success": False, "error": f"Nicht genügend Spieler (mindestens {team_count} erforderlich)"}), 400
        
        # Mische Spieler zufällig mit verschiedenen Methoden für maximale Zufälligkeit
        players_list = list(players)
        current_app.logger.info(f"Spieler vor Mischen: {[p.player_name for p in players_list]}")
        
        # Mehrfaches Mischen für bessere Zufälligkeit
        import time
        random.seed(int(time.time() * 1000000) % 1000000)  # Microsekunden-basierter Seed
        for _ in range(3):
            random.shuffle(players_list)
        
        current_app.logger.info(f"Spieler nach Mischen: {[p.player_name for p in players_list]}")
        
        # Erstelle Teams mit zufälligen 6-stelligen Passwörtern
        created_teams = []
        
        for i in range(team_count):
            # Generiere 6-stelliges Passwort
            password = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            
            # Erstelle Team
            team = Team(
                name=f"Team {i+1}",
                members="",  # Wird später mit Spielernamen gefüllt
                welcome_password=password  # Speichere Klartext-Passwort für Welcome-System
            )
            team.set_password(password)
            
            db.session.add(team)
            db.session.flush()  # Damit wir die Team-ID bekommen
            
            created_teams.append({
                "team": team,
                "password": password,
                "members": []
            })
        
        # Verteile Spieler gleichmäßig auf Teams
        for i, player in enumerate(players_list):
            team_index = i % team_count
            selected_team = created_teams[team_index]
            
            # Setze Team-Zuordnung für Spieler
            player.assigned_team_id = selected_team["team"].id
            selected_team["members"].append(player.player_name)
            
            # Kopiere Profilbild ins Team falls vorhanden
            if player.profile_image_path:
                selected_team["team"].set_profile_image(player.player_name, player.profile_image_path)
        
        # Aktualisiere Team-Members String
        for team_data in created_teams:
            team_data["team"].members = ", ".join(team_data["members"])
        
        # Markiere Welcome-Session als teams_created
        welcome_session.teams_created = True
        welcome_session.team_count = team_count
        
        db.session.commit()
        
        current_app.logger.info(f"Teams erstellt von Admin {current_user.username}: {team_count} Teams mit {len(players_list)} Spielern")
        
        # Erstelle Response mit Team-Informationen (inkl. Passwörter für Admin)
        teams_info = []
        for team_data in created_teams:
            teams_info.append({
                "id": team_data["team"].id,
                "name": team_data["team"].name,
                "password": team_data["password"],
                "members": team_data["members"]
            })
        
        return jsonify({
            "success": True,
            "message": f"{team_count} Teams erfolgreich erstellt",
            "teams": teams_info
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Erstellen der Teams: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Ein Fehler ist aufgetreten"}), 500

@admin_bp.route('/api/end-welcome', methods=['POST'])
@login_required
def end_welcome():
    """Beendet Welcome-Modus und wechselt zum Spielbrett"""
    if not isinstance(current_user, Admin):
        return jsonify({"success": False, "error": "Nur Admins können das Welcome-System beenden"}), 403
    
    try:
        
        welcome_session = WelcomeSession.get_active_session()
        if not welcome_session:
            return jsonify({"success": False, "error": "Keine aktive Welcome-Session"}), 400
        
        if not welcome_session.teams_created:
            return jsonify({"success": False, "error": "Teams müssen erst erstellt werden"}), 400
        
        # Beende Welcome-Session
        welcome_session.deactivate()
        
        current_app.logger.info(f"Welcome-System beendet von Admin: {current_user.username}")
        
        return jsonify({
            "success": True,
            "message": "Welcome-System beendet, Spiel kann beginnen"
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Beenden des Welcome-Systems: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Ein Fehler ist aufgetreten"}), 500

@admin_bp.route('/api/end-registration', methods=['POST'])
@login_required
def end_registration():
    """Beendet die Registrierung komplett (ohne Teams zu erstellen)"""
    current_app.logger.info(f"end-registration aufgerufen von User: {current_user}")
    
    # CSRF Token Validierung mit JSON-Response bei Fehlern
    try:
        from flask_wtf.csrf import validate_csrf
        validate_csrf(request.headers.get('X-CSRFToken'))
    except Exception as csrf_error:
        current_app.logger.error(f"CSRF validation failed: {csrf_error}")
        return jsonify({"success": False, "error": "CSRF token validation failed"}), 400
    
    if not isinstance(current_user, Admin):
        current_app.logger.warning(f"Unauthorized access attempt by: {current_user}")
        return jsonify({"success": False, "error": "Nur Admins können die Registrierung beenden"}), 403
    
    try:
        current_app.logger.info("Suche nach aktiver Welcome-Session")
        welcome_session = WelcomeSession.get_active_session()
        if not welcome_session:
            current_app.logger.warning("Keine aktive Welcome-Session gefunden")
            return jsonify({"success": False, "error": "Keine aktive Welcome-Session"}), 400
        
        current_app.logger.info(f"Deaktiviere Welcome-Session {welcome_session.id}")
        # Beende Welcome-Session
        welcome_session.deactivate()
        
        current_app.logger.info(f"Registrierung erfolgreich beendet von Admin: {current_user.username}")
        
        return jsonify({
            "success": True,
            "message": "Registrierung erfolgreich beendet"
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Beenden der Registrierung: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Ein Fehler ist aufgetreten"
        }), 500

@admin_bp.route('/player_rotation_stats')
@login_required
def player_rotation_stats():
    """Zeigt Statistiken zur Spieler-Rotation"""
    if not isinstance(current_user, Admin):
        flash('Zugriff verweigert. Nur Admins können Rotations-Statistiken sehen.', 'danger')
        return redirect(url_for('main.index'))
    
    try:
        active_session = GameSession.query.filter_by(is_active=True).first()
        if not active_session:
            flash('Keine aktive Spielsitzung gefunden.', 'warning')
            return redirect(url_for('admin.admin_dashboard'))
        
        # Hole Statistiken
        rotation_stats = active_session.get_player_statistics()
        
        # Hole Team-Informationen
        teams = Team.query.all()
        team_lookup = {str(team.id): team for team in teams}
        
        # Format für Template
        formatted_stats = {}
        for team_id, stats in rotation_stats.items():
            team = team_lookup.get(team_id)
            if team:
                formatted_stats[team.name] = {
                    'total_games': stats['total_games'],
                    'players': stats['players'],
                    'most_played': stats['most_played'],
                    'least_played': stats['least_played'],
                    'team_members': team.members.split(', ') if team.members else []
                }
        
        return jsonify({
            'success': True,
            'stats': formatted_stats,
            'session_id': active_session.id
        })
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Laden der Rotations-Statistiken: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Fehler beim Laden der Statistiken'
        }), 500

@admin_bp.route('/reset_player_rotation', methods=['POST'])
@login_required
def reset_player_rotation():
    """Setzt die Spieler-Rotation zurück"""
    if not isinstance(current_user, Admin):
        return jsonify({'success': False, 'error': 'Zugriff verweigert'}), 403
    
    try:
        active_session = GameSession.query.filter_by(is_active=True).first()
        if not active_session:
            return jsonify({'success': False, 'error': 'Keine aktive Spielsitzung'}), 400
        
        # Reset der Rotation
        active_session.reset_player_rotation()
        db.session.commit()
        
        # Event loggen
        event = GameEvent(
            game_session_id=active_session.id,
            event_type="player_rotation_reset",
            description="Spieler-Rotation wurde zurückgesetzt.",
            related_team_id=None
        )
        db.session.add(event)
        db.session.commit()
        
        flash('Spieler-Rotation wurde zurückgesetzt. Alle Spieler starten wieder mit 0 Einsätzen.', 'success')
        
        return jsonify({
            'success': True,
            'message': 'Spieler-Rotation zurückgesetzt'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Zurücksetzen der Rotation: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Fehler beim Zurücksetzen'
        }), 500


# =============================================================================
# FELD-MINIGAME API ENDPUNKTE
# =============================================================================

@admin_bp.route('/api/field_minigame_counts')
@login_required
def api_field_minigame_counts():
    """API-Endpunkt für Feld-Minigame Anzahl"""
    if not isinstance(current_user, Admin):
        return jsonify({'error': 'Zugriff verweigert'}), 403
    
    try:
        import os
        
        team_vs_all_path = os.path.join(current_app.static_folder, 'field_minigames', 'team_vs_all')
        team_vs_team_path = os.path.join(current_app.static_folder, 'field_minigames', 'team_vs_team')
        
        team_vs_all_count = 0
        team_vs_team_count = 0
        
        # Zähle JSON-Dateien in team_vs_all
        if os.path.exists(team_vs_all_path):
            team_vs_all_count = len([f for f in os.listdir(team_vs_all_path) if f.endswith('.json')])
        
        # Zähle JSON-Dateien in team_vs_team
        if os.path.exists(team_vs_team_path):
            team_vs_team_count = len([f for f in os.listdir(team_vs_team_path) if f.endswith('.json')])
        
        return jsonify({
            'team_vs_all': team_vs_all_count,
            'team_vs_team': team_vs_team_count
        })
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Laden der Minigame-Anzahl: {e}")
        return jsonify({'error': 'Fehler beim Laden'}), 500


@admin_bp.route('/api/field_minigame_config', methods=['GET', 'POST'])
@login_required
def api_field_minigame_config():
    """API-Endpunkt für Feld-Minigame Konfiguration"""
    if not isinstance(current_user, Admin):
        return jsonify({'error': 'Zugriff verweigert'}), 403
    
    config_path = os.path.join(current_app.static_folder, 'field_minigames', 'config.json')
    
    if request.method == 'GET':
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                return jsonify(config)
            else:
                return jsonify({'field_minigames': {'enabled': True}})
        except Exception as e:
            current_app.logger.error(f"Fehler beim Laden der Konfiguration: {e}")
            return jsonify({'error': 'Fehler beim Laden'}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            key = data.get('key')
            value = data.get('value')
            
            # Lade aktuelle Konfiguration
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {'field_minigames': {'enabled': True, 'modes': {}}}
            
            # Aktualisiere Konfiguration basierend auf dem Key
            field_config = config.get('field_minigames', {})
            
            if key == 'reward_forward':
                # Aktualisiere Belohnung für beide Modi
                modes = field_config.get('modes', {})
                if 'team_vs_all' in modes:
                    modes['team_vs_all']['reward_forward'] = int(value)
                if 'team_vs_team' in modes:
                    modes['team_vs_team']['reward_forward'] = int(value)
                field_config['modes'] = modes
            elif key == 'default_mode':
                field_config['default_mode'] = value
            elif key == 'auto_start_timer':
                if 'game_flow' not in field_config:
                    field_config['game_flow'] = {}
                field_config['game_flow']['auto_start_timer'] = int(value)
            
            config['field_minigames'] = field_config
            
            # Speichere Konfiguration
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            return jsonify({'success': True, 'message': 'Konfiguration gespeichert'})
            
        except Exception as e:
            current_app.logger.error(f"Fehler beim Speichern der Konfiguration: {e}")
            return jsonify({'success': False, 'error': 'Fehler beim Speichern'}), 500


@admin_bp.route('/api/field_minigames/<mode>', methods=['GET', 'POST'])
@login_required
def api_field_minigames(mode):
    """API-Endpunkt für Feld-Minigame Verwaltung"""
    if not isinstance(current_user, Admin):
        return jsonify({'error': 'Zugriff verweigert'}), 403
    
    if mode not in ['team_vs_all', 'team_vs_team']:
        return jsonify({'error': 'Ungültiger Modus'}), 400
    
    folder_path = os.path.join(current_app.static_folder, 'field_minigames', mode)
    
    if request.method == 'GET':
        try:
            minigames = []
            
            if os.path.exists(folder_path):
                for filename in os.listdir(folder_path):
                    if filename.endswith('.json'):
                        file_path = os.path.join(folder_path, filename)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = json.load(f)
                            content['id'] = filename  # Verwende Dateiname als ID
                            minigames.append(content)
            
            return jsonify({'minigames': minigames})
            
        except Exception as e:
            current_app.logger.error(f"Fehler beim Laden der Minigames: {e}")
            return jsonify({'error': 'Fehler beim Laden'}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            
            # Validierung - nur Spiele erlaubt
            if not data.get('type') or data['type'] != 'game':
                return jsonify({'success': False, 'error': 'Nur Spiele sind erlaubt'}), 400
            
            if not data.get('title') or not data.get('description') or not data.get('instructions'):
                return jsonify({'success': False, 'error': 'Fehlende Pflichtfelder für Spiel'}), 400
            
            if not data.get('player_count') or not isinstance(data['player_count'], int) or data['player_count'] < 1:
                return jsonify({'success': False, 'error': 'Ungültige Spieleranzahl'}), 400
            
            # Erstelle Ordner falls nicht vorhanden
            os.makedirs(folder_path, exist_ok=True)
            
            # Generiere eindeutigen Dateinamen
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"game_{timestamp}_{str(uuid.uuid4())[:8]}.json"
            file_path = os.path.join(folder_path, filename)
            
            # Speichere Minigame
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return jsonify({'success': True, 'message': 'Minigame gespeichert', 'id': filename})
            
        except Exception as e:
            current_app.logger.error(f"Fehler beim Speichern des Minigames: {e}")
            return jsonify({'success': False, 'error': 'Fehler beim Speichern'}), 500


@admin_bp.route('/api/field_minigames/<mode>/<minigame_id>', methods=['DELETE'])
@login_required
def api_delete_field_minigame(mode, minigame_id):
    """API-Endpunkt zum Löschen von Feld-Minigames"""
    if not isinstance(current_user, Admin):
        return jsonify({'error': 'Zugriff verweigert'}), 403
    
    if mode not in ['team_vs_all', 'team_vs_team']:
        return jsonify({'error': 'Ungültiger Modus'}), 400
    
    try:
        folder_path = os.path.join(current_app.static_folder, 'field_minigames', mode)
        file_path = os.path.join(folder_path, minigame_id)
        
        if os.path.exists(file_path) and file_path.endswith('.json'):
            os.remove(file_path)
            return jsonify({'success': True, 'message': 'Minigame gelöscht'})
        else:
            return jsonify({'success': False, 'error': 'Minigame nicht gefunden'}), 404
            
    except Exception as e:
        current_app.logger.error(f"Fehler beim Löschen des Minigames: {e}")
        return jsonify({'success': False, 'error': 'Fehler beim Löschen'}), 500