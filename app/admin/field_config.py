"""
Utility-Funktionen für das Management von Feld-Konfigurationen
Erweitert das Admin-Interface um Feld-Verwaltungsfunktionen
"""
import json
from typing import Dict, List, Optional, Any
from flask import current_app
from app.models import FieldConfiguration, db
from app.game_logic.special_fields import get_all_special_field_positions, get_field_statistics


def get_field_type_color_mapping():
    """
    Gibt eine Zuordnung von Feld-Typen zu Farben zurück
    """
    field_configs = FieldConfiguration.query.all()
    color_mapping = {}
    
    for config in field_configs:
        color_mapping[config.field_type] = {
            'color': config.color_hex,
            'emission': config.emission_hex,
            'display_name': config.display_name,
            'icon': config.icon,
            'enabled': config.is_enabled
        }
    
    return color_mapping


def get_field_preview_data(max_fields=73):
    """
    Generiert Vorschau-Daten für die Feld-Verteilung
    """
    from app.game_logic.special_fields import get_field_type_at_position
    
    field_preview = []
    field_counts = {}
    
    for position in range(max_fields):
        field_type = get_field_type_at_position(position)
        config = FieldConfiguration.get_config_for_field(field_type)
        
        field_info = {
            'position': position,
            'field_type': field_type,
            'display_name': config.display_name if config else field_type.replace('_', ' ').title(),
            'color': config.color_hex if config else '#CCCCCC',
            'icon': config.icon if config else '?',
            'enabled': config.is_enabled if config else False
        }
        
        field_preview.append(field_info)
        
        # Zähle Feld-Typen
        if field_type in field_counts:
            field_counts[field_type] += 1
        else:
            field_counts[field_type] = 1
    
    return {
        'fields': field_preview,
        'counts': field_counts,
        'total_fields': max_fields
    }


def create_default_field_config(field_type, display_name, **kwargs):
    """
    Erstellt eine Standard-Feld-Konfiguration
    """
    default_values = {
        'description': f'Standard-Konfiguration für {display_name}',
        'is_enabled': True,
        'frequency_type': 'modulo',
        'frequency_value': 10,
        'color_hex': '#81C784',
        'emission_hex': '#4CAF50',
        'icon': '⬜',
        'config_data': '{}'
    }
    
    # Überschreibe Standard-Werte mit übergebenen Parametern
    default_values.update(kwargs)
    
    config = FieldConfiguration(
        field_type=field_type,
        display_name=display_name,
        **default_values
    )
    
    return config


def update_field_config(config_id, form_data):
    """
    Aktualisiert eine Feld-Konfiguration basierend auf Formulardaten
    """
    config = FieldConfiguration.query.get_or_404(config_id)
    
    # Basis-Felder aktualisieren
    config.display_name = form_data.get('display_name', config.display_name)
    config.description = form_data.get('description', config.description)
    config.is_enabled = form_data.get('is_enabled', False)  # Checkbox-Wert
    config.frequency_type = form_data.get('frequency_type', config.frequency_type)
    config.frequency_value = int(form_data.get('frequency_value', config.frequency_value))
    config.color_hex = form_data.get('color_hex', config.color_hex)
    config.emission_hex = form_data.get('emission_hex', config.emission_hex)
    config.icon = form_data.get('icon', config.icon)
    
    # Erweiterte Konfiguration (JSON)
    extended_config = {}
    
    # Feldspezifische Konfigurationen
    if config.field_type == 'catapult_forward':
        extended_config['min_distance'] = int(form_data.get('min_distance', 3))
        extended_config['max_distance'] = int(form_data.get('max_distance', 5))
    elif config.field_type == 'catapult_backward':
        extended_config['min_distance'] = int(form_data.get('min_distance', 2))
        extended_config['max_distance'] = int(form_data.get('max_distance', 4))
    elif config.field_type == 'player_swap':
        extended_config['min_distance'] = int(form_data.get('min_distance', 3))
    elif config.field_type == 'barrier':
        target_numbers_str = form_data.get('target_numbers', '4,5,6')
        try:
            extended_config['target_numbers'] = [int(x.strip()) for x in target_numbers_str.split(',')]
        except ValueError:
            extended_config['target_numbers'] = [4, 5, 6]
    elif config.field_type == 'bonus':
        extended_config['bonus_type'] = form_data.get('bonus_type', 'extra_dice')
    elif config.field_type == 'trap':
        trap_effects = form_data.getlist('trap_effects')  # Multiple select
        if trap_effects:
            extended_config['trap_effects'] = trap_effects
        else:
            extended_config['trap_effects'] = ['move_back', 'skip_turn', 'remove_bonus']
    elif config.field_type == 'chance':
        chance_events = form_data.getlist('chance_events')  # Multiple select
        if chance_events:
            extended_config['events'] = chance_events
        else:
            extended_config['events'] = ['bonus_move', 'lose_turn', 'extra_roll']
    
    # Feste Positionen für frequency_type 'fixed_positions'
    if config.frequency_type == 'fixed_positions':
        positions_str = form_data.get('fixed_positions', '')
        try:
            extended_config['positions'] = [int(x.strip()) for x in positions_str.split(',') if x.strip()]
        except ValueError:
            extended_config['positions'] = []
    
    config.config_dict = extended_config
    
    return config


