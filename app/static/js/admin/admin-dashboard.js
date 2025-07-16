/**
 * Admin Dashboard JavaScript - Complete functionality for admin interface
 */

// Global variables
let isRollingDice = false;
let questionResponsesInterval = null;
let currentPhase = '';
let lastResponseCount = 0;
let csrfToken = '';

/**
 * Initialize admin dashboard
 */
function initAdminDashboard(config) {
    // Set global configuration
    csrfToken = config.csrfToken;
    currentPhase = config.currentPhase;
    
    document.addEventListener('DOMContentLoaded', function() {
        initializeComponents();
        initializeEventListeners();
        startPeriodicUpdates();
    });
}

/**
 * Initialize all dashboard components
 */
function initializeComponents() {
    initializeMinigameSourceSelection();
    initializeDirectQuestionType();
    initializeWelcomeSystem();
    initializeTeamManagement();
    
    // Setup initial phase display
    if (currentPhase === 'QUESTION_ACTIVE') {
        startQuestionResponsesPolling();
    }
}

/**
 * Initialize event listeners
 */
function initializeEventListeners() {
    const rollDiceBtn = document.getElementById('admin-roll-dice');
    if (rollDiceBtn) {
        rollDiceBtn.addEventListener('click', adminRollDice);
    }
    
    // Team management controls
    const teamCountSelect = document.getElementById('team-count-select');
    if (teamCountSelect) {
        teamCountSelect.addEventListener('change', handleTeamCountChange);
    }
    
    const createTeamsBtn = document.getElementById('create-teams-admin-btn');
    if (createTeamsBtn) {
        createTeamsBtn.addEventListener('click', handleCreateTeams);
    }
    
    const fullscreenBtn = document.getElementById('start-fullscreen-game-btn');
    if (fullscreenBtn) {
        fullscreenBtn.addEventListener('click', handleFullscreenGame);
    }
}

/**
 * Initialize minigame source selection
 */
function initializeMinigameSourceSelection() {
    const sourceRadios = document.querySelectorAll('input[name="minigame_source"]');
    const sections = document.querySelectorAll('.minigame-section');
    
    function showMinigameSection(selectedValue) {
        sections.forEach(section => section.classList.add('hidden'));
        const targetSection = document.getElementById(selectedValue + '-section');
        if (targetSection) targetSection.classList.remove('hidden');
        
        localStorage.setItem('adminMinigameSource', selectedValue);
    }
    
    sourceRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.checked) showMinigameSection(this.value);
        });
    });
    
    // Restore saved selection
    const savedSource = localStorage.getItem('adminMinigameSource');
    if (savedSource) {
        const savedRadio = document.getElementById('source_' + savedSource);
        if (savedRadio) {
            savedRadio.checked = true;
            showMinigameSection(savedSource);
        }
    } else {
        const checkedRadio = document.querySelector('input[name="minigame_source"]:checked');
        if (checkedRadio) showMinigameSection(checkedRadio.value);
    }
}

/**
 * Initialize direct question type handling
 */
function initializeDirectQuestionType() {
    const directQuestionType = document.getElementById('direct-question-type');
    const mcOptions = document.getElementById('direct-mc-options');
    const textAnswer = document.getElementById('direct-text-answer');
    
    function toggleDirectQuestionType() {
        if (directQuestionType) {
            const selectedType = directQuestionType.value;
            if (mcOptions && textAnswer) {
                if (selectedType === 'multiple_choice') {
                    mcOptions.classList.remove('hidden');
                    textAnswer.classList.add('hidden');
                } else {
                    mcOptions.classList.add('hidden');
                    textAnswer.classList.remove('hidden');
                }
            }
        }
    }
    
    if (directQuestionType) {
        directQuestionType.addEventListener('change', toggleDirectQuestionType);
        toggleDirectQuestionType();
    }
}

/**
 * Load question responses
 */
function loadQuestionResponses() {
    if (currentPhase !== 'QUESTION_ACTIVE') return;
    
    fetch('/admin/api/question-responses')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayQuestionResponses(data.responses, data.total_teams);
                updateResponseCount(data.responses, data.total_teams);
            }
        })
        .catch(error => {
            console.warn('Fehler beim Laden der Antworten:', error);
        });
}

/**
 * Display question responses
 */
