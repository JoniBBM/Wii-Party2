/**
 * Team Dashboard JavaScript
 * Main functionality for the team dashboard page
 */

// Global variables (initialized from template)
let lastGameData = null;
let isCurrentlyMyTurn = false;
let myTeamId = null;
let updateInterval = null;
let isDiceAnimationShowing = false;
let lastMinigameName = "";
let hasShowMinigameResults = false;
let lastPhase = "UNKNOWN";
let serverLastDiceResult = null;
let lastDiceResult = null;
let lastQuestionData = null;
let currentQuestionAnswered = false;
let diceResultTimer = null;

// Track if user is currently interacting with question form
let userInteractingWithQuestion = false;
let questionInterfaceInitialized = false;

// Banner variables
let lastSelectedPlayers = null;
let bannerTimer = null;
let progressTimer = null;
let lastSpecialFieldEventId = null;
let lastSpecialFieldEventTime = 0; // Track when last special field event occurred
let originalDiceMovement = null; // Store original dice movement for display
let originalDiceRolls = null; // Store original dice roll values for catapult events

// Chart-Variablen
let progressChart = null;
let lastProgressData = [];

// Config object - initialized from template
let dashboardConfig = {
    urls: {
        submitQuestionAnswer: '',
        dashboardStatusApi: ''
    },
    csrfToken: '',
    maxBoardFields: 72,
    currentTeamTurnName: '',
    currentUserId: null,
    activeSession: null,
    allTeams: []
};

/**
 * Initialize dashboard configuration
 */
function initializeDashboard(config) {
    dashboardConfig = { ...dashboardConfig, ...config };
    
    // Set initial values
    isCurrentlyMyTurn = dashboardConfig.currentTeamTurnName === dashboardConfig.currentUser?.name;
    myTeamId = dashboardConfig.currentUserId;
    lastMinigameName = dashboardConfig.activeSession?.current_minigame_name || "";
    lastPhase = dashboardConfig.activeSession?.current_phase || "UNKNOWN";
    serverLastDiceResult = dashboardConfig.lastDiceResult || null;
    currentQuestionAnswered = dashboardConfig.questionAnswered || false;
    lastProgressData = dashboardConfig.gameProgress || [];
}

