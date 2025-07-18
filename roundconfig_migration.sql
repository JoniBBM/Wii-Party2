-- Migration für RoundFieldConfiguration Tabelle
-- Führe dies in deiner SQLite-Datenbank aus

-- Erstelle die neue Tabelle
CREATE TABLE IF NOT EXISTS round_field_configuration (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_round_id INTEGER NOT NULL,
    field_type VARCHAR(50) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description VARCHAR(500),
    is_enabled BOOLEAN DEFAULT 1,
    frequency_type VARCHAR(20) DEFAULT 'modulo',
    frequency_value INTEGER DEFAULT 10,
    color_hex VARCHAR(7) NOT NULL,
    emission_hex VARCHAR(7),
    icon VARCHAR(10),
    config_data TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(game_round_id, field_type),
    FOREIGN KEY(game_round_id) REFERENCES game_round(id)
);

-- Beispiel: Erstelle rundenspezifische Konfigurationen für alle existierenden Runden
-- (Du musst dies für jede Runde und jeden Feldtyp anpassen)

-- Für Standard-Spiel Runde (ID 1 - anpassen falls anders):
INSERT OR IGNORE INTO round_field_configuration 
(game_round_id, field_type, display_name, description, is_enabled, frequency_type, frequency_value, color_hex, emission_hex, icon, config_data)
VALUES 
(1, 'start', 'Startfeld', 'Das Startfeld, wo alle Teams beginnen', 1, 'fixed_positions', 0, '#00BFFF', '#0066CC', '🏁', '{}'),
(1, 'goal', 'Zielfeld', 'Das Zielfeld - Hier gewinnt man!', 1, 'fixed_positions', 72, '#FF6600', '#CC4400', '🎯', '{}'),
(1, 'normal', 'Normale Felder', 'Standard-Spielfelder ohne besondere Effekte', 1, 'default', 0, '#00FF00', '#00CC00', '⬜', '{}'),
(1, 'catapult_forward', 'Katapult Vorwärts', 'Schleudert Teams 3-5 Felder nach vorne', 1, 'modulo', 15, '#32CD32', '#228B22', '🚀', '{"min_distance": 3, "max_distance": 5}'),
(1, 'catapult_backward', 'Katapult Rückwärts', 'Schleudert Teams 4-10 Felder nach hinten', 1, 'modulo', 13, '#FF0000', '#CC0000', '💥', '{"min_distance": 4, "max_distance": 10}'),
(1, 'player_swap', 'Spieler-Tausch', 'Tauscht Position mit zufälligem anderen Team', 1, 'modulo', 17, '#0080FF', '#0066CC', '🔄', '{"min_distance": 3}'),
(1, 'barrier', 'Sperren-Feld', 'Blockiert Team bis bestimmte Zahl gewürfelt wird', 1, 'modulo', 19, '#666666', '#333333', '🚧', '{"target_numbers": [4, 5, 6]}'),
(1, 'minigame', 'Minispiel', 'Startet ein Minispiel oder eine Frage', 1, 'modulo', 12, '#8A2BE2', '#6A1B9A', '🎮', '{}');

-- Für Test1 Runde (ID 2 - anpassen falls anders):
INSERT OR IGNORE INTO round_field_configuration 
(game_round_id, field_type, display_name, description, is_enabled, frequency_type, frequency_value, color_hex, emission_hex, icon, config_data)
VALUES 
(2, 'start', 'Startfeld', 'Das Startfeld, wo alle Teams beginnen', 1, 'fixed_positions', 0, '#00BFFF', '#0066CC', '🏁', '{}'),
(2, 'goal', 'Zielfeld', 'Das Zielfeld - Hier gewinnt man!', 1, 'fixed_positions', 72, '#FF6600', '#CC4400', '🎯', '{}'),
(2, 'normal', 'Normale Felder', 'Standard-Spielfelder ohne besondere Effekte', 1, 'default', 0, '#00FF00', '#00CC00', '⬜', '{}'),
(2, 'catapult_forward', 'Katapult Vorwärts', 'Schleudert Teams 3-5 Felder nach vorne', 1, 'modulo', 15, '#32CD32', '#228B22', '🚀', '{"min_distance": 3, "max_distance": 5}'),
(2, 'catapult_backward', 'Katapult Rückwärts', 'Schleudert Teams 4-10 Felder nach hinten', 1, 'modulo', 13, '#FF0000', '#CC0000', '💥', '{"min_distance": 4, "max_distance": 10}'),
(2, 'player_swap', 'Spieler-Tausch', 'Tauscht Position mit zufälligem anderen Team', 1, 'modulo', 17, '#0080FF', '#0066CC', '🔄', '{"min_distance": 3}'),
(2, 'barrier', 'Sperren-Feld', 'Blockiert Team bis bestimmte Zahl gewürfelt wird', 1, 'modulo', 19, '#666666', '#333333', '🚧', '{"target_numbers": [4, 5, 6]}'),
(2, 'minigame', 'Minispiel', 'Startet ein Minispiel oder eine Frage', 1, 'modulo', 12, '#8A2BE2', '#6A1B9A', '🎮', '{}');

-- Prüfe die Daten
SELECT 'Runden:' as info;
SELECT id, name FROM game_round;

SELECT 'Rundenspezifische Konfigurationen:' as info;
SELECT gr.name as round_name, rfc.field_type, rfc.is_enabled 
FROM round_field_configuration rfc
JOIN game_round gr ON rfc.game_round_id = gr.id
ORDER BY gr.name, rfc.field_type;