function displayQuestionResponses(responses, totalTeams) {
    const responsesList = document.getElementById('question-responses-list');
    if (!responsesList) return;
    
    if (responses.length === 0) {
        responsesList.innerHTML = '<div class="text-center text-muted"><i class="fas fa-clock"></i> Warte auf Antworten...</div>';
        return;
    }
    
    let html = '<div class="row">';
    responses.forEach((response, index) => {
        const statusIcon = response.is_correct ? '<i class="fas fa-check text-success"></i>' : '<i class="fas fa-times text-danger"></i>';
        const statusClass = response.is_correct ? 'correct' : 'incorrect';
        const isNew = index >= lastResponseCount;
        
        html += `
            <div class="col-md-6 mb-2">
                <div class="response-item ${statusClass} ${isNew ? 'new' : ''}">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${response.team_name}</strong>
                            <small class="d-block text-muted">${response.answer_preview}</small>
                            ${response.answered_at ? `<small class="text-muted">${response.answered_at}</small>` : ''}
                        </div>
                        <span>${statusIcon}</span>
                    </div>
                </div>
            </div>
        `;
    });
    html += '</div>';
    
    if (responses.length === totalTeams && totalTeams > 0) {
        html += '<div class="alert alert-success mt-3 mb-0"><i class="fas fa-check-circle"></i> Alle Teams haben geantwortet!</div>';
    }
    
    responsesList.innerHTML = html;
    lastResponseCount = responses.length;
}

/**
 * Update response count display
 */
function updateResponseCount(responses, totalTeams) {
    const responseCount = document.getElementById('question-response-count');
    if (responseCount) {
        const count = responses.length;
        responseCount.innerHTML = `${count}/${totalTeams} Teams haben geantwortet`;
        
        if (count === totalTeams && count > 0) {
            responseCount.innerHTML += ' <span class="badge badge-success">Alle</span>';
        }
    }
}

/**
 * Admin dice rolling functionality
 */
function adminRollDice() {
    if (isRollingDice) return;
    isRollingDice = true;
    
    const rollDiceBtn = document.getElementById('admin-roll-dice');
    rollDiceBtn.disabled = true;
    rollDiceBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Würfeln...';
    
    fetch(getAdminRollDiceUrl(), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken 
        },
        body: JSON.stringify({})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showDiceResult(data);
            setTimeout(updateGameStatus, 500);
        } else {
            alert('Fehler: ' + (data.error || 'Unbekannter Fehler'));
            resetDiceButton();
        }
    })
    .catch(error => {
        alert('Netzwerkfehler beim Würfeln.');
        resetDiceButton();
    });
}

/**
 * Reset dice button to initial state
 */
function resetDiceButton() {
    isRollingDice = false;
    const rollDiceBtn = document.getElementById('admin-roll-dice');
    if (rollDiceBtn) {
        rollDiceBtn.disabled = false;
        rollDiceBtn.innerHTML = '<i class="fas fa-dice"></i> Für aktuelles Team würfeln';
        rollDiceBtn.classList.remove('btn-secondary');
        rollDiceBtn.classList.add('btn-success');
    }
}

/**
 * Show dice result animation
 */
function showDiceResult(data) {
    document.getElementById('admin-standard-roll').textContent = data.standard_roll;
    document.getElementById('admin-total-roll').textContent = data.total_roll;
    
    const bonusSection = document.getElementById('admin-bonus-section');
    if (data.bonus_roll > 0) {
        document.getElementById('admin-bonus-roll').textContent = data.bonus_roll;
        bonusSection.classList.remove('hidden');
    } else {
        bonusSection.classList.add('hidden');
    }
    
    const diceResultDiv = document.getElementById('dice-result-admin');
    diceResultDiv.classList.remove('hidden');
    
    setTimeout(() => diceResultDiv.classList.add('hidden'), 4000);
}

/**
 * Update game status from server
 */
function updateGameStatus() {
    fetch(getBoardStatusUrl() + '?t=' + new Date().getTime())
        .then(response => response.json())
        .then(data => {
            if (data.game_session) {
                const newPhase = data.game_session.current_phase;
                
                if (newPhase !== currentPhase) {
                    currentPhase = newPhase;
                    updatePhaseDisplay(newPhase);
                    updateSectionVisibility(newPhase);
                    
                    if (newPhase === 'QUESTION_ACTIVE') {
                        startQuestionResponsesPolling();
                    } else {
                        stopQuestionResponsesPolling();
                    }
                }
                
                if (newPhase === 'DICE_ROLLING') {
                    const newTeamId = data.game_session.current_team_turn_id;
                    updateCurrentTeamDisplay(data.teams, newTeamId);
                    resetDiceButton();
                }
                
                updateContentInfo(data.game_session);
            }
        })
        .catch(error => console.warn('Status-Update fehlgeschlagen:', error));
}

/**
 * Update phase display
 */
