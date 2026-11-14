"""Void ground units for Shardfall: five rigged, animated swarm creatures in the family of
art/ref/void_style_reference.png (glossy purple chitin plates with bone rims, bone spikes and blades,
crimson flesh in the gaps, acid-green glowing sacs and eyes; insectoid, predatory, grown not built).

    Blender --background --factory-startup --python-exit-code 1 --python art/void_units/build.py -- <id|all|lineup|verify> [--round N] [--no-render]

ids: void_drudge (worker grub-beetle), void_spitter (ranged acid spitter), void_mauler (scythe-armed
brute), void_acidback (armoured acid-spraying beetle beast), void_spinefiend (artillery quadruped with a
fan of bone spines). `lineup` renders the five exported GLBs side by side from the game camera at 25 and
40 m; `verify` re-imports every GLB into an empty scene and lists its animations.

Writes assets/models/<id>.glb, assets/icons/<id>.png (256 px, transparent, three-quarter from the
front-left), review renders into art/void_units/review/round<N>/ (front and back three-quarters, the game
camera at 55 degrees from 25 m, an animation contact sheet) and art/void_units/review/<id>_stats.json.

Contract (docs/ART_SPEC.md): metres, front -Y, lowest point z = 0, centred in X and Y. Each GLB holds one
armature object `rig` (24 bones at most, `root` at the ground centre) and one skinned mesh named after the
unit, rigidly weighted (every part 100 % on one bone; the Spinefiend tail is blended). Three materials:
`void_unit` (a 256 px gradient palette: one column per colour ramp, UVs at the column centre with v along the
ramp, plus a matching roughness texture), `team` (light grey, recoloured in game) and `glow_acid` (the
palette's green ramp as base and emission colour). Three actions, exported as glTF animations:
`idle_loop`, `walk_loop` (one gait cycle, in place) and `attack` (returns to the rest pose); the rest
pose is the modelled pose.

Animation is posed procedurally: FK rotations for bodies, heads, jaws, sacs and arms, and an analytic
two-bone IK for every leg so feet stay planted while bodies bob and lunge; a key on every frame (30 fps).
Shared helpers (staging, camera fitting, renders) come from art/ambron_vehicles/build.py.
"""
import importlib.util
import json
import math
import os
import struct
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MODELS = os.path.join(ROOT, "assets", "models")
ICONS = os.path.join(ROOT, "assets", "icons")
CACHE = os.path.join(HERE, "cache")
REVIEW = os.path.join(HERE, "review")
sys.dont_write_bytecode = True                 # no __pycache__ beside the vehicle script
_spec = importlib.util.spec_from_file_location("ambron_vehicles_build",
                                               os.path.join(os.path.dirname(HERE), "ambron_vehicles", "build.py"))
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)

IDS = ("void_drudge", "void_spitter", "void_mauler", "void_acidback", "void_spinefiend")
FPS = 30
# seconds per clip
CLIPS = {
    "void_drudge":     {"idle_loop": 2.4, "walk_loop": 0.7, "attack": 0.5},
    "void_spitter":    {"idle_loop": 2.4, "walk_loop": 0.8, "attack": 0.5},
    "void_mauler":     {"idle_loop": 2.8, "walk_loop": 0.9, "attack": 0.6},
    "void_acidback":   {"idle_loop": 2.4, "walk_loop": 0.8, "attack": 0.5},
    "void_spinefiend": {"idle_loop": 2.8, "walk_loop": 1.0, "attack": 0.6},
}
# the attack's wind-up and strike moments (fractions of the clip), for the contact sheet
ATTACK_MARKS = {
    "void_drudge": (0.40, 0.58), "void_spitter": (0.36, 0.50), "void_mauler": (0.40, 0.55),
    "void_acidback": (0.36, 0.52), "void_spinefiend": (0.40, 0.50),
}

# --- palette (ART_SPEC Void look) ---------------------------------------------------------------------
# One 32 px column per ramp in a 256 x 256 texture; v runs from the ramp's start (0) to its end (1).
COLS = [
    # chitin plates: purple body, a lighter band, then a bone rim at v = 1
    ("plate", [(0.0, "#3A2050"), (0.45, "#5A3378"), (0.70, "#6B3C8A"), (0.84, "#8E5BB0"), (0.91, "#BCA58F"),
               (1.0, "#E2D4B6")]),
    # limbs and heads: deep purple to highlight
    ("chitin", [(0.0, "#1E0E28"), (0.35, "#3A2050"), (0.70, "#5A3378"), (1.0, "#8E5BB0")]),
    # bone: darker base to bright tip
    ("bone", [(0.0, "#5A4A36"), (0.30, "#9C8A6A"), (0.72, "#D8C8A8"), (1.0, "#F2EAD6")]),
    # crimson flesh
    ("flesh", [(0.0, "#2A0812"), (0.35, "#5E1A2A"), (0.75, "#8A2C3C"), (1.0, "#B04C60")]),
    # mouths and throats
    ("maw", [(0.0, "#0C0306"), (0.60, "#3A0A18"), (1.0, "#7A1E30")]),
    # acid glow (used by glow_acid only)
    ("glow", [(0.0, "#2C6410"), (0.40, "#62D622"), (0.72, "#8CFF3A"), (1.0, "#E2FFB4")]),
]
ROUGH = {
    "plate": [(0.0, 0.34), (0.84, 0.24), (0.91, 0.48), (1.0, 0.50)],
    "chitin": [(0.0, 0.42), (1.0, 0.28)],
    "bone": [(0.0, 0.62), (1.0, 0.44)],
    "flesh": [(0.0, 0.50), (1.0, 0.34)],
    "maw": [(0.0, 0.60), (1.0, 0.48)],
    "glow": [(0.0, 0.30), (1.0, 0.20)],
}
NCOL = 8
COL_INDEX = {k: i for i, (k, _) in enumerate(COLS)}
TEAM = "#C9CDD3"
GLOW_STRENGTH = 2.4


def col_uv(key, t):
    return ((COL_INDEX[key] + 0.5) / NCOL, 0.02 + 0.96 * min(1.0, max(0.0, t)))


def palette_images():
    h, cw = 256, 32
    col = np.ones((h, NCOL * cw, 4), np.float32)
    mr = np.ones((h, NCOL * cw, 4), np.float32)
    vs = (np.arange(h) + 0.5) / h
    for ci in range(NCOL):
        key, stops = COLS[min(ci, len(COLS) - 1)]
        sv = [s for s, _ in stops]
        rgb = np.array([V.srgb(c) for _, c in stops])
        for ch in range(3):
            col[:, ci * cw:(ci + 1) * cw, ch] = np.interp(vs, sv, rgb[:, ch])[:, None]
        rs = ROUGH[key]
        rough = np.interp(vs, [s for s, _ in rs], [r for _, r in rs])
        mr[:, ci * cw:(ci + 1) * cw, 0] = 1.0
        mr[:, ci * cw:(ci + 1) * cw, 1] = rough[:, None]
        mr[:, ci * cw:(ci + 1) * cw, 2] = 0.0
    imgs = []
    for name, px, cs in (("void_unit_palette", col, "sRGB"), ("void_unit_palette_mr", mr, "Non-Color")):
        img = bpy.data.images.new(name, NCOL * cw, h, alpha=False)
        img.colorspace_settings.name = cs
        img.pixels.foreach_set(px.ravel())
        img.pack()
        imgs.append(img)
    return imgs


def make_materials():
    colimg, mrimg = palette_images()
    body, nt, p = V.principled("void_unit")
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image, t.interpolation = colimg, "Linear"
    nt.links.new(t.outputs["Color"], p.inputs["Base Color"])
    t2 = nt.nodes.new("ShaderNodeTexImage")
    t2.image, t2.interpolation = mrimg, "Linear"
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(t2.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], p.inputs["Roughness"])
    p.inputs["Metallic"].default_value = 0.0
    team = V.flat("team", TEAM, 0.42, 0.0)
    glow, nt, p = V.principled("glow_acid")
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image, t.interpolation = colimg, "Linear"
    nt.links.new(t.outputs["Color"], p.inputs["Base Color"])
    nt.links.new(t.outputs["Color"], p.inputs["Emission Color"])
    p.inputs["Emission Strength"].default_value = GLOW_STRENGTH
    p.inputs["Roughness"].default_value = 0.25
    return [body, team, glow]


MAT_INDEX = {"body": 0, "team": 1, "glow": 2}


# --- geometry -----------------------------------------------------------------------------------------
# Parts are plain vertex/face lists with a ramp parameter t per vertex (the palette v coordinate).

class Geo:
    __slots__ = ("v", "f", "t")

    def __init__(self, v, f, t):
        self.v, self.f, self.t = v, f, t

    def xf(self, M):
        self.v = [M @ p for p in self.v]
        return self

    def tmap(self, lo, hi):
        self.t = [lo + (hi - lo) * x for x in self.t]
        return self