function updateDashboard(data) {
    if (!data || !data.success) return;
    
    const gameData = data.data;
    const currentUser = gameData.current_user;
    
    // Fragen-Interface Management
    updateQuestionInterface(gameData);
    
    // Check for new question announcement
    if (gameData.question_data && gameData.question_data.name && 
        (!lastQuestionData || lastQuestionData.id !== gameData.question_data.id)) {
        if (lastQuestionData) {
            showQuestionAnnouncement(gameData.question_data.name, gameData.question_data.description);
        }
        lastQuestionData = gameData.question_data;
    } else if (!gameData.question_data && lastQuestionData) {
        lastQuestionData = null;
    }
    
    // Check for new minigame announcement (auch bei der ersten Runde)
    if (gameData.current_minigame_name && 
        gameData.current_minigame_name !== lastMinigameName && !gameData.question_data) {
        // Zeige Banner auch bei der ersten Runde (lastMinigameName === "")
        showMinigameAnnouncement(gameData.current_minigame_name, gameData.current_minigame_description);
    }
    lastMinigameName = gameData.current_minigame_name || "";
    
    // Check for selected players announcement
    updateSelectedPlayersDisplay(gameData);
    
    // Check for minigame/question results
    if (gameData.current_phase === 'DICE_ROLLING' && lastPhase !== 'DICE_ROLLING' && !hasShowMinigameResults) {
        showMinigameResults(gameData.teams);
        hasShowMinigameResults = true;
    } else if (gameData.current_phase !== 'DICE_ROLLING') {
        hasShowMinigameResults = false;
    }
    lastPhase = gameData.current_phase;
    
    // Check for dice animation with longer result display
    if (gameData.current_phase === 'DICE_ROLLING' && 
        currentUser.is_current_turn && 
        !isCurrentlyMyTurn &&
        !isDiceAnimationShowing) {
        
        showDiceWaitingAnimation();
        isCurrentlyMyTurn = true;
    } else if (!currentUser.is_current_turn && isCurrentlyMyTurn) {
        // Team's turn is over, but show result longer
        if (isDiceAnimationShowing) {
            // Position should have changed, show result
            const positionChanged = lastGameData && 
                lastGameData.current_user.position !== currentUser.position;
            
            if (positionChanged || currentUser.is_blocked) {
                // Check if we have original dice rolls from catapult/special field events
                if (originalDiceRolls && 
                    originalDiceRolls.standard_roll !== undefined && 
                    originalDiceRolls.total_roll !== undefined) {
                    // Use stored dice roll values from catapult events
                    const diceData = originalDiceRolls;
                    // For catapult events, use the original dice movement positions, not final position
                    const oldPos = originalDiceMovement ? originalDiceMovement.oldPos : lastGameData.current_user.position;
                    const newPos = originalDiceMovement ? originalDiceMovement.newPos : (lastGameData.current_user.position + diceData.total_roll);
                    
                    console.log('Using original dice rolls for catapult event:', diceData, 'positions:', oldPos, '->', newPos);
                    console.log('Position data - lastPos:', lastGameData.current_user.position, 'currentPos:', currentUser.position);
                    
                    showDiceResultAnimation(diceData.standard_roll, diceData.bonus_roll, diceData.total_roll, 
                                          oldPos, newPos,
                                          currentUser.is_blocked, currentUser.blocked_target_number);
                    // Clear after use to prevent showing old data
                    originalDiceRolls = null;
                    originalDiceMovement = null;
                } else if (gameData.last_dice_result) {
                    // Use server data when available - this should have the correct dice values
                    const diceData = gameData.last_dice_result;
                    console.log('Using server dice data:', diceData);
                    
                    // If we have originalDiceMovement, use those positions for more accurate display
                    const oldPos = originalDiceMovement ? originalDiceMovement.oldPos : lastGameData.current_user.position;
                    const newPos = originalDiceMovement ? originalDiceMovement.newPos : (oldPos + diceData.total_roll);
                    
                    showDiceResultAnimation(diceData.standard_roll, diceData.bonus_roll, diceData.total_roll, 
                                          oldPos, newPos,
                                          currentUser.is_blocked, currentUser.blocked_target_number);
                    // Clear movement data after use
                    originalDiceMovement = null;
                } else {
                    // Fallback calculation - use originalDiceMovement if available for catapult scenarios
                    let oldPos = lastGameData.current_user.position;
                    let newPos = currentUser.position;
                    let positionChange = newPos - oldPos;
                    
                    if (originalDiceMovement) {
                        // For catapult events, use only the original dice movement, not the full position change
                        oldPos = originalDiceMovement.oldPos;
                        newPos = originalDiceMovement.newPos;
                        positionChange = newPos - oldPos;
                        console.log('Fallback: Using original dice movement for calculation:', oldPos, '->', newPos, 'change:', positionChange);
                        originalDiceMovement = null;
                    } else {
                        console.log('Fallback: Using full position change for calculation:', oldPos, '->', newPos, 'change:', positionChange);
                    }
                    
                    if (positionChange > 0 || currentUser.is_blocked) {
                        const standardRoll = Math.min(6, Math.max(positionChange, 1));
                        const bonusRoll = Math.max(0, positionChange - 6);
                        showDiceResultAnimation(standardRoll, bonusRoll, positionChange, 
                                              oldPos, newPos,
                                              currentUser.is_blocked, currentUser.blocked_target_number);
                    }
                }
            } else {
                // No position change yet, keep waiting animation
            }
        }
        isCurrentlyMyTurn = false;
    }
    
    // Check for special field events (with duplicate prevention and delayed display)
    if (gameData.special_field_event) {
        const event = gameData.special_field_event;
        
        // Only show banner if this is a new event
        if (event.event_id && event.event_id !== lastSpecialFieldEventId) {
            lastSpecialFieldEventId = event.event_id;
            lastSpecialFieldEventTime = Date.now(); // Track when this event occurred
            
            // Store original dice movement for dice result display
            if (event.dice_old_position !== undefined && event.dice_new_position !== undefined) {
                originalDiceMovement = {
                    oldPos: event.dice_old_position,
                    newPos: event.dice_new_position
                };
            }
            
            // Store original dice roll values for catapult events
            console.log('Special field event received:', event);
            
            if ((event.dice_roll !== undefined && event.dice_roll !== null) || 
                (event.total_roll !== undefined && event.total_roll !== null)) {
                originalDiceRolls = {
                    standard_roll: event.dice_roll || 0,
                    bonus_roll: event.bonus_roll || 0,
                    total_roll: event.total_roll || event.dice_roll || 0
                };
                
                // Debug log for catapult events
                console.log('Catapult event detected - stored dice rolls:', originalDiceRolls);
                console.log('Event dice data:', {
                    dice_roll: event.dice_roll,
                    bonus_roll: event.bonus_roll,
                    total_roll: event.total_roll
                });
            } else {
                console.log('No dice roll data found in special field event');
            }
            
            // Delay special field banners to show after dice result and movement
            const showDelayedBanner = () => {
                if (event.type === 'barrier_set') {
                    showBarrierFieldBanner(event.target_config);
                } else if (event.type === 'barrier_released') {
                    showBarrierReleaseBanner(event.dice_roll, event.barrier_config);
                } else if (event.type === 'barrier_failed') {
                    showBarrierFailedBanner(event.dice_roll, event.barrier_config);
                } else if (event.type === 'catapult_forward') {
                    showCatapultForwardBanner(event.catapult_distance, event.dice_old_position, event.dice_new_position, event.new_position);
                } else if (event.type === 'catapult_backward') {
                    showCatapultBackwardBanner(event.catapult_distance, event.dice_old_position, event.dice_new_position, event.new_position);
                } else if (event.type === 'player_swap') {
                    // Bestimme Position und Team-Namen basierend auf der Rolle
                    let oldPosition, newPosition, otherTeamName;
                    
                    if (event.is_initiating_team) {
                        // Dieses Team hat gewürfelt
                        oldPosition = event.current_team_old_position;
                        newPosition = event.current_team_new_position;
                        otherTeamName = event.swap_team_name;
                    } else {
                        // Dieses Team wurde getauscht
                        oldPosition = event.swap_team_old_position; 
                        newPosition = event.swap_team_new_position;
                        otherTeamName = event.current_team_name;
                    }
                    
                    showPlayerSwapBanner(otherTeamName, oldPosition, newPosition, event.is_initiating_team, otherTeamName);
                }
            };
            
            // Determine appropriate delay based on current state
            let delay = 0;
            
            // If dice animation is currently showing, wait for it to complete
            if (isDiceAnimationShowing) {
                delay = 9000; // Wait for full dice animation (8s) + 1000ms buffer for safety
            } 
            // If this is the current team's turn ending, wait for dice result
            else if (!currentUser.is_current_turn && isCurrentlyMyTurn) {
                delay = 4000; // Extended wait for dice result to be fully processed and shown
            }
            // For player swap events, ensure dice result is shown first for initiating team
            else if (event.type === 'player_swap') {
                if (event.is_initiating_team) {
                    // Check if dice animation was recently shown
                    const recentlyRolled = isCurrentlyMyTurn || (Date.now() - lastSpecialFieldEventTime < 10000);
                    delay = recentlyRolled ? 5000 : 2000; // Longer delay if recently rolled dice
                } else {
                    delay = 1500; // Shorter delay for team that was swapped
                }
            }
            // For catapult events, ensure movement animation completes
            else if (event.type === 'catapult_forward' || event.type === 'catapult_backward') {
                const recentlyRolled = isCurrentlyMyTurn || (Date.now() - lastSpecialFieldEventTime < 10000);
                delay = recentlyRolled ? 4000 : 1500; // Longer delay if recently rolled dice
            }
            // For barrier events, show more quickly
            else if (event.type.includes('barrier')) {
                delay = 500; // Minimal delay for barriers
            }
            
            setTimeout(showDelayedBanner, delay);
        }
    }
    
    // Update game status
    updateGameStatus(gameData);
    
    // Update statistics
    updateStatistics(currentUser, gameData.stats);
    
    // Update team rankings
    updateTeamRankings(gameData.teams, gameData.stats.max_board_fields);
    
    // Update dice order
    updateDiceOrder(gameData.dice_roll_order);
    
    // Update progress chart
    if (gameData.game_progress) {
        updateProgressChart(gameData.game_progress);
        updateProgressStats(gameData.game_progress, currentUser, gameData.stats.max_board_fields);
    }
    
    // Update server dice result wenn verfügbar
    if (gameData.last_dice_result) {
        serverLastDiceResult = gameData.last_dice_result;
        updateLastDiceResultDisplay();
    }
    
    lastGameData = gameData;
}

// Chart-Funktionen
function initializeProgressChart() {
    const ctx = document.getElementById('progressChart');
    if (!ctx) return;
    
    const chartData = lastProgressData || [];
    
    if (chartData.length === 0) {
        return; // Kein Chart wenn keine Daten
    }
    
    const maxPosition = Math.max(dashboardConfig.maxBoardFields - 1, ...chartData.map(d => d.position));
    
    progressChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.map(d => `Zug ${d.move}`),
            datasets: [{
                label: 'Position',
                data: chartData.map(d => d.position),
                borderColor: '#17a2b8',
                backgroundColor: 'rgba(23, 162, 184, 0.1)',
                borderWidth: 3,
                pointBackgroundColor: '#17a2b8',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 8,
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: '#17a2b8',
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            const dataPoint = lastProgressData[context.dataIndex];
                            if (!dataPoint) return `Position: ${context.parsed.y}`;
                            
                            let label = `Position: ${context.parsed.y}`;
                            
                            // Verschiedene Event-Typen
                            if (dataPoint.event_type && dataPoint.event_type.includes('catapult')) {
                                const direction = dataPoint.catapult_direction || 'unbekannt';
                                const distance = dataPoint.catapult_distance || 0;
                                label += ` (Katapult ${direction}: ${distance} Felder)`;
                            } else if (dataPoint.event_type === 'special_field_player_swap') {
                                const teamName = dataPoint.swap_team_name || 'Unbekannt';
                                const role = dataPoint.is_initiating_team ? 'Initiiert' : 'Getauscht';
                                label += ` (${role} Tausch mit ${teamName})`;
                            } else if (dataPoint.dice_roll && dataPoint.dice_roll > 0) {
                                label += ` (Würfel: ${dataPoint.dice_roll})`;
                            } else if (dataPoint.description && dataPoint.description !== 'Bewegung') {
                                label += ` (${dataPoint.description})`;
                            }
                            
                            return label;
                        },
                        afterLabel: function(context) {
                            const dataPoint = lastProgressData[context.dataIndex];
                            if (!dataPoint) return '';
                            
                            let additionalInfo = `Zeit: ${dataPoint.timestamp}`;
                            
                            // Zusätzliche Informationen je Event-Typ
                            if (dataPoint.description && dataPoint.description !== `Position: ${context.parsed.y}`) {
                                additionalInfo += `\nAktion: ${dataPoint.description}`;
                            }
                            
                            return additionalInfo;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Spielzug',
                        color: '#666',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Position auf dem Spielbrett',
                        color: '#666',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    },
                    beginAtZero: true,
                    max: maxPosition,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    },
                    ticks: {
                        stepSize: Math.max(1, Math.floor(maxPosition / 10))
                    }
                }
            },
            animations: {
                tension: {
                    duration: 1000,
                    easing: 'linear',
                    from: 0.3,
                    to: 0.3,
                    loop: false
                }
            }
        }
    });
}

