// Shardfall: Void Maw (extractor), from art/void_buildings/concepts/shardfall_void_maw.png
// Front faces +Z. 3 x 3 m footprint. A ring of chitin humps round a crimson gullet that sucks
// up the slime pile, bone teeth curling inward from the rim, acid sacs at the sides and purple
// slime spilling out at the front.
const meta = { name: 'Void Maw', role: 'building' };

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

async function build() {
  const root = createRoot('VoidMaw');
  const chitin = gameMaterial(0x6b2f93, { roughness: 0.32, metalness: 0.1, name: 'chitin', flatShading: false });
  const chitinDark = gameMaterial(0x40195c, { roughness: 0.4, metalness: 0.05, name: 'chitin_dark', flatShading: false });
  const flesh = gameMaterial(0x7c1f37, { roughness: 0.45, name: 'flesh', flatShading: false });
  const throat = gameMaterial(0x3a0814, { roughness: 0.5, name: 'flesh_dark', flatShading: false });
  const bone = gameMaterial(0xdcc9a6, { roughness: 0.5, name: 'bone', flatShading: false });
  const acid = gameMaterial(0x8cff3a, { emissive: 0x8cff3a, emissiveIntensity: 1.5, roughness: 0.2, name: 'glow_acid', flatShading: false });
  const slime = gameMaterial(0x3a1458, { roughness: 0.12, metalness: 0.1, name: 'slime', flatShading: false });
  const slimeGlow = gameMaterial(0x9d3cff, { emissive: 0x9d3cff, emissiveIntensity: 1.2, roughness: 0.15, name: 'glow_slime', flatShading: false });
  const team = gameMaterial(0x8cff3a, { emissive: 0x8cff3a, emissiveIntensity: 1.0, roughness: 0.3, name: 'team', flatShading: false });

  // the ring body: a thick chitin collar with a funnel inside, flesh lips and a dark throat
  const ring = [[0.5, 0], [1.25, 0], [1.2, 0.35], [1.0, 0.85], [0.72, 1.0], [0.55, 0.85], [0.42, 0.2]];
  createPart('Collar', await revolveProfile(ring, { segments: 28, smooth: true }), chitinDark, { parent: root });
  createPart('Lips', torusGeo(0.6, 0.14, 10, 28), flesh, { position: [0, 0.9, 0], rotation: [90, 0, 0], parent: root });
  createPart('Gullet', cylinderGeo(0.55, 0.3, 0.8, 24, ), flesh, { position: [0, 0.5, 0], parent: root });
  createPart('Throat', cylinderGeo(0.36, 0.36, 0.06, 24), throat, { position: [0, 0.9, 0], parent: root });
  for (let k = 0; k < 10; k++) {
    const th = k * 36;
    createPart(`Rib${k}`, boxGeo(0.06, 0.6, 0.05), throat, { position: [Math.cos(th * RAD) * 0.5, 0.6, Math.sin(th * RAD) * 0.5], rotation: [0, -th, 12], parent: root });
  }

  // chitin humps round the rim, each with a tooth curling inward (front left open for the spill)
  for (const th of [20, 60, 130, 165, 210, 255, 300, 340]) {
    const g = orient(root, `Hump${th}`, [Math.cos(th * RAD) * 0.92, 0.72, Math.sin(th * RAD) * 0.92], th, 50);
    createPart(`HumpShell${th}`, sphereGeo(0.5, 12, 8), chitin, { scale: [0.85, 0.42, 0.9], parent: g });
    const t = createPivot(`Tooth${th}`, [Math.cos(th * RAD) * 0.7, 0.95, Math.sin(th * RAD) * 0.7], root);
    t.rotation.set(0, -th * RAD, 0);
    claw(`ToothBone${th}`, [[0.08, -0.05, 0], [0.1, 0.25, 0], [-0.02, 0.48, 0], [-0.26, 0.56, 0], [-0.42, 0.44, 0]], 0.16, bone, t);
  }
  // two low fangs either side of the spill
  for (const s of [-1, 1]) {
    const t = createPivot(`Fang${s}`, [s * 0.38, 0.75, 0.8], root);
    t.rotation.set(0, -90 * RAD, 0);
    claw(`FangBone${s}`, [[0.05, 0, 0], [0.08, 0.28, 0], [-0.04, 0.5, 0], [-0.22, 0.58, 0]], 0.11, bone, t);
  }

  // acid sacs at the sides
  for (const s of [-1, 1]) {
    createPart(`Sac${s}`, sphereGeo(0.4, 14, 10), acid, { position: [s * 1.12, 0.62, 0.05], scale: [0.75, 1.1, 1], parent: root });
    createPart(`SacHood${s}`, sphereGeo(0.42, 12, 8), chitin, { position: [s * 1.12, 0.98, 0.0], scale: [0.85, 0.4, 1], parent: root });
  }

  // slime spilling out at the front and pooling on the ground
  const spill = [[0, 0.85, 0.62, 0.3], [0, 0.62, 0.9, 0.32], [0.05, 0.35, 1.12, 0.34], [-0.05, 0.12, 1.3, 0.4]];
  spill.forEach(([x, y, z, r], i) => {
    createPart(`Spill${i}`, sphereGeo(r, 12, 8), slime, { position: [x, y, z], scale: [0.9, 0.55, 0.8], parent: root });
  });
  createPart('Pool', sphereGeo(0.62, 14, 8), slime, { position: [0, 0, 1.3], scale: [1.1, 0.12, 0.6], parent: root });
  createPart('PoolGlow', sphereGeo(0.3, 12, 6), slimeGlow, { position: [0.1, 0.03, 1.32], scale: [1.2, 0.15, 0.7], parent: root });

  // team nodules
  for (const th of [40, 140, 230, 320]) {
    createPart(`Nodule${th}`, sphereGeo(0.08, 8, 6), team, { position: [Math.cos(th * RAD) * 1.18, 0.3, Math.sin(th * RAD) * 1.18], parent: root });
  }
  return root;
}
