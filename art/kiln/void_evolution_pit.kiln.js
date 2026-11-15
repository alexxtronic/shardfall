// Shardfall: Void Evolution Pit (upgrades), from art/void_buildings/concepts/shardfall_void_evolution_pit.png
// Front faces +Z. 2.9 x 2.9 m footprint. A low crater mound of crimson flesh with a twisted flesh
// rim, overlapping pointed chitin plates down the flanks, six pitted bone tusks leaning in over a
// glowing acid pool, egg sacs set into the outer rim and root tendrils spreading over the ground.
// A half-formed bone blade drips in the pool: the node "float_blade".
const meta = { name: 'Void Evolution Pit', role: 'building' };

const RAD = Math.PI / 180;
const POOL_Y = 1.0;                         // acid surface
const R_CREST = 0.8, R_FOOT = 1.2;          // rim crest and mound foot radii
const FLANK_LEN = 1.4;                      // crest to foot along the flank, for sizing things in s
const TUSKS = [0, 60, 120, 180, 240, 300];  // theta 90 is the front (+Z)

const rimH = (th) => 1.3 - 0.26 * ((1 + Math.sin(th * RAD)) / 2) ** 2;   // lowest at the front
const polar = (th, r, y) => [Math.cos(th * RAD) * r, y, Math.sin(th * RAD) * r];
const flankR = (s) => { const c = Math.min(s, 1); return R_CREST + 0.24 * Math.sin(c * Math.PI / 2) + 0.16 * c ** 3; };

// a point on the outer flank: s runs 0 (crest) to 1 (foot) and on over the ground; n lifts it off the surface
function flank(th, s, n = 0) {
  const H = rimH(th), c = Math.min(s, 1), ph = c * Math.PI / 2;
  let r = flankR(s), nr = H * Math.sin(ph) * Math.PI / 2, ny = 0.24 * Math.cos(ph) * Math.PI / 2 + 0.48 * c * c;
  if (s > 1) { const k = Math.min(1, (s - 1) / 0.12); r += (s - 1) * 0.5; nr *= 1 - k; ny = ny * (1 - k) + 2 * k; }
  const l = Math.hypot(nr, ny);
  return polar(th, r + nr / l * n, Math.max(0, H * Math.cos(ph) + ny / l * n));
}

// a tube of rings along a path, closing to a point at its end (or blunt, or a closed loop)
function tubeGeo(path, radii, seg, o = {}) {
  const n = path.length, pos = [], idx = [], sx = o.sx || 1, sy = o.sy || 1, tipped = !o.closed && !o.blunt;
  let nrm = o.side || null;
  for (let i = 0; i < n; i++) {
    const a = path[o.closed ? (i + n - 1) % n : Math.max(i - 1, 0)], b = path[o.closed ? (i + 1) % n : Math.min(i + 1, n - 1)];
    let t = [b[0] - a[0], b[1] - a[1], b[2] - a[2]];
    const tl = Math.hypot(t[0], t[1], t[2]);
    t = [t[0] / tl, t[1] / tl, t[2] / tl];
    if (!nrm) nrm = Math.abs(t[1]) > 0.9 ? [1, 0, 0] : [0, 1, 0];
    const d = nrm[0] * t[0] + nrm[1] * t[1] + nrm[2] * t[2];
    nrm = [nrm[0] - d * t[0], nrm[1] - d * t[1], nrm[2] - d * t[2]];
    const nl = Math.hypot(nrm[0], nrm[1], nrm[2]);
    nrm = [nrm[0] / nl, nrm[1] / nl, nrm[2] / nl];
    const bin = [t[1] * nrm[2] - t[2] * nrm[1], t[2] * nrm[0] - t[0] * nrm[2], t[0] * nrm[1] - t[1] * nrm[0]];
    if (tipped && i === n - 1) { pos.push(...path[i]); break; }
    for (let k = 0; k < seg; k++) {
      const an = k / seg * 2 * Math.PI, c = Math.cos(an) * radii[i] * sx, s = Math.sin(an) * radii[i] * sy;
      pos.push(path[i][0] + nrm[0] * c + bin[0] * s, path[i][1] + nrm[1] * c + bin[1] * s, path[i][2] + nrm[2] * c + bin[2] * s);
    }
  }
  const rings = tipped ? n - 1 : n;
  for (let i = 0; i < (o.closed ? rings : rings - 1); i++) {
    const i2 = (i + 1) % rings;
    for (let k = 0; k < seg; k++) {
      const k2 = (k + 1) % seg, a = i * seg + k, b = i * seg + k2, c = i2 * seg + k, e = i2 * seg + k2;
      idx.push(a, b, c, b, e, c);
    }
  }
  if (tipped) for (let k = 0; k < seg; k++) idx.push((rings - 1) * seg + k, (rings - 1) * seg + (k + 1) % seg, rings * seg);
  return meshGeo({ positions: pos, indices: idx });
}

