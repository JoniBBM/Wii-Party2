"""
Security utilities for enhanced application security.
"""
from flask import request, make_response
from functools import wraps
import time
from collections import defaultdict


def add_security_headers(response):
    """
    Add security headers to Flask response.
    
    Args:
        response: Flask response object
        
    Returns:
        Modified response with security headers
    """
    # Content Security Policy (without HTTPS requirements)
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "media-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    
    # X-Frame-Options
    response.headers['X-Frame-Options'] = 'DENY'
    
    # X-Content-Type-Options
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # X-XSS-Protection
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Referrer Policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Permissions Policy
    response.headers['Permissions-Policy'] = (
        "geolocation=(), "
        "microphone=(), "
        "camera=(), "
        "payment=(), "
        "usb=(), "
        "magnetometer=(), "
        "accelerometer=(), "
        "gyroscope=()"
    )
    
    # Server header removal
    response.headers.pop('Server', None)
    
    return response


def secure_cookie_config(app):
    """
    Configure secure cookie settings.
    
    Args:
        app: Flask application instance
    """
    # Session cookie configuration
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False  # Set to True when using HTTPS
    
    # Remember me cookie configuration
    app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'
    app.config['REMEMBER_COOKIE_SECURE'] = False  # Set to True when using HTTPS
    
    # WTF CSRF cookie configuration
    app.config['WTF_CSRF_SSL_STRICT'] = False  # Set to True when using HTTPS
    app.config['WTF_CSRF_CHECK_DEFAULT'] = True
    app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour


def rate_limit_decorator(max_requests=60, window_seconds=60, key_func=None):
    """
    Rate limiting decorator for Flask routes.
    
    Args:
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds
        key_func: Function to generate rate limit key (default: IP address)
    
    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get rate limit key
            if key_func:
                key = key_func()
            else:
                key = request.remote_addr
            
            # Check rate limit
            from app.utils.validation import rate_limit_check
            if not rate_limit_check(key, limit=max_requests, window=window_seconds):
                from flask import jsonify
                return jsonify({
                    "success": False, 
                    "error": "Rate limit exceeded"
                }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def validate_request_size(max_size_mb=10):
    """
    Validate request content length.
    
    Args:
        max_size_mb: Maximum request size in MB
    
    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            max_size_bytes = max_size_mb * 1024 * 1024
            
            if request.content_length and request.content_length > max_size_bytes:
                from flask import jsonify
                return jsonify({
                    "success": False, 
                    "error": f"Request too large (max {max_size_mb}MB)"
                }), 413
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def cors_headers(origin="*", methods="GET,POST,PUT,DELETE,OPTIONS", headers="*"):
    """
    Add CORS headers to response.
    
    Args:
        origin: Allowed origin (default: *)
        methods: Allowed methods
        headers: Allowed headers
    
    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Handle preflight requests
            if request.method == 'OPTIONS':
                from flask import make_response
                response = make_response()
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Allow-Methods'] = methods
                response.headers['Access-Control-Allow-Headers'] = headers
                response.headers['Access-Control-Max-Age'] = '86400'
                return response
            
            # Handle actual requests
            response = make_response(f(*args, **kwargs))
            response.headers['Access-Control-Allow-Origin'] = origin
            return response
        return decorated_function
    return decorator


def log_security_event(event_type, details=None, user_id=None):
    """
    Log security-related events.
    
    Args:
        event_type: Type of security event
        details: Additional details
        user_id: User ID if applicable
    """
    from flask import current_app
    
    log_entry = {
        'event_type': event_type,
        'timestamp': time.time(),
        'ip_address': request.remote_addr if request else None,
        'user_agent': request.headers.get('User-Agent') if request else None,
        'user_id': user_id,
        'details': details
    }
    
    current_app.logger.warning(f"SECURITY_EVENT: {log_entry}")


def check_suspicious_activity(ip_address, threshold=50, window=300):
    """
    Check for suspicious activity patterns.
    
    Args:
        ip_address: IP address to check
        threshold: Request threshold
        window: Time window in seconds
    
    Returns:
        True if suspicious activity detected
    """
    from app.utils.validation import rate_limit_check
    
    # Use a stricter rate limit for suspicious activity detection
    if not rate_limit_check(f"suspicious_{ip_address}", limit=threshold, window=window):
        log_security_event("suspicious_activity", {
            "ip_address": ip_address,
            "threshold": threshold,
            "window": window
        })
        return True
    
    return False


def sanitize_headers():
    """
    Sanitize and validate request headers.
    
    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check for suspicious headers
            suspicious_headers = [
                'X-Forwarded-For',
                'X-Real-IP',
                'X-Cluster-Client-IP'
            ]
            
            for header in suspicious_headers:
                if header in request.headers:
                    value = request.headers[header]
                    # Log potential IP spoofing attempts
                    if value != request.remote_addr:
                        log_security_event("header_spoofing", {
                            "header": header,
                            "value": value,
                            "actual_ip": request.remote_addr
                        })
            
            # Validate Content-Type for POST requests
            if request.method == 'POST' and request.content_type:
                allowed_content_types = [
                    'application/json',
                    'application/x-www-form-urlencoded',
                    'multipart/form-data'
                ]
                
                if not any(ct in request.content_type for ct in allowed_content_types):
                    log_security_event("invalid_content_type", {
                        "content_type": request.content_type
                    })
                    from flask import jsonify
                    return jsonify({
                        "success": False,
                        "error": "Invalid content type"
                    }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def init_security(app):
    """
    Initialize security features for Flask app.
    
    Args:
        app: Flask application instance
    """
    # Configure secure cookies
    secure_cookie_config(app)
    
    # Add security headers to all responses
    @app.after_request
    def add_security_headers_middleware(response):
        return add_security_headers(response)
    
    # Log security events
    @app.before_request
    def log_requests():
        # Log suspicious activity
        if check_suspicious_activity(request.remote_addr):
            # Additional logging for suspicious IPs
            pass
    
    # Configure CSP nonce if needed
    @app.before_request
    def generate_csp_nonce():
        import secrets
        request.csp_nonce = secrets.token_hex(16)