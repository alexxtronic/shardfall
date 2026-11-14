"""Neutral world pieces for Shardfall, built by script: the golden crystal clusters players mine, the Void
Slime pile, and the alien rock formations that block paths.

    Blender --background --factory-startup --python-exit-code 1 --python art/neutral/build.py -- <id|all|lineup> [--round N] [--no-render]

ids: crystal_a .. crystal_d (golden spike clusters on a rocky base, about 2 x 1 m, 1.4-2.2 m tall),
slime_pile (3 x 3 m glossy black goo mound with glowing green cracks), rock_a .. rock_c (slate-blue faceted
rock with teal lichen, 3 x 3, 4 x 2 and 5 x 3 m). `lineup` renders every finished GLB (these and the
Ambron vehicles) together under the game camera.

Writes assets/models/<id>.glb, assets/icons/<id>.png (not for rocks) and review renders into
art/neutral/review/round<N>/. Shared helpers (lathe, transforms, staging, renders, export) come from
art/ambron_vehicles/build.py, loaded the way the mailbox loads the bench build.

Materials: crystals `glow_crystal` (a gold-to-amber gradient texture as base colour and, at low strength,
emission; flat facets) and `rock`; slime `slime` (an oily black texture with purple-green sheen bands) and
`glow_slime` (the cracks); rocks `rock` only (a slate gradient by height plus teal lichen columns).
"""
import importlib.util
import json
import math
import os
import random
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector, noise

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True                 # no __pycache__ beside the vehicle script
_spec = importlib.util.spec_from_file_location("ambron_vehicles_build",
                                               os.path.join(os.path.dirname(HERE), "ambron_vehicles", "build.py"))
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)

IDS = ("crystal_a", "crystal_b", "crystal_c", "crystal_d", "slime_pile", "rock_a", "rock_b", "rock_c")
NO_ICON = {"rock_a", "rock_b", "rock_c"}

# --- palettes (sRGB) -----------------------------------------------------------------------------------
# texture columns of (v, hex) stops, v running from the bottom (0) to the top (1)
CRYSTAL_COLS = [
    [(0.0, "#A9530A"), (0.22, "#E08A12"), (0.62, "#FFC93A"), (0.9, "#FFE07A"), (1.0, "#FFF1B8")],   # wide faces
    [(0.0, "#D27C10"), (0.25, "#F5A623"), (0.6, "#FFD65C"), (0.88, "#FFEDA6"), (1.0, "#FFF8DC")],   # chamfers
    [(0.0, "#94460A"), (0.25, "#CF7410"), (0.65, "#F7B22E"), (0.92, "#FFD465"), (1.0, "#FFE9A0")],  # amber spike
    [(0.0, "#C26C0E"), (0.3, "#EE9A1E"), (0.65, "#FFC93A"), (0.9, "#FFE48C"), (1.0, "#FFF4C8")],   # its chamfers
]
CRYSTAL_EMIT = 0.45
ROCK_COLS = [
    [(0.0, "#2A303A"), (0.18, "#353C49"), (0.5, "#454D5C"), (1.0, "#5A6474")],      # slate
    [(0.0, "#30363F"), (0.18, "#3C4351"), (0.5, "#4E5767"), (1.0, "#646E7E")],      # lighter facets
    [(0.0, "#22413B"), (0.3, "#2C5F56"), (1.0, "#3E8577")],                          # lichen, dark
    [(0.0, "#2B5148"), (0.3, "#3A7A6C"), (1.0, "#56A08E")],                          # lichen, light
]
ROCK_V_SCALE = 3.0           # metres of height across the rock gradient
SLIME_GLOW = "#8CFF3A"


# --- textures and materials ------------------------------------------------------------------------------

def column_image(name, cols, h=128):
    w = 16 * len(cols)
    px = np.ones((h, w, 4), np.float32)
    vs = (np.arange(h) + 0.5) / h
    for ci, stops in enumerate(cols):
        sv = [s for s, _ in stops]
        rgb = np.array([V.srgb(c) for _, c in stops])
        for ch in range(3):
            px[:, ci * 16:(ci + 1) * 16, ch] = np.interp(vs, sv, rgb[:, ch])[:, None]
    img = bpy.data.images.new(name, w, h, alpha=False)
    img.pixels.foreach_set(px.ravel())
    img.pack()
    return img


def col_uv(ci, ncols, t):
    return ((ci + 0.5) / ncols, 0.02 + 0.96 * min(1.0, max(0.0, t)))


