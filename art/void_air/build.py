"""Void creatures for Shardfall, built and animated by script: the Skitter (fast bat-winged flyer), the
Gorgon (bloated floating bomber with acid sacs and hanging tendrils) and the Leviathan (the colossal
six-legged crawler with a glowing maw). The look follows art/ref/void_style_reference.png and the Void
buildings (art/void_buildings): glossy purple chitin plates with bone-coloured rims and hooked tips, curved
bone spikes fading to a darker base, crimson ribbed flesh in the gaps, acid-green glowing sacs and eyes.
Grown, not built.

    Blender --background --factory-startup --python-exit-code 1 --python art/void_air/build.py -- <id|all> [--round N] [--no-render]

ids: void_skitter, void_gorgon, void_leviathan.

Writes assets/models/<id>.glb (one armature `rig` and one skinned mesh `<id>`, with named glTF animations),
assets/icons/<id>.png (256 px, transparent, three-quarter from the front-left), review renders into
art/void_air/review/round<N>/ (front and back three-quarters, the game camera at 55 degrees from 25 m and
45 m, a top view for the flyers, a contact sheet of animation frames, and a sheet of the stills) and
art/void_air/review/<id>_stats.json (triangles, size, bones, and what a fresh re-import of the GLB finds).

Contract (docs/ART_SPEC.md): metres, front -Y, lowest point z = 0 in the bind pose, centred in X and Y. The
bind pose is the modelled pose. Three materials: `void_skin` (a 512 px painted atlas with a matching
roughness map: chitin, armour plate, bone, flesh, wing membrane, gullet, dark chitin, bladder), `glow_acid`
(emissive, its own vein texture; the game pulses materials named glow*) and `team` (light grey, recoloured
in game). Animations (30 fps, in place, loops start and end on the same pose): flyers `idle_loop`,
`fly_loop`, `attack`; the Leviathan `idle_loop`, `walk_loop`, `attack`. Every model has an Empty `muzzle`
parented to the bone that fires (mouth, belly or maw), so it follows the animation.

Shared staging, framing and render helpers come from art/ambron_vehicles/build.py, loaded the way
art/neutral/build.py loads them.
"""
import importlib.util
import json
import math
import os
import random
import sys

import bpy
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector, noise

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CACHE = os.path.join(HERE, "cache")
sys.dont_write_bytecode = True                 # no __pycache__ beside the vehicle script
_spec = importlib.util.spec_from_file_location("ambron_vehicles_build",
                                               os.path.join(os.path.dirname(HERE), "ambron_vehicles", "build.py"))
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)

IDS = ("void_skitter", "void_gorgon", "void_leviathan")
AIR = {"void_skitter": 3.6, "void_gorgon": 4.6}      # flight height in the game (defs.gd "fly")
FPS = 30
UP = Vector((0, 0, 1))

# --- palette (ART_SPEC Void look, same values as art/void_buildings) ---------------------------------------
TEAM_GREY = "#C8C8C8"
GLOW_STRENGTH = 2.4
ATLAS = 512
# kind: (x0, x1) pixel columns of the atlas; every region runs the full height (v from 0 to 1)
REGIONS = {
    "chitin": (0, 64), "plate": (64, 128), "bone": (128, 192), "flesh": (192, 256),
    "membrane": (256, 384), "gullet": (384, 416), "chitin_dk": (416, 480), "bladder": (480, 512),
}
ROUGH = {"chitin": 0.26, "plate": 0.24, "bone": 0.5, "flesh": 0.34, "membrane": 0.7, "gullet": 0.3,
         "chitin_dk": 0.28, "bladder": 0.3}


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def sstep(e0, e1, x):
    t = clamp((x - e0) / (e1 - e0)) if e1 != e0 else (1.0 if x >= e1 else 0.0)
    return t * t * (3 - 2 * t)


def ease(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def srgb_arr(h):
    return np.array(V.srgb(h), np.float32)


# --- painted atlas ------------------------------------------------------------------------------------------

def vnoise(h, w, cy, cx, seed, octaves=3):
    """Smooth value noise in [0, 1], periodic across the width (so loft seams match)."""
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        gy, gx = cy * 2 ** o, cx * 2 ** o
        g = rng.random((gy + 1, gx)).astype(np.float32)
        ys = np.linspace(0, gy, h, endpoint=False)
        xs = np.linspace(0, gx, w, endpoint=False)
        y0, x0 = ys.astype(int), xs.astype(int)
        fy, fx = ys - y0, xs - x0
        fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
        x1 = (x0 + 1) % gx
        a = g[y0][:, x0] * (1 - fx) + g[y0][:, x1] * fx
        b = g[y0 + 1][:, x0] * (1 - fx) + g[y0 + 1][:, x1] * fx
        out += amp * (a * (1 - fy[:, None]) + b * fy[:, None])
        tot += amp
        amp *= 0.5
    return out / tot


def ramp(stops, t):
    t = np.clip(t, 0, 1)
    pos = [s for s, _ in stops]
    cols = np.array([V.srgb(c) for _, c in stops], np.float32)
    return np.stack([np.interp(t, pos, cols[:, k]) for k in range(3)], -1)


def mix(a, b, m):
    m = np.asarray(m, np.float32)
    if m.ndim == a.ndim - 1:
        m = m[..., None]
    return a * (1 - m) + b * m


def paint_region(kind, h, w, seed):
    """Colour (h, w, 3, sRGB) and roughness (h, w) of one atlas region; u across, v up."""
    u = (np.arange(w) + 0.5)[None, :] / w * np.ones((h, 1))
    v = (np.arange(h) + 0.5)[:, None] / h * np.ones((1, w))
    streak = vnoise(h, w, 24, 6, seed)
    fine = vnoise(h, w, 64, 16, seed + 1)
    rough = np.full((h, w), ROUGH[kind], np.float32)
    if kind in ("chitin", "chitin_dk"):
        stops = ([(0, "#2C1840"), (0.45, "#4A2A63"), (0.8, "#6B3C8A"), (1, "#7E4C9E")] if kind == "chitin" else
                 [(0, "#160A1E"), (0.5, "#2A1638"), (1, "#45275C")])
        col = ramp(stops, 0.25 + 0.75 * streak + 0.15 * (fine - 0.5))
        fleck = np.clip((fine - 0.78) / 0.12, 0, 1)
        col = mix(col, srgb_arr("#8E5BB0"), fleck * (0.55 if kind == "chitin" else 0.3))
        # darker joint rings at both ends of a part
        ends = 1 - sstep_np(0.0, 0.07, v) * sstep_np(1.0, 0.93, v)
        col = mix(col, srgb_arr("#1E0E28"), ends * 0.7)
    elif kind == "plate":
        # top surface (u < 0.5): deep at the root, glossy purple, highlight, bone rim at the tip; edges bone too
        top = u < 0.5
        g = ramp([(0, "#24112E"), (0.18, "#4A2A63"), (0.55, "#6B3C8A"), (0.8, "#8456A8"), (0.86, "#8E5BB0")],
                 v + 0.08 * (streak - 0.5))
        bot = ramp([(0, "#1A0B22"), (1, "#3A1F4C")], v)
        col = np.where(top[..., None], g, bot)
        ue = np.minimum(np.minimum(np.abs(u), np.abs(u - 0.5)), np.abs(u - 1.0))
        rim = np.maximum(sstep_np(0.1, 0.05, ue), sstep_np(0.76, 0.84, v))
        bone = ramp([(0, "#9C8A6A"), (0.5, "#C8B898"), (1, "#E2D5B8")], 0.3 + 0.7 * v + 0.2 * (fine - 0.5))
        col = mix(col, bone, rim)
        ridge = 0.5 + 0.5 * np.cos(2 * np.pi * (u * 6 + 0.3 * streak))      # faint growth ridges
        col = col * (0.92 + 0.08 * ridge[..., None])
        rough = np.where(rim > 0.5, 0.45, ROUGH[kind]).astype(np.float32)
    elif kind == "bone":
        col = ramp([(0, "#55452F"), (0.12, "#6E5E44"), (0.35, "#9C8A6A"), (0.7, "#C8B898"), (1, "#E6DAC0")],
                   v + 0.12 * (streak - 0.5))
        rings = sstep_np(0.9, 1.0, np.abs(np.sin(np.pi * v * 9 + 0.6 * streak))) * (1 - sstep_np(0.35, 0.7, v))
        col = mix(col, srgb_arr("#4A3D2E"), rings * 0.45)
        col = col * (0.94 + 0.12 * fine[..., None])
    elif kind == "flesh":
        rib = 0.5 + 0.5 * np.cos(2 * np.pi * (v * 16 + 0.25 * np.sin(2 * np.pi * u) + 0.15 * streak))
        col = mix(srgb_arr("#3E0E1A")[None, None, :] * np.ones((h, w, 3)), srgb_arr("#8A2C3C"), rib ** 0.8)
        col = mix(col, srgb_arr("#A8465A"), np.clip((rib - 0.85) / 0.15, 0, 1) * 0.6)
        col = col * (0.88 + 0.2 * fine[..., None])
    elif kind == "membrane":
        # u along the span (root to tip), v across the chord (leading edge to trailing edge)
        base = ramp([(0, "#200E28"), (0.45, "#341230"), (0.8, "#521830"), (1, "#702232")],
                    0.55 * v + 0.35 * u + 0.15 * (streak - 0.5))
        warp = vnoise(h, w, 8, 8, seed + 5, 2)
        vein = np.abs(np.sin(2 * np.pi * (v * 4.0 + u * 1.5 + 0.6 * warp)))
        vein2 = np.abs(np.sin(2 * np.pi * (u * 5.0 - v * 0.8 + 0.7 * warp)))
        lines = np.maximum(sstep_np(0.12, 0.0, vein), 0.6 * sstep_np(0.08, 0.0, vein2))
        col = mix(base, srgb_arr("#1C0818"), lines * 0.75)
        col = mix(col, srgb_arr("#A8465A"), sstep_np(0.93, 1.0, v) * 0.6)
    elif kind == "gullet":
        col = ramp([(0, "#0E0408"), (0.6, "#2A0812"), (1, "#4A1220")], v + 0.2 * (fine - 0.5))
    elif kind == "bladder":
        n2 = vnoise(h, w, 12, 3, seed + 7)
        vein = sstep_np(0.035, 0.0, np.abs(n2 - 0.5))
        col = ramp([(0, "#4A1222"), (0.5, "#6E2238"), (1, "#8A2C3C")], 0.3 + 0.7 * streak)
        col = mix(col, srgb_arr("#2A0612"), vein * 0.8)
        col = mix(col, srgb_arr("#B05A68"), np.clip((fine - 0.8) / 0.15, 0, 1) * 0.5)
    return np.clip(col, 0, 1), rough


def sstep_np(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def make_images():
    col = np.zeros((ATLAS, ATLAS, 4), np.float32)
    mr = np.zeros((ATLAS, ATLAS, 4), np.float32)
    col[..., 3] = mr[..., 3] = 1
    for i, (kind, (x0, x1)) in enumerate(REGIONS.items()):
        c, r = paint_region(kind, ATLAS, x1 - x0, 11 + 7 * i)
        col[:, x0:x1, :3] = c
        mr[:, x0:x1, 0] = 1.0
        mr[:, x0:x1, 1] = r
        mr[:, x0:x1, 2] = 0.0
    # the glow texture: v from the bottom pole of a sac (deep green) to its crown (pale core), dark veins
    g = 128
    u = (np.arange(g) + 0.5)[None, :] / g * np.ones((g, 1))
    v = (np.arange(g) + 0.5)[:, None] / g * np.ones((1, g))
    n1 = vnoise(g, g, 6, 6, 91)
    n2 = vnoise(g, g, 5, 5, 92, 2)
    gc = ramp([(0, "#2F6E0C"), (0.25, "#62D622"), (0.55, "#8CFF3A"), (0.8, "#B6FF6E"), (1, "#D4FFA0")],
              v + 0.25 * (n1 - 0.5))
    vein = sstep_np(0.045, 0.0, np.abs(n2 - 0.5)) * (1 - 0.6 * sstep_np(0.75, 1.0, v))
    gc = mix(gc, srgb_arr("#1F4A0A"), vein * 0.85)
    glow = np.ones((g, g, 4), np.float32)
    glow[..., :3] = np.clip(gc, 0, 1)
    imgs = {}
    for name, px, cs in (("void_atlas", col, "sRGB"), ("void_atlas_mr", mr, "Non-Color"), ("void_glow", glow, "sRGB")):
        img = bpy.data.images.new(name, px.shape[1], px.shape[0], alpha=False)
        img.colorspace_settings.name = cs
        img.pixels.foreach_set(px.ravel())
        img.pack()
        imgs[name] = img
    return imgs


def make_materials():
    imgs = make_images()
    skin, nt, p = V.principled("void_skin")
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = imgs["void_atlas"]
    nt.links.new(t.outputs["Color"], p.inputs["Base Color"])
    t2 = nt.nodes.new("ShaderNodeTexImage")
    t2.image = imgs["void_atlas_mr"]
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(t2.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], p.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], p.inputs["Metallic"])
    glow, nt, p = V.principled("glow_acid")
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = imgs["void_glow"]
    nt.links.new(t.outputs["Color"], p.inputs["Base Color"])
    nt.links.new(t.outputs["Color"], p.inputs["Emission Color"])
    p.inputs["Emission Strength"].default_value = GLOW_STRENGTH
    p.inputs["Roughness"].default_value = 0.25
    team = V.flat("team", TEAM_GREY, 0.4, 0.0)
    return [skin, glow, team]


