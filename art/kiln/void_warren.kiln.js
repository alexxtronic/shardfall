// Shardfall: Void Beast Warren (vehicle factory), from art/void_buildings/concepts/shardfall_void_warren.png
// Front faces +Z. 3 x 3 m footprint. A long low burrow mound of layered chitin plates over crimson
// flesh, a row of bone spines along its back growing toward the front, two great tusks arching
// over a green-lit tunnel at the front, and glowing eye sacs along the flanks.
const meta = { name: 'Void Beast Warren', role: 'building' };

const RAD = Math.PI / 180;

function orient(parent, name, pos, theta, elev) {
  const g = createPivot(name, pos, parent);
  g.rotation.set(0, -theta * RAD, -(90 - elev) * RAD);
  return g;
}
function claw(name, ctrl, r0, mat, parent) {
  const path = catmullRomPath(ctrl, 3);
  const radii = path.map((_, i) => Math.max(0.012, r0 * (1 - i / (path.length - 1)) ** 0.9));
  return createPart(name, taperedTube(path, radii, { radialSegments: 6 }), mat, { parent });
}
async function dome(R, h, seg) {
  const prof = [[0, 0], [R, 0], [R * 0.98, h * 0.28], [R * 0.86, h * 0.6], [R * 0.62, h * 0.85], [R * 0.3, h * 0.97], [0, h]];
  return revolveProfile(prof, { segments: seg, smooth: true });
}
// a point on the stretched mound (x half 1.2, z half 1.45, centre z -0.1)
const SX = 1.2, SZ = 1.28, MZ = -0.12;
const onMound = (theta, f, y) => [Math.cos(theta * RAD) * SX * f, y, MZ + Math.sin(theta * RAD) * SZ * f];