def tex_mat(name, img, rough, metal=0.0, emit=0.0):
    m, nt, p = V.principled(name)
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    nt.links.new(t.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if emit:
        nt.links.new(t.outputs["Color"], p.inputs["Emission Color"])
        p.inputs["Emission Strength"].default_value = emit
    return m


def slime_image(n=256, seed=3):
    """Oily black with thin-film bands: a warped interference field mapped through purple, blue and green,
    kept dark except along the bands."""
    rng = np.random.default_rng(seed)
    x, y = np.meshgrid(np.linspace(-1.6, 1.6, n), np.linspace(-1.6, 1.6, n))
    f = np.zeros_like(x)
    for _ in range(5):
        a, b, c, d = rng.uniform(1.5, 4.5, 4)
        p1, p2 = rng.uniform(0, 6.3, 2)
        f += np.sin(a * x + 1.6 * np.sin(b * y + p1)) * np.cos(c * y + 1.2 * np.sin(d * x + p2))
    f /= 5
    phase = (f * 2.6) % 1.0
    stops = np.array([V.srgb(h) for h in ("#5B2A8C", "#2B3F9A", "#1E8A6A", "#5FA82A", "#5B2A8C")])
    sv = np.linspace(0, 1, len(stops))
    band = np.stack([np.interp(phase, sv, stops[:, ch]) for ch in range(3)], -1)
    m = np.clip((np.abs(np.sin(np.pi * f * 4.3)) - 0.80) / 0.20, 0, 1) ** 2.0
    m = m * (0.35 + 0.65 * np.clip(0.5 + 0.5 * np.sin(2.1 * x - 1.3 * y + 0.4), 0, 1))   # sheen comes and goes
    base = np.array(V.srgb("#0A090E"))
    col = base * (1 - 0.42 * m[..., None]) + band * 0.42 * m[..., None]
    px = np.ones((n, n, 4), np.float32)
    px[..., :3] = col
    img = bpy.data.images.new("slime_sheen", n, n, alpha=False)
    img.pixels.foreach_set(px.ravel())
    img.pack()
    return img


# --- mesh assembly ----------------------------------------------------------------------------------------

def uv_layer(bm):
    return bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")


def merge(dst, src, smooth=False):
    """Copies src's faces (with their UVs and material indices) into dst."""
    su, du = uv_layer(src), uv_layer(dst)
    vmap = {v: dst.verts.new(v.co) for v in src.verts}
    for f in src.faces:
        nf = dst.faces.new([vmap[v] for v in f.verts])
        nf.material_index, nf.smooth = f.material_index, smooth
        for nl, ol in zip(nf.loops, f.loops):
            nl[du].uv = ol[su].uv
    src.free()


def to_object(name, bm, mats):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def rand_dir(rng):
    u = rng.uniform(-1, 1)
    th = rng.uniform(0, 2 * math.pi)
    s = math.sqrt(1 - u * u)
    return Vector((s * math.cos(th), s * math.sin(th), u))


def hull(points, angle=4.0):
    """Convex hull of the points; near-coplanar triangles merged into big facets."""
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in points]
    res = bmesh.ops.convex_hull(bm, input=vs)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(angle), verts=bm.verts[:], edges=bm.edges[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def lump(rng, center, size, n=14, taper=0.0, lean=(0.0, 0.0), zmin=0.0, rr=(0.6, 1.0), mesa=0.82):
    """An angular boulder: hull of a few random points in an ellipsoid (size = half extents), its base at
    center z, flattened where it meets zmin, cut flat on top at `mesa` of its height, narrowing by `taper`
    and leaning by `lean` toward its top."""
    pts = []
    top = center[2] + 2 * size[2] * mesa
    for _ in range(n):
        d = rand_dir(rng) * rng.uniform(*rr)
        x, y, z = d.x * size[0], d.y * size[1], d.z * size[2]
        t = (d.z + 1) / 2
        x, y = x * (1 - taper * t) + lean[0] * t, y * (1 - taper * t) + lean[1] * t
        pts.append(Vector((center[0] + x, center[1] + y, min(top, max(zmin, center[2] + z + size[2])))))
    return hull(pts)


def chunk(rng, base, z0, z1, r0, r1, squash=1.0, apex=False, tilt=0.35):
    """A segment of a crooked pillar: an irregular 5-7 sided prism (basalt-like) from z0 (radius r0) to z1
    (radius r1) with a tilted top facet, or a pointed tip when `apex`."""
    k = rng.randint(5, 7)
    phi = rng.uniform(0, 2 * math.pi)
    t = tilt * rng.uniform(0.4, 1.0)
    pts = []
    for i in range(k):
        a = 2 * math.pi * (i + rng.uniform(-0.25, 0.25)) / k
        q = rng.uniform(0.72, 1.0)
        c, s_ = math.cos(a) * q, math.sin(a) * q * squash
        pts.append(Vector((base[0] + r0 * c, base[1] + r0 * s_, z0)))
        pts.append(Vector((base[0] + r1 * c, base[1] + r1 * s_, z1 + t * r1 * math.cos(a - phi))))
    if apex:
        pts.append(Vector((base[0] + rng.uniform(-0.2, 0.2) * r1, base[1] + rng.uniform(-0.2, 0.2) * r1, z1 + r1 * rng.uniform(0.7, 1.1))))
    return hull(pts, angle=2.0)


def paint_rock(bm, rng, seed, lichen=0.22, mat=0, tones=False):
    """Rock UVs: v from the height; each facet picks the slate or lighter column, or lichen on up-facing
    facets where a noise says so. With tones=True a facet's material index (0 or 1, set per chunk) says
    which of the two slate columns it mostly keeps."""
    uv = uv_layer(bm)
    off = Vector((seed * 3.1, seed * 1.7, seed * 0.9))
    for f in bm.faces:
        tone = f.material_index if tones else (0 if rng.random() < 0.6 else 1)
        f.material_index = mat
        c = f.calc_center_median()
        up = f.normal.z
        n = noise.noise(c * 0.9 + off)
        if up > 0.45 and n > 0.35 - lichen:
            ci = 2 if rng.random() < 0.55 else 3
        else:
            ci = tone if rng.random() < 0.8 else 1 - tone
        for lp in f.loops:
            lp[uv].uv = col_uv(ci, 4, lp.vert.co.z / ROCK_V_SCALE)


# --- crystals ---------------------------------------------------------------------------------------------

def spike(rng, r, h, cols=(0, 1), chamfer=0.17, waist=1.08, taper=0.86, tipf=0.24):
    """A hexagonal crystal with chamfered edges (12 faces, wide and narrow) and an off-centre pyramid tip,
    standing on +Z from just below 0. UV v follows height so the gradient runs amber to pale gold."""
    bm = bmesh.new()
    uv = uv_layer(bm)
    sec = []
    for i in range(6):
        a = math.pi / 3 * i
        c = Vector((math.cos(a), math.sin(a)))
        pv = Vector((math.cos(a - math.pi / 3), math.sin(a - math.pi / 3)))
        nx = Vector((math.cos(a + math.pi / 3), math.sin(a + math.pi / 3)))
        sec += [c.lerp(pv, chamfer) * r, c.lerp(nx, chamfer) * r]
    levels = [(-0.30, 0.94), (h * rng.uniform(0.38, 0.5), waist), (h * (1 - tipf), taper)]
    rings = [[bm.verts.new((p.x * s, p.y * s, z)) for p in sec] for z, s in levels]
    a = rng.uniform(0, 2 * math.pi)
    apex = bm.verts.new((math.cos(a) * r * 0.22, math.sin(a) * r * 0.22, h))
    faces = []
    for ra, rb in zip(rings, rings[1:]):
        for j in range(12):
            k = (j + 1) % 12
            faces.append((bm.faces.new((ra[j], ra[k], rb[k], rb[j])), j % 2))
    for j in range(12):
        faces.append((bm.faces.new((rings[-1][j], rings[-1][(j + 1) % 12], apex)), j % 2))
    faces.append((bm.faces.new(rings[0][::-1]), 1))
    for f, kind in faces:
        ci = cols[0] if kind == 1 else cols[1]          # odd j: p2_i -> p1_i+1, the wide face
        for lp in f.loops:
            lp[uv].uv = col_uv(ci, 4, lp.vert.co.z / h)
    return bm


# (x, y, height, radius, lean degrees, lean heading offset degrees); headings point away from the middle
CLUSTERS = {
    "crystal_a": dict(seed=11, spikes=[
        (0.00, 0.02, 2.00, 0.21, 5, 0), (-0.30, -0.08, 1.45, 0.17, 17, 0), (0.30, 0.08, 1.55, 0.18, 15, 0),
        (-0.50, 0.12, 0.95, 0.14, 30, 0), (0.52, -0.10, 1.00, 0.14, 28, 0), (0.10, -0.22, 0.80, 0.12, 34, 0),
        (-0.12, 0.24, 0.85, 0.12, 32, 0)],
        base=[((0.0, 0.0), (0.72, 0.36, 0.17)), ((-0.42, 0.05), (0.38, 0.30, 0.13)), ((0.45, -0.04), (0.36, 0.28, 0.12))]),
    "crystal_b": dict(seed=23, spikes=[
        (-0.38, 0.00, 1.60, 0.19, 8, 0), (-0.62, 0.10, 1.10, 0.15, 24, 0), (-0.20, -0.18, 1.05, 0.14, 22, -20),
        (-0.42, 0.24, 0.70, 0.11, 34, 0), (0.42, 0.04, 1.25, 0.17, 10, 0), (0.62, -0.12, 0.85, 0.13, 28, 0),
        (0.24, 0.18, 0.80, 0.12, 26, 30), (0.08, -0.06, 0.55, 0.10, 30, 0), (0.70, 0.20, 0.45, 0.09, 40, 0)],
        base=[((-0.40, 0.02), (0.48, 0.36, 0.15)), ((0.45, 0.0), (0.42, 0.32, 0.13)), ((0.02, 0.0), (0.30, 0.26, 0.09))]),
    "crystal_c": dict(seed=37, spikes=[
        (0.05, 0.00, 2.10, 0.25, 4, 0), (-0.38, 0.05, 1.50, 0.21, 20, 0), (0.42, -0.06, 1.30, 0.20, 22, 0),
        (-0.05, -0.24, 0.85, 0.15, 34, 0), (0.12, 0.24, 0.95, 0.15, 30, 0), (-0.62, -0.10, 0.55, 0.11, 46, 0)],
        base=[((0.0, 0.0), (0.66, 0.40, 0.20)), ((0.35, 0.12), (0.34, 0.26, 0.14))]),
    "crystal_d": dict(seed=51, spikes=[
        (-0.15, 0.00, 1.45, 0.18, 12, 0), (0.18, 0.06, 1.30, 0.17, 18, 0), (-0.48, -0.08, 0.95, 0.14, 36, 0),
        (0.52, -0.02, 1.00, 0.15, 38, 0), (-0.05, -0.24, 0.75, 0.13, 42, 0), (0.06, 0.26, 0.70, 0.12, 44, 0),
        (-0.72, 0.16, 0.42, 0.09, 55, 0), (0.78, 0.18, 0.40, 0.09, 58, 0)],
        base=[((0.0, 0.0), (0.62, 0.34, 0.14)), ((-0.48, 0.0), (0.34, 0.26, 0.11)), ((0.52, 0.04), (0.34, 0.26, 0.11))]),
}


def crystal(uid, mats):
    spec = CLUSTERS[uid]
    rng = random.Random(spec["seed"])
    bm = bmesh.new()
    uv_layer(bm)
    for i, (x, y, h, r, lean, dh) in enumerate(spec["spikes"]):
        cols = (2, 3) if rng.random() < 0.3 else (0, 1)
        r *= 1.25
        s = spike(rng, r, h, cols)
        for f in s.faces:
            f.material_index = 0
        heading = math.atan2(y * 2.2, x) if (abs(x) + abs(y)) > 1e-6 else rng.uniform(0, 6.28)
        heading += math.radians(dh + rng.uniform(-12, 12))
        M = (Matrix.Translation((x, y, 0.02 + r * math.sin(math.radians(lean)))) @ Matrix.Rotation(heading, 4, "Z") @ Matrix.Rotation(math.radians(lean), 4, "Y")
             @ Matrix.Rotation(rng.uniform(0, 6.28), 4, "Z"))
        bmesh.ops.transform(s, matrix=M, verts=s.verts)
        merge(bm, s)
    for j, ((x, y), size) in enumerate(spec["base"]):
        size = (size[0] * 1.15, size[1] * 1.2, size[2] * 1.9)
        rk = lump(rng, (x, y, -size[2] * 0.35), size, n=22, taper=0.35)
        paint_rock(rk, rng, spec["seed"] + j, lichen=0.12, mat=1)
        merge(bm, rk)
    # a collar of slate rocks round the roots, so the gold sits in dark stone and reads from far away
    n_ring = 7
    for j in range(n_ring):
        a = 2 * math.pi * (j + rng.uniform(-0.2, 0.2)) / n_ring
        x, y = math.cos(a) * rng.uniform(0.58, 0.70), math.sin(a) * rng.uniform(0.28, 0.36)
        size = (rng.uniform(0.26, 0.34), rng.uniform(0.18, 0.24), rng.uniform(0.15, 0.21))
        rk = lump(rng, (x, y, -size[2] * 0.3), size, n=14, taper=0.35)
        paint_rock(rk, rng, spec["seed"] + 20 + j, lichen=0.35, mat=1)
        merge(bm, rk)
    # a few loose pebbles on the ground round the base
    for _ in range(3):
        a = rng.uniform(0, 2 * math.pi)
        x, y = math.cos(a) * rng.uniform(0.75, 0.95), math.sin(a) * rng.uniform(0.32, 0.42)
        rk = lump(rng, (x, y, -0.03), (0.09, 0.08, 0.05), n=10)
        paint_rock(rk, rng, spec["seed"] + 9, lichen=0.0, mat=1)
        merge(bm, rk)
    # cut everything off at the ground (the spikes' buried roots), then keep the footprint about 2 x 1 m
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, 0), plane_no=(0, 0, 1),
                           clear_inner=True)
    lo = Vector([min(v.co[i] for v in bm.verts) for i in range(3)])
    hi = Vector([max(v.co[i] for v in bm.verts) for i in range(3)])
    fx, fy = min(1.0, 2.1 / (hi.x - lo.x)), min(1.0, 1.15 / (hi.y - lo.y))
    bmesh.ops.transform(bm, matrix=Matrix.Diagonal((fx, fy, 1, 1)) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, 0)),
                        verts=bm.verts)
    return to_object(uid, bm, [mats["glow_crystal"], mats["rock"]])


