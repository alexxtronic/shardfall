// Shardfall: Void Spawning Nest (infantry), from art/void_buildings/concepts/shardfall_void_nest.png
// Front faces +Z. 3 x 3 m footprint. A hooded chitin mound with a big flesh-lipped tunnel at the
// front glowing acid green inside, layered plates, bone horns along the ridge, claw feet round
// the base and glowing egg sacs on the flanks.
const meta = { name: 'Void Spawning Nest', role: 'building' };

const RAD = Math.PI / 180;

function orient(parent, name, pos, theta, elev) {
  const g = createPivot(name, pos, parent);
  g.rotation.set(0, -theta * RAD, -(90 - elev) * RAD);
  return g;
}
function claw(name, ctrl, r0, mat, parent) {
  const path = catmullRomPath(ctrl, 3);
  const radii = path.map((_, i) => Math.max(0.012, r0 * (1 - i / (path.length - 1)) ** 0.9));
  return createPart(name, taperedTube(path, radii, { radialSegments: 6 }), mat, { parent });
}
async function dome(R, h, seg) {
  const prof = [[0, 0], [R, 0], [R * 0.98, h * 0.28], [R * 0.86, h * 0.6], [R * 0.62, h * 0.85], [R * 0.3, h * 0.97], [0, h]];
  return revolveProfile(prof, { segments: seg, smooth: true });
}
const MZ = -0.25;   // the mound sits back so the tunnel stands proud at the front
const onDome = (theta, r, y) => [Math.cos(theta * RAD) * r, y, MZ + Math.sin(theta * RAD) * r];

