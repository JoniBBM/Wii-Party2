# 🎯 Rundenspezifische Konfigurationen

## 🎮 Problem gelöst!

**Jetzt hat jede Runde ihre eigenen, persistenten Konfigurationen!**

Wenn du in "Test1" Player Swap ausmachst und dann zu "Standard-Spiel" wechselst, ist dort Player Swap noch an. Wenn du wieder zu "Test1" wechselst, ist Player Swap dort immer noch aus - genau wie du es eingestellt hattest!

## 🔧 Wie es funktioniert

### ✅ Vor der Änderung (Problem):
- **Globale Konfigurationen**: Alle Runden teilten dieselben Einstellungen
- **Player Swap in "Test1" ausschalten** → auch in "Standard-Spiel" aus
- **Rundenwechsel** → Konfigurationen gingen verloren

### ✅ Nach der Änderung (Lösung):
- **Rundenspezifische Konfigurationen**: Jede Runde hat eigene Einstellungen
- **Player Swap in "Test1" ausschalten** → in "Standard-Spiel" noch an
- **Rundenwechsel** → Konfigurationen werden automatisch gespeichert/geladen

## 📊 Neue Datenbank-Struktur

### 🗄️ Neue Tabelle: `RoundFieldConfiguration`
```sql
CREATE TABLE round_field_configuration (
    id INTEGER PRIMARY KEY,
    game_round_id INTEGER NOT NULL,           -- Verknüpfung zur Runde
    field_type VARCHAR(50) NOT NULL,          -- z.B. 'player_swap'
    display_name VARCHAR(100) NOT NULL,       -- z.B. 'Spieler-Tausch'
    description VARCHAR(500),
    is_enabled BOOLEAN DEFAULT TRUE,          -- An/Aus für diese Runde
    frequency_type VARCHAR(20) DEFAULT 'modulo',
    frequency_value INTEGER DEFAULT 10,
    color_hex VARCHAR(7) NOT NULL,
    emission_hex VARCHAR(7),
    icon VARCHAR(10),
    config_data TEXT,                         -- JSON-Konfiguration
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(game_round_id, field_type)         -- Pro Runde nur eine Konfiguration pro Feldtyp
);
```

### 🔗 Erweiterte `GameRound` Tabelle
```python
class GameRound(db.Model):
    # ... bestehende Felder ...
    
    # Neue Beziehung zu rundenspezifischen Konfigurationen
    round_field_configs = db.relationship('RoundFieldConfiguration', 
                                         backref='game_round', 
                                         lazy='dynamic', 
                                         cascade="all, delete-orphan")
```

## 🔄 Automatischer Ablauf

### 1. **Runde aktivieren**
```python
# Admin klickt "Aktivieren" für Runde "Test1"
round_obj = GameRound.query.get(round_id)
round_obj.activate()
```

**Was passiert automatisch:**
1. **Aktuelle Konfigurationen sichern** für vorherige Runde
2. **Konfigurationen laden** für neue Runde "Test1"
3. **Globale FieldConfiguration aktualisieren** mit "Test1"-Einstellungen

### 2. **Konfiguration ändern**
```python
# Admin schaltet Player Swap aus
field_config = FieldConfiguration.query.filter_by(field_type='player_swap').first()
field_config.is_enabled = False
```

**Was passiert beim nächsten Rundenwechsel:**
1. **Aktuelle Einstellungen** werden in `RoundFieldConfiguration` für "Test1" gespeichert
2. **Neue Runde aktivieren** lädt deren spezifische Konfigurationen

### 3. **Zurück zu "Test1" wechseln**
```python
# Admin aktiviert "Test1" wieder
test1_round.activate()
```

**Was passiert:**
1. **Player Swap ist immer noch aus** - so wie es eingestellt war
2. **Alle anderen Einstellungen** sind ebenfalls wiederhergestellt

## 📁 Erweiterte Spielstände-Sicherung

### 🗂️ Neue Ordnerstruktur (erweitert):
```
spielstaende/
└── runden/
    ├── Test1/
    │   ├── rundeninfo.json
    │   ├── teams.json
    │   ├── spielsitzung.json
    │   ├── konfiguration.json      # ← Rundenspezifische Konfigurationen!
    │   ├── ordner.json
    │   └── minigames/
    │       └── Default/
    │           └── minigames.json
    │
    └── Standard-Spiel/
        ├── rundeninfo.json
        ├── teams.json
        ├── spielsitzung.json
        ├── konfiguration.json      # ← Andere Konfigurationen!
        ├── ordner.json
        └── minigames/
```

### 📄 Beispiel `konfiguration.json` für "Test1":
```json
[
  {
    "field_type": "player_swap",
    "display_name": "Spieler-Tausch",
    "description": "Tauscht Position mit zufälligem anderen Team",
    "is_enabled": false,              // ← Für "Test1" ausgeschaltet
    "frequency_type": "modulo",
    "frequency_value": 17,
    "color_hex": "#0080FF",
    "emission_hex": "#0066CC",
    "icon": "🔄",
    "config_data": "{\"min_distance\": 3}"
  },
  {
    "field_type": "catapult_forward",
    "display_name": "Katapult Vorwärts",
    "is_enabled": true,               // ← Für "Test1" eingeschaltet
    "frequency_value": 15,
    "color_hex": "#32CD32",
    "icon": "🚀"
  }
]
```

