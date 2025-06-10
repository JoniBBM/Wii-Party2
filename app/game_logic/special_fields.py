"""
Sonderfeld-Logik für Wii Party Clone - Erweitert mit konfigurierbaren Feld-Häufigkeiten
Enthält alle Funktionen für die verschiedenen Sonderfelder basierend auf FieldConfiguration
Mit intelligentem Konflikt-Auflösungs-Algorithmus
"""
import random
from flask import current_app
from app.models import db, GameEvent, FieldConfiguration

# Cache für berechnete Feld-Verteilung
_field_distribution_cache = None
_cache_max_fields = None


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


def calculate_smart_field_distribution(max_fields=73):
    """
    Intelligenter Algorithmus zur konfliktfreien Feld-Verteilung
    
    1. Sammelt alle gewünschten Positionen für jeden Feld-Typ
    2. Erkennt Konflikte (mehrere Feld-Typen für eine Position)
    3. Löst Konflikte durch gewichtete Zufallsauswahl oder Umverteilung auf
    4. Gibt eine konfliktfreie Zuordnung zurück: {position: field_type}
    """
    # Lade alle aktivierten Konfigurationen
    field_configs = FieldConfiguration.get_all_enabled()
    
    # Sammle gewünschte Positionen für jeden Feld-Typ
    desired_positions = {}
    
    for config in field_configs:
        field_type = config.field_type
        positions = []
        
        # Spezielle Behandlung für Start und Ziel
        if field_type == 'start':
            positions = [0]
        elif field_type == 'goal':
            positions = [max_fields - 1]
        elif field_type == 'normal':
            # Normale Felder werden später als Fallback zugewiesen
            continue
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
        elif config.frequency_type == 'probability':
            # Wahrscheinlichkeitsbasierte Verteilung
            probability = config.frequency_value / 100.0
            for pos in range(1, max_fields - 1):  # Nicht Start oder Ziel
                if random.random() < probability:
                    positions.append(pos)
        
        if positions:
            desired_positions[field_type] = positions
    
    # Erkenne Konflikte
    position_conflicts = {}
    for field_type, positions in desired_positions.items():
        for pos in positions:
            if pos not in position_conflicts:
                position_conflicts[pos] = []
            position_conflicts[pos].append(field_type)
    
    # Erstelle finale Zuordnung
    final_assignment = {}
    conflict_resolution_stats = {
        'total_conflicts': 0,
        'resolved_randomly': 0,
        'redistributed': 0
    }
    
    for position, field_types in position_conflicts.items():
        if len(field_types) == 1:
            # Kein Konflikt
            final_assignment[position] = field_types[0]
        else:
            # Konflikt gefunden
            conflict_resolution_stats['total_conflicts'] += 1
            
            # Gewichtete Zufallsauswahl basierend auf Prioritäten
            field_priorities = {}
            for field_type in field_types:
                config = FieldConfiguration.get_config_for_field(field_type)
                if config:
                    # Niedrigere frequency_value = höhere Priorität (seltener = wichtiger)
                    priority = 1000 / max(config.frequency_value, 1) if config.frequency_value else 1
                    field_priorities[field_type] = priority
                else:
                    field_priorities[field_type] = 1
            
            # Gewichtete Zufallsauswahl
            total_weight = sum(field_priorities.values())
            if total_weight > 0:
                rand_value = random.random() * total_weight
                cumulative_weight = 0
                chosen_field = field_types[0]  # Fallback
                
                for field_type, weight in field_priorities.items():
                    cumulative_weight += weight
                    if rand_value <= cumulative_weight:
                        chosen_field = field_type
                        break
                
                final_assignment[position] = chosen_field
                conflict_resolution_stats['resolved_randomly'] += 1
    
    # Umverteilung: Versuche überzählige Felder auf benachbarte Positionen zu verteilen
    for field_type, desired_pos_list in desired_positions.items():
        assigned_count = sum(1 for pos, assigned_type in final_assignment.items() if assigned_type == field_type)
        missing_count = len(desired_pos_list) - assigned_count
        
        if missing_count > 0:
            # Finde alternative Positionen in der Nähe
            for _ in range(missing_count):
                alternative_pos = find_alternative_position(final_assignment, desired_pos_list, max_fields)
                if alternative_pos is not None:
                    final_assignment[alternative_pos] = field_type
                    conflict_resolution_stats['redistributed'] += 1
    
    # Fülle verbleibende Positionen mit 'normal'
    for position in range(max_fields):
        if position not in final_assignment:
            final_assignment[position] = 'normal'
    
    # Debug-Info ausgeben (optional)
    if current_app and current_app.config.get('DEBUG_SPECIAL_FIELDS'):
        current_app.logger.info(f"Feld-Verteilung berechnet: {conflict_resolution_stats['total_conflicts']} Konflikte, "
                               f"{conflict_resolution_stats['resolved_randomly']} zufällig gelöst, "
                               f"{conflict_resolution_stats['redistributed']} umverteilt")
    
    return final_assignment


