// Shardfall: Void Hive Heart (main base), from art/void_buildings/concepts/shardfall_void_hive.png
// Front faces +Z. 5 x 5 m footprint. A chitin mound under layered purple plates with bone claws,
// glowing acid-green sacs, a toothed maw at the front glowing green inside, and claws splayed
// round the base. Materials: chitin, chitin_dark, flesh, bone, glow_acid, team (small nodules
// the game recolours to the player's colour).
const meta = { name: 'Void Hive Heart', role: 'building' };

const RAD = Math.PI / 180;

// a pivot at pos, turned to azimuth theta (degrees from +X toward +Z) with its local +Y tilted
// outward to elevation elev (90 = straight up, 0 = horizontal outward)
function orient(parent, name, pos, theta, elev) {
  const g = createPivot(name, pos, parent);
  g.rotation.set(0, -theta * RAD, -(90 - elev) * RAD);
  return g;
}

function onMound(theta, r, y) {
  return [Math.cos(theta * RAD) * r, y, Math.sin(theta * RAD) * r];
}

// a curved tapering bone claw; ctrl are control points in the parent frame
function claw(name, ctrl, r0, mat, parent) {
  const path = catmullRomPath(ctrl, 3);
  const radii = path.map((_, i) => Math.max(0.012, r0 * (1 - i / (path.length - 1)) ** 0.9));
  return createPart(name, taperedTube(path, radii, { radialSegments: 6 }), mat, { parent });
}

async function dome(R, h, seg) {
  const prof = [[0, 0], [R, 0], [R * 0.98, h * 0.28], [R * 0.86, h * 0.6], [R * 0.62, h * 0.85], [R * 0.3, h * 0.97], [0, h]];
  return revolveProfile(prof, { segments: seg, smooth: true });
}

