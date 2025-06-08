function createBallerinaCappuccina(colorHex) {
    const group = new THREE.Group();
    const color = parseInt(colorHex.replace('#', '0x'), 16);

    // MASSIVE Ballerina-Tutu - BRAIN ROT OVERSIZED - RICHTIGE HÖHE
    const tutuGeometry = new THREE.CylinderGeometry(0.5, 0.7, 0.18, 16);
    const tutuMaterial = new THREE.MeshPhongMaterial({
        color: color,
        shininess: 30,
        transparent: true,
        opacity: 0.9
    });
    const tutu = new THREE.Mesh(tutuGeometry, tutuMaterial);
    tutu.position.y = 0.15; // ZURÜCK ZUR BOMBARDINO HÖHE
    group.add(tutu);

    // ITALIENISCHE CAPPUCCINO TASSE - RICHTIGE HÖHE
    const cupGeometry = new THREE.CylinderGeometry(0.3, 0.25, 0.45, 16);
    const cupMaterial = new THREE.MeshPhongMaterial({
        color: 0xF5F5DC, // Cremeweiß
        shininess: 50
    });
    const cup = new THREE.Mesh(cupGeometry, cupMaterial);
    cup.position.y = 0.35; // ZURÜCK ZUR BOMBARDINO HÖHE
    group.add(cup);

    // ÜBERTRIEBENER Griff der Tasse
    const handleGeometry = new THREE.TorusGeometry(0.15, 0.04, 8, 16, Math.PI);
    const handle = new THREE.Mesh(handleGeometry, cupMaterial);
    handle.position.set(0, 0.35, -0.25); // ZURÜCK ZUR BOMBARDINO HÖHE
    handle.rotation.x = Math.PI / 2;
    group.add(handle);

    // MASSIVER Cappuccino-Schaum - RICHTIGE HÖHE
    const foamGeometry = new THREE.SphereGeometry(0.3, 16, 16);
    const foamMaterial = new THREE.MeshPhongMaterial({
        color: 0xFFFFEE,
        shininess: 20
    });
    const foam = new THREE.Mesh(foamGeometry, foamMaterial);
    foam.scale.set(1.2, 0.4, 1.2);
    foam.position.y = 0.6; // ZURÜCK ZUR BOMBARDINO HÖHE
    group.add(foam);

    // ITALIENISCHES HERZ-MUSTER (anstatt Tulpe) - RICHTIGE HÖHE
    const patternGeometry = new THREE.SphereGeometry(0.08, 16, 16);
    const patternMaterial = new THREE.MeshBasicMaterial({
        color: 0x8B4513
    });
    const heartPattern = new THREE.Mesh(patternGeometry, patternMaterial);
    heartPattern.scale.set(1, 0.8, 1);
    heartPattern.position.set(0, 0.61, 0); // ZURÜCK ZUR BOMBARDINO HÖHE
    group.add(heartPattern);

    const heartPattern2 = new THREE.Mesh(patternGeometry, patternMaterial);
    heartPattern2.scale.set(0.7, 0.6, 0.7);
    heartPattern2.position.set(-0.05, 0.62, 0.05); // ZURÜCK ZUR BOMBARDINO HÖHE
    group.add(heartPattern2);

    // RIESIGE GOOGLY AUGEN - RICHTIGE HÖHE
    for (let i = 0; i < 2; i++) {
        const eye = new THREE.Mesh(
            new THREE.SphereGeometry(0.04, 8, 8),
            new THREE.MeshBasicMaterial({ color: 0xFFFFFF })
        );
        eye.position.set(i === 0 ? 0.12 : -0.12, 0.4, 0.22); // ZURÜCK ZUR BOMBARDINO HÖHE
        eye.scale.set(1.2, 1.8, 1);
        group.add(eye);

        // CRAZY PUPILS - RICHTIGE HÖHE
        const pupil = new THREE.Mesh(
            new THREE.SphereGeometry(0.02, 8, 8),
            new THREE.MeshBasicMaterial({ color: 0x000000 })
        );
        pupil.position.set(i === 0 ? 0.12 : -0.12, 0.42, 0.25); // ZURÜCK ZUR BOMBARDINO HÖHE
        group.add(pupil);
    }

    // ITALIENISCHER LÄCHELNDER MUND - RICHTIGE HÖHE
    const smile = new THREE.Mesh(
        new THREE.TorusGeometry(0.08, 0.015, 8, 16, Math.PI),
        new THREE.MeshBasicMaterial({ color: 0x8B0000 })
    );
    smile.position.set(0, 0.32, 0.22); // ZURÜCK ZUR BOMBARDINO HÖHE
    smile.rotation.x = Math.PI / 2;
    group.add(smile);

    // ÜBERTRIEBENE Ballerina-Beine - RICHTIGE HÖHE
    const legGeometry = new THREE.CylinderGeometry(0.04, 0.04, 0.25, 8);
    const legMaterial = new THREE.MeshPhongMaterial({
        color: 0xFFDFBA, // Hautfarbe
        shininess: 20
    });

    // EXTREME DANCE POSE - WIE BOMBARDINO LEVEL
    const leftLeg = new THREE.Mesh(legGeometry, legMaterial);
    leftLeg.position.set(0.15, 0.05, 0); // ZURÜCK ZUR BOMBARDINO HÖHE
    leftLeg.rotation.z = Math.PI / 8;
    group.add(leftLeg);

    const rightLeg = new THREE.Mesh(legGeometry, legMaterial);
    rightLeg.position.set(-0.15, 0.05, 0); // ZURÜCK ZUR BOMBARDINO HÖHE
    rightLeg.rotation.z = -Math.PI / 4;
    rightLeg.rotation.x = Math.PI / 6;
    group.add(rightLeg);

    // ITALIENISCHE BALLERINA-SCHUHE - AUF DEM BODEN
    for (let i = 0; i < 2; i++) {
        const shoe = new THREE.Mesh(
            new THREE.SphereGeometry(0.05, 8, 8),
            new THREE.MeshPhongMaterial({
                color: 0x8B0000, // Italienisches Rot
                shininess: 40
            })
        );
        shoe.scale.set(1.4, 0.7, 2.2);

        if (i === 0) { // Linker Schuh
            shoe.position.set(0.15, -0.08, 0.08); // ZURÜCK ZUR BOMBARDINO HÖHE
        } else { // Rechter Schuh  
            shoe.position.set(-0.22, -0.05, 0.12); // ZURÜCK ZUR BOMBARDINO HÖHE
            shoe.rotation.x = Math.PI / 6;
        }
        group.add(shoe);
    }

    // DRAMATISCHE Arme in ITALIENISCHER Tanzposition - RICHTIGE HÖHE
    for (let i = 0; i < 2; i++) {
        const arm = new THREE.Mesh(
            new THREE.CylinderGeometry(0.035, 0.025, 0.35, 8),
            legMaterial
        );

        if (i === 0) { // Linker Arm - ITALIAN GESTURE
            arm.position.set(0.3, 0.4, 0); // ZURÜCK ZUR BOMBARDINO HÖHE
            arm.rotation.z = -Math.PI / 2.5;
        } else { // Rechter Arm - DRAMATIC
            arm.position.set(-0.3, 0.4, 0); // ZURÜCK ZUR BOMBARDINO HÖHE
            arm.rotation.z = Math.PI / 2.5;
        }
        group.add(arm);
    }

    // ITALIENISCHE FLAGGE am Tutu - RICHTIGE HÖHE
    const flag = new THREE.Mesh(
        new THREE.PlaneGeometry(0.1, 0.06),
        new THREE.MeshBasicMaterial({
            color: 0x00AA00, // Grün der italienischen Flagge
            side: THREE.DoubleSide
        })
    );
    flag.position.set(0.4, 0.15, 0); // ZURÜCK ZUR BOMBARDINO HÖHE
    group.add(flag);

    // WICHTIG: GESAMTE GROUP EXTREM HOCH - DAMIT SIE IN DER LUFT FLIEGT
    group.position.y = 2.0; // EXTREM HOCH! DAMIT WIR SIE SEHEN KÖNNEN

    // Animation - ITALIAN BRAIN ROT DANCE
    group.userData = {
        animation: time => {
            // CRAZY SPINNING wie beim Tanz
            group.rotation.y = Math.sin(time * 1.2) * 0.3; // Mehr Bewegung

            // COFFEE BOUNCING
            group.position.y = Math.sin(time * 4) * 0.08; // Mehr Hüpfen

            // TUTU WILD SWINGING
            if (tutu) {
                tutu.scale.x = 1 + Math.sin(time * 3) * 0.1;
                tutu.scale.z = 1 + Math.sin(time * 3 + 0.5) * 0.1;
                tutu.rotation.y = Math.sin(time * 2) * 0.2; // Tutu dreht sich
            }

            // STEAM GOING CRAZY vom Cappuccino
            if (Math.random() > 0.9) { // Mehr Dampf
                const steamParticle = new THREE.Mesh(
                    new THREE.SphereGeometry(0.025 + Math.random() * 0.025, 6, 6),
                    new THREE.MeshBasicMaterial({
                        color: 0xFFFFFF,
                        transparent: true,
                        opacity: 0.6
                    })
                );

                steamParticle.position.set(
                    (Math.random() - 0.5) * 0.3,
                    0.65,
                    (Math.random() - 0.5) * 0.3
                );
                group.add(steamParticle);

                // WILD Dampf-Animation
                let particleAge = 0;
                const animateSteam = () => {
                    particleAge += 0.08; // Schneller

                    if (particleAge > 1 || !steamParticle.parent) {
                        if(steamParticle.parent) group.remove(steamParticle);
                        return;
                    }

                    steamParticle.position.y += 0.015; // Schneller nach oben
                    steamParticle.position.x += Math.sin(particleAge * 6) * 0.01; // Wiggly
                    steamParticle.material.opacity = 0.6 * (1 - particleAge);
                    requestAnimationFrame(animateSteam);
                };
                animateSteam();
            }

            // CRAZY LEGS im Tanzrhythmus - mit korrigierten Referenzen
            if (leftLeg && rightLeg) {
                leftLeg.rotation.x = Math.sin(time * 6) * 0.3; // Schneller
                rightLeg.rotation.x = Math.PI / 6 + Math.sin(time * 6 + Math.PI) * 0.3;
            }

            // ITALIAN ARMS GESTURING WILDLY
            group.children.forEach((child, index) => {
                if (child.geometry && child.geometry.type === 'CylinderGeometry' &&
                    child.geometry.parameters && child.geometry.parameters.height === 0.35) {
                    const direction = index % 2 === 0 ? 1 : -1;
                    child.rotation.z = direction * Math.PI / 2.5 + Math.sin(time * 4 + index) * 0.2;
                    child.rotation.x = Math.sin(time * 3 + index) * 0.15;
                }
            });

            // EYES GOING CRAZY
            group.children.forEach((child) => {
                if (child.geometry && child.geometry.type === 'SphereGeometry' &&
                    child.geometry.parameters && child.geometry.parameters.radius === 0.02) {
                    child.position.x += Math.sin(time * 8) * 0.01; // Eyes moving
                }
            });
        }
    };
    return group;
}