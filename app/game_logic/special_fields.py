"""
Sonderfeld-Logik für Wii Party Clone
Enthält alle Funktionen für die verschiedenen Sonderfelder
"""
import random
from flask import current_app
from app.models import db, GameEvent


def handle_catapult_forward(team, current_position, game_session):
    """
    Katapultiert ein Team 3-5 Felder nach vorne
    """
    max_board_fields = current_app.config.get('MAX_BOARD_FIELDS', 72)
    catapult_distance = random.randint(3, 5)
    
    old_position = current_position
    new_position = min(current_position + catapult_distance, max_board_fields)
    
    team.current_position = new_position
    
    # Event erstellen
    event = GameEvent(
        game_session_id=game_session.id,
        event_type="special_field_catapult_forward",
        description=f"Team {team.name} wurde {catapult_distance} Felder nach vorne katapultiert (von Feld {old_position} zu Feld {new_position})!",
        related_team_id=team.id,
        data_json=str({
            "field_type": "catapult_forward",
            "catapult_distance": catapult_distance,
            "old_position": old_position,
            "new_position": new_position
        })
    )
    db.session.add(event)
    
    return {
        "success": True,
        "action": "catapult_forward", 
        "catapult_distance": catapult_distance,
        "old_position": old_position,
        "new_position": new_position,
        "message": f"🚀 Katapult! {team.name} fliegt {catapult_distance} Felder nach vorne!"
    }


def handle_catapult_backward(team, current_position, game_session):
    """
    Katapultiert ein Team 2-4 Felder nach hinten
    """
    catapult_distance = random.randint(2, 4)
    
    old_position = current_position
    new_position = max(0, current_position - catapult_distance)
    
    team.current_position = new_position
    
    # Event erstellen
    event = GameEvent(
        game_session_id=game_session.id,
        event_type="special_field_catapult_backward",
        description=f"Team {team.name} wurde {catapult_distance} Felder nach hinten katapultiert (von Feld {old_position} zu Feld {new_position})!",
        related_team_id=team.id,
        data_json=str({
            "field_type": "catapult_backward",
            "catapult_distance": catapult_distance,
            "old_position": old_position,
            "new_position": new_position
        })
    )
    db.session.add(event)
    
    return {
        "success": True,
        "action": "catapult_backward",
        "catapult_distance": catapult_distance,
        "old_position": old_position,
        "new_position": new_position,
        "message": f"💥 Rückschlag! {team.name} wird {catapult_distance} Felder zurück geschleudert!"
    }


def handle_player_swap(current_team, all_teams, game_session):
    """
    Tauscht die Position des aktuellen Teams mit einem zufälligen anderen Team
    """
    # Finde andere Teams (nicht das aktuelle)
    other_teams = [team for team in all_teams if team.id != current_team.id and team.current_position != current_team.current_position]
    
    if not other_teams:
        return {
            "success": False,
            "action": "player_swap",
            "message": f"🔄 Kein anderes Team zum Tauschen verfügbar!"
        }
    
    # Wähle zufälliges Team zum Tauschen
    swap_team = random.choice(other_teams)
    
    # Tausche Positionen
    old_current_position = current_team.current_position
    old_swap_position = swap_team.current_position
    
    current_team.current_position = old_swap_position
    swap_team.current_position = old_current_position
    
    # Event erstellen
    event = GameEvent(
        game_session_id=game_session.id,
        event_type="special_field_player_swap",
        description=f"Team {current_team.name} (Feld {old_current_position}) tauschte Positionen mit Team {swap_team.name} (Feld {old_swap_position})!",
        related_team_id=current_team.id,
        data_json=str({
            "field_type": "player_swap",
            "current_team_id": current_team.id,
            "current_team_old_position": old_current_position,
            "current_team_new_position": current_team.current_position,
            "swap_team_id": swap_team.id,
            "swap_team_name": swap_team.name,
            "swap_team_old_position": old_swap_position,
            "swap_team_new_position": swap_team.current_position
        })
    )
    db.session.add(event)
    
    return {
        "success": True,
        "action": "player_swap",
        "current_team_old_position": old_current_position,
        "current_team_new_position": current_team.current_position,
        "swap_team_name": swap_team.name,
        "swap_team_old_position": old_swap_position,
        "swap_team_new_position": swap_team.current_position,
        "message": f"🔄 Positionstausch! {current_team.name} tauscht mit {swap_team.name}!"
    }


