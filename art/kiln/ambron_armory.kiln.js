// Shardfall: Ambron Armory (upgrade building), from art/ambron_buildings/concepts/shardfall_ambron_armory.png
// Front faces +Z. 2.8 x 2.8 m footprint. A stepped octagonal graphite base, a chamfered cream block with
// a shutter door under a crossed-blaster emblem, a rifle rack on the left (-X) wall, and on the roof a
// lit workbench under a jointed robot arm holding a rifle, a console box and two antennas.
const meta = { name: 'Ambron Armory', role: 'building' };

const CREAM = 0xe8dcc3, GOLD = 0xe2a531, DARK = 0x2c2e35, CYAN = 0x5fe3ff;
const FOOT = 1.4, BASE1 = 0.16, BASE2 = 0.1, B = BASE1 + BASE2;      // half footprint, the two base steps
const HW = 1.15, CH = 0.25, WALL = 0.98;                              // body half width, corner chamfer, wall height
const SH = 0.34, TOP = 0.88, TOP_CH = 0.2, RIM = 0.08;                // sloped shoulder up to the roof
const SHY = B + WALL, RY = SHY + SH + RIM, DECK = RY + 0.02;
const DEG = Math.PI / 180;

function oct(hw, hd, c) {
  return [[-hw + c, -hd], [hw - c, -hd], [hw, -hd + c], [hw, hd - c], [hw - c, hd], [-hw + c, hd], [-hw, hd - c], [-hw, -hd + c]];
}

