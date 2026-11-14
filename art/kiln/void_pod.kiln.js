// Shardfall: Void Brood Pod (supply), from art/void_buildings/concepts/shardfall_void_pod.png
// Front faces +Z. 2 x 2 m footprint. Four glowing egg sacs under pointed chitin hoods, cupped
// in a base of purple chitin buttresses, with bone spikes rising at the corners.
const meta = { name: 'Void Brood Pod', role: 'building' };

const RAD = Math.PI / 180;

function orient(parent, name, pos, theta, elev) {
  const g = createPivot(name, pos, parent);
  g.rotation.set(0, -theta * RAD, -(90 - elev) * RAD);
  return g;
}

function claw(name, ctrl, r0, mat, parent) {
  const path = catmullRomPath(ctrl, 3);
  const radii = path.map((_, i) => Math.max(0.01, r0 * (1 - i / (path.length - 1)) ** 0.9));
  return createPart(name, taperedTube(path, radii, { radialSegments: 6 }), mat, { parent });
}

async function dome(R, h, seg) {
  const prof = [[0, 0], [R, 0], [R * 0.98, h * 0.28], [R * 0.86, h * 0.6], [R * 0.62, h * 0.85], [R * 0.3, h * 0.97], [0, h]];
  return revolveProfile(prof, { segments: seg, smooth: true });
}

async function build() {
  const root = createRoot('VoidBroodPod');
  const chitin = gameMaterial(0x6b2f93, { roughness: 0.32, metalness: 0.1, name: 'chitin', flatShading: false });
  const chitinDark = gameMaterial(0x40195c, { roughness: 0.4, metalness: 0.05, name: 'chitin_dark', flatShading: false });
  const flesh = gameMaterial(0x7c1f37, { roughness: 0.45, name: 'flesh', flatShading: false });
  const bone = gameMaterial(0xdcc9a6, { roughness: 0.5, name: 'bone', flatShading: false });
  const acid = gameMaterial(0x8cff3a, { emissive: 0x8cff3a, emissiveIntensity: 1.5, roughness: 0.2, name: 'glow_acid', flatShading: false });
  const team = gameMaterial(0x8cff3a, { emissive: 0x8cff3a, emissiveIntensity: 1.0, roughness: 0.3, name: 'team', flatShading: false });

  // base: a low chitin dome with four buttress feet and lit gaps between them
  createPart('Base', await dome(0.86, 0.5, 18), chitinDark, { parent: root });
  for (const th of [45, 135, 225, 315]) {
    const g = orient(root, `Foot${th}`, [Math.cos(th * RAD) * 0.62, 0.2, Math.sin(th * RAD) * 0.62], th, 30);
    createPart(`FootShell${th}`, sphereGeo(0.42, 11, 7), chitin, { scale: [0.75, 0.42, 0.62], parent: g });
  }
  for (const th of [0, 90, 180, 270]) {
    createPart(`BaseGlow${th}`, sphereGeo(0.13, 10, 7), acid, { position: [Math.cos(th * RAD) * 0.8, 0.12, Math.sin(th * RAD) * 0.8], scale: [1, 0.7, 1], parent: root });
    createPart(`Nodule${th}`, sphereGeo(0.07, 8, 6), team, { position: [Math.cos((th + 45) * RAD) * 0.92, 0.3, Math.sin((th + 45) * RAD) * 0.92], parent: root });
  }
  createPart('Flesh', sphereGeo(0.55, 14, 9), flesh, { position: [0, 0.75, -0.05], scale: [1.1, 0.8, 1], parent: root });

  // eggs, each under a pointed chitin hood
  const eggs = [[0, 0.9, 0.36, 0.44, 0], [-0.45, 1.0, -0.06, 0.37, -18], [0.45, 1.0, -0.06, 0.37, 18], [0, 1.4, -0.32, 0.38, 0]];
  eggs.forEach(([x, y, z, r, lean], i) => {
    createPart(`Egg${i}`, sphereGeo(r, 14, 10), acid, { position: [x, y, z], scale: [1, 1.12, 1], parent: root });
    const h = createPivot(`Hood${i}`, [x, y + r * 0.85, z - 0.03], root);
    h.rotation.set(-12 * RAD, 0, lean * RAD);
    createPart(`HoodShell${i}`, sphereGeo(r * 1.05, 12, 8), chitin, { scale: [1, 0.5, 1], parent: h });
    createPart(`HoodTip${i}`, coneGeo(r * 0.45, r * 0.8, 8), chitin, { position: [0, r * 0.35, -r * 0.2], rotation: [-30, 0, 0], parent: h });
  });

  // bone spikes rising at the corners
  for (const [sx, sz] of [[-1, 1], [1, 1], [-1, -1], [1, -1]]) {
    claw(`Spike${sx}${sz}`, [[sx * 0.62, 0.3, sz * 0.55], [sx * 0.8, 0.75, sz * 0.62], [sx * 0.82, 1.2, sz * 0.6], [sx * 0.7, 1.55, sz * 0.45]], 0.11, bone, root);
  }
  return root;
}