def get_frequency_type_options():
    """
    Gibt verfügbare Häufigkeits-Typen zurück
    """
    return [
        ('modulo', 'Modulo-basiert (alle X Felder)'),
        ('fixed_positions', 'Feste Positionen'),
        ('probability', 'Wahrscheinlichkeitsbasiert (%)'),
        ('default', 'Standard (für normale Felder)')
    ]


def get_field_type_templates():
    """
    Gibt Vorlagen für verschiedene Feld-Typen zurück
    """
    templates = {
        'catapult_forward': {
            'display_name': 'Katapult Vorwärts',
            'description': 'Schleudert Teams vorwärts',
            'color_hex': '#4CAF50',
            'emission_hex': '#2E7D32',
            'icon': '🚀',
            'frequency_type': 'modulo',
            'frequency_value': 15,
            'config_fields': [
                {'name': 'min_distance', 'type': 'number', 'default': 3, 'label': 'Min. Distanz'},
                {'name': 'max_distance', 'type': 'number', 'default': 5, 'label': 'Max. Distanz'}
            ]
        },
        'catapult_backward': {
            'display_name': 'Katapult Rückwärts',
            'description': 'Schleudert Teams rückwärts',
            'color_hex': '#F44336',
            'emission_hex': '#C62828',
            'icon': '💥',
            'frequency_type': 'modulo',
            'frequency_value': 13,
            'config_fields': [
                {'name': 'min_distance', 'type': 'number', 'default': 2, 'label': 'Min. Distanz'},
                {'name': 'max_distance', 'type': 'number', 'default': 4, 'label': 'Max. Distanz'}
            ]
        },
        'player_swap': {
            'display_name': 'Spieler-Tausch',
            'description': 'Tauscht Positionen zwischen Teams',
            'color_hex': '#2196F3',
            'emission_hex': '#1565C0',
            'icon': '🔄',
            'frequency_type': 'modulo',
            'frequency_value': 17,
            'config_fields': [
                {'name': 'min_distance', 'type': 'number', 'default': 3, 'label': 'Min. Abstand für Tausch'}
            ]
        },
        'barrier': {
            'display_name': 'Sperren-Feld',
            'description': 'Blockiert Teams bis bestimmte Zahl gewürfelt wird',
            'color_hex': '#9E9E9E',
            'emission_hex': '#424242',
            'icon': '🚧',
            'frequency_type': 'modulo',
            'frequency_value': 19,
            'config_fields': [
                {'name': 'target_numbers', 'type': 'text', 'default': '4,5,6', 'label': 'Ziel-Zahlen (komma-getrennt)'}
            ]
        },
        'bonus': {
            'display_name': 'Bonusfeld',
            'description': 'Gibt Teams einen Vorteil',
            'color_hex': '#FFD54F',
            'emission_hex': '#FFA000',
            'icon': '⭐',
            'frequency_type': 'modulo',
            'frequency_value': 8,
            'config_fields': [
                {'name': 'bonus_type', 'type': 'select', 'default': 'extra_dice', 'label': 'Bonus-Typ',
                 'options': [('extra_dice', 'Extra-Würfel'), ('extra_move', 'Extra-Bewegung')]}
            ]
        },
        'trap': {
            'display_name': 'Falle',
            'description': 'Schadet Teams oder blockiert sie',
            'color_hex': '#E57373',
            'emission_hex': '#D32F2F',
            'icon': '⚠️',
            'frequency_type': 'modulo',
            'frequency_value': 25,
            'config_fields': [
                {'name': 'trap_effects', 'type': 'multiselect', 'default': ['move_back', 'skip_turn', 'remove_bonus'],
                 'label': 'Fallen-Effekte',
                 'options': [('move_back', 'Zurück bewegen'), ('skip_turn', 'Zug überspringen'), ('remove_bonus', 'Bonus entfernen')]}
            ]
        },
        'chance': {
            'display_name': 'Ereignisfeld',
            'description': 'Zufällige Ereignisse',
            'color_hex': '#AED581',
            'emission_hex': '#689F38',
            'icon': '🎲',
            'frequency_type': 'modulo',
            'frequency_value': 20,
            'config_fields': [
                {'name': 'chance_events', 'type': 'multiselect', 'default': ['bonus_move', 'lose_turn', 'extra_roll'],
                 'label': 'Mögliche Ereignisse',
                 'options': [('bonus_move', 'Bonus-Bewegung'), ('lose_turn', 'Zug verlieren'), ('extra_roll', 'Extra-Wurf')]}
            ]
        },
        'minigame': {
            'display_name': 'Minispiel',
            'description': 'Startet Minispiele oder Fragen',
            'color_hex': '#BA68C8',
            'emission_hex': '#8E24AA',
            'icon': '🎮',
            'frequency_type': 'modulo',
            'frequency_value': 12,
            'config_fields': []
        }
    }
    
    return templates