def mat4(loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    return (Matrix.Translation(Vector(loc)) @ Euler([math.radians(a) for a in rot], "XYZ").to_matrix().to_4x4()
            @ Matrix.Diagonal((scale[0], scale[1], scale[2], 1.0)))


def frame(p, along, out):
    """Local X across, Y along `along`, Z out of the surface, origin at p."""
    Zv = Vector(out).normalized()
    a = Vector(along)
    Yv = a - Zv * a.dot(Zv)
    if Yv.length < 1e-6:
        Yv = Zv.orthogonal()
    Yv.normalize()
    Xv = Yv.cross(Zv)
    M = Matrix((Xv, Yv, Zv)).transposed().to_4x4()
    M.translation = Vector(p)
    return M


def sphere(seg=12, rings=8):
    v = [Vector((0, 0, -1))]
    for i in range(1, rings):
        th = math.pi * i / rings
        z, r = -math.cos(th), math.sin(th)
        for j in range(seg):
            a = 2 * math.pi * j / seg
            v.append(Vector((r * math.cos(a), r * math.sin(a), z)))
    v.append(Vector((0, 0, 1)))
    top = len(v) - 1
    f = [(0, 1 + (j + 1) % seg, 1 + j) for j in range(seg)]
    for i in range(rings - 2):
        a0, b0 = 1 + i * seg, 1 + (i + 1) * seg
        for j in range(seg):
            k = (j + 1) % seg
            f.append((a0 + j, a0 + k, b0 + k, b0 + j))
    last = 1 + (rings - 2) * seg
    f += [(last + j, last + (j + 1) % seg, top) for j in range(seg)]
    return Geo(v, f, [(p.z + 1) / 2 for p in v])


def ell(c, r, seg=12, rings=8, rot=(0, 0, 0), t=(0.0, 1.0)):
    """An ellipsoid; t runs from its bottom (t[0]) to its top (t[1])."""
    if not isinstance(r, (tuple, list)):
        r = (r, r, r)
    return sphere(seg, rings).tmap(*t).xf(mat4(c, rot, r))


def ell_m(M, r, seg=10, rings=6, t=(0.0, 1.0)):
    """An ellipsoid in a frame (its local Z is the frame's out direction)."""
    return sphere(seg, rings).tmap(*t).xf(M @ Matrix.Diagonal((r[0], r[1], r[2], 1.0)))


def sweep(path, radii, ring=8, flat=1.0, up=(0, 0, 1), t=(0.0, 1.0), ts=None):
    """A tube through `path` with a radius per point (0 = a pointed tip), capped. `flat` squashes the
    cross-section along `up` (blades); t runs along the length unless `ts` gives one value per point."""
    P = [Vector(p) for p in path]
    n = len(P)
    L = [0.0]
    for i in range(1, n):
        L.append(L[-1] + (P[i] - P[i - 1]).length)
    if ts is None:
        ts = [t[0] + (t[1] - t[0]) * l / L[-1] for l in L]
    upv = Vector(up).normalized()
    v, f, tv, rings_ = [], [], [], []
    prevN = None
    for i in range(n):
        T = (P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized()
        N = upv - T * upv.dot(T)
        if N.length < 1e-5:
            N = prevN.copy() if prevN is not None else T.orthogonal()
        N.normalize()
        prevN = N
        B = T.cross(N)
        r = radii[i]
        if r <= 1e-6:
            rings_.append([len(v)])
            v.append(P[i].copy())
            tv.append(ts[i])
            continue
        idx = []
        for k in range(ring):
            a = 2 * math.pi * k / ring
            v.append(P[i] + B * (math.cos(a) * r) + N * (math.sin(a) * r * flat))
            tv.append(ts[i])
            idx.append(len(v) - 1)
        rings_.append(idx)
    for i in range(n - 1):
        A, Bn = rings_[i], rings_[i + 1]
        if len(A) == 1 and len(Bn) == 1:
            continue
        if len(A) == 1:
            f += [(A[0], Bn[(k + 1) % ring], Bn[k]) for k in range(ring)]
        elif len(Bn) == 1:
            f += [(A[k], A[(k + 1) % ring], Bn[0]) for k in range(ring)]
        else:
            f += [(A[k], A[(k + 1) % ring], Bn[(k + 1) % ring], Bn[k]) for k in range(ring)]
    if len(rings_[0]) > 1:
        f.append(tuple(reversed(rings_[0])))
    if len(rings_[-1]) > 1:
        f.append(tuple(rings_[-1]))
    return Geo(v, f, tv)


def spike(base, d, length, r0, bend=(0, 0, 0), segs=4, ring=6, flat=1.0, up=None, t=(0.05, 1.0), sink=0.5):
    """A tapering, optionally bent bone spike from `base` along `d`, sunk a little into the surface."""
    d = Vector(d).normalized()
    bend = Vector(bend)
    pts, rs = [], []
    for i in range(segs + 1):
        s = i / segs
        pts.append(Vector(base) - d * (r0 * sink) + d * (length * s) + bend * (length * s * s))
        rs.append(r0 * (1 - s) ** 0.85)
    return sweep(pts, rs, ring, flat, up if up is not None else d.orthogonal(), t=t)


class Plate:
    """A curved chitin plate with a bone rim: arched across (edges drop by H), shield-shaped outline with a
    rounded front and a pointed back. Origin at the front-centre of the top surface; local Y runs back
    along the plate, Z out. lod 0 = 6 x 5 quads per face, lod 1 = 4 x 3."""
    GRID = {0: ((-1.0, -0.8, -0.42, 0.0, 0.42, 0.8, 1.0), (0.0, 0.12, 0.4, 0.7, 0.9, 1.0)),
            1: ((-1.0, -0.76, 0.0, 0.76, 1.0), (0.0, 0.16, 0.62, 1.0))}

    def __init__(self, W, L, H, thick=0.035, tip=0.25, front=0.8, hook=0.0, droop=0.0, lod=0):
        self.W, self.L, self.H, self.thick = W, L, H, thick
        self.tip, self.front, self.hook, self.droop, self.lod = tip, front, hook, droop, lod

    def hw(self, s):
        if s <= 0.4:
            g = self.front + (1 - self.front) * math.sin(math.pi / 2 * s / 0.4)
        else:
            g = self.tip + (1 - self.tip) * math.cos(math.pi / 2 * (s - 0.4) / 0.6)
        return self.W / 2 * g

    def z(self, u, s):
        return -self.H * u * u + self.hook * s * s - self.droop * (1 - s) ** 2

    def pt(self, u, s):
        return Vector((u * self.hw(s), s * self.L, self.z(u, s)))

    def geo(self):
        PU, PS = self.GRID[self.lod]
        nu, ns = len(PU), len(PS)
        v, tv = [], []
        for j, s in enumerate(PS):
            for i, u in enumerate(PU):
                v.append(self.pt(u, s))
                edge = i in (0, nu - 1) or j in (0, ns - 1)
                near = i in (1, nu - 2) or j in (1, ns - 2)
                tv.append(1.0 if edge else (0.84 if near else 0.52 + 0.14 * abs(u)))
        off = len(v)
        for j, s in enumerate(PS):
            for i, u in enumerate(PU):
                p = v[j * nu + i]
                v.append(Vector((p.x * 0.9, p.y * 0.96 + self.L * 0.02, p.z - self.thick * (0.5 + 0.5 * (1 - u * u)))))
                edge = i in (0, nu - 1) or j in (0, ns - 1)
                tv.append(0.95 if edge else 0.15)

        def top(i, j):
            return j * nu + i

        def bot(i, j):
            return off + j * nu + i
        f = []
        for j in range(ns - 1):
            for i in range(nu - 1):
                f.append((top(i, j), top(i + 1, j), top(i + 1, j + 1), top(i, j + 1)))
                f.append((bot(i, j + 1), bot(i + 1, j + 1), bot(i + 1, j), bot(i, j)))
        loop = ([(i, 0) for i in range(nu)] + [(nu - 1, j) for j in range(1, ns)]
                + [(i, ns - 1) for i in range(nu - 2, -1, -1)] + [(0, j) for j in range(ns - 2, 0, -1)])
        for k in range(len(loop)):
            a, b = loop[k], loop[(k + 1) % len(loop)]
            f.append((top(*b), top(*a), bot(*a), bot(*b)))
        return Geo(v, f, tv)


def ell_normal(c, r, p):
    c, p = Vector(c), Vector(p)
    return Vector(((p.x - c.x) / r[0] ** 2, (p.y - c.y) / r[1] ** 2, (p.z - c.z) / r[2] ** 2)).normalized()


def ell_top(c, r, x, y):
    """The point on top of an ellipsoid above (x, y)."""
    c = Vector(c)
    k = 1 - ((x - c.x) / r[0]) ** 2 - ((y - c.y) / r[1]) ** 2
    return Vector((x, y, c.z + r[2] * math.sqrt(max(0.0, k))))


def mx(v):
    return Vector((-v[0], v[1], v[2]))


def sw(name):
    if name is None:
        return None
    if name in ("L", "R"):
        return "R" if name == "L" else "L"
    if "_L" in name:
        return name.replace("_L", "_R")
    if "_R" in name:
        return name.replace("_R", "_L")
    return name


class Builder:
    def __init__(self):
        self.parts = []       # (Geo, column, material, bone or weight function)
        self.bones = {}       # name -> [head, tail, parent, deform]
        self.legs = []        # IK legs
        self.order = []

    def bone(self, name, head, tail, parent=None, deform=True, mirror=False):
        self.bones[name] = [Vector(head), Vector(tail), parent, deform]
        if mirror:
            self.bones[sw(name)] = [mx(head), mx(tail), sw(parent), deform]

    def add(self, geo, col, bone, mat="body", mirror=False):
        self.parts.append((geo, col, mat, bone))
        if mirror:
            g2 = Geo([mx(p) for p in geo.v], [tuple(reversed(fc)) for fc in geo.f], list(geo.t))
            if callable(bone):
                fn = bone
                b2 = lambda p, fn=fn: {sw(k): w for k, w in fn(mx(p)).items()}
            else:
                b2 = sw(bone)
            self.parts.append((g2, col, mat, b2))

    def plate(self, P, M, bone, col="plate", mirror=False):
        self.add(P.geo().xf(M), col, bone, mirror=mirror)
        return M

    def ik(self, key, upper, lower, foot=None, mode="splay", mirror=True):
        self.legs.append({"key": key, "upper": upper, "lower": lower, "foot": foot, "mode": mode})
        if mirror:
            self.legs.append({"key": sw(key), "upper": sw(upper), "lower": sw(lower), "foot": sw(foot), "mode": mode})

    def insect_leg(self, key, hip, knee, foot, parent, r=(0.05, 0.04, 0.03), ring=8, knee_spike=0.0,
                   claw_frac=0.45, thigh_plate=None):
        """A two-segment arthropod leg (left side, mirrored): chitin thigh, flesh knee, chitin shin ending
        in a bone claw on the ground. Bones leg_<key>_L_1 (hip to knee) and _2 (knee to foot)."""
        u, l = "leg_%s_L_1" % key, "leg_%s_L_2" % key
        self.bone(u, hip, knee, parent, mirror=True)
        self.bone(l, knee, foot, u, mirror=True)
        hip, knee, foot = Vector(hip), Vector(knee), Vector(foot)
        out = Vector((hip.x - 0, 0, 0)).normalized() if abs(hip.x) > 1e-6 else Vector((1, 0, 0))
        mid = (hip + knee) / 2 + Vector((0, 0, 0.25 * r[0]))
        self.add(sweep([hip, mid, knee], [r[0], r[0] * 1.12, r[1]], ring, t=(0.3, 0.8)), "chitin", u, mirror=True)
        self.add(ell(knee, r[1] * 1.12, 8, 6, t=(0.25, 0.85)), "flesh", l, mirror=True)
        cl = knee + (foot - knee) * (1 - claw_frac)
        self.add(sweep([knee, knee + (foot - knee) * 0.5, cl], [r[1], r[1] * 0.95, r[2]], ring, t=(0.75, 0.35)),
                 "chitin", l, mirror=True)
        self.add(sweep([cl - (foot - knee) * 0.06, cl + (foot - cl) * 0.5, foot], [r[2] * 1.05, r[2] * 0.7, 0.0], 6,
                       t=(0.25, 1.0)), "bone", l, mirror=True)
        if knee_spike > 0:
            d = (knee - hip).normalized() + Vector((0, 0, 0.6)) + out * 0.3
            self.add(spike(knee, d, knee_spike, r[1] * 0.55, bend=(0, 0.15, 0)), "bone", l, mirror=True)
        if thigh_plate:
            W, H = thigh_plate
            P = Plate(W, (knee - hip).length * 0.95, H, 0.025, tip=0.4, front=0.7, lod=1)
            M = frame(hip + Vector((0, 0, r[0] * 0.9)), knee - hip, Vector((0, 0, 1)) + out * 0.2)
            self.plate(P, M, u, mirror=True)
        self.ik(key + "_L", u, l)


# --- the creatures --------------------------------------------------------------------------------------
# Each builder fills a Builder in metres with the front at -Y; settling (z = 0, centred) happens later.

def drudge(b):
    b.bone("root", (0, 0, 0), (0, 0.3, 0), None, deform=False)
    b.bone("body", (0, 0.10, 0.30), (0, -0.14, 0.30), "root")
    b.bone("head", (0, -0.20, 0.27), (0, -0.34, 0.27), "body")
    b.bone("abdomen", (0, 0.22, 0.27), (0, 0.44, 0.25), "body")
    b.bone("mand_L", (0.06, -0.34, 0.21), (0.13, -0.45, 0.21), "head", mirror=True)
    b.bone("ant_L", (0.05, -0.31, 0.33), (0.09, -0.39, 0.46), "head", mirror=True)
    # flesh core under the shell
    b.add(ell((0, 0.0, 0.31), (0.28, 0.32, 0.26), 16, 10, t=(0.05, 0.8)), "flesh", "body")
    b.add(ell((0, -0.04, 0.16), (0.20, 0.26, 0.10), 12, 6, t=(0.0, 0.45)), "chitin", "body")      # belly
    # the shell: four overlapping segments down a domed profile
    yc, zc, ay, az = 0.0, 0.30, 0.31, 0.33

    def prof(ph):
        a = math.radians(ph)
        return Vector((0, yc + ay * math.cos(a), zc + az * math.sin(a)))

    def nrm(ph):
        a = math.radians(ph)
        return Vector((0, math.cos(a) / ay, math.sin(a) / az)).normalized()
    segs = [(165, 120, 0.60, 0.22, "f"), (128, 86, 0.70, 0.27, "m"), (94, 52, 0.72, 0.27, "m"),
            (60, 14, 0.62, 0.24, "r")]
    tops = []
    for i, (pa, pb, W, H, _k) in enumerate(segs):
        A, B = prof(pa) + nrm(pa) * 0.025, prof(pb) + nrm(pb) * 0.025
        L = (B - A).length * 1.14
        n = nrm((pa + pb) / 2)
        P = Plate(W, L, H, 0.035, tip=0.62, front=0.86, hook=0.01 if i < 3 else -0.03)
        M = b.plate(P, frame(A, B - A, n), "body")
        tops.append((P, M))
        if i in (1, 2):                               # bone spikes off the shell's flanks
            for s in (0.55,):
                p = M @ P.pt(1.0, s)
                d = M.to_3x3() @ Vector((1.0, 0.45, -0.35))
                b.add(spike(p, d, 0.11, 0.028, bend=(0, 0.04, 0.05)), "bone", "body", mirror=True)
    # team nodules down the spine
    for P, M in tops[:3]:
        p = M @ P.pt(0.0, 0.55)
        R = M.to_3x3()
        b.add(ell_m(frame(p, R @ Vector((0, 1, 0)), R @ Vector((0, 0, 1))), (0.05, 0.06, 0.03)), "flesh", "body",
              mat="team")
    # tail spikes off the last segment
    P, M = tops[3]
    for x in (0.09,):
        p = M @ P.pt(0.25, 0.92)
        b.add(spike(p, M.to_3x3() @ Vector((0.3, 1, 0.2)), 0.09, 0.026), "bone", "body", mirror=True)
    # the harvest sac behind, glowing between flesh ribs
    b.add(ell((0, 0.36, 0.24), (0.17, 0.15, 0.15), 14, 8, t=(0.2, 1.0)), "glow", "abdomen", mat="glow")
    for y, rr in ((0.30, 0.165), (0.40, 0.14)):
        ring = [Vector((rr * 1.02 * math.cos(a), y, 0.24 + rr * 1.02 * math.sin(a))) for a in
                [math.radians(-20 + 22 * k) for k in range(11)]]
        b.add(sweep(ring, [0.022] * len(ring), 6, t=(0.5, 0.8)), "flesh", "abdomen")
    # head: chitin skull with a bone-rimmed plate, two pairs of eyes, a dark maw, sickle mandibles
    b.add(ell((0, -0.31, 0.27), (0.16, 0.13, 0.12), 12, 8, t=(0.2, 0.85)), "chitin", "head")
    P = Plate(0.30, 0.19, 0.08, 0.03, tip=0.6, front=0.7, lod=1)
    b.plate(P, frame((0, -0.43, 0.33), (0, 1, 0.45), (0, -0.4, 1)), "head")
    b.add(ell((0.085, -0.42, 0.30), 0.036, 10, 6, t=(0.7, 1.0)), "glow", "head", mat="glow", mirror=True)
    b.add(ell((0.13, -0.37, 0.33), 0.022, 8, 5, t=(0.7, 1.0)), "glow", "head", mat="glow", mirror=True)
    b.add(ell((0, -0.42, 0.21), (0.075, 0.05, 0.05), 10, 6, t=(0.1, 0.7)), "maw", "head")
    mand = [(0.06, -0.36, 0.21), (0.14, -0.43, 0.215), (0.15, -0.51, 0.21), (0.10, -0.57, 0.205), (0.03, -0.585, 0.20)]
    b.add(sweep(mand, [0.042, 0.04, 0.032, 0.02, 0.0], 8, flat=0.55, t=(0.2, 1.0)), "bone", "mand_L", mirror=True)
    b.add(spike((0.135, -0.47, 0.21), (-1, -0.4, 0), 0.05, 0.016), "bone", "mand_L", mirror=True)
    ant = [(0.05, -0.32, 0.33), (0.08, -0.40, 0.46), (0.13, -0.45, 0.59), (0.20, -0.43, 0.70)]
    b.add(sweep(ant, [0.02, 0.017, 0.012, 0.0], 6, t=(0.0, 0.95)), "bone", "ant_L", mirror=True)
    # six stubby legs, knees poking out under the shell
    b.insect_leg("f", (0.19, -0.15, 0.24), (0.36, -0.25, 0.35), (0.43, -0.33, 0.0), "body", (0.05, 0.04, 0.03))
    b.insect_leg("m", (0.22, 0.01, 0.23), (0.40, 0.01, 0.34), (0.47, 0.03, 0.0), "body", (0.05, 0.04, 0.03))
    b.insect_leg("r", (0.19, 0.17, 0.23), (0.35, 0.27, 0.33), (0.41, 0.36, 0.0), "body", (0.05, 0.04, 0.03))


def spitter(b):
    b.bone("root", (0, 0, 0), (0, 0.3, 0), None, deform=False)
    b.bone("pelvis", (0, 0.06, 0.56), (0, 0.06, 0.70), "root")
    b.bone("chest", (0, 0.04, 0.68), (0, -0.08, 0.92), "pelvis")
    b.bone("head", (0, -0.10, 0.95), (0, -0.30, 0.99), "chest")
    b.bone("jaw", (0, -0.15, 0.93), (0, -0.34, 0.88), "head")
    b.bone("sac", (0, 0.13, 0.58), (0, 0.44, 0.50), "pelvis")
    b.bone("arm_L_1", (0.10, -0.08, 0.84), (0.17, -0.15, 0.70), "chest", mirror=True)
    b.bone("arm_L_2", (0.17, -0.15, 0.70), (0.12, -0.34, 0.72), "arm_L_1", mirror=True)
    hip, knee, ankle, toe = Vector((0.10, 0.06, 0.55)), Vector((0.15, -0.09, 0.35)), Vector((0.15, 0.08, 0.14)), Vector((0.15, -0.12, 0.0))
    b.bone("thigh_L", hip, knee, "pelvis", mirror=True)
    b.bone("shin_L", knee, ankle, "thigh_L", mirror=True)
    b.bone("foot_L", ankle, toe, "shin_L", mirror=True)
    b.ik("L", "thigh_L", "shin_L", "foot_L", mode="plane")
    # pelvis and the acid sac (a glowing abdomen held in chitin bands, a bone stinger at the tip)
    b.add(ell((0, 0.06, 0.57), (0.12, 0.11, 0.10), 12, 7, t=(0.1, 0.7)), "flesh", "pelvis")
    P = Plate(0.27, 0.17, 0.09, 0.03, tip=0.5, front=0.8, lod=1)
    b.plate(P, frame((0, -0.01, 0.67), (0, 1, -0.55), (0, 0.5, 1)), "pelvis")
    b.add(sweep([(0, 0.09, 0.585), (0, 0.17, 0.57)], [0.06, 0.07], 8, t=(0.4, 0.6)), "flesh", "sac")
    SC, SR = Vector((0, 0.29, 0.55)), (0.15, 0.19, 0.15)
    b.add(ell(SC, SR, 14, 9, t=(0.15, 1.0)), "glow", "sac", mat="glow")
    for y in (0.17, 0.29, 0.41):
        p = ell_top(SC, SR, 0.0, y) + Vector((0, 0, 0.012))
        n = ell_normal(SC, SR, p)
        P = Plate(0.34 if y == 0.29 else 0.29, 0.075, 0.15 if y == 0.29 else 0.12, 0.025, tip=0.92, front=0.95, lod=1)
        b.plate(P, frame(p - Vector((0, 0.03, 0)), Vector((0, 1, 0)), n), "sac")
    b.add(spike((0, 0.46, 0.50), (0, 0.7, -0.45), 0.13, 0.032, bend=(0, 0, -0.1)), "bone", "sac")
    # thorax: ribbed flesh with chitin plates down the back, spines, a chest plate
    axis = [Vector((0, 0.04, 0.63)), Vector((0, -0.01, 0.76)), Vector((0, -0.07, 0.88)), Vector((0, -0.10, 0.95))]
    b.add(sweep(axis, [0.10, 0.12, 0.11, 0.07], 10, ts=[0.3, 0.75, 0.3, 0.7]), "flesh", "chest")
    up = (axis[-1] - axis[0]).normalized()
    back = Vector((0, 0.92, 0.40)).normalized()
    for k, s in enumerate((0.92, 0.62, 0.32)):
        c = axis[0] + (axis[-1] - axis[0]) * s
        P = Plate(0.28 - 0.03 * k, 0.17, 0.10, 0.03, tip=0.35, front=0.8, hook=0.02)
        M = b.plate(P, frame(c + back * 0.10, -up, back), "chest")
        b.add(spike(M @ P.pt(0, 0.55), back + up * 0.9, 0.13 - 0.02 * k, 0.026, bend=(0, 0.05, 0)), "bone", "chest")
    P = Plate(0.20, 0.22, 0.06, 0.025, tip=0.5, front=0.7, lod=1)
    fr_ = Vector((0, -0.92, -0.25)).normalized()
    b.plate(P, frame(axis[2] + fr_ * 0.105, -up, fr_), "chest", col="chitin")
    b.add(spike((0.10, -0.01, 0.89), (0.5, 0.35, 1), 0.10, 0.026), "bone", "chest", mirror=True)
    b.add(ell_m(frame((0.105, -0.085, 0.865), (0, 0, 1), (0.6, -0.5, 0.6)), (0.045, 0.045, 0.028)), "flesh", "chest",
          mat="team", mirror=True)
    # head: neck, long skull with a bone-rimmed plate and crest spines, eyes, a glowing throat, the jaw
    b.add(sweep([(0, -0.06, 0.89), (0, -0.11, 0.94), (0, -0.15, 0.97)], [0.065, 0.06, 0.06], 8, ts=[0.3, 0.75, 0.4]),
          "flesh", "head")
    b.add(ell((0, -0.23, 0.99), (0.09, 0.15, 0.075), 12, 8, rot=(8, 0, 0), t=(0.2, 0.9)), "chitin", "head")
    P = Plate(0.20, 0.30, 0.07, 0.03, tip=0.3, front=0.6, hook=0.03, lod=1)
    b.plate(P, frame((0, -0.37, 1.005), (0, 1, 0.16), (0, -0.12, 1)), "head")
    b.add(spike((0, -0.10, 1.03), (0, 0.65, 0.75), 0.21, 0.032, bend=(0, 0.08, -0.03)), "bone", "head")
    b.add(spike((0.05, -0.12, 1.02), (0.3, 0.65, 0.7), 0.15, 0.026, bend=(0, 0.06, -0.02)), "bone", "head", mirror=True)
    b.add(ell((0.055, -0.33, 1.005), 0.026, 8, 6, t=(0.7, 1.0)), "glow", "head", mat="glow", mirror=True)
    b.add(ell((0.075, -0.27, 1.025), 0.018, 8, 5, t=(0.7, 1.0)), "glow", "head", mat="glow", mirror=True)
    b.add(ell((0, -0.25, 0.935), (0.05, 0.09, 0.035), 10, 6, t=(0.5, 1.0)), "glow", "head", mat="glow")
    b.add(ell((0, -0.25, 0.905), (0.07, 0.12, 0.03), 10, 6, t=(0.3, 0.8)), "chitin", "jaw")
    for x, y in ((0.04, -0.31), (0.05, -0.23)):
        b.add(spike((x, y, 0.915), (0, 0, 1), 0.04, 0.012, ring=5, segs=2), "bone", "jaw", mirror=True)
    hook = [(0.06, -0.19, 0.925), (0.10, -0.29, 0.925), (0.075, -0.37, 0.915), (0.03, -0.40, 0.905)]
    b.add(sweep(hook, [0.022, 0.02, 0.012, 0.0], 6, flat=0.6, t=(0.2, 1.0)), "bone", "jaw", mirror=True)
    # raptorial arms: chitin upper arm, bone sickle claw
    b.add(sweep([(0.10, -0.08, 0.84), (0.14, -0.11, 0.77), (0.17, -0.15, 0.70)], [0.038, 0.036, 0.03], 8, t=(0.4, 0.8)),
          "chitin", "arm_L_1", mirror=True)
    b.add(ell((0.17, -0.15, 0.70), 0.032, 8, 5, t=(0.3, 0.8)), "flesh", "arm_L_2", mirror=True)
    blade = [(0.17, -0.15, 0.70), (0.165, -0.25, 0.765), (0.145, -0.33, 0.75), (0.12, -0.36, 0.67)]
    b.add(sweep(blade, [0.03, 0.03, 0.017, 0.0], 8, flat=0.45, up=(1, 0, 0), t=(0.2, 1.0)), "bone", "arm_L_2", mirror=True)
    # digitigrade legs: thigh forward, shin back to a raised ankle, a foot with three toe claws
    b.add(sweep([hip, (hip + knee) / 2 + Vector((0.015, -0.01, 0)), knee], [0.065, 0.062, 0.045], 8, t=(0.35, 0.8)),
          "chitin", "thigh_L", mirror=True)
    P = Plate(0.13, 0.20, 0.04, 0.025, tip=0.35, front=0.7, lod=1)
    b.plate(P, frame(hip + Vector((0.03, -0.035, 0.02)), knee - hip, (0.5, -0.8, 0.3)), "thigh_L", mirror=True)
    b.add(ell(knee, 0.048, 8, 6, t=(0.3, 0.85)), "flesh", "shin_L", mirror=True)
    b.add(sweep([knee, (knee + ankle) / 2, ankle], [0.042, 0.036, 0.03], 8, t=(0.75, 0.4)), "chitin", "shin_L", mirror=True)
    b.add(spike(knee, (0, 0.55, 0.65), 0.09, 0.02, ring=5), "bone", "shin_L", mirror=True)
    b.add(ell(ankle, 0.033, 8, 5, t=(0.3, 0.8)), "flesh", "foot_L", mirror=True)
    ball = Vector((0.15, -0.02, 0.035))
    b.add(sweep([ankle, ball], [0.03, 0.026], 8, t=(0.45, 0.65)), "chitin", "foot_L", mirror=True)
    for dx in (-0.045, 0.0, 0.045):
        b.add(spike(ball, (dx, -1, -0.32), 0.105, 0.022, bend=(0, 0, -0.03)), "bone", "foot_L", mirror=True)
    b.add(spike(ball, (0, 1, -0.4), 0.07, 0.018), "bone", "foot_L", mirror=True)


def mauler(b):
    b.bone("root", (0, 0, 0), (0, 0.3, 0), None, deform=False)
    b.bone("pelvis", (0, 0.14, 0.66), (0, 0.14, 0.82), "root")
    b.bone("chest", (0, 0.10, 0.80), (0, -0.08, 1.18), "pelvis")
    b.bone("head", (0, -0.24, 1.06), (0, -0.44, 1.04), "chest")
    b.bone("jaw", (0, -0.32, 0.99), (0, -0.48, 0.93), "head")
    b.bone("arm_L_1", (0.36, -0.06, 1.20), (0.55, -0.24, 1.27), "chest", mirror=True)
    b.bone("arm_L_2", (0.55, -0.24, 1.27), (0.60, -0.64, 1.30), "arm_L_1", mirror=True)
    hip, knee, ankle, toe = Vector((0.20, 0.14, 0.62)), Vector((0.27, -0.06, 0.38)), Vector((0.27, 0.10, 0.15)), Vector((0.28, -0.16, 0.0))
    b.bone("thigh_L", hip, knee, "pelvis", mirror=True)
    b.bone("shin_L", knee, ankle, "thigh_L", mirror=True)
    b.bone("foot_L", ankle, toe, "shin_L", mirror=True)
    b.ik("L", "thigh_L", "shin_L", "foot_L", mode="plane")
    # pelvis and gut
    b.add(ell((0, 0.14, 0.68), (0.22, 0.19, 0.16), 12, 8, t=(0.1, 0.7)), "flesh", "pelvis")
    for k, (y, z) in enumerate(((0.12, 0.80), (0.26, 0.74))):
        P = Plate(0.48 - 0.06 * k, 0.20, 0.13, 0.035, tip=0.45, front=0.85, lod=1)
        b.plate(P, frame((0, y, z), (0, 1, -0.7), (0, 0.6, 1)), "pelvis")
    b.add(sweep([(0, 0.10, 0.70), (0, 0.0, 0.84), (0, -0.06, 0.98)], [0.17, 0.20, 0.24], 10, ts=[0.3, 0.75, 0.35]),
          "flesh", "chest")
    # the hunched torso: flesh core, a huge dorsal hump of layered plates, pauldrons, spikes
    TC, TR = Vector((0, -0.02, 1.07)), (0.37, 0.31, 0.29)
    b.add(ell(TC, TR, 16, 10, t=(0.1, 0.8)), "flesh", "chest")
    for k, (y, z, W, L, H) in enumerate(((-0.14, 1.36, 0.62, 0.36, 0.20), (0.06, 1.33, 0.66, 0.34, 0.22),
                                         (0.22, 1.20, 0.58, 0.30, 0.20))):
        p = Vector((0, y, z))
        n = (p - TC + Vector((0, 0, 0.05))).normalized()
        P = Plate(W, L, H, 0.04, tip=0.4, front=0.85, hook=0.03)
        M = b.plate(P, frame(p, Vector((0, 1, -0.55 - 0.35 * k)), n), "chest")
        if k < 2:
            b.add(spike(M @ P.pt(0.0, 0.7), n + Vector((0, 0.7, 0.4)), 0.22, 0.045, bend=(0, 0.1, -0.03)), "bone", "chest")
        b.add(spike(M @ P.pt(0.75, 0.6), n + Vector((0.7, 0.5, 0.2)), 0.12, 0.03), "bone", "chest", mirror=True)
    # pauldrons over the scythe shoulders, crowned with bone horns
    for k, (p, W, L, H) in enumerate((((0.30, -0.18, 1.34), 0.40, 0.42, 0.13), ((0.36, -0.02, 1.22), 0.34, 0.36, 0.12))):
        p = Vector(p)
        n = Vector((0.75, -0.15, 1.0)).normalized()
        P = Plate(W, L, H, 0.04, tip=0.35, front=0.8, hook=0.04)
        M = b.plate(P, frame(p, Vector((0.25, 1, -0.45)), n), "chest", mirror=True)
        if k == 0:
            for (u, s, d, ln) in ((0.0, 0.35, (0.45, 0.3, 1.0), 0.30), (-0.45, 0.6, (0.15, 0.6, 1.0), 0.24),
                                  (0.55, 0.65, (0.9, 0.5, 0.6), 0.18)):
                b.add(spike(M @ P.pt(u, s), d, ln, 0.045, bend=(0, 0.12, -0.05)), "bone", "chest", mirror=True)
            q = M @ P.pt(0.2, 0.15)
            R = M.to_3x3()
            b.add(ell_m(frame(q + n * 0.01, R @ Vector((0, 1, 0)), n), (0.06, 0.06, 0.035)), "flesh", "chest",
                  mat="team", mirror=True)
    # chest plate under the head
    P = Plate(0.40, 0.30, 0.10, 0.035, tip=0.4, front=0.7, lod=1)
    fn = Vector((0, -1, -0.15)).normalized()
    b.plate(P, frame((0, -0.31, 1.00), (0, 0.15, -1), fn), "chest", col="chitin")
    # the head: low, heavy brow, four eyes, bone tusk mandibles
    b.add(sweep([(0, -0.16, 1.07), (0, -0.24, 1.07)], [0.10, 0.10], 8, t=(0.4, 0.7)), "flesh", "head")
    b.add(ell((0, -0.33, 1.05), (0.13, 0.13, 0.10), 12, 8, t=(0.2, 0.9)), "chitin", "head")
    P = Plate(0.28, 0.24, 0.07, 0.035, tip=0.5, front=0.6, hook=0.05, lod=1)
    b.plate(P, frame((0, -0.45, 1.10), (0, 1, 0.3), (0, -0.3, 1)), "head")
    for x, y, z, r in ((0.05, -0.445, 1.07, 0.027), (0.095, -0.415, 1.09, 0.02)):
        b.add(ell((x, y, z), r, 8, 6, t=(0.7, 1.0)), "glow", "head", mat="glow", mirror=True)
    b.add(ell((0, -0.42, 1.00), (0.08, 0.05, 0.05), 10, 6, t=(0.1, 0.7)), "maw", "jaw")
    tusk = [(0.07, -0.38, 0.99), (0.11, -0.47, 0.95), (0.10, -0.53, 0.88), (0.06, -0.55, 0.83)]
    b.add(sweep(tusk, [0.035, 0.03, 0.02, 0.0], 8, t=(0.2, 1.0)), "bone", "jaw", mirror=True)
    # the scythe arms: chitin upper arm under the pauldron, flesh elbow, a sheath, the bone blade
    sh, el = Vector((0.36, -0.06, 1.20)), Vector((0.55, -0.24, 1.27))
    b.add(sweep([sh, (sh + el) / 2 + Vector((0, 0, 0.03)), el], [0.11, 0.105, 0.085], 10, t=(0.35, 0.8)),
          "chitin", "arm_L_1", mirror=True)
    b.add(ell(el, 0.09, 10, 6, t=(0.3, 0.85)), "flesh", "arm_L_2", mirror=True)
    b.add(sweep([el, el + Vector((0.02, -0.08, 0.05)), el + Vector((0.035, -0.17, 0.08))], [0.085, 0.09, 0.07], 8,
                t=(0.3, 0.75)), "chitin", "arm_L_2", mirror=True)
    blade = [(0.56, -0.28, 1.30), (0.595, -0.42, 1.39), (0.615, -0.58, 1.38), (0.61, -0.73, 1.24), (0.585, -0.81, 1.03),
             (0.56, -0.82, 0.86), (0.545, -0.78, 0.76)]
    b.add(sweep(blade, [0.085, 0.10, 0.095, 0.08, 0.055, 0.03, 0.0], 8, flat=0.3, up=(1, 0, 0),
                ts=[0.25, 0.45, 0.6, 0.72, 0.84, 0.94, 1.0]), "bone", "arm_L_2", mirror=True)
    for s, (y, z) in enumerate(((-0.50, 1.47), (-0.66, 1.42))):
        b.add(spike((0.61, y, z - 0.04), (0.1, 0.35, 1), 0.08, 0.025), "bone", "arm_L_2", mirror=True)
    # legs: thick thighs with plates, shins, splayed bone-clawed feet
    b.add(sweep([hip, (hip + knee) / 2 + Vector((0.02, -0.02, 0)), knee], [0.13, 0.125, 0.09], 10, t=(0.35, 0.8)),
          "chitin", "thigh_L", mirror=True)
    P = Plate(0.24, 0.30, 0.08, 0.035, tip=0.35, front=0.75, lod=1)
    b.plate(P, frame(hip + Vector((0.06, -0.08, 0.02)), knee - hip, (0.6, -0.7, 0.3)), "thigh_L", mirror=True)
    b.add(ell(knee, 0.09, 10, 6, t=(0.3, 0.85)), "flesh", "shin_L", mirror=True)
    b.add(sweep([knee, (knee + ankle) / 2, ankle], [0.085, 0.075, 0.06], 8, t=(0.75, 0.4)), "chitin", "shin_L", mirror=True)
    b.add(spike(knee + Vector((0, 0.04, 0)), (0.2, 0.6, 0.6), 0.12, 0.035), "bone", "shin_L", mirror=True)
    b.add(ell(ankle, 0.062, 8, 6, t=(0.3, 0.8)), "flesh", "foot_L", mirror=True)
    ball = Vector((0.28, -0.04, 0.055))
    b.add(sweep([ankle, ball], [0.06, 0.055], 8, t=(0.45, 0.65)), "chitin", "foot_L", mirror=True)
    for dx in (-0.07, 0.0, 0.07):
        b.add(spike(ball, (dx, -1, -0.45), 0.15, 0.036, bend=(0, 0, -0.05)), "bone", "foot_L", mirror=True)
    b.add(spike(ball, (0, 1, -0.45), 0.09, 0.03), "bone", "foot_L", mirror=True)


def acidback(b):
    b.bone("root", (0, 0, 0), (0, 0.4, 0), None, deform=False)
    b.bone("body", (0, 0.30, 0.62), (0, -0.30, 0.62), "root")
    b.bone("abdomen", (0, 0.42, 0.60), (0, 0.85, 0.52), "body")
    b.bone("head", (0, -0.60, 0.55), (0, -0.80, 0.52), "body")
    b.bone("sprayer", (0, -0.80, 0.46), (0, -1.02, 0.42), "head")
    b.bone("mand_L", (0.16, -0.80, 0.44), (0.20, -0.96, 0.42), "head", mirror=True)
    sacs = [((0, -0.17, 0.96), (0.20, 0.21, 0.17)), ((0, 0.17, 1.01), (0.23, 0.23, 0.19)), ((0, 0.49, 0.91), (0.18, 0.18, 0.15))]
    for i, (c, r) in enumerate(sacs):
        b.bone("sac_%d" % (i + 1), (c[0], c[1], c[2] - r[2] * 0.8), (c[0], c[1], c[2] + r[2]), "body")
    # flesh body and abdomen
    b.add(ell((0, 0.02, 0.62), (0.50, 0.62, 0.32), 16, 10, t=(0.05, 0.75)), "flesh", "body")
    b.add(ell((0, 0.02, 0.40), (0.38, 0.55, 0.12), 12, 6, t=(0.0, 0.4)), "chitin", "body")
    AC, AR = Vector((0, 0.62, 0.56)), (0.38, 0.32, 0.26)
    b.add(ell(AC, AR, 14, 8, t=(0.05, 0.7)), "flesh", "abdomen")
    for k, (y, W) in enumerate(((0.56, 0.74), (0.72, 0.60))):
        p = ell_top(AC, AR, 0, y) + Vector((0, 0, 0.02))
        P = Plate(W, 0.22, 0.30 - 0.05 * k, 0.04, tip=0.5, front=0.9, hook=-0.02)
        M = b.plate(P, frame(p, Vector((0, 1, -0.5 - 0.4 * k)), ell_normal(AC, AR, p)), "abdomen")
    for x, d in ((0.0, (0, 1, 0.1)), (0.12, (0.4, 1, 0.0))):
        b.add(spike((x, 0.90, 0.56), d, 0.16, 0.04, bend=(0, 0, -0.05)), "bone", "abdomen", mirror=x > 0)
    # the shell: a broad pronotum shield and two elytra parted over the acid sacs
    P = Plate(1.06, 0.48, 0.30, 0.045, tip=0.62, front=0.82, droop=0.04)
    M = b.plate(P, frame((0, -0.60, 0.86), (0, 1, 0.12), (0, -0.25, 1)), "body")
    for u, s in ((0.42, 0.45), (0.62, 0.42)):
        q = M @ P.pt(u, s)
        R = M.to_3x3()
        b.add(ell_m(frame(q, R @ Vector((0, 1, 0)), R @ Vector((0, 0, 1)) + R @ Vector((0.5 * u, 0, 0))),
                    (0.055, 0.07, 0.03)), "flesh", "body", mat="team", mirror=True)
    for u, s, d, ln in ((0.95, 0.35, (1, -0.4, -0.2), 0.16), (0.8, 0.12, (0.6, -1, 0.1), 0.14)):
        b.add(spike(M @ P.pt(u, s), M.to_3x3() @ Vector(d), ln, 0.04, bend=(0, 0, 0.04)), "bone", "body", mirror=True)
    P = Plate(0.62, 1.02, 0.26, 0.045, tip=0.34, front=0.85, hook=-0.02)
    M = b.plate(P, frame((0.30, -0.26, 0.98), (0.04, 1, -0.22), (0.62, 0.0, 1)), "body", mirror=True)
    for s in (0.3, 0.55, 0.8):
        b.add(spike(M @ P.pt(0.95, s), M.to_3x3() @ Vector((1, 0.35, -0.4)), 0.15, 0.04, bend=(0, 0.04, 0.04)),
              "bone", "body", mirror=True)
    b.add(spike(M @ P.pt(-0.75, 0.25), M.to_3x3() @ Vector((-0.2, 0.3, 1)), 0.18, 0.04, bend=(0, 0.05, 0)),
          "bone", "body", mirror=True)
    # the acid sacs on their own bones, strapped with flesh
    for i, (c, r) in enumerate(sacs):
        bn = "sac_%d" % (i + 1)
        b.add(ell(c, r, 14, 9, t=(0.15, 1.0)), "glow", bn, mat="glow")
        cc = Vector(c)
        strap = [cc + Vector((r[0] * 1.03 * math.cos(a), 0, r[2] * 1.03 * math.sin(a))) for a in
                 [math.radians(10 + 16 * k) for k in range(11)]]
        b.add(sweep(strap, [0.024] * len(strap), 6, t=(0.45, 0.8)), "flesh", bn)
    # the head: a broad shovel skull with eyes, hooked mandibles and the sprayer proboscis
    b.add(ell((0, -0.70, 0.53), (0.30, 0.21, 0.17), 14, 8, t=(0.2, 0.85)), "chitin", "head")
    P = Plate(0.58, 0.26, 0.13, 0.04, tip=0.6, front=0.7, hook=0.03)
    b.plate(P, frame((0, -0.86, 0.62), (0, 1, 0.45), (0, -0.4, 1)), "head")
    for x, y, z, r in ((0.11, -0.86, 0.58, 0.035), (0.19, -0.80, 0.60, 0.026)):
        b.add(ell((x, y, z), r, 8, 6, t=(0.7, 1.0)), "glow", "head", mat="glow", mirror=True)
    mand = [(0.16, -0.80, 0.44), (0.27, -0.90, 0.44), (0.25, -1.00, 0.425), (0.15, -1.05, 0.41), (0.08, -1.04, 0.40)]
    b.add(sweep(mand, [0.05, 0.05, 0.038, 0.022, 0.0], 8, flat=0.55, t=(0.2, 1.0)), "bone", "mand_L", mirror=True)
    pro = [(0, -0.78, 0.47), (0, -0.86, 0.455), (0, -0.94, 0.44), (0, -1.00, 0.43)]
    b.add(sweep(pro, [0.09, 0.08, 0.075, 0.07], 10, ts=[0.3, 0.75, 0.3, 0.7]), "flesh", "sprayer")
    for y in (-0.88, -0.97):
        b.add(sweep([(0, y + 0.015, 0.45), (0, y - 0.015, 0.445)], [0.085, 0.085], 10, t=(0.5, 0.7)), "chitin", "sprayer")
    b.add(ell((0, -1.03, 0.43), (0.065, 0.05, 0.065), 10, 6, t=(0.5, 1.0)), "glow", "sprayer", mat="glow")
    # six thick legs with knee spikes
    for key, hip, knee, foot in (("f", (0.40, -0.36, 0.50), (0.68, -0.52, 0.68), (0.77, -0.66, 0.0)),
                                 ("m", (0.45, 0.04, 0.48), (0.75, 0.05, 0.68), (0.85, 0.07, 0.0)),
                                 ("r", (0.40, 0.42, 0.48), (0.68, 0.58, 0.66), (0.77, 0.74, 0.0))):
        b.insect_leg(key, hip, knee, foot, "body", (0.09, 0.075, 0.05), ring=8, knee_spike=0.13)


def spinefiend(b):
    b.bone("root", (0, 0, 0), (0, 0.4, 0), None, deform=False)
    b.bone("body", (0, 0.15, 0.72), (0, -0.15, 0.72), "root")
    b.bone("chest", (0, -0.15, 0.73), (0, -0.55, 0.73), "body")
    b.bone("hips", (0, 0.15, 0.70), (0, 0.55, 0.68), "body")
    b.bone("head", (0, -0.62, 0.71), (0, -0.90, 0.66), "chest")
    b.bone("jaw", (0, -0.72, 0.63), (0, -0.96, 0.57), "head")
    b.bone("fan", (0, 0.04, 0.90), (0, 0.04, 1.12), "body")
    b.bone("fan_shot", (0, -0.04, 0.95), (0, -0.20, 1.42), "fan")
    b.bone("tail_1", (0, 0.62, 0.64), (0, 0.82, 0.58), "hips")
    b.bone("tail_2", (0, 0.82, 0.58), (0, 1.02, 0.48), "tail_1")
    # flesh body in three parts, chitin back plates
    b.add(ell((0, -0.38, 0.74), (0.27, 0.30, 0.23), 14, 8, t=(0.05, 0.75)), "flesh", "chest")
    b.add(sweep([(0, -0.22, 0.73), (0, 0.0, 0.74), (0, 0.22, 0.72)], [0.24, 0.25, 0.24], 12, ts=[0.3, 0.75, 0.3]),
          "flesh", "body")
    b.add(ell((0, 0.38, 0.70), (0.26, 0.30, 0.22), 14, 8, t=(0.05, 0.75)), "flesh", "hips")
    for k, (y, z, bn, W, tilt) in enumerate(((-0.62, 0.95, "chest", 0.50, -0.35), (-0.36, 0.99, "chest", 0.60, -0.1),
                                             (-0.10, 0.99, "body", 0.62, 0.0), (0.18, 0.97, "body", 0.62, 0.15),
                                             (0.42, 0.93, "hips", 0.58, 0.3), (0.62, 0.86, "hips", 0.46, 0.55))):
        P = Plate(W, 0.30, 0.22, 0.04, tip=0.55, front=0.85, hook=0.0)
        M = b.plate(P, frame((0, y, z), (0, 1, -tilt), (0, tilt * 0.6, 1)), bn)
        if k in (0, 4):
            q = M @ P.pt(0.55, 0.4)
            R = M.to_3x3()
            b.add(ell_m(frame(q, R @ Vector((0, 1, 0)), R @ Vector((0.35, 0, 1))), (0.05, 0.065, 0.03)), "flesh", bn,
                  mat="team", mirror=True)
        if k in (1, 3, 5):
            b.add(spike(M @ P.pt(0.95, 0.5), M.to_3x3() @ Vector((1, 0.3, -0.5)), 0.12, 0.03), "bone", bn, mirror=True)
    # the fan: a bony socket, glowing launch glands, two rows of long spines and a crimson web between them
    b.add(ell((0, 0.04, 1.00), (0.15, 0.24, 0.08), 12, 6, t=(0.3, 0.6)), "bone", "fan")
    spines = []
    for k, ang in enumerate((-38, -22, -6, 10, 26, 42, 58)):
        side = 1 if k % 2 == 0 else -1
        a = math.radians(ang)
        d = Vector((0.22 * side, math.sin(a), math.cos(a))).normalized()
        base = Vector((0.045 * side, 0.04 + 0.10 * math.sin(a), 1.02))
        ln = 0.52 - 0.00005 * (ang - 10) ** 2
        spines.append((base, d, ln))
        b.add(spike(base, d, ln, 0.04, bend=(0, 0.10, -0.02), segs=4, ring=6, t=(0.0, 1.0)), "bone", "fan")
        b.add(ell(base + d * 0.02, 0.04, 8, 5, t=(0.5, 1.0)), "glow", "fan", mat="glow")
    web = [Vector((0, 0.04 + 0.08 * math.sin(math.radians(a)), 1.02)) +
           Vector((0, math.sin(math.radians(a)), math.cos(math.radians(a)))) * 0.26 for a in range(-38, 60, 8)]
    pts = [Vector((0, -0.18, 1.0))] + web + [Vector((0, 0.30, 0.98))]
    outline = [(p.y, p.z) for p in pts]
    bm = V.prism(outline, -0.012, 0.012, "x", 0.0, 1)
    gv = [v.co.copy() for v in bm.verts]
    gf = [tuple(v.index for v in fc.verts) for fc in bm.faces]
    bm.free()
    b.add(Geo(gv, gf, [0.55 + 0.25 * (p.z - 1.0) / 0.26 for p in gv]), "flesh", "fan")
    sb = Vector((0, -0.02, 1.0))
    b.add(spike(sb, (0, -0.30, 1), 0.52, 0.055, bend=(0, -0.05, -0.04), segs=5, ring=7, t=(0.0, 1.0)), "bone", "fan_shot")
    b.add(ell(sb + Vector((0, -0.01, 0.03)), 0.05, 8, 5, t=(0.5, 1.0)), "glow", "fan_shot", mat="glow")
    # the head: a wedge skull with swept horns, four eyes, a toothed jaw
    b.add(sweep([(0, -0.55, 0.73), (0, -0.64, 0.71)], [0.13, 0.12], 8, t=(0.4, 0.7)), "flesh", "head")
    b.add(ell((0, -0.76, 0.69), (0.17, 0.21, 0.12), 12, 8, rot=(10, 0, 0), t=(0.2, 0.85)), "chitin", "head")
    P = Plate(0.34, 0.30, 0.09, 0.035, tip=0.4, front=0.5, hook=0.04, lod=1)
    b.plate(P, frame((0, -0.95, 0.72), (0, 1, 0.35), (0, -0.3, 1)), "head")
    b.add(spike((0.10, -0.70, 0.78), (0.35, 0.8, 0.45), 0.24, 0.04, bend=(0, 0.05, 0.08)), "bone", "head", mirror=True)
    for x, y, z, r in ((0.06, -0.93, 0.71, 0.026), (0.11, -0.88, 0.73, 0.02)):
        b.add(ell((x, y, z), r, 8, 6, t=(0.7, 1.0)), "glow", "head", mat="glow", mirror=True)
    b.add(ell((0, -0.84, 0.60), (0.11, 0.15, 0.04), 10, 6, t=(0.2, 0.7)), "chitin", "jaw")
    b.add(ell((0, -0.84, 0.635), (0.08, 0.11, 0.03), 8, 5, t=(0.1, 0.6)), "maw", "jaw")
    for x, y in ((0.07, -0.92), (0.09, -0.82)):
        b.add(spike((x, y, 0.62), (0.1, -0.2, 1), 0.05, 0.014, ring=5, segs=2), "bone", "jaw", mirror=True)
    # the tail, blended over two bones, ending in a bone stinger
    def tail_w(p):
        w2 = min(1.0, max(0.0, (p.y - 0.74) / 0.14))
        w2 = w2 * w2 * (3 - 2 * w2)
        return {"tail_1": 1.0 - w2, "tail_2": w2}
    tail = [(0, 0.56, 0.66), (0, 0.70, 0.62), (0, 0.82, 0.58), (0, 0.94, 0.52), (0, 1.03, 0.47)]
    b.add(sweep(tail, [0.13, 0.11, 0.09, 0.07, 0.05], 10, ts=[0.3, 0.75, 0.3, 0.75, 0.4]), "flesh", tail_w)
    b.add(spike((0, 1.02, 0.47), (0, 1, -0.35), 0.16, 0.05, bend=(0, 0, 0.06)), "bone", "tail_2")
    # four splayed legs
    for key, hip, knee, foot in (("f", (0.25, -0.42, 0.64), (0.52, -0.56, 0.74), (0.56, -0.70, 0.0)),
                                 ("r", (0.25, 0.42, 0.62), (0.52, 0.56, 0.72), (0.56, 0.72, 0.0))):
        b.insect_leg(key, hip, knee, foot, "chest" if key == "f" else "hips", (0.085, 0.07, 0.048), ring=8,
                     knee_spike=0.14, thigh_plate=(0.17, 0.05))


BUILDERS = {"void_drudge": drudge, "void_spitter": spitter, "void_mauler": mauler, "void_acidback": acidback,
            "void_spinefiend": spinefiend}


# --- mesh and armature ---------------------------------------------------------------------------------

def realize(b, uid, mats):
    # bone weights first (weight functions are written in design coordinates)
    weights = []
    for g, col, mat, bone in b.parts:
        for p in g.v:
            weights.append({bone: 1.0} if isinstance(bone, str) else bone(p))
    allv = [p for g, *_ in b.parts for p in g.v]
    lo = Vector((min(p.x for p in allv), min(p.y for p in allv), min(p.z for p in allv)))
    hi = Vector((max(p.x for p in allv), max(p.y for p in allv), max(p.z for p in allv)))
    d = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    for g, *_ in b.parts:
        g.v = [p - d for p in g.v]
    for bd in b.bones.values():
        bd[0], bd[1] = bd[0] - d, bd[1] - d
    verts, faces, fmat, vuv = [], [], [], []
    for g, col, mat, bone in b.parts:
        o = len(verts)
        verts += [tuple(p) for p in g.v]
        for fc in g.f:
            assert len(set(fc)) == len(fc), "degenerate face"
            faces.append(tuple(o + i for i in fc))
            fmat.append(MAT_INDEX[mat])
        for t in g.t:
            vuv.append(col_uv(col, t))
    me = bpy.data.meshes.new(uid)
    me.from_pydata(verts, [], faces)
    me.polygons.foreach_set("material_index", fmat)
    uvl = me.uv_layers.new(name="UVMap")
    lv = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get("vertex_index", lv)
    uvl.data.foreach_set("uv", np.array(vuv, np.float32)[lv].ravel())
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    nonman = sum(1 for e in bm.edges if not e.is_manifold)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(uid, me)
    bpy.context.scene.collection.objects.link(ob)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(52))
    md = ob.modifiers.new("wn", "WEIGHTED_NORMAL")
    md.keep_sharp, md.weight, md.mode = True, 50, "FACE_AREA"
    with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob]):
        bpy.ops.object.modifier_apply(modifier=md.name)
    # armature
    arm = bpy.data.armatures.new("rig")
    rig = bpy.data.objects.new("rig", arm)
    bpy.context.scene.collection.objects.link(rig)
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for name, (h, t, par, dfm) in b.bones.items():
        eb = arm.edit_bones.new(name)
        eb.head, eb.tail, eb.roll = h, t, 0.0
        eb.use_deform = dfm
    for name, (h, t, par, dfm) in b.bones.items():
        if par:
            arm.edit_bones[name].parent = arm.edit_bones[par]
            arm.edit_bones[name].use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.display_type = "STICK"
    # skin
    groups = {}
    for name, bd in b.bones.items():
        if bd[3]:
            groups[name] = ob.vertex_groups.new(name=name)
    full = {}
    for i, w in enumerate(weights):
        for bn, x in w.items():
            if x <= 1e-4:
                continue
            if abs(x - 1.0) < 1e-6:
                full.setdefault(bn, []).append(i)
            else:
                groups[bn].add([i], x, "REPLACE")
    for bn, idx in full.items():
        groups[bn].add(idx, 1.0, "REPLACE")
    ob.parent = rig
    am = ob.modifiers.new("rig", "ARMATURE")
    am.object = rig
    return rig, ob, hi - lo, nonman


