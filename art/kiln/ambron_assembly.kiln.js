// Shardfall: Ambron Assembly Bay (infantry factory), from art/ambron_buildings/concepts/shardfall_ambron_assembly.png
// Front faces +Z. 3 x 3 m footprint. A chunky chamfered hangar with a roll-up gate lit at the
// seams, armoured corner pillars, slatted side vents, a robot assembly arm and an antenna mast.
const meta = { name: 'Ambron Assembly Bay', role: 'building' };

const CREAM = 0xe8dcc3, GOLD = 0xe2a531, DARK = 0x2c2e35, CYAN = 0x5fe3ff;
const W = 2.5, D = 2.3, BODY_H = 1.45, PLINTH = 0.14;

function chamferRect(hw, hd, c) {
  return [[-hw + c, -hd], [hw - c, -hd], [hw, -hd + c], [hw, hd - c], [hw - c, hd], [-hw + c, hd], [-hw, hd - c], [-hw, -hd + c]];
}

async function build() {
  const root = createRoot('AmbronAssemblyBay');
  const cream = gameMaterial(CREAM, { roughness: 0.55, name: 'cream', flatShading: false });
  const gold = gameMaterial(GOLD, { roughness: 0.35, metalness: 0.55, name: 'gold', flatShading: false });
  const dark = gameMaterial(DARK, { roughness: 0.6, metalness: 0.2, name: 'graphite', flatShading: false });
  const glow = gameMaterial(CYAN, { emissive: CYAN, emissiveIntensity: 2.2, roughness: 0.3, name: 'glow_cyan', flatShading: false });
  const team = gameMaterial(CYAN, { emissive: CYAN, emissiveIntensity: 1.2, roughness: 0.4, name: 'team', flatShading: false });
  const rb = (w, h, d, r) => roundedBoxGeo(w, h, d, r, { style: 'chamfer' });

  // plinth and hangar body
  createPart('Plinth', await extrudeProfile(chamferRect(1.45, 1.42, 0.22), { depth: PLINTH, bevel: 0.03, bevelStyle: 'chamfer' }), dark,
    { position: [0, PLINTH / 2, 0], parent: root });
  createPart('Body', await rb(W, BODY_H, D, 0.16), cream, { position: [0, PLINTH + BODY_H / 2, -0.05], parent: root });
  createPart('BodyBand', await rb(W + 0.04, 0.12, D + 0.04, 0.05), gold, { position: [0, PLINTH + BODY_H - 0.22, -0.05], parent: root });
  createPart('Roof', await rb(W - 0.5, 0.32, D - 0.55, 0.1), cream, { position: [0, PLINTH + BODY_H + 0.14, -0.15], parent: root });
  createPart('RoofDeck', boxGeo(W - 0.75, 0.04, D - 0.8), dark, { position: [0, PLINTH + BODY_H + 0.31, -0.15], parent: root });
  for (const [x, z, ry] of [[0, (D - 0.55) / 2 - 0.15 + 0.005, 0], [0, -(D - 0.55) / 2 - 0.15 - 0.005, 0]]) {
    createPart(`RoofSlot${z}`, boxGeo(0.7, 0.07, 0.03), team, { position: [x, PLINTH + BODY_H + 0.14, z], parent: root });
  }

  // front gate: gold frame, dark roll-up door with lit seams, gold kick plates
  const fz = D / 2 - 0.05;
  createPart('GateFrame', await extrudeProfile(chamferRect(0.78, 0.66, 0.12), { depth: 0.12, axis: 'z', holes: [chamferRect(0.6, 0.55, 0.06)] }), gold,
    { position: [0, PLINTH + 0.62, fz + 0.06], parent: root });
  createPart('GateDoor', boxGeo(1.22, 1.12, 0.06), dark, { position: [0, PLINTH + 0.62, fz + 0.01], parent: root });
  for (const y of [0.3, 0.62, 0.94]) {
    createPart(`GateSeam${y}`, boxGeo(1.0, 0.045, 0.03), glow, { position: [0, PLINTH + y, fz + 0.05], parent: root });
  }
  createPart('GateHood', await rb(0.9, 0.24, 0.3, 0.06), cream, { position: [0, PLINTH + 1.36, fz + 0.06], parent: root });
  createPart('GateHoodSlot', boxGeo(0.4, 0.07, 0.03), team, { position: [0, PLINTH + 1.36, fz + 0.22], parent: root });
  createPart('Apron', boxGeo(1.3, 0.04, 0.32), dark, { position: [0, PLINTH + 0.02, fz + 0.18], parent: root });
  for (const s of [-1, 1]) {
    createPart(`ApronStripe${s}`, boxGeo(0.3, 0.02, 0.24), gold, { position: [s * 0.45, PLINTH + 0.05, fz + 0.2], parent: root });
  }

  // armoured corner pillars with lit slots
  for (const sx of [-1, 1]) {
    for (const sz of [-1, 1]) {
      const x = sx * (W / 2 - 0.1), z = sz * (D / 2 - 0.12) - 0.05;
      createPart(`Pillar${sx}${sz}`, await rb(0.5, BODY_H + 0.15, 0.52, 0.08), cream, { position: [x, PLINTH + (BODY_H + 0.15) / 2, z], parent: root });
      createPart(`PillarFoot${sx}${sz}`, await rb(0.58, 0.26, 0.6, 0.05), gold, { position: [x, PLINTH + 0.13, z], parent: root });
      createPart(`PillarCap${sx}${sz}`, await rb(0.56, 0.16, 0.58, 0.05), gold, { position: [x, PLINTH + BODY_H + 0.12, z], parent: root });
      createPart(`PillarSlot${sx}${sz}`, boxGeo(0.08, 0.5, 0.03), team, { position: [x, PLINTH + 0.75, z + sz * 0.27], parent: root });
      createPart(`PillarSlotSide${sx}${sz}`, boxGeo(0.03, 0.5, 0.08), team, { position: [x + sx * 0.26, PLINTH + 0.75, z], parent: root });
    }
  }

  // slatted vents on both sides
  for (const s of [-1, 1]) {
    const x = s * (W / 2 + 0.02);
    createPart(`Vent${s}`, await rb(0.12, 0.7, 0.9, 0.03), gold, { position: [x, PLINTH + 0.7, -0.05], parent: root });
    for (let k = 0; k < 4; k++) {
      createPart(`VentSlat${s}${k}`, boxGeo(0.05, 0.08, 0.72), dark, { position: [x + s * 0.05, PLINTH + 0.47 + k * 0.15, -0.05], parent: root });
    }
  }

  // robot assembly arm on the roof
  const ry = PLINTH + BODY_H + 0.33;
  createPart('ArmBase', cylinderGeo(0.36, 0.42, 0.14, 24), dark, { position: [-0.2, ry + 0.07, -0.25], parent: root });
  createPart('ArmBaseRing', torusGeo(0.34, 0.04, 8, 24), gold, { position: [-0.2, ry + 0.15, -0.25], rotation: [90, 0, 0], parent: root });
  for (const th of [0, 120, 240]) {
    const a = th * Math.PI / 180;
    createPart(`ArmBaseLight${th}`, boxGeo(0.1, 0.05, 0.03), team, { position: [-0.2 + Math.cos(a) * 0.4, ry + 0.07, -0.25 + Math.sin(a) * 0.4], rotation: [0, -th - 90, 0], parent: root });
  }
  const arm = createPivot('Arm', [-0.2, ry + 0.15, -0.25], root);
  arm.rotation.set(0, 25 * Math.PI / 180, 0);
  createPart('ArmShoulder', cylinderGeo(0.14, 0.14, 0.3, 16), gold, { position: [0, 0.12, 0], rotation: [90, 0, 0], parent: arm });
  createPart('ArmUpper', await rb(0.2, 0.75, 0.22, 0.05), cream, { position: [0.12, 0.45, 0], rotation: [0, 0, -18], parent: arm });
  createPart('ArmElbow', cylinderGeo(0.13, 0.13, 0.28, 16), dark, { position: [0.24, 0.82, 0], rotation: [90, 0, 0], parent: arm });
  createPart('ArmElbowLight', cylinderGeo(0.07, 0.07, 0.3, 12), glow, { position: [0.24, 0.82, 0], rotation: [90, 0, 0], parent: arm });
  createPart('ArmFore', await rb(0.6, 0.18, 0.2, 0.05), cream, { position: [0.5, 0.74, 0], rotation: [0, 0, -18], parent: arm });
  createPart('ArmWrist', cylinderGeo(0.1, 0.1, 0.24, 12), gold, { position: [0.78, 0.62, 0], rotation: [90, 0, 0], parent: arm });
  for (const s of [-1, 1]) {
    createPart(`Claw${s}`, await rb(0.06, 0.28, 0.06, 0.02), gold, { position: [0.8 + s * 0.08, 0.45, 0], rotation: [0, 0, s * 15], parent: arm });
  }

  // antenna mast, back right
  const mx = W / 2 - 0.55, mz = -D / 2 + 0.35;
  createPart('MastBlock', await rb(0.36, 0.5, 0.36, 0.06), cream, { position: [mx, ry + 0.2, mz], parent: root });
  createPart('MastCap', await rb(0.3, 0.1, 0.3, 0.03), gold, { position: [mx, ry + 0.5, mz], parent: root });
  createPart('MastSlot', boxGeo(0.18, 0.06, 0.03), team, { position: [mx, ry + 0.25, mz + 0.19], parent: root });
  createPart('MastRod', cylinderGeo(0.025, 0.035, 0.75, 8), dark, { position: [mx, ry + 0.9, mz], parent: root });
  createPart('MastTip', cylinderGeo(0.04, 0.04, 0.18, 8), glow, { position: [mx, ry + 1.32, mz], parent: root });
  createPart('MastRod2', cylinderGeo(0.02, 0.03, 0.45, 8), dark, { position: [mx - 0.14, ry + 0.75, mz], parent: root });
  return root;
}
