#!/usr/bin/env python3
"""
Reset Session Data Script
"""
from app import create_app
from app.models import db, GameSession

app = create_app()
with app.app_context():
    session = GameSession.query.filter_by(is_active=True).first()
    if session:
        print(f'Session gefunden: {session.id}')
        print(f'Phase: {session.current_phase}')
        print(f'Field minigame data: {bool(session.field_minigame_selected_players)}')
        
        # Reset FELD-Minispiel Daten
        session.field_minigame_selected_players = None
        session.field_minigame_landing_team_id = None
        session.field_minigame_opponent_team_id = None
        session.field_minigame_content_id = None
        session.field_minigame_mode = None
        session.current_phase = 'DICE_ROLLING'
        
        db.session.commit()
        print('Session zurückgesetzt!')
    else:
        print('Keine aktive Session')