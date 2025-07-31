#!/usr/bin/env python3
"""
Debug Player Data Script
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, Team

app = create_app()
with app.app_context():
    # Hole alle Teams
    teams = Team.query.all()
    print(f"Gefundene Teams: {len(teams)}")
    
    for team in teams:
        print(f"\n=== Team: {team.name} ===")
        print(f"Members: {team.members}")
        print(f"Player Config: {team.player_config}")
        print(f"Profile Images: {team.profile_images}")
        
        # Teste get_player_by_name für alle Spieler
        if team.members:
            players = [m.strip() for m in team.members.split(',') if m.strip()]
            for player_name in players:
                print(f"\n--- Player: {player_name} ---")
                player_info = team.get_player_by_name(player_name)
                print(f"get_player_by_name result: {player_info}")
                
                # Einzeln testen
                player_config = team.get_player_config()
                profile_images = team.get_profile_images()
                print(f"Player config: {player_config}")
                print(f"Profile images: {profile_images}")
                print(f"Player in config: {player_name in player_config}")
                print(f"Player in images: {player_name in profile_images}")
                if player_name in player_config:
                    print(f"Config for {player_name}: {player_config[player_name]}")