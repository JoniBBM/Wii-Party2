function createTungTungTungSahur(colorHex) {
    const group = new THREE.Group();

    // Braun-orangener wurstförmiger Körper (ohne CapsuleGeometry)
    // Besteht aus einer länglichen Box und zwei Sphären an den Enden
    const bodyCore = new THREE.Mesh(
        new THREE.BoxGeometry(0.7, 0.35, 0.35),
        new THREE.MeshPhongMaterial({
            color: 0xA86B32, // Braun-orange
            shininess: 20
        })
    );
    bodyCore.position.y = 0.35;
    group.add(bodyCore);

    // Halbkugeln an den Enden
    const endCapGeometry = new THREE.SphereGeometry(0.175, 12, 12);
    const leftCap = new THREE.Mesh(endCapGeometry, bodyCore.material);
    leftCap.position.set(-0.35, 0.35, 0);
    group.add(leftCap);

    const rightCap = new THREE.Mesh(endCapGeometry, bodyCore.material);
    rightCap.position.set(0.35, 0.35, 0);
    group.add(rightCap);

    // Großer, rundlicher Kopf
    const head = new THREE.Mesh(
        new THREE.SphereGeometry(0.24, 16, 16),
        new THREE.MeshPhongMaterial({
            color: 0xA86B32, // Gleiche Farbe wie Körper
            shininess: 20
        })
    );
    head.scale.set(1.1, 0.85, 0.9);
    head.position.set(0.4, 0.35, 0);
    group.add(head);

    // Weiße große Augen mit schwarzen Pupillen und Augenhöhlen
    for (let i = 0; i < 2; i++) {
        // Schwarze Augenhöhlen
        const eyeSocket = new THREE.Mesh(
            new THREE.CircleGeometry(0.09, 24),
            new THREE.MeshBasicMaterial({
                color: 0x000000,
                side: THREE.DoubleSide
            })
        );
        eyeSocket.position.set(0.42, i === 0 ? 0.42 : 0.28, 0.2);
        eyeSocket.rotation.y = Math.PI / 2;
        group.add(eyeSocket);

        // Weiße Augäpfel
        const eye = new THREE.Mesh(
            new THREE.CircleGeometry(0.07, 24),
            new THREE.MeshBasicMaterial({
                color: 0xFFFFFF,
                side: THREE.DoubleSide
            })
        );
        eye.position.set(0.421, i === 0 ? 0.42 : 0.28, 0.201);
        eye.rotation.y = Math.PI / 2;
        group.add(eye);

        // Schwarze Pupillen
        const pupil = new THREE.Mesh(
            new THREE.CircleGeometry(0.035, 16),
            new THREE.MeshBasicMaterial({
                color: 0x000000,
                side: THREE.DoubleSide
            })
        );
        pupil.position.set(0.422, i === 0 ? 0.42 : 0.28, 0.202);
        pupil.rotation.y = Math.PI / 2;
        group.add(pupil);
    }

    // Mund (einfache schwarze Linie)
    const mouth = new THREE.Mesh(
        new THREE.BoxGeometry(0.001, 0.04, 0.02),
        new THREE.MeshBasicMaterial({
            color: 0x000000
        })
    );
    mouth.position.set(0.42, 0.35, 0.2);
    group.add(mouth);

    // Extrem dünne Arme
    for (let i = 0; i < 2; i++) {
        const arm = new THREE.Mesh(
            new THREE.CylinderGeometry(0.025, 0.025, 0.4, 8),
            new THREE.MeshPhongMaterial({
                color: 0xA86B32
            })
        );
        arm.rotation.z = Math.PI / 2;
        arm.rotation.y = i === 0 ? -Math.PI/6 : Math.PI/6;
        arm.position.set(i === 0 ? 0.2 : -0.2, 0.35, 0);
        group.add(arm);
    }

    // Extrem dünne Beine
    for (let i = 0; i < 2; i++) {
        const leg = new THREE.Mesh(
            new THREE.CylinderGeometry(0.025, 0.025, 0.5, 8),
            new THREE.MeshPhongMaterial({
                color: 0xA86B32
            })
        );
        leg.position.set(i === 0 ? -0.15 : 0.15, -0.05, 0);
        leg.rotation.x = Math.PI/12;
        leg.rotation.z = i === 0 ? -Math.PI/12 : Math.PI/12;
        group.add(leg);
    }

    // Baseballschläger/Holzstock
    const bat = new THREE.Mesh(
        new THREE.CylinderGeometry(0.03, 0.08, 0.8, 10),
        new THREE.MeshPhongMaterial({
            color: 0x8B4513, // Dunkles Braun für Holz
            shininess: 5
        })
    );
    bat.position.set(-0.45, 0, 0);
    bat.rotation.z = Math.PI / 2;
    bat.rotation.y = Math.PI / 8;
    group.add(bat);

    // Füße (einfache ovale Formen)
    for (let i = 0; i < 2; i++) {
        const foot = new THREE.Mesh(
            new THREE.SphereGeometry(0.04, 8, 8),
            new THREE.MeshPhongMaterial({
                color: 0x8B4513
            })
        );
        foot.scale.set(1.5, 0.5, 1);
        foot.position.set(i === 0 ? -0.15 : 0.15, -0.3, 0.03);
        group.add(foot);
    }

    // Animation
    group.userData = {
        animation: time => {
            // Rhythmische Bewegung
            bodyCore.rotation.x = Math.sin(time * 4) * 0.1;
            if(head) head.rotation.x = Math.sin(time * 4 + 0.5) * 0.1; // head might not be direct child

            // Stock schwingt im Takt
            if (bat) {
                bat.rotation.y = Math.PI / 8 + Math.sin(time * 8) * 0.2;
            }

            // Beine bewegen sich rhythmisch
            group.children.forEach((child, index) => {
                if (child.geometry && child.geometry.type === 'CylinderGeometry' &&
                    child.geometry.parameters && child.geometry.parameters.height === 0.5) { // Check if parameters exist
                    child.rotation.x = Math.PI/12 + Math.sin(time * 4 + (index % 2)) * 0.1;
                }
            });
        }
    };
    return group;
}