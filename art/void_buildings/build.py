"""Void structures for Shardfall: the seven grown buildings of the Void swarm (docs/ART_SPEC.md).

Every building is grown, not built: a flesh mass (metaballs or a lathe, displaced with noise), overlapping
chitin plates (curved, pointed, solid shells with bone-coloured rims and hooked tips), curved bone spikes
and teeth (swept, tapering, bent cones), glowing green sacs, and a flat dark creep mat round the base.
The look follows art/ref/void_style_reference.png: glossy purple chitin, bone hooks fading to a darker
base, crimson ribbed flesh in the gaps, acid-green sacs.

Colour is painted by procedural Cycles shaders (one per part kind), baked to one shared colour,
roughness and normal atlas per building on a Smart UV unwrap, and packed into the GLB as JPEG.

    Blender --background --factory-startup --python-exit-code 1 --python art/void_buildings/build.py -- <id|all> [--fast] [--round NAME] [--lineup]

--fast      shape pass only: flat colours, no bake, no export, renders into review/fast/
--round     review subfolder name for this pass (default "latest")
--lineup    also render all seven exported GLBs side by side from the game camera

Writes assets/models/<id>.glb, assets/icons/<id>.png, review renders in art/void_buildings/review/<round>/,
baked textures in art/void_buildings/cache/ (ignored by git). Front faces -Y, origin at the ground centre,
1 unit = 1 m.
"""
import math
import os
import random
import sys
import time

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector, noise
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MODELS = os.path.join(ROOT, "assets", "models")
ICONS = os.path.join(ROOT, "assets", "icons")
REVIEW = os.path.join(HERE, "review")
CACHE = os.path.join(HERE, "cache")
TEX = int(os.environ.get("VOID_TEX", 1024))

UP = Vector((0, 0, 1))
DOWN = Vector((0, 0, -1))


# --- colour ---------------------------------------------------------------------------------------

def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hexc(h, a=1.0):
    h = h.lstrip("#")
    return tuple(_lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4)) + (a,)


BASE_PAL = {
    # chitin (spec: #4A2A63 to #6B3C8A, highlights #8E5BB0)
    "chitin_dark": "#4A2A63", "chitin": "#6B3C8A", "chitin_hi": "#8E5BB0", "chitin_deep": "#24112E",
    # bone (spec: #D8C8A8 fading to #9C8A6A at the base)
    "bone": "#D8C8A8", "bone_base": "#9C8A6A", "bone_dark": "#7E6D52", "bone_deep": "#4A3D2E",
    # flesh (spec: #5E1A2A to #8A2C3C)
    "flesh_dark": "#5E1A2A", "flesh": "#8A2C3C", "flesh_hi": "#A8465A", "flesh_deep": "#2A0812",
    # glow (spec: #8CFF3A)
    "glow": "#8CFF3A", "glow_mid": "#62D622", "glow_hi": "#D4FFA0", "glow_vein": "#1F4A0A",
    # creep: dark organic root mat
    "creep_dark": "#120A17", "creep": "#22132B", "creep_hi": "#3A2350", "creep_vein": "#4E1630",
    # egg membrane (pod)
    "memb_a": "#B7C98A", "memb_b": "#E4E9BE", "memb_vein": "#6A1F36",
}
PAL_OVERRIDE = {
    # the Abyssal Lair is the ominous one: darker chitin, same family
    "void_abyss": {"chitin_dark": "#2E1A40", "chitin": "#4A2A63", "chitin_hi": "#734398", "chitin_deep": "#140818"},
}
TEAM_GREY = "#C8C8C8"
STATE = {}  # values a builder hands to produce() (e.g. the pod core pivot)


def palette(bid):
    p = dict(BASE_PAL)
    p.update(PAL_OVERRIDE.get(bid, {}))
    return {k: hexc(v) for k, v in p.items()}


# --- small maths ----------------------------------------------------------------------------------

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def sstep(e0, e1, x):
    t = clamp((x - e0) / (e1 - e0))
    return t * t * (3 - 2 * t)


def radial(th):
    return Vector((math.cos(th), math.sin(th), 0.0))


def angdiff(a, b):
    return (a - b + math.pi) % (2 * math.pi) - math.pi


def frame(p, along, out):
    """A matrix whose local X runs across, Y along `along`, Z out of the surface, origin at p."""
    Z = Vector(out).normalized()
    a = Vector(along)
    Y = a - Z * a.dot(Z)
    if Y.length < 1e-5:
        Y = Z.orthogonal()
    Y.normalize()
    X = Y.cross(Z)
    M = Matrix((X, Y, Z)).transposed().to_4x4()
    M.translation = Vector(p)
    return M


def catmull(ctrl, per=4):
    pts = [Vector(c) for c in ctrl]
    P = [pts[0] + (pts[0] - pts[1])] + pts + [pts[-1] + (pts[-1] - pts[-2])]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(per):
            t = k / per
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1])
    return out


# --- scene and mesh plumbing ----------------------------------------------------------------------

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.metaballs):
        for d in list(coll):
            coll.remove(d)


def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def set_attr(ob, name, vals=None):
    me = ob.data
    a = me.attributes.get(name)
    if a is None:
        a = me.attributes.new(name, "FLOAT", "POINT")
        if vals is None:
            vals = [0.0] * len(me.vertices)
    if vals is not None:
        a.data.foreach_set("value", [float(v) for v in vals])


def mesh_obj(name, verts, faces, kind, along=None, rim=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    ob = link(bpy.data.objects.new(name, me))
    ob["kind"] = kind
    set_attr(ob, "along", along)
    set_attr(ob, "rim", rim)
    return ob


def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def apply_modifiers(ob):
    ob.data.update()
    ob.update_tag(refresh={"OBJECT", "DATA"})
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    bpy.data.meshes.remove(old)


def decimate(ob, ratio):
    if ratio >= 0.999:
        return
    m = ob.modifiers.new("dec", "DECIMATE")
    m.ratio = max(0.02, ratio)
    m.use_collapse_triangulate = True
    apply_modifiers(ob)


def ground_cut(ob):
    me = ob.data
    if min(v.co.z for v in me.vertices) >= -1e-4:
        return
    bm = bmesh.new()
    bm.from_mesh(me)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, 0), plane_no=(0, 0, 1), clear_inner=True, dist=1e-5)
    for v in bm.verts:
        if v.co.z < 0:
            v.co.z = 0.0
    bm.to_mesh(me)
    bm.free()
    me.update()


def orient_outward(ob):
    """Flips a part whose faces wind inward (signed volume about the ground plane < 0)."""
    me = ob.data
    vol = 0.0
    co = [v.co for v in me.vertices]
    for p in me.polygons:
        vs = p.vertices
        a = co[vs[0]]
        for i in range(1, len(vs) - 1):
            vol += a.dot(co[vs[i]].cross(co[vs[i + 1]]))
    if vol < 0:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        bm.to_mesh(me)
        bm.free()
        me.update()
        return True
    return False


def bvh_of(ob):
    me = ob.data
    return BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [p.vertices[:] for p in me.polygons])


def cast(bvh, origin, direction):
    o = Vector(origin)
    d = Vector(direction).normalized()
    loc, nrm, _i, _d = bvh.ray_cast(o, d)
    if loc is None:
        return None
    if nrm.dot(d) > 0:
        nrm = -nrm
    return loc, nrm


def cast_in(bvh, target, dirvec, far=14.0):
    """Hits the surface coming in from far out along `dirvec` toward `target`."""
    d = Vector(dirvec).normalized()
    return cast(bvh, Vector(target) + d * far, -d)


def sph(th, el):
    return Vector((math.cos(el) * math.cos(th), math.cos(el) * math.sin(th), math.sin(el)))


# --- shape generators -----------------------------------------------------------------------------

def sweep(name, pts, radii, kind, ring=8, flat=1.0, side=None, closed=False, cap0=True, cap1=True,
          shape=None, rimfn=None, along=None):
    """A tube along `pts` with a radius per point (0 at the end makes a point). `flat` squashes the
    section across `side` (the section's wide axis starts along `side`)."""
    P = [Vector(p) for p in pts]
    n = len(P)
    T = []
    for i in range(n):
        if closed:
            t = P[(i + 1) % n] - P[(i - 1) % n]
        elif i == 0:
            t = P[1] - P[0]
        elif i == n - 1:
            t = P[-1] - P[-2]
        else:
            t = P[i + 1] - P[i - 1]
        T.append(t.normalized())
    ref = Vector(side) if side is not None else Vector((0, 0, 1))
    N = ref - T[0] * ref.dot(T[0])
    if N.length < 1e-5:
        N = T[0].orthogonal()
    N.normalize()
    Ns = [N]
    for i in range(1, n):  # rotation-minimising frames (double reflection)
        v1 = P[i] - P[i - 1]
        c1 = v1.dot(v1)
        if c1 < 1e-12:
            Ns.append(Ns[-1].copy())
            continue
        rL = Ns[-1] - (2 / c1) * v1.dot(Ns[-1]) * v1
        tL = T[i - 1] - (2 / c1) * v1.dot(T[i - 1]) * v1
        v2 = T[i] - tL
        c2 = v2.dot(v2)
        r = rL - (2 / c2) * v2.dot(rL) * v2 if c2 > 1e-12 else rL
        r = r - T[i] * r.dot(T[i])
        Ns.append(r.normalized())
    tip = (not closed) and radii[-1] <= 1e-6
    nring = n - 1 if tip else n
    verts, al, rv = [], [], []
    for i in range(nring):
        Bv = T[i].cross(Ns[i])
        t = along[i] if along else i / (n - 1)
        for k in range(ring):
            a = 2 * math.pi * k / ring
            m = shape(a, t) if shape else 1.0
            off = Ns[i] * (math.cos(a) * radii[i] * m) + Bv * (math.sin(a) * radii[i] * m * flat)
            verts.append(P[i] + off)
            al.append(t)
            rv.append(rimfn(a, t) if rimfn else 0.0)
    faces = []
    segs = nring if closed else nring - 1
    for i in range(segs):
        i2 = (i + 1) % nring
        for k in range(ring):
            k1 = (k + 1) % ring
            faces.append((i * ring + k, i * ring + k1, i2 * ring + k1, i2 * ring + k))
    if tip:
        verts.append(P[-1])
        al.append(along[-1] if along else 1.0)
        rv.append(rimfn(0.0, 1.0) if rimfn else 0.0)
        ti = len(verts) - 1
        b = (nring - 1) * ring
        for k in range(ring):
            faces.append((b + k, b + (k + 1) % ring, ti))
    elif not closed and cap1:
        b = (nring - 1) * ring
        faces.append(tuple(b + k for k in range(ring)))
    if not closed and cap0:
        faces.append(tuple(reversed(range(ring))))
    return mesh_obj(name, verts, faces, kind, al, rv)


def horn_path(base, d, length, curl_to, bend, segs, power=1.3):
    d = Vector(d).normalized()
    c = Vector(curl_to)
    axis = d.cross(c)
    if axis.length < 1e-6:
        axis = d.orthogonal()
    axis.normalize()
    pts = [Vector(base)]
    ds = length / segs
    for k in range(segs):
        t = (k + 0.5) / segs
        dk = Matrix.Rotation(bend * t ** power, 3, axis) @ d
        pts.append(pts[-1] + dk * ds)
    return pts


def horn(name, base, d, length, r0, curl_to, bend, kind="bone", segs=8, ring=8, flat=1.0, power=1.3,
         taper=0.85, rimfn=None):
    """A curved, tapering cone: a bone spike, tooth, claw or tusk."""
    pts = horn_path(base, d, length, curl_to, bend, segs, power)
    radii = [r0 * (1 - i / segs) ** taper for i in range(segs + 1)]
    radii[-1] = 0.0
    return sweep(name, pts, radii, kind, ring=ring, flat=flat, side=Vector(curl_to), rimfn=rimfn)


