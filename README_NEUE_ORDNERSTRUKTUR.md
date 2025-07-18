# 📁 Neue Spielstände-Ordnerstruktur

## 🎯 Übersicht

Das System speichert jetzt alle Spielstände in einer **sauberen, separaten Ordnerstruktur**, getrennt von den Minigame-Ordnern. Jede Runde bekommt ihren eigenen Ordner mit allen relevanten Dateien.

## 📂 Ordnerstruktur

```
spielstaende/
├── runden/
│   ├── Test1/                          # Deine Runde "Test1"
│   │   ├── rundeninfo.json            # Runden-Metadaten
│   │   ├── teams.json                 # Alle Teams mit Positionen
│   │   ├── spielsitzung.json          # GameSession Daten
│   │   ├── konfiguration.json         # Feld-Konfigurationen
│   │   ├── ordner.json                # Minigame-Ordner Metadaten
│   │   └── minigames/                 # Kopie der Minigame-Ordner
│   │       ├── Default/
│   │       │   └── minigames.json     # Alle Spiele und Fragen
│   │       └── Pfingstfreizeit 2025/
│   │           └── minigames.json
│   │
│   ├── Standard-Spiel/                # Weitere Runden
│   │   ├── rundeninfo.json
│   │   ├── teams.json
│   │   ├── spielsitzung.json
│   │   ├── konfiguration.json
│   │   ├── ordner.json
│   │   └── minigames/
│   │       └── Default/
│   │           └── minigames.json
│   │
│   └── Pfingstfreizeit-2025/
│       └── ...
│
└── archive/                           # Zukünftig: Archiv alter Spielstände
    └── backup_2025_07_17/
```

## 📄 Datei-Aufbau

### 1. `rundeninfo.json` - Runden-Metadaten
```json
{
  "name": "Test1",
  "description": "Meine Testrunde",
  "minigame_folder_name": "Default",
  "is_active": true,
  "created_at": "2025-07-17T20:30:00.000000",
  "saved_at": "2025-07-17T20:45:15.123456",
  "version": "2.0"
}
```

### 2. `teams.json` - Alle Teams mit kompletten Daten
```json
[
  {
    "name": "Team Alpha",
    "members": "Alice, Bob, Charlie",
    "current_position": 25,
    "character_name": "Hero",
    "profile_images": "{\"Alice\": \"profile_images/alice.jpg\"}",
    "player_config": "{\"Alice\": {\"can_be_selected\": true}}",
    "is_blocked": false,
    "blocked_turns_remaining": 0,
    "extra_moves_remaining": 0,
    "password_hash": "pbkdf2:sha256:...",
    "welcome_password": "ABC123"
  },
  {
    "name": "Team Beta",
    "members": "David, Eve, Frank",
    "current_position": 18,
    "character_name": "Warrior",
    "is_blocked": true,
    "blocked_turns_remaining": 2
  }
]
```

### 3. `spielsitzung.json` - GameSession Daten
```json
{
  "current_phase": "DICE_ROLLING",
  "played_content_ids": "game_001,question_002,game_003",
  "player_rotation_data": "{\"1\": {\"Alice\": 3, \"Bob\": 2}, \"2\": {\"David\": 1}}",
  "current_minigame_name": "Wer bin ich?",
  "current_player_count": "2",
  "selected_players": "{\"1\": [\"Alice\", \"Bob\"], \"2\": [\"David\"]}",
  "volcano_countdown": 3,
  "volcano_active": false,
  "field_minigame_mode": "team_vs_all",
  "dice_roll_order": "1,2,3",
  "current_team_turn_id": 1
}
```

### 4. `konfiguration.json` - Feld-Konfigurationen
```json
[
  {
    "field_type": "catapult_forward",
    "display_name": "Katapult Vorwärts",
    "description": "Schleudert Teams 3-5 Felder nach vorne",
    "is_enabled": true,
    "frequency_type": "modulo",
    "frequency_value": 15,
    "color_hex": "#32CD32",
    "emission_hex": "#228B22",
    "icon": "🚀",
    "config_data": "{\"min_distance\": 3, \"max_distance\": 5}"
  },
  {
    "field_type": "barrier",
    "display_name": "Sperren-Feld",
    "is_enabled": true,
    "frequency_value": 19,
    "color_hex": "#666666",
    "icon": "🚧"
  }
]
```

### 5. `ordner.json` - Minigame-Ordner Metadaten
```json
[
  {
    "name": "Default",
    "description": "Standard-Minispiele für allgemeine Verwendung",
    "folder_path": "Default",
    "created_at": "2025-07-17T18:00:00.000000"
  },
  {
    "name": "Pfingstfreizeit 2025",
    "description": "Spezielle Spiele für die Pfingstfreizeit",
    "folder_path": "Pfingstfreizeit 2025",
    "created_at": "2025-07-17T19:00:00.000000"
  }
]
```

