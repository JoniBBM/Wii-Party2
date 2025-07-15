"""
Input validation and sanitization utilities for enhanced security.
"""
import re
import html
import bleach
from typing import Any, Optional, List, Dict
from markupsafe import Markup

# Allowed HTML tags for rich text content
ALLOWED_TAGS = {
    'basic': [],  # No HTML tags allowed
    'text': ['p', 'br', 'strong', 'em', 'u'],  # Basic text formatting
    'full': ['p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li', 'a', 'span']  # Full formatting
}

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'span': ['class'],
}

class ValidationError(Exception):
    """Custom validation error for input validation."""
    pass

def sanitize_string(value: str, max_length: int = 255, allow_html: str = 'basic') -> str:
    """
    Sanitize string input by removing/escaping dangerous content.
    
    Args:
        value: Input string to sanitize
        max_length: Maximum allowed length
        allow_html: Level of HTML allowed ('basic', 'text', 'full')
    
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return str(value)
    
    # Strip whitespace
    value = value.strip()
    
    # Truncate if too long
    if len(value) > max_length:
        value = value[:max_length]
    
    # Handle HTML based on allowed level
    if allow_html == 'basic':
        # No HTML allowed - escape everything
        return html.escape(value)
    elif allow_html in ['text', 'full']:
        # Use bleach to clean HTML
        allowed_tags = ALLOWED_TAGS.get(allow_html, [])
        return bleach.clean(value, tags=allowed_tags, attributes=ALLOWED_ATTRIBUTES, strip=True)
    
    return value

def validate_team_name(name: str) -> str:
    """
    Validate and sanitize team name.
    
    Args:
        name: Team name to validate
        
    Returns:
        Sanitized team name
        
    Raises:
        ValidationError: If name is invalid
    """
    if not name or not name.strip():
        raise ValidationError("Team name cannot be empty")
    
    # Sanitize
    name = sanitize_string(name, max_length=50, allow_html='basic')
    
    # Check length after sanitization
    if len(name) < 2:
        raise ValidationError("Team name must be at least 2 characters long")
    
    # Check for valid characters (alphanumeric, spaces, hyphens, underscores)
    if not re.match(r'^[a-zA-Z0-9_\-\s]+$', name):
        raise ValidationError("Team name contains invalid characters")
    
    return name

def validate_player_name(name: str) -> str:
    """
    Validate and sanitize player name.
    
    Args:
        name: Player name to validate
        
    Returns:
        Sanitized player name
        
    Raises:
        ValidationError: If name is invalid
    """
    if not name or not name.strip():
        raise ValidationError("Player name cannot be empty")
    
    # Sanitize
    name = sanitize_string(name, max_length=50, allow_html='basic')
    
    # Check length after sanitization
    if len(name) < 1:
        raise ValidationError("Player name cannot be empty after sanitization")
    
    if len(name) > 50:
        raise ValidationError("Player name too long")
    
    # Check for valid characters (alphanumeric, spaces, hyphens, underscores)
    if not re.match(r'^[a-zA-Z0-9_\-\s]+$', name):
        raise ValidationError("Player name contains invalid characters")
    
    return name

def validate_member_list(members_str: str) -> List[str]:
    """
    Validate and sanitize team member list.
    
    Args:
        members_str: Comma or newline separated member names
        
    Returns:
        List of sanitized member names
        
    Raises:
        ValidationError: If member list is invalid
    """
    if not members_str or not members_str.strip():
        return []
    
    # Split by comma or newline
    raw_members = re.split(r'[,\n]', members_str)
    
    # Validate each member
    validated_members = []
    for member in raw_members:
        member = member.strip()
        if member:  # Skip empty entries
            validated_member = validate_player_name(member)
            if validated_member not in validated_members:  # Avoid duplicates
                validated_members.append(validated_member)
    
    # Check member count
    if len(validated_members) > 10:
        raise ValidationError("Too many team members (maximum 10)")
    
    return validated_members

def validate_position(position: Any) -> int:
    """
    Validate game position.
    
    Args:
        position: Position to validate
        
    Returns:
        Validated position as integer
        
    Raises:
        ValidationError: If position is invalid
    """
    try:
        pos = int(position)
    except (ValueError, TypeError):
        raise ValidationError("Position must be a number")
    
    if pos < 0 or pos > 72:
        raise ValidationError("Position must be between 0 and 72")
    
    return pos

def validate_dice_result(dice_result: Any) -> int:
    """
    Validate dice result.
    
    Args:
        dice_result: Dice result to validate
        
    Returns:
        Validated dice result as integer
        
    Raises:
        ValidationError: If dice result is invalid
    """
    try:
        result = int(dice_result)
    except (ValueError, TypeError):
        raise ValidationError("Dice result must be a number")
    
    if result < 1 or result > 6:
        raise ValidationError("Dice result must be between 1 and 6")
    
    return result

def validate_hex_color(color: str) -> str:
    """
    Validate hex color code.
    
    Args:
        color: Color code to validate
        
    Returns:
        Validated color code
        
    Raises:
        ValidationError: If color is invalid
    """
    if not color or not color.strip():
        raise ValidationError("Color cannot be empty")
    
    color = color.strip()
    
    # Add # if missing
    if not color.startswith('#'):
        color = '#' + color
    
    # Validate hex pattern
    if not re.match(r'^#[0-9a-fA-F]{6}$', color):
        raise ValidationError("Invalid hex color format")
    
    return color

def validate_json_data(data: Dict[str, Any], required_fields: List[str] = None) -> Dict[str, Any]:
    """
    Validate JSON data structure.
    
    Args:
        data: JSON data to validate
        required_fields: List of required field names
        
    Returns:
        Validated data dictionary
        
    Raises:
        ValidationError: If data is invalid
    """
    if not isinstance(data, dict):
        raise ValidationError("Data must be a dictionary")
    
    if required_fields:
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}")
    
    return data

def validate_image_data(image_data: str, max_size_mb: float = 5.0) -> str:
    """
    Validate base64 image data.
    
    Args:
        image_data: Base64 encoded image data
        max_size_mb: Maximum file size in MB
        
    Returns:
        Validated image data
        
    Raises:
        ValidationError: If image data is invalid
    """
    if not image_data or not image_data.strip():
        raise ValidationError("Image data cannot be empty")
    
    # Remove data URL prefix if present
    if image_data.startswith('data:image'):
        try:
            image_data = image_data.split(',')[1]
        except IndexError:
            raise ValidationError("Invalid image data format")
    
    # Clean base64 data
    image_data = image_data.strip().replace(' ', '').replace('\n', '').replace('\r', '')
    
    # Validate base64 format
    if not re.match(r'^[A-Za-z0-9+/]*={0,2}$', image_data):
        raise ValidationError("Invalid base64 format")
    
    # Check size (base64 is ~33% larger than original)
    estimated_size_mb = len(image_data) * 0.75 / (1024 * 1024)
    if estimated_size_mb > max_size_mb:
        raise ValidationError(f"Image too large (max {max_size_mb}MB)")
    
    return image_data

def validate_password(password: str, min_length: int = 6) -> str:
    """
    Validate password strength.
    
    Args:
        password: Password to validate
        min_length: Minimum password length
        
    Returns:
        Validated password
        
    Raises:
        ValidationError: If password is invalid
    """
    if not password:
        raise ValidationError("Password cannot be empty")
    
    if len(password) < min_length:
        raise ValidationError(f"Password must be at least {min_length} characters long")
    
    # Check for basic complexity (at least one letter and one number)
    if not re.search(r'[a-zA-Z]', password) or not re.search(r'[0-9]', password):
        raise ValidationError("Password must contain at least one letter and one number")
    
    return password

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage.
    
    Args:
        filename: Filename to sanitize
        
    Returns:
        Sanitized filename
    """
    import os
    
    if not filename:
        return "unnamed_file"
    
    # Remove path components
    filename = os.path.basename(filename)
    
    # Replace dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    return filename or "unnamed_file"

def rate_limit_check(key: str, limit: int = 10, window: int = 60) -> bool:
    """
    Simple rate limiting check (in-memory).
    
    Args:
        key: Unique key for rate limiting (e.g., IP address)
        limit: Maximum requests per window
        window: Time window in seconds
        
    Returns:
        True if within limit, False if exceeded
    """
    import time
    from collections import defaultdict
    
    # In-memory storage (in production, use Redis)
    if not hasattr(rate_limit_check, 'requests'):
        rate_limit_check.requests = defaultdict(list)
    
    now = time.time()
    requests = rate_limit_check.requests[key]
    
    # Remove old requests
    requests[:] = [req_time for req_time in requests if now - req_time < window]
    
    # Check limit
    if len(requests) >= limit:
        return False
    
    # Add current request
    requests.append(now)
    return True