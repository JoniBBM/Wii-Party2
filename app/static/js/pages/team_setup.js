/**
 * Team Setup Page JavaScript
 * Handles character creation, customization, and team setup functionality
 */

// Global variables
let selectedCharacterId = 1;
let availableCharacters = [];
let scene, camera, renderer, character, controls;
let currentCustomization = {};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize extended character customization
    loadCharacterData();
    loadExistingCustomization();
    initCharacterPreview();
    setupColorListeners();
    setupTabs();
    setupCustomizationOptions();
    setupFormHandlers();
    setupEventListeners();
});

/**
 * Character Data Loading
 */
async function loadCharacterData() {
    try {
        const response = await fetch('/api/characters');
        if (response.ok) {
            availableCharacters = await response.json();
            renderCharacterGrid();
        }
    } catch (error) {
        console.error('Fehler beim Laden der Charaktere:', error);
        // Fallback: Standard-Charakter
        availableCharacters = [{
            id: 1,
            name: 'Standard-Charakter',
            description: 'Ein vielseitiger Charakter für alle Situationen',
            rarity: 'common',
            is_unlocked: true,
            stats: {strength: 5, speed: 5, luck: 5, charisma: 5}
        }];
        renderCharacterGrid();
    }
}

/**
 * Character Grid Rendering
 */
function renderCharacterGrid() {
    const grid = document.getElementById('character-grid');
    grid.innerHTML = '';
    
    availableCharacters.forEach(char => {
        const card = document.createElement('div');
        card.className = `character-card ${char.is_unlocked ? '' : 'locked'}`;
        card.dataset.characterId = char.id;
        
        card.innerHTML = `
            <div class="character-name">${char.name}</div>
            <div class="character-description">${char.description || ''}</div>
            <div class="character-rarity ${char.rarity}">${char.rarity.toUpperCase()}</div>
            ${!char.is_unlocked ? '<div class="unlock-indicator">🔒</div>' : ''}
        `;
        
        if (char.is_unlocked) {
            card.addEventListener('click', () => selectCharacter(char.id));
        }
        
        grid.appendChild(card);
    });
    
    // Select first available character
    if (availableCharacters.length > 0) {
        const firstAvailable = availableCharacters.find(char => char.is_unlocked);
        if (firstAvailable) {
            selectCharacter(firstAvailable.id);
        }
    }
}

/**
 * Character Selection
 */
function selectCharacter(characterId) {
    selectedCharacterId = characterId;
    document.getElementById('selected-character-id').value = characterId;
    
    // Update visual selection
    document.querySelectorAll('.character-card').forEach(card => {
        card.classList.remove('selected');
    });
    
    const selectedCard = document.querySelector(`[data-character-id="${characterId}"]`);
    if (selectedCard) {
        selectedCard.classList.add('selected');
    }
    
    // Load character details
    const selectedChar = availableCharacters.find(char => char.id === characterId);
    if (selectedChar) {
        updateCharacterStats(selectedChar.stats);
        updateCharacterPreview();
    }
}

/**
 * Character Stats Update
 */
function updateCharacterStats(stats) {
    ['strength', 'speed', 'luck', 'charisma'].forEach(stat => {
        const value = stats[stat] || 5;
        const bar = document.getElementById(`${stat}-bar`);
        const valueDisplay = document.getElementById(`${stat}-value`);
        
        if (bar && valueDisplay) {
            bar.style.width = `${(value / 10) * 100}%`;
            valueDisplay.textContent = value;
        }
    });
}

/**
 * 3D Character Preview Initialization
 */
function initCharacterPreview() {
    const container = document.getElementById('character-preview');
    
    // Scene setup
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x2a2a2a);
    
    // Camera setup
    camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.set(0, 0.5, 1.5);
    
    // Renderer setup
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setClearColor(0x2a2a2a);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);
    
    // Controls setup
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.enableZoom = true;
    controls.enablePan = false;
    controls.minDistance = 1;
    controls.maxDistance = 3;
    controls.minPolarAngle = Math.PI / 6;
    controls.maxPolarAngle = Math.PI / 2;
    
    // Lighting setup
    const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
    scene.add(ambientLight);
    
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(2, 2, 2);
    directionalLight.castShadow = true;
    scene.add(directionalLight);
    
    // Load initial character
    updateCharacterPreview();
    
    // Animation loop
    function animate() {
        requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
    }
    animate();
}