function updatePhaseDisplay(phase) {
    const phaseDisplay = document.getElementById('current-phase-display');
    if (phaseDisplay) {
        let phaseText = '';
        switch(phase) {
            case 'SETUP_MINIGAME':
                phaseText = 'Inhalt festlegen';
                break;
            case 'MINIGAME_ANNOUNCED':
                phaseText = 'Minispiel angekündigt - Warte auf Platzierungen';
                break;
            case 'QUESTION_ACTIVE':
                phaseText = 'Frage läuft - Teams antworten';
                break;
            case 'DICE_ROLLING':
                phaseText = 'Würfelrunde aktiv';
                break;
            case 'ROUND_OVER':
                phaseText = 'Runde beendet - Nächsten Inhalt festlegen';
                break;
            default:
                phaseText = phase.replace('_', ' ').title();
        }
        phaseDisplay.textContent = phaseText;
        phaseDisplay.setAttribute('data-phase', phase);
    }
}

/**
 * Update section visibility based on game phase
 */
function updateSectionVisibility(phase) {
    const sections = [
        'question-control-section',
        'dice-control-section', 
        'content-selection-section',
        'placement-section'
    ];
    
    sections.forEach(sectionId => {
        const section = document.getElementById(sectionId);
        if (section) section.classList.add('hidden');
    });
    
    let targetSection = null;
    switch(phase) {
        case 'QUESTION_ACTIVE':
            targetSection = 'question-control-section';
            break;
        case 'DICE_ROLLING':
            targetSection = 'dice-control-section';
            break;
        case 'SETUP_MINIGAME':
        case 'ROUND_OVER':
            targetSection = 'content-selection-section';
            break;
        case 'MINIGAME_ANNOUNCED':
            targetSection = 'placement-section';
            break;
    }
    
    if (targetSection) {
        const section = document.getElementById(targetSection);
        if (section) section.classList.remove('hidden');
    }
}

/**
 * Update current team display
 */
function updateCurrentTeamDisplay(teams, currentTeamId) {
    const currentTurnInfo = document.getElementById('current-turn-info');
    if (!currentTurnInfo) return;
    
    if (!currentTeamId) {
        currentTurnInfo.innerHTML = '<span class="text-muted">Runde beendet</span>';
        return;
    }
    
    const currentTeam = teams.find(t => t.id === currentTeamId);
    if (currentTeam) {
        let bonusText = 'Standard';
        if (currentTeam.bonus_dice_sides === 6) bonusText = '1-6';
        else if (currentTeam.bonus_dice_sides === 4) bonusText = '1-4';
        else if (currentTeam.bonus_dice_sides === 2) bonusText = '1-2';
        
        currentTurnInfo.innerHTML = `
            <span class="badge badge-primary badge-team-status">
                ${currentTeam.name}
            </span>
            <small class="d-block mt-1">
                Position: ${currentTeam.position} | Bonus: ${bonusText}
            </small>
        `;
    }
}

/**
 * Update content info display
 */
function updateContentInfo(gameSession) {
    const contentInfo = document.getElementById('current-content-info');
    const minigameName = document.getElementById('current-minigame-name');
    
    if (contentInfo) {
        if (gameSession.current_minigame_name) {
            const isQuestion = gameSession.current_phase === 'QUESTION_ACTIVE';
            const icon = isQuestion ? '❓' : '🎮';
            const type = isQuestion ? 'Frage' : 'Minispiel';
            
            contentInfo.innerHTML = `
                <p><strong>Aktueller Inhalt:</strong> ${icon} ${type}: ${gameSession.current_minigame_name}</p>
                ${gameSession.current_minigame_description ? `<p><em>Beschreibung: ${gameSession.current_minigame_description}</em></p>` : ''}
            `;
        } else {
            contentInfo.innerHTML = '<p>Noch kein Inhalt für diese Runde festgelegt.</p>';
        }
    }
    
    if (minigameName) {
        minigameName.textContent = gameSession.current_minigame_name || '';
    }
}

/**
 * Start question responses polling
 */
function startQuestionResponsesPolling() {
    if (questionResponsesInterval) clearInterval(questionResponsesInterval);
    
    loadQuestionResponses();
    questionResponsesInterval = setInterval(loadQuestionResponses, 2000);
}

/**
 * Stop question responses polling
 */
function stopQuestionResponsesPolling() {
    if (questionResponsesInterval) {
        clearInterval(questionResponsesInterval);
        questionResponsesInterval = null;
    }
    lastResponseCount = 0;
}

/**
 * Initialize welcome system
 */
function initializeWelcomeSystem() {
    updateWelcomeStatus();
    setInterval(updateWelcomeStatus, 5000);
}

/**
 * Update welcome system status
 */