async function build() {
  const root = createRoot('VoidHiveHeart');
  const chitin = gameMaterial(0x6b2f93, { roughness: 0.32, metalness: 0.1, name: 'chitin', flatShading: false });
  const chitinDark = gameMaterial(0x40195c, { roughness: 0.4, metalness: 0.05, name: 'chitin_dark', flatShading: false });
  const flesh = gameMaterial(0x7c1f37, { roughness: 0.45, name: 'flesh', flatShading: false });
  const bone = gameMaterial(0xdcc9a6, { roughness: 0.5, name: 'bone', flatShading: false });
  const acid = gameMaterial(0x8cff3a, { emissive: 0x8cff3a, emissiveIntensity: 1.7, roughness: 0.25, name: 'glow_acid', flatShading: false });
  const team = gameMaterial(0x8cff3a, { emissive: 0x8cff3a, emissiveIntensity: 1.0, roughness: 0.3, name: 'team', flatShading: false });

  // fleshy skirt and the mound itself
  createPart('Skirt', await dome(2.2, 0.4, 18), flesh, { position: [0, 0, 0], parent: root });
  createPart('Mound', await dome(1.85, 2.15, 20), chitinDark, { position: [0, 0, -0.1], parent: root });
  createPart('Crown', sphereGeo(1.0, 14, 9), chitinDark, { position: [0, 2.0, -0.35], scale: [1, 0.8, 0.95], parent: root });

  // glowing sacs between the plates
  const sacs = [[-0.6, 2.35, -0.55, 0.55], [0.45, 2.45, -0.45, 0.6], [1.15, 1.95, -0.7, 0.45], [-1.62, 1.0, 0.25, 0.46], [1.66, 1.0, 0.3, 0.46], [-1.1, 0.75, 1.3, 0.38], [0.2, 1.6, -1.55, 0.45]];
  sacs.forEach(([x, y, z, r], i) => {
    createPart(`Sac${i}`, sphereGeo(r, 12, 8), acid, { position: [x, y, z], scale: [1, 0.9, 1], parent: root });
  });

  // lower ring of chitin plates, each with a bone claw at its tip (skip the maw at 90)
  for (const th of [10, 50, 130, 170, 210, 250, 290, 330]) {
    const g = orient(root, `PlateLow${th}`, onMound(th, 1.5, 0.95), th, 40);
    createPart(`PlateLowShell${th}`, sphereGeo(0.95, 11, 7), chitin, { position: [0, 0, 0], scale: [0.75, 0.28, 0.85], parent: g });
    createPart(`PlateLowRidge${th}`, sphereGeo(0.5, 9, 6), chitinDark, { position: [-0.1, 0.12, 0], scale: [1.1, 0.35, 0.5], parent: g });
    claw(`PlateLowClaw${th}`, [[0.35, 0.05, 0], [0.62, 0.18, 0], [0.8, 0.48, 0], [0.82, 0.82, 0]], 0.15, bone, g);
  }
  // upper ring, steeper, with bigger claws sweeping up
  for (const th of [30, 150, 210, 270, 330]) {
    const g = orient(root, `PlateHigh${th}`, onMound(th, 1.0, 2.25), th, 55);
    createPart(`PlateHighShell${th}`, sphereGeo(0.85, 11, 7), chitin, { position: [0, 0, 0], scale: [0.8, 0.3, 0.85], parent: g });
    claw(`PlateHighClaw${th}`, [[0.35, 0.1, 0], [0.7, 0.3, 0], [0.9, 0.7, 0], [0.8, 1.15, 0]], 0.17, bone, g);
  }
  // three crown horns sweeping back
  for (const [x, lean] of [[-0.55, -14], [0.1, 0], [0.75, 12]]) {
    const g = createPivot(`Horn${x}`, [x, 2.55, -0.2], root);
    g.rotation.set(0, 0, lean * RAD);
    claw(`HornBone${x}`, [[0, 0, 0.2], [0, 0.5, 0.05], [0, 0.95, -0.35], [0, 1.15, -0.85]], 0.2, bone, g);
  }

  // the maw at the front: green-lit tunnel, crimson lips, bone teeth
  const mawY = 1.0, mawZ = 1.62;
  createPart('MawHood', sphereGeo(1.15, 14, 9), chitin, { position: [0, mawY + 0.35, mawZ - 0.5], scale: [1.15, 0.95, 0.75], parent: root });
  createPart('MawGlow', cylinderGeo(0.86, 0.86, 0.2, 24), acid, { position: [0, mawY, mawZ + 0.1], rotation: [90, 0, 0], scale: [1, 1, 0.85], parent: root });
  createPart('MawLips', torusGeo(0.9, 0.2, 10, 28), flesh, { position: [0, mawY, mawZ + 0.18], scale: [1, 0.85, 1], parent: root });
  for (let k = 0; k < 7; k++) {
    const a = (200 + k * 23.3) * RAD;  // upper arc, teeth pointing down and in
    const px = Math.cos(a) * 0.88, py = mawY - Math.sin(a) * 0.76;
    const g = createPivot(`Tooth${k}`, [px, py, mawZ + 0.3], root);
    g.rotation.set(0, 0, Math.atan2(-px, py - mawY) + Math.PI);
    createPart(`ToothBone${k}`, coneGeo(0.11, 0.44, 8), bone, { position: [0, 0.2, 0], parent: g });
  }
  for (const s of [-1, 1]) {
    createPart(`LowerFang${s}`, coneGeo(0.1, 0.36, 8), bone, { position: [s * 0.4, mawY - 0.68, mawZ + 0.32], parent: root });
    // tusks framing the maw
    claw(`Tusk${s}`, [[s * 1.05, 0.15, mawZ], [s * 1.25, 0.65, mawZ + 0.3], [s * 1.15, 1.3, mawZ + 0.5], [s * 0.8, 1.65, mawZ + 0.55]], 0.19, bone, root);
  }

  // claws splayed round the base
  for (const th of [20, 60, 120, 160, 200, 240, 280, 320]) {
    const g = createPivot(`BaseClaw${th}`, onMound(th, 1.6, 0.1), root);
    g.rotation.set(0, -th * RAD, 0);
    createPart(`BasePlate${th}`, sphereGeo(0.55, 9, 6), chitin, { position: [0.1, 0.12, 0], scale: [1.2, 0.3, 0.7], parent: g });
    claw(`BaseClawBone${th}`, [[0.15, 0.15, 0], [0.4, 0.2, 0], [0.58, 0.35, 0], [0.64, 0.62, 0]], 0.12, bone, g);
  }

  // team nodules: small lit pustules on the plates and round the maw
  const nod = [[-0.95, 1.55, 0.95], [0.95, 1.55, 0.95], [-1.65, 0.55, 0.75], [1.65, 0.55, 0.75], [0, 2.75, 0.2], [-1.2, 1.9, -1.0], [1.2, 1.9, -1.0], [0, 1.1, -1.85]];
  nod.forEach(([x, y, z], i) => {
    createPart(`Nodule${i}`, sphereGeo(0.12, 8, 6), team, { position: [x, y, z], parent: root });
  });
  return root;
}