async function build() {
  const root = createRoot('AmbronArmory');
  const cream = gameMaterial(CREAM, { roughness: 0.55, name: 'cream', flatShading: false });
  const gold = gameMaterial(GOLD, { roughness: 0.35, metalness: 0.55, name: 'gold', flatShading: false });
  const dark = gameMaterial(DARK, { roughness: 0.6, metalness: 0.2, name: 'graphite', flatShading: false });
  const glow = gameMaterial(CYAN, { emissive: CYAN, emissiveIntensity: 2.2, roughness: 0.3, name: 'glow_cyan', flatShading: false });
  const team = gameMaterial(CYAN, { emissive: CYAN, emissiveIntensity: 1.2, roughness: 0.4, name: 'team', flatShading: false });
  const rb = (w, h, d, r) => roundedBoxGeo(w, h, d, r, { style: 'chamfer' });

  // one pivot per wall and per corner: local +Z points out of that wall, local +X runs along it
  const facing = (name, deg) => { const p = createPivot(name, [0, 0, 0], root); p.rotation.set(0, deg * DEG, 0); return p; };
  const front = facing('WallFront', 0), right = facing('WallRight', 90), back = facing('WallBack', 180), left = facing('WallLeft', -90);
  const corners = [45, 135, 225, 315].map((d) => facing(`Corner${d}`, d));

  // ---------- base: sloped skirt and a step ----------
  createPart('BaseSkirt', loftProfiles([{ profile: oct(FOOT, FOOT, 0.42) }, { profile: oct(FOOT - 0.07, FOOT - 0.07, 0.4), frame: { origin: [0, BASE1, 0] } }]), dark, { parent: root });
  createPart('BaseStep', await extrudeProfile(oct(1.3, 1.3, 0.39), { depth: BASE2 + 0.02, bevel: 0.02, bevelStyle: 'chamfer' }), dark,
    { position: [0, BASE1 + BASE2 / 2 - 0.01, 0], parent: root });
  const skirtLean = Math.atan2(0.07, BASE1) / DEG;
  const baseLight = (name, wall, x, w) => createPart(name, boxGeo(w, 0.075, 0.03), team,
    { position: [x, BASE1 / 2 + 0.002, FOOT - 0.035 + 0.004], rotation: [-skirtLean, 0, 0], parent: wall });
  const wedgeGeo = await rb(0.18, 0.13, 0.4, 0.03);
  const wedge = (name, wall, x) => createPart(name, wedgeGeo, gold, { position: [x, 0.215, 1.185], rotation: [30, 0, 0], parent: wall });

  // ---------- body: walls, sloped shoulder, roof ----------
  createPart('Body', await extrudeProfile(oct(HW, HW, CH), { depth: WALL, bevel: 0.03, bevelStyle: 'chamfer' }), cream, { position: [0, B + WALL / 2, 0], parent: root });
  createPart('Shoulder', loftProfiles([{ profile: oct(HW, HW, CH), frame: { origin: [0, SHY, 0] } }, { profile: oct(TOP, TOP, TOP_CH), frame: { origin: [0, SHY + SH, 0] } }]), cream, { parent: root });
  createPart('RoofRim', await extrudeProfile(oct(TOP, TOP, TOP_CH), { depth: RIM, bevel: 0.02, bevelStyle: 'chamfer' }), cream, { position: [0, SHY + SH + RIM / 2, 0], parent: root });
  createPart('RoofDeck', await extrudeProfile(oct(TOP - 0.09, TOP - 0.09, TOP_CH - 0.04), { depth: 0.04 }), dark, { position: [0, RY, 0], parent: root });

  // parts lying on the sloped shoulder of a wall (lift = centre distance above the slope)
  const slopeOf = (d0, d1) => { const a = Math.atan2(d0 - d1, SH); return { a: a / DEG, y: SHY + SH / 2, z: (d0 + d1) / 2, ny: Math.sin(a), nz: Math.cos(a), len: Math.hypot(d0 - d1, SH) }; };
  const wallSlope = slopeOf(HW, TOP);
  const cornerD0 = (HW - CH / 2) * Math.SQRT2, cornerD1 = (TOP - TOP_CH / 2) * Math.SQRT2;
  const cornerSlope = slopeOf(cornerD0, cornerD1);
  const onSlope = (name, wall, s, geo, mat, x, lift, along) => createPart(name, geo, mat,
    { position: [x, s.y + s.ny * lift + s.nz * (along || 0), s.z + s.nz * lift - s.ny * (along || 0)], rotation: [-s.a, 0, 0], parent: wall });
  const plateH = wallSlope.len - 0.05;
  const plate = async (name, wall, x, w) => onSlope(name, wall, wallSlope, await rb(w, plateH, 0.08, 0.025), cream, x, -0.01);
  const trim = async (name, wall, x) => onSlope(name, wall, wallSlope, await rb(0.11, plateH + 0.03, 0.1, 0.025), gold, x, 0.005);

  // corner armour: a foot and a shoulder plate on each chamfered corner
  const footGeo = await rb(0.44, 0.22, 0.16, 0.04), cornerPlateGeo = await rb(0.27, cornerSlope.len - 0.06, 0.08, 0.025);
  corners.forEach((c, i) => {
    createPart(`CornerFoot${i}`, footGeo, cream, { position: [0, B + 0.11, cornerD0], parent: c });
    onSlope(`CornerPlate${i}`, c, cornerSlope, cornerPlateGeo, cream, 0, -0.01);
  });

  // gold-framed graphite recess used on the left, right and back walls
  const recessGeo = await extrudeProfile(oct(0.68, 0.46, 0.1), { depth: 0.1, axis: 'z', holes: [oct(0.57, 0.37, 0.06)] });
  const recess = (name, wall) => {
    createPart(`${name}Frame`, recessGeo, gold, { position: [0, B + 0.5, HW + 0.04], parent: wall });
    createPart(`${name}Panel`, boxGeo(1.18, 0.78, 0.04), dark, { position: [0, B + 0.5, HW + 0.012], parent: wall });
  };

  // rifle: barrel along local +X, about 1.08 long before scaling
  const RG = {
    stock: await rb(0.26, 0.11, 0.07, 0.02), receiver: await rb(0.4, 0.13, 0.085, 0.025), guard: await rb(0.2, 0.1, 0.075, 0.02),
    muzzle: await rb(0.08, 0.075, 0.07, 0.015), grip: await rb(0.065, 0.14, 0.06, 0.015), mag: await rb(0.08, 0.1, 0.06, 0.015),
  };
  const rifle = (name, parent, pos, s) => {
    const p = createPivot(name, pos, parent);
    p.scale.setScalar(s);
    createPart(`${name}Stock`, RG.stock, cream, { position: [-0.36, -0.015, 0], parent: p });
    createPart(`${name}Butt`, boxGeo(0.04, 0.13, 0.075), dark, { position: [-0.505, -0.02, 0], parent: p });
    createPart(`${name}Receiver`, RG.receiver, cream, { position: [-0.04, 0, 0], parent: p });
    createPart(`${name}Cell`, boxGeo(0.2, 0.04, 0.095), glow, { position: [-0.02, 0.01, 0], parent: p });
    createPart(`${name}Rail`, boxGeo(0.24, 0.035, 0.05), dark, { position: [-0.04, 0.08, 0], parent: p });
    createPart(`${name}RailLight`, boxGeo(0.14, 0.02, 0.056), glow, { position: [-0.04, 0.098, 0], parent: p });
    createPart(`${name}Guard`, RG.guard, dark, { position: [0.25, -0.005, 0], parent: p });
    createPart(`${name}Barrel`, cylinderGeo(0.022, 0.022, 0.2, 8), dark, { position: [0.42, 0.01, 0], rotation: [0, 0, 90], parent: p });
    createPart(`${name}Muzzle`, RG.muzzle, dark, { position: [0.52, 0.01, 0], parent: p });
    createPart(`${name}Grip`, RG.grip, dark, { position: [-0.16, -0.12, 0], rotation: [0, 0, -15], parent: p });
    createPart(`${name}Mag`, RG.mag, dark, { position: [0.05, -0.105, 0], parent: p });
    return p;
  };

  // ---------- front wall: shutter door, gold yoke, lamps, emblem ----------
  const fz = HW;
  createPart('DoorSurround', boxGeo(1.34, 1.06, 0.04), dark, { position: [0, B + 0.53, fz + 0.012], parent: front });
  for (let k = 0; k < 6; k++) {
    createPart(`DoorSlat${k}`, await rb(1.02, 0.128, 0.05, 0.02), dark, { position: [0, B + 0.067 + k * 0.13, fz + 0.05], parent: front });
    if (k % 2 === 1) {
      createPart(`DoorStrip${k}`, boxGeo(0.6, 0.035, 0.02), glow, { position: [-0.04, B + 0.067 + k * 0.13, fz + 0.08], parent: front });
      createPart(`DoorStripTab${k}`, boxGeo(0.1, 0.035, 0.02), glow, { position: [0.3, B + 0.082 + k * 0.13, fz + 0.08], parent: front });
    }
  }
  const header = [[-0.64, 0.6], [-0.52, 0.6], [-0.52, 0.74], [-0.46, 0.8], [0.46, 0.8], [0.52, 0.74], [0.52, 0.6], [0.64, 0.6], [0.64, 0.84], [0.5, 0.98], [-0.5, 0.98], [-0.64, 0.84]];
  createPart('DoorHeader', await extrudeProfile(header, { depth: 0.11, axis: 'z' }), cream, { position: [0, B, fz + 0.065], parent: front });
  const yoke = [[-0.9, 0.7], [-0.66, 0.7], [-0.66, 0.9], [-0.52, 1.04], [0.52, 1.04], [0.66, 0.9], [0.66, 0.7], [0.9, 0.7], [0.9, 0.9], [0.68, 1.12], [-0.68, 1.12], [-0.9, 0.9]];
  createPart('DoorYoke', await extrudeProfile(yoke, { depth: 0.14, axis: 'z' }), gold, { position: [0, B, fz + 0.05], parent: front });
  for (const s of [-1, 1]) {
    const x = s * 0.78;
    createPart(`LampFrame${s}`, await extrudeProfile(oct(0.13, 0.3, 0.05), { depth: 0.12, axis: 'z', holes: [oct(0.065, 0.225, 0.03)] }), gold, { position: [x, B + 0.46, fz + 0.06], parent: front });
    createPart(`LampBack${s}`, boxGeo(0.15, 0.47, 0.04), dark, { position: [x, B + 0.46, fz + 0.03], parent: front });
    createPart(`Lamp${s}`, await rb(0.075, 0.38, 0.04, 0.015), glow, { position: [x, B + 0.46, fz + 0.065], parent: front });
    createPart(`LampFoot${s}`, await rb(0.34, 0.2, 0.16, 0.04), cream, { position: [x, B + 0.1, fz + 0.05], parent: front });
    baseLight(`BaseLightFront${s}`, front, s * 0.84, 0.24);
    wedge(`DoorWedge${s}`, front, s * 0.6);
  }
  createPart('Ramp', await rb(1.02, 0.06, 0.44, 0.02), dark, { position: [0, 0.206, 1.185], rotation: [30, 0, 0], parent: front });

  // pediment and the crossed-blaster emblem
  createPart('Pediment', await extrudeProfile([[-0.66, 0], [0.66, 0], [0.66, 0.32], [0.46, 0.52], [-0.46, 0.52], [-0.66, 0.32]], { depth: 0.32, axis: 'z' }), cream,
    { position: [0, SHY - 0.02, fz - 0.14], parent: front });
  const ey = SHY + 0.17, ez = fz + 0.12;
  createPart('EmblemRim', cylinderGeo(0.39, 0.39, 0.07, 32), gold, { position: [0, ey, ez + 0.035], rotation: [90, 0, 0], parent: front });
  createPart('EmblemRing', torusGeo(0.345, 0.05, 10, 32), gold, { position: [0, ey, ez + 0.07], parent: front });
  createPart('EmblemFace', cylinderGeo(0.31, 0.31, 0.03, 32), dark, { position: [0, ey, ez + 0.08], rotation: [90, 0, 0], parent: front });
  const blaster = (name, rotDeg, g) => {
    const p = createPivot(name, [0, ey, ez + 0.106], front);
    p.rotation.set(0, 0, rotDeg * DEG);
    createPart(`${name}Body`, boxGeo(0.52, 0.06, 0.024), glow, { position: [0.01, 0, 0], parent: p });
    createPart(`${name}Top`, boxGeo(0.2, 0.026, 0.024), glow, { position: [-0.12, 0.04 * g, 0], parent: p });
    createPart(`${name}Grip`, boxGeo(0.06, 0.1, 0.024), glow, { position: [-0.215, -0.07 * g, 0], rotation: [0, 0, 12 * g], parent: p });
    createPart(`${name}Guard`, boxGeo(0.05, 0.02, 0.024), glow, { position: [-0.15, -0.045 * g, 0], parent: p });
  };
  blaster('BlasterA', 45, 1);
  blaster('BlasterB', 135, -1);

  // ---------- left wall: rifle rack ----------
  recess('Rack', left);
  for (let k = 0; k < 3; k++) rifle(`RackRifle${k}`, left, [-0.02, B + 0.285 + k * 0.24, HW + 0.076], 0.9);
  await plate('LeftPlateFront', left, 0.33, 0.68);
  await trim('LeftTrim', left, -0.09);
  await plate('LeftPlateBack', left, -0.42, 0.5);
  onSlope('LeftVent', left, wallSlope, await rb(0.36, 0.22, 0.03, 0.01), dark, -0.42, 0.04);
  for (let k = -1; k <= 1; k++) onSlope(`LeftVentSlat${k}`, left, wallSlope, boxGeo(0.28, 0.028, 0.02), dark, -0.42, 0.058, k * 0.06);
  baseLight('BaseLightLeft', left, 0, 0.3);
  wedge('LeftWedgeA', left, -0.74);
  wedge('LeftWedgeB', left, 0.74);

  // ---------- right wall: ammunition lockers ----------
  recess('Locker', right);
  for (const s of [-1, 1]) {
    createPart(`LockerDoor${s}`, await rb(0.5, 0.64, 0.05, 0.02), cream, { position: [s * 0.27, B + 0.5, HW + 0.05], parent: right });
    createPart(`LockerSlot${s}`, boxGeo(0.06, 0.3, 0.02), team, { position: [s * 0.27, B + 0.56, HW + 0.076], parent: right });
    await plate(`RightPlate${s}`, right, s * 0.37, 0.6);
    wedge(`RightWedge${s}`, right, s * 0.74);
  }
  await trim('RightTrim', right, 0);
  baseLight('BaseLightRight', right, 0, 0.3);

  // ---------- back wall: louvred vent ----------
  recess('BackVent', back);
  for (let k = 0; k < 5; k++) createPart(`BackSlat${k}`, await rb(1.04, 0.1, 0.05, 0.02), dark, { position: [0, B + 0.22 + k * 0.14, HW + 0.05], parent: back });
  for (const k of [1, 3]) createPart(`BackStrip${k}`, boxGeo(0.8, 0.025, 0.02), team, { position: [0, B + 0.15 + k * 0.14, HW + 0.045], parent: back });
  for (const s of [-1, 1]) {
    await plate(`BackPlate${s}`, back, s * 0.37, 0.6);
    baseLight(`BaseLightBack${s}`, back, s * 0.45, 0.26);
    wedge(`BackWedge${s}`, back, s * 0.9);
  }
  await trim('BackTrim', back, 0);

  // ---------- roof: workbench ----------
  const AX = -0.56, AZ = -0.38, BX = 0.08, BZ = 0;
  createPart('BenchPad', await rb(1.0, 0.05, 0.62, 0.02), dark, { position: [BX, DECK + 0.02, BZ], parent: root });
  createPart('BenchPadLight', boxGeo(0.22, 0.02, 0.02), team, { position: [BX - 0.2, DECK + 0.025, BZ + 0.31], parent: root });
  createPart('Bench', await rb(0.7, 0.13, 0.36, 0.03), dark, { position: [BX, DECK + 0.105, BZ], parent: root });
  createPart('BenchGlowFrame', await extrudeProfile(oct(0.2, 0.09, 0.02), { depth: 0.012, holes: [oct(0.165, 0.055, 0.01)] }), glow, { position: [BX, DECK + 0.174, BZ], parent: root });
  createPart('BenchGlowPanel', boxGeo(0.32, 0.006, 0.1), team, { position: [BX, DECK + 0.172, BZ], parent: root });
  for (const s of [-1, 1]) {
    createPart(`BenchClamp${s}`, await rb(0.1, 0.17, 0.4, 0.025), gold, { position: [BX + s * 0.27, DECK + 0.13, BZ], parent: root });
    createPart(`BenchPost${s}`, await rb(0.09, 0.12, 0.1, 0.02), gold, { position: [BX + s * 0.27, DECK + 0.25, BZ - s * 0.1], parent: root });
  }

  // ---------- roof: robot arm reaching over the bench ----------
  createPart('ArmPedestal', cylinderGeo(0.26, 0.3, 0.1, 24), dark, { position: [AX, DECK + 0.045, AZ], parent: root });
  createPart('ArmPedestalRing', cylinderGeo(0.2, 0.24, 0.06, 24), gold, { position: [AX, DECK + 0.12, AZ], parent: root });
  createPart('ArmTurret', cylinderGeo(0.1, 0.16, 0.12, 16), dark, { position: [AX, DECK + 0.2, AZ], parent: root });
  for (const th of [-45, 45, 135, 225]) {
    createPart(`ArmPedestalLight${th}`, boxGeo(0.14, 0.04, 0.03), team,
      { position: [AX + Math.sin(th * DEG) * 0.285, DECK + 0.05, AZ + Math.cos(th * DEG) * 0.285], rotation: [0, th, 0], parent: root });
  }
  const arm = createPivot('Arm', [AX, DECK + 0.24, AZ], root);   // local +X points at the bench, joints turn about local Z
  arm.rotation.set(0, -Math.atan2(BZ - AZ, BX - AX), 0);
  const reach = Math.hypot(BX - AX, BZ - AZ);
  const joint = (name, x, y, r) => {
    createPart(`${name}Rim`, cylinderGeo(r, r, 0.32, 20), gold, { position: [x, y, 0], rotation: [90, 0, 0], parent: arm });
    createPart(`${name}Hub`, cylinderGeo(r * 0.72, r * 0.72, 0.35, 20), dark, { position: [x, y, 0], rotation: [90, 0, 0], parent: arm });
    createPart(`${name}Lens`, cylinderGeo(r * 0.45, r * 0.45, 0.37, 16), glow, { position: [x, y, 0], rotation: [90, 0, 0], parent: arm });
  };
  const S = [0, 0.08], E = [-0.16, 0.83], Wp = [reach - 0.02, 0.91];
  const lowLen = Math.hypot(E[0] - S[0], E[1] - S[1]), lowAng = Math.atan2(S[0] - E[0], E[1] - S[1]) / DEG;
  const foreLen = Math.hypot(Wp[0] - E[0], Wp[1] - E[1]), foreAng = Math.atan2(Wp[1] - E[1], Wp[0] - E[0]) / DEG;
  joint('ArmShoulder', S[0], S[1], 0.17);
  createPart('ArmLower', await rb(0.26, lowLen - 0.14, 0.22, 0.05), cream, { position: [(S[0] + E[0]) / 2, (S[1] + E[1]) / 2, 0], rotation: [0, 0, lowAng], parent: arm });
  createPart('ArmLowerCore', await rb(0.14, lowLen, 0.26, 0.03), dark, { position: [(S[0] + E[0]) / 2, (S[1] + E[1]) / 2, 0], rotation: [0, 0, lowAng], parent: arm });
  joint('ArmElbow', E[0], E[1], 0.18);
  createPart('ArmFore', await rb(foreLen - 0.22, 0.25, 0.22, 0.05), cream, { position: [(E[0] + Wp[0]) / 2, (E[1] + Wp[1]) / 2, 0], rotation: [0, 0, foreAng], parent: arm });
  createPart('ArmForeCore', await rb(foreLen - 0.1, 0.13, 0.26, 0.03), dark, { position: [(E[0] + Wp[0]) / 2, (E[1] + Wp[1]) / 2, 0], rotation: [0, 0, foreAng], parent: arm });
  createPart('ArmWristCap', await rb(0.24, 0.3, 0.28, 0.05), gold, { position: [Wp[0] - 0.02, Wp[1], 0], rotation: [0, 0, foreAng - 22], parent: arm });
  createPart('ArmWrist', cylinderGeo(0.085, 0.085, 0.2, 16), dark, { position: [reach, Wp[1] - 0.1, 0], rotation: [90, 0, 0], parent: arm });
  createPart('ArmWristLink', await rb(0.16, 0.1, 0.15, 0.03), cream, { position: [reach, Wp[1] - 0.2, 0], parent: arm });
  createPart('ClawHub', await rb(0.12, 0.08, 0.12, 0.02), dark, { position: [reach, Wp[1] - 0.27, 0], parent: arm });
  createPart('ClawHubLight', boxGeo(0.06, 0.03, 0.126), glow, { position: [reach, Wp[1] - 0.27, 0], parent: arm });
  // the claw and the rifle it holds hang square to the bench
  const clawY = DECK + 0.24 + Wp[1] - 0.44, ro = 0.15, ri = 0.085, jaw = [-67.5, -22.5, 22.5, 67.5, 112.5, 157.5, 202.5, 247.5];
  const clawProfile = jaw.map((a) => [ro * Math.cos(a * DEG), ro * Math.sin(a * DEG)]).concat(jaw.slice().reverse().map((a) => [ri * Math.cos(a * DEG), ri * Math.sin(a * DEG)]));
  createPart('Claw', await extrudeProfile(clawProfile, { depth: 0.08, axis: 'z' }), gold, { position: [BX, clawY, BZ], parent: root });
  rifle('HeldRifle', root, [BX + 0.02, clawY - 0.235, BZ], 0.95);

  // ---------- roof: console box and antennas ----------
  const con = createPivot('Console', [0.64, DECK, 0.38], root);
  createPart('ConsoleBody', await rb(0.32, 0.32, 0.32, 0.05), cream, { position: [0, 0.155, 0], parent: con });
  createPart('ConsoleBezel', await rb(0.04, 0.16, 0.22, 0.015), dark, { position: [-0.15, 0.2, 0], rotation: [0, 0, -18], parent: con });
  createPart('ConsoleScreen', boxGeo(0.02, 0.1, 0.16), glow, { position: [-0.163, 0.204, 0], rotation: [0, 0, -18], parent: con });
  createPart('ConsoleArmour', await rb(0.22, 0.28, 0.06, 0.025), gold, { position: [0.04, 0.15, 0.15], parent: con });
  createPart('ConsoleVent', boxGeo(0.11, 0.15, 0.02), dark, { position: [0.04, 0.15, 0.176], parent: con });
  for (let k = -1; k <= 1; k++) createPart(`ConsoleVentSlat${k}`, boxGeo(0.085, 0.016, 0.02), gold, { position: [0.04, 0.15 + k * 0.04, 0.182], parent: con });
  const antenna = (name, x, rodH, tipH, tipMat, collar) => {
    createPart(`${name}Base`, cylinderGeo(0.035, 0.045, 0.04, 12), dark, { position: [x, 0.33, -0.03], parent: con });
    createPart(`${name}Rod`, cylinderGeo(0.018, 0.022, rodH, 8), dark, { position: [x, 0.35 + rodH / 2, -0.03], parent: con });
    if (collar) createPart(`${name}Collar`, cylinderGeo(0.036, 0.036, 0.04, 12), gold, { position: [x, 0.37 + rodH, -0.03], parent: con });
    createPart(`${name}Tip`, cylinderGeo(0.03, 0.03, tipH, 12), tipMat, { position: [x, 0.35 + rodH + (collar ? 0.04 : 0) + tipH / 2, -0.03], parent: con });
  };
  antenna('AntennaShort', -0.07, 0.16, 0.13, cream, false);
  antenna('AntennaTall', 0.08, 0.24, 0.24, glow, true);
  return root;
}