def plate(name, M, W, L, kind="chitin", thick=0.08, cross=0.3, hook=0.25, bow=0.1, nu=4, nv=6, rim=True,
          conform=None, clear=0.03):
    """A curved, pointed chitin shell: local X across, Y root to tip, Z out of the body. Solid, with
    edges thinner than the middle; `rim` marks the edges and tip for the bone colour."""
    top, bot, rv = [], [], []
    for j in range(nv):
        v = j / (nv - 1)
        w = 0.5 * W * max(0.04, 1 - v ** 1.7) * (0.82 + 0.6 * v * (1 - v))
        for i in range(nu):
            u = -1 + 2 * i / (nu - 1)
            x, y = u * w, v * L
            z = (-cross * 0.5 * W * u * u * (0.35 + 0.65 * (1 - v)) - bow * L * v * v
                 + hook * L * max(0.0, v - 0.45) ** 2 * 3.3)
            th = thick * (1 - 0.55 * u * u) * (1 - 0.55 * v) + 0.008
            top.append(M @ Vector((x, y, z)))
            bot.append(M @ Vector((x * 0.96, y * 0.985, z - th)))
            r = max(abs(u) ** 2.2, (v - 0.55) / 0.45 if v > 0.55 else 0.0) if rim else 0.0
            rv.append(min(1.0, r))
    if conform is not None:
        # drape it: push each top/bottom pair out so the underside clears the body it sits on
        for i in range(len(top)):
            loc, nrm, _idx, _d = conform.find_nearest(bot[i])
            if loc is None:
                continue
            sd = (bot[i] - loc).dot(nrm)
            if sd < clear:
                push = nrm * (clear - sd)
                top[i] = top[i] + push
                bot[i] = bot[i] + push
    verts = top + bot
    rim_all = rv + rv
    al = [0.0] * len(verts)
    ob_ = nu * nv
    faces = []
    for j in range(nv - 1):
        for i in range(nu - 1):
            a = j * nu + i
            faces.append((a, a + 1, a + nu + 1, a + nu))
            faces.append((ob_ + a, ob_ + a + nu, ob_ + a + nu + 1, ob_ + a + 1))
    loop = [i for i in range(nu)] + [j * nu + nu - 1 for j in range(1, nv)] + \
           [(nv - 1) * nu + i for i in range(nu - 2, -1, -1)] + [j * nu for j in range(nv - 2, 0, -1)]
    for k in range(len(loop)):
        a, b = loop[k], loop[(k + 1) % len(loop)]
        faces.append((a, ob_ + a, ob_ + b, b))
    return mesh_obj(name, verts, faces, kind, al, rim_all)


