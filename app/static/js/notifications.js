/**
 * macOS-style Notification System
 * Zeigt Benachrichtigungen oben rechts im Bildschirm an
 */
class NotificationSystem {
    constructor() {
        this.container = null;
        this.notifications = [];
        this.init();
    }

    init() {
        // Erstelle Container für Notifications
        this.container = document.createElement('div');
        this.container.className = 'notification-container';
        document.body.appendChild(this.container);
        
        // Überwache Vollbildmodus-Änderungen
        this.setupFullscreenHandling();
    }
    
    setupFullscreenHandling() {
        const updateFullscreen = () => {
            const isFullscreen = document.fullscreenElement || 
                                document.webkitFullscreenElement || 
                                document.mozFullScreenElement;
            
            if (isFullscreen) {
                // Im Vollbildmodus: Container in das Vollbild-Element verschieben
                const fullscreenContainer = document.querySelector('#game-canvas-container');
                if (fullscreenContainer && !fullscreenContainer.contains(this.container)) {
                    fullscreenContainer.appendChild(this.container);
                }
                this.container.style.zIndex = '2147483647';
            } else {
                // Außerhalb Vollbildmodus: Container zurück zum body
                if (!document.body.contains(this.container)) {
                    document.body.appendChild(this.container);
                }
                this.container.style.zIndex = '999999';
            }
        };
        
        // Event Listener für Vollbildmodus-Änderungen
        document.addEventListener('fullscreenchange', updateFullscreen);
        document.addEventListener('webkitfullscreenchange', updateFullscreen);
        document.addEventListener('mozfullscreenchange', updateFullscreen);
        
        // Initial check
        updateFullscreen();
    }

    /**
     * Zeigt eine Würfelergebnis-Benachrichtigung an
     * @param {string} teamName - Name des Teams
     * @param {number} standardRoll - Standard-Würfelergebnis (1-6)
     * @param {number} bonusRoll - Bonus-Würfelergebnis (falls vorhanden)
     * @param {number} totalRoll - Gesamtergebnis
     * @param {number} duration - Anzeigedauer in ms (default: 8000)
     */
    showDiceRoll(teamName, standardRoll, bonusRoll = 0, totalRoll = null, duration = 8000) {
        if (totalRoll === null) {
            totalRoll = standardRoll + bonusRoll;
        }

        const notification = this.createNotification({
            type: 'dice',
            icon: '🎲',
            title: `${teamName} würfelt`,
            message: this.formatDiceMessage(standardRoll, bonusRoll, totalRoll),
            data: { standardRoll, bonusRoll, totalRoll },
            duration
        });

        this.showNotification(notification);
    }

    /**
     * Formatiert die Würfel-Nachricht
     */
    formatDiceMessage(standardRoll, bonusRoll, totalRoll) {
        if (bonusRoll > 0) {
            return `${standardRoll} + ${bonusRoll} (Bonus) = ${totalRoll} Felder`;
        }
        return `${standardRoll} ${totalRoll === 1 ? 'Feld' : 'Felder'}`;
    }

    /**
     * Erstellt eine Notification-Element
     */
    createNotification({type, icon, title, message, data, duration}) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        
        const id = Date.now() + Math.random();
        notification.dataset.id = id;

        let diceResultHtml = '';
        if (type === 'dice' && data) {
            diceResultHtml = this.createDiceResultHTML(data.standardRoll, data.bonusRoll, data.totalRoll);
        }

        notification.innerHTML = `
            <div class="notification-header">
                <span class="notification-icon">${icon}</span>
                <span class="notification-title">${title}</span>
            </div>
            <div class="notification-message">${message}</div>
            ${diceResultHtml}
            <div class="notification-progress" style="transition-duration: ${duration}ms;"></div>
        `;

        // Auto-hide Timer
        setTimeout(() => {
            this.hideNotification(notification);
        }, duration);

        // Progress Bar Animation
        const progressBar = notification.querySelector('.notification-progress');
        setTimeout(() => {
            progressBar.style.transform = 'scaleX(0)';
        }, 10);

