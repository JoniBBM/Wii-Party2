from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'teams.team_login'

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    login_manager.init_app(app)
    
    from app.models import Team
    
    @login_manager.user_loader
    def load_user(user_id):
        return Team.query.get(int(user_id))
    
    from app.main.routes import main_bp
    from app.teams.routes import teams_bp
    from app.admin.routes import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(teams_bp, url_prefix='/teams')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    return app