### 6. `minigames/[Ordnername]/minigames.json` - Kopie der Minigame-Inhalte
```json
{
  "folder_info": {
    "name": "Default",
    "description": "Standard-Minispiele",
    "created_at": "2025-07-17T18:00:00.000000"
  },
  "minigames": [
    {
      "id": "game_001",
      "name": "Wer bin ich?",
      "type": "question",
      "question": "Wer ist der Autor von Harry Potter?",
      "options": ["J.K. Rowling", "J.R.R. Tolkien", "Stephen King"],
      "correct_answer": 0,
      "player_count": "2",
      "created_at": "2025-07-17T18:05:00.000000"
    },
    {
      "id": "game_002",
      "name": "Pantomime",
      "type": "game",
      "description": "Stelle einen Begriff pantomimisch dar",
      "player_count": "1",
      "created_at": "2025-07-17T18:10:00.000000"
    }
  ]
}
```

## 🔄 Automatische Sicherung

### ✅ Beim Erstellen einer Runde: "Test1"

1. **Ordner erstellen**: `spielstaende/runden/Test1/`
2. **Rundeninfo speichern**: `rundeninfo.json`
3. **Teams sichern**: Alle aktuellen Teams in `teams.json`
4. **Spielsitzung sichern**: Aktuelle GameSession in `spielsitzung.json`
5. **Konfiguration sichern**: Alle FieldConfigurations in `konfiguration.json`
6. **Minigame-Ordner kopieren**: Komplette Kopie in `minigames/`

### 🔄 Bei Änderungen

Das System sichert automatisch bei:
- Runden-Bearbeitung
- Team-Änderungen
- Spielfortschritt
- Konfigurationsänderungen

## 🛠️ Vorteile der neuen Struktur

### ✅ Saubere Trennung
- **Spielstände** sind getrennt von **Minigame-Ordnern**
- Jede Runde hat ihren eigenen Ordner
- Keine Konflikte zwischen verschiedenen Runden

### 📊 Bessere Organisation
- **Strukturierte Dateien** statt einer großen JSON-Datei
- **Leichter zu debuggen** und zu verstehen
- **Modulare Wiederherstellung** möglich

### 🔄 Flexibilität
- **Backward Compatibility**: Alte JSON-Dateien werden weiterhin unterstützt
- **Selektive Wiederherstellung**: Nur bestimmte Teile wiederherstellen
- **Einfache Erweiterung**: Neue Dateien können hinzugefügt werden

### 💾 Vollständige Sicherung
- **Komplette Minigame-Ordner** werden kopiert
- **Alle Spiele und Fragen** sind gesichert
- **Unabhängig von der Haupt-Installation**

## 🔧 Technische Details

### 🏗️ Speicher-Prozess

1. **Ordner erstellen**: `spielstaende/runden/[RundenName]/`
2. **Daten sammeln**: Alle relevanten Daten aus der Datenbank
3. **Dateien schreiben**: Separate JSON-Dateien für jede Kategorie
4. **Minigames kopieren**: Komplette Kopie der Minigame-Ordner
5. **Validierung**: Prüfung auf erfolgreiche Speicherung

### 🔄 Lade-Prozess

1. **Ordner scannen**: Alle Ordner in `spielstaende/runden/`
2. **Dateien laden**: Einzelne JSON-Dateien einlesen
3. **Daten kombinieren**: Zusammenfügen für Kompatibilität
4. **Wiederherstellung**: Daten zurück in die Datenbank

### 🔒 Backward Compatibility

Das System unterstützt weiterhin:
- **Alte JSON-Dateien**: Werden automatisch erkannt und geladen
- **Gemischte Strukturen**: Alte und neue Formate gleichzeitig
- **Nahtlose Migration**: Beim nächsten Speichern wird neue Struktur verwendet

## 🎮 Anwendungsbeispiele

### 📝 Runde "Test1" erstellen

```bash
# Admin-Interface → Runden verwalten → Neue Runde erstellen
# Name: Test1
# Beschreibung: Meine Testrunde
# Minigame-Ordner: Default
```

**Ergebnis**: Automatische Erstellung von `spielstaende/runden/Test1/` mit allen Dateien

### 🔄 Nach Datenbank-Reset

```bash
python init_db.py
```

**Automatischer Ablauf**:
1. Vor Reset: Alle Runden werden automatisch gesichert
2. Nach Reset: Alle Runden werden automatisch wiederhergestellt
3. Spielfortschritt: Bleibt vollständig erhalten

### 📊 Manuelle Verwaltung

```
Admin → Runden verwalten → Backup & Wiederherstellung
```

**Funktionen**:
- Einzelne Runden sichern
- Alle Runden wiederherstellen
- Statistiken anzeigen
- Alte Backups löschen

## 🚀 Zukünftige Erweiterungen

### 📦 Geplante Features

- **Archiv-System**: Alte Spielstände automatisch archivieren
- **Komprimierung**: Spielstände komprimieren für weniger Speicherplatz
- **Export/Import**: Spielstände zwischen Installationen teilen
- **Versionierung**: Mehrere Versionen einer Runde behalten
- **Cloud-Sync**: Spielstände in der Cloud synchronisieren

### 🔧 Weitere Optimierungen

- **Inkrementelle Backups**: Nur Änderungen speichern
- **Automatische Bereinigung**: Alte Backups automatisch löschen
- **Backup-Validierung**: Integrität der Backups prüfen
- **Performance-Optimierung**: Schnellere Speicher- und Lade-Vorgänge

---

Die neue Ordnerstruktur bietet eine saubere, professionelle Lösung für die Verwaltung von Spielständen und ist bereit für den produktiven Einsatz! 🎯