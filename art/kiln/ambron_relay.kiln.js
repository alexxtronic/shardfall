// Shardfall: Ambron Power Relay (supply), from art/ambron_buildings/concepts/shardfall_ambron_relay.png
// Front faces +Z. 2 x 2 m footprint. The floating crystal and its rings are the node "float_crystal".
const meta = { name: 'Ambron Power Relay', role: 'building' };

const CREAM = 0xe8dcc3, GOLD = 0xe2a531, DARK = 0x2c2e35, CYAN = 0x5fe3ff;
const H = 0.95;                 // half width of the base plate
const PLATE_H = 0.14;
const TIER_H = 0.24;
const BAND_H = 0.1;
const OB_Y = PLATE_H + TIER_H + BAND_H;   // obelisk foot
const OB_H = 1.45;

function chamferSquare(h, c) {
  return [[-h + c, -h], [h - c, -h], [h, -h + c], [h, h - c], [h - c, h], [-h + c, h], [-h, h - c], [-h, -h + c]];
}

function at(theta, r, y) {
  const a = theta * Math.PI / 180;
  return [Math.cos(a) * r, y, Math.sin(a) * r];
}

async function build() {
  const root = createRoot('AmbronRelay');
  const cream = gameMaterial(CREAM, { roughness: 0.55, name: 'cream', flatShading: false });
  const gold = gameMaterial(GOLD, { roughness: 0.35, metalness: 0.55, name: 'gold', flatShading: false });
  const dark = gameMaterial(DARK, { roughness: 0.6, metalness: 0.2, name: 'graphite', flatShading: false });
  const glow = gameMaterial(CYAN, { emissive: CYAN, emissiveIntensity: 2.4, roughness: 0.3, name: 'glow_cyan', flatShading: false });
  const team = gameMaterial(CYAN, { emissive: CYAN, emissiveIntensity: 1.2, roughness: 0.4, name: 'team', flatShading: false });

  // stepped base: dark plate, cream tier with gold blocks and light slots, dark band
  createPart('Plate', await extrudeProfile(chamferSquare(H, 0.28), { depth: PLATE_H, bevel: 0.03, bevelStyle: 'chamfer' }), dark,
    { position: [0, PLATE_H / 2, 0], parent: root });
  createPart('Tier', await extrudeProfile(chamferSquare(H - 0.08, 0.26), { depth: TIER_H, bevel: 0.05, bevelStyle: 'chamfer' }), cream,
    { position: [0, PLATE_H + TIER_H / 2, 0], parent: root });
  createPart('Band', await extrudeProfile(chamferSquare(0.6, 0.18), { depth: BAND_H }), dark,
    { position: [0, PLATE_H + TIER_H + BAND_H / 2, 0], parent: root });
  for (const th of [0, 90, 180, 270]) {
    createPart(`TierBlock${th}`, await roundedBoxGeo(0.14, 0.16, 0.34, 0.03, { style: 'chamfer' }), gold,
      { position: at(th, H - 0.12, PLATE_H + TIER_H + 0.04), rotation: [0, -th, 0], parent: root });
    createPart(`TierSlot${th}`, boxGeo(0.04, 0.07, 0.3), team,
      { position: at(th, H - 0.075, PLATE_H + TIER_H * 0.45), rotation: [0, -th, 0], parent: root });
    createPart(`PlateSlot${th}`, boxGeo(0.04, 0.05, 0.4), team,
      { position: at(th + 45, (H - 0.14) * 1.0, PLATE_H * 0.5), rotation: [0, -(th + 45), 0], parent: root });
  }

  // obelisk: an octagonal frustum of cream panels with a light strip on each main face
  createPart('Obelisk', cylinderGeo(0.24, 0.48, OB_H, 8), cream, { position: [0, OB_Y + OB_H / 2, 0], rotation: [0, 22.5, 0], parent: root });
  const tilt = Math.atan2(0.24, OB_H) * 180 / Math.PI;
  for (const th of [0, 90, 180, 270]) {
    const g = createPivot(`Strip${th}`, [0, OB_Y, 0], root);
    g.rotation.set(0, -th * Math.PI / 180, 0);
    createPart(`StripLight${th}`, boxGeo(0.05, OB_H * 0.72, 0.09), team,
      { position: [0.355 * 1.0 + 0.0, OB_H * 0.5, 0], rotation: [0, 0, tilt], parent: g });
  }
  createPart('Collar', cylinderGeo(0.3, 0.3, 0.12, 24), dark, { position: [0, OB_Y + OB_H + 0.05, 0], parent: root });
  createPart('CollarRim', torusGeo(0.28, 0.035, 8, 28), gold, { position: [0, OB_Y + OB_H + 0.11, 0], rotation: [90, 0, 0], parent: root });
  createPart('CollarLight', cylinderGeo(0.2, 0.2, 0.04, 24), glow, { position: [0, OB_Y + OB_H + 0.12, 0], parent: root });

  // four gold fins standing round the obelisk
  const fin = [[0, 0], [0.26, 0], [0.3, 0.32], [0.17, 1.15], [0.03, 1.28], [-0.03, 0.32]];
  for (const th of [0, 90, 180, 270]) {
    const g = createPivot(`Fin${th}`, [0, PLATE_H + TIER_H, 0], root);
    g.rotation.set(0, -th * Math.PI / 180, 0);
    createPart(`FinBlade${th}`, await extrudeProfile(fin, { depth: 0.15, axis: 'z', bevel: 0.03, bevelStyle: 'chamfer' }), gold,
      { position: [0.5, 0, 0], rotation: [0, 0, 4], parent: g });
    createPart(`FinLight${th}`, boxGeo(0.03, 0.55, 0.05), team, { position: [0.73, 0.55, 0], rotation: [0, 0, 5], parent: g });
  }

  // floating cyan crystal in two gold rings
  const fl = createPivot('float_crystal', [0, OB_Y + OB_H + 0.62, 0], root);
  fl.name = 'float_crystal';
  createPart('CrystalTop', coneGeo(0.19, 0.5, 6), glow, { position: [0, 0.25, 0], parent: fl });
  createPart('CrystalBottom', coneGeo(0.19, 0.3, 6), glow, { position: [0, -0.15, 0], rotation: [180, 0, 0], parent: fl });
  createPart('RingTop', torusGeo(0.42, 0.03, 8, 40), gold, { position: [0, 0.08, 0], rotation: [90, 0, 0], parent: fl });
  createPart('RingLow', torusGeo(0.3, 0.03, 8, 36), gold, { position: [0, -0.2, 0], rotation: [90, 0, 0], parent: fl });
  for (const th of [30, 150, 270]) {
    createPart(`RingLight${th}`, boxGeo(0.05, 0.035, 0.14), glow, { position: at(th, 0.42, 0.08), rotation: [0, -th - 90, 0], parent: fl });
  }
  return root;
}