async function build() {
  const root = createRoot('VoidSpawningNest');
  const chitin = gameMaterial(0x6b2f93, { roughness: 0.32, metalness: 0.1, name: 'chitin', flatShading: false });
  const chitinDark = gameMaterial(0x40195c, { roughness: 0.4, metalness: 0.05, name: 'chitin_dark', flatShading: false });
  const flesh = gameMaterial(0x7c1f37, { roughness: 0.45, name: 'flesh', flatShading: false });
  const throat = gameMaterial(0x3a0814, { roughness: 0.5, name: 'flesh_dark', flatShading: false });
  const bone = gameMaterial(0xdcc9a6, { roughness: 0.5, name: 'bone', flatShading: false });
  const acid = gameMaterial(0x8cff3a, { emissive: 0x8cff3a, emissiveIntensity: 1.6, roughness: 0.2, name: 'glow_acid', flatShading: false });
  const team = gameMaterial(0x8cff3a, { emissive: 0x8cff3a, emissiveIntensity: 1.0, roughness: 0.3, name: 'team', flatShading: false });

  // the mound, a flesh underlayer showing between the plates
  createPart('Flesh', await dome(1.22, 1.6, 18), flesh, { position: [0, 0.005, MZ + 0.05], parent: root });
  createPart('Mound', await dome(1.08, 2.05, 18), chitinDark, { position: [0, 0, MZ - 0.05], parent: root });

  // tunnel at the front: thick flesh lips, a dark throat and a green glow deep inside
  const tY = 0.86, tZ = 1.0;
  createPart('Collar', sphereGeo(1.0, 14, 9), chitinDark, { position: [0, 0.85, 0.42], scale: [1.0, 0.95, 0.6], parent: root });
  createPart('Lips', torusGeo(0.68, 0.17, 10, 28), flesh, { position: [0, tY, tZ], scale: [1, 1.0, 1.2], parent: root });
  createPart('Throat', cylinderGeo(0.72, 0.72, 0.3, 24), throat, { position: [0, tY, tZ - 0.18], rotation: [90, 0, 0], parent: root });
  createPart('Glow', cylinderGeo(0.5, 0.5, 0.04, 24), acid, { position: [0, tY - 0.04, tZ - 0.01], rotation: [90, 0, 0], parent: root });
  createPart('GlowCore', sphereGeo(0.3, 12, 8), acid, { position: [0, tY - 0.06, tZ - 0.02], scale: [1, 1, 0.3], parent: root });
  createPart('InnerRing', torusGeo(0.56, 0.07, 8, 26), flesh, { position: [0, tY, tZ + 0.0], parent: root });
  createPart('Floor', sphereGeo(0.45, 12, 6), acid, { position: [0, 0.18, tZ - 0.15], scale: [1, 0.2, 1.1], parent: root });
  for (let k = 0; k < 6; k++) {
    const a = (200 + k * 28) * RAD;
    createPart(`Fold${k}`, sphereGeo(0.12, 8, 6), flesh, { position: [Math.cos(a) * 0.74, tY - Math.sin(a) * 0.76, tZ + 0.12], parent: root });
  }
  // the hood plate overhanging the tunnel, with a bone crest
  const hood = orient(root, 'Hood', [0, 1.62, 0.72], 90, 28);
  createPart('HoodShell', sphereGeo(1.0, 12, 8), chitin, { scale: [0.62, 0.26, 1.0], parent: hood });
  createPart('HoodRidge', sphereGeo(0.5, 10, 6), chitinDark, { position: [-0.15, 0.12, 0], scale: [1.1, 0.4, 0.4], parent: hood });

  // layered plates down the flanks and back (front left open for the tunnel)
  for (const th of [20, 55, 125, 160, 200, 245, 290, 335]) {
    const g = orient(root, `PlateLow${th}`, onDome(th, 1.12, 0.62), th, 35);
    createPart(`PlateLowShell${th}`, sphereGeo(0.72, 11, 7), chitin, { scale: [0.7, 0.26, 0.85], parent: g });
  }
  for (const th of [10, 70, 110, 170, 230, 310]) {
    const g = orient(root, `PlateHigh${th}`, onDome(th, 0.78, 1.45), th, 55);
    createPart(`PlateHighShell${th}`, sphereGeo(0.62, 11, 7), chitin, { scale: [0.75, 0.28, 0.85], parent: g });
  }

  // bone horns along the ridge, curving back, biggest at the front
  const horns = [[-0.62, 0.2, 1.72, 0.27, 28], [-0.2, -0.15, 2.0, 0.32, 8], [0.28, -0.2, 1.98, 0.34, -10], [0.68, 0.12, 1.7, 0.27, -30]];
  horns.forEach(([x, z, y, r, lean], i) => {
    const g = createPivot(`Horn${i}`, [x, y, z], root);
    g.rotation.set(0, 0, lean * RAD);
    claw(`HornBone${i}`, [[0, -0.1, 0.05], [0, 0.35, 0.12], [0, 0.75, -0.05], [0, 0.95, -0.4]].map(([x, yy, zz]) => [x, yy * r / 0.3, zz * r / 0.3]), r * 0.62, bone, g);
  });
  for (const s of [-1, 1]) {
    const g = createPivot(`SideHorn${s}`, [s * 0.9, 1.05, -0.4], root);
    g.rotation.set(0, 0, -s * 30 * RAD);
    claw(`SideHornBone${s}`, [[0, 0, 0.05], [0, 0.3, 0.08], [0, 0.6, -0.05], [0, 0.75, -0.3]], 0.15, bone, g);
  }

  // claw feet round the base and two fangs at the tunnel mouth
  for (const th of [15, 50, 130, 165, 210, 250, 290, 330]) {
    const g = createPivot(`Foot${th}`, onDome(th, 1.2, 0.0), root);
    g.rotation.set(0, -th * RAD, 0);
    createPart(`FootPlate${th}`, sphereGeo(0.42, 9, 6), chitin, { position: [0.05, 0.1, 0], scale: [1.1, 0.42, 0.75], parent: g });
    claw(`FootClaw${th}`, [[0.15, 0.12, 0], [0.38, 0.16, 0], [0.5, 0.3, 0], [0.5, 0.5, 0]], 0.1, bone, g);
  }
  for (const s of [-1, 1]) {
    claw(`Fang${s}`, [[s * 0.78, 0.05, 1.05], [s * 0.82, 0.35, 1.2], [s * 0.74, 0.6, 1.3], [s * 0.6, 0.72, 1.28]], 0.13, bone, root);
  }

  // egg sacs on the flanks
  for (const [x, y, z, r] of [[-1.1, 0.55, 0.2, 0.34], [-1.0, 0.92, -0.4, 0.28], [1.12, 0.52, 0.0, 0.3]]) {
    createPart(`Egg${x}${z}`, sphereGeo(r, 14, 10), acid, { position: [x, y, z], scale: [0.85, 1.05, 1], parent: root });
  }
  for (const [x, y, z] of [[0.8, 1.15, 0.35], [-0.8, 1.2, 0.35], [0, 1.9, -0.8], [1.0, 0.5, -0.9], [-1.05, 0.4, -0.9]]) {
    createPart(`Nodule${x}${z}`, sphereGeo(0.09, 8, 6), team, { position: [x, y, z], parent: root });
  }
  return root;
}
