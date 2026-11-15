// Shardfall: Ambron Aero Lab (flyer upgrade building), from art/ambron_buildings/concepts/shardfall_ambron_aerolab.png
// Front faces +Z. 2.8 x 2.8 m footprint, about 3 m tall. A stepped octagonal graphite base, a cream
// eight-sided dome with gold ribs on its corners, a big gold-rimmed turbine intake on the front-right
// face and a small gold-framed door with a window strip on the front-left face. On the roof: a round
// landing pad, a tilted radar dish and an antenna on the left, and a jointed clamp arm at the back
// right that holds a small delta-wing drone over the pad: the node "float_drone".
const meta = { name: 'Ambron Aero Lab', role: 'building' };

const CREAM = 0xe8dcc3, GOLD = 0xe2a531, DARK = 0x2c2e35, CYAN = 0x5fe3ff;
const RAD = Math.PI / 180;
const C8 = Math.cos(22.5 * RAD);       // apothem of an octagon of circumradius 1
const B1 = 0.21, B2 = 0.34;            // tops of the two base tiers
const WR = 1.2, WA = WR * C8, W1 = 1.2;   // wall circumradius, apothem and top
const S1 = [1.02, 1.55], S2 = [0.66, 1.78], CAP = 1.8;   // dome shoulder breaks (circumradius, y) and cap
const POD = 0.98;                      // turbine axis height
const PX = 0.28, PZ = -0.1, PY = 2.05, PR = 0.5;   // landing pad centre, deck height, deck radius
const DX = -0.72, DZ = 0.12;           // dish plinth centre
const FLY = 2.32;                      // drone hover height

function at(theta, r, y) {
  return [Math.cos(theta * RAD) * r, y, Math.sin(theta * RAD) * r];
}
// Outline of a band laid on a polyline that climbs with the body on its left:
// `out` proud of the surface, `inn` sunk into it.
function bandOutline(path, out, inn) {
  const n = path.length, nor = [];
  for (let i = 0; i < n - 1; i++) {
    const dx = path[i + 1][0] - path[i][0], dy = path[i + 1][1] - path[i][1], l = Math.hypot(dx, dy);
    nor.push([dy / l, -dx / l]);
  }
  const side = (d) => path.map((p, i) => {
    const a = nor[Math.max(0, i - 1)], b = nor[Math.min(n - 2, i)];
    const bx = a[0] + b[0], by = a[1] + b[1];
    const k = d / (bx * a[0] + by * a[1]);
    return [p[0] + bx * k, p[1] + by * k];
  });
  const o = side(out), i = side(-inn);
  return [i[0], ...o, ...i.slice(1).reverse()];
}