/**
 * Character Preview Update
 */
function updateCharacterPreview() {
    // Remove existing character
    if (character) {
        scene.remove(character);
    }
    
    // Get current customization values
    const customization = getCurrentCustomization();
    
    // Create new character with customization
    console.log('Creating character with customization:', customization);
    character = createDefaultCharacter('#FF6B6B', customization);
    scene.add(character);
}

/**
 * Get Current Customization Settings
 */
function getCurrentCustomization() {
    const customization = {
        // Basic colors
        shirtColor: getInputValue('shirt-color', '#4169E1'),
        pantsColor: getInputValue('pants-color', '#8B4513'),
        hairColor: getInputValue('hair-color', '#2C1810'),
        shoeColor: getInputValue('shoe-color', '#8B4513'),
        skinColor: getInputValue('skin-color', '#FFDE97'),
        eyeColor: getInputValue('eye-color', '#4169E1'),
        
        // Appearance
        faceShape: getActiveOption('faceShape', 'oval'),
        bodyType: getActiveOption('bodyType', 'normal'),
        height: getActiveOption('height', 'normal'),
        hairStyle: getActiveOption('hairStyle', 'short'),
        eyeShape: getActiveOption('eyeShape', 'normal'),
        beardStyle: getActiveOption('beardStyle', 'none'),
        
        // Clothing
        shirtType: getActiveOption('shirtType', 'tshirt'),
        pantsType: getActiveOption('pantsType', 'jeans'),
        shoeType: getActiveOption('shoeType', 'sneakers'),
        
        // Accessories
        hat: getActiveOption('hat', 'none'),
        glasses: getActiveOption('glasses', 'none'),
        jewelry: getActiveOption('jewelry', 'none'),
        backpack: getActiveOption('backpack', 'none'),
        
        // Animations
        animationStyle: getActiveOption('animationStyle', 'normal'),
        walkStyle: getActiveOption('walkStyle', 'normal'),
        idleStyle: getActiveOption('idleStyle', 'normal'),
        voiceType: getActiveOption('voiceType', 'normal')
    };
    
    console.log('getCurrentCustomization returning:', customization);
    return customization;
}

/**
 * Utility Functions
 */
function getInputValue(id, defaultValue) {
    const input = document.getElementById(id);
    return input ? input.value : defaultValue;
}

function getActiveOption(optionName, defaultValue) {
    const activeBtn = document.querySelector(`[data-option="${optionName}"].active`);
    return activeBtn ? activeBtn.dataset.value : defaultValue;
}

/**
 * Tab Navigation Setup
 */
function setupTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.dataset.tab;
            
            // Deactivate all tabs
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            // Activate selected tab
            btn.classList.add('active');
            document.getElementById(`${tabName}-tab`).classList.add('active');
        });
    });
}

/**
 * Customization Options Setup
 */
function setupCustomizationOptions() {
    const optionBtns = document.querySelectorAll('.option-btn');
    
    optionBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const optionName = btn.dataset.option;
            
            // Deactivate all buttons in this group
            document.querySelectorAll(`[data-option="${optionName}"]`).forEach(b => {
                b.classList.remove('active');
            });
            
            // Activate selected button
            btn.classList.add('active');
            
            // Update preview
            updateCharacterPreview();
        });
    });
}

/**
 * Color Input Listeners Setup
 */
function setupColorListeners() {
    const colorInputs = ['skin-color', 'hair-color', 'eye-color', 'shirt-color', 'pants-color', 'shoe-color'];
    
    colorInputs.forEach(inputId => {
        const input = document.getElementById(inputId);
        if (input) {
            input.addEventListener('input', updateCharacterPreview);
        }
    });
}

/**
 * Form Handlers Setup
 */
function setupFormHandlers() {
    // Form submission
    const setupForm = document.getElementById('setup-form');
    if (setupForm) {
        setupForm.addEventListener('submit', function(e) {
            e.preventDefault();
            submitSetup();
        });
    }

    // Enter key for form
    const teamNameInput = document.getElementById('team-name');
    if (teamNameInput) {
        teamNameInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                submitSetup();
            }
        });
    }
}

/**
 * Event Listeners Setup
 */
function setupEventListeners() {
    // Camera view reset button
    const resetCameraBtn = document.querySelector('[data-action="reset-camera"]');
    if (resetCameraBtn) {
        resetCameraBtn.addEventListener('click', resetCameraView);
    }
    
    // Randomize character button
    const randomizeBtn = document.querySelector('[data-action="randomize-character"]');
    if (randomizeBtn) {
        randomizeBtn.addEventListener('click', randomizeCharacter);
    }
}