def blob(name, c, r, kind, scale=(1, 1, 1), seg=12, rings=8, lump=0.08, seed=0.0, axis=None, rim=0.0):
    """A lumpy ellipsoid: sacs, eggs, nodules. `axis` turns its local Z to that direction."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    R = Vector(axis).normalized().to_track_quat("Z", "Y").to_matrix() if axis is not None else Matrix.Identity(3)
    off = Vector((seed * 3.17, seed * 1.31, seed * 0.71))
    for v in bm.verts:
        p = v.co.copy()
        d = 1 + lump * noise.noise(p * 1.6 + off)
        q = Vector((p.x * scale[0], p.y * scale[1], p.z * scale[2])) * (r * d)
        v.co = R @ q + Vector(c)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = link(bpy.data.objects.new(name, me))
    ob["kind"] = kind
    set_attr(ob, "along")
    set_attr(ob, "rim", [rim] * len(me.vertices))
    return ob


def lathe(name, prof, kind, seg=28, square=0.0, sq_top=0.6, shear=0.0, lump=0.0, lump_f=1.5, seed=0.0,
          center=(0.0, 0.0)):
    """A surface of revolution from (r, z) pairs (last r == 0 closes it with a pole). `square` pulls
    the low rings toward a superellipse so the base fills a square footprint."""
    pole = prof[-1][0] <= 1e-6
    rows = prof[:-1] if pole else prof
    zmax = max(z for _r, z in prof) or 1.0
    cx, cy = center
    off = Vector((seed * 2.3, seed * 0.7, seed * 1.9))
    verts = []
    for r, z in rows:
        for k in range(seg):
            a = 2 * math.pi * k / seg
            c, s = math.cos(a), math.sin(a)
            m = 1.0
            if square:
                sq = (abs(c) ** square + abs(s) ** square) ** (-1 / square)
                m = 1 + (sq - 1) * sstep(sq_top, 0.0, z)
            rr = r * m
            if lump:
                rr *= 1 + lump * noise.noise(Vector((c, s, z * 0.8)) * lump_f + off)
            verts.append((cx + rr * c, cy + rr * s + shear * z / zmax, z))
    faces = []
    for i in range(len(rows) - 1):
        for k in range(seg):
            k1 = (k + 1) % seg
            faces.append((i * seg + k, i * seg + k1, (i + 1) * seg + k1, (i + 1) * seg + k))
    if pole:
        zp = prof[-1][1]
        verts.append((cx, cy + shear * zp / zmax, zp))
        pi_ = len(verts) - 1
        b = (len(rows) - 1) * seg
        for k in range(seg):
            faces.append((b + k, b + (k + 1) % seg, pi_))
    return mesh_obj(name, verts, faces, kind)


def metaball_mass(name, elems, res=0.08, threshold=0.5):
    """elems: (type, co, radius, size or None, negative). Converted to a mesh at once."""
    mb = bpy.data.metaballs.new(name + "MB")
    mb.resolution = res
    mb.render_resolution = res
    mb.threshold = threshold
    for typ, co, r, size, neg in elems:
        e = mb.elements.new(type=typ)
        e.co = co
        e.radius = r
        if size:
            e.size_x, e.size_y, e.size_z = size
        e.use_negative = neg
    tmp = link(bpy.data.objects.new(name + "MBob", mb))
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp)
    bpy.data.metaballs.remove(mb)
    me.name = name
    ob = link(bpy.data.objects.new(name, me))
    ob["kind"] = "flesh"
    return ob


def fit(ob, hx, hy, h):
    """Scales a mass about the origin so it spans +-hx, +-hy and 0..h."""
    co = [v.co.copy() for v in ob.data.vertices]
    cx = (min(c.x for c in co) + max(c.x for c in co)) / 2
    cy = (min(c.y for c in co) + max(c.y for c in co)) / 2
    mx = (max(c.x for c in co) - min(c.x for c in co)) / 2 or 1
    my = (max(c.y for c in co) - min(c.y for c in co)) / 2 or 1
    mz = max(c.z for c in co) or 1
    for v in ob.data.vertices:
        v.co = Vector(((v.co.x - cx) * hx / mx, (v.co.y - cy) * hy / my, v.co.z * h / mz))
    ob.data.update()


def displace(ob, amp, freq, seed=0.0, amp2=0.0, freq2=0.0, zfade=0.15):
    """Pushes a mass along its normals by noise, fading out at the ground so the base stays put."""
    me = ob.data
    me.update()
    off = Vector((seed * 13.1, seed * 7.7, seed * 3.3))
    nrm = [v.normal.copy() for v in me.vertices]
    for v, n in zip(me.vertices, nrm):
        d = amp * noise.noise(v.co * freq + off)
        if amp2:
            d += amp2 * noise.noise(v.co * freq2 + off * 1.7)
        d *= sstep(0.0, zfade, v.co.z)
        v.co += n * d
    me.update()


def carve(ob, center, radii, lump=0.08, seed=0.0):
    """Cuts a lumpy ellipsoid out of a closed mass with an exact boolean: maws, tunnels, rifts."""
    cut = blob("cutter", center, 1.0, "cut", scale=radii, seg=24, rings=16, lump=lump, seed=seed)
    m = ob.modifiers.new("carve", "BOOLEAN")
    m.operation = "DIFFERENCE"
    m.object = cut
    try:
        m.solver = "EXACT"
    except TypeError:
        pass
    cut.hide_render = True
    apply_modifiers(ob)
    me = cut.data
    bpy.data.objects.remove(cut)
    bpy.data.meshes.remove(me)
    ob.data.materials.clear()
    ob.data.polygons.foreach_set("material_index", [0] * len(ob.data.polygons))


def mass_from(name, elems, hx, hy, h, res=0.08, threshold=0.5, amp=0.06, freq=0.9, amp2=0.03, freq2=2.6,
              seed=1.0, cutters=()):
    """A flesh mass: metaballs, scaled to +-hx, +-hy, 0..h, displaced, carved, cut at the ground."""
    ob = metaball_mass(name, elems, res, threshold)
    fit(ob, hx, hy, h)
    displace(ob, amp, freq, seed, amp2, freq2)
    for i, (c, rad, lump) in enumerate(cutters):
        carve(ob, c, rad, lump, seed + i)
    ground_cut(ob)
    ob["flex"] = True
    ob["kind"] = "flesh"
    return ob


def creep(half, rr, veins=10, seg=48):
    """The flat root mat round the base: a lobed squarish sheet, at most ~4.5 cm high, edge at z = 0,
    with low root veins running out across it."""
    seed = rr.uniform(0, 50)

    def R(a):
        c, s = abs(math.cos(a)), abs(math.sin(a))
        se = half / ((c ** 5 + s ** 5) ** 0.2)
        return se * (0.88 + 0.12 * (0.5 + 0.5 * noise.noise(Vector((math.cos(a) * 2.4, math.sin(a) * 2.4, seed)))))

    def h(f):
        return 0.025 * (1 - sstep(0.6, 1.0, f))

    fr = [0.42, 0.68, 0.84, 0.93, 1.0]
    verts = [(0.0, 0.0, h(0))]
    for f in fr:
        for k in range(seg):
            a = 2 * math.pi * k / seg
            r = R(a) * f
            z = h(f)
            if f < 0.95:
                z += 0.003 * noise.noise(Vector((math.cos(a) * r, math.sin(a) * r, seed)) * 2.0)
            verts.append((r * math.cos(a), r * math.sin(a), max(0.0, z)))
    faces = [(0, 1 + k, 1 + (k + 1) % seg) for k in range(seg)]
    for i in range(len(fr) - 1):
        for k in range(seg):
            k1 = (k + 1) % seg
            a0, a1 = 1 + i * seg, 1 + (i + 1) * seg
            faces.append((a0 + k, a1 + k, a1 + k1, a0 + k1))
    ob = mesh_obj("creep", verts, faces, "creep")
    ob["open"] = True
    for v in range(veins):
        a0 = 2 * math.pi * (v + rr.uniform(-0.3, 0.3)) / veins
        da = rr.uniform(-0.25, 0.25)
        pts = []
        for i in range(7):
            f = 0.5 + 0.47 * i / 6
            a = a0 + da * i / 6 + 0.08 * math.sin(i * 1.7 + v)
            r = R(a) * f
            pts.append(Vector((r * math.cos(a), r * math.sin(a), h(f) + 0.004)))
        radii = [0.05 * (1 - i / 6) ** 0.7 for i in range(7)]
        radii[-1] = 0.0
        sd = UP.cross((pts[-1] - pts[0]).normalized())
        sweep("creep_vein", pts, radii, "creep", ring=5, flat=0.26, side=sd, rimfn=lambda a, t: 1.0)
    return ob


def sac(name, hit, r, embed=0.45, kind="glow", scale=(1, 1, 1), lump=0.1, seed=0.0, seg=10, rings=7):
    if hit is None:
        return None
    p, n = hit
    return blob(name, p + n * r * (1 - 2 * embed) * scale[2], r, kind, scale=scale, seg=seg, rings=rings,
                lump=lump, seed=seed, axis=n)


def nodule(name, hit, r, kind="team", seed=0.0):
    if hit is None:
        return None
    p, n = hit
    return blob(name, p + n * r * 0.15, r, kind, scale=(1, 1, 0.75), seg=6, rings=4, lump=0.12, seed=seed, axis=n)


def plate_on(name, hit, along, W, L, sink=0.0, lift=12.0, bvh=None, **kw):
    """A plate rooted at a surface hit, its tip tilted `lift` degrees off the surface so it stands proud."""
    if hit is None:
        print(f"[void] skipped {name}: no surface")
        return None
    p, n = hit
    a = Vector(along)
    t = a - n * a.dot(n)
    if t.length < 1e-5:
        t = n.orthogonal()
    t.normalize()
    lr = math.radians(lift)
    t2 = t * math.cos(lr) + n * math.sin(lr)
    n2 = n * math.cos(lr) - t * math.sin(lr)
    return plate(name, frame(p - n * sink, t2, n2), W, L, conform=bvh, **kw)


def inset(ob, d):
    """Shrinks a flesh mass along its normals so the plates and sacs placed on it sit proud."""
    me = ob.data
    me.update()
    nrm = [v.normal.copy() for v in me.vertices]
    for v, n in zip(me.vertices, nrm):
        v.co -= n * d * sstep(0.0, 0.2, v.co.z)
    me.update()


def rim_points(bvh, zc, n, front_lim, rmax=1.8, step=0.04):
    """Walks out from (0, zc) on the front until rays from -Y stop going deep: the rim of a cavity."""
    out = []
    for k in range(n):
        ph = 2 * math.pi * k / n
        hit = None
        s = 0.1
        while s < rmax:
            x, z = s * math.cos(ph), zc + s * math.sin(ph)
            if z < 0.03:
                break
            h = cast(bvh, (x, -12, z), (0, 1, 0))
            if h and h[0].y < front_lim:
                hit = h
                break
            s += step
        out.append((ph, hit))
    return out


def leg(name, root, knee, foot, r0, r1, claw_len, claw_r, kind="chitin"):
    """A chitin leg arching out of the body to the ground, ending in a bone claw hooked into it."""
    path = catmull([root, knee, foot], per=5)
    n = len(path)
    radii = [(r0 + (r1 - r0) * (i / (n - 1)) ** 0.8) * (1 + 0.13 * math.cos(i / (n - 1) * 3 * 2 * math.pi))
             for i in range(n)]
    sweep(name, path, radii, kind, ring=9, rimfn=lambda a, t: 0.0)
    out = Vector((foot.x, foot.y, 0)).normalized()
    horn(name + "_claw", foot - out * 0.02, out * 0.45 + DOWN, claw_len, claw_r, -out, math.radians(55),
         segs=6, ring=7, flat=0.7)
    # two hooked spurs on the knee, as on the reference's legs
    kn = Vector(knee)
    for s, ln in ((0.0, 0.42), (0.6, 0.3)):
        horn(name + "_spur", kn + UP * (r0 * 0.6) - out * s * 0.25, UP * 0.9 + out * 0.6, ln * (r0 / 0.22), r0 * 0.38,
             out, math.radians(50), segs=4, ring=5, flat=0.7)


def ribbed(n, r0, r1, ribs, amp=0.14, end_taper=True):
    out = []
    for i in range(n):
        t = i / (n - 1)
        r = r0 + (r1 - r0) * t
        r *= 1 + amp * math.cos(t * ribs * 2 * math.pi)
        out.append(r)
    if end_taper:
        out[-1] *= 0.6
    return out


def tendril(name, pts, r0, r1, ribs, kind="flesh", ring=8, per=4):
    path = catmull(pts, per=per)
    return sweep(name, path, ribbed(len(path), r0, r1, ribs), kind, ring=ring)


def patch(name, A, B, C, D, kind="flesh", nu=6, nv=5, sag=None, thick=0.03, scallop=0.0):
    """A thin two-sided membrane sheet over the bilinear patch A-B-C-D (A-B top edge, D-C bottom),
    bulging by `sag` in the middle; the bottom edge is scalloped like a bat wing's trailing edge (`scallop`
    is the fraction of each column the edge rises between the finger points, so the sheet never folds)."""
    A, B, C, D = (Vector(x) for x in (A, B, C, D))
    sag = Vector(sag) if sag is not None else Vector((0, 0, 0))
    verts = []
    for j in range(nv):
        v = j / (nv - 1)
        for i in range(nu):
            u = i / (nu - 1)
            vv = v * (1 - scallop * abs(math.sin(u * math.pi * 2)))
            p = (A * (1 - u) + B * u) * (1 - vv) + (D * (1 - u) + C * u) * vv
            p += sag * (4 * u * (1 - u)) * (0.4 + 0.6 * v)
            verts.append(p)
    faces = []
    for j in range(nv - 1):
        for i in range(nu - 1):
            a = j * nu + i
            faces.append((a, a + 1, a + nu + 1, a + nu))
    ob = mesh_obj(name, verts, faces, kind)
    m = ob.modifiers.new("solid", "SOLIDIFY")
    m.thickness = thick
    m.offset = 0.0
    m.use_rim = True
    m.use_even_offset = True
    apply_modifiers(ob)
    set_attr(ob, "along")
    set_attr(ob, "rim")
    return ob


# --- the seven buildings --------------------------------------------------------------------------

def build_hive(rr):
    """Hive Heart, 5x5, ~4.5 m: a lobed heart-mound shingled in hooked chitin plates, a crown of bone
    spikes round three glowing heart sacs, an open maw at the front, four arched chitin legs."""
    creep(2.72, rr, veins=9)
    mass = mass_from("hive_mass", [
        ("ELLIPSOID", (0, 0.1, 0.0), 2.2, (1.25, 1.2, 1.0), False),
        ("BALL", (0, 0.2, 1.3), 1.9, None, False),
        ("BALL", (-1.0, 0.35, 0.5), 1.5, None, False),
        ("BALL", (1.0, 0.35, 0.5), 1.5, None, False),
        ("BALL", (0, 1.0, 0.6), 1.6, None, False),
        ("BALL", (-0.5, 0.25, 2.25), 1.1, None, False),
        ("BALL", (0.5, 0.25, 2.25), 1.1, None, False),
    ], 1.95, 1.95, 3.15, res=0.09, amp=0.07, seed=1.0,
        cutters=[((0, -1.92, 0.42), (0.86, 1.0, 1.02), 0.07)])
    bvh = bvh_of(mass)
    C = Vector((0, 0.2, 1.1))
    # heart sacs on top and the crown of bone spikes round them
    top = cast(bvh, (0, 0.25, 12), DOWN)[0]
    for i, (dx, dy, r) in enumerate(((-0.3, 0.05, 0.44), (0.3, 0.05, 0.44), (0.0, 0.42, 0.38))):
        hit = cast(bvh, (dx, 0.25 + dy, 12), DOWN)
        sac(f"heart{i}", hit, r, embed=0.35, scale=(1, 1, 0.9), seed=i + 1)
    for k in range(8):
        th = 2 * math.pi * k / 8 + math.pi / 8
        hit = cast(bvh, (0.95 * math.cos(th), 0.25 + 0.95 * math.sin(th), 12), DOWN)
        rd = radial(th)
        horn(f"crown{k}", hit[0] - hit[1] * 0.15, UP + rd * 0.55, 1.6 + 0.15 * (k % 2), 0.17, -rd + UP * 0.3,
             math.radians(70), segs=9, ring=8, flat=0.75)
    for k in range(9):
        th = 2 * math.pi * k / 9
        hit = cast(bvh, (0.66 * math.cos(th), 0.25 + 0.66 * math.sin(th), 12), DOWN)
        nodule(f"team_crown{k}", hit, 0.12, seed=k)
    # shingled chitin plates, tips down, hooking out
    sac_zones = (0.0, math.pi, math.pi / 2)
    tiers = [(75, 6, 0.85, 0.7, 0.25), (60, 7, 1.15, 0.95, 0.0), (38, 9, 1.3, 1.05, 0.5), (17, 11, 1.25, 1.05, 0.0), (-2, 12, 1.15, 0.95, 0.5)]
    for ti, (el, n, W, L, ph) in enumerate(tiers):
        for k in range(n):
            th = 2 * math.pi * (k + ph) / n + rr.uniform(-0.05, 0.05)
            if ti >= 2 and abs(angdiff(th, -math.pi / 2)) < math.radians(36):
                continue
            if ti == 3 and any(abs(angdiff(th, z)) < math.radians(14) for z in sac_zones):
                continue
            hit = cast_in(bvh, C, sph(th, math.radians(el)))
            if hit is None:
                continue
            p, nn = hit
            along = DOWN if abs(nn.z) < 0.9 else -radial(th)
            plate_on(f"plate{ti}_{k}", hit, along, W * rr.uniform(0.9, 1.1), L * rr.uniform(0.9, 1.1),
                     hook=0.35, cross=0.3, bow=0.05, thick=0.1, bvh=bvh)
    # glowing sac clusters on the flanks and back
    for zi, th in enumerate(sac_zones):
        hit = cast_in(bvh, C, sph(th, math.radians(14)))
        p, nn = hit
        tang = UP.cross(nn).normalized()
        for j, (u, v, r) in enumerate(((-0.33, 0.0, 0.36), (0.3, 0.08, 0.32), (0.0, -0.32, 0.3))):
            h2 = cast_in(bvh, C, (p + tang * u + UP * v) - C)
            sac(f"sac{zi}_{j}", h2, r, embed=0.4, scale=(1, 1, 0.85), seed=zi * 3 + j)
    # the maw: the cavity's rim ringed with hooked teeth, a chitin brow over it, a green throat, mandibles
    front = min(v.co.y for v in mass.data.vertices)
    zc = 0.6
    rim = rim_points(bvh, zc, 22, front + 0.45)
    pts = [h for _ph, h in rim if h]
    ys = [h[0].y for h in pts]
    ctr = Vector((0, sum(ys) / len(ys), zc))
    top_z = max(h[0].z for h in pts)
    half_w = max(abs(h[0].x) for h in pts)
    for k, (ph, h) in enumerate(rim):
        if h is None or h[0].z < 0.15:
            continue
        p, nn = h
        inward = Vector((ctr.x - p.x, 0, ctr.z - p.z)).normalized()
        big = 1.0 + 0.35 * max(0.0, math.sin(ph))
        horn(f"tooth{k}", p - nn * 0.04, inward * 0.8 + Vector((0, -0.35, 0)), 0.36 * big, 0.075 * big,
             Vector((0, 1, 0)) + inward * 0.4, math.radians(60), segs=5, ring=6, flat=0.7)
    hit = cast(bvh, (0, -12, top_z + 0.32), (0, 1, 0))
    plate_on("brow", hit, DOWN + Vector((0, -0.6, 0)), half_w * 2.1, 0.95, lift=8, hook=0.5, cross=0.45, bow=0.0,
             thick=0.12, nv=7, nu=5, bvh=bvh)
    for s_ in (-1, 1):
        hit = cast(bvh, (s_ * (half_w * 0.85 + 0.35), -12, top_z + 0.1), (0, 1, 0))
        plate_on(f"cheek{s_}", hit, Vector((s_ * 0.45, -0.3, -1.0)), 0.75, 0.9, lift=10, hook=0.45, cross=0.35,
                 bow=0.0, thick=0.1, bvh=bvh)
    sac("throat", (Vector((0, ctr.y + 0.95, 0.55)), Vector((0, -1, 0.3)).normalized()), 0.48, embed=0.15,
        scale=(1.15, 1.15, 0.65), seed=9)
    for s_ in (-1, 1):
        hit = cast(bvh, (s_ * (half_w + 0.1), -12, zc - 0.15), (0, 1, 0))
        horn(f"mandible{s_}", hit[0] - hit[1] * 0.12, Vector((s_ * 0.3, -1.0, -0.35)), 1.05, 0.19,
             Vector((-s_, 0.25, -0.15)), math.radians(85), segs=8, ring=8, flat=0.7)
    for k in range(5):
        x = (k - 2) * 0.3
        hit = cast(bvh, (x, -12, top_z + 0.78 + 0.06 * abs(k - 2) * -1), (0, 1, 0))
        if hit:
            nodule(f"team_maw{k}", hit, 0.12, seed=20 + k)
    # four arched chitin legs into the corners
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        th = math.atan2(sy, sx)
        hit = cast_in(bvh, C, sph(th, math.radians(18)))
        rd = radial(th)
        root = hit[0] - hit[1] * 0.25
        knee = hit[0] + rd * 0.45 + UP * 0.55
        foot = Vector((sx * 2.02, sy * 2.02, 0.42))
        leg(f"leg{sx}{sy}", root, knee, foot, 0.26, 0.15, 0.7, 0.15)


def build_pod(rr):
    """Brood Pod, 2x2, ~2.2 m: a translucent egg cluster with glowing cores (the glow_core object),
    sitting in a cup of chitin petals and caged by bone ribs that curl over the big egg."""
    creep(1.22, rr, veins=7)
    base = mass_from("pod_base", [
        ("ELLIPSOID", (0, 0, 0), 1.3, (1.0, 1.0, 0.55), False),
        ("BALL", (0.45, 0.3, 0.1), 0.8, None, False),
        ("BALL", (-0.45, -0.25, 0.1), 0.8, None, False),
        ("BALL", (-0.3, 0.4, 0.1), 0.7, None, False),
    ], 0.72, 0.72, 0.46, res=0.05, amp=0.03, freq=2.0, amp2=0.015, freq2=5.0, seed=2.0)
    bvh = bvh_of(base)
    for k in range(8):
        th = 2 * math.pi * k / 8 + 0.2
        hit = cast_in(bvh, (0, 0, 0.05), sph(th, math.radians(34)))
        plate_on(f"petal{k}", hit, DOWN, 0.46 * rr.uniform(0.9, 1.1), 0.42, hook=0.45, cross=0.35, bow=0.05,
                 thick=0.06, lift=8, bvh=bvh)
    eggs = [((0.0, 0.04, 1.08), 0.57, 1.34, UP, 0.35),
            ((-0.5, -0.3, 0.5), 0.27, 1.25, (-0.5, -0.3, 1.0), 0.16),
            ((0.5, -0.17, 0.47), 0.25, 1.25, (0.5, -0.17, 1.0), 0.15),
            ((0.22, 0.52, 0.44), 0.24, 1.25, (0.22, 0.5, 1.0), 0.14),
            ((-0.42, 0.38, 0.4), 0.2, 1.2, (-0.4, 0.4, 1.0), 0.12)]
    c0, r0_, _sz, ax0, _rc = eggs[0]
    STATE["core_pivot"] = Vector(c0) - Vector(ax0).normalized() * r0_ * 0.06
    for i, (c, r, sz, ax, rc) in enumerate(eggs):
        blob(f"egg{i}", c, r, "membrane", scale=(1, 1, sz), seg=16 if i == 0 else 12, rings=12 if i == 0 else 8,
             lump=0.05, seed=i + 3, axis=ax)
        blob(f"core{i}", Vector(c) - Vector(ax).normalized() * r * 0.06, rc, "core", scale=(1, 1, sz * 0.95),
             seg=12 if i == 0 else 8, rings=9 if i == 0 else 6, lump=0.16, seed=i + 7, axis=ax)
    cup = [Vector((0.38 * math.cos(2 * math.pi * k / 20), 0.04 + 0.38 * math.sin(2 * math.pi * k / 20),
                   0.44 + 0.03 * math.sin(k * 1.9))) for k in range(20)]
    sweep("cup", cup, ribbed(20, 0.13, 0.13, 5, 0.2, end_taper=False), "flesh", ring=8, closed=True, side=UP)
    for k in range(6):
        th = 2 * math.pi * k / 6 + 0.5
        p = Vector((0.38 * math.cos(th), 0.04 + 0.38 * math.sin(th), 0.47))
        nodule(f"team{k}", (p + radial(th) * 0.11 + UP * 0.04, (radial(th) + UP * 0.7).normalized()), 0.075, seed=k)
    for k in range(5):
        th = 2 * math.pi * k / 5 + 0.3
        rd = radial(th)
        c0 = Vector((0, 0.04, 0))
        ctrl = [(0.62, 0.22), (0.76, 0.75), (0.74, 1.28), (0.57, 1.8), (0.31, 2.08), (0.1, 2.2)]
        path = catmull([c0 + rd * r + UP * z for r, z in ctrl], per=3)
        nn = len(path)
        radii = [0.09 * (1 - i / (nn - 1)) ** 0.75 for i in range(nn)]
        radii[-1] = 0.0
        sweep(f"rib{k}", path, radii, "bone", ring=7, flat=0.6, side=UP.cross(rd))


def build_maw(rr):
    """Void Maw, 3x3, ~2.5 m: a squat chitin-armoured collar over the slime pile, a lamprey ring mouth
    of bone teeth round a green-lit throat, hooks curling over the lip, ribbed feeding tendrils."""
    creep(1.72, rr, veins=9)
    R0 = 1.3
    shear = -0.08
    prof = [(1.00, 0.00), (0.985, 0.18), (0.93, 0.45), (0.83, 0.75), (0.73, 0.98), (0.67, 1.12), (0.63, 1.22),
            (0.585, 1.27), (0.53, 1.25), (0.48, 1.13), (0.42, 0.95), (0.34, 0.78), (0.22, 0.64), (0.1, 0.58),
            (0.0, 0.57)]
    ZS = 1.16  # r2: the collar stands taller (overall 2.1 -> ~2.5 m)
    col = lathe("maw_collar", [(r * R0, z * ZS) for r, z in prof], "flesh", seg=30, square=4.0, sq_top=0.7,
                shear=shear, lump=0.05, seed=3.0)
    col["flex"] = True
    bvh = bvh_of(col)
    zmax = 1.27 * ZS

    def sh(p):
        return Vector((p.x, p.y + shear * p.z / zmax, p.z))

    for ti, (z, n, W, L, ph) in enumerate(((0.2, 12, 0.88, 0.8, 0.0), (0.6, 11, 0.74, 0.66, 0.5),
                                           (0.93, 10, 0.56, 0.5, 0.0))):
        z *= ZS
        for k in range(n):
            th = 2 * math.pi * (k + ph) / n + rr.uniform(-0.05, 0.05)
            hit = cast_in(bvh, (0, shear * z / zmax, z), radial(th))
            plate_on(f"collar{ti}_{k}", hit, UP, W * rr.uniform(0.92, 1.08), L, hook=0.4, cross=0.32, bow=0.04,
                     thick=0.08, lift=14, bvh=bvh)
    for ri, (rf, z, n, ln, r0) in enumerate(((0.53, 1.21, 16, 0.42, 0.075), (0.46, 1.02, 12, 0.32, 0.065),
                                             (0.38, 0.84, 9, 0.24, 0.055))):
        for k in range(n):
            th = 2 * math.pi * (k + 0.5 * ri) / n
            rd = radial(th)
            p = sh(Vector((rd.x * rf * R0, rd.y * rf * R0, z * ZS)))
            horn(f"tooth{ri}_{k}", p, -rd * 0.75 + DOWN * 0.5, ln, r0, DOWN, math.radians(45), segs=4, ring=6, flat=0.7)
    for k in range(7):
        th = 2 * math.pi * k / 7 + math.pi / 7
        rd = radial(th)
        p = sh(Vector((rd.x * 0.62 * R0, rd.y * 0.62 * R0, 1.16 * ZS)))
        horn(f"hook{k}", p, rd * 0.45 + UP, 1.32, 0.12, -rd, math.radians(96), segs=9, ring=7, flat=0.7)
    for k in range(7):
        th = 2 * math.pi * k / 7
        rd = radial(th)
        p = sh(Vector((rd.x * 0.6 * R0, rd.y * 0.6 * R0, 1.27 * ZS)))
        nodule(f"team{k}", (p, (rd + UP).normalized()), 0.085, seed=k)
    blob("throat", sh(Vector((0, 0, 0.6 * ZS))), 0.34, "glow", scale=(1, 1, 0.45), lump=0.15, seed=4)
    for k, th in enumerate((0.4, 2.5, 4.4)):
        hit = cast_in(bvh, (0, 0, 0.45 * ZS), radial(th) + UP * 0.1)
        sac(f"sac{k}", hit, 0.16, embed=0.35, seed=k + 2)
    # r2: feeding tendrils sprawl out over the slime pile's corners and curl at the tips (were hanging straps)
    for k in range(4):
        th = math.pi / 4 + k * math.pi / 2
        rd = radial(th)
        tg = UP.cross(rd) * (1 if k % 2 else -1)
        pts = [rd * 0.85 + UP * 0.8, rd * 1.2 + UP * 0.62, rd * 1.47 + UP * 0.26, rd * 1.64 + UP * 0.07,
               rd * 1.68 + tg * 0.17 + UP * 0.06, rd * 1.56 + tg * 0.3 + UP * 0.2]
        tendril(f"tendril{k}", pts, 0.18, 0.035, 7)
    for k in range(4):
        th = k * math.pi / 2 + 0.3
        rd = radial(th)
        tg = UP.cross(rd)
        pts = [rd * 0.95 + UP * 0.55, rd * 1.16 + UP * 0.42, rd * 1.3 + UP * 0.13, rd * 1.33 + tg * 0.15 + UP * 0.04,
               rd * 1.25 + tg * 0.26 + UP * 0.12]
        tendril(f"tendril_s{k}", pts, 0.11, 0.03, 5, ring=7)


def build_nest(rr):
    """Spawning Nest, 3x3, ~2.8 m: a cupped ring of tall chitin plates round a glowing spawning pool,
    open at the front, bone spikes arching over the pool."""
    creep(1.72, rr, veins=9)
    R0 = 1.3
    prof = [(1.0, 0.0), (0.99, 0.14), (0.94, 0.32), (0.86, 0.44), (0.77, 0.48), (0.70, 0.43), (0.66, 0.33),
            (0.63, 0.24)]
    ring = lathe("nest_ring", [(r * R0, z) for r, z in prof], "flesh", seg=36, square=4.0, sq_top=0.5,
                 lump=0.05, seed=5.0)
    ring["open"] = True
    bvh = bvh_of(ring)
    pool = lathe("pool", [(0.66 * R0, 0.22), (0.5 * R0, 0.26), (0.28 * R0, 0.28), (0.0, 0.29)], "glow", seg=28,
                 lump=0.03, seed=6.0)
    pool["open"] = True
    for k in range(7):
        a = rr.uniform(0, 2 * math.pi)
        r = rr.uniform(0.1, 0.6)
        blob(f"spawn{k}", (r * math.cos(a), r * math.sin(a), 0.26), rr.uniform(0.09, 0.15), "membrane" if k % 2 else "glow",
             scale=(1, 1, 0.8), lump=0.15, seed=k)
    front = -math.pi / 2
    n = 9
    for k in range(n):
        th = 2 * math.pi * k / n + math.pi / n + front
        if abs(angdiff(th, front)) < math.radians(32):
            continue
        rd = radial(th)
        back = 0.5 + 0.5 * math.sin(th)
        p = rd * 1.0 + UP * 0.28
        M = frame(p, UP + rd * 0.2, rd)
        plate(f"wall{k}", M, 1.02 * rr.uniform(0.95, 1.05), 1.25 + 0.5 * back, hook=-0.32, cross=0.5, bow=-0.1,
              thick=0.11, nv=7, nu=5, conform=bvh)
    for k in range(5):
        th = math.pi / 2 + (k - 2) * math.radians(42)
        rd = radial(th)
        horn(f"spike{k}", rd * 1.14 + UP * 0.3, UP + rd * 0.18, 2.72 - 0.2 * abs(k - 2), 0.145, -rd,
             math.radians(58), segs=9, ring=8, flat=0.7)
    for s in (-1, 1):
        th = front + s * math.radians(36)
        rd = radial(th)
        horn(f"gate{s}", rd * 1.05 + UP * 0.3, UP + rd * 0.25, 1.45, 0.14,
             Vector((-s * 0.8, -0.1, 0.35)), math.radians(70), segs=8, ring=8, flat=0.7)
    loop = [Vector((1.1 * math.cos(2 * math.pi * k / 30), 1.1 * math.sin(2 * math.pi * k / 30), 0.4)) for k in range(30)]
    sweep("ribs", loop, ribbed(30, 0.13, 0.13, 10, 0.25, end_taper=False), "flesh", ring=8, closed=True, side=UP)
    for k, th in enumerate((0.15, math.pi - 0.15, math.pi / 2 + 0.4)):
        hit = cast_in(bvh, (0, 0, 0.15), radial(th) + UP * 0.25)
        sac(f"sac{k}", hit, 0.17, embed=0.3, seed=k)
    for k in range(10):
        th = 2 * math.pi * (k + 0.5) / 10
        hit = cast_in(bvh, (0, 0, 0.1), radial(th) + UP * 0.12)
        nodule(f"team{k}", hit, 0.085, seed=k)


def build_warren(rr):
    """Beast Warren, 3x3, ~3 m: a long, low armoured burrow mound with a ribbed bone tunnel mouth at
    the front, overlapping plated ridges down its back and flanks, and a row of heavy spines."""
    creep(1.72, rr, veins=9)
    mass = mass_from("warren_mass", [
        ("ELLIPSOID", (0, 0.2, 0.0), 1.7, (0.95, 1.2, 0.72), False),
        ("BALL", (0, 0.5, 0.6), 1.1, None, False),
        ("ELLIPSOID", (0, -0.8, 0.3), 1.2, (0.95, 0.75, 0.95), False),
        ("BALL", (-0.8, 0.3, 0.2), 0.9, None, False),
        ("BALL", (0.8, 0.3, 0.2), 0.9, None, False),
    ], 1.1, 1.15, 1.7, res=0.06, amp=0.045, seed=4.0,
        cutters=[((0, -1.25, 0.18), (0.56, 0.95, 0.82), 0.06)])
    bvh = bvh_of(mass)
    front = min(v.co.y for v in mass.data.vertices)
    zc = 0.4
    rim = [h for _ph, h in rim_points(bvh, zc, 24, front + 0.4) if h]
    a = max(abs(h[0].x) for h in rim if abs(h[0].z - zc) < 0.25)
    b = max(h[0].z for h in rim)
    yf = sum(h[0].y for h in rim) / len(rim)
    print(f"[void] warren tunnel: half width {a:.2f}, top {b:.2f}, front y {yf:.2f}")
    for k in range(4):
        ak, bk = a * (1.04 - 0.11 * k), b * (1.04 - 0.11 * k)
        y = yf + 0.04 + 0.24 * k
        pts = [Vector((ak * math.cos(math.pi * i / 12), y, -0.1 + (bk + 0.1) * math.sin(math.pi * i / 12))) for i in range(13)]
        al = [math.sin(math.pi * i / 12) for i in range(13)]
        rk = 0.11 - 0.015 * k
        sweep(f"arch{k}", pts, ribbed(13, rk, rk, 5, 0.18, end_taper=False), "bone", ring=7, flat=0.75,
              side=Vector((0, -1, 0)), along=al)
    for k in range(5):
        ph = math.radians(35 + 27.5 * k)
        p = Vector((a * 1.04 * math.cos(ph), yf, -0.1 + (b * 1.04 + 0.1) * math.sin(ph)))
        out = Vector((math.cos(ph), 0, math.sin(ph)))
        horn(f"archspike{k}", p, out + Vector((0, -0.6, 0)), 0.45, 0.065, Vector((0, -1, 0.5)), math.radians(45),
             segs=4, ring=6, flat=0.7)
    blob("den_glow", (0, yf + 1.0, 0.38), 0.4, "glow", scale=(1.1, 0.7, 0.8), lump=0.12, seed=3)
    # armadillo bands: broad, short plates overlapping front to back along the ridge and both flanks
    for k in range(6):
        y = -0.6 + 0.27 * k
        hit = cast(bvh, (0, y, 12), DOWN)
        plate_on(f"dorsal{k}", hit, Vector((0, 1, 0)), 1.2, 0.62, hook=0.22, cross=0.5, bow=0.04, thick=0.13,
                 lift=9, bvh=bvh)
    for s in (-1, 1):
        for row, (dirv, cnt, W, L) in enumerate((((s * 0.8, 0, 1.0), 5, 1.0, 0.6), ((s * 1.0, 0, 0.3), 5, 0.95, 0.58))):
            for k in range(cnt):
                y = -0.68 + 1.2 * k / (cnt - 1)
                hit = cast_in(bvh, (0, y, 0.45), Vector(dirv))
                plate_on(f"flank{s}_{row}_{k}", hit, Vector((0, 1, -0.3)), W, L, hook=0.25, cross=0.42, bow=0.04,
                         thick=0.12, lift=8, bvh=bvh)
    for k in range(5):
        th = math.pi / 2 + (k - 2) * 0.45
        hit = cast_in(bvh, (0, 0.3, 0.4), sph(th, math.radians(10)))
        plate_on(f"rump{k}", hit, DOWN, 0.9, 0.55, hook=0.25, cross=0.35, bow=0.05, thick=0.11, lift=8, bvh=bvh)
    for k in range(6):
        y = -0.45 + 0.23 * k
        hit = cast(bvh, (0, y, 12), DOWN)
        if hit is None:
            continue
        ln = 1.15 + 0.5 * math.sin(math.pi * (k + 0.5) / 6)
        horn(f"spine{k}", hit[0] - UP * 0.12, UP + Vector((0, 0.12, 0)), ln, 0.14, Vector((0, 1, 0)),
             math.radians(32), segs=8, ring=8, flat=0.6)
    for s in (-1, 1):
        for k in range(3):
            y = -0.3 + 0.55 * k
            hit = cast_in(bvh, (0, y, 0.45), Vector((s * 0.75, 0, 1.0)))
            horn(f"fspine{s}_{k}", hit[0] - hit[1] * 0.05, hit[1] + UP * 0.6, 0.6, 0.08, Vector((s, 0.6, 0)),
                 math.radians(45), segs=5, ring=6, flat=0.7)
    for s in (-1, 1):
        for j, (y, z, r) in enumerate(((0.45, 0.42, 0.22), (0.85, 0.3, 0.19))):
            hit = cast_in(bvh, (0, y, z), Vector((s, 0.1, 0.05)))
            sac(f"sac{s}_{j}", hit, r, embed=0.35, seed=j + 2 + s)
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        hit = cast_in(bvh, (0, 0.2 * sy, 0.25), Vector((sx, sy * 1.0, 0.15)))
        out = Vector((sx, sy, 0)).normalized()
        horn(f"claw{sx}{sy}", hit[0] - hit[1] * 0.1, out * 0.6 + DOWN * 0.3, 0.6, 0.13, DOWN - out * 0.2,
             math.radians(80), segs=6, ring=7, flat=0.7)
    for k in range(5):
        ph = math.radians(50 + 20 * k)
        hit = cast(bvh, ((a + 0.28) * math.cos(ph), -12, (b + 0.3) * math.sin(ph) + 0.05), (0, 1, 0))
        nodule(f"team{k}", hit, 0.1, seed=k)


def build_aerie(rr):
    """Aerie, 3x3, ~3.6 m: a tall twisted chitin spire on a rooted base, bone hook perches near the
    top with crimson bat-wing membranes under them, glowing sacs hanging off the spire."""
    creep(1.72, rr, veins=9)
    base = mass_from("aerie_base", [
        ("ELLIPSOID", (0, 0, 0), 1.3, (1.0, 1.0, 0.6), False),
        ("BALL", (0.45, 0.4, 0.1), 0.8, None, False), ("BALL", (-0.5, 0.35, 0.1), 0.75, None, False),
        ("BALL", (0.4, -0.45, 0.1), 0.75, None, False), ("BALL", (-0.4, -0.45, 0.1), 0.8, None, False),
    ], 0.95, 0.95, 0.7, res=0.05, amp=0.04, freq=1.8, seed=5.0)
    bvh = bvh_of(base)
    for k in range(9):
        th = 2 * math.pi * k / 9
        hit = cast_in(bvh, (0, 0, 0.1), sph(th, math.radians(40)))
        plate_on(f"bplate{k}", hit, DOWN, 0.62, 0.55, hook=0.4, cross=0.35, bow=0.04, thick=0.08, lift=10, bvh=bvh)
    spine = catmull([(0, 0, 0.3), (0.1, 0.06, 1.1), (-0.08, -0.05, 2.0), (0.06, 0.03, 2.75), (0.0, 0.0, 3.08)], per=5)
    n = len(spine)
    radii = [0.08 + 0.5 * (1 - i / (n - 1)) ** 0.9 for i in range(n)]
    tw = 3.2
    spire = sweep("spire", spine, radii, "chitin", ring=15, side=Vector((1, 0, 0)),
                  shape=lambda a, t: 1 + 0.32 * math.cos(3 * (a - tw * t)),
                  rimfn=lambda a, t: sstep(0.55, 1.0, math.cos(3 * (a - tw * t))))
    sb = bvh_of(spire)
    for j in range(3):
        for k, t in enumerate((0.1, 0.24, 0.38, 0.52, 0.66, 0.78)):
            i = int(t * (n - 1))
            a = tw * t + 2 * math.pi * j / 3 + 0.45
            hit = cast_in(sb, spine[i], radial(a))
            tang = UP.cross(radial(a))
            plate_on(f"sp{j}_{k}", hit, UP + tang * 0.45, 0.5 * (1 - 0.45 * t), 0.62 * (1 - 0.3 * t), hook=0.5,
                     cross=0.38, bow=0.03, thick=0.08, lift=16, bvh=sb)
    for k in range(4):
        th = math.pi / 4 + k * math.pi / 2 + 0.2
        rd = radial(th)
        z = 2.62 + 0.14 * (k % 2)
        i = min(range(n), key=lambda q: abs(spine[q].z - z))
        root = spine[i] + rd * 0.08
        pts = horn_path(root, rd + UP * 0.18, 1.3, UP, math.radians(105), 9, 1.7)
        radii_h = [0.115 * (1 - q / 9) ** 0.8 for q in range(10)]
        radii_h[-1] = 0.0
        sweep(f"perch{k}", pts, radii_h, "bone", ring=7, flat=0.7, side=UP)
        tipb = pts[6]
        j2 = min(range(n), key=lambda q: abs(spine[q].z - (z - 1.3)))
        side = UP.cross(rd) * 0.18
        # r3: a bat wing, tapering from the hook tip back down to the spire (was a near-rectangular banner)
        patch(f"flap{k}", spine[i] + rd * 0.12, tipb, tipb + DOWN * 0.36 - rd * 0.34 + side, spine[j2] + rd * 0.22,
              nu=9, nv=5, sag=rd * 0.14 + DOWN * 0.12, thick=0.035, scallop=0.32)
    horn("crest", spine[-1] - UP * 0.1, UP, 0.62, 0.11, Vector((0.3, 0, 1)), math.radians(15), segs=5, ring=7)
    for j, (z, a, r) in enumerate(((1.75, 3.6, 0.2), (1.55, 3.95, 0.17), (1.95, 3.85, 0.15), (1.45, 0.6, 0.18),
                                   (1.7, 0.85, 0.15))):
        i = min(range(n), key=lambda q: abs(spine[q].z - z))
        hit = cast_in(sb, spine[i], radial(a))
        sac(f"sac{j}", hit, r, embed=0.3, scale=(1, 1, 1.15), seed=j)
    for j, th in enumerate((2.3, 5.6)):
        hit = cast_in(bvh, (0, 0, 0.2), sph(th, math.radians(35)))
        sac(f"bsac{j}", hit, 0.2, embed=0.35, seed=j + 5)
    for k in range(7):
        a = 2 * math.pi * k / 7
        i = min(range(n), key=lambda q: abs(spine[q].z - 1.12))
        hit = cast_in(sb, spine[i], radial(a))
        nodule(f"team{k}", hit, 0.09, seed=k)
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        th = math.atan2(sy, sx)
        hit = cast_in(bvh, (0, 0, 0.2), sph(th, math.radians(30)))
        rd = radial(th)
        leg(f"root{sx}{sy}", hit[0] - hit[1] * 0.15, hit[0] + rd * 0.3 + UP * 0.35,
            Vector((sx * 1.08, sy * 1.08, 0.28)), 0.16, 0.1, 0.42, 0.1)


def build_abyss(rr):
    """Abyssal Lair, 4x4, ~5 m: a towering dark monolith split by a deep glowing green rift, its two
    halves armoured in overlapping upward hooked plates, giant curved tusks sweeping out of the base."""
    creep(2.22, rr, veins=12)
    mass = mass_from("abyss_mass", [
        ("ELLIPSOID", (0, 0, 0), 2.2, (1.0, 0.95, 0.42), False),
        ("ELLIPSOID", (-0.62, 0, 1.0), 1.3, (0.8, 1.0, 1.2), False),
        ("ELLIPSOID", (0.62, 0, 1.0), 1.3, (0.8, 1.0, 1.2), False),
        ("ELLIPSOID", (-0.56, 0.05, 2.3), 1.1, (0.75, 0.9, 1.3), False),
        ("ELLIPSOID", (0.56, 0.05, 2.3), 1.1, (0.75, 0.9, 1.3), False),
        ("ELLIPSOID", (-0.42, 0.05, 3.5), 0.85, (0.7, 0.85, 1.35), False),
        ("ELLIPSOID", (0.42, 0.05, 3.5), 0.85, (0.7, 0.85, 1.35), False),
        ("BALL", (-0.3, 0.0, 4.4), 0.55, None, False),
        ("BALL", (0.3, 0.0, 4.4), 0.55, None, False),
    ], 1.3, 1.15, 4.4, res=0.07, amp=0.05, seed=7.0,
        cutters=[((0, 0, 2.95), (0.17, 2.2, 2.45), 0.15), ((0, 0, 4.75), (0.42, 2.0, 0.85), 0.1)])
    bvh = bvh_of(mass)
    blob("rift", (0, 0.0, 1.55), 1.0, "glow", scale=(0.06, 0.44, 1.15), seg=12, rings=10, lump=0.1, seed=2)
    blob("rift2", (0, 0.0, 3.35), 1.0, "glow", scale=(0.05, 0.3, 0.95), seg=10, rings=8, lump=0.1, seed=3)
    for k, (x, y, z, r) in enumerate(((0.0, -0.95, 0.45, 0.3), (-0.3, -1.05, 0.3, 0.2), (0.32, -1.0, 0.32, 0.22))):
        blob(f"riftsac{k}", (x, y, z), r, "glow", lump=0.12, seed=k + 3)
    tiers = ((0.8, 5, 1.1, 1.35), (1.55, 5, 1.0, 1.3), (2.3, 4, 0.95, 1.2), (3.0, 4, 0.82, 1.05),
             (3.65, 3, 0.68, 0.9))
    for s in (-1, 1):
        for ti, (z, cnt, W, L) in enumerate(tiers):
            for k in range(cnt):
                frac = (k + 0.5 * (ti % 2) + 0.25) / cnt
                th = (math.pi / 2 + math.pi * frac) if s < 0 else (-math.pi / 2 + math.pi * frac)
                th += rr.uniform(-0.06, 0.06)
                cx = s * (0.55 - 0.035 * ti)
                hit = cast_in(bvh, (cx, 0, z), radial(th) + UP * 0.05)
                if hit is None or abs(hit[0].x) < 0.16:
                    continue
                plate_on(f"mono{s}_{ti}_{k}", hit, UP + radial(th) * 0.0, W * rr.uniform(0.92, 1.08),
                         L * rr.uniform(0.95, 1.05), hook=0.4, cross=0.42, bow=0.03, thick=0.12, lift=11, bvh=bvh)
        for k in range(5):
            th = (math.pi / 2 + math.pi * (k + 0.5) / 5) if s < 0 else (-math.pi / 2 + math.pi * (k + 0.5) / 5)
            hit = cast_in(bvh, (s * 0.5, 0, 0.3), sph(th, math.radians(25)))
            if hit and abs(hit[0].x) > 0.2:
                plate_on(f"skirt{s}_{k}", hit, DOWN, 1.0, 0.75, hook=0.35, cross=0.35, bow=0.04, thick=0.1, lift=8,
                         bvh=bvh)
        for k, (dy, ln) in enumerate(((-0.25, 1.25), (0.22, 1.05), (0.0, 0.8))):
            h2 = cast(bvh, (s * (0.3 + 0.12 * k), dy, 12), DOWN)
            horn(f"crown{s}{k}", h2[0] - UP * 0.14, UP + Vector((s * 0.4, dy * 0.8, 0)), ln, 0.16,
                 Vector((s, 0, 0.2)), math.radians(55 + 10 * k), segs=8, ring=8, flat=0.7)
    for s in (-1, 1):
        hit = cast_in(bvh, (s * 0.6, -0.4, 0.75), Vector((s * 0.7, -1.0, 0.0)))
        horn(f"tusk_f{s}", hit[0] - hit[1] * 0.15, Vector((s * 0.55, -0.85, -0.05)), 3.0, 0.3,
             Vector((-s * 0.35, 0.25, 1.0)), math.radians(125), segs=12, ring=10, flat=0.85, power=1.15)
        hit = cast_in(bvh, (s * 0.6, 0.4, 0.75), Vector((s * 0.8, 1.0, 0.0)))
        horn(f"tusk_b{s}", hit[0] - hit[1] * 0.15, Vector((s * 0.6, 0.8, 0.0)), 2.2, 0.24,
             Vector((-s * 0.2, -0.2, 1.0)), math.radians(110), segs=10, ring=9, flat=0.85, power=1.15)
    for k, (y, z) in enumerate(((-0.45, 1.45), (0.35, 2.55), (-0.2, 3.5))):
        pts = [Vector((-0.45, y, z + 0.05)), Vector((0, y - 0.05, z - 0.18)), Vector((0.45, y, z + 0.05))]
        tendril(f"strand{k}", pts, 0.085, 0.085, 3, ring=7)
    for k in range(6):
        x = -0.95 + 0.38 * k
        nodule(f"team_f{k}", cast(bvh, (x, -12, 0.42), (0, 1, 0)), 0.11, seed=k)
        nodule(f"team_b{k}", cast(bvh, (x, 12, 0.42), (0, -1, 0)), 0.11, seed=k + 9)


BUILDINGS = {
    "void_hive": dict(fn=build_hive, F=5.0, H=4.5, tris=11800, seed=11),
    "void_pod": dict(fn=build_pod, F=2.0, H=2.2, tris=5500, seed=12),
    "void_maw": dict(fn=build_maw, F=3.0, H=2.5, tris=8500, seed=13),
    "void_nest": dict(fn=build_nest, F=3.0, H=2.8, tris=8500, seed=14),
    "void_warren": dict(fn=build_warren, F=3.0, H=3.0, tris=9500, seed=15),
    "void_aerie": dict(fn=build_aerie, F=3.0, H=3.6, tris=8500, seed=16),
    "void_abyss": dict(fn=build_abyss, F=4.0, H=5.0, tris=11500, seed=17),
}


# --- part clean-up, budget, footprint -------------------------------------------------------------

def parts():
    return [o for o in bpy.context.scene.objects if o.type == "MESH" and "kind" in o]


def finish_parts(spec):
    F = spec["F"]
    flips = 0
    for o in parts():
        if o.get("flex"):
            inset(o, 0.05)
        ground_cut(o)
        if not o.get("open") and o["kind"] != "creep":
            flips += orient_outward(o)
        set_attr(o, "along")
        set_attr(o, "rim")
    # fit the building (not the creep) inside the footprint less ~0.15 m a side
    lim = F / 2 - 0.13
    body = [o for o in parts() if o["kind"] != "creep"]
    mx = max(max(abs(v.co.x) for v in o.data.vertices) for o in body)
    my = max(max(abs(v.co.y) for v in o.data.vertices) for o in body)
    sx, sy = min(1.0, lim / mx), min(1.0, lim / my)
    over = sorted(((max(max(abs(v.co.x), abs(v.co.y)) for v in o.data.vertices), o.name) for o in body), reverse=True)[:4]
    print("[void] widest parts:", ", ".join(f"{n} {e:.2f}" for e, n in over))
    if sx < 1 or sy < 1:
        for o in body:
            for v in o.data.vertices:
                v.co.x *= sx
                v.co.y *= sy
            o.data.update()
    # triangle budget: the flesh masses give way to everything else
    total = sum(tri_count(o) for o in parts())
    flex = [o for o in parts() if o.get("flex")]
    ft = sum(tri_count(o) for o in flex)
    want = max(900 * len(flex), spec["tris"] - (total - ft))
    if flex and ft > want:
        for o in flex:
            decimate(o, want / ft)
    total = sum(tri_count(o) for o in parts())
    print(f"[void] parts={len(parts())} flipped={flips} fit=({sx:.3f},{sy:.3f}) extent=({mx * sx:.2f},{my * sy:.2f}) tris={total}")


# --- materials ------------------------------------------------------------------------------------

class G:
    """A tiny node-graph helper for the bake shaders."""

    def __init__(self, mat):
        self.nt = mat.node_tree
        self.n = self.nt.nodes
        self.L = self.nt.links
        self._p = None

    def new(self, t, **kw):
        nd = self.n.new(t)
        for k, v in kw.items():
            setattr(nd, k, v)
        return nd

    def put(self, sock, v):
        if isinstance(v, bpy.types.NodeSocket):
            self.L.new(v, sock)
        else:
            sock.default_value = v

    def pos(self):
        if self._p is None:
            self._p = self.new("ShaderNodeTexCoord").outputs["Object"]
        return self._p

    def math(self, op, a, b=0.0):
        nd = self.new("ShaderNodeMath", operation=op)
        self.put(nd.inputs[0], a)
        self.put(nd.inputs[1], b)
        return nd.outputs[0]

    def mr(self, x, lo, hi, a=0.0, b=1.0):
        nd = self.new("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP", clamp=True)
        self.put(nd.inputs["Value"], x)
        nd.inputs["From Min"].default_value = lo
        nd.inputs["From Max"].default_value = hi
        nd.inputs["To Min"].default_value = a
        nd.inputs["To Max"].default_value = b
        return nd.outputs["Result"]

    def mix(self, f, a, b):
        nd = self.new("ShaderNodeMix", data_type="RGBA")
        ins = {s.identifier: s for s in nd.inputs}
        self.put(ins["Factor_Float"], f)
        self.put(ins["A_Color"], a)
        self.put(ins["B_Color"], b)
        return [s for s in nd.outputs if s.identifier == "Result_Color"][0]

    def noise(self, scale, detail=3.0, rough=0.55, dist=0.0, vec=None):
        nd = self.new("ShaderNodeTexNoise")
        self.put(nd.inputs["Vector"], vec if vec is not None else self.pos())
        nd.inputs["Scale"].default_value = scale
        nd.inputs["Detail"].default_value = detail
        nd.inputs["Roughness"].default_value = rough
        nd.inputs["Distortion"].default_value = dist
        return nd.outputs["Fac"]

    def warp(self, amount=0.3, scale=2.5):
        nz = self.new("ShaderNodeTexNoise")
        self.put(nz.inputs["Vector"], self.pos())
        nz.inputs["Scale"].default_value = scale
        nz.inputs["Detail"].default_value = 2.0
        sc = self.new("ShaderNodeVectorMath", operation="SCALE")
        self.L.new(nz.outputs["Color"], sc.inputs[0])
        sc.inputs["Scale"].default_value = amount
        add = self.new("ShaderNodeVectorMath", operation="ADD")
        self.L.new(self.pos(), add.inputs[0])
        self.L.new(sc.outputs[0], add.inputs[1])
        return add.outputs[0]

    def edge(self, scale, vec=None):
        nd = self.new("ShaderNodeTexVoronoi", feature="DISTANCE_TO_EDGE")
        self.put(nd.inputs["Vector"], vec if vec is not None else self.pos())
        nd.inputs["Scale"].default_value = scale
        return nd.outputs["Distance"]

    def wave(self, scale, dist, detail=2.0, direction="Z", vec=None):
        nd = self.new("ShaderNodeTexWave", wave_type="BANDS", bands_direction=direction)
        self.put(nd.inputs["Vector"], vec if vec is not None else self.pos())
        nd.inputs["Scale"].default_value = scale
        nd.inputs["Distortion"].default_value = dist
        nd.inputs["Detail"].default_value = detail
        return nd.outputs["Fac"]

    def attr(self, name):
        return self.new("ShaderNodeAttribute", attribute_name=name).outputs["Fac"]

    def ao(self, dist=0.45, samples=16):
        nd = self.new("ShaderNodeAmbientOcclusion")
        nd.samples = samples
        nd.inputs["Distance"].default_value = dist
        return nd.outputs["AO"]

    def nz(self):
        geo = self.new("ShaderNodeNewGeometry")
        sep = self.new("ShaderNodeSeparateXYZ")
        self.L.new(geo.outputs["Normal"], sep.inputs[0])
        return sep.outputs["Z"]


def sh_chitin(g, P):
    ao, nz, rim = g.ao(), g.nz(), g.attr("rim")
    n1 = g.noise(1.6, 3.0, 0.55)
    n2 = g.noise(9.0, 4.0, 0.6)
    streak = g.noise(3.0, 2.0, 0.5, dist=2.5)
    col = g.mix(g.mr(n1, 0.32, 0.68), P["chitin_dark"], P["chitin"])
    col = g.mix(g.mr(streak, 0.55, 0.7, 0.0, 0.35), col, P["chitin_hi"])
    col = g.mix(g.mr(nz, 0.15, 0.95, 0.0, 0.5), col, P["chitin_hi"])
    col = g.mix(g.mr(n2, 0.62, 0.74, 0.0, 0.3), col, P["chitin_hi"])
    bone = g.mix(g.mr(n2, 0.3, 0.7), P["bone_base"], P["bone"])
    col = g.mix(g.mr(rim, 0.62, 0.95), col, bone)
    col = g.mix(g.mr(ao, 0.25, 0.9, 0.85, 0.0), col, P["chitin_deep"])
    rough = g.math("ADD", g.mr(n2, 0.2, 0.8, 0.22, 0.34), g.mr(rim, 0.6, 0.95, 0.0, 0.2))
    height = g.math("ADD", g.math("MULTIPLY", n2, 0.5), g.math("MULTIPLY", streak, 0.4))
    return col, rough, height, 0.35


def sh_flesh(g, P):
    ao = g.ao()
    w = g.wave(2.6, 9.0, 3.0, "Z", g.warp(0.55, 1.3))
    n1 = g.noise(3.0, 3.0, 0.55)
    veins = g.mr(g.edge(3.5, g.warp(0.35, 2.0)), 0.0, 0.04, 1.0, 0.0)
    col = g.mix(g.mr(w, 0.1, 0.9, 0.25, 0.8), P["flesh_dark"], P["flesh"])
    col = g.mix(g.mr(n1, 0.55, 0.75, 0.0, 0.45), col, P["flesh_hi"])
    col = g.mix(g.math("MULTIPLY", veins, 0.55), col, P["flesh_deep"])
    col = g.mix(g.mr(ao, 0.2, 0.9, 0.9, 0.0), col, P["flesh_deep"])
    rough = g.mr(n1, 0.2, 0.8, 0.28, 0.42)
    height = g.math("SUBTRACT", g.math("MULTIPLY", w, 0.45), g.math("MULTIPLY", veins, 0.3))
    return col, rough, height, 0.55


def sh_bone(g, P):
    ao, t = g.ao(), g.attr("along")
    n1 = g.noise(7.0, 3.0, 0.6)
    rings = g.math("SINE", g.math("MULTIPLY", t, 55.0))
    col = g.mix(g.mr(t, 0.0, 0.75), P["bone_base"], P["bone"])
    col = g.mix(g.mr(rings, 0.55, 1.0, 0.0, 0.22), col, P["bone_dark"])
    col = g.mix(g.mr(n1, 0.56, 0.78, 0.0, 0.3), col, P["bone_dark"])
    col = g.mix(g.mr(ao, 0.25, 0.9, 0.8, 0.0), col, P["bone_deep"])
    rough = g.mr(n1, 0.2, 0.8, 0.42, 0.58)
    height = g.math("ADD", g.math("MULTIPLY", rings, 0.25), g.math("MULTIPLY", n1, 0.6))
    return col, rough, height, 0.35


def sh_creep(g, P):
    ao, rim = g.ao(), g.attr("rim")
    veins = g.mr(g.edge(1.8, g.warp(0.5, 1.5)), 0.0, 0.05, 1.0, 0.0)
    n1 = g.noise(4.0, 3.0, 0.55)
    col = g.mix(g.mr(n1, 0.3, 0.7), P["creep_dark"], P["creep"])
    col = g.mix(g.mr(n1, 0.6, 0.78, 0.0, 0.45), col, P["creep_hi"])
    col = g.mix(g.math("MULTIPLY", veins, 0.75), col, P["creep_vein"])
    col = g.mix(g.mr(rim, 0.5, 1.0, 0.0, 0.8), col, P["creep_vein"])
    col = g.mix(g.mr(ao, 0.2, 0.9, 0.7, 0.0), col, P["creep_dark"])
    rough = g.mr(n1, 0.2, 0.8, 0.62, 0.8)
    return col, rough, veins, 0.5


def sh_glow(g, P):
    ao = g.ao(0.3)
    veins = g.mr(g.edge(5.0, g.warp(0.25, 3.0)), 0.0, 0.03, 1.0, 0.0)
    n1 = g.noise(5.0, 3.0, 0.55)
    col = g.mix(g.mr(n1, 0.3, 0.7), P["glow_mid"], P["glow"])
    col = g.mix(g.mr(n1, 0.6, 0.78, 0.0, 0.55), col, P["glow_hi"])
    col = g.mix(g.math("MULTIPLY", veins, 0.7), col, P["glow_vein"])
    col = g.mix(g.mr(ao, 0.2, 0.85, 0.75, 0.0), col, P["glow_vein"])
    return col, 0.25, g.math("SUBTRACT", 1.0, veins), 0.3


def sh_membrane(g, P):
    veins = g.mr(g.edge(3.0, g.warp(0.6, 1.8)), 0.0, 0.016, 1.0, 0.0)
    n1 = g.noise(3.0, 3.0, 0.55)
    col = g.mix(g.mr(n1, 0.3, 0.7), P["memb_a"], P["memb_b"])
    col = g.mix(g.math("MULTIPLY", veins, 0.42), col, P["memb_vein"])
    return col, 0.18, veins, 0.35


SHADERS = {"chitin": sh_chitin, "flesh": sh_flesh, "bone": sh_bone, "creep": sh_creep, "glow": sh_glow,
           "core": sh_glow, "membrane": sh_membrane}
FLAT = {"chitin": "#5A3378", "flesh": "#7A2434", "bone": "#C8B898", "creep": "#1E1226", "glow": "#8CFF3A",
        "core": "#8CFF3A", "membrane": "#D0DAA4", "team": TEAM_GREY}


def bake_material(kind, P, target):
    m = bpy.data.materials.new("bake_" + kind)
    m.use_nodes = True
    g = G(m)
    col, rough, height, strength = SHADERS[kind](g, P)
    b = g.n["Principled BSDF"]
    g.put(b.inputs["Base Color"], col)
    g.put(b.inputs["Roughness"], rough)
    bump = g.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = 0.02
    g.put(bump.inputs["Height"], height)
    g.L.new(bump.outputs["Normal"], b.inputs["Normal"])
    tex = g.new("ShaderNodeTexImage")
    tex.image = target
    tex.name = "bake_target"
    for nd in g.n:
        nd.select = False
    tex.select = True
    g.n.active = tex
    return m


def flat_material(kind):
    m = bpy.data.materials.new("flat_" + kind)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    c = hexc(FLAT[kind])
    b.inputs["Base Color"].default_value = c
    b.inputs["Roughness"].default_value = 0.4
    if kind in ("glow", "core"):
        b.inputs["Emission Color"].default_value = c
        b.inputs["Emission Strength"].default_value = 2.0
    return m


def team_material():
    m = bpy.data.materials.new("team")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = hexc(TEAM_GREY)
    b.inputs["Roughness"].default_value = 0.4
    return m


def final_material(name, imgs, kind):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    g = G(m)
    b = g.n["Principled BSDF"]
    c = g.new("ShaderNodeTexImage")
    c.image = imgs["col"]
    g.L.new(c.outputs["Color"], b.inputs["Base Color"])
    r = g.new("ShaderNodeTexImage")
    r.image = imgs["rough"]
    sep = g.new("ShaderNodeSeparateColor")
    g.L.new(r.outputs["Color"], sep.inputs["Color"])
    g.L.new(sep.outputs["Green"], b.inputs["Roughness"])
    nm = g.new("ShaderNodeTexImage")
    nm.image = imgs["nrm"]
    nmap = g.new("ShaderNodeNormalMap")
    g.L.new(nm.outputs["Color"], nmap.inputs["Color"])
    g.L.new(nmap.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Metallic"].default_value = 0.0
    if kind == "glow":
        g.L.new(c.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = 2.5
    elif kind == "membrane":
        # translucent, not emissive: only materials named glow* emit (the game pulses those)
        b.inputs["Alpha"].default_value = 0.6
        b.inputs["Emission Strength"].default_value = 0.0
        m.surface_render_method = "BLENDED"
    return m


# --- join, unwrap, bake ---------------------------------------------------------------------------

def select_only(objs, active=None):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or objs[0]


def join(objs, name):
    select_only(objs)
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name
    return ob


def unwrap(ob, shrink_mats=(), shrink=0.4):
    select_only([ob])
    bpy.context.scene.tool_settings.use_uv_select_sync = True
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(58), island_margin=0.002, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.object.mode_set(mode="OBJECT")
    me = ob.data
    uv = me.uv_layers.active.data
    for p in me.polygons:
        if p.material_index in shrink_mats:
            for li in p.loop_indices:
                uv[li].uv = uv[li].uv * shrink
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")


def use_gpu():
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == "METAL"
        sc.cycles.device = "GPU"
    except Exception as e:  # noqa: BLE001
        print("[void] GPU unavailable, baking on CPU:", e)
        sc.cycles.device = "CPU"


def bake(ob, bid, res):
    sc = bpy.context.scene
    use_gpu()
    sc.cycles.use_denoising = False
    sc.render.bake.margin = max(4, res // 128)
    sc.render.bake.use_clear = True
    imgs = {}
    for t in ("col", "rough", "nrm"):
        img = bpy.data.images.new(f"{bid}_{t}", res, res, alpha=False)
        if t != "col":
            img.colorspace_settings.name = "Non-Color"
        imgs[t] = img
    nodes = [m.node_tree.nodes["bake_target"] for m in ob.data.materials if m and m.node_tree and "bake_target" in m.node_tree.nodes]
    select_only([ob])
    for t, typ, samples, kw in (("col", "DIFFUSE", 16, dict(pass_filter={"COLOR"})),
                                ("rough", "ROUGHNESS", 1, {}),
                                ("nrm", "NORMAL", 1, dict(normal_space="TANGENT"))):
        for nd in nodes:
            nd.image = imgs[t]
        sc.cycles.samples = samples
        t0 = time.time()
        bpy.ops.object.bake(type=typ, margin=sc.render.bake.margin, use_clear=True, **kw)
        print(f"[void] baked {t} in {time.time() - t0:.1f}s")
    os.makedirs(CACHE, exist_ok=True)
    for t, img in imgs.items():
        img.filepath_raw = os.path.join(CACHE, f"{bid}_{t}.png")
        img.file_format = "PNG"
        img.save()
    return imgs


def remap_materials(ob, mapping):
    """mapping: old slot index -> final material; merges duplicate slots."""
    finals = []
    for i in range(len(ob.data.materials)):
        m = mapping[i]
        if m not in finals:
            finals.append(m)
    idx = np.zeros(len(ob.data.polygons), dtype=np.int32)
    ob.data.polygons.foreach_get("material_index", idx)
    lut = np.array([finals.index(mapping[i]) for i in range(len(ob.data.materials))], dtype=np.int32)
    idx = lut[idx]
    ob.data.materials.clear()
    for m in finals:
        ob.data.materials.append(m)
    ob.data.polygons.foreach_set("material_index", idx)
    ob.data.update()


def split_material(ob, mat_name, new_name):
    """Moves the faces using `mat_name` into their own object (the pod's glow_core)."""
    me = ob.data
    mi = [i for i, m in enumerate(me.materials) if m and m.name == mat_name][0]
    for p in me.polygons:
        p.select = p.material_index == mi
    select_only([ob])
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_mode(type="FACE")
    bpy.ops.mesh.separate(type="SELECTED")
    bpy.ops.object.mode_set(mode="OBJECT")
    new = [o for o in bpy.context.selected_objects if o is not ob][0]
    new.name = new_name
    new.data.name = new_name
    # tidy both slot lists
    for o, keep in ((ob, lambda m: m.name != mat_name), (new, lambda m: m.name == mat_name)):
        used = {p.material_index for p in o.data.polygons}
        mapping = {}
        for i, m in enumerate(o.data.materials):
            mapping[i] = m
        finals = [o.data.materials[i] for i in sorted(used)]
        lut = {i: finals.index(o.data.materials[i]) for i in sorted(used)}
        idx = [lut[p.material_index] for p in o.data.polygons]
        o.data.materials.clear()
        for m in finals:
            o.data.materials.append(m)
        o.data.polygons.foreach_set("material_index", idx)
    return new


def strip_attrs(ob):
    for name in ("along", "rim"):
        a = ob.data.attributes.get(name)
        if a:
            ob.data.attributes.remove(a)


# --- review rendering -----------------------------------------------------------------------------

def look_at(ob, target):
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat("-Z", "Y").to_euler()


def sun(name, direction, color, strength, angle=0.15):
    ld = bpy.data.lights.new(name, "SUN")
    ld.color = color
    ld.energy = strength
    ld.angle = angle
    ob = link(bpy.data.objects.new(name, ld))
    ob.rotation_euler = Vector(direction).normalized().to_track_quat("Z", "Y").to_euler()
    return ob


def plain(name, hexcol, rough=0.9, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = hexc(hexcol)
    b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = hexc(hexcol)
        b.inputs["Emission Strength"].default_value = emit
    return m


def stage(F_list=None, ground=True):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.eevee.taa_render_samples = 48
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.16, 0.17, 0.2, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
    sc.world = w
    sun("key", (-0.55, -0.8, 1.0), (1.0, 0.88, 0.74), 3.6, 0.12)
    sun("rim", (0.75, 0.9, 0.55), (0.62, 0.76, 1.0), 2.4, 0.2)
    sun("fill", (0.9, -0.5, 0.35), (0.85, 0.85, 0.95), 0.6, 0.5)
    stage_objs = []
    if ground:
        bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.002))
        g = bpy.context.active_object
        g.name = "ground"
        g.data.materials.append(plain("ground", "#5C554B", 0.95))
        stage_objs.append(g)
        line = plain("footprint", "#E8E4DA", 0.6, emit=0.4)
        for cx, F in (F_list or []):
            for (x, y, sx, sy) in ((0, -F / 2, F, 0.035), (0, F / 2, F, 0.035), (-F / 2, 0, 0.035, F), (F / 2, 0, 0.035, F)):
                bpy.ops.mesh.primitive_cube_add(size=1, location=(cx + x, y, 0.0))
                c = bpy.context.active_object
                c.scale = (sx, sy, 0.004)
                c.data.materials.append(line)
                stage_objs.append(c)
    return stage_objs


