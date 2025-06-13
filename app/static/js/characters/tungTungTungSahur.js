function createTungTungTungSahur(colorHex) {
    const group = new THREE.Group();

    // Holzfarbe - natürliches Braun
    const woodColor = 0xD2691E; // Saddlebrown
    const woodMaterial = new THREE.MeshPhongMaterial({
        color: woodColor,
        shininess: 10,
        specular: 0x111111
    });

    // Hauptkörper - rechteckiger Holzklotz wie eine Holzpuppe
    const body = new THREE.Mesh(
        new THREE.BoxGeometry(0.4, 0.8, 0.25),
        woodMaterial
    );
    body.position.y = 0;
    group.add(body);

    // Kopf - rechteckiger Holzklotz
    const head = new THREE.Mesh(
        new THREE.BoxGeometry(0.35, 0.4, 0.3),
        woodMaterial
    );
    head.position.set(0, 0.6, 0);
    group.add(head);

    // RIESIGE GOOGLY EYES wie im Bild
    const eyePositions = [
        { x: -0.08, y: 0.65, z: 0.16 },
        { x: 0.08, y: 0.65, z: 0.16 }
    ];

    eyePositions.forEach(pos => {
        // Schwarzer Augenrand
        const eyeSocket = new THREE.Mesh(
            new THREE.CircleGeometry(0.08, 24),
            new THREE.MeshBasicMaterial({
                color: 0x000000,
                side: THREE.DoubleSide
            })
        );
        eyeSocket.position.set(pos.x, pos.y, pos.z);
        group.add(eyeSocket);

        // Weißer Augapfel
        const eye = new THREE.Mesh(
            new THREE.CircleGeometry(0.07, 24),
            new THREE.MeshBasicMaterial({
                color: 0xFFFFFF,
                side: THREE.DoubleSide
            })
        );
        eye.position.set(pos.x, pos.y, pos.z + 0.001);
        group.add(eye);

        // Schwarze Pupille
        const pupil = new THREE.Mesh(
            new THREE.CircleGeometry(0.03, 16),
            new THREE.MeshBasicMaterial({
                color: 0x000000,
                side: THREE.DoubleSide
            })
        );
        pupil.position.set(pos.x, pos.y, pos.z + 0.002);
        group.add(pupil);
    });

    // Einfacher schwarzer Mund
    const mouth = new THREE.Mesh(
        new THREE.BoxGeometry(0.001, 0.04, 0.08),
        new THREE.MeshBasicMaterial({
            color: 0x000000
        })
    );
    mouth.position.set(0, 0.52, 0.16);
    group.add(mouth);

    // Arme - einfache Holzstäbe
    for (let i = 0; i < 2; i++) {
        const arm = new THREE.Mesh(
            new THREE.CylinderGeometry(0.03, 0.03, 0.5, 8),
            woodMaterial
        );
        arm.rotation.z = Math.PI / 2;
        arm.position.set(i === 0 ? -0.35 : 0.35, 0.2, 0);
        group.add(arm);
    }

    // Beine - einfache Holzstäbe
    for (let i = 0; i < 2; i++) {
        const leg = new THREE.Mesh(
            new THREE.CylinderGeometry(0.04, 0.04, 0.6, 8),
            woodMaterial
        );
        leg.position.set(i === 0 ? -0.1 : 0.1, -0.7, 0);
        group.add(leg);
    }

    // Baseball-Schläger - prominenter wie im Original
    const batHandle = new THREE.Mesh(
        new THREE.CylinderGeometry(0.02, 0.02, 0.4, 12),
        new THREE.MeshPhongMaterial({
            color: 0x8B4513,
            shininess: 20
        })
    );
    batHandle.position.set(-0.6, 0.3, 0);
    batHandle.rotation.z = Math.PI / 6;
    group.add(batHandle);

    const batHead = new THREE.Mesh(
        new THREE.CylinderGeometry(0.06, 0.04, 0.3, 12),
        batHandle.material
    );
    batHead.position.set(-0.8, 0.55, 0);
    batHead.rotation.z = Math.PI / 6;
    group.add(batHead);

    // Einfache Füße
    for (let i = 0; i < 2; i++) {
        const foot = new THREE.Mesh(
            new THREE.BoxGeometry(0.12, 0.06, 0.2),
            woodMaterial
        );
        foot.position.set(i === 0 ? -0.1 : 0.1, -1.03, 0.05);
        group.add(foot);
    }

    // Animation - einfacher und charakteristischer
    group.userData = {
        animation: time => {
            // Leichtes Wippen des ganzen Körpers
            group.rotation.y = Math.sin(time * 2) * 0.05;
            
            // Googly Eyes bewegen sich verrückt
            group.children.forEach((child, index) => {
                if (child.geometry && child.geometry.type === 'CircleGeometry' &&
                    child.geometry.parameters && child.geometry.parameters.radius === 0.03) {
                    // Pupillen bewegen sich wild
                    const baseX = eyePositions[index < 2 ? 0 : 1].x;
                    child.position.x = baseX + Math.sin(time * 8 + index) * 0.02;
                    child.position.y = eyePositions[index < 2 ? 0 : 1].y + Math.cos(time * 6 + index) * 0.02;
                }
            });

            // Baseball-Schläger schwingt rhythmisch
            if (batHandle && batHead) {
                const swingAngle = Math.sin(time * 3) * 0.3;
                batHandle.rotation.z = Math.PI / 6 + swingAngle;
                batHead.rotation.z = Math.PI / 6 + swingAngle;
            }

            // Arme bewegen sich leicht
            group.children.forEach((child, index) => {
                if (child.geometry && child.geometry.type === 'CylinderGeometry' &&
                    child.geometry.parameters && Math.abs(child.geometry.parameters.height - 0.5) < 0.01) {
                    child.rotation.y = Math.sin(time * 2 + index) * 0.1;
                }
            });
        }
    };

    return group;
}