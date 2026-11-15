// Shardfall: Void Sky Chrysalis (flyer upgrades), from art/void_buildings/concepts/shardfall_void_sky_chrysalis.png
// Front faces +Z. 2.8 x 2.8 m footprint, 3 m tall. An upright cocoon of overlapping pointed chitin
// plates with glowing acid slits between them stands under two bone arches that meet in a spiked
// crest. Two folded membrane wings wrap its lower sides, and plates, flesh roots and bone spikes
// ring its foot. Every shape is baked in world space and merged into one mesh per role.
// Materials: chitin, chitin_dark, flesh (wing membrane), flesh_dark (wing ribs, roots), bone,
// glow_acid, team (wing knuckles and base nodules).
const meta = { name: 'Void Sky Chrysalis', role: 'building' };

const RAD = Math.PI / 180;
// palette: flesh and flesh_dark are tuned to this concept (bright membrane, darker ribs and roots)
const CHITIN = 0x6b2f93, CHITIN_DARK = 0x40195c, FLESH = 0xa32b48, FLESH_DARK = 0x6a1830, BONE = 0xdcc9a6, ACID = 0x8cff3a;

const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const mul = (a, s) => [a[0] * s, a[1] * s, a[2] * s];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const norm = (a) => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };
const lerp = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
const bez = (a, b, c, t) => lerp(lerp(a, b, t), lerp(b, c, t), t);
// phi is measured from the front (+Z) toward the right (+X)
const ring = (phi, r, y) => [Math.sin(phi * RAD) * r, y, Math.cos(phi * RAD) * r];

// ---- mesh accumulator
function mesh() { return { p: [], i: [] }; }
function vert(M, q) { M.p.push(q[0], q[1], q[2]); return M.p.length / 3 - 1; }
function tri(M, a, b, c) { M.i.push(a, b, c); }
function mirrorX(M, T) {
  const base = M.p.length / 3;
  for (let k = 0; k < T.p.length; k += 3) M.p.push(-T.p[k], T.p[k + 1], T.p[k + 2]);
  for (let k = 0; k < T.i.length; k += 3) M.i.push(base + T.i[k], base + T.i[k + 2], base + T.i[k + 1]);
}
function merge(M, T) {
  const base = M.p.length / 3;
  for (const v of T.p) M.p.push(v);
  for (const k of T.i) M.i.push(base + k);
}
function emit(name, M, mat, parent) {
  for (let k = 1; k < M.p.length; k += 3) M.p[k] = Math.max(0, M.p[k]); // nothing below the ground
  return createPart(name, meshGeo({ positions: M.p, indices: M.i }), mat, { parent });
}

