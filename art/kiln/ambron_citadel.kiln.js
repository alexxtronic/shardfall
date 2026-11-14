// Shardfall: Ambron Citadel (main base), from art/ambron_buildings/concepts/shardfall_ambron_citadel.png
// Front faces +Z (the game's glTF front). Metres; footprint about 4.8 m, stands on y = 0.
// Materials: cream, gold, graphite, glow_cyan, glow_gold, and team (light strips the game
// recolours to the player's colour). The floating crystal is the node "float_crystal".
const meta = { name: 'Ambron Citadel', role: 'building' };

const CREAM = 0xe8dcc3;
const GOLD = 0xe2a531;
const DARK = 0x2c2e35;
const CYAN = 0x5fe3ff;

const PLINTH_R = 2.6;      // octagon circumradius of the dark base plate
const PLINTH_H = 0.22;
const TIER_R = 2.35;       // cream tier on the plate
const TIER_H = 0.3;
const DECK = PLINTH_H + TIER_H + 0.07;   // top of the gold band, where everything stands
const DOME_R = 1.7;
const COLLAR_H = 0.22;     // dark band under the dome
const DOME_Y = DECK + COLLAR_H;
const DOME_H = 1.95;

function octagon(r) {
  const pts = [];
  for (let k = 0; k < 8; k++) {
    const a = (22.5 + 45 * k) * Math.PI / 180;
    pts.push([Math.cos(a) * r, Math.sin(a) * r]);
  }
  return pts;
}

function at(theta, r, y) {
  const a = theta * Math.PI / 180;
  return [Math.cos(a) * r, y, Math.sin(a) * r];
}

