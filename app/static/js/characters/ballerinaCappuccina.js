function createBallerinaCappuccina(colorHex) {
    const group = new THREE.Group();
    const color = parseInt(colorHex.replace('#', '0x'), 16);

    // Ballerina-Tutu (Röckchen)
    const tutuGeometry = new THREE.CylinderGeometry(0.4, 0.6, 0.15, 16);
    const tutuMaterial = new THREE.MeshPhongMaterial({
        color: color,
        shininess: 30,
        transparent: true,
        opacity: 0.9
    });
    const tutu = new THREE.Mesh(tutuGeometry, tutuMaterial);
    tutu.position.y = 0.3;
    group.add(tutu);

    // Oberkörper (Tasse)
    const cupGeometry = new THREE.CylinderGeometry(0.25, 0.2, 0.4, 16);
    const cupMaterial = new THREE.MeshPhongMaterial({
        color: 0xF5F5DC, // Cremeweiß
        shininess: 50
    });
    const cup = new THREE.Mesh(cupGeometry, cupMaterial);
    cup.position.y = 0.6;
    group.add(cup);

    // Griff der Tasse
    const handleGeometry = new THREE.TorusGeometry(0.12, 0.03, 8, 16, Math.PI);
    const handle = new THREE.Mesh(handleGeometry, cupMaterial);
    handle.position.set(0, 0.6, -0.2);
    handle.rotation.x = Math.PI / 2;
    group.add(handle);

    // Cappuccino-Schaum oben
    const foamGeometry = new THREE.SphereGeometry(0.25, 16, 16);
    const foamMaterial = new THREE.MeshPhongMaterial({
        color: 0xFFFFEE,
        shininess: 20
    });
    const foam = new THREE.Mesh(foamGeometry, foamMaterial);
    foam.scale.set(1, 0.3, 1);
    foam.position.y = 0.85;
    group.add(foam);

    // Cappuccino-Muster (Tulpen-Design)
    const patternGeometry = new THREE.CircleGeometry(0.15, 16);
    const patternMaterial = new THREE.MeshBasicMaterial({
        color: 0x8B4513,
        side: THREE.DoubleSide
    });
    const pattern = new THREE.Mesh(patternGeometry, patternMaterial);
    pattern.position.set(0, 0.86, 0);
    pattern.rotation.x = -Math.PI / 2;
    group.add(pattern);

    // Gesicht (auf der Tasse)
    // Augen
    for (let i = 0; i < 2; i++) {
        const eye = new THREE.Mesh(
            new THREE.SphereGeometry(0.03, 8, 8),
            new THREE.MeshBasicMaterial({ color: 0x000000 })
        );
        eye.position.set(i === 0 ? 0.08 : -0.08, 0.65, 0.2);
        group.add(eye);
    }

    // Lächelnder Mund
    const smile = new THREE.Mesh(
        new THREE.TorusGeometry(0.06, 0.01, 8, 16, Math.PI),
        new THREE.MeshBasicMaterial({ color: 0x000000 })
    );
    smile.position.set(0, 0.55, 0.2);
    smile.rotation.x = Math.PI / 2;
    group.add(smile);

    // Ballerina-Beine
    const legGeometry = new THREE.CylinderGeometry(0.03, 0.03, 0.4, 8);
    const legMaterial = new THREE.MeshPhongMaterial({
        color: 0xFFDFBA, // Hautfarbe
        shininess: 20
    });

    // Beine im Tanzpose
    const leftLeg = new THREE.Mesh(legGeometry, legMaterial);
    leftLeg.position.set(0.1, 0.05, 0);
    leftLeg.rotation.z = Math.PI / 12;
    group.add(leftLeg);

    const rightLeg = new THREE.Mesh(legGeometry, legMaterial);
    rightLeg.position.set(-0.1, 0.05, 0);
    rightLeg.rotation.z = -Math.PI / 6;
    rightLeg.rotation.x = Math.PI / 4;
    group.add(rightLeg);

    // Ballerina-Schuhe
    for (let i = 0; i < 2; i++) {
        const shoe = new THREE.Mesh(
            new THREE.SphereGeometry(0.04, 8, 8),
            new THREE.MeshPhongMaterial({
                color: color,
                shininess: 40
            })
        );
        shoe.scale.set(1.2, 0.6, 2);

        if (i === 0) { // Linker Schuh
            shoe.position.set(0.1, -0.15, 0.05);
        } else { // Rechter Schuh
            shoe.position.set(-0.18, -0.05, 0.1);
            shoe.rotation.x = Math.PI / 4;
        }
        group.add(shoe);
    }

    // Arme in Tanzposition
    for (let i = 0; i < 2; i++) {
        const arm = new THREE.Mesh(
            new THREE.CylinderGeometry(0.03, 0.02, 0.3, 8),
            legMaterial
        );

        if (i === 0) { // Linker Arm
            arm.position.set(0.25, 0.65, 0);
            arm.rotation.z = -Math.PI / 3;
        } else { // Rechter Arm
            arm.position.set(-0.25, 0.65, 0);
            arm.rotation.z = Math.PI / 3;
        }
        group.add(arm);
    }

    // Animation
    group.userData = {
        animation: time => {
            // Drehbewegung wie beim Tanz
            group.rotation.y = Math.sin(time * 0.5) * 0.2;

            // Schweben und Wippen
            group.position.y = Math.sin(time * 2) * 0.05;

            // Tutu schwingt
            if (tutu) {
                tutu.scale.x = 1 + Math.sin(time * 2) * 0.05;
                tutu.scale.z = 1 + Math.sin(time * 2 + 0.5) * 0.05;
            }

            // Dampf vom Cappuccino
            if (Math.random() > 0.95) {
                const steamParticle = new THREE.Mesh(
                    new THREE.SphereGeometry(0.02 + Math.random() * 0.02, 6, 6),
                    new THREE.MeshBasicMaterial({
                        color: 0xFFFFFF,
                        transparent: true,
                        opacity: 0.5
                    })
                );

                steamParticle.position.set(
                    (Math.random() - 0.5) * 0.2,
                    0.9,
                    (Math.random() - 0.5) * 0.2
                );
                group.add(steamParticle); // Add to character group for local coordinates

                // Dampf-Animation
                let particleAge = 0;
                const animateSteam = () => {
                    particleAge += 0.05;

                    if (particleAge > 1 || !steamParticle.parent) { // Check if still part of the scene
                        if(steamParticle.parent) group.remove(steamParticle);
                        return;
                    }

                    steamParticle.position.y += 0.01;
                    steamParticle.material.opacity = 0.5 * (1 - particleAge);
                    requestAnimationFrame(animateSteam);
                };
                animateSteam();
            }

            // Beine bewegen im Tanzrhythmus
            if (leftLeg && rightLeg) {
                leftLeg.rotation.x = Math.sin(time * 3) * 0.2;
                rightLeg.rotation.x = Math.PI / 4 + Math.sin(time * 3 + Math.PI) * 0.2;
            }

            // Arme bewegen
            group.children.forEach((child, index) => {
                if (child.geometry && child.geometry.type === 'CylinderGeometry' &&
                    child.geometry.parameters && child.geometry.parameters.height === 0.3) {
                    const direction = index % 2 === 0 ? 1 : -1; // Simplified check, might need refinement
                    child.rotation.z = direction * Math.PI / 3 + Math.sin(time * 2 + index) * 0.1;
                    child.rotation.x = Math.sin(time * 1.5 + index) * 0.1;
                }
            });
        }
    };
    return group;
}