// round tube along a path; radii is an array or a function of 0..1. flatN squashes it along ref.
function tube(M, path, radii, o = {}) {
  const seg = o.seg || 6, n = path.length, rings = [];
  let N = null;
  for (let i = 0; i < n; i++) {
    const T = norm(sub(path[Math.min(i + 1, n - 1)], path[Math.max(i - 1, 0)]));
    if (!N) {
      const ref = o.ref || (Math.abs(T[1]) < 0.9 ? [0, 1, 0] : [1, 0, 0]);
      N = norm(sub(ref, mul(T, dot(ref, T))));
    } else N = norm(sub(N, mul(T, dot(N, T))));
    const B = cross(T, N);
    const r = typeof radii === 'function' ? radii(i / (n - 1)) : radii[i];
    const row = [];
    for (let k = 0; k < seg; k++) {
      const a = (k / seg) * 2 * Math.PI;
      row.push(vert(M, add(path[i], add(mul(N, Math.cos(a) * r * (o.flatN || 1)), mul(B, Math.sin(a) * r * (o.flatB || 1))))));
    }
    rings.push(row);
  }
  for (let i = 0; i < n - 1; i++) for (let k = 0; k < seg; k++) {
    const a = rings[i][k], b = rings[i][(k + 1) % seg], c = rings[i + 1][(k + 1) % seg], d = rings[i + 1][k];
    tri(M, a, b, d); tri(M, b, c, d);
  }
  if (o.capStart) { const c = vert(M, path[0]); for (let k = 0; k < seg; k++) tri(M, rings[0][(k + 1) % seg], rings[0][k], c); }
  const e = vert(M, path[n - 1]);
  for (let k = 0; k < seg; k++) tri(M, rings[n - 1][k], rings[n - 1][(k + 1) % seg], e);
}
// a horn, thorn or claw: a spline tube that tapers to a point
function claw(M, ctrl, r0, o = {}) {
  tube(M, catmullRomPath(ctrl, o.samples || 2), (t) => 0.007 + r0 * Math.pow(1 - t, o.pow || 0.85), o);
}
// surface of revolution about Y; prof is [[r, y], ...] from bottom to top, r = 0 closes an end
function lathe(M, prof, seg, c = [0, 0, 0], s = [1, 1, 1]) {
  const rows = prof.map(([r, y]) => {
    if (r <= 1e-6) return [vert(M, [c[0], c[1] + y * s[1], c[2]])];
    const row = [];
    for (let k = 0; k < seg; k++) {
      const a = (k / seg) * 2 * Math.PI;
      row.push(vert(M, [c[0] + r * Math.sin(a) * s[0], c[1] + y * s[1], c[2] + r * Math.cos(a) * s[2]]));
    }
    return row;
  });
  for (let j = 0; j < rows.length - 1; j++) {
    const A = rows[j], B = rows[j + 1];
    for (let k = 0; k < seg; k++) {
      const k1 = (k + 1) % seg;
      if (A.length === 1 && B.length === 1) continue;
      if (A.length === 1) tri(M, A[0], B[k1], B[k]);
      else if (B.length === 1) tri(M, A[k], A[k1], B[0]);
      else { tri(M, A[k], A[k1], B[k]); tri(M, A[k1], B[k1], B[k]); }
    }
  }
}
function blob(M, c, rad, seg = 8, rows = 5) {
  const prof = [];
  for (let j = 0; j <= rows; j++) {
    const a = -Math.PI / 2 + (Math.PI * j) / rows;
    prof.push([j === 0 || j === rows ? 0 : Math.cos(a), Math.sin(a)]);
  }
  lathe(M, prof, seg, c, rad);
}

// A pointed shield plate: root edge at the local origin, tip at (0, -L). Crowned with a ridge,
// the tip lifting off its carrier, closed underneath by a fan to a belly point inside the carrier.
// carrier(x, y, z) maps plate coordinates (x across, y along, z lift) to world.
function plate(M, carrier, o) {
  const { L, W, T = 0.06, lift = 0.08, nu = 4, nv = 6, rootW = 0.5, belly = -0.1, hump = 0 } = o;
  const prof = (v) => {
    if (v < 0.3) return rootW + (1 - rootW) * Math.sin((v / 0.3) * Math.PI / 2);
    return 1 - Math.pow((v - 0.3) / 0.7, 1.6);
  };
  const P = (s, v) => {
    const crown = 0.4 * (1 - s * s) + 0.6 * (1 - Math.abs(s));
    const z = T * crown * (0.55 + 0.45 * Math.sin(Math.PI * Math.min(1, v * 1.25))) + lift * v * v + hump * Math.sin(Math.PI * v);
    return carrier(W * prof(v) * s, -L * v, z);
  };
  const rows = [];
  for (let j = 0; j < nv; j++) {
    const row = [];
    for (let i = 0; i <= nu; i++) row.push(vert(M, P(-1 + (2 * i) / nu, j / nv)));
    rows.push(row);
  }
  const tip = vert(M, P(0, 1));
  for (let j = 0; j < nv - 1; j++) for (let i = 0; i < nu; i++) {
    const a = rows[j][i], b = rows[j][i + 1], c = rows[j + 1][i + 1], d = rows[j + 1][i];
    tri(M, a, d, b); tri(M, b, d, c);
  }
  for (let i = 0; i < nu; i++) tri(M, rows[nv - 1][i], tip, rows[nv - 1][i + 1]);
  const rim = [];
  for (let i = 0; i <= nu; i++) rim.push(P(-1 + (2 * i) / nu, 0));
  for (let j = 1; j < nv; j++) rim.push(P(1, j / nv));
  rim.push(P(0, 1));
  for (let j = nv - 1; j >= 1; j--) rim.push(P(-1, j / nv));
  const ids = rim.map((q) => vert(M, q));
  const b = vert(M, carrier(0, -L * 0.42, belly));
  for (let k = 0; k < ids.length; k++) tri(M, ids[k], ids[(k + 1) % ids.length], b);
}
// carrier on a frame: Y along the plate (root end), Z its outward normal; wrapR curls it about Y
function frameCarrier(O, Yax, Zax, wrapR) {
  const Y = norm(Yax), Z = norm(sub(Zax, mul(Y, dot(Zax, Y)))), X = cross(Y, Z);
  return (x, y, z) => {
    let lx = x, lz = z;
    if (wrapR) { const a = x / wrapR; lx = (wrapR + z) * Math.sin(a); lz = (wrapR + z) * Math.cos(a) - wrapR; }
    return add(O, add(mul(X, lx), add(mul(Y, y), mul(Z, lz))));
  };
}

