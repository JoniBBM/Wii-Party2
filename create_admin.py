from app import create_app, db
from app.models import Admin

app = create_app()
with app.app_context():
    # Prüfen ob Admin existiert
    admin = Admin.query.filter_by(username="admin").first()
    
    if not admin:
        # Admin-Benutzer erstellen
        admin = Admin(username="admin")
        admin.set_password("1234qwer!")
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin-Benutzer erfolgreich erstellt!")
    else:
        print("⚠️ Admin-Benutzer existiert bereits!")
