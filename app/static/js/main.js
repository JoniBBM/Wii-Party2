/**
 * Wii Party - Hauptskript
 * Enthält gemeinsam genutzte Funktionen für die gesamte Anwendung
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Wii Party Application loaded');
    
    
    // Flash-Nachrichten automatisch ausblenden
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert.alert-dismissible');
        alerts.forEach(alert => {
            const closeBtn = alert.querySelector('.close');
            if (closeBtn) closeBtn.click();
        });
    }, 5000);
    
    // Tooltip-Initialisierung
    if (typeof $ !== 'undefined' && typeof $.fn.tooltip !== 'undefined') {
        $('[data-toggle="tooltip"]').tooltip();
    }
    
    // Formular-Validierung 
    const forms = document.querySelectorAll('.needs-validation');
    if (forms.length > 0) {
        Array.from(forms).forEach(form => {
            form.addEventListener('submit', event => {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                form.classList.add('was-validated');
            }, false);
        });
    }
    
    // Dark Mode Toggle (falls vorhanden)
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', function() {
            document.body.classList.toggle('dark-mode');
            
            // Speichern der Präferenz
            const isDarkMode = document.body.classList.contains('dark-mode');
            localStorage.setItem('darkMode', isDarkMode ? 'enabled' : 'disabled');
        });
        
        // Gespeicherte Präferenz laden
        if (localStorage.getItem('darkMode') === 'enabled') {
            document.body.classList.add('dark-mode');
        }
    }
    
    // Responsive Menu Enhancement
    const navbarToggler = document.querySelector('.navbar-toggler');
    if (navbarToggler) {
        navbarToggler.addEventListener('click', function() {
            this.classList.toggle('active');
        });
    }
    
    // Automatische Seitenaktualisierung
    const autoRefresh = document.querySelector('[data-auto-refresh]');
    if (autoRefresh) {
        const interval = parseInt(autoRefresh.dataset.refreshInterval || 30) * 1000;
        setInterval(() => {
            location.reload();
        }, interval);
    }
});
// Test Three.js
document.addEventListener('DOMContentLoaded', function() {
  try {
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth/window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({canvas: document.getElementById('game-canvas')});
    renderer.setClearColor(0x0088ff);
    renderer.render(scene, camera);
    console.log("Three.js grundlegender Test erfolgreich!");
  } catch (error) {
    console.error("Three.js Fehler:", error);
  }
});
