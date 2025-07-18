-- SQL-Script zum Löschen aller existierenden Runden
-- Führe dies in deiner SQLite-Datenbank aus: sqlite3 instance/database.db < clean_rounds.sql

-- Zeige aktuellen Zustand
SELECT 'Aktuelle Runden:' as info;
SELECT id, name, is_active FROM game_round;

SELECT 'Aktuelle rundenspezifische Konfigurationen:' as info;
SELECT COUNT(*) as count FROM round_field_configuration;

SELECT 'Aktive GameSessions:' as info;
SELECT COUNT(*) as count FROM game_session WHERE is_active = 1;

-- Bereinigung beginnen
SELECT 'Starte Bereinigung...' as info;

-- 1. Alle GameSessions deaktivieren
UPDATE game_session SET is_active = 0;
SELECT 'GameSessions deaktiviert' as status;

-- 2. Alle rundenspezifischen Konfigurationen löschen
DELETE FROM round_field_configuration;
SELECT 'Rundenspezifische Konfigurationen gelöscht' as status;

-- 3. Alle GameRounds löschen
DELETE FROM game_round;
SELECT 'Alle GameRounds gelöscht' as status;

-- 4. Prüfe Ergebnis
SELECT 'Bereinigung abgeschlossen!' as info;

SELECT 'Verbleibende Runden:' as info;
SELECT COUNT(*) as count FROM game_round;

SELECT 'Verbleibende rundenspezifische Konfigurationen:' as info;
SELECT COUNT(*) as count FROM round_field_configuration;

SELECT 'Globale FieldConfigurations (bleiben erhalten):' as info;
SELECT field_type, display_name, is_enabled FROM field_configuration ORDER BY field_type;

SELECT 'System bereit für manuelle Runden-Erstellung!' as status;