# --- posing: FK deltas in world axes, analytic two-bone IK for legs --------------------------------------

Xa, Ya, Za = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
QI = Quaternion((1, 0, 0, 0))


def rq(*pairs):
    """Product of rotations (axis, degrees), the first applied last (outermost)."""
    q = Quaternion((1, 0, 0, 0))
    for ax, deg in pairs:
        q = q @ Quaternion(ax, math.radians(deg))
    return q


def S(p, k=1.0, ph=0.0):
    return math.sin(2 * math.pi * (k * p + ph))


def C(p, k=1.0, ph=0.0):
    return math.cos(2 * math.pi * (k * p + ph))


def env(p, keys):
    """Smoothstepped key curve [(time, value), ...]."""
    if p <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if p <= t1:
            x = (p - t0) / (t1 - t0) if t1 > t0 else 1.0
            x = x * x * (3 - 2 * x)
            return v0 + (v1 - v0) * x
    return keys[-1][1]


def pulse(p, c, w):
    """A periodic bump of width w (cycle fraction) centred at c."""
    dd = (p - c + 0.5) % 1.0 - 0.5
    return math.cos(math.pi * dd / w) ** 2 if abs(dd) < w / 2 else 0.0


def step(p, phase, beta, stride, lift):
    """In-place foot offset for one gait cycle: stance (on the ground, sliding back from front to back),
    then swing (lifted, forward). Returns the offset and the swing fraction (0 in stance)."""
    q = (p + phase) % 1.0
    if q < beta:
        k = q / beta
        return Vector((0, -stride / 2 + stride * k, 0)), 0.0
    k = (q - beta) / (1 - beta)
    e = 0.5 - 0.5 * math.cos(math.pi * k)
    return Vector((0, stride / 2 - stride * e, lift * math.sin(math.pi * k))), k