### 📄 Beispiel `konfiguration.json` für "Standard-Spiel":
```json
[
  {
    "field_type": "player_swap",
    "display_name": "Spieler-Tausch",
    "is_enabled": true,               // ← Für "Standard-Spiel" eingeschaltet
    "frequency_value": 17,
    "color_hex": "#0080FF",
    "icon": "🔄"
  },
  {
    "field_type": "catapult_forward",
    "display_name": "Katapult Vorwärts",
    "is_enabled": false,              // ← Für "Standard-Spiel" ausgeschaltet
    "frequency_value": 15,
    "color_hex": "#32CD32",
    "icon": "🚀"
  }
]
```

## 🖥️ Erweiterte Admin-Oberfläche

### 🎯 Feld-Management zeigt aktive Runde
```html
<div class="alert alert-info">
    <i class="fas fa-info-circle"></i> 
    <strong>Aktive Runde:</strong> Test1
    <br>
    <small>Die Konfigurationen unten sind spezifisch für diese Runde und werden beim Rundenwechsel automatisch gespeichert.</small>
</div>
```

### 🔄 Rundenwechsel mit Feedback
```
✅ Spielrunde 'Test1' wurde aktiviert. Rundenspezifische Konfigurationen wurden geladen.
```

### 🗂️ Backup-System erweitert
- **Rundenspezifische Configs** werden automatisch gesichert
- **Wiederherstellung** lädt die korrekten Konfigurationen für jede Runde
- **Vollständige Trennung** zwischen verschiedenen Runden

## 🚀 Praktisches Beispiel

### 📋 Szenario: Zwei verschiedene Spiele

**"Test1" - Schnelles Spiel:**
- ✅ Katapult Vorwärts: **AN** (alle 10 Felder)
- ❌ Katapult Rückwärts: **AUS**
- ✅ Player Swap: **AN** (alle 15 Felder)
- ❌ Barrier: **AUS**

**"Standard-Spiel" - Langsames Spiel:**
- ❌ Katapult Vorwärts: **AUS**
- ✅ Katapult Rückwärts: **AN** (alle 20 Felder)
- ❌ Player Swap: **AUS**
- ✅ Barrier: **AN** (alle 25 Felder)

### 🎮 Workflow:

1. **"Test1" aktivieren**
   - Admin → Runden verwalten → "Test1" aktivieren
   - System lädt: Katapult Vorwärts AN, Player Swap AN, etc.

2. **Konfiguration anpassen**
   - Admin → Feld-Management → Player Swap ausschalten
   - Einstellung wird für "Test1" gespeichert

3. **Zu "Standard-Spiel" wechseln**
   - Admin → Runden verwalten → "Standard-Spiel" aktivieren
   - System lädt: Katapult Vorwärts AUS, Player Swap AUS, etc.
   - **Player Swap ist hier noch AUS** (eigene Einstellungen!)

4. **Zurück zu "Test1"**
   - Admin → Runden verwalten → "Test1" aktivieren
   - System lädt: **Player Swap ist immer noch AUS** (gespeicherte Einstellung!)

## 🔧 Technische Details

### 🏗️ Initialisierung
```python
# Bei Datenbank-Reset oder neuer Runde
round_obj.ensure_round_configurations()
```

**Was passiert:**
1. **Prüfe alle FieldConfiguration-Typen**
2. **Erstelle RoundFieldConfiguration** für jeden Typ
3. **Kopiere Standardwerte** aus globaler Konfiguration
4. **Speichere in Datenbank**

### 🔄 Rundenwechsel-Logik
```python
def activate(self):
    # 1. Sichere aktuelle Konfigurationen der vorherigen Runde
    self._save_current_configurations()
    
    # 2. Lade Konfigurationen für diese Runde
    self._load_round_configurations()
    
    # 3. Aktiviere Runde
    self.is_active = True
    db.session.commit()
```

### 💾 Automatische Sicherung
```python
def _save_current_configurations(self):
    # Hole aktuelle globale Konfigurationen
    global_configs = FieldConfiguration.query.all()
    
    # Speichere in rundenspezifische Tabelle
    for global_config in global_configs:
        round_config = RoundFieldConfiguration(...)
        db.session.add(round_config)
```

## 🎉 Ergebnis

### ✅ Vorher vs. Nachher

**❌ Vorher (Problem):**
- Alle Runden teilten dieselben Konfigurationen
- Änderungen beeinflussten alle Runden
- Konfigurationen gingen beim Rundenwechsel verloren

**✅ Nachher (Lösung):**
- **Jede Runde hat eigene Konfigurationen**
- **Änderungen sind rundenspezifisch**
- **Konfigurationen bleiben dauerhaft erhalten**
- **Automatisches Speichern/Laden beim Rundenwechsel**
- **Vollständige Sicherung in Spielständen**

### 🎯 Dein Wunsch erfüllt:
> "Wenn ich z.B. Test aktiviere und da Player Swap ausmache, dann zum Standard wechsel, dann ist player swap trotzdem aus."

**Jetzt nicht mehr!** 🎊

- **"Test1" aktivieren** → Player Swap ausmachen → **gespeichert für "Test1"**
- **"Standard-Spiel" aktivieren** → Player Swap ist dort **noch an**
- **Zurück zu "Test1"** → Player Swap ist **immer noch aus**

Das System ist jetzt vollständig rundenspezifisch und bereit für den produktiven Einsatz! 🚀