def handle_barrier_field(team, game_session):
    """
    Setzt ein Team auf ein Sperren-Feld
    Das Team muss eine bestimmte Zahl würfeln um freizukommen
    """
    target_numbers = [4, 5, 6]  # Mögliche Zahlen die gewürfelt werden müssen
    target_number = random.choice(target_numbers)
    
    # Team blockieren
    team.is_blocked = True
    team.blocked_target_number = target_number
    
    # Event erstellen
    event = GameEvent(
        game_session_id=game_session.id,
        event_type="special_field_barrier_set",
        description=f"Team {team.name} ist auf ein Sperren-Feld geraten! Sie müssen eine {target_number} oder höher würfeln um freizukommen.",
        related_team_id=team.id,
        data_json=str({
            "field_type": "barrier",
            "target_number": target_number,
            "position": team.current_position
        })
    )
    db.session.add(event)
    
    return {
        "success": True,
        "action": "barrier_set",
        "target_number": target_number,
        "message": f"🚧 Blockiert! {team.name} muss eine {target_number} oder höher würfeln!"
    }


def check_barrier_release(team, dice_roll, game_session):
    """
    Prüft ob ein blockiertes Team durch den Würfelwurf freikommt
    """
    if not team.is_blocked:
        return {"released": False}
    
    if dice_roll >= team.blocked_target_number:
        # Team freigeben
        team.is_blocked = False
        old_target = team.blocked_target_number
        team.blocked_target_number = None
        
        # Event erstellen
        event = GameEvent(
            game_session_id=game_session.id,
            event_type="special_field_barrier_released",
            description=f"Team {team.name} hat eine {dice_roll} gewürfelt und ist von der Sperre befreit! (Benötigt: {old_target}+)",
            related_team_id=team.id,
            data_json=str({
                "field_type": "barrier_release",
                "dice_roll": dice_roll,
                "target_number": old_target,
                "position": team.current_position
            })
        )
        db.session.add(event)
        
        return {
            "released": True,
            "dice_roll": dice_roll,
            "target_number": old_target,
            "message": f"🎉 Befreit! {team.name} hat eine {dice_roll} gewürfelt und ist frei!"
        }
    else:
        # Immer noch blockiert
        event = GameEvent(
            game_session_id=game_session.id,
            event_type="special_field_barrier_failed",
            description=f"Team {team.name} hat eine {dice_roll} gewürfelt, aber benötigt mindestens {team.blocked_target_number}. Immer noch blockiert!",
            related_team_id=team.id,
            data_json=str({
                "field_type": "barrier_failed",
                "dice_roll": dice_roll,
                "target_number": team.blocked_target_number,
                "position": team.current_position
            })
        )
        db.session.add(event)
        
        return {
            "released": False,
            "dice_roll": dice_roll,
            "target_number": team.blocked_target_number,
            "message": f"🚧 Immer noch blockiert! {team.name} braucht mindestens {team.blocked_target_number}!"
        }


def get_field_type_at_position(position):
    """
    Bestimmt den Feldtyp basierend auf der Position
    Verwendet die gleiche Logik wie im Frontend
    """
    if position == 0:
        return 'start'
    elif position == 72:  # Zielfeld
        return 'goal'
    elif position % 15 == 0:  # Katapult vorwärts
        return 'catapult_forward' 
    elif position % 13 == 0:  # Katapult rückwärts
        return 'catapult_backward'
    elif position % 17 == 0:  # Spieler-Tausch
        return 'player_swap'
    elif position % 19 == 0:  # Sperren-Feld
        return 'barrier'
    elif position % 8 == 0:   # Bonus-Feld
        return 'bonus'
    elif position % 12 == 0:  # Minispiel
        return 'minigame'
    elif position % 20 == 0:  # Ereignis-Feld
        return 'chance'
    elif position % 25 == 0:  # Falle
        return 'trap'
    else:
        return 'normal'


def handle_special_field_action(team, all_teams, game_session):
    """
    Hauptfunktion die nach einer Bewegung aufgerufen wird
    Prüft den Feldtyp und führt entsprechende Aktionen aus
    """
    field_type = get_field_type_at_position(team.current_position)
    
    if field_type == 'catapult_forward':
        return handle_catapult_forward(team, team.current_position, game_session)
    elif field_type == 'catapult_backward':
        return handle_catapult_backward(team, team.current_position, game_session)
    elif field_type == 'player_swap':
        return handle_player_swap(team, all_teams, game_session)
    elif field_type == 'barrier':
        return handle_barrier_field(team, game_session)
    else:
        # Kein Sonderfeld oder andere Felder (Minispiel, Bonus, etc.)
        return {"success": False, "action": "none"}


def get_all_special_field_positions(max_fields=73):
    """
    Gibt alle Positionen der Sonderfelder zurück
    Nützlich für Frontend-Visualisierung
    """
    special_positions = {
        'catapult_forward': [],
        'catapult_backward': [],
        'player_swap': [],
        'barrier': []
    }
    
    for pos in range(max_fields):
        field_type = get_field_type_at_position(pos)
        if field_type in special_positions:
            special_positions[field_type].append(pos)
    
    return special_positions