from app.models import Character, CharacterPart, db # Import db direkt vom app.models Modul oder app Modul
import json

# Liste der Standardcharaktere mit erweiterten Eigenschaften
DEFAULT_CHARACTERS = [
    {
        "name": "Standard-Charakter",
        "description": "Ein vielseitiger Charakter für alle Situationen",
        "category": "default",
        "rarity": "common",
        "color": "#4169E1",
        "is_unlocked": True,
        "js_file": "characters/defaultCharacter.js",
        "preview_image": "characters/previews/default.png",
        "thumbnail": "characters/thumbnails/default.png",
        "stats": {"strength": 5, "speed": 5, "luck": 5, "charisma": 5},
        "customization_options": {
            "faces": ["oval", "round", "square", "heart"],
            "bodies": ["normal", "slim", "athletic", "chunky"],
            "hair": ["short", "medium", "long", "bald", "curly"],
            "tshirts": ["tshirt", "polo", "hoodie", "formal"],
            "pants": ["jeans", "shorts", "formal", "athletic"],
            "shoes": ["sneakers", "boots", "formal", "sandals"],
            "accessories": ["hat", "glasses", "jewelry", "backpack"]
        }
    },
    {
        "name": "Sportlicher Typ",
        "description": "Ein athletischer Charakter mit Bonus-Geschwindigkeit",
        "category": "special",
        "rarity": "rare",
        "color": "#32CD32",
        "is_unlocked": True,
        "js_file": "characters/athleticCharacter.js",
        "preview_image": "characters/previews/athletic.png",
        "thumbnail": "characters/thumbnails/athletic.png",
        "stats": {"strength": 7, "speed": 8, "luck": 4, "charisma": 5},
        "customization_options": {
            "faces": ["oval", "square"],
            "bodies": ["athletic", "normal"],
            "hair": ["short", "medium"],
            "tshirts": ["tshirt", "polo"],
            "pants": ["athletic", "shorts"],
            "shoes": ["sneakers"],
            "accessories": ["cap", "watch", "backpack"]
        }
    },
    {
        "name": "Eleganter Charakter",
        "description": "Ein stilvoller Charakter mit Bonus-Charisma",
        "category": "special",
        "rarity": "rare",
        "color": "#8A2BE2",
        "is_unlocked": True,
        "js_file": "characters/elegantCharacter.js",
        "preview_image": "characters/previews/elegant.png",
        "thumbnail": "characters/thumbnails/elegant.png",
        "stats": {"strength": 4, "speed": 5, "luck": 6, "charisma": 8},
        "customization_options": {
            "faces": ["oval", "heart"],
            "bodies": ["slim", "normal"],
            "hair": ["medium", "long"],
            "tshirts": ["formal", "polo"],
            "pants": ["formal", "jeans"],
            "shoes": ["formal", "boots"],
            "accessories": ["glasses", "jewelry", "hat"]
        }
    },
    {
        "name": "Glückspilz",
        "description": "Ein Charakter mit außergewöhnlichem Glück",
        "category": "special",
        "rarity": "epic",
        "color": "#FFD700",
        "is_unlocked": False,
        "unlock_condition": {"type": "points", "value": 1000},
        "js_file": "characters/luckyCharacter.js",
        "preview_image": "characters/previews/lucky.png",
        "thumbnail": "characters/thumbnails/lucky.png",
        "stats": {"strength": 4, "speed": 4, "luck": 9, "charisma": 6},
        "customization_options": {
            "faces": ["round", "oval"],
            "bodies": ["normal", "chunky"],
            "hair": ["curly", "medium"],
            "tshirts": ["hoodie", "tshirt"],
            "pants": ["jeans", "shorts"],
            "shoes": ["sneakers", "sandals"],
            "accessories": ["hat", "jewelry"]
        }
    },
    {
        "name": "Power-Charakter",
        "description": "Ein starker Charakter mit maximaler Kraft",
        "category": "premium",
        "rarity": "legendary",
        "color": "#FF4500",
        "is_unlocked": False,
        "unlock_condition": {"type": "achievements", "value": ["win_10_games", "complete_challenges"]},
        "js_file": "characters/powerCharacter.js",
        "preview_image": "characters/previews/power.png",
        "thumbnail": "characters/thumbnails/power.png",
        "stats": {"strength": 10, "speed": 6, "luck": 5, "charisma": 7},
        "customization_options": {
            "faces": ["square", "oval"],
            "bodies": ["athletic", "chunky"],
            "hair": ["short", "bald"],
            "tshirts": ["tshirt", "hoodie"],
            "pants": ["jeans", "athletic"],
            "shoes": ["boots", "sneakers"],
            "accessories": ["cap", "watch"]
        }
    }
]