def kind_uv(kind, u, v):
    """Local (u, v) in 0..1 to the atlas (material 0), the glow texture (1) or the team colour (2)."""
    if kind == "glow":
        return 1, (0.03 + 0.94 * (u % 1.0001), 0.04 + 0.92 * v)
    if kind == "eye":
        return 1, (0.03 + 0.94 * (u % 1.0001), 0.42 + 0.3 * v)
    if kind == "team":
        return 2, (0.5, 0.5)
    x0, x1 = REGIONS[kind]
    pad = 2.0
    return 0, ((x0 + pad + u * (x1 - x0 - 2 * pad)) / ATLAS, (pad + v * (ATLAS - 2 * pad)) / ATLAS)


# --- geometry -----------------------------------------------------------------------------------------------

class Geo:
    """A closed piece of mesh: vertices, faces (vertex index tuples, outward winding), per-corner local UVs."""

    def __init__(self, verts=None, faces=None, uvs=None):
        self.v = verts or []
        self.f = faces or []
        self.uv = uvs or []

    def copy(self):
        return Geo([p.copy() for p in self.v], list(self.f), list(self.uv))

    def xf(self, M):
        M = Matrix(M)
        if len(M) == 3:
            M = M.to_4x4()
        self.v = [M @ p for p in self.v]
        if M.to_3x3().determinant() < 0:
            self.f = [tuple(reversed(f)) for f in self.f]
            self.uv = [tuple(reversed(u)) for u in self.uv]
        return self

    def mirrored(self):
        return self.copy().xf(Matrix.Diagonal((-1, 1, 1, 1)))

    def lumpy(self, amp, freq, seed=0.0, center=None, keep_z_below=None):
        """Pushes every vertex along a smooth noise field: organic unevenness, same displacement for shared
        vertices so the piece stays closed."""
        off = Vector((seed * 7.1, seed * 3.3, seed * 5.7))
        for i, p in enumerate(self.v):
            d = noise.noise_vector(p * freq + off) * amp
            self.v[i] = p + d
        return self


def frames(pts, up):
    m = len(pts)
    T = []
    for i in range(m):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, m - 1)]
        d = b - a
        T.append(d.normalized() if d.length > 1e-9 else Vector((0, 1, 0)))
    up = Vector(up)
    N0 = up - T[0] * up.dot(T[0])
    if N0.length < 1e-6:
        N0 = T[0].orthogonal()
    N = [N0.normalized()]
    for i in range(1, m):
        q = T[i - 1].rotation_difference(T[i])
        n_ = q @ N[-1]
        n_ = n_ - T[i] * n_.dot(T[i])
        N.append(n_.normalized())
    return T, N


def skin_rings(rings, vs, cap0=True, cap1=True):
    """Faces between rings of world points (each a counter-clockwise list seen from the far end, all the
    same length); a ring whose points all coincide is a pole. UVs: u around, v from `vs` per ring."""
    g = Geo()
    R = []
    n = len(rings[0])
    for ring in rings:
        if all((p - ring[0]).length < 1e-7 for p in ring):
            g.v.append(ring[0].copy())
            R.append([len(g.v) - 1] * n)
        else:
            R.append(list(range(len(g.v), len(g.v) + n)))
            g.v.extend(p.copy() for p in ring)
    m = len(rings)
    us = [j / n for j in range(n + 1)]
    for i in range(m - 1):
        for j in range(n):
            k = (j + 1) % n
            quad = [(R[i][j], (us[j], vs[i])), (R[i + 1][j], (us[j], vs[i + 1])),
                    (R[i + 1][k], (us[j + 1], vs[i + 1])), (R[i][k], (us[j + 1], vs[i]))]
            out = []
            for vi, uv in quad:
                if not out or out[-1][0] != vi:
                    out.append((vi, uv))
            if len(out) > 1 and out[0][0] == out[-1][0]:
                out.pop()
            if len(out) >= 3:
                g.f.append(tuple(a for a, _ in out))
                g.uv.append(tuple(b for _, b in out))
    for end, cap, sign in ((0, cap0, 1), (m - 1, cap1, -1)):
        ring_i = R[end]
        if not cap or ring_i[0] == ring_i[1]:
            continue
        c = sum((g.v[r] for r in ring_i), Vector()) / n
        g.v.append(c)
        ci = len(g.v) - 1
        for j in range(n):
            k = (j + 1) % n
            g.f.append((ci, ring_i[j], ring_i[k]) if sign > 0 else (ci, ring_i[k], ring_i[j]))
            g.uv.append(((0.5, vs[end]),) * 3)
    return g


def loft(pts, ring, up=(0, 0, 1), cap0=True, cap1=True, v_range=(0.0, 1.0)):
    """A tube through `pts` (Vectors). ring(t) gives the cross-section at t (0..1 along the length) as a
    counter-clockwise list of (X, Y) offsets in metres, X across (side), Y toward `up` (parallel-transported).
    A ring of all zeros becomes a pole (a pointed end). UVs: u around (0..1), v along (v_range)."""
    pts = [Vector(p) for p in pts]
    m = len(pts)
    T, N = frames(pts, up)
    L = [0.0]
    for i in range(1, m):
        L.append(L[-1] + (pts[i] - pts[i - 1]).length)
    tot = L[-1] or 1.0
    ts = [l / tot for l in L]
    vs = [v_range[0] + (v_range[1] - v_range[0]) * t for t in ts]
    rings = []
    for i in range(m):
        B = T[i].cross(N[i])
        rings.append([pts[i] + B * x + N[i] * y for x, y in ring(ts[i])])
    return skin_rings(rings, vs, cap0, cap1)