// ---- cocoon: radius by height, a teardrop widest at 1.4 m and drawn in to a neck under the crest
const COCOON = [[0.2, 0.27], [0.45, 0.37], [0.8, 0.47], [1.15, 0.525], [1.45, 0.535], [1.7, 0.505], [1.9, 0.46], [2.05, 0.37], [2.17, 0.23], [2.3, 0.1]];
function cocoonR(y) {
  const t = COCOON, n = t.length;
  if (y <= t[0][0]) return t[0][1];
  if (y >= t[n - 1][0]) return t[n - 1][1];
  let k = 0;
  while (y > t[k + 1][0]) k++;
  const m = (j) => { const a = t[Math.max(j - 1, 0)], b = t[Math.min(j + 1, n - 1)]; return (b[1] - a[1]) / (b[0] - a[0]); };
  const h = t[k + 1][0] - t[k][0], u = (y - t[k][0]) / h, u2 = u * u, u3 = u2 * u;
  return (2 * u3 - 3 * u2 + 1) * t[k][1] + (u3 - 2 * u2 + u) * h * m(k) + (-2 * u3 + 3 * u2) * t[k + 1][1] + (u3 - u2) * h * m(k + 1);
}
// carrier on the cocoon skin: theta from the front toward +X, tilt swings the tip toward +theta
const onCocoon = (th0, y0, tilt) => (x, y, z) => {
  const ct = Math.cos(tilt * RAD), st = Math.sin(tilt * RAD);
  const xr = x * ct - y * st, yr = x * st + y * ct;
  const Y = Math.max(0.2, Math.min(2.3, y0 + yr)), R = cocoonR(Y);
  const th = th0 * RAD + xr / Math.max(R, 0.16);
  return [(R + z) * Math.sin(th), Y, (R + z) * Math.cos(th)];
};
// a glowing lens, pointed top and bottom, bulging through the skin
function slit(M, th0, yc, h, w, tilt) {
  const car = onCocoon(th0, yc, tilt), nu = 4, nv = 8;
  const P = (s, v) => {
    const e = Math.sin(Math.PI * v);
    return car(0.5 * w * Math.pow(e, 0.7) * s, (0.5 - v) * h, -0.008 + 0.05 * (1 - s * s) * Math.sqrt(e));
  };
  const top = vert(M, P(0, 0)), rows = [];
  for (let j = 1; j < nv; j++) {
    const row = [];
    for (let i = 0; i <= nu; i++) row.push(vert(M, P(-1 + (2 * i) / nu, j / nv)));
    rows.push(row);
  }
  const bot = vert(M, P(0, 1));
  for (let i = 0; i < nu; i++) { tri(M, top, rows[0][i], rows[0][i + 1]); tri(M, rows[rows.length - 1][i], bot, rows[rows.length - 1][i + 1]); }
  for (let j = 0; j < rows.length - 1; j++) for (let i = 0; i < nu; i++) {
    const a = rows[j][i], b = rows[j][i + 1], c = rows[j + 1][i + 1], d = rows[j + 1][i];
    tri(M, a, d, b); tri(M, b, d, c);
  }
}
// [theta, centre height, height, width, tilt]
const SLITS = [
  [-8, 1.08, 0.88, 0.2, -5], [15, 1.73, 0.38, 0.12, 8], [-38, 1.53, 0.34, 0.13, -14], [36, 1.15, 0.55, 0.12, -3],
  [-69, 1.08, 0.26, 0.09, 0], [108, 1.45, 0.5, 0.12, 0], [172, 1.1, 0.8, 0.2, 0], [-128, 1.48, 0.45, 0.12, 0],
];
// [theta, root height, length, half width, tilt]
const PLATES = [
  // cap petals hanging from the neck
  [-12, 2.24, 0.6, 0.25, 0], [52, 2.24, 0.58, 0.25, 4], [124, 2.24, 0.54, 0.25, 0], [-164, 2.24, 0.56, 0.25, 0], [-88, 2.24, 0.5, 0.25, -4],
  // shoulder row, flanking the slits
  [30, 1.88, 0.78, 0.115, -5], [58, 1.62, 0.8, 0.14, 0], [82, 1.8, 0.75, 0.13, 0], [143, 1.8, 0.78, 0.13, 0], [201, 1.8, 0.78, 0.13, 0],
  [-105, 1.8, 0.75, 0.13, 0], [-62, 1.86, 0.7, 0.13, 0], [-31, 1.4, 0.7, 0.115, 4],
  // lower row
  [20, 1.02, 0.62, 0.12, -3], [47, 0.84, 0.5, 0.13, 0], [78, 1.0, 0.6, 0.14, 0], [110, 0.95, 0.6, 0.14, 0], [140, 0.9, 0.55, 0.13, 0],
  [205, 0.9, 0.55, 0.13, 0], [-120, 0.95, 0.6, 0.15, 0], [-85, 1.0, 0.6, 0.14, 0], [-8, 0.66, 0.42, 0.14, 0], [172, 0.66, 0.42, 0.14, 0],
];

