function createDefaultCharacter(colorHex) {
    const group = new THREE.Group();
    const color = parseInt(colorHex.replace('#', '0x'), 16);

    // Körper
    const body = new THREE.Mesh(
        new THREE.CylinderGeometry(0.12, 0.18, 0.4, 12),
        new THREE.MeshPhongMaterial({
            color: color,
            shininess: 30
        })
    );
    body.position.y = 0.2; // Base at y=0, center at 0.2
    group.add(body);

    // Kopf
    const head = new THREE.Mesh(
        new THREE.SphereGeometry(0.2, 16, 16),
        new THREE.MeshPhongMaterial({
            color: 0xFFDE97, // Skin color
            shininess: 40
        })
    );
    head.position.y = 0.2 + 0.4/2 + 0.2; // body.y + bodyHeight/2 + headRadius
    group.add(head);

    // Augen
    for (let i = 0; i < 2; i++) {
        const eye = new THREE.Mesh(
            new THREE.SphereGeometry(0.04, 8, 8),
            new THREE.MeshPhongMaterial({
                color: 0xffffff,
                shininess: 100
            })
        );
        eye.position.set(i === 0 ? 0.08 : -0.08, head.position.y + 0.05, 0.15); // Relative to head center, forward
        group.add(eye);

        const pupil = new THREE.Mesh(
            new THREE.SphereGeometry(0.02, 8, 8),
            new THREE.MeshPhongMaterial({ // Was MeshBasicMaterial, changed for consistency
                color: 0x000000,
                shininess: 100 // Added shininess
            })
        );
        pupil.position.set(i === 0 ? 0.08 : -0.08, head.position.y + 0.05, 0.18); // On eye, slightly forward
        group.add(pupil);
    }

    // Arme
    for (let i = 0; i < 2; i++) {
        const arm = new THREE.Mesh(
            new THREE.CylinderGeometry(0.05, 0.05, 0.25, 8),
            new THREE.MeshPhongMaterial({
                color: color, // Same color as body
                shininess: 30
            })
        );
        arm.position.set(i === 0 ? (0.18 + 0.05/2) : -(0.18 + 0.05/2), body.position.y + 0.1, 0); // Side of body, mid height
        arm.rotation.z = i === 0 ? Math.PI / 3 : -Math.PI / 3; // Angled
        group.add(arm);
    }

    // Beine
    for (let i = 0; i < 2; i++) {
        const leg = new THREE.Mesh(
            new THREE.CylinderGeometry(0.06, 0.08, 0.25, 8),
            new THREE.MeshPhongMaterial({
                color: new THREE.Color(color).multiplyScalar(0.8), // Darker shade
                shininess: 30
            })
        );
        leg.position.set(i === 0 ? 0.08 : -0.08, body.position.y - 0.4/2 - 0.25/2 + 0.05, 0); // Bottom of body
        group.add(leg);
    }

    group.userData = {
        animation: time => {
            const breathOffsetBody = Math.sin(time * 1.5) * 0.02;
            if(body) body.position.y = 0.2 + breathOffsetBody; // Original y + offset

            const breathOffsetHead = Math.sin(time * 1.5) * 0.02;
            if(head) {
                head.position.y = 0.6 + breathOffsetHead; // Original y + offset
                head.rotation.y = Math.sin(time * 0.7) * 0.1;
            }


            let eyeWhiteFound = 0;
            group.children.forEach(child => {
                if (child.geometry && child.geometry.type === 'SphereGeometry' &&
                    child.geometry.parameters && Math.abs(child.geometry.parameters.radius - 0.04) < 0.001 && eyeWhiteFound < 2) {
                     eyeWhiteFound++;
                    if (Math.sin(time * 0.5) > 0.95) {
                        child.scale.y = 0.2;
                    } else {
                        child.scale.y = 1;
                    }
                }
            });
        }
    };
    return group;
}