class Body:
    """A lofted body (catmull path, elliptic sections with a flatter belly) that armour shells can hug."""

    def __init__(self, ctrl, rx, ry, per=3, up=(0, 0, 1), n=14, belly=0.8, wobble=None):
        self.pts = catmull(ctrl, per) if len(ctrl) > 2 else [Vector(c) for c in ctrl]
        self.T, self.N = frames(self.pts, up)
        L = [0.0]
        for a, b in zip(self.pts, self.pts[1:]):
            L.append(L[-1] + (b - a).length)
        self.ts = [l / L[-1] for l in L]
        self.rxs, self.rys = rx, ry
        self.up, self.n, self.belly, self.wobble = up, n, belly, wobble

    def r(self, t):
        w = self.wobble(t) if self.wobble else 1.0
        return (interp(t, [a for a, _ in self.rxs], [b for _, b in self.rxs]) * w,
                interp(t, [a for a, _ in self.rys], [b for _, b in self.rys]) * w)

    def frame(self, t):
        i = max(0, min(len(self.ts) - 2, int(np.searchsorted(self.ts, t, side="right")) - 1))
        f = clamp((t - self.ts[i]) / max(1e-9, self.ts[i + 1] - self.ts[i]))
        c = self.pts[i].lerp(self.pts[i + 1], f)
        T = self.T[i].lerp(self.T[i + 1], f).normalized()
        N = self.N[i].lerp(self.N[i + 1], f)
        N = (N - T * N.dot(T)).normalized()
        return c, T, N, T.cross(N)

    def point(self, t, ang, off=0.0):
        """A point on (or `off` outside) the surface at t, `ang` degrees round from the side (90 = top)."""
        c, T, N, B = self.frame(t)
        rx, ry = self.r(t)
        a = math.radians(ang)
        y = math.sin(a) * (ry + off)
        if y < 0:
            y *= self.belly
        return c + B * math.cos(a) * (rx + off) + N * y

    def normal(self, t, ang):
        c = self.frame(t)[0]
        return (self.point(t, ang) - c).normalized()

    def geo(self, cap0=True, cap1=True):
        def ring(t):
            rx, ry = self.r(t)
            return ell(rx, ry, self.n, self.belly) if rx > 1e-6 else [(0.0, 0.0)] * self.n
        return loft(self.pts, ring, self.up, cap0, cap1)


def shell(body, t0, t1, a0, a1, off=0.008, thick=0.022, k=5, rings=6, lift=0.03, narrow=(0.55, 1.0), mid=90.0):
    """An armour plate hugging `body` from t0 (its root) to t1 (its tip, may be behind t0): an arc of the
    body's section from a0 to a1 degrees (90 = top), `thick` thick and `off` clear of the skin. Its outline
    narrows toward `mid` to a point at the tip, which lifts off the body by `lift`. UVs as plate(): u = 0
    and 0.5 are its edges, u < 0.5 the outside, v root to tip (the atlas paints the bone rim)."""
    rings_pts, vs = [], []
    back = t1 < t0          # the section runs counter-clockwise about the direction of travel
    for i in range(rings + 1):
        s = i / rings
        t = lerp(t0, t1, s)
        f = 1 - sstep(narrow[0], narrow[1], s) ** 1.3
        o = off + lift * sstep(0.35, 1.0, s)
        if s >= 1.0:
            rings_pts.append([body.point(t, mid, o + thick * 0.5)] * (2 * k))
        else:
            angs = [mid + (lerp(a0, a1, j / (k - 1)) - mid) * f for j in range(k)]
            if back:
                angs.reverse()
            outer = [body.point(t, a, o + thick * (1 - 0.5 * s)) for a in angs]
            inner = [body.point(t, a, o) for a in reversed(angs)]
            rings_pts.append(outer + inner)
        vs.append(s)
    return skin_rings(rings_pts, vs)


def ell(rx, ry, n, belly=1.0, phase=0.0):
    """An ellipse section, the lower half scaled by `belly`."""
    out = []
    for j in range(n):
        a = 2 * math.pi * j / n + phase
        y = math.sin(a) * ry
        out.append((math.cos(a) * rx, y * (belly if y < 0 else 1.0)))
    return out


def interp(t, xs, ys):
    return float(np.interp(t, xs, ys))


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


def tube(ctrl, radii, n=10, per=3, up=(0, 0, 1), belly=1.0, ry_scale=1.0, cap0=True, cap1=True, wobble=None):
    """A smooth tube through control points; radii is a list of (t, r) stops (r = 0 makes a point)."""
    pts = catmull(ctrl, per) if len(ctrl) > 2 else [Vector(c) for c in ctrl]
    ts_, rs_ = [a for a, _ in radii], [b for _, b in radii]

    def ring(t):
        r = interp(t, ts_, rs_)
        if wobble:
            r *= wobble(t)
        return ell(r, r * ry_scale, n, belly) if r > 1e-6 else [(0.0, 0.0)] * n
    return loft(pts, ring, up, cap0, cap1)


def spike(base, d, length, r0, bend=0.0, bend_to=None, n=7, rings=6, sink=0.3, flare=1.3, power=0.9):
    """A curved bone spike or claw: from below `base` (sunk by `sink` x length) along d, bending by `bend`
    radians toward `bend_to` as it goes, tapering to a point. UV v runs from the buried base to the tip."""
    d = Vector(d).normalized()
    bt = Vector(bend_to) if bend_to is not None else d.orthogonal()
    axis = d.cross(bt)
    axis = axis.normalized() if axis.length > 1e-6 else d.orthogonal()
    tsteps = [-sink + (1 + sink) * k / rings for k in range(rings + 1)]
    pts = [Vector(base) - d * length * sink]
    dirs = []
    for k in range(1, rings + 1):
        t = 0.5 * (tsteps[k - 1] + tsteps[k])
        q = Quaternion(axis, bend * max(0.0, t))
        dd = q @ d
        dirs.append(dd)
        pts.append(pts[-1] + dd * length * (tsteps[k] - tsteps[k - 1]))

    def ring(tt):
        t = -sink + (1 + sink) * tt
        r = r0 * max(0.0, 1 - max(t, 0.0)) ** power * (1 + (flare - 1) * sstep(0.2, -sink, t))
        return ell(r, r, n) if t < 0.999 else [(0.0, 0.0)] * n
    return loft(pts, ring, bt, True, True)


def plate(root, along, normal, length, width, thick=0.03, curl=0.4, arch=0.35, hook=0.25, n=10, rings=6,
          start=0.62, power=0.8):
    """A curved chitin armour plate: a lens-shaped section, a leaf outline that starts `start` wide and comes
    to a hooked point, laid from `root` along `along` with its back to `normal`, curling toward -normal by
    `curl` radians to hug a round body and hooking back out by `hook` at the tip. UVs: u = 0 and 0.5 are
    its two edges (u < 0.5 is the top), v runs root to tip, so the atlas paints the bone rim."""
    a = Vector(along).normalized()
    nr = Vector(normal)
    nr = (nr - a * nr.dot(a)).normalized()
    side = a.cross(nr)
    pts = [Vector(root)]
    for k in range(1, rings + 1):
        t = (k - 0.5) / rings
        ang = -curl * t + hook * sstep(0.55, 1.0, t)
        dd = Quaternion(side, ang) @ a
        pts.append(pts[-1] + dd * length / rings)
    s0 = math.asin(clamp(start)) / math.pi

    def ring(t):
        w = 0.5 * width * max(0.0, math.sin(math.pi * (s0 + (1 - s0) * t))) ** power / 1.0
        th = 0.5 * thick * (1 - 0.65 * t)
        if t > 0.999:
            return [(0.0, 0.0)] * n
        out = []
        for j in range(n):
            ang = 2 * math.pi * j / n
            x, y = math.cos(ang), math.sin(ang)
            out.append((w * x, th * y - arch * w * x * x))
        return out
    return loft(pts, ring, nr, True, True)


def blob(center, radii, n=12, rings=8, axis=(0, 0, 1), up=None, lump=0.0, seed=0.0, freq=6.0):
    """An ellipsoid (radii along the side, `up` and `axis` directions) with poles on the axis; v runs from
    the bottom pole to the top pole."""
    ax = Vector(axis).normalized()
    c = Vector(center)
    rx, ry, rz = radii
    pts = [c + ax * rz * (-math.cos(math.pi * k / rings)) for k in range(rings + 1)]
    upv = Vector(up) if up is not None else ax.orthogonal()

    def ring(t):
        s = math.sin(math.pi * t)
        return ell(rx * s, ry * s, n) if s > 1e-4 else [(0.0, 0.0)] * n
    g = loft(pts, ring, upv, False, False)
    if lump:
        g.lumpy(lump * min(radii), freq / max(radii), seed)
    return g


# --- rig description ----------------------------------------------------------------------------------------

def mirror_name(n):
    if n.endswith("_L"):
        return n[:-2] + "_R"
    if n.endswith("_R"):
        return n[:-2] + "_L"
    return n


def mx(p):
    return Vector((-p[0], p[1], p[2]))


class RigDef:
    def __init__(self):
        self.b = {}

    def add(self, name, head, tail, parent=None, mirror=False, deform=True):
        self.b[name] = {"head": Vector(head), "tail": Vector(tail), "parent": parent, "deform": deform}
        if mirror:
            self.b[mirror_name(name)] = {"head": mx(head), "tail": mx(tail),
                                         "parent": mirror_name(parent) if parent else None, "deform": deform}

    def head(self, n):
        return self.b[n]["head"]

    def tail(self, n):
        return self.b[n]["tail"]


class Chain:
    """Smooth weights along a chain of bones: a vertex is projected onto the chain's polyline and shares
    its weight between neighbouring bones over a blend zone round each joint."""

    def __init__(self, rd, names, blend=0.5):
        self.names = list(names)
        self.pts = [rd.head(names[0])] + [rd.tail(n) for n in names]
        self.S = [0.0]
        for a, b in zip(self.pts, self.pts[1:]):
            self.S.append(self.S[-1] + (b - a).length)
        self.blend = [blend * min(self.S[i + 1] - self.S[i], self.S[i] - self.S[i - 1])
                      for i in range(1, len(self.names))]

    def param(self, p):
        best, bs = 1e9, 0.0
        for i, (a, b) in enumerate(zip(self.pts, self.pts[1:])):
            ab = b - a
            t = clamp((p - a).dot(ab) / ab.length_squared)
            d = (a + ab * t - p).length
            if d < best:
                best, bs = d, self.S[i] + t * ab.length
        return bs

    def weights_at_s(self, s):
        w = {}
        k = len(self.names)
        for i, nm in enumerate(self.names):
            lo = 1.0 if i == 0 else sstep(self.S[i] - self.blend[i - 1] / 2, self.S[i] + self.blend[i - 1] / 2, s)
            hi = 1.0 if i == k - 1 else 1 - sstep(self.S[i + 1] - self.blend[i] / 2, self.S[i + 1] + self.blend[i] / 2, s)
            w[nm] = lo * hi
        return w

    def __call__(self, p):
        return self.weights_at_s(self.param(p))

    def at(self, p):
        w = self(Vector(p))
        return lambda q: w