async function build() {
  const root = createRoot('VoidBeastWarren');
  const chitin = gameMaterial(0x6b2f93, { roughness: 0.32, metalness: 0.1, name: 'chitin', flatShading: false });
  const chitinDark = gameMaterial(0x40195c, { roughness: 0.4, metalness: 0.05, name: 'chitin_dark', flatShading: false });
  const flesh = gameMaterial(0x7c1f37, { roughness: 0.45, name: 'flesh', flatShading: false });
  const throat = gameMaterial(0x3a0814, { roughness: 0.5, name: 'flesh_dark', flatShading: false });
  const bone = gameMaterial(0xdcc9a6, { roughness: 0.5, name: 'bone', flatShading: false });
  const acid = gameMaterial(0x8cff3a, { emissive: 0x8cff3a, emissiveIntensity: 1.6, roughness: 0.2, name: 'glow_acid', flatShading: false });
  const team = gameMaterial(0x8cff3a, { emissive: 0x8cff3a, emissiveIntensity: 1.0, roughness: 0.3, name: 'team', flatShading: false });

  // the long low mound with flesh showing beneath the plates
  createPart('Flesh', await dome(1.0, 1.25, 18), flesh, { position: [0, 0.005, MZ], scale: [SX, 1, SZ], parent: root });
  createPart('Mound', await dome(0.92, 1.55, 18), chitinDark, { position: [0, 0, MZ - 0.05], scale: [SX, 1, SZ], parent: root });

  // two rows of overlapping plates down each flank and across the back
  for (const th of [0, 35, 145, 180, 215, 250, 290, 325]) {
    const g = orient(root, `PlateLow${th}`, onMound(th, 0.92, 0.42), th, 30);
    createPart(`PlateLowShell${th}`, sphereGeo(0.62, 11, 7), chitin, { scale: [0.7, 0.26, 0.9], parent: g });
    // an eye sac peeping out under every other plate
    if (th % 2 === 1 || th === 0 || th === 180) {
      createPart(`Eye${th}`, sphereGeo(0.17, 10, 7), acid, { position: onMound(th, 0.98, 0.24), parent: root });
    }
  }
  for (const th of [15, 60, 120, 165, 230, 270, 310]) {
    const g = orient(root, `PlateHigh${th}`, onMound(th, 0.58, 1.05), th, 50);
    createPart(`PlateHighShell${th}`, sphereGeo(0.6, 11, 7), chitin, { scale: [0.75, 0.26, 0.9], parent: g });
  }

  // tunnel at the front, framed by an arched plate and two great tusks
  const tY = 0.6, tZ = 1.1;
  createPart('Porch', sphereGeo(0.85, 14, 9), chitinDark, { position: [0, 0.6, 0.55], scale: [0.95, 0.85, 0.6], parent: root });
  createPart('Lips', torusGeo(0.5, 0.14, 10, 26), flesh, { position: [0, tY, tZ], scale: [1, 1.05, 1.15], parent: root });
  createPart('Throat', cylinderGeo(0.54, 0.54, 0.3, 22), throat, { position: [0, tY, tZ - 0.18], rotation: [90, 0, 0], parent: root });
  createPart('Glow', cylinderGeo(0.36, 0.36, 0.04, 22), acid, { position: [0, tY - 0.03, tZ - 0.01], rotation: [90, 0, 0], parent: root });
  createPart('GlowCore', sphereGeo(0.22, 12, 8), acid, { position: [0, tY - 0.05, tZ - 0.02], scale: [1, 1, 0.3], parent: root });
  createPart('InnerRing', torusGeo(0.4, 0.06, 8, 24), flesh, { position: [0, tY, tZ], parent: root });
  createPart('Spill', sphereGeo(0.34, 12, 6), acid, { position: [0, 0.0, tZ + 0.12], scale: [1, 0.12, 0.6], parent: root });
  const arch = orient(root, 'ArchPlate', [0, 1.15, 0.8], 90, 30);
  createPart('ArchPlateShell', sphereGeo(0.75, 12, 8), chitin, { scale: [0.6, 0.26, 1.0], parent: arch });
  for (const s of [-1, 1]) {
    createPart(`TuskFoot${s}`, sphereGeo(0.3, 10, 7), chitin, { position: [s * 0.78, 0.1, 1.02], scale: [1, 0.55, 1.1], parent: root });
    claw(`Tusk${s}`, [[s * 0.78, 0.1, 1.02], [s * 0.86, 0.6, 1.17], [s * 0.74, 1.15, 1.12], [s * 0.45, 1.5, 0.92]], 0.18, bone, root);
  }

  // bone spines along the back, growing toward the front, each curving backward
  const spines = [[-1.12, 0.75, 0.15], [-0.75, 1.05, 0.19], [-0.35, 1.3, 0.23], [0.08, 1.45, 0.28], [0.48, 1.35, 0.32]];
  spines.forEach(([z, y, r], i) => {
    const g = createPivot(`Spine${i}`, [0, y, z], root);
    const k = r / 0.3;
    claw(`SpineBone${i}`, [[0, -0.05, 0.08 * k], [0, 0.35 * k, 0.1 * k], [0, 0.7 * k, -0.1 * k], [0, 0.85 * k, -0.45 * k]], r * 0.62, bone, g);
  });

  // claw feet round the base
  for (const th of [10, 50, 130, 170, 215, 255, 290, 325]) {
    const g = createPivot(`Foot${th}`, onMound(th, 1.05, 0.0), root);
    g.rotation.set(0, -th * RAD, 0);
    createPart(`FootPlate${th}`, sphereGeo(0.36, 9, 6), chitin, { position: [0.05, 0.08, 0], scale: [1.1, 0.42, 0.8], parent: g });
    claw(`FootClaw${th}`, [[0.12, 0.1, 0], [0.32, 0.14, 0], [0.42, 0.26, 0], [0.42, 0.42, 0]], 0.09, bone, g);
  }
  for (const [x, y, z] of [[0.75, 0.95, 0.4], [-0.75, 0.95, 0.4], [0.6, 1.0, -0.9], [-0.6, 1.0, -0.9], [0, 1.5, -0.3]]) {
    createPart(`Nodule${x}${z}`, sphereGeo(0.09, 8, 6), team, { position: [x, y, z], parent: root });
  }
  return root;
}
