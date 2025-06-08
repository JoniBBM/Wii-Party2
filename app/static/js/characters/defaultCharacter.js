function createDefaultCharacter(colorHex) {
    const group = new THREE.Group();
    const color = parseInt(colorHex.replace('#', '0x'), 16);

    // MASSIVE Körper - BRAIN ROT ITALIAN DEFAULT
    const body = new THREE.Mesh(
        new THREE.CylinderGeometry(0.15, 0.22, 0.45, 12), // Größer
        new THREE.MeshPhongMaterial({
            color: color,
            shininess: 30
        })
    );
    body.position.y = 0.2; // NIEDRIGER wie Bombardino
    group.add(body);

    // GRÖßERER Kopf - BRAIN ROT SIZE
    const head = new THREE.Mesh(
        new THREE.SphereGeometry(0.25, 16, 16), // Viel größer
        new THREE.MeshPhongMaterial({
            color: 0xFFDE97, // Skin color
            shininess: 40
        })
    );
    head.position.y = 0.55; // body.y + bodyHeight/2 + headRadius, niedriger
    group.add(head);

    // RIESIGE GOOGLY AUGEN - BRAIN ROT ESSENTIAL
    for (let i = 0; i < 2; i++) {
        const eye = new THREE.Mesh(
            new THREE.SphereGeometry(0.06, 8, 8), // Viel größer
            new THREE.MeshPhongMaterial({
                color: 0xffffff,
                shininess: 100
            })
        );
        eye.position.set(i === 0 ? 0.12 : -0.12, head.position.y + 0.08, 0.2); // Weiter auseinander
        eye.scale.set(1.2, 1.6, 1); // Oval und verrückt
        group.add(eye);

        const pupil = new THREE.Mesh(
            new THREE.SphereGeometry(0.03, 8, 8), // Größer
            new THREE.MeshPhongMaterial({
                color: 0x000000,
                shininess: 100
            })
        );
        pupil.position.set(i === 0 ? 0.12 : -0.12, head.position.y + 0.08, 0.24);
        group.add(pupil);
    }

    // ITALIENISCHER SCHNURRBART
    const mustache = new THREE.Mesh(
        new THREE.TorusGeometry(0.1, 0.025, 8, 16, Math.PI),
        new THREE.MeshPhongMaterial({
            color: 0x2C1810, // Dunkelbraun
            shininess: 30
        })
    );
    mustache.position.set(0, head.position.y - 0.05, 0.2);
    mustache.rotation.x = Math.PI / 2;
    mustache.rotation.z = Math.PI;
    group.add(mustache);

    // GROSSER ITALIENISCHER MUND
    const mouth = new THREE.Mesh(
        new THREE.SphereGeometry(0.04, 8, 8),
        new THREE.MeshPhongMaterial({
            color: 0x8B0000, // Italienisches Rot
            shininess: 50
        })
    );
    mouth.scale.set(1.5, 0.8, 1);
    mouth.position.set(0, head.position.y - 0.12, 0.22);
    group.add(mouth);

    // ITALIENISCHER CHEF HAT
    const hatBase = new THREE.Mesh(
        new THREE.CylinderGeometry(0.15, 0.15, 0.03, 16),
        new THREE.MeshPhongMaterial({
            color: 0xFFFFFF,
            shininess: 50
        })
    );
    hatBase.position.set(0, head.position.y + 0.28, 0);
    group.add(hatBase);

    const hatTop = new THREE.Mesh(
        new THREE.CylinderGeometry(0.1, 0.12, 0.15, 16),
        hatBase.material
    );
    hatTop.position.set(0, head.position.y + 0.38, 0);
    group.add(hatTop);

    // DICKERE Arme - ITALIAN GESTURE READY
    for (let i = 0; i < 2; i++) {
        const arm = new THREE.Mesh(
            new THREE.CylinderGeometry(0.06, 0.06, 0.3, 8), // Dicker
            new THREE.MeshPhongMaterial({
                color: color,
                shininess: 30
            })
        );
        arm.position.set(i === 0 ? (0.22 + 0.06/2) : -(0.22 + 0.06/2), body.position.y + 0.1, 0);
        arm.rotation.z = i === 0 ? Math.PI / 2.5 : -Math.PI / 2.5; // Italienische Gesten
        group.add(arm);
    }

    // DICKERE Beine - RICHTIG AUF DEM BODEN
    for (let i = 0; i < 2; i++) {
        const leg = new THREE.Mesh(
            new THREE.CylinderGeometry(0.08, 0.1, 0.2, 8), // Kürzer für bessere Positionierung
            new THREE.MeshPhongMaterial({
                color: new THREE.Color(color).multiplyScalar(0.8),
                shininess: 30
            })
        );
        leg.position.set(i === 0 ? 0.1 : -0.1, 0.05, 0); // AUF DEM BODEN wie Bombardino
        group.add(leg);
    }

    // ITALIENISCHE SCHUHE - AUF DEM BODEN
    for (let i = 0; i < 2; i++) {
        const shoe = new THREE.Mesh(
            new THREE.SphereGeometry(0.06, 8, 8), // Größer
            new THREE.MeshPhongMaterial({
                color: 0x8B4513,
                shininess: 40
            })
        );
        shoe.scale.set(1.8, 0.6, 2.2); // Längere Italienische Schuhe
        shoe.position.set(i === 0 ? 0.1 : -0.1, -0.08, 0.08); // AUF DEM BODEN
        group.add(shoe);
    }

    // PIZZA SLICE in der Hand
    const pizzaGroup = new THREE.Group();
    const pizzaBase = new THREE.Mesh(
        new THREE.ConeGeometry(0.06, 0.12, 3),
        new THREE.MeshPhongMaterial({ color: 0xFFE4B5 })
    );
    pizzaBase.rotation.z = Math.PI;
    pizzaBase.position.set(0.4, body.position.y + 0.2, 0);
    pizzaGroup.add(pizzaBase);

    // Pizza Toppings
    const pepperoni = new THREE.Mesh(
        new THREE.SphereGeometry(0.01, 8, 8),
        new THREE.MeshPhongMaterial({ color: 0x8B0000 })
    );
    pepperoni.position.set(0.38, body.position.y + 0.25, 0.02);
    pizzaGroup.add(pepperoni);

    group.add(pizzaGroup);

    // ITALIENISCHE FLAGGE als Zubehör
    const flagGroup = new THREE.Group();
    const flagPole = new THREE.Mesh(
        new THREE.CylinderGeometry(0.01, 0.01, 0.3, 8),
        new THREE.MeshPhongMaterial({ color: 0x8B4513 })
    );
    flagPole.position.set(-0.35, body.position.y + 0.1, 0);
    flagGroup.add(flagPole);

    const flag = new THREE.Mesh(
        new THREE.PlaneGeometry(0.12, 0.08),
        new THREE.MeshBasicMaterial({
            color: 0x00AA00, // Grün
            side: THREE.DoubleSide
        })
    );
    flag.position.set(-0.3, body.position.y + 0.25, 0);
    flagGroup.add(flag);

    group.add(flagGroup);

    group.userData = {
        animation: time => {
            const breathOffsetBody = Math.sin(time * 2) * 0.03; // Schnelleres Atmen
            if(body) body.position.y = 0.2 + breathOffsetBody;

            const breathOffsetHead = Math.sin(time * 2) * 0.03;
            if(head) {
                head.position.y = 0.55 + breathOffsetHead;
                head.rotation.y = Math.sin(time * 1.5) * 0.15; // Mehr Kopfbewegung
            }

            // CRAZY BLINKING
            let eyeWhiteFound = 0;
            group.children.forEach(child => {
                if (child.geometry && child.geometry.type === 'SphereGeometry' &&
                    child.geometry.parameters && Math.abs(child.geometry.parameters.radius - 0.06) < 0.001 && eyeWhiteFound < 2) {
                     eyeWhiteFound++;
                    if (Math.sin(time * 1.5) > 0.9) {
                        child.scale.y = 0.1; // Längeres Blinzeln
                    } else {
                        child.scale.y = 1.6; // Zurück zu oval
                    }
                }
            });

            // MUSTACHE WIGGLE
            if (mustache) {
                mustache.rotation.z = Math.PI + Math.sin(time * 6) * 0.15;
            }

            // CHEF HAT WOBBLE
            if (hatTop) {
                hatTop.rotation.z = Math.sin(time * 4) * 0.1;
            }

            // PIZZA FLOATING
            if (pizzaGroup) {
                pizzaGroup.position.y = Math.sin(time * 3) * 0.02;
                pizzaGroup.rotation.z = Math.PI + Math.sin(time * 2) * 0.05;
            }

            // FLAG WAVING
            if (flagGroup) {
                flag.rotation.y = Math.sin(time * 4) * 0.2;
            }

            // PUPILS MOVING CRAZY
            group.children.forEach((child) => {
                if (child.geometry && child.geometry.type === 'SphereGeometry' &&
                    child.geometry.parameters && child.geometry.parameters.radius === 0.03) {
                    child.position.x += Math.sin(time * 8) * 0.01;
                    child.position.y += Math.cos(time * 6) * 0.005;
                }
            });

            // MOUTH TALKING
            if (mouth) {
                mouth.scale.y = 0.8 + Math.abs(Math.sin(time * 5)) * 0.4;
                mouth.scale.x = 1.5 + Math.sin(time * 5) * 0.2;
            }
        }
    };
    return group;
}