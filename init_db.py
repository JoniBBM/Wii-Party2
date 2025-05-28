from app import create_app, db
from app.models import Team, Admin, Game, MinigameResult

app = create_app()
with app.app_context():
    db.drop_all()
    db.create_all()
    print("✅ Datenbank erfolgreich initialisiert!")