function updateProgressChart(newProgressData) {
    if (!progressChart) {
        lastProgressData = newProgressData;
        if (newProgressData && newProgressData.length > 0) {
            initializeProgressChart();
        }
        return;
    }
    
    // Prüfe ob sich die Daten geändert haben
    if (JSON.stringify(newProgressData) === JSON.stringify(lastProgressData)) {
        return; // Keine Änderung
    }
    
    lastProgressData = newProgressData;
    
    if (!newProgressData || newProgressData.length === 0) {
        return;
    }
    
    // Aktualisiere Chart-Daten
    const maxPosition = Math.max(dashboardConfig.maxBoardFields - 1, ...newProgressData.map(d => d.position));
    
    progressChart.data.labels = newProgressData.map(d => `Zug ${d.move}`);
    progressChart.data.datasets[0].data = newProgressData.map(d => d.position);
    progressChart.options.scales.y.max = maxPosition;
    progressChart.options.scales.y.ticks.stepSize = Math.max(1, Math.floor(maxPosition / 10));
    
    progressChart.update('active');
}

function updateProgressStats(progressData, currentUser, maxFields) {
    // Total moves
    const totalMovesEl = document.getElementById('total-moves');
    if (totalMovesEl) {
        totalMovesEl.textContent = progressData.length > 1 ? progressData.length - 1 : 0;
    }
    
    // Current position
    const currentPositionEl = document.getElementById('current-position-stat');
    if (currentPositionEl) {
        currentPositionEl.textContent = currentUser.position;
    }
    
    // Average move
    const averageMoveEl = document.getElementById('average-move');
    if (averageMoveEl) {
        const totalMoves = progressData.length > 1 ? progressData.length - 1 : 0;
        const average = totalMoves > 0 ? (currentUser.position / totalMoves).toFixed(1) : 0;
        averageMoveEl.textContent = average;
    }
    
    // Progress percentage
    const progressPercentageEl = document.getElementById('progress-percentage');
    if (progressPercentageEl) {
        const percentage = ((currentUser.position / (maxFields - 1)) * 100).toFixed(1);
        progressPercentageEl.textContent = percentage + '%';
    }
}