# --- slime ------------------------------------------------------------------------------------------------

def slime_pile(mats, segs=40, rings=12):
    rng = random.Random(7)
    R0, H = 1.20, 0.62
    tongues = [(0.6, 0.20, 0.20), (2.4, 0.16, 0.16), (4.1, 0.22, 0.18), (5.4, 0.14, 0.13)]
    lumps = [(0.22, 0.12, 0.17, 0.45), (-0.42, 0.28, 0.12, 0.40), (0.10, -0.48, 0.10, 0.36), (-0.30, -0.30, 0.07, 0.30)]

    def rim(th):
        r = R0 + 0.09 * math.sin(3 * th + 0.7) + 0.05 * math.sin(5 * th + 2.1) + 0.04 * math.sin(7 * th + 0.3)
        for a0, w, amp in tongues:
            d = (th - a0 + math.pi) % (2 * math.pi) - math.pi
            r += amp * math.exp(-(d / w) ** 2)
        return r

    def height(x, y, rho):
        z = H * max(0.0, 1 - rho ** 2.4) ** 0.55
        for lx, ly, amp, sg in lumps:
            z += amp * math.exp(-((x - lx) ** 2 + (y - ly) ** 2) / sg ** 2) * max(0.0, 1 - rho ** 3)
        return z

    def surf(x, y):
        th = math.atan2(y, x)
        rho = math.hypot(x, y) / rim(th)
        return height(x, y, min(rho, 1.0))

    bm = bmesh.new()
    uv = uv_layer(bm)
    apex = bm.verts.new((0, 0, height(0, 0, 0)))
    grid = []
    for i in range(1, rings + 1):
        rho = 1 - (1 - i / rings) ** 1.25
        row = []
        for j in range(segs):
            th = 2 * math.pi * j / segs + (0.5 * math.pi / segs if i % 2 else 0.0)
            R = rim(th) * rho
            x, y = R * math.cos(th), R * math.sin(th)
            row.append(bm.verts.new((x, y, height(x, y, rho))))
        grid.append(row)
    cells = {}
    for j in range(segs):
        bm.faces.new((apex, grid[0][j], grid[0][(j + 1) % segs]))
    for i in range(rings - 1):
        for j in range(segs):
            k = (j + 1) % segs
            cells[(i + 1, j)] = bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][k], grid[i][k]))
    for f in bm.faces:
        f.smooth = True
        f.material_index = 0

    def normal_at(x, y, e=0.02):
        return Vector((surf(x - e, y) - surf(x + e, y), surf(x, y - e) - surf(x, y + e), 2 * e)).normalized()

    # the cracks: thin glowing fissures that wander down from near the top, tapering at both ends
    def fissure(pts, width):
        n = len(pts)
        left, right = [], []
        for i, (x, y) in enumerate(pts):
            a_, b_ = pts[max(0, i - 1)], pts[min(n - 1, i + 1)]
            tx, ty = b_[0] - a_[0], b_[1] - a_[1]
            tl = math.hypot(tx, ty) or 1.0
            px, py = -ty / tl, tx / tl
            w = width * math.sin(math.pi * (i + 0.5) / n) ** 0.6
            nz = normal_at(x, y)
            for side, lst in ((1, left), (-1, right)):
                qx, qy = x + px * w * side, y + py * w * side
                lst.append(bm.verts.new(Vector((qx, qy, surf(qx, qy))) + nz * 0.012))
        for i in range(n - 1):
            f = bm.faces.new((left[i], right[i], right[i + 1], left[i + 1]))
            if f.normal.z < 0:
                f.normal_flip()
            f.smooth, f.material_index = True, 1

    def wander(r0, r1, th0, bend, steps=14):
        pts = []
        for i in range(steps):
            t = i / (steps - 1)
            th = th0 + bend * math.sin(t * 2.4) + 0.05 * math.sin(t * 17 + th0 * 5)
            rr = (r0 + (r1 - r0) * t) * rim(th)
            pts.append((rr * math.cos(th), rr * math.sin(th)))
        return pts
    for r0, r1, th0, bend, w in ((0.10, 0.82, 0.35, 0.25, 0.034), (0.18, 0.86, 1.95, -0.30, 0.03),
                                 (0.08, 0.80, 3.30, 0.22, 0.034), (0.20, 0.84, 4.70, -0.25, 0.03),
                                 (0.42, 0.78, 5.70, 0.20, 0.022), (0.45, 0.80, 2.70, 0.18, 0.02)):
        fissure(wander(r0, r1, th0, bend), w)
    # bubbles on the surface, droplets on the ground beyond the rim
    for x, y, r in ((0.35, -0.10, 0.13), (-0.20, 0.45, 0.10), (0.62, 0.38, 0.08), (-0.55, -0.15, 0.11), (0.05, 0.62, 0.06),
                    (0.25, -0.65, 0.07)):
        b = V.lathe([(0, -0.3), (0.97, -0.25), (0.92, 0.38), (0.6, 0.8), (0, 1.0)], 10)
        V.xf(b, (x, y, surf(x, y) - 0.2 * r), (0, 0, 0), (r, r, r * 0.85))
        merge(bm, b, smooth=True)
    for th, d, r in ((0.6, 1.62, 0.07), (2.45, 1.50, 0.06), (4.15, 1.58, 0.08), (5.45, 1.42, 0.05), (1.5, 1.38, 0.05)):
        b = V.lathe([(0, 0), (0.9, 0), (1.0, 0.25), (0.7, 0.6), (0, 0.72)], 10)
        V.xf(b, (math.cos(th) * d, math.sin(th) * d, 0), (0, 0, 0), (r, r, r))
        merge(bm, b, smooth=True)
    for f in bm.faces:
        for lp in f.loops:
            lp[uv].uv = ((lp.vert.co.x + 1.6) / 3.2, (lp.vert.co.y + 1.6) / 3.2)
    ob = to_object("slime_pile", bm, [mats["slime"], mats["glow_slime"]])
    return ob