class Solver:
    def __init__(self, rig, legs):
        bones = rig.data.bones
        self.rig = rig
        self.rest = {bn.name: bn.matrix_local.copy() for bn in bones}
        self.par = {bn.name: (bn.parent.name if bn.parent else None) for bn in bones}
        order, seen = [], set()

        def visit(n):
            if n in seen:
                return
            if self.par[n]:
                visit(self.par[n])
            seen.add(n)
            order.append(n)
        for bn in bones:
            visit(bn.name)
        self.order = order
        self.legs = {}
        self.F0 = {}
        self.skip = set()
        for lg in legs:
            u, l = lg["upper"], lg["lower"]
            H0 = self.rest[u].translation.copy()
            K0 = self.rest[l].translation.copy()
            F0 = bones[l].tail_local.copy()
            n0 = (K0 - H0).cross(F0 - K0).normalized()
            fh0 = (F0 - H0).normalized()
            ks = 1.0 if (K0 - H0).dot(n0.cross(fh0)) > 0 else -1.0
            info = dict(lg, H0=H0, K0=K0, F0=F0, a=(K0 - H0).length, b=(F0 - K0).length, n0=n0, ks=ks)
            self.legs[u] = info
            self.F0[lg["key"]] = F0
            self.skip.add(l)
            if lg["foot"]:
                self.skip.add(lg["foot"])

    def motion(self, posed, n):
        P = self.par[n]
        return posed[P] @ self.rest[P].inverted() if P else Matrix.Identity(4)

    def solve(self, fk, feet):
        posed, basis = {}, {}
        for n in self.order:
            if n in self.skip:
                continue
            R = self.rest[n]
            base = self.motion(posed, n) @ R
            if n in self.legs:
                self._ik(self.legs[n], base, posed, basis, feet.get(self.legs[n]["key"]))
                continue
            q, d, s = fk.get(n, (None, None, None))
            Rr = R.to_3x3().normalized()
            Ri = Rr.transposed()
            qloc = (Ri @ (q or QI).to_matrix() @ Rr).to_quaternion()
            loc = Ri @ (Vector(d) if d is not None else Vector())
            B = Matrix.LocRotScale(loc, qloc, Vector(s) if s is not None else Vector((1, 1, 1)))
            basis[n] = B
            posed[n] = base @ B
        return basis

    def _ik(self, lg, base_u, posed, basis, target):
        u, l, f = lg["upper"], lg["lower"], lg["foot"]
        Ru, Rl = self.rest[u], self.rest[l]
        Rp = self.motion(posed, u).to_3x3().normalized()
        H = base_u.translation.copy()
        if target is None:
            F, fq = lg["F0"].copy(), QI
        else:
            F, fq = target
        a, b = lg["a"], lg["b"]
        dv = F - H
        dist = min(max(dv.length, abs(a - b) + 1e-4), a + b - 1e-4)
        fh = dv.normalized()
        Fe = H + fh * dist
        n0p = Rp @ lg["n0"]
        if lg["mode"] == "splay":
            n = Za.cross(Vector((dv.x, dv.y, 0.0)))
            if n.length < 1e-6:
                n = n0p.copy()
            n.normalize()
            if n.dot(n0p) < 0:
                n = -n
        else:
            n = n0p.copy()
        n = (n - fh * n.dot(fh)).normalized()
        m = n.cross(fh) * lg["ks"]
        cA = (a * a + dist * dist - b * b) / (2 * a * dist)
        A = math.acos(min(1.0, max(-1.0, cA)))
        K = H + (fh * math.cos(A) + m * math.sin(A)) * a

        def fr(dv_, nv):
            return Matrix((dv_, nv, dv_.cross(nv))).transposed()
        du = (K - H).normalized()
        dl = (Fe - K).normalized()
        du0p = Rp @ (lg["K0"] - lg["H0"]).normalized()
        Qu = fr(du, n) @ fr(du0p, n0p).transposed()
        Mu = Matrix.Translation(H) @ (Qu @ Rp @ Ru.to_3x3().normalized()).to_4x4()
        basis[u], posed[u] = base_u.inverted() @ Mu, Mu
        base_l = Mu @ Ru.inverted() @ Rl
        dl0p = Qu @ Rp @ (lg["F0"] - lg["K0"]).normalized()
        Ql = fr(dl, n) @ fr(dl0p, n).transposed()
        Ml = Matrix.Translation(K) @ (Ql @ Qu @ Rp @ Rl.to_3x3().normalized()).to_4x4()
        basis[l], posed[l] = base_l.inverted() @ Ml, Ml
        if f:
            Rf = self.rest[f]
            base_f = Ml @ Rl.inverted() @ Rf
            Mf = Matrix.Translation(base_f.translation) @ (fq.to_matrix() @ Rf.to_3x3().normalized()).to_4x4()
            basis[f], posed[f] = base_f.inverted() @ Mf, Mf