def camera(name, loc, target, lens=50.0, ortho=None):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_end = 500
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    ob = link(bpy.data.objects.new(name, cd))
    ob.location = loc
    look_at(ob, target)
    bpy.context.scene.camera = ob
    return ob


def model_bounds(objs):
    pts = []
    for o in objs:
        if o.type != "MESH":
            continue
        mw = o.matrix_world
        pts += [mw @ v.co for v in o.data.vertices]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi, pts


def render(path, w, h, transparent=False):
    sc = bpy.context.scene
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def view_dir(az_deg, el_deg):
    az, el = math.radians(az_deg), math.radians(el_deg)
    return Vector((-math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))


def fit_ortho(cam, pts, pad=1.06):
    view = cam.matrix_world.inverted()
    cs = [view @ p for p in pts]
    x0, x1 = min(c.x for c in cs), max(c.x for c in cs)
    y0, y1 = min(c.y for c in cs), max(c.y for c in cs)
    cam.data.ortho_scale = max(x1 - x0, y1 - y0) * pad
    cam.location = cam.matrix_world @ Vector(((x0 + x1) / 2, (y0 + y1) / 2, 0))


def review_views(bid, model_objs, folder, F):
    """Three-quarter view, the game camera view and the icon, then a sheet of all three."""
    os.makedirs(folder, exist_ok=True)
    stage_objs = stage([(0.0, F)])
    lo, hi, pts = model_bounds(model_objs)
    H = hi.z
    tgt = Vector((0, 0, H * 0.42))
    rad = max((p - tgt).length for p in pts)
    d = view_dir(40, 26)
    cam = camera("cam34", tgt + d * (rad / math.sin(math.radians(17)) * 1.0), tgt, lens=58)
    p34 = os.path.join(folder, f"{bid}_three_quarter.png")
    render(p34, 512, 512)
    el = math.radians(55)
    cam = camera("camgame", Vector((0, -25 * math.cos(el), 25 * math.sin(el))), Vector((0, 0, 0.5)), lens=35)
    pg = os.path.join(folder, f"{bid}_game.png")
    render(pg, 512, 288)
    cam = camera("camfront", tgt + view_dir(0, 12) * (rad / math.sin(math.radians(17))), tgt, lens=58)
    pf = os.path.join(folder, f"{bid}_front.png")
    render(pf, 256, 256)
    for o in stage_objs:
        o.hide_render = True
    cam = camera("camicon", Vector((0, 0, 0)) + view_dir(40, 24) * 30, tgt, ortho=10)
    cam.location = tgt + view_dir(40, 24) * 30
    look_at(cam, tgt)
    bpy.context.view_layer.update()
    fit_ortho(cam, pts)
    pi = os.path.join(folder, f"{bid}_icon.png")
    render(pi, 256, 256, transparent=True)
    for o in stage_objs:
        o.hide_render = False
    sheet(os.path.join(folder, f"{bid}_sheet.png"), p34, pg, pi, pf)
    return pi


