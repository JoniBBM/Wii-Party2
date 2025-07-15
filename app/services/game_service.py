"""
Game management service for centralized game operations.
"""
from app.models import GameSession, GameEvent, Team, GameRound, db
from app.utils.validation import validate_position, validate_dice_result, ValidationError
from flask import current_app
import json
import random
from datetime import datetime


class GameService:
    """Service class for game-related operations."""
    
    @staticmethod
    def get_active_session():
        """
        Get the currently active game session.
        
        Returns:
            GameSession object or None
        """
        return GameSession.query.filter_by(is_active=True).first()
    
    @staticmethod
    def create_game_session(game_round_id):
        """
        Create a new game session.
        
        Args:
            game_round_id: Game round ID
            
        Returns:
            GameSession object
            
        Raises:
            ValidationError: If creation fails
        """
        # Deactivate any existing sessions
        GameSession.query.update({GameSession.is_active: False})
        
        # Create new session
        session = GameSession(
            is_active=True,
            current_phase='SETUP',
            game_round_id=game_round_id
        )
        
        try:
            db.session.add(session)
            db.session.commit()
            current_app.logger.info(f"New game session created with round {game_round_id}")
            return session
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating game session: {str(e)}")
            raise ValidationError("Failed to create game session")
    
    @staticmethod
    def end_game_session(session_id):
        """
        End a game session.
        
        Args:
            session_id: Session ID
            
        Raises:
            ValidationError: If session not found
        """
        session = GameSession.query.get(session_id)
        if not session:
            raise ValidationError("Game session not found")
        
        session.is_active = False
        
        try:
            db.session.commit()
            current_app.logger.info(f"Game session {session_id} ended")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error ending game session: {str(e)}")
            raise ValidationError("Failed to end game session")
    
    @staticmethod
    def update_team_position(team_id, new_position, dice_result=None):
        """
        Update team position with validation.
        
        Args:
            team_id: Team ID
            new_position: New position
            dice_result: Dice result (optional)
            
        Returns:
            Updated team object
            
        Raises:
            ValidationError: If validation fails
        """
        team = Team.query.get(team_id)
        if not team:
            raise ValidationError("Team not found")
        
        # Validate position
        new_position = validate_position(new_position)
        
        # Validate dice result if provided
        if dice_result is not None:
            dice_result = validate_dice_result(dice_result)
        
        old_position = team.current_position
        team.current_position = new_position
        
        if dice_result is not None:
            team.last_dice_result = dice_result
        
        try:
            db.session.commit()
            
            # Log the position change
            GameService.log_game_event(
                event_type='POSITION_CHANGE',
                team_id=team_id,
                data={
                    'old_position': old_position,
                    'new_position': new_position,
                    'dice_result': dice_result
                }
            )
            
            current_app.logger.info(f"Team {team.name} moved from {old_position} to {new_position}")
            return team
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating team position: {str(e)}")
            raise ValidationError("Failed to update team position")
    
    @staticmethod
    def roll_dice_for_team(team_id, admin_user_id=None):
        """
        Roll dice for a team.
        
        Args:
            team_id: Team ID
            admin_user_id: Admin user ID (optional)
            
        Returns:
            Dict with dice result and new position
            
        Raises:
            ValidationError: If team not found or roll fails
        """
        team = Team.query.get(team_id)
        if not team:
            raise ValidationError("Team not found")
        
        # Roll dice (1-6)
        dice_result = random.randint(1, 6)
        
        # Add bonus dice if applicable
        bonus_dice = team.bonus_dice_sides if team.bonus_dice_sides else 0
        total_roll = dice_result + bonus_dice
        
        # Calculate new position
        old_position = team.current_position
        new_position = min(old_position + total_roll, 72)  # Max position is 72
        
        # Update team
        team.current_position = new_position
        team.last_dice_result = dice_result
        
        try:
            db.session.commit()
            
            # Log the dice roll
            GameService.log_game_event(
                event_type='DICE_ROLL',
                team_id=team_id,
                data={
                    'dice_result': dice_result,
                    'bonus_dice': bonus_dice,
                    'total_roll': total_roll,
                    'old_position': old_position,
                    'new_position': new_position,
                    'admin_user_id': admin_user_id
                }
            )
            
            current_app.logger.info(f"Team {team.name} rolled {dice_result} (total: {total_roll}), moved to {new_position}")
            
            return {
                'dice_result': dice_result,
                'bonus_dice': bonus_dice,
                'total_roll': total_roll,
                'old_position': old_position,
                'new_position': new_position,
                'team_name': team.name
            }
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error rolling dice for team: {str(e)}")
            raise ValidationError("Failed to roll dice")
    
    @staticmethod
    def log_game_event(event_type, team_id=None, data=None):
        """
        Log a game event.
        
        Args:
            event_type: Type of event
            team_id: Team ID (optional)
            data: Event data (optional)
        """
        event = GameEvent(
            event_type=event_type,
            team_id=team_id,
            data=json.dumps(data) if data else None,
            timestamp=datetime.utcnow()
        )
        
        try:
            db.session.add(event)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error logging game event: {str(e)}")
    
    @staticmethod
    def get_game_events(limit=100, event_type=None, team_id=None):
        """
        Get game events with optional filtering.
        
        Args:
            limit: Maximum number of events
            event_type: Filter by event type
            team_id: Filter by team ID
            
        Returns:
            List of game events
        """
        query = GameEvent.query
        
        if event_type:
            query = query.filter_by(event_type=event_type)
        
        if team_id:
            query = query.filter_by(team_id=team_id)
        
        return query.order_by(GameEvent.timestamp.desc()).limit(limit).all()
    
    @staticmethod
    def get_team_statistics(team_id):
        """
        Get statistics for a team.
        
        Args:
            team_id: Team ID
            
        Returns:
            Dict with team statistics
        """
        team = Team.query.get(team_id)
        if not team:
            raise ValidationError("Team not found")
        
        # Get dice roll events
        dice_events = GameService.get_game_events(
            event_type='DICE_ROLL',
            team_id=team_id
        )
        
        # Calculate statistics
        total_rolls = len(dice_events)
        total_moves = 0
        dice_results = []
        
        for event in dice_events:
            if event.data:
                try:
                    data = json.loads(event.data)
                    dice_results.append(data.get('dice_result', 0))
                    total_moves += data.get('total_roll', 0)
                except (json.JSONDecodeError, KeyError):
                    pass
        
        average_roll = sum(dice_results) / len(dice_results) if dice_results else 0
        
        return {
            'team_name': team.name,
            'current_position': team.current_position,
            'total_rolls': total_rolls,
            'total_moves': total_moves,
            'average_roll': round(average_roll, 2),
            'dice_results': dice_results
        }
    
    @staticmethod
    def reset_game_state():
        """
        Reset the entire game state.
        
        Raises:
            ValidationError: If reset fails
        """
        try:
            # Reset all team positions
            Team.query.update({
                Team.current_position: 0,
                Team.last_dice_result: None,
                Team.bonus_dice_sides: 0,
                Team.minigame_placement: None
            })
            
            # Deactivate all game sessions
            GameSession.query.update({GameSession.is_active: False})
            
            # Clear game events (optional - comment out to keep history)
            # GameEvent.query.delete()
            
            db.session.commit()
            current_app.logger.info("Game state reset successfully")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error resetting game state: {str(e)}")
            raise ValidationError("Failed to reset game state")
    
    @staticmethod
    def get_game_status():
        """
        Get current game status.
        
        Returns:
            Dict with game status information
        """
        active_session = GameService.get_active_session()
        teams = Team.query.order_by(Team.current_position.desc()).all()
        
        return {
            'active_session': active_session,
            'teams': teams,
            'total_teams': len(teams),
            'leading_team': teams[0] if teams else None,
            'game_phase': active_session.current_phase if active_session else None
        }