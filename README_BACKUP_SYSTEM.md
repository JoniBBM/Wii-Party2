# 🗂️ Erweiterte Runden-Backup & Wiederherstellung

## Übersicht

Das System wurde erweitert, um den **kompletten Spielzustand** zu speichern, nicht nur die Quizfragen. Jede Runde wird nun mit allen relevanten Daten gesichert und kann nach einem Datenbank-Reset vollständig wiederhergestellt werden.

## 🎯 Was wird gesichert?

### ✅ Vollständiger Spielzustand
- **Runden-Informationen**: Name, Beschreibung, Minigame-Ordner
- **Teams**: Alle Teams mit kompletten Daten
  - Positionen, Passwörter, Teammitglieder
  - Charakterauswahl und -anpassungen
  - Profilbilder und Spielerkonfigurationen
  - Sonderfeld-Status (Blockierungen, Extra-Bewegungen)
- **Spielsitzung**: Aktuelle GameSession mit allen Parametern
  - Minigame-Status, Spielerauswahl, Phasen
  - Gespielte Inhalte, Spieler-Rotation
  - Vulkan-System, Feld-Minigames
- **Konfigurationen**: Alle FieldConfiguration-Einstellungen
- **Minigame-Ordner**: Komplette Ordnerstruktur und Inhalte

### 🔄 Automatische Sicherung

Das System sichert automatisch bei:
- **Runden-Erstellung**: Neue Runden werden sofort gesichert
- **Runden-Bearbeitung**: Änderungen werden automatisch gesichert
- **Runden-Aktivierung**: Beim Wechsel wird der Status gesichert
- **Datenbank-Reset**: Alle Runden werden vor dem Reset gesichert

## 🛠️ Neue Admin-Funktionen

### 📊 Backup-Dashboard
- Erreichbar über: **Admin → Runden verwalten → Backup & Wiederherstellung**
- Zeigt Statistiken über Datenbank und gesicherte Runden
- Übersicht über Speicherplatz und Backup-Status

### 🔄 Bulk-Aktionen
- **Alle Runden sichern**: Sichert alle aktuellen Runden
- **Alle Runden wiederherstellen**: Stellt alle gesicherten Runden wieder her
- **Einzelne Runde sichern**: Sichert eine bestimmte Runde
- **Backup löschen**: Entfernt ein Backup aus dem Dateisystem

### 📋 Detaillierte Ansicht
- **Datenbank-Runden**: Alle aktuellen Runden mit Status
- **Gesicherte Runden**: Alle Backups mit Metadaten
- **Team-Anzahl**: Wie viele Teams pro Runde gesichert wurden
- **Timestamp**: Wann das Backup erstellt wurde

## 🗂️ Dateisystem-Struktur

```
app/static/saved_rounds/
├── Test1.json                 # Komplettes Backup mit allen Daten
├── Standard-Spiel.json        # Standard-Runde
└── Pfingstfreizeit-2025.json  # Weitere Runden
```

### 📄 Backup-Dateiformat (JSON)
```json
{
  "name": "Test1",
  "description": "Testrunde",
  "minigame_folder_name": "Default",
  "is_active": true,
  "created_at": "2025-07-17T18:07:21.099340",
  "saved_at": "2025-07-17T18:07:21.125647",
  
  "teams": [
    {
      "name": "Team Alpha",
      "members": "Alice, Bob, Charlie",
      "current_position": 15,
      "character_name": "Hero",
      "profile_images": "{\"Alice\": \"profile_images/alice.jpg\"}",
      "player_config": "{\"Alice\": {\"can_be_selected\": true}}",
      "is_blocked": false,
      "blocked_turns_remaining": 0,
      "extra_moves_remaining": 0
    }
  ],
  
  "game_session": {
    "current_phase": "DICE_ROLLING",
    "played_content_ids": "game_001,question_002",
    "player_rotation_data": "{\"1\": {\"Alice\": 2, \"Bob\": 1}}",
    "volcano_countdown": 3,
    "field_minigame_mode": "team_vs_all"
  },
  
  "field_configurations": [
    {
      "field_type": "catapult_forward",
      "display_name": "Katapult Vorwärts",
      "is_enabled": true,
      "frequency_value": 15,
      "color_hex": "#32CD32"
    }
  ],
  
  "minigame_folders": [
    {
      "name": "Default",
      "description": "Standard-Minispiele",
      "folder_path": "Default"
    }
  ],
  
  "minigame_contents": {
    "Default": [
      {
        "id": "game_001",
        "name": "Wer bin ich?",
        "type": "question",
        "question": "Wer ist der Autor von Harry Potter?",
        "options": ["J.K. Rowling", "J.R.R. Tolkien"],
        "correct_answer": 0
      }
    ]
  }
}
```

