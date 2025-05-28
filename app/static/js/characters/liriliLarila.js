function createLiriliLarila(colorHex) {
    const group = new THREE.Group();
    const color = parseInt(colorHex.replace('#', '0x'), 16);

    // Körper wie eine Musiknote
    const bodyGeometry = new THREE.SphereGeometry(0.2, 16, 16);
    const bodyMaterial = new THREE.MeshPhongMaterial({
        color: color, // Use provided color
        shininess: 40
    });
    const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
    body.position.y = 0.2;
    group.add(body);

    // Notenhals
    const stemGeometry = new THREE.CylinderGeometry(0.04, 0.04, 0.5, 8);
    const stem = new THREE.Mesh(stemGeometry, bodyMaterial); // Use body's material
    stem.position.set(0.12, 0.45, 0); // y is top of body + half of stem height
    group.add(stem);

    // Notenfähnchen
    const flagGeometry = new THREE.BoxGeometry(0.2, 0.08, 0.08);
    const flag = new THREE.Mesh(flagGeometry, bodyMaterial); // Use body's material
    flag.position.set(0.25, 0.65, 0); // x offset from stem, y at top of stem
    group.add(flag);


    // Kopf (verträumt)
    const headGeometry = new THREE.SphereGeometry(0.2, 16, 16);
    const headMaterial = new THREE.MeshPhongMaterial({
        color: 0xFFEFD5, // Pastellfarbe
        shininess: 20
    });
    const head = new THREE.Mesh(headGeometry, headMaterial);
    head.position.y = 0.65; // Above the note stem/flag
    group.add(head);

    // Große träumerische Augen
    for (let i = 0; i < 2; i++) {
        const eye = new THREE.Mesh(
            new THREE.SphereGeometry(0.05, 12, 12),
            new THREE.MeshPhongMaterial({
                color: 0xFFFFFF,
                shininess: 80
            })
        );
        eye.position.set(i === 0 ? 0.08 : -0.08, 0.68, 0.15); // On the head, forward
        eye.scale.set(1, 1.5, 1); // Oval und träumerisch
        group.add(eye);

        // Große blaue Pupillen
        const pupil = new THREE.Mesh(
            new THREE.SphereGeometry(0.025, 8, 8),
            new THREE.MeshPhongMaterial({ color: 0x6495ED })
        );
        pupil.position.set(i === 0 ? 0.08 : -0.08, 0.70, 0.19); // Slightly up and forward on eye
        group.add(pupil);

        // Glanzpunkt
        const highlight = new THREE.Mesh(
            new THREE.SphereGeometry(0.01, 6, 6),
            new THREE.MeshPhongMaterial({ color: 0xFFFFFF })
        );
        highlight.position.set(i === 0 ? 0.09 : -0.07, 0.73, 0.20); // Top-forward on pupil
        group.add(highlight);
    }

    // Mond-/sternförmiger Mund (singend) - Simplified to a sphere for now
    const mouthGeometry = new THREE.SphereGeometry(0.04, 8, 8);
    const mouthMaterial = new THREE.MeshPhongMaterial({
        color: 0xFFA07A, // Light red/pink
        shininess: 30
    });
    const mouth = new THREE.Mesh(mouthGeometry, mouthMaterial);
    mouth.scale.set(1, 0.8, 1); // Slightly flattened
    mouth.position.set(0, 0.58, 0.17); // Below eyes, on the head, forward
    group.add(mouth);

    // Musiknoten um den Charakter
    const notesGroup = new THREE.Group();
    for (let i = 0; i < 5; i++) {
        const noteItemGroup = new THREE.Group(); // Renamed to avoid conflict
        const noteHead = new THREE.Mesh(
            new THREE.SphereGeometry(0.04, 8, 8),
            new THREE.MeshBasicMaterial({
                color: Math.random() > 0.5 ? 0x87CEEB : 0xFFB6C1,
                transparent: true,
                opacity: 0.8
            })
        );
        noteItemGroup.add(noteHead);

        const noteStick = new THREE.Mesh(
            new THREE.CylinderGeometry(0.01, 0.01, 0.1, 4),
            noteHead.material // Same material as note head
        );
        noteStick.position.set(0.04, 0.05, 0); // Relative to note head
        noteStick.rotation.z = -0.3;
        noteItemGroup.add(noteStick);

        const angle = (i / 5) * Math.PI * 2;
        const radius = 0.4 + Math.random() * 0.2;
        noteItemGroup.position.set(
            Math.cos(angle) * radius,
            0.6 + Math.random() * 0.4, // Around head height
            Math.sin(angle) * radius
        );
        notesGroup.add(noteItemGroup);
    }
    group.add(notesGroup);


    // Arme und Beine (Simple cylinders)
    const limbGeometry = new THREE.CylinderGeometry(0.03, 0.03, 0.25, 8);
    const limbMaterial = new THREE.MeshPhongMaterial({
        color: 0xFFEFD5, // Wie Kopf
        shininess: 20
    });

    // Arme
    for (let i = 0; i < 2; i++) {
        const arm = new THREE.Mesh(limbGeometry, limbMaterial);
        arm.position.set(i === 0 ? 0.15 : -0.15, 0.4, 0); // Attached to body/note sphere sides
        arm.rotation.z = i === 0 ? -Math.PI / 4 : Math.PI / 4;
        group.add(arm);
    }

    // Beine (Attached to the bottom of the note sphere)
    for (let i = 0; i < 2; i++) {
        const leg = new THREE.Mesh(limbGeometry, limbMaterial);
        leg.position.set(i === 0 ? 0.07 : -0.07, 0.00, 0); // y at bottom of body
        group.add(leg);
    }


    // Sterne und Glitzern
    const starsGroup = new THREE.Group();
    for (let i = 0; i < 10; i++) {
        const star = new THREE.Mesh(
            new THREE.OctahedronGeometry(0.02 + Math.random() * 0.02, 0), // Detail 0 for octahedron
            new THREE.MeshPhongMaterial({
                color: 0xFFFFFF,
                emissive: 0xFFFF99,
                emissiveIntensity: 0.5,
                transparent: true,
                opacity: 0.8
            })
        );
        const angle = Math.random() * Math.PI * 2;
        const radius = 0.3 + Math.random() * 0.4;
        const height = 0.4 + Math.random() * 0.5; // Around character
        star.position.set(
            Math.cos(angle) * radius,
            height,
            Math.sin(angle) * radius
        );
        starsGroup.add(star);
    }
    group.add(starsGroup);


    group.userData = {
        animation: time => {
            group.position.y = Math.sin(time * 1.5) * 0.05; // Main group hover
            if(head) {
                head.rotation.y = Math.sin(time * 0.7) * 0.2;
                head.rotation.z = Math.sin(time * 0.5) * 0.1;
            }
            if (mouth) {
                mouth.scale.y = 0.5 + Math.abs(Math.sin(time * 4)) * 0.5;
            }

            if(notesGroup) {
                notesGroup.children.forEach((noteItem, i) => { // Changed from 'note' to 'noteItem'
                    noteItem.position.y += Math.sin(time + i) * 0.002;
                    noteItem.rotation.y = time * 0.5;
                    noteItem.position.x += Math.sin(time * 0.5 + i) * 0.002;
                    noteItem.position.z += Math.cos(time * 0.5 + i) * 0.002;
                    noteItem.children.forEach(part => {
                        if (part.material) part.material.opacity = 0.5 + Math.sin(time + i) * 0.3;
                    });
                });
            }

            if(starsGroup) {
                starsGroup.children.forEach((star, i) => {
                    star.rotation.y = time * (0.2 + i * 0.05);
                    if(star.material) star.material.emissiveIntensity = 0.3 + Math.sin(time * 3 + i) * 0.2;
                });
            }

            // Arme schwingen
            let armCount = 0;
            group.children.forEach((child) => {
                if (child.geometry && child.geometry.type === 'CylinderGeometry' &&
                    child.geometry.parameters && child.geometry.parameters.height === 0.25 && armCount < 2) {
                    const direction = armCount % 2 === 0 ? 1 : -1;
                    child.rotation.z = direction * Math.PI / 4 + Math.sin(time * 2 + armCount * Math.PI) * 0.3;
                    child.rotation.x = Math.sin(time * 1.5 + armCount) * 0.2;
                    armCount++;
                }
            });
        }
    };
    return group;
}