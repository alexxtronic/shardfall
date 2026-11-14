// Shardfall: Void Slime Spire (defence tower), from art/void_buildings/concepts/shardfall_void_slime_spire.png
// Front faces +Z. 2 x 2 m footprint. A root mound of chitin plates and bone claws, a twisting
// flesh stalk wrapped in plates, and a turning head (node "turret"): a swollen glowing slime sac
// cupped in chitin, ringed by curved bone spines, dripping slime.
const meta = { name: 'Void Slime Spire', role: 'building' };

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
const ring = (theta, r, y) => [Math.cos(theta * RAD) * r, y, Math.sin(theta * RAD) * r];

async function build() {
  const root = createRoot('VoidSlimeSpire');
  const chitin = gameMaterial(0x6b2f93, { roughness: 0.32, metalness: 0.1, name: 'chitin', flatShading: false });
  const chitinDark = gameMaterial(0x40195c, { roughness: 0.4, metalness: 0.05, name: 'chitin_dark', flatShading: false });
  const flesh = gameMaterial(0x7c1f37, { roughness: 0.45, name: 'flesh', flatShading: false });
  const bone = gameMaterial(0xdcc9a6, { roughness: 0.5, name: 'bone', flatShading: false });
  const acid = gameMaterial(0x8cff3a, { emissive: 0x8cff3a, emissiveIntensity: 1.7, roughness: 0.15, name: 'glow_acid', flatShading: false });
  const team = gameMaterial(0x8cff3a, { emissive: 0x8cff3a, emissiveIntensity: 1.0, roughness: 0.3, name: 'team', flatShading: false });

  // root mound: flesh, chitin plates, glowing sacs and bone claw feet
  createPart('Root', await dome(0.82, 0.42, 16), flesh, { parent: root });
  for (const th of [10, 85, 160, 235, 310]) {
    const g = orient(root, `RootPlate${th}`, ring(th, 0.55, 0.24), th, 28);
    createPart(`RootPlateShell${th}`, sphereGeo(0.48, 10, 7), chitin, { scale: [0.75, 0.3, 0.85], parent: g });
  }
  for (const th of [50, 195, 275]) {
    createPart(`RootSac${th}`, sphereGeo(0.17, 12, 8), acid, { position: ring(th, 0.66, 0.16), parent: root });
  }
  for (const th of [30, 100, 170, 250, 320]) {
    const g = createPivot(`Foot${th}`, ring(th, 0.68, 0.0), root);
    g.rotation.set(0, -th * RAD, 0);
    claw(`FootClaw${th}`, [[-0.05, 0.12, 0], [0.18, 0.14, 0], [0.3, 0.28, 0], [0.3, 0.48, 0]], 0.12, bone, g);
  }

  // twisting stalk wrapped in chitin plates spiralling up
  const stalkPath = catmullRomPath([[0, 0.2, 0], [0.08, 0.7, -0.05], [-0.06, 1.2, 0.04], [0.05, 1.7, 0.0], [0.0, 2.05, 0.02]], 4);
  createPart('Stalk', taperedTube(stalkPath, stalkPath.map((_, i) => 0.3 - 0.12 * i / (stalkPath.length - 1)), { radialSegments: 10 }), flesh, { parent: root });
  [[0.75, 20], [1.05, 140], [1.35, 260], [1.65, 30]].forEach(([y, th], i) => {
    const g = orient(root, `Wrap${i}`, ring(th, 0.18, y), th, 72);
    createPart(`WrapShell${i}`, sphereGeo(0.44, 10, 7), chitin, { scale: [0.55, 0.28, 0.9], parent: g });
    claw(`WrapSpike${i}`, [[0.1, 0.06, 0], [0.26, 0.14, 0], [0.36, 0.36, 0], [0.3, 0.55, 0]], 0.09, bone, g);
  });
  for (const [y, th] of [[0.95, 200], [1.5, 100]]) {
    createPart(`StalkSac${y}`, sphereGeo(0.09, 10, 7), acid, { position: ring(th, 0.2, y), scale: [0.8, 1.3, 0.8], parent: root });
  }

  // the turning head
  const head = createPivot('turret', [0, 2.05, 0], root);
  head.name = 'turret';
  createPart('Cup', sphereGeo(0.5, 14, 9), chitinDark, { position: [0, 0.05, 0], scale: [1, 0.45, 1], parent: head });
  for (const th of [0, 72, 144, 216, 288]) {
    const g = orient(head, `CupPlate${th}`, ring(th, 0.38, 0.1), th, 25);
    createPart(`CupPlateShell${th}`, sphereGeo(0.3, 10, 7), chitin, { scale: [0.8, 0.3, 0.9], parent: g });
  }
  createPart('Sac', sphereGeo(0.48, 18, 12), acid, { position: [0, 0.42, 0.06], scale: [1, 0.88, 1.05], parent: head });
  for (const [x, y, z, r] of [[0.22, 0.62, 0.3, 0.16], [-0.28, 0.5, 0.28, 0.14], [0.05, 0.75, -0.2, 0.15], [-0.2, 0.7, 0.05, 0.13]]) {
    createPart(`Lump${x}${z}`, sphereGeo(r, 10, 8), acid, { position: [x, y, z], parent: head });
  }
  // drips hanging from the front of the sac
  for (const [x, z, len] of [[0.12, 0.42, 0.42], [-0.08, 0.4, 0.3], [0.3, 0.28, 0.24]]) {
    const top = [x, 0.18, z];
    createPart(`Drip${x}`, cylinderGeo(0.035, 0.02, len, 8), acid, { position: [x, 0.18 - len / 2, z], parent: head });
    createPart(`DripDrop${x}`, sphereGeo(0.045, 8, 6), acid, { position: [x, 0.18 - len, z], scale: [1, 1.3, 1], parent: head });
  }
  // curved bone spines ringing the sac, pointing up and out
  for (const th of [20, 80, 150, 210, 260, 320]) {
    const g = createPivot(`Spine${th}`, ring(th, 0.4, 0.3), head);
    g.rotation.set(0, -th * RAD, 0);
    claw(`SpineBone${th}`, [[-0.05, 0, 0], [0.2, 0.15, 0], [0.34, 0.42, 0], [0.3, 0.72, 0]], 0.13, bone, g);
  }
  for (const th of [110, 290]) {
    createPart(`Nodule${th}`, sphereGeo(0.06, 8, 6), team, { position: ring(th, 0.46, 0.06), parent: head });
  }
  for (const th of [60, 240]) {
    createPart(`RootNodule${th}`, sphereGeo(0.07, 8, 6), team, { position: ring(th, 0.72, 0.12), parent: root });
  }
  return root;
}
