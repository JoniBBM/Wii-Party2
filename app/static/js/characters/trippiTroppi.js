function createTrippiTroppi(colorHex) {
    const group = new THREE.Group();
    const color = parseInt(colorHex.replace('#', '0x'), 16);

    // MASSIVER Körper - BRAIN ROT ITALIAN BEACH STYLE
    const bodyGeometry = new THREE.SphereGeometry(0.25, 16, 16); // Größer
    const bodyMaterial = new THREE.MeshPhongMaterial({
        color: color,
        shininess: 40
    });
    const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
    body.position.y = 0.2; // NIEDRIGER wie Bombardino
    body.scale.set(1.2, 0.8, 1.2); // Breiter
    group.add(body);

    // GRÖßERER Kopf - BRAIN ROT SIZE
    const headGeometry = new THREE.SphereGeometry(0.2, 16, 16); // Größer
    const headMaterial = new THREE.MeshPhongMaterial({
        color: 0xFFDFB0, // Sonnengebräunt
        shininess: 30
    });
    const head = new THREE.Mesh(headGeometry, headMaterial);
    head.position.y = 0.5; // Niedriger
    group.add(head);

    // RIESIGE AUGEN - BRAIN ROT GOOGLY EYES
    for (let i = 0; i < 2; i++) {
        const eye = new THREE.Mesh(
            new THREE.SphereGeometry(0.05, 10, 10), // Größer
            new THREE.MeshPhongMaterial({
                color: 0xFFFFFF,
                shininess: 80
            })
        );
        eye.position.set(i === 0 ? 0.09 : -0.09, 0.52, 0.15);
        eye.scale.set(1.2, 1.5, 1); // Ovaler
        group.add(eye);

        const pupil = new THREE.Mesh(
            new THREE.SphereGeometry(0.025, 8, 8), // Größer
            new THREE.MeshPhongMaterial({ color: 0x004D40 })
        );
        pupil.position.set(i === 0 ? 0.09 : -0.09, 0.52, 0.18);
        group.add(pupil);
    }

    // ÜBERTRIEBENES italienisches Lächeln
    const smileGeometry = new THREE.TorusGeometry(0.09, 0.02, 8, 16, Math.PI);
    const smile = new THREE.Mesh(
        smileGeometry,
        new THREE.MeshPhongMaterial({
            color: 0x8B0000, // Italienisches Rot
            shininess: 60
        })
    );
    smile.position.set(0, 0.43, 0.15);
    smile.rotation.x = Math.PI / 2;
    group.add(smile);

    // ITALIENISCHER SOMMERHUT - BRAIN ROT STYLE
    const hatGroup = new THREE.Group();
    const brimGeometry = new THREE.CylinderGeometry(0.35, 0.35, 0.025, 16); // Größer
    const brimMaterial = new THREE.MeshPhongMaterial({
        color: 0xF9E29C,
        shininess: 10
    });
    const brim = new THREE.Mesh(brimGeometry, brimMaterial);
    brim.position.y = 0.68; // Niedriger
    hatGroup.add(brim);

    const crownGeometry = new THREE.ConeGeometry(0.18, 0.1, 16);
    const crown = new THREE.Mesh(crownGeometry, brimMaterial);
    crown.position.y = 0.73;
    hatGroup.add(crown);

    // ITALIENISCHER Hutband
    const hatBandGeometry = new THREE.CylinderGeometry(0.185, 0.185, 0.04, 16);
    const hatBand = new THREE.Mesh(
        hatBandGeometry,
        new THREE.MeshPhongMaterial({
            color: 0x8B0000, // Italienisches Rot
            shininess: 30
        })
    );
    hatBand.position.y = 0.69;
    hatGroup.add(hatBand);

    // ITALIENISCHE FLAGGE am Hut
    const italianFlag = new THREE.Mesh(
        new THREE.PlaneGeometry(0.08, 0.06),
        new THREE.MeshBasicMaterial({
            color: 0x00AA00, // Grün
            side: THREE.DoubleSide
        })
    );
    italianFlag.position.set(0.2, 0.69, 0);
    hatGroup.add(italianFlag);

    const flagWhite = new THREE.Mesh(
        new THREE.PlaneGeometry(0.08, 0.06),
        new THREE.MeshBasicMaterial({
            color: 0xFFFFFF,
            side: THREE.DoubleSide
        })
    );
    flagWhite.position.set(0.25, 0.69, 0);
    hatGroup.add(flagWhite);

    const flagRed = new THREE.Mesh(
        new THREE.PlaneGeometry(0.08, 0.06),
        new THREE.MeshBasicMaterial({
            color: 0x8B0000,
            side: THREE.DoubleSide
        })
    );
    flagRed.position.set(0.3, 0.69, 0);
    hatGroup.add(flagRed);

    // MEGA ITALIENISCHE BLUME am Hut
    const flowerGroup = new THREE.Group();
    const italianFlowerColors = [0x8B0000, 0x00AA00, 0xFFFFFF]; // Italienische Flaggenfarben
    for (let i = 0; i < 6; i++) { // Mehr Blütenblätter
        const petal = new THREE.Mesh(
            new THREE.SphereGeometry(0.04, 8, 8), // Größer
            new THREE.MeshPhongMaterial({
                color: italianFlowerColors[i % 3],
                shininess: 70
            })
        );
        const angle = (i / 6) * Math.PI * 2;
        petal.position.set(
            Math.cos(angle) * 0.04,
            0,
            Math.sin(angle) * 0.04
        );
        petal.scale.set(0.8, 0.4, 0.8);
        flowerGroup.add(petal);
    }

    const flowerCenter = new THREE.Mesh(
        new THREE.SphereGeometry(0.025, 8, 8),
        new THREE.MeshPhongMaterial({
            color: 0xFFD54F,
            shininess: 80
        })
    );
    flowerGroup.add(flowerCenter);
    flowerGroup.position.set(0.18, 0.72, 0.08);
    hatGroup.add(flowerGroup);
    group.add(hatGroup);

    // ITALIENISCHE BADEHOSE
    const shortsGeometry = new THREE.CylinderGeometry(0.2, 0.2, 0.18, 12); // Größer
    const shortsMaterial = new THREE.MeshPhongMaterial({
        color: 0x8B0000, // Italienisches Rot
        shininess: 20
    });
    const shorts = new THREE.Mesh(shortsGeometry, shortsMaterial);
    shorts.position.y = 0.15; // Niedriger
    group.add(shorts);

    // ITALIENISCHE STREIFEN auf der Badehose
    for (let i = 0; i < 3; i++) {
        const stripe = new THREE.Mesh(
            new THREE.CylinderGeometry(0.205, 0.205, 0.02, 12),
            new THREE.MeshPhongMaterial({
                color: i % 2 === 0 ? 0xFFFFFF : 0x00AA00
            })
        );
        stripe.position.y = 0.1 + i * 0.04;
        group.add(stripe);
    }

    // DICKERE Beine und Arme
    const limbGeometry = new THREE.CylinderGeometry(0.04, 0.04, 0.18, 8); // Dicker
    const limbMaterial = new THREE.MeshPhongMaterial({
        color: 0xFFDFB0,
        shininess: 20
    });

    // Beine - RICHTIG AUF DEM BODEN
    for (let i = 0; i < 2; i++) {
        const leg = new THREE.Mesh(limbGeometry, limbMaterial);
        leg.position.set(i === 0 ? 0.06 : -0.06, 0.05, 0); // AUF DEM BODEN wie Bombardino
        group.add(leg);
    }

    // ITALIENISCHE SANDALEN - AUF DEM BODEN
    for (let i = 0; i < 2; i++) {
        const sandal = new THREE.Mesh(
            new THREE.BoxGeometry(0.08, 0.02, 0.15),
            new THREE.MeshPhongMaterial({
                color: 0x8B4513,
                shininess: 30
            })
        );
        sandal.position.set(i === 0 ? 0.06 : -0.06, -0.08, 0.02); // AUF DEM BODEN
        group.add(sandal);

        // Sandalen-Riemen
        const strap = new THREE.Mesh(
            new THREE.BoxGeometry(0.03, 0.01, 0.1),
            new THREE.MeshPhongMaterial({ color: 0x654321 })
        );
        strap.position.set(i === 0 ? 0.06 : -0.06, -0.07, 0.02);
        group.add(strap);
    }

    // ITALIAN GESTURE Arme
    for (let i = 0; i < 2; i++) {
        const arm = new THREE.Mesh(limbGeometry, limbMaterial);
        arm.position.set(i === 0 ? 0.18 : -0.18, 0.25, 0); // Niedriger
        arm.rotation.z = i === 0 ? -Math.PI / 4 : Math.PI / 4; // Italienische Gesten
        group.add(arm);
    }

    // PIZZA SLICE als Accessoire
    const pizzaGroup = new THREE.Group();
    const pizzaBase = new THREE.Mesh(
        new THREE.ConeGeometry(0.08, 0.15, 3),
        new THREE.MeshPhongMaterial({ color: 0xFFE4B5 }) // Pizza-Teig
    );
    pizzaBase.rotation.z = Math.PI;
    pizzaBase.position.set(0.25, 0.25, 0);
    pizzaGroup.add(pizzaBase);

    // Pizza Toppings
    const pepperoni = new THREE.Mesh(
        new THREE.SphereGeometry(0.015, 8, 8),
        new THREE.MeshPhongMaterial({ color: 0x8B0000 })
    );
    pepperoni.position.set(0.22, 0.3, 0.02);
    pizzaGroup.add(pepperoni);

    const cheese = new THREE.Mesh(
        new THREE.SphereGeometry(0.01, 6, 6),
        new THREE.MeshPhongMaterial({ color: 0xFFFF99 })
    );
    cheese.position.set(0.28, 0.22, -0.02);
    pizzaGroup.add(cheese);

    group.add(pizzaGroup);

    group.userData = {
        animation: time => {
            // ITALIAN BEACH PARTY BOUNCING
            const jumpOffset = Math.abs(Math.sin(time * 5)) * 0.1; // Mehr Hüpfen
            group.position.y = jumpOffset;

            if(body) body.rotation.y = Math.sin(time * 2.5) * 0.25; // Mehr Bewegung
            if(head) head.rotation.y = Math.sin(time * 2.5) * 0.25;

            if (smile) {
                smile.scale.x = 1 + Math.sin(time * 4) * 0.3; // Größeres Lächeln
                smile.scale.y = 1 + Math.cos(time * 4) * 0.15;
            }

            // MEGA FLOWER SPINNING
            if (flowerGroup) {
                flowerGroup.rotation.y = time * 1.5; // Schneller
                flowerGroup.children.forEach((child, i) => {
                    if (i < 6 && child.rotation) {
                        child.rotation.z = Math.sin(time * 4 + i) * 0.3;
                        child.scale.setScalar(0.8 + Math.sin(time * 3 + i) * 0.2);
                    }
                });
            }

            // HAT WOBBLING
            if (hatGroup) {
                hatGroup.rotation.z = Math.sin(time * 3) * 0.1;
            }

            // ITALIAN ARMS GESTURING WILDLY
            let armCount = 0;
            group.children.forEach((child) => {
                if (child.geometry && child.geometry.type === 'CylinderGeometry' &&
                    child.geometry.parameters && child.geometry.parameters.height === 0.18 && armCount < 2) {
                    const direction = armCount % 2 === 0 ? 1 : -1;
                    child.rotation.z = direction * Math.PI / 4 + Math.sin(time * 4 + armCount * Math.PI) * 0.4;
                    child.rotation.x = Math.sin(time * 3 + armCount) * 0.3;
                    child.rotation.y = Math.sin(time * 2 + armCount) * 0.2;
                    armCount++;
                }
            });

            // PIZZA FLOATING
            if (pizzaGroup) {
                pizzaGroup.position.y = Math.sin(time * 4) * 0.02;
                pizzaGroup.rotation.z = Math.PI + Math.sin(time * 2) * 0.1;
            }

            // EYES GOING CRAZY
            group.children.forEach((child) => {
                if (child.geometry && child.geometry.type === 'SphereGeometry' &&
                    child.geometry.parameters && child.geometry.parameters.radius === 0.025) {
                    child.position.x += Math.sin(time * 10) * 0.005; // Pupils moving
                    child.position.y += Math.cos(time * 8) * 0.003;
                }
            });
        }
    };
    return group;
}