# --- rocks ------------------------------------------------------------------------------------------------

def pillar(rng, x, y, height, r, segs=3, lean=(0.0, 0.0), squash=1.0):
    """A crooked, segmented alien pillar: stacked hull chunks, each shifted along the lean."""
    out = []
    z = 0.0
    bx, by = x, y
    prev = r
    for s in range(segs):
        z1 = height * (s + 1) / segs
        r0 = prev * (rng.uniform(0.9, 0.98) if s else 1.0)          # each segment steps in, never overhangs
        r1 = r0 * (0.6 if s == segs - 1 else rng.uniform(0.86, 0.95))
        prev = r1
        last = s == segs - 1
        out.append(chunk(rng, (bx, by), max(0.0, z - 0.08), z1 - (0.25 * r1 if last else 0.0), r0, r1, squash=squash,
                         apex=last and rng.random() < 0.7))
        bx += lean[0] * height / segs + rng.uniform(-0.06, 0.06)
        by += lean[1] * height / segs + rng.uniform(-0.06, 0.06)
        z = z1
    return out


ROCKS = {
    # footprint (x, y) and height the finished rock is scaled to (a little inside the brief's footprint)
    "rock_a": dict(seed=101, size=(2.85, 2.85, 2.3)),
    "rock_b": dict(seed=202, size=(3.85, 1.9, 1.7)),
    "rock_c": dict(seed=303, size=(4.85, 2.85, 2.9)),
}


