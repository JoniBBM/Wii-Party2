"""
Sonderfeld-Logik für Wii Party Clone - Erweitert mit konfigurierbaren Feld-Häufigkeiten
Enthält alle Funktionen für die verschiedenen Sonderfelder basierend auf FieldConfiguration
"""
import random
from flask import current_app
from app.models import db, GameEvent, FieldConfiguration


def handle_catapult_forward(team, current_position, game_session):
    """
    Katapultiert ein Team 3-5 Felder nach vorne (konfigurierbar)
    """
    config = FieldConfiguration.get_config_for_field('catapult_forward')
    if not config or not config.is_enabled:
        return {"success": False, "action": "none"}
    
    config_data = config.config_dict
    min_distance = config_data.get('min_distance', 3)
    max_distance = config_data.get('max_distance', 5)
    
    max_board_fields = current_app.config.get('MAX_BOARD_FIELDS', 72)
    catapult_distance = random.randint(min_distance, max_distance)
    
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
    Katapultiert ein Team 2-4 Felder nach hinten (konfigurierbar)
    """
    config = FieldConfiguration.get_config_for_field('catapult_backward')
    if not config or not config.is_enabled:
        return {"success": False, "action": "none"}
    
    config_data = config.config_dict
    min_distance = config_data.get('min_distance', 2)
    max_distance = config_data.get('max_distance', 4)
    
    catapult_distance = random.randint(min_distance, max_distance)
    
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
    Tauscht die Position des aktuellen Teams mit einem zufälligen anderen Team (konfigurierbar)
    """
    config = FieldConfiguration.get_config_for_field('player_swap')
    if not config or not config.is_enabled:
        return {"success": False, "action": "none"}
    
    config_data = config.config_dict
    min_distance = config_data.get('min_distance', 3)
    
    # Finde andere Teams (nicht das aktuelle) mit Mindestabstand
    other_teams = []
    for team in all_teams:
        if team.id != current_team.id:
            distance = abs(team.current_position - current_team.current_position)
            if distance >= min_distance:
                other_teams.append(team)
    
    if not other_teams:
        # Fallback: alle anderen Teams wenn kein Mindestabstand erfüllt wird
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
    Setzt ein Team auf ein Sperren-Feld (konfigurierbar)
    Das Team muss eine bestimmte Zahl würfeln um freizukommen
    """
    config = FieldConfiguration.get_config_for_field('barrier')
    if not config or not config.is_enabled:
        return {"success": False, "action": "none"}
    
    config_data = config.config_dict
    target_numbers = config_data.get('target_numbers', [4, 5, 6])
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
    Bestimmt den Feldtyp basierend auf der Position unter Verwendung der FieldConfiguration
    """
    # Spezielle Felder zuerst prüfen
    if position == 0:
        return 'start'
    elif position == 72:  # Zielfeld
        return 'goal'
    
    # Alle aktivierten Konfigurationen laden
    field_configs = FieldConfiguration.get_all_enabled()
    
    # Nach Priorität sortieren (niedrigere frequency_value = höhere Priorität)
    # Das verhindert Konflikte zwischen verschiedenen Feld-Typen
    field_configs = sorted(field_configs, key=lambda x: x.frequency_value if x.frequency_value > 0 else 999)
    
    for config in field_configs:
        if config.field_type in ['start', 'goal', 'normal']:
            continue  # Diese werden speziell behandelt
        
        if config.frequency_type == 'modulo' and config.frequency_value > 0:
            if position % config.frequency_value == 0:
                return config.field_type
        elif config.frequency_type == 'fixed_positions':
            # Für fest definierte Positionen
            fixed_positions = config.config_dict.get('positions', [])
            if position in fixed_positions:
                return config.field_type
        elif config.frequency_type == 'probability':
            # Wahrscheinlichkeitsbasiert (für zukünftige Implementierung)
            probability = config.frequency_value / 100.0  # frequency_value als Prozent
            if random.random() < probability:
                return config.field_type
    
    # Fallback zu normal
    return 'normal'


def get_field_config_for_position(position):
    """
    Gibt die FieldConfiguration für eine bestimmte Position zurück
    """
    field_type = get_field_type_at_position(position)
    return FieldConfiguration.get_config_for_field(field_type)


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
    elif field_type == 'bonus':
        return handle_bonus_field(team, game_session)
    elif field_type == 'trap':
        return handle_trap_field(team, game_session)
    elif field_type == 'chance':
        return handle_chance_field(team, game_session)
    else:
        # Kein Sonderfeld oder andere Felder (Minispiel, normale Felder, etc.)
        return {"success": False, "action": "none"}