// Aktive Felder laden und anzeigen
function loadActiveFields() {
    fetch('/teams/api/active-fields')
        .then(response => response.json())
        .then(data => {
            const activeFieldsList = document.getElementById('active-fields-list');
            if (!activeFieldsList) return;
            
            if (data.success && data.fields) {
                if (data.fields.length === 0) {
                    activeFieldsList.innerHTML = `
                        <div class="text-center py-4">
                            <i class="fas fa-info-circle text-muted" style="font-size: 2rem; opacity: 0.5;"></i>
                            <h6 class="text-muted mt-2">Keine aktiven Spezialfelder</h6>
                            <p class="text-muted mb-0 small">Zurzeit sind keine Spezialfelder aktiviert.</p>
                        </div>
                    `;
                    return;
                }
                
                let fieldsHtml = '<div class="row">';
                data.fields.forEach(field => {
                    const borderColor = field.color || '#ffc107';
                    fieldsHtml += `
                        <div class="col-xl-3 col-lg-4 col-md-6 col-sm-12 mb-3">
                            <div class="active-field-item" style="border-left-color: ${borderColor};">
                                <div class="d-flex align-items-start">
                                    <div class="active-field-icon" style="color: ${borderColor};">
                                        ${field.icon}
                                    </div>
                                    <div class="active-field-info flex-grow-1">
                                        <h6>${field.name}</h6>
                                        <p>${field.description}</p>
                                        <div class="active-field-frequency">${field.frequency}</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                });
                fieldsHtml += '</div>';
                
                activeFieldsList.innerHTML = fieldsHtml;
            } else {
                activeFieldsList.innerHTML = `
                    <div class="text-center py-4">
                        <i class="fas fa-exclamation-triangle text-warning" style="font-size: 2rem;"></i>
                        <h6 class="text-warning mt-2">Fehler beim Laden</h6>
                        <p class="text-muted mb-0 small">${data.error || 'Unbekannter Fehler'}</p>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Error loading active fields:', error);
            const activeFieldsList = document.getElementById('active-fields-list');
            if (activeFieldsList) {
                activeFieldsList.innerHTML = `
                    <div class="text-center py-4">
                        <i class="fas fa-wifi text-danger" style="font-size: 2rem;"></i>
                        <h6 class="text-danger mt-2">Verbindungsfehler</h6>
                        <p class="text-muted mb-0 small">Felder konnten nicht geladen werden.</p>
                    </div>
                `;
            }
        });
}

function updateQuestionInterface(gameData) {
    const questionSection = document.getElementById('question-interface-section');
    
    if (gameData.question_data && gameData.current_phase === 'QUESTION_ACTIVE') {
        // Show question interface
        if (questionSection) {
            const wasHidden = questionSection.style.display === 'none';
            questionSection.style.display = 'block';
            
            if (wasHidden) {
                questionSection.classList.add('question-updated');
                setTimeout(() => questionSection.classList.remove('question-updated'), 1000);
            }
            
            // Only update content if user is not currently interacting or if interface wasn't initialized
            if (!userInteractingWithQuestion || !questionInterfaceInitialized) {
                updateQuestionContent(gameData.question_data, gameData.question_data.answered);
                questionInterfaceInitialized = true;
            }
        }
    } else {
        // Hide question interface
        if (questionSection) {
            questionSection.style.display = 'none';
            questionInterfaceInitialized = false;
            userInteractingWithQuestion = false;
        }
    }
}

function updateQuestionContent(questionData, isAnswered) {
    const questionTitle = document.getElementById('question-title');
    const questionContent = document.getElementById('question-content');
    
    if (questionTitle) {
        questionTitle.textContent = questionData.name;
    }
    
    if (questionContent) {
        if (isAnswered) {
            // Show "already answered" state
            questionContent.innerHTML = `
                <div class="question-completed">
                    <div class="question-completed-icon">
                        <i class="fas fa-check-circle text-success"></i>
                    </div>
                    <h4 class="text-success mb-3">Frage beantwortet!</h4>
                    <p class="text-muted mb-0">
                        Du hast die Frage bereits beantwortet. 
                        Warte, bis alle anderen Teams fertig sind.
                    </p>
                </div>
            `;
        } else {
            // Preserve current form state if user is interacting
            let currentFormData = {};
            if (userInteractingWithQuestion) {
                const existingForm = document.getElementById('question-answer-form');
                if (existingForm) {
                    // Save current form state
                    const formData = new FormData(existingForm);
                    for (let [key, value] of formData.entries()) {
                        currentFormData[key] = value;
                    }
                    
                    // If user has already started answering, don't rebuild the form
                    if (Object.keys(currentFormData).length > 0) {
                        return; // Exit early to preserve user input
                    }
                }
            }
            
            // Show question form
            let optionsHtml = '';
            
            if (questionData.question_type === 'multiple_choice') {
                questionData.options.forEach((option, index) => {
                    const isChecked = currentFormData.selected_option == index ? 'checked' : '';
                    optionsHtml += `
                        <div class="custom-control custom-radio mb-3">
                            <input type="radio" class="custom-control-input" 
                                   id="option_${index}" name="selected_option" value="${index}" ${isChecked}>
                            <label class="custom-control-label answer-option-label" for="option_${index}">
                                <span class="option-letter">${"ABCD"[index]}.</span>
                                <span class="option-text">${option}</span>
                            </label>
                        </div>
                    `;
                });
            }
            
            questionContent.innerHTML = `
                <div class="question-form">
                    ${questionData.description ? `<p class="text-muted mb-3">${questionData.description}</p>` : ''}
                    
                    <div class="question-text mb-4">
                        ${questionData.question_text}
                    </div>
                    
                    <form id="question-answer-form">
                        ${questionData.question_type === 'multiple_choice' ? `
                            <div class="answer-options">
                                <label class="form-control-label mb-3">
                                    <strong>Wähle die richtige Antwort:</strong>
                                </label>
                                ${optionsHtml}
                            </div>
                        ` : `
                            <div class="form-group">
                                <label class="form-control-label mb-3">
                                    <strong>Gib deine Antwort ein:</strong>
                                </label>
                                <textarea name="answer_text" class="form-control form-control-lg" 
                                         rows="3" placeholder="Deine Antwort hier eingeben...">${currentFormData.answer_text || ''}</textarea>
                                <small class="form-text text-muted mt-2">
                                    <i class="fas fa-lightbulb mr-1"></i>
                                    Tipp: Achte auf Rechtschreibung - die Antwort muss exakt stimmen!
                                </small>
                            </div>
                        `}
                        
                        <div class="text-center mt-4">
                            <button type="submit" class="btn btn-success btn-lg question-submit-btn">
                                <i class="fas fa-paper-plane mr-2"></i>
                                Antwort abschicken
                            </button>
                        </div>
                    </form>
                </div>
            `;
            
            // Attach form handler and interaction listeners
            const form = document.getElementById('question-answer-form');
            if (form) {
                form.addEventListener('submit', handleQuestionSubmit);
                
                // Add interaction listeners
                const inputs = form.querySelectorAll('input, textarea');
                inputs.forEach(input => {
                    input.addEventListener('focus', () => {
                        userInteractingWithQuestion = true;
                    });
                    
                    input.addEventListener('blur', () => {
                        // Only set to false if no other inputs are focused
                        setTimeout(() => {
                            const focusedElement = document.activeElement;
                            const isFormElement = form.contains(focusedElement);
                            if (!isFormElement) {
                                userInteractingWithQuestion = false;
                            }
                        }, 100);
                    });
                    
                    input.addEventListener('input', () => {
                        userInteractingWithQuestion = true;
                    });
                    
                    input.addEventListener('change', () => {
                        userInteractingWithQuestion = true;
                    });
                });
            }
        }
    }
}

function handleQuestionSubmit(e) {
    e.preventDefault();
    
    const form = e.target;
    const submitBtn = form.querySelector('.question-submit-btn');
    const questionData = lastQuestionData;
    
    if (!questionData) return;
    
    let answerData = {
        question_id: questionData.id,
        answer_type: questionData.question_type
    };
    
    // Validation and data collection
    let isValid = false;
    
    if (questionData.question_type === 'multiple_choice') {
        const selectedOption = form.querySelector('input[name="selected_option"]:checked');
        if (selectedOption) {
            answerData.selected_option = parseInt(selectedOption.value);
            isValid = true;
        } else {
            alert('Bitte wähle eine Antwort aus!');
            return;
        }
    } else if (questionData.question_type === 'text_input') {
        const answerText = form.querySelector('textarea[name="answer_text"]').value.trim();
        if (answerText) {
            answerData.answer_text = answerText;
            isValid = true;
        } else {
            alert('Bitte gib eine Antwort ein!');
            return;
        }
    }
    
    if (!isValid) return;
    
    // Disable form and reset interaction flag
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Wird gesendet...';
    userInteractingWithQuestion = false;
    
    // Send answer
    fetch(dashboardConfig.urls.submitQuestionAnswer, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': dashboardConfig.csrfToken
        },
        body: JSON.stringify(answerData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            currentQuestionAnswered = true;
            showQuestionResult(data);
            // Update interface to show "answered" state
            setTimeout(() => {
                updateQuestionContent(questionData, true);
            }, 3000);
        } else {
            alert('Fehler: ' + (data.error || 'Unbekannter Fehler'));
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-paper-plane mr-2"></i>Antwort abschicken';
            userInteractingWithQuestion = false;
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Netzwerkfehler beim Senden der Antwort.');
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-paper-plane mr-2"></i>Antwort abschicken';
        userInteractingWithQuestion = false;
    });
}

function showQuestionResult(data) {
    // Show a quick feedback message
    const questionContent = document.getElementById('question-content');
    const questionSection = document.getElementById('question-interface-section');
    
    if (questionContent) {
        const isCorrect = data.is_correct;
        const resultHtml = `
            <div class="question-result text-center p-4">
                <div class="result-icon mb-3">
                    <i class="fas ${isCorrect ? 'fa-check-circle text-success' : 'fa-times-circle text-danger'}" 
                       style="font-size: 4rem;"></i>
                </div>
                <h4 class="${isCorrect ? 'text-success' : 'text-danger'} mb-3">
                    ${isCorrect ? 'Richtig!' : 'Leider falsch'}
                </h4>
                <p class="text-muted">
                    ${data.feedback && data.feedback.message ? data.feedback.message : ''}
                    ${data.feedback && data.feedback.correct_answer && !isCorrect ? 
                        '<br><strong>Die richtige Antwort war:</strong> ' + data.feedback.correct_answer : ''}
                </p>
                <p class="text-info mt-3">
                    ${data.all_teams_answered ? 
                        'Alle Teams haben geantwortet. Der Admin wird die Ergebnisse auswerten.' : 
                        'Warte, bis alle anderen Teams geantwortet haben.'}
                </p>
            </div>
        `;
        
        questionContent.innerHTML = resultHtml;
        
        // Hide the question result after 10 seconds
        setTimeout(() => {
            if (questionSection) {
                questionSection.style.display = 'none';
                questionInterfaceInitialized = false;
                userInteractingWithQuestion = false;
            }
        }, 10000);
    }
}

// Banner functions
function showQuestionAnnouncement(name, description) {
    const banner = document.getElementById('question-announcement-banner');
    const nameEl = document.getElementById('question-banner-name');
    const descEl = document.getElementById('question-banner-description');
    
    if (banner && nameEl && descEl) {
        nameEl.textContent = name;
        descEl.textContent = description || '';
        
        banner.classList.add('show');
        
        setTimeout(() => {
            banner.classList.add('hide');
            setTimeout(() => {
                banner.classList.remove('show', 'hide');
            }, 500);
        }, 4000);
    }
}

function showMinigameAnnouncement(name, description) {
    const banner = document.getElementById('minigame-announcement-banner');
    const nameEl = document.getElementById('minigame-banner-name');
    const descEl = document.getElementById('minigame-banner-description');
    
    if (banner && nameEl && descEl) {
        nameEl.textContent = name;
        descEl.textContent = description || '';
        
        banner.classList.add('show');
        
        setTimeout(() => {
            banner.classList.add('hide');
            setTimeout(() => {
                banner.classList.remove('show', 'hide');
            }, 500);
        }, 4000);
    }
}

function showBarrierFieldBanner(targetConfig) {
    const banner = document.getElementById('barrier-field-banner');
    const messageEl = document.getElementById('barrier-banner-message');
    const requirementEl = document.getElementById('barrier-banner-requirement');
    
    if (banner && messageEl && requirementEl) {
        messageEl.textContent = 'Du bist auf ein Sperren-Feld geraten!';
        
        // Use display_text from target_config or fallback
        if (targetConfig && targetConfig.display_text) {
            requirementEl.textContent = targetConfig.display_text;
        } else if (typeof targetConfig === 'number') {
            // Backward compatibility
            requirementEl.textContent = `Würfle mindestens eine ${targetConfig} um dich zu befreien!`;
        } else {
            requirementEl.textContent = 'Würfle die richtige Zahl um dich zu befreien!';
        }
        
        banner.classList.add('show');
        
        setTimeout(() => {
            banner.classList.add('hide');
            setTimeout(() => {
                banner.classList.remove('show', 'hide');
            }, 500);
        }, 5000);
    }
}

function showBarrierReleaseBanner(diceRoll, barrierConfig) {
    const banner = document.getElementById('barrier-release-banner');
    const messageEl = document.getElementById('release-banner-message');
    
    if (banner && messageEl) {
        // Build dice description if we have detailed data
        let diceDescription = diceRoll;
        if (typeof diceRoll === 'object') {
            diceDescription = `${diceRoll.dice_roll}`;
            if (diceRoll.bonus_roll > 0) {
                diceDescription += ` + ${diceRoll.bonus_roll} (Bonus) = ${diceRoll.total_roll}`;
            }
        }
        
        if (barrierConfig && barrierConfig.display_text) {
            messageEl.textContent = `Du hast ${diceDescription} gewürfelt und bist befreit!`;
        } else {
            // Backward compatibility
            const targetNumber = barrierConfig && barrierConfig.min_number ? barrierConfig.min_number : 4;
            messageEl.textContent = `Du hast ${diceDescription} gewürfelt (benötigt: ${targetNumber}+)`;
        }
        
        banner.classList.add('show');
        
        setTimeout(() => {
            banner.classList.add('hide');
            setTimeout(() => {
                banner.classList.remove('show', 'hide');
            }, 500);
        }, 4000);
    }
}

function showBarrierFailedBanner(diceRoll, barrierConfig) {
    const banner = document.getElementById('barrier-failed-banner');
    const messageEl = document.getElementById('failed-banner-message');
    
    if (banner && messageEl) {
        // Build dice description if we have detailed data
        let diceDescription = diceRoll;
        if (typeof diceRoll === 'object') {
            diceDescription = `${diceRoll.dice_roll}`;
            if (diceRoll.bonus_roll > 0) {
                diceDescription += ` + ${diceRoll.bonus_roll} (Bonus) = ${diceRoll.total_roll}`;
            }
        }
        
        if (barrierConfig && barrierConfig.display_text) {
            messageEl.textContent = `Du hast ${diceDescription} gewürfelt. ${barrierConfig.display_text}`;
        } else {
            // Backward compatibility
            const targetNumber = barrierConfig && barrierConfig.min_number ? barrierConfig.min_number : 6;
            messageEl.textContent = `Du hast nur ${diceDescription} gewürfelt (benötigt: ${targetNumber}+)`;
        }
        
        banner.classList.add('show');
        
        setTimeout(() => {
            banner.classList.add('hide');
            setTimeout(() => {
                banner.classList.remove('show', 'hide');
            }, 500);
        }, 5000);
    }
}

function showMinigameResults(teams) {
    const banner = document.getElementById('minigame-results-banner');
    const resultsList = document.getElementById('minigame-results-list');
    
    if (banner && resultsList) {
        const teamsWithPlacements = teams
            .filter(team => team.minigame_placement)
            .sort((a, b) => a.minigame_placement - b.minigame_placement);
        
        resultsList.innerHTML = '';
        teamsWithPlacements.forEach(team => {
            const resultItem = document.createElement('div');
            resultItem.className = 'result-item';
            
            let medalIcon = '';
            if (team.minigame_placement === 1) medalIcon = '🥇';
            else if (team.minigame_placement === 2) medalIcon = '🥈';
            else if (team.minigame_placement === 3) medalIcon = '🥉';
            else medalIcon = `${team.minigame_placement}.`;
            
            resultItem.innerHTML = `${medalIcon} ${team.name}`;
            if (team.is_current_user) {
                resultItem.style.backgroundColor = 'rgba(255, 255, 255, 0.2)';
                resultItem.style.fontWeight = 'bold';
            }
            resultsList.appendChild(resultItem);
        });
        
        banner.classList.add('show');
        
        setTimeout(() => {
            banner.classList.add('hide');
            setTimeout(() => {
                banner.classList.remove('show', 'hide');
            }, 500);
        }, 5000);
    }
}

function showCatapultForwardBanner(catapultDistance, diceOldPosition, diceNewPosition, finalPosition) {
    const banner = document.getElementById('catapult-forward-banner');
    const messageEl = document.getElementById('catapult-forward-message');
    
    if (banner && messageEl) {
        messageEl.textContent = `Du fliegst ${catapultDistance} Felder nach vorne!`;
        
        // Add position info to description if available
        const descEl = banner.querySelector('.banner-description');
        if (descEl && finalPosition !== undefined) {
            if (diceOldPosition !== undefined && diceNewPosition !== undefined) {
                descEl.textContent = `Würfel: Feld ${diceOldPosition} → ${diceNewPosition}, jetzt auf Feld ${finalPosition}`;
            } else {
                descEl.textContent = `Jetzt auf Feld ${finalPosition}`;
            }
        }
        
        banner.classList.add('show');
        
        setTimeout(() => {
            banner.classList.add('hide');
            setTimeout(() => {
                banner.classList.remove('show', 'hide');
            }, 500);
        }, 5000);
    }
}

function showCatapultBackwardBanner(catapultDistance, diceOldPosition, diceNewPosition, finalPosition) {
    const banner = document.getElementById('catapult-backward-banner');
    const messageEl = document.getElementById('catapult-backward-message');
    
    if (banner && messageEl) {
        messageEl.textContent = `Du wirst ${catapultDistance} Felder zurück geschleudert!`;
        
        // Add position info to description if available
        const descEl = banner.querySelector('.banner-description');
        if (descEl && finalPosition !== undefined) {
            if (diceOldPosition !== undefined && diceNewPosition !== undefined) {
                descEl.textContent = `Würfel: Feld ${diceOldPosition} → ${diceNewPosition}, jetzt auf Feld ${finalPosition}`;
            } else {
                descEl.textContent = `Jetzt auf Feld ${finalPosition}`;
            }
        }
        
        banner.classList.add('show');
        
        setTimeout(() => {
            banner.classList.add('hide');
            setTimeout(() => {
                banner.classList.remove('show', 'hide');
            }, 500);
        }, 5000);
    }
}

function showPlayerSwapBanner(swapTeamName, oldPosition, newPosition, isInitiatingTeam, otherTeamName) {
    const banner = document.getElementById('player-swap-banner');
    const messageEl = document.getElementById('player-swap-message');
    
    if (banner && messageEl) {
        // Unterschiedliche Nachrichten je nach Team-Rolle
        if (isInitiatingTeam) {
            messageEl.textContent = `Du tauschst deine Position mit ${swapTeamName}!`;
        } else {
            messageEl.textContent = `${otherTeamName} hat mit dir getauscht!`;
        }
        
        // Add position info to description if available
        const descEl = banner.querySelector('.banner-description');
        if (descEl && oldPosition !== undefined && newPosition !== undefined) {
            descEl.textContent = `Jetzt auf Feld ${newPosition} (war auf Feld ${oldPosition})`;
        }
        
        banner.classList.add('show');
        
        setTimeout(() => {
            banner.classList.add('hide');
            setTimeout(() => {
                banner.classList.remove('show', 'hide');
            }, 500);
        }, 5000);
    }
}

// Dice animation functions
function showDiceWaitingAnimation() {
    const overlay = document.getElementById('dice-animation-overlay');
    const waitingDiv = document.getElementById('dice-waiting');
    const resultDiv = document.getElementById('dice-result-animation');
    
    if (overlay && waitingDiv && resultDiv) {
        waitingDiv.style.display = 'block';
        resultDiv.style.display = 'none';
        overlay.style.display = 'flex';
        isDiceAnimationShowing = true;
    }
}

function showDiceResultAnimation(standardRoll, bonusRoll, totalRoll, oldPos, newPos, isBlocked = false, targetNumber = null) {
    const waitingDiv = document.getElementById('dice-waiting');
    const resultDiv = document.getElementById('dice-result-animation');
    
    if (waitingDiv && resultDiv) {
        // Hide waiting animation and show result
        waitingDiv.style.display = 'none';
        resultDiv.style.display = 'block';
        
        // Update result values
        document.getElementById('standard-roll').textContent = standardRoll;
        document.getElementById('total-roll').textContent = totalRoll;
        document.getElementById('old-pos').textContent = oldPos;
        document.getElementById('new-pos').textContent = newPos;
        
        // Store dice result
        lastDiceResult = {
            standard: standardRoll,
            bonus: bonusRoll,
            total: totalRoll
        };
        updateLastDiceResultDisplay();
        
        if (bonusRoll > 0) {
            document.getElementById('bonus-roll').textContent = bonusRoll;
            document.getElementById('bonus-row').style.display = 'flex';
        } else {
            document.getElementById('bonus-row').style.display = 'none';
        }
        
        // Update movement text based on barrier status
        const movementText = document.getElementById('movement-text');
        if (isBlocked && oldPos === newPos) {
            let blockedText = 'Du bist weiterhin blockiert!';
            if (typeof targetNumber === 'object' && targetNumber.display_text) {
                blockedText += ` ${targetNumber.display_text}`;
            } else if (targetNumber) {
                blockedText += ` (Benötigt: ${targetNumber}+)`;
            }
            movementText.innerHTML = `<span class="text-warning">${blockedText}</span>`;
        } else if (!isBlocked && oldPos === newPos) {
            movementText.innerHTML = `<span class="text-success">Du hast die Sperre durchbrochen!</span>`;
        } else {
            // Use the provided positions directly (they should already be correct for catapult events)
            movementText.innerHTML = `Du bewegst dich von Position <span id="old-pos">${oldPos}</span> auf Position <span id="new-pos">${newPos}</span>!`;
        }
        
        // Hide the banner after longer time (8 seconds instead of 3)
        if (diceResultTimer) {
            clearTimeout(diceResultTimer);
        }
        
        diceResultTimer = setTimeout(() => {
            hideDiceAnimation();
        }, 8000); // Longer display time
    }
}

function hideDiceAnimation() {
    const overlay = document.getElementById('dice-animation-overlay');
    
    if (overlay) {
        overlay.style.display = 'none';
        isDiceAnimationShowing = false;
    }
    
    if (diceResultTimer) {
        clearTimeout(diceResultTimer);
        diceResultTimer = null;
    }
}

function updateLastDiceResultDisplay() {
    const lastDiceResultEl = document.getElementById('last-dice-result');
    const diceData = lastDiceResult || serverLastDiceResult;
    
    if (lastDiceResultEl && diceData) {
        let resultText = `<strong class="text-primary">${diceData.standard_roll || diceData.standard}</strong>`;
        
        const bonusRoll = diceData.bonus_roll || diceData.bonus || 0;
        if (bonusRoll > 0) {
            resultText += ` + <strong class="text-success">${bonusRoll}</strong>`;
        }
        
        const totalRoll = diceData.total_roll || diceData.total || 0;
        resultText += ` = <strong class="text-info">${totalRoll}</strong>`;
        
        if (diceData.was_blocked) {
            resultText += ' <span class="badge badge-warning ml-1">Blockiert</span>';
        }
        
        if (diceData.timestamp) {
            resultText += ` <small class="text-muted ml-2">(${diceData.timestamp})</small>`;
        }
        
        lastDiceResultEl.innerHTML = resultText;
    }
}

// Game status and statistics functions
function updateGameStatus(gameData) {
    const statusAlert = document.getElementById('game-status-alert');
    const statusText = document.getElementById('game-status-text');
    const minigameInfo = document.getElementById('minigame-info');
    
    if (statusAlert && statusText) {
        statusAlert.className = `alert alert-${gameData.game_status_class} alert-dismissible fade show`;
        statusText.innerHTML = `<strong>${gameData.game_status}</strong>`;
        
        // Add blocked status indicator
        if (gameData.current_user && gameData.current_user.is_blocked) {
            let blockedText = '🔒 Blockiert';
            if (gameData.current_user.blocked_config) {
                try {
                    const config = JSON.parse(gameData.current_user.blocked_config);
                    blockedText += ` - ${config.display_text}`;
                } catch (e) {
                    blockedText += ` - Benötigt ${gameData.current_user.blocked_target_number}+ zum Befreien`;
                }
            } else if (gameData.current_user.blocked_target_number) {
                blockedText += ` - Benötigt ${gameData.current_user.blocked_target_number}+ zum Befreien`;
            }
            statusText.innerHTML += `<br><span class="badge badge-danger">${blockedText}</span>`;
        }
        
        // Hide minigame info in status section since it's now shown in the persistent section above
        if (minigameInfo) {
            minigameInfo.style.display = 'none';
        }
    }
}

function updateStatistics(currentUser, stats) {
    // Position
    const positionNumber = document.getElementById('position-number');
    if (positionNumber && positionNumber.textContent != currentUser.position) {
        positionNumber.textContent = currentUser.position;
        document.getElementById('position-circle').classList.add('position-updated');
        setTimeout(() => {
            document.getElementById('position-circle').classList.remove('position-updated');
        }, 1000);
    }
    
    // Rank
    const currentRank = document.getElementById('current-rank');
    if (currentRank && currentRank.textContent != currentUser.rank) {
        currentRank.textContent = currentUser.rank;
        currentRank.parentElement.parentElement.parentElement.classList.add('stat-updated');
        setTimeout(() => {
            currentRank.parentElement.parentElement.parentElement.classList.remove('stat-updated');
        }, 800);
    }
    
    // Fields to goal
    const fieldsToGoal = document.getElementById('fields-to-goal');
    if (fieldsToGoal) fieldsToGoal.textContent = currentUser.fields_to_goal;
    
    // Teams ahead
    const teamsAhead = document.getElementById('teams-ahead');
    if (teamsAhead) teamsAhead.textContent = currentUser.teams_ahead;
    
    // Teams count
    const teamsCount = document.getElementById('teams-count');
    if (teamsCount) teamsCount.textContent = stats.teams_count;
    
    const totalTeams = document.getElementById('total-teams');
    if (totalTeams) totalTeams.textContent = stats.teams_count;
    
    // Bonus dice
    const bonusDice = document.getElementById('bonus-dice');
    const bonusDiceStatus = document.getElementById('bonus-dice-status');
    if (bonusDice && bonusDiceStatus) {
        let diceText = 'Standard';
        let statusText = 'Standard';
        let statusClass = 'text-muted';
        
        if (currentUser.bonus_dice_sides == 6) {
            diceText = '1-6';
            statusText = '1-6 (Gold)';
            statusClass = 'text-success';
        } else if (currentUser.bonus_dice_sides == 4) {
            diceText = '1-4';
            statusText = '1-4 (Silber)';
            statusClass = 'text-success';
        } else if (currentUser.bonus_dice_sides == 2) {
            diceText = '1-2';
            statusText = '1-2 (Bronze)';
            statusClass = 'text-success';
        }
        
        bonusDice.textContent = diceText;
        bonusDiceStatus.textContent = statusText;
        bonusDiceStatus.className = statusClass;
    }
    
    // Minigame placement
    const lastMinigamePlacement = document.getElementById('last-minigame-placement');
    if (lastMinigamePlacement) {
        if (currentUser.minigame_placement) {
            lastMinigamePlacement.innerHTML = `
                <span class="badge badge-placement-${currentUser.minigame_placement}">
                    ${currentUser.minigame_placement}. Platz
                </span>
            `;
        } else {
            lastMinigamePlacement.innerHTML = '<span class="text-muted">Noch kein Spiel</span>';
        }
    }
}

function updateTeamRankings(teams, maxFields) {
    const tbody = document.getElementById('team-rankings');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    teams.forEach((team, index) => {
        const rank = index + 1;
        const progressPercent = ((team.position / (maxFields - 1)) * 100).toFixed(1);
        
        const row = document.createElement('tr');
        if (team.is_current_user) {
            row.className = 'table-primary';
        }
        row.setAttribute('data-team-id', team.id);
        
        row.innerHTML = `
            <td>
                <span class="rank-badge rank-${rank}">
                    ${rank === 1 ? '<span class="rank-first"><i class="fas fa-crown"></i><span class="rank-number">1</span></span>' : rank}
                </span>
            </td>
            <td>
                <div class="d-flex align-items-center">
                    ${team.character_name ? '<i class="fas fa-user-astronaut mr-2 text-info"></i>' : '<i class="fas fa-user mr-2 text-muted"></i>'}
                    <strong ${team.is_current_user ? 'class="text-primary"' : ''}>
                        ${team.name}
                        ${team.is_current_user ? '<small class="badge badge-primary ml-1">Du</small>' : ''}
                    </strong>
                </div>
                ${team.character_name ? '<small class="text-muted">' + team.character_name + '</small>' : ''}
            </td>
            <td>
                <span class="position-indicator">
                    ${team.position} / ${maxFields - 1}
                </span>
                <div class="progress progress-sm mt-1">
                    <div class="progress-bar" style="width: ${progressPercent}%"></div>
                </div>
            </td>
            <td>
                ${team.minigame_placement ? 
                    `<span class="badge badge-placement-${team.minigame_placement}">${team.minigame_placement}. Platz</span>` : 
                    '<span class="text-muted">-</span>'
                }
            </td>
        `;
        
        tbody.appendChild(row);
    });
}

function updateDiceOrder(diceOrder) {
    const diceOrderSection = document.getElementById('dice-order-section');
    const diceOrderContainer = document.getElementById('dice-order');
    
    if (!diceOrder || diceOrder.length === 0) {
        if (diceOrderSection) diceOrderSection.style.display = 'none';
        return;
    }
    
    if (diceOrderSection) diceOrderSection.style.display = 'block';
    
    if (diceOrderContainer) {
        diceOrderContainer.innerHTML = '';
        
        diceOrder.forEach(order => {
            const badge = document.createElement('span');
            let badgeClass = 'badge mr-1 mb-1 ';
            
            if (order.is_current_turn) {
                badgeClass += 'badge-success';
            } else if (order.is_current_user) {
                badgeClass += 'badge-primary';
            } else {
                badgeClass += 'badge-secondary';
            }
            
            badge.className = badgeClass;
            badge.innerHTML = `
                ${order.position}. ${order.name}
                ${order.is_current_turn ? '<i class="fas fa-arrow-right ml-1"></i>' : ''}
            `;
            
            diceOrderContainer.appendChild(badge);
        });
    }
}

// Data fetching and updates
function refreshDashboard() {
    fetchDashboardData();
}

function fetchDashboardData() {
    fetch(dashboardConfig.urls.dashboardStatusApi + "?t=" + new Date().getTime())
        .then(response => response.json())
        .then(data => {
            updateDashboard(data);
        })
        .catch(error => {
            console.error('Dashboard update failed:', error);
        });
}

// Live updates management
function startLiveUpdates() {
    if (updateInterval) {
        clearInterval(updateInterval);
    }
    
    updateInterval = setInterval(() => {
        if (!document.hidden) {
            fetchDashboardData();
        }
    }, 2000);
}

function stopLiveUpdates() {
    if (updateInterval) {
        clearInterval(updateInterval);
        updateInterval = null;
    }
}

// Page visibility change handler
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        stopLiveUpdates();
    } else {
        startLiveUpdates();
        fetchDashboardData();
    }
});

