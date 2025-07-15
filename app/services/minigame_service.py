"""
Minigame management service for centralized minigame operations.
"""
from app.models import MinigameFolder, GameRound, GameSession, db
from app.utils.validation import sanitize_string, ValidationError
from flask import current_app
import json
import os
import random


class MinigameService:
    """Service class for minigame-related operations."""
    
    @staticmethod
    def get_all_folders():
        """
        Get all minigame folders.
        
        Returns:
            List of MinigameFolder objects
        """
        return MinigameFolder.query.order_by(MinigameFolder.name).all()
    
    @staticmethod
    def get_folder_by_id(folder_id):
        """
        Get minigame folder by ID.
        
        Args:
            folder_id: Folder ID
            
        Returns:
            MinigameFolder object or None
        """
        return MinigameFolder.query.get(folder_id)
    
    @staticmethod
    def create_folder(name, description=None, folder_path=None):
        """
        Create a new minigame folder.
        
        Args:
            name: Folder name
            description: Folder description (optional)
            folder_path: Folder path (optional)
            
        Returns:
            MinigameFolder object
            
        Raises:
            ValidationError: If creation fails
        """
        # Sanitize inputs
        name = sanitize_string(name, max_length=100)
        if not name:
            raise ValidationError("Folder name cannot be empty")
        
        # Check if folder already exists
        if MinigameFolder.query.filter_by(name=name).first():
            raise ValidationError("Folder name already exists")
        
        if description:
            description = sanitize_string(description, max_length=500)
        
        if not folder_path:
            folder_path = name
        
        folder = MinigameFolder(
            name=name,
            description=description,
            folder_path=folder_path
        )
        
        try:
            db.session.add(folder)
            db.session.commit()
            current_app.logger.info(f"Minigame folder '{name}' created")
            return folder
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating minigame folder: {str(e)}")
            raise ValidationError("Failed to create minigame folder")
    
    @staticmethod
    def update_folder(folder_id, name=None, description=None):
        """
        Update a minigame folder.
        
        Args:
            folder_id: Folder ID
            name: New name (optional)
            description: New description (optional)
            
        Returns:
            Updated MinigameFolder object
            
        Raises:
            ValidationError: If update fails
        """
        folder = MinigameFolder.query.get(folder_id)
        if not folder:
            raise ValidationError("Folder not found")
        
        if name is not None:
            name = sanitize_string(name, max_length=100)
            if not name:
                raise ValidationError("Folder name cannot be empty")
            
            # Check if name already exists (excluding current folder)
            existing = MinigameFolder.query.filter_by(name=name).first()
            if existing and existing.id != folder_id:
                raise ValidationError("Folder name already exists")
            
            folder.name = name
        
        if description is not None:
            folder.description = sanitize_string(description, max_length=500)
        
        try:
            db.session.commit()
            current_app.logger.info(f"Minigame folder '{folder.name}' updated")
            return folder
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating minigame folder: {str(e)}")
            raise ValidationError("Failed to update minigame folder")
    
    @staticmethod
    def delete_folder(folder_id):
        """
        Delete a minigame folder.
        
        Args:
            folder_id: Folder ID
            
        Raises:
            ValidationError: If deletion fails
        """
        folder = MinigameFolder.query.get(folder_id)
        if not folder:
            raise ValidationError("Folder not found")
        
        # Check if folder is being used by any game rounds
        rounds_using_folder = GameRound.query.filter_by(minigame_folder_id=folder_id).count()
        if rounds_using_folder > 0:
            raise ValidationError("Cannot delete folder - it is being used by game rounds")
        
        try:
            db.session.delete(folder)
            db.session.commit()
            current_app.logger.info(f"Minigame folder '{folder.name}' deleted")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting minigame folder: {str(e)}")
            raise ValidationError("Failed to delete minigame folder")
    
    @staticmethod
    def get_folder_minigames(folder_id):
        """
        Get all minigames from a folder.
        
        Args:
            folder_id: Folder ID
            
        Returns:
            List of minigame data
            
        Raises:
            ValidationError: If folder not found
        """
        folder = MinigameFolder.query.get(folder_id)
        if not folder:
            raise ValidationError("Folder not found")
        
        # Load minigames from JSON file
        minigames_file = os.path.join(
            current_app.instance_path,
            'app', 'static', 'minigame_folders',
            folder.folder_path,
            'minigames.json'
        )
        
        if not os.path.exists(minigames_file):
            return []
        
        try:
            with open(minigames_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('minigames', [])
        except (json.JSONDecodeError, IOError) as e:
            current_app.logger.error(f"Error reading minigames file: {str(e)}")
            return []
    
    @staticmethod
    def get_random_minigame(folder_id, exclude_played=None):
        """
        Get a random minigame from a folder.
        
        Args:
            folder_id: Folder ID
            exclude_played: List of already played minigame IDs
            
        Returns:
            Random minigame data or None
            
        Raises:
            ValidationError: If folder not found
        """
        minigames = MinigameService.get_folder_minigames(folder_id)
        
        if not minigames:
            return None
        
        # Filter out already played minigames
        if exclude_played:
            available_minigames = [
                mg for mg in minigames 
                if mg.get('id') not in exclude_played
            ]
        else:
            available_minigames = minigames
        
        if not available_minigames:
            # All minigames have been played, reset and use all
            available_minigames = minigames
        
        return random.choice(available_minigames)
    
    @staticmethod
    def get_all_rounds():
        """
        Get all game rounds.
        
        Returns:
            List of GameRound objects
        """
        return GameRound.query.order_by(GameRound.name).all()
    
    @staticmethod
    def get_active_round():
        """
        Get the currently active game round.
        
        Returns:
            GameRound object or None
        """
        return GameRound.query.filter_by(is_active=True).first()
    
    @staticmethod
    def create_round(name, description=None, minigame_folder_id=None):
        """
        Create a new game round.
        
        Args:
            name: Round name
            description: Round description (optional)
            minigame_folder_id: Minigame folder ID (optional)
            
        Returns:
            GameRound object
            
        Raises:
            ValidationError: If creation fails
        """
        # Sanitize inputs
        name = sanitize_string(name, max_length=100)
        if not name:
            raise ValidationError("Round name cannot be empty")
        
        # Check if round already exists
        if GameRound.query.filter_by(name=name).first():
            raise ValidationError("Round name already exists")
        
        if description:
            description = sanitize_string(description, max_length=500)
        
        # Validate minigame folder
        if minigame_folder_id:
            folder = MinigameFolder.query.get(minigame_folder_id)
            if not folder:
                raise ValidationError("Invalid minigame folder")
        
        round_obj = GameRound(
            name=name,
            description=description,
            minigame_folder_id=minigame_folder_id,
            is_active=False
        )
        
        try:
            db.session.add(round_obj)
            db.session.commit()
            current_app.logger.info(f"Game round '{name}' created")
            return round_obj
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating game round: {str(e)}")
            raise ValidationError("Failed to create game round")
    
    @staticmethod
    def activate_round(round_id):
        """
        Activate a game round (deactivate all others).
        
        Args:
            round_id: Round ID
            
        Raises:
            ValidationError: If round not found
        """
        round_obj = GameRound.query.get(round_id)
        if not round_obj:
            raise ValidationError("Round not found")
        
        try:
            # Deactivate all rounds
            GameRound.query.update({GameRound.is_active: False})
            
            # Activate selected round
            round_obj.is_active = True
            
            db.session.commit()
            current_app.logger.info(f"Game round '{round_obj.name}' activated")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error activating game round: {str(e)}")
            raise ValidationError("Failed to activate game round")
    
    @staticmethod
    def update_game_session_minigame(session_id, minigame_name, minigame_description=None):
        """
        Update the current minigame in a game session.
        
        Args:
            session_id: Session ID
            minigame_name: Minigame name
            minigame_description: Minigame description (optional)
            
        Raises:
            ValidationError: If session not found
        """
        session = GameSession.query.get(session_id)
        if not session:
            raise ValidationError("Game session not found")
        
        session.current_minigame_name = sanitize_string(minigame_name, max_length=200)
        if minigame_description:
            session.current_minigame_description = sanitize_string(minigame_description, max_length=1000)
        
        try:
            db.session.commit()
            current_app.logger.info(f"Game session minigame updated: {minigame_name}")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating game session minigame: {str(e)}")
            raise ValidationError("Failed to update game session minigame")