# Standard-Charakter-Teile
DEFAULT_CHARACTER_PARTS = [
    # Gesichter
    {"name": "Ovales Gesicht", "category": "face", "subcategory": "shape", "asset_path": "parts/faces/oval.obj", "rarity": "common"},
    {"name": "Rundes Gesicht", "category": "face", "subcategory": "shape", "asset_path": "parts/faces/round.obj", "rarity": "common"},
    {"name": "Eckiges Gesicht", "category": "face", "subcategory": "shape", "asset_path": "parts/faces/square.obj", "rarity": "common"},
    {"name": "Herzförmiges Gesicht", "category": "face", "subcategory": "shape", "asset_path": "parts/faces/heart.obj", "rarity": "rare"},
    
    # Augen
    {"name": "Normale Augen", "category": "face", "subcategory": "eyes", "asset_path": "parts/eyes/normal.obj", "rarity": "common"},
    {"name": "Große Augen", "category": "face", "subcategory": "eyes", "asset_path": "parts/eyes/big.obj", "rarity": "common"},
    {"name": "Kleine Augen", "category": "face", "subcategory": "eyes", "asset_path": "parts/eyes/small.obj", "rarity": "common"},
    {"name": "Schläfrige Augen", "category": "face", "subcategory": "eyes", "asset_path": "parts/eyes/sleepy.obj", "rarity": "rare"},
    
    # Haare
    {"name": "Kurze Haare", "category": "hair", "subcategory": "style", "asset_path": "parts/hair/short.obj", "rarity": "common"},
    {"name": "Mittlere Haare", "category": "hair", "subcategory": "style", "asset_path": "parts/hair/medium.obj", "rarity": "common"},
    {"name": "Lange Haare", "category": "hair", "subcategory": "style", "asset_path": "parts/hair/long.obj", "rarity": "common"},
    {"name": "Lockige Haare", "category": "hair", "subcategory": "style", "asset_path": "parts/hair/curly.obj", "rarity": "rare"},
    {"name": "Glatze", "category": "hair", "subcategory": "style", "asset_path": "parts/hair/bald.obj", "rarity": "common"},
    
    # Körper
    {"name": "Normaler Körper", "category": "body", "subcategory": "type", "asset_path": "parts/bodies/normal.obj", "rarity": "common"},
    {"name": "Schlanker Körper", "category": "body", "subcategory": "type", "asset_path": "parts/bodies/slim.obj", "rarity": "common"},
    {"name": "Athletischer Körper", "category": "body", "subcategory": "type", "asset_path": "parts/bodies/athletic.obj", "rarity": "rare"},
    {"name": "Kräftiger Körper", "category": "body", "subcategory": "type", "asset_path": "parts/bodies/chunky.obj", "rarity": "common"},
    
    # T-Shirts
    {"name": "Standard T-Shirt", "category": "clothing", "subcategory": "shirt", "asset_path": "parts/shirts/tshirt.obj", "rarity": "common"},
    {"name": "Polo-Shirt", "category": "clothing", "subcategory": "shirt", "asset_path": "parts/shirts/polo.obj", "rarity": "common"},
    {"name": "Hoodie", "category": "clothing", "subcategory": "shirt", "asset_path": "parts/shirts/hoodie.obj", "rarity": "rare"},
    {"name": "Formelles Hemd", "category": "clothing", "subcategory": "shirt", "asset_path": "parts/shirts/formal.obj", "rarity": "rare"},
    
    # Hosen
    {"name": "Jeans", "category": "clothing", "subcategory": "pants", "asset_path": "parts/pants/jeans.obj", "rarity": "common"},
    {"name": "Shorts", "category": "clothing", "subcategory": "pants", "asset_path": "parts/pants/shorts.obj", "rarity": "common"},
    {"name": "Formelle Hose", "category": "clothing", "subcategory": "pants", "asset_path": "parts/pants/formal.obj", "rarity": "rare"},
    {"name": "Sporthose", "category": "clothing", "subcategory": "pants", "asset_path": "parts/pants/athletic.obj", "rarity": "common"},
    
    # Schuhe
    {"name": "Sneakers", "category": "clothing", "subcategory": "shoes", "asset_path": "parts/shoes/sneakers.obj", "rarity": "common"},
    {"name": "Stiefel", "category": "clothing", "subcategory": "shoes", "asset_path": "parts/shoes/boots.obj", "rarity": "rare"},
    {"name": "Formelle Schuhe", "category": "clothing", "subcategory": "shoes", "asset_path": "parts/shoes/formal.obj", "rarity": "rare"},
    {"name": "Sandalen", "category": "clothing", "subcategory": "shoes", "asset_path": "parts/shoes/sandals.obj", "rarity": "common"},
    
    # Accessoires - Hüte
    {"name": "Baseballkappe", "category": "accessory", "subcategory": "hat", "asset_path": "parts/hats/cap.obj", "rarity": "common"},
    {"name": "Beanie", "category": "accessory", "subcategory": "hat", "asset_path": "parts/hats/beanie.obj", "rarity": "common"},
    {"name": "Formeller Hut", "category": "accessory", "subcategory": "hat", "asset_path": "parts/hats/formal.obj", "rarity": "epic"},
    {"name": "Kochmütze", "category": "accessory", "subcategory": "hat", "asset_path": "parts/hats/chef.obj", "rarity": "rare"},
    
    # Accessoires - Brillen
    {"name": "Normale Brille", "category": "accessory", "subcategory": "glasses", "asset_path": "parts/glasses/normal.obj", "rarity": "common"},
    {"name": "Sonnenbrille", "category": "accessory", "subcategory": "glasses", "asset_path": "parts/glasses/sunglasses.obj", "rarity": "rare"},
    {"name": "Lesebrille", "category": "accessory", "subcategory": "glasses", "asset_path": "parts/glasses/reading.obj", "rarity": "common"},
    
    # Accessoires - Schmuck
    {"name": "Uhr", "category": "accessory", "subcategory": "jewelry", "asset_path": "parts/jewelry/watch.obj", "rarity": "rare"},
    {"name": "Kette", "category": "accessory", "subcategory": "jewelry", "asset_path": "parts/jewelry/chain.obj", "rarity": "rare"},
    {"name": "Ringe", "category": "accessory", "subcategory": "jewelry", "asset_path": "parts/jewelry/rings.obj", "rarity": "epic"},
    
    # Accessoires - Rucksäcke
    {"name": "Schulrucksack", "category": "accessory", "subcategory": "backpack", "asset_path": "parts/backpacks/school.obj", "rarity": "common"},
    {"name": "Wanderrucksack", "category": "accessory", "subcategory": "backpack", "asset_path": "parts/backpacks/hiking.obj", "rarity": "rare"},
    {"name": "Stylischer Rucksack", "category": "accessory", "subcategory": "backpack", "asset_path": "parts/backpacks/stylish.obj", "rarity": "epic"},
]

