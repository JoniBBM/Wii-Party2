function createTralaleroTralala(colorHex) {
    const group = new THREE.Group();
    const sharkColor = 0x7E8A97; // Grau-Blau für den Hai
    const bellyColor = 0xFFFFFF;
    const sneakerColor = 0x8B0000; // ITALIENISCHES ROT für die Sneaker
    const white = 0xFFFFFF;

    // Materialien
    const sharkMaterial = new THREE.MeshPhongMaterial({ color: sharkColor, shininess: 30 });
    const bellyMaterial = new THREE.MeshPhongMaterial({ color: bellyColor, shininess: 20 });
    const sneakerMaterial = new THREE.MeshPhongMaterial({ color: sneakerColor, shininess: 40 });
    const whiteMaterial = new THREE.MeshPhongMaterial({ color: white, shininess: 20 });
    const eyeMaterial = new THREE.MeshBasicMaterial({ color: 0x000000 });

    // MASSIVER Körper - BRAIN ROT SHARK
    const body = new THREE.Mesh(
        new THREE.SphereGeometry(0.35, 16, 12), // Größer
        sharkMaterial
    );
    body.scale.set(2.0, 1.0, 1.2); // Noch länglicher
    body.rotation.z = Math.PI / 25; // Leicht nach vorne geneigt
    body.position.y = 0.2; // NIEDRIGER wie Bombardino
    group.add(body);

    // GRÖßERER Bauch
    const bellyMesh = new THREE.Mesh(
        new THREE.SphereGeometry(0.3, 16, 8),
        bellyMaterial
    );
    bellyMesh.scale.set(1.8, 0.7, 1.0);
    bellyMesh.position.y = -0.1;
    body.add(bellyMesh);

    // RIESIGE GOOGLY AUGEN - BRAIN ROT ESSENTIAL
    for (let i = 0; i < 2; i++) {
        const eye = new THREE.Mesh(new THREE.SphereGeometry(0.06, 8, 8), // Größer
            new THREE.MeshPhongMaterial({ color: 0xFFFFFF, shininess: 100 }));
        eye.position.set(0.5, 0.08, i === 0 ? 0.15 : -0.15); // Weiter vorne
        eye.scale.set(1, 1.5, 1); // Oval
        body.add(eye);

        // CRAZY PUPILS
        const pupil = new THREE.Mesh(new THREE.SphereGeometry(0.03, 8, 8), eyeMaterial);
        pupil.position.set(0.52, 0.1, i === 0 ? 0.15 : -0.15);
        body.add(pupil);
    }

    // SHARK GRIN mit ITALIENISCHEN ZÄHNEN
    const mouthGeometry = new THREE.CylinderGeometry(0.15, 0.1, 0.05, 16, 1, false);
    const mouth = new THREE.Mesh(mouthGeometry, 
        new THREE.MeshPhongMaterial({ color: 0x8B0000 })); // Italienisches Rot
    mouth.position.set(0.45, -0.05, 0);
    mouth.rotation.z = Math.PI / 2;
    body.add(mouth);

    // ITALIENISCHE ZÄHNE
    for (let i = 0; i < 6; i++) {
        const tooth = new THREE.Mesh(
            new THREE.ConeGeometry(0.02, 0.06, 4),
            whiteMaterial
        );
        tooth.position.set(0.48, -0.02, -0.08 + i * 0.03);
        tooth.rotation.z = Math.PI;
        body.add(tooth);
    }

    // GRÖßERE Rückenflosse
    const dorsalFin = new THREE.Mesh(
        new THREE.ConeGeometry(0.15, 0.3, 8),
        sharkMaterial
    );
    dorsalFin.position.set(-0.1, 0.3, 0);
    dorsalFin.rotation.x = -Math.PI / 12;
    body.add(dorsalFin);

    // MASSIVE Schwanzflosse
    const tailFinGroup = new THREE.Group();
    tailFinGroup.position.set(-0.7, 0, 0);
    body.add(tailFinGroup);

    const tailFinUpper = new THREE.Mesh(
        new THREE.BoxGeometry(0.4, 0.2, 0.06),
        sharkMaterial
    );
    tailFinUpper.rotation.z = -Math.PI / 4;
    tailFinUpper.position.y = 0.08;
    tailFinGroup.add(tailFinUpper);

    const tailFinLower = new THREE.Mesh(
        new THREE.BoxGeometry(0.3, 0.15, 0.06),
        sharkMaterial
    );
    tailFinLower.rotation.z = Math.PI / 3;
    tailFinLower.position.y = -0.05;
    tailFinGroup.add(tailFinLower);

    // ITALIENISCHE DESIGNER SNEAKER - BRAIN ROT STYLE
    const legPositions = [
        { x: 0.2, z: 0.12, side: 'left' },
        { x: 0.2, z: -0.12, side: 'right' }
    ];

    legPositions.forEach(config => {
        const legGroup = new THREE.Group();
        legGroup.position.set(config.x, -0.1, config.z); // WENIGER TIEF - näher am Boden
        body.add(legGroup);

        const leg = new THREE.Mesh(
            new THREE.CylinderGeometry(0.06, 0.05, 0.15, 8), // Kürzer für bessere Positionierung
            sharkMaterial
        );
        leg.position.y = -0.05;
        legGroup.add(leg);

        // MEGA ITALIENISCHE SNEAKER - AUF DEM BODEN
        const sneaker = new THREE.Mesh(
            new THREE.BoxGeometry(0.15, 0.12, 0.28), // Größer
            sneakerMaterial
        );
        sneaker.position.y = -0.12; // Weniger tief
        leg.add(sneaker);

        // WEIßE SOHLE
        const sole = new THREE.Mesh(
            new THREE.BoxGeometry(0.16, 0.04, 0.3),
            whiteMaterial
        );
        sole.position.y = -0.08;
        sneaker.add(sole);

        // ITALIENISCHER SWOOSH - ÜBERTRIEBEN
        const swoosh = new THREE.Mesh(
            new THREE.BoxGeometry(0.02, 0.04, 0.15),
            whiteMaterial
        );
        swoosh.position.set(config.side === 'left' ? -0.06 : 0.06, 0.02, 0);
        swoosh.rotation.y = Math.PI / 2;
        swoosh.rotation.z = config.side === 'left' ? Math.PI/4 : -Math.PI/4;
        sneaker.add(swoosh);

        // ITALIENISCHE FLAGGE auf dem Sneaker
        const flagStripe1 = new THREE.Mesh(
            new THREE.PlaneGeometry(0.03, 0.08),
            new THREE.MeshBasicMaterial({ color: 0x00AA00, side: THREE.DoubleSide }) // Grün
        );
        flagStripe1.position.set(0, 0.04, 0.14);
        sneaker.add(flagStripe1);

        const flagStripe2 = new THREE.Mesh(
            new THREE.PlaneGeometry(0.03, 0.08),
            new THREE.MeshBasicMaterial({ color: 0xFFFFFF, side: THREE.DoubleSide }) // Weiß
        );
        flagStripe2.position.set(0, 0.04, 0.11);
        sneaker.add(flagStripe2);

        const flagStripe3 = new THREE.Mesh(
            new THREE.PlaneGeometry(0.03, 0.08),
            new THREE.MeshBasicMaterial({ color: 0x8B0000, side: THREE.DoubleSide }) // Rot
        );
        flagStripe3.position.set(0, 0.04, 0.08);
        sneaker.add(flagStripe3);
    });

    // ITALIENISCHE CHEF MÜTZE
    const hatBase = new THREE.Mesh(
        new THREE.CylinderGeometry(0.18, 0.18, 0.03, 16),
        whiteMaterial
    );
    hatBase.position.set(0.35, 0.25, 0);
    body.add(hatBase);

    const hatTop = new THREE.Mesh(
        new THREE.CylinderGeometry(0.12, 0.15, 0.15, 16),
        whiteMaterial
    );
    hatTop.position.set(0.35, 0.35, 0);
    body.add(hatTop);

    // ITALIENISCHE SEITENFLOSSE als "ARME"
    for (let i = 0; i < 2; i++) {
        const sideFin = new THREE.Mesh(
            new THREE.BoxGeometry(0.25, 0.08, 0.15),
            sharkMaterial
        );
        sideFin.position.set(0.1, 0.05, i === 0 ? 0.25 : -0.25);
        sideFin.rotation.y = i === 0 ? Math.PI/6 : -Math.PI/6;
        sideFin.rotation.z = i === 0 ? -Math.PI/8 : Math.PI/8;
        body.add(sideFin);
    }

    // PASTA NOODLES um den Hai herum
    const pastaGroup = new THREE.Group();
    for (let i = 0; i < 5; i++) {
        const noodle = new THREE.Mesh(
            new THREE.TorusGeometry(0.05, 0.01, 8, 16),
            new THREE.MeshPhongMaterial({ color: 0xFFE4B5 }) // Pasta-Farbe
        );
        const angle = (i / 5) * Math.PI * 2;
        const radius = 0.6 + Math.random() * 0.2;
        noodle.position.set(
            Math.cos(angle) * radius,
            0.3 + Math.random() * 0.3,
            Math.sin(angle) * radius
        );
        noodle.rotation.x = Math.random() * Math.PI;
        noodle.rotation.y = Math.random() * Math.PI;
        pastaGroup.add(noodle);
    }
    group.add(pastaGroup);

    // Position anpassen - AUF GLEICHER HÖHE wie Bombardino

    group.userData = {
        animation: time => {
            // Entfernt: group.position.y = Math.abs(Math.sin(time * 4)) * 0.1;
            // Damit das Spielbrett die Y-Position kontrollieren kann
            body.rotation.y = Math.sin(time * 1.5) * 0.15; // Mehr Bewegung
            body.rotation.z = Math.PI / 25 + Math.sin(time * 2.5) * 0.08; // Mehr Wackeln

            // CRAZY BEINE MOVEMENT
            body.children.forEach(child => {
                if (child.type === 'Group' && child.position.y < -0.2) {
                    const sideFactor = child.position.z > 0 ? 1 : -1;
                    child.rotation.x = Math.sin(time * 6 + sideFactor * Math.PI/2) * 0.4; // Schneller
                    child.rotation.z = Math.sin(time * 4 + sideFactor) * 0.2;
                }
            });

            // SCHWANZFLOSSE WILD WAVING
            if (tailFinGroup) {
                tailFinGroup.rotation.y = Math.sin(time * 5) * 0.3;
            }

            // CHEF HAT WOBBLE
            if (hatTop) {
                hatTop.rotation.z = Math.sin(time * 4) * 0.1;
            }

            // PASTA FLOATING
            if (pastaGroup) {
                pastaGroup.rotation.y = time * 0.2;
                pastaGroup.children.forEach((noodle, i) => {
                    noodle.rotation.x += 0.02;
                    noodle.rotation.y += 0.015;
                    noodle.position.y += Math.sin(time * 3 + i) * 0.002;
                });
            }

            // EYES ROLLING
            body.children.forEach((child) => {
                if (child.geometry && child.geometry.type === 'SphereGeometry' &&
                    child.geometry.parameters && child.geometry.parameters.radius === 0.03) {
                    child.position.x += Math.sin(time * 8) * 0.01;
                    child.position.y += Math.cos(time * 6) * 0.005;
                }
            });
        }
    };
    return group;
}