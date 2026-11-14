// Shardfall: Ambron Arc Tower (defence tower), from art/ambron_buildings/concepts/shardfall_ambron_arc_tower.png
// Front faces +Z. 2 x 2 m footprint. A stepped octagonal base, a tapering cream pylon with gold
// buttresses and lit slots, a collar and neck, and a turning head (node "turret") carrying a
// Tesla coil: gold rings round a glowing core under an orb, with four prongs and lightning arcs.
const meta = { name: 'Ambron Arc Tower', role: 'building' };

const CREAM = 0xe8dcc3, GOLD = 0xe2a531, DARK = 0x2c2e35, CYAN = 0x5fe3ff;
const RAD = Math.PI / 180;

function at(theta, r, y) {
  return [Math.cos(theta * RAD) * r, y, Math.sin(theta * RAD) * r];
}
function octagon(r) {
  const pts = [];
  for (let k = 0; k < 8; k++) {
    const a = (k * 45 + 22.5) * RAD;
    pts.push([Math.cos(a) * r, Math.sin(a) * r]);
  }
  return pts;
}

async function build() {
  const root = createRoot('AmbronArcTower');
  const cream = gameMaterial(CREAM, { roughness: 0.55, name: 'cream', flatShading: false });
  const gold = gameMaterial(GOLD, { roughness: 0.35, metalness: 0.55, name: 'gold', flatShading: false });
  const dark = gameMaterial(DARK, { roughness: 0.6, metalness: 0.2, name: 'graphite', flatShading: false });
  const glow = gameMaterial(CYAN, { emissive: CYAN, emissiveIntensity: 2.6, roughness: 0.25, name: 'glow_cyan', flatShading: false });
  const team = gameMaterial(CYAN, { emissive: CYAN, emissiveIntensity: 1.2, roughness: 0.4, name: 'team', flatShading: false });
  const rb = (w, h, d, r) => roundedBoxGeo(w, h, d, r, { style: 'chamfer' });

  // stepped base
  createPart('Plinth', await extrudeProfile(octagon(0.95), { depth: 0.18, bevel: 0.03, bevelStyle: 'chamfer' }), dark, { position: [0, 0.09, 0], parent: root });
  createPart('Tier', await extrudeProfile(octagon(0.82), { depth: 0.2, bevel: 0.04, bevelStyle: 'chamfer' }), cream, { position: [0, 0.28, 0], parent: root });
  for (let k = 0; k < 8; k++) {
    const th = k * 45;
    createPart(`PlinthSlot${k}`, boxGeo(0.03, 0.06, 0.32), team, { position: at(th, 0.885, 0.09), rotation: [0, -th, 0], parent: root });
  }

  // tapering pylon: cream panels over dark grooves, gold buttresses on the diagonals
  createPart('Pylon', cylinderGeo(0.36, 0.66, 1.1, 8), cream, { position: [0, 0.93, 0], rotation: [0, 22.5, 0], parent: root });
  createPart('PylonGrooves', cylinderGeo(0.345, 0.625, 1.08, 8), dark, { position: [0, 0.93, 0], parent: root });
  const tilt = Math.atan2(0.3, 1.1) / RAD;
  for (const th of [45, 135, 225, 315]) {
    const g = createPivot(`Butt${th}`, [0, 0, 0], root);
    g.rotation.set(0, -th * RAD, 0);
    createPart(`ButtGold${th}`, await rb(0.2, 0.75, 0.24, 0.05), gold, { position: [0.62, 0.72, 0], rotation: [0, 0, tilt], parent: g });
    createPart(`ButtFoot${th}`, await rb(0.32, 0.22, 0.3, 0.05), gold, { position: [0.74, 0.45, 0], parent: g });
  }
  for (const th of [0, 90, 180, 270]) {
    const g = createPivot(`Face${th}`, [0, 0, 0], root);
    g.rotation.set(0, -th * RAD, 0);
    createPart(`FaceSlot${th}`, boxGeo(0.03, 0.5, 0.09), team, { position: [0.55, 1.0, 0], rotation: [0, 0, tilt], parent: g });
    createPart(`FaceVent${th}`, boxGeo(0.04, 0.12, 0.26), dark, { position: [0.72, 0.5, 0], parent: g });
    for (const z of [-0.07, 0, 0.07]) {
      createPart(`FaceVentSlot${th}${z}`, boxGeo(0.03, 0.08, 0.03), team, { position: [0.745, 0.5, z], parent: g });
    }
  }

  // collar and neck
  createPart('Collar', cylinderGeo(0.5, 0.48, 0.2, 16), cream, { position: [0, 1.56, 0], parent: root });
  createPart('CollarRing', torusGeo(0.5, 0.045, 8, 28), gold, { position: [0, 1.66, 0], rotation: [90, 0, 0], parent: root });
  createPart('CollarBlock', await rb(0.3, 0.24, 0.14, 0.04), gold, { position: [0, 1.56, 0.5], parent: root });
  createPart('Neck', cylinderGeo(0.3, 0.34, 0.24, 16), dark, { position: [0, 1.78, 0], parent: root });
  for (const th of [30, 90, 150, 210, 270, 330]) {
    createPart(`NeckSlot${th}`, boxGeo(0.03, 0.07, 0.14), team, { position: at(th, 0.335, 1.78), rotation: [0, -th, 0], parent: root });
  }

  // the turning head
  const head = createPivot('turret', [0, 1.9, 0], root);
  head.name = 'turret';
  createPart('HeadRing', cylinderGeo(0.6, 0.5, 0.3, 8), cream, { position: [0, 0.15, 0], rotation: [0, 22.5, 0], parent: head });
  createPart('HeadBand', cylinderGeo(0.585, 0.585, 0.08, 8), dark, { position: [0, 0.12, 0], rotation: [0, 22.5, 0], parent: head });
  createPart('HeadTop', cylinderGeo(0.42, 0.5, 0.08, 24), dark, { position: [0, 0.33, 0], parent: head });
  for (let k = 0; k < 8; k++) {
    const th = k * 45;
    createPart(`HeadSlot${k}`, boxGeo(0.03, 0.06, 0.2), team, { position: at(th, 0.58, 0.12), rotation: [0, -th, 0], parent: head });
  }
  // four prongs rising and leaning out
  for (const th of [45, 135, 225, 315]) {
    const g = createPivot(`Prong${th}`, [0, 0, 0], head);
    g.rotation.set(0, -th * RAD, 0);
    createPart(`ProngBase${th}`, await rb(0.24, 0.3, 0.26, 0.06), gold, { position: [0.52, 0.2, 0], parent: g });
    createPart(`ProngArm${th}`, await rb(0.14, 0.62, 0.2, 0.04), cream, { position: [0.6, 0.6, 0], rotation: [0, 0, -14], parent: g });
    createPart(`ProngSlot${th}`, boxGeo(0.03, 0.26, 0.08), team, { position: [0.675, 0.58, 0], rotation: [0, 0, -14], parent: g });
    createPart(`ProngTip${th}`, sphereGeo(0.05, 8, 6), glow, { position: [0.68, 0.93, 0], parent: g });
  }
  // the coil: glowing core in three gold rings under an orb
  createPart('CoreBase', cylinderGeo(0.24, 0.3, 0.12, 20), dark, { position: [0, 0.42, 0], parent: head });
  createPart('Core', cylinderGeo(0.15, 0.15, 0.62, 16), glow, { position: [0, 0.78, 0], parent: head });
  for (const y of [0.56, 0.76, 0.96]) {
    createPart(`CoilRing${y}`, torusGeo(0.24, 0.045, 8, 24), gold, { position: [0, y, 0], rotation: [90, 0, 0], parent: head });
  }
  createPart('OrbCup', cylinderGeo(0.14, 0.1, 0.08, 16), dark, { position: [0, 1.12, 0], parent: head });
  createPart('Orb', sphereGeo(0.14, 16, 10), glow, { position: [0, 1.2, 0], parent: head });
  // lightning arcs from the orb out to each prong tip
  let seed = 7;
  const rnd = () => { seed = (seed * 9301 + 49297) % 233280; return seed / 233280 - 0.5; };
  for (const th of [45, 135, 225, 315]) {
    const tip = at(th, 0.68, 0.93);
    const pts = [[0, 1.22, 0]];
    for (let i = 1; i < 5; i++) {
      const f = i / 5;
      pts.push([tip[0] * f + rnd() * 0.12, 1.22 + (tip[1] - 1.22) * f + 0.14 * Math.sin(f * Math.PI) + rnd() * 0.08, tip[2] * f + rnd() * 0.12]);
    }
    pts.push(tip);
    const path = catmullRomPath(pts, 2);
    createPart(`Arc${th}`, taperedTube(path, path.map(() => 0.018), { radialSegments: 4 }), glow, { parent: head });
  }
  return root;
}
