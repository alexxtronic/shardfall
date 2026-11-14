// Shardfall: Void Aerie (air factory), from art/void_buildings/concepts/shardfall_void_aerie.png
// Front faces +Z. 3 x 3 m footprint. A twisting trunk wrapped in chitin plates rises from a mound
// of plates and glowing egg sacs, and holds out three bone-rimmed perches on branches, each
// slung with a pink membrane web.
const meta = { name: 'Void Aerie', role: 'building' };

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
const ring = (theta, r, y) => [Math.cos(theta * RAD) * r, y, Math.sin(theta * RAD) * r];

async function build() {
  const root = createRoot('VoidAerie');
  const chitin = gameMaterial(0x6b2f93, { roughness: 0.32, metalness: 0.1, name: 'chitin', flatShading: false });
  const chitinDark = gameMaterial(0x40195c, { roughness: 0.4, metalness: 0.05, name: 'chitin_dark', flatShading: false });
  const flesh = gameMaterial(0x7c1f37, { roughness: 0.45, name: 'flesh', flatShading: false });
  const membrane = gameMaterial(0xc4466a, { roughness: 0.6, name: 'membrane', flatShading: false });
  const bone = gameMaterial(0xdcc9a6, { roughness: 0.5, name: 'bone', flatShading: false });
  const acid = gameMaterial(0x8cff3a, { emissive: 0x8cff3a, emissiveIntensity: 1.6, roughness: 0.2, name: 'glow_acid', flatShading: false });
  const team = gameMaterial(0x8cff3a, { emissive: 0x8cff3a, emissiveIntensity: 1.0, roughness: 0.3, name: 'team', flatShading: false });

  // base mound of plates with big glowing egg sacs
  createPart('Mound', await dome(1.15, 0.7, 18), chitinDark, { parent: root });
  for (const th of [0, 50, 100, 160, 200, 270, 300]) {
    const g = orient(root, `BasePlate${th}`, ring(th, 0.98, 0.34), th, 32);
    createPart(`BasePlateShell${th}`, sphereGeo(0.62, 10, 7), chitin, { scale: [0.72, 0.28, 0.85], parent: g });
  }
  for (const [th, r] of [[75, 0.32], [130, 0.28], [25, 0.26], [230, 0.28], [335, 0.24]]) {
    createPart(`Egg${th}`, sphereGeo(r, 14, 10), acid, { position: ring(th, 1.12, r * 0.95), scale: [0.9, 1.1, 0.9], parent: root });
  }

  // twisting trunk wrapped in plates
  const trunk = catmullRomPath([[0, 0.3, 0], [0.12, 0.9, 0.05], [-0.1, 1.5, -0.05], [0.05, 2.1, -0.08], [-0.02, 2.55, -0.12]], 4);
  createPart('Trunk', taperedTube(trunk, trunk.map((_, i) => 0.5 - 0.24 * i / (trunk.length - 1)), { radialSegments: 10 }), flesh, { parent: root });
  [[0.8, 60], [1.15, 180], [1.5, 300], [1.85, 60], [2.2, 180]].forEach(([y, th], i) => {
    const g = orient(root, `Wrap${i}`, ring(th, 0.26, y), th, 70);
    createPart(`WrapShell${i}`, sphereGeo(0.62, 10, 7), chitin, { scale: [0.55, 0.3, 0.95], parent: g });
    claw(`WrapSpike${i}`, [[0.1, 0.1, 0], [0.24, 0.16, 0], [0.32, 0.34, 0], [0.28, 0.5, 0]], 0.08, bone, g);
  });

  createPart('TrunkCap', sphereGeo(0.3, 12, 8), chitin, { position: [-0.02, 2.55, -0.12], scale: [1, 0.7, 1], parent: root });

  // three perches on branches: left, right (lower) and top-back
  const perches = [[180, 0.95, 1.8, 0.95], [5, 0.95, 1.55, 0.9], [250, 0.55, 2.65, 1.0]];
  for (const [th, reach, y, sc] of perches) {
    const g = createPivot(`Perch${th}`, [0, 0, 0], root);
    g.rotation.set(0, -th * RAD, 0);
    // the branch out from the trunk
    claw(`Branch${th}`, [[0.05, y - 0.55, 0], [0.3, y - 0.25, 0], [reach * 0.7, y - 0.08, 0], [reach, y, 0]], 0.16, chitin, g);
    const p = createPivot(`PerchHead${th}`, [reach, y, 0], g);
    p.scale.set(sc, sc, sc);
    createPart(`PerchPad${th}`, sphereGeo(0.5, 14, 8), flesh, { position: [0.1, 0.02, 0], scale: [0.7, 0.12, 1.05], parent: p });
    const rim = catmullRomPath([[-0.05, 0.12, -0.6], [0.25, 0.0, -0.42], [0.42, -0.03, 0], [0.25, 0.0, 0.42], [-0.05, 0.12, 0.6]], 4);
    createPart(`PerchRim${th}`, taperedTube(rim, rim.map((_, i) => 0.04 + 0.07 * Math.sin(Math.PI * i / (rim.length - 1))), { radialSegments: 6 }), bone, { parent: p });
    for (const s of [-1, 1]) {
      claw(`PerchHook${th}${s}`, [[-0.05, 0.1, s * 0.58], [-0.12, 0.3, s * 0.66], [-0.02, 0.5, s * 0.62], [0.12, 0.55, s * 0.5]], 0.07, bone, p);
    }
    for (const z of [-0.2, 0.2]) {
      claw(`PerchSpur${th}${z}`, [[0.32, 0.02, z], [0.4, 0.12, z], [0.38, 0.22, z]], 0.035, bone, p);
    }
    // membrane web from the perch's underside back to the trunk
    createPart(`Web${th}`, sphereGeo(0.5, 10, 6), membrane, { position: [reach * 0.55, y - 0.35, 0], rotation: [0, 0, -35], scale: [0.75 * reach, 0.5, 0.04], parent: g });
  }
  for (const [x, y, z] of [[0.3, 1.0, 0.3], [-0.3, 1.6, 0.25], [0.95, 0.35, -0.3], [-0.95, 0.35, -0.3]]) {
    createPart(`Nodule${x}${y}`, sphereGeo(0.08, 8, 6), team, { position: [x, y, z], parent: root });
  }
  return root;
}
