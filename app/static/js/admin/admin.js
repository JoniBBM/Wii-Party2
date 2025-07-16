/**
 * Admin page JavaScript - handles admin dashboard functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeAdminHandlers();
});

/**
 * Initialize all admin event handlers
 */
function initializeAdminHandlers() {
    initializeRotationHandlers();
    initializeQuestionHandlers();
    initializeContentHandlers();
    initializeTeamHandlers();
    initializeConfirmationHandlers();
}

/**
 * Initialize rotation statistics handlers
 */
function initializeRotationHandlers() {
    // Show rotation stats button
    const showStatsButtons = document.querySelectorAll('[data-action="show-rotation-stats"]');
    showStatsButtons.forEach(button => {
        button.addEventListener('click', showRotationStats);
    });
    
    // Reset rotation buttons
    const resetButtons = document.querySelectorAll('[data-action="reset-rotation"]');
    resetButtons.forEach(button => {
        button.addEventListener('click', resetRotation);
    });
    
    // Modal reset button
    const modalResetButtons = document.querySelectorAll('[data-action="modal-reset-rotation"]');
    modalResetButtons.forEach(button => {
        button.addEventListener('click', function() {
            resetRotation();
            $('#rotationModal').modal('hide');
        });
    });
}

/**
 * Initialize question handling
 */
function initializeQuestionHandlers() {
    // End question buttons with confirmation
    const endQuestionButtons = document.querySelectorAll('[data-action="end-question"]');
    endQuestionButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const confirmed = confirm('Frage beenden und automatische Platzierung berechnen?');
            if (!confirmed) {
                e.preventDefault();
                return false;
            }
        });
    });
}

/**
 * Initialize content management handlers
 */
function initializeContentHandlers() {
    // Reset played content buttons
    const resetContentButtons = document.querySelectorAll('[data-action="reset-played-content"]');
    resetContentButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const confirmed = confirm('Alle gespielten Inhalte zurücksetzen? Damit werden alle Spiele wieder verfügbar.');
            if (!confirmed) {
                e.preventDefault();
                return false;
            }
        });
    });
}

/**
 * Initialize team management handlers
 */
function initializeTeamHandlers() {
    // Manual team release buttons
    const releaseButtons = document.querySelectorAll('[data-action="release-team"]');
    releaseButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const teamName = this.dataset.teamName || 'dieses Team';
            const confirmed = confirm(`Team ${teamName} manuell freigeben?`);
            if (!confirmed) {
                e.preventDefault();
                return false;
            }
        });
    });
}

/**
 * Initialize confirmation handlers for various actions
 */
function initializeConfirmationHandlers() {
    // Generic confirmation buttons
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    confirmButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const message = this.dataset.confirm;
            const confirmed = confirm(message);
            if (!confirmed) {
                e.preventDefault();
                return false;
            }
        });
    });
}

/**
 * Show rotation statistics
 */
function showRotationStats() {
    console.log('Showing rotation statistics');
    // Implementation for showing rotation stats
    // This would typically fetch data and display in a modal or section
}

/**
 * Reset rotation system
 */
function resetRotation() {
    console.log('Resetting rotation system');
    // Implementation for resetting the rotation system
    // This would typically make an AJAX call to reset the backend state
}