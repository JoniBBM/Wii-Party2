from app import create_app, db
from app.models import Character

app = create_app()

def init_characters():
    with app.app_context():
        # Check if characters already exist
        if Character.query.count() > 0:
            print("Characters already initialized!")
            return

        # Create the Italian Brainrot characters
        characters = [
            {
                "name": "Tung Tung Tung Sahur",
                "description": "Ein rhythmischer Charakter mit einem sehr langen Namen",
                "color": "#9C27B0"  # Purple
            },
            {
                "name": "Ballerina Cappuccina",
                "description": "Eine tanzende Ballerina mit einer Cappuccino-Tasse als Kopf",
                "color": "#FF69B4"  # Pink
            },
            {
                "name": "Bombardino Crocodilo",
                "description": "Eine grüne Krokodil-Figur mit einer explosiven Persönlichkeit",
                "color": "#4CAF50"  # Green
            },
            {
                "name": "Lirilì Larilà",
                "description": "Ein verträumter, singender Charakter mit einer melodischen Stimme",
                "color": "#FFEB3B"  # Yellow
            },
            {
                "name": "Tralalero Tralala",
                "description": "Ein musikalischer Charakter, der immer eine Melodie auf den Lippen hat",
                "color": "#2196F3"  # Blue
            },
            {
                "name": "Trippi Troppi",
                "description": "Ein verspielter, tropischer Charakter voller Energie",
                "color": "#F44336"  # Red
            }
        ]

        # Add characters to database
        for char_data in characters:
            character = Character(
                name=char_data["name"],
                description=char_data["description"],
                color=char_data["color"]
            )
            db.session.add(character)

        db.session.commit()
        print("✅ Characters successfully initialized!")

if __name__ == "__main__":
    init_characters()