def load_px(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    a = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(h, w, 4)


def sheet(out, p34, pg, pi, pf):
    """One review image: three-quarter (left), front and icon (top right), game camera (bottom right)."""
    W, H = 1024, 544
    S = np.zeros((H, W, 4), dtype=np.float32)
    S[..., :3] = 0.2
    S[..., 3] = 1

    def put(px, x, y):  # x, y from the top left
        h, w = px.shape[:2]
        r0 = H - y - h
        al = px[..., 3:4]
        S[r0:r0 + h, x:x + w, :3] = px[..., :3] * al + S[r0:r0 + h, x:x + w, :3] * (1 - al)

    put(load_px(p34), 0, 0)
    put(load_px(pf), 512, 0)
    put(load_px(pi), 768, 0)
    put(load_px(pg), 512, 256)
    img = bpy.data.images.new("sheet", W, H, alpha=True)
    img.pixels.foreach_set(S.ravel())
    img.filepath_raw = out
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


# --- pipeline -------------------------------------------------------------------------------------

def build_parts(bid):
    reset()
    spec = BUILDINGS[bid]
    rr = random.Random(spec["seed"])
    spec["fn"](rr)
    finish_parts(spec)
    return spec


def fast(bid, round_name):
    spec = build_parts(bid)
    mats = {}
    for o in parts():
        k = o["kind"]
        if k not in mats:
            mats[k] = flat_material(k)
        o.data.materials.append(mats[k])
        o.data.shade_smooth()
    objs = parts()
    review_views(bid, objs, os.path.join(REVIEW, round_name), spec["F"])


def produce(bid, round_name):
    t0 = time.time()
    spec = build_parts(bid)
    P = palette(bid)
    dummy = bpy.data.images.new("dummy", 8, 8)
    kinds = sorted({o["kind"] for o in parts()})
    bake_mats = {k: bake_material(k, P, dummy) for k in kinds if k != "team"}
    team = team_material() if "team" in kinds else None
    for o in parts():
        o.data.materials.append(team if o["kind"] == "team" else bake_mats[o["kind"]])
    body = join([o for o in parts() if o["kind"] != "team"], bid)
    me = body.data
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(62))
    creep_slots = [i for i, m in enumerate(me.materials) if m.name == "bake_creep"]
    unwrap(body, shrink_mats=creep_slots, shrink=0.4)
    imgs = bake(body, bid, TEX)
    short = bid.split("_", 1)[1]
    finals = {
        "skin": final_material(f"{bid}_skin", imgs, "skin"),
        "glow": final_material(f"glow_{short}", imgs, "glow"),
        "core": final_material("glow_core", imgs, "glow"),
        "membrane": final_material(f"{bid}_membrane", imgs, "membrane"),
    }
    group = {"chitin": "skin", "flesh": "skin", "bone": "skin", "creep": "skin", "glow": "glow", "core": "core",
             "membrane": "membrane"}
    mapping = {i: finals[group[m.name[5:]]] for i, m in enumerate(me.materials)}
    remap_materials(body, mapping)
    teams = [o for o in parts() if o["kind"] == "team" and o is not body]
    for o in teams:
        o.data.shade_smooth()
        if "UVMap" not in o.data.uv_layers:
            o.data.uv_layers.new(name="UVMap")
    if body.data.uv_layers.active.name != "UVMap":
        body.data.uv_layers.active.name = "UVMap"
    if teams:
        select_only([body] + teams, active=body)
        bpy.ops.object.join()
        body = bpy.context.view_layer.objects.active
    for v in body.data.vertices:
        if v.co.z < 0.0:
            v.co.z = 0.0
    strip_attrs(body)
    for m in list(bpy.data.materials):
        if m.users == 0:
            bpy.data.materials.remove(m)
    out_objs = [body]
    if "core" in kinds:
        core = split_material(body, "glow_core", "glow_core")
        strip_attrs(core)
        lo, hi, _ = model_bounds([core])
        # pivot the core on its main (largest, central) sac so a pulse by scale stays in place
        c = STATE.get("core_pivot", Vector((0.0, 0.04, 1.05))).copy()
        core.data.transform(Matrix.Translation(-c))
        core.location = c
        core.parent = body
        out_objs.append(core)
    # report and export
    bpy.context.view_layer.update()
    tris = sum(tri_count(o) for o in out_objs)
    lo, hi, _ = model_bounds(out_objs)
    os.makedirs(MODELS, exist_ok=True)
    path = os.path.join(MODELS, bid + ".glb")
    select_only(out_objs, active=body)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True,
                              export_yup=True, export_cameras=False, export_lights=False, export_animations=False,
                              export_image_format="JPEG", export_image_quality=90, export_jpeg_quality=90,
                              export_extras=False, export_attributes=False)
    mats = sorted({m.name for o in out_objs for m in o.data.materials})
    print(f"[void] {bid}: tris={tris} size=({hi.x - lo.x:.2f},{hi.y - lo.y:.2f},{hi.z - lo.z:.2f}) "
          f"min=({lo.x:.2f},{lo.y:.2f},{lo.z:.3f}) max=({hi.x:.2f},{hi.y:.2f},{hi.z:.2f}) mats={mats} "
          f"glb={os.path.getsize(path) / 1e6:.2f}MB in {time.time() - t0:.0f}s")
    review_glb(bid, round_name)