// Session validation
function validateSession() {
    fetch('/teams/api/dashboard-status')
        .then(response => {
            if (response.status === 401) {
                // Session abgelaufen
                console.log('Session abgelaufen - Weiterleitung zum Login');
                window.location.href = '/teams/login';
            } else if (response.status === 403) {
                // Forbidden - aber nicht ausloggen, nur warnen
                console.warn('Zugriff verweigert, aber Session bleibt bestehen');
            }
            return response.json();
        })
        .catch(error => {
            console.error('Session-Validierung fehlgeschlagen:', error);
            // Netzwerkfehler führen nicht zum Logout
        });
}

// Selected players banner functions
function updateSelectedPlayersDisplay(gameData) {
    if (!gameData) {
        hideSelectedPlayersBanner();
        hideSelectedPlayersInfo();
        return;
    }

    // Zeige Minispiel-Info wenn ein Spiel/Frage aktiv ist
    if (gameData.current_minigame_name) {
        // Update persistent display (immer zeigen wenn Minispiel aktiv)
        updateSelectedPlayersInfo(gameData.selected_players);
        
        // Banner nur bei Änderungen und wenn Spieler ausgewählt wurden
        if (gameData.selected_players) {
            const currentSelectedPlayers = JSON.stringify(gameData.selected_players);
            if (currentSelectedPlayers !== lastSelectedPlayers) {
                // Show banner for new selection
                if (lastSelectedPlayers !== null && currentSelectedPlayers !== lastSelectedPlayers) {
                    showSelectedPlayersBanner(gameData.selected_players);
                }
                lastSelectedPlayers = currentSelectedPlayers;
            }
        }
    } else {
        hideSelectedPlayersBanner();
        hideSelectedPlayersInfo();
        lastSelectedPlayers = null;
    }
}