// the crater: inner wall up from the pool, over the crest and down the lumpy outer flank
function moundGeo(seg) {
  const pos = [], idx = [], rings = 9;
  for (let i = 0; i < seg; i++) {
    const th = i / seg * 360, H = rimH(th);
    pos.push(...polar(th, 0.58, POOL_Y - 0.12), ...polar(th, 0.635, POOL_Y + 0.03), ...polar(th, 0.73, H - 0.07));
    for (let j = 0; j <= 5; j++) {
      const lump = j > 0 && j < 5 ? 0.035 * Math.sin(th * RAD * 9 + j * 1.7) : 0;
      pos.push(...flank(th, j / 5, lump));
    }
  }
  for (let i = 0; i < seg; i++) {
    for (let j = 0; j < rings - 1; j++) {
      const a = i * rings + j, b = ((i + 1) % seg) * rings + j;
      idx.push(a, b, a + 1, b, b + 1, a + 1);
    }
  }
  return meshGeo({ positions: pos, indices: idx });
}

// the twisted flesh rim: one ring whose two-lobed section turns as it goes round, so it reads as wound strands
function braidGeo(R, dy, rad, lobe, turns, useg, vseg) {
  const pos = [], idx = [];
  for (let i = 0; i < useg; i++) {
    const th = i / useg * 360, cy = rimH(th) + dy;
    for (let k = 0; k < vseg; k++) {
      const v = k / vseg * 2 * Math.PI, rho = rad * (1 + lobe * Math.cos(2 * (v - turns * th * RAD)));
      pos.push(...polar(th, R + rho * Math.cos(v), cy + rho * Math.sin(v)));
    }
  }
  for (let i = 0; i < useg; i++) {
    const i2 = (i + 1) % useg;
    for (let k = 0; k < vseg; k++) {
      const k2 = (k + 1) % vseg, a = i * vseg + k, b = i2 * vseg + k, c = i * vseg + k2, e = i2 * vseg + k2;
      idx.push(a, c, b, b, c, e);
    }
  }
  return meshGeo({ positions: pos, indices: idx });
}

// a pointed chitin plate lying on the flank: faceted, a raised boss with ridges running out to three tips
function plateGeo(th0, s0, s1, w, tipN, bossV, dn = 0) {
  const half = [[0, -0.03, 0.03], [0.5, 0, 0.03], [0.78, 0.2, 0.05], [1.2, 0.56, tipN * 0.85], [0.6, 0.5, 0.05], [0.36, 0.74, 0.06], [0, 1, tipN]];
  const out = [...half, ...half.slice(1, -1).reverse().map(([u, v, n]) => [-u, v, n])];
  const P = ([u, v, n], d = 0) => {
    const s = s0 + (s1 - s0) * v;
    return flank(th0 + u * w / flankR(s) / RAD, s, n + d + dn);
  };
  const boss = P([0, bossV, 0.15]), under = P([0, bossV, -0.05]), pos = [];
  for (let k = 0; k < out.length; k++) {
    const a = out[k], b = out[(k + 1) % out.length];
    const ta = P(a), tb = P(b), ba = P(a, -0.07), bb = P(b, -0.07);
    pos.push(...boss, ...ta, ...tb, ...ta, ...ba, ...bb, ...ta, ...bb, ...tb, ...under, ...bb, ...ba);
  }
  return meshGeo({ positions: pos });
}