async function build() {
  const root = createRoot('AmbronAeroLab');
  const cream = gameMaterial(CREAM, { roughness: 0.55, name: 'cream', flatShading: false });
  const gold = gameMaterial(GOLD, { roughness: 0.35, metalness: 0.55, name: 'gold', flatShading: false });
  const dark = gameMaterial(DARK, { roughness: 0.6, metalness: 0.2, name: 'graphite', flatShading: false });
  const glow = gameMaterial(CYAN, { emissive: CYAN, emissiveIntensity: 2.2, roughness: 0.3, name: 'glow_cyan', flatShading: false });
  const team = gameMaterial(CYAN, { emissive: CYAN, emissiveIntensity: 1.2, roughness: 0.4, name: 'team', flatShading: false });
  const rb = (w, h, d, r) => roundedBoxGeo(w, h, d, r, { style: 'chamfer' });
  const oct = { segments: 8, smooth: false };
  // a frame whose +X points out of the face at angle th, +Z to the left of someone facing it
  const facet = (name, th) => {
    const g = createPivot(name, [0, 0, 0], root);
    g.rotation.set(0, -th * RAD, 0);
    return g;
  };
  const TILT = Math.atan2(WA - S1[0] * C8, S1[1] - W1);
  const shoulder = (name, g, z) => {
    const s = createPivot(name, [(WA + S1[0] * C8) / 2, (W1 + S1[1]) / 2, z], g);
    s.rotation.set(0, 0, TILT);
    return s;
  };

  // stepped octagonal base with a team light on every face
  createPart('Plinth', await revolveProfile([[0, 0], [1.47, 0], [1.47, 0.13], [1.4, B1], [0, B1]], oct), dark, { rotation: [0, 22.5, 0], parent: root });
  createPart('Step', await revolveProfile([[0, B1 - 0.02], [1.34, B1 - 0.02], [1.34, 0.3], [1.29, B2], [0, B2]], oct), dark, { rotation: [0, 22.5, 0], parent: root });
  for (let k = 0; k < 8; k++) {
    const th = k * 45, g = facet(`Base${th}`, th);
    if (th === 135) {
      for (const s of [-1, 1]) createPart(`BaseLight${th}${s}`, boxGeo(0.03, 0.07, 0.14), team, { position: [1.47 * C8 + 0.004, 0.075, 0.06 + s * 0.39], parent: g });
    } else {
      createPart(`BaseLight${th}`, boxGeo(0.03, 0.07, 0.42), team, { position: [1.47 * C8 + 0.004, 0.075, 0], parent: g });
    }
  }

  // the lab body: an eight-sided dome, gold ribs on its corners, cream buttresses at their feet
  createPart('Dome', await revolveProfile([[0, B2 - 0.03], [WR, B2 - 0.03], [WR, W1], S1, S2, [0, CAP]], oct), cream, { rotation: [0, 22.5, 0], parent: root });
  const ribGeo = await extrudeProfile(bandOutline([[WR, 0.84], [WR, W1], S1, [0.72, 1.742]], 0.06, 0.08), { depth: 0.2, axis: 'z', bevel: 0.015, bevelStyle: 'chamfer' });
  const buttGeo = await extrudeProfile([[1.1, B2 - 0.02], [1.33, B2 - 0.02], [1.33, 0.48], [1.25, 0.86], [1.1, 0.9]], { depth: 0.3, axis: 'z', bevel: 0.03, bevelStyle: 'chamfer' });
  for (const th of [22.5, 112.5, 157.5, 202.5, 247.5, 292.5, 337.5]) {
    const g = facet(`Corner${th}`, th);
    createPart(`Rib${th}`, ribGeo, gold, { parent: g });
    if (th > 113) createPart(`Buttress${th}`, buttGeo, cream, { parent: g });
  }
  // plain faces: a lit slit, a raised shoulder plate, and a foot block beside the turbine
  for (const [th, z] of [[90, 0.1], [0, -0.1], [180, 0], [225, 0], [270, 0], [315, 0]]) {
    const g = facet(`Face${th}`, th);
    createPart(`SlitFrame${th}`, await rb(0.06, 0.5, 0.22, 0.025), cream, { position: [WA + 0.01, 0.92, z], parent: g });
    createPart(`SlitInset${th}`, boxGeo(0.02, 0.38, 0.12), dark, { position: [WA + 0.045, 0.92, z], parent: g });
    createPart(`SlitLight${th}`, boxGeo(0.02, 0.3, 0.055), glow, { position: [WA + 0.055, 0.92, z], parent: g });
    const s = shoulder(`Shoulder${th}`, g, z);
    createPart(`ShoulderPlate${th}`, await rb(0.05, 0.26, z ? 0.42 : 0.52, 0.02), cream, { position: [0.012, 0, 0], parent: s });
    if (z) createPart(`FootBlock${th}`, await rb(0.24, 0.42, 0.3, 0.07), cream, { position: [WA + 0.07, B2 + 0.19, -2 * z], rotation: [0, 0, 10], parent: g });
  }

  // front-left face: the door, its step, a vent and the window strip
  const df = facet('DoorFace', 135);
  const dz = 0.06;
  createPart('DoorSurround', await extrudeProfile([[-0.26, 0], [0.26, 0], [0.26, 0.6], [0.15, 0.76], [-0.15, 0.76], [-0.26, 0.6]], { depth: 0.07, axis: 'x', bevel: 0.02, bevelStyle: 'chamfer' }), cream,
    { position: [WA + 0.015, B2, dz], parent: df });
  createPart('DoorFrame', await extrudeProfile([[0.2, 0.06], [0.2, 0.52], [0.11, 0.66], [-0.11, 0.66], [-0.2, 0.52], [-0.2, 0.06], [-0.13, 0.06], [-0.13, 0.49], [-0.065, 0.59], [0.065, 0.59], [0.13, 0.49], [0.13, 0.06]], { depth: 0.07, axis: 'x' }), gold,
    { position: [WA + 0.055, B2, dz], parent: df });
  createPart('DoorLeaf', boxGeo(0.04, 0.56, 0.3), dark, { position: [WA + 0.045, B2 + 0.33, dz], parent: df });
  createPart('DoorLine', boxGeo(0.02, 0.4, 0.035), glow, { position: [WA + 0.065, B2 + 0.3, dz], parent: df });
  createPart('DoorLight', boxGeo(0.02, 0.045, 0.14), glow, { position: [WA + 0.052, B2 + 0.705, dz], parent: df });
  createPart('Stair', await extrudeProfile([[1.08, 0.1], [1.37, 0.1], [1.37, B1 + 0.02], [1.22, 0.42], [1.08, 0.42]], { depth: 0.3, axis: 'z' }), dark, { position: [0, 0, dz], parent: df });
  const cheekGeo = await extrudeProfile([[1.08, 0.1], [1.39, 0.1], [1.39, B1 + 0.09], [1.25, 0.5], [1.08, 0.5]], { depth: 0.07, axis: 'z', bevel: 0.015, bevelStyle: 'chamfer' });
  for (const s of [-1, 1]) createPart(`StairCheek${s}`, cheekGeo, gold, { position: [0, 0, dz + s * 0.185], parent: df });
  for (const t of [0.2, 0.5, 0.8]) {
    createPart(`StairLight${t}`, boxGeo(0.05, 0.02, 0.22), glow, { position: [1.226 + 0.15 * t, 0.425 - 0.19 * t, dz], rotation: [0, 0, -51.7], parent: df });
  }
  createPart('VentPlate', await rb(0.06, 0.4, 0.2, 0.025), cream, { position: [WA + 0.01, B2 + 0.36, -0.33], parent: df });
  createPart('VentInset', boxGeo(0.02, 0.26, 0.12), dark, { position: [WA + 0.045, B2 + 0.36, -0.33], parent: df });
  for (const k of [-1, 0, 1]) createPart(`VentSlat${k}`, boxGeo(0.02, 0.025, 0.12), cream, { position: [WA + 0.055, B2 + 0.36 + k * 0.07, -0.33], parent: df });
  const ws = shoulder('Windows', df, 0);
  createPart('WindowFrame', await rb(0.08, 0.3, 0.64, 0.035), cream, { position: [0.01, 0, 0], parent: ws });
  createPart('WindowInset', boxGeo(0.02, 0.2, 0.54), dark, { position: [0.05, 0, 0], parent: ws });
  for (const k of [-1, 0, 1]) createPart(`WindowPane${k}`, boxGeo(0.02, 0.15, 0.15), glow, { position: [0.06, 0, k * 0.175], parent: ws });

  // front-right face: the turbine intake. Revolved parts run out along the pod axis.
  const pod = facet('Turbine', 45);
  const along = () => ({ position: [0, POD, 0], rotation: [0, 0, -90], parent: pod });
  createPart('PodHousing', await revolveProfile([[0.42, 0.72], [0.6, 0.72], [0.6, 1.21], [0.56, 1.28], [0.42, 1.28]], { segments: 16, smooth: false }), cream, along());
  createPart('PodLiner', await revolveProfile([[0.395, 1.06], [0.44, 1.06], [0.44, 1.27], [0.395, 1.27]], { segments: 24, smooth: true }), dark, along());
  createPart('PodRim', await revolveProfile([[0.4, 1.24], [0.53, 1.24], [0.545, 1.29], [0.52, 1.345], [0.45, 1.365], [0.4, 1.33]], { segments: 24, smooth: true }), gold, along());
  createPart('FanBack', cylinderGeo(0.42, 0.42, 0.04, 24), dark, { position: [1.08, POD, 0], rotation: [0, 0, -90], parent: pod });
  const bladeGeo = await extrudeProfile([[-0.035, 0.13], [0.035, 0.13], [0.1, 0.395], [-0.1, 0.395]], { depth: 0.014, axis: 'x' });
  for (let k = 0; k < 10; k++) {
    const b = createPivot(`Blade${k}`, [1.15, POD, 0], pod);
    b.rotation.set(k * 36 * RAD, 0, 0);
    createPart(`BladeFin${k}`, bladeGeo, glow, { rotation: [0, 24, 0], parent: b });
  }
  createPart('Hub', cylinderGeo(0.07, 0.19, 0.24, 14), dark, { position: [1.22, POD, 0], rotation: [0, 0, -90], parent: pod });
  createPart('HubRing', torusGeo(0.075, 0.02, 6, 18), glow, { position: [1.345, POD, 0], rotation: [0, 90, 0], parent: pod });
  createPart('HubTip', sphereGeo(0.06, 10, 6), dark, { position: [1.345, POD, 0], parent: pod });
  for (const s of [-1, 1]) createPart(`PodTab${s}`, await rb(0.2, 0.16, 0.09, 0.03), gold, { position: [1.15, POD, s * 0.6], parent: pod });
  createPart('PodPlinth', await rb(0.32, 0.3, 0.86, 0.05), cream, { position: [1.14, 0.35, 0], parent: pod });
  createPart('PodStrap', await extrudeProfile(bandOutline([[1.21, 1.585], [0.93, 1.6], [0.62, 1.775]], 0.07, 0.05), { depth: 0.26, axis: 'z', bevel: 0.015, bevelStyle: 'chamfer' }), gold, { parent: pod });
  createPart('PodStrapLight', boxGeo(0.15, 0.02, 0.07), glow, { position: [1.07, 1.668, 0], rotation: [0, 0, -3], parent: pod });

  // landing pad on the roof, centre right
  const pad = createPivot('Pad', [PX, 0, PZ], root);
  createPart('PadCollar', cylinderGeo(0.61, 0.66, 0.38, 16), cream, { position: [0, 1.65, 0], parent: pad });
  createPart('PadBand', cylinderGeo(0.6, 0.6, 0.14, 24), dark, { position: [0, 1.89, 0], parent: pad });
  createPart('PadRim', await revolveProfile([[PR - 0.02, -0.11], [PR + 0.14, -0.11], [PR + 0.18, -0.04], [PR + 0.18, 0.02], [PR + 0.13, 0.06], [PR - 0.02, 0.06]], { segments: 16, smooth: false }), cream,
    { position: [0, PY, 0], parent: pad });
  createPart('PadDeck', cylinderGeo(PR, PR, 0.08, 32), dark, { position: [0, PY - 0.04, 0], parent: pad });
  createPart('DeckRing', torusGeo(0.3, 0.03, 6, 40), glow, { position: [0, PY + 0.004, 0], rotation: [90, 0, 0], scale: [1, 1, 0.35], parent: pad });
  for (const th of [45, 135, 225, 315]) {
    createPart(`DeckGap${th}`, boxGeo(0.1, 0.03, 0.1), dark, { position: at(th, 0.3, PY + 0.006), rotation: [0, -th, 0], parent: pad });
  }
  for (const th of [0, 90, 180, 270]) {
    createPart(`BandLight${th}`, boxGeo(0.03, 0.06, 0.22), team, { position: at(th, 0.6, 1.89), rotation: [0, -th, 0], parent: pad });
  }
  for (const th of [45, 135]) {
    createPart(`PadClamp${th}`, await rb(0.22, 0.3, 0.26, 0.05), gold, { position: at(th, PR + 0.14, PY - 0.04), rotation: [0, -th, 0], parent: pad });
  }
  createPart('PadPost', await rb(0.2, 0.4, 0.24, 0.05), gold, { position: at(225, PR + 0.13, PY + 0.02), rotation: [0, -225, 0], parent: pad });
  createPart('PadPostLight', boxGeo(0.02, 0.1, 0.1), glow, { position: at(225, PR + 0.025, PY + 0.15), rotation: [0, -225, 0], parent: pad });

  // clamp arm at the back right of the pad: base, lower arm, elbow, forearm, head and an open claw
  const arm = createPivot('Arm', [0, 0, 0], pad);
  arm.rotation.set(0, 42 * RAD, 0);
  createPart('ArmBase', await rb(0.26, 0.34, 0.26, 0.05), gold, { position: [PR + 0.12, PY + 0.03, 0], parent: arm });
  createPart('ArmBaseLight', boxGeo(0.12, 0.12, 0.02), glow, { position: [PR + 0.12, PY + 0.1, 0.132], parent: arm });
  createPart('ArmLower', await rb(0.17, 0.46, 0.17, 0.05), cream, { position: [PR + 0.13, PY + 0.4, 0], rotation: [0, 0, -4], parent: arm });
  createPart('ArmLowerBand', await rb(0.2, 0.07, 0.2, 0.03), gold, { position: [PR + 0.125, PY + 0.25, 0], rotation: [0, 0, -4], parent: arm });
  const EX = PR + 0.15, EY = PY + 0.63;
  createPart('Elbow', cylinderGeo(0.115, 0.115, 0.22, 14), gold, { position: [EX, EY, 0], rotation: [90, 0, 0], parent: arm });
  createPart('ElbowRing', cylinderGeo(0.08, 0.08, 0.03, 14), dark, { position: [EX, EY, 0.11], rotation: [90, 0, 0], parent: arm });
  createPart('ElbowLens', cylinderGeo(0.05, 0.05, 0.03, 12), glow, { position: [EX, EY, 0.118], rotation: [90, 0, 0], parent: arm });
  createPart('Forearm', await rb(0.4, 0.15, 0.15, 0.045), cream, { position: [0.475, EY + 0.105, 0], rotation: [0, 0, -31], parent: arm });
  createPart('Wrist', cylinderGeo(0.085, 0.085, 0.19, 12), dark, { position: [0.3, EY + 0.21, 0], rotation: [90, 0, 0], parent: arm });
  createPart('ArmHead', await rb(0.36, 0.17, 0.22, 0.05), cream, { position: [0.1, EY + 0.21, 0], parent: arm });
  createPart('ArmHeadCap', await rb(0.16, 0.05, 0.16, 0.02), gold, { position: [0.08, EY + 0.31, 0], parent: arm });
  createPart('ClawNeck', cylinderGeo(0.06, 0.07, 0.1, 10), dark, { position: [0, 2.76, 0], parent: pad });
  createPart('ClawHub', await rb(0.24, 0.08, 0.15, 0.03), dark, { position: [0, 2.69, 0], parent: pad });
  createPart('ClawLight', boxGeo(0.1, 0.035, 0.02), glow, { position: [0, 2.69, 0.076], parent: pad });
  for (const s of [-1, 1]) {
    createPart(`ClawUpper${s}`, await rb(0.17, 0.055, 0.08, 0.02), dark, { position: [s * 0.155, 2.64, 0], rotation: [0, 0, -s * 24.8], parent: pad });
    createPart(`ClawLower${s}`, await rb(0.12, 0.05, 0.08, 0.02), dark, { position: [s * 0.195, 2.57, 0], rotation: [0, 0, s * 58], parent: pad });
    createPart(`ClawFingerLight${s}`, boxGeo(0.06, 0.025, 0.02), glow, { position: [s * 0.195, 2.57, 0.042], rotation: [0, 0, s * 58], parent: pad });
  }

  // the drone the game bobs and turns: nose along its own +Z
  const fl = createPivot('float_drone', [PX, FLY, PZ], root);
  fl.name = 'float_drone';
  fl.rotation.set(0, -20 * RAD, 0);
  createPart('DroneWing', await extrudeProfile([[0, -0.16], [0.11, -0.04], [0.4, 0.12], [0.4, 0.19], [0.12, 0.15], [-0.12, 0.15], [-0.4, 0.19], [-0.4, 0.12], [-0.11, -0.04]], { depth: 0.035, axis: 'y', bevel: 0.01, bevelStyle: 'chamfer' }), cream, { parent: fl });
  createPart('DroneBody', await rb(0.15, 0.11, 0.44, 0.045), cream, { position: [0, 0.01, 0.02], parent: fl });
  createPart('DroneNose', cylinderGeo(0.02, 0.07, 0.14, 8), cream, { position: [0, 0, 0.3], rotation: [90, 0, 0], parent: fl });
  createPart('DroneCanopy', await rb(0.1, 0.04, 0.13, 0.015), glow, { position: [0, 0.055, 0.14], parent: fl });
  createPart('DroneTail', await rb(0.06, 0.07, 0.14, 0.02), gold, { position: [0, 0.04, -0.14], parent: fl });
  createPart('DroneEngine', boxGeo(0.09, 0.05, 0.02), glow, { position: [0, 0.01, -0.205], parent: fl });
  for (const s of [-1, 1]) {
    createPart(`DroneEdge${s}`, boxGeo(0.33, 0.045, 0.05), gold, { position: [s * 0.255, 0, -0.03], rotation: [0, s * 28.9, 0], parent: fl });
    createPart(`DroneTip${s}`, await rb(0.05, 0.06, 0.12, 0.02), gold, { position: [s * 0.4, 0, -0.155], parent: fl });
    createPart(`DroneStrip${s}`, boxGeo(0.16, 0.012, 0.035), glow, { position: [s * 0.25, 0.02, -0.12], rotation: [0, s * 8, 0], parent: fl });
  }

  // radar dish on its plinth, upper left, and the antenna on the left corner
  const dp = createPivot('DishPlinth', [DX, 0, DZ], root);
  createPart('PlinthFoot', cylinderGeo(0.31, 0.36, 0.6, 8), cream, { position: [0, 1.6, 0], rotation: [0, 22.5, 0], parent: dp });
  createPart('PlinthBand', cylinderGeo(0.285, 0.285, 0.1, 8), dark, { position: [0, 1.94, 0], rotation: [0, 22.5, 0], parent: dp });
  createPart('PlinthTop', cylinderGeo(0.27, 0.32, 0.08, 8), cream, { position: [0, 2.02, 0], rotation: [0, 22.5, 0], parent: dp });
  for (const th of [45, 90, 135]) {
    createPart(`PlinthLight${th}`, boxGeo(0.02, 0.05, 0.13), glow, { position: at(th, 0.285 * C8 + 0.003, 1.94), rotation: [0, -th, 0], parent: dp });
  }
  createPart('DishPedestal', cylinderGeo(0.09, 0.14, 0.1, 10), dark, { position: [0, 2.11, 0], parent: dp });
  createPart('DishMast', cylinderGeo(0.05, 0.06, 0.2, 8), dark, { position: [-0.02, 2.25, -0.04], parent: dp });
  createPart('DishJoint', sphereGeo(0.09, 10, 8), dark, { position: [-0.02, 2.36, -0.05], parent: dp });
  const yaw = createPivot('DishYaw', [-0.02, 2.36, -0.05], dp);
  yaw.rotation.set(0, 28.7 * RAD, 0);
  const dish = createPivot('DishTilt', [0, 0, 0], yaw);
  dish.rotation.set(56.6 * RAD, 0, 0);
  dish.scale.set(1.2, 1.2, 1.2);
  const dh = { segments: 20, smooth: true };
  createPart('DishBowl', await revolveProfile([[0, 0], [0.16, 0.02], [0.27, 0.075], [0.33, 0.15], [0.3, 0.15], [0.24, 0.1], [0.13, 0.05], [0, 0.035]], dh), cream, { position: [0, 0.06, 0], parent: dish });
  createPart('DishRim', await revolveProfile([[0.29, 0.125], [0.345, 0.125], [0.36, 0.16], [0.34, 0.19], [0.3, 0.175]], dh), gold, { position: [0, 0.06, 0], parent: dish });
  createPart('DishFeedBase', cylinderGeo(0.06, 0.075, 0.05, 10), dark, { position: [0, 0.12, 0], parent: dish });
  createPart('DishFeedRing', torusGeo(0.115, 0.016, 6, 20), glow, { position: [0, 0.115, 0], rotation: [90, 0, 0], scale: [1, 1, 0.5], parent: dish });
  createPart('DishFeed', cylinderGeo(0.018, 0.04, 0.24, 8), dark, { position: [0, 0.26, 0], parent: dish });
  createPart('DishFeedTip', sphereGeo(0.045, 10, 8), glow, { position: [0, 0.4, 0], parent: dish });
  const an = at(157.5, 1.13, 0);
  createPart('AntennaBase', await rb(0.17, 0.18, 0.17, 0.04), gold, { position: [an[0], 1.36, an[2]], rotation: [0, -157.5, 0], parent: root });
  createPart('AntennaMast', cylinderGeo(0.018, 0.026, 0.72, 6), dark, { position: [an[0], 1.8, an[2]], parent: root });
  createPart('AntennaCollar', cylinderGeo(0.035, 0.035, 0.05, 8), gold, { position: [an[0], 2.17, an[2]], parent: root });
  createPart('AntennaTip', cylinderGeo(0.035, 0.035, 0.17, 8), glow, { position: [an[0], 2.28, an[2]], parent: root });
  return root;
}