        return notification;
    }

    /**
     * Erstellt HTML für Würfelergebnis-Anzeige
     */
    createDiceResultHTML(standardRoll, bonusRoll, totalRoll) {
        let diceVisual = `<div class="dice-cube">${standardRoll}</div>`;
        
        if (bonusRoll > 0) {
            diceVisual += `<span style="margin: 0 8px;">+</span><div class="dice-cube">${bonusRoll}</div>`;
        }

        return `
            <div class="notification-dice-result">
                <div class="dice-visual">
                    ${diceVisual}
                </div>
                <div class="dice-total">${totalRoll}</div>
            </div>
        `;
    }

    /**
     * Zeigt eine Notification an
     */
    showNotification(notification) {
        this.container.appendChild(notification);
        this.notifications.push(notification);

        // Animation starten
        requestAnimationFrame(() => {
            notification.classList.add('show');
        });

        // Prüfe, ob zu viele Notifications angezeigt werden
        this.limitNotifications();
    }

    /**
     * Versteckt eine Notification
     */
    hideNotification(notification) {
        if (!notification || !notification.parentNode) return;

        notification.classList.remove('show');
        notification.classList.add('hide');

        // Entferne nach Animation
        setTimeout(() => {
            if (notification.parentNode) {
                this.container.removeChild(notification);
                this.notifications = this.notifications.filter(n => n !== notification);
            }
        }, 400);
    }

    /**
     * Begrenzt die Anzahl der gleichzeitig angezeigten Notifications
     */
    limitNotifications(maxNotifications = 3) {
        while (this.notifications.length > maxNotifications) {
            const oldestNotification = this.notifications[0];
            this.hideNotification(oldestNotification);
        }
    }

    /**
     * Entfernt alle Notifications
     */
    clearAll() {
        this.notifications.forEach(notification => {
            this.hideNotification(notification);
        });
    }

    /**
     * Zeigt Katapult Vorwärts Benachrichtigung an
     */
    showCatapultForward(teamName, distance, duration = 8000) {
        const notification = this.createNotification({
            type: 'catapult-forward',
            icon: '🚀',
            title: `${teamName} - Katapult!`,
            message: `Wird ${distance} Felder nach vorne geschleudert!`,
            duration
        });

        this.showNotification(notification);
    }

    /**
     * Zeigt Katapult Rückwärts Benachrichtigung an
     */
    showCatapultBackward(teamName, distance, duration = 8000) {
        const notification = this.createNotification({
            type: 'catapult-backward',
            icon: '💥',
            title: `${teamName} - Katapult!`,
            message: `Wird ${distance} Felder zurück geschleudert!`,
            duration
        });

        this.showNotification(notification);
    }

    /**
     * Zeigt Spieler-Tausch Benachrichtigung an
     */
    showPlayerSwap(team1Name, team2Name, duration = 8000) {
        const notification = this.createNotification({
            type: 'player-swap',
            icon: '🔄',
            title: 'Positionstausch!',
            message: `${team1Name} tauscht Position mit ${team2Name}`,
            duration
        });

        this.showNotification(notification);
    }

    /**
     * Zeigt Sperren-Feld Benachrichtigung an
     */
    showBarrierSet(teamName, requiredNumber, duration = 8000) {
        const notification = this.createNotification({
            type: 'barrier-set',
            icon: '🚧',
            title: `${teamName} - Blockiert!`,
            message: `Muss ${requiredNumber}+ würfeln zum Befreien`,
            duration
        });

        this.showNotification(notification);
    }

    /**
     * Zeigt Befreiung vom Sperren-Feld an
     */
    showBarrierReleased(teamName, diceRoll, bonusRoll, method, duration = 8000) {
        let diceText = `${diceRoll}`;
        if (bonusRoll > 0) {
            diceText += ` + ${bonusRoll} = ${diceRoll + bonusRoll}`;
        }
        
        let methodText = '';
        if (method === 'standard') {
            methodText = ' (Standard-Würfel)';
        } else if (method === 'bonus') {
            methodText = ' (Bonus-Würfel)';
        } else if (method === 'total') {
            methodText = ' (Gesamtwurf)';
        }

        const notification = this.createNotification({
            type: 'barrier-released',
            icon: '🎉',
            title: `${teamName} - Befreit!`,
            message: `Gewürfelt: ${diceText}${methodText}`,
            duration
        });

        this.showNotification(notification);
    }

    /**
     * Zeigt fehlgeschlagene Befreiung an
     */
    showBarrierFailed(teamName, diceRoll, bonusRoll, requiredText, duration = 8000) {
        console.log('📱 showBarrierFailed called with:', { teamName, diceRoll, bonusRoll, requiredText, duration });
        
        let diceText = `${diceRoll}`;
        if (bonusRoll > 0) {
            diceText += ` + ${bonusRoll} = ${diceRoll + bonusRoll}`;
        }

        const notification = this.createNotification({
            type: 'barrier-failed',
            icon: '❌',
            title: `${teamName} - Noch blockiert!`,
            message: `Gewürfelt: ${diceText} - ${requiredText}`,
            duration
        });

        console.log('📱 Created barrier failed notification:', notification);
        this.showNotification(notification);
    }

    /**
     * Zeigt Benachrichtigung für Feld-Minigame Sieg an
     */
    showFieldMinigameWin(teamName, forwardFields, duration = 8000) {
        console.log('📱 showFieldMinigameWin called with:', { teamName, forwardFields, duration });
        
        const notification = this.createNotification({
            type: 'field-minigame-win',
            icon: '🏆',
            title: `${teamName} - Minigame gewonnen!`,
            message: `Belohnung: ${forwardFields} Felder vorwärts`,
            duration
        });

        console.log('📱 Created field minigame win notification:', notification);
        this.showNotification(notification);
    }

    /**
     * Zeigt Benachrichtigung für Feld-Minigame Niederlage an
     */
    showFieldMinigameLoss(teamName, duration = 8000) {
        console.log('📱 showFieldMinigameLoss called with:', { teamName, duration });
        
        const notification = this.createNotification({
            type: 'field-minigame-loss',
            icon: '💔',
            title: `${teamName} - Minigame verloren`,
            message: `Keine Belohnung - weiter geht's!`,
            duration
        });

        console.log('📱 Created field minigame loss notification:', notification);
        this.showNotification(notification);
    }

    /**
     * Zeigt eine einfache Benachrichtigung an
     */
    show(title, message, type = 'info', duration = 6000) {
        const icons = {
            info: 'ℹ️',
            success: '✅',
            warning: '⚠️',
            error: '❌',
            dice: '🎲'
        };

        const notification = this.createNotification({
            type,
            icon: icons[type] || icons.info,
            title,
            message,
            duration
        });

        this.showNotification(notification);
    }
}