def walk_feet(R, p, phases, beta, stride, lift, toe=0.0):
    feet = {}
    for key, ph in phases.items():
        off, k = step(p, ph, beta, stride, lift)
        q = Quaternion(Xa, math.radians(toe * math.sin(math.pi * k))) if (toe and k > 0) else QI
        feet[key] = (R.F0[key] + off, q)
    return feet


def fk(q=None, d=None, s=None):
    return (q, d, s)


def uni(k):
    return (k, k, k)


TRIPOD = {"f_L": 0.0, "m_R": 0.0, "r_L": 0.0, "f_R": 0.5, "m_L": 0.5, "r_R": 0.5}


def anim_drudge(clip, p, R):
    F, feet = {}, {}
    if clip == "idle_loop":
        F["body"] = fk(rq((Ya, 1.5 * S(p)), (Xa, 1.2 * S(p, 2, 0.1))), (0, 0, 0.008 * S(p)))
        k = 1 + 0.07 * S(p, 2)
        F["abdomen"] = fk(rq((Xa, 3 * S(p, 1, 0.25)), (Za, 4 * S(p))), None, uni(k))
        F["head"] = fk(rq((Za, 9 * S(p)), (Xa, 4 * S(p, 2, 0.2))))
        clack = 18 * (pulse(p, 0.30, 0.08) + pulse(p, 0.40, 0.08) + 0.7 * pulse(p, 0.78, 0.1))
        F["mand_L"], F["mand_R"] = fk(rq((Za, clack))), fk(rq((Za, -clack)))
        F["ant_L"] = fk(rq((Xa, 12 * S(p, 3)), (Za, 10 * S(p, 2, 0.1))))
        F["ant_R"] = fk(rq((Xa, 12 * S(p, 3, 0.3)), (Za, -10 * S(p, 2, 0.35))))
    elif clip == "walk_loop":
        feet = walk_feet(R, p, TRIPOD, 0.5, 0.24, 0.10)
        F["body"] = fk(rq((Ya, 4 * S(p)), (Xa, 2 * S(p, 2, 0.1))), (0, 0, 0.022 * C(p, 2)))
        F["head"] = fk(rq((Za, -5 * S(p)), (Xa, -4 * C(p, 2))))
        F["abdomen"] = fk(rq((Za, 7 * S(p, 1, -0.1)), (Xa, 4 * S(p, 2))), None, uni(1 + 0.04 * C(p, 2)))
        m = 6 + 6 * S(p, 2)
        F["mand_L"], F["mand_R"] = fk(rq((Za, m))), fk(rq((Za, -m)))
        F["ant_L"] = fk(rq((Xa, 14 * S(p, 2)), (Za, 6 * S(p))))
        F["ant_R"] = fk(rq((Xa, 14 * S(p, 2, 0.15)), (Za, 6 * S(p))))
    else:      # bite: rear back with mandibles wide, snap forward
        F["body"] = fk(rq((Xa, env(p, [(0, 0), (0.4, -11), (0.58, 9), (0.72, 7), (1, 0)]))),
                       (0, env(p, [(0, 0), (0.4, 0.05), (0.58, -0.08), (0.72, -0.07), (1, 0)]),
                        env(p, [(0, 0), (0.4, 0.035), (0.58, -0.01), (1, 0)])))
        F["head"] = fk(rq((Xa, env(p, [(0, 0), (0.4, -16), (0.58, 14), (0.72, 10), (1, 0)]))))
        m = env(p, [(0, 0), (0.4, 34), (0.54, -6), (0.72, -6), (1, 0)])
        F["mand_L"], F["mand_R"] = fk(rq((Za, m))), fk(rq((Za, -m)))
        F["abdomen"] = fk(rq((Xa, env(p, [(0, 0), (0.4, 8), (0.58, -6), (1, 0)]))))
        a = env(p, [(0, 0), (0.4, -25), (0.58, 15), (1, 0)])
        F["ant_L"], F["ant_R"] = fk(rq((Xa, a))), fk(rq((Xa, a)))
    return F, feet


