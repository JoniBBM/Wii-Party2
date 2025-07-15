function createTungTungTungSahur(colorHex) {
    console.log('🏗️ Creating improved Tung Tung Sahur character...');
    const group = new THREE.Group();

    // Realistische Hautfarbe statt Holz
    const skinColor = 0xFFDBAC; // Natürliche Hautfarbe
    const skinMaterial = new THREE.MeshPhongMaterial({
        color: skinColor,
        shininess: 30,
        specular: 0x444444
    });
    
    // Kleidungsmaterial
    const clothingMaterial = new THREE.MeshPhongMaterial({
        color: 0x4169E1, // Königsblau für Kleidung
        shininess: 5,
        specular: 0x222222
    });

    // Hauptkörper - realistischere Proportionen
    const torso = new THREE.Mesh(
        new THREE.BoxGeometry(0.35, 0.6, 0.2),
        clothingMaterial
    );
    torso.position.y = 0.1;
    group.add(torso);
    
    // Bauch/Unterkörper
    const belly = new THREE.Mesh(
        new THREE.BoxGeometry(0.32, 0.35, 0.18),
        clothingMaterial
    );
    belly.position.y = -0.25;
    group.add(belly);

    // Kopf - rundere, menschlichere Form
    const head = new THREE.Mesh(
        new THREE.SphereGeometry(0.18, 16, 16),
        skinMaterial
    );
    head.scale.set(1, 1.1, 0.9); // Leicht oval
    head.position.set(0, 0.65, 0);
    group.add(head);
    
    // Hals
    const neck = new THREE.Mesh(
        new THREE.CylinderGeometry(0.06, 0.06, 0.12, 8),
        skinMaterial
    );
    neck.position.set(0, 0.48, 0);
    group.add(neck);

    // Realistische Augen
    const eyePositions = [
        { x: -0.06, y: 0.68, z: 0.15 },
        { x: 0.06, y: 0.68, z: 0.15 }
    ];

    eyePositions.forEach(pos => {
        // Augenhöhle
        const eyeSocket = new THREE.Mesh(
            new THREE.SphereGeometry(0.04, 12, 12),
            new THREE.MeshPhongMaterial({
                color: 0xFFFFFF,
                shininess: 100
            })
        );
        eyeSocket.position.set(pos.x, pos.y, pos.z);
        group.add(eyeSocket);

        // Iris (braun)
        const iris = new THREE.Mesh(
            new THREE.CircleGeometry(0.02, 16),
            new THREE.MeshBasicMaterial({
                color: 0x8B4513,
                side: THREE.DoubleSide
            })
        );
        iris.position.set(pos.x, pos.y, pos.z + 0.035);
        group.add(iris);

        // Pupille
        const pupil = new THREE.Mesh(
            new THREE.CircleGeometry(0.01, 12),
            new THREE.MeshBasicMaterial({
                color: 0x000000,
                side: THREE.DoubleSide
            })
        );
        pupil.position.set(pos.x, pos.y, pos.z + 0.036);
        group.add(pupil);
    });
    
    // Augenbrauen
    for (let i = 0; i < 2; i++) {
        const eyebrow = new THREE.Mesh(
            new THREE.BoxGeometry(0.06, 0.015, 0.02),
            new THREE.MeshBasicMaterial({ color: 0x4A4A4A })
        );
        eyebrow.position.set(i === 0 ? -0.06 : 0.06, 0.72, 0.14);
        group.add(eyebrow);
    }

    // Realistischer Mund
    const mouth = new THREE.Mesh(
        new THREE.SphereGeometry(0.025, 8, 8),
        new THREE.MeshBasicMaterial({
            color: 0x8B0000
        })
    );
    mouth.scale.set(1.5, 0.5, 0.5);
    mouth.position.set(0, 0.58, 0.16);
    group.add(mouth);
    
    // Nase
    const nose = new THREE.Mesh(
        new THREE.ConeGeometry(0.015, 0.04, 6),
        skinMaterial
    );
    nose.position.set(0, 0.62, 0.16);
    nose.rotation.x = Math.PI / 2;
    group.add(nose);

    // Realistische Arme
    for (let i = 0; i < 2; i++) {
        // Oberarm
        const upperArm = new THREE.Mesh(
            new THREE.CylinderGeometry(0.035, 0.03, 0.25, 8),
            skinMaterial
        );
        upperArm.position.set(i === 0 ? -0.22 : 0.22, 0.25, 0);
        group.add(upperArm);
        
        // Unterarm
        const lowerArm = new THREE.Mesh(
            new THREE.CylinderGeometry(0.03, 0.025, 0.22, 8),
            skinMaterial
        );
        lowerArm.position.set(i === 0 ? -0.45 : 0.45, 0.05, 0);
        group.add(lowerArm);
        
        // Hand
        const hand = new THREE.Mesh(
            new THREE.SphereGeometry(0.04, 8, 8),
            skinMaterial
        );
        hand.position.set(i === 0 ? -0.58 : 0.58, -0.08, 0);
        group.add(hand);
    }

    // Realistische Beine
    for (let i = 0; i < 2; i++) {
        // Oberschenkel
        const thigh = new THREE.Mesh(
            new THREE.CylinderGeometry(0.045, 0.04, 0.35, 8),
            clothingMaterial
        );
        thigh.position.set(i === 0 ? -0.08 : 0.08, -0.6, 0);
        group.add(thigh);
        
        // Unterschenkel
        const shin = new THREE.Mesh(
            new THREE.CylinderGeometry(0.035, 0.03, 0.3, 8),
            skinMaterial
        );
        shin.position.set(i === 0 ? -0.08 : 0.08, -0.95, 0);
        group.add(shin);
    }

    // Verbesserter Baseball-Schläger
    const batMaterial = new THREE.MeshPhongMaterial({
        color: 0x8B4513,
        shininess: 50,
        specular: 0x666666
    });
    
    const batHandle = new THREE.Mesh(
        new THREE.CylinderGeometry(0.018, 0.022, 0.35, 12),
        batMaterial
    );
    batHandle.position.set(-0.45, 0.1, 0);
    batHandle.rotation.z = Math.PI / 4;
    group.add(batHandle);

    const batHead = new THREE.Mesh(
        new THREE.CylinderGeometry(0.055, 0.035, 0.25, 12),
        batMaterial
    );
    batHead.position.set(-0.62, 0.28, 0);
    batHead.rotation.z = Math.PI / 4;
    group.add(batHead);
    
    // Schläger-Griff
    const grip = new THREE.Mesh(
        new THREE.CylinderGeometry(0.025, 0.025, 0.08, 8),
        new THREE.MeshPhongMaterial({ color: 0x000000 })
    );
    grip.position.set(-0.36, 0.02, 0);
    grip.rotation.z = Math.PI / 4;
    group.add(grip);

    // Realistische Schuhe
    for (let i = 0; i < 2; i++) {
        const shoe = new THREE.Mesh(
            new THREE.BoxGeometry(0.1, 0.06, 0.18),
            new THREE.MeshPhongMaterial({ color: 0x000000 })
        );
        shoe.position.set(i === 0 ? -0.08 : 0.08, -1.12, 0.04);
        group.add(shoe);
        
        // Schuhsohle
        const sole = new THREE.Mesh(
            new THREE.BoxGeometry(0.11, 0.02, 0.19),
            new THREE.MeshPhongMaterial({ color: 0x8B4513 })
        );
        sole.position.set(i === 0 ? -0.08 : 0.08, -1.15, 0.04);
        group.add(sole);
    }

    // Verbesserte Animation
    group.userData = {
        animation: time => {
            // Sanftes Atmen/Wippen
            const breathe = Math.sin(time * 1.5) * 0.02;
            torso.position.y = 0.1 + breathe;
            head.position.y = 0.65 + breathe;
            neck.position.y = 0.48 + breathe;
            
            // Baseball-Schläger schwingt realistischer
            if (batHandle && batHead && grip) {
                const swingAngle = Math.sin(time * 2.5) * 0.2;
                batHandle.rotation.z = Math.PI / 4 + swingAngle;
                batHead.rotation.z = Math.PI / 4 + swingAngle;
                grip.rotation.z = Math.PI / 4 + swingAngle;
            }

            // Leichte Gewichtsverlagerung
            group.rotation.z = Math.sin(time * 1.8) * 0.03;
            
            // Augen blinzeln gelegentlich (subtil)
            if (Math.sin(time * 0.3) > 0.98) {
                group.children.forEach(child => {
                    if (child.geometry && child.geometry.type === 'SphereGeometry' &&
                        child.geometry.parameters && child.geometry.parameters.radius === 0.04) {
                        child.scale.y = 0.1;
                    }
                });
            } else {
                group.children.forEach(child => {
                    if (child.geometry && child.geometry.type === 'SphereGeometry' &&
                        child.geometry.parameters && child.geometry.parameters.radius === 0.04) {
                        child.scale.y = 1;
                    }
                });
            }
        }
    };
    
    // Haare hinzufügen
    const hair = new THREE.Mesh(
        new THREE.SphereGeometry(0.19, 12, 12),
        new THREE.MeshPhongMaterial({ color: 0x4A4A4A })
    );
    hair.position.set(0, 0.75, -0.02);
    hair.scale.set(1, 0.6, 1.1);
    group.add(hair);
    
    // Shirt-Details
    const shirtLine = new THREE.Mesh(
        new THREE.BoxGeometry(0.36, 0.02, 0.01),
        new THREE.MeshBasicMaterial({ color: 0x000080 })
    );
    shirtLine.position.set(0, 0.3, 0.11);
    group.add(shirtLine);

    return group;
}