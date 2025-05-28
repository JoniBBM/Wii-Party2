function createTralaleroTralala(colorHex) {
    const group = new THREE.Group();
    const sharkColor = 0x7E8A97; // Grau-Blau für den Hai
    const bellyColor = 0xFFFFFF;
    const sneakerColor = 0x4A90E2;
    const white = 0xFFFFFF;

    // Materialien
    const sharkMaterial = new THREE.MeshPhongMaterial({ color: sharkColor, shininess: 30 });
    const bellyMaterial = new THREE.MeshPhongMaterial({ color: bellyColor, shininess: 20 });
    const sneakerMaterial = new THREE.MeshPhongMaterial({ color: sneakerColor, shininess: 40 });
    const whiteMaterial = new THREE.MeshPhongMaterial({ color: white, shininess: 20 });
    const eyeMaterial = new THREE.MeshBasicMaterial({ color: 0x000000 });

    // Körper - Hauptform (etwas nach vorne geneigt)
    const body = new THREE.Mesh(
        new THREE.SphereGeometry(0.3, 16, 12), // radius, widthSegments, heightSegments
        sharkMaterial
    );
    body.scale.set(1.7, 0.9, 1); // Länglicher und etwas breiter
    body.rotation.z = Math.PI / 20; // Leicht nach vorne geneigt
    body.position.y = 0.3; // Grundposition des Körperschwerpunkts
    group.add(body);

    // Bauch
    const bellyMesh = new THREE.Mesh(
        new THREE.SphereGeometry(0.25, 16, 8),
        bellyMaterial
    );
    bellyMesh.scale.set(1.6, 0.6, 0.9);
    bellyMesh.position.y = -0.1; // Unter dem Körpermittelpunkt
    body.add(bellyMesh);

    // Kopfpartie - angedeutet durch Augenposition
    // Augen
    for (let i = 0; i < 2; i++) {
        const eye = new THREE.Mesh(new THREE.SphereGeometry(0.04, 8, 8), eyeMaterial);
        // Position relativ zur Vorderseite des Körpers
        eye.position.set(0.4, 0.05, i === 0 ? 0.12 : -0.12);
        body.add(eye);
    }

    // Rückenflosse
    const dorsalFin = new THREE.Mesh(
        new THREE.ConeGeometry(0.12, 0.25, 8), // radius, height, segments
        sharkMaterial
    );
    dorsalFin.position.set(0, 0.25, 0); // Oben auf dem Körper
    dorsalFin.rotation.x = -Math.PI / 12;
    body.add(dorsalFin);

    // Schwanzflosse
    const tailFinGroup = new THREE.Group();
    tailFinGroup.position.set(-0.5, 0, 0); // Am Ende des Körpers
    body.add(tailFinGroup);

    const tailFinUpper = new THREE.Mesh(
        new THREE.BoxGeometry(0.3, 0.15, 0.05), // Tiefe, Höhe, Breite (nach Drehung)
        sharkMaterial
    );
    tailFinUpper.rotation.z = -Math.PI / 4;
    tailFinUpper.position.y = 0.05;
    tailFinGroup.add(tailFinUpper);

    const tailFinLower = new THREE.Mesh(
        new THREE.BoxGeometry(0.25, 0.12, 0.05),
        sharkMaterial
    );
    tailFinLower.rotation.z = Math.PI / 3;
    tailFinLower.position.y = -0.04;
    tailFinGroup.add(tailFinLower);


    // Beine & Sneaker
    const legPositions = [
        { x: 0.15, z: 0.1, side: 'left' },
        { x: 0.15, z: -0.1, side: 'right' }
    ];

    legPositions.forEach(config => {
        const legGroup = new THREE.Group();
        legGroup.position.set(config.x, -0.2, config.z); // Unter dem Körper
        body.add(legGroup);

        const leg = new THREE.Mesh(
            new THREE.CylinderGeometry(0.05, 0.04, 0.25, 8),
            sharkMaterial
        );
        leg.position.y = -0.05; // Bein hängt leicht nach unten
        legGroup.add(leg);

        // Sneaker
        const sneaker = new THREE.Mesh(
            new THREE.BoxGeometry(0.12, 0.1, 0.22), // Breite, Höhe, Tiefe
            sneakerMaterial
        );
        sneaker.position.y = -0.16; // Am Ende des Beins
        leg.add(sneaker);

        const sole = new THREE.Mesh(
            new THREE.BoxGeometry(0.13, 0.03, 0.23),
            whiteMaterial
        );
        sole.position.y = -0.065; // Unter dem Sneaker
        sneaker.add(sole);

        // Weißer Streifen (Nike-Swoosh-Andeutung)
        const stripe = new THREE.Mesh(
            new THREE.BoxGeometry(0.015, 0.03, 0.1),
            whiteMaterial
        );
        stripe.position.set(config.side === 'left' ? -0.05 : 0.05, 0.01, 0); // Seitlich
        stripe.rotation.y = Math.PI / 2;
        stripe.rotation.z = config.side === 'left' ? Math.PI/6 : -Math.PI/6;
        sneaker.add(stripe);
    });

    // Gesamtposition der Gruppe anpassen, falls nötig, um auf dem Feld zu stehen
    group.position.y = 0.1; // Anheben, damit die Unterseite der Sneaker bei ca. y=0 ist

    group.userData = {
        animation: time => {
            group.position.y = 0.1 + Math.abs(Math.sin(time * 2.5)) * 0.04; // Hüpfen
            body.rotation.y = Math.sin(time * 0.8) * 0.1; // Leichte Drehung
            body.rotation.z = Math.PI / 20 + Math.sin(time * 1.5) * 0.05; // Wackeln

            // Beine bewegen (wenn sie an body hängen, relativ zu body)
             body.children.forEach(child => {
                if (child.type === 'Group' && child.position.y < -0.1) { // Annahme: legGroup
                    // Differenzierte Bewegung für linkes/rechtes Bein
                    const sideFactor = child.position.z > 0 ? 1 : -1;
                    child.rotation.x = Math.sin(time * 4 + sideFactor * Math.PI/2) * 0.3;
                }
            });
        }
    };
    return group;
}