def initialize_characters():
    """
    Erweiterte Charakterinitialisierung mit umfassenden Anpassungsoptionen.
    Diese Funktion sollte innerhalb eines App-Kontextes aufgerufen werden.
    """
    try:
        # Initialisiere Standard-Charaktere
        existing_characters_names = {char.name for char in Character.query.all()}
        
        new_characters_added = False
        for char_data in DEFAULT_CHARACTERS:
            if char_data["name"] not in existing_characters_names:
                new_character = Character(
                    name=char_data["name"],
                    description=char_data.get("description"),
                    category=char_data.get("category", "default"),
                    rarity=char_data.get("rarity", "common"),
                    color=char_data.get("color", "#FFFFFF"),
                    is_unlocked=char_data.get("is_unlocked", True),
                    js_file=char_data.get("js_file"),
                    preview_image=char_data.get("preview_image"),
                    thumbnail=char_data.get("thumbnail")
                )
                
                # Setze Stats
                if "stats" in char_data:
                    new_character.set_stats(char_data["stats"])
                
                # Setze Unlock-Bedingung
                if "unlock_condition" in char_data:
                    new_character.set_unlock_condition(char_data["unlock_condition"])
                
                # Setze Anpassungsoptionen
                if "customization_options" in char_data:
                    new_character.set_customization_options(char_data["customization_options"])
                
                db.session.add(new_character)
                print(f"Charakter '{char_data['name']}' zur Datenbank hinzugefügt.")
                new_characters_added = True
        
        if new_characters_added:
            db.session.commit()
            print("Neue Charaktere erfolgreich in die Datenbank geschrieben.")
        else:
            print("Alle Standardcharaktere sind bereits in der Datenbank vorhanden.")
            
    except Exception as e:
        print(f"Fehler bei der Initialisierung der Charaktere: {e}")
        db.session.rollback()