def anim_spitter(clip, p, R):
    F, feet = {}, {}
    if clip == "idle_loop":
        F["pelvis"] = fk(rq((Za, 3 * S(p))), (0, 0, 0.008 * S(p, 1, 0.25)))
        F["chest"] = fk(rq((Xa, -3 * S(p, 1, 0.25)), (Ya, 2 * S(p, 1))))
        F["sac"] = fk(rq((Xa, 3 * S(p, 1, 0.1)), (Za, -3 * S(p))), None, uni(1 + 0.06 * S(p, 2)))
        F["head"] = fk(rq((Za, 14 * S(p)), (Ya, 9 * S(p, 2, 0.1)), (Xa, 4 * S(p, 3))))
        j = 22 * pulse(p, 0.62, 0.12) + 8 * pulse(p, 0.2, 0.08)
        F["jaw"] = fk(rq((Xa, j)))
        for s, side in ((1, "L"), (-1, "R")):
            F["arm_%s_1" % side] = fk(rq((Xa, 7 * S(p, 1, 0.1 * s)), (Ya, 4 * s * S(p, 2))))
            F["arm_%s_2" % side] = fk(rq((Xa, -10 * S(p, 2, 0.2 * s))))
    elif clip == "walk_loop":
        feet = walk_feet(R, p, {"L": 0.0, "R": 0.5}, 0.6, 0.34, 0.13, toe=28)
        F["pelvis"] = fk(rq((Za, 7 * S(p, 1, -0.05)), (Ya, -5 * S(p, 1, -0.05))), (0, 0, 0.035 * C(p, 2, -0.6)))
        F["chest"] = fk(rq((Za, -10 * S(p, 1, -0.05)), (Xa, 7 + 2 * C(p, 2))))
        F["head"] = fk(rq((Za, 4 * S(p, 1, -0.05)), (Xa, -6 - 3 * C(p, 2))))
        F["jaw"] = fk(rq((Xa, 4 + 3 * S(p, 2))))
        F["sac"] = fk(rq((Za, -8 * S(p, 1, -0.2)), (Xa, 5 * S(p, 2, 0.1))))
        for s, side in ((1, "L"), (-1, "R")):
            F["arm_%s_1" % side] = fk(rq((Xa, 16 * s * S(p, 1, -0.05))))
            F["arm_%s_2" % side] = fk(rq((Xa, -8 + 8 * s * S(p, 1, 0.05))))
    else:      # spit: rear back, sac swells; thrust the head, jaw wide, sac squeezes
        F["pelvis"] = fk(None, (0, env(p, [(0, 0), (0.36, 0.035), (0.5, -0.05), (0.62, -0.045), (1, 0)]), 0))
        F["chest"] = fk(rq((Xa, env(p, [(0, 0), (0.36, -20), (0.5, 16), (0.62, 13), (1, 0)]))))
        F["head"] = fk(rq((Xa, env(p, [(0, 0), (0.36, -22), (0.5, 12), (0.62, 9), (1, 0)]))))
        F["jaw"] = fk(rq((Xa, env(p, [(0, 0), (0.36, 10), (0.46, 42), (0.62, 34), (1, 0)]))))
        k = env(p, [(0, 1), (0.36, 1.18), (0.5, 0.82), (0.7, 0.95), (1, 1)])
        F["sac"] = fk(rq((Xa, env(p, [(0, 0), (0.36, 8), (0.5, -10), (1, 0)]))), None, uni(k))
        for side in ("L", "R"):
            F["arm_%s_1" % side] = fk(rq((Xa, env(p, [(0, 0), (0.36, -24), (0.5, 12), (1, 0)]))))
            F["arm_%s_2" % side] = fk(rq((Xa, env(p, [(0, 0), (0.36, -20), (0.5, 10), (1, 0)]))))
    return F, feet


