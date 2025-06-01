from app.models import Character, db # Import db direkt vom app.models Modul oder app Modul

# Liste der Standardcharaktere
DEFAULT_CHARACTERS = [
    {"name": "TungTungTungSahur", "image_file": "images/characters/TungTungTungSahur.png", "js_file": "js/characters/tungTungTungSahur.js"},
    {"name": "TrippiTroppi", "image_file": "images/characters/TrippiTroppi.png", "js_file": "js/characters/trippiTroppi.js"},
    {"name": "TralaleroTralala", "image_file": "images/characters/TralaleroTralala.png", "js_file": "js/characters/tralaleroTralala.js"},
    {"name": "LiriliLarila", "image_file": "images/characters/LiriliLarila.png", "js_file": "js/characters/liriliLarila.js"},
    {"name": "BombardinoCrocodilo", "image_file": "images/characters/BombardinoCrocodilo.png", "js_file": "js/characters/bombardinoCrocodilo.js"},
    {"name": "BallerinaCappuccina", "image_file": "images/characters/BallerinaCappuccina.png", "js_file": "js/characters/ballerinaCappuccina.js"},
    # Füge hier bei Bedarf weitere Standardcharaktere hinzu
]

def initialize_characters():
    """
    Überprüft die Datenbank auf vorhandene Charaktere und fügt fehlende Standardcharaktere hinzu.
    Diese Funktion sollte innerhalb eines App-Kontextes aufgerufen werden.
    """
    try:
        existing_characters_names = {char.name for char in Character.query.all()}
        
        new_characters_added = False
        for char_data in DEFAULT_CHARACTERS:
            if char_data["name"] not in existing_characters_names:
                new_character = Character(
                    name=char_data["name"],
                    image_file=char_data.get("image_file"),
                    js_file=char_data.get("js_file")
                )
                db.session.add(new_character)
                print(f"Charakter '{char_data['name']}' zur Datenbank hinzugefügt.")
                new_characters_added = True
            # else:
                # print(f"Charakter '{char_data['name']}' existiert bereits.")

        if new_characters_added:
            db.session.commit()
            print("Neue Charaktere erfolgreich in die Datenbank geschrieben.")
        else:
            print("Alle Standardcharaktere sind bereits in der Datenbank vorhanden.")
            
    except Exception as e:
        print(f"Fehler bei der Initialisierung der Charaktere: {e}")
        db.session.rollback()

if __name__ == '__main__':
    # Dieser Block ist für den direkten Aufruf des Skripts gedacht
    # und benötigt einen App-Kontext, um zu funktionieren.
    # Normalerweise wird initialize_characters aus init_db.py oder einer Admin-Route aufgerufen.
    print("Dieser Teil ist für den direkten Aufruf gedacht und erfordert einen App-Kontext.")
    # Beispiel:
    # from app import create_app
    # app = create_app()
    # with app.app_context():
    #     initialize_characters()