function showSelectedPlayersBanner(selectedPlayers) {
    const banner = document.getElementById('selected-players-banner');
    const content = document.getElementById('selected-players-content');
    const progressBar = document.getElementById('banner-progress');
    
    if (!banner || !content || !progressBar) return;

    // Build display text
    const playersList = [];
    for (const [teamId, players] of Object.entries(selectedPlayers)) {
        // Find team name from current dashboard data
        const teamName = getTeamNameById(teamId) || `Team ${teamId}`;
        playersList.push(`${teamName}: ${players.join(', ')}`);
    }

    content.innerHTML = playersList.join('<br>');
    
    // Show banner
    banner.style.display = 'block';
    progressBar.style.width = '100%';
    
    // Clear existing timers
    if (bannerTimer) clearTimeout(bannerTimer);
    if (progressTimer) clearInterval(progressTimer);
    
    // Start progress bar animation
    let width = 100;
    const decrementSpeed = 2; // Decrease by 2% every 100ms
    progressTimer = setInterval(() => {
        width -= decrementSpeed;
        progressBar.style.width = width + '%';
        
        if (width <= 0) {
            clearInterval(progressTimer);
            hideSelectedPlayersBanner();
        }
    }, 100);
    
    // Fallback timer
    bannerTimer = setTimeout(() => {
        hideSelectedPlayersBanner();
    }, 5000);
}