# --- the skin: one mesh with materials, UVs and weights ------------------------------------------------------

def signed_volume(g):
    vol = 0.0
    for f in g.f:
        p0 = g.v[f[0]]
        for a, b in zip(f[1:], f[2:]):
            vol += p0.dot(g.v[a].cross(g.v[b])) / 6.0
    return vol


class Skin:
    def __init__(self):
        self.v, self.w, self.f, self.uv, self.mat = [], [], [], [], []
        self.parts, self.flipped = 0, []

    def add(self, g, kind, w, mirror=False):
        self._add(g, kind, w)
        if mirror:
            if callable(w):
                fn = w
                wm = lambda p, fn=fn: {mirror_name(k): x for k, x in fn(mx(p)).items()}
            elif isinstance(w, dict):
                wm = {mirror_name(k): x for k, x in w.items()}
            else:
                wm = mirror_name(w)
            self._add(g.mirrored(), kind, wm)

    def _add(self, g, kind, w):
        self.parts += 1
        if signed_volume(g) <= 0:
            self.flipped.append("%s#%d" % (kind, self.parts))
        base = len(self.v)
        for p in g.v:
            self.v.append(p.copy())
            if callable(w):
                wd = w(p)
            elif isinstance(w, dict):
                wd = w
            else:
                wd = {w: 1.0}
            wd = sorted(((k, x) for k, x in wd.items() if x > 0.01), key=lambda kv: -kv[1])[:4]
            tot = sum(x for _, x in wd) or 1.0
            self.w.append({k: x / tot for k, x in wd})
        for f, uvs in zip(g.f, g.uv):
            mi = None
            out = []
            for u, v in uvs:
                mi, uv = kind_uv(kind, u, v)
                out.append(uv)
            self.f.append(tuple(base + i for i in f))
            self.uv.append(tuple(out))
            self.mat.append(mi)

    def tris(self):
        return sum(len(f) - 2 for f in self.f)

    def shift(self, d):
        self.v = [p - d for p in self.v]


# --- assembling objects ----------------------------------------------------------------------------------

def make_rig(rd, name="rig"):
    ad = bpy.data.armatures.new(name)
    rig = bpy.data.objects.new(name, ad)
    bpy.context.scene.collection.objects.link(rig)
    ad.display_type = "STICK"
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for nm, b in rd.b.items():
        eb = ad.edit_bones.new(nm)
        eb.head, eb.tail = b["head"], b["tail"]
        eb.use_deform = b["deform"]
        d = (b["tail"] - b["head"]).normalized()
        upv = UP if abs(d.dot(UP)) < 0.9 else Vector((0, -1, 0))
        eb.align_roll(upv)
    for nm, b in rd.b.items():
        if b["parent"]:
            ad.edit_bones[nm].parent = ad.edit_bones[b["parent"]]
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
    return rig


def make_mesh(skin, name, mats, rig):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in skin.v], [], skin.f)
    uvl = me.uv_layers.new(name="UVMap")
    flat = [c for f in skin.uv for uv in f for c in uv]
    uvl.data.foreach_set("uv", flat)
    me.polygons.foreach_set("material_index", skin.mat)
    for m in mats:
        me.materials.append(m)
    me.validate(clean_customdata=False)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(62))
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    groups = {}
    for i, wd in enumerate(skin.w):
        for k, x in wd.items():
            if k not in groups:
                groups[k] = ob.vertex_groups.new(name=k)
            groups[k].add([i], x, "REPLACE")
    ob.parent = rig
    md = ob.modifiers.new("rig", "ARMATURE")
    md.object = rig
    return ob


def bone_empty(name, rig, bone, world):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type, e.empty_display_size = "ARROWS", 0.2
    bpy.context.scene.collection.objects.link(e)
    e.parent = rig
    e.parent_type = "BONE"
    e.parent_bone = bone
    bpy.context.view_layer.update()
    e.matrix_world = Matrix.Translation(Vector(world))
    return e


# --- animation: pose functions baked to actions ----------------------------------------------------------

class Poser:
    """Poses bones by rotations about the armature's axes (degrees, as seen in the rest pose), so a pose
    function can say "pitch the head down 10 degrees" without knowing bone rolls."""

    def __init__(self, rig):
        self.rig = rig
        self.R = {b.name: b.matrix_local.to_3x3() for b in rig.data.bones}

    def reset(self):
        for pb in self.rig.pose.bones:
            pb.location = (0, 0, 0)
            pb.rotation_quaternion = (1, 0, 0, 0)
            pb.scale = (1, 1, 1)

    def rot(self, name, x=0.0, y=0.0, z=0.0):
        q = Euler((math.radians(x), math.radians(y), math.radians(z)), "XYZ").to_matrix()
        R = self.R[name]
        ql = (R.inverted() @ q @ R).to_quaternion()
        pb = self.rig.pose.bones[name]
        pb.rotation_quaternion = pb.rotation_quaternion @ ql

    def move(self, name, v):
        pb = self.rig.pose.bones[name]
        pb.location = pb.location + self.R[name].inverted() @ Vector(v)

    def scale(self, name, s):
        self.rig.pose.bones[name].scale = (s, s, s) if isinstance(s, (int, float)) else s


def bake(rig, P, name, seconds, fn, ik=None):
    """Samples fn(P, t) for t in 0..1 (t = 1 must repeat t = 0 for loops), lets `ik` place legs, reads the
    evaluated pose and writes it as linear keys on every bone into a new action on its own NLA track."""
    n = max(2, int(round(seconds * FPS)))
    names = [b.name for b in rig.data.bones]
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    par = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
    poses = []
    for f in range(n + 1):
        t = f / n
        P.reset()
        targets = fn(P, t)
        bpy.context.view_layer.update()
        if ik and targets:
            ik(rig, targets)
            bpy.context.view_layer.update()
        poses.append({nm: rig.pose.bones[nm].matrix.copy() for nm in names})
    P.reset()
    bpy.context.view_layer.update()
    keys = {nm: [] for nm in names}
    for fr in poses:
        for nm in names:
            p = par[nm]
            if p:
                basis = (rest[p].inverted() @ rest[nm]).inverted() @ fr[p].inverted() @ fr[nm]
            else:
                basis = rest[nm].inverted() @ fr[nm]
            keys[nm].append(basis.decompose())
    ad = rig.animation_data or rig.animation_data_create()
    act = bpy.data.actions.new(name)
    ad.action = act
    for nm in names:
        ks = keys[nm]
        qs = []
        for _, q, _ in ks:
            if qs and qs[-1].dot(q) < 0:
                q = -q
            qs.append(q)
        chans = {"location": [tuple(k[0]) for k in ks], "rotation_quaternion": [tuple(q) for q in qs],
                 "scale": [tuple(k[2]) for k in ks]}
        for path, vals in chans.items():
            restv = (1.0,) * 3 if path == "scale" else ((0.0,) * 3 if path == "location" else None)
            if restv and all(abs(a - b) < 1e-5 for v in vals for a, b in zip(v, restv)):
                continue
            for i in range(len(vals[0])):
                fc = act.fcurve_ensure_for_datablock(rig, 'pose.bones["%s"].%s' % (nm, path), index=i, group_name=nm)
                fc.keyframe_points.add(n + 1)
                co = []
                for f, v in enumerate(vals):
                    co += [float(f), float(v[i])]
                fc.keyframe_points.foreach_set("co", co)
                fc.keyframe_points.foreach_set("interpolation", [1] * (n + 1))    # LINEAR
                fc.update()
    act.use_fake_user = True
    act.use_frame_range = True
    act.frame_start, act.frame_end = 0, n
    act.use_cyclic = name.endswith("_loop")
    ad.action = None
    tr = ad.nla_tracks.new()
    tr.name = name
    tr.strips.new(name, 0, act)
    return act


def wave(t, cycles=1.0, phase=0.0):
    return math.sin(2 * math.pi * (cycles * t + phase))


def pulse(t, a, b, c):
    """0 before a, eases up to 1 at b, holds, eases back to 0 at c."""
    if t <= a or t >= c:
        return 0.0
    return ease((t - a) / (b - a)) if t < b else 1 - ease((t - b) / (c - b))