def anim_mauler(clip, p, R):
    F, feet = {}, {}
    if clip == "idle_loop":
        F["pelvis"] = fk(rq((Za, 3 * S(p))), (0, 0, 0.012 * S(p, 1, 0.25)))
        F["chest"] = fk(rq((Xa, -4 * S(p, 1, 0.25)), (Ya, 2.5 * S(p))), (0, 0, 0.01 * S(p, 1, 0.25)))
        F["head"] = fk(rq((Za, 12 * S(p, 1, 0.1)), (Xa, 5 * S(p, 2))))
        F["jaw"] = fk(rq((Xa, 14 * pulse(p, 0.55, 0.15) + 6 * pulse(p, 0.15, 0.1))))
        for s, side in ((1, "L"), (-1, "R")):
            F["arm_%s_1" % side] = fk(rq((Xa, 5 * S(p, 1, 0.15 * s)), (Za, 3 * s * S(p, 1))))
            F["arm_%s_2" % side] = fk(rq((Xa, -7 * S(p, 2, 0.2 * s))))
    elif clip == "walk_loop":
        feet = walk_feet(R, p, {"L": 0.0, "R": 0.5}, 0.62, 0.40, 0.14, toe=24)
        F["pelvis"] = fk(rq((Za, 8 * S(p, 1, -0.05)), (Ya, -6 * S(p, 1, -0.05))), (0, 0, 0.045 * C(p, 2, -0.62)))
        F["chest"] = fk(rq((Za, -11 * S(p, 1, -0.05)), (Ya, 4 * S(p, 1, -0.05)), (Xa, 6 + 3 * C(p, 2))))
        F["head"] = fk(rq((Za, 5 * S(p, 1, -0.05)), (Xa, -5 - 3 * C(p, 2))))
        F["jaw"] = fk(rq((Xa, 5 + 4 * S(p, 2))))
        for s, side in ((1, "L"), (-1, "R")):
            F["arm_%s_1" % side] = fk(rq((Xa, 14 * s * S(p, 1, -0.05))))
            F["arm_%s_2" % side] = fk(rq((Xa, -6 + 8 * s * S(p, 1, 0.05))))
    else:      # double scythe slash: rear back with blades high, chop down and forward
        F["pelvis"] = fk(None, (0, env(p, [(0, 0), (0.4, 0.05), (0.55, -0.08), (0.7, -0.07), (1, 0)]),
                                env(p, [(0, 0), (0.4, 0.02), (0.55, -0.04), (1, 0)])))
        F["chest"] = fk(rq((Xa, env(p, [(0, 0), (0.4, -16), (0.55, 18), (0.7, 15), (1, 0)]))))
        F["head"] = fk(rq((Xa, env(p, [(0, 0), (0.4, -10), (0.55, 6), (1, 0)]))))
        F["jaw"] = fk(rq((Xa, env(p, [(0, 0), (0.4, 24), (0.55, 10), (1, 0)]))))
        for s, side in ((1, "L"), (-1, "R")):
            F["arm_%s_1" % side] = fk(rq((Xa, env(p, [(0, 0), (0.4, -40), (0.55, 32), (0.7, 28), (1, 0)])),
                                         (Ya, s * env(p, [(0, 0), (0.4, -10), (0.55, 8), (1, 0)]))))
            F["arm_%s_2" % side] = fk(rq((Xa, env(p, [(0, 0), (0.4, -35), (0.55, 40), (0.7, 34), (1, 0)]))))
    return F, feet


def anim_acidback(clip, p, R):
    F, feet = {}, {}
    if clip == "idle_loop":
        F["body"] = fk(rq((Ya, 1.2 * S(p)), (Xa, 1.0 * S(p, 1, 0.25))), (0, 0, 0.012 * S(p, 1, 0.25)))
        F["abdomen"] = fk(rq((Za, 4 * S(p, 1, 0.1)), (Xa, 2 * S(p, 2))))
        F["head"] = fk(rq((Za, 8 * S(p)), (Xa, 3 * S(p, 2, 0.15))))
        F["sprayer"] = fk(rq((Za, 10 * S(p, 2)), (Xa, 6 * S(p, 1, 0.3))))
        m = 14 * (pulse(p, 0.3, 0.1) + pulse(p, 0.42, 0.1)) + 4 * S(p, 3)
        F["mand_L"], F["mand_R"] = fk(rq((Za, m))), fk(rq((Za, -m)))
        for i in range(3):
            k = 1 + 0.09 * S(p, 2, -i / 3)
            F["sac_%d" % (i + 1)] = fk(None, None, (k, k, 1 + 0.12 * S(p, 2, -i / 3)))
    elif clip == "walk_loop":
        feet = walk_feet(R, p, TRIPOD, 0.52, 0.36, 0.14)
        F["body"] = fk(rq((Ya, 3.5 * S(p)), (Za, 2.5 * S(p, 1, 0.1)), (Xa, 1.5 * S(p, 2))), (0, 0, 0.03 * C(p, 2)))
        F["abdomen"] = fk(rq((Za, -6 * S(p, 1, -0.1)), (Xa, 3 * S(p, 2, 0.2))))
        F["head"] = fk(rq((Za, -4 * S(p, 1, 0.1)), (Xa, -4 * C(p, 2))))
        F["sprayer"] = fk(rq((Za, 8 * S(p, 1, -0.15)), (Xa, 5 * S(p, 2, -0.1))))
        F["mand_L"], F["mand_R"] = fk(rq((Za, 5 + 4 * S(p, 2)))), fk(rq((Za, -5 - 4 * S(p, 2))))
        for i in range(3):
            k = 1 + 0.06 * S(p, 2, -0.15 - i * 0.12)
            F["sac_%d" % (i + 1)] = fk(rq((Ya, 4 * S(p, 1, -0.2 - 0.1 * i))), None, (1 / k ** 0.5, 1 / k ** 0.5, k))
    else:      # spray: rear up while the sacs swell, then drop the head and spray, sacs squeezing in turn
        F["body"] = fk(rq((Xa, env(p, [(0, 0), (0.36, -9), (0.52, 6), (0.7, 5), (1, 0)]))),
                       (0, env(p, [(0, 0), (0.36, 0.05), (0.52, -0.06), (0.7, -0.05), (1, 0)]),
                        env(p, [(0, 0), (0.36, 0.04), (0.52, -0.02), (1, 0)])))
        F["head"] = fk(rq((Xa, env(p, [(0, 0), (0.36, -16), (0.52, 13), (0.7, 11), (1, 0)]))))
        F["sprayer"] = fk(rq((Xa, env(p, [(0, 0), (0.36, -12), (0.52, 6), (1, 0)]))),
                          (0, env(p, [(0, 0), (0.36, 0.02), (0.5, -0.09), (0.7, -0.07), (1, 0)]), 0),
                          uni(env(p, [(0, 1), (0.36, 0.95), (0.5, 1.2), (0.7, 1.12), (1, 1)])))
        m = env(p, [(0, 0), (0.36, 10), (0.5, 30), (0.7, 26), (1, 0)])
        F["mand_L"], F["mand_R"] = fk(rq((Za, m))), fk(rq((Za, -m)))
        F["abdomen"] = fk(rq((Xa, env(p, [(0, 0), (0.36, 6), (0.52, -5), (1, 0)]))))
        for i in range(3):
            o = 0.04 * (2 - i)
            k = env(p, [(0, 1), (0.3, 1.2), (0.44 + o, 1.2), (0.54 + o, 0.82), (0.75, 0.95), (1, 1)])
            F["sac_%d" % (i + 1)] = fk(None, None, uni(k))
    return F, feet


