// Shardfall: Ambron Skyport (air factory), from art/ambron_buildings/concepts/shardfall_ambron_skyport.png
// Front faces +Z. 3 x 3 m footprint. A raised round landing pad on four splayed legs, its rim
// segmented with gold blocks and lit slots and its deck marked with a cyan ring; a control tower
// with a lit cab and a dish at the back left, and twin fuel tanks under the pad.
const meta = { name: 'Ambron Skyport', role: 'building' };

const CREAM = 0xe8dcc3, GOLD = 0xe2a531, DARK = 0x2c2e35, CYAN = 0x5fe3ff;
const RAD = Math.PI / 180;
const PY = 1.22;          // pad deck height
const PR = 1.08;          // deck radius

function at(theta, r, y) {
  return [Math.cos(theta * RAD) * r, y, Math.sin(theta * RAD) * r];
}

async function build() {
  const root = createRoot('AmbronSkyport');
  const cream = gameMaterial(CREAM, { roughness: 0.55, name: 'cream', flatShading: false });
  const gold = gameMaterial(GOLD, { roughness: 0.35, metalness: 0.55, name: 'gold', flatShading: false });
  const dark = gameMaterial(DARK, { roughness: 0.6, metalness: 0.2, name: 'graphite', flatShading: false });
  const glow = gameMaterial(CYAN, { emissive: CYAN, emissiveIntensity: 2.2, roughness: 0.3, name: 'glow_cyan', flatShading: false });
  const team = gameMaterial(CYAN, { emissive: CYAN, emissiveIntensity: 1.2, roughness: 0.4, name: 'team', flatShading: false });
  const rb = (w, h, d, r) => roundedBoxGeo(w, h, d, r, { style: 'chamfer' });

  // four splayed legs on the diagonals
  for (const th of [45, 135, 315]) {
    const g = createPivot(`Leg${th}`, [0, 0, 0], root);
    g.rotation.set(0, -th * RAD, 0);
    createPart(`Foot${th}`, await rb(0.56, 0.18, 0.5, 0.05), dark, { position: [1.3, 0.09, 0], parent: g });
    createPart(`FootSlot${th}`, boxGeo(0.03, 0.06, 0.3), team, { position: [1.585, 0.09, 0], parent: g });
    createPart(`FootGold${th}`, await rb(0.46, 0.2, 0.42, 0.05), gold, { position: [1.25, 0.27, 0], parent: g });
    createPart(`Shin${th}`, await rb(0.36, 1.0, 0.42, 0.07), cream, { position: [1.1, 0.7, 0], rotation: [0, 0, 22], parent: g });
    createPart(`ShinSlot${th}`, boxGeo(0.03, 0.46, 0.09), team, { position: [1.29, 0.66, 0], rotation: [0, 0, 22], parent: g });
    createPart(`Knee${th}`, await rb(0.32, 0.18, 0.46, 0.05), gold, { position: [0.93, 1.1, 0], rotation: [0, 0, 22], parent: g });
  }

  // the pad: dark underside, deck, segmented cream rim with gold blocks and posts
  createPart('Underside', cylinderGeo(PR - 0.05, 0.75, 0.24, 32), dark, { position: [0, PY - 0.17, 0], parent: root });
  createPart('Deck', cylinderGeo(PR, PR, 0.06, 40), dark, { position: [0, PY - 0.03, 0], parent: root });
  createPart('Rim', await revolveProfile([[PR - 0.02, -0.18], [PR + 0.2, -0.18], [PR + 0.24, 0.08], [PR + 0.18, 0.16], [PR - 0.02, 0.16]], { segments: 16, smooth: false }), cream,
    { position: [0, PY, 0], parent: root });
  createPart('RimBand', cylinderGeo(PR + 0.235, PR + 0.215, 0.08, 16), dark, { position: [0, PY - 0.2, 0], parent: root });
  for (let k = 0; k < 8; k++) {
    const th = k * 45 + 22.5;
    const big = k === 3;   // the front block (~90 degrees)
    createPart(`RimBlock${k}`, await rb(0.16, 0.24, big ? 0.62 : 0.32, 0.05), gold, { position: at(th, PR + 0.23, PY - 0.02), rotation: [0, -th, 0], parent: root });
    createPart(`RimSlot${k}`, boxGeo(0.03, 0.07, big ? 0.46 : 0.2), team, { position: at(th, PR + 0.315, PY - 0.02), rotation: [0, -th, 0], parent: root });
  }
  for (const th of [0, 60, 120, 180, 240, 300]) {
    createPart(`Post${th}`, await rb(0.14, 0.2, 0.2, 0.04), gold, { position: at(th, PR + 0.08, PY + 0.25), rotation: [0, -th, 0], parent: root });
    createPart(`PostSlot${th}`, boxGeo(0.03, 0.1, 0.08), team, { position: at(th, PR + 0.155, PY + 0.25), rotation: [0, -th, 0], parent: root });
  }
  // deck markings: a lit ring with four ticks, panel seams
  createPart('DeckRing', torusGeo(0.6, 0.035, 6, 40), glow, { position: [0, PY + 0.005, 0], rotation: [90, 0, 0], scale: [1, 1, 0.4], parent: root });
  for (const th of [45, 135, 225, 315]) {
    createPart(`Tick${th}`, boxGeo(0.22, 0.02, 0.05), glow, { position: at(th, 0.38, PY + 0.005), rotation: [0, -th, 0], parent: root });
  }
  for (const th of [0, 90]) {
    createPart(`Seam${th}`, boxGeo(2 * PR - 0.1, 0.012, 0.02), cream, { position: [0, PY + 0.003, 0], rotation: [0, th, 0], parent: root });
  }

  // twin fuel tanks under the pad, front
  createPart('TankBase', await rb(1.2, 0.2, 0.72, 0.05), dark, { position: [0, 0.1, 0.75], parent: root });
  createPart('TankBaseFront', await rb(0.9, 0.16, 0.12, 0.04), cream, { position: [0, 0.12, 1.12], parent: root });
  createPart('TankBaseSlot', boxGeo(0.5, 0.05, 0.03), team, { position: [0, 0.12, 1.185], parent: root });
  for (const s of [-1, 1]) {
    const x = s * 0.27;
    createPart(`Tank${s}`, await rb(0.48, 0.5, 0.62, 0.18), cream, { position: [x, 0.47, 0.78], parent: root });
    createPart(`TankBand${s}`, await rb(0.5, 0.12, 0.64, 0.05), gold, { position: [x, 0.3, 0.78], parent: root });
    createPart(`TankSlot${s}`, boxGeo(0.08, 0.24, 0.03), team, { position: [x, 0.52, 1.095], parent: root });
    createPart(`PipeUp${s}`, cylinderGeo(0.05, 0.05, 0.28, 10), dark, { position: [x, 0.84, 0.78], parent: root });
    createPart(`PipeCollar${s}`, cylinderGeo(0.08, 0.08, 0.08, 10), gold, { position: [x, 0.76, 0.78], parent: root });
  }
  createPart('PipeAcross', cylinderGeo(0.05, 0.05, 0.6, 10), dark, { position: [0, 0.98, 0.78], rotation: [0, 0, 90], parent: root });
  for (const s of [-1, 1]) {
    createPart(`PipeElbow${s}`, sphereGeo(0.055, 10, 8), dark, { position: [s * 0.27, 0.98, 0.78], parent: root });
  }

  // control tower, back left
  const tx = -1.0, tz = -0.98;
  createPart('TowerFoot', await rb(0.74, 0.22, 0.74, 0.06), dark, { position: [tx, 0.11, tz], parent: root });
  createPart('TowerBase', await rb(0.62, 0.55, 0.62, 0.1), cream, { position: [tx, 0.48, tz], parent: root });
  createPart('TowerBaseGrille', boxGeo(0.3, 0.2, 0.03), dark, { position: [tx + 0.2, 0.5, tz + 0.315], parent: root });
  for (const k of [0, 1, 2]) {
    createPart(`TowerBaseSlot${k}`, boxGeo(0.24, 0.025, 0.03), team, { position: [tx + 0.2, 0.43 + k * 0.065, tz + 0.33], parent: root });
  }
  createPart('Column', cylinderGeo(0.24, 0.3, 1.25, 8), cream, { position: [tx, 1.38, tz], rotation: [0, 22.5, 0], parent: root });
  for (const th of [0, 180]) {
    createPart(`ColumnGold${th}`, await rb(0.08, 1.0, 0.2, 0.03), gold, { position: [tx + Math.cos(th * RAD) * 0.26, 1.35, tz + Math.sin(th * RAD) * 0.26], rotation: [0, -th, 4 * Math.cos(th * RAD)], parent: root });
  }
  createPart('ColumnSlot', boxGeo(0.07, 0.6, 0.03), team, { position: [tx + 0.19, 1.35, tz + 0.19], rotation: [0, 45, 0], parent: root });
  const cy = 2.15;
  createPart('CabFloor', cylinderGeo(0.4, 0.28, 0.16, 8), cream, { position: [tx, cy - 0.12, tz], rotation: [0, 22.5, 0], parent: root });
  createPart('CabGlass', cylinderGeo(0.46, 0.4, 0.22, 8), glow, { position: [tx, cy + 0.07, tz], rotation: [0, 22.5, 0], parent: root });
  for (let k = 0; k < 8; k++) {
    const th = k * 45 + 22.5;
    createPart(`Mullion${k}`, boxGeo(0.05, 0.24, 0.05), dark, { position: at(th, 0.455, cy + 0.07).map((v, i) => v + [tx, 0, tz][i]), parent: root });
  }
  createPart('CabRoof', cylinderGeo(0.4, 0.5, 0.12, 8), gold, { position: [tx, cy + 0.24, tz], rotation: [0, 22.5, 0], parent: root });
  createPart('CabTop', cylinderGeo(0.28, 0.36, 0.12, 8), cream, { position: [tx, cy + 0.36, tz], rotation: [0, 22.5, 0], parent: root });
  // dish and antenna
  const dish = createPivot('Dish', [tx + 0.1, cy + 0.62, tz + 0.05], root);
  dish.rotation.set(-55 * RAD, 35 * RAD, 0);
  createPart('DishMount', cylinderGeo(0.07, 0.09, 0.2, 10), dark, { position: [0, -0.15, 0], rotation: [35, 0, 0], parent: dish });
  createPart('DishBowl', await revolveProfile([[0, 0], [0.12, 0.01], [0.24, 0.05], [0.3, 0.11], [0.28, 0.12], [0.22, 0.08], [0.1, 0.04], [0, 0.03]], { segments: 18, smooth: true }), gold,
    { parent: dish });
  createPart('DishFeed', cylinderGeo(0.015, 0.015, 0.2, 6), dark, { position: [0, 0.12, 0], parent: dish });
  createPart('DishTip', sphereGeo(0.035, 8, 6), glow, { position: [0, 0.23, 0], parent: dish });
  createPart('Antenna', cylinderGeo(0.018, 0.025, 0.5, 6), dark, { position: [tx - 0.2, cy + 0.65, tz - 0.08], parent: root });
  createPart('AntennaTip', cylinderGeo(0.03, 0.03, 0.12, 8), glow, { position: [tx - 0.2, cy + 0.94, tz - 0.08], parent: root });
  return root;
}
