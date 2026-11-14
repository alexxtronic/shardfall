// Shardfall: Void Abyssal Lair (special tech building), from art/void_buildings/concepts/shardfall_void_abyss.png
// Front faces +Z. 4 x 4 m footprint. A wide crater of chitin plates over crimson flesh round a deep
// pit glowing acid green, with slime strands down into it; giant bone horns arch up and inward from
// the back of the rim, egg clusters sit in alcoves on the flanks and bone claws ring the base.
const meta = { name: 'Void Abyssal Lair', role: 'building' };

const RAD = Math.PI / 180;

function orient(parent, name, pos, theta, elev) {
  const g = createPivot(name, pos, parent);
  g.rotation.set(0, -theta * RAD, -(90 - elev) * RAD);
  return g;
}
function claw(name, ctrl, r0, mat, parent) {
  const path = catmullRomPath(ctrl, 3);
  const radii = path.map((_, i) => Math.max(0.014, r0 * (1 - i / (path.length - 1)) ** 0.9));
  return createPart(name, taperedTube(path, radii, { radialSegments: 6 }), mat, { parent });
}
const ring = (theta, r, y) => [Math.cos(theta * RAD) * r, y, Math.sin(theta * RAD) * r];

async function build() {
  const root = createRoot('VoidAbyssalLair');
  const chitin = gameMaterial(0x6b2f93, { roughness: 0.32, metalness: 0.1, name: 'chitin', flatShading: false });
  const chitinDark = gameMaterial(0x40195c, { roughness: 0.4, metalness: 0.05, name: 'chitin_dark', flatShading: false });
  const flesh = gameMaterial(0x7c1f37, { roughness: 0.45, name: 'flesh', flatShading: false });
  const throat = gameMaterial(0x3a0814, { roughness: 0.5, name: 'flesh_dark', flatShading: false });
  const bone = gameMaterial(0xdcc9a6, { roughness: 0.5, name: 'bone', flatShading: false });
  const acid = gameMaterial(0x8cff3a, { emissive: 0x8cff3a, emissiveIntensity: 1.8, roughness: 0.2, name: 'glow_acid', flatShading: false });
  const team = gameMaterial(0x8cff3a, { emissive: 0x8cff3a, emissiveIntensity: 1.0, roughness: 0.3, name: 'team', flatShading: false });

  // crater body, flesh lips and the pit
  createPart('Crater', await revolveProfile([[0.7, 0.3], [1.68, 0], [1.62, 0.35], [1.42, 0.8], [1.12, 1.02], [0.9, 0.95], [0.72, 0.55]], { segments: 24, smooth: true }), chitinDark, { parent: root });
  createPart('Lips', torusGeo(0.98, 0.2, 8, 24), flesh, { position: [0, 0.98, 0], rotation: [90, 0, 0], parent: root });
  createPart('PitWall', cylinderGeo(0.82, 0.62, 0.6, 26), throat, { position: [0, 0.6, 0], parent: root });
  createPart('Pool', sphereGeo(0.72, 14, 6), acid, { position: [0, 0.88, 0], scale: [1, 0.12, 1], parent: root });
  createPart('PoolCore', sphereGeo(0.35, 14, 8), acid, { position: [0, 0.9, 0], scale: [1, 0.35, 1], parent: root });
  for (let k = 0; k < 8; k++) {
    const th = k * 45 + 10;
    createPart(`Fold${k}`, sphereGeo(0.16, 8, 6), flesh, { position: ring(th, 1.0, 1.12), scale: [1, 0.7, 1], parent: root });
  }
  // slime strands hanging from the rim into the pool
  for (const th of [30, 110, 200, 290]) {
    const a = ring(th, 0.85, 1.05), b = ring(th + 12, 0.45, 0.9), m = ring(th + 6, 0.68, 0.86);
    const path = catmullRomPath([a, m, b], 3);
    createPart(`Strand${th}`, taperedTube(path, path.map((_, i) => 0.035 - 0.012 * i / (path.length - 1)), { radialSegments: 5 }), acid, { parent: root });
  }

  // chitin plates down the outer slope, and a crest at the front
  for (const th of [0, 40, 80, 120, 160, 200, 240, 280, 320]) {
    const g = orient(root, `Plate${th}`, ring(th, 1.56, 0.5), th, 38);
    createPart(`PlateShell${th}`, sphereGeo(0.62, 9, 6), chitin, { scale: [0.75, 0.26, 0.9], parent: g });
    claw(`PlateSpur${th}`, [[0.28, 0.05, 0], [0.45, 0.12, 0], [0.55, 0.3, 0]], 0.07, bone, g);
  }
  for (const th of [20, 60, 100, 140, 180, 220, 260, 300, 340]) {
    const g = orient(root, `UpperPlate${th}`, ring(th, 1.28, 0.92), th, 55);
    createPart(`UpperPlateShell${th}`, sphereGeo(0.4, 8, 5), chitin, { scale: [0.75, 0.28, 0.85], parent: g });
  }
  const crest = orient(root, 'Crest', ring(90, 1.5, 0.72), 90, 40);
  createPart('CrestBone', coneGeo(0.24, 0.65, 6), bone, { position: [0.0, 0.3, 0], scale: [1, 1, 0.55], parent: crest });

  // giant horns arching up and inward from the back of the rim
  for (const [th, sc] of [[195, 0.8], [235, 1.0], [305, 1.0], [345, 0.8], [140, 0.55], [40, 0.55]]) {
    const g = createPivot(`Horn${th}`, [0, 0, 0], root);
    g.rotation.set(0, -th * RAD, 0);
    const k = sc;
    claw(`HornBone${th}`, [[1.2, 0.8, 0], [1.5, 0.8 + 0.8 * k, 0], [1.35, 0.8 + 1.6 * k, 0], [0.8, 0.8 + 2.1 * k, 0], [0.25 + 0.3 * (1 - k), 0.8 + 2.05 * k, 0]], 0.3 * k, bone, g);
    claw(`HornSpur${th}`, [[1.38, 0.8 + 1.2 * k, 0], [1.18, 0.8 + 1.22 * k, 0], [1.06, 0.8 + 1.38 * k, 0]], 0.08 * k, bone, g);
  }

  // egg clusters in alcoves on the flanks
  for (const th of [10, 170, 125, 55]) {
    const c = ring(th, 1.66, 0.3);
    createPart(`Alcove${th}`, sphereGeo(0.38, 8, 6), throat, { position: c, scale: [1, 0.8, 1], parent: root });
    [[0, 0.08, 0, 0.2], [0.14, -0.02, 0.1, 0.15], [-0.12, 0.0, -0.1, 0.14]].forEach(([dx, dy, dz, r], i) => {
      createPart(`Egg${th}${i}`, sphereGeo(r, 12, 8), acid, { position: [c[0] * 1.08 + dx, c[1] + dy, c[2] * 1.08 + dz], parent: root });
    });
  }

  // bone claws ringing the base
  for (let k = 0; k < 10; k++) {
    const th = k * 36 + 18;
    const g = createPivot(`BaseClaw${k}`, ring(th, 1.62, 0.0), root);
    g.rotation.set(0, -th * RAD, 0);
    claw(`BaseClawBone${k}`, [[-0.05, 0.12, 0], [0.18, 0.14, 0], [0.3, 0.28, 0], [0.3, 0.46, 0]], 0.12, bone, g);
  }
  for (const th of [70, 150, 250, 330]) {
    createPart(`Nodule${th}`, sphereGeo(0.1, 8, 6), team, { position: ring(th, 1.3, 0.9), parent: root });
  }
  return root;
}