def handle_bonus_field(team, game_session):
    """
    Behandelt Bonus-Felder (konfigurierbar)
    """
    config = FieldConfiguration.get_config_for_field('bonus')
    if not config or not config.is_enabled:
        return {"success": False, "action": "none"}
    
    config_data = config.config_dict
    bonus_type = config_data.get('bonus_type', 'extra_dice')
    
    if bonus_type == 'extra_dice':
        # Gib dem Team einen Bonus-Würfel für den nächsten Zug
        team.bonus_dice_sides = max(team.bonus_dice_sides, 6)
        message = f"⭐ Bonus! {team.name} erhält einen Bonus-Würfel!"
    elif bonus_type == 'extra_move':
        # Gib dem Team eine Extra-Bewegung
        team.add_extra_moves(1)
        message = f"⭐ Bonus! {team.name} erhält eine Extra-Bewegung!"
    else:
        message = f"⭐ Bonus! {team.name} erhält einen unbekannten Bonus!"
    
    # Event erstellen
    event = GameEvent(
        game_session_id=game_session.id,
        event_type="special_field_bonus",
        description=message,
        related_team_id=team.id,
        data_json=str({
            "field_type": "bonus",
            "bonus_type": bonus_type,
            "position": team.current_position
        })
    )
    db.session.add(event)
    
    return {
        "success": True,
        "action": "bonus",
        "bonus_type": bonus_type,
        "message": message
    }


def handle_trap_field(team, game_session):
    """
    Behandelt Fallen-Felder (konfigurierbar)
    """
    config = FieldConfiguration.get_config_for_field('trap')
    if not config or not config.is_enabled:
        return {"success": False, "action": "none"}
    
    config_data = config.config_dict
    trap_effects = config_data.get('trap_effects', ['move_back', 'skip_turn', 'remove_bonus'])
    trap_effect = random.choice(trap_effects)
    
    if trap_effect == 'move_back':
        # Bewege das Team 2-3 Felder zurück
        move_distance = random.randint(2, 3)
        old_position = team.current_position
        team.current_position = max(0, team.current_position - move_distance)
        message = f"⚠️ Falle! {team.name} fällt {move_distance} Felder zurück!"
    elif trap_effect == 'skip_turn':
        # Team verliert nächsten Zug (implementiere als Blockierung für 1 Runde)
        team.is_blocked = True
        team.blocked_target_number = 1  # Kann mit jeder Zahl befreit werden
        team.blocked_turns_remaining = 1
        message = f"⚠️ Falle! {team.name} muss eine Runde aussetzen!"
    elif trap_effect == 'remove_bonus':
        # Entferne Bonus-Würfel
        team.bonus_dice_sides = 0
        message = f"⚠️ Falle! {team.name} verliert alle Bonus-Würfel!"
    else:
        message = f"⚠️ Falle! {team.name} wird von einer unbekannten Falle getroffen!"
    
    # Event erstellen
    event = GameEvent(
        game_session_id=game_session.id,
        event_type="special_field_trap",
        description=message,
        related_team_id=team.id,
        data_json=str({
            "field_type": "trap",
            "trap_effect": trap_effect,
            "position": team.current_position
        })
    )
    db.session.add(event)
    
    return {
        "success": True,
        "action": "trap",
        "trap_effect": trap_effect,
        "message": message
    }


def handle_chance_field(team, game_session):
    """
    Behandelt Ereignis-Felder (konfigurierbar)
    """
    config = FieldConfiguration.get_config_for_field('chance')
    if not config or not config.is_enabled:
        return {"success": False, "action": "none"}
    
    config_data = config.config_dict
    events = config_data.get('events', ['bonus_move', 'lose_turn', 'extra_roll'])
    event_type = random.choice(events)
    
    if event_type == 'bonus_move':
        # Bewege das Team 1-3 Felder vor
        move_distance = random.randint(1, 3)
        max_board_fields = current_app.config.get('MAX_BOARD_FIELDS', 72)
        old_position = team.current_position
        team.current_position = min(team.current_position + move_distance, max_board_fields)
        message = f"🎲 Ereignis! {team.name} bewegt sich {move_distance} Felder vor!"
    elif event_type == 'lose_turn':
        # Team verliert nächsten Zug
        team.is_blocked = True
        team.blocked_target_number = 1  # Kann mit jeder Zahl befreit werden
        team.blocked_turns_remaining = 1
        message = f"🎲 Ereignis! {team.name} verliert den nächsten Zug!"
    elif event_type == 'extra_roll':
        # Team erhält Extra-Würfelwurf
        team.add_extra_moves(1)
        message = f"🎲 Ereignis! {team.name} erhält einen Extra-Würfelwurf!"
    else:
        message = f"🎲 Ereignis! {team.name} erlebt ein unbekanntes Ereignis!"
    
    # Event erstellen
    event = GameEvent(
        game_session_id=game_session.id,
        event_type="special_field_chance",
        description=message,
        related_team_id=team.id,
        data_json=str({
            "field_type": "chance",
            "event_type": event_type,
            "position": team.current_position
        })
    )
    db.session.add(event)
    
    return {
        "success": True,
        "action": "chance",
        "event_type": event_type,
        "message": message
    }