function hideSelectedPlayersBanner() {
    const banner = document.getElementById('selected-players-banner');
    if (banner) {
        banner.style.display = 'none';
    }
    
    if (bannerTimer) {
        clearTimeout(bannerTimer);
        bannerTimer = null;
    }
    if (progressTimer) {
        clearInterval(progressTimer);
        progressTimer = null;
    }
}

function updateSelectedPlayersInfo(selectedPlayers) {
    const infoSection = document.getElementById('selected-players-info');
    const content = document.getElementById('selected-players-persistent');
    const minigameNameEl = document.getElementById('current-minigame-name');
    const minigameDescEl = document.getElementById('current-minigame-description');
    const minigameTitleEl = document.getElementById('current-minigame-title');
    
    if (!infoSection || !content || !minigameNameEl) return;

    // Zeige Info wenn Minispiel läuft (auch ohne ausgewählte Spieler bei Fragen)
    // Aber verstecke es, wenn das Team bereits gewürfelt hat
    if (lastGameData && lastGameData.current_minigame_name && 
        lastGameData.current_phase !== 'DICE_ROLLING') {
        // Setze Minispiel-Name
        minigameNameEl.textContent = lastGameData.current_minigame_name;
        
        // Setze Minispiel-Beschreibung
        if (minigameDescEl) {
            if (lastGameData.current_minigame_description) {
                minigameDescEl.textContent = lastGameData.current_minigame_description;
                minigameDescEl.style.display = 'block';
            } else {
                minigameDescEl.style.display = 'none';
            }
        }
        
        // Bestimme Icon und Titel basierend auf Typ
        if (lastGameData.question_data) {
            minigameTitleEl.innerHTML = '<i class="fas fa-question-circle mr-2"></i>Aktuelle Frage';
        } else {
            minigameTitleEl.innerHTML = '<i class="fas fa-gamepad mr-2"></i>Aktuelles Minispiel';
        }
        
        // Spieler-Info nur bei Minispielen, nicht bei Fragen
        if (lastGameData.question_data) {
            // Bei Fragen keine Spieler-Info anzeigen (da immer alle antworten)
            content.innerHTML = '';
        } else {
            // Bei Minispielen: Prüfe ob "ganzes Team" oder spezifische Auswahl
            const isWholeTeam = lastGameData.current_player_count === 'all';
            console.log('Debug - current_player_count:', lastGameData.current_player_count, 'isWholeTeam:', isWholeTeam);
            
            if (isWholeTeam) {
                content.innerHTML = '<i class="fas fa-users"></i> <strong>Alle spielen</strong>';
            } else if (selectedPlayers && Object.keys(selectedPlayers).length > 0) {
                // Build display text für spezifische Auswahl
                const playersList = [];
                for (const [teamId, players] of Object.entries(selectedPlayers)) {
                    const teamName = getTeamNameById(teamId) || `Team ${teamId}`;
                    playersList.push(`<strong>${teamName}:</strong> ${players.join(', ')}`);
                }
                content.innerHTML = '<i class="fas fa-user-friends"></i> ' + playersList.join(' | ');
            } else {
                // Fallback wenn keine Spieler-Info verfügbar
                content.innerHTML = '<i class="fas fa-users"></i> Alle Spieler nehmen teil';
            }
        }
        
        infoSection.style.display = 'block';
    } else {
        hideSelectedPlayersInfo();
    }
}