def rock(uid, mats):
    spec = ROCKS[uid]
    rng = random.Random(spec["seed"])
    parts = []
    if uid == "rock_a":
        parts += pillar(rng, 0.15, 0.05, 2.3, 0.62, 3, (0.10, 0.05))
        parts += pillar(rng, -0.65, 0.45, 1.45, 0.42, 2, (-0.16, 0.10))
        parts.append(lump(rng, (-0.55, -0.35, 0.0), (0.62, 0.55, 0.45), taper=0.3))
        parts.append(lump(rng, (0.55, -0.55, 0.0), (0.45, 0.42, 0.32), taper=0.2))
        parts.append(lump(rng, (-0.35, 0.65, 0.0), (0.55, 0.45, 0.38), taper=0.25, lean=(-0.1, 0.1)))
        parts.append(lump(rng, (0.75, 0.55, 0.0), (0.32, 0.30, 0.22)))
        for x, y in ((-1.15, 0.1), (1.15, -0.1), (0.1, -1.15)):
            parts.append(lump(rng, (x, y, 0.0), (0.18, 0.16, 0.1), n=10))
    elif uid == "rock_b":
        for x, h, r, ln in ((-1.15, 1.25, 0.48, (-0.12, 0.02)), (-0.25, 1.7, 0.55, (0.04, -0.05)), (0.75, 1.35, 0.5, (0.14, 0.04))):
            parts += pillar(rng, x, rng.uniform(-0.1, 0.1), h, r, 2, ln, squash=0.75)
        parts.append(lump(rng, (0.0, 0.0, 0.0), (1.55, 0.62, 0.30), taper=0.3))
        parts.append(lump(rng, (1.45, 0.25, 0.0), (0.40, 0.35, 0.25)))
        parts.append(lump(rng, (-1.6, -0.3, 0.0), (0.32, 0.30, 0.18)))
        for x, y in ((0.4, 0.75), (-0.7, -0.72), (1.75, -0.35)):
            parts.append(lump(rng, (x, y, 0.0), (0.16, 0.14, 0.09), n=10))
    else:
        parts += pillar(rng, -0.9, 0.1, 2.9, 0.75, 3, (0.12, -0.04))
        parts += pillar(rng, 0.85, -0.2, 2.2, 0.62, 3, (-0.10, 0.06))
        parts += pillar(rng, 1.75, 0.45, 1.3, 0.42, 2, (0.10, 0.08))
        parts.append(lump(rng, (0.0, 0.0, 0.0), (2.0, 1.05, 0.45), n=26, taper=0.35))
        parts.append(lump(rng, (-1.9, -0.6, 0.0), (0.55, 0.48, 0.35), taper=0.2))
        parts.append(lump(rng, (0.1, 0.95, 0.0), (0.6, 0.42, 0.42), taper=0.25))
        parts.append(lump(rng, (-0.1, -0.95, 0.0), (0.5, 0.40, 0.30)))
        for x, y in ((2.2, -0.6), (-2.25, 0.55), (1.0, 1.25), (-1.0, -1.25)):
            parts.append(lump(rng, (x, y, 0.0), (0.2, 0.18, 0.12), n=10))
    bm = bmesh.new()
    uv_layer(bm)
    for i, p in enumerate(parts):
        tone = rng.choice((0, 1))                 # each chunk keeps one tone, so pillars read as strata
        for f in p.faces:
            f.material_index = tone
        merge(bm, p)
    # fit the footprint and height exactly, centred
    lo = Vector([min(v.co[i] for v in bm.verts) for i in range(3)])
    hi = Vector([max(v.co[i] for v in bm.verts) for i in range(3)])
    sx, sy, sz = (spec["size"][i] / (hi[i] - lo[i]) for i in range(3))
    M = Matrix.Diagonal((sx, sy, sz, 1)) @ Matrix.Translation((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    bm.normal_update()
    paint_rock(bm, rng, spec["seed"], lichen=0.12, mat=0, tones=True)
    for f in bm.faces:
        f.material_index = 0
    return to_object(uid, bm, [mats["rock"]])


# --- build, review --------------------------------------------------------------------------------------

def make_materials():
    mats = {}
    mats["glow_crystal"] = tex_mat("glow_crystal", column_image("crystal_gradient", CRYSTAL_COLS), 0.18, 0.0, CRYSTAL_EMIT)
    mats["rock"] = tex_mat("rock", column_image("rock_gradient", ROCK_COLS), 0.85)
    mats["slime"] = tex_mat("slime", slime_image(), 0.08, 0.0)
    mats["glow_slime"] = V.flat("glow_slime", "#4FBF2A", 0.3, 0.0, SLIME_GLOW, 0.9)
    return mats


def review(uid, objs, rnd):
    cam, ground, bg = V.stage()
    pts = V.world_points(objs, 3000)
    out = os.path.join(HERE, "review", "round%d" % rnd)
    shots = []
    ground.hide_render = True
    icon = None
    if uid not in NO_ICON:
        V.fit(cam, pts, 35, 26, 0.04)
        icon = os.path.join(V.ICONS, uid + ".png")
        V.render(icon, (256, 256), True)
    V.fit(cam, pts, 35, 24, 0.08)
    shots.append(os.path.join(out, uid + "_front.png"))
    V.render(shots[-1], (512, 512), False)
    V.fit(cam, pts, -140, 30, 0.08)
    shots.append(os.path.join(out, uid + "_back.png"))
    V.render(shots[-1], (512, 512), False)
    ground.hide_render = False
    cam.data.lens_unit, cam.data.sensor_fit = "FOV", "VERTICAL"
    cam.data.angle = math.radians(45)
    cam.data.shift_x = cam.data.shift_y = 0.0
    tgt = Vector((0, 0, 0.5))
    cam.location = tgt + V.view_dir(-25, 55) * 25
    V.look(cam, tgt)
    shots.append(os.path.join(out, uid + "_game.png"))
    V.render(shots[-1], (512, 512), False)
    V.sheet(shots + ([icon] if icon else []), os.path.join(out, uid + "_sheet.png"))


def build(uid, rnd, do_render):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats = make_materials()
    if uid.startswith("crystal"):
        ob = crystal(uid, mats)
    elif uid == "slime_pile":
        ob = slime_pile(mats)
    else:
        ob = rock(uid, mats)
    V.settle([ob])
    path = os.path.join(V.MODELS, uid + ".glb")
    V.export([ob], path)
    pts = V.world_points([ob])
    info = {"id": uid, "triangles": V.tris(ob),
            "size_m": [round(max(p[i] for p in pts) - min(p[i] for p in pts), 3) for i in range(3)],
            "min_z": round(min(p.z for p in pts), 4), "glb_bytes": os.path.getsize(path),
            "materials": [m.name for m in ob.data.materials], "origin": list(ob.location)}
    print("[shardfall]", json.dumps(info))
    os.makedirs(os.path.join(HERE, "review"), exist_ok=True)
    with open(os.path.join(HERE, "review", uid + "_stats.json"), "w") as f:
        json.dump(info, f, indent=1)
    if do_render:
        review(uid, [ob], rnd)


def lineup(rnd):
    """Every finished GLB on one patch of ground under the game camera, for judging them side by side."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    place = {"crystal_a": (-3.0, 2.2, 10), "crystal_b": (0.0, 2.6, -15), "crystal_c": (3.0, 2.2, 25), "crystal_d": (6.0, 2.4, 0),
             "slime_pile": (-6.0, -1.5, 0), "rock_a": (-8.0, 4.5, 0), "rock_b": (1.5, 6.5, 0), "rock_c": (8.5, 6.0, 0),
             "ambron_scorcher": (-1.5, -1.5, 30), "ambron_hailfire": (1.5, -2.0, -20), "ambron_dart": (4.0, -2.5, 0),
             "ambron_monolith": (7.0, -1.0, 10)}
    objs = []
    for uid, (x, y, rz) in place.items():
        path = os.path.join(V.MODELS, uid + ".glb")
        if not os.path.exists(path):
            continue
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=path)
        new = [o for o in bpy.data.objects if o not in before]
        lift = V.AIR.get(uid, 0.0)
        for o in new:
            if o.parent is None:
                o.location = Vector((x, y, lift)) + o.location
                o.rotation_euler.z += math.radians(rz)
        objs += new
    cam, ground, bg = V.stage()
    cam.data.lens_unit, cam.data.sensor_fit = "FOV", "VERTICAL"
    cam.data.angle = math.radians(45)
    tgt = Vector((0, 1.5, 0.5))
    for dist, name in ((25, "lineup_game.png"), (18, "lineup_near.png"), (40, "lineup_far.png")):
        cam.location = tgt + V.view_dir(0, 55) * dist
        V.look(cam, tgt)
        V.render(os.path.join(HERE, "review", "round%d" % rnd, name), (1024, 576), False)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    which = argv[0] if argv else "all"
    rnd = int(argv[argv.index("--round") + 1]) if "--round" in argv else 1
    if which == "lineup":
        lineup(rnd)
        return
    for uid in (IDS if which == "all" else [which]):
        if uid not in IDS:
            raise SystemExit("unknown id " + uid)
        build(uid, rnd, "--no-render" not in argv)


if __name__ == "__main__":
    main()