// ---- bone arches (authored for the left, sx = -1 mirrors to the right)
const ARCH = [[-1.12, -0.02, 0], [-1.13, 0.5, 0], [-1.08, 1.05, 0], [-0.96, 1.52, 0], [-0.75, 1.9, 0], [-0.46, 2.18, 0], [-0.16, 2.38, 0], [-0.02, 2.45, 0]];
const archR = (u) => (u < 0.15 ? 0.07 + 0.06 * Math.sin((u / 0.15) * Math.PI / 2) : 0.13 - 0.04 * (u - 0.15) / 0.85);
function arch(sx, bone, plates, thorns) {
  const path = catmullRomPath(ARCH.map(([x, y, z]) => [x * sx, y, z]), 3), n = path.length;
  const at = (u) => {
    const f = u * (n - 1), i = Math.min(Math.floor(f), n - 2), t = norm(sub(path[i + 1], path[i]));
    return { p: lerp(path[i], path[i + 1], f - i), t, o: [-t[1] * sx, t[0] * sx, 0], r: archR(u) };
  };
  tube(bone, path, archR, { seg: 8, ref: [1, 0, 0], flatB: 0.85, capStart: true });
  // [u, side (1 out, -1 in), lean toward the front, length, radius, curl toward the crest]
  for (const [u, side, zl, L, r0, curl] of thorns) {
    const a = at(u), d = norm(add(mul(a.o, side), [0, 0, zl])), b = add(a.p, mul(d, a.r * 0.5));
    claw(bone, [b, add(b, add(mul(d, L * 0.45), mul(a.t, curl * L * 0.08))), add(b, add(mul(d, L * 0.8), mul(a.t, curl * L * 0.35))), add(b, add(mul(d, L), mul(a.t, curl * L * 0.75)))], r0, { seg: 5, flatN: 0.75 });
  }
  for (const u of [0.56, 0.455, 0.35]) {
    const a = at(u), wr = a.r + 0.012;
    plate(plates, frameCarrier(add(a.p, mul(a.o, a.r)), a.t, a.o, wr), { L: 0.46, W: 0.24, T: 0.06, lift: 0.06, belly: -wr, nv: 5 });
  }
  return at;
}

