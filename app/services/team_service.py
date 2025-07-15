"""
Team management service for centralized team operations.
"""
from app.models import Team, Character, GameSession, db
from app.utils.validation import validate_team_name, validate_member_list, ValidationError
from werkzeug.security import generate_password_hash
from flask import current_app
import random
import string


class TeamService:
    """Service class for team-related operations."""
    
    @staticmethod
    def create_team(name, password, character_id, members_str=None):
        """
        Create a new team with validation.
        
        Args:
            name: Team name
            password: Team password
            character_id: Character ID
            members_str: Comma/newline separated member names
            
        Returns:
            Team object if successful
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate team name
        name = validate_team_name(name)
        
        # Check if team name already exists
        if Team.query.filter_by(name=name).first():
            raise ValidationError("Team name already exists")
        
        # Validate members
        members = []
        if members_str:
            members = validate_member_list(members_str)
        
        # Validate character
        character = Character.query.get(character_id)
        if not character:
            raise ValidationError("Invalid character selected")
        
        if character.is_selected:
            raise ValidationError("Character is already selected")
        
        # Create team
        team = Team(name=name)
        team.set_password(password)
        team.character_id = character_id
        
        # Set members
        if members:
            team.members = ', '.join(members)
        
        # Mark character as selected
        character.is_selected = True
        
        try:
            db.session.add(team)
            db.session.commit()
            current_app.logger.info(f"Team '{name}' created successfully")
            return team
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating team: {str(e)}")
            raise ValidationError("Failed to create team")
    
    @staticmethod
    def update_team(team_id, name=None, password=None, character_id=None, members_str=None, position=None):
        """
        Update an existing team.
        
        Args:
            team_id: Team ID
            name: New team name (optional)
            password: New password (optional)
            character_id: New character ID (optional)
            members_str: New members string (optional)
            position: New position (optional)
            
        Returns:
            Updated team object
            
        Raises:
            ValidationError: If validation fails
        """
        team = Team.query.get(team_id)
        if not team:
            raise ValidationError("Team not found")
        
        # Update name if provided
        if name is not None:
            name = validate_team_name(name)
            
            # Check if name already exists (excluding current team)
            existing_team = Team.query.filter_by(name=name).first()
            if existing_team and existing_team.id != team_id:
                raise ValidationError("Team name already exists")
            
            team.name = name
        
        # Update password if provided
        if password is not None:
            team.set_password(password)
        
        # Update character if provided
        if character_id is not None:
            new_character = Character.query.get(character_id)
            if not new_character:
                raise ValidationError("Invalid character selected")
            
            # If changing character, free up old one and mark new one as selected
            if team.character_id != character_id:
                if team.character:
                    team.character.is_selected = False
                
                if new_character.is_selected:
                    raise ValidationError("Character is already selected")
                
                new_character.is_selected = True
                team.character_id = character_id
        
        # Update members if provided
        if members_str is not None:
            members = validate_member_list(members_str)
            team.members = ', '.join(members) if members else None
        
        # Update position if provided
        if position is not None:
            if not isinstance(position, int) or position < 0 or position > 72:
                raise ValidationError("Invalid position")
            team.current_position = position
        
        try:
            db.session.commit()
            current_app.logger.info(f"Team '{team.name}' updated successfully")
            return team
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating team: {str(e)}")
            raise ValidationError("Failed to update team")
    
    @staticmethod
    def delete_team(team_id):
        """
        Delete a team and free up its character.
        
        Args:
            team_id: Team ID
            
        Raises:
            ValidationError: If team not found or deletion fails
        """
        team = Team.query.get(team_id)
        if not team:
            raise ValidationError("Team not found")
        
        # Free up character
        if team.character:
            team.character.is_selected = False
        
        try:
            db.session.delete(team)
            db.session.commit()
            current_app.logger.info(f"Team '{team.name}' deleted successfully")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting team: {str(e)}")
            raise ValidationError("Failed to delete team")
    
    @staticmethod
    def get_team_by_name(name):
        """
        Get team by name.
        
        Args:
            name: Team name
            
        Returns:
            Team object or None
        """
        return Team.query.filter_by(name=name).first()
    
    @staticmethod
    def get_all_teams():
        """
        Get all teams ordered by name.
        
        Returns:
            List of team objects
        """
        return Team.query.order_by(Team.name).all()
    
    @staticmethod
    def generate_team_password(length=6):
        """
        Generate a random team password.
        
        Args:
            length: Password length
            
        Returns:
            Random password string
        """
        # Use uppercase letters and numbers for readability
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
    
    @staticmethod
    def reset_team_positions():
        """
        Reset all team positions to 0.
        """
        try:
            Team.query.update({Team.current_position: 0})
            db.session.commit()
            current_app.logger.info("All team positions reset to 0")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error resetting team positions: {str(e)}")
            raise ValidationError("Failed to reset team positions")
    
    @staticmethod
    def get_team_ranking():
        """
        Get teams ordered by position (highest first).
        
        Returns:
            List of teams ordered by position
        """
        return Team.query.order_by(Team.current_position.desc()).all()
    
    @staticmethod
    def validate_team_login(name, password):
        """
        Validate team login credentials.
        
        Args:
            name: Team name
            password: Team password
            
        Returns:
            Team object if valid, None otherwise
        """
        try:
            name = validate_team_name(name)
        except ValidationError:
            return None
        
        team = Team.query.filter_by(name=name).first()
        if team and team.check_password(password):
            return team
        
        return None