// tusks: a spine in the radial plane [r, y], fattest at the root and hooking in over the pool
function tuskSpine(th) {
  const H = rimH(th), k = (2.63 - 0.07 * Math.sin(th * RAD) - H) / 1.45;
  return catmullRomPath([[0.97, H * 0.78, 0], [1.1, H + 0.22 * k, 0], [1.14, H + 0.62 * k, 0], [1.02, H + k, 0], [0.74, H + 1.3 * k, 0], [0.36, H + 1.45 * k, 0]], 3);
}
const TUSK_FLAT = 0.88;   // tusks are a little thinner through than across
const tuskR = (t) => 0.012 + 0.25 * (1 - t) ** 0.85;
// a point on a tusk's skin: t along it, phi round it (0 faces outward), k scales the radius
function tuskSkin(th, spine, t, phi, k) {
  const f = Math.min(Math.max(t, 0), 0.999) * (spine.length - 1), i = Math.floor(f), u = f - i;
  const a = spine[i], b = spine[i + 1];
  const tl = Math.hypot(b[0] - a[0], b[1] - a[1]), tr = (b[0] - a[0]) / tl, ty = (b[1] - a[1]) / tl;
  const R = tuskR(t) * k, out = Math.cos(phi * RAD) * R * TUSK_FLAT, side = Math.sin(phi * RAD) * R;
  const r = a[0] + (b[0] - a[0]) * u + ty * out, y = a[1] + (b[1] - a[1]) * u - tr * out;
  return [Math.cos(th * RAD) * r - Math.sin(th * RAD) * side, y, Math.sin(th * RAD) * r + Math.cos(th * RAD) * side];
}
// pits in the bone: [t, phi, half length in t, half width in degrees]
const PITS = [[0.14, -30, 0.045, 17], [0.22, 24, 0.055, 20], [0.33, -12, 0.05, 20], [0.42, 36, 0.035, 20], [0.52, -28, 0.035, 22],
  [0.62, 8, 0.03, 24], [0.27, 88, 0.045, 18], [0.36, -95, 0.04, 18], [0.2, 150, 0.04, 16]];

// a tapering spike along control points, resting on the ground where it would sink
function spike(name, ctrl, r0, mat, parent, seg = 6, per = 3, pow = 1.1) {
  const path = catmullRomPath(ctrl, per), n = path.length - 1;
  const radii = path.map((_, i) => Math.max(0.012, r0 * (1 - (i / n) ** pow)));
  const p = path.map(([x, y, z], i) => [x, Math.max(y, radii[i]), z]);
  createPart(name, tubeGeo(p, radii, seg), mat, { parent });
  return p;
}

