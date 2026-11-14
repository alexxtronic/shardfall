// Shardfall: Ambron Mech Forge (vehicle factory), from art/ambron_buildings/concepts/shardfall_ambron_forge.png
// Front faces +Z. 3 x 3 m footprint. A heavy cream hangar with a lit roll-up gate between two big
// armoured buttresses, a gantry arch over the roof carrying a hanging claw, an annex with twin
// exhaust stacks at the back right, and a gold-framed vent on the right side.
const meta = { name: 'Ambron Mech Forge', role: 'building' };

const CREAM = 0xe8dcc3, GOLD = 0xe2a531, DARK = 0x2c2e35, CYAN = 0x5fe3ff;
const W = 2.5, D = 2.3;          // main block
const P = 0.14;                  // plinth height
const BH = 1.05;                 // main block height
const RIM = 0.4;                 // the thick cream rim round the roof
const TOP = P + BH + RIM;        // roof level

function chamferRect(hw, hd, c) {
  return [[-hw + c, -hd], [hw - c, -hd], [hw, -hd + c], [hw, hd - c], [hw - c, hd], [-hw + c, hd], [-hw, hd - c], [-hw, -hd + c]];
}

// a C-shaped claw finger in the XY plane, opening toward +X
function cProfile(ro, ri, a0, a1, n) {
  const out = [], inn = [];
  for (let i = 0; i <= n; i++) {
    const a = (a0 + (a1 - a0) * i / n) * Math.PI / 180;
    out.push([Math.cos(a) * ro, Math.sin(a) * ro]);
    inn.push([Math.cos(a) * ri, Math.sin(a) * ri]);
  }
  return out.concat(inn.reverse());
}