def anim_spinefiend(clip, p, R):
    F, feet = {}, {}
    if clip == "idle_loop":
        F["body"] = fk(rq((Ya, 1.2 * S(p)), (Xa, 1.0 * S(p, 1, 0.25))), (0, 0, 0.012 * S(p, 1, 0.25)))
        F["chest"] = fk(rq((Za, 2 * S(p))))
        F["head"] = fk(rq((Za, 14 * S(p, 1, 0.1)), (Xa, 5 * S(p, 2))))
        F["jaw"] = fk(rq((Xa, 16 * pulse(p, 0.6, 0.14) + 6 * pulse(p, 0.25, 0.1))))
        rattle = 4 * pulse(p, 0.35, 0.2) * S(p, 12)
        F["fan"] = fk(rq((Xa, 4 * S(p, 1, 0.2)), (Ya, 2.5 * S(p, 2) + rattle)), None,
                      (1 + 0.04 * S(p, 2), 1, 1 + 0.03 * S(p, 2)))
        F["fan_shot"] = fk(rq((Xa, 3 * S(p, 2, 0.3))))
        F["tail_1"] = fk(rq((Za, 9 * S(p)), (Xa, 3 * S(p, 2))))
        F["tail_2"] = fk(rq((Za, 12 * S(p, 1, -0.12))))
    elif clip == "walk_loop":
        feet = walk_feet(R, p, {"f_L": 0.0, "r_R": 0.06, "f_R": 0.5, "r_L": 0.56}, 0.6, 0.42, 0.15)
        F["body"] = fk(rq((Ya, 3 * S(p)), (Xa, 1.5 * S(p, 2))), (0, 0, 0.035 * C(p, 2)))
        F["chest"] = fk(rq((Za, -5 * S(p))))
        F["hips"] = fk(rq((Za, 5 * S(p))))
        F["head"] = fk(rq((Za, 4 * S(p)), (Xa, -4 * C(p, 2))))
        F["jaw"] = fk(rq((Xa, 4 + 4 * S(p, 2))))
        F["fan"] = fk(rq((Ya, -6 * S(p, 1, -0.12)), (Xa, 4 * S(p, 2, -0.1))))
        F["tail_1"] = fk(rq((Za, 12 * S(p, 1, -0.1))))
        F["tail_2"] = fk(rq((Za, 14 * S(p, 1, -0.22))))
    else:      # fling: crouch and pull the fan back, whip it forward, the big spine leaves and regrows
        F["body"] = fk(rq((Xa, env(p, [(0, 0), (0.4, -7), (0.5, 7), (0.65, 5), (1, 0)]))),
                       (0, env(p, [(0, 0), (0.4, 0.06), (0.5, -0.05), (1, 0)]),
                        env(p, [(0, 0), (0.4, -0.05), (0.5, 0.02), (1, 0)])))
        F["head"] = fk(rq((Xa, env(p, [(0, 0), (0.4, 8), (0.5, -10), (1, 0)]))))
        F["jaw"] = fk(rq((Xa, env(p, [(0, 0), (0.4, 12), (0.5, 26), (0.7, 10), (1, 0)]))))
        F["fan"] = fk(rq((Xa, env(p, [(0, 0), (0.4, -32), (0.5, 34), (0.62, 26), (1, 0)]))))
        F["fan_shot"] = fk(rq((Xa, env(p, [(0, 0), (0.4, -10), (0.47, 20), (1, 0)]))), None,
                           uni(env(p, [(0, 1), (0.46, 1), (0.5, 0.02), (0.62, 0.02), (1, 1)])))
        F["tail_1"] = fk(rq((Xa, env(p, [(0, 0), (0.4, 12), (0.5, -12), (1, 0)]))))
        F["tail_2"] = fk(rq((Xa, env(p, [(0, 0), (0.4, 10), (0.5, -14), (1, 0)]))))
    return F, feet


ANIMS = {"void_drudge": anim_drudge, "void_spitter": anim_spitter, "void_mauler": anim_mauler,
         "void_acidback": anim_acidback, "void_spinefiend": anim_spinefiend}


def bake_actions(uid, rig, solver):
    scn = bpy.context.scene
    scn.render.fps = FPS
    rig.animation_data_create()
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
    acts = {}
    for clip, secs in CLIPS[uid].items():
        frames = int(round(secs * FPS))
        act = bpy.data.actions.new(clip)
        act.use_fake_user = True
        rig.animation_data.action = act
        prev = {}
        for f in range(frames + 1):
            Fk, feet = ANIMS[uid](clip, f / frames, solver)
            for n, B in solver.solve(Fk, feet).items():
                pb = rig.pose.bones[n]
                loc, q, s = B.decompose()
                if n in prev and prev[n].dot(q) < 0:
                    q.negate()
                prev[n] = q
                pb.location, pb.rotation_quaternion, pb.scale = loc, q, s
                for path in ("location", "rotation_quaternion", "scale"):
                    pb.keyframe_insert(path, frame=f, group=n)
        acts[clip] = (act, frames)
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
    return acts


# --- export and checks ---------------------------------------------------------------------------------

def export(rig, ob, path):
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = rig
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True,
                              export_yup=True, export_cameras=False, export_lights=False, export_animations=True,
                              export_animation_mode="ACTIONS", export_force_sampling=True, export_frame_step=1)


def glb_json(path):
    with open(path, "rb") as fh:
        data = fh.read()
    ln = struct.unpack("<I", data[12:16])[0]
    return json.loads(data[20:20 + ln])


def glb_report(path):
    js = glb_json(path)
    acc = js.get("accessors", [])
    anims = []
    for a in js.get("animations", []):
        dur = max(acc[s["input"]]["max"][0] for s in a["samplers"])
        anims.append({"name": a["name"], "seconds": round(dur, 3), "channels": len(a["channels"])})
    tris = 0
    for m in js.get("meshes", []):
        for pr in m["primitives"]:
            tris += acc[pr["indices"]]["count"] // 3
    return {"animations": anims, "triangles": tris, "materials": [m["name"] for m in js.get("materials", [])],
            "joints": [len(s["joints"]) for s in js.get("skins", [])],
            "meshes": [m["name"] for m in js.get("meshes", [])],
            "nodes": [n.get("name") for n in js.get("nodes", []) if "mesh" in n or "skin" in n]}


def reimport(path):
    """A fresh empty scene, the GLB imported back: the actions Blender finds."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=path)
    acts = [(a.name, round((a.frame_range[1] - a.frame_range[0]) / bpy.context.scene.render.fps, 3))
            for a in bpy.data.actions]
    arms = [o.name for o in bpy.data.objects if o.type == "ARMATURE"]
    meshes = [(o.name, len(o.data.polygons)) for o in bpy.data.objects if o.type == "MESH"]
    bones = sum(len(o.data.bones) for o in bpy.data.objects if o.type == "ARMATURE")
    return {"actions": sorted(acts), "armatures": arms, "meshes": meshes, "bones": bones}


# --- review renders ---------------------------------------------------------------------------------------

def mesh_points(ob, limit=4000):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    mw = ob.matrix_world
    pts = [mw @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    if len(pts) > limit:
        pts = pts[::max(1, len(pts) // limit)]
    return pts


def grid_sheet(rows, out, cell=256, bgc=(0.2, 0.21, 0.23)):
    tiles = []
    for row in rows:
        line = []
        for p in row:
            a = V.load_px(p)
            t = np.zeros((cell, cell, 4), np.float32)
            t[..., :3] = bgc
            t[..., 3] = 1
            h, w = a.shape[:2]
            al = a[..., 3:4]
            t[:h, :w, :3] = a[..., :3] * al + t[:h, :w, :3] * (1 - al)
            line.append(t)
        tiles.append(np.concatenate(line, axis=1))
    s = np.concatenate(tiles[::-1], axis=0)        # image rows run bottom-up
    img = bpy.data.images.new("sheet", s.shape[1], s.shape[0], alpha=True)
    img.pixels.foreach_set(s.ravel())
    img.filepath_raw = out
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def review(uid, rig, ob, acts, rnd):
    sc = bpy.context.scene
    cam, ground, bg = V.stage()
    out = os.path.join(REVIEW, "round%d" % rnd)
    os.makedirs(out, exist_ok=True)
    pts = mesh_points(ob)
    shots = []
    ground.hide_render = True
    V.fit(cam, pts, 35, 24, 0.04)
    icon = os.path.join(ICONS, uid + ".png")
    V.render(icon, (256, 256), True)
    bg.inputs[0].default_value = (0.05, 0.053, 0.06, 1)
    V.fit(cam, pts, 35, 22, 0.08)
    shots.append(os.path.join(out, uid + "_front.png"))
    V.render(shots[-1], (512, 512), False)
    V.fit(cam, pts, -140, 26, 0.08)
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
    # the same camera at phone pixel density (45 degrees over 1080 px): a 160 px crop, shown 3x
    cam.data.angle = math.radians(45 * 160 / 1080)
    crop = os.path.join(CACHE, uid + "_game_px.png")
    V.render(crop, (160, 160), False)
    a = V.load_px(crop)
    big = np.repeat(np.repeat(a, 3, axis=0), 3, axis=1)
    img = bpy.data.images.new("crop", big.shape[1], big.shape[0], alpha=True)
    img.pixels.foreach_set(big.ravel())
    img.filepath_raw = os.path.join(out, uid + "_game_px.png")
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    shots.append(os.path.join(out, uid + "_game_px.png"))
    V.sheet(shots + [icon], os.path.join(out, uid + "_sheet.png"))
    # animation contact sheet: rows idle, walk, attack; a side three-quarter on the ground
    wu, st = ATTACK_MARKS[uid]
    picks = {"idle_loop": (0.0, 0.25, 0.5, 0.75), "walk_loop": (0.0, 0.25, 0.5, 0.75),
             "attack": (0.0, wu, st, 0.8)}
    poses = []
    allp = []
    for clip in ("idle_loop", "walk_loop", "attack"):
        act, frames = acts[clip]
        rig.animation_data.action = act
        row = []
        for fr in picks[clip]:
            f = int(round(fr * frames))
            sc.frame_set(f)
            allp += mesh_points(ob, 1500)
            row.append((clip, f))
        poses.append(row)
    sc.eevee.taa_render_samples = 24
    V.fit(cam, allp, 55, 14, 0.05)
    rows = []
    for row in poses:
        line = []
        for clip, f in row:
            rig.animation_data.action = acts[clip][0]
            sc.frame_set(f)
            pth = os.path.join(CACHE, "%s_%s_%02d.png" % (uid, clip, f))
            V.render(pth, (256, 256), False)
            line.append(pth)
        rows.append(line)
    grid_sheet(rows, os.path.join(out, uid + "_anim.png"))
    rig.animation_data.action = None
    sc.frame_set(0)
    for pb in rig.pose.bones:
        pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)


def lineup(rnd):
    """The five exported GLBs side by side under the game camera at 25 and 40 m, at game scale."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sizes = {"void_drudge": (0.95, 0.95), "void_spitter": (0.9, 1.15), "void_mauler": (1.3, 1.6),
             "void_acidback": (1.9, 1.35), "void_spinefiend": (2.0, 1.5)}
    x = -4.4
    for uid in IDS:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(MODELS, uid + ".glb"))
        new = [o for o in bpy.data.objects if o not in before]
        tops = [o for o in new if o.parent is None]
        bpy.context.view_layer.update()
        pts = []
        for o in new:
            if o.type == "MESH":
                pts += mesh_points(o)
        w = max(max(p.x for p in pts) - min(p.x for p in pts), max(p.y for p in pts) - min(p.y for p in pts))
        h = max(p.z for p in pts) - min(p.z for p in pts)
        s = min(sizes[uid][0] / w, sizes[uid][1] / h)          # the game's Models.fit
        for o in tops:
            o.scale = (s, s, s)
            o.location = (x, 0, 0)
            o.rotation_euler = (0, 0, math.radians(-20))
        x += 2.2
    cam, ground, bg = V.stage()
    out = os.path.join(REVIEW, "round%d" % rnd)
    os.makedirs(out, exist_ok=True)
    cam.data.lens_unit, cam.data.sensor_fit = "FOV", "VERTICAL"
    cam.data.angle = math.radians(45)
    for dist in (25, 40):
        tgt = Vector((0, 0, 0.5))
        cam.location = tgt + V.view_dir(0, 55) * dist
        V.look(cam, tgt)
        V.render(os.path.join(out, "lineup_game_%dm.png" % dist), (1024, 576), False)


# --- main ------------------------------------------------------------------------------------------------

def build(uid, rnd, do_render):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = FPS
    mats = make_materials()
    b = Builder()
    BUILDERS[uid](b)
    rig, ob, dims, nonman = realize(b, uid, mats)
    solver = Solver(rig, b.legs)
    acts = bake_actions(uid, rig, solver)
    path = os.path.join(MODELS, uid + ".glb")
    export(rig, ob, path)
    me = ob.data
    me.calc_loop_triangles()
    info = {
        "id": uid,
        "triangles": len(me.loop_triangles),
        "vertices": len(me.vertices),
        "size_m": [round(v, 3) for v in dims],
        "bones": len(rig.data.bones),
        "bone_names": [bn.name for bn in rig.data.bones],
        "non_manifold_edges": nonman,
        "glb_bytes": os.path.getsize(path),
        "materials": [m.name for m in me.materials],
        "clips": {k: {"frames": n, "seconds": round(n / FPS, 3)} for k, (a, n) in acts.items()},
    }
    if do_render:
        os.makedirs(CACHE, exist_ok=True)
        review(uid, rig, ob, acts, rnd)
    info["glb"] = glb_report(path)
    info["reimport"] = reimport(path)
    print("[shardfall]", json.dumps(info))
    os.makedirs(REVIEW, exist_ok=True)
    with open(os.path.join(REVIEW, uid + "_stats.json"), "w") as fh:
        json.dump(info, fh, indent=1)
    return info


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    which = argv[0] if argv else "all"
    rnd = int(argv[argv.index("--round") + 1]) if "--round" in argv else 1
    if which == "lineup":
        lineup(rnd)
        return
    if which == "verify":
        for uid in IDS:
            path = os.path.join(MODELS, uid + ".glb")
            print("[verify]", uid, json.dumps({"glb": glb_report(path), "reimport": reimport(path)}))
        return
    ids = IDS if which == "all" else [which]
    for uid in ids:
        if uid not in BUILDERS:
            raise SystemExit("unknown id " + uid)
        build(uid, rnd, "--no-render" not in argv)


if __name__ == "__main__":
    main()
