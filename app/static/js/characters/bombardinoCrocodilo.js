// Datei: app/static/js/characters/bombardinoCrocodilo.js
function createBombardinoCrocodilo(colorHex) {
    const group = new THREE.Group();

    const planeColor = colorHex ? new THREE.Color(colorHex).getHex() : 0x9E9E9E; // Charakterfarbe für Rumpf
    const crocColor = 0x2E7D32; // Krokodilgrün beibehalten oder anpassen
    const darkGray = 0x424242;
    const propellerColor = 0x546E7A;
    const eyeColor = 0xFFEB3B;
    const pupilColor = 0x000000;
    const toothColor = 0xFFFFFF;
    const bombColor = 0x388E3C; // Farbe der Bombe, könnte auch von colorHex abgeleitet werden
    const cockpitColor = 0xB0E0E6;

    const planeMaterial = new THREE.MeshPhongMaterial({ color: planeColor, shininess: 60 });
    const crocMaterial = new THREE.MeshPhongMaterial({ color: crocColor, shininess: 30 });
    const darkGrayMaterial = new THREE.MeshPhongMaterial({ color: darkGray, shininess: 50 });
    const propellerMaterial = new THREE.MeshPhongMaterial({ color: propellerColor, shininess: 70 });
    const eyeMaterial = new THREE.MeshPhongMaterial({ color: eyeColor, shininess: 80 });
    const pupilMaterial = new THREE.MeshBasicMaterial({ color: pupilColor });
    const toothMaterial = new THREE.MeshBasicMaterial({ color: toothColor });
    const bombMaterial = new THREE.MeshPhongMaterial({ color: bombColor, shininess: 40 });
    const cockpitMaterial = new THREE.MeshPhongMaterial({ color: cockpitColor, transparent: true, opacity: 0.7, shininess: 80 });

    const fuselageRadiusBottom = 0.2, fuselageHeight = 1.1;

    // 1. FLUGZEUGRUMPF
    const fuselage = new THREE.Mesh(new THREE.CylinderGeometry(0.25, fuselageRadiusBottom, fuselageHeight, 16), planeMaterial);
    fuselage.position.y = fuselageRadiusBottom;
    fuselage.rotation.x = Math.PI / 2;
    group.add(fuselage);

    // 2. KROKODILKOPF
    const crocHeadGroup = new THREE.Group();
    crocHeadGroup.position.y = fuselageHeight / 2;
    crocHeadGroup.rotation.x = -Math.PI / 2;
    fuselage.add(crocHeadGroup);
    const headBase = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.25, 0.3), crocMaterial);
    crocHeadGroup.add(headBase);
    const snout = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.15, 0.5), crocMaterial);
    snout.position.set(0, -0.05, 0.15 + 0.25); headBase.add(snout);
    for (let i = 0; i < 2; i++) {
        const eye = new THREE.Mesh(new THREE.SphereGeometry(0.07, 10, 10), eyeMaterial);
        eye.position.set(i === 0 ? 0.13 : -0.13, 0.1, 0.15 - 0.03); headBase.add(eye);
        const pupil = new THREE.Mesh(new THREE.SphereGeometry(0.035, 8, 8), pupilMaterial);
        pupil.position.z = 0.05; eye.add(pupil);
    }
    for (let i = 0; i < 3; i++) {
        const tooth1 = new THREE.Mesh(new THREE.ConeGeometry(0.015, 0.05, 4), toothMaterial);
        tooth1.position.set(0.08, -(0.15/2 - 0.01), -0.2 + i * 0.2); snout.add(tooth1);
        const tooth2 = tooth1.clone(); tooth2.position.x = -0.08; snout.add(tooth2);
    }

    const propellersToAnimate = [];

    // 3. FLÜGEL UND MOTOREN/PROPELLER
    for (let i = 0; i < 2; i++) {
        const wing = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.08, 0.25), planeMaterial);
        wing.position.x = (i === 0 ? 1 : -1) * (fuselageRadiusBottom + 1.2 / 2);
        wing.rotation.x = -Math.PI / 2;
        fuselage.add(wing);

        const engineHeight = 0.18;
        const engineRadius = 0.08;
        const engineUnit = new THREE.Group();
        const engine = new THREE.Mesh(
            new THREE.CylinderGeometry(engineRadius, engineRadius * 0.95, engineHeight, 12),
            darkGrayMaterial
        );
        engineUnit.add(engine);

        const propellerGroup = new THREE.Group(); // Gruppe für die Propellerblätter
        propellerGroup.userData = { type: 'propeller' }; // Markierung für die Sammlung
        propellerGroup.position.y = engineHeight / 2;
        engine.add(propellerGroup);
        propellersToAnimate.push(propellerGroup); // Zum Array hinzufügen

        for (let j = 0; j < 3; j++) {
            const blade = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.015, 0.01), propellerMaterial);
            blade.position.x = 0.22 / 2;
            const bladeGroup = new THREE.Group();
            bladeGroup.add(blade);
            bladeGroup.rotation.y = (j / 3) * Math.PI * 2;
            propellerGroup.add(bladeGroup);
        }

        engineUnit.rotation.x = Math.PI / 2;
        wing.add(engineUnit);
        engineUnit.position.z = (wing.geometry.parameters.depth / 2) + engineRadius * 0.8;
        engineUnit.position.y = wing.geometry.parameters.height * 0.1;
    }

    // Leitwerk, Bombe, Cockpit
    const verticalStabilizer = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.3, 0.15), planeMaterial);
    verticalStabilizer.position.set(0, -fuselageHeight / 2, fuselageRadiusBottom + (0.3 / 2));
    fuselage.add(verticalStabilizer);
    const horizontalStabilizer = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.05, 0.12), planeMaterial);
    horizontalStabilizer.position.set(0, -fuselageHeight / 2, fuselageRadiusBottom);
    fuselage.add(horizontalStabilizer);
    const bombBody = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 0.25, 10), bombMaterial);
    const bombNose = new THREE.Mesh(new THREE.SphereGeometry(0.07, 10, 8, 0, Math.PI * 2, 0, Math.PI / 2), bombMaterial);
    bombNose.position.y = 0.125; bombBody.add(bombNose);
    const bombTail = bombNose.clone(); bombTail.rotation.x = Math.PI; bombTail.position.y = -0.125; bombBody.add(bombTail);
    bombBody.position.z = -(fuselageRadiusBottom + 0.07);
    fuselage.add(bombBody);
    const cockpit = new THREE.Mesh(new THREE.SphereGeometry(0.12, 16, 12, 0, Math.PI * 2, 0, Math.PI / 2), cockpitMaterial);
    cockpit.position.set(0, fuselageHeight / 2 * 0.3, fuselageRadiusBottom + 0.06);
    fuselage.add(cockpit);

    group.userData = {
        isFlyingCharacter: true, // Als fliegenden Charakter markieren
        isMoving: false,         // Wird von game_board.html gesetzt
        propellerBaseSpeed: 20,  // Grundgeschwindigkeit der Propeller
        propellerBoostSpeed: 30, // Zusätzliche Geschwindigkeit beim Bewegen
        propellers: propellersToAnimate, // Referenzen zu den Propeller-Gruppen
        animation: function(time) { // 'this' bezieht sich auf group.userData
            // Interne Animationen:
            if (snout && !this.isMoving) { // Schnauze nur bewegen, wenn nicht in Bewegung
                snout.rotation.x = Math.abs(Math.sin(time * 2.5)) * 0.08;
            }

            // Propelleranimation
            let currentSpeed = this.propellerBaseSpeed;
            if (this.isMoving) {
                currentSpeed += this.propellerBoostSpeed;
            }

            this.propellers.forEach(p => {
                // Die Y-Achse der Propeller-Gruppe ist ihre Rotationsachse
                p.rotation.y = time * currentSpeed;
            });
        }
    };
    return group;
}