def initialize_character_parts():
    """
    Initialisiert Standard-Charakter-Teile in der Datenbank.
    """
    try:
        existing_parts_names = {part.name for part in CharacterPart.query.all()}
        
        new_parts_added = False
        for part_data in DEFAULT_CHARACTER_PARTS:
            if part_data["name"] not in existing_parts_names:
                new_part = CharacterPart(
                    name=part_data["name"],
                    category=part_data["category"],
                    subcategory=part_data.get("subcategory"),
                    asset_path=part_data["asset_path"],
                    texture_path=part_data.get("texture_path"),
                    icon_path=part_data.get("icon_path"),
                    rarity=part_data.get("rarity", "common"),
                    is_unlocked=part_data.get("is_unlocked", True),
                    color_customizable=part_data.get("color_customizable", True),
                    default_color=part_data.get("default_color", "#FFFFFF"),
                    description=part_data.get("description")
                )
                
                # Setze kompatible Körpertypen
                if "compatible_body_types" in part_data:
                    new_part.set_compatible_body_types(part_data["compatible_body_types"])
                
                # Setze kompatible Gesichtsformen
                if "compatible_face_shapes" in part_data:
                    new_part.set_compatible_face_shapes(part_data["compatible_face_shapes"])
                
                # Setze Konflikte
                if "conflicts_with" in part_data:
                    new_part.set_conflicts_with(part_data["conflicts_with"])
                
                # Setze Stats-Modifikatoren
                if "stats_modifier" in part_data:
                    new_part.set_stats_modifier(part_data["stats_modifier"])
                
                # Setze Spezialeffekte
                if "special_effects" in part_data:
                    new_part.set_special_effects(part_data["special_effects"])
                
                # Setze Unlock-Bedingung
                if "unlock_condition" in part_data:
                    new_part.set_unlock_condition(part_data["unlock_condition"])
                
                db.session.add(new_part)
                print(f"Charakter-Teil '{part_data['name']}' zur Datenbank hinzugefügt.")
                new_parts_added = True
        
        if new_parts_added:
            db.session.commit()
            print("Neue Charakter-Teile erfolgreich in die Datenbank geschrieben.")
        else:
            print("Alle Standard-Charakter-Teile sind bereits in der Datenbank vorhanden.")
            
    except Exception as e:
        print(f"Fehler bei der Initialisierung der Charakter-Teile: {e}")
        db.session.rollback()

def initialize_all_character_data():
    """
    Initialisiert alle Charakter-bezogenen Daten.
    """
    print("Initialisiere Charakter-System...")
    initialize_characters()
    initialize_character_parts()
    print("Charakter-System-Initialisierung abgeschlossen.")

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