def get_all_special_field_positions(max_fields=73):
    """
    Gibt alle Positionen der Sonderfelder zurück basierend auf FieldConfiguration
    Nützlich für Frontend-Visualisierung
    """
    special_positions = {}
    
    # Alle aktivierten Konfigurationen laden
    field_configs = FieldConfiguration.get_all_enabled()
    
    for config in field_configs:
        if config.field_type in ['normal']:
            continue  # Normale Felder überspringen
        
        positions = []
        
        if config.field_type == 'start':
            positions = [0]
        elif config.field_type == 'goal':
            positions = [max_fields - 1]
        elif config.frequency_type == 'modulo' and config.frequency_value > 0:
            # Modulo-basierte Felder
            for pos in range(max_fields):
                if pos > 0 and pos < max_fields - 1:  # Nicht Start oder Ziel
                    if pos % config.frequency_value == 0:
                        positions.append(pos)
        elif config.frequency_type == 'fixed_positions':
            # Fest definierte Positionen
            fixed_positions = config.config_dict.get('positions', [])
            positions = [pos for pos in fixed_positions if 0 <= pos < max_fields]
        
        if positions:
            special_positions[config.field_type] = positions
    
    return special_positions


def get_field_statistics():
    """
    Gibt Statistiken über die aktuellen Feld-Konfigurationen zurück
    """
    field_configs = FieldConfiguration.query.all()
    
    enabled_count = sum(1 for config in field_configs if config.is_enabled)
    disabled_count = len(field_configs) - enabled_count
    
    # Berechne Feld-Verteilung für 73 Felder
    field_distribution = {}
    special_positions = get_all_special_field_positions(73)
    
    total_special_fields = 0
    total_fields = 73
    
    # Zähle tatsächliche Felder auf dem Spielbrett
    field_counts = {}
    for position in range(total_fields):
        field_type = get_field_type_at_position(position)
        field_counts[field_type] = field_counts.get(field_type, 0) + 1
    
    # Erstelle Statistik-Objekte mit count und percentage
    for field_type, count in field_counts.items():
        percentage = (count / total_fields * 100) if total_fields > 0 else 0
        field_distribution[field_type] = {
            'count': count,
            'percentage': round(percentage, 1)
        }
        
        if field_type not in ['start', 'goal', 'normal']:
            total_special_fields += count
    
    return {
        'total_configs': len(field_configs),
        'enabled_configs': enabled_count,
        'disabled_configs': disabled_count,
        'total_fields': total_fields,
        'special_field_count': total_special_fields,
        'normal_field_count': field_counts.get('normal', 0),
        'field_distribution': field_distribution,
        'special_positions': special_positions
    }


def validate_field_configuration(config_data):
    """
    Validiert eine Feld-Konfiguration
    """
    errors = []
    
    if not config_data.get('field_type'):
        errors.append("Feld-Typ ist erforderlich")
    
    if not config_data.get('display_name'):
        errors.append("Anzeige-Name ist erforderlich")
    
    frequency_type = config_data.get('frequency_type', 'modulo')
    frequency_value = config_data.get('frequency_value', 0)
    
    if frequency_type == 'modulo' and frequency_value <= 0:
        errors.append("Modulo-Wert muss größer als 0 sein")
    
    if frequency_type == 'probability' and (frequency_value < 0 or frequency_value > 100):
        errors.append("Wahrscheinlichkeit muss zwischen 0 und 100 liegen")
    
    color_hex = config_data.get('color_hex', '')
    if not color_hex.startswith('#') or len(color_hex) != 7:
        errors.append("Farbe muss ein gültiger Hex-Code sein (#RRGGBB)")
    
    return errors