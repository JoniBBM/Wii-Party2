function createTungTungTungSahur(colorHex) {
    const group = new THREE.Group();

    // Braun-orangener wurstförmiger Körper - VIEL VERRÜCKTER und niedriger
    const bodyCore = new THREE.Mesh(
        new THREE.BoxGeometry(0.8, 0.4, 0.4), // Größer für mehr BRAIN ROT
        new THREE.MeshPhongMaterial({
            color: 0xA86B32, // Braun-orange
            shininess: 20
        })
    );
    bodyCore.position.y = 0.2; // NIEDRIGER! Wie Bombardino
    group.add(bodyCore);

    // Halbkugeln an den Enden - FETTER
    const endCapGeometry = new THREE.SphereGeometry(0.2, 12, 12); // Größer
    const leftCap = new THREE.Mesh(endCapGeometry, bodyCore.material);
    leftCap.position.set(-0.4, 0.2, 0);
    group.add(leftCap);

    const rightCap = new THREE.Mesh(endCapGeometry, bodyCore.material);
    rightCap.position.set(0.4, 0.2, 0);
    group.add(rightCap);

    // MASSIVER Kopf - BRAIN ROT STYLE
    const head = new THREE.Mesh(
        new THREE.SphereGeometry(0.28, 16, 16), // VIEL GRÖßER
        new THREE.MeshPhongMaterial({
            color: 0xA86B32,
            shininess: 20
        })
    );
    head.scale.set(1.3, 0.9, 1.1); // Breiter und flacher
    head.position.set(0.45, 0.2, 0); // Auf gleicher Höhe wie Körper
    group.add(head);

    // RIESIGE GOOGLY EYES - BRAIN ROT ESSENTIAL
    for (let i = 0; i < 2; i++) {
        // Schwarze Augenhöhlen - GRÖßER
        const eyeSocket = new THREE.Mesh(
            new THREE.CircleGeometry(0.12, 24), // Noch größer
            new THREE.MeshBasicMaterial({
                color: 0x000000,
                side: THREE.DoubleSide
            })
        );
        eyeSocket.position.set(0.48, i === 0 ? 0.32 : 0.08, 0.22);
        eyeSocket.rotation.y = Math.PI / 2;
        group.add(eyeSocket);

        // Weiße Augäpfel - RIESIG
        const eye = new THREE.Mesh(
            new THREE.CircleGeometry(0.1, 24),
            new THREE.MeshBasicMaterial({
                color: 0xFFFFFF,
                side: THREE.DoubleSide
            })
        );
        eye.position.set(0.485, i === 0 ? 0.32 : 0.08, 0.225);
        eye.rotation.y = Math.PI / 2;
        group.add(eye);

        // Schwarze Pupillen - WILD
        const pupil = new THREE.Mesh(
            new THREE.CircleGeometry(0.05, 16),
            new THREE.MeshBasicMaterial({
                color: 0x000000,
                side: THREE.DoubleSide
            })
        );
        pupil.position.set(0.49, i === 0 ? 0.32 : 0.08, 0.23);
        pupil.rotation.y = Math.PI / 2;
        group.add(pupil);
    }

    // DICKER Mund - ITALIAN STYLE
    const mouth = new THREE.Mesh(
        new THREE.BoxGeometry(0.001, 0.06, 0.03), // Größer
        new THREE.MeshBasicMaterial({
            color: 0x000000
        })
    );
    mouth.position.set(0.48, 0.2, 0.22);
    group.add(mouth);

    // ITALIENISCHE SCHNURRBART
    const mustache = new THREE.Mesh(
        new THREE.TorusGeometry(0.08, 0.02, 8, 16, Math.PI),
        new THREE.MeshPhongMaterial({
            color: 0x2C1810 // Dunkelbraun
        })
    );
    mustache.position.set(0.48, 0.25, 0.22);
    mustache.rotation.x = Math.PI / 2;
    mustache.rotation.z = Math.PI;
    group.add(mustache);

    // DICKERE Arme
    for (let i = 0; i < 2; i++) {
        const arm = new THREE.Mesh(
            new THREE.CylinderGeometry(0.035, 0.035, 0.45, 8), // Dicker
            new THREE.MeshPhongMaterial({
                color: 0xA86B32
            })
        );
        arm.rotation.z = Math.PI / 2;
        arm.rotation.y = i === 0 ? -Math.PI/6 : Math.PI/6;
        arm.position.set(i === 0 ? 0.15 : -0.15, 0.2, 0); // Auf Körperhöhe
        group.add(arm);
    }

    // DICKERE Beine
    for (let i = 0; i < 2; i++) {
        const leg = new THREE.Mesh(
            new THREE.CylinderGeometry(0.035, 0.035, 0.4, 8), // Dicker
            new THREE.MeshPhongMaterial({
                color: 0xA86B32
            })
        );
        leg.position.set(i === 0 ? -0.1 : 0.1, -0.1, 0); // Niedriger
        leg.rotation.x = Math.PI/12;
        leg.rotation.z = i === 0 ? -Math.PI/12 : Math.PI/12;
        group.add(leg);
    }

    // MEGA BASEBALL BAT - BRAIN ROT SIZE
    const bat = new THREE.Mesh(
        new THREE.CylinderGeometry(0.04, 0.1, 1.0, 10), // MASSIVER
        new THREE.MeshPhongMaterial({
            color: 0x8B4513,
            shininess: 5
        })
    );
    bat.position.set(-0.6, 0.1, 0); // Niedriger
    bat.rotation.z = Math.PI / 2;
    bat.rotation.y = Math.PI / 8;
    group.add(bat);

    // GRÖßERE Füße
    for (let i = 0; i < 2; i++) {
        const foot = new THREE.Mesh(
            new THREE.SphereGeometry(0.05, 8, 8), // Größer
            new THREE.MeshPhongMaterial({
                color: 0x8B4513
            })
        );
        foot.scale.set(1.8, 0.6, 1.2); // Breitere Füße
        foot.position.set(i === 0 ? -0.1 : 0.1, -0.28, 0.04); // Niedriger
        group.add(foot);
    }

    // ITALIENISCHER HUT
    const hatBase = new THREE.Mesh(
        new THREE.CylinderGeometry(0.15, 0.15, 0.03, 16),
        new THREE.MeshPhongMaterial({
            color: 0x8B0000 // Italienisches Rot
        })
    );
    hatBase.position.set(0.45, 0.42, 0);
    group.add(hatBase);

    const hatTop = new THREE.Mesh(
        new THREE.CylinderGeometry(0.08, 0.12, 0.15, 16),
        hatBase.material
    );
    hatTop.position.set(0.45, 0.52, 0);
    group.add(hatTop);

    // Animation - MEHR BRAIN ROT BEWEGUNG
    group.userData = {
        animation: time => {
            // WAHNSINNIGE rhythmische Bewegung
            bodyCore.rotation.x = Math.sin(time * 6) * 0.15; // Schneller
            if(head) head.rotation.x = Math.sin(time * 6 + 0.5) * 0.15;

            // BAT SWINGING WILD
            if (bat) {
                bat.rotation.y = Math.PI / 8 + Math.sin(time * 12) * 0.4; // WILD swinging
            }

            // CRAZY LEG MOVEMENT
            group.children.forEach((child, index) => {
                if (child.geometry && child.geometry.type === 'CylinderGeometry' &&
                    child.geometry.parameters && child.geometry.parameters.height === 0.4) {
                    child.rotation.x = Math.PI/12 + Math.sin(time * 8 + (index % 2)) * 0.2; // Schneller
                }
            });

            // EYES GOING CRAZY
            group.children.forEach((child) => {
                if (child.geometry && child.geometry.type === 'CircleGeometry' &&
                    child.geometry.parameters && child.geometry.parameters.radius === 0.05) {
                    child.rotation.z = Math.sin(time * 10) * 0.3; // Pupillen drehen sich
                }
            });

            // MUSTACHE WIGGLE
            if (mustache) {
                mustache.rotation.z = Math.PI + Math.sin(time * 8) * 0.1;
            }
        }
    };
    return group;
}