async function build() {
  const root = createRoot('AmbronMechForge');
  const cream = gameMaterial(CREAM, { roughness: 0.55, name: 'cream', flatShading: false });
  const gold = gameMaterial(GOLD, { roughness: 0.35, metalness: 0.55, name: 'gold', flatShading: false });
  const dark = gameMaterial(DARK, { roughness: 0.6, metalness: 0.2, name: 'graphite', flatShading: false });
  const glow = gameMaterial(CYAN, { emissive: CYAN, emissiveIntensity: 2.2, roughness: 0.3, name: 'glow_cyan', flatShading: false });
  const team = gameMaterial(CYAN, { emissive: CYAN, emissiveIntensity: 1.2, roughness: 0.4, name: 'team', flatShading: false });
  const rb = (w, h, d, r) => roundedBoxGeo(w, h, d, r, { style: 'chamfer' });

  // plinth, main block and the thick rim round the roof
  createPart('Plinth', await extrudeProfile(chamferRect(1.45, 1.4, 0.2), { depth: P, bevel: 0.03, bevelStyle: 'chamfer' }), dark,
    { position: [0, P / 2, 0], parent: root });
  createPart('Block', await rb(W, BH, D, 0.1), cream, { position: [0, P + BH / 2, -0.05], parent: root });
  createPart('Skirt', await rb(W + 0.06, 0.16, D + 0.06, 0.05), dark, { position: [0, P + 0.08, -0.05], parent: root });
  createPart('Rim', await rb(W + 0.1, RIM, D + 0.1, 0.12), cream, { position: [0, P + BH + RIM / 2, -0.05], parent: root });
  createPart('RimBand', await rb(W + 0.14, 0.08, D + 0.14, 0.03), dark, { position: [0, P + BH + 0.02, -0.05], parent: root });
  createPart('RoofDeck', boxGeo(W - 0.3, 0.05, D - 0.3), dark, { position: [0, TOP + 0.005, -0.05], parent: root });
  for (let k = -2; k <= 2; k++) {
    createPart(`DeckRib${k}`, boxGeo(0.06, 0.04, D - 0.5), dark, { position: [k * 0.4, TOP + 0.04, -0.05], parent: root });
  }
  for (const s of [-1, 1]) {
    createPart(`DeckStripe${s}`, boxGeo(0.26, 0.02, 0.1), gold, { position: [s * 0.55, TOP + 0.035, 0.75], parent: root });
  }
  // rim details: a gold block with three slots over the gate, light slots along the front and side
  const fz = D / 2 + 0.0;
  createPart('RimBlock', await rb(0.6, 0.36, 0.14, 0.05), gold, { position: [0, P + BH + RIM / 2, fz], parent: root });
  for (const x of [-0.12, 0, 0.12]) {
    createPart(`RimBlockSlot${x}`, boxGeo(0.05, 0.2, 0.03), team, { position: [x, P + BH + RIM / 2, fz + 0.075], parent: root });
  }
  for (const s of [-1, 1]) {
    createPart(`RimSlot${s}`, boxGeo(0.4, 0.07, 0.03), team, { position: [s * 0.65, P + BH + RIM / 2, fz + 0.005], parent: root });
    createPart(`RimSideSlot${s}`, boxGeo(0.03, 0.07, 0.4), team, { position: [s * (W / 2 + 0.055), P + BH + RIM / 2, 0.3], parent: root });
  }

  // gate: gold frame with chamfered top corners, dark door with two lit seams, ramp with gold treads
  createPart('GateFrame', await extrudeProfile(chamferRect(0.72, 0.52, 0.16), { depth: 0.1, axis: 'z', holes: [chamferRect(0.6, 0.45, 0.1)] }), gold,
    { position: [0, P + 0.5, fz + 0.03], parent: root });
  createPart('GateDoor', boxGeo(1.24, 0.92, 0.05), dark, { position: [0, P + 0.48, fz], parent: root });
  for (const y of [0.3, 0.62]) {
    createPart(`GateSeam${y}`, boxGeo(1.05, 0.04, 0.03), glow, { position: [0, P + y, fz + 0.035], parent: root });
    for (const s of [-1, 1]) {
      createPart(`GateSeamEnd${y}${s}`, boxGeo(0.04, 0.12, 0.03), glow, { position: [s * 0.54, P + y + 0.06, fz + 0.035], parent: root });
    }
  }
  createPart('Ramp', boxGeo(1.25, 0.06, 0.4), dark, { position: [0, P + 0.0, fz + 0.2], parent: root });
  for (const s of [-1, 1]) {
    for (const k of [0, 1]) {
      createPart(`Tread${s}${k}`, boxGeo(0.22, 0.03, 0.06), gold, { position: [s * 0.45, P + 0.04, fz + 0.12 + k * 0.14], parent: root });
    }
  }

  // two big front buttresses either side of the gate, smaller ones at the back
  for (const s of [-1, 1]) {
    const x = s * (W / 2 - 0.04), z = D / 2 - 0.08;
    createPart(`ButtFoot${s}`, await rb(0.82, 0.18, 0.84, 0.05), dark, { position: [x, P + 0.09, z], parent: root });
    createPart(`ButtFootSlot${s}`, boxGeo(0.36, 0.06, 0.03), team, { position: [x, P + 0.09, z + 0.43], parent: root });
    createPart(`ButtGold${s}`, await rb(0.78, 0.34, 0.8, 0.08), gold, { position: [x, P + 0.33, z], parent: root });
    createPart(`Butt${s}`, cylinderGeo(0.3, 0.42, 1.05, 4), cream, { position: [x, P + 0.98, z], rotation: [0, 45, 0], scale: [1, 1, 1.0], parent: root });
    createPart(`ButtSlot${s}`, boxGeo(0.08, 0.5, 0.03), team, { position: [x, P + 0.98, z + 0.26], rotation: [-6.5, 0, 0], parent: root });
    createPart(`ButtCap${s}`, await rb(0.6, 0.22, 0.6, 0.08), gold, { position: [x, P + 1.56, z], parent: root });
    const bx = s * (W / 2 - 0.1), bz = -D / 2 + 0.05;
    createPart(`BackButt${s}`, await rb(0.42, 1.2, 0.42, 0.08), cream, { position: [bx, P + 0.6, bz], parent: root });
    createPart(`BackButtFoot${s}`, await rb(0.5, 0.2, 0.5, 0.05), gold, { position: [bx, P + 0.1, bz], parent: root });
  }

  // gold-framed slatted vent on the right side
  createPart('VentFrame', await rb(0.1, 0.62, 0.86, 0.04), gold, { position: [W / 2 + 0.02, P + 0.55, -0.15], parent: root });
  for (let k = 0; k < 5; k++) {
    createPart(`VentSlat${k}`, boxGeo(0.05, 0.06, 0.7), dark, { position: [W / 2 + 0.08, P + 0.35 + k * 0.1, -0.15], parent: root });
  }
  createPart('VentLeft', await rb(0.1, 0.62, 0.86, 0.04), gold, { position: [-W / 2 - 0.02, P + 0.55, -0.15], parent: root });
  for (const z of [-0.35, 0.05]) {
    createPart(`VentLeftSlot${z}`, boxGeo(0.03, 0.42, 0.06), team, { position: [-W / 2 - 0.08, P + 0.55, z], parent: root });
  }

  // gantry arch over the roof: angled legs, a beam across, a hub and a hanging claw
  const gz = -0.15, legTop = TOP + 1.05;
  for (const s of [-1, 1]) {
    const x = s * 1.08;
    createPart(`LegBase${s}`, await rb(0.5, 0.36, 0.56, 0.08), cream, { position: [x, TOP + 0.18, gz], parent: root });
    createPart(`LegBaseSlot${s}`, boxGeo(0.2, 0.07, 0.03), team, { position: [x, TOP + 0.18, gz + 0.29], parent: root });
    createPart(`Leg${s}`, await rb(0.42, 0.95, 0.48, 0.08), cream, { position: [x - s * 0.04, TOP + 0.75, gz], rotation: [0, 0, s * 6], parent: root });
    createPart(`LegGold${s}`, await rb(0.12, 0.7, 0.3, 0.04), gold, { position: [x - s * 0.2, TOP + 0.72, gz], rotation: [0, 0, s * 6], parent: root });
    createPart(`LegSlot${s}`, boxGeo(0.08, 0.34, 0.03), team, { position: [x - s * 0.04, TOP + 0.72, gz + 0.25], rotation: [0, 0, s * 6], parent: root });
    createPart(`Shoulder${s}`, await rb(0.62, 0.42, 0.52, 0.1), cream, { position: [x - s * 0.12, legTop, gz], rotation: [0, 0, -s * 28], parent: root });
    createPart(`ShoulderGold${s}`, await rb(0.36, 0.12, 0.56, 0.04), gold, { position: [x - s * 0.22, legTop - 0.12, gz], rotation: [0, 0, -s * 28], parent: root });
    createPart(`BeamLight${s}`, boxGeo(0.3, 0.07, 0.03), team, { position: [s * 0.48, legTop + 0.08, gz + 0.13], parent: root });
  }
  createPart('Beam', await rb(1.6, 0.18, 0.24, 0.05), dark, { position: [0, legTop + 0.08, gz], parent: root });
  createPart('BeamTrim', boxGeo(1.4, 0.04, 0.26), gold, { position: [0, legTop + 0.19, gz], parent: root });
  createPart('Hub', await rb(0.42, 0.42, 0.4, 0.1), cream, { position: [0, legTop + 0.1, gz], parent: root });
  createPart('HubGold', await rb(0.46, 0.14, 0.44, 0.04), gold, { position: [0, legTop - 0.1, gz], parent: root });
  createPart('HubSlot', boxGeo(0.1, 0.16, 0.03), team, { position: [0, legTop + 0.14, gz + 0.205], parent: root });
  createPart('ClawRod', cylinderGeo(0.07, 0.07, 0.3, 10), dark, { position: [0, legTop - 0.3, gz], parent: root });
  createPart('ClawCollar', cylinderGeo(0.17, 0.13, 0.14, 16), gold, { position: [0, legTop - 0.46, gz], parent: root });
  createPart('ClawKnuckle', sphereGeo(0.1, 12, 8), dark, { position: [0, legTop - 0.56, gz], parent: root });
  for (const s of [-1, 1]) {
    const g = createPivot(`Finger${s}`, [s * 0.05, legTop - 0.8, gz], root);
    g.rotation.set(0, s < 0 ? 0 : Math.PI, 0);
    createPart(`FingerShell${s}`, await extrudeProfile(cProfile(0.27, 0.16, 105, 255, 9), { depth: 0.14, axis: 'z', bevel: 0.015, bevelStyle: 'chamfer' }), cream,
      { position: [0.24, 0, 0], parent: g });
    createPart(`FingerLight${s}`, boxGeo(0.03, 0.14, 0.08), glow, { position: [0.09, 0, 0], parent: g });
  }

  // annex with twin exhaust stacks, back right on the roof
  const ax = 0.7, az = -0.75;
  createPart('Annex', await rb(0.85, 0.5, 0.62, 0.1), cream, { position: [ax, TOP + 0.25, az], parent: root });
  createPart('AnnexGrille', boxGeo(0.4, 0.2, 0.03), dark, { position: [ax, TOP + 0.27, az + 0.31], parent: root });
  for (const k of [0, 1, 2]) {
    createPart(`AnnexSlot${k}`, boxGeo(0.32, 0.03, 0.03), team, { position: [ax, TOP + 0.2 + k * 0.07, az + 0.33], parent: root });
  }
  for (const dx of [-0.2, 0.2]) {
    const x = ax + dx;
    createPart(`Stack${dx}`, cylinderGeo(0.12, 0.14, 0.55, 16), dark, { position: [x, TOP + 0.77, az], parent: root });
    createPart(`StackBand${dx}`, cylinderGeo(0.135, 0.135, 0.08, 16), glow, { position: [x, TOP + 0.85, az], parent: root });
    createPart(`StackCap${dx}`, await revolveProfile([[0.07, 0], [0.15, 0], [0.16, 0.06], [0.15, 0.14], [0.07, 0.14]], { segments: 16, smooth: false }), gold,
      { position: [x, TOP + 1.03, az], parent: root });
  }

  // gold handrails on the roof
  for (const [x, z, len, ry] of [[-0.75, 0.85, 0.5, 0], [0.75, 0.85, 0.5, 0], [-1.05, -0.9, 0.5, 90]]) {
    const g = createPivot(`Rail${x}${z}`, [x, TOP, z], root);
    g.rotation.set(0, ry * Math.PI / 180, 0);
    createPart(`RailBar${x}${z}`, cylinderGeo(0.025, 0.025, len, 8), gold, { position: [0, 0.16, 0], rotation: [0, 0, 90], parent: g });
    for (const s of [-1, 1]) {
      createPart(`RailPost${x}${z}${s}`, cylinderGeo(0.025, 0.025, 0.16, 8), gold, { position: [s * len / 2, 0.08, 0], parent: g });
    }
  }
  return root;
}