// Globale Instance erstellen
window.NotificationSystem = window.NotificationSystem || new NotificationSystem();

// Debug: Teste System beim Load
console.log("🔔 NotificationSystem geladen:", !!window.NotificationSystem);

// Test-Notification beim Load (für Debug)
setTimeout(() => {
    if (window.NotificationSystem) {
        console.log("🔔 NotificationSystem Test erfolgreich");
        // Test-Notification entfernen nach dem Debugging
        // window.NotificationSystem.show("System Test", "NotificationSystem funktioniert!", "success", 2000);
    } else {
        console.error("🔔 NotificationSystem Test fehlgeschlagen");
    }
}, 1000);

// Für einfachere Verwendung
window.showNotification = (title, message, type, duration) => {
    window.NotificationSystem.show(title, message, type, duration);
};

window.showDiceNotification = (teamName, standardRoll, bonusRoll, totalRoll, duration) => {
    window.NotificationSystem.showDiceRoll(teamName, standardRoll, bonusRoll, totalRoll, duration);
};

// Hilfsfunktionen für Sonderfelder
window.showCatapultForwardNotification = (teamName, distance, duration) => {
    window.NotificationSystem.showCatapultForward(teamName, distance, duration);
};

window.showCatapultBackwardNotification = (teamName, distance, duration) => {
    window.NotificationSystem.showCatapultBackward(teamName, distance, duration);
};

window.showPlayerSwapNotification = (team1Name, team2Name, duration) => {
    window.NotificationSystem.showPlayerSwap(team1Name, team2Name, duration);
};

window.showBarrierSetNotification = (teamName, requiredNumber, duration) => {
    window.NotificationSystem.showBarrierSet(teamName, requiredNumber, duration);
};

window.showBarrierReleasedNotification = (teamName, diceRoll, bonusRoll, method, duration) => {
    window.NotificationSystem.showBarrierReleased(teamName, diceRoll, bonusRoll, method, duration);
};

window.showBarrierFailedNotification = (teamName, diceRoll, bonusRoll, requiredText, duration) => {
    window.NotificationSystem.showBarrierFailed(teamName, diceRoll, bonusRoll, requiredText, duration);
};

// Hilfsfunktionen für Feld-Minigames
window.showFieldMinigameWinNotification = (teamName, forwardFields, duration) => {
    window.NotificationSystem.showFieldMinigameWin(teamName, forwardFields, duration);
};

window.showFieldMinigameLossNotification = (teamName, duration) => {
    window.NotificationSystem.showFieldMinigameLoss(teamName, duration);
};