/**
 * Camera View Reset
 */
function resetCameraView() {
    if (camera && controls) {
        camera.position.set(0, 0.5, 1.5);
        controls.reset();
    }
}

/**
 * Character Randomization
 */
function randomizeCharacter() {
    // Random options selection
    const options = [
        { name: 'faceShape', values: ['oval', 'round', 'square', 'heart'] },
        { name: 'bodyType', values: ['slim', 'normal', 'athletic', 'chunky'] },
        { name: 'hairStyle', values: ['short', 'medium', 'long', 'curly', 'bald'] },
        { name: 'eyeShape', values: ['normal', 'big', 'small', 'sleepy'] },
        { name: 'beardStyle', values: ['none', 'mustache', 'goatee', 'full'] },
        { name: 'shirtType', values: ['tshirt', 'polo', 'hoodie', 'formal'] },
        { name: 'pantsType', values: ['jeans', 'shorts', 'formal', 'athletic'] },
        { name: 'shoeType', values: ['sneakers', 'boots', 'formal', 'sandals'] },
        { name: 'hat', values: ['none', 'cap', 'beanie', 'formal'] },
        { name: 'glasses', values: ['none', 'normal', 'sunglasses', 'reading'] },
        { name: 'jewelry', values: ['none', 'watch', 'chain', 'rings'] },
        { name: 'backpack', values: ['none', 'school', 'hiking', 'stylish'] },
        { name: 'animationStyle', values: ['normal', 'energetic', 'calm', 'quirky'] },
        { name: 'walkStyle', values: ['normal', 'bouncy', 'confident', 'sneaky'] },
        { name: 'idleStyle', values: ['normal', 'fidgety', 'relaxed', 'proud'] },
        { name: 'voiceType', values: ['normal', 'deep', 'high', 'robotic'] }
    ];
    
    options.forEach(option => {
        const randomValue = option.values[Math.floor(Math.random() * option.values.length)];
        const btn = document.querySelector(`[data-option="${option.name}"][data-value="${randomValue}"]`);
        if (btn) {
            btn.click();
        }
    });
    
    // Random colors
    const colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9'];
    const shirtColorInput = document.getElementById('shirt-color');
    const pantsColorInput = document.getElementById('pants-color');
    const hairColorInput = document.getElementById('hair-color');
    const shoeColorInput = document.getElementById('shoe-color');
    
    if (shirtColorInput) shirtColorInput.value = colors[Math.floor(Math.random() * colors.length)];
    if (pantsColorInput) pantsColorInput.value = colors[Math.floor(Math.random() * colors.length)];
    if (hairColorInput) hairColorInput.value = colors[Math.floor(Math.random() * colors.length)];
    if (shoeColorInput) shoeColorInput.value = colors[Math.floor(Math.random() * colors.length)];
    
    updateCharacterPreview();
}

/**
 * Load Existing Customization
 */
function loadExistingCustomization() {
    // This would typically load from server data
    // For now, we'll use defaults or any existing data
    const teamCustomizationElement = document.getElementById('team-customization-data');
    if (teamCustomizationElement) {
        try {
            const teamCustomization = JSON.parse(teamCustomizationElement.textContent);
            if (teamCustomization) {
                // Set colors
                setInputValue('skin-color', teamCustomization.skinColor);
                setInputValue('hair-color', teamCustomization.hairColor);
                setInputValue('eye-color', teamCustomization.eyeColor);
                setInputValue('shirt-color', teamCustomization.shirtColor);
                setInputValue('pants-color', teamCustomization.pantsColor);
                setInputValue('shoe-color', teamCustomization.shoeColor);
                
                // Set options
                setActiveOption('faceShape', teamCustomization.faceShape);
                setActiveOption('bodyType', teamCustomization.bodyType);
                setActiveOption('height', teamCustomization.height);
                setActiveOption('hairStyle', teamCustomization.hairStyle);
                setActiveOption('eyeShape', teamCustomization.eyeShape);
                setActiveOption('beardStyle', teamCustomization.beardStyle);
                setActiveOption('shirtType', teamCustomization.shirtType);
                setActiveOption('pantsType', teamCustomization.pantsType);
                setActiveOption('shoeType', teamCustomization.shoeType);
                setActiveOption('hat', teamCustomization.hat);
                setActiveOption('glasses', teamCustomization.glasses);
                setActiveOption('jewelry', teamCustomization.jewelry);
                setActiveOption('backpack', teamCustomization.backpack);
                setActiveOption('animationStyle', teamCustomization.animationStyle);
                setActiveOption('walkStyle', teamCustomization.walkStyle);
                setActiveOption('idleStyle', teamCustomization.idleStyle);
                setActiveOption('voiceType', teamCustomization.voiceType);
            }
        } catch (error) {
            console.error('Error loading existing customization:', error);
        }
    }
}

