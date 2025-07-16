/**
 * Index page JavaScript - handles registration popup and camera functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize popup event handlers
    initializePopupHandlers();
    initializeCameraHandlers();
});

/**
 * Initialize registration popup event handlers
 */
function initializePopupHandlers() {
    // Close button
    const closeButtons = document.querySelectorAll('.popup-close');
    closeButtons.forEach(button => {
        button.addEventListener('click', closeRegistrationPopup);
    });
    
    // Proceed to camera button
    const proceedButtons = document.querySelectorAll('[data-action="proceed-camera"]');
    proceedButtons.forEach(button => {
        button.addEventListener('click', proceedToCamera);
    });
    
    // Cancel/close buttons
    const cancelButtons = document.querySelectorAll('[data-action="close-popup"]');
    cancelButtons.forEach(button => {
        button.addEventListener('click', closeRegistrationPopup);
    });
    
    // Back to name step button
    const backButtons = document.querySelectorAll('[data-action="back-name"]');
    backButtons.forEach(button => {
        button.addEventListener('click', backToNameStep);
    });
}

/**
 * Initialize camera-related event handlers
 */
function initializeCameraHandlers() {
    // Camera controls will be handled by existing camera JS
    console.log('Camera handlers initialized');
}

/**
 * Close registration popup
 */
function closeRegistrationPopup() {
    const popup = document.getElementById('registrationPopup');
    if (popup) {
        popup.style.display = 'none';
    }
}

/**
 * Proceed to camera step
 */
function proceedToCamera() {
    console.log('Proceeding to camera step');
    // Implementation depends on existing camera functionality
}

/**
 * Go back to name input step
 */
function backToNameStep() {
    console.log('Going back to name step');
    // Implementation depends on existing form state management
}