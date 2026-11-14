// Shardfall: Ambron Apex Spire (special tech building), from art/ambron_buildings/concepts/shardfall_ambron_spire.png
// Front faces +Z. 4 x 4 m footprint. A stepped square base, four wedge buttresses on the sides
// (the front one carries a lit orb), four curved gold buttresses rising from the corners, a tall
// panelled tapering spire with gold rings, and a hovering crystal: the node "float_crystal".
const meta = { name: 'Ambron Apex Spire', role: 'building' };

const CREAM = 0xe8dcc3, GOLD = 0xe2a531, DARK = 0x2c2e35, CYAN = 0x5fe3ff;
const RAD = Math.PI / 180;
const T0 = 0.73;          // tower foot
const TH = 3.3;           // tower height
const RB = 0.76, RT = 0.22;

function chamferSquare(h, c) {
  return [[-h + c, -h], [h - c, -h], [h, -h + c], [h, h - c], [h - c, h], [-h + c, h], [-h, h - c], [-h, -h + c]];
}
function at(theta, r, y) {
  return [Math.cos(theta * RAD) * r, y, Math.sin(theta * RAD) * r];
}
const towerR = (y) => RB + (RT - RB) * (y - T0) / TH;

async function build() {
  const root = createRoot('AmbronApexSpire');
  const cream = gameMaterial(CREAM, { roughness: 0.55, name: 'cream', flatShading: false });
  const gold = gameMaterial(GOLD, { roughness: 0.35, metalness: 0.55, name: 'gold', flatShading: false });
  const dark = gameMaterial(DARK, { roughness: 0.6, metalness: 0.2, name: 'graphite', flatShading: false });
  const glow = gameMaterial(CYAN, { emissive: CYAN, emissiveIntensity: 2.4, roughness: 0.25, name: 'glow_cyan', flatShading: false });
  const team = gameMaterial(CYAN, { emissive: CYAN, emissiveIntensity: 1.2, roughness: 0.4, name: 'team', flatShading: false });
  const rb = (w, h, d, r) => roundedBoxGeo(w, h, d, r, { style: 'chamfer' });

  // stepped base
  createPart('Plinth', await extrudeProfile(chamferSquare(1.9, 0.6), { depth: 0.2, bevel: 0.04, bevelStyle: 'chamfer' }), dark, { position: [0, 0.1, 0], parent: root });
  createPart('Tier', await extrudeProfile(chamferSquare(1.72, 0.55), { depth: 0.3, bevel: 0.05, bevelStyle: 'chamfer' }), cream, { position: [0, 0.35, 0], parent: root });
  createPart('TierBand', await extrudeProfile(chamferSquare(1.75, 0.56), { depth: 0.07 }), gold, { position: [0, 0.4, 0], parent: root });
  createPart('Disc', cylinderGeo(1.15, 1.25, 0.24, 32), dark, { position: [0, 0.6, 0], parent: root });
  createPart('DiscRim', torusGeo(1.12, 0.045, 8, 40), gold, { position: [0, 0.72, 0], rotation: [90, 0, 0], parent: root });
  for (const th of [0, 90, 180, 270]) {
    for (const off of [-0.75, 0.75]) {
      const tx = Math.cos(th * RAD), tz = Math.sin(th * RAD);
      const g = createPivot(`PlinthSlot${th}${off}`, [tx * 1.86 - tz * off, 0.1, tz * 1.86 + tx * off], root);
      g.rotation.set(0, -th * RAD, 0);
      createPart(`PlinthSlotLight${th}${off}`, boxGeo(0.03, 0.06, 0.42), team, { parent: g });
    }
  }

  // corner pods with curved gold buttresses rising from them
  for (const th of [45, 135, 225, 315]) {
    const g = createPivot(`Corner${th}`, [0, 0, 0], root);
    g.rotation.set(0, -th * RAD, 0);
    createPart(`Pod${th}`, await rb(0.7, 0.4, 0.62, 0.1), cream, { position: [1.62, 0.66, 0], parent: g });
    createPart(`PodGold${th}`, await rb(0.74, 0.1, 0.66, 0.04), gold, { position: [1.62, 0.5, 0], parent: g });
    createPart(`PodSlot${th}`, boxGeo(0.03, 0.08, 0.36), team, { position: [2.0, 0.26, 0], parent: g });
    const path = catmullRomPath([[1.6, 0.8, 0], [1.72, 1.4, 0], [1.55, 2.2, 0], [1.2, 2.85, 0], [1.08, 3.15, 0]], 4);
    const radii = path.map((_, i) => 0.23 - 0.1 * i / (path.length - 1));
    createPart(`Arch${th}`, taperedTube(path, radii, { radialSegments: 6 }), gold, { parent: g });
    for (const [x, y, a] of [[1.86, 1.45, -4], [1.74, 2.15, 22]]) {
      createPart(`ArchSlot${th}${y}`, boxGeo(0.04, 0.34, 0.08), team, { position: [x, y, 0], rotation: [0, 0, a], parent: g });
    }
  }

  // wedge buttresses on the four sides, the front one with a lit orb
  const wedge = [[0.5, 0], [1.55, 0], [1.55, 0.36], [0.72, 2.15], [0.5, 2.2]];
  const slant = Math.atan2(1.55 - 0.72, 2.15 - 0.36) / RAD;
  for (const th of [0, 90, 180, 270]) {
    const g = createPivot(`Wedge${th}`, [0, 0.48, 0], root);
    g.rotation.set(0, -th * RAD, 0);
    createPart(`WedgeBody${th}`, await extrudeProfile(wedge, { depth: 0.82, axis: 'z', bevel: 0.04, bevelStyle: 'chamfer' }), cream, { parent: g });
    for (const s of [-1, 1]) {
      createPart(`WedgeTrim${th}${s}`, boxGeo(0.08, 1.96, 0.09), gold,
        { position: [1.165, 1.26, s * 0.43], rotation: [0, 0, slant], parent: g });
    }
    createPart(`WedgeSlot${th}`, boxGeo(0.03, 0.7, 0.12), team, { position: [1.3, 1.0, 0], rotation: [0, 0, slant], parent: g });
    if (th === 90) {
      createPart('OrbRing', torusGeo(0.26, 0.07, 8, 24), gold, { position: [1.58, 0.55, 0], rotation: [0, 90, 0], parent: g });
      createPart('Orb', sphereGeo(0.19, 16, 10), glow, { position: [1.58, 0.55, 0], scale: [0.5, 1, 1], parent: g });
      createPart('OrbSlot', boxGeo(0.03, 0.2, 0.07), team, { position: [1.52, 0.12, 0], parent: g });
    }
  }

  // the spire: cream panels with dark grooves, a lit band at the foot, gold rings higher up
  createPart('TowerPanels', cylinderGeo(RT, RB, TH, 8), cream, { position: [0, T0 + TH / 2, 0], parent: root });
  createPart('TowerGrooves', cylinderGeo(RT * 0.94, RB * 0.937, TH - 0.03, 8), dark, { position: [0, T0 + TH / 2, 0], rotation: [0, 22.5, 0], parent: root });
  createPart('FootBand', cylinderGeo(0.86, 0.9, 0.46, 24), dark, { position: [0, T0 + 0.2, 0], parent: root });
  for (let k = 0; k < 8; k++) {
    createPart(`FootSlot${k}`, boxGeo(0.03, 0.18, 0.1), team, { position: at(k * 45 + 22.5, 0.885, T0 + 0.22), rotation: [0, -(k * 45 + 22.5), 0], parent: root });
  }
  createPart('FootRing', torusGeo(0.84, 0.06, 8, 32), gold, { position: [0, T0 + 0.46, 0], rotation: [90, 0, 0], parent: root });
  for (const y of [2.0, 2.75, 3.3]) {
    const r = towerR(y) + 0.08;
    createPart(`Ring${y}`, await revolveProfile([[r, -0.09], [r + 0.11, -0.07], [r + 0.11, 0.07], [r, 0.09]], { segments: 28, smooth: false }), gold,
      { position: [0, y, 0], parent: root });
    for (let k = 0; k < 6; k++) {
      createPart(`RingSlot${y}${k}`, boxGeo(0.03, 0.07, 0.14), team, { position: at(k * 60 + 30, r + 0.115, y), rotation: [0, -(k * 60 + 30), 0], parent: root });
    }
  }
  const tip = T0 + TH;
  createPart('TipCollar', cylinderGeo(0.2, 0.25, 0.16, 16), dark, { position: [0, tip + 0.06, 0], parent: root });
  createPart('TipRim', torusGeo(0.2, 0.035, 8, 20), gold, { position: [0, tip + 0.15, 0], rotation: [90, 0, 0], parent: root });
  createPart('TipLight', cylinderGeo(0.14, 0.14, 0.04, 16), glow, { position: [0, tip + 0.15, 0], parent: root });

  // hovering crystal with its halo and two gold tabs
  const fl = createPivot('float_crystal', [0, tip + 1.2, 0], root);
  fl.name = 'float_crystal';
  createPart('Crystal', sphereGeo(0.4, 6, 2), glow, { scale: [1, 2.0, 1], parent: fl });
  createPart('Halo', torusGeo(0.4, 0.025, 6, 32), glow, { position: [0, -0.82, 0], rotation: [90, 0, 0], parent: fl });
  for (const s of [-1, 1]) {
    createPart(`Tab${s}`, await rb(0.1, 0.34, 0.07, 0.03), gold, { position: [s * 0.75, 0.05, 0], parent: fl });
    createPart(`TabSlot${s}`, boxGeo(0.03, 0.2, 0.08), team, { position: [s * 0.75, 0.05, 0.005], parent: fl });
  }
  return root;
}
