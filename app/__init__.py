from flask import Flask, g
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
import os

# Initialisiere die Erweiterungen außerhalb der Factory, aber ohne App-Instanz
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

# Login Manager Konfiguration
login_manager.login_view = 'teams.team_login' # Korrigierter Endpunkt für Team-Login
login_manager.login_message_category = 'info'
login_manager.needs_refresh_message = (
    "Um diese Seite zu schützen, bestätige bitte deine Identität."
)
login_manager.needs_refresh_message_category = "info"


# User Loader für Flask-Login
@login_manager.user_loader
def load_user(user_id):
    from app.models import Admin, Team 
    user = Admin.query.get(int(user_id))
    if user:
        g.user_type = 'admin'
        return user
    
    user = Team.query.get(int(user_id))
    if user:
        g.user_type = 'team'
        return user
    return None

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    from app.main.routes import main_bp
    app.register_blueprint(main_bp)

    from app.admin.routes import admin_bp
    app.register_blueprint(admin_bp)

    from app.teams.routes import teams_bp
    app.register_blueprint(teams_bp)

    @app.context_processor
    def inject_now_year_and_user_type():
        from datetime import datetime
        from flask_login import current_user
        from app.models import Admin, Team # Importiere hier für isinstance

        user_type_in_context = None
        if current_user.is_authenticated:
            if isinstance(current_user, Admin):
                user_type_in_context = 'admin'
            elif isinstance(current_user, Team):
                user_type_in_context = 'team'
        return {'now_year': datetime.utcnow().year, 'user_type': user_type_in_context}

    @app.template_filter('is_admin')
    def is_admin_filter(user):
        from app.models import Admin
        return isinstance(user, Admin)

    @app.template_filter('is_team')
    def is_team_filter(user):
        from app.models import Team
        return isinstance(user, Team)
        
    with app.app_context():
        from app import models 

    return app
