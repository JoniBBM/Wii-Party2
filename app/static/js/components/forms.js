/**
 * Form utilities and handlers for various form interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeFormHandlers();
});

/**
 * Initialize all form-related event handlers
 */
function initializeFormHandlers() {
    initializeBulkSelectHandlers();
    initializePlayerEditHandlers();
    initializePlayerSelectionHandlers();
    initializeRefreshHandlers();
}

/**
 * Initialize bulk select functionality
 */
function initializeBulkSelectHandlers() {
    // Select all buttons
    const selectAllButtons = document.querySelectorAll('[data-action="select-all"]');
    selectAllButtons.forEach(button => {
        button.addEventListener('click', selectAll);
    });
    
    // Select none buttons
    const selectNoneButtons = document.querySelectorAll('[data-action="select-none"]');
    selectNoneButtons.forEach(button => {
        button.addEventListener('click', selectNone);
    });
}

/**
 * Initialize player edit functionality
 */
function initializePlayerEditHandlers() {
    // Edit player name buttons
    const editButtons = document.querySelectorAll('[data-action="edit-player"]');
    editButtons.forEach(button => {
        button.addEventListener('click', function() {
            const playerId = this.dataset.playerId;
            editPlayerName(playerId);
        });
    });
    
    // Save player name buttons
    const saveButtons = document.querySelectorAll('[data-action="save-player"]');
    saveButtons.forEach(button => {
        button.addEventListener('click', function() {
            const playerId = this.dataset.playerId;
            savePlayerName(playerId);
        });
    });
    
    // Cancel player edit buttons
    const cancelButtons = document.querySelectorAll('[data-action="cancel-player-edit"]');
    cancelButtons.forEach(button => {
        button.addEventListener('click', function() {
            const playerId = this.dataset.playerId;
            cancelPlayerEdit(playerId);
        });
    });
}

/**
 * Initialize player selection handlers
 */
function initializePlayerSelectionHandlers() {
    const selectionButtons = document.querySelectorAll('[data-action="toggle-player-selection"]');
    selectionButtons.forEach(button => {
        button.addEventListener('click', function() {
            const playerName = this.dataset.playerName;
            const teamId = this.dataset.teamId;
            const playerIndex = this.dataset.playerIndex;
            const canBeSelected = this.dataset.canBeSelected === 'true';
            
            togglePlayerSelection(playerName, teamId, playerIndex, !canBeSelected);
        });
    });
}

/**
 * Initialize refresh handlers
 */
function initializeRefreshHandlers() {
    // Dashboard refresh buttons
    const refreshButtons = document.querySelectorAll('[data-action="refresh-dashboard"]');
    refreshButtons.forEach(button => {
        button.addEventListener('click', function() {
            if (typeof TeamDashboard !== 'undefined' && TeamDashboard.refresh) {
                TeamDashboard.refresh();
            } else if (typeof refreshDashboard === 'function') {
                refreshDashboard();
            }
        });
    });
}

/**
 * Select all checkboxes/items
 */
function selectAll() {
    const checkboxes = document.querySelectorAll('input[type="checkbox"]:not([data-exclude-bulk])');
    checkboxes.forEach(checkbox => {
        checkbox.checked = true;
    });
    console.log('Selected all items');
}

/**
 * Deselect all checkboxes/items
 */
function selectNone() {
    const checkboxes = document.querySelectorAll('input[type="checkbox"]:not([data-exclude-bulk])');
    checkboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    console.log('Deselected all items');
}

/**
 * Edit player name
 * @param {string} playerId - The player ID
 */
function editPlayerName(playerId) {
    const nameElement = document.querySelector(`[data-player-name="${playerId}"]`);
    const editButton = document.querySelector(`[data-action="edit-player"][data-player-id="${playerId}"]`);
    const saveButton = document.querySelector(`[data-action="save-player"][data-player-id="${playerId}"]`);
    const cancelButton = document.querySelector(`[data-action="cancel-player-edit"][data-player-id="${playerId}"]`);
    
    if (nameElement) {
        const currentName = nameElement.textContent.trim();
        nameElement.innerHTML = `<input type="text" class="form-control form-control-sm" value="${currentName}" data-original-name="${currentName}">`;
        
        if (editButton) editButton.style.display = 'none';
        if (saveButton) saveButton.style.display = 'inline-block';
        if (cancelButton) cancelButton.style.display = 'inline-block';
    }
}

/**
 * Save player name
 * @param {string} playerId - The player ID
 */
function savePlayerName(playerId) {
    const nameElement = document.querySelector(`[data-player-name="${playerId}"]`);
    const inputElement = nameElement ? nameElement.querySelector('input') : null;
    
    if (inputElement) {
        const newName = inputElement.value.trim();
        if (newName) {
            nameElement.textContent = newName;
            // Here you would typically make an AJAX call to save the name
            console.log(`Saving player name: ${newName}`);
        }
        
        resetPlayerEditUI(playerId);
    }
}

/**
 * Cancel player edit
 * @param {string} playerId - The player ID
 */
function cancelPlayerEdit(playerId) {
    const nameElement = document.querySelector(`[data-player-name="${playerId}"]`);
    const inputElement = nameElement ? nameElement.querySelector('input') : null;
    
    if (inputElement) {
        const originalName = inputElement.dataset.originalName;
        nameElement.textContent = originalName;
        resetPlayerEditUI(playerId);
    }
}

/**
 * Reset player edit UI
 * @param {string} playerId - The player ID
 */
function resetPlayerEditUI(playerId) {
    const editButton = document.querySelector(`[data-action="edit-player"][data-player-id="${playerId}"]`);
    const saveButton = document.querySelector(`[data-action="save-player"][data-player-id="${playerId}"]`);
    const cancelButton = document.querySelector(`[data-action="cancel-player-edit"][data-player-id="${playerId}"]`);
    
    if (editButton) editButton.style.display = 'inline-block';
    if (saveButton) saveButton.style.display = 'none';
    if (cancelButton) cancelButton.style.display = 'none';
}

/**
 * Toggle player selection
 * @param {string} playerName - The player name
 * @param {number} teamId - The team ID
 * @param {number} playerIndex - The player index
 * @param {boolean} canBeSelected - Whether the player can be selected
 */
function togglePlayerSelection(playerName, teamId, playerIndex, canBeSelected) {
    console.log(`Toggling selection for player: ${playerName}, team: ${teamId}, index: ${playerIndex}, can select: ${canBeSelected}`);
    // Implementation would typically make an AJAX call to update selection state
}