function updateWelcomeStatus() {
    fetch('/api/welcome-admin-status')
        .then(response => response.json())
        .then(data => {
            const statusCard = document.getElementById('welcome-status-card');
            const startBtn = document.getElementById('start-welcome-btn');
            
            if (data.active) {
                displayActiveWelcomeStatus(data, statusCard, startBtn);
                updateTeamManagementControls(data);
            } else {
                displayInactiveWelcomeStatus(statusCard, startBtn);
                hideTeamManagementControls();
            }
        })
        .catch(error => {
            console.error('Error updating welcome status:', error);
            displayWelcomeError();
        });
}

/**
 * Display active welcome status
 */
function displayActiveWelcomeStatus(data, statusCard, startBtn) {
    let teamsDisplay = '';
    if (data.teams_created && data.teams && data.teams.length > 0) {
        teamsDisplay = `
            <div class="mt-3">
                <small class="text-info"><strong>Teams & Passwörter:</strong></small>
                <div class="mt-2">
                    ${data.teams.map(team => `
                        <div class="card card-body p-2 mb-2 team-card-compact">
                            <div class="d-flex justify-content-between align-items-center">
                                <strong>Team ${team.name}</strong>
                                <span class="badge badge-dark badge-team-password">🔑 ${team.password}</span>
                            </div>
                            <div class="team-card-detail">
                                ${team.members.join(', ')}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    statusCard.innerHTML = `
        <div class="text-success">
            <i class="fas fa-check-circle"></i> <strong>Aktiv</strong>
        </div>
        <div class="mt-2">
            <small class="text-muted">Spieler registriert: <strong>${data.player_count || 0}</strong></small>
        </div>
        ${data.teams_created ? `
            <div class="mt-2">
                <small class="text-info">Teams erstellt: <strong>${data.team_count || 0}</strong></small>
            </div>
            <div class="mt-2">
                <span class="badge badge-success">Bereit zum Spielstart</span>
            </div>
            ${teamsDisplay}
        ` : `
            <div class="mt-2">
                <span class="badge badge-warning">Warten auf Teamaufteilung</span>
            </div>
        `}
    `;
    
    startBtn.innerHTML = '<i class="fas fa-stop"></i> Beenden';
    startBtn.className = 'btn btn-danger btn-sm';
    startBtn.onclick = () => endWelcomeSystem();
}

/**
 * Display inactive welcome status
 */
function displayInactiveWelcomeStatus(statusCard, startBtn) {
    statusCard.innerHTML = `
        <div class="text-muted">
            <i class="fas fa-pause-circle"></i> <strong>Inaktiv</strong>
        </div>
        <div class="mt-2">
            <small class="text-muted">Welcome-System ist nicht aktiv</small>
        </div>
    `;
    
    startBtn.innerHTML = '<i class="fas fa-play"></i> Starten';
    startBtn.className = 'btn btn-success btn-sm';
    startBtn.onclick = () => startWelcomeSystem();
}

/**
 * Display welcome system error
 */
function displayWelcomeError() {
    const statusCard = document.getElementById('welcome-status-card');
    statusCard.innerHTML = `
        <div class="text-danger">
            <i class="fas fa-exclamation-triangle"></i> Fehler beim Laden
        </div>
    `;
}

/**
 * Start welcome system
 */
function startWelcomeSystem() {
    fetch('/admin/api/start-welcome', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrfToken
        },
        credentials: 'same-origin',
        body: JSON.stringify({})
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errorData => {
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            updateWelcomeStatus();
            alert('Welcome-System erfolgreich gestartet! Welcome-Seite ist jetzt aktiv.');
        } else {
            alert('Fehler beim Starten: ' + data.error);
            updateWelcomeStatus();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Ein Fehler ist aufgetreten: ' + error.message);
        updateWelcomeStatus();
    });
}

/**
 * End welcome system
 */
function endWelcomeSystem() {
    if (confirm('Welcome-System wirklich beenden?')) {
        fetch('/admin/api/end-registration', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken
            },
            credentials: 'same-origin',
            body: JSON.stringify({})
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateWelcomeStatus();
                alert('Welcome-System erfolgreich beendet.');
            } else {
                alert('Fehler beim Beenden: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Ein Fehler ist aufgetreten beim Beenden des Welcome-Systems');
        });
    }
}

/**
 * Initialize team management
 */
function initializeTeamManagement() {
    // Event listeners are set in initializeEventListeners
}

/**
 * Update team management controls visibility
 */
function updateTeamManagementControls(data) {
    const teamControls = document.getElementById('team-management-controls');
    if (data.teams_created) {
        teamControls.classList.add('hidden');
    } else {
        teamControls.classList.remove('hidden');
    }
}