def bat_wing(S, SH, WR, tips, HP, z0, dih, names, depths, k=1.0, rows=6, cols=16, camber=0.022,
             plates=((0.3, 0.15), (0.65, 0.13)), thumb=0.11, knob="team", arm_kind="chitin"):
    """A left bat wing (mirrored to the right): a chitin arm from the shoulder SH to the wrist WR, finger
    spars from the wrist to `tips` (the first is the wingtip), a membrane slab between the arm, the first
    finger and a scalloped trailing edge through the other tips back to the hip HP; bone claws, a thumb
    claw and a team knob at the wrist, small plates along the arm. Points are top-view (x, y); the
    surface rises from z0 at the shoulder with `dih` degrees of dihedral. `k` scales thicknesses. Weights
    blend body -> names[0] (arm) -> names[1] (hand) along the arm. Returns the key points and the weight
    function."""
    n1, n2, nb = names
    T1 = tips[0]
    DIH = math.tan(math.radians(dih))

    def le_y(x):
        return interp(x, [SH[0], WR[0], T1[0]], [SH[1], WR[1], T1[1]])
    te_pts = []
    for a, b, depth in zip(tips, list(tips[1:]) + [HP], depths):
        mid = Vector(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
        seg = Vector((b[0] - a[0], b[1] - a[1]))
        perp = Vector((-seg.y, seg.x)).normalized()
        if perp.dot(Vector((WR[0], WR[1])) - mid) < 0:
            perp = -perp
        c = mid + perp * depth
        for j in range(12):
            t = j / 12
            p = (1 - t) ** 2 * Vector(a) + 2 * t * (1 - t) * c + t * t * Vector(b)
            te_pts.append((p.x, p.y))
    te_pts.append(HP)
    te_pts.sort()
    te_x, te_yv = [p[0] for p in te_pts], [p[1] for p in te_pts]

    def te_y(x):
        return interp(x, te_x, te_yv)

    def zw(x, y):
        yl, yt = le_y(x), te_y(x)
        c = clamp((y - yl) / max(1e-4, yt - yl))
        return z0 + (x - SH[0]) * DIH + camber * k * math.sin(math.pi * c) - 0.5 * camber * k * c

    def P3(x, y, dz=0.0):
        return Vector((x, y, zw(x, y) + dz))
    sh3, wr3, t13 = P3(*SH), P3(*WR), P3(*T1)
    arm_dir = wr3 - sh3
    arm_len = arm_dir.length
    arm_dir.normalize()
    rb = 0.09 * k

    def wingw(p):
        s = (p - sh3).dot(arm_dir) / arm_len
        w2 = sstep(0.8, 1.06, s)
        wb = 1 - sstep(0.0, rb, p.x - SH[0] + 0.15 * rb)
        return {nb: wb, n1: (1 - w2) * (1 - wb), n2: w2 * (1 - wb)}

    # membrane: a thin closed slab on a grid of spanwise columns and chordwise rows
    x0, x1 = SH[0], T1[0] - 0.006 * k
    xs = sorted(set([round(x0 + (x1 - x0) * j / (cols - 1), 4) for j in range(cols)] + [t[0] for t in tips[1:]] + [WR[0]]))
    th = 0.0065 * k
    g = Geo()
    top, bot = [], []
    for x in xs:
        yl, yt = le_y(x), te_y(x)
        rt, rbt = [], []
        for j in range(rows + 1):
            y = yl + (yt - yl) * j / rows
            z = zw(x, y)
            rt.append(len(g.v))
            g.v.append(Vector((x, y, z + th)))
            rbt.append(len(g.v))
            g.v.append(Vector((x, y, z - th)))
        top.append(rt)
        bot.append(rbt)

    def muv(i, j):
        return ((xs[i] - x0) / (x1 - x0), j / rows)
    for i in range(len(xs) - 1):
        for j in range(rows):
            g.f.append((top[i][j], top[i + 1][j], top[i + 1][j + 1], top[i][j + 1]))
            g.uv.append((muv(i, j), muv(i + 1, j), muv(i + 1, j + 1), muv(i, j + 1)))
            g.f.append((bot[i][j], bot[i][j + 1], bot[i + 1][j + 1], bot[i + 1][j]))
            g.uv.append((muv(i, j), muv(i, j + 1), muv(i + 1, j + 1), muv(i + 1, j)))
    last = len(xs) - 1
    loop = ([(i, 0) for i in range(last)] + [(last, j) for j in range(rows)] +
            [(i, rows) for i in range(last, 0, -1)] + [(0, j) for j in range(rows, 0, -1)])
    cen = Vector((sum(xs) / len(xs), sum(le_y(x) + te_y(x) for x in xs) / (2 * len(xs)), z0))
    for (ia, ja), (ib, jb) in zip(loop, loop[1:] + loop[:1]):
        a, b = top[ia][ja], top[ib][jb]
        c, d = bot[ib][jb], bot[ia][ja]
        nrm = (g.v[b] - g.v[a]).cross(g.v[d] - g.v[a])
        out = (g.v[a] + g.v[b]) / 2 - cen
        out.z = 0
        if nrm.dot(out) > 0:
            g.f.append((a, b, c, d))
            g.uv.append(tuple(muv(*ij) for ij in ((ia, ja), (ib, jb), (ib, jb), (ia, ja))))
        else:
            g.f.append((a, d, c, b))
            g.uv.append(tuple(muv(*ij) for ij in ((ia, ja), (ia, ja), (ib, jb), (ib, jb))))
    S.add(g, "membrane", wingw, mirror=True)
    # arm (leading edge): a chitin tube from the shoulder to the wrist, bowed a little forward
    arm = [P3(*SH) + Vector((-0.01 * k, 0.0, 0.0))]
    for j in range(1, 7):
        t = j / 6
        x, y = lerp(SH[0], WR[0], t), lerp(SH[1], WR[1], t) - 0.022 * k * math.sin(math.pi * t)
        arm.append(Vector((x, y, zw(x, le_y(x)) + 0.004 * k)))
    S.add(tube(arm, [(0, 0.04 * k), (0.5, 0.032 * k), (1, 0.026 * k)], n=9, per=1), arm_kind, wingw, mirror=True)
    # fingers: dark chitin spars from the wrist out along the membrane, bone claws past the tips
    for tip, r0 in zip(tips, (0.022, 0.017, 0.015, 0.015)):
        r0 *= k
        fp = [P3(lerp(WR[0], tip[0], j / 6), lerp(WR[1], tip[1], j / 6), 0.002 * k) for j in range(7)]
        S.add(tube(fp, [(0, r0), (0.6, r0 * 0.7), (1, r0 * 0.45)], n=7, per=1), "chitin_dk", wingw, mirror=True)
        dvec = (fp[-1] - fp[-2]).normalized()
        S.add(spike(fp[-1], dvec, 0.045 * k, r0 * 0.75, bend=0.5, bend_to=(0, 0, -1), n=6, rings=4, sink=0.25),
              "bone", wingw, mirror=True)
    # wrist: a knob and a hooked thumb claw; small plates along the top of the arm
    S.add(blob(wr3 + Vector((0, 0, 0.012 * k)), (0.03 * k, 0.03 * k, 0.026 * k), n=10, rings=6), knob, wingw,
          mirror=True)
    S.add(spike(wr3 + Vector((0.01, -0.01, 0.0)) * k, (0.35, -1.0, 0.15), thumb * k, 0.022 * k, bend=0.9,
                bend_to=(0, 0, -1), n=7, rings=5), "bone", wingw, mirror=True)
    for t, ln in plates:
        x = lerp(SH[0], WR[0], t)
        p = P3(x, le_y(x) - 0.01 * k, 0.025 * k)
        S.add(plate(p, (0.75, 0.55, 0.1), (0, -0.2, 1), ln * k, 0.075 * k, 0.022 * k, 0.15, 0.3, 0.45, n=8, rings=5),
              "plate", wingw, mirror=True)
    return {"sh": sh3, "wr": wr3, "tip": t13, "w": wingw, "P3": P3}


# =========================================================================================================
# the creatures. Each builder returns (skin, rigdef, muzzle (bone, point), anims, info). Front -Y, left +X.
# =========================================================================================================

def skitter():
    S, R = Skin(), RigDef()
    Z = 0.43
    # --- wings (bat wings: a chitin arm, three dark finger spars, a veined membrane) -------------------------
    W = bat_wing(S, SH=(0.085, -0.115), WR=(0.385, -0.205), tips=((0.655, 0.02), (0.56, 0.245), (0.37, 0.335)),
                 HP=(0.085, 0.175), z0=Z + 0.06, dih=17, names=("wing1_L", "wing2_L", "body"),
                 depths=(0.055, 0.06, 0.07))
    sh3, wr3, t13 = W["sh"], W["wr"], W["tip"]
    R.add("root", (0, 0, 0), (0, 0.25, 0))
    R.add("body", (0, 0.07, Z), (0, -0.25, Z + 0.01), "root")
    R.add("head", (0, -0.25, Z + 0.01), (0, -0.48, Z - 0.015), "body")
    R.add("mand_L", (0.034, -0.47, Z - 0.045), (0.028, -0.62, Z - 0.07), "head", mirror=True)
    R.add("tail1", (0, 0.07, Z), (0, 0.27, Z - 0.02), "body")
    R.add("tail2", (0, 0.27, Z - 0.02), (0, 0.46, Z - 0.035), "tail1")
    R.add("tail3", (0, 0.46, Z - 0.035), (0, 0.66, Z + 0.03), "tail2")
    R.add("wing1_L", sh3, wr3, "body", mirror=True)
    R.add("wing2_L", wr3, t13, "wing1_L", mirror=True)
    R.add("scythe_L", (0.055, -0.20, Z - 0.06), (0.10, -0.30, Z - 0.19), "body", mirror=True)
    R.add("leg_L", (0.06, 0.02, Z - 0.07), (0.15, 0.08, Z - 0.22), "body", mirror=True)
    # a bone spike rising from each shoulder
    S.add(spike(sh3 + Vector((-0.01, 0.03, 0.05)), (0.3, 0.4, 1.0), 0.25, 0.034, bend=0.7, bend_to=(0, 1, 0),
                n=7, rings=6), "bone", "body", mirror=True)

    # --- body ---------------------------------------------------------------------------------------------
    # thorax: crimson ribbed flesh under three overlapping armour shells, a team stripe down their middle
    thx = Body([(0, 0.10, Z - 0.005), (0, -0.02, Z), (0, -0.14, Z + 0.005), (0, -0.24, Z + 0.005), (0, -0.31, Z)],
               [(0, 0.075), (0.25, 0.12), (0.55, 0.135), (0.85, 0.115), (1.0, 0.085)],
               [(0, 0.07), (0.25, 0.095), (0.55, 0.1), (0.85, 0.09), (1.0, 0.07)], n=14, belly=0.8)
    S.add(thx.geo(), "flesh", "body")
    for t0, t1, lift in ((0.98, 0.62, 0.03), (0.74, 0.34, 0.032), (0.46, 0.02, 0.03)):
        for a0, a1, kind in ((-8, 76, "plate"), (76, 104, "team"), (104, 188, "plate")):
            S.add(shell(thx, t0, t1, a0, a1, 0.006, 0.024, 5 if kind == "plate" else 2, 6, lift), kind, "body")
    # head: a pointed wedge, a crest plate, four eyes, mandibles, a dark mouth
    hd = [Vector((0, -0.22, Z + 0.01)), Vector((0, -0.33, Z + 0.01)), Vector((0, -0.45, Z - 0.005)),
          Vector((0, -0.57, Z - 0.03))]
    hx = [0, 0.3, 0.7, 1.0]
    S.add(loft(catmull(hd, 3), lambda t: ell(interp(t, hx, [0.075, 0.09, 0.065, 0.0]),
                                             interp(t, hx, [0.066, 0.06, 0.042, 0.0]), 12, 0.75)),
          "chitin", "head")
    S.add(plate((0, -0.545, Z + 0.0), (0, 1, 0.42), (0, -0.3, 1), 0.30, 0.13, 0.034, 0.12, 0.5, 0.55, n=10, rings=6),
          "plate", "head")
    for x, y, z, r in ((0.06, -0.40, Z + 0.032, 0.026), (0.05, -0.457, Z + 0.014, 0.02)):
        S.add(blob((x, y, z), (r, r * 0.9, r * 1.1), n=10, rings=6, axis=(0.8, 0, 0.6)), "eye", "head", mirror=True)
    S.add(blob((0, -0.505, Z - 0.035), (0.04, 0.03, 0.035), n=10, rings=6), "gullet", "head")
    S.add(spike((0.036, -0.47, Z - 0.045), (0.05, -1.0, -0.12), 0.17, 0.024, bend=0.9, bend_to=(-1, 0, 0),
                n=7, rings=6, sink=0.2), "bone", "mand_L", mirror=True)
    # abdomen / tail: segmented flesh under four shells with bone spines, acid sacs on its flanks, a stinger
    tch = Chain(R, ["tail1", "tail2", "tail3"], 0.6)
    tlb = Body([(0, 0.02, Z + 0.005), (0, 0.18, Z), (0, 0.34, Z - 0.03), (0, 0.50, Z - 0.035), (0, 0.62, Z - 0.005),
                (0, 0.68, Z + 0.035)],
               [(0, 0.085), (0.15, 0.108), (0.4, 0.092), (0.7, 0.06), (0.9, 0.036), (1.0, 0.0)],
               [(0, 0.078), (0.15, 0.092), (0.4, 0.08), (0.7, 0.052), (0.9, 0.03), (1.0, 0.0)], n=12, belly=0.85,
               wobble=lambda t: 1 + 0.07 * math.cos(2 * math.pi * t * 5))
    S.add(tlb.geo(), "flesh", tch)
    for t0, t1 in ((0.0, 0.27), (0.2, 0.47), (0.4, 0.67), (0.6, 0.86)):
        S.add(shell(tlb, t0, t1, -10, 190, 0.005, 0.022, 5, 6, 0.028), "plate", tch)
        sp = tlb.point(t0 + 0.6 * (t1 - t0), 90, 0.03)
        if t1 < 0.8:
            S.add(spike(sp, (0, 0.6, 1.0), 0.09 - 0.02 * t0, 0.017, bend=0.6, bend_to=(0, 1, 0), n=6, rings=4),
                  "bone", tch.at(sp))
    for tt in (0.2, 0.36):
        c = tlb.point(tt, 12, 0.01)
        S.add(blob(c, (0.04, 0.045, 0.06 - 0.1 * (tt - 0.2)), n=10, rings=7, axis=(0, 1, 0), up=(1, 0, 0.3),
                   lump=0.12, seed=tt), "glow", tch.at(c), mirror=True)
    S.add(blob((0, 0.63, Z + 0.0), (0.044, 0.044, 0.05), n=10, rings=7, axis=(0, 1, 0.3), lump=0.1, seed=2),
          "glow", "tail3")
    S.add(spike((0, 0.67, Z + 0.03), (0, 0.6, 0.8), 0.16, 0.027, bend=1.2, bend_to=(0, -1, 0.3), n=7, rings=6),
          "bone", "tail3")

    # --- limbs ----------------------------------------------------------------------------------------------
    # scythe arms folded under the head: a dark chitin upper arm, a bone blade hooked forward
    a0, a1 = Vector((0.055, -0.19, Z - 0.05)), Vector((0.10, -0.30, Z - 0.19))
    S.add(tube([a0, a1], [(0, 0.03), (1, 0.022)], n=8), "chitin_dk", "scythe_L", mirror=True)
    S.add(blob(a1, (0.028, 0.028, 0.028), n=8, rings=5), "flesh", "scythe_L", mirror=True)
    S.add(spike(a1, (-0.15, -1.0, 0.55), 0.24, 0.026, bend=1.25, bend_to=(0, 0.2, -1), n=7, rings=7, sink=0.15,
                flare=1.1), "bone", "scythe_L", mirror=True)
    # hind legs: hanging, hooked claws
    l0, l1, l2 = Vector((0.06, 0.02, Z - 0.06)), Vector((0.16, 0.09, Z - 0.21)), Vector((0.15, 0.16, Z - 0.41))
    S.add(tube([l0, l1], [(0, 0.028), (1, 0.02)], n=8), "chitin_dk", "leg_L", mirror=True)
    S.add(blob(l1, (0.022, 0.022, 0.022), n=8, rings=5), "flesh", "leg_L", mirror=True)
    S.add(tube([l1, l2], [(0, 0.02), (1, 0.012)], n=7), "chitin_dk", "leg_L", mirror=True)
    S.add(spike(l2, (0, -0.4, -1.0), 0.07, 0.014, bend=1.0, bend_to=(0, -1, 0), n=6, rings=4, sink=0.2),
          "bone", "leg_L", mirror=True)

    # --- animations ------------------------------------------------------------------------------------------
    def wings(P, flap, lag, sweep=0.0, fold=0.0):
        for side, sg in (("L", 1), ("R", -1)):
            P.rot("wing1_" + side, y=-sg * flap, z=sg * sweep)
            P.rot("wing2_" + side, y=-sg * (lag + fold))

    def tail(P, a, b, sway=0.0):
        P.rot("tail1", x=a, z=sway)
        P.rot("tail2", x=a * 1.2 + b, z=sway * 1.3)
        P.rot("tail3", x=a * 1.4 + 1.5 * b, z=sway * 1.6)

    def idle(P, t):
        beat = 2.0
        ph = wave(t, beat)
        flap = 26 * ph + 4
        lag = 16 * wave(t, beat, -0.18)
        wings(P, flap, lag)
        P.move("root", (0, 0, -0.035 * ph))
        P.rot("body", x=2.5 * wave(t, beat, 0.1))
        tail(P, 3.5 * wave(t, beat, -0.25), 0, 4 * wave(t, 1))
        P.rot("head", x=-2.5 * wave(t, 1, 0.3), z=5 * wave(t, 1, 0.1))
        for s in ("L", "R"):
            sg = 1 if s == "L" else -1
            P.rot("mand_" + s, z=sg * 6 * max(0.0, wave(t, 2, 0.2)))
            P.rot("leg_" + s, x=6 * wave(t, beat, -0.3))
            P.rot("scythe_" + s, x=4 * wave(t, 1, 0.4))

    def fly(P, t):
        ph = wave(t)
        flap = 44 * ph + 6
        lag = 30 * wave(t, 1, -0.2)
        wings(P, flap, lag, sweep=6 * wave(t, 1, 0.25))
        P.rot("body", x=9)
        P.move("root", (0, 0, -0.05 * ph))
        tail(P, -4 + 5 * wave(t, 1, -0.3), 4 * wave(t, 1, -0.5), 0)
        P.rot("head", x=-5)
        for s in ("L", "R"):
            P.rot("leg_" + s, x=35)
            P.rot("scythe_" + s, x=15)

    def attack(P, t):
        k = pulse(t, 0.0, 0.32, 1.0)               # wind up, strike at 0.32, recover
        strike = pulse(t, 0.18, 0.34, 0.75)
        P.rot("body", x=28 * k)
        P.move("root", (0, -0.12 * strike, -0.10 * k))
        wings(P, 30 * k + 8 * wave(t, 1) * (1 - k), 10 * k, sweep=20 * k, fold=25 * k)
        P.rot("head", x=10 * strike)
        for s in ("L", "R"):
            sg = 1 if s == "L" else -1
            P.rot("mand_" + s, z=sg * 28 * pulse(t, 0.05, 0.25, 0.45))
            P.rot("scythe_" + s, x=-70 * strike)
            P.rot("leg_" + s, x=25 * k)
        tail(P, 18 * k, 25 * strike, 0)

    anims = [("idle_loop", 2.4, idle), ("fly_loop", 0.6, fly), ("attack", 0.5, attack)]
    return S, R, ("head", Vector((0, -0.56, Z - 0.03))), anims, {}


def gorgon():
    S, R = Skin(), RigDef()
    Z = 0.86
    # --- the bladder: a bloated veined gas sac, the lower part on the belly bone so it can squeeze ----------
    body = Body([(0, 0.86, Z + 0.06), (0, 0.55, Z + 0.02), (0, 0.1, Z), (0, -0.35, Z - 0.02), (0, -0.70, Z - 0.08)],
                [(0, 0.0), (0.06, 0.3), (0.2, 0.52), (0.45, 0.63), (0.7, 0.58), (0.9, 0.44), (1.0, 0.30)],
                [(0, 0.0), (0.06, 0.2), (0.2, 0.34), (0.45, 0.42), (0.7, 0.39), (0.9, 0.3), (1.0, 0.21)],
                per=4, n=18, belly=1.0, wobble=lambda t: 1 + 0.03 * math.cos(2 * math.pi * t * 4))

    def bellyw(p):
        wb = 0.85 * sstep(Z - 0.08, Z - 0.38, p.z)
        return {"belly": wb, "body": 1 - wb}
    S.add(body.geo(), "bladder", bellyw)

    def tpos(y):                       # body parameter at a given y
        return clamp((0.86 - y) / 1.56)

    def under(x, y, sink=0.05):
        t = tpos(y)
        rx, ry = body.r(t)
        c = body.frame(t)[0]
        return Vector((x, y, c.z - ry * math.sqrt(max(0.0, 1 - (x / rx) ** 2)) + sink))

    # --- carapace: five overlapping shells over the top with a team stripe, flank plates, bone spikes -----
    top = ((0.995, 0.74), (0.82, 0.55), (0.64, 0.37), (0.46, 0.18), (0.28, 0.03))
    for i, (t0, t1) in enumerate(top):
        for a0, a1, kind in ((30, 83, "plate"), (83, 97, "team"), (97, 150, "plate")):
            S.add(shell(body, t0, t1, a0, a1, 0.01, 0.042, 5 if kind == "plate" else 2, 7, 0.055), kind, "body")
        for ang in (74, 106):
            tt = lerp(t0, t1, 0.55)
            base = body.point(tt, ang, 0.05)
            out = body.normal(tt, ang)
            ln = (0.2, 0.22, 0.19, 0.15, 0.11)[i]
            S.add(spike(base, out + Vector((0, 0.9, 0)), ln, 0.035, bend=0.55, bend_to=(0, 1, 0), n=7, rings=5),
                  "bone", "body")
    for side in (0, 1):
        for t0, t1 in ((0.9, 0.62), (0.6, 0.33), (0.33, 0.1)):
            a0, a1 = (-12, 26) if side == 0 else (154, 192)
            S.add(shell(body, t0, t1, a0, a1, 0.008, 0.034, 4, 6, 0.05, mid=(a0 + a1) / 2), "plate", "body")
            tt = lerp(t0, t1, 0.75)
            ang = (a0 + a1) / 2
            base = body.point(tt, ang, 0.04)
            S.add(spike(base, body.normal(tt, ang) + Vector((0, 0.6, -0.3)), 0.12, 0.025, bend=0.5,
                        bend_to=(0, 1, 0), n=6, rings=4), "bone", "body")
    # brow horns over the head, a spiked rump
    for ang in (58, 122):
        base = body.point(0.93, ang, 0.04)
        S.add(spike(base, body.normal(0.93, ang) + Vector((0, -0.5, 0.6)), 0.24, 0.04, bend=0.9, bend_to=(0, 1, 0.3),
                    n=7, rings=6), "bone", "body")
    for dx, dz in ((0.0, 0.08), (0.12, -0.02), (-0.12, -0.02)):
        S.add(spike((dx, 0.80, Z + 0.06 + dz), (dx, 1.0, 0.25 + dz), 0.18, 0.035, bend=0.4, bend_to=(0, 0, 1),
                    n=7, rings=5), "bone", "body")
    # --- acid sacs: two bulging out of each flank seam, pustules on the back, the bomb cluster underneath --
    for tt, r, sd in ((0.70, 0.19, 1), (0.42, 0.21, 2)):
        for ang in (24, 156):
            c = body.point(tt, ang, -0.02)
            S.add(blob(c, (r, r * 0.95, r * 1.1), n=12, rings=8, axis=body.normal(tt, ang), lump=0.14,
                       seed=sd + ang), "glow", "body")
    for tt, ang, r in ((0.13, 72, 0.1), (0.13, 108, 0.1), (0.22, 90, 0.08)):
        c = body.point(tt, ang, 0.02)
        S.add(blob(c, (r, r, r * 0.8), n=10, rings=6, axis=body.normal(tt, ang), lump=0.15, seed=ang), "glow", "body")
    for x, y, r in ((0.0, 0.05, 0.17), (0.2, -0.12, 0.13), (-0.2, -0.12, 0.13), (0.0, 0.3, 0.12)):
        c = under(x, y, 0.07)
        S.add(blob(c, (r, r, r * 0.9), n=12, rings=7, lump=0.15, seed=x + y), "glow", "belly")
    # --- head: an armoured beak hung under the front of the carapace, six eyes, a hinged jaw with tusks ----
    hd = Body([(0, -0.58, Z - 0.08), (0, -0.78, Z - 0.12), (0, -0.96, Z - 0.18), (0, -1.08, Z - 0.25)],
              [(0, 0.26), (0.4, 0.24), (0.8, 0.15), (1.0, 0.0)], [(0, 0.2), (0.4, 0.17), (0.8, 0.1), (1.0, 0.0)],
              per=3, n=14, belly=0.7)
    S.add(hd.geo(), "chitin", "head")
    S.add(shell(hd, 0.25, 0.95, 20, 160, 0.006, 0.03, 5, 6, 0.0, narrow=(0.6, 1.0)), "plate", "head")
    for x, y, z, r in ((0.15, -0.80, Z - 0.05, 0.04), (0.12, -0.88, Z - 0.09, 0.034), (0.17, -0.74, Z - 0.1, 0.03)):
        S.add(blob((x, y, z), (r, r, r * 1.1), n=10, rings=6, axis=(0.7, -0.3, 0.6)), "eye", "head", mirror=True)
    S.add(blob((0, -0.93, Z - 0.27), (0.11, 0.1, 0.07), n=10, rings=6), "gullet", "head")
    jw = Body([(0, -0.70, Z - 0.26), (0, -0.88, Z - 0.31), (0, -1.02, Z - 0.33)],
              [(0, 0.15), (0.6, 0.12), (1.0, 0.0)], [(0, 0.06), (0.6, 0.05), (1.0, 0.0)], per=3, n=12, belly=1.0)
    S.add(jw.geo(), "chitin_dk", "jaw")
    S.add(spike((0.1, -0.92, Z - 0.3), (-0.15, -1.0, -0.2), 0.22, 0.035, bend=1.1, bend_to=(-1, 0, 0.6),
                n=7, rings=6), "bone", "jaw", mirror=True)
    # --- fins: two small bat wings on the flanks ---------------------------------------------------------
    W = bat_wing(S, SH=(0.50, -0.30), WR=(0.92, -0.30), tips=((1.29, 0.06), (1.12, 0.36), (0.84, 0.47)),
                 HP=(0.50, 0.40), z0=Z + 0.1, dih=12, names=("fin1_L", "fin2_L", "body"), depths=(0.09, 0.09, 0.1),
                 k=1.8, plates=((0.4, 0.13), (0.72, 0.11)), thumb=0.08)
    # --- tendrils: six ribbed flesh feelers with bone barbs ----------------------------------------------
    R.add("root", (0, 0, 0), (0, 0.3, 0))
    R.add("body", (0, 0.3, Z), (0, -0.3, Z), "root")
    R.add("belly", (0, 0.05, Z - 0.12), (0, 0.05, Z - 0.46), "body")
    R.add("head", (0, -0.6, Z - 0.1), (0, -1.0, Z - 0.2), "body")
    R.add("jaw", (0, -0.70, Z - 0.26), (0, -1.0, Z - 0.33), "head")
    R.add("fin1_L", W["sh"], W["wr"], "body", mirror=True)
    R.add("fin2_L", W["wr"], W["tip"], "fin1_L", mirror=True)
    tnd = []
    for i, (x, y, ln) in enumerate(((0.24, -0.30, 0.46), (0.38, 0.06, 0.52), (0.22, 0.40, 0.44))):
        p0 = under(x, y, 0.06)
        ctrl = [p0, p0 + Vector((0.03, 0.01, -0.12)), p0 + Vector((0.07, 0.06, -0.26)) * (ln / 0.5),
                p0 + Vector((0.05, 0.13, -0.40)) * (ln / 0.5), p0 + Vector((-0.01, 0.16, -0.48)) * (ln / 0.5)]
        a, b = "tnd%da_L" % (i + 1), "tnd%db_L" % (i + 1)
        R.add(a, ctrl[0], ctrl[2], "belly", mirror=True)
        R.add(b, ctrl[2], ctrl[4], a, mirror=True)
        ch = Chain(R, [a, b], 0.8)
        S.add(tube(ctrl, [(0, 0.06), (0.4, 0.04), (0.8, 0.024), (1, 0.014)], n=9, per=3,
                   wobble=lambda t: 1 + 0.16 * math.cos(2 * math.pi * t * 7)), "flesh", ch, mirror=True)
        d = (ctrl[4] - ctrl[3]).normalized()
        S.add(spike(ctrl[4], d, 0.1, 0.02, bend=1.0, bend_to=(0, -1, 0), n=6, rings=4, sink=0.2), "bone", b,
              mirror=True)
        tnd.append((i + 1, 0.23 * i))

    # --- animations ------------------------------------------------------------------------------------------
    def fins(P, flap, lag, sweep=0.0):
        for side, sg in (("L", 1), ("R", -1)):
            P.rot("fin1_" + side, y=-sg * flap, z=sg * sweep)
            P.rot("fin2_" + side, y=-sg * lag)

    def tendrils(P, fn):
        for i, ph in tnd:
            for side, sg in (("L", 1), ("R", -1)):
                (ax, ay), (bx, by) = fn(ph + (0.11 if sg < 0 else 0.0))
                P.rot("tnd%da_%s" % (i, side), x=ax, y=-sg * ay)
                P.rot("tnd%db_%s" % (i, side), x=bx, y=-sg * by)

    def idle(P, t):
        P.move("root", (0, 0, 0.045 * wave(t, 1)))
        P.rot("body", x=2.5 * wave(t, 1, 0.25), y=2.5 * wave(t, 1, 0.1))
        P.scale("body", 1 + 0.018 * wave(t, 2))
        w2 = wave(t, 2, 0.25)
        P.scale("belly", (1 + 0.04 * w2, 1 - 0.05 * w2, 1 + 0.04 * w2))
        fins(P, 4 + 13 * wave(t, 2), 16 * wave(t, 2, -0.2))
        tendrils(P, lambda ph: ((7 * wave(t, 1, ph), 6 * wave(t, 1, ph + 0.25)),
                                (13 * wave(t, 1, ph - 0.2), 9 * wave(t, 1, ph + 0.05))))
        P.rot("head", x=3 * wave(t, 2, 0.1), z=6 * wave(t, 1, 0.3))
        P.rot("jaw", x=7 * max(0.0, wave(t, 2, 0.1)))

    def fly(P, t):
        P.move("root", (0, 0, -0.04 * wave(t, 1)))
        P.rot("body", x=7)
        fins(P, 6 + 30 * wave(t), 22 * wave(t, 1, -0.2), sweep=5 * wave(t, 1, 0.25))
        tendrils(P, lambda ph: ((26 + 5 * wave(t, 1, ph), 3 * wave(t, 1, ph + 0.25)),
                                (16 + 12 * wave(t, 1, ph - 0.25), 5 * wave(t, 1, ph))))
        P.rot("head", x=-6)
        P.rot("jaw", x=4)
        P.scale("belly", (1 + 0.03 * wave(t, 1), 1 - 0.04 * wave(t, 1), 1 + 0.03 * wave(t, 1)))

    def attack(P, t):
        sq = pulse(t, 0.0, 0.3, 0.42)              # squeeze the bomb sacs
        rel = pulse(t, 0.3, 0.42, 0.95)            # and let go: the belly kicks down, the body bounces up
        P.scale("belly", ((1 + 0.16 * sq) * (1 - 0.08 * rel), (1 - 0.28 * sq) * (1 + 0.32 * rel), (1 + 0.16 * sq) * (1 - 0.08 * rel)))
        P.scale("body", 1 - 0.04 * sq + 0.03 * rel)
        P.move("root", (0, 0, -0.05 * sq + 0.12 * rel))
        P.rot("body", x=-6 * sq + 4 * rel)
        fins(P, 26 * sq - 28 * rel, 14 * sq - 20 * rel)
        tendrils(P, lambda ph: ((-8 * sq + 14 * rel, 28 * sq - 10 * rel), (-6 * sq + 18 * rel, 20 * sq - 6 * rel)))
        P.rot("head", x=-10 * sq)
        P.rot("jaw", x=26 * pulse(t, 0.05, 0.28, 0.6))

    anims = [("idle_loop", 3.0, idle), ("fly_loop", 0.8, fly), ("attack", 0.6, attack)]
    return S, R, ("belly", Vector((0, 0.05, Z - 0.52))), anims, {}


BUILDERS = {"void_skitter": skitter, "void_gorgon": gorgon}


# --- checks, export, re-import ------------------------------------------------------------------------------

def settle(skin, rd, extra):
    """Lowest point to z = 0, bounding box centred in X and Y; moves bones and marker points with it."""
    vs = skin.v
    lo = Vector((min(p.x for p in vs), min(p.y for p in vs), min(p.z for p in vs)))
    hi = Vector((max(p.x for p in vs), max(p.y for p in vs), max(p.z for p in vs)))
    d = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    skin.shift(d)
    for b in rd.b.values():
        b["head"] = b["head"] - d
        b["tail"] = b["tail"] - d
    rd.b["root"]["head"] = Vector((0, 0, 0))
    rd.b["root"]["tail"] = Vector((0, 0.25 * max(1.0, (hi.z - lo.z)), 0))
    return d, hi - lo, [p - d for p in extra]


def export(objs, path):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True,
                              export_yup=True, export_cameras=False, export_lights=False,
                              export_skins=True, export_animations=True, export_animation_mode="ACTIONS",
                              export_force_sampling=True, export_frame_step=1, export_def_bones=False)