// ---- folded wing (left); the right one is its mirror
function wingLeft(mem, ribs, knuckle) {
  const S = [-0.5, 1.72, 0.2];
  const K = [[-0.98, 0.93, 0.2], [-0.86, 0.56, 0.5], [-0.6, 0.62, 0.7], [-0.36, 0.26, 0.68], [-0.17, 0.78, 0.62]];
  const BULGE = [0.2, 0.24, 0.26, 0.24, 0.22];
  const out = (p) => norm([p[0], 0, p[2]]);
  const C = K.map((k, i) => { const m = lerp(S, k, 0.5); return add(add(m, mul(out(m), BULGE[i])), [0, 0.06, 0]); });
  const NR = K.length, SUB = 4, cols = (NR - 1) * SUB, rows = 5, r0 = 0.1;
  const P = (a, r) => {
    const i = Math.min(Math.floor(a), NR - 2), f = a - i, sc = Math.sin(Math.PI * f);
    const k = lerp(lerp(K[i], K[i + 1], f), S, 0.2 * sc);
    const c0 = lerp(C[i], C[i + 1], f);
    return bez(S, add(c0, mul(out(c0), -0.04 * sc)), k, r);
  };
  const grid = (off) => {
    const g = [];
    for (let j = 0; j <= rows; j++) {
      const row = [];
      for (let i = 0; i <= cols; i++) {
        let p = P(i / SUB, r0 + ((1 - r0) * j) / rows);
        if (off) p = add(p, mul(out(p), -off * Math.min(1, 3 * Math.min(j / rows, 1 - j / rows, i / cols, 1 - i / cols))));
        row.push(vert(mem, p));
      }
      g.push(row);
    }
    return g;
  };
  const F = grid(0), B = grid(0.035);
  for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) {
    tri(mem, F[j][i], F[j + 1][i], F[j][i + 1]); tri(mem, F[j][i + 1], F[j + 1][i], F[j + 1][i + 1]);
    tri(mem, B[j][i], B[j][i + 1], B[j + 1][i]); tri(mem, B[j][i + 1], B[j + 1][i + 1], B[j + 1][i]);
  }
  const RIB = [0.06, 0.042, 0.042, 0.046, 0.04];
  for (let i = 0; i < NR; i++) {
    const path = [];
    for (let s = 0; s <= 7; s++) { const p = bez(S, C[i], K[i], 0.03 + (1.03 * s) / 7); path.push(add(p, mul(out(p), 0.012))); }
    tube(ribs, path, (t) => 0.01 + (RIB[i] - 0.01) * Math.pow(1 - t, 0.8), { seg: 5, capStart: true });
  }
  blob(knuckle, S, [0.1, 0.1, 0.1], 8, 5);
}