function hideSelectedPlayersInfo() {
    const infoSection = document.getElementById('selected-players-info');
    if (infoSection) {
        infoSection.style.display = 'none';
    }
}

function getTeamNameById(teamId) {
    // Try to find team name from lastGameData if available
    if (lastGameData && lastGameData.teams) {
        const team = lastGameData.teams.find(t => t.id.toString() === teamId.toString());
        return team ? team.name : null;
    }
    return null;
}

// Initialization function
function initializeDashboardApp() {
    startLiveUpdates();
    updateLastDiceResultDisplay();
    loadActiveFields(); // Lade aktive Felder beim Start
    
    // Session-Validierung alle 30 Minuten
    setInterval(validateSession, 1800000); // 30 Minuten (war 5 Minuten)
    
    // Initialize progress chart if data exists
    if (lastProgressData && lastProgressData.length > 0) {
        initializeProgressChart();
    }
    
    // Zeige Minispiel-Info beim ersten Laden
    if (dashboardConfig.activeSession && dashboardConfig.activeSession.current_minigame_name) {
        const initialGameData = {
            current_minigame_name: dashboardConfig.activeSession.current_minigame_name,
            current_player_count: dashboardConfig.activeSession.current_player_count,
            question_data: dashboardConfig.activeSession.current_question_id ? true : null,
            selected_players: dashboardConfig.activeSession.selected_players || null,
            teams: dashboardConfig.allTeams || []
        };
        lastGameData = initialGameData;
        updateSelectedPlayersDisplay(initialGameData);
    }
    
    // Auto-hide flash messages
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(alert => {
            const closeBtn = alert.querySelector('.close');
            if (closeBtn) closeBtn.click();
        });
    }, 5000);
}

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    stopLiveUpdates();
    if (diceResultTimer) {
        clearTimeout(diceResultTimer);
    }
    if (bannerTimer) {
        clearTimeout(bannerTimer);
    }
    if (progressTimer) {
        clearInterval(progressTimer);
    }
    if (progressChart) {
        progressChart.destroy();
    }
});

// Export functions for global access
window.TeamDashboard = {
    init: initializeDashboard,
    start: initializeDashboardApp,
    refresh: refreshDashboard
};