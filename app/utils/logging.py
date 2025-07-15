"""
Enhanced logging system for comprehensive application monitoring.
"""
import logging
import logging.handlers
import os
import json
import traceback
from datetime import datetime
from flask import request, current_app, g
from functools import wraps
import time


class SecurityLogFilter(logging.Filter):
    """Filter for security-related log messages."""
    
    def filter(self, record):
        """Filter security events."""
        security_keywords = [
            'SECURITY_EVENT', 'authentication', 'authorization', 'csrf',
            'rate_limit', 'validation_error', 'suspicious_activity'
        ]
        
        message = record.getMessage().lower()
        return any(keyword in message for keyword in security_keywords)


class GameEventLogFilter(logging.Filter):
    """Filter for game-related log messages."""
    
    def filter(self, record):
        """Filter game events."""
        game_keywords = [
            'game_event', 'dice_roll', 'position_change', 'minigame',
            'team_created', 'team_updated', 'game_session'
        ]
        
        message = record.getMessage().lower()
        return any(keyword in message for keyword in game_keywords)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        """Format log record as JSON."""
        log_obj = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add request context if available
        if request:
            log_obj['request'] = {
                'method': request.method,
                'url': request.url,
                'remote_addr': request.remote_addr,
                'user_agent': request.headers.get('User-Agent'),
                'referrer': request.headers.get('Referer')
            }
        
        # Add user context if available
        if hasattr(g, 'user_id'):
            log_obj['user_id'] = g.user_id
        
        # Add exception info if present
        if record.exc_info:
            log_obj['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 
                          'exc_text', 'stack_info']:
                log_obj[key] = value
        
        return json.dumps(log_obj)


class RequestIDFilter(logging.Filter):
    """Add request ID to log records."""
    
    def filter(self, record):
        """Add request ID to record."""
        if hasattr(g, 'request_id'):
            record.request_id = g.request_id
        return True