## 🔧 Technische Details

### 🏗️ Implementierung

1. **Erweiterte Speicher-Logik** (`save_round_to_filesystem()`)
   - Sammelt alle relevanten Daten aus der Datenbank
   - Erstellt vollständige JSON-Struktur
   - Sichert auch Minigame-Ordner-Inhalte

2. **Erweiterte Lade-Logik** (`restore_rounds_to_database()`)
   - Stellt alle Komponenten wieder her
   - Berücksichtigt bereits existierende Daten
   - Aktualisiert Konfigurationen falls nötig

3. **Automatische Sicherung** (`backup_all_rounds_before_db_reset()`)
   - Wird vor jedem `init_db.py` Lauf ausgeführt
   - Verhindert Datenverlust bei Datenbank-Resets

### 📡 API-Endpunkte

- `GET /admin/backup_rounds` - Backup-Dashboard anzeigen
- `POST /admin/backup_rounds` - Backup-Aktionen ausführen
  - `action=backup_all` - Alle Runden sichern
  - `action=restore_all` - Alle Runden wiederherstellen
  - `action=backup_single&round_id=X` - Einzelne Runde sichern
  - `action=delete_backup&round_name=X` - Backup löschen

## 🎮 Anwendung

### 🆕 Neue Runde erstellen: "Test1"

1. **Runde erstellen**: Admin → Runden verwalten → Neue Runde erstellen
2. **Automatische Sicherung**: Runde wird sofort mit allen Daten gesichert
3. **Spielen**: Teams können beitreten und spielen
4. **Kontinuierliche Sicherung**: Alle Änderungen werden automatisch gesichert

### 🔄 Nach Datenbank-Reset

1. **Automatische Sicherung**: Alle Runden werden vor Reset gesichert
2. **Datenbank-Reset**: `python init_db.py` ausführen
3. **Automatische Wiederherstellung**: Alle Runden werden wiederhergestellt
4. **Vollständiger Zustand**: Teams, Positionen, Konfigurationen sind wiederhergestellt

### 📋 Manuelle Verwaltung

1. **Backup-Dashboard**: Admin → Runden verwalten → Backup & Wiederherstellung
2. **Übersicht**: Alle Datenbank- und gesicherten Runden einsehen
3. **Aktionen**: Einzelne Runden sichern oder alle auf einmal
4. **Aufräumen**: Alte Backups löschen bei Bedarf

## 🏆 Vorteile

### ✅ Vollständiger Schutz
- **Kein Datenverlust**: Kompletter Spielzustand wird erhalten
- **Nahtlose Wiederherstellung**: Spiel kann sofort weitergehen
- **Automatische Sicherung**: Keine manuellen Schritte erforderlich

### 🔄 Flexibilität
- **Manuelle Kontrolle**: Admin kann jederzeit sichern/wiederherstellen
- **Selektive Wiederherstellung**: Nur bestimmte Runden wiederherstellen
- **Backup-Verwaltung**: Alte Backups können gelöscht werden

### 📊 Transparenz
- **Statistiken**: Überblick über Speicherplatz und Backup-Status
- **Detaillierte Informationen**: Anzahl Teams, Inhalte pro Runde
- **Zeitstempel**: Wann wurde was gesichert

## 🔮 Zukunftserweiterungen

- **Automatische Rotation**: Alte Backups automatisch löschen
- **Komprimierung**: Backups komprimieren für weniger Speicherplatz
- **Export/Import**: Runden zwischen verschiedenen Installationen teilen
- **Versionierung**: Mehrere Versionen einer Runde behalten
- **Cloud-Backup**: Backups in Cloud-Speicher sichern

---

Das System ist nun vollständig darauf ausgelegt, den kompletten Spielzustand zu erhalten und ist bereit für produktive Nutzung! 🚀