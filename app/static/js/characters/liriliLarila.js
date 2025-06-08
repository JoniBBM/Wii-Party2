function createLiriliLarila(colorHex) {
    const group = new THREE.Group();
    const color = parseInt(colorHex.replace('#', '0x'), 16);

    // MASSIVE Musiknote Körper - BRAIN ROT SIZE
    const bodyGeometry = new THREE.SphereGeometry(0.25, 16, 16); // Größer
    const bodyMaterial = new THREE.MeshPhongMaterial({
        color: color,
        shininess: 40
    });
    const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
    body.position.y = 0.2; // NIEDRIGER wie Bombardino
    group.add(body);

    // ÜBERTRIEBENER Notenhals
    const stemGeometry = new THREE.CylinderGeometry(0.05, 0.05, 0.6, 8); // Dicker und höher
    const stem = new THREE.Mesh(stemGeometry, bodyMaterial);
    stem.position.set(0.15, 0.5, 0); // Höher wegen größerem Body
    group.add(stem);

    // MEGA Notenfähnchen - ITALIAN STYLE
    const flagGeometry = new THREE.BoxGeometry(0.25, 0.1, 0.1); // Größer
    const flagMaterial = new THREE.MeshPhongMaterial({
        color: 0x8B0000, // Italienisches Rot
        shininess: 30
    });
    const flag = new THREE.Mesh(flagGeometry, flagMaterial);
    flag.position.set(0.3, 0.75, 0);
    group.add(flag);

    // ITALIENISCHE MINI-FLAGGE auf dem Fähnchen
    const miniFlag = new THREE.Mesh(
        new THREE.PlaneGeometry(0.08, 0.05),
        new THREE.MeshBasicMaterial({
            color: 0x00AA00, // Grün
            side: THREE.DoubleSide
        })
    );
    miniFlag.position.set(0.35, 0.75, 0.05);
    group.add(miniFlag);

    // GROSSER träumerischer Kopf
    const headGeometry = new THREE.SphereGeometry(0.25, 16, 16); // Größer
    const headMaterial = new THREE.MeshPhongMaterial({
        color: 0xFFEFD5, // Pastellfarbe
        shininess: 20
    });
    const head = new THREE.Mesh(headGeometry, headMaterial);
    head.position.y = 0.7; // Angepasst an niedrigere Basis
    group.add(head);

    // RIESIGE träumerische Augen - BRAIN ROT
    for (let i = 0; i < 2; i++) {
        const eye = new THREE.Mesh(
            new THREE.SphereGeometry(0.06, 12, 12), // Größer
            new THREE.MeshPhongMaterial({
                color: 0xFFFFFF,
                shininess: 80
            })
        );
        eye.position.set(i === 0 ? 0.1 : -0.1, 0.75, 0.18);
        eye.scale.set(1.2, 1.8, 1); // Noch ovaler und träumerischer
        group.add(eye);

        // MASSIVE blaue Pupillen
        const pupil = new THREE.Mesh(
            new THREE.SphereGeometry(0.035, 8, 8), // Größer
            new THREE.MeshPhongMaterial({ color: 0x6495ED })
        );
        pupil.position.set(i === 0 ? 0.1 : -0.1, 0.78, 0.22);
        group.add(pupil);

        // ÜBERTRIEBENER Glanzpunkt
        const highlight = new THREE.Mesh(
            new THREE.SphereGeometry(0.015, 6, 6), // Größer
            new THREE.MeshPhongMaterial({ color: 0xFFFFFF })
        );
        highlight.position.set(i === 0 ? 0.11 : -0.09, 0.82, 0.23);
        group.add(highlight);
    }

    // ITALIENISCHER singender Mund - O SOLE MIO
    const mouthGeometry = new THREE.SphereGeometry(0.05, 8, 8);
    const mouthMaterial = new THREE.MeshPhongMaterial({
        color: 0xFFA07A,
        shininess: 30
    });
    const mouth = new THREE.Mesh(mouthGeometry, mouthMaterial);
    mouth.scale.set(1.2, 1, 1);
    mouth.position.set(0, 0.63, 0.2);
    group.add(mouth);

    // MUSIKNOTEN schweben um den Charakter - ITALIAN OPERA NOTES
    const notesGroup = new THREE.Group();
    const italianNoteColors = [0x8B0000, 0x00AA00, 0xFFFFFF]; // Italienische Flaggenfarben
    
    for (let i = 0; i < 8; i++) { // Mehr Noten
        const noteItemGroup = new THREE.Group();
        const noteHead = new THREE.Mesh(
            new THREE.SphereGeometry(0.05, 8, 8), // Größer
            new THREE.MeshBasicMaterial({
                color: italianNoteColors[i % 3],
                transparent: true,
                opacity: 0.9
            })
        );
        noteItemGroup.add(noteHead);

        const noteStick = new THREE.Mesh(
            new THREE.CylinderGeometry(0.012, 0.012, 0.12, 4),
            noteHead.material
        );
        noteStick.position.set(0.05, 0.06, 0);
        noteStick.rotation.z = -0.3;
        noteItemGroup.add(noteStick);

        const angle = (i / 8) * Math.PI * 2;
        const radius = 0.5 + Math.random() * 0.3; // Größerer Radius
        noteItemGroup.position.set(
            Math.cos(angle) * radius,
            0.7 + Math.random() * 0.5,
            Math.sin(angle) * radius
        );
        notesGroup.add(noteItemGroup);
    }
    group.add(notesGroup);

    // DICKERE Arme und Beine
    const limbGeometry = new THREE.CylinderGeometry(0.04, 0.04, 0.3, 8); // Dicker
    const limbMaterial = new THREE.MeshPhongMaterial({
        color: 0xFFEFD5,
        shininess: 20
    });

    // ITALIAN GESTURE Arme
    for (let i = 0; i < 2; i++) {
        const arm = new THREE.Mesh(limbGeometry, limbMaterial);
        arm.position.set(i === 0 ? 0.2 : -0.2, 0.4, 0); // Niedriger
        arm.rotation.z = i === 0 ? -Math.PI / 3 : Math.PI / 3; // Italienische Gesten
        group.add(arm);
    }

    // Beine - RICHTIG AUF DEM BODEN
    for (let i = 0; i < 2; i++) {
        const leg = new THREE.Mesh(limbGeometry, limbMaterial);
        leg.position.set(i === 0 ? 0.08 : -0.08, 0.05, 0); // AUF DEM BODEN wie Bombardino
        group.add(leg);
    }

    // ITALIENISCHE SCHUHE - AUF DEM BODEN
    for (let i = 0; i < 2; i++) {
        const shoe = new THREE.Mesh(
            new THREE.SphereGeometry(0.04, 8, 8),
            new THREE.MeshPhongMaterial({
                color: 0x8B4513,
                shininess: 40
            })
        );
        shoe.scale.set(1.5, 0.6, 2);
        shoe.position.set(i === 0 ? 0.08 : -0.08, -0.08, 0.04); // AUF DEM BODEN
        group.add(shoe);
    }

    // VERRÜCKTE Sterne und Glitzern - ITALIAN MAGIC
    const starsGroup = new THREE.Group();
    for (let i = 0; i < 15; i++) { // Mehr Sterne
        const star = new THREE.Mesh(
            new THREE.OctahedronGeometry(0.025 + Math.random() * 0.025, 0),
            new THREE.MeshPhongMaterial({
                color: italianNoteColors[i % 3],
                emissive: 0xFFFF99,
                emissiveIntensity: 0.6,
                transparent: true,
                opacity: 0.9
            })
        );
        const angle = Math.random() * Math.PI * 2;
        const radius = 0.4 + Math.random() * 0.5;
        const height = 0.5 + Math.random() * 0.6;
        star.position.set(
            Math.cos(angle) * radius,
            height,
            Math.sin(angle) * radius
        );
        starsGroup.add(star);
    }
    group.add(starsGroup);

    // ITALIENISCHER CHEF HAT
    const hatBase = new THREE.Mesh(
        new THREE.CylinderGeometry(0.12, 0.12, 0.02, 16),
        new THREE.MeshPhongMaterial({ color: 0xFFFFFF })
    );
    hatBase.position.set(0, 0.92, 0);
    group.add(hatBase);

    const hatTop = new THREE.Mesh(
        new THREE.CylinderGeometry(0.08, 0.1, 0.12, 16),
        hatBase.material
    );
    hatTop.position.set(0, 1.02, 0);
    group.add(hatTop);

    group.userData = {
        animation: time => {
            group.position.y = Math.sin(time * 2) * 0.08; // Mehr Schweben
            
            if(head) {
                head.rotation.y = Math.sin(time * 1.5) * 0.3; // Mehr Kopfbewegung
                head.rotation.z = Math.sin(time * 0.8) * 0.15;
            }
            
            if (mouth) {
                mouth.scale.y = 0.7 + Math.abs(Math.sin(time * 6)) * 0.6; // Schnelleres Singen
                mouth.scale.x = 1.2 + Math.sin(time * 6) * 0.2;
            }

            // WILD FLOATING NOTES
            if(notesGroup) {
                notesGroup.rotation.y = time * 0.3; // Langsamer
                notesGroup.children.forEach((noteItem, i) => {
                    noteItem.position.y += Math.sin(time * 2 + i) * 0.004;
                    noteItem.rotation.y = time * 1.5;
                    noteItem.position.x += Math.sin(time * 1.2 + i) * 0.003;
                    noteItem.position.z += Math.cos(time * 1.2 + i) * 0.003;
                    noteItem.children.forEach(part => {
                        if (part.material) part.material.opacity = 0.6 + Math.sin(time * 2 + i) * 0.3;
                    });
                });
            }

            // CRAZY STARS
            if(starsGroup) {
                starsGroup.children.forEach((star, i) => {
                    star.rotation.y = time * (0.5 + i * 0.1);
                    star.rotation.x = time * (0.3 + i * 0.05);
                    if(star.material) star.material.emissiveIntensity = 0.4 + Math.sin(time * 4 + i) * 0.3;
                });
            }

            // ITALIAN ARMS GESTURING
            let armCount = 0;
            group.children.forEach((child) => {
                if (child.geometry && child.geometry.type === 'CylinderGeometry' &&
                    child.geometry.parameters && child.geometry.parameters.height === 0.3 && armCount < 2) {
                    const direction = armCount % 2 === 0 ? 1 : -1;
                    child.rotation.z = direction * Math.PI / 3 + Math.sin(time * 3 + armCount * Math.PI) * 0.4;
                    child.rotation.x = Math.sin(time * 2 + armCount) * 0.3;
                    armCount++;
                }
            });

            // CHEF HAT WOBBLE
            if (hatTop) {
                hatTop.rotation.z = Math.sin(time * 3) * 0.1;
            }
        }
    };
    return group;
}