async function build() {
  const root = createRoot('VoidEvolutionPit');
  const chitin = gameMaterial(0x6b2f93, { roughness: 0.32, metalness: 0.1, name: 'chitin', flatShading: false });
  const chitinDark = gameMaterial(0x40195c, { roughness: 0.4, metalness: 0.05, name: 'chitin_dark', flatShading: false });
  const flesh = gameMaterial(0x7c1f37, { roughness: 0.45, name: 'flesh', flatShading: false });
  const fleshDark = gameMaterial(0x3a0814, { roughness: 0.5, name: 'flesh_dark', flatShading: false });
  const bone = gameMaterial(0xdcc9a6, { roughness: 0.5, name: 'bone', flatShading: false });
  const acid = gameMaterial(0x8cff3a, { emissive: 0x8cff3a, emissiveIntensity: 1.6, roughness: 0.2, name: 'glow_acid', flatShading: false });
  const team = gameMaterial(0x8cff3a, { emissive: 0x8cff3a, emissiveIntensity: 1.0, roughness: 0.3, name: 'team', flatShading: false });

  // the flesh crater and the twisted flesh round its rim
  createPart('Mound', moundGeo(36), flesh, { parent: root });
  createPart('RimBraid', braidGeo(0.74, -0.05, 0.125, 0.35, 6, 60, 8), flesh, { parent: root });
  createPart('InnerBraid', braidGeo(0.655, -0.2, 0.085, 0.35, -7, 56, 6), flesh, { parent: root });

  // chitin plates, each over a darker under-plate: a tier under the tusks and a tier of feet between them
  for (const th of TUSKS) {
    createPart(`Plate${th}`, plateGeo(th, 0.05, 0.74, 0.43, 0.16, 0.25), chitin, { parent: root });
    createPart(`PlateUnder${th}`, plateGeo(th, 0.03, 0.82, 0.49, 0.13, 0.25, -0.05), chitinDark, { parent: root });
    const front = th === 60, w = front ? 0.54 : 0.46, s0 = front ? 0.36 : 0.44;
    createPart(`FootPlate${th + 30}`, plateGeo(th + 30, s0, 1.13, w, 0.08, 0.4), chitin, { parent: root });
    createPart(`FootPlateUnder${th + 30}`, plateGeo(th + 30, s0 - 0.02, 1.15, w + 0.06, 0.06, 0.4, -0.05), chitinDark, { parent: root });
  }

  // six bone tusks leaning in over the pool, with root prongs gripping the plates and dark pits
  const pits = [];
  TUSKS.forEach((th, ti) => {
    const sp = tuskSpine(th), n = sp.length - 1;
    createPart(`Tusk${th}`, tubeGeo(sp.map(([r, y]) => polar(th, r, y)), sp.map((_, i) => tuskR(i / n)), 8,
      { side: [-Math.sin(th * RAD), 0, Math.cos(th * RAD)], sy: TUSK_FLAT }), bone, { parent: root });
    for (const d of [-1, 0, 1]) {
      spike(`TuskRoot${th}_${d + 1}`, [flank(th + d * 9, 0.1, 0.14), flank(th + d * 14, 0.27, 0.16), flank(th + d * 18, 0.46 - Math.abs(d) * 0.08, 0.1)], 0.12, bone, root, 4, 2);
    }
    PITS.forEach(([t, phi, dt, dphi], q) => {
      const j = (ti + q) % 2 ? 1 : -1, c = tuskSkin(th, sp, t, j * phi, 1.02);
      for (let k = 0; k < 8; k++) {
        const a0 = k * 45 * RAD, a1 = (k + 1) * 45 * RAD;
        pits.push(...c, ...tuskSkin(th, sp, t + dt * Math.cos(a0), j * phi + dphi * Math.sin(a0), 1.06),
          ...tuskSkin(th, sp, t + dt * Math.cos(a1), j * phi + dphi * Math.sin(a1), 1.06));
      }
    });
  });
  createPart('TuskPits', meshGeo({ positions: pits }), fleshDark, { parent: root });

  // glowing egg sacs set into the foot plates, each in a dark socket ring
  for (const [th, s, r, n] of [[150, 0.72, 0.25, 0.1], [30, 0.72, 0.24, 0.1], [270, 0.72, 0.23, 0.1], [43, 0.84, 0.12, 0.07]]) {
    createPart(`EggSac${th}`, sphereGeo(r, 12, 8), acid, { position: flank(th, s, n), scale: [0.88, 1.12, 0.88], parent: root });
    const ring = [];
    for (let k = 0; k < 10; k++) {
      const a = k * 36 * RAD;
      ring.push(flank(th + r * 0.95 * Math.cos(a) / flankR(s) / RAD, s + r * 1.1 * Math.sin(a) / FLANK_LEN, n + 0.04));
    }
    createPart(`SacSocket${th}`, tubeGeo(ring, ring.map(() => 0.05), 5, { closed: true }), chitinDark, { parent: root });
  }

  // root tendrils spreading over the ground from between the foot plates, some forking into toes
  const TENDRILS = [[56, 0.11, 1.4, -9, 1], [65, 0.13, 1.43, 10, 0], [115, 0.13, 1.43, -10, 1], [124, 0.12, 1.42, 9, 1],
    [-5, 0.1, 1.4, -9, 0], [5, 0.11, 1.42, 10, 1], [175, 0.11, 1.42, -10, 1], [185, 0.1, 1.4, 9, 0],
    [236, 0.1, 1.38, -9, 0], [245, 0.11, 1.42, 10, 1], [295, 0.11, 1.42, -10, 1], [304, 0.1, 1.38, 9, 0]];
  TENDRILS.forEach(([th, r0, reach, wig, toes], i) => {
    const p = spike(`Tendril${i}`, [flank(th, 0.78, -0.02), flank(th + wig * 0.5, 0.92, 0.05), flank(th + wig, 1.0, 0.06),
      polar(th + wig * 1.3, R_FOOT + (reach - R_FOOT) * 0.6, 0), polar(th + wig * 2, reach, 0)], r0, flesh, root, 6, 3);
    if (toes) {
      const q = p[Math.floor(p.length * 0.6)], qr = Math.hypot(q[0], q[2]), qt = Math.atan2(q[2], q[0]) / RAD;
      for (const d of [-1, 1]) {
        spike(`Toe${i}_${d + 1}`, [q, polar(qt + d * 6, qr + 0.1, 0), polar(qt + d * 13, Math.min(1.42, qr + 0.24), 0)], r0 * 0.5, flesh, root, 4, 2);
      }
    }
  });

  // the acid pool with bubbles and a swell where the blade stands
  createPart('Pool', cylinderGeo(0.65, 0.65, 0.06, 28), acid, { position: [0, POOL_Y - 0.03, 0], parent: root });
  createPart('PoolSwell', sphereGeo(0.36, 12, 6), acid, { position: [0, POOL_Y, 0], scale: [1, 0.22, 1], parent: root });
  [[-0.38, 0.22, 0.09], [0.33, 0.33, 0.075], [0.42, -0.12, 0.1], [-0.2, -0.42, 0.08], [0.12, -0.45, 0.06], [-0.47, -0.08, 0.06], [0.05, 0.5, 0.055], [-0.25, 0.45, 0.045], [0.28, 0.1, 0.05]]
    .forEach(([x, z, r], i) => createPart(`Bubble${i}`, sphereGeo(r, 6, 4), acid, { position: [x, POOL_Y + r * 0.25, z], parent: root }));

  // the half-formed bone blade rising out of the pool and dripping: the game bobs this node
  const fl = createPivot('float_blade', [0, POOL_Y, 0], root);
  fl.name = 'float_blade';
  const bp = catmullRomPath([[-0.12, 0.3, 0], [-0.13, 0.6, 0], [-0.07, 0.9, 0], [0.09, 1.12, 0], [0.32, 1.22, 0]], 3), bn = bp.length - 1;
  const br = bp.map((_, i) => { const t = i / bn; return 0.012 + 0.15 * (t < 0.2 ? 0.8 + t : (1 - (t - 0.2) / 0.8) ** 0.8); });
  createPart('BladeBone', tubeGeo(bp, br, 8, { side: [0, 0, 1], sx: 0.5 }), bone, { parent: fl });
  [[[-0.24, 0.42, 0.02], [-0.28, 0.28, 0.04], [-0.31, 0.14, 0.05]], [[-0.12, 0.4, -0.03], [-0.12, 0.24, -0.04], [-0.1, 0.1, -0.04]], [[-0.01, 0.42, 0.03], [0.03, 0.28, 0.05], [0.07, 0.16, 0.06]]]
    .forEach((c, i) => spike(`BladeProng${i}`, c, 0.075, bone, fl, 4, 2));
  [[[-0.31, 0.2, 0.05], [-0.37, 0.04, 0.08], [-0.46, -0.1, 0.12]], [[-0.1, 0.16, -0.04], [-0.11, 0.0, -0.09], [-0.13, -0.1, -0.17]],
    [[0.07, 0.22, 0.06], [0.12, 0.04, 0.13], [0.2, -0.1, 0.22]], [[0.08, 0.84, 0.0], [0.2, 0.4, 0.02], [0.33, -0.1, 0.0]],
    [[-0.14, 0.5, 0.07], [-0.05, 0.2, 0.18], [-0.02, -0.1, 0.3]], [[-0.2, 0.56, -0.05], [-0.27, 0.2, -0.14], [-0.33, -0.1, -0.22]]].forEach((c, i) => {
    const path = catmullRomPath(c, 3), n = path.length - 1;
    const radii = path.map((_, k) => { const t = k / n; return 0.03 + 0.03 * (1 - t) ** 2 + 0.09 * t ** 3; });
    createPart(`BladeSlime${i}`, tubeGeo(path, radii, 5, { blunt: true }), acid, { parent: fl });
  });
  createPart('BladeDrip0', sphereGeo(0.035, 6, 4), acid, { position: [0.2, 0.98, 0], scale: [1, 1.5, 1], parent: fl });
  createPart('BladeDrip1', sphereGeo(0.028, 6, 4), acid, { position: [0.12, 0.8, 0.02], scale: [1, 1.5, 1], parent: fl });

  // small team-colour nodules on the upper plates
  TUSKS.forEach((th, i) => {
    createPart(`Nodule${th}`, sphereGeo(0.07, 6, 4), team, { position: flank(th + (i % 2 ? 20 : -20), 0.38, 0.1), parent: root });
  });
  return root;
}
