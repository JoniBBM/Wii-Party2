function createTrippiTroppi(colorHex) {
    const group = new THREE.Group();
    const color = parseInt(colorHex.replace('#', '0x'), 16);

    // Körper
    const bodyGeometry = new THREE.SphereGeometry(0.2, 16, 16);
    const bodyMaterial = new THREE.MeshPhongMaterial({
        color: color, // Use provided color
        shininess: 40
    });
    const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
    body.position.y = 0.25; // Base slightly above ground
    body.scale.set(1, 0.7, 1); // Flattened sphere
    group.add(body);

    // Kopf
    const headGeometry = new THREE.SphereGeometry(0.15, 16, 16);
    const headMaterial = new THREE.MeshPhongMaterial({
        color: 0xFFDFB0, // Sonnengebräunt
        shininess: 30
    });
    const head = new THREE.Mesh(headGeometry, headMaterial);
    head.position.y = 0.5; // body.y + body.height (approx) + head.radius
    group.add(head);

    // Augen
    for (let i = 0; i < 2; i++) {
        const eye = new THREE.Mesh(
            new THREE.SphereGeometry(0.04, 10, 10),
            new THREE.MeshPhongMaterial({
                color: 0xFFFFFF,
                shininess: 80
            })
        );
        eye.position.set(i === 0 ? 0.07 : -0.07, 0.52, 0.12); // On head, forward
        group.add(eye);

        const pupil = new THREE.Mesh(
            new THREE.SphereGeometry(0.02, 8, 8),
            new THREE.MeshPhongMaterial({ color: 0x004D40 }) // Dark teal
        );
        pupil.position.set(i === 0 ? 0.07 : -0.07, 0.52, 0.15); // On eye, forward
        group.add(pupil);
    }

    // Lächeln
    const smileGeometry = new THREE.TorusGeometry(0.07, 0.015, 8, 16, Math.PI); // Semi-circle
    const smile = new THREE.Mesh(
        smileGeometry,
        new THREE.MeshPhongMaterial({
            color: 0xFF3D00, // Bright red/orange
            shininess: 60
        })
    );
    smile.position.set(0, 0.45, 0.12); // On head, below eyes
    smile.rotation.x = Math.PI / 2; // Align with face
    group.add(smile);

    // Tropischer Hut
    const hatGroup = new THREE.Group();
    const brimGeometry = new THREE.CylinderGeometry(0.25, 0.25, 0.02, 16); // Wide brim
    const brimMaterial = new THREE.MeshPhongMaterial({
        color: 0xF9E29C, // Strohfarbe
        shininess: 10
    });
    const brim = new THREE.Mesh(brimGeometry, brimMaterial);
    brim.position.y = 0.63; // On top of head
    hatGroup.add(brim);

    const crownGeometry = new THREE.ConeGeometry(0.15, 0.08, 16); // Low cone
    const crown = new THREE.Mesh(crownGeometry, brimMaterial); // Same material as brim
    crown.position.y = 0.63 + 0.02/2 + 0.08/2; // Stacked on brim
    hatGroup.add(crown);

    // Band (using a thin cylinder now, torus was too thick)
    const hatBandGeometry = new THREE.CylinderGeometry(0.155, 0.155, 0.03, 16);
    const hatBand = new THREE.Mesh( // Renamed variable
        hatBandGeometry,
        new THREE.MeshPhongMaterial({
            color: new THREE.Color(color).multiplyScalar(0.7), // Darker shade of body color
            shininess: 30
        })
    );
    hatBand.position.y = 0.63 + 0.02/2 + 0.01; // Around base of crown
    hatGroup.add(hatBand);


    // Blume am Hut
    const flowerGroup = new THREE.Group();
    const petalColors = [0xFF4081, 0xFFEB3B, 0x00BCD4, 0x76FF03];
    for (let i = 0; i < 5; i++) {
        const petal = new THREE.Mesh(
            new THREE.SphereGeometry(0.03, 8, 8),
            new THREE.MeshPhongMaterial({
                color: petalColors[i % petalColors.length],
                shininess: 70
            })
        );
        const angle = (i / 5) * Math.PI * 2;
        petal.position.set(
            Math.cos(angle) * 0.03, // Relative to flower center
            0,
            Math.sin(angle) * 0.03
        );
        petal.scale.set(0.6, 0.3, 0.6); // Flattened petals
        flowerGroup.add(petal);
    }

    const flowerCenter = new THREE.Mesh(
        new THREE.SphereGeometry(0.02, 8, 8),
        new THREE.MeshPhongMaterial({
            color: 0xFFD54F, // Yellowish center
            shininess: 80
        })
    );
    flowerGroup.add(flowerCenter); // Add center to flower group
    flowerGroup.position.set(0.15, 0.67, 0.05); // Position flower on hat band, slightly forward
    hatGroup.add(flowerGroup);
    group.add(hatGroup);


    // Shorts
    const shortsGeometry = new THREE.CylinderGeometry(0.16, 0.16, 0.15, 12); // Adjusted size
    const shortsMaterial = new THREE.MeshPhongMaterial({
        color: 0x00B8D4, // Türkis
        shininess: 20
    });
    const shorts = new THREE.Mesh(shortsGeometry, shortsMaterial);
    shorts.position.y = 0.17; // Covering lower part of body
    group.add(shorts);


    // Beine und Arme
    const limbGeometry = new THREE.CylinderGeometry(0.03, 0.03, 0.15, 8);
    const limbMaterial = new THREE.MeshPhongMaterial({
        color: 0xFFDFB0, // Wie Kopf
        shininess: 20
    });

    // Beine
    for (let i = 0; i < 2; i++) {
        const leg = new THREE.Mesh(limbGeometry, limbMaterial);
        leg.position.set(i === 0 ? 0.05 : -0.05, 0.05, 0); // From bottom of shorts
        group.add(leg);
    }

    // Arme
    for (let i = 0; i < 2; i++) {
        const arm = new THREE.Mesh(limbGeometry, limbMaterial);
        arm.position.set(i === 0 ? 0.15 : -0.15, 0.3, 0); // From sides of body
        arm.rotation.z = i === 0 ? -Math.PI / 6 : Math.PI / 6; // Angled
        group.add(arm);
    }


    group.userData = {
        animation: time => {
            // Hüpfende Animation applied to the main group
            const jumpOffset = Math.abs(Math.sin(time * 3)) * 0.05;
            group.position.y = jumpOffset; // Move the whole character up and down

            if(body) body.rotation.y = Math.sin(time * 1.5) * 0.2;
            if(head) head.rotation.y = Math.sin(time * 1.5) * 0.2; // Sync head rotation

            if (smile) {
                smile.scale.x = 1 + Math.sin(time * 2) * 0.2;
            }
            if (flowerGroup) {
                flowerGroup.rotation.y = time * 0.5;
                flowerGroup.children.forEach((child, i) => {
                    if (i < 5 && child.rotation) { // Petals
                        child.rotation.z = Math.sin(time * 2 + i) * 0.2;
                    }
                });
            }
        }
    };
    return group;
}