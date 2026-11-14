// Shardfall: Ambron Void Machine (extractor), from art/ambron_buildings/concepts/shardfall_ambron_void_machine.png
// Front faces +Z. 3 x 3 m footprint. Sits over a slime pile: a basin of glowing purple slime,
// a piston down into it, a drum housing on four splayed legs and two slime tanks at the sides.
const meta = { name: 'Ambron Void Machine', role: 'building' };

const CREAM = 0xe8dcc3, GOLD = 0xe2a531, DARK = 0x2c2e35, CYAN = 0x5fe3ff;
const SLIME = 0x9d3cff;
const DRUM_Y = 1.2;     // bottom of the drum housing
const DRUM_H = 0.6;
const DR = 0.84;        // drum radius

function at(theta, r, y) {
  const a = theta * Math.PI / 180;
  return [Math.cos(a) * r, y, Math.sin(a) * r];
}

async function build() {
  const root = createRoot('AmbronVoidMachine');
  const cream = gameMaterial(CREAM, { roughness: 0.55, name: 'cream', flatShading: false });
  const gold = gameMaterial(GOLD, { roughness: 0.35, metalness: 0.55, name: 'gold', flatShading: false });
  const dark = gameMaterial(DARK, { roughness: 0.6, metalness: 0.2, name: 'graphite', flatShading: false });
  const glow = gameMaterial(CYAN, { emissive: CYAN, emissiveIntensity: 2.2, roughness: 0.3, name: 'glow_cyan', flatShading: false });
  const team = gameMaterial(CYAN, { emissive: CYAN, emissiveIntensity: 1.2, roughness: 0.4, name: 'team', flatShading: false });
  const slimeGlow = gameMaterial(SLIME, { emissive: SLIME, emissiveIntensity: 1.6, roughness: 0.2, name: 'glow_slime', flatShading: false });
  const slime = gameMaterial(0x2a1240, { roughness: 0.15, metalness: 0.1, name: 'slime', flatShading: false });

  // basin: low ring wall round a pool of slime
  createPart('BasinFoot', cylinderGeo(1.3, 1.36, 0.1, 40), dark, { position: [0, 0.05, 0], parent: root });
  createPart('BasinWall', await revolveProfile([[0.95, 0], [1.28, 0], [1.28, 0.26], [1.2, 0.36], [0.95, 0.36]], { segments: 40, smooth: false }), cream,
    { position: [0, 0.1, 0], parent: root });
  createPart('BasinRim', torusGeo(1.12, 0.04, 8, 48), gold, { position: [0, 0.47, 0], rotation: [90, 0, 0], parent: root });
  createPart('Pool', cylinderGeo(0.97, 0.97, 0.2, 40), slime, { position: [0, 0.22, 0], parent: root });
  createPart('PoolGlow', cylinderGeo(0.55, 0.75, 0.04, 32), slimeGlow, { position: [0, 0.33, 0], parent: root });
  const blobs = [[0.55, 0.36, 0.2], [-0.5, 0.36, 0.35], [0.2, 0.35, -0.6], [-0.35, 0.36, -0.4], [0.6, 0.34, -0.2], [-0.15, 0.37, 0.6]];
  blobs.forEach(([x, y, z], i) => {
    createPart(`SlimeBlob${i}`, sphereGeo(0.16 + 0.04 * (i % 3), 12, 8), slime, { position: [x, y, z], scale: [1, 0.55, 1], parent: root });
  });
  for (const th of [90, 210, 330]) {
    createPart(`BasinBlock${th}`, await roundedBoxGeo(0.2, 0.3, 0.42, 0.04, { style: 'chamfer' }), gold,
      { position: at(th, 1.26, 0.27), rotation: [0, -th, 0], parent: root });
    createPart(`BasinSlot${th}`, boxGeo(0.04, 0.08, 0.3), team, { position: at(th, 1.37, 0.3), rotation: [0, -th, 0], parent: root });
  }

  // four splayed legs on the diagonals
  for (const th of [45, 135, 225, 315]) {
    const g = createPivot(`Leg${th}`, [0, 0, 0], root);
    g.rotation.set(0, -th * Math.PI / 180, 0);
    createPart(`Foot${th}`, await roundedBoxGeo(0.5, 0.18, 0.42, 0.05, { style: 'chamfer' }), dark, { position: [1.28, 0.09, 0], parent: g });
    createPart(`Toe${th}`, await roundedBoxGeo(0.16, 0.12, 0.36, 0.03, { style: 'chamfer' }), gold, { position: [1.5, 0.2, 0], parent: g });
    createPart(`Shin${th}`, await roundedBoxGeo(0.3, 1.35, 0.36, 0.06, { style: 'chamfer' }), cream,
      { position: [1.02, 0.74, 0], rotation: [0, 0, 26], parent: g });
    createPart(`Knee${th}`, await roundedBoxGeo(0.34, 0.16, 0.4, 0.04, { style: 'chamfer' }), gold,
      { position: [0.98, 0.84, 0], rotation: [0, 0, 26], parent: g });
    createPart(`LegSlot${th}`, boxGeo(0.04, 0.32, 0.08), team, { position: [1.2, 0.55, 0], rotation: [0, 0, 26], parent: g });
  }

  // drum housing on the legs, with a gold band and light slots
  createPart('Drum', await revolveProfile([[0.3, 0], [DR - 0.1, 0], [DR, 0.12], [DR, 0.44], [DR - 0.12, DRUM_H], [0.3, DRUM_H]], { segments: 40, smooth: false }), cream,
    { position: [0, DRUM_Y, 0], parent: root });
  createPart('DrumBand', cylinderGeo(DR + 0.015, DR + 0.015, 0.1, 40), gold, { position: [0, DRUM_Y + 0.08, 0], parent: root });
  createPart('DrumUnder', cylinderGeo(DR - 0.1, 0.55, 0.14, 32), dark, { position: [0, DRUM_Y - 0.06, 0], parent: root });
  for (const th of [30, 90, 150, 210, 270, 330]) {
    createPart(`DrumPanel${th}`, await roundedBoxGeo(0.12, 0.3, 0.36, 0.03, { style: 'chamfer' }), th === 90 ? gold : dark,
      { position: at(th, DR - 0.02, DRUM_Y + 0.3), rotation: [0, -th, 0], parent: root });
    createPart(`DrumSlot${th}`, boxGeo(0.04, 0.16, 0.06), team, { position: at(th, DR + 0.05, DRUM_Y + 0.3), rotation: [0, -th, 0], parent: root });
  }
  const capY = DRUM_Y + DRUM_H;
  createPart('Cap', cylinderGeo(0.46, 0.55, 0.16, 32), dark, { position: [0, capY + 0.08, 0], parent: root });
  createPart('CapRim', torusGeo(0.42, 0.04, 8, 32), gold, { position: [0, capY + 0.17, 0], rotation: [90, 0, 0], parent: root });
  createPart('CapLight', cylinderGeo(0.34, 0.34, 0.04, 32), glow, { position: [0, capY + 0.17, 0], parent: root });

  // two gold horns on top, toward the back
  const blade = [[-0.14, 0], [0.14, 0], [0.1, 0.55], [0.02, 0.78], [-0.08, 0.62]];
  for (const s of [-1, 1]) {
    const g = createPivot(`Horn${s}`, [s * 0.55, capY - 0.08, -0.22], root);
    g.rotation.set(0, 0, -s * 10 * Math.PI / 180);
    const shape = s < 0 ? blade.map(([u, v]) => [-u, v]) : blade;
    createPart(`HornBlade${s}`, await extrudeProfile(shape, { depth: 0.14, axis: 'z', bevel: 0.03, bevelStyle: 'chamfer' }), gold, { parent: g });
    createPart(`HornLight${s}`, boxGeo(0.05, 0.36, 0.03), team, { position: [s * 0.02, 0.36, 0.075], parent: g });
  }

  // piston down into the slime
  createPart('Piston', cylinderGeo(0.26, 0.26, DRUM_Y - 0.3, 24), dark, { position: [0, 0.3 + (DRUM_Y - 0.3) / 2, 0], parent: root });
  createPart('PistonCollar', cylinderGeo(0.34, 0.34, 0.16, 24), gold, { position: [0, DRUM_Y - 0.18, 0], parent: root });
  createPart('PistonFoot', cylinderGeo(0.3, 0.3, 0.12, 24), gold, { position: [0, 0.46, 0], parent: root });
  createPart('PistonTip', cylinderGeo(0.16, 0.2, 0.22, 20), slimeGlow, { position: [0, 0.33, 0], parent: root });
  for (const th of [60, 90, 120]) {
    createPart(`PistonSlot${th}`, boxGeo(0.03, 0.26, 0.05), team, { position: at(th, 0.265, 0.78), rotation: [0, -th, 0], parent: root });
  }

  // slime tanks at the sides, piped into the drum
  for (const s of [-1, 1]) {
    const x = s * 1.22;
    createPart(`TankPost${s}`, cylinderGeo(0.15, 0.2, 0.66, 16), dark, { position: [x, 0.33, 0.1], parent: root });
    createPart(`TankPostRing${s}`, torusGeo(0.17, 0.03, 8, 20), gold, { position: [x, 0.3, 0.1], rotation: [90, 0, 0], parent: root });
    createPart(`TankBase${s}`, cylinderGeo(0.34, 0.36, 0.16, 24), cream, { position: [x, 0.72, 0.1], parent: root });
    createPart(`TankSlime${s}`, cylinderGeo(0.27, 0.27, 0.62, 24), slimeGlow, { position: [x, 1.1, 0.1], parent: root });
    createPart(`TankTop${s}`, cylinderGeo(0.36, 0.34, 0.18, 24), cream, { position: [x, 1.5, 0.1], parent: root });
    createPart(`TankRingLow${s}`, torusGeo(0.3, 0.035, 8, 28), gold, { position: [x, 0.82, 0.1], rotation: [90, 0, 0], parent: root });
    createPart(`TankRingHigh${s}`, torusGeo(0.3, 0.035, 8, 28), gold, { position: [x, 1.4, 0.1], rotation: [90, 0, 0], parent: root });
    createPart(`TankSlot${s}`, boxGeo(0.03, 0.06, 0.18), team, { position: [x, 1.52, 0.47], rotation: [0, 90, 0], parent: root });
    createPart(`PipeUp${s}`, cylinderGeo(0.09, 0.09, 0.32, 12), dark, { position: [x, 1.74, 0.1], parent: root });
    createPart(`PipeBend${s}`, sphereGeo(0.1, 12, 8), dark, { position: [x, 1.9, 0.1], parent: root });
    createPart(`PipeAcross${s}`, cylinderGeo(0.09, 0.09, 0.5, 12), dark, { position: [s * 0.98, 1.9, 0.1], rotation: [0, 0, 90], parent: root });
  }
  return root;
}