async function build() {
  const root = createRoot('VoidSkyChrysalis');
  const chitin = gameMaterial(CHITIN, { roughness: 0.32, metalness: 0.1, name: 'chitin', flatShading: false });
  const chitinDark = gameMaterial(CHITIN_DARK, { roughness: 0.4, metalness: 0.05, name: 'chitin_dark', flatShading: false });
  const flesh = gameMaterial(FLESH, { roughness: 0.5, name: 'flesh', flatShading: false });
  const fleshDark = gameMaterial(FLESH_DARK, { roughness: 0.45, name: 'flesh_dark', flatShading: false });
  const bone = gameMaterial(BONE, { roughness: 0.5, name: 'bone', flatShading: false });
  const acid = gameMaterial(ACID, { emissive: ACID, emissiveIntensity: 1.7, roughness: 0.2, name: 'glow_acid', flatShading: false });
  const team = gameMaterial(ACID, { emissive: ACID, emissiveIntensity: 1.0, roughness: 0.3, name: 'team', flatShading: false });

  // cocoon: dark core, glowing slits, overlapping pointed plates
  const core = mesh(), prof = [[0, 0.17]];
  for (let j = 0; j <= 12; j++) { const y = 0.2 + (2.1 * j) / 12; prof.push([cocoonR(y) - 0.004, y]); }
  prof.push([0, 2.33]);
  lathe(core, prof, 18);
  emit('CocoonCore', core, chitinDark, root);
  const slits = mesh();
  for (const [th, y, h, w, tilt] of SLITS) slit(slits, th, y, h, w, tilt);
  emit('CocoonSlits', slits, acid, root);
  const plates = mesh();
  for (const [th, y, L, W, tilt] of PLATES) plate(plates, onCocoon(th, y, tilt), { L, W, T: 0.09, lift: 0.1, belly: -0.12 });
  emit('CocoonPlates', plates, chitin, root);

  // arches with thorns and chitin plates
  const arches = mesh(), archPlates = mesh();
  arch(1, arches, archPlates, [[0.63, 1, 0, 0.36, 0.075, 1], [0.2, 1, 0.6, 0.17, 0.045, 1], [0.08, 1, -0.6, 0.14, 0.04, 1], [0.5, -1, 0.2, 0.15, 0.04, 0.6], [0.3, -1, -0.2, 0.14, 0.04, 0.6], [0.85, 1, 0, 0.14, 0.04, 1]]);
  arch(-1, arches, archPlates, [[0.67, 1, 0, 0.34, 0.075, 1], [0.24, 1, -0.5, 0.16, 0.045, 1], [0.1, 1, 0.6, 0.15, 0.04, 1], [0.56, -1, -0.2, 0.15, 0.04, 0.6], [0.36, -1, 0.2, 0.14, 0.04, 0.6], [0.16, -1, 0, 0.13, 0.04, 0.6]]);
  emit('Arches', arches, bone, root);
  emit('ArchPlates', archPlates, chitin, root);

  // crest: a knot of bone with a hooked top horn, side horns and fangs
  const crest = mesh(), H = { seg: 6, ref: [0, 0, 1], flatN: 0.6, samples: 3 };
  blob(crest, [0, 2.46, 0], [0.17, 0.13, 0.13], 8, 5);
  claw(crest, [[0.02, 2.4, 0], [0.17, 2.58, 0], [0.17, 2.78, 0], [0.04, 2.93, 0], [-0.13, 2.99, 0]], 0.16, { seg: 6, ref: [0, 0, 1], flatN: 0.5, samples: 3, pow: 0.7 });
  claw(crest, [[-0.02, 2.46, 0.02], [-0.22, 2.52, 0.04], [-0.38, 2.47, 0.05], [-0.5, 2.36, 0.05]], 0.13, H);
  claw(crest, [[0.02, 2.46, 0.02], [0.22, 2.52, 0.04], [0.37, 2.48, 0.05], [0.49, 2.38, 0.05]], 0.13, H);
  claw(crest, [[-0.2, 2.52, 0.04], [-0.25, 2.64, 0.04], [-0.2, 2.74, 0.04]], 0.07, H);
  claw(crest, [[0.26, 2.52, 0.04], [0.33, 2.63, 0.04], [0.3, 2.73, 0.04]], 0.07, H);
  claw(crest, [[0.05, 2.42, 0.04], [0.13, 2.33, 0.08], [0.17, 2.19, 0.1]], 0.07, { seg: 5 });
  claw(crest, [[-0.04, 2.42, 0.07], [-0.03, 2.33, 0.15], [0.0, 2.23, 0.18]], 0.06, { seg: 5 });
  claw(crest, [[0, 2.46, -0.04], [0, 2.53, -0.2], [0, 2.49, -0.36]], 0.08, { seg: 5 });
  emit('Crest', crest, bone, root);
  const neck = mesh();
  tube(neck, [[0, 2.12, 0], [0, 2.26, 0], [0, 2.36, 0], [0, 2.46, 0]], [0.13, 0.085, 0.09, 0.11], { seg: 7 });
  for (const sx of [-1, 1]) blob(neck, [sx * 0.2, 2.35, 0], [0.11, 0.09, 0.12], 7, 4);
  emit('Neck', neck, fleshDark, root);

  // wings
  const mem = mesh(), ribs = mesh(), knuckles = mesh(), tm = mesh(), tr = mesh(), tk = mesh();
  wingLeft(tm, tr, tk);
  merge(mem, tm); mirrorX(mem, tm); merge(ribs, tr); mirrorX(ribs, tr); merge(knuckles, tk); mirrorX(knuckles, tk);
  emit('WingMembranes', mem, flesh, root);
  emit('WingRibs', ribs, fleshDark, root);

  // base: flesh mound and roots, chitin plates, bone spikes
  const mound = mesh();
  lathe(mound, [[1.02, 0], [0.96, 0.07], [0.74, 0.15], [0.5, 0.26], [0.36, 0.4], [0.3, 0.52]], 14);
  for (const [phi, wig, reach, r0] of [[2, 8, 1.3, 0.11], [38, -10, 1.34, 0.1], [72, 9, 1.2, 0.1], [104, -8, 1.3, 0.1], [140, 10, 1.34, 0.11], [185, -9, 1.3, 0.1], [222, 8, 1.34, 0.1], [-104, 8, 1.28, 0.1], [-76, -8, 1.22, 0.1], [-48, 10, 1.36, 0.11], [-18, -9, 1.3, 0.1]]) {
    const path = catmullRomPath([ring(phi, 0.3, 0.36), ring(phi + wig * 0.4, 0.58, 0.22), ring(phi + wig, 0.92, 0.1), ring(phi + wig * 0.5, reach, 0.05)], 2);
    tube(mound, path, (t) => r0 * (1 - 0.65 * t), { seg: 5 });
  }
  for (const sx of [-1, 1]) {
    blob(mound, [sx * 1.08, 0.15, 0], [0.2, 0.15, 0.24], 7, 4);
    claw(mound, [[sx * 0.62, 0.2, 0.22], [sx * 0.95, 0.12, 0.2], [sx * 1.04, 0.3, 0.13], [sx * 1.07, 0.55, 0.1]], 0.08, { seg: 5, pow: 0.6 });
    claw(mound, [[sx * 0.62, 0.2, -0.22], [sx * 0.95, 0.12, -0.2], [sx * 1.03, 0.26, -0.13], [sx * 1.06, 0.45, -0.1]], 0.08, { seg: 5, pow: 0.6 });
  }
  emit('BaseRoots', mound, fleshDark, root);
  const basePlates = mesh();
  for (const [phi, ra, ya, rb, W] of [[-32, 0.68, 0.3, 1.34, 0.3], [24, 0.72, 0.28, 1.22, 0.22], [60, 0.72, 0.28, 1.3, 0.24], [120, 0.72, 0.28, 1.3, 0.24], [168, 0.68, 0.3, 1.34, 0.3], [-150, 0.72, 0.28, 1.28, 0.24], [-116, 0.74, 0.26, 1.26, 0.22], [-64, 0.74, 0.26, 1.26, 0.22]]) {
    const O = ring(phi, ra, ya), tipP = ring(phi, rb, 0.0), Y = sub(O, tipP);
    plate(basePlates, frameCarrier(O, Y, [0, 1, 0], 0.3), { L: Math.hypot(Y[0], Y[1], Y[2]), W, T: 0.08, lift: 0.02, hump: 0.1, belly: -0.25, nv: 6 });
  }
  emit('BasePlates', basePlates, chitin, root);
  const spikes = mesh();
  for (const [phi, r, h] of [[-8, 1.0, 0.34], [-50, 1.22, 0.26], [-100, 1.3, 0.2], [-125, 0.85, 0.22], [32, 1.12, 0.27], [14, 1.2, 0.2], [78, 1.22, 0.24], [125, 0.8, 0.2], [150, 1.2, 0.24], [200, 1.15, 0.22], [-150, 1.25, 0.2], [100, 1.3, 0.18]]) {
    const b = ring(phi, r, 0.03), o = ring(phi, 1, 0);
    claw(spikes, [b, add(b, add([0, h * 0.45, 0], mul(o, h * 0.22))), add(b, add([0, h * 0.8, 0], mul(o, h * 0.3))), add(b, add([0, h, 0], mul(o, h * 0.2)))], Math.max(0.05, h * 0.24), { seg: 5 });
  }
  emit('BaseSpikes', spikes, bone, root);

  // team accents: wing knuckles and nodules on the base plates
  for (const phi of [-32, 60, 168, -116]) blob(knuckles, ring(phi, 0.9, 0.33), [0.075, 0.075, 0.075], 7, 4);
  emit('TeamNodules', knuckles, team, root);
  return root;
}