/**
 * Hide team management controls
 */
function hideTeamManagementControls() {
    const teamControls = document.getElementById('team-management-controls');
    teamControls.classList.add('hidden');
}

/**
 * Handle team count selection change
 */
function handleTeamCountChange() {
    const teamCountSelect = document.getElementById('team-count-select');
    const createBtn = document.getElementById('create-teams-admin-btn');
    createBtn.disabled = teamCountSelect.value === '';
}

/**
 * Handle create teams button click
 */
function handleCreateTeams() {
    const teamCount = document.getElementById('team-count-select').value;
    if (!teamCount) {
        alert('Bitte wähle zuerst die Anzahl der Teams!');
        return;
    }
    
    if (confirm(`${teamCount} Teams erstellen? Dies teilt die registrierten Spieler automatisch auf.`)) {
        fetch('/admin/api/create-teams', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ team_count: parseInt(teamCount) })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateWelcomeStatus();
                alert('Teams erfolgreich erstellt! Passwörter sind im Admin-Dashboard sichtbar.');
            } else {
                alert('Fehler beim Erstellen der Teams: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Ein Fehler ist aufgetreten beim Erstellen der Teams');
        });
    }
}

/**
 * Handle fullscreen game start
 */
function handleFullscreenGame() {
    const gameWindow = window.open('/admin/open-board', '_blank');
    
    setTimeout(() => {
        if (gameWindow) {
            gameWindow.postMessage({action: 'requestFullscreen'}, '*');
            
            if (!gameWindow.document.fullscreenElement) {
                gameWindow.alert('Für die beste Erfahrung drücke F11 für Vollbild!');
            }
        }
    }, 1000);
}

/**
 * Show rotation statistics
 */
function showRotationStats() {
    fetch('/admin/player_rotation_stats')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayRotationStatsModal(data.stats);
            } else {
                alert('Fehler beim Laden der Statistiken: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Ein Fehler ist aufgetreten beim Laden der Statistiken');
        });
}

/**
 * Display rotation statistics in modal
 */
function displayRotationStatsModal(stats) {
    let statsHtml = '<h5>Spieler-Rotation Statistiken</h5>';
    
    if (Object.keys(stats).length === 0) {
        statsHtml += '<p class="text-muted">Noch keine Rotations-Daten verfügbar.</p>';
    } else {
        statsHtml += '<div class="row">';
        for (const [teamName, teamStats] of Object.entries(stats)) {
            statsHtml += `
                <div class="col-md-6 mb-3">
                    <div class="card">
                        <div class="card-header">
                            <strong>${teamName}</strong>
                            <small class="text-muted">(${teamStats.total_games} Spiele gesamt)</small>
                        </div>
                        <div class="card-body">
                            <div class="player-stats">
            `;
            
            for (const [playerName, gameCount] of Object.entries(teamStats.players)) {
                const isEqual = gameCount === teamStats.least_played && gameCount === teamStats.most_played;
                const isLeast = gameCount === teamStats.least_played && !isEqual;
                const isMost = gameCount === teamStats.most_played && !isEqual;
                
                let badgeClass = 'badge-secondary';
                if (isLeast) badgeClass = 'badge-success';
                if (isMost) badgeClass = 'badge-warning';
                
                statsHtml += `<span class="badge ${badgeClass} mr-1">${playerName}: ${gameCount}</span>`;
            }
            
            statsHtml += `
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        statsHtml += '</div>';
    }
    
    document.getElementById('rotationModalBody').innerHTML = statsHtml;
    $('#rotationModal').modal('show');
}

/**
 * Reset player rotation
 */
function resetRotation() {
    if (confirm('Spieler-Rotation zurücksetzen? Alle Spieler starten wieder mit 0 Einsätzen.')) {
        fetch('/admin/reset_player_rotation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Spieler-Rotation erfolgreich zurückgesetzt!');
                location.reload();
            } else {
                alert('Fehler beim Zurücksetzen: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Ein Fehler ist aufgetreten beim Zurücksetzen');
        });
    }
}

/**
 * Start periodic updates
 */
function startPeriodicUpdates() {
    setInterval(updateGameStatus, 3000);
}

/**
 * Get URL helpers (to be set by template)
 */
function getAdminRollDiceUrl() {
    return window.adminUrls ? window.adminUrls.rollDice : '/admin/admin_roll_dice';
}

function getBoardStatusUrl() {
    return window.adminUrls ? window.adminUrls.boardStatus : '/api/board-status';
}

// Global functions for backwards compatibility
window.showRotationStats = showRotationStats;
window.resetRotation = resetRotation;