function setInputValue(id, value) {
    const input = document.getElementById(id);
    if (input && value) {
        input.value = value;
    }
}

function setActiveOption(optionName, value) {
    if (!value) return;
    
    // Deactivate all buttons in this group
    document.querySelectorAll(`[data-option="${optionName}"]`).forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Activate selected button
    const activeBtn = document.querySelector(`[data-option="${optionName}"][data-value="${value}"]`);
    if (activeBtn) {
        activeBtn.classList.add('active');
    }
}

/**
 * Form Submission Handler
 */
function submitSetup() {
    const teamName = document.getElementById('team-name').value.trim();
    const submitBtn = document.getElementById('submit-btn');
    const statusDiv = document.getElementById('status-message');
    
    if (!teamName) {
        showStatus('Team-Name ist erforderlich!', 'error');
        return;
    }

    // Disable button
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Wird gespeichert...';

    // Collect all customization data
    const customization = getCurrentCustomization();
    
    const formData = {
        team_name: teamName,
        character_id: selectedCharacterId || 1,
        customization: customization
    };

    // Get CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || 
                     document.querySelector('input[name="csrf_token"]')?.value || '';
    
    console.log('Sending comprehensive team setup with data:', formData);
    console.log('CSRF Token:', csrfToken);

    fetch(window.location.href, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(formData)
    })
    .then(response => {
        console.log('Response status:', response.status);
        console.log('Response headers:', response.headers);
        
        if (!response.ok) {
            return response.text().then(text => {
                console.error('Error response body:', text);
                throw new Error(`HTTP ${response.status}: ${text.substring(0, 200)}`);
            });
        }
        
        const contentType = response.headers.get('content-type');
        console.log('Content-Type:', contentType);
        
        if (contentType && contentType.includes('application/json')) {
            return response.json();
        } else {
            return response.text().then(text => {
                console.error('Non-JSON response:', text);
                throw new Error('Server hat keine JSON-Antwort gesendet: ' + text.substring(0, 100));
            });
        }
    })
    .then(data => {
        if (data.success) {
            showStatus(data.message, 'success');
            setTimeout(() => {
                window.location.href = data.redirect || '/teams/dashboard';
            }, 2000);
        } else {
            showStatus(data.error || 'Ein Fehler ist aufgetreten', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        if (error.message.includes('JSON')) {
            showStatus('Server-Fehler: Ungültige Antwort erhalten', 'error');
        } else {
            showStatus('Ein Fehler ist aufgetreten. Versuche es nochmal!', 'error');
        }
    })
    .finally(() => {
        // Re-enable button
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-check"></i> Setup abschließen';
    });
}

/**
 * Show Status Message
 */
function showStatus(message, type) {
    const statusDiv = document.getElementById('status-message');
    const statusText = document.getElementById('status-text');
    
    if (statusDiv && statusText) {
        statusDiv.className = `status-message status-${type}`;
        statusText.textContent = message;
        statusDiv.style.display = 'block';
        
        // Auto-hide after 5 seconds for errors
        if (type === 'error') {
            setTimeout(() => {
                statusDiv.style.display = 'none';
            }, 5000);
        }
    }
}

/**
 * Legacy Functions for Compatibility
 */
function updateCharacterSelection() {
    // All character cards reset
    document.querySelectorAll('.character-card').forEach(card => {
        card.classList.remove('selected');
    });
    
    // Mark selected card
    if (selectedCharacterId) {
        const selectedCard = document.querySelector(`#character-${selectedCharacterId}`)?.closest('.character-card');
        if (selectedCard) {
            selectedCard.classList.add('selected');
        }
    }
}

/**
 * Window Resize Handler
 */
window.addEventListener('resize', function() {
    if (renderer && camera) {
        const container = document.getElementById('character-preview');
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    }
});