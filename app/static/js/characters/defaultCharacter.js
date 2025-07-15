function createDefaultCharacter(colorHex, customization = {}) {
    const group = new THREE.Group();
    const color = parseInt(colorHex.replace('#', '0x'), 16);
    
    // Umfassende Standard-Anpassungswerte
    const defaults = {
        // Basis-Farben
        shirtColor: '#4169E1',     // Royal Blue
        pantsColor: '#8B4513',     // Saddle Brown
        hairColor: '#2C1810',      // Dark Brown
        shoeColor: '#8B4513',      // Saddle Brown
        skinColor: '#FFDE97',      // Skin color
        eyeColor: '#4169E1',       // Eye color
        
        // Aussehen
        faceShape: 'oval',         // oval, round, square, heart
        bodyType: 'normal',        // slim, normal, athletic, chunky
        height: 'normal',          // short, normal, tall
        hairStyle: 'short',        // short, medium, long, curly, bald
        eyeShape: 'normal',        // normal, big, small, sleepy
        beardStyle: 'none',        // none, mustache, goatee, full
        
        // Kleidung
        shirtType: 'tshirt',       // tshirt, polo, hoodie, formal
        pantsType: 'jeans',        // jeans, shorts, formal, athletic
        shoeType: 'sneakers',      // sneakers, boots, formal, sandals
        
        // Accessoires
        hat: 'none',               // none, cap, beanie, formal
        glasses: 'none',           // none, normal, sunglasses, reading
        jewelry: 'none',           // none, watch, chain, rings
        backpack: 'none',          // none, school, hiking, stylish
        
        // Animationen
        animationStyle: 'normal',  // normal, energetic, calm, quirky
        walkStyle: 'normal',       // normal, bouncy, confident, sneaky
        idleStyle: 'normal',       // normal, fidgety, relaxed, proud
        voiceType: 'normal'        // normal, deep, high, robotic
    };
    
    // Merge with provided customization
    const custom = { ...defaults, ...customization };
    
    // Convert hex colors to THREE.Color
    const shirtColor = parseInt(custom.shirtColor.replace('#', '0x'), 16);
    const pantsColor = parseInt(custom.pantsColor.replace('#', '0x'), 16);
    const hairColor = parseInt(custom.hairColor.replace('#', '0x'), 16);
    const shoeColor = parseInt(custom.shoeColor.replace('#', '0x'), 16);
    const skinColor = parseInt(custom.skinColor.replace('#', '0x'), 16);
    const eyeColor = parseInt(custom.eyeColor.replace('#', '0x'), 16);

    // ADAPTIVE Körper basierend auf Body-Type
    let bodyScale = 1.0;
    let bodyWidth = 0.18;
    let bodyHeight = 0.55;
    
    switch (custom.bodyType) {
        case 'slim':
            bodyScale = 0.8;
            bodyWidth = 0.15;
            break;
        case 'athletic':
            bodyScale = 1.2;
            bodyWidth = 0.22;
            break;
        case 'chunky':
            bodyScale = 1.4;
            bodyWidth = 0.26;
            bodyHeight = 0.6;
            break;
        default: // normal
            bodyScale = 1.0;
            bodyWidth = 0.18;
    }
    
    // Höhen-Anpassung
    let heightMultiplier = 1.0;
    switch (custom.height) {
        case 'short':
            heightMultiplier = 0.8;
            break;
        case 'tall':
            heightMultiplier = 1.2;
            break;
        default: // normal
            heightMultiplier = 1.0;
    }
    
    // Körper mit anpassbarer Geometrie (Hauptkörper als Zentrum)
    const body = new THREE.Mesh(
        new THREE.CylinderGeometry(bodyWidth, bodyWidth * 1.2, bodyHeight * heightMultiplier, 12),
        new THREE.MeshPhongMaterial({
            color: shirtColor,
            shininess: 30
        })
    );
    body.position.y = 0.3 * heightMultiplier; // Wird später nach Bein-Definition korrigiert
    
    // Körper-Gruppe für alle anhängenden Teile
    const bodyGroup = new THREE.Group();
    bodyGroup.add(body);
    group.add(bodyGroup);

    // Adaptiver Kopf basierend auf Gesichtsform
    let headGeometry;
    let headScale = { x: 1, y: 1, z: 1 };
    
    switch (custom.faceShape) {
        case 'round':
            headGeometry = new THREE.SphereGeometry(0.25, 16, 16);
            headScale = { x: 1.1, y: 1.1, z: 1.1 };
            break;
        case 'square':
            headGeometry = new THREE.BoxGeometry(0.4, 0.4, 0.4);
            headScale = { x: 1, y: 1, z: 1 };
            break;
        case 'heart':
            headGeometry = new THREE.SphereGeometry(0.25, 16, 16);
            headScale = { x: 1.1, y: 0.9, z: 1 };
            break;
        default: // oval
            headGeometry = new THREE.SphereGeometry(0.25, 16, 16);
            headScale = { x: 1, y: 1.1, z: 1 };
    }
    
    const head = new THREE.Mesh(
        headGeometry,
        new THREE.MeshPhongMaterial({
            color: skinColor,
            shininess: 40
        })
    );
    head.position.y = body.position.y + (bodyHeight * heightMultiplier * 0.5) + 0.25; // Kopf direkt auf Körper
    head.scale.set(headScale.x, headScale.y, headScale.z);
    bodyGroup.add(head);

    // ADAPTIVE Augen basierend auf Augenform
    let eyeSize = 0.06;
    let eyeScale = { x: 1.2, y: 1.6, z: 1 };
    
    switch (custom.eyeShape) {
        case 'big':
            eyeSize = 0.08;
            eyeScale = { x: 1.4, y: 1.8, z: 1 };
            break;
        case 'small':
            eyeSize = 0.05;
            eyeScale = { x: 1.1, y: 1.3, z: 1 };
            break;
        case 'sleepy':
            eyeSize = 0.06;
            eyeScale = { x: 1.5, y: 0.8, z: 1 };
            break;
        default: // normal
            eyeSize = 0.06;
            eyeScale = { x: 1.2, y: 1.6, z: 1 };
    }
    
    for (let i = 0; i < 2; i++) {
        const eye = new THREE.Mesh(
            new THREE.SphereGeometry(eyeSize, 8, 8),
            new THREE.MeshPhongMaterial({
                color: 0xffffff,
                shininess: 100
            })
        );
        eye.position.set(i === 0 ? 0.12 : -0.12, head.position.y + 0.08, 0.2);
        eye.scale.set(eyeScale.x, eyeScale.y, eyeScale.z);
        bodyGroup.add(eye);

        // Pupille mit besserer Größenverteilung
        let pupilSize = eyeSize * 0.6; // Größeres Verhältnis für bessere Sichtbarkeit
        let pupilZ = 0.25; // Standard Z-Position
        
        if (custom.eyeShape === 'small') {
            pupilSize = eyeSize * 0.8; // Noch größer für kleine Augen
            pupilZ = 0.26; // Weiter vorne für kleine Augen
        }
        
        const pupil = new THREE.Mesh(
            new THREE.SphereGeometry(pupilSize, 8, 8),
            new THREE.MeshPhongMaterial({
                color: eyeColor,
                shininess: 100
            })
        );
        pupil.position.set(i === 0 ? 0.12 : -0.12, head.position.y + 0.08, pupilZ);
        // Pupille nicht skalieren, um korrekte Größe zu behalten
        bodyGroup.add(pupil);
    }

    // ADAPTIVE Bart basierend auf Bart-Stil
    let facial_hair = null;
    
    switch (custom.beardStyle) {
        case 'mustache':
            facial_hair = new THREE.Mesh(
                new THREE.TorusGeometry(0.1, 0.025, 8, 16, Math.PI),
                new THREE.MeshPhongMaterial({
                    color: hairColor,
                    shininess: 30
                })
            );
            facial_hair.position.set(0, head.position.y - 0.05, 0.2);
            facial_hair.rotation.x = Math.PI / 2;
            facial_hair.rotation.z = Math.PI;
            break;
        case 'goatee':
            facial_hair = new THREE.Mesh(
                new THREE.SphereGeometry(0.04, 8, 8),
                new THREE.MeshPhongMaterial({
                    color: hairColor,
                    shininess: 30
                })
            );
            facial_hair.position.set(0, head.position.y - 0.15, 0.2);
            facial_hair.scale.set(1, 1.5, 1);
            break;
        case 'full':
            facial_hair = new THREE.Mesh(
                new THREE.SphereGeometry(0.15, 8, 8),
                new THREE.MeshPhongMaterial({
                    color: hairColor,
                    shininess: 30
                })
            );
            facial_hair.position.set(0, head.position.y - 0.1, 0.15);
            facial_hair.scale.set(1.2, 0.8, 0.8);
            break;
        default: // none
            // Kein Bart
            break;
    }
    
    if (facial_hair) {
        bodyGroup.add(facial_hair);
    }

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
    bodyGroup.add(mouth);

    // ADAPTIVE Haare basierend auf Haarstil
    let hair = null;
    
    switch (custom.hairStyle) {
        case 'short':
            hair = new THREE.Mesh(
                new THREE.SphereGeometry(0.27, 16, 16),
                new THREE.MeshPhongMaterial({
                    color: hairColor,
                    shininess: 30
                })
            );
            hair.position.set(0, head.position.y + 0.18, -0.05);
            hair.scale.set(0.9, 0.5, 0.9);
            break;
        case 'medium':
            hair = new THREE.Mesh(
                new THREE.SphereGeometry(0.29, 16, 16),
                new THREE.MeshPhongMaterial({
                    color: hairColor,
                    shininess: 30
                })
            );
            hair.position.set(0, head.position.y + 0.18, -0.05);
            hair.scale.set(1.0, 0.6, 1.0);
            break;
        case 'long':
            hair = new THREE.Mesh(
                new THREE.SphereGeometry(0.31, 16, 16),
                new THREE.MeshPhongMaterial({
                    color: hairColor,
                    shininess: 30
                })
            );
            hair.position.set(0, head.position.y + 0.15, -0.05);
            hair.scale.set(1.1, 0.8, 1.1);
            break;
        case 'curly':
            hair = new THREE.Mesh(
                new THREE.SphereGeometry(0.33, 8, 8),
                new THREE.MeshPhongMaterial({
                    color: hairColor,
                    shininess: 20
                })
            );
            hair.position.set(0, head.position.y + 0.19, -0.05);
            hair.scale.set(1.2, 0.7, 1.2);
            break;
        case 'bald':
            // Kein Haar
            break;
        default: // short
            hair = new THREE.Mesh(
                new THREE.SphereGeometry(0.27, 16, 16),
                new THREE.MeshPhongMaterial({
                    color: hairColor,
                    shininess: 30
                })
            );
            hair.position.set(0, head.position.y + 0.18, -0.05);
            hair.scale.set(0.9, 0.5, 0.9);
    }
    
    if (hair) {
        bodyGroup.add(hair);
    }
    
    // ADAPTIVE Kopfbedeckung basierend auf Hat-Auswahl
    let hat = null;
    
    switch (custom.hat) {
        case 'cap':
            hat = new THREE.Mesh(
                new THREE.CylinderGeometry(0.15, 0.15, 0.05, 16),
                new THREE.MeshPhongMaterial({
                    color: shirtColor,
                    shininess: 50
                })
            );
            hat.position.set(0, head.position.y + 0.25, 0);
            break;
        case 'beanie':
            hat = new THREE.Mesh(
                new THREE.SphereGeometry(0.28, 16, 16),
                new THREE.MeshPhongMaterial({
                    color: hairColor,
                    shininess: 30
                })
            );
            hat.position.set(0, head.position.y + 0.15, 0);
            hat.scale.set(1, 0.8, 1);
            break;
        case 'formal':
            // Formeller Hut (Original Chef Hat)
            const hatBase = new THREE.Mesh(
                new THREE.CylinderGeometry(0.15, 0.15, 0.03, 16),
                new THREE.MeshPhongMaterial({
                    color: 0x000000,
                    shininess: 50
                })
            );
            hatBase.position.set(0, head.position.y + 0.28, 0);
            bodyGroup.add(hatBase);

            const hatTop = new THREE.Mesh(
                new THREE.CylinderGeometry(0.1, 0.12, 0.15, 16),
                hatBase.material
            );
            hatTop.position.set(0, head.position.y + 0.38, 0);
            bodyGroup.add(hatTop);
            hat = hatTop;
            break;
        default: // none
            // Kein Hut
            break;
    }
    
    if (hat) {
        bodyGroup.add(hat);
    }

    // ADAPTIVE Arme basierend auf Body-Type
    let armThickness = 0.06;
    let armLength = 0.3;
    
    switch (custom.bodyType) {
        case 'slim':
            armThickness = 0.04;
            armLength = 0.25;
            break;
        case 'athletic':
            armThickness = 0.08;
            armLength = 0.35;
            break;
        case 'chunky':
            armThickness = 0.1;
            armLength = 0.32;
            break;
        default: // normal
            armThickness = 0.06;
            armLength = 0.3;
    }
    
    for (let i = 0; i < 2; i++) {
        const arm = new THREE.Mesh(
            new THREE.CylinderGeometry(armThickness, armThickness, armLength * heightMultiplier, 8),
            new THREE.MeshPhongMaterial({
                color: shirtColor,
                shininess: 30
            })
        );
        arm.position.set(i === 0 ? (bodyWidth + 0.08) : -(bodyWidth + 0.08), body.position.y + 0.05, 0); // Arme näher am Körper
        arm.rotation.z = i === 0 ? Math.PI / 2.5 : -Math.PI / 2.5;
        bodyGroup.add(arm);
    }

    // ADAPTIVE Beine basierend auf Body-Type und Hosen-Stil
    let legThickness = 0.08;
    let legLength = 0.35;
    
    switch (custom.bodyType) {
        case 'slim':
            legThickness = 0.06;
            legLength = 0.38;
            break;
        case 'athletic':
            legThickness = 0.1;
            legLength = 0.42;
            break;
        case 'chunky':
            legThickness = 0.12;
            legLength = 0.32;
            break;
        default: // normal
            legThickness = 0.08;
            legLength = 0.35;
    }
    
    // Korrigiere Körper-Position: Körper sitzt direkt auf Beinen
    body.position.y = (0.05 + (legLength * heightMultiplier * 0.5) + (bodyHeight * heightMultiplier * 0.5)) * heightMultiplier;
    
    // Korrigiere Kopf-Position: Kopf sitzt direkt auf Körper
    head.position.y = body.position.y + (bodyHeight * heightMultiplier * 0.5) + 0.25;
    
    // Korrigiere Arm-Positionen: Arme an korrigierter Körperposition
    bodyGroup.children.forEach(child => {
        if (child.geometry && child.geometry.type === 'CylinderGeometry' && 
            child.geometry.parameters.height === armLength * heightMultiplier) {
            const isRightArm = child.position.x > 0;
            child.position.set(
                isRightArm ? (bodyWidth + 0.08) : -(bodyWidth + 0.08), 
                body.position.y + 0.1, 
                0
            );
        }
    });
    
    // Korrigiere alle kopfbezogenen Elemente-Positionen
    bodyGroup.children.forEach(child => {
        // Augen
        if (child.geometry && child.geometry.type === 'SphereGeometry' && 
            child.material.color.getHex() === 0xffffff && child.geometry.parameters.radius === eyeSize) {
            const isRightEye = child.position.x > 0;
            child.position.set(isRightEye ? 0.12 : -0.12, head.position.y + 0.08, 0.2);
        }
        // Pupillen
        if (child.geometry && child.geometry.type === 'SphereGeometry' && 
            (child.geometry.parameters.radius === eyeSize * 0.6 || child.geometry.parameters.radius === eyeSize * 0.7 || child.geometry.parameters.radius === eyeSize * 0.8)) {
            const isRightPupil = child.position.x > 0;
            let pupilZ = 0.25; // Standard Z-Position
            if (custom.eyeShape === 'small') {
                pupilZ = 0.26; // Weiter vorne für kleine Augen
            }
            child.position.set(isRightPupil ? 0.12 : -0.12, head.position.y + 0.08, pupilZ);
        }
    });
    
    // Mund
    if (mouth) {
        mouth.position.set(0, head.position.y - 0.12, 0.22);
    }
    
    // Bart
    if (facial_hair) {
        switch (custom.beardStyle) {
            case 'mustache':
                facial_hair.position.set(0, head.position.y - 0.05, 0.2);
                break;
            case 'goatee':
                facial_hair.position.set(0, head.position.y - 0.15, 0.2);
                break;
            case 'full':
                facial_hair.position.set(0, head.position.y - 0.1, 0.15);
                break;
        }
    }
    
    // Haare
    if (hair) {
        switch (custom.hairStyle) {
            case 'short':
            case 'medium':
                hair.position.set(0, head.position.y + 0.18, -0.05);
                break;
            case 'long':
                hair.position.set(0, head.position.y + 0.15, -0.05);
                break;
            case 'curly':
                hair.position.set(0, head.position.y + 0.19, -0.05);
                break;
            default:
                hair.position.set(0, head.position.y + 0.18, -0.05);
        }
    }
    
    // Hut
    if (hat) {
        switch (custom.hat) {
            case 'cap':
                hat.position.set(0, head.position.y + 0.25, 0);
                break;
            case 'beanie':
                hat.position.set(0, head.position.y + 0.15, 0);
                break;
            case 'formal':
                // hatBase und hatTop werden separat behandelt
                bodyGroup.children.forEach(child => {
                    if (child.geometry && child.geometry.type === 'CylinderGeometry' && 
                        child.material.color.getHex() === 0x000000) {
                        if (child.geometry.parameters.height === 0.03) {
                            child.position.set(0, head.position.y + 0.28, 0);
                        } else if (child.geometry.parameters.height === 0.15) {
                            child.position.set(0, head.position.y + 0.38, 0);
                        }
                    }
                });
                break;
        }
    }
    
    // Brille (wird später korrigiert wenn sie existiert)
    
    // Anpassung basierend auf Hosen-Typ
    let legGeometry;
    switch (custom.pantsType) {
        case 'shorts':
            legGeometry = new THREE.CylinderGeometry(legThickness, legThickness * 1.2, legLength * 0.6 * heightMultiplier, 8);
            break;
        case 'formal':
            legGeometry = new THREE.CylinderGeometry(legThickness * 0.9, legThickness * 0.9, legLength * heightMultiplier, 8);
            break;
        case 'athletic':
            legGeometry = new THREE.CylinderGeometry(legThickness * 1.1, legThickness * 1.3, legLength * heightMultiplier, 8);
            break;
        default: // jeans
            legGeometry = new THREE.CylinderGeometry(legThickness, legThickness * 1.2, legLength * heightMultiplier, 8);
    }
    
    for (let i = 0; i < 2; i++) {
        const leg = new THREE.Mesh(
            legGeometry,
            new THREE.MeshPhongMaterial({
                color: pantsColor,
                shininess: 30
            })
        );
        leg.position.set(i === 0 ? 0.08 : -0.08, 0.05 * heightMultiplier, 0); // Beine höher positioniert
        bodyGroup.add(leg);
    }

    // ADAPTIVE Schuhe basierend auf Schuh-Typ
    let shoeGeometry;
    let shoeScale = { x: 1.8, y: 0.6, z: 2.2 };
    
    switch (custom.shoeType) {
        case 'boots':
            shoeGeometry = new THREE.CylinderGeometry(0.08, 0.06, 0.15, 8);
            shoeScale = { x: 1, y: 1, z: 1.5 };
            break;
        case 'formal':
            shoeGeometry = new THREE.SphereGeometry(0.05, 8, 8);
            shoeScale = { x: 2.0, y: 0.5, z: 2.5 };
            break;
        case 'sandals':
            shoeGeometry = new THREE.BoxGeometry(0.12, 0.02, 0.18);
            shoeScale = { x: 1, y: 1, z: 1 };
            break;
        default: // sneakers
            shoeGeometry = new THREE.SphereGeometry(0.06, 8, 8);
            shoeScale = { x: 1.8, y: 0.6, z: 2.2 };
    }
    
    for (let i = 0; i < 2; i++) {
        const shoe = new THREE.Mesh(
            shoeGeometry,
            new THREE.MeshPhongMaterial({
                color: shoeColor,
                shininess: 40
            })
        );
        shoe.scale.set(shoeScale.x, shoeScale.y, shoeScale.z);
        shoe.position.set(i === 0 ? 0.08 : -0.08, -0.08 * heightMultiplier, 0.12); // Schuhe auf Bodenebene
        bodyGroup.add(shoe);
    }


    
    // ADAPTIVE Brillen basierend auf Brillen-Auswahl
    let glasses = null;
    
    switch (custom.glasses) {
        case 'normal':
            glasses = new THREE.Group();
            // Zwei separate Brillengläser
            for (let i = 0; i < 2; i++) {
                const eyeX = i === 0 ? 0.12 : -0.12;
                // Brillenrahmen für jedes Auge
                const frame = new THREE.Mesh(
                    new THREE.TorusGeometry(0.06, 0.008, 8, 16),
                    new THREE.MeshPhongMaterial({
                        color: 0x333333,
                        shininess: 60
                    })
                );
                frame.position.set(eyeX, head.position.y + 0.08, 0.21);
                glasses.add(frame);
                
                // Brillenglas
                const lens = new THREE.Mesh(
                    new THREE.CircleGeometry(0.055, 16),
                    new THREE.MeshPhongMaterial({
                        color: 0xffffff,
                        transparent: true,
                        opacity: 0.2,
                        shininess: 90
                    })
                );
                lens.position.set(eyeX, head.position.y + 0.08, 0.22);
                glasses.add(lens);
            }
            // Nasensteg
            const normalBridge = new THREE.Mesh(
                new THREE.CylinderGeometry(0.008, 0.008, 0.04, 8),
                new THREE.MeshPhongMaterial({
                    color: 0x333333,
                    shininess: 60
                })
            );
            normalBridge.position.set(0, head.position.y + 0.08, 0.21);
            normalBridge.rotation.z = Math.PI / 2;
            glasses.add(normalBridge);
            break;
        case 'sunglasses':
            glasses = new THREE.Group();
            // Zwei separate Sonnenbrillen-Gläser
            for (let i = 0; i < 2; i++) {
                const eyeX = i === 0 ? 0.12 : -0.12;
                // Dunkle Gläser
                const darkLens = new THREE.Mesh(
                    new THREE.CircleGeometry(0.065, 16),
                    new THREE.MeshPhongMaterial({
                        color: 0x1a1a1a,
                        shininess: 120,
                        transparent: true,
                        opacity: 0.9
                    })
                );
                darkLens.position.set(eyeX, head.position.y + 0.08, 0.22);
                glasses.add(darkLens);
                
                // Coole Rahmen
                const coolFrame = new THREE.Mesh(
                    new THREE.TorusGeometry(0.07, 0.01, 8, 16),
                    new THREE.MeshPhongMaterial({
                        color: 0x2a2a2a,
                        shininess: 90
                    })
                );
                coolFrame.position.set(eyeX, head.position.y + 0.08, 0.21);
                glasses.add(coolFrame);
            }
            // Nasensteg
            const sunBridge = new THREE.Mesh(
                new THREE.CylinderGeometry(0.01, 0.01, 0.04, 8),
                new THREE.MeshPhongMaterial({
                    color: 0x2a2a2a,
                    shininess: 90
                })
            );
            sunBridge.position.set(0, head.position.y + 0.08, 0.21);
            sunBridge.rotation.z = Math.PI / 2;
            glasses.add(sunBridge);
            break;
        case 'reading':
            glasses = new THREE.Group();
            // Zwei separate Lesebrille-Gläser
            for (let i = 0; i < 2; i++) {
                const eyeX = i === 0 ? 0.12 : -0.12;
                // Kleine Lesebrille
                const readingFrame = new THREE.Mesh(
                    new THREE.TorusGeometry(0.05, 0.006, 8, 16),
                    new THREE.MeshPhongMaterial({
                        color: 0x8B4513,
                        shininess: 40
                    })
                );
                readingFrame.position.set(eyeX, head.position.y + 0.06, 0.21);
                glasses.add(readingFrame);
                
                // Lesebrille-Glas
                const readingLens = new THREE.Mesh(
                    new THREE.CircleGeometry(0.045, 16),
                    new THREE.MeshPhongMaterial({
                        color: 0xffffff,
                        transparent: true,
                        opacity: 0.15,
                        shininess: 80
                    })
                );
                readingLens.position.set(eyeX, head.position.y + 0.06, 0.22);
                glasses.add(readingLens);
            }
            // Nasensteg
            const readingBridge = new THREE.Mesh(
                new THREE.CylinderGeometry(0.006, 0.006, 0.03, 8),
                new THREE.MeshPhongMaterial({
                    color: 0x8B4513,
                    shininess: 40
                })
            );
            readingBridge.position.set(0, head.position.y + 0.06, 0.21);
            readingBridge.rotation.z = Math.PI / 2;
            glasses.add(readingBridge);
            break;
        default: // none
            // Keine Brille
            break;
    }
    
    if (glasses) {
        bodyGroup.add(glasses);
        
        // Korrigiere Brillen-Position
        glasses.children.forEach(child => {
            if (child.geometry && child.geometry.type === 'TorusGeometry') {
                child.position.set(0, head.position.y + 0.05, 0.22);
            } else if (child.geometry && child.geometry.type === 'CircleGeometry') {
                child.position.set(0, head.position.y + 0.05, 0.23);
            }
        });
    }
    
    // ADAPTIVE Schmuck basierend auf Schmuck-Auswahl
    let jewelry = null;
    
    switch (custom.jewelry) {
        case 'watch':
            jewelry = new THREE.Mesh(
                new THREE.CylinderGeometry(0.03, 0.03, 0.02, 16),
                new THREE.MeshPhongMaterial({
                    color: 0xFFD700,
                    shininess: 100
                })
            );
            jewelry.position.set(0.15, body.position.y, 0);
            jewelry.rotation.z = Math.PI / 2;
            break;
        case 'chain':
            jewelry = new THREE.Group();
            // Hauptkette
            const mainChain = new THREE.Mesh(
                new THREE.TorusGeometry(0.1, 0.006, 8, 16),
                new THREE.MeshPhongMaterial({
                    color: 0xFFD700,
                    shininess: 120
                })
            );
            mainChain.position.set(0, body.position.y + 0.18, 0.14);
            jewelry.add(mainChain);
            
            // Kleine Kettenglieder für Detaileffekt
            for (let i = 0; i < 8; i++) {
                const angle = (i / 8) * Math.PI * 2;
                const link = new THREE.Mesh(
                    new THREE.TorusGeometry(0.015, 0.004, 6, 8),
                    new THREE.MeshPhongMaterial({
                        color: 0xFFD700,
                        shininess: 120
                    })
                );
                link.position.set(
                    Math.sin(angle) * 0.1,
                    body.position.y + 0.18 + Math.cos(angle) * 0.03,
                    0.14
                );
                link.rotation.x = angle;
                jewelry.add(link);
            }
            
            // Anhänger
            const pendant = new THREE.Mesh(
                new THREE.SphereGeometry(0.02, 8, 8),
                new THREE.MeshPhongMaterial({
                    color: 0xFFD700,
                    shininess: 140
                })
            );
            pendant.position.set(0, body.position.y + 0.1, 0.15);
            jewelry.add(pendant);
            break;
        case 'rings':
            jewelry = new THREE.Group();
            for (let i = 0; i < 3; i++) {
                const ring = new THREE.Mesh(
                    new THREE.TorusGeometry(0.01, 0.003, 8, 16),
                    new THREE.MeshPhongMaterial({
                        color: 0xFFD700,
                        shininess: 100
                    })
                );
                ring.position.set(0.2 + i * 0.015, body.position.y - 0.1, 0.05);
                ring.rotation.x = Math.PI / 2;
                jewelry.add(ring);
            }
            break;
        default: // none
            // Kein Schmuck
            break;
    }
    
    if (jewelry) {
        bodyGroup.add(jewelry);
    }
    
    // ADAPTIVE Rucksack basierend auf Rucksack-Auswahl
    let backpack = null;
    
    switch (custom.backpack) {
        case 'school':
            backpack = new THREE.Mesh(
                new THREE.BoxGeometry(0.2, 0.3, 0.1),
                new THREE.MeshPhongMaterial({
                    color: 0x0066CC,
                    shininess: 30
                })
            );
            backpack.position.set(0, body.position.y + 0.1, -0.15);
            break;
        case 'hiking':
            backpack = new THREE.Mesh(
                new THREE.BoxGeometry(0.25, 0.35, 0.15),
                new THREE.MeshPhongMaterial({
                    color: 0x228B22,
                    shininess: 20
                })
            );
            backpack.position.set(0, body.position.y + 0.1, -0.18);
            break;
        case 'stylish':
            backpack = new THREE.Mesh(
                new THREE.BoxGeometry(0.18, 0.25, 0.08),
                new THREE.MeshPhongMaterial({
                    color: 0x8B4513,
                    shininess: 60
                })
            );
            backpack.position.set(0, body.position.y + 0.1, -0.12);
            break;
        default: // none
            // Kein Rucksack
            break;
    }
    
    if (backpack) {
        bodyGroup.add(backpack);
    }

    // Eindeutige Zufallswerte für jeden Charakter (basierend auf Farbe als Seed)
    const characterSeed = parseInt(colorHex.replace('#', ''), 16) || Math.random() * 10000;
    const timeOffset = (characterSeed % 1000) / 100; // 0-10 Sekunden Verschiebung
    const speedVariation = 0.8 + ((characterSeed % 100) / 250); // 0.8-1.2x Geschwindigkeit
    const jumpFrequency = 0.1 + ((characterSeed % 50) / 500); // Verschiedene Sprungfrequenzen
    
    // Sprungstatus für diesen Charakter
    let currentJumpType = 'none'; // 'none', 'normal', 'spin'
    let jumpStartTime = 0;
    let jumpDuration = 0;
    let lastJumpTriggerTime = -10; // Verhindert sofortige Wiederholung
    
    group.userData = {
        characterSeed: characterSeed,
        timeOffset: timeOffset,
        speedVariation: speedVariation,
        jumpFrequency: jumpFrequency,
        animation: time => {
            // Angepasste Zeit für diesen spezifischen Charakter
            const adjustedTime = (time + timeOffset) * speedVariation;
            // ADAPTIVE Animationen basierend auf Animationsstil
            let animationSpeed = 2 * speedVariation;
            let animationIntensity = 0.03;
            
            switch (custom.animationStyle) {
                case 'energetic':
                    animationSpeed = 4 * speedVariation;
                    animationIntensity = 0.05;
                    break;
                case 'calm':
                    animationSpeed = 1 * speedVariation;
                    animationIntensity = 0.02;
                    break;
                case 'quirky':
                    animationSpeed = 3 * speedVariation;
                    animationIntensity = 0.06;
                    break;
                default: // normal
                    animationSpeed = 2 * speedVariation;
                    animationIntensity = 0.03;
            }
            
            // Seitliches Wackeln für Oberkörper mit anpassbarer Intensität
            if(bodyGroup) {
                // Basis Y-Position (kein vertikales Bewegen mehr)
                bodyGroup.position.y = 0;
                
                // Seitliches Wackeln im Rhythmus
                let swayIntensity = 0.08;
                switch (custom.idleStyle) {
                    case 'fidgety':
                        swayIntensity = 0.12;
                        break;
                    case 'relaxed':
                        swayIntensity = 0.05;
                        break;
                    case 'proud':
                        swayIntensity = 0.03;
                        break;
                    default: // normal
                        swayIntensity = 0.08;
                }
                
                // Seitliches Wackeln (links-rechts) mit individueller Zeit
                bodyGroup.rotation.z = Math.sin(adjustedTime * animationSpeed * 0.8) * swayIntensity;
                
                // Sprunglogik mit diskreten Einzelsprüngen und Cooldown
                const timeSinceLastJump = adjustedTime - lastJumpTriggerTime;
                const minCooldown = 2.0; // Mindestens 2 Sekunden zwischen Sprüngen
                
                const normalJumpTrigger = Math.sin(adjustedTime * jumpFrequency) > 0.988;
                const spinJumpTrigger = Math.sin(adjustedTime * jumpFrequency * 0.6) > 0.995;
                
                // Neuen Sprung starten (nur wenn nicht bereits am Springen UND Cooldown abgelaufen)
                if (currentJumpType === 'none' && timeSinceLastJump > minCooldown) {
                    if (spinJumpTrigger) {
                        currentJumpType = 'spin';
                        jumpStartTime = adjustedTime;
                        jumpDuration = 1.0; // 1 Sekunde für Drehsprung
                        lastJumpTriggerTime = adjustedTime;
                    } else if (normalJumpTrigger) {
                        currentJumpType = 'normal';
                        jumpStartTime = adjustedTime;
                        jumpDuration = 0.8; // 0.8 Sekunden für normalen Sprung
                        lastJumpTriggerTime = adjustedTime;
                    }
                }
                
                // Sprunganimation ausführen
                if (currentJumpType !== 'none') {
                    const jumpElapsed = adjustedTime - jumpStartTime;
                    const jumpProgress = Math.min(1, jumpElapsed / jumpDuration);
                    
                    if (jumpProgress >= 1) {
                        // Sprung beendet
                        currentJumpType = 'none';
                        bodyGroup.position.y = 0;
                        bodyGroup.rotation.y = 0;
                    } else {
                        // Sprung läuft
                        const jumpHeight = Math.sin(jumpProgress * Math.PI); // Parabel
                        
                        if (currentJumpType === 'spin') {
                            // Drehsprung: höher und mit 360° Drehung
                            bodyGroup.position.y = jumpHeight * 0.25;
                            bodyGroup.rotation.y = jumpProgress * Math.PI * 2; // Exakt eine Drehung
                        } else {
                            // Normaler Sprung: niedriger und ohne Drehung
                            bodyGroup.position.y = jumpHeight * 0.15;
                            bodyGroup.rotation.y = 0;
                        }
                    }
                } else {
                    // Normaler Stand
                    bodyGroup.position.y = 0;
                    bodyGroup.rotation.y = 0;
                }
                
                // Sanfte Kopfbewegung nur wenn Kopf vorhanden
                let headRotation = 0.1;
                switch (custom.idleStyle) {
                    case 'fidgety':
                        headRotation = 0.15;
                        break;
                    case 'relaxed':
                        headRotation = 0.05;
                        break;
                    case 'proud':
                        headRotation = 0.02;
                        break;
                    default: // normal
                        headRotation = 0.1;
                }
                
                bodyGroup.children.forEach(child => {
                    if (child === head) {
                        child.rotation.y = Math.sin(adjustedTime * 1.2) * headRotation;
                    }
                });
            }

            // ADAPTIVE Blinzeln (nur in bodyGroup suchen)
            let eyeWhiteFound = 0;
            const isBlinking = Math.sin(adjustedTime * 1.5) > 0.9;
            
            if (bodyGroup) {
                bodyGroup.children.forEach(child => {
                    // Augen blinzeln
                    if (child.geometry && child.geometry.type === 'SphereGeometry' &&
                        child.geometry.parameters && Math.abs(child.geometry.parameters.radius - eyeSize) < 0.001 && eyeWhiteFound < 2) {
                        eyeWhiteFound++;
                        if (isBlinking) {
                            child.scale.y = 0.1; // Blinzeln
                        } else {
                            child.scale.y = eyeScale.y; // Zurück zu normaler Größe
                        }
                    }
                    
                    // Pupillen während Blinzeln verstecken
                    if (child.geometry && child.geometry.type === 'SphereGeometry' &&
                        child.geometry.parameters && (child.geometry.parameters.radius === eyeSize * 0.6 || child.geometry.parameters.radius === eyeSize * 0.7 || child.geometry.parameters.radius === eyeSize * 0.8)) {
                        if (isBlinking) {
                            child.visible = false; // Pupillen verstecken
                        } else {
                            child.visible = true; // Pupillen wieder zeigen
                        }
                    }
                });
            }

            // BART BEWEGUNG
            if (facial_hair && custom.beardStyle === 'mustache') {
                facial_hair.rotation.z = Math.PI + Math.sin(adjustedTime * 6) * 0.15;
            }

            // HUT WACKELN
            if (hat && custom.hat === 'formal') {
                hat.rotation.z = Math.sin(adjustedTime * 4) * 0.1;
            }


            // PUPILLEN BEWEGUNG (nur bei quirky)
            if (custom.animationStyle === 'quirky' && bodyGroup) {
                bodyGroup.children.forEach((child) => {
                    if (child.geometry && child.geometry.type === 'SphereGeometry' &&
                        child.geometry.parameters && (child.geometry.parameters.radius === eyeSize * 0.6 || child.geometry.parameters.radius === eyeSize * 0.7 || child.geometry.parameters.radius === eyeSize * 0.8)) {
                        const isRightPupil = child.position.z > 0.24; // Pupillen sind bei z > 0.24
                        const baseX = isRightPupil ? 0.12 : -0.12;
                        const baseY = head.position.y + 0.08;
                        child.position.x = baseX + Math.sin(adjustedTime * 8) * 0.01;
                        child.position.y = baseY + Math.cos(adjustedTime * 6) * 0.005;
                    }
                });
            }

            // MUND SPRECHEN
            if (mouth) {
                let mouthAnimation = 0.4;
                switch (custom.voiceType) {
                    case 'deep':
                        mouthAnimation = 0.6;
                        break;
                    case 'high':
                        mouthAnimation = 0.2;
                        break;
                    case 'robotic':
                        mouthAnimation = 0.3;
                        break;
                    default: // normal
                        mouthAnimation = 0.4;
                }
                mouth.scale.y = 0.8 + Math.abs(Math.sin(adjustedTime * 5)) * mouthAnimation;
                mouth.scale.x = 1.5 + Math.sin(adjustedTime * 5) * 0.2;
            }
            
            // BRILLEN SPIEGELUNG
            if (glasses && custom.glasses === 'sunglasses') {
                glasses.rotation.y = Math.sin(adjustedTime * 0.5) * 0.1;
            }
            
            // SCHMUCK GLÄNZEN
            if (jewelry && custom.jewelry !== 'none') {
                // Subtile Rotation für Glänzeffekt
                if (custom.jewelry === 'chain') {
                    jewelry.rotation.z = Math.sin(adjustedTime * 2) * 0.05;
                }
            }
        }
    };
    return group;
}