#!/usr/bin/env python3
"""
Migration Script: Add selected_players field to GameSession table
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import GameSession
from sqlalchemy import text

def add_selected_players_field():
    """Add selected_players field to GameSession table"""
    
    app = create_app()
    
    with app.app_context():
        print("Starting migration: Add selected_players field to GameSession...")
        
        try:
            # Check if column already exists
            result = db.engine.execute(text(
                "PRAGMA table_info(game_session);"
            )).fetchall()
            
            columns = [row[1] for row in result]
            
            if 'selected_players' in columns:
                print("Column 'selected_players' already exists. Migration skipped.")
                return
            
            # Add the new column
            db.engine.execute(text(
                "ALTER TABLE game_session ADD COLUMN selected_players TEXT;"
            ))
            
            print("✅ Successfully added 'selected_players' column to game_session table.")
            
            # Test the new column by trying to access it
            test_session = GameSession.query.first()
            if test_session:
                test_session.get_selected_players()
                print("✅ New methods are working correctly.")
            
            print("Migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Error during migration: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    add_selected_players_field()