def review_glb(bid, round_name):
    """Renders the exported GLB as the game will get it, and writes the icon."""
    reset()
    bpy.ops.import_scene.gltf(filepath=os.path.join(MODELS, bid + ".glb"))
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    tris = sum(tri_count(o) for o in objs)
    lo, hi, _ = model_bounds(objs)
    creep_lim = BUILDINGS[bid]["F"] / 2 + 0.3
    print(f"[void] {bid} GLB check: objects={[o.name for o in objs]} tris={tris} "
          f"x=({lo.x:.2f},{hi.x:.2f}) y=({lo.y:.2f},{hi.y:.2f}) z=({lo.z:.3f},{hi.z:.2f}) creep_ok={max(-lo.x, hi.x, -lo.y, hi.y) <= creep_lim}")
    icon = review_views(bid, objs, os.path.join(REVIEW, round_name), BUILDINGS[bid]["F"])
    os.makedirs(ICONS, exist_ok=True)
    import shutil
    shutil.copyfile(icon, os.path.join(ICONS, bid + ".png"))


def lineup(round_name):
    reset()
    xs, x = [], 0.0
    order = ["void_pod", "void_maw", "void_nest", "void_hive", "void_warren", "void_aerie", "void_abyss"]
    for bid in order:
        F = BUILDINGS[bid]["F"]
        x += F / 2
        before = set(bpy.context.scene.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(MODELS, bid + ".glb"))
        for o in set(bpy.context.scene.objects) - before:
            if o.parent is None:
                o.location.x += x
        xs.append((x, F))
        x += F / 2 + 1.6
    shift = x / 2 - 0.8
    for o in bpy.context.scene.objects:
        if o.parent is None:
            o.location.x -= shift
    stage([(cx - shift, F) for cx, F in xs])
    el = math.radians(55)
    for dist, name in ((40, "lineup_game_40m"), (25, "lineup_game_25m")):
        camera("cam", Vector((0, -dist * math.cos(el), dist * math.sin(el))), Vector((0, 0, 0.5)), lens=35)
        render(os.path.join(REVIEW, round_name, name + ".png"), 1024, 576)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    which = [a for a in argv if not a.startswith("--")]
    round_name = "latest"
    if "--round" in argv:
        round_name = argv[argv.index("--round") + 1]
        which = [a for a in which if a != round_name]
    ids = list(BUILDINGS) if (not which or which == ["all"]) else which
    for bid in ids:
        if bid not in BUILDINGS:
            raise SystemExit(f"unknown id {bid}; one of {list(BUILDINGS)}")
    for bid in ids:
        if "--fast" in argv:
            fast(bid, "fast")
        else:
            produce(bid, round_name)
    if "--lineup" in argv:
        lineup(round_name)


if __name__ == "__main__":
    main()