def reimport(path):
    """Opens the GLB in a fresh scene and reports what a consumer sees."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=path)
    fps = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.vertex_groups]
    tris = 0
    for o in meshes:
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)
    anims = {a.name: round((a.frame_range[1] - a.frame_range[0]) / fps, 3) for a in bpy.data.actions}
    return {"animations_seconds": anims, "armatures": [o.name for o in arms],
            "bones": len(arms[0].data.bones) if arms else 0,
            "skinned_meshes": [o.name for o in meshes], "triangles": tris,
            "materials": sorted({m.name for o in meshes for m in o.data.materials if m}),
            "empties": [o.name for o in bpy.data.objects if o.type == "EMPTY"]}


# --- review and icon renders ---------------------------------------------------------------------------

def set_action(rig, act):
    ad = rig.animation_data
    for tr in ad.nla_tracks:
        tr.mute = True
    ad.action = act
    if act is not None and act.slots:
        ad.action_slot = act.slots[0]


def grid_sheet(paths, cols, out, cell=256, bgc=(0.2, 0.21, 0.23)):
    rows = (len(paths) + cols - 1) // cols
    s = np.zeros((rows * cell, cols * cell, 4), np.float32)
    s[..., :3] = bgc
    s[..., 3] = 1
    for i, p in enumerate(paths):
        if p is None:
            continue
        a = V.load_px(p)
        h, w = a.shape[:2]
        r, c = i // cols, i % cols
        y0 = (rows - 1 - r) * cell + (cell - h) // 2
        x0 = c * cell + (cell - w) // 2
        al = a[..., 3:4]
        s[y0:y0 + h, x0:x0 + w, :3] = a[..., :3] * al + s[y0:y0 + h, x0:x0 + w, :3] * (1 - al)
    img = bpy.data.images.new("grid", s.shape[1], s.shape[0], alpha=True)
    img.pixels.foreach_set(s.ravel())
    img.filepath_raw = out
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def review(uid, rig, ob, rnd, acts, sheet_view):
    sc = bpy.context.scene
    set_action(rig, None)
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    cam, ground, bg = V.stage()
    out = os.path.join(HERE, "review", "round%d" % rnd)
    os.makedirs(out, exist_ok=True)
    pts = V.world_points([ob], 4000)
    shots = []
    ground.hide_render = True
    V.fit(cam, pts, 35, 24, 0.04)
    icon = os.path.join(V.ICONS, uid + ".png")
    V.render(icon, (256, 256), True)
    bg.inputs[0].default_value = (0.05, 0.053, 0.06, 1)
    for name, az, el in (("front", 35, 22), ("back", -140, 26)) + ((("top", 0, 89.5),) if uid in AIR else ()):
        V.fit(cam, pts, az, el, 0.08)
        shots.append(os.path.join(out, "%s_%s.png" % (uid, name)))
        V.render(shots[-1], (512, 512), False)
    # the game camera: 55 degrees down, 45 degree vertical field of view, on the ground; air units lifted
    ground.hide_render = False
    lift = AIR.get(uid, 0.0)
    rig.location.z += lift
    tgt = Vector((0, 0, 0.5 + lift))
    crops = []
    for dist in (25, 45):
        cam.data.lens_unit, cam.data.sensor_fit = "FOV", "VERTICAL"
        cam.data.angle = math.radians(45)
        cam.data.shift_x = cam.data.shift_y = 0.0
        cam.location = tgt + V.view_dir(-25, 55) * dist
        V.look(cam, tgt)
        full = os.path.join(out, "%s_game%s.png" % (uid, "" if dist == 25 else "45"))
        # 1024 px tall at a 45 degree field of view is about a 1080p phone held landscape; the crop is
        # the unit at the pixel size a player sees
        V.render(full, (1024, 1024), False)
        a = V.load_px(full)
        h = a.shape[0]
        c = a[h // 2 - 192:h // 2 + 192, h // 2 - 192:h // 2 + 192]
        crop = full.replace(".png", "_crop.png")
        img = bpy.data.images.new("crop", 384, 384, alpha=True)
        img.pixels.foreach_set(np.ascontiguousarray(c).ravel())
        img.filepath_raw, img.file_format = crop, "PNG"
        img.save()
        bpy.data.images.remove(img)
        shots.append(full)
        crops.append(crop)
    rig.location.z -= lift
    V.sheet([p for p in shots if "_game" not in p] + crops + [icon], os.path.join(out, uid + "_sheet.png"), cell=512)
    # animation contact sheet: one row per action, five frames each, fixed camera
    ground.hide_render = True
    az, el = sheet_view
    allp = []
    samples = {}
    for act in acts:
        n = int(act.frame_range[1])
        fr = [round(n * k / 5) for k in range(5)] if act.name != "attack" else [0, round(n * 0.2), round(n * 0.34),
                                                                                round(n * 0.55), round(n * 0.8)]
        samples[act.name] = fr
        set_action(rig, act)
        for f in fr:
            sc.frame_set(f)
            allp += V.world_points([ob], 1500)
    V.fit(cam, allp, az, el, 0.05)
    tiles = []
    tmp = os.path.join(CACHE, "frames")
    for act in acts:
        set_action(rig, act)
        for f in samples[act.name]:
            sc.frame_set(f)
            p = os.path.join(tmp, "%s_%s_%03d.png" % (uid, act.name, f))
            V.render(p, (256, 256), True)
            tiles.append(p)
    grid_sheet(tiles, 5, os.path.join(out, uid + "_anim.png"))
    set_action(rig, None)
    sc.frame_set(0)
    return shots


# --- main ------------------------------------------------------------------------------------------------

SHEET_VIEW = {"void_skitter": (25, 18), "void_gorgon": (25, 15), "void_leviathan": (70, 14)}


def build(uid, rnd, do_render):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps, sc.render.fps_base = FPS, 1.0
    mats = make_materials()
    skin, rd, (mbone, mpt), anims, extra = BUILDERS[uid]()
    d, dims, (mpt,) = settle(skin, rd, [mpt])
    rig = make_rig(rd)
    ob = make_mesh(skin, uid, mats, rig)
    muz = bone_empty("muzzle", rig, mbone, mpt)
    P = Poser(rig)
    acts = []
    for name, secs, fn in anims:
        acts.append(bake(rig, P, name, secs, fn, extra.get("ik")))
    path = os.path.join(V.MODELS, uid + ".glb")
    export([rig, ob, muz], path)
    info = {
        "id": uid,
        "triangles": skin.tris(),
        "parts": skin.parts,
        "inward_parts": skin.flipped,
        "size_m": [round(v, 3) for v in dims],
        "bones": len(rig.data.bones),
        "bone_names": [b.name for b in rig.data.bones],
        "glb_bytes": os.path.getsize(path),
        "materials": [m.name for m in mats],
        "actions": {a.name: round(a.frame_range[1] / FPS, 3) for a in acts},
        "muzzle": {"bone": mbone, "rest": [round(v, 3) for v in mpt]},
    }
    if do_render:
        review(uid, rig, ob, rnd, acts, SHEET_VIEW[uid])
    info["reimport"] = reimport(path)
    print("[shardfall]", json.dumps(info))
    os.makedirs(os.path.join(HERE, "review"), exist_ok=True)
    with open(os.path.join(HERE, "review", uid + "_stats.json"), "w") as f:
        json.dump(info, f, indent=1)
    return info


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    which = argv[0] if argv else "all"
    rnd = int(argv[argv.index("--round") + 1]) if "--round" in argv else 1
    ids = IDS if which == "all" else [which]
    for uid in ids:
        if uid not in BUILDERS:
            raise SystemExit("unknown id " + uid)
        build(uid, rnd, "--no-render" not in argv)


if __name__ == "__main__":
    main()