def setup_logging(app):
    """
    Setup comprehensive logging configuration.
    
    Args:
        app: Flask application instance
    """
    # Create logs directory
    logs_dir = os.path.join(app.instance_path, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colored output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Application log file (rotating)
    app_log_path = os.path.join(logs_dir, 'app.log')
    app_handler = logging.handlers.RotatingFileHandler(
        app_log_path,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(JSONFormatter())
    app_handler.addFilter(RequestIDFilter())
    root_logger.addHandler(app_handler)
    
    # Security log file
    security_log_path = os.path.join(logs_dir, 'security.log')
    security_handler = logging.handlers.RotatingFileHandler(
        security_log_path,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=10
    )
    security_handler.setLevel(logging.WARNING)
    security_handler.setFormatter(JSONFormatter())
    security_handler.addFilter(SecurityLogFilter())
    security_handler.addFilter(RequestIDFilter())
    root_logger.addHandler(security_handler)
    
    # Game events log file
    game_log_path = os.path.join(logs_dir, 'game_events.log')
    game_handler = logging.handlers.RotatingFileHandler(
        game_log_path,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=5
    )
    game_handler.setLevel(logging.INFO)
    game_handler.setFormatter(JSONFormatter())
    game_handler.addFilter(GameEventLogFilter())
    game_handler.addFilter(RequestIDFilter())
    root_logger.addHandler(game_handler)
    
    # Error log file
    error_log_path = os.path.join(logs_dir, 'errors.log')
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_path,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=10
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    error_handler.addFilter(RequestIDFilter())
    root_logger.addHandler(error_handler)
    
    # Set specific logger levels
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    app.logger.info("Logging system initialized")


def generate_request_id():
    """Generate unique request ID."""
    import uuid
    return str(uuid.uuid4())[:8]


def log_request_start():
    """Log request start."""
    g.request_id = generate_request_id()
    g.request_start_time = time.time()
    
    current_app.logger.info(
        f"REQUEST_START: {request.method} {request.url}",
        extra={
            'event_type': 'request_start',
            'method': request.method,
            'url': request.url,
            'remote_addr': request.remote_addr,
            'user_agent': request.headers.get('User-Agent')
        }
    )


def log_request_end(response):
    """Log request end."""
    if hasattr(g, 'request_start_time'):
        duration = time.time() - g.request_start_time
        
        current_app.logger.info(
            f"REQUEST_END: {request.method} {request.url} - {response.status_code} ({duration:.3f}s)",
            extra={
                'event_type': 'request_end',
                'method': request.method,
                'url': request.url,
                'status_code': response.status_code,
                'duration': duration,
                'content_length': response.content_length
            }
        )
    
    return response


def log_game_event(event_type, details=None, team_id=None, user_id=None):
    """
    Log game-related events.
    
    Args:
        event_type: Type of game event
        details: Event details dictionary
        team_id: Team ID if applicable
        user_id: User ID if applicable
    """
    current_app.logger.info(
        f"GAME_EVENT: {event_type}",
        extra={
            'event_type': 'game_event',
            'game_event_type': event_type,
            'details': details or {},
            'team_id': team_id,
            'user_id': user_id
        }
    )


def log_security_event(event_type, details=None, user_id=None, severity='WARNING'):
    """
    Log security-related events.
    
    Args:
        event_type: Type of security event
        details: Event details dictionary
        user_id: User ID if applicable
        severity: Log severity level
    """
    logger_method = getattr(current_app.logger, severity.lower())
    
    logger_method(
        f"SECURITY_EVENT: {event_type}",
        extra={
            'event_type': 'security_event',
            'security_event_type': event_type,
            'details': details or {},
            'user_id': user_id,
            'severity': severity
        }
    )


def log_performance_metric(metric_name, value, unit='ms', tags=None):
    """
    Log performance metrics.
    
    Args:
        metric_name: Name of the metric
        value: Metric value
        unit: Unit of measurement
        tags: Additional tags dictionary
    """
    current_app.logger.info(
        f"PERFORMANCE_METRIC: {metric_name} = {value}{unit}",
        extra={
            'event_type': 'performance_metric',
            'metric_name': metric_name,
            'value': value,
            'unit': unit,
            'tags': tags or {}
        }
    )


def log_user_action(action, details=None, user_id=None):
    """
    Log user actions for audit trail.
    
    Args:
        action: User action description
        details: Action details dictionary
        user_id: User ID if applicable
    """
    current_app.logger.info(
        f"USER_ACTION: {action}",
        extra={
            'event_type': 'user_action',
            'action': action,
            'details': details or {},
            'user_id': user_id
        }
    )


def log_decorator(action_name=None, log_args=False, log_result=False):
    """
    Decorator for automatic function logging.
    
    Args:
        action_name: Custom action name
        log_args: Whether to log function arguments
        log_result: Whether to log function result
    
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Log function start
            log_data = {
                'function': func.__name__,
                'module': func.__module__
            }
            
            if log_args:
                log_data['args'] = str(args)
                log_data['kwargs'] = str(kwargs)
            
            current_app.logger.info(
                f"FUNCTION_START: {action_name or func.__name__}",
                extra=log_data
            )
            
            try:
                result = func(*args, **kwargs)
                
                # Log function end
                duration = time.time() - start_time
                log_data.update({
                    'duration': duration,
                    'status': 'success'
                })
                
                if log_result:
                    log_data['result'] = str(result)
                
                current_app.logger.info(
                    f"FUNCTION_END: {action_name or func.__name__} ({duration:.3f}s)",
                    extra=log_data
                )
                
                return result
                
            except Exception as e:
                # Log function error
                duration = time.time() - start_time
                log_data.update({
                    'duration': duration,
                    'status': 'error',
                    'error': str(e)
                })
                
                current_app.logger.error(
                    f"FUNCTION_ERROR: {action_name or func.__name__} - {str(e)}",
                    extra=log_data,
                    exc_info=True
                )
                
                raise
        
        return wrapper
    return decorator


def init_logging(app):
    """
    Initialize comprehensive logging system.
    
    Args:
        app: Flask application instance
    """
    # Setup logging configuration
    setup_logging(app)
    
    # Add request/response logging
    @app.before_request
    def before_request():
        log_request_start()
    
    @app.after_request
    def after_request(response):
        return log_request_end(response)
    
    # Add error logging
    @app.errorhandler(Exception)
    def log_exception(e):
        current_app.logger.error(
            f"UNHANDLED_EXCEPTION: {str(e)}",
            extra={
                'event_type': 'unhandled_exception',
                'exception_type': type(e).__name__,
                'exception_message': str(e)
            },
            exc_info=True
        )
        
        # Re-raise the exception to maintain normal error handling
        raise
    
    # Add CLI command for log analysis
    @app.cli.command()
    def analyze_logs():
        """Analyze application logs."""
        logs_dir = os.path.join(app.instance_path, 'logs')
        
        if not os.path.exists(logs_dir):
            print("No logs directory found")
            return
        
        for log_file in os.listdir(logs_dir):
            if log_file.endswith('.log'):
                log_path = os.path.join(logs_dir, log_file)
                file_size = os.path.getsize(log_path)
                
                with open(log_path, 'r') as f:
                    line_count = sum(1 for _ in f)
                
                print(f"{log_file}: {line_count} lines, {file_size / 1024:.1f} KB")
    
    app.logger.info("Enhanced logging system initialized")
    
    return app