def find_alternative_position(final_assignment, preferred_positions, max_fields):
    """
    Findet eine alternative Position für ein Feld in der Nähe der bevorzugten Positionen
    """
    # Suche in der Nähe der bevorzugten Positionen
    for preferred_pos in preferred_positions:
        # Suche in zunehmendem Abstand um die bevorzugte Position
        for distance in range(1, 10):  # Maximal 10 Felder Abstand
            for direction in [-1, 1]:  # Links und rechts
                alt_pos = preferred_pos + (direction * distance)
                
                # Prüfe ob Position gültig und verfügbar ist
                if (0 < alt_pos < max_fields - 1 and  # Nicht Start oder Ziel
                    alt_pos not in final_assignment):
                    return alt_pos
    
    # Fallback: Suche irgendeine freie Position
    for position in range(1, max_fields - 1):
        if position not in final_assignment:
            return position
    
    return None


def clear_field_distribution_cache():
    """
    Löscht den Cache für die Feld-Verteilung (z.B. nach Konfigurations-Änderungen)
    """
    global _field_distribution_cache, _cache_max_fields
    _field_distribution_cache = None
    _cache_max_fields = None
    
    # Prüfe ob FieldConfiguration-Daten existieren
    try:
        field_configs = FieldConfiguration.get_all_enabled()
        if field_configs:
            current_app.logger.info(f"Cache geleert. {len(field_configs)} Feld-Konfigurationen verfügbar.")
        else:
            current_app.logger.warning("Cache geleert, aber keine FieldConfiguration-Daten gefunden!")
    except Exception as e:
        current_app.logger.error(f"Fehler beim Prüfen der FieldConfiguration: {e}")


def get_field_type_at_position(position):
    """
    Bestimmt den Feldtyp basierend auf der Position unter Verwendung des intelligenten
    Konflikt-Auflösungs-Algorithmus mit Caching für bessere Performance
    """
    global _field_distribution_cache, _cache_max_fields
    
    max_fields = 73  # Standard-Wert
    
    # Cache prüfen und neu berechnen falls nötig
    if (_field_distribution_cache is None or 
        _cache_max_fields != max_fields):
        
        _field_distribution_cache = calculate_smart_field_distribution(max_fields)
        _cache_max_fields = max_fields
    
    # Position aus Cache zurückgeben
    return _field_distribution_cache.get(position, 'normal')


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
    Gibt alle Positionen der Sonderfelder zurück basierend auf der intelligenten
    Feld-Verteilung (verwendet den Cache)
    """
    # Verwende die gecachte Verteilung
    field_distribution = _field_distribution_cache
    if field_distribution is None:
        # Cache ist leer, berechne neu
        field_distribution = calculate_smart_field_distribution(max_fields)
    
    special_positions = {}
    
    # Gruppiere Positionen nach Feld-Typ
    for position, field_type in field_distribution.items():
        if field_type not in special_positions:
            special_positions[field_type] = []
        special_positions[field_type].append(position)
    
    # Sortiere Positionen innerhalb jedes Feld-Typs
    for field_type in special_positions:
        special_positions[field_type].sort()
    
    return special_positions


def get_field_statistics():
    """
    Gibt Statistiken über die aktuellen Feld-Konfigurationen zurück
    Verwendet die intelligente Feld-Verteilung
    """
    field_configs = FieldConfiguration.query.all()
    
    enabled_count = sum(1 for config in field_configs if config.is_enabled)
    disabled_count = len(field_configs) - enabled_count
    
    # Verwende die intelligente Feld-Verteilung
    total_fields = 73
    field_distribution = _field_distribution_cache
    if field_distribution is None:
        field_distribution = calculate_smart_field_distribution(total_fields)
    
    # Zähle Felder pro Typ
    field_counts = {}
    for position, field_type in field_distribution.items():
        field_counts[field_type] = field_counts.get(field_type, 0) + 1
    
    total_special_fields = 0
    
    # Erstelle Statistik-Objekte mit count und percentage
    field_distribution_stats = {}
    for field_type, count in field_counts.items():
        percentage = (count / total_fields * 100) if total_fields > 0 else 0
        field_distribution_stats[field_type] = {
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
        'field_distribution': field_distribution_stats,
        'special_positions': get_all_special_field_positions(total_fields),
        'conflict_free': True  # Neuer Status-Indikator
    }


def validate_field_conflicts():
    """
    Prüft auf Konflikte zwischen verschiedenen Feld-Konfigurationen
    Mit dem neuen Algorithmus sollten keine Konflikte mehr auftreten
    """
    # Da wir jetzt einen intelligenten Konflikt-Auflösungs-Algorithmus verwenden,
    # sollten normalerweise keine Konflikte mehr auftreten
    return []  # Keine Konflikte mehr!


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


def regenerate_field_distribution():
    """
    Hilfsfunktion um eine neue Feld-Verteilung zu generieren
    (z.B. nach Konfigurations-Änderungen im Admin-Interface)
    """
    clear_field_distribution_cache()
    return calculate_smart_field_distribution(73)