def export_field_configurations():
    """
    Exportiert alle Feld-Konfigurationen als JSON
    """
    configs = FieldConfiguration.query.all()
    export_data = []
    
    for config in configs:
        export_data.append({
            'field_type': config.field_type,
            'display_name': config.display_name,
            'description': config.description,
            'is_enabled': config.is_enabled,
            'frequency_type': config.frequency_type,
            'frequency_value': config.frequency_value,
            'color_hex': config.color_hex,
            'emission_hex': config.emission_hex,
            'icon': config.icon,
            'config_data': config.config_data
        })
    
    return export_data


def import_field_configurations(import_data):
    """
    Importiert Feld-Konfigurationen aus JSON
    """
    imported_count = 0
    errors = []
    
    for config_data in import_data:
        try:
            field_type = config_data.get('field_type')
            if not field_type:
                errors.append("Feld-Typ fehlt in Import-Daten")
                continue
            
            # Prüfe ob Konfiguration bereits existiert
            existing_config = FieldConfiguration.query.filter_by(field_type=field_type).first()
            
            if existing_config:
                # Aktualisiere existierende Konfiguration
                for key, value in config_data.items():
                    if hasattr(existing_config, key):
                        setattr(existing_config, key, value)
            else:
                # Erstelle neue Konfiguration
                new_config = FieldConfiguration(**config_data)
                db.session.add(new_config)
            
            imported_count += 1
            
        except Exception as e:
            errors.append(f"Fehler beim Importieren von {config_data.get('field_type', 'unbekannt')}: {str(e)}")
    
    if imported_count > 0:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            errors.append(f"Fehler beim Speichern: {str(e)}")
            imported_count = 0
    
    return {
        'imported_count': imported_count,
        'errors': errors
    }


def reset_to_default_configurations():
    """
    Setzt alle Feld-Konfigurationen auf Standard-Werte zurück
    """
    try:
        # Lösche alle existierenden Konfigurationen
        FieldConfiguration.query.delete()
        
        # Erstelle Standard-Konfigurationen
        FieldConfiguration.initialize_default_configs()
        
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Fehler beim Zurücksetzen der Feld-Konfigurationen: {e}")
        return False


def validate_field_conflicts():
    """
    Prüft auf Konflikte zwischen verschiedenen Feld-Konfigurationen
    """
    conflicts = []
    positions_map = {}
    
    # Sammle alle Positionen für jeden Feld-Typ
    special_positions = get_all_special_field_positions(73)
    
    for field_type, positions in special_positions.items():
        for position in positions:
            if position in positions_map:
                conflicts.append({
                    'position': position,
                    'field_types': [positions_map[position], field_type]
                })
            else:
                positions_map[position] = field_type
    
    return conflicts


def get_field_usage_statistics():
    """
    Gibt Nutzungsstatistiken für Feld-Typen zurück
    """
    from app.models import GameEvent
    
    # Hole alle Sonderfeld-Events aus der Datenbank
    field_events = GameEvent.query.filter(
        GameEvent.event_type.like('special_field_%')
    ).all()
    
    usage_stats = {}
    
    for event in field_events:
        # Extrahiere Feld-Typ aus Event-Typ
        if event.event_type.startswith('special_field_'):
            field_action = event.event_type.replace('special_field_', '')
            
            # Mappe Aktion zu Feld-Typ
            field_type_mapping = {
                'catapult_forward': 'catapult_forward',
                'catapult_backward': 'catapult_backward',
                'player_swap': 'player_swap',
                'barrier_set': 'barrier',
                'barrier_released': 'barrier',
                'barrier_failed': 'barrier',
                'bonus': 'bonus',
                'trap': 'trap',
                'chance': 'chance'
            }
            
            field_type = field_type_mapping.get(field_action, 'unknown')
            
            if field_type in usage_stats:
                usage_stats[field_type] += 1
            else:
                usage_stats[field_type] = 1
    
    return usage_stats