async function build() {
  const root = createRoot('AmbronCitadel');
  const cream = gameMaterial(CREAM, { roughness: 0.55, name: 'cream', flatShading: false });
  const gold = gameMaterial(GOLD, { roughness: 0.35, metalness: 0.55, name: 'gold', flatShading: false });
  const dark = gameMaterial(DARK, { roughness: 0.6, metalness: 0.2, name: 'graphite', flatShading: false });
  const glow = gameMaterial(CYAN, { emissive: CYAN, emissiveIntensity: 2.2, roughness: 0.3, name: 'glow_cyan', flatShading: false });
  const glowGold = gameMaterial(0xffc93a, { emissive: 0xffb820, emissiveIntensity: 1.6, roughness: 0.25, name: 'glow_gold', flatShading: false });
  const team = gameMaterial(CYAN, { emissive: CYAN, emissiveIntensity: 1.2, roughness: 0.4, name: 'team', flatShading: false });

  // --- base: dark octagon plate, cream tier, gold band
  createPart('Plinth', await extrudeProfile(octagon(PLINTH_R), { depth: PLINTH_H, bevel: 0.06, bevelStyle: 'chamfer' }), dark,
    { position: [0, PLINTH_H / 2, 0], parent: root });
  createPart('Tier', await extrudeProfile(octagon(TIER_R), { depth: TIER_H, bevel: 0.1, bevelStyle: 'chamfer' }), cream,
    { position: [0, PLINTH_H + TIER_H / 2, 0], parent: root });
  createPart('TierBand', await extrudeProfile(octagon(TIER_R - 0.06), { depth: 0.07 }), gold,
    { position: [0, PLINTH_H + TIER_H + 0.035, 0], parent: root });
  // team light strips on each face of the plate
  const flat = PLINTH_R * Math.cos(Math.PI / 8);
  for (let k = 0; k < 8; k++) {
    const th = 45 * k;
    if (th === 90) continue; // the ramp sits there
    createPart(`PlinthLight${k}`, boxGeo(0.06, 0.07, 0.55), team,
      { position: at(th, flat + 0.005, PLINTH_H * 0.5), rotation: [0, -th, 0], parent: root });
  }

  // --- four round side pods on the diagonals, cyan lit tops
  for (const th of [45, 135, 225, 315]) {
    const p = at(th, 1.78, DECK);
    createPart(`PodBase${th}`, cylinderGeo(0.62, 0.66, 0.12, 24), dark, { position: [p[0], DECK + 0.06, p[2]], parent: root });
    createPart(`Pod${th}`, cylinderGeo(0.56, 0.6, 0.5, 24), cream, { position: [p[0], DECK + 0.37, p[2]], parent: root });
    createPart(`PodRim${th}`, torusGeo(0.5, 0.06, 8, 32), gold, { position: [p[0], DECK + 0.62, p[2]], rotation: [90, 0, 0], parent: root });
    createPart(`PodLight${th}`, cylinderGeo(0.4, 0.4, 0.05, 24), glow, { position: [p[0], DECK + 0.63, p[2]], parent: root });
    // a team light slot on the pod's outer face
    createPart(`PodSlot${th}`, boxGeo(0.05, 0.09, 0.32), team, { position: at(th, 1.78 + 0.6, DECK + 0.32), rotation: [0, -th, 0], parent: root });
  }

  // --- dark collar with light slots, then the cream dome
  createPart('Collar', cylinderGeo(DOME_R + 0.06, DOME_R + 0.12, COLLAR_H, 40), dark, { position: [0, DECK + COLLAR_H / 2, 0], parent: root });
  for (const th of [30, 150, 210, 270, 330]) {
    createPart(`CollarSlot${th}`, boxGeo(0.05, 0.08, 0.4), team, { position: at(th, DOME_R + 0.13, DECK + COLLAR_H / 2), rotation: [0, -th, 0], parent: root });
  }
  const K = DOME_H / 1.3;
  const domeProfile = [[0, 0], [DOME_R, 0], [DOME_R, 0.28 * K], [DOME_R * 0.95, 0.62 * K], [DOME_R * 0.78, 0.98 * K], [DOME_R * 0.46, DOME_H - 0.08], [0, DOME_H]];
  createPart('Dome', await revolveProfile(domeProfile, { segments: 40, smooth: true }), cream, { position: [0, DOME_Y, 0], parent: root });
  createPart('DomeBand', torusGeo(DOME_R + 0.01, 0.07, 8, 48), gold, { position: [0, DOME_Y + 0.3, 0], rotation: [90, 0, 0], parent: root });

  // --- armour shoulder plates leaning on the dome (not over the front eye)
  for (const th of [15, 165, 215, 270, 325, 52, 128]) {
    const big = th !== 52 && th !== 128;
    const g = createPivot(`Shoulder${th}`, at(th, DOME_R + 0.02, DOME_Y + 0.05), root);
    g.rotation.set(0, -th * Math.PI / 180, 0);
    const hgt = big ? 1.45 : 1.0;
    const wid = big ? 1.05 : 0.8;
    createPart(`ShoulderPlate${th}`, await roundedBoxGeo(0.32, hgt, wid, 0.09, { style: 'chamfer' }), cream,
      { position: [-0.05, hgt * 0.45, 0], rotation: [0, 0, 20], parent: g });
    createPart(`ShoulderTrim${th}`, boxGeo(0.08, 0.2, wid * 0.86), gold, { position: [-0.1 + 0.02, hgt * 0.86, 0], rotation: [0, 0, 20], parent: g });
    createPart(`ShoulderSlot${th}`, boxGeo(0.05, hgt * 0.32, 0.08), team, { position: [0.08, hgt * 0.42, 0], rotation: [0, 0, 20], parent: g });
  }

  // --- the big cyan eye on the dome front
  const eyeY = DOME_Y + 1.18;
  const eyeZ = DOME_R * 0.86;
  const eye = createPivot('EyeMount', [0, eyeY, eyeZ], root);
  eye.rotation.set(-22 * Math.PI / 180, 0, 0);
  createPart('EyeSocket', cylinderGeo(0.63, 0.63, 0.24, 32), dark, { position: [0, 0, 0.02], rotation: [90, 0, 0], parent: eye });
  createPart('EyeRing', torusGeo(0.52, 0.13, 10, 36), gold, { position: [0, 0, 0.16], parent: eye });
  createPart('Eye', cylinderGeo(0.4, 0.4, 0.1, 32), glow, { position: [0, 0, 0.17], rotation: [90, 0, 0], parent: eye });

  // --- crown: gold collar on top of the dome, cyan beam, floating golden crystal
  const topY = DOME_Y + DOME_H;
  createPart('CrownBase', cylinderGeo(0.62, 0.7, 0.18, 32), gold, { position: [0, topY - 0.02, 0], parent: root });
  createPart('CrownLight', cylinderGeo(0.42, 0.42, 0.05, 32), glow, { position: [0, topY + 0.09, 0], parent: root });
  createPart('Beam', cylinderGeo(0.13, 0.24, 0.42, 16), glow, { position: [0, topY + 0.3, 0], parent: root });
  const fl = createPivot('float_crystal', [0, topY + 0.95, 0], root);
  fl.scale.set(1.35, 1.35, 1.35);
  fl.name = 'float_crystal';
  createPart('CrystalTop', coneGeo(0.3, 0.62, 6), glowGold, { position: [0, 0.31, 0], parent: fl });
  createPart('CrystalBottom', coneGeo(0.3, 0.32, 6), glowGold, { position: [0, -0.16, 0], rotation: [180, 0, 0], parent: fl });
  for (const s of [-1, 1]) {
    createPart(`Shard${s}`, boxGeo(0.07, 0.3, 0.07), glowGold, { position: [s * 0.5, 0.05, 0], parent: fl });
  }

  // --- two tall gold horn blades at the back
  const blade = [[-0.32, 0], [0.32, 0], [0.22, 2.5], [0.05, 3.1], [-0.17, 2.65]];
  for (const s of [-1, 1]) {
    const g = createPivot(`Horn${s}`, [s * 1.2, DOME_Y + 0.05, -0.5], root);
    g.rotation.set(0, 0, -s * 9 * Math.PI / 180);
    const shape = s < 0 ? blade.map(([u, v]) => [-u, v]) : blade;
    createPart(`HornBlade${s}`, await extrudeProfile(shape, { depth: 0.24, axis: 'z', bevel: 0.05, bevelStyle: 'chamfer' }), gold,
      { position: [0, 0, 0], parent: g });
    createPart(`HornLight${s}`, boxGeo(0.11, 1.5, 0.04), team, { position: [s * 0.05, 1.45, 0.13], parent: g });
  }

  // --- front gate: cream hood with a gold arch frame and a glowing door, ramp down to the plate
  const gateZ0 = 1.3;               // back of the hood (inside the dome)
  const gateZ1 = 1.95;               // front face of the hood
  const hood = [[-0.85, 0], [0.85, 0], [0.85, 0.72], [0.52, 1.02], [-0.52, 1.02], [-0.85, 0.72]];
  createPart('GateHood', await extrudeProfile(hood, { depth: gateZ1 - gateZ0, axis: 'z', bevel: 0.06, bevelStyle: 'chamfer' }), cream,
    { position: [0, DECK, (gateZ0 + gateZ1) / 2], parent: root });
  const frame = [[-0.66, 0], [0.66, 0], [0.66, 0.72], [0.4, 0.96], [-0.4, 0.96], [-0.66, 0.72]];
  const door = [[-0.44, 0.04], [0.44, 0.04], [0.44, 0.62], [0.28, 0.78], [-0.28, 0.78], [-0.44, 0.62]];
  createPart('GateFrame', await extrudeProfile(frame, { depth: 0.12, axis: 'z', holes: [door] }), gold,
    { position: [0, DECK, gateZ1 + 0.05], parent: root });
  createPart('GateDoor', await extrudeProfile(door, { depth: 0.04, axis: 'z' }), glow,
    { position: [0, DECK, gateZ1 + 0.01], parent: root });
  createPart('GateCap', await roundedBoxGeo(0.5, 0.22, 0.5, 0.05, { style: 'chamfer' }), cream, { position: [0, DECK + 1.1, gateZ1 - 0.3], parent: root });
  for (const s of [-1, 1]) {
    createPart(`GateCapSlot${s}`, boxGeo(0.05, 0.12, 0.03), team, { position: [s * 0.07, DECK + 1.1, gateZ1 - 0.04], parent: root });
    createPart(`GateSideLight${s}`, boxGeo(0.03, 0.34, 0.12), team, { position: [s * 0.83, DECK + 0.42, gateZ1 - 0.2], parent: root });
  }
  // ramp: wedge from the gate down to the plate top, inside the footprint
  const rampLen = 2.45 - gateZ1;
  const rampRise = DECK - PLINTH_H;
  createPart('Ramp', await extrudeProfile([[0, 0], [-rampLen, 0], [0, rampRise]], { depth: 1.0, axis: 'x' }), dark,
    { position: [0, PLINTH_H, gateZ1], parent: root });
  for (const s of [-1, 1]) {
    const len = Math.hypot(rampLen, rampRise);
    const ang = Math.atan2(rampRise, rampLen) * 180 / Math.PI;
    createPart(`RampLight${s}`, boxGeo(0.06, 0.02, len * 0.85), team,
      { position: [s * 0.24, PLINTH_H + rampRise / 2 + 0.015, gateZ1 + rampLen / 2], rotation: [ang, 0